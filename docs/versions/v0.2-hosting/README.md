# v0.2 Initial Hosting

v0.2 makes the existing Checkmate container available remotely for an
owner-only initial release. The first deployment runs on the owner's Mac and is
published through a named Cloudflare Tunnel. It is intentionally a low-cost,
short-term hosting arrangement rather than a high-availability production
platform.

## Documents

- [Requirements](requirements.md)
- [Technical design](technical-design.md)
- [Verification plan](tests.md)
- [Implementation tasks](tasks.md)

## Release posture

- Canonical URL: `https://checkmate.rishabhtamhane.com/`
- Convenience entry point: `https://www.rishabhtamhane.com/checkmate/`
- Audience: owner and explicitly allowlisted testers
- Origin: one Checkmate container on the owner's Mac
- Ingress: Cloudflare Access and a named Cloudflare Tunnel
- Availability: best effort while the Mac is powered, awake, online, logged in,
  and running Docker and `cloudflared`

The current `www.rishabhtamhane.com` origin must be inventoried before any DNS
or redirect change. This version must not replace or interrupt that site.

## Relationship to v0.1

This version deploys the stateless image and product workflow defined by
`../v0.1-mvp/`. It does not change split behavior, add accounts, or close the
deferred v0.1 live-provider quality evaluation. Until that evaluation is
complete, automatic extraction remains preview functionality and every value
still requires user review.
