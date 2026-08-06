# Frame TV Schedule — Release Guide

This project has no CI pipeline and deploys to no server. **Releasing is
publishing a version**, and Home Assistant add-on stores poll this repository —
so a push reaches real users' Home Assistant instances with no further action
from you.

Where it runs is `docs/INFRASTRUCTURE.md`. This is the runbook.

As-built 2026-08-02.

## Deployment reality

This project does **not** deploy to any VM in this lab — it installs into a Home
Assistant instance from the `dcasale` add-on repository. There is no CI here.
The live install target is not yet pinned; see `docs/INFRASTRUCTURE.md`.

## Release checklist

1. **Run the tests.** Every module has a colocated `*_test.py`; run them before
   anything else.
2. **Bump `version:`** in `frame_tv_schedule/config.yaml`. This is the step that
   actually ships — an unbumped version means nobody receives the change, and
   the add-on store shows no update.
3. **Add a `frame_tv_schedule/CHANGELOG.md` entry.** Users read it in the add-on
   store before updating.
4. **Check the shipped defaults.** `push_mode` must still default to `dry_run`,
   and no `options:` value may contain a real token, IP, or entity ID from your
   own setup.
5. Commit and push.

## Verify a release

Install or update the add-on on a test Home Assistant instance before the house
one. The lab has `haos-t` (192.168.100.136) for exactly this; the primary is
`haos-House` (192.168.100.10).

After update, check in order:

1. The add-on starts and the ingress UI on 8099 loads.
2. With `push_mode: dry_run`, an image renders.
3. Only then switch to `local_frame_api` and confirm the TV updates.

**HAOS VMs have no SSH.** There is no shell to debug from — use the add-on's Log
tab and the ingress UI. Plan for that before you need it.

## Roll back

**You cannot recall a published version.** The store has already served it.

Publish a *new, higher* version that reverts the change, and note it plainly in
the changelog. Users who already updated need an upgrade path, not a rollback.

A user can pin themselves by uninstalling and installing an older version
manually, but do not rely on users doing that — it is not the fix.

## Things that bite

- **`host_network: true`** means the add-on shares the HA host's network
  namespace. Port 8099 must be free there; a collision looks like the add-on
  failing to start for no visible reason.
- **The TV needs a static IP.** DHCP reassignment breaks pushing silently — the
  add-on keeps rendering and the TV simply never updates. Check `tv_host` first
  when someone reports "it stopped working".
- **Frame Art Mode behaviour varies by model and firmware.** That is why all
  Samsung-specific code is confined to `app/frame_client.py`. A change that works
  on your TV may not work on someone else's — this is the main reason to
  rehearse a release rather than push it straight out.
- **Three architectures** are built (`aarch64`, `amd64`, `armv7`). A change that
  assumes x86 will break Raspberry Pi users.

## Related

- Distribution and runtime footprint: `docs/INFRASTRUCTURE.md`
- Secrets and what must never be logged: `docs/SECRETS.md`
- Disclosure policy: `../SECURITY.md`
- User-facing setup: `../frame_tv_schedule/DOCS.md`
