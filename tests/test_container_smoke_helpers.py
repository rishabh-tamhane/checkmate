from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest


def _load_container_smoke_test() -> ModuleType:
    script_path = Path(__file__).with_name("container_smoke_test.py")
    spec = importlib.util.spec_from_file_location(
        "checkmate_container_smoke_test", script_path
    )
    if spec is None or spec.loader is None:
        raise AssertionError("Could not load the container smoke-test script.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wait_until_ready_retries_connection_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smoke_test = _load_container_smoke_test()
    attempts = 0

    def request(_url: str) -> tuple[int, dict[str, str], bytes]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ConnectionResetError("synthetic startup reset")
        return 200, {}, b'{"status":"ok","version":"0.1.0"}'

    monkeypatch.setattr(smoke_test, "_request", request)
    monkeypatch.setattr(smoke_test.time, "sleep", lambda _seconds: None)

    smoke_test._wait_until_ready("http://127.0.0.1:8000")

    assert attempts == 2
