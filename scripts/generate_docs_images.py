from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CalendarEvent:
    calendar: str
    summary: str
    start: datetime | None
    end: datetime | None
    all_day: bool
    location: str = ""


@dataclass(frozen=True)
class WeatherForecast:
    datetime: datetime | None
    condition: str
    temperature: float | int | None
    precipitation_probability: int | None
    precipitation: float | int | None = None


@dataclass
class AddonConfig:
    calendar_entity: str = "calendar.family"
    weather_entity: str = "weather.forecast_home"
    image_width: int = 3840
    image_height: int = 2160
    timezone: str = "America/Los_Angeles"
    privacy_mode: bool = False


def load_renderer_module() -> ModuleType:
    app_module = ModuleType("app")
    app_module.__path__ = [str(REPO_ROOT / "frame_tv_schedule" / "app")]  # type: ignore[attr-defined]
    calendar_module = ModuleType("app.calendar_client")
    calendar_module.CalendarEvent = CalendarEvent
    calendar_module.WeatherForecast = WeatherForecast
    config_module = ModuleType("app.config")
    config_module.AddonConfig = AddonConfig
    sys.modules["app"] = app_module
    sys.modules["app.calendar_client"] = calendar_module
    sys.modules["app.config"] = config_module

    spec = importlib.util.spec_from_file_location("app.renderer", REPO_ROOT / "frame_tv_schedule" / "app" / "renderer.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load renderer module")
    module = importlib.util.module_from_spec(spec)
    sys.modules["app.renderer"] = module
    spec.loader.exec_module(module)
    return module


renderer_module = load_renderer_module()
ScheduleRenderer = renderer_module.ScheduleRenderer
load_font = renderer_module.load_font
text_width = renderer_module.text_width


IMAGE_DIR = REPO_ROOT / "docs" / "images"


def main() -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    schedule_path = render_sample_schedule()
    render_schedule_page(schedule_path)
    render_gallery_page()


def render_sample_schedule() -> Path:
    zone = ZoneInfo("America/Los_Angeles")
    now = datetime(2026, 5, 7, 7, 15, tzinfo=zone)
    config = AddonConfig(
        calendar_entity="calendar.family",
        weather_entity="weather.forecast_home",
        image_width=3840,
        image_height=2160,
        timezone="America/Los_Angeles",
    )
    events = [
        CalendarEvent("calendar.family", "Library books due", None, None, True),
        CalendarEvent("calendar.family", "Trash pickup", None, None, True),
        CalendarEvent("calendar.family", "School drop-off", datetime(2026, 5, 7, 7, 45, tzinfo=zone), datetime(2026, 5, 7, 8, 15, tzinfo=zone), False, "Maple Elementary"),
        CalendarEvent("calendar.family", "Doctor appointment", datetime(2026, 5, 7, 9, 30, tzinfo=zone), datetime(2026, 5, 7, 10, 15, tzinfo=zone), False, "Northside Clinic"),
        CalendarEvent("calendar.family", "Lunch with family", datetime(2026, 5, 7, 12, 0, tzinfo=zone), datetime(2026, 5, 7, 13, 0, tzinfo=zone), False, "Park Cafe"),
        CalendarEvent("calendar.family", "Piano lesson", datetime(2026, 5, 7, 15, 30, tzinfo=zone), datetime(2026, 5, 7, 16, 0, tzinfo=zone), False, "Music Studio"),
        CalendarEvent("calendar.family", "Soccer practice", datetime(2026, 5, 7, 17, 15, tzinfo=zone), datetime(2026, 5, 7, 18, 30, tzinfo=zone), False, "Field 3"),
    ]
    weather = [
        WeatherForecast(datetime(2026, 5, 7, hour, tzinfo=zone), condition=condition, temperature=temp, precipitation_probability=rain)
        for hour, condition, temp, rain in [
            (7, "partlycloudy", 58, 10),
            (8, "sunny", 61, 5),
            (9, "sunny", 65, 5),
            (10, "cloudy", 67, 15),
            (11, "cloudy", 68, 20),
            (12, "rainy", 66, 45),
            (13, "rainy", 64, 55),
            (14, "cloudy", 63, 30),
        ]
    ]
    path = IMAGE_DIR / "sample-schedule.png"
    ScheduleRenderer(config, output_path=path).render(events, now=now, weather=weather)
    return path


