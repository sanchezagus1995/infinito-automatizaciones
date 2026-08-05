from __future__ import annotations

import json
import os


class ConfigurationError(RuntimeError):
    pass


def notion_property_name() -> str:
    return os.getenv("NOTION_PDF_PROPERTY", "PDF nuevo")


def drive_folder_for(bank: str) -> str:
    raw_mapping = os.getenv("DRIVE_FOLDER_BY_BANK_JSON", "{}")
    try:
        mapping = {str(key).strip().upper(): value for key, value in json.loads(raw_mapping).items()}
    except (json.JSONDecodeError, AttributeError) as exc:
        raise ConfigurationError("DRIVE_FOLDER_BY_BANK_JSON no contiene un objeto JSON válido") from exc

    normalized_bank = bank.strip().upper()
    folder_id = mapping.get(normalized_bank) or os.getenv("DRIVE_DEFAULT_FOLDER_ID")
    if not folder_id:
        raise ConfigurationError(f"No hay una carpeta de Drive configurada para {bank}")
    return str(folder_id)
