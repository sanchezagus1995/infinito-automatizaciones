from __future__ import annotations

import os

import httpx

from .config import ConfigurationError


async def set_pdf_url(*, page_id: str, property_name: str, url: str) -> None:
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise ConfigurationError("Falta configurar NOTION_TOKEN")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.patch(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json={"properties": {property_name: {"url": url}}},
        )
    response.raise_for_status()
