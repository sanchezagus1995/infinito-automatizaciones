from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.colors import black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .pdf_form import _age, _cuil, _date_parts, _digits, _upper, money, money_words


PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
REFERENCE_WIDTH = 1157.0
REFERENCE_HEIGHT = 1637.0


def _x(value: float) -> float:
    return value * PAGE_WIDTH / REFERENCE_WIDTH


def _y(value: float) -> float:
    return PAGE_HEIGHT - value * PAGE_HEIGHT / REFERENCE_HEIGHT


def _fit_size(text: str, width: float, requested: float, minimum: float = 5.5) -> float:
    size = requested
    while size > minimum and stringWidth(text, "Helvetica", size) > width:
        size -= 0.2
    return size


def _draw(
    canvas: Canvas,
    text: Any,
    x: float,
    y: float,
    width: float = 250,
    size: float = 8.2,
    *,
    bold: bool = False,
) -> None:
    value = _upper(text)
    if not value:
        return
    font = "Helvetica-Bold" if bold else "Helvetica"
    canvas.setFillColor(black)
    canvas.setFont(font, _fit_size(value, _x(width), size))
    canvas.drawString(_x(x), _y(y), value)


def _mark(canvas: Canvas, x: float, y: float) -> None:
    canvas.setStrokeColor(black)
    canvas.setLineWidth(1.4)
    size = _x(9)
    center_x, center_y = _x(x), _y(y)
    canvas.line(center_x - size, center_y - size, center_x + size, center_y + size)
    canvas.line(center_x - size, center_y + size, center_x + size, center_y - size)


def _address(values: dict[str, Any]) -> str:
    parts = [values.get("calle"), values.get("numero_calle")]
    return " ".join(_upper(part) for part in parts if _upper(part))


def _full_address(values: dict[str, Any]) -> str:
    parts = [
        _address(values),
        values.get("piso_departamento"),
        values.get("localidad"),
        values.get("provincia"),
        values.get("codigo_postal"),
    ]
    return " - ".join(_upper(part) for part in parts if _upper(part))


def values_from_icbc_form(form: dict[str, Any]) -> dict[str, Any]:
    civil_status = _upper(form.get("estado_civil"))
    nationality = _upper(form.get("nacionalidad"))
    due = _date_parts(form.get("fecha_vencimiento"))
    armed = _date_parts(form.get("fecha_armado"))
    return {
        **form,
        "nombre": _upper(form.get("nombre")),
        "dni": _digits(form.get("dni")),
        "cuil": _cuil(form.get("cuil")),
        "estado_civil": civil_status,
        "nacionalidad": nationality,
        "edad": _age(form.get("fecha_nacimiento"), form.get("fecha_armado")),
        "monto": money(form.get("bruto")),
        "monto_letras": money_words(form.get("bruto")),
        "cuota": money(form.get("cuota")),
        "vencimiento": "/".join(part for part in due if part),
        "anio_armado": armed[2] or "",
        "domicilio_resumido": _address(form),
        "domicilio_completo": _full_address(form),
    }


