from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
import math
import re
from typing import Any

from num2words import num2words
from reportlab.lib.colors import black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .galicia_layout import (
    MARK_PLACEMENTS,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    STATIC_TEXT,
    TEXT_PLACEMENTS,
)


MAX_FONT_SIZE = 10.0
MIN_FONT_SIZE = 8.0
MIN_HORIZONTAL_SCALE = 75.0
FIELD_HORIZONTAL_PADDING = 4.0


def _fit_text_style(text: str, width: float) -> tuple[float, float]:
    """Balance font size and horizontal scale for one vector text item."""
    if not text:
        return MAX_FONT_SIZE, 100.0
    available_width = width - FIELD_HORIZONTAL_PADDING
    width_at_one_point = stringWidth(text, "Helvetica", 1)
    if available_width <= 0 or width_at_one_point <= 0:
        return MAX_FONT_SIZE, 100.0

    natural_width = width_at_one_point * MAX_FONT_SIZE
    if natural_width <= available_width:
        return MAX_FONT_SIZE, 100.0

    scale_at_maximum = math.floor((available_width / natural_width) * 1000) / 10
    if scale_at_maximum >= MIN_HORIZONTAL_SCALE:
        return MAX_FONT_SIZE, scale_at_maximum

    fitted_size = math.floor(
        (
            available_width
            / (width_at_one_point * MIN_HORIZONTAL_SCALE / 100)
        )
        * 10
    ) / 10
    size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, fitted_size))
    scale = math.floor((available_width / (width_at_one_point * size)) * 1000) / 10
    return size, min(100.0, scale)


def _draw_text(canvas: Canvas, value: Any, rect: tuple[float, ...]) -> None:
    """Draw a value as regular PDF text, matching the old field appearance."""
    text = str(value or "")
    if not text or text.startswith("/"):
        return
    x1, _, x2, y2 = rect
    size, horizontal_scale = _fit_text_style(text, x2 - x1)

    text_object = canvas.beginText()
    text_object.setTextOrigin(x1 + 2, y2 - size - 1)
    text_object.setFont("Helvetica", size)
    text_object.setHorizScale(horizontal_scale)
    text_object.textOut(text)
    canvas.setFillColor(black)
    canvas.drawText(text_object)


def _draw_mark(canvas: Canvas, rect: tuple[float, ...]) -> None:
    """Draw a vector check mark at the former checkbox position."""
    x1, y1, x2, y2 = rect
    height = y2 - y1
    size = 2.4 if height < 13 else 3.2
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    canvas.setStrokeColor(black)
    canvas.setLineWidth(0.9)
    canvas.line(center_x - size, center_y, center_x - size * 0.35, center_y - size * 0.65)
    canvas.line(center_x - size * 0.35, center_y - size * 0.65, center_x + size, center_y + size * 0.8)


def _draw_static_text(
    canvas: Canvas,
    text: str,
    rect: tuple[float, ...],
    size: float,
    bold: bool,
) -> None:
    """Draw fixed Galicia/registry data formerly stored as PDF annotations."""
    x1, y1, _, _ = rect
    canvas.setFillColor(black)
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    # Acrobat's old FreeText appearances used this baseline proportion.
    canvas.drawString(x1, y1 + size * 0.211, text.replace("˚", "°"))


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
        raise ValueError("El monto no tiene un formato válido") from exc


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
        "TNA / 12": str((_decimal(form.get("tna")) / 12).quantize(Decimal("0.01"))),
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
        "dia armado": armed[0],
        "mes armado": armed[1],
        "año armado": armed[2],
        "soltero 03": "/Yes" if civil == "SOLTERO" else "/Off",
        "casado 03": "/Yes" if civil == "CASADO" else "/Off",
        "div 03": "/Yes" if civil == "DIVORCIADO" else "/Off",
        "dia nac": birth[0],
        "mes nac": birth[1],
        "año nac": birth[2],
        "apellido y nombre": _upper(form.get("nombre")),
        "dia vto": due[0],
        "mes vto": due[1],
        "año vto": due[2],
    }


def fill_galicia(values: dict[str, Any]) -> bytes:
    """Create the five-page Galicia packet as editable vector PDF text."""
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)

    for page_number in range(1, 6):
        for item_page, text, rect, size, bold in STATIC_TEXT:
            if item_page == page_number:
                _draw_static_text(canvas, text, rect, size, bold)
        for item_page, name, rect in TEXT_PLACEMENTS:
            if item_page == page_number:
                _draw_text(canvas, values.get(name), rect)
        for item_page, name, rect in MARK_PLACEMENTS:
            if item_page == page_number and values.get(name) == "/Yes":
                _draw_mark(canvas, rect)
        canvas.showPage()

    canvas.save()
    return stream.getvalue()
