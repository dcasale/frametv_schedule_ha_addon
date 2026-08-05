# Frame TV Schedule — Infrastructure

**Scope: this project's slice only.** Lab-wide host inventory lives in the vault
(`memory-bank/reference/ref_service_inventory.md`). A map, not a mirror.
As-built 2026-08-02.

This project is unusual in this workspace: **it does not deploy to any VM here.**
It ships as a Home Assistant add-on and runs on whichever HA instance installs
it.

## Distribution

| | |
|---|---|
| Add-on repository | `https://github.com/dcasale/frametv_schedule_ha_addon` |
| Repository manifest | `repository.yaml` at the repo root |
| Install path | HA → Settings → Add-ons → Add-on Store → add this repository → install **Frame TV Schedule** |
| Current version | **0.2.26** (`frame_tv_schedule/config.yaml`) |
| Architectures | `aarch64`, `amd64`, `armv7` |

Releasing means bumping `version:` in `config.yaml`, updating
`frame_tv_schedule/CHANGELOG.md`, and pushing — HA add-on stores poll the repo.
There is no CI pipeline in this repository.

## Runtime footprint on the HA host

| | |
|---|---|
| Ingress port | **8099/tcp** |
| Networking | `host_network: true` — shares the HA host's network namespace |
| Persistent config | `addon_config` mapped read-write |
| Pairing token | `/config/samsung-frame-token.txt` |
| Refresh interval | 30 minutes (`refresh_minutes`) |

Because of `host_network: true`, port 8099 must be free on the HA host.

## Which HA instance?

The lab has three Home Assistant instances (details in
`memory-bank/reference/ref_service_inventory.md`):

- **haos-House, 192.168.100.10** — primary, and the likely production target
- **haos-Guesthouse, 192.168.100.102**
- **haos-t, 192.168.100.136** — test instance, rarely used

**The live install target is not pinned in memory.** haos-t is the natural place
to test an add-on before promoting to the house instance. Confirm and record it
here when next working on this project.

**HAOS VMs have no SSH** — they are managed through the HA UI only. There is no
`ssh root@…` path for debugging; use the add-on's log tab and ingress UI.

## Device dependency

The Samsung Frame TV must have a **static IP** (`tv_host`, `tv_port` 8002).
DHCP reassignment silently breaks pushing — the add-on keeps rendering and the
TV just never updates.

Local development runs the app directly rather than as an add-on; `scripts/`
holds the helpers.

## Related

- Internal shape: `docs/ARCHITECTURE.md`
- User setup: `frame_tv_schedule/DOCS.md`
- Vault memory: `memory-bank/projects/tv-schedule-ha-addon/project_frametv.md`
