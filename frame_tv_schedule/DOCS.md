# Frame TV Schedule

<!-- agentdocs:audience external -->

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
refresh_minutes: 30
morning_window_start: 06:00
morning_window_end: 08:00
afternoon_window_start: 14:30
afternoon_window_end: 16:30
weekend_morning_window_start: 06:00
weekend_morning_window_end: 08:00
weekend_afternoon_window_start: 14:30
weekend_afternoon_window_end: 16:30
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

Use **Push Calendar Image** after switching to `local_frame_api` when you want to force an immediate TV connection, upload, and pairing test without waiting for a display window. This action regenerates the schedule image first.

Use **Pause Schedule on TV** at the top of the Schedule page to stop the schedule being pushed to the TV during display windows, for example while guests are over. Pausing takes effect immediately: if the schedule is on screen, Artwork is put back. **Resume Schedule on TV** turns it back on, and shows the schedule straight away if a display window is open. The setting is kept across restarts. While paused, the add-on also stops generating the schedule image automatically, because it only generates one when pushing it; **Generate** and **Push Calendar Image** still work by hand, and a manual push is replaced by Artwork at the next window check.

Use **Push Artwork** to show the configured Artwork. Select Artwork from either the **TV Art** page or the **Add-on Art** page first.

Use **Diagnostics** -> **Run Window Check** to test whether the add-on should show the schedule or Artwork based on the configured display windows.

After each web UI action, the status banner near the top of the page shows whether the action succeeded or failed and when it ran.

Use the **Diagnostics** page and select **Run Calendar Debug** if the generated image does not show expected events. The debug output lists the configured calendar entities, the Home Assistant calendar entities visible to the add-on, the raw response shape, and sample parsed events.

If diagnostics shows:

```text
Home Assistant supervisor token is unavailable
```

or the add-on logs show:

```text
Home Assistant API token available=False env_has_supervisor_token=False env_has_hassio_token=False
```

then the add-on is running without Home Assistant API permission. The add-on manifest includes `homeassistant_api: true`, but Home Assistant may not apply newly added API permissions to an already-installed add-on. Update to the latest add-on version first. If the token is still unavailable, uninstall the add-on, reload the add-on repository from the add-on store menu, install it again, restore the configuration values, and start it again.

If the Supervisor token is still unavailable after reinstalling, configure the manual Home Assistant API fallback:

1. In Home Assistant, open your user profile.
2. Create a **Long-lived access token**.
3. Paste it into the add-on's `home_assistant_token` field.
4. Leave `home_assistant_url` as `http://127.0.0.1:8123/api` if Home Assistant Core is reachable from the add-on through the host network.
5. If that URL does not work, use your Home Assistant URL with `/api` at the end, for example `http://homeassistant.local:8123/api` or `http://192.168.1.10:8123/api`.
6. Restart the add-on and run **Diagnostics** -> **Run Calendar Debug** again.

When a manual token is configured, the add-on uses that token instead of `SUPERVISOR_TOKEN`.

## Art library

Every button in the web UI explains itself when you hover over it, and each action's status message says what changed on the TV and for how long.

Use the **Art Library** section in the web UI to upload images into the add-on. You can select several pictures at once in the file picker. Uploaded images are stored under the add-on config directory and normalized to the configured Frame image size. JPEG and PNG work; HEIC files (the iPhone default when copied off a Mac) are rejected, so export them as JPEG first. Uploading from Safari on an iPhone converts them automatically. If some files in a batch fail, the rest are still saved and the status line names each failed file. There is no practical size limit on a batch; 20 phone photos upload in one go, and processing takes roughly a second per picture.

After uploading art, use the dropdown or gallery cards to:

- **Preview Selected Art on TV** (or **Preview on TV** on a card): show that image on the TV for now. The add-on uploads it to the TV the first time and reuses that copy afterwards. A preview is temporary and does not change Artwork: it stays until the next display window starts (or, during an open window, until the next window check), and Artwork comes back when that window ends. While the schedule is paused it stays until you change it.
- **Set Selected Art as Artwork** (or **Set Artwork** on a card): make that image the Artwork, the default the TV returns to after every schedule window. It does not change the TV right away; the gallery card marked **Artwork** is the current choice. This makes it the Artwork used by **Push Artwork** and by automatic window-end switching.
- **Delete** (asks first): remove that uploaded image from the add-on art library. A copy already on the TV stays there. If it was selected as Artwork, the Artwork selection is cleared.

This is the recommended safety path before relying on automatic window switching. Upload one or more normal artwork images, set one as Artwork, and verify **Preview Selected Art on TV** and **Push Artwork**.

## TV art

The **TV Art** page can refresh the list of artwork reported by the Samsung Frame TV. After refreshing, you can preview an existing TV art item, set it as the Artwork, or delete it from the TV (the add-on asks first, because this cannot be undone). The add-on also tries to fetch and cache thumbnails under the add-on config directory.

