"""Smoke-test the loopback Compose ingress with synthetic configuration."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Mapping

CANONICAL_HOST = "checkmate.rishabhtamhane.com"


def _available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _request(
    port: int,
    path: str,
    *,
    method: str = "GET",
    headers: Mapping[str, str] | None = None,
    body: bytes | None = None,
) -> tuple[int, Mapping[str, str], bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    request_headers = {"Host": CANONICAL_HOST, **(headers or {})}
    try:
        connection.request(method, path, body=body, headers=request_headers)
        response = connection.getresponse()
        normalized_headers = {
            name.casefold(): value for name, value in response.getheaders()
        }
        return response.status, normalized_headers, response.read()
    finally:
        connection.close()


def _valid_payload() -> bytes:
    return json.dumps(
        {
            "revision": 1,
            "receipt": {
                "restaurantName": "Synthetic Cafe",
                "date": "2026-08-16",
                "items": [
                    {
                        "id": "item-1",
                        "name": "Noodles",
                        "quantity": "1",
                        "lineTotal": "10.00",
                    }
                ],
                "subtotal": "10.00",
                "tax": "1.00",
                "tip": "2.00",
                "total": "13.00",
            },
            "participants": [{"id": "person-1", "name": "Maya"}],
            "assignments": {"item-1": ["person-1"]},
        }
    ).encode()


def _wait_until_ready(port: int) -> None:
    deadline = time.monotonic() + 60
    while True:
        try:
            status, _, body = _request(port, "/health")
            if status == 200 and json.loads(body)["status"] == "ok":
                return
        except ConnectionError, TimeoutError, http.client.HTTPException:
            pass
        if time.monotonic() >= deadline:
            raise AssertionError("Compose ingress did not become healthy.")
        time.sleep(0.25)


def main() -> None:
    """Run the complete local hosting-stack contract."""
    image = sys.argv[1] if len(sys.argv) > 1 else "checkmate:hosting-smoke"
    port = _available_port()
    project = f"checkmate-hosting-smoke-{os.getpid()}"
    environment = {
        **os.environ,
        "CHECKMATE_IMAGE": image,
        "CHECKMATE_INGRESS_PORT": str(port),
        "OPENAI_API_KEY": "synthetic-not-a-real-key",
    }
    compose = ["docker", "compose", "--project-name", project]

    rendered = subprocess.run(
        [*compose, "config", "--format", "json"],
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    ).stdout
    config = json.loads(rendered)
    app = config["services"]["app"]
    ingress = config["services"]["ingress"]
    assert app["platform"] == "linux/amd64"
    assert app["read_only"] is True
    assert app.get("ports", []) == []
    assert app["environment"]["PUBLIC_ORIGIN"] == f"https://{CANONICAL_HOST}"
    assert app["environment"]["REQUEST_CONCURRENCY_LIMIT"] == "32"
    assert ingress["read_only"] is True
    assert ingress["ports"] == [
        {
            "mode": "ingress",
            "target": 8080,
            "published": str(port),
            "protocol": "tcp",
            "host_ip": "127.0.0.1",
        }
    ]
    assert "synthetic-not-a-real-key" not in ingress.get("environment", {}).values()

    try:
        subprocess.run(
            [*compose, "up", "--detach", "--no-build", "--wait"],
            check=True,
            env=environment,
        )
        _wait_until_ready(port)

        health_status, _, health_body = _request(port, "/health")
        assert health_status == 200
        assert json.loads(health_body)["status"] == "ok"

        unknown_status, _, _ = _request(
            port, "/", headers={"Host": "unknown.example.test"}
        )
        assert unknown_status == 421

        page_status, page_headers, page_body = _request(port, "/")
        assert page_status == 200
        assert page_headers["x-frame-options"] == "DENY"
        assert b"Checkmate" in page_body
        assert b'href="/static/checkmate.v1.css"' in page_body
        assert b'src="/static/checkmate.v1.js"' in page_body
        assert b"http://checkmate.rishabhtamhane.com" not in page_body

        asset_status, _, asset_body = _request(port, "/static/checkmate.v1.css")
        assert asset_status == 200
        assert asset_body

        payload = _valid_payload()
        calculation_status, calculation_headers, calculation_body = _request(
            port,
            "/api/splits/calculate",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Origin": f"https://{CANONICAL_HOST}",
                "X-Checkmate-Request": "1",
            },
            body=payload,
        )
        assert calculation_status == 200
        assert calculation_headers["cache-control"] == "no-store"
        assert json.loads(calculation_body)["finalized"] is True

        oversized_status, _, _ = _request(
            port,
            "/api/splits/calculate",
            method="POST",
            headers={"Content-Type": "application/json"},
            body=b"x" * (256 * 1024 + 1),
        )
        assert oversized_status == 413

        subprocess.run([*compose, "restart", "app"], check=True, env=environment)
        _wait_until_ready(port)
    finally:
        subprocess.run(
            [*compose, "down", "--volumes", "--remove-orphans"],
            check=False,
            env=environment,
        )

    print("hosting_stack_smoke=passed loopback_only=true origin=https")


if __name__ == "__main__":
    main()
