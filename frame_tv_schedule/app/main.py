from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from html import escape
import logging
from pathlib import Path
import re
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import File, Form, HTTPException, Request, UploadFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from .art_library import ArtLibrary
from .art_window_manager import ArtWindowManager, generated_today
from .calendar_client import HomeAssistantCalendarClient
from .config import config_json, load_config
from .frame_client import FrameClient
from .renderer import ScheduleRenderer
from .state_store import StateStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("frame_tv_schedule")

config = load_config()
window_manager = ArtWindowManager(config)
calendar_client = HomeAssistantCalendarClient(config)
frame_client = FrameClient(config)
renderer = ScheduleRenderer(config)
state_store = StateStore()
art_library = ArtLibrary(width=config.image_width, height=config.image_height)
thumbnail_cache_path = Path("/config/tv-art-thumbnails")
thumbnail_cache_path.mkdir(parents=True, exist_ok=True)
scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.timezone))


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(
        "starting add-on push_mode=%s tv_host=%s calendar_entities=%s display_windows=%s",
        config.push_mode,
        config.tv_host or "(not set)",
        config.calendar_entities,
        [window.model_dump() for window in config.display_windows],
    )
    scheduler.add_job(tick, "interval", minutes=max(config.refresh_minutes, 1), next_run_time=datetime.now(ZoneInfo(config.timezone)))
    for window in config.display_windows:
        scheduler.add_job(tick, "cron", hour=parse_hour(window.start), minute=parse_minute(window.start))
        scheduler.add_job(tick, "cron", hour=parse_hour(window.end), minute=parse_minute(window.end))
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Frame TV Schedule", lifespan=lifespan)


@app.get("/")
async def index() -> HTMLResponse:
    return schedule_page()


@app.get("/art")
async def art_page() -> HTMLResponse:
    state = state_store.read()
    art_images = art_library.list_images()
    art_options = render_art_options(art_images, selected_artwork_file(state))
    art_grid = render_addon_art_grid(art_images, selected_artwork_file(state))
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        {page_styles()}
      </head>
      <body>
        {nav("art")}
        {render_status(state)}
        <h1>Art Library</h1>
        <div class="action-panel">
          <form method="post" action="./upload-art" enctype="multipart/form-data">
            <input type="file" name="art_file" accept="image/*" required>
            <button>Upload Art</button>
          </form>
          <form method="post" action="./push-art">
            <select name="art_name" required>{art_options}</select>
            <button>Push Selected Art</button>
          </form>
          <form method="post" action="./set-fallback-art">
            <select name="art_name" required>{art_options}</select>
            <button>Use Selected Art as Artwork</button>
          </form>
        </div>
        <div class="art-grid">{art_grid}</div>
      </body>
    </html>
    """
    return HTMLResponse(body)


@app.get("/tv-art")
async def tv_art_page() -> HTMLResponse:
    state = state_store.read()
    tv_art_options = render_tv_art_options(state.get("tv_art_items", []), selected_artwork_tv_id(state))
    tv_art_grid = render_tv_art_grid(state.get("tv_art_items", []), selected_artwork_tv_id(state))
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        {page_styles()}
      </head>
      <body>
        {nav("tv-art")}
        {render_status(state)}
        <h1>TV Art</h1>
        <p>Refresh the list from the Samsung Frame TV, then select an existing TV art item to display or use as Artwork.</p>
        <div class="action-panel">
          <form method="post" action="./refresh-tv-art"><button>Refresh TV Art List</button></form>
          <form method="post" action="./push-tv-art">
            <select name="art_id" required>{tv_art_options}</select>
            <button>Push Selected TV Art</button>
          </form>
          <form method="post" action="./set-fallback-tv-art">
            <select name="art_id" required>{tv_art_options}</select>
            <button>Use Selected TV Art as Artwork</button>
          </form>
        </div>
        <div class="art-grid">{tv_art_grid}</div>
      </body>
    </html>
    """
    return HTMLResponse(body)


