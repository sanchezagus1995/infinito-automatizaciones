from __future__ import annotations

from datetime import date
from typing import Any


class PayloadError(ValueError):
    pass


def _plain_text(items: list[dict[str, Any]] | None) -> str:
    return "".join((item.get("plain_text") or item.get("text", {}).get("content") or "") for item in (items or [])).strip()


def property_value(prop: dict[str, Any] | None) -> Any:
    if not prop:
        return None
    kind = prop.get("type")
    if kind in {"title", "rich_text"}:
        return _plain_text(prop.get(kind))
    if kind == "number":
        return prop.get("number")
    if kind in {"select", "status"}:
        selected = prop.get(kind)
        return selected.get("name") if selected else None
    if kind == "multi_select":
        return [item.get("name", "") for item in prop.get("multi_select", []) if item.get("name")]
    if kind == "date":
        value = prop.get("date")
        return value.get("start") if value else None
    if kind == "formula":
        formula = prop.get("formula") or {}
        return formula.get(formula.get("type"))
    return prop.get(kind)


def _money(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):,.0f}".replace(",", ".")


def _date_ar(value: Any) -> str:
    if not value:
        return "—"
    try:
        return date.fromisoformat(str(value)[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return str(value)


def operation_from_webhook(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        if len(payload) != 1:
            raise PayloadError("Se esperaba un único bundle del webhook")
        payload = payload[0]
    data = payload.get("data") if isinstance(payload, dict) else None
    if not data or not data.get("id") or not isinstance(data.get("properties"), dict):
        raise PayloadError("El payload no contiene data.id y data.properties")

    props = data["properties"]
    get = lambda name: property_value(props.get(name))
    banks = get("Banco") or []
    if isinstance(banks, str):
        banks = [banks]

    operation = {
        "page_id": data["id"],
        "cliente_nombre": get("Nombre y apellido") or "—",
        "dni_cliente": get("DNI") or "—",
        "domicilio_cliente": get("Domicilio titular") or "—",
        "localidad_cliente": get("Localidad titular") or "—",
        "co_nombre": get("Nombre cotitular / conyuge") or "—",
        "co_dni": get("DNI cotitular / conyuge") or "—",
        "co_domicilio": get("Domicilio cotitular / conyuge") or "—",
        "localidad_co": get("Localidad cotitular / conyuge") or "—",
        "bancos": banks,
        "banco": " / ".join(banks) or "—",
        "neto": _money(get("Neto")),
        "bruto": _money(get("Bruto")),
        "plazo": get("Plazo") or "—",
        "primer_cuota": _money(get("1ra Cuota")),
        "promedio_cuota": _money(get("Cuota promedio")),
        "ultima_cuota": _money(get("Última cuota")),
        "tna": get("TNA") if get("TNA") is not None else "—",
        "tasa": get("Tasa") or "—",
        "fecha_armado": _date_ar(get("Fecha armada")),
        "vencimiento_cuota": _date_ar(get("Vencimiento 1er cuota")),
        "nro_op": get("Nro op") or "—",
        "texto_agencia": get("nombre agencia") or "—",
        "marca_vehiculo": get("Marca vehículo") or "—",
        "modelo_vehiculo": get("Versión vehículo") or "—",
        "año_vehiculo": get("Año") or "—",
        "aseguradora": get("Compañia Seguro") or "—",
        "cobertura": get("Tipo de cobertura") or "—",
        "monto_seguro": _money(get("Monto seguro")),
        "sellado": get("Sellado") or "—",
        "monto_sellado": _money(get("Monto sellado")),
    }
    return operation
