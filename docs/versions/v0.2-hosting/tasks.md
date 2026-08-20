# v0.2 Initial Hosting Tasks

## Workstreams

- [Mac and Cloudflare hosting](tasks/01-mac-cloudflare-hosting.md)
  - Status: In progress; application compatibility and the local loopback stack
    are complete, while release inventory and owner-assisted Cloudflare setup
    remain
  - Design approved on 2026-08-20

## Execution priority

Milestone 1 is the travel-ready critical path. Complete it before undertaking
the managed-host follow-up. Cloudflare account and macOS changes require the
owner's active session and must preserve the existing `www` site.

## Definition of Done

- Every v0.2 acceptance criterion has passing or explicitly owner-deferred
  evidence in `tests.md`.
- Required repository checks pass.
- No secret or real receipt data appears in Git, image layers, Compose output,
  logs, screenshots, or task evidence.
- The owner completes an authenticated iPhone test over cellular.
- Start, stop, status, recovery, and rollback instructions are usable without
  repository knowledge.
- The owner acknowledges that the site stops when the Mac, Docker, Internet,
  or tunnel stops.