@app.get("/current-tv")
async def current_tv_page() -> HTMLResponse:
    state = state_store.read()
    current = state.get("current_tv_art", {})
    current_html = render_current_tv_art(current, state.get("tv_art_items", []))
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        {page_styles()}
      </head>
      <body>
        {nav("current-tv")}
        {render_status(state)}
        <h1>Current TV Image</h1>
        <p>Refresh this page's TV status to see the current Samsung Frame art ID reported by the TV.</p>
        <div class="subnav">
          <form method="post" action="./refresh-current-tv"><button>Refresh Current TV Image</button></form>
        </div>
        {current_html}
      </body>
    </html>
    """
    return HTMLResponse(body)


@app.get("/diagnostics")
async def diagnostics_page() -> HTMLResponse:
    state = state_store.read()
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        {page_styles()}
      </head>
      <body>
        {nav("diagnostics")}
        {render_status(state)}
        <h1>Diagnostics</h1>
        <div class="subnav">
          <form method="post" action="./tick"><button>Run Window Check</button></form>
          <form method="post" action="./calendar-debug"><button>Run Calendar Debug</button></form>
          <form method="post" action="./weather-debug"><button>Run Weather Debug</button></form>
        </div>
        <h2>Calendar Debug</h2>
        <pre>{escape(json_dump(state.get("calendar_debug", {})))}</pre>
        <h2>Weather Debug</h2>
        <pre>{escape(json_dump(state.get("weather_debug", {})))}</pre>
        <h2>State</h2>
        <pre>{escape(json_dump(state))}</pre>
        <h2>Config</h2>
        <pre>{escape(config_json(config))}</pre>
      </body>
    </html>
    """
    return HTMLResponse(body)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/image")
async def image() -> FileResponse:
    if not renderer.output_path.exists():
        await generate_schedule()
    return FileResponse(renderer.output_path, media_type="image/png")


@app.get("/tv-art-thumbnail/{filename}")
async def tv_art_thumbnail(filename: str) -> FileResponse:
    path = thumbnail_cache_path / Path(filename).name
    if path.parent != thumbnail_cache_path or not path.exists():
        raise HTTPException(status_code=404, detail="TV art thumbnail not found")
    return FileResponse(path, media_type=media_type_for_thumbnail(path))


@app.get("/addon-art-image/{filename}")
async def addon_art_image(filename: str) -> FileResponse:
    path = art_library.get(filename)
    return FileResponse(path, media_type="image/png")


@app.post("/generate", response_model=None)
async def generate_route(request: Request) -> Response:
    result = await run_ui_action(generate_schedule_action)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/tick", response_model=None)
async def tick_route(request: Request) -> Response:
    result = await run_ui_action(tick)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/push-calendar", response_model=None)
async def push_calendar_route(request: Request) -> Response:
    result = await run_ui_action(push_calendar_image)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/push-fallback", response_model=None)
async def push_fallback_route(request: Request) -> Response:
    result = await run_ui_action(push_fallback_image)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/upload-art", response_model=None)
async def upload_art_route(request: Request, art_file: UploadFile = File(...)) -> Response:
    result = await run_ui_action(lambda: upload_art(art_file))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./art", status_code=303)


@app.post("/push-art", response_model=None)
async def push_art_route(request: Request, art_name: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: push_library_art(art_name))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./art", status_code=303)


@app.post("/set-fallback-art", response_model=None)
async def set_fallback_art_route(request: Request, art_name: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: set_fallback_art(art_name))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./art", status_code=303)


@app.post("/delete-art", response_model=None)
async def delete_art_route(request: Request, art_name: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: delete_library_art(art_name))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./art", status_code=303)


@app.post("/refresh-tv-art", response_model=None)
async def refresh_tv_art_route(request: Request) -> Response:
    result = await run_ui_action(refresh_tv_art)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./tv-art", status_code=303)


@app.post("/push-tv-art", response_model=None)
async def push_tv_art_route(request: Request, art_id: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: push_tv_art(art_id))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./tv-art", status_code=303)


@app.post("/set-fallback-tv-art", response_model=None)
async def set_fallback_tv_art_route(request: Request, art_id: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: set_fallback_tv_art(art_id))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./tv-art", status_code=303)


