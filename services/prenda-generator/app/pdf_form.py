from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
import re
from pathlib import Path
from typing import Any

from num2words import num2words
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "galicia" / "galicia_form.pdf"


# The labels are part of the bank form and already sit in the verified physical
# area. These tighter rectangles put their values on four clean baselines while
# reserving the longest spaces for engine, chassis and model identifiers.
VEHICLE_RECTS = {
    "modelo año": (90.4, 707.2, 130.0, 721.6),
    "mca motor": (366.8, 707.2, 448.4, 721.6),
    "nro motor": (498.8, 707.2, 600.4, 721.6),
    "dominio": (120.0, 694.4, 184.0, 708.8),
    "marca vehiculo": (234.8, 694.4, 326.8, 708.8),
    "mca chasis": (390.8, 694.4, 470.4, 708.8),
    "tipo": (100.0, 680.0, 180.0, 694.4),
    "tipo de uso": (218.0, 680.0, 286.0, 694.4),
    "nro chasis": (354.4, 680.0, 510.0, 694.4),
    "usado/0km": (542.0, 680.0, 592.8, 694.4),
    "modelo": (139.2, 665.6, 450.0, 680.0),
}

A4_WIDTH = 595.32
A4_HEIGHT = 841.92
MM_TO_POINTS = 72 / 25.4
SECOND_PRINTABLE_PAGE_OFFSET_Y = -5 * MM_TO_POINTS


SMALL_FIELDS = {
    "monto de prenda en letras": 6.5,
    "nombre titular": 8.5,
    "apellido y nombre": 8.5,
    "titular casado": 8.5,
    "nombre conyuge": 8.5,
    "domicilio conyuge": 8.0,
    "modelo": 8.5,
    "nro motor": 8.5,
    "nro chasis": 8.0,
    "calle": 8.5,
    "mail": 8.0,
    "cuil": 8.5,
}


def _effective_name(widget: Any) -> Any:
    parent = widget.get("/Parent")
    parent = parent.get_object() if parent else None
    return widget.get("/T") or (parent.get("/T") if parent else None)


def _set_widget_style(writer: PdfWriter) -> None:
    acroform = writer.root_object["/AcroForm"].get_object()
    resources = acroform.get("/DR") or DictionaryObject()
    fonts = resources.get("/Font") or DictionaryObject()
    fonts[NameObject("/Helv")] = writer._add_object(DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
        NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
    }))
    resources[NameObject("/Font")] = fonts
    acroform[NameObject("/DR")] = resources

    for page_number, page in enumerate(writer.pages, 1):
        for ref in page.get("/Annots", []):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            name = _effective_name(widget)
            if not name or name == "Button1" or "@" in str(name):
                continue
            parent_ref = widget.get("/Parent")
            parent = parent_ref.get_object() if parent_ref else None
            target = parent if parent is not None else widget
            if target.get("/FT") == "/Btn":
                continue

            # The source marks most text fields as comb fields, which spreads
            # letters across the rectangle. Keep placement but remove that flag.
            flags = int(target.get("/Ff", 0)) & ~16777216
            target[NameObject("/Ff")] = NumberObject(flags)
            widget[NameObject("/Ff")] = NumberObject(flags)
            size = SMALL_FIELDS.get(str(name), 10.0)
            appearance = TextStringObject(f"/Helv {size:g} Tf 0 g")
            widget[NameObject("/DA")] = appearance
            target[NameObject("/DA")] = appearance
            widget[NameObject("/Q")] = NumberObject(0)
            target[NameObject("/Q")] = NumberObject(0)

            # Vehicle data lives on source page 3 (final page 2 after removing
            # the data-entry sheet).
            if page_number == 3 and str(name) in VEHICLE_RECTS:
                widget[NameObject("/Rect")] = ArrayObject([
                    FloatObject(value) for value in VEHICLE_RECTS[str(name)]
                ])


def _transform_widget_rects(page: Any, scale: float, tx: float, ty: float) -> None:
    for ref in page.get("/Annots", []):
        widget = ref.get_object()
        rect = widget.get("/Rect")
        if not rect:
            continue
        x1, y1, x2, y2 = (float(value) for value in rect)
        widget[NameObject("/Rect")] = ArrayObject([
            FloatObject(x1 * scale + tx), FloatObject(y1 * scale + ty),
            FloatObject(x2 * scale + tx), FloatObject(y2 * scale + ty),
        ])


def _fit_contract_pages_to_a4(writer: PdfWriter) -> None:
    # Source page 2 (the "03" sheet) is already A4 and must print at 100%.
    # Source pages 3-6 previously required the print dialog's "Fit" option.
    # Bake that proportional fit into the PDF so the whole packet can be sent
    # with the printer's default/actual-size setting.
    for page in writer.pages[2:]:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        scale = min(A4_WIDTH / width, A4_HEIGHT / height)
        tx = (A4_WIDTH - width * scale) / 2
        ty = (A4_HEIGHT - height * scale) / 2
        page.add_transformation(Transformation().scale(scale).translate(tx, ty))
        _transform_widget_rects(page, scale, tx, ty)
        page.mediabox.lower_left = (0, 0)
        page.mediabox.upper_right = (A4_WIDTH, A4_HEIGHT)
        page.cropbox.lower_left = (0, 0)
        page.cropbox.upper_right = (A4_WIDTH, A4_HEIGHT)

    # A physical comparison showed that the second printable sheet sits about
    # 5 mm too high after the proportional fit. Move only that sheet down while
    # preserving its scale and every relative field coordinate.
    second_printable_page = writer.pages[2]
    second_printable_page.add_transformation(
        Transformation().translate(0, SECOND_PRINTABLE_PAGE_OFFSET_Y)
    )
    _transform_widget_rects(
        second_printable_page, 1.0, 0, SECOND_PRINTABLE_PAGE_OFFSET_Y
    )


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
    _set_widget_style(writer)
    writer.update_page_form_field_values(None, values, auto_regenerate=False)
    _fit_contract_pages_to_a4(writer)
    # The first page is only the bank's data-entry sheet. The five following
    # pages are the stable printable packet used by the operations team.
    del writer.pages[0]
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
