from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from .calendar_client import CalendarEvent
from .config import AddonConfig


class ScheduleRenderer:
    def __init__(self, config: AddonConfig, output_path: str | Path = "/config/schedule-today.png") -> None:
        self.config = config
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.timezone = ZoneInfo(config.timezone)

    def render(self, events: list[CalendarEvent], now: datetime | None = None) -> Path:
        now = now or datetime.now(self.timezone)
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

        draw.rectangle((0, 0, width, height), fill="#fbf7ec")
        draw.rounded_rectangle((margin - 48, top - 44, width - margin + 48, height - top + 42), radius=44, fill="#fffdf6")
        divider_y = top + 310
        draw.line((margin, divider_y, width - margin, divider_y), fill="#243232", width=8)

        draw.text((margin, top), "Today's Schedule", fill="#172424", font=title_font)
        draw.text((margin, top + 158), now.strftime("%A, %B %-d"), fill="#3f4d4c", font=date_font)

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

        if not timed:
            draw.text((margin, cursor), "No timed events today", fill="#172424", font=event_font)
        else:
            max_events = 6
            row_gap = 22
            row_height = max(184, int((height - cursor - 165 - row_gap * (max_events - 1)) / max_events))
            for event in timed[:max_events]:
                time_label = event_time_label(event)
                row_bottom = min(cursor + row_height, height - 160)
                draw.rounded_rectangle((margin, cursor, width - margin, row_bottom), radius=24, fill="#f1eadc")
                draw.text((margin + 42, cursor + 42), time_label, fill="#263737", font=time_font)
                text_x = margin + 760
                draw_wrapped_text(
                    draw,
                    summary(event, self.config.privacy_mode),
                    (text_x, cursor + 30),
                    event_font,
                    "#172424",
                    width - margin - text_x - 52,
                    max_lines=2,
                    line_gap=8,
                )
                if event.location and not self.config.privacy_mode:
                    draw.text((text_x, row_bottom - 64), fit_text(draw, event.location, detail_font, width - margin - text_x - 52), fill="#51605f", font=detail_font)
                cursor += row_height + row_gap

            if len(timed) > max_events:
                draw.text((margin, height - 120), f"+ {len(timed) - max_events} more events today", fill="#3f4d4c", font=small_font)

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