@app.post("/delete-tv-art", response_model=None)
async def delete_tv_art_route(request: Request, art_id: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: delete_tv_art(art_id))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./tv-art", status_code=303)


@app.post("/refresh-current-tv", response_model=None)
async def refresh_current_tv_route(request: Request) -> Response:
    result = await run_ui_action(refresh_current_tv)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./current-tv", status_code=303)


@app.post("/calendar-debug", response_model=None)
async def calendar_debug_route(request: Request) -> Response:
    result = await run_ui_action(calendar_debug)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./diagnostics", status_code=303)


@app.post("/weather-debug", response_model=None)
async def weather_debug_route(request: Request) -> Response:
    result = await run_ui_action(weather_debug)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./diagnostics", status_code=303)


async def generate_schedule() -> Path:
    start, end = window_manager.today_bounds()
    logger.info(
        "generating schedule for calendar_entities=%s start=%s end=%s",
        config.calendar_entities,
        start.isoformat(),
        end.isoformat(),
    )
    events = await calendar_client.get_events(config.calendar_entities, start, end)
    weather = await calendar_client.get_hourly_weather(config.weather_entity)
    path = renderer.render(events, weather=weather)
    logger.info("generated schedule image at %s with %s event(s) and %s weather forecast(s)", path, len(events), len(weather))
    weather_note = " Weather was skipped." if config.weather_entity and not weather else ""
    state_store.update(
        {
            "last_action": f"Generated schedule image with {len(events)} event(s) and {len(weather)} weather forecast(s).{weather_note}",
            "last_generated": datetime.now(ZoneInfo(config.timezone)).isoformat(),
            "event_count": len(events),
            "weather_count": len(weather),
        }
    )
    return path


async def generate_schedule_action() -> dict[str, str]:
    path = await generate_schedule()
    return {"action": "generate", "image": str(path), "message": "Generated schedule image."}


async def tick() -> dict[str, str]:
    should_show = window_manager.should_show_schedule()
    state = state_store.read()
    active = bool(state.get("schedule_active")) and state.get("schedule_push_mode") == config.push_mode
    logger.info(
        "window check push_mode=%s should_show=%s active=%s stored_push_mode=%s tv_host=%s",
        config.push_mode,
        should_show,
        active,
        state.get("schedule_push_mode", ""),
        config.tv_host or "(not set)",
    )

    if should_show and not active:
        await push_schedule_to_frame("Window check", force_generate=True)
        return {"action": "show_schedule", "message": "Generated and pushed schedule image for the active display window."}

    if not should_show and active:
        result = await show_window_fallback_image()
        state_store.update(
            {
                "last_action": result["message"],
                "schedule_active": False,
                "schedule_push_mode": config.push_mode,
            }
        )
        logger.info("window check showed artwork")
        return {"action": "show_artwork", "message": "Showed Artwork after the schedule window."}

    state_store.update({"last_action": "Window check completed. No display change was needed."})
    logger.info("window check completed with no display change")
    return {"action": "no_change", "message": "Window check completed. No display change was needed."}


async def push_calendar_image() -> dict[str, str]:
    logger.info("push calendar requested push_mode=%s tv_host=%s", config.push_mode, config.tv_host or "(not set)")
    await push_schedule_to_frame("Manual calendar push", force_generate=True)
    return {"action": "show_schedule", "message": "Generated and pushed the calendar image."}


async def push_fallback_image() -> dict[str, str]:
    result = await show_selected_fallback_image()
    state_store.update(
        {
            "last_action": result["message"],
            "schedule_active": False,
            "schedule_push_mode": config.push_mode,
        }
    )
    return result


async def show_window_fallback_image() -> dict[str, str]:
    return await show_selected_fallback_image()


