# Frame TV Schedule Home Assistant Add-on

Frame TV Schedule generates a daily calendar artwork image from Home Assistant calendar entities and displays it on a Samsung Frame TV during configured time windows.

The first goal is a reliable schedule image pipeline:

- read events from Home Assistant calendars, including Apple Calendar through HA CalDAV
- render a polished 16:9 PNG suitable for Samsung Frame Art Mode
- display that image only during configured windows, such as 6:00-8:00 AM and 2:30-4:30 PM
- restore the previously selected art, or a configured fallback art, outside those windows

Samsung Frame Art Mode upload and restore support varies by model and firmware, so the TV control layer is intentionally isolated behind a driver module.

## Add-on

Add this repository to the Home Assistant add-on store, then install **Frame TV Schedule**.

Initial development can also be done by copying the `frame_tv_schedule` directory into a Home Assistant `/addons` folder and using the local add-ons repository.
