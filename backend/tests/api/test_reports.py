"""Tests for GET /api/reports/daily and /api/reports/weekly."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.llm.agents.report_generator import invalidate_cache


@pytest.mark.anyio
async def test_daily_report_returns_200(client):
    invalidate_cache()
    with patch(
        "app.services.llm.agents.generate_report",
        new=AsyncMock(return_value="All quiet for the past 24 hours."),
    ):
        resp = await client.get("/api/reports/daily")

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_type"] == "daily"
    assert "24 hours" in body["content"]


@pytest.mark.anyio
async def test_weekly_report_returns_200(client):
    invalidate_cache()
    with patch(
        "app.services.llm.agents.generate_report",
        new=AsyncMock(return_value="Weekly summary: 12 events recorded."),
    ):
        resp = await client.get("/api/reports/weekly")

    assert resp.status_code == 200
    body = resp.json()
    assert body["report_type"] == "weekly"
    assert "12 events" in body["content"]


@pytest.mark.anyio
async def test_report_response_schema(client):
    invalidate_cache()
    with patch(
        "app.services.llm.agents.generate_report",
        new=AsyncMock(return_value="Report text."),
    ):
        resp = await client.get("/api/reports/daily")

    body = resp.json()
    assert set(body.keys()) == {"report_type", "content"}
