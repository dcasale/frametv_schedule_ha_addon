from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from html import escape
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Request
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response

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
    status = escape(str(state.get("last_action", "Ready")))
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        <style>
          body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2a2a; background: #f7f4ec; }}
          img {{ max-width: 100%; border: 1px solid #cfc8ba; }}
          button {{ padding: 0.65rem 1rem; margin-right: 0.5rem; }}
          .status {{ background: #ffffff; border: 1px solid #cfc8ba; padding: 1rem; margin: 1rem 0; }}
          pre {{ background: rgba(255,255,255,0.65); padding: 1rem; overflow: auto; }}
        </style>
      </head>
      <body>
        <h1>Frame TV Schedule</h1>
        <form method="post" action="./generate"><button>Generate</button></form>
        <form method="post" action="./tick"><button>Run Window Check</button></form>
        <form method="post" action="./show-now"><button>Push to TV Now</button></form>
        <div class="status">{status}</div>
        <p>Schedule image: {"ready" if image_exists else "not generated yet"}</p>
        {'<img src="./image" alt="Generated schedule">' if image_exists else ''}
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


@app.post("/show-now", response_model=None)
async def show_now_route(request: Request) -> Response:
    result = await show_now()
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


async def show_now() -> dict[str, str]:
    logger.info("manual push requested push_mode=%s tv_host=%s", config.push_mode, config.tv_host or "(not set)")
    await push_schedule_to_frame("Manual push")
    return {"action": "show_schedule"}


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


def wants_json(request: Request) -> bool:
    accept = request.headers.get("accept", "")
    return "application/json" in accept and "text/html" not in accept


def parse_hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def parse_minute(value: str) -> int:
    return int(value.split(":", 1)[1])