async def show_selected_fallback_image(allow_empty: bool = False) -> dict[str, str]:
    state = state_store.read()
    artwork_tv_art_id = selected_artwork_tv_id(state)
    if artwork_tv_art_id:
        logger.info("push artwork requested from TV art id=%s", artwork_tv_art_id)
        await frame_client.select_art(artwork_tv_art_id)
        return {"action": "push_artwork", "art_id": artwork_tv_art_id, "message": f"Pushed Artwork TV art {artwork_tv_art_id}."}

    artwork_art_file = selected_artwork_file(state)
    if artwork_art_file:
        path = art_library.get(artwork_art_file)
        logger.info("push artwork requested from art library path=%s", path)
        await frame_client.show_image(path, label=f"artwork_{path.stem}")
        return {"action": "push_artwork", "image": path.name, "message": f"Pushed Artwork {path.name} to the Frame TV."}

    message = "No Artwork is configured."
    if allow_empty:
        return {"action": "push_artwork", "message": message}
    raise RuntimeError(message)


async def upload_art(art_file: UploadFile) -> dict[str, str]:
    path = await art_library.save_upload(art_file)
    state_store.update({"last_action": f"Uploaded art image {path.name}."})
    logger.info("uploaded art library image path=%s", path)
    return {"action": "upload_art", "image": path.name, "message": f"Uploaded art image {path.name}."}


async def push_library_art(art_name: str) -> dict[str, str]:
    path = art_library.get(art_name)
    logger.info("push selected art requested path=%s", path)
    await frame_client.show_image(path, label=f"library_{path.stem}")
    state_store.update(
        {
            "last_action": f"Pushed selected art {path.name} to the Frame TV.",
            "schedule_active": False,
            "schedule_push_mode": config.push_mode,
        }
    )
    return {"action": "push_art", "image": path.name, "message": f"Pushed selected art {path.name} to the Frame TV."}


async def set_fallback_art(art_name: str) -> dict[str, str]:
    path = art_library.get(art_name)
    state_store.update(
        {
            "last_action": f"Set Artwork to {path.name}.",
            "artwork_art_file": path.name,
            "artwork_tv_art_id": "",
            "fallback_art_file": "",
            "fallback_tv_art_id": "",
        }
    )
    logger.info("artwork set to path=%s", path)
    return {"action": "set_artwork", "image": path.name, "message": f"Set Artwork to {path.name}."}


async def delete_library_art(art_name: str) -> dict[str, str]:
    path = art_library.delete(art_name)
    state = state_store.read()
    update: dict[str, Any] = {"last_action": f"Deleted add-on art {path.name}."}
    if selected_artwork_file(state) == path.name:
        update["artwork_art_file"] = ""
        update["fallback_art_file"] = ""
    state_store.update(update)
    logger.info("deleted art library image path=%s", path)
    return {"action": "delete_art", "image": path.name, "message": f"Deleted add-on art {path.name}."}


async def refresh_tv_art() -> dict[str, str]:
    items = await frame_client.list_available_art()
    cached_items = await cache_tv_art_thumbnails(items)
    state_store.update(
        {
            "last_action": f"Loaded {len(cached_items)} art item(s) from the Frame TV.",
            "tv_art_items": cached_items,
        }
    )
    return {"action": "refresh_tv_art", "count": str(len(cached_items)), "message": f"Loaded {len(cached_items)} art item(s) from the Frame TV."}


async def push_tv_art(art_id: str) -> dict[str, str]:
    await frame_client.select_art(art_id)
    state_store.update(
        {
            "last_action": f"Pushed TV art {art_id}.",
            "schedule_active": False,
            "schedule_push_mode": config.push_mode,
        }
    )
    return {"action": "push_tv_art", "art_id": art_id, "message": f"Pushed TV art {art_id}."}


async def set_fallback_tv_art(art_id: str) -> dict[str, str]:
    state_store.update(
        {
            "last_action": f"Set Artwork to TV art {art_id}.",
            "artwork_tv_art_id": art_id,
            "artwork_art_file": "",
            "fallback_tv_art_id": "",
            "fallback_art_file": "",
        }
    )
    return {"action": "set_artwork", "art_id": art_id, "message": f"Set Artwork to TV art {art_id}."}


