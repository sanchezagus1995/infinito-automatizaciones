from __future__ import annotations

from io import BytesIO
from typing import Any

from reportlab.lib.colors import black
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .pdf_form import _age, _cuil, _date_parts, _digits, _upper, money, money_words


PAGE_WIDTH = 595.0
PAGE_HEIGHT = 842.0
OFICIO_WIDTH = 612.0
OFICIO_HEIGHT = 936.0
REFERENCE_WIDTH = 1157.0
REFERENCE_HEIGHT = 1637.0
PAGE4_ADDRESS_OFFSET_X = 10 * 72 / 25.4
PAGE4_ADDRESS_OFFSET_Y = 40 * 72 / 25.4


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


def _draw_at(
    canvas: Canvas,
    text: Any,
    x: float,
    baseline_from_top: float,
    width: float = 250,
    size: float = 8.2,
    *,
    bold: bool = False,
) -> None:
    """Draw at exact PDF point coordinates measured from the approved sample."""
    value = _upper(text)
    if not value:
        return
    font = "Helvetica-Bold" if bold else "Helvetica"
    canvas.setFillColor(black)
    canvas.setFont(font, _fit_size(value, width, size))
    canvas.drawString(x, canvas._pagesize[1] - baseline_from_top, value)


def _mark(canvas: Canvas, x: float, y: float) -> None:
    canvas.setStrokeColor(black)
    canvas.setLineWidth(1.4)
    size = _x(9)
    center_x, center_y = _x(x), _y(y)
    canvas.line(center_x - size, center_y - size, center_x + size, center_y + size)
    canvas.line(center_x - size, center_y + size, center_x + size, center_y - size)


def _address(values: dict[str, Any]) -> str:
    parts = [values.get("calle"), values.get("numero_calle"), values.get("piso_departamento")]
    return " ".join(_upper(part) for part in parts if _upper(part))


def _full_address(values: dict[str, Any]) -> str:
    parts = [
        _address(values),
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
        "monto": money(form.get("monto_prenda")),
        "monto_letras": money_words(form.get("monto_prenda")),
        "cuota": money(form.get("cuota")),
        "vencimiento": "/".join(part for part in due if part),
        "anio_armado": armed[2] or "",
        "domicilio_resumido": _address(form),
        "domicilio_completo": _full_address(form),
    }


