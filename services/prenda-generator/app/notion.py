from __future__ import annotations

import os
from typing import Any

import httpx


class NotionError(RuntimeError):
    pass


def _text(items: list[dict[str, Any]] | None) -> str:
    return "".join(item.get("plain_text", "") for item in (items or [])).strip()


def property_value(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    kind = prop.get("type")
    if kind in {"title", "rich_text"}:
        return _text(prop.get(kind))
    if kind == "number":
        return prop.get("number")
    if kind in {"select", "status"}:
        selected = prop.get(kind)
        return selected.get("name") if selected else None
    if kind == "multi_select":
        return [item.get("name") for item in prop.get(kind, []) if item.get("name")]
    if kind == "date":
        value = prop.get("date")
        return value.get("start") if value else None
    if kind == "formula":
        value = prop.get("formula") or {}
        return value.get(value.get("type"))
    return prop.get(kind)


async def fetch_page(page_id: str) -> dict[str, Any]:
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise NotionError("Falta configurar NOTION_TOKEN")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"https://api.notion.com/v1/pages/{page_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": "2022-06-28",
            },
        )
    if response.status_code == 404:
        raise NotionError("La operación no existe o la integración no tiene acceso")
    response.raise_for_status()
    return response.json()


async def set_page_url(*, page_id: str, property_name: str, url: str) -> None:
    token = os.getenv("NOTION_TOKEN")
    if not token:
        raise NotionError("Falta configurar NOTION_TOKEN")
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
    if response.status_code == 404:
        raise NotionError("La operación no existe o la integración no tiene acceso")
    if response.is_error:
        try:
            message = response.json().get("message")
        except ValueError:
            message = None
        raise NotionError(message or "No se pudo guardar el enlace del formulario en Notion")


def operation_from_page(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties") or {}
    get = lambda name: property_value(props.get(name))
    title = next(
        (property_value(prop) for prop in props.values() if prop.get("type") == "title"),
        None,
    )
    banks = get("Banco") or []
    if isinstance(banks, str):
        banks = [banks]
    return {
        "page_id": page["id"],
        "nombre": title or get("Nombre y apellido") or "",
        "dni": get("DNI") or "",
        "cuil": get("CUIL CUIT") or "",
        "fecha_nacimiento": get("Fecha de nacimiento") or "",
        "estado_civil": get("Estado civil") or "",
        "domicilio": get("Domicilio titular") or "",
        "localidad": get("Localidad titular") or "",
        "provincia": get("Provincia titular") or "",
        "email": get("Correo Electronico") or "",
        "dominio": get("Dominio") or "",
        "anio": get("Año") or "",
        "marca": get("Marca vehículo") or "",
        "modelo": get("Versión vehículo") or "",
        "condicion": get("0km / Usado") or "",
        "bruto": get("Bruto") or "",
        "plazo": get("Plazo") or "",
        "tna": get("TNA") or "",
        "tasa": get("tasa") or get("Tasa") or "",
        "fecha_armado": get("Fecha armada") or "",
        "fecha_vencimiento": get("Vencimiento 1er cuota") or "",
        "bancos": banks,
    }
