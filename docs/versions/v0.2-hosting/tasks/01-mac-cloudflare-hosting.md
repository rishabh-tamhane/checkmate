# Mac and Cloudflare Hosting

## Status

In progress. M1-02 and M1-03 are complete with automated evidence. M1-01 release
inventory and M1-04 through M1-07 require the final release commit and the
owner's active macOS and Cloudflare sessions.

## Design sources

Read all of these before application or deployment changes:

- [v0.2 requirements](../requirements.md)
- [Approved Mac and Cloudflare hosting design](../technical-design/01-mac-cloudflare-hosting.md)
- [v0.1 MVP implementation design](../../v0.1-mvp/technical-design/02-mvp-implementation.md)
- [v0.1 security and privacy guide](../../v0.1-mvp/technical-design/02-mvp-implementation/06-security-and-privacy.md)
- [v0.1 runtime and testing guide](../../v0.1-mvp/technical-design/02-mvp-implementation/07-runtime-and-testing.md)
- [Engineering tenets](../../../ENGINEERING_TENETS.md)

## Execution rules

- Use synthetic data for every automated or recorded test.
- Do not display, log, save in a repository file, or commit any credential.
- Inventory Cloudflare `www` state before changing DNS or rules.
- Prefer dashboard changes for the first launch; do not create a broad
  Cloudflare API token for convenience.
- Ask the owner before applying macOS power, login-item, launch-service, DNS,
  Access, or redirect changes.
- If an account plan cannot provide an approved security control, stop and
  update the design rather than silently omitting it.

## Milestone 1 — Travel-ready private launch

Outcome: the owner can use Checkmate from an iPhone over cellular while the Mac
is powered, awake, online, and running the stack.

### M1-01 Inventory and preflight

- [ ] Record the current Git commit and confirm required repository checks
  pass.
- [ ] Confirm the production image builds and passes
  `tests/container_smoke_test.py`.
- [ ] Confirm the OpenAI Keychain item authenticates without printing it.
- [ ] Record sanitized current Cloudflare state for the `www` DNS record,
  certificate, redirects, Access organization, and available rate-limit rule
  settings.
- [ ] Confirm `checkmate.rishabhtamhane.com` is unused.
- [ ] Confirm the Mac can remain on reliable power and Internet with its lid and
  sleep configuration proven for the travel window.

### M1-02 Add explicit public-origin configuration

- [x] Add optional, validated `PUBLIC_ORIGIN` to application settings.
- [x] Use it for state-changing Origin validation while retaining the current
  local default when it is absent.
- [x] Keep Uvicorn proxy-header trust disabled.
- [x] Add validated `REQUEST_CONCURRENCY_LIMIT`, default it to 32, and pass it
  to Uvicorn's request-concurrency control.
- [x] Add unit and HTTP regression tests for valid, invalid, accepted, and
  foreign origins, plus concurrency-limit parsing and wiring.
- [x] Document the new environment variable without including a secret.

### M1-03 Build the loopback production stack

- [x] Add digest-pinned `compose.yaml` services for Checkmate and unprivileged
  Nginx.
- [x] Bind only the Nginx ingress port to `127.0.0.1` and keep the app port on
  the private Compose network.
- [x] Preserve the non-root, read-only, bounded-tmpfs image contract.
- [x] Add measured CPU, memory, restart, and health-check settings.
- [x] Add route-specific request limits and conservative connection limits to
  Nginx.
- [x] Disable ingress request-body logging and preserve upstream security and
  cache headers.
- [x] Add a helper that silently vends the existing Keychain value to Compose,
  fails closed, and leaves no plaintext secret file.
- [x] Add focused tests for Compose rendering, loopback binding, unknown hosts,
  health, request boundaries, and restart behavior.

### M1-04 Create the named Cloudflare Tunnel connector

- [ ] Install a pinned current `cloudflared` package from Cloudflare's supported
  macOS distribution path.
- [ ] Create a named Checkmate tunnel without exposing credentials in shell
  output or repository files.
