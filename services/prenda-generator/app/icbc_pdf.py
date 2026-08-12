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


def _mark_at(canvas: Canvas, center_x: float, center_from_top: float) -> None:
    canvas.setStrokeColor(black)
    canvas.setLineWidth(1.4)
    size = 4.63
    center_y = canvas._pagesize[1] - center_from_top
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
    _draw_at(canvas, values["monto"], 135.76, 138.88, 130, 9)
    _draw_at(canvas, values.get("dominio"), 276.80, 138.88, 80, 9)

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
        _mark_at(canvas, 362.56, 377.54)
    else:
        _mark(canvas, 937, 734)
    _draw_at(canvas, values["dni"], 362.04, 409.94, 70)
    _draw_at(canvas, values.get("autoridad_dni", "R.N.P."), 451.01, 409.94, 60)
    birth = _date_parts(values.get("fecha_nacimiento"))
    _draw_at(canvas, birth[0], 341.91, 453.35, 20)
    _draw_at(canvas, birth[1], 369.16, 453.35, 20)
    _draw_at(canvas, f"19{birth[2]}" if birth[2] else "", 391.91, 453.35, 40)
    civil_marks = {
        "SOLTERO": (428.30, 450.06),
        "CASADO": (459.14, 450.06),
        "VIUDO": (488.45, 450.06),
        "DIVORCIADO": (519.30, 450.06),
    }
    if values["estado_civil"] in civil_marks:
        _mark_at(canvas, *civil_marks[values["estado_civil"]])

    _draw_at(canvas, values.get("dominio"), 248.90, 657.58, 80, 9)
    _draw_at(canvas, values.get("marca"), 207.25, 679.42, 80)
    _draw_at(canvas, values.get("tipo_vehiculo"), 152.33, 700.79, 80)
    _draw_at(canvas, values.get("modelo"), 158.73, 715.15, 150, 7.2)
    _draw_at(canvas, values.get("marca_motor"), 168.48, 737.58, 70)
    _draw_at(canvas, values.get("numero_motor"), 168.48, 760.06, 120)
    _draw_at(canvas, values.get("marca_chasis"), 158.73, 782.28, 70)
    _draw_at(canvas, values.get("numero_chasis"), 158.73, 803.30, 145, 7.2)

    # Section I - invariant ICBC contract modality.
    _draw_at(canvas, "1", 379.59, 759.38, 20, 8)
    _mark_at(canvas, 523.00, 747.87)
    _mark_at(canvas, 523.00, 780.79)


def _draw_page_2(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw_at(canvas, values["monto"], 178.96, 184.48, 130, 9)
    _draw_at(canvas, values.get("provincia"), 403.91, 167.77, 100)
    armed = _date_parts(values.get("fecha_armado"))
    _draw_at(canvas, "/".join(part for part in armed if part), 500.0, 167.77, 75)
    words = values["monto_letras"]
    midpoint = min(len(words), 58)
    split = words.rfind(" ", 0, midpoint)
    split = split if split > 0 else midpoint
    _draw_at(canvas, words[:split], 331.70, 200.08, 220, 6.4)
    _draw_at(canvas, words[split:].strip(), 148.11, 216.42, 260, 7)
    _draw_at(canvas, values["nombre"], 421.69, 215.91, 150, 7.2)
    _draw_at(canvas, f"UN AUTOMOTOR: DOMINIO {values.get('dominio', '')} - MARCA {values.get('marca', '')}", 159.94, 273.72, 380, 6.5)
    _draw_at(canvas, f"TIPO {values.get('tipo_vehiculo', '')} - MODELO {values.get('modelo', '')}", 179.48, 287.09, 370, 6.5)
    _draw_at(canvas, f"MARCA MOTOR {values.get('marca_motor', '')} - NRO MOTOR {values.get('numero_motor', '')}", 181.02, 300.98, 360, 6.5)
    _draw_at(canvas, f"MARCA CHASIS {values.get('marca_chasis', '')} - NRO CHASIS {values.get('numero_chasis', '')}", 179.99, 314.87, 380, 6.5)
    _draw_at(canvas, f"AÑO {values.get('anio', '')} - USO {values.get('tipo_uso', '')}", 185.13, 329.27, 200, 6.8)
    _draw_at(canvas, values.get("provincia"), 293.64, 352.85, 100)
    _draw_at(canvas, values.get("partido"), 204.68, 366.22, 70)
    _draw_at(canvas, values.get("localidad"), 220.62, 385.08, 170, 6.8)
    _draw_at(canvas, values["domicilio_resumido"], 392.90, 385.08, 190, 5.7)
    _draw_at(canvas, "NINGUNO", 454.09, 352.85, 80)
    _draw_at(canvas, f"{values.get('plazo', '')} CUOTAS IGUALES, MENSUALES Y CONSECUTIVAS", 374.16, 413.17, 175, 6.7)
    _draw_at(canvas, values["cuota"], 550.27, 413.17, 45, 6.7)
    _draw_at(canvas, f"LA PRIMERA CUOTA VENCE EL DÍA {values['vencimiento']}", 401.47, 439.08, 190, 6.5)
    _draw_at(canvas, "Y LAS RESTANTES EL MISMO DÍA DE CADA MES SUBSIGUIENTE", 172.23, 446.31, 300, 6.5)
    _draw_at(canvas, values.get("tna"), 388.27, 470.42, 35, 8)
    _draw_at(canvas, values["nombre"], 449.98, 547.88, 130, 7)
    _draw_at(canvas, f"{values['estado_civil']} {values.get('profesion', '')}", 444.84, 560.37, 140, 6.6)
    _draw_at(canvas, values["nacionalidad"], 441.24, 574.78, 80, 6.8)
    _draw_at(canvas, values["edad"], 524.55, 574.78, 25, 6.8)
    _draw_at(canvas, values["domicilio_resumido"], 435.06, 587.65, 150, 5.5)
    _draw_at(canvas, values["dni"], 456.23, 601.57, 70, 6.5)
    _draw_at(canvas, values["cuil"], 444.84, 616.97, 90, 6.8)


def _draw_page_3(canvas: Canvas, values: dict[str, Any]) -> None:
    _draw_at(canvas, values.get("tna"), 411.25, 58.87, 30, 8.2)
    _draw_at(canvas, values.get("tea"), 132.22, 70.14, 35, 8)
    _draw_at(canvas, values.get("cftea"), 532.02, 68.82, 35, 8.2)
    if len(values["domicilio_completo"]) > 38:
        _draw_at(canvas, f"* CALLE: {values['domicilio_resumido']}", 256.10, 409.73, 290, 6.4, bold=True)
        _draw_at(canvas, f"* DOMICILIO: {values['domicilio_completo']}", 256.10, 422.58, 330, 5.4, bold=True)


def _draw_page_4(canvas: Canvas, values: dict[str, Any]) -> None:
    # ICBC is preprinted as creditor on this sheet; only the debtor is added.
    _draw_at(canvas, values["nombre"], 150.16, 122.75, 180, 7)
    _draw_at(canvas, values["domicilio_resumido"], 420.22, 890.07, 160, 5.8)
    _draw_at(canvas, values.get("localidad"), 115.77, 904.47, 210, 6)
    _draw_at(canvas, values.get("provincia"), 448.50, 904.47, 80, 6)


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