async def delete_tv_art(art_id: str) -> dict[str, str]:
    await frame_client.delete_art(art_id)
    state = state_store.read()
    items = remove_tv_art_item(state.get("tv_art_items", []), art_id)
    update: dict[str, Any] = {"last_action": f"Deleted TV art {art_id}.", "tv_art_items": items}
    if selected_artwork_tv_id(state) == art_id:
        update["artwork_tv_art_id"] = ""
        update["fallback_tv_art_id"] = ""
    current = state.get("current_tv_art", {})
    if isinstance(current, dict) and str(current.get("art_id", "")) == art_id:
        update["current_tv_art"] = {}
    delete_existing_thumbnail(art_id)
    state_store.update(update)
    return {"action": "delete_tv_art", "art_id": art_id, "message": f"Deleted TV art {art_id}."}


async def refresh_current_tv() -> dict[str, str]:
    item = await frame_client.current_art()
    current = {
        "art_id": item.art_id,
        "title": item.title,
        "checked_at": datetime.now(ZoneInfo(config.timezone)).isoformat(),
        "push_mode": config.push_mode,
    }
    state_store.update({"current_tv_art": current})
    art_label = item.art_id or item.title or "current TV art"
    return {"action": "refresh_current_tv", "art_id": item.art_id, "message": f"Loaded current TV image: {art_label}."}


async def calendar_debug() -> dict[str, str]:
    start, end = window_manager.today_bounds()
    result = await calendar_client.debug_calendar_fetch(config.calendar_entities, start, end)
    state_store.update({"last_action": "Calendar debug completed.", "calendar_debug": result})
    return {"action": "calendar_debug", "message": "Calendar debug completed."}


async def weather_debug() -> dict[str, str]:
    result = await calendar_client.debug_weather_fetch(config.weather_entity)
    state_store.update({"last_action": "Weather debug completed.", "weather_debug": result})
    return {"action": "weather_debug", "message": "Weather debug completed."}


async def push_schedule_to_frame(action_label: str, force_generate: bool = False) -> None:
    await ensure_current_schedule_image(force=force_generate)
    state_store.update(
        {
            "last_action": f"{action_label} is showing the schedule on the Frame TV.",
            "schedule_active": True,
            "schedule_push_mode": config.push_mode,
        }
    )
    await frame_client.show_schedule(renderer.output_path)
    state_store.update(
        {
            "last_action": f"{action_label} showed the schedule on the Frame TV.",
            "schedule_active": True,
            "schedule_push_mode": config.push_mode,
        }
    )
    logger.info("%s showed schedule using push_mode=%s", action_label.lower(), config.push_mode)


async def ensure_current_schedule_image(force: bool = False) -> None:
    now = datetime.now(ZoneInfo(config.timezone))
    state = state_store.read()
    if force or not renderer.output_path.exists() or not generated_today(state, now, ZoneInfo(config.timezone)):
        await generate_schedule()


async def run_ui_action(action: Any) -> dict[str, Any]:
    try:
        result = await action()
        message = str(result.get("message", "Action completed.")) if isinstance(result, dict) else "Action completed."
        state_store.update(action_status(message, "success", result if isinstance(result, dict) else {}))
        return result
    except Exception as error:
        logger.exception("web UI action failed")
        message = f"{type(error).__name__}: {error}"
        result = {"action": "error", "error": message}
        state_store.update(action_status(f"Action failed: {message}", "error", result))
        return result


def action_status(message: str, status: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_action": message,
        "last_action_status": status,
        "last_action_time": datetime.now(ZoneInfo(config.timezone)).isoformat(),
        "last_action_result": result,
    }


def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


def selected_artwork_file(state: dict[str, Any]) -> str:
    return str(state.get("artwork_art_file", "") or state.get("fallback_art_file", ""))


def selected_artwork_tv_id(state: dict[str, Any]) -> str:
    return str(state.get("artwork_tv_art_id", "") or state.get("fallback_tv_art_id", ""))


def render_art_options(paths: list[Path], selected_name: str = "") -> str:
    if not paths:
        return '<option value="">Upload art first</option>'
    options = []
    for path in paths:
        selected = " selected" if path.name == selected_name else ""
        label = escape(path.stem.replace("-", " "))
        value = escape(path.name)
        options.append(f'<option value="{value}"{selected}>{label}</option>')
    return "\n".join(options)


