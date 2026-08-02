# Frame TV Schedule

Home Assistant add-on that renders the day's calendar as 4K artwork and shows it
on a Samsung Frame TV during configured windows. This file is the agent entry
point; workspace-wide rules live one level up (`/root/projects/AGENTS.md`) and
in the memory-bank vault.

*(Was a symlink to the workspace rules until 2026-08-02. Promoted to a real file
because this project now has its own docs and specifics worth stating.)*

## Docs
```
docs/VISION.md                    what it is, who it serves — ⚠️ AI DRAFT, NEEDS DANNY'S REVIEW
docs/ARCHITECTURE.md              module shape, TV driver isolation, packaging
docs/INFRASTRUCTURE.md            distribution, HA runtime footprint, install target
frame_tv_schedule/DOCS.md         user-facing setup (the add-on's own docs)
frame_tv_schedule/CHANGELOG.md    release history
BACKLOG.md                        open work
```

> **⚠️ `docs/VISION.md` was drafted by an agent on 2026-08-02 and has not been
> reviewed.** The product shape came straight from `config.yaml` and the add-on
> source, but the goals are inference. It ends with two open questions (whether
> this is a maintained public add-on or primarily Danny's own, and whether
> `docs/` should hold written documentation or defer to `DOCS.md`).
> **Next time you work on this project, settle those with Danny, correct the
> file, and delete its banner.**

## Layout

- `frame_tv_schedule/` — the add-on itself (`config.yaml`, `Dockerfile`,
  `run.sh`, `app/`)
- `frame_tv_schedule/app/` — the Python application; each module has a
  colocated `*_test.py`
- `repository.yaml` — the HA add-on repository manifest
- `scripts/` — local dev helpers

## Rules

- **All Samsung-specific behaviour stays in `app/frame_client.py`.** Frame Art
  Mode support varies by TV model and firmware; that variance is deliberately
  confined to the driver. Do not let TV calls leak into `renderer.py` or
  `art_window_manager.py`.
- **Default `push_mode` is `dry_run`.** Never change the shipped default —
  new installs must render before they touch a TV.
- **Bump `version:` in `frame_tv_schedule/config.yaml` and add a
  `CHANGELOG.md` entry for any user-visible change.** HA add-on stores poll the
  repo; an unbumped version means nobody gets the fix.
- `home_assistant_token` is a secret (`password?` in the schema) — never log it,
  never commit a filled-in `options`.
- Tests live next to the code. Run them before bumping a version.

## Deployment reality

This project does **not** deploy to any VM in this lab — it installs into a Home
Assistant instance from the `dcasale` add-on repository. There is no CI here.
The live install target is not yet pinned; see `docs/INFRASTRUCTURE.md`.
