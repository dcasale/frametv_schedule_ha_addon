from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from .calendar_client import CalendarEvent, WeatherForecast
from .config import AddonConfig


class ScheduleRenderer:
    def __init__(self, config: AddonConfig, output_path: str | Path = "/config/schedule-today.png") -> None:
        self.config = config
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.timezone = ZoneInfo(config.timezone)

    def render(self, events: list[CalendarEvent], now: datetime | None = None, weather: list[WeatherForecast] | None = None) -> Path:
        now = now or datetime.now(self.timezone)
        weather = weather or []
        image = Image.new("RGB", (self.config.image_width, self.config.image_height), "#fbf7ec")
        draw = ImageDraw.Draw(image)

        width, height = image.size
        margin = int(width * 0.06)
        top = int(height * 0.075)
        title_font = load_font(168, bold=True)
        date_font = load_font(76, bold=True)
        section_font = load_font(54, bold=True)
        time_font = load_font(66, bold=True)
        event_font = load_font(78, bold=True)
        detail_font = load_font(50)
        small_font = load_font(42)
        weather_time_font = load_font(44, bold=True)
        weather_temp_font = load_font(62, bold=True)
        weather_detail_font = load_font(38)

        draw.rectangle((0, 0, width, height), fill="#fbf7ec")
        draw.rounded_rectangle((margin - 48, top - 44, width - margin + 48, height - top + 42), radius=44, fill="#fffdf6")

        title = "Today's Schedule"
        date_label = now.strftime("%A, %B %-d")
        title_bottom = draw.textbbox((margin, top), title, font=title_font)[3]
        date_y = title_bottom + 44
        date_bottom = draw.textbbox((margin, date_y), date_label, font=date_font)[3]
        divider_y = date_bottom + 78

        draw.text((margin, top), title, fill="#172424", font=title_font)
        draw.text((margin, date_y), date_label, fill="#3f4d4c", font=date_font)
        draw.line((margin, divider_y, width - margin, divider_y), fill="#243232", width=8)

        all_day = [event for event in events if event.all_day]
        timed = [event for event in events if not event.all_day]

        cursor = divider_y + 88
        if all_day:
            draw.text((margin, cursor), "All Day", fill="#9a5b1e", font=section_font)
            cursor += 78
            text = "  |  ".join(summary(event, self.config.privacy_mode) for event in all_day[:3])
            draw_wrapped_text(draw, text, (margin, cursor), event_font, "#172424", width - margin * 2, max_lines=2, line_gap=14)
            if len(all_day) > 3:
                draw.text((margin, cursor + 200), f"+ {len(all_day) - 3} more all-day", fill="#3f4d4c", font=small_font)
            cursor += 290

        draw.text((margin, cursor), "Today", fill="#9a5b1e", font=section_font)
        cursor += 82

        weather_band_height = min(310, max(190, int(height * 0.145)))
        weather_top = height - weather_band_height - 92 if weather else height - 150
        content_bottom = weather_top - 36

        if not timed:
            draw.text((margin, cursor), "No timed events today", fill="#172424", font=event_font)
        else:
            max_events = 6
            row_gap = 22
            visible_events = min(len(timed), max_events)
            row_height = max(int(height * 0.105), int((content_bottom - cursor - row_gap * (visible_events - 1)) / max(visible_events, 1)))
            for event in timed[:max_events]:
                time_label = event_time_label(event)
                row_bottom = min(cursor + row_height, content_bottom)
                if row_bottom <= cursor:
                    break
                draw.rounded_rectangle((margin, cursor, width - margin, row_bottom), radius=24, fill="#f1eadc")
                row_mid = cursor + ((row_bottom - cursor) // 2)
                time_y = row_mid - (font_size(time_font) // 2)
                draw.text((margin + 42, time_y), time_label, fill="#263737", font=time_font)
                text_x = margin + 760
                draw_wrapped_text(
                    draw,
                    summary(event, self.config.privacy_mode),
                    (text_x, cursor + 28),
                    event_font,
                    "#172424",
                    width - margin - text_x - 52,
                    max_lines=1 if event.location and not self.config.privacy_mode else 2,
                    line_gap=8,
                )
                if event.location and not self.config.privacy_mode:
                    draw_wrapped_text(
                        draw,
                        event.location,
                        (text_x, cursor + 120),
                        detail_font,
                        "#51605f",
                        width - margin - text_x - 52,
                        max_lines=max(1, min(2, int((row_bottom - cursor - 132) / (font_size(detail_font) + 8)))),
                        line_gap=8,
                    )
                cursor += row_height + row_gap

            if len(timed) > max_events:
                draw.text((margin, content_bottom + 20), f"+ {len(timed) - max_events} more events today", fill="#3f4d4c", font=small_font)

        if weather:
            draw_weather_band(
                draw,
                weather[:8],
                (margin, weather_top, width - margin, height - 92),
                weather_time_font,
                weather_temp_font,
                weather_detail_font,
            )
        else:
            footer = "Home Assistant"
            draw.text((width - margin - text_width(draw, footer, small_font), height - 92), footer, fill="#6f7a78", font=small_font)
        self.output_path.write_bytes(b"")
        image.save(self.output_path, "PNG")
        return self.output_path


def summary(event: CalendarEvent, privacy_mode: bool) -> str:
    return "Busy" if privacy_mode else event.summary


def event_time_label(event: CalendarEvent) -> str:
    if not event.start:
        return ""
    if event.end:
        if event.start.strftime("%p") == event.end.strftime("%p"):
            return f"{event.start.strftime('%-I:%M')}-{event.end.strftime('%-I:%M %p')}"
        return f"{event.start.strftime('%-I:%M %p')}-{event.end.strftime('%-I:%M %p')}"
    return event.start.strftime("%-I:%M %p")


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: str,
    max_width: int,
    max_lines: int,
    line_gap: int = 0,
) -> None:
    x, y = xy
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)

    for index, line in enumerate(lines[:max_lines]):
        if index == max_lines - 1 and len(lines) == max_lines and text_width(draw, line, font) > max_width:
            line = fit_text(draw, line, font, max_width)
        draw.text((x, y + index * (font_size(font) + line_gap)), line, fill=fill, font=font)


