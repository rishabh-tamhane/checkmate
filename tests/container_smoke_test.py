"""Smoke-test one locally loaded Checkmate production container image."""

from __future__ import annotations

import html.parser
import http.client
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping


class _AssetCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attribute_name = "href" if tag == "link" else "src" if tag == "script" else None
        if attribute_name is None:
            return
        for name, value in attrs:
            path = "" if value is None else urllib.parse.urlparse(value).path
            if (
                name == attribute_name
                and value is not None
                and path.startswith("/static/")
            ):
                self.paths.add(path)


def _available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


def _request(
    url: str,
    *,
    payload: Mapping[str, object] | None = None,
) -> tuple[int, Mapping[str, str], bytes]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = (
        {}
        if data is None
        else {
            "Content-Type": "application/json",
            "X-Checkmate-Request": "1",
        }
    )
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        normalized_headers = {
            name.casefold(): value for name, value in response.headers.items()
        }
        return response.status, normalized_headers, response.read()


def _valid_payload() -> dict[str, object]:
    return {
        "revision": 12,
        "receipt": {
            "restaurantName": "Synthetic Cafe",
            "date": "2026-08-16",
            "items": [
                {
                    "id": "item-1",
                    "name": "Noodles",
                    "quantity": "2",
                    "lineTotal": "10.01",
                }
            ],
            "subtotal": "10.01",
            "tax": "1.00",
            "tip": "2.00",
            "total": "13.01",
        },
        "participants": [
            {"id": "person-1", "name": "Maya"},
            {"id": "person-2", "name": "Alex"},
        ],
        "assignments": {"item-1": ["person-1", "person-2"]},
    }


def _assert_image_contract(image: str) -> None:
    metadata = subprocess.run(
        [
            "docker",
            "image",
            "inspect",
            image,
            "--format",
            "{{.Os}}|{{.Architecture}}|{{.Config.User}}|"
            "{{.Config.WorkingDir}}|{{json .Config.Cmd}}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert metadata == 'linux|amd64|10001:10001|/app|["checkmate-web"]'

    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--platform",
            "linux/amd64",
            "--entrypoint",
            "/app/.venv/bin/python",
            image,
            "-c",
            "import os, shutil; from pathlib import Path; "
            "assert os.getuid() == 10001; "
            "assert shutil.which('uv') is None; "
            "assert shutil.which('cc') is None; "
            "assert shutil.which('gcc') is None; "
            "assert all(not Path(path).exists() for path in "
            "('/bin/uv', '/bin/uvx', '/app/tests', '/app/docs', '/app/.git', "
            "'/app/src', '/app/pyproject.toml', '/app/uv.lock', '/app/README.md'))",
        ],
        check=True,
    )


def _wait_until_ready(base_url: str) -> None:
    deadline = time.monotonic() + 20
    while True:
        try:
            status, _, body = _request(f"{base_url}/health")
            assert status == 200
            assert json.loads(body) == {"status": "ok", "version": "0.1.0"}
            return
        except urllib.error.URLError, TimeoutError, http.client.HTTPException:
            if time.monotonic() >= deadline:
                raise AssertionError("Container did not become healthy.") from None
            time.sleep(0.1)


def main() -> None:
    """Run the complete local production-container smoke contract."""
    image = sys.argv[1] if len(sys.argv) > 1 else "checkmate:m5"
    _assert_image_contract(image)
    port = _available_port()
    container_name = f"checkmate-smoke-{os.getpid()}"
    subprocess.run(
        [
            "docker",
            "run",
            "--detach",
            "--rm",
            "--platform",
            "linux/amd64",
            "--name",
            container_name,
            "--read-only",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=16m",
            "--publish",
            f"127.0.0.1:{port}:8000",
            image,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_until_ready(base_url)
        page_status, _, page_body = _request(f"{base_url}/")
        assert page_status == 200
        page_text = page_body.decode("utf-8")
        assert "Continue with manual entry." in page_text
        assert "data-upload-file" in page_text and "disabled" in page_text

        assets = _AssetCollector()
        assets.feed(page_text)
        assert assets.paths == {
            "/static/checkmate.v1.css",
            "/static/checkmate.v1.js",
        }
        for path in assets.paths:
            asset_status, _, asset_body = _request(f"{base_url}{path}")
            assert asset_status == 200
            assert asset_body

        calculation_status, calculation_headers, calculation_body = _request(
            f"{base_url}/api/splits/calculate", payload=_valid_payload()
        )
        assert calculation_status == 200
        assert calculation_headers["cache-control"] == "no-store"
        calculation = json.loads(calculation_body)
        assert calculation["finalized"] is True
        assert [entry["total"] for entry in calculation["participantTotals"]] == [
            "$6.51",
            "$6.50",
        ]

        pdf_status, pdf_headers, pdf_body = _request(
            f"{base_url}/api/splits/pdf", payload=_valid_payload()
        )
        assert pdf_status == 200
        assert pdf_headers["content-type"] == "application/pdf"
        assert pdf_headers["cache-control"] == "no-store"
        assert pdf_headers["content-disposition"] == (
            'attachment; filename="checkmate-split.pdf"'
        )
        assert pdf_body.startswith(b"%PDF-")
    finally:
        stopped_at = time.monotonic()
        subprocess.run(
            ["docker", "stop", "--time", "5", container_name],
            check=True,
            capture_output=True,
            text=True,
        )
        assert time.monotonic() - stopped_at < 8

    print("container_smoke=passed platform=linux/amd64 read_only=true user=10001")


if __name__ == "__main__":
    main()
