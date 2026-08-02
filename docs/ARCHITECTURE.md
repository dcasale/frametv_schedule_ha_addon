# Frame TV Schedule — Architecture

As-built 2026-08-02. User-facing setup documentation is the add-on's own
`frame_tv_schedule/DOCS.md`; this file is the internal shape.

## Shape

A single Python application packaged as a Home Assistant add-on.

```
HA calendar entities ──▶ calendar_client.py
HA weather entity    ──▶            │
                                    ▼
                              renderer.py ──▶ 3840×2160 PNG
                                    │
                        art_window_manager.py   decides: schedule image or artwork?
                                    │
                              frame_client.py ──▶ Samsung Frame TV
                                    ▲
                              art_library.py     what to show outside windows
```

| Module | Responsibility |
|---|---|
| `main.py` | entrypoint, refresh loop |
| `config.py` | reads add-on options |
| `calendar_client.py` | fetches events from the HA API |
| `renderer.py` | composes the PNG |
| `art_window_manager.py` | window logic — schedule image vs. normal artwork |
| `art_library.py` | the artwork shown outside windows |
| `frame_client.py` | **the TV driver** — all Samsung-specific behaviour |

Every module has a colocated `*_test.py`.

## Key decisions

- **The TV layer is isolated in `frame_client.py`.** Frame Art Mode upload and
  selection support varies by model and firmware, so all of that variance is
  confined to one module. Do not let Samsung-specific calls leak into the
  renderer or the window manager.
- **`push_mode` is a three-way switch, defaulting to the safe one:**
  `dry_run` (render only) → `local_frame_api` (talk to the TV directly) →
  `home_assistant_service` (go through HA). New installs start in `dry_run`.
- **Windows are configured as eight independent strings** — weekday and weekend,
  morning and afternoon, start and end — all optional. An empty string disables
  that window rather than requiring a separate toggle.
- **Tests live next to the code**, not in a separate tree.

## Add-on packaging

| Setting | Value |
|---|---|
| Slug / version | `frame_tv_schedule` / **0.2.26** |
| Architectures | `aarch64`, `amd64`, `armv7` |
| Base images | `ghcr.io/home-assistant/{arch}-base:latest` |
| Ingress | yes, port **8099**, panel icon `mdi:calendar-clock` |
| Startup | `application`, `boot: auto`, `init: false` |
| Networking | `host_network: true` — needed to reach the TV on the LAN |
| APIs | `homeassistant_api` and `hassio_api` both enabled |
| Storage | `addon_config` mapped read-write |

The Samsung pairing token persists at `/config/samsung-frame-token.txt`
(`tv_token_file`), so it survives restarts. `home_assistant_token` is typed
`password?` in the schema and must never be logged.

## Gotchas

- `host_network: true` means the add-on shares the host's network namespace —
  port 8099 must not collide with anything else on the HA box.
- The TV needs a **static IP** (`tv_host`); DHCP churn silently breaks pushing.
- Rendering targets 4K (3840×2160) regardless of the TV's own scaling.

## Related

- User setup: `frame_tv_schedule/DOCS.md`
- Deploy/distribution: `docs/INFRASTRUCTURE.md`
- Open work: `BACKLOG.md`
- Vault memory: `memory-bank/projects/project_frametv.md`
