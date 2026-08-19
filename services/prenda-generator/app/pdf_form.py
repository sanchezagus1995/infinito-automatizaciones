from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO
import math
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
from reportlab.pdfbase.pdfmetrics import stringWidth


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

# Final AcroForm rectangles measured from the physically corrected Galicia
# packet approved on 2026-08-18. Keys contain the printable page,
# effective field name and the pre-correction rectangle rounded to 2 decimals.
# This keeps duplicate field names unambiguous and fails safely if the bank
# template or an earlier transformation changes.
FINAL_WIDGET_RECTS = {
    (1, "dominio", (262.55, 704.2, 362.47, 724.0)): (262.25, 692.5, 362.47, 711.7),
    (1, "monto de prenda", (130.23, 700.9, 228.65, 717.7)): (130.23, 693.1, 228.65, 709.9),
    (1, "cuil", (348.87, 603.83, 552.11, 621.84)): (349.87, 604.89, 553.31, 622.89),
    (1, "nro calle", (354.47, 537.0, 396.88, 554.61)): (354.67, 540.68, 396.68, 558.08),
    (1, "codigo postal", (495.3, 539.81, 547.31, 556.61)): (495.1, 542.48, 547.31, 559.28),
    (1, "partido", (352.07, 495.79, 459.29, 511.39)): (352.27, 499.27, 459.09, 514.87),
    (1, "provincia", (475.3, 496.19, 550.51, 512.59)): (475.9, 499.27, 550.91, 515.47),
    (1, "dni", (348.55, 422.16, 422.01, 438.01)): (348.97, 427.26, 422.19, 443.16),
    (1, "ARG", (362.17, 443.76, 379.88, 455.77)): (362.47, 451.56, 380.18, 463.57),
    (1, "EXT", (466.17, 444.25, 485.86, 456.26)): (466.59, 452.16, 486.1, 464.17),
    (1, "soltero 03", (423.69, 375.65, 437.79, 390.96)): (423.69, 378.65, 437.79, 393.96),
    (1, "casado 03", (453.09, 375.65, 468.39, 390.96)): (453.09, 378.35, 468.39, 393.66),
    (1, "div 03", (509.86, 375.09, 529.07, 390.46)): (509.8, 377.75, 529.01, 393.06),
    (1, "apellido y nombre", (350.02, 628.29, 582.27, 648.69)): (349.27, 625.89, 581.52, 646.29),
    (2, "monto de prenda", (144.03, 720.89, 224.62, 734.92)): (144.03, 728.8, 224.75, 742.61),
    (2, "nombre titular", (133.59, 687.79, 315.29, 700.38)): (117.62, 692.5, 299.46, 705.1),
    (2, "TNA", (278.57, 404.49, 301.64, 417.45)): (285.36, 426.66, 308.46, 439.56),
    (2, "calle", (104.99, 486.93, 276.88, 499.48)): (105.02, 497.77, 530.0, 510.37),
    (2, "nro calle", (539.08, 486.66, 571.46, 499.61)): (538.91, 498.07, 571.32, 511.27),
    (2, "provincia", (244.23, 566.27, 312.23, 578.81)): (243.95, 573.98, 312.06, 586.58),
    (2, "localidad", (146.91, 499.61, 255.2, 512.57)): (147.33, 514.87, 530.0, 527.78),
    (2, "nombre titular", (395.88, 258.19, 570.02, 271.14)): (396.08, 281.44, 570.11, 294.64),
    (2, "profesion", (474.32, 236.96, 568.59, 250.28)): (474.1, 260.44, 568.31, 273.64),
    (2, "estado civil", (366.02, 236.96, 418.19, 250.28)): (366.07, 260.44, 418.28, 273.64),
    (2, "nacionalidad", (376.46, 209.62, 466.4, 222.57)): (376.28, 232.83, 466.29, 246.04),
    (2, "edad", (501.66, 209.26, 531.53, 222.57)): (501.7, 232.83, 531.71, 246.04),
    (2, "calle", (355.14, 190.91, 526.76, 204.4)): (355.27, 214.23, 526.91, 228.03),
    (2, "nro calle", (318.17, 175.44, 356.31, 188.75)): (318.06, 198.63, 356.47, 212.43),
    (2, "dni", (428.0, 157.18, 493.84, 170.54)): (427.89, 180.63, 493.9, 193.83),
    (2, "provincia", (336.88, 747.51, 404.88, 759.75)): (336.97, 754.61, 404.78, 766.91),
    (2, "dia armado", (409.92, 747.51, 427.91, 762.62)): (410.18, 753.11, 428.19, 768.41),
    (2, "mes armado", (432.22, 747.15, 450.21, 762.26)): (432.39, 752.51, 450.39, 767.81),
    (2, "año armado", (453.81, 747.87, 471.8, 762.98)): (453.99, 753.41, 472.0, 768.41),
    (2, "localidad", (356.31, 175.44, 432.22, 188.75)): (356.47, 198.63, 432.09, 212.43),
    (2, "partido", (432.22, 175.44, 503.82, 188.75)): (432.09, 198.63, 504.1, 212.43),
    (2, "provincia", (503.82, 175.44, 571.46, 188.75)): (504.1, 198.63, 571.32, 212.43),
    (3, "plazo", (265.82, 798.34, 281.33, 811.29)): (267.95, 785.81, 283.56, 798.71),
    (3, "mail", (162.38, 559.84, 291.9, 575.31)): (162.33, 552.68, 291.96, 567.98),
    (3, "año vto", (179.06, 782.82, 191.34, 795.1)): (181.24, 770.21, 193.54, 782.51),
    (3, "mes vto", (161.25, 782.82, 173.53, 795.1)): (163.23, 770.21, 175.54, 782.51),
    (3, "dia vto", (142.23, 783.09, 154.51, 795.37)): (144.33, 770.51, 156.63, 782.81),
}


