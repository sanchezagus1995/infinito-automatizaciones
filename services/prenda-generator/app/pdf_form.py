from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from pathlib import Path
from typing import Any

from num2words import num2words
from pypdf import PdfReader, PdfWriter


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "galicia" / "galicia_form.pdf"


def _upper(value: Any) -> str:
    return str(value or "").strip().upper()


def _digits(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return re.sub(r"\D", "", str(value))


def _cuil(value: Any) -> str:
    digits = _digits(value)
    return f"{digits[:2]}-{digits[2:10]}-{digits[10:]}" if len(digits) == 11 else digits


def _decimal(value: Any) -> Decimal:
    text = str(value or "0").replace("$", "").replace("ARS", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("El monto bruto no tiene un formato válido") from exc


def money(value: Any) -> str:
    amount = _decimal(value).quantize(Decimal("0.01"))
    integer, cents = f"{amount:.2f}".split(".")
    grouped = f"{int(integer):,}".replace(",", ".")
    return f"${grouped},{cents}"


def money_words(value: Any) -> str:
    amount = _decimal(value).quantize(Decimal("0.01"))
    integer = int(amount)
    cents = int((amount - integer) * 100)
    words = num2words(integer, lang="es").replace("uno mil", "un mil")
    return f"{words} CON {cents:02d}/100".upper()


def _date_parts(value: Any) -> tuple[str, str, str]:
    raw = str(value or "")[:10]
    if not raw:
        return "", "", ""
    try:
        parsed = date.fromisoformat(raw)
    except ValueError:
        parts = re.split(r"[/.-]", raw)
        if len(parts) != 3:
            return "", "", ""
        parsed = date(int(parts[2]), int(parts[1]), int(parts[0]))
    return f"{parsed.day:02d}", f"{parsed.month:02d}", f"{parsed.year % 100:02d}"


def _age(birth: Any, armed: Any) -> str:
    bd, bm, by = _date_parts(birth)
    ad, am, ay = _date_parts(armed)
    if not all((bd, bm, by, ad, am, ay)):
        return ""
    birth_year = int(str(birth)[:4]) if re.match(r"\d{4}-", str(birth)) else int(str(birth)[-4:])
    armed_year = int(str(armed)[:4]) if re.match(r"\d{4}-", str(armed)) else int(str(armed)[-4:])
    return str(armed_year - birth_year - ((int(am), int(ad)) < (int(bm), int(bd))))


def values_from_form(form: dict[str, Any]) -> dict[str, Any]:
    armed = _date_parts(form.get("fecha_armado"))
    birth = _date_parts(form.get("fecha_nacimiento"))
    due = _date_parts(form.get("fecha_vencimiento"))
    nationality = _upper(form.get("nacionalidad"))
    civil = _upper(form.get("estado_civil"))
    is_uva = "UVA" in _upper(form.get("tasa"))
    bruto = form.get("bruto")
    return {
        "dominio": _upper(form.get("dominio")),
        "monto de prenda": money(bruto),
        "nombre titular": _upper(form.get("nombre")),
        "TNA": str(form.get("tna") or ""),
        "TNA / 12": str((_decimal(form.get("tna")) / 12).quantize(Decimal("0.0001"))),
        "cuil": _cuil(form.get("cuil")),
        "profesion": _upper(form.get("profesion")),
        "calle": _upper(form.get("calle")),
        "mail": _upper(form.get("email")),
        "monto de prenda en letras": money_words(bruto),
        "nro calle": _upper(form.get("numero_calle")),
        "codigo postal": _upper(form.get("codigo_postal")),
        "localidad": _upper(form.get("localidad")),
        "partido": _upper(form.get("partido")),
        "provincia": _upper(form.get("provincia")),
        "marca vehiculo": _upper(form.get("marca")),
        "plazo": str(form.get("plazo") or ""),
        "tipo": _upper(form.get("tipo_vehiculo")),
        "modelo": _upper(form.get("modelo")),
        "mca motor": _upper(form.get("marca_motor")),
        "nro motor": _upper(form.get("numero_motor")),
        "mca chasis": _upper(form.get("marca_chasis")),
        "nro chasis": _upper(form.get("numero_chasis")),
        "modelo año": str(form.get("anio") or ""),
        "estado civil": civil,
        "nacionalidad": nationality,
        "edad": _age(form.get("fecha_nacimiento"), form.get("fecha_armado")),
        "dni": _digits(form.get("dni")),
        "ARG": "/Yes" if nationality in {"ARGENTINO", "ARGENTINA"} else "/Off",
        "EXT": "/Off" if nationality in {"ARGENTINO", "ARGENTINA"} else "/Yes",
        "monto uva": money(bruto) if is_uva else "",
        "titular casado": _upper(form.get("nombre")) if civil == "CASADO" else "",
        "nombre conyuge": _upper(form.get("nombre_conyuge")) if civil == "CASADO" else "",
        "domicilio conyuge": _upper(form.get("domicilio_conyuge")) if civil == "CASADO" else "",
        "monto casado": money(bruto) if civil == "CASADO" else "",
        "usado/0km": _upper(form.get("condicion")),
        "tipo de uso": _upper(form.get("tipo_uso")),
        "dia armado": armed[0], "mes armado": armed[1], "año armado": armed[2],
        "soltero 03": "/Yes" if civil == "SOLTERO" else "/Off",
        "casado 03": "/Yes" if civil == "CASADO" else "/Off",
        "div 03": "/Yes" if civil == "DIVORCIADO" else "/Off",
        "dia nac": birth[0], "mes nac": birth[1], "año nac": birth[2],
        "apellido y nombre": _upper(form.get("nombre")),
        "dia vto": due[0], "mes vto": due[1], "año vto": due[2],
    }


def fill_galicia(values: dict[str, Any]) -> bytes:
    reader = PdfReader(TEMPLATE)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    available = writer.get_fields() or {}
    missing = set(values) - set(available)
    if missing:
        raise ValueError(f"Faltan campos en la plantilla Galicia: {sorted(missing)}")
    writer.update_page_form_field_values(None, values, auto_regenerate=False)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
