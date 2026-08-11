import os

import pytest
from fastapi import HTTPException

from app.main import _authorize_session, _page_id_from_webhook, _session_token


def test_page_id_from_notion_webhook():
    assert _page_id_from_webhook({"data": {"id": "page-123", "properties": {}}}) == "page-123"


def test_signed_session_is_valid_only_for_its_page(monkeypatch):
    monkeypatch.setenv("FORM_TOKEN", "test-secret")
    token = _session_token("page-123", now=1_000)
    _authorize_session(token, "page-123", now=1_001)

    with pytest.raises(HTTPException) as error:
        _authorize_session(token, "another-page", now=1_001)
    assert error.value.status_code == 401


def test_signed_session_expires(monkeypatch):
    monkeypatch.setenv("FORM_TOKEN", "test-secret")
    monkeypatch.setenv("FORM_LINK_TTL_SECONDS", "60")
    token = _session_token("page-123", now=1_000)

    with pytest.raises(HTTPException) as error:
        _authorize_session(token, "page-123", now=1_061)
    assert error.value.status_code == 401