MAX_FONT_SIZE = 10.0
MIN_FONT_SIZE = 8.0
MIN_HORIZONTAL_SCALE = 75.0
FIELD_HORIZONTAL_PADDING = 4.0


def _effective_name(widget: Any) -> Any:
    parent = widget.get("/Parent")
    parent = parent.get_object() if parent else None
    return widget.get("/T") or (parent.get("/T") if parent else None)


def _fit_text_style(text: str, rect: Any) -> tuple[float, float]:
    """Balance font size and horizontal scale for a single-line widget."""
    if not text:
        return MAX_FONT_SIZE, 100.0
    width = abs(float(rect[2]) - float(rect[0])) - FIELD_HORIZONTAL_PADDING
    width_at_one_point = stringWidth(text, "Helvetica", 1)
    if width <= 0 or width_at_one_point <= 0:
        return MAX_FONT_SIZE, 100.0

    natural_width = width_at_one_point * MAX_FONT_SIZE
    if natural_width <= width:
        return MAX_FONT_SIZE, 100.0

    scale_at_maximum = math.floor((width / natural_width) * 1000) / 10
    if scale_at_maximum >= MIN_HORIZONTAL_SCALE:
        return MAX_FONT_SIZE, scale_at_maximum

    fitted_size = math.floor(
        (width / (width_at_one_point * MIN_HORIZONTAL_SCALE / 100)) * 10
    ) / 10
    size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, fitted_size))
    scale = math.floor((width / (width_at_one_point * size)) * 1000) / 10
    return size, min(100.0, scale)


def _set_vehicle_widget_rects(writer: PdfWriter) -> None:
    # Vehicle data lives on source page 3 (final page 2 after removing the
    # data-entry sheet). Its rectangles must be set before fitting the source
    # contract pages to A4.
    page = writer.pages[2]
    for ref in page.get("/Annots", []):
        widget = ref.get_object()
        name = _effective_name(widget)
        if str(name) not in VEHICLE_RECTS:
            continue
        widget[NameObject("/Rect")] = ArrayObject([
            FloatObject(value) for value in VEHICLE_RECTS[str(name)]
        ])


def _set_widget_style(writer: PdfWriter, values: dict[str, Any]) -> None:
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

    for page in writer.pages:
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
            size, horizontal_scale = _fit_text_style(
                str(values.get(str(name), "")), widget["/Rect"]
            )
            appearance = TextStringObject(
                f"/Helv {size:g} Tf {horizontal_scale:g} Tz 0 g"
            )
            widget[NameObject("/DA")] = appearance
            target[NameObject("/DA")] = appearance
            widget[NameObject("/Q")] = NumberObject(0)
            target[NameObject("/Q")] = NumberObject(0)


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


def _apply_final_widget_rects(writer: PdfWriter) -> None:
    applied = set()
    for page_number, page in enumerate(writer.pages, 1):
        for ref in page.get("/Annots", []):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            name = _effective_name(widget)
            rect = widget.get("/Rect")
            if not name or not rect:
                continue
            source_rect = tuple(round(float(value), 2) for value in rect)
            key = (page_number, str(name), source_rect)
            target_rect = FINAL_WIDGET_RECTS.get(key)
            if target_rect is None:
                continue
            widget[NameObject("/Rect")] = ArrayObject([
                FloatObject(value) for value in target_rect
            ])
            applied.add(key)

    missing = set(FINAL_WIDGET_RECTS) - applied
    if missing:
        raise ValueError(
            "No se pudieron aplicar todas las coordenadas finales de Galicia: "
            f"{sorted(missing)}"
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
    _set_vehicle_widget_rects(writer)
    _fit_contract_pages_to_a4(writer)
    # The first page is only the bank's data-entry sheet. The five following
    # pages are the stable printable packet used by the operations team.
    del writer.pages[0]
    _apply_final_widget_rects(writer)
    # Generate each appearance only after every widget has its final rectangle.
    # Long values receive a widget-specific font size, so the same field can fit
    # both a wide occurrence and a narrower repeated occurrence in the packet.
    _set_widget_style(writer, values)
    writer.update_page_form_field_values(None, values, auto_regenerate=False)
    output = BytesIO()
    writer.write(output)
    # Preserve the AcroForm widgets instead of rasterizing the packet. This
    # keeps every Galicia value editable and movable in a PDF form editor while
    # retaining the calibrated page sizes and widget coordinates.
    return output.getvalue()