def render_tv_art_options(items: Any, selected_art_id: str = "") -> str:
    if not isinstance(items, list) or not items:
        return '<option value="">Refresh TV art first</option>'
    options = []
    for item in items:
        if not isinstance(item, dict):
            continue
        art_id = str(item.get("art_id", ""))
        if not art_id:
            continue
        title = str(item.get("title", "")) or art_id
        selected = " selected" if art_id == selected_art_id else ""
        options.append(f'<option value="{escape(art_id)}"{selected}>{escape(title)} ({escape(art_id)})</option>')
    return "\n".join(options) or '<option value="">Refresh TV art first</option>'


def render_addon_art_grid(paths: list[Path], selected_name: str = "") -> str:
    if not paths:
        return '<p>No add-on art uploaded yet.</p>'
    cards = []
    for path in paths:
        selected = " selected" if path.name == selected_name else ""
        title = path.stem.replace("-", " ")
        cards.append(
            f"""
            <article class="art-card{selected}">
              <img src="./addon-art-image/{escape(path.name)}" alt="{escape(title)}">
              <div class="art-title">{escape(title)}</div>
              <div class="art-id">{escape(path.name)}</div>
              <form method="post" action="./push-art">
                <input type="hidden" name="art_name" value="{escape(path.name)}">
                <button>Show</button>
              </form>
              <form method="post" action="./set-fallback-art">
                <input type="hidden" name="art_name" value="{escape(path.name)}">
                <button>Set Artwork</button>
              </form>
              <form method="post" action="./delete-art">
                <input type="hidden" name="art_name" value="{escape(path.name)}">
                <button class="danger">Delete</button>
              </form>
            </article>
            """
        )
    return "\n".join(cards)


def render_tv_art_grid(items: Any, selected_art_id: str = "") -> str:
    if not isinstance(items, list) or not items:
        return '<p>No TV art loaded yet.</p>'
    cards = []
    for item in items:
        if not isinstance(item, dict):
            continue
        art_id = str(item.get("art_id", ""))
        if not art_id:
            continue
        title = str(item.get("title", "")) or art_id
        thumbnail = str(item.get("thumbnail", ""))
        selected = " selected" if art_id == selected_art_id else ""
        thumbnail_html = (
            f'<img src="./tv-art-thumbnail/{escape(thumbnail)}" alt="{escape(title)}">'
            if thumbnail
            else '<div class="thumb-placeholder">No thumbnail</div>'
        )
        cards.append(
            f"""
            <article class="art-card{selected}">
              {thumbnail_html}
              <div class="art-title">{escape(title)}</div>
              <div class="art-id">{escape(art_id)}</div>
              <form method="post" action="./push-tv-art">
                <input type="hidden" name="art_id" value="{escape(art_id)}">
                <button>Show</button>
              </form>
              <form method="post" action="./set-fallback-tv-art">
                <input type="hidden" name="art_id" value="{escape(art_id)}">
                <button>Set Artwork</button>
              </form>
              <form method="post" action="./delete-tv-art">
                <input type="hidden" name="art_id" value="{escape(art_id)}">
                <button class="danger">Delete</button>
              </form>
            </article>
            """
        )
    return "\n".join(cards) or '<p>No TV art loaded yet.</p>'


def render_current_tv_art(current: Any, tv_art_items: Any) -> str:
    if not isinstance(current, dict) or not current:
        return '<div class="detail-panel"><p>No current TV image has been loaded yet.</p></div>'
    art_id = str(current.get("art_id", "")) or "(unknown)"
    title = str(current.get("title", "")) or "(not reported)"
    checked_at = str(current.get("checked_at", "")) or "(not checked)"
    push_mode = str(current.get("push_mode", "")) or "(unknown)"
    thumbnail = current_tv_thumbnail(art_id, tv_art_items)
    thumbnail_html = (
        f'<img class="current-thumb" src="./tv-art-thumbnail/{escape(thumbnail)}" alt="{escape(title)}">'
        if thumbnail
        else '<div class="current-thumb thumb-placeholder">No thumbnail loaded</div>'
    )
    return f"""
    <div class="detail-panel">
      {thumbnail_html}
      <dl>
        <dt>Title</dt><dd>{escape(title)}</dd>
        <dt>Art ID</dt><dd>{escape(art_id)}</dd>
        <dt>Push mode</dt><dd>{escape(push_mode)}</dd>
        <dt>Last refreshed</dt><dd>{escape(checked_at)}</dd>
      </dl>
    </div>
    """