def draw_weather_band(
    draw: ImageDraw.ImageDraw,
    forecasts: list[WeatherForecast],
    box: tuple[int, int, int, int],
    time_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    temp_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    detail_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> None:
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=28, fill="#233232")
    draw.text((left + 36, top + 26), "Hourly Weather", fill="#f7f1e3", font=time_font)
    if not forecasts:
        return

    grid_top = top + 84
    column_width = (right - left - 72) / len(forecasts)
    available_height = bottom - grid_top
    compact = available_height < 190
    for index, forecast in enumerate(forecasts):
        x = int(left + 36 + index * column_width)
        center_x = int(x + column_width / 2)
        if index:
            draw.line((x, grid_top + 8, x, bottom - 22), fill="#5b6967", width=2)
        time_label = forecast.datetime.strftime("%-I %p") if forecast.datetime else "--"
        draw.text((center_x - text_width(draw, time_label, time_font) // 2, grid_top), time_label, fill="#dfe8e2", font=time_font)
        icon_y = grid_top + (58 if compact else 76)
        icon_size = 28 if compact else 36
        draw_weather_icon(draw, (center_x, icon_y), icon_size, forecast.condition)
        temp_label = f"{round(forecast.temperature)}°" if forecast.temperature is not None else "--"
        temp_y = grid_top + (92 if compact else 118)
        draw.text((center_x - text_width(draw, temp_label, temp_font) // 2, temp_y), temp_label, fill="#fffdf6", font=temp_font)
        rain_value = forecast.precipitation_probability
        rain_label = f"{rain_value}% rain" if rain_value is not None else "rain --"
        rain_y = grid_top + (150 if compact else 184)
        draw.text((center_x - text_width(draw, rain_label, detail_font) // 2, rain_y), rain_label, fill="#b9d8e7", font=detail_font)


def draw_weather_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int, condition: str) -> None:
    x, y = center
    condition = condition.lower()
    if "rain" in condition or "pour" in condition or "snow" in condition:
        draw.ellipse((x - size, y - size // 3, x + size // 3, y + size // 2), fill="#dfe8e2")
        draw.ellipse((x - size // 3, y - size, x + size, y + size // 2), fill="#dfe8e2")
        for offset in (-24, 0, 24):
            draw.line((x + offset, y + size // 2 + 12, x + offset - 10, y + size // 2 + 36), fill="#8fc3dc", width=6)
        return
    if "cloud" in condition or "fog" in condition:
        draw.ellipse((x - size, y - size // 3, x + size // 3, y + size // 2), fill="#dfe8e2")
        draw.ellipse((x - size // 3, y - size, x + size, y + size // 2), fill="#dfe8e2")
        draw.rectangle((x - size, y, x + size, y + size // 2), fill="#dfe8e2")
        return
    draw.ellipse((x - size // 2, y - size // 2, x + size // 2, y + size // 2), fill="#e4a543")
    for offset_x, offset_y in ((0, -size), (0, size), (-size, 0), (size, 0), (-28, -28), (28, -28), (-28, 28), (28, 28)):
        draw.line((x, y, x + offset_x, y + offset_y), fill="#e4a543", width=5)


def fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> str:
    if text_width(draw, text, font) <= max_width:
        return text
    ellipsis = "..."
    trimmed = text
    while trimmed and text_width(draw, trimmed + ellipsis, font) > max_width:
        trimmed = trimmed[:-1].rstrip()
    return trimmed + ellipsis if trimmed else ellipsis


def text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0]


def font_size(font: ImageFont.FreeTypeFont | ImageFont.ImageFont) -> int:
    return int(getattr(font, "size", 48))


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/usr/share/fonts/ttf-dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/ttf-dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
