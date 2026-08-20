# Mac and Cloudflare Hosting Technical Design

## Status

Approved.

Approval date: 2026-08-20.

The owner explicitly accepted the Mac as the initial server for near-term
travel use. This design resolves the safeguards and limitations required by
`../requirements.md` while preserving a straightforward later migration to a
managed host.

## Design goals

- Produce a usable owner-only remote release today without opening a router
  port.
- Reuse the v0.1 OCI image and keep the application stateless.
- Preserve the existing portfolio site and provide `/checkmate/` as a safe
  redirect rather than changing the app's base path.
- Keep secrets out of Git, image layers, browser code, and logs.
- Add the minimum compatibility and ingress behavior needed for a safe private
  preview.
- Make failures diagnosable by an owner who is away from the Mac.

## Deployment topology

**Approved:** Run one Checkmate container and one unprivileged reverse-proxy
container under Docker Compose on the owner's Mac. Install `cloudflared` as a
named macOS service. Cloudflare Access authenticates users before Cloudflare
forwards requests down the tunnel.

```text
iPhone browser
  |
  | HTTPS: checkmate.rishabhtamhane.com
  v
Cloudflare edge
  |-- Access: exact email allowlist + one-time PIN
  |-- extraction rate limit
  |-- hostname-scoped HSTS response rule
  `-- named Tunnel (outbound connection from Mac)
        |
        v
Mac 127.0.0.1:<ingress-port>
  reverse proxy container
  |-- request envelope limits
  |-- connection limits
  `-- private Compose network
        |
        v
  Checkmate container :8000
        |
        `-- OpenAI Responses API over outbound HTTPS
```

Neither application container is published on a non-loopback interface. The
router has no inbound forwarding rule. The tunnel's final ingress rule is a
fixed 404 so an unmatched hostname cannot reach a local service.

Cloudflare documents a named tunnel as a public-hostname-to-local-service
mapping and supports running `cloudflared` as a macOS launch service:

- <https://developers.cloudflare.com/tunnel/setup/>
- <https://developers.cloudflare.com/tunnel/routing/>
- <https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/macos/>

## Canonical URL and portfolio redirect

**Approved:** The application owns the complete origin
`https://checkmate.rishabhtamhane.com`. The portfolio paths `/checkmate` and
`/checkmate/` return a temporary `302` redirect to that origin during initial
verification. After the owner confirms both sites, the redirect may become a
`301`.

The existing app emits root-relative `/static/...` paths and calls root-relative
`/api/...` endpoints. Hosting it directly below `/checkmate/` would require a
base-path feature across HTML, JavaScript, FastAPI routes, health checks, CSP,
and tests, or a fragile set of rewrites that shares an origin with the
portfolio. A dedicated subdomain isolates both applications. Cloudflare Single
Redirects support scoped URL forwarding on every plan:

<https://developers.cloudflare.com/rules/url-forwarding/>

Before creating the redirect, record the current proxied `www` DNS target and
all redirect rules. The new rule matches only the two exact Checkmate entry
paths. It must not replace the `www` DNS record or claim `www/*`.

## Application origin compatibility

**Approved:** Add an optional `PUBLIC_ORIGIN` runtime setting. When configured,
it is the exact expected value for the browser `Origin` header on
state-changing requests. Its production value is:

```text
https://checkmate.rishabhtamhane.com
```

The setting accepts only an absolute `http` or `https` origin with a hostname
and optional port; it rejects credentials, path, query, fragment, and trailing
slash ambiguity. Invalid configuration fails startup without echoing secret
values. When absent, local development retains the existing request-derived
origin behavior.

This is safer and more deterministic than enabling broad proxy-header trust.
Uvicorn continues with `proxy_headers=False`; a caller cannot forge forwarded
scheme or host headers to influence same-origin checks. Unit and HTTP tests
cover valid public origin, invalid settings, accepted HTTPS Origin, and rejected
foreign Origin.

Add a validated `REQUEST_CONCURRENCY_LIMIT` runtime setting and pass it to
Uvicorn's `limit_concurrency`. Its default and Compose value are 32 concurrent
requests. Values outside 1 through 1,000 fail startup. This limit protects the
single Python process; the existing four-call extraction semaphore remains the
stricter provider boundary.

## Local production stack

**Approved:** Add a committed `compose.yaml` and non-secret configuration under
`deploy/macos/`. The stack has these services:

### `app`

- Builds the repository Dockerfile for `linux/amd64`, the architecture already
  covered by the production smoke contract.
