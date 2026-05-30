"""Health endpoint tests."""

from __future__ import annotations


def test_health_is_ok(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    # the request-id middleware should stamp a response header
    assert "X-Request-ID" in res.headers


def test_ready_checks_db(client, db_required):
    res = client.get("/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"
