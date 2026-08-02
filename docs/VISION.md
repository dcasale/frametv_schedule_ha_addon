# Frame TV Schedule — Vision

> ⚠️ **DRAFT — needs Danny's review.** Written by an agent on 2026-08-02 from
> `README.md`, `frame_tv_schedule/config.yaml`, and the add-on source. The
> product shape is directly evidenced by the code; **the goals and non-goals
> below are inference.** Confirm or correct this the next time you work on this
> project, then delete this banner.

**One-sentence pitch:** A Home Assistant add-on that turns your family calendar
into a piece of artwork and shows it on a Samsung Frame TV during the parts of
the day when you actually want to see it.

## What is it?

A Home Assistant add-on (`slug: frame_tv_schedule`, currently **v0.2.26**,
built for aarch64 / amd64 / armv7) that:

1. Reads events from HA calendar entities — up to three, including Apple
   Calendar via HA's CalDAV integration.
2. Renders a polished **3840×2160 16:9 PNG** suitable for Frame Art Mode,
   optionally including weather from a configured weather entity.
3. Displays that image on the TV **only during configured windows** — separate
   weekday and weekend morning/afternoon windows — and shows your normal
   artwork the rest of the time.

It refreshes every 30 minutes by default and exposes an ingress UI on port 8099.

## Who is it for?

Households with a Samsung Frame TV and Home Assistant who want the day's
schedule glanceable in a living space without a screen that looks like a screen.
Danny first; published publicly through the `dcasale` add-on repository.

## Why does it exist?

A Frame TV spends most of its life displaying art. That is a free, already-paid-for
ambient display in a room people walk through — showing the family's actual day
on it is more useful than another landscape, but only at the times when someone
is there to read it.

## What does success look like?

*(Inferred.)*

- The schedule is on the wall at breakfast and after school without anyone
  touching anything.
- Outside those windows the TV looks like art, not a dashboard.
- It survives Samsung firmware updates — hence the isolated driver layer.

## Design commitments

- **The TV control layer is deliberately isolated behind a driver module**
  (`app/frame_client.py`), because Frame Art Mode upload and selection support
  varies by model and firmware. This is an explicit architectural hedge.
- **`push_mode` starts at `dry_run`.** Get image generation right before
  touching the TV. Modes: `dry_run` → `local_frame_api` → `home_assistant_service`.
- **`privacy_mode`** exists as a first-class option — event details can be
  suppressed on a screen in a shared room.

## Explicit non-goals

- Not a general calendar app — it renders, it does not edit.
- Not a TV remote — it puts one image on one TV.
- Not Samsung-agnostic today, though the driver split leaves room for it.

## Open questions for review

1. Is this intended as a maintained public add-on with users, or primarily
   Danny's own with the repo public as a side effect?
2. `docs/` currently holds only images — is written documentation intended here,
   or is the add-on's own `DOCS.md` the canonical user documentation?