def current_tv_thumbnail(art_id: str, tv_art_items: Any) -> str:
    if not isinstance(tv_art_items, list):
        return ""
    for item in tv_art_items:
        if not isinstance(item, dict):
            continue
        if str(item.get("art_id", "")) == art_id:
            return str(item.get("thumbnail", ""))
    return ""


def remove_tv_art_item(items: Any, art_id: str) -> list[dict[str, str]]:
    if not isinstance(items, list):
        return []
    remaining: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("art_id", "")) == art_id:
            continue
        remaining.append({str(key): str(value) for key, value in item.items()})
    return remaining


async def cache_tv_art_thumbnails(items: Any) -> list[dict[str, str]]:
    art_items = [item.__dict__ for item in items]
    missing_ids = [item["art_id"] for item in art_items if not existing_thumbnail_name(item["art_id"])]
    thumbnails = await frame_client.fetch_art_thumbnails(missing_ids)
    for art_id, data in thumbnails.items():
        write_thumbnail(art_id, data)

    for item in art_items:
        item["thumbnail"] = existing_thumbnail_name(item["art_id"])
    return art_items


def write_thumbnail(art_id: str, data: bytes) -> Path:
    suffix = thumbnail_suffix(data)
    path = thumbnail_cache_path / f"{safe_thumbnail_stem(art_id)}{suffix}"
    path.write_bytes(data)
    return path


def existing_thumbnail_name(art_id: str) -> str:
    stem = safe_thumbnail_stem(art_id)
    for suffix in (".jpg", ".png", ".webp", ".bin"):
        path = thumbnail_cache_path / f"{stem}{suffix}"
        if path.exists():
            return path.name
    return ""


def delete_existing_thumbnail(art_id: str) -> None:
    thumbnail = existing_thumbnail_name(art_id)
    if thumbnail:
        (thumbnail_cache_path / thumbnail).unlink(missing_ok=True)


