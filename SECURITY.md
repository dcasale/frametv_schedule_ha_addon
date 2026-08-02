# Security Policy

This is a Home Assistant add-on that runs on users' own hardware, holds a
long-lived Home Assistant access token, and talks to a TV on their LAN. Security
reports are welcome and taken seriously.

*This file lives at the repository root because GitHub reads it from there (or
`docs/`, or `.github/`) to populate the Security tab. It is a disclosure policy —
what secrets the project handles and how they rotate is `docs/SECRETS.md`.*

## Supported versions

Only the latest released version receives fixes. The add-on version is in
`frame_tv_schedule/config.yaml`; release history is
`frame_tv_schedule/CHANGELOG.md`. Home Assistant add-on stores poll this
repository, so users are expected to be on the newest version.

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Use GitHub's private reporting: **Security → Report a vulnerability** on this
repository. That opens a private advisory visible only to the maintainer.

Please include:

- what an attacker can do, and what access they need to start
- affected version (`config.yaml` `version:`)
- reproduction steps
- relevant logs — **with your `home_assistant_token` and any Samsung pairing
  token redacted**

Expect an initial response within about a week. This is a hobby project
maintained by one person; there is no on-call rotation, and setting that
expectation honestly is better than implying otherwise.

## Scope

**In scope**

- Exposure or logging of `home_assistant_token` or the Samsung pairing token
- Anything reachable through the ingress UI on port 8099
- Privilege issues arising from `host_network: true` or the `homeassistant_api`
  and `hassio_api` permissions this add-on requests
- Path traversal or arbitrary write via `tv_token_file` or the artwork library
- Injection through calendar event content — event names and descriptions are
  attacker-influenced if a user subscribes to a shared calendar, and they are
  rendered into an image

**Out of scope**

- Vulnerabilities in Home Assistant itself, or in the Samsung TV firmware —
  report those upstream
- Anything requiring physical access to an already-unlocked machine
- A user choosing to expose their Home Assistant instance to the internet
- Denial of service from a malformed calendar feed

## Handling secrets in this project

`home_assistant_token` is typed `password?` in the add-on schema so Home
Assistant masks it. Neither it nor the Samsung pairing token may ever be written
to logs, filenames, rendered images, or error messages — users routinely paste
add-on logs into public issues. See `docs/SECRETS.md`.