- Runs as image user `10001:10001` with a read-only root filesystem.
- Uses a `16 MiB`, `noexec`, `nosuid` `/tmp` tmpfs.
- Is capped at 2 CPU cores, 1 GiB of memory, 128 processes, and the existing
  16 MiB temporary filesystem. The hosting smoke test proves the application
  starts, calculates, and restarts within those bounds.
- Sets `PUBLIC_ORIGIN`, `REQUEST_CONCURRENCY_LIMIT=32`, `LOG_LEVEL=info`, and
  `OPENAI_API_KEY` through the process environment.
- Uses `restart: unless-stopped` and a `/health` health check.
- Exposes port 8000 only to the private Compose network.

The amd64 image runs under emulation on the Apple-silicon Mac. Supporting a
native arm64 release is follow-up work and must add separate build and smoke
evidence before changing the production architecture contract.

### `ingress`

- Uses a digest-pinned, unprivileged Nginx image.
- Publishes loopback-only Mac port 8080.
- Proxies only to `app:8000` on the private Compose network.
- Uses a read-only root filesystem and bounded tmpfs mounts required by Nginx.
- Is capped at 0.5 CPU core, 128 MiB of memory, 64 processes, and a 16 MiB
  temporary filesystem.
- Applies a 256 KiB body limit to calculation and PDF routes.
- Applies an ingress limit that permits a 10 MiB image plus multipart envelope
  overhead only on the extraction route; Checkmate remains the exact 10 MiB
  uploaded-file authority.
- Applies conservative per-client connection and request limits without
  logging request bodies.
- Does not cache application or API responses. Versioned static assets may be
  cached only if the upstream response permits it.
- Returns a fixed error for unknown hostnames.

Image references use immutable digests. Compose configuration, the Nginx
configuration, and helper scripts contain no credential values.

## Secret vending

**Approved:** Continue using the verified macOS Keychain item with service name
`checkmate-openai-api-key`. A repository helper reads the value silently into
the current process environment and immediately invokes Docker Compose. It
must:

1. fail if the Keychain item is absent or empty;
2. never use shell tracing;
3. never print the value;
4. avoid writing a committed or local plaintext `.env` file; and
5. unset the shell variable after Compose has created the service.

Docker stores container environment configuration in its local administrative
metadata. Anyone with access to the owner's login session or Docker daemon is
inside this initial server's trust boundary. This is acceptable for the
owner-operated preview but is one reason the later managed-host migration must
use a platform secret store.

Cloudflare tunnel tokens, credentials JSON, account IDs, and API tokens are not
Compose inputs. They live only in the permission-restricted `cloudflared`
service configuration outside the repository. Dashboard setup is preferred for
this first deployment so no long-lived Cloudflare API token is needed locally.

## Cloudflare configuration

**Approved:** Configure Cloudflare in this order:

1. Create a named tunnel dedicated to Checkmate.
2. Run the connector on the Mac and verify it is healthy without publishing a
   hostname.
3. Create a self-hosted Cloudflare Access application for the full hostname.
4. Enable one-time PIN and create an Allow policy containing the owner's exact
   email address; never use `Everyone` or an unrestricted OTP login selector.
5. Add an extraction-specific rate-limiting rule.
6. Add a response-header rule that supplies HSTS only for the Checkmate
   hostname.
7. Add `checkmate.rishabhtamhane.com` as a published application whose service
   URL is loopback port 8080, with a final catch-all returning 404.
8. Verify Access intercepts the first external request before testing the app.
9. Add the two exact-path `www` redirects after canonical-host tests pass.

Cloudflare Access sits in front of self-hosted public hostnames and supports an
exact email allowlist with one-time PIN:

- <https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/>
- <https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/>
- <https://developers.cloudflare.com/cloudflare-one/access-controls/policies/>

The extraction rate-limit expression matches the canonical host, method
`POST`, and exact path `/api/receipts/extract`. The initial threshold is five
attempts per minute per source IP, with a ten-minute mitigation timeout when
the account plan supports those values. Access is the primary identity gate;
the IP rate limit is a secondary cost and abuse control. The exact dashboard
configuration and available plan values are captured as sanitized evidence.

HSTS uses `max-age=31536000` without `includeSubDomains` or preload. Applying
the header only to the Checkmate hostname avoids imposing an unreviewed policy
on the portfolio or other subdomains. Cloudflare explicitly supports an origin
header or response transform when HSTS must be scoped to one subdomain:

<https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/>

## Capacity and cost controls

The controls address different risks:

| Control | Initial setting | Purpose |
|---|---|---|
| Cloudflare Access | Exact email allowlist | Prevent anonymous use |
| Cloudflare extraction rate limit | 5/minute/IP | Bound rapid provider spending |
| Checkmate extraction semaphore | Existing 4/process | Bound simultaneous provider calls |
| Nginx request and connection limits | Measured conservative values | Bound local origin pressure |
| App container memory/CPU | Explicit Compose limits | Protect the Mac |
| `/tmp` tmpfs | Existing 16 MiB bound | Bound temporary storage |
| OpenAI project budget/alert | Owner-configured | Independent spending control |