def _draw_page_1(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw(canvas, values["monto"], 264, 273, 210, 9)
    _draw(canvas, values.get("dominio"), 528, 276, 135, 9)

    # Section D - invariant ICBC creditor data.
    _draw(canvas, "INDUSTRIAL AND COMMERCIAL BANK", 274, 402, 360)
    _draw(canvas, "OF CHINA (ARGENTINA) S.A.U.", 274, 446, 360)
    _draw(canvas, "CUIT: 30-70944784-6", 282, 477, 330)
    _draw(canvas, "FLORIDA", 288, 535, 210)
    _draw(canvas, "99", 304, 568, 80)
    _draw(canvas, "1005", 566, 568, 90)
    _draw(canvas, "C.A.B.A.", 302, 608, 210)
    _draw(canvas, "C.A.B.A.", 287, 646, 180)
    _draw(canvas, "BS. AS.", 542, 648, 100)
    _draw(canvas, "I.G.J. N° 4987-7-6 ACC.", 270, 970, 350)
    _draw(canvas, "31", 519, 1042, 45)
    _draw(canvas, "03", 567, 1042, 45)
    _draw(canvas, "06", 615, 1042, 45)

    _draw(canvas, values["nombre"], 711, 419, 350, 8.5)
    _draw(canvas, f"CUIL: {values['cuil']}", 700, 461, 330)
    _draw(canvas, values.get("profesion"), 714, 495, 220)
    _draw(canvas, values["domicilio_resumido"], 684, 550, 390, 6.8)
    _draw(canvas, values.get("piso_departamento"), 706, 588, 70)
    _draw(canvas, values.get("codigo_postal"), 1053, 588, 75)
    _draw(canvas, values.get("localidad"), 778, 625, 300, 7.6)
    _draw(canvas, values.get("partido"), 758, 659, 150)
    _draw(canvas, values.get("provincia"), 971, 659, 150)

    if values["nacionalidad"] in {"ARGENTINO", "ARGENTINA"}:
        _mark(canvas, 705, 734)
    else:
        _mark(canvas, 937, 734)
    _draw(canvas, values["dni"], 704, 797, 190)
    _draw(canvas, values.get("autoridad_dni", "R.N.P."), 877, 797, 135)
    birth = _date_parts(values.get("fecha_nacimiento"))
    _draw(canvas, birth[0], 689, 882, 45)
    _draw(canvas, birth[1], 742, 882, 45)
    _draw(canvas, f"19{birth[2]}" if birth[2] else "", 800, 882, 75)
    civil_marks = {"SOLTERO": (856, 875), "CASADO": (916, 875), "VIUDO": (973, 875), "DIVORCIADO": (1033, 875)}
    if values["estado_civil"] in civil_marks:
        _mark(canvas, *civil_marks[values["estado_civil"]])

    _draw(canvas, values.get("dominio"), 484, 1240, 160, 9)
    _draw(canvas, values.get("marca"), 403, 1286, 150)
    _draw(canvas, values.get("tipo_vehiculo"), 350, 1330, 160)
    _draw(canvas, values.get("modelo"), 360, 1375, 330, 7.2)
    _draw(canvas, values.get("marca_motor"), 405, 1418, 140)
    _draw(canvas, values.get("numero_motor"), 397, 1462, 230)
    _draw(canvas, values.get("marca_chasis"), 403, 1505, 130)
    _draw(canvas, values.get("numero_chasis"), 382, 1547, 310, 7.2)

    # Section I - invariant ICBC contract modality.
    _draw(canvas, "1", 476, 1516, 30, 8)
    _mark(canvas, 512, 1518)
    _mark(canvas, 1017, 1518)
    _mark(canvas, 1017, 1582)


def _draw_page_2(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw(canvas, values["monto"], 348, 303, 260, 9)
    _draw(canvas, values.get("localidad_armado") or values.get("provincia"), 765, 299, 150)
    _draw(canvas, values["anio_armado"], 1005, 299, 80)
    words = values["monto_letras"]
    midpoint = min(len(words), 58)
    split = words.rfind(" ", 0, midpoint)
    split = split if split > 0 else midpoint
    _draw(canvas, words[:split], 645, 346, 430, 7)
    _draw(canvas, words[split:].strip(), 288, 375, 570, 7)
    _draw(canvas, values["nombre"], 820, 374, 270, 7.2)
    _draw(canvas, f"UN AUTOMOTOR: DOMINIO {values.get('dominio', '')} - MARCA {values.get('marca', '')}", 311, 454, 730, 6.5)
    _draw(canvas, f"TIPO {values.get('tipo_vehiculo', '')} - MODELO {values.get('modelo', '')}", 349, 480, 650, 6.5)
    _draw(canvas, f"MARCA MOTOR {values.get('marca_motor', '')} - NRO MOTOR {values.get('numero_motor', '')}", 352, 507, 600, 6.5)
    _draw(canvas, f"MARCA CHASIS {values.get('marca_chasis', '')} - NRO CHASIS {values.get('numero_chasis', '')}", 350, 534, 650, 6.5)
    _draw(canvas, f"AÑO {values.get('anio', '')} - USO {values.get('tipo_uso', '')}", 360, 562, 350, 6.8)
    _draw(canvas, values.get("provincia"), 571, 606, 180)
    _draw(canvas, values.get("partido"), 398, 632, 120)
    _draw(canvas, values.get("localidad"), 429, 659, 280, 6.8)
    _draw(canvas, values["domicilio_resumido"], 764, 659, 300, 6.3)
    _draw(canvas, values.get("piso_departamento"), 1020, 659, 70)
    _draw(canvas, "NINGUNO", 883, 686, 170)
    _draw(canvas, f"{values.get('plazo', '')} CUOTAS IGUALES, MENSUALES Y CONSECUTIVAS", 535, 740, 480, 6.7)
    _draw(canvas, values["cuota"], 908, 740, 160, 6.7)
    _draw(canvas, f"LA PRIMERA CUOTA VENCE EL DÍA {values['vencimiento']}", 540, 767, 500, 6.5)
    _draw(canvas, "Y LAS RESTANTES EL MISMO DÍA DE CADA MES SUBSIGUIENTE", 385, 793, 650, 6.2)
    _draw(canvas, values.get("tna"), 755, 839, 70, 8)
    _draw(canvas, values["nombre"], 875, 936, 270, 7)
    _draw(canvas, f"{values['estado_civil']} - PROFESIÓN: {values.get('profesion', '')}", 865, 965, 270, 6.6)
    _draw(canvas, values["nacionalidad"], 858, 993, 130, 6.8)
    _draw(canvas, values["edad"], 1020, 993, 55, 6.8)
    _draw(canvas, values["domicilio_resumido"], 846, 1020, 280, 5.9)
    _draw(canvas, values["dni"], 875, 1049, 160, 6.8)
    _draw(canvas, values["cuil"], 865, 1077, 190, 6.8)


def _draw_page_3(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw(canvas, values.get("tna"), 766, 77, 50, 8)
    _draw(canvas, values.get("tea"), 297, 101, 70, 8)
    _draw(canvas, values.get("cftea"), 999, 101, 70, 8)
    if len(values["domicilio_completo"]) > 38:
        _draw(canvas, f"* CALLE: {values['domicilio_resumido']}", 498, 710, 560, 6.4, bold=True)
        _draw(canvas, f"* DOMICILIO: {values['domicilio_completo']}", 498, 735, 610, 5.8, bold=True)


def _draw_page_4(canvas: Canvas, values: dict[str, Any]) -> None:
    # ICBC is preprinted as creditor on this sheet; only the debtor is added.
    _draw(canvas, values["nombre"], 292, 190, 340, 7)
    _draw(canvas, values["domicilio_resumido"], 762, 1510, 360, 5.8)
    _draw(canvas, values.get("piso_departamento"), 1063, 1510, 60, 6)
    _draw(canvas, values.get("localidad"), 170, 1538, 300, 6)
    _draw(canvas, values.get("provincia"), 817, 1538, 130, 6)


def fill_icbc(values: dict[str, Any]) -> bytes:
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    for drawer in (_draw_page_1, _draw_page_2, _draw_page_3, _draw_page_4):
        drawer(canvas, values)
        canvas.showPage()
    canvas.save()
    return stream.getvalue()
