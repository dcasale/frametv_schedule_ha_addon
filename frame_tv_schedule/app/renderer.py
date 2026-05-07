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
        image = Image.new("RGB", (self.config.image_width, self.config.image_height), "#fffdf6")
        draw = ImageDraw.Draw(image)

        width, height = image.size
        scale = min(width / 3840, height / 2160)
        s = lambda value: scaled(value, scale)
        margin = int(width * 0.045)
        top = int(height * 0.055)
        title_font = load_font(s(128), bold=True)
        date_font = load_font(s(68), bold=True)
        section_font = load_font(s(46), bold=True)
        event_font = load_font(s(64), bold=True)
        small_font = load_font(s(38))
        weather_time_font = load_font(s(44), bold=True)
        weather_temp_font = load_font(s(62), bold=True)
        weather_detail_font = load_font(s(38))

        draw.rectangle((0, 0, width, height), fill="#fffdf6")

        title = "Today's Schedule"
        date_label = now.strftime("%A, %B %-d")
        title_bottom = draw.textbbox((margin, top), title, font=title_font)[3]
        date_y = title_bottom + s(44)
        date_bottom = draw.textbbox((margin, date_y), date_label, font=date_font)[3]
        divider_y = date_bottom + s(78)

        draw.text((margin, top), title, fill="#172424", font=title_font)
        draw.text((margin, date_y), date_label, fill="#3f4d4c", font=date_font)
        draw.line((margin, divider_y, width - margin, divider_y), fill="#243232", width=s(8))

        all_day = [event for event in events if event.all_day]
        timed = [event for event in events if not event.all_day]

        display_weather = visible_weather_forecasts(weather, now, self.timezone)
        weather_band_height = min(330, max(210, int(height * 0.155)))
        weather_bottom = height - int(height * 0.04)
        weather_top = weather_bottom - weather_band_height if display_weather else height - int(height * 0.07)
        content_top = divider_y + s(72)
        content_bottom = weather_top - s(42)
        column_gap = int(width * 0.032)
        all_day_width = int(width * 0.255) if all_day else 0
        timed_left = margin
        timed_right = width - margin - all_day_width - (column_gap if all_day else 0)
        all_day_left = timed_right + column_gap
        all_day_right = width - margin

        draw.text((timed_left, content_top), "Today", fill="#9a5b1e", font=section_font)
        timed_cursor = content_top + s(70)
        timed_bottom = content_bottom

        if not timed:
            draw.text((timed_left, timed_cursor), "No timed events today", fill="#172424", font=event_font)
        else:
            row_gap = s(14)
            available_event_height = max(0, timed_bottom - timed_cursor)
            visible_events = visible_event_count(len(timed), available_event_height, row_gap, scale)
            if visible_events <= 0:
                draw.text((timed_left, timed_cursor), "Not enough room to show timed events", fill="#172424", font=event_font)
                visible_events = 0
                row_height = 0
            else:
                row_height = int((available_event_height - row_gap * (visible_events - 1)) / max(visible_events, 1))
                row_height = max(minimum_row_height(visible_events, scale), row_height)
            if not visible_events:
                rendered_events = 0
            else:
                row_fonts = row_font_set(row_height, scale)
                rendered_events = 0
                for event in timed[:visible_events]:
                    time_label = event_time_label(event)
                    row_bottom = min(timed_cursor + row_height, timed_bottom)
                    if row_bottom <= timed_cursor + s(64):
                        break
                    rendered_events += 1
                    draw.rounded_rectangle((timed_left, timed_cursor, timed_right, row_bottom), radius=s(20), fill="#f1eadc")
                    row_mid = timed_cursor + ((row_bottom - timed_cursor) // 2)
                    time_y = row_mid - (font_size(row_fonts["time"]) // 2)
                    draw.text((timed_left + s(34), time_y), time_label, fill="#263737", font=row_fonts["time"])
                    text_x = timed_left + min(s(560), max(s(410), int((timed_right - timed_left) * 0.22)))
                    text_width_available = timed_right - text_x - s(42)
                    location_lines = 1 if event.location and not self.config.privacy_mode and row_height >= s(136) else 0
                    title_lines = 1 if location_lines else max(1, min(2, int((row_height - s(42)) / (font_size(row_fonts["event"]) + s(6)))))
                    draw_wrapped_text(
                        draw,
                        summary(event, self.config.privacy_mode),
                        (text_x, timed_cursor + s(22)),
                        row_fonts["event"],
                        "#172424",
                        text_width_available,
                        max_lines=title_lines,
                        line_gap=s(8),
                    )
                    if location_lines:
                        draw_wrapped_text(
                            draw,
                            event.location,
                            (text_x, timed_cursor + row_height - font_size(row_fonts["detail"]) - s(22)),
                            row_fonts["detail"],
                            "#51605f",
                            text_width_available,
                            max_lines=1,
                            line_gap=s(8),
                        )
                    timed_cursor += row_height + row_gap

            if len(timed) > rendered_events:
                more_label = f"+ {len(timed) - rendered_events} more events today"
                more_y = max(timed_cursor, timed_bottom - font_size(small_font) - s(8))
                if more_y + font_size(small_font) < weather_top - s(8):
                    draw.text((timed_left, more_y), more_label, fill="#3f4d4c", font=small_font)

        if all_day:
            draw.text((all_day_left, content_top), "All Day", fill="#9a5b1e", font=section_font)
            draw_all_day_box(
                draw,
                all_day,
                (all_day_left, content_top + s(70), all_day_right, content_bottom),
                load_font(s(48), bold=True),
                small_font,
                self.config.privacy_mode,
                scale,
            )

        if display_weather:
            draw_weather_band(
                draw,
                display_weather,
                (margin, weather_top, width - margin, weather_bottom),
                weather_time_font,
                weather_temp_font,
                weather_detail_font,
            )
        else:
            footer = "Home Assistant"
            draw.text((width - margin - text_width(draw, footer, small_font), height - int(height * 0.04)), footer, fill="#6f7a78", font=small_font)
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


def visible_event_count(event_count: int, available_height: int, row_gap: int, scale: float = 1.0) -> int:
    if event_count <= 0 or available_height <= 0:
        return 0
    max_events = min(event_count, 12)
    for count in range(max_events, 0, -1):
        row_height = int((available_height - row_gap * (count - 1)) / count)
        if row_height >= minimum_row_height(count, scale):
            return count
    return 1


def minimum_row_height(event_count: int, scale: float = 1.0) -> int:
    if event_count <= 5:
        return scaled(150, scale)
    if event_count <= 8:
        return scaled(112, scale)
    return scaled(82, scale)


def row_font_set(row_height: int, scale: float = 1.0) -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    if row_height >= scaled(180, scale):
        return {"time": load_font(scaled(58, scale), bold=True), "event": load_font(scaled(68, scale), bold=True), "detail": load_font(scaled(42, scale))}
    if row_height >= scaled(120, scale):
        return {"time": load_font(scaled(50, scale), bold=True), "event": load_font(scaled(58, scale), bold=True), "detail": load_font(scaled(36, scale))}
    return {"time": load_font(scaled(36, scale), bold=True), "event": load_font(scaled(40, scale), bold=True), "detail": load_font(scaled(26, scale))}


def draw_all_day_box(
    draw: ImageDraw.ImageDraw,
    events: list[CalendarEvent],
    box: tuple[int, int, int, int],
    event_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    small_font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    privacy_mode: bool,
    scale: float = 1.0,
) -> None:
    s = lambda value: scaled(value, scale)
    left, top, right, bottom = box
    draw.rounded_rectangle(box, radius=s(20), fill="#f1eadc")
    cursor = top + s(28)
    line_height = font_size(event_font) + s(20)
    available_lines = max(1, int((bottom - cursor - s(34)) / line_height))
    visible_events = events[:available_lines]
    for event in visible_events:
        marker_y = cursor + font_size(event_font) // 2
        draw.ellipse((left + s(32), marker_y - s(8), left + s(48), marker_y + s(8)), fill="#9a5b1e")
        draw_wrapped_text(
            draw,
            summary(event, privacy_mode),
            (left + s(66), cursor),
            event_font,
            "#172424",
            right - left - s(96),
            max_lines=1,
        )
        cursor += line_height
    if len(events) > len(visible_events):
        draw.text((left + s(30), bottom - font_size(small_font) - s(28)), f"+ {len(events) - len(visible_events)} more all-day", fill="#3f4d4c", font=small_font)


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
    text = strip_emoji(text)
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
    scale = max(0.25, font_size(time_font) / 44)
    s = lambda value: scaled(value, scale)
    draw.rounded_rectangle(box, radius=s(28), fill="#233232")
    draw.text((left + s(36), top + s(26)), "Hourly Weather", fill="#f7f1e3", font=time_font)
    if not forecasts:
        return

    grid_top = top + s(84)
    max_columns = max(1, int((right - left - s(72)) / s(360)))
    forecasts = forecasts[:max_columns]
    column_width = (right - left - s(72)) / len(forecasts)
    available_height = bottom - grid_top
    compact = available_height < s(190)
    for index, forecast in enumerate(forecasts):
        x = int(left + s(36) + index * column_width)
        center_x = int(x + column_width / 2)
        if index:
            draw.line((x, grid_top + s(8), x, bottom - s(22)), fill="#5b6967", width=max(1, s(2)))
        time_label = forecast.datetime.strftime("%-I %p") if forecast.datetime else "--"
        draw.text((center_x - text_width(draw, time_label, time_font) // 2, grid_top), time_label, fill="#dfe8e2", font=time_font)
        icon_y = grid_top + s(58 if compact else 76)
        icon_size = s(28 if compact else 36)
        draw_weather_icon(draw, (center_x, icon_y), icon_size, forecast.condition)
        temp_label = f"{round(forecast.temperature)}°" if forecast.temperature is not None else "--"
        temp_y = grid_top + s(92 if compact else 118)
        draw.text((center_x - text_width(draw, temp_label, temp_font) // 2, temp_y), temp_label, fill="#fffdf6", font=temp_font)
        rain_label = weather_rain_label(forecast)
        rain_y = grid_top + s(150 if compact else 184)
        draw.text((center_x - text_width(draw, rain_label, detail_font) // 2, rain_y), rain_label, fill="#b9d8e7", font=detail_font)


def visible_weather_forecasts(forecasts: list[WeatherForecast], now: datetime, timezone: ZoneInfo) -> list[WeatherForecast]:
    current_hour = now.astimezone(timezone).replace(minute=0, second=0, microsecond=0)
    visible: list[WeatherForecast] = []
    for forecast in forecasts:
        forecast_time = forecast.datetime
        if forecast_time:
            forecast_time = forecast_time.astimezone(timezone)
            if forecast_time < current_hour:
                continue
        visible.append(
            WeatherForecast(
                datetime=forecast_time,
                condition=forecast.condition,
                temperature=forecast.temperature,
                precipitation_probability=forecast.precipitation_probability,
                precipitation=forecast.precipitation,
            )
        )
    return visible


def weather_rain_label(forecast: WeatherForecast) -> str:
    if forecast.precipitation_probability is not None:
        return f"{forecast.precipitation_probability}% rain"
    if forecast.precipitation is not None:
        return f"{forecast.precipitation:g} rain"
    return "-- rain"


def scaled(value: int, scale: float) -> int:
    return max(1, int(round(value * scale)))


def strip_emoji(text: str) -> str:
    return "".join(character for character in text if not is_emoji_character(character)).replace("  ", " ").strip()


def is_emoji_character(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or 0xFE00 <= codepoint <= 0xFE0F
        or codepoint == 0x200D
    )


def draw_weather_icon(draw: ImageDraw.ImageDraw, center: tuple[int, int], size: int, condition: str) -> None:
    x, y = center
    condition = condition.lower()
    if "rain" in condition or "pour" in condition or "snow" in condition:
        draw.ellipse((x - size, y - size // 3, x + size // 3, y + size // 2), fill="#dfe8e2")
        draw.ellipse((x - size // 3, y - size, x + size, y + size // 2), fill="#dfe8e2")
        for offset in (-int(size * 0.67), 0, int(size * 0.67)):
            draw.line((x + offset, y + size // 2 + int(size * 0.33), x + offset - int(size * 0.28), y + size // 2 + size), fill="#8fc3dc", width=max(1, int(size * 0.16)))
        return
    if "cloud" in condition or "fog" in condition:
        draw.ellipse((x - size, y - size // 3, x + size // 3, y + size // 2), fill="#dfe8e2")
        draw.ellipse((x - size // 3, y - size, x + size, y + size // 2), fill="#dfe8e2")
        draw.rectangle((x - size, y, x + size, y + size // 2), fill="#dfe8e2")
        return
    draw.ellipse((x - size // 2, y - size // 2, x + size // 2, y + size // 2), fill="#e4a543")
    diagonal = int(size * 0.78)
    for offset_x, offset_y in ((0, -size), (0, size), (-size, 0), (size, 0), (-diagonal, -diagonal), (diagonal, -diagonal), (-diagonal, diagonal), (diagonal, diagonal)):
        draw.line((x, y, x + offset_x, y + offset_y), fill="#e4a543", width=max(1, int(size * 0.14)))


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
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "/usr/share/fonts/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/noto/NotoEmoji-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()
