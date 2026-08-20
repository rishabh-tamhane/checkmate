# Checkmate Initial Hosting Requirements

## 1. Overview

The owner must be able to use Checkmate from an iPhone or another remote device
while away from the development network. For the initial phase, the owner's Mac
may run the server. Cloudflare provides the public hostname, authentication,
HTTPS, and an outbound tunnel so the home router does not expose an inbound
port.

The initial release is a private preview for the owner and explicitly invited
testers. It is not a high-availability public service.

## 2. URL and existing-site safety

- The canonical application URL is
  `https://checkmate.rishabhtamhane.com/`.
- `https://www.rishabhtamhane.com/checkmate` and the same path with a trailing
  slash redirect to the canonical URL.
- The redirect must be scoped to those paths and must not change the behavior
  of any other `www.rishabhtamhane.com` route.
- The existing `www` DNS record, origin, redirect rules, and certificate state
  must be recorded before a Cloudflare change is made.
- The app is not required to operate natively below `/checkmate/`. The
  subdomain remains canonical because the v0.1 app owns root-relative `/api`,
  `/static`, and `/health` paths.

## 3. Private preview access

- Cloudflare Access must protect the complete canonical hostname before
  automatic extraction is exposed.
- Only individually allowlisted email addresses may authenticate.
- One-time PIN may be used as the identity method so the owner can sign in on
  an iPhone without installing a VPN client.
- A policy that permits every email address or every one-time-PIN user is not
  acceptable.
- The owner must be able to remove an allowlisted tester without changing the
  application.

## 4. Mac-hosted runtime

- The tested OCI image runs as a non-root container with a read-only root
  filesystem and bounded temporary storage.
- The application is reachable only on a loopback-bound Mac port; it is not
  exposed directly to the LAN or Internet.
- A local reverse proxy enforces request-size and connection limits before a
  request reaches the Python process.
- The application container and reverse proxy restart automatically after a
  process failure and after Docker restarts.
- The named Cloudflare Tunnel runs as a macOS service and connects outbound to
  Cloudflare.
- The Mac must remain powered, awake, online, logged in, and with Docker
  running. Closing an unsupported MacBook lid, losing power or Internet, a
  reboot awaiting login, or Docker failure may make the app unavailable.
- Setup documentation must include start, stop, status, log, restart, and
  recovery commands that do not display secrets.

## 5. HTTPS and request identity

- Visitors use HTTPS only, with a valid Cloudflare-managed certificate.
- Responses from the canonical hostname include an HSTS policy without
  changing HSTS behavior for unrelated hostnames.
- The app accepts state-changing browser requests from the exact configured
  canonical HTTPS origin.
- The deployment must not broadly trust client-supplied proxy headers.
- The tunnel must not require a public inbound router port.

## 6. Secrets and privacy

- `OPENAI_API_KEY`, Cloudflare tunnel credentials, and Cloudflare API tokens
  are never committed, copied into an image layer, printed, or included in
  application logs.
- The OpenAI key is loaded from the owner's macOS Keychain into the container
  environment only when the local stack is created or updated.
- Cloudflare credentials remain in Cloudflare-managed configuration or a
  permission-restricted host service location outside the repository.
- Receipt images, request bodies, PDF contents, participant names, and provider
  responses are not written to application or ingress logs.
- Sensitive application responses remain `Cache-Control: no-store` at every
  layer.

## 7. Abuse, capacity, and cost controls

- The local ingress rejects receipt uploads whose HTTP envelope exceeds the
  configured upload boundary and rejects calculation or PDF JSON bodies above
  256 KiB. The application remains the authoritative exact 10 MiB image-file
  validator.
- The Python server has a bounded request-concurrency setting, and receipt
  extraction retains its stricter per-process provider concurrency limit.
- Cloudflare rate-limits `POST /api/receipts/extract` for authenticated users.
- The OpenAI project has a budget or usage alert independent of the Cloudflare
  control.
- The host container has explicit CPU, memory, and temporary-storage bounds.
- Manual entry, calculation, PDF generation, and `/health` remain usable when
  OpenAI is unavailable.

## 8. Deployment, verification, and recovery

- A local production stack is reproducible from committed, non-secret
  configuration.
- A deployment records the Git commit and local image tag that are running.
- A release is verified locally before its tunnel route is enabled.
- External smoke checks cover the Access challenge, authenticated app shell,
  static assets, health, calculation, PDF download, and one explicitly
  authorized extraction test when desired.
- The owner performs an iPhone test over cellular rather than relying only on
  the home Wi-Fi path.
- Rollback recreates the prior known-good image without changing DNS or the
  tunnel.
- A short recovery checklist covers Mac wake state, Docker state, container
  health, tunnel state, and Cloudflare route state.

## 9. Acceptance criteria

The initial hosting release is complete when:

1. The owner can open `https://checkmate.rishabhtamhane.com/` over cellular.
2. A non-allowlisted visitor cannot reach the Checkmate page or API.
3. An allowlisted owner can authenticate by email and use the complete v0.1
   workflow.
4. The two `/checkmate` convenience URLs redirect to the canonical subdomain,
   while an unrelated `www` URL is unchanged.
5. The browser can calculate and generate a PDF through the HTTPS origin
   without an origin-validation failure.
6. Automatic extraction receives the OpenAI key without exposing it to the
   browser, repository, image, command output, or logs.
7. Oversized requests and excessive extraction attempts are rejected by the
   configured controls.
8. The public response includes HSTS and retains the v0.1 CSP, no-sniff,
   no-referrer, frame-denial, and no-store policies.
9. No inbound port-forwarding rule is needed on the home router.
10. The app recovers after a deliberate container restart, and the documented
    status commands identify an app or tunnel failure.
11. The production stack passes repository checks and focused hosting tests.
12. The owner has acknowledged the availability limits of using the Mac before
    relying on it during travel.

## 10. Out of scope

- High availability, uptime guarantees, or a second tunnel replica
- Running when the Mac is off, asleep, offline, or awaiting user login
- A native application deployment below the `/checkmate/` path prefix
- Public anonymous extraction
- Application accounts, saved history, or a database
- Automated DNS or Cloudflare account provisioning in this first release
- Remote shell access to the Mac
- Migrating to a managed container host; that is recorded as follow-up work
