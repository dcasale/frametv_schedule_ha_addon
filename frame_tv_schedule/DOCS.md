# Frame TV Schedule

This add-on creates a daily schedule image from Home Assistant calendar entities and can display it on a Samsung Frame TV during configured time windows.

## Calendar setup

For Apple Calendar, add your iCloud calendars to Home Assistant with the CalDAV integration. Then add the resulting `calendar.*` entity IDs to this add-on's `calendar_entities` option.

## Display windows

Use `display_windows` to control when the generated schedule should temporarily become the selected artwork.

```yaml
display_windows:
  - start: "06:00"
    end: "08:00"
  - start: "14:30"
    end: "16:30"
```

Outside these windows the add-on restores the previous art when the TV driver can read it. If that is not supported on your model, configure a fallback art ID or fallback image.

## TV push modes

`dry_run` renders the image and logs what would happen. This is the safest starting point.

`local_frame_api` connects directly to the Samsung Frame on your local network and uses its Art Mode API.

Recommended TV settings before using `local_frame_api`:

- reserve a static DHCP address for the TV
- keep Home Assistant and the TV on the same subnet/VLAN
- on the TV, approve the connection prompt the first time the add-on connects
- set the TV's access notification behavior to first-time-only if repeated prompts appear

Required add-on options:

```yaml
push_mode: local_frame_api
tv_host: 192.168.1.50
tv_port: 8002
tv_token_file: /config/samsung-frame-token.txt
tv_matte: none
```

The token file stores the local TV pairing token in the add-on config directory so pairing survives restarts and backups.

`home_assistant_service` is reserved for calling a Home Assistant service exposed by another Samsung Frame integration.

## Generated files

The rendered schedule image and runtime state are stored under `/config` inside the add-on container. Home Assistant maps this to the add-on's backed-up config directory.