This requires `push_mode: local_frame_api` and a working `tv_host`. The list and thumbnails come from the TV's local Art Mode API, so the exact titles, IDs, dates, and thumbnail availability depend on what your model and firmware return. The add-on uses the thumbnail-list API when the library provides it, and the legacy per-image thumbnail API only on TVs without it. Some items, such as Art Store content on newer firmware, refuse thumbnails; those show a placeholder and do not stop the list from refreshing. The TV's API returns thumbnails only, never the original full-resolution files, so **thumbnails are not a backup of your art**. Keep the originals elsewhere, or upload through the add-on's Art page, which keeps a 4K copy in the add-on config folder (included in Home Assistant backups). When art disappears from the TV, its cached thumbnail moves to `tv-art-thumbnails-removed/` rather than being deleted. If the Artwork you chose on this page is no longer on the TV, the add-on clears it and asks you to choose new Artwork. Pictures from the Add-on Art page don't have this problem: if their copy on the TV has gone, the add-on uploads them again.

The **Current TV** page is a read-only diagnostic page. Select **Refresh Current TV Image** to ask the Samsung Frame TV which art ID is currently selected. This does not change the automatic switching logic; the add-on still switches only between the generated schedule image and the configured Artwork.

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
weekend_morning_window_start: "08:00"
weekend_morning_window_end: "10:00"
weekend_afternoon_window_start: "15:30"
weekend_afternoon_window_end: "17:30"
```

At the start of each window, the add-on generates a fresh schedule image and then pushes it to the TV. This keeps weather and calendar data current for that window.

Saturday and Sunday use the weekend fields.

Leave either time in a window blank to disable that image switch. Disabled windows are removed from the active schedule window list, so they do not schedule a boundary check and do not push a schedule image to the TV.

The window fields do not have default times. Configure both start and end for each image switch you want the add-on to run.

Outside these windows the add-on shows the configured Artwork. Artwork selected from the **TV Art** page or the add-on **Art Library** page is used by both the manual **Push Artwork** button and the automatic window-end switch.

If the previous Artwork restore failed and left the schedule marked active, the next display window start still regenerates and pushes a fresh schedule image.

You must configure Artwork before relying on automatic window-end switching. If no Artwork is configured when a window ends, the add-on reports the failure and keeps the schedule marked active so later window checks can retry after Artwork is selected.

Local Samsung Frame API calls are wrapped in an add-on timeout so a stuck upload, selection, thumbnail, or current-art request cannot block later scheduled window checks indefinitely. The add-on selects artwork with Samsung's `select_image(..., show=True)` call and does not call the separate `set_artmode` command because some TVs hang on that command after selection.

## Schedule image readability

The schedule image is designed for dim Frame TV Art Mode viewing. It uses large, high-contrast rows and scales the timed-event row height depending on how many events are on the calendar. All-day events are grouped in a right-side section because they do not have start/end times. If there are more timed events than fit comfortably, the image shows a `+ more events today` line.

This is intentional: the TV should be readable from across the room, not behave like a dense calendar dashboard.

Emoji in calendar titles are removed from the rendered image. The add-on uses Pillow and system fonts inside Home Assistant, and common color emoji render as missing-glyph boxes there instead of clean icons.

The GitHub README includes screenshots generated from fake sample calendar and weather data. Those screenshots are documentation examples only and are not pulled from a real Home Assistant calendar.

## Weather

Set `weather_entity` to a Home Assistant weather entity, such as `weather.forecast_home`, to add a weather strip to the bottom of the schedule image. Use the entity ID from **Settings** -> **Devices & services** -> **Entities**; the friendly name is not enough.

The strip uses Home Assistant's `weather.get_forecasts` action. Leave `weather_forecast_type` set to `auto` unless you know the integration supports a specific forecast type. In `auto` mode, the add-on tries `hourly`, then `daily`, then `twice_daily` and uses the first forecast response that contains entries. Set it to `hourly` if you only want hourly forecast slots. Forecast times are converted to the configured add-on timezone and the strip starts at the current hour.

Leave `weather_entity` blank to hide the weather strip and give the schedule more vertical room.

Use the **Diagnostics** page and select **Run Weather Debug** if the generated image shows `weather_count: 0`. The debug output checks whether the configured weather entity exists, then shows which forecast types Home Assistant accepted and how many forecast entries each returned.

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
7. Upload a normal art image in **Art Library**, select it, and choose **Set Selected Art as Artwork**.
8. Select **Push Artwork** to verify Artwork behavior.
9. Temporarily set one display window to include the current time.
10. Select **Run Window Check**.

For example, if it is currently 3:05 PM, temporarily use:

```text
afternoon_window_start: 15:00
afternoon_window_end: 15:20
```

After the TV test works, set the window back to the normal schedule.

The add-on logs should show entries for `push_mode`, `tv_host`, whether a window check decided to show the schedule, and each Samsung Frame action attempted.

## Generated files

The rendered schedule image and runtime state are stored under `/config` inside the add-on container. Home Assistant maps this to the add-on's backed-up config directory. After a schedule image is generated successfully, the add-on removes older `schedule*.png` files from that same directory and keeps the current schedule image.

When `push_mode` is `local_frame_api`, the add-on also tracks the Samsung Frame art IDs it uploaded for schedule images. After selecting the current schedule image, it deletes older tracked schedule uploads from the TV and keeps the current schedule art ID in state. It does not delete manually uploaded Artwork or TV art items that were not created as schedule images by this add-on.
