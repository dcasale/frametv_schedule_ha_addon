# Frame TV Schedule

This add-on creates a daily schedule image from Home Assistant calendar entities and can display it on a Samsung Frame TV during configured time windows.

## Calendar setup

For Apple Calendar, add your iCloud calendars to Home Assistant with the CalDAV integration. Then add the resulting `calendar.*` entity ID to the add-on's `calendar_entity` field.

For a calendar named `Family`, Home Assistant will usually create an entity ID like:

```text
calendar.family
```

Use the entity ID, not only the friendly calendar name. The add-on configuration field is a text field, so type or paste the entity ID manually.

To find the exact entity ID in Home Assistant:

1. Go to **Settings** -> **Devices & services**.
2. Open the **Entities** tab.
3. Search for `Family`.
4. Open the matching calendar entity.
5. Copy the entity ID shown by Home Assistant, for example `calendar.family`.

You can also go to **Developer tools** -> **States** and search for `Family` or `calendar.`.

If you want more calendars on the same schedule image, use `additional_calendar_entity_1` and `additional_calendar_entity_2`.

Recommended first calendar configuration:

```text
calendar_entity: calendar.family
additional_calendar_entity_1:
additional_calendar_entity_2:
```

Leave the additional calendar fields blank unless you want to combine multiple calendars into one schedule image.

The CalDAV integration stores and manages your Apple Calendar credentials in Home Assistant. This add-on only asks Home Assistant for events from the calendar entity; it does not need your Apple username, Apple password, or app-specific password.

## First test configuration

Start in `dry_run` mode. This lets you confirm that the add-on can read the calendar and render the schedule image before it tries to control the TV.

```text
calendar_entity: calendar.family
timezone: America/Los_Angeles
generate_time: 05:00
refresh_minutes: 30
morning_window_start: 06:00
morning_window_end: 08:00
afternoon_window_start: 14:30
afternoon_window_end: 16:30
push_mode: dry_run
privacy_mode: false
```

## After starting the add-on

After saving the configuration and starting the add-on, use the add-on web UI to test the schedule image.

1. Start or restart the add-on.
2. Select **Open Web UI** from the add-on page.
3. Select **Generate**.
4. Confirm that the schedule image appears.
5. Check the add-on logs if no events appear.

If you see a response like this:

```text
{"image":"/config/schedule-today.png"}
```

That means the image was generated successfully, but you are viewing the raw API response instead of the add-on's main web page. Go back to the add-on page and select **Open Web UI** again. Add-on version `0.1.2` and later keep browser actions on the web UI and show the generated image preview.

Use **Generate** to test calendar/image generation without touching the TV.

Use **Push Calendar Image** after switching to `local_frame_api` when you want to force an immediate TV connection, upload, and pairing test without waiting for a display window.

Use **Restore Prior Image** to restore the art that was active before the last calendar push. This only works after the add-on has successfully read and stored a prior art ID.

Use **Push Fallback Image** to show the configured fallback art. Configure either `fallback_art_id` or `fallback_image` first.

Use **Run Window Check** to test whether the add-on should show or restore the schedule based on the configured display windows.

## Art library

Use the **Art Library** section in the web UI to upload images into the add-on. Uploaded images are stored under the add-on config directory and normalized to the configured Frame image size.

After uploading art, use the dropdown to:

- **Push Selected Art**: manually show that image on the TV.
- **Use Selected Art as Fallback**: make that image the fallback used by **Push Fallback Image**.

This is the recommended safety path if restore-prior is unreliable on your TV. Upload one or more normal artwork images, set one as fallback, and verify **Push Selected Art** and **Push Fallback Image** before relying on automatic restore behavior.

## Configuration fields

`calendar_entity` is the Home Assistant calendar entity ID, such as `calendar.family`.

`additional_calendar_entity_1` and `additional_calendar_entity_2` are optional extra calendars to include on the same schedule image.

`push_mode` controls whether the add-on only renders an image or also talks to the TV:

- `dry_run`: generate the image only
- `local_frame_api`: connect directly to the Samsung Frame TV on your local network
- `home_assistant_service`: reserved for a future Home Assistant service-based TV driver

`privacy_mode` controls what appears on the rendered TV image:

- `false`: show event titles and locations from the calendar
- `true`: replace event titles with `Busy` and hide locations

Use `privacy_mode: true` if the TV is in a public/shared space and you do not want appointment names or locations visible.

## Display windows

Use the simple window fields to control when the generated schedule should temporarily become the selected artwork.

```yaml
morning_window_start: "06:00"
morning_window_end: "08:00"
afternoon_window_start: "14:30"
afternoon_window_end: "16:30"
```

Outside these windows the add-on restores the previous art when the TV driver can read it. If that is not supported on your model, configure a fallback art ID or fallback image.

## Schedule image readability

The schedule image is designed for dim Frame TV Art Mode viewing. It shows a small number of large, high-contrast rows instead of trying to fit every event on the screen. If there are more timed events than fit comfortably, the image shows a `+ more events today` line.

This is intentional: the TV should be readable from across the room, not behave like a dense calendar dashboard.

## TV push modes

`dry_run` renders the image and logs what would happen. This is the safest starting point.

`local_frame_api` connects directly to the Samsung Frame on your local network and uses its Art Mode API.

The Samsung TV connection does not use a username or password. It uses local network pairing:

1. Set a static DHCP reservation for the TV in your router.
2. Put the TV IP address in `tv_host`.
3. Set `push_mode` to `local_frame_api`.
4. Start or restart the add-on.
5. Approve the connection prompt on the Samsung TV the first time the add-on connects.

The pairing token is saved in:

```text
/config/samsung-frame-token.txt
```

That file is stored in the add-on config directory so the approval should survive add-on restarts and Home Assistant backups.

Recommended TV settings before using `local_frame_api`:

- reserve a static DHCP address for the TV
- keep Home Assistant and the TV on the same subnet/VLAN
- on the TV, approve the connection prompt the first time the add-on connects
- set the TV's access notification behavior to first-time-only if repeated prompts appear

Required add-on options:

```text
push_mode: local_frame_api
tv_host: 192.168.1.50
tv_port: 8002
tv_token_file: /config/samsung-frame-token.txt
tv_matte: none
```

Use the TV's real static IP address for `tv_host`.

`home_assistant_service` is reserved for calling a Home Assistant service exposed by another Samsung Frame integration.

## First TV test

After `dry_run` works:

1. Assign the TV a static DHCP address.
2. Save that IP in `tv_host`.
3. Change `push_mode` from `dry_run` to `local_frame_api`.
4. Save and restart the add-on.
5. Open the add-on web UI and select **Push Calendar Image**.
6. Watch the TV for a pairing prompt and approve it.
7. If **Push Calendar Image** works, select **Restore Prior Image** to verify restore behavior.
8. Upload a normal art image in **Art Library**, select it, and choose **Use Selected Art as Fallback**.
9. Select **Push Fallback Image** to verify fallback behavior.
10. Temporarily set one display window to include the current time.
11. Select **Run Window Check**.

For example, if it is currently 3:05 PM, temporarily use:

```text
afternoon_window_start: 15:00
afternoon_window_end: 15:20
```

After the TV test works, set the window back to the normal schedule.

The add-on logs should show entries for `push_mode`, `tv_host`, whether a window check decided to show the schedule, and each Samsung Frame action attempted.

## Generated files

The rendered schedule image and runtime state are stored under `/config` inside the add-on container. Home Assistant maps this to the add-on's backed-up config directory.
