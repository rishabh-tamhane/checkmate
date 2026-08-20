# Checkmate macOS Host Operations

This directory contains the non-secret configuration for the initial
owner-operated host. The public architecture and limitations are defined in
`docs/versions/v0.2-hosting/`.

After the local stack is healthy, follow the
[Cloudflare travel launch checklist](CLOUDFLARE.md).

## Prerequisites

- Apple-silicon Mac connected to reliable power and Internet
- Docker Desktop running and configured to start at login
- Verified `checkmate-openai-api-key` item in the current user's macOS Keychain
- Repository checks passing for the current commit

Keep the Mac awake on power. Keep a MacBook lid open unless a powered clamshell
configuration has already been proven. Lock the screen instead of logging out.

## Start or update

From the repository root:

```bash
./deploy/macos/start.sh
```

The helper reads the OpenAI key from Keychain without printing or writing it,
tags the image with the current short Git commit, builds the tested amd64
container, starts both services, and waits for health checks.

## Status and health

```bash
./deploy/macos/status.sh
```

The stack is intentionally available only through the loopback ingress. A
direct request must provide the canonical host:

```bash
curl --fail --silent --show-error \
  --header "Host: checkmate.rishabhtamhane.com" \
  http://127.0.0.1:8080/health
```

## Logs

Application logs contain allowlisted operational metadata only:

```bash
CHECKMATE_IMAGE=unused OPENAI_API_KEY=unused \
  docker compose --project-name checkmate logs --tail 100 app ingress
```

Do not enable shell tracing or paste unreviewed Docker inspection output into a
ticket or chat. Docker administrative metadata includes the container
environment and is inside the Mac owner's trust boundary.

## Restart and stop

Restart both existing containers without re-reading the secret:

```bash
docker restart checkmate-app-1 checkmate-ingress-1
```

Stop the stack:

```bash
./deploy/macos/stop.sh
```

Start it again with `./deploy/macos/start.sh`.

## Recovery order

When the external site is unavailable, check in this order:

1. Confirm the Mac has power, Internet, an active login session, and is awake.
2. Start Docker Desktop and run `./deploy/macos/status.sh`.
3. If a container is unhealthy, review the bounded logs and run
   `docker restart checkmate-app-1 checkmate-ingress-1`.
4. Confirm the loopback health request succeeds.
5. Check the macOS `cloudflared` service and the named tunnel in Cloudflare.
6. Check the published hostname and Cloudflare Access application.

If the local stack is unhealthy, disable the published application route. Do
not bypass Access, remove rate limiting, or expose a direct router port.

## Rollback

List local immutable Checkmate tags:

```bash
docker image ls --filter reference='checkmate:hosting-*'
```

Roll back to a recorded local tag:

```bash
./deploy/macos/rollback.sh checkmate:hosting-<commit>
```

The helper verifies that the immutable local image exists, reads the Keychain
secret without printing it, recreates the application, restarts Nginx so it
resolves the recreated container, and waits for both health checks. DNS,
Access, and the tunnel remain unchanged.
