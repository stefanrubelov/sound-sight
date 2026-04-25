"""Fixtures for MCP tool tests: patches AsyncSessionLocal to use the test DB."""

from contextlib import asynccontextmanager

import pytest


@pytest.fixture
def patched_db(db_session, monkeypatch):
    """Patch app.mcp.server.AsyncSessionLocal to yield the test DB session."""

    class _Factory:
        def __call__(self):
            return self._ctx()

        @asynccontextmanager
        async def _ctx(self):
            yield db_session

    monkeypatch.setattr("app.mcp.server.AsyncSessionLocal", _Factory())
