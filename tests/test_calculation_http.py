"""HTTP contract tests for stateless manual split calculation."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from checkmate.web.app import (
    JSON_BODY_LIMIT,
    SAME_ORIGIN_HEADER,
    SAME_ORIGIN_VALUE,
    create_app,
)

REQUEST_HEADERS = {SAME_ORIGIN_HEADER: SAME_ORIGIN_VALUE}


@contextmanager
def calculation_client() -> Iterator[TestClient]:
    with TestClient(create_app()) as client:
        yield client


def valid_payload() -> dict[str, object]:
    return {
        "revision": 12,
        "receipt": {
            "restaurantName": "  Synthetic Cafe  ",
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
        "assignments": {"item-1": ["person-2", "person-1"]},
    }


def test_calculation_echoes_revision_and_returns_server_owned_totals() -> None:
    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate", json=valid_payload(), headers=REQUEST_HEADERS
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "access-control-allow-origin" not in response.headers
    assert len(response.headers["x-request-id"]) == 32
    assert response.json() == {
        "revision": 12,
        "normalized": {
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
        },
        "issues": [],
        "itemAllocations": [
            {
                "itemId": "item-1",
                "shares": [
                    {"participantId": "person-1", "amount": "$5.01"},
                    {"participantId": "person-2", "amount": "$5.00"},
                ],
            }
        ],
        "participantTotals": [
            {
                "participantId": "person-1",
                "name": "Maya",
                "itemSubtotal": "$5.01",
                "tax": "$0.50",
                "tip": "$1.00",
                "total": "$6.51",
            },
            {
                "participantId": "person-2",
                "name": "Alex",
                "itemSubtotal": "$5.00",
                "tax": "$0.50",
                "tip": "$1.00",
                "total": "$6.50",
            },
        ],
        "reconciliation": {
            "subtotal": {
                "entered": "$10.01",
                "calculated": "$10.01",
                "difference": "$0.00",
            },
            "total": {
                "entered": "$13.01",
                "calculated": "$13.01",
                "difference": "$0.00",
            },
        },
        "finalized": True,
        "nonZero": True,
    }


def test_user_correctable_domain_errors_return_200_with_issues() -> None:
    payload = valid_payload()
    receipt = payload["receipt"]
    assert isinstance(receipt, dict)
    receipt["subtotal"] = "9.00"

    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate", json=payload, headers=REQUEST_HEADERS
        )

    assert response.status_code == 200
    body = response.json()
    assert body["revision"] == 12
    assert body["finalized"] is False
    assert {issue["code"] for issue in body["issues"]} >= {"subtotal_mismatch"}


@pytest.mark.parametrize(
    ("assigned_ids", "expected_code"),
    [
        (["missing-person"], "unknown_participant_reference"),
        (["person-1", "person-1"], "duplicate_participant_reference"),
    ],
)
def test_reference_errors_remain_visible_through_the_http_contract(
    assigned_ids: list[str], expected_code: str
) -> None:
    payload = valid_payload()
    assignments = payload["assignments"]
    assert isinstance(assignments, dict)
    assignments["item-1"] = assigned_ids

    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate", json=payload, headers=REQUEST_HEADERS
        )

    assert response.status_code == 200
    assert expected_code in {issue["code"] for issue in response.json()["issues"]}
    assert response.json()["finalized"] is False


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        json.dumps({"revision": 1}).encode(),
        json.dumps({**valid_payload(), "unexpected": True}).encode(),
        json.dumps({**valid_payload(), "revision": "12"}).encode(),
    ],
)
def test_structurally_malformed_requests_return_safe_422(body: bytes) -> None:
    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate",
            content=body,
            headers={**REQUEST_HEADERS, "Content-Type": "application/json"},
        )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["error"]["code"] == "invalid_request"
    assert "input" not in response.text
    assert body.decode(errors="ignore") not in response.text


def test_body_larger_than_256_kib_is_rejected_before_schema_parsing() -> None:
    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate",
            content=b"x" * (JSON_BODY_LIMIT + 1),
            headers={**REQUEST_HEADERS, "Content-Type": "application/json"},
        )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"
    assert response.headers["cache-control"] == "no-store"


def test_custom_header_and_matching_origin_are_required() -> None:
    with calculation_client() as client:
        missing_header = client.post("/api/splits/calculate", json=valid_payload())
        wrong_origin = client.post(
            "/api/splits/calculate",
            json=valid_payload(),
            headers={**REQUEST_HEADERS, "Origin": "https://cross-site.invalid"},
        )
        matching_origin = client.post(
            "/api/splits/calculate",
            json=valid_payload(),
            headers={**REQUEST_HEADERS, "Origin": "http://testserver"},
        )

    assert missing_header.status_code == 403
    assert missing_header.json()["error"]["code"] == "same_origin_required"
    assert wrong_origin.status_code == 403
    assert wrong_origin.json()["error"]["code"] == "origin_not_allowed"
    assert matching_origin.status_code == 200


def test_calculation_logging_excludes_request_and_response_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    payload = valid_payload()
    caplog.set_level(logging.INFO, logger="checkmate.http")

    with calculation_client() as client:
        response = client.post(
            "/api/splits/calculate", json=payload, headers=REQUEST_HEADERS
        )

    assert response.status_code == 200
    assert "route=/api/splits/calculate" in caplog.text
    for sensitive_value in ("Synthetic Cafe", "Noodles", "Maya", "10.01", "$6.51"):
        assert sensitive_value not in caplog.text