Cloudflare's rate limiter is deliberately not treated as exact billing
accounting. The OpenAI project budget or alert remains an independent control.

## Mac lifecycle and availability

**Approved:** This release is best effort. The deployment checklist requires:

- Connect the Mac to reliable power and Internet.
- Keep the Mac awake on power and keep a MacBook lid open unless a supported
  powered clamshell configuration is already proven.
- Configure Docker Desktop to start at login.
- Use Compose restart policies for both containers.
- Install the named tunnel as a macOS service.
- Lock the screen rather than logging out.
- Disable automatic operating-system restarts during the travel window.
- Perform a restart drill before leaving.

If the Mac reboots and Docker or the tunnel requires an interactive login, the
site remains unavailable until the owner or a trusted person logs in. Remote
shell access and attempts to bypass macOS security controls are out of scope.

## Logs and health

Application logs retain the existing allowlisted route, status, duration,
request ID, extraction category, and normalized image metadata. Nginx access
logs are disabled for the private preview unless troubleshooting requires
short-lived metadata-only logging. Cloudflare logs must not record request
bodies.

The operational check sequence is:

```text
Mac power/network/awake
  -> Docker engine
  -> Compose service and health state
  -> loopback /health through Nginx
  -> cloudflared service/tunnel state
  -> Cloudflare Access challenge
  -> authenticated external /health and app workflow
```

`/health` remains independent of OpenAI. An OpenAI outage must not trigger a
container restart or make manual splitting unavailable.

## Deployment and rollback

Build and smoke-test a unique image tag containing the short Git commit before
recreating the stack. Do not use an untraceable `latest` tag. Record the tag in
sanitized deployment evidence.

Deployment order:

1. Run all repository checks.
2. Build and run the existing container smoke contract.
3. Start the stack on loopback and run focused ingress tests.
4. Confirm the external Access policy and canonical hostname.
5. Test the complete workflow from an iPhone on cellular.
6. Enable the `www` redirect.

Rollback changes only the local image tag: recreate the app using the prior
known-good tag, confirm local health, then confirm external health. DNS, Access,
and the tunnel remain stable. If a security control is missing or the origin is
unhealthy, disable the published application route rather than bypassing
Access or exposing a direct port.

## Later managed-host migration

The application remains a stateless OCI container with environment
configuration and `/health`, so moving it does not require product-data
migration. A later workstream selects a managed container platform, stores
secrets in its secret manager, adds continuous deployment and platform health
checks, then switches the tunnel/DNS origin after acceptance. The Mac deployment
is removed only after the managed host passes the same external contract.

## Alternatives considered

- **Serve directly at `www/.../checkmate/`:** rejected for the initial release
  because root-relative routes require coordinated base-path changes and share
  failure scope with the portfolio.
- **Open router port 8000:** rejected because a Cloudflare Tunnel removes the
  inbound exposure and works behind ordinary residential NAT.
- **Cloudflare quick tunnel:** rejected for the travel release because
  Cloudflare documents quick tunnels as testing-only and their hostname is not
  stable.
- **Anonymous public preview:** rejected because extraction spends an external
  API budget and v0.1 has no accounts.
- **Managed Cloudflare Container immediately:** deferred because the owner
  accepted the Mac for the initial phase and wants access today; managed
  hosting remains the durability path.
- **Trust all proxy headers:** rejected because an explicit canonical origin
  solves the required same-origin behavior without expanding trust.

## Design references

- v0.1 system and security design under `../../v0.1-mvp/technical-design/`
- [Cloudflare Tunnel setup](https://developers.cloudflare.com/tunnel/setup/)
- [Cloudflare Tunnel routing](https://developers.cloudflare.com/tunnel/routing/)
- [Cloudflare Tunnel on macOS](https://developers.cloudflare.com/tunnel/advanced/local-management/as-a-service/macos/)
- [Cloudflare Access web applications](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/)
- [Cloudflare one-time PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- [Cloudflare Access policies](https://developers.cloudflare.com/cloudflare-one/access-controls/policies/)
- [Cloudflare rate limiting](https://developers.cloudflare.com/waf/rate-limiting-rules/)
- [Cloudflare URL forwarding](https://developers.cloudflare.com/rules/url-forwarding/)
- [Cloudflare HSTS](https://developers.cloudflare.com/ssl/edge-certificates/additional-options/http-strict-transport-security/)
