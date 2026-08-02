# Frame TV Schedule — Secrets

**Never put a secret value in this file.** It records only what exists, where the
authoritative copy lives, and how to rotate it.

**This repo is public.** That raises the stakes: anything committed here is
world-readable immediately and permanently, not merely retrievable by someone
with repo access.

As-built 2026-08-02.

## Add-on options (per user, set in the Home Assistant UI)

These are *the user's* secrets, not Danny's — they live in that user's HA config
and never come near this repository.

| Option | Purpose | Schema type |
|---|---|---|
| `home_assistant_token` | calls the HA API for calendars and weather | **`password?`** — typed so HA masks it in the UI |
| `tv_token_file` | path to the Samsung pairing token, default `/config/samsung-frame-token.txt` | `str` — the *path*, not the token |

The Samsung pairing token is written by the add-on on first successful pair and
persists at `tv_token_file` so it survives restarts.

**Rules that follow:**

- `home_assistant_token` is typed `password?` in `config.yaml`. **Keep it that
  way** — changing it to `str` would render it in plain text in the HA UI.
- **Never log either value.** Log that a token was found or missing, never the
  token. Users paste add-on logs into GitHub issues on a public repo.
- Never write either into a rendered image, a filename, or an error message.

## Maintainer secrets (never in this repo)

| Secret | Purpose | Where it lives |
|---|---|---|
| GitHub PAT (fine-grained) | `gh` CLI against the HA add-on repos | `.gh_token` on granny-d — **gitignored**, added 2026-08-02 |

`.gitignore` covers `.gh_token` and `.env`. That entry is load-bearing on a
public repo; do not remove it.

## Authoritative copies

Vaultwarden at https://192.168.100.50 for the maintainer PAT. User secrets have
no authoritative copy here by design — they belong to the user.

## Rotation

- **Maintainer PAT:** regenerate in GitHub settings, replace `.gh_token`. Nothing
  in CI depends on it (this repo has no pipeline).
- **A user's HA token:** they revoke the long-lived token in their own HA profile
  and paste a new one into the add-on options.
- **Samsung pairing token:** delete `/config/samsung-frame-token.txt` and let the
  add-on re-pair. Expect the TV to prompt for approval again.

## If a secret leaks

If a maintainer PAT ever reaches a commit here, **revoke it immediately** — this
repo is public and the value is scraped within minutes, not hours. Rotating
after the fact is not sufficient on its own; assume the old value was used.

For a user-reported leak (a token pasted into an issue), tell them to revoke the
HA long-lived token — editing or deleting the comment does not undo the
exposure.