- [ ] Install and verify `cloudflared` as the appropriate macOS service.
- [ ] Verify the connector is healthy before publishing any hostname.
- [ ] Confirm no home-router inbound port forwarding is present or required.

### M1-05 Protect and publish the private preview

- [ ] Create a full-hostname Cloudflare Access self-hosted application.
- [ ] Enable one-time PIN and allow only the owner's exact email address.
- [ ] Verify another email address cannot reach the page or API.
- [ ] Configure the extraction rate limit for the exact host, POST method, and
  extraction path; capture sanitized rule evidence.
- [ ] Confirm an OpenAI project budget or usage alert is active.
- [ ] Add hostname-scoped HSTS without `includeSubDomains` or preload.
- [ ] Only after the controls exist, publish
  `checkmate.rishabhtamhane.com` to loopback port 8080 and retain a final
  fixed-404 tunnel rule.
- [ ] Verify the first external request is intercepted by Access.
- [ ] Confirm sensitive responses are not cached at Cloudflare.

### M1-06 Verify remotely and enable the convenience redirect

- [ ] Verify certificate, HSTS, Access challenge, app shell, assets, `/health`,
  calculation, and PDF download at the canonical hostname.
- [ ] Test from the owner's iPhone with Wi-Fi disabled.
- [ ] Perform one owner-authorized synthetic extraction or record its explicit
  deferral without closing the existing v0.1 evaluation gate.
- [ ] Add temporary exact-path redirects for both `/checkmate` forms.
- [ ] Verify the portfolio root and an unrelated path are unchanged.
- [ ] Promote the redirects to permanent only after owner acceptance.

### M1-07 Complete the travel handoff

- [ ] Document exact start, stop, update, status, log, health, rollback, and
  tunnel-recovery commands.
- [ ] Configure Docker to start at login and verify container restart policies.
- [ ] Verify the Mac remains awake while powered and the screen is locked.
- [ ] Deliberately restart the app and tunnel, then use the recovery checklist.
- [ ] Record the running Git commit and image tag without credentials.
- [ ] Have the owner acknowledge the reboot/login, power, lid, Internet, and
  Docker availability limits.

## Milestone 2 — Operability after the trip

Outcome: routine updates and diagnostics are repeatable and do not depend on
remembered commands.

- [ ] Add a sanitized deployment evidence template.
- [ ] Add a scripted external metadata-only smoke check compatible with Access
  service credentials or document why interactive verification remains safer.
- [ ] Add a documented monthly `cloudflared`, base-image, and dependency update
  check.
- [ ] Review Cloudflare and OpenAI usage after real use and adjust limits in the
  design before changing them.
- [ ] Decide whether invited testers remain exact-email allowlisted or whether
  the preview should become public; public launch requires a separate reviewed
  abuse and availability decision.

## Milestone 3 — Managed-host migration backlog

Outcome: the Mac is no longer the availability dependency when the owner is
ready to pay for managed hosting.

- [ ] Compare managed OCI hosts using measured Checkmate memory, startup time,
  request duration, secrets, health checks, custom-domain support, and monthly
  cost.
- [ ] Approve a new managed-host technical design before implementation.
- [ ] Add platform secret management and least-privilege deployment
  credentials.
- [ ] Add CI deployment, preview verification, promotion, and rollback.
- [ ] Pass the v0.2 external contract on the managed host.
- [ ] Switch the canonical origin and retire the Mac stack only after owner
  acceptance.

## Requirement coverage

| Requirement area | Primary tasks |
|---|---|
| Canonical URL and existing-site safety | M1-01, M1-04, M1-06 |
| Private Access | M1-05 |
| Mac runtime and restart | M1-03, M1-07 |
| HTTPS and request identity | M1-02, M1-05 |
| Secrets and privacy | M1-01, M1-03, M1-04 |
| Abuse, capacity, and cost | M1-03, M1-05 |
| Remote verification and recovery | M1-06, M1-07 |
| Later durability | Milestone 3 |
