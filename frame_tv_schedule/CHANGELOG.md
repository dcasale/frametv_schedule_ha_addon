# Changelog

## 0.2.13

- Normalize calendar event timestamps into the configured add-on timezone before sorting, fixing mixed timezone-aware and timezone-naive Home Assistant calendar responses.

## 0.2.12

- Regenerate the schedule image before pushing to the TV when the cached image was generated before today.
- Force the manual calendar push to regenerate the schedule image so it never reuses stale output.

## 0.2.11

- Restore UI-selected fallback TV art or uploaded add-on art when a schedule display window ends.
- Add schedule window boundary tests to confirm the end time is exclusive.

## 0.2.10

- Show weather forecast times in the configured local timezone and start the strip at the current hour.
- Let the weather strip fill the available horizontal space instead of always stopping at eight forecast slots.
- Accept additional precipitation probability field names from Home Assistant weather providers.

## 0.2.9

- Fetch hourly weather forecasts through Home Assistant's WebSocket API to avoid REST service-response failures.
- Add automatic weather forecast type fallback and weather diagnostics for entities such as `weather.forecast_home`.

## 0.2.8

- Keep schedule image generation working when Home Assistant returns an error for hourly weather forecasts.

## 0.2.7

- Add optional hourly weather forecast strip to the bottom of the generated schedule image.
- Give event rows more vertical space and wrap event locations instead of cutting them off quickly.
- Move TV art thumbnail fixing back to the backlog after real-TV thumbnails failed to render.

## 0.2.6

- Add cached Samsung Frame TV art thumbnails to the TV Art page.
- Update Pillow to 12.2.0 to resolve open Dependabot alerts.

## 0.2.5

- Add optional Home Assistant API URL and long-lived access token settings as a fallback when `SUPERVISOR_TOKEN` is not injected.

## 0.2.4

- Request Supervisor API access in addition to Home Assistant API access so `SUPERVISOR_TOKEN` is reliably injected on more add-on installs.
- Log whether Home Assistant API token environment variables are available at startup and in calendar diagnostics.
- Document reinstall/reload troubleshooting when Home Assistant has not applied add-on API permissions.

## 0.2.3

- Add top navigation with separate Schedule, Add-on Art, TV Art, and Diagnostics pages.
- Add a TV Art page that can refresh art from the Samsung Frame TV, select existing TV art, and use TV art as fallback.
- Add calendar diagnostics to show configured calendars, raw response shape, sample events, and event counts.

## 0.2.2

- Fetch the full day's calendar events from Home Assistant's calendar REST endpoint so past events from today remain visible.
- Increase dynamic spacing between the title and date line in the generated schedule image.

## 0.2.1

- Install DejaVu fonts in the add-on image so the schedule renderer uses large TrueType text instead of Pillow's tiny fallback font.
- Accept friendly calendar names such as `Family` by normalizing them to Home Assistant calendar entity ids such as `calendar.family`.
- Add calendar fetch logging for configured entities, date bounds, returned calendars, and event counts.

## 0.2.0

- Add an add-on art library for uploading and normalizing user artwork.
- Add dropdown controls to push selected art and set selected art as fallback.
- Make restore-prior fail clearly when no prior art ID was captured.
- Add cache busting to the generated schedule image preview.

## 0.1.9

- Redesign the rendered calendar image for Frame TV Art Mode readability.
- Limit the visible timeline to larger high-contrast rows with overflow text.
- Remove the temporary Samsung Art support override option.

## 0.1.8

- Add `ignore_art_support_check` advanced option for TVs that report `FrameTVSupport=false` but may still answer Art API commands.

## 0.1.7

- Add explicit web UI buttons to push the calendar image, restore the prior image, and push fallback art.
- Show web UI action failures in the status panel.

## 0.1.6

- Add detailed add-on logs for schedule generation, window checks, and Samsung Frame actions.
- Add a **Push to TV Now** web UI action for pairing and direct TV testing.
- Prevent previous `dry_run` state from blocking the first `local_frame_api` push.

## 0.1.5

- Add Home Assistant add-on icon and logo assets.

## 0.1.4

- Fix FastAPI startup crash caused by browser action response annotations.

## 0.1.3

- Clarify the first-start flow: start add-on, open the web UI, generate the image, then run window checks.
- Document `privacy_mode` behavior.

## 0.1.2

- Keep browser actions on the web UI after generating an image or running a window check.
- Show the last action status above the generated image preview.

## 0.1.1

- Replace YAML-style first-run options with simple Home Assistant add-on config fields.
- Add direct fields for the primary calendar, optional extra calendars, and morning/afternoon display windows.
- Keep support for the previous internal calendar/window list format.

## 0.1.0

- Initial add-on scaffold.
- Calendar fetching from Home Assistant API.
- PNG schedule rendering.
- Configurable display windows and restore-mode state tracking.
- Dry-run Frame TV client.