def _draw_page_1(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw_at(canvas, values["monto"], 135.76, 128.19, 130, 9)
    _draw_at(canvas, values.get("dominio"), 276.80, 128.19, 80, 9)

    # Section D - invariant ICBC creditor data.
    _draw_at(canvas, "INDUSTRIAL AND COMMERCIAL BANK", 140.91, 201.56, 190)
    _draw_at(canvas, "OF CHINA (ARGENTINA) S.A.U.", 140.91, 225.07, 180)
    _draw_at(canvas, "CUIT: 30-70944784-6", 145.02, 241.02, 130)
    _draw_at(canvas, "FLORIDA", 148.11, 265.55, 100)
    _draw_at(canvas, "99", 156.34, 290.61, 35)
    _draw_at(canvas, "1005", 291.07, 290.61, 40)
    _draw_at(canvas, "C.A.B.A.", 155.31, 312.73, 80)
    _draw_at(canvas, "C.A.B.A.", 147.59, 332.27, 80)
    _draw_at(canvas, "BS. AS.", 278.73, 333.30, 55)
    _draw_at(canvas, "I.G.J. N° 4987-7-6 ACC.", 138.85, 507.96, 130)
    _draw_at(canvas, "31", 256.70, 547.51, 20)
    _draw_at(canvas, "03", 281.39, 547.51, 20)
    _draw_at(canvas, "06", 306.07, 547.51, 20)

    _draw_at(canvas, values["nombre"], 365.64, 201.86, 180, 8.5)
    _draw_at(canvas, f"CUIL: {values['cuil']}", 365.64, 223.53, 150)
    _draw_at(canvas, values.get("profesion"), 372.84, 241.02, 110)
    _draw_at(canvas, values["domicilio_resumido"], 351.75, 264.80, 190, 6.8)
    _draw_at(canvas, values.get("codigo_postal"), 517.25, 290.61, 40)
    _draw_at(canvas, values.get("localidad"), 400.10, 312.85, 145, 7.6)
    _draw_at(canvas, values.get("partido"), 389.81, 333.30, 80)
    _draw_at(canvas, values.get("provincia"), 499.35, 333.30, 70)

    if values["nacionalidad"] in {"ARGENTINO", "ARGENTINA"}:
        _mark(canvas, 705, 734)
    else:
        _mark(canvas, 937, 734)
    _draw_at(canvas, values["dni"], 362.04, 409.94, 70)
    _draw_at(canvas, values.get("autoridad_dni", "R.N.P."), 451.01, 409.94, 60)
    birth = _date_parts(values.get("fecha_nacimiento"))
    _draw_at(canvas, birth[0], 341.91, 453.48, 20)
    _draw_at(canvas, birth[1], 369.16, 453.48, 20)
    _draw_at(canvas, f"19{birth[2]}" if birth[2] else "", 398.99, 453.48, 40)
    civil_marks = {"SOLTERO": (856, 875), "CASADO": (916, 875), "VIUDO": (973, 875), "DIVORCIADO": (1033, 875)}
    if values["estado_civil"] in civil_marks:
        _mark(canvas, *civil_marks[values["estado_civil"]])

    _draw_at(canvas, values.get("dominio"), 248.90, 671.99, 80, 9)
    _draw_at(canvas, values.get("marca"), 207.25, 693.83, 80)
    _draw_at(canvas, values.get("tipo_vehiculo"), 152.33, 715.20, 80)
    _draw_at(canvas, values.get("modelo"), 158.73, 729.56, 150, 7.2)
    _draw_at(canvas, values.get("marca_motor"), 168.48, 751.99, 70)
    _draw_at(canvas, values.get("numero_motor"), 168.48, 774.47, 120)
    _draw_at(canvas, values.get("marca_chasis"), 158.73, 796.69, 70)
    _draw_at(canvas, values.get("numero_chasis"), 158.73, 817.71, 145, 7.2)

    # Section I - invariant ICBC contract modality.
    _draw_at(canvas, "1", 370.13, 778.39, 20, 8)
    _mark(canvas, 512, 1518)
    _mark(canvas, 1017, 1518)
    _mark(canvas, 1017, 1582)


def _draw_page_2(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw_at(canvas, values["monto"], 178.96, 172.30, 130, 9)
    _draw_at(canvas, values.get("provincia"), 403.91, 155.59, 100)
    armed = _date_parts(values.get("fecha_armado"))
    _draw_at(canvas, "/".join(part for part in armed if part), 500.0, 155.59, 75)
    words = values["monto_letras"]
    midpoint = min(len(words), 58)
    split = words.rfind(" ", 0, midpoint)
    split = split if split > 0 else midpoint
    _draw_at(canvas, words[:split], 331.70, 192.48, 220, 7)
    _draw_at(canvas, words[split:].strip(), 148.11, 207.40, 260, 7)
    _draw_at(canvas, values["nombre"], 421.69, 206.89, 150, 7.2)
    _draw_at(canvas, f"UN AUTOMOTOR: DOMINIO {values.get('dominio', '')} - MARCA {values.get('marca', '')}", 159.94, 233.52, 380, 6.5)
    _draw_at(canvas, f"TIPO {values.get('tipo_vehiculo', '')} - MODELO {values.get('modelo', '')}", 179.48, 246.89, 370, 6.5)
    _draw_at(canvas, f"MARCA MOTOR {values.get('marca_motor', '')} - NRO MOTOR {values.get('numero_motor', '')}", 181.02, 260.78, 360, 6.5)
    _draw_at(canvas, f"MARCA CHASIS {values.get('marca_chasis', '')} - NRO CHASIS {values.get('numero_chasis', '')}", 179.99, 274.67, 380, 6.5)
    _draw_at(canvas, f"AÑO {values.get('anio', '')} - USO {values.get('tipo_uso', '')}", 185.13, 289.07, 200, 6.8)
    _draw_at(canvas, values.get("provincia"), 293.64, 352.85, 100)
    _draw_at(canvas, values.get("partido"), 204.68, 366.22, 70)
    _draw_at(canvas, values.get("localidad"), 220.62, 380.72, 170, 6.8)
    _draw_at(canvas, values["domicilio_resumido"], 392.90, 380.72, 190, 5.7)
    _draw_at(canvas, "NINGUNO", 454.09, 352.85, 80)
    _draw_at(canvas, f"{values.get('plazo', '')} CUOTAS IGUALES, MENSUALES Y CONSECUTIVAS", 336.34, 413.03, 190, 6.7)
    _draw_at(canvas, values["cuota"], 528.16, 413.03, 70, 6.7)
    _draw_at(canvas, f"LA PRIMERA CUOTA VENCE EL DÍA {values['vencimiento']}", 338.91, 426.92, 220, 6.5)
    _draw_at(canvas, "Y LAS RESTANTES EL MISMO DÍA DE CADA MES SUBSIGUIENTE", 378.06, 439.28, 210, 6.2)
    _draw_at(canvas, values.get("tna"), 388.27, 482.42, 35, 8)
    _draw_at(canvas, values["nombre"], 449.98, 554.47, 130, 7)
    _draw_at(canvas, f"{values['estado_civil']} - PROFESIÓN: {values.get('profesion', '')}", 444.84, 569.38, 140, 6.6)
    _draw_at(canvas, values["nacionalidad"], 441.24, 583.79, 80, 6.8)
    _draw_at(canvas, values["edad"], 524.55, 583.79, 25, 6.8)
    _draw_at(canvas, values["domicilio_resumido"], 435.06, 597.67, 150, 5.5)
    _draw_at(canvas, values["dni"], 449.98, 612.59, 70, 6.8)
    _draw_at(canvas, values["cuil"], 444.84, 626.99, 90, 6.8)


def _draw_page_3(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw_at(canvas, values.get("tna"), 431.77, 39.18, 30, 8.2)
    _draw_at(canvas, values.get("tea"), 152.74, 50.45, 35, 8)
    _draw_at(canvas, values.get("cftea"), 552.54, 49.13, 35, 8.2)
    if len(values["domicilio_completo"]) > 38:
        _draw_at(canvas, f"* CALLE: {values['domicilio_resumido']}", 256.10, 405.72, 290, 6.4, bold=True)
        _draw_at(canvas, f"* DOMICILIO: {values['domicilio_completo']}", 256.10, 418.57, 330, 5.4, bold=True)


def _draw_page_4(canvas: Canvas, values: dict[str, Any]) -> None:
    # ICBC is preprinted as creditor on this sheet; only the debtor is added.
    _draw_at(canvas, values["nombre"], 150.16, 97.73, 180, 7)
    # The physical continuation sheet is oficio. The approved A4 reference is
    # shifted here by the measured 1 cm right / 4 cm down correction.
    _draw_at(canvas, values["domicilio_resumido"], 391.87 + PAGE4_ADDRESS_OFFSET_X, 776.68 + PAGE4_ADDRESS_OFFSET_Y, 160, 5.8)
    _draw_at(canvas, values.get("localidad"), 87.42 + PAGE4_ADDRESS_OFFSET_X, 791.08 + PAGE4_ADDRESS_OFFSET_Y, 210, 6)
    _draw_at(canvas, values.get("provincia"), 420.15 + PAGE4_ADDRESS_OFFSET_X, 791.08 + PAGE4_ADDRESS_OFFSET_Y, 80, 6)


def fill_icbc(values: dict[str, Any]) -> bytes:
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(PAGE_WIDTH, PAGE_HEIGHT), pageCompression=1)
    for page_number, drawer in enumerate((_draw_page_1, _draw_page_2, _draw_page_3, _draw_page_4), 1):
        if page_number == 4:
            canvas.setPageSize((OFICIO_WIDTH, OFICIO_HEIGHT))
        drawer(canvas, values)
        canvas.showPage()
    canvas.save()
    return stream.getvalue()
