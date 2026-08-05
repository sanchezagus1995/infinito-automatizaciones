import pytest

from app.config import ConfigurationError, drive_folder_for


def test_bank_specific_folder_has_priority(monkeypatch):
    monkeypatch.setenv("DRIVE_FOLDER_BY_BANK_JSON", '{"COLUMBIA":"folder-columbia"}')
    monkeypatch.setenv("DRIVE_DEFAULT_FOLDER_ID", "folder-default")
    assert drive_folder_for("Columbia") == "folder-columbia"


def test_default_folder_is_used(monkeypatch):
    monkeypatch.setenv("DRIVE_FOLDER_BY_BANK_JSON", "{}")
    monkeypatch.setenv("DRIVE_DEFAULT_FOLDER_ID", "folder-default")
    assert drive_folder_for("OTRO BANCO") == "folder-default"


def test_missing_folder_fails_explicitly(monkeypatch):
    monkeypatch.setenv("DRIVE_FOLDER_BY_BANK_JSON", "{}")
    monkeypatch.delenv("DRIVE_DEFAULT_FOLDER_ID", raising=False)
    with pytest.raises(ConfigurationError):
        drive_folder_for("COLUMBIA")
