"""Headless Chromium evidence for the manual splitting workflow."""

from __future__ import annotations

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from io import BytesIO

import pytest
import uvicorn
from PIL import Image
from playwright.sync_api import Page, expect

from checkmate.adapters.receipt_parser import FakeReceiptParser
from checkmate.web.app import create_app


def available_port() -> int:
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        return int(candidate.getsockname()[1])


@pytest.fixture(scope="module")
def live_server_url() -> Iterator[str]:
    """Run the real ASGI application for browser-only integration tests."""
    port = available_port()
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(),
            host="127.0.0.1",
            port=port,
            log_level="critical",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while True:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    break
        except urllib.error.URLError, TimeoutError:
            if time.monotonic() >= deadline:
                raise AssertionError("Browser test server did not start.") from None
            time.sleep(0.05)

    yield url
    server.should_exit = True
    thread.join(timeout=5)
    assert not thread.is_alive()


@pytest.fixture(scope="module")
def extraction_server_url() -> Iterator[str]:
    """Run the application with its deterministic receipt parser enabled."""
    port = available_port()
    url = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(receipt_parser=FakeReceiptParser()),
            host="127.0.0.1",
            port=port,
            log_level="critical",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while True:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=1) as response:
                if response.status == 200:
                    break
        except urllib.error.URLError, TimeoutError:
            if time.monotonic() >= deadline:
                raise AssertionError(
                    "Extraction browser server did not start."
                ) from None
            time.sleep(0.05)

    yield url
    server.should_exit = True
    thread.join(timeout=5)
    assert not thread.is_alive()


