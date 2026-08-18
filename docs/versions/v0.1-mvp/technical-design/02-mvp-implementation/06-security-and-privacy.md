# Security and Privacy Guide

## Status

Draft, awaiting review.

## Document role

This guide explains the sensitive-data lifecycle, trust boundaries, abuse
controls, logging policy, browser protections, and deployment responsibilities
proposed in [`../02-mvp-implementation.md`](../02-mvp-implementation.md). The
parent document remains authoritative. This status records review of this
design area; it does not approve the overall workstream.

Read this guide before implementing request handling, logging, error responses,
OpenAI configuration, browser rendering, caching, or public deployment.

## What Checkmate must protect

The MVP has no account database, but it still processes sensitive information:

- Receipt image bytes
- Restaurant and date
- Purchased items and amounts
- Participant names
- Extracted provider content
- Generated split PDFs
- `OPENAI_API_KEY`

“Not saved in a database” does not mean “not sensitive.” Data can also leak
through logs, exception messages, caches, temporary files, analytics, HTTP
headers, screenshots, and third-party requests.

## Data lifecycle

```text
User device
    |
    | receipt upload over HTTPS in production
    v
Checkmate request memory
    |
    | normalized image only
    v
OpenAI request
    |
    v
Editable extraction result in browser memory
    |
    v
Calculation and PDF requests
    |
    v
Response returned; application retains no draft or file
```

The browser draft disappears on refresh or close. The server does not write the
receipt, draft, provider response, or PDF to application-managed persistent
storage.

## Trust boundaries

### Browser to server

All browser input is untrusted, even when it came from Checkmate's own page. A
caller can modify JavaScript, forge JSON, change IDs, or call endpoints directly.

The server therefore validates:

- Body size and structure
- Every editable value
- Item and participant identity references
- Origin policy
- Reconciliation and finalization

### Server to external provider

The receipt image and provider response cross a third-party boundary. The user
must be told before upload that the image will be sent to OpenAI.

The provider response is also untrusted input. Structured shape, lengths, and
values are validated before the result becomes an editable draft.

### Server to PDF library and browser

User-controlled text is escaped before ReportLab markup processing and rendered
with safe DOM properties such as `textContent`, not `innerHTML`.

## Secret management

`OPENAI_API_KEY` belongs in the process environment or a deployment secret
store. It must never be:

- Committed to Git
- Placed in `.env.example` with a real value
- Embedded in HTML or JavaScript
- Accepted from a browser form
- Printed in logs or exceptions
- Added to a Docker image layer

The key is read by server configuration at startup. Browser requests reach the
Checkmate backend; the backend calls OpenAI.

```text
Correct:
Browser -> Checkmate server [secret lives here] -> OpenAI

Incorrect:
Browser [secret exposed here] ------------------> OpenAI
```

## Privacy disclosure

Before upload, the interface should state:

- The receipt image will be sent to OpenAI for extraction.
- Extracted fields must be reviewed.
- Manual entry is available without uploading.
- Users should upload restaurant receipts only, not regulated health,
  identity, or financial documents.

The application must not claim zero provider retention unless the deployed
OpenAI project is separately approved and configured for Zero Data Retention.

## Logging by allowlist

It is safer to define what may be logged than to try to enumerate every secret
afterward.

Allowed operational fields include:

- Timestamp and level
- Generated request ID
- Route and HTTP status
- Duration
- Upload byte count
- Normalized image dimensions
- Provider model and prompt version
- Safe error category

Excluded fields include:

- Request or response bodies
- Original filenames
- Restaurant, item, and participant text
- Monetary values
- Receipt images
- Prompt body or provider response body
- API keys
- Stack traces returned to clients

A request ID lets a user report a failure while internal logs retain only safe
diagnostic context.

## Safe errors

An external exception may contain a request body, provider details, internal
path, or credential fragment. It must be translated before reaching the client.

```text
Internal exception
      |
      v
Log safe category + request ID
      |
      v
Return stable code + safe message + request ID
```

User-correctable validation messages remain specific because they describe
fields the user already supplied. Internal errors remain intentionally generic.

## Browser output protections

Jinja autoescaping remains enabled. Dynamic receipt and participant text is
assigned with DOM text properties rather than interpreted as HTML.

Static response headers include:

- A same-origin Content Security Policy
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- A policy denying other sites permission to frame the page

These reduce script injection, content-type confusion, referrer leakage, and
clickjacking exposure. HTTPS and HSTS are applied by the selected production
ingress rather than by Uvicorn inside the container.

## Same-origin request policy

v0.1 has no public cross-origin API. State-changing requests include a custom
same-origin header and validate the `Origin` header when it is present. CORS is
not enabled.

An ordinary cross-site HTML form cannot set an arbitrary custom header. This
helps prevent another website from silently submitting paid extraction requests
through a visitor's browser.

This control does not stop a script or bot from calling the public endpoint
directly. Public rate limiting is still necessary.

## Size, concurrency, and rate limits solve different problems

| Control | Protects against | Scope |
|---|---|---|
| 10 MiB upload limit | One oversized image request | Application and ingress |
| 256 KiB JSON limit | One oversized calculation/PDF request | Application and ingress |
| Four-call semaphore | Too many simultaneous provider calls in one process | One container |
| Public rate limit | Repeated calls consuming capacity or provider budget | All public traffic |
| Deployment concurrency cap | Too many simultaneous requests per replica/fleet | Hosting platform |

The in-process semaphore is not a distributed rate limiter. If three containers
run, each has its own semaphore. Public deployment must add ingress-level abuse
and cost controls.

## Cache and storage policy

Responses containing receipt, split, extraction, or PDF data use:

```http
Cache-Control: no-store
```

The application does not use cookies, browser storage, analytics, or a service
worker. Static CSS and JavaScript may be versioned and cached because they do
not contain user data.

Temporary framework spooling must be closed in `finally`; the application does
not create its own persistent receipt or PDF files.

## Availability and cost abuse

`POST /api/receipts/extract` is the highest-risk public endpoint because one
request can spend external API quota. Before public launch, deployment must
provide:

- Public request rate limiting
- A maximum request concurrency policy
- Matching ingress and application body-size limits
- OpenAI usage budgets or alerts
- Safe monitoring based on metadata, not receipt contents

The manual workflow should remain healthy when the provider is unavailable or
the API key is not configured.

## Synthetic development data

Only generated receipt images and fictional people belong in:

- Unit and browser fixtures
- Documentation examples
- Screenshots and traces
- Issue reports
- Committed evaluation inputs

Real receipt data should not be copied into a convenient fixture because a Git
history is persistent even after the visible file is later deleted.

## Implications for implementation tasks

Security is included in every milestone rather than postponed entirely:

1. Validate configuration and keep secrets server-side.
2. Add safe request IDs, errors, and allowlisted logging with the first routes.
3. Enforce body and image bounds at the relevant endpoints.
4. Escape browser and PDF output as those adapters are built.
5. Add same-origin policy and static security headers before browser acceptance.
6. Assert `no-store` on sensitive responses.
7. Add tests proving fixture names, amounts, and payloads do not appear in logs.
8. Document ingress rate limiting, HTTPS, HSTS, and concurrency as deployment
   gates before public launch.

## Review checklist

- Is every sensitive value absent from logs and client error details?
- Can a real secret enter source control or a Docker image layer?
- Does the user understand the third-party receipt upload before submitting it?
- Are provider results treated as untrusted input?
- Are all user strings safely rendered in HTML and PDF output?
- Do sensitive responses disable caching?
- Are size, concurrency, and public rate limiting treated as distinct controls?
- Can manual calculation remain available during provider failure?
