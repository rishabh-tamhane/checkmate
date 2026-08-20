# v0.2 Initial Hosting Technical Design

This file indexes the approved design workstream for the initial hosted
release.

## Workstreams

- [Mac and Cloudflare hosting](technical-design/01-mac-cloudflare-hosting.md)
  - Status: Approved on 2026-08-20

## Design governance

- Requirements in `requirements.md` define the release behavior.
- The detailed workstream defines the approved implementation approach.
- Application, container, or deployment configuration must not change contrary
  to the approved workstream without returning it to Draft and resolving the
  decision first.
- Cloudflare dashboard changes are production changes. Inventory existing
  records and rules, record the intended diff, and preserve the current `www`
  site before applying them.
- Secrets and real receipt data must never be added to repository evidence.