def synthetic_receipt_upload() -> dict[str, str | bytes]:
    """Return a generated PNG in Playwright's in-memory upload shape."""
    image = Image.new("RGB", (120, 240), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    return {
        "name": "synthetic-receipt.png",
        "mimeType": "image/png",
        "buffer": output.getvalue(),
    }


def open_application(page: Page, live_server_url: str) -> None:
    page.set_default_timeout(5_000)
    page.goto(live_server_url)
    expect(page.get_by_role("heading", name="Items and assignments")).to_be_visible()
    expect(page.locator("[data-calculation-status]")).not_to_have_text("Pending")


def complete_manual_split(page: Page, live_server_url: str) -> None:
    open_application(page, live_server_url)
    page.get_by_role("button", name="Add participant").click()
    page.get_by_label("Participant 1 name").fill("Maya")
    page.get_by_role("button", name="Add participant").click()
    page.get_by_label("Participant 2 name").fill("Alex")

    page.get_by_label("Item 1 name").fill("Synthetic noodles")
    page.get_by_label("Item 1 quantity").fill("2")
    page.get_by_label("Item 1 line total").fill("10.01")
    page.get_by_label("Subtotal").fill("10.01")
    page.get_by_label("Tax").fill("1.00")
    page.get_by_label("Tip").fill("2.00")
    page.get_by_label("Total", exact=True).fill("13.01")
    page.get_by_label("Share item 1 with Maya").check()
    page.get_by_label("Share item 1 with Alex").check()
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")


def test_manual_entry_calculates_exact_totals_and_enables_export_state(
    page: Page, live_server_url: str
) -> None:
    complete_manual_split(page, live_server_url)

    summary = page.locator("[data-summary-body]")
    expect(summary).to_contain_text("Maya")
    expect(summary).to_contain_text("$6.51")
    expect(summary).to_contain_text("Alex")
    expect(summary).to_contain_text("$6.50")
    expect(page.locator("[data-calculated-subtotal]")).to_have_text("$10.01")
    expect(page.locator("[data-calculated-total]")).to_have_text("$13.01")
    expect(page.locator("[data-error-summary]")).to_be_hidden()
    expect(page.get_by_role("button", name="Generate PDF")).to_be_enabled()


def test_text_edits_are_debounced_and_checkboxes_calculate_immediately(
    page: Page, live_server_url: str
) -> None:
    open_application(page, live_server_url)
    calculation_requests: list[float] = []

    def record_request(request: object) -> None:
        url = getattr(request, "url", "")
        if str(url).endswith("/api/splits/calculate"):
            calculation_requests.append(time.monotonic())

    page.on("request", record_request)
    page.get_by_label("Item 1 name").fill("Synthetic salad")
    page.wait_for_timeout(150)
    assert calculation_requests == []
    page.wait_for_timeout(250)
    assert len(calculation_requests) == 1

    page.get_by_role("button", name="Add participant").click()
    expect(page.locator("[data-calculation-status]")).not_to_have_text("Pending")
    page.get_by_label("Participant 1 name").fill("Maya")
    page.wait_for_timeout(350)
    calculation_requests.clear()
    with page.expect_request("**/api/splits/calculate"):
        page.get_by_label("Share item 1 with Maya").check()
    assert len(calculation_requests) == 1


def test_record_removal_cleans_dangling_assignments(
    page: Page, live_server_url: str
) -> None:
    open_application(page, live_server_url)
    payloads: list[dict[str, object]] = []

    def capture_payload(request: object) -> None:
        url = getattr(request, "url", "")
        post_data = getattr(request, "post_data", None)
        if str(url).endswith("/api/splits/calculate") and isinstance(post_data, str):
            payloads.append(json.loads(post_data))

    page.on("request", capture_payload)
    page.get_by_role("button", name="Add participant").click()
    page.get_by_label("Participant 1 name").fill("Maya")
    page.wait_for_timeout(350)
    participant_id = payloads[-1]["participants"][0]["id"]
    page.get_by_label("Share item 1 with Maya").check()
    page.get_by_role("button", name="Remove participant 1").click()
    page.wait_for_timeout(100)
    latest = payloads[-1]
    assert latest["participants"] == []
    assert all(
        participant_id not in assigned for assigned in latest["assignments"].values()
    )

    item_id = latest["receipt"]["items"][0]["id"]
    page.get_by_role("button", name="Remove item 1").click()
    page.wait_for_timeout(100)
    latest = payloads[-1]
    assert latest["receipt"]["items"] == []
    assert item_id not in latest["assignments"]


def test_mismatch_errors_are_linked_and_keyboard_assignment_works(
    page: Page, live_server_url: str
) -> None:
    complete_manual_split(page, live_server_url)
    subtotal = page.get_by_label("Subtotal")
    subtotal.fill("9.00")
    expect(page.locator("[data-calculation-status]")).to_have_text("Needs attention")
    summary = page.locator("[data-error-summary]")
    expect(summary).to_be_visible()
    summary.get_by_role("link", name="Entered subtotal must match").click()
    expect(subtotal).to_be_focused()
    expect(subtotal).to_have_attribute("aria-describedby", "field-issue-0")

    subtotal.fill("10.01")
    expect(summary).to_be_hidden()
    expect(page.locator("[data-calculation-status]")).to_have_text("Pending")
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")
    maya_assignment = page.get_by_label("Share item 1 with Maya")
    maya_assignment.focus()
    page.keyboard.press("Space")
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")
    page.keyboard.press("Space")
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")


def test_network_retry_stale_responses_and_narrow_table_behavior(
    page: Page, live_server_url: str
) -> None:
    page.route("**/api/splits/calculate", lambda route: route.abort())
    page.goto(live_server_url)
    expect(page.locator("[data-calculation-status]")).to_have_text("Unavailable")
    expect(page.get_by_label("Item 1 name")).to_be_visible()
    page.unroute("**/api/splits/calculate")
    page.get_by_role("button", name="Retry calculation").click()
    expect(page.locator("[data-calculation-status]")).to_have_text("Needs attention")

    page.set_viewport_size({"width": 390, "height": 844})
    for _ in range(8):
        page.get_by_role("button", name="Add participant").click()
    scroll_metrics = page.locator("[data-table-scroll]").evaluate(
        "element => ({clientWidth: element.clientWidth, "
        "scrollWidth: element.scrollWidth})"
    )
    assert scroll_metrics["scrollWidth"] > scroll_metrics["clientWidth"]
    checkbox_box = page.locator('input[type="checkbox"]').first.bounding_box()
    assert checkbox_box is not None
    assert checkbox_box["height"] >= 44
    receipt_box = page.locator(".receipt-panel").bounding_box()
    summary_box = page.locator(".summary-panel").bounding_box()
    assert receipt_box is not None and summary_box is not None
    assert summary_box["y"] > receipt_box["y"]


def test_older_calculation_response_cannot_replace_a_newer_revision(
    page: Page, live_server_url: str
) -> None:
    page.add_init_script(
        """
        const originalFetch = window.fetch.bind(window);
        window.__delayNextCalculation = false;
        window.__delayedCalculationStarted = false;
        window.fetch = async (...args) => {
          const response = await originalFetch(...args);
          if (window.__delayNextCalculation) {
            window.__delayNextCalculation = false;
            window.__delayedCalculationStarted = true;
            await new Promise((resolve) => setTimeout(resolve, 700));
          }
          return response;
        };
        """
    )
    complete_manual_split(page, live_server_url)
    page.evaluate("window.__delayNextCalculation = true")
    page.get_by_label("Subtotal").fill("9.00")
    page.wait_for_timeout(400)
    assert page.evaluate("window.__delayedCalculationStarted") is True
    page.get_by_label("Subtotal").fill("10.01")
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")
    page.wait_for_timeout(500)
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")
    expect(page.locator("[data-error-summary]")).to_be_hidden()


def test_browser_source_uses_no_persistence_or_unsafe_html() -> None:
    source = (
        __import__("pathlib").Path(__file__).parents[1]
        / "src/checkmate/web/static/checkmate.v1.js"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "innerHTML",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "serviceWorker",
    ):
        assert forbidden not in source


def test_successful_extraction_replaces_receipt_and_preserves_participants(
    page: Page, extraction_server_url: str
) -> None:
    open_application(page, extraction_server_url)
    calculation_payloads: list[dict[str, object]] = []

    def capture_calculation(request: object) -> None:
        url = getattr(request, "url", "")
        post_data = getattr(request, "post_data", None)
        if str(url).endswith("/api/splits/calculate") and isinstance(post_data, str):
            calculation_payloads.append(json.loads(post_data))

    page.on("request", capture_calculation)
    page.get_by_role("button", name="Add participant").click()
    page.get_by_label("Participant 1 name").fill("Maya")
    page.get_by_role("button", name="Add participant").click()
    page.get_by_label("Participant 2 name").fill("Alex")
    page.get_by_label("Item 1 name").fill("Old manual item")
    page.get_by_label("Item 1 line total").fill("1.00")
    page.get_by_label("Share item 1 with Maya").check()

    page.locator("[data-upload-file]").set_input_files(synthetic_receipt_upload())
    page.get_by_role("button", name="Extract receipt").click()

    expect(page.locator("[data-upload-status]")).to_contain_text("Extraction complete")
    expect(page.get_by_label("Participant 1 name")).to_have_value("Maya")
    expect(page.get_by_label("Participant 2 name")).to_have_value("Alex")
    expect(page.get_by_label("Item 1 name")).to_have_value("Piza")
    expect(page.get_by_label("Item 2 name")).to_have_value("Salad")
    expect(page.get_by_label("Share item 1 with Maya")).not_to_be_checked()
    expect(page.get_by_label("Share item 2 with Alex")).not_to_be_checked()
    expect(page.locator("[data-extraction-notices]")).to_be_visible()

    page.get_by_label("Item 1 name").fill("Pizza")
    page.wait_for_timeout(350)
    assert calculation_payloads[-1]["receipt"]["items"][0]["name"] == "Pizza"
    page.get_by_label("Share item 1 with Maya").check()
    page.get_by_label("Share item 1 with Alex").check()
    page.get_by_label("Share item 2 with Alex").check()
    expect(page.locator("[data-calculation-status]")).to_have_text("Ready")


def test_extraction_failure_preserves_draft_and_retry_succeeds(
    page: Page, extraction_server_url: str
) -> None:
    open_application(page, extraction_server_url)
    page.get_by_label("Restaurant name").fill("Current Manual Draft")
    page.get_by_label("Item 1 name").fill("Keep this item")
    page.get_by_label("Item 1 line total").fill("4.20")

    page.route(
        "**/api/receipts/extract",
        lambda route: route.fulfill(
            status=502,
            content_type="application/json",
            body=json.dumps(
                {
                    "error": {
                        "code": "receipt_extraction_unavailable",
                        "message": "Retry or enter the receipt manually.",
                        "request_id": "synthetic-request-id",
                    }
                }
            ),
        ),
    )
    page.locator("[data-upload-file]").set_input_files(synthetic_receipt_upload())
    page.get_by_role("button", name="Extract receipt").click()

    expect(page.locator("[data-upload-status]")).to_contain_text(
        "current draft is unchanged"
    )
    expect(page.get_by_label("Restaurant name")).to_have_value("Current Manual Draft")
    expect(page.get_by_label("Item 1 name")).to_have_value("Keep this item")
    expect(page.get_by_role("button", name="Retry extraction")).to_be_visible()

    page.unroute("**/api/receipts/extract")
    page.get_by_role("button", name="Retry extraction").click()
    expect(page.locator("[data-upload-status]")).to_contain_text("Extraction complete")
    expect(page.get_by_label("Item 1 name")).to_have_value("Piza")


def test_no_key_browser_mode_keeps_manual_controls_available(
    page: Page, live_server_url: str
) -> None:
    open_application(page, live_server_url)

    expect(page.locator("[data-upload-file]")).to_be_disabled()
    expect(page.get_by_role("button", name="Extract receipt")).to_be_disabled()
    expect(page.locator("[data-upload-status]")).to_have_text(
        "Continue with manual entry."
    )
    expect(page.get_by_label("Item 1 name")).to_be_editable()
