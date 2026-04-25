"""Tests for POST /api/devices/register and GET /api/devices."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# POST /api/devices/register — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_device_returns_id(client):
    resp = await client.post(
        "/api/devices/register",
        json={"name": "Kitchen Sensor", "room": "kitchen"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["device_id"] > 0
    assert body["name"] == "Kitchen Sensor"
    assert body["room"] == "kitchen"


@pytest.mark.anyio
async def test_register_multiple_devices(client):
    r1 = await client.post(
        "/api/devices/register",
        json={"name": "Sensor A", "room": "bedroom"},
    )
    r2 = await client.post(
        "/api/devices/register",
        json={"name": "Sensor B", "room": "hallway"},
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["device_id"] != r2.json()["device_id"]


# ---------------------------------------------------------------------------
# POST /api/devices/register — sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_register_device_missing_name_returns_422(client):
    resp = await client.post("/api/devices/register", json={"room": "kitchen"})
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_register_device_missing_room_returns_422(client):
    resp = await client.post("/api/devices/register", json={"name": "Sensor"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/devices — happy path
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_devices_empty(client):
    resp = await client.get("/api/devices")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.anyio
async def test_list_devices_after_register(client):
    await client.post(
        "/api/devices/register",
        json={"name": "Garden Sensor", "room": "garden"},
    )
    resp = await client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(d["name"] == "Garden Sensor" for d in data)


# ---------------------------------------------------------------------------
# GET /api/devices/{id} — happy and sad paths
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_get_device_by_id(client):
    reg = await client.post(
        "/api/devices/register",
        json={"name": "Living Room Sensor", "room": "living room"},
    )
    device_id = reg.json()["device_id"]
    resp = await client.get(f"/api/devices/{device_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Living Room Sensor"


@pytest.mark.anyio
async def test_get_device_not_found(client):
    resp = await client.get("/api/devices/99999")
    assert resp.status_code == 404