def render_schedule_page(schedule_path: Path) -> None:
    image = Image.new("RGB", (1800, 1200), "#f7f4ec")
    draw = ImageDraw.Draw(image)
    title = load_font(46, bold=True)
    body = load_font(24)
    nav = load_font(22, bold=True)
    small = load_font(18)
    draw.text((72, 56), "Frame TV Schedule", fill="#172424", font=title)
    tabs = ["Current TV", "Schedule", "Add-on Art", "TV Art", "Diagnostics"]
    x = 72
    for tab in tabs:
        width = text_width(draw, tab, nav) + 42
        fill = "#233232" if tab == "Schedule" else "#ede5d7"
        text_fill = "#fffdf6" if tab == "Schedule" else "#263737"
        draw.rounded_rectangle((x, 138, x + width, 190), radius=12, fill=fill)
        draw.text((x + 21, 151), tab, fill=text_fill, font=nav)
        x += width + 14

    draw.rounded_rectangle((72, 232, 1728, 318), radius=16, fill="#e1f0e6")
    draw.text((102, 254), "Generate completed successfully - sample schedule image refreshed.", fill="#173825", font=body)

    buttons = ["Generate", "Push Calendar", "Push Artwork"]
    x = 72
    for button in buttons:
        width = text_width(draw, button, nav) + 54
        draw.rounded_rectangle((x, 358, x + width, 420), radius=12, fill="#9a5b1e")
        draw.text((x + 27, 376), button, fill="#fffdf6", font=nav)
        x += width + 16

    preview = Image.open(schedule_path)
    preview.thumbnail((1260, 708))
    draw.rounded_rectangle((72, 462, 1390, 1116), radius=18, fill="#fffdf6")
    image.paste(preview, (101, 489))
    draw.text((1450, 492), "Schedule preview", fill="#172424", font=nav)
    draw.text((1450, 540), "Sample calendar and weather data only.", fill="#51605f", font=small)
    draw.text((1450, 590), "Manual controls show", fill="#51605f", font=small)
    draw.text((1450, 620), "success or failure status.", fill="#51605f", font=small)
    image.save(IMAGE_DIR / "addon-schedule-page.png", "PNG")


def render_gallery_page() -> None:
    image = Image.new("RGB", (1800, 1200), "#f7f4ec")
    draw = ImageDraw.Draw(image)
    title = load_font(46, bold=True)
    nav = load_font(22, bold=True)
    body = load_font(24)
    small = load_font(18)
    draw.text((72, 56), "Frame TV Schedule", fill="#172424", font=title)
    tabs = ["Current TV", "Schedule", "Add-on Art", "TV Art", "Diagnostics"]
    x = 72
    for tab in tabs:
        width = text_width(draw, tab, nav) + 42
        fill = "#233232" if tab == "TV Art" else "#ede5d7"
        text_fill = "#fffdf6" if tab == "TV Art" else "#263737"
        draw.rounded_rectangle((x, 138, x + width, 190), radius=12, fill=fill)
        draw.text((x + 21, 151), tab, fill=text_fill, font=nav)
        x += width + 14

    draw.text((72, 238), "TV Art", fill="#172424", font=title)
    draw.text((72, 296), "Sample gallery using generated placeholder artwork.", fill="#51605f", font=body)

    cards = [
        ("Canvas Mountains", ("#5d7569", "#d8c3a5")),
        ("Soft Coast", ("#4e7180", "#e6d8bd")),
        ("Evening Garden", ("#384c43", "#c89055")),
        ("Quiet Abstract", ("#233232", "#d6c0a7")),
        ("Morning Field", ("#778b5d", "#ead9b5")),
        ("Blue Study", ("#456173", "#dfe8e2")),
    ]
    card_w = 500
    card_h = 350
    gap = 42
    start_x = 72
    start_y = 374
    for index, (name, colors) in enumerate(cards):
        col = index % 3
        row = index // 3
        left = start_x + col * (card_w + gap)
        top = start_y + row * (card_h + gap)
        draw.rounded_rectangle((left, top, left + card_w, top + card_h), radius=16, fill="#fffdf6")
        art_box = (left + 22, top + 22, left + card_w - 22, top + 236)
        draw.rounded_rectangle(art_box, radius=10, fill=colors[0])
        draw.rectangle((art_box[0], art_box[3] - 68, art_box[2], art_box[3]), fill=colors[1])
        draw.ellipse((art_box[0] + 64, art_box[1] + 42, art_box[0] + 142, art_box[1] + 120), fill="#e4a543")
        draw.text((left + 24, top + 262), name, fill="#172424", font=nav)
        draw.text((left + 24, top + 302), "Push  |  Use as Artwork  |  Delete", fill="#9a5b1e", font=small)
    image.save(IMAGE_DIR / "tv-art-gallery.png", "PNG")


if __name__ == "__main__":
    main()
