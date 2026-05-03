# Changelog

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
