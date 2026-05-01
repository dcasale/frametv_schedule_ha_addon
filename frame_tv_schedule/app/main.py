from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .art_window_manager import ArtWindowManager
from .calendar_client import HomeAssistantCalendarClient
from .config import config_json, load_config
from .frame_client import ArtState, FrameClient
from .renderer import ScheduleRenderer
from .state_store import StateStore

config = load_config()
window_manager = ArtWindowManager(config)
calendar_client = HomeAssistantCalendarClient()
frame_client = FrameClient(config)
renderer = ScheduleRenderer(config)
state_store = StateStore()
scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.timezone))


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler.add_job(generate_schedule, "cron", hour=parse_hour(config.generate_time), minute=parse_minute(config.generate_time))
    scheduler.add_job(tick, "interval", minutes=max(config.refresh_minutes, 1), next_run_time=datetime.now(ZoneInfo(config.timezone)))
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="Frame TV Schedule", lifespan=lifespan)


@app.get("/")
async def index() -> HTMLResponse:
    state = state_store.read()
    image_exists = renderer.output_path.exists()
    body = f"""
    <!doctype html>
    <html>
      <head>
        <title>Frame TV Schedule</title>
        <style>
          body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2a2a; background: #f7f4ec; }}
          img {{ max-width: 100%; border: 1px solid #cfc8ba; }}
          button {{ padding: 0.65rem 1rem; margin-right: 0.5rem; }}
          pre {{ background: rgba(255,255,255,0.65); padding: 1rem; overflow: auto; }}
        </style>
      </head>
      <body>
        <h1>Frame TV Schedule</h1>
        <form method="post" action="/generate"><button>Generate</button></form>
        <form method="post" action="/tick"><button>Run Window Check</button></form>
        <p>Schedule image: {"ready" if image_exists else "not generated yet"}</p>
        {'<img src="/image" alt="Generated schedule">' if image_exists else ''}
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


@app.post("/generate")
async def generate_route() -> JSONResponse:
    path = await generate_schedule()
    return JSONResponse({"image": str(path)})


@app.post("/tick")
async def tick_route() -> JSONResponse:
    result = await tick()
    return JSONResponse(result)


async def generate_schedule() -> Path:
    start, end = window_manager.today_bounds()
    events = await calendar_client.get_events(config.calendar_entities, start, end)
    path = renderer.render(events)
    state_store.update({"last_generated": datetime.now(ZoneInfo(config.timezone)).isoformat(), "event_count": len(events)})
    return path


async def tick() -> dict[str, str]:
    should_show = window_manager.should_show_schedule()
    state = state_store.read()
    active = bool(state.get("schedule_active"))

    if should_show and not active:
        if not renderer.output_path.exists():
            await generate_schedule()
        previous = await frame_client.get_current_art()
        await frame_client.show_schedule(renderer.output_path)
        state_store.update({"schedule_active": True, "previous_art": previous.__dict__})
        return {"action": "show_schedule"}

    if not should_show and active:
        previous_art = state.get("previous_art") or {}
        previous = ArtState(**previous_art) if previous_art else None
        await frame_client.restore_art(previous)
        state_store.update({"schedule_active": False})
        return {"action": "restore_art"}

    return {"action": "no_change"}


def parse_hour(value: str) -> int:
    return int(value.split(":", 1)[0])


def parse_minute(value: str) -> int:
    return int(value.split(":", 1)[1])
