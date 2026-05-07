# Frame TV Schedule Home Assistant Add-on

Frame TV Schedule generates a daily calendar artwork image from Home Assistant calendar entities and displays it on a Samsung Frame TV during configured time windows.

The first goal is a reliable schedule image pipeline:

- read events from Home Assistant calendars, including Apple Calendar through HA CalDAV
- render a polished 16:9 PNG suitable for Samsung Frame Art Mode
- display that image only during configured windows, such as 6:00-8:00 AM and 2:30-4:30 PM
- show configured Artwork outside those windows

Samsung Frame Art Mode upload and selection support varies by model and firmware, so the TV control layer is intentionally isolated behind a driver module.

## Add-on

Add this repository to the Home Assistant add-on store, then install **Frame TV Schedule**.

Use the add-on's **Documentation** tab for setup details. The most important first-run fields are:

- `calendar_entity`: the Home Assistant entity ID for your calendar, such as `calendar.family`
- `push_mode`: start with `dry_run`, then switch to `local_frame_api` after image generation works
- `tv_host`: the static IP address assigned to the Samsung Frame TV

After starting the add-on, select **Open Web UI**, then select **Generate** to render and preview the first schedule image.

The add-on does not need Apple credentials or Samsung account credentials. Apple Calendar credentials stay in Home Assistant's CalDAV integration. Samsung Frame control uses a local TV pairing prompt and stores the resulting token in the add-on config directory.

If calendar diagnostics reports that the Home Assistant supervisor token is unavailable, update the add-on first. If it remains unavailable, uninstall and reinstall the add-on after reloading the repository so Home Assistant reapplies the add-on API permissions.

If the Supervisor token is still unavailable, create a Home Assistant long-lived access token in your user profile and paste it into the add-on's `home_assistant_token` field. The default manual API URL is `http://127.0.0.1:8123/api`; change `home_assistant_url` if your Home Assistant instance is reachable at a different address from the add-on.

Initial development can also be done by copying the `frame_tv_schedule` directory into a Home Assistant `/addons` folder and using the local add-ons repository.
