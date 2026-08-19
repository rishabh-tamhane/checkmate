"""Smoke-test an installed Checkmate distribution and its packaged web assets."""

import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

from checkmate import __version__


def find_available_port() -> int:
    """Reserve and release an available loopback port for the smoke process."""
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def get_response(url: str) -> tuple[int, str, str]:
    """Request one local URL and return status, content type, and text."""
    with urllib.request.urlopen(url, timeout=2) as response:
        return (
            response.status,
            response.headers.get_content_type(),
            response.read().decode("utf-8"),
        )


assert __version__ == "0.1.0"

port = find_available_port()
environment = os.environ.copy()
environment.update(
    {
        "HOST": "127.0.0.1",
        "PORT": str(port),
        "LOG_LEVEL": "warning",
    }
)
process = subprocess.Popen(
    ["checkmate-web"],
    env=environment,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

try:
    health_url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + 10
    while True:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise AssertionError(f"checkmate-web exited before startup: {output}")
        try:
            health = get_response(health_url)
            break
        except urllib.error.URLError, TimeoutError:
            if time.monotonic() >= deadline:
                raise AssertionError("checkmate-web did not become healthy") from None
            time.sleep(0.05)

    assert health == (
        200,
        "application/json",
        json.dumps({"status": "ok", "version": "0.1.0"}, separators=(",", ":")),
    )
    page = get_response(f"http://127.0.0.1:{port}/")
    stylesheet = get_response(f"http://127.0.0.1:{port}/static/checkmate.v1.css")
    script = get_response(f"http://127.0.0.1:{port}/static/checkmate.v1.js")
    assert page[0:2] == (200, "text/html")
    assert "checkmate.v1.css" in page[2]
    assert "checkmate.v1.js" in page[2]
    assert stylesheet[0:2] == (200, "text/css")
    assert script[0] == 200
    assert "javascript" in script[1]
finally:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
