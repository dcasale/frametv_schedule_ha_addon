# Backlog

## TV Art Thumbnails

- Status: first attempt shipped in add-on `0.2.6`, but thumbnails did not render on the user's TV.
- Follow-up: capture the raw `art.get_thumbnail` / D2D failure from logs and make thumbnail retrieval work for the user's Frame firmware.
- Future follow-up: expose any date metadata returned by the TV once we can inspect a real `art.available()` payload from the user's model.