def safe_thumbnail_stem(art_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", art_id).strip(".-") or "art"


def thumbnail_suffix(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ".webp"
    return ".bin"


def media_type_for_thumbnail(path: Path) -> str:
    if path.suffix == ".jpg":
        return "image/jpeg"
    if path.suffix == ".png":
        return "image/png"
    if path.suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def schedule_page() -> HTMLResponse:
    state = state_store.read()
    image_exists = renderer.output_path.exists()
    image_version = int(renderer.output_path.stat().st_mtime) if image_exists else 0
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        {page_styles()}
      </head>
      <body>
        {nav("schedule")}
        {render_status(state)}
        <h1>Schedule</h1>
        <div class="subnav">
          <form method="post" action="./generate"><button>Generate</button></form>
          <form method="post" action="./push-calendar"><button>Push Calendar Image</button></form>
          <form method="post" action="./push-fallback"><button>Push Artwork</button></form>
        </div>
        <p>Schedule image: {"ready" if image_exists else "not generated yet"}</p>
        {f'<img src="./image?v={image_version}" alt="Generated schedule">' if image_exists else ''}
      </body>
    </html>
    """
    return HTMLResponse(body)


def page_styles() -> str:
    return """
        <style>
          body { font-family: system-ui, sans-serif; margin: 2rem; color: #1f2a2a; background: #f7f4ec; }
          nav { display: flex; gap: 0.5rem; margin-bottom: 1.25rem; flex-wrap: wrap; }
          nav a { color: #1f2a2a; text-decoration: none; padding: 0.55rem 0.8rem; border: 1px solid #cfc8ba; background: rgba(255,255,255,0.55); }
          nav a.active { background: #1f2a2a; color: #fffdf6; border-color: #1f2a2a; }
          img { max-width: 100%; border: 1px solid #cfc8ba; }
          .subnav, .action-panel { display: flex; flex-wrap: wrap; align-items: center; gap: 0.65rem; padding: 0.75rem; margin: 1rem 0 1.25rem; background: rgba(255,255,255,0.55); border: 1px solid #cfc8ba; }
          .action-panel { align-items: stretch; flex-direction: column; max-width: 58rem; }
          .art-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 1rem; margin-top: 1.5rem; }
          .art-card { background: rgba(255,255,255,0.65); border: 1px solid #cfc8ba; padding: 0.75rem; }
          .art-card.selected { border-color: #1f2a2a; box-shadow: inset 0 0 0 2px #1f2a2a; }
          .art-card img, .thumb-placeholder { width: 100%; aspect-ratio: 16 / 9; object-fit: cover; background: #e8e0d2; border: 1px solid #cfc8ba; display: grid; place-items: center; color: #53605f; }
          .art-title { font-weight: 700; margin-top: 0.65rem; overflow-wrap: anywhere; }
          .art-id { color: #53605f; font-size: 0.85rem; overflow-wrap: anywhere; margin-top: 0.25rem; }
          .detail-panel { background: rgba(255,255,255,0.65); border: 1px solid #cfc8ba; padding: 1rem; max-width: 58rem; }
          .current-thumb { width: min(100%, 32rem); aspect-ratio: 16 / 9; object-fit: cover; margin-bottom: 1rem; }
          dl { display: grid; grid-template-columns: minmax(8rem, 12rem) 1fr; gap: 0.65rem 1rem; margin: 0; }
          dt { color: #53605f; font-weight: 700; }
          dd { margin: 0; overflow-wrap: anywhere; }
          button { padding: 0.65rem 1rem; border: 1px solid #1f2a2a; background: #fffdf6; color: #1f2a2a; cursor: pointer; }
          button:hover { background: #1f2a2a; color: #fffdf6; }
          button.danger { border-color: #8f3d30; color: #8f3d30; }
          button.danger:hover { background: #8f3d30; color: #fffdf6; }
          input, select { padding: 0.55rem; margin-right: 0.5rem; min-width: 18rem; max-width: 100%; }
          form { margin: 0; }
          .status { background: #ffffff; border: 1px solid #cfc8ba; padding: 1rem; margin: 1rem 0; }
          .status.success { border-left: 0.35rem solid #46725d; }
          .status.error { border-left: 0.35rem solid #a54434; }
          .status-time { color: #53605f; font-size: 0.85rem; margin-top: 0.35rem; }
          pre { background: rgba(255,255,255,0.65); padding: 1rem; overflow: auto; }
        </style>
    """


def nav(active: str) -> str:
    links = [
        ("current-tv", "./current-tv", "Current TV"),
        ("schedule", "./", "Schedule"),
        ("art", "./art", "Add-on Art"),
        ("tv-art", "./tv-art", "TV Art"),
        ("diagnostics", "./diagnostics", "Diagnostics"),
    ]
    return "<nav>" + "".join(
        f'<a class="{"active" if key == active else ""}" href="{href}">{label}</a>' for key, href, label in links
    ) + "</nav>"


def render_status(state: dict[str, Any]) -> str:
    message = str(state.get("last_action", "Ready"))
    status_class = str(state.get("last_action_status", "")) or ("error" if message.startswith("Action failed:") else "success")
    if status_class not in {"success", "error"}:
        status_class = "success"
    timestamp = str(state.get("last_action_time", ""))
    time_html = f'<div class="status-time">{escape(timestamp)}</div>' if timestamp else ""
    return f'<div class="status {status_class}">{escape(message)}{time_html}</div>'


def json_dump(value: Any) -> str:
    import json

    return json.dumps(value, indent=2, sort_keys=True)


def parse_hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def parse_minute(value: str) -> int:
    return int(value.split(":", 1)[1])
