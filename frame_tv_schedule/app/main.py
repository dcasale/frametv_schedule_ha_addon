from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from html import escape
import logging
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import File, Form, Request, UploadFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

from .art_library import ArtLibrary
from .art_window_manager import ArtWindowManager
from .calendar_client import HomeAssistantCalendarClient
from .config import config_json, load_config
from .frame_client import ArtState, FrameClient
from .renderer import ScheduleRenderer
from .state_store import StateStore

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("frame_tv_schedule")

config = load_config()
window_manager = ArtWindowManager(config)
calendar_client = HomeAssistantCalendarClient()
frame_client = FrameClient(config)
renderer = ScheduleRenderer(config)
state_store = StateStore()
art_library = ArtLibrary(width=config.image_width, height=config.image_height)
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
    scheduler.add_job(generate_schedule, "cron", hour=parse_hour(config.generate_time), minute=parse_minute(config.generate_time))
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
    state = state_store.read()
    image_exists = renderer.output_path.exists()
    image_version = int(renderer.output_path.stat().st_mtime) if image_exists else 0
    status = escape(str(state.get("last_action", "Ready")))
    art_options = render_art_options(art_library.list_images(), str(state.get("fallback_art_file", "")))
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        <style>
          body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2a2a; background: #f7f4ec; }}
          img {{ max-width: 100%; border: 1px solid #cfc8ba; }}
          button {{ padding: 0.65rem 1rem; margin-right: 0.5rem; }}
          input, select {{ padding: 0.55rem; margin-right: 0.5rem; min-width: 18rem; }}
          form {{ margin: 0.65rem 0; }}
          .status {{ background: #ffffff; border: 1px solid #cfc8ba; padding: 1rem; margin: 1rem 0; }}
          pre {{ background: rgba(255,255,255,0.65); padding: 1rem; overflow: auto; }}
        </style>
      </head>
      <body>
        <h1>Frame TV Schedule</h1>
        <form method="post" action="./generate"><button>Generate</button></form>
        <form method="post" action="./push-calendar"><button>Push Calendar Image</button></form>
        <form method="post" action="./restore-prior"><button>Restore Prior Image</button></form>
        <form method="post" action="./push-fallback"><button>Push Fallback Image</button></form>
        <form method="post" action="./tick"><button>Run Window Check</button></form>
        <div class="status">{status}</div>
        <h2>Art Library</h2>
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
          <button>Use Selected Art as Fallback</button>
        </form>
        <p>Schedule image: {"ready" if image_exists else "not generated yet"}</p>
        {f'<img src="./image?v={image_version}" alt="Generated schedule">' if image_exists else ''}
        <h2>State</h2>
        <pre>{state}</pre>
        <h2>Config</h2>
        <pre>{config_json(config)}</pre>
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


@app.post("/generate", response_model=None)
async def generate_route(request: Request) -> Response:
    path = await generate_schedule()
    result = {"image": str(path)}
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/tick", response_model=None)
async def tick_route(request: Request) -> Response:
    result = await tick()
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/push-calendar", response_model=None)
async def push_calendar_route(request: Request) -> Response:
    result = await run_ui_action(push_calendar_image)
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/restore-prior", response_model=None)
async def restore_prior_route(request: Request) -> Response:
    result = await run_ui_action(restore_prior_image)
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
    return RedirectResponse("./", status_code=303)


@app.post("/push-art", response_model=None)
async def push_art_route(request: Request, art_name: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: push_library_art(art_name))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


@app.post("/set-fallback-art", response_model=None)
async def set_fallback_art_route(request: Request, art_name: str = Form(...)) -> Response:
    result = await run_ui_action(lambda: set_fallback_art(art_name))
    if wants_json(request):
        return JSONResponse(result)
    return RedirectResponse("./", status_code=303)


async def generate_schedule() -> Path:
    start, end = window_manager.today_bounds()
    logger.info("generating schedule for %s calendar(s)", len(config.calendar_entities))
    events = await calendar_client.get_events(config.calendar_entities, start, end)
    path = renderer.render(events)
    logger.info("generated schedule image at %s with %s event(s)", path, len(events))
    state_store.update(
        {
            "last_action": f"Generated schedule image with {len(events)} event(s).",
            "last_generated": datetime.now(ZoneInfo(config.timezone)).isoformat(),
            "event_count": len(events),
        }
    )
    return path


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
        previous = await push_schedule_to_frame("Window check")
        return {"action": "show_schedule"}

    if not should_show and active:
        previous_art = state.get("previous_art") or {}
        previous = ArtState(**previous_art) if previous_art else None
        await frame_client.restore_art(previous)
        state_store.update(
            {
                "last_action": "Window check restored the previous art.",
                "schedule_active": False,
                "schedule_push_mode": config.push_mode,
            }
        )
        logger.info("window check restored art")
        return {"action": "restore_art"}

    state_store.update({"last_action": "Window check completed. No display change was needed."})
    logger.info("window check completed with no display change")
    return {"action": "no_change"}


async def push_calendar_image() -> dict[str, str]:
    logger.info("push calendar requested push_mode=%s tv_host=%s", config.push_mode, config.tv_host or "(not set)")
    await push_schedule_to_frame("Manual calendar push")
    return {"action": "show_schedule"}


async def restore_prior_image() -> dict[str, str]:
    state = state_store.read()
    previous_art = state.get("previous_art") or {}
    previous = ArtState(**previous_art) if previous_art else None
    logger.info("restore prior requested previous_art=%s", previous.art_id if previous else "(not stored)")
    if not previous or not previous.art_id:
        raise RuntimeError("No prior art ID was stored before the calendar image was pushed")
    await frame_client.restore_art(previous)
    state_store.update(
        {
            "last_action": "Restored prior image on the Frame TV.",
            "schedule_active": False,
            "schedule_push_mode": config.push_mode,
        }
    )
    return {"action": "restore_prior"}


async def push_fallback_image() -> dict[str, str]:
    state = state_store.read()
    fallback_art_file = str(state.get("fallback_art_file", ""))
    if fallback_art_file:
        path = art_library.get(fallback_art_file)
        logger.info("push fallback requested from art library path=%s", path)
        await frame_client.show_image(path, label=f"fallback_{path.stem}")
        state_store.update(
            {
                "last_action": f"Pushed fallback art {path.name} to the Frame TV.",
                "schedule_active": False,
                "schedule_push_mode": config.push_mode,
            }
        )
        return {"action": "push_fallback", "image": path.name}

    logger.info(
        "push fallback requested fallback_art_id=%s fallback_image=%s",
        config.fallback_art_id or "(not set)",
        config.fallback_image or "(not set)",
    )
    await frame_client.show_fallback()
    state_store.update(
        {
            "last_action": "Pushed fallback image to the Frame TV.",
            "schedule_active": False,
            "schedule_push_mode": config.push_mode,
        }
    )
    return {"action": "push_fallback"}


async def upload_art(art_file: UploadFile) -> dict[str, str]:
    path = await art_library.save_upload(art_file)
    state_store.update({"last_action": f"Uploaded art image {path.name}."})
    logger.info("uploaded art library image path=%s", path)
    return {"action": "upload_art", "image": path.name}


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
    return {"action": "push_art", "image": path.name}


async def set_fallback_art(art_name: str) -> dict[str, str]:
    path = art_library.get(art_name)
    state_store.update({"last_action": f"Set fallback art to {path.name}.", "fallback_art_file": path.name})
    logger.info("fallback art set to path=%s", path)
    return {"action": "set_fallback_art", "image": path.name}


async def push_schedule_to_frame(action_label: str) -> ArtState:
    if not renderer.output_path.exists():
        await generate_schedule()
    previous = await frame_client.get_current_art()
    await frame_client.show_schedule(renderer.output_path)
    state_store.update(
        {
            "last_action": f"{action_label} showed the schedule on the Frame TV.",
            "schedule_active": True,
            "schedule_push_mode": config.push_mode,
            "previous_art": previous.__dict__,
        }
    )
    logger.info("%s showed schedule using push_mode=%s", action_label.lower(), config.push_mode)
    return previous


async def run_ui_action(action: Any) -> dict[str, str]:
    try:
        return await action()
    except Exception as error:
        logger.exception("web UI action failed")
        message = f"{type(error).__name__}: {error}"
        state_store.update({"last_action": f"Action failed: {message}"})
        return {"action": "error", "error": message}


def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


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


def parse_hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def parse_minute(value: str) -> int:
    return int(value.split(":", 1)[1])
