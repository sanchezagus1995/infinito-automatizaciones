from io import BytesIO
import re

from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.icbc_pdf import fill_icbc, values_from_icbc_form
from app.pdf_form import (
    FINAL_WIDGET_RECTS,
    SECOND_PRINTABLE_PAGE_OFFSET_Y,
    fill_galicia,
    money,
    money_words,
    values_from_form,
)


def test_money_argentina():
    assert money(15345002.34) == "$15.345.002,34"
    assert money_words(15345002.34).endswith("CON 34/100")


def test_uva_and_cuil_mapping():
    values = values_from_form({
        "nombre": "Ana Pérez", "dni": 12345678, "cuil": 27123456786,
        "bruto": 1000000, "tna": 60, "tasa": "UVA", "estado_civil": "Soltero",
        "nacionalidad": "Argentina", "fecha_nacimiento": "1990-02-10",
        "fecha_armado": "2026-08-11", "fecha_vencimiento": "2026-09-10",
    })
    assert values["cuil"] == "27-12345678-6"
    assert values["monto uva"] == "$1.000.000,00"
    assert values["dia vto"] == "10"


def test_final_packet_has_five_printable_pages_and_normal_text_fields():
    values = values_from_form({
        "nombre": "Adriana Ramora",
        "dni": 20301230,
        "cuil": 20203012301,
        "bruto": 15345002.34,
        "tna": 60,
        "tasa": "Tradicional",
        "estado_civil": "Soltero",
        "nacionalidad": "Argentina",
        "fecha_nacimiento": "1980-02-10",
        "fecha_armado": "2026-08-11",
        "fecha_vencimiento": "2026-09-10",
        "marca": "Toyota",
        "modelo": "Corolla Cross XEI 2.0 CVT",
        "numero_motor": "M20A1234567",
        "numero_chasis": "9BRK43BE0R1234567",
    })
    reader = PdfReader(BytesIO(fill_galicia(values)))

    assert len(reader.pages) == 5
    for page in reader.pages:
        assert round(float(page.mediabox.width), 2) == 595.32
        assert round(float(page.mediabox.height), 2) == 841.92
    fields = reader.get_fields() or {}
    assert "/AcroForm" in reader.trailer["/Root"]
    assert fields
    assert any(
        annotation.get_object().get("/Subtype") == "/Widget"
        for page in reader.pages
        for annotation in page.get("/Annots", [])
    )
    assert all(
        annotation.get_object().get("/AP", {}).get_object().get("/N")
        for page in reader.pages
        for annotation in page.get("/Annots", [])
        if annotation.get_object().get("/Subtype") == "/Widget"
    )
    assert fields["nombre titular"]["/V"] == "ADRIANA RAMORA"
    for field in fields.values():
        if field.get("/FT") == "/Tx":
            assert int(field.get("/Ff", 0)) & 16777216 == 0

    actual_rects = set()
    for page_number, page in enumerate(reader.pages, 1):
        for annotation in page.get("/Annots", []):
            widget = annotation.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            parent_ref = widget.get("/Parent")
            parent = parent_ref.get_object() if parent_ref else None
            name = widget.get("/T") or (parent.get("/T") if parent else None)
            rect = tuple(round(float(value), 2) for value in widget.get("/Rect", []))
            actual_rects.add((page_number, str(name), rect))

    expected_rects = {
        (page_number, name, target_rect)
        for (page_number, name, _), target_rect in FINAL_WIDGET_RECTS.items()
    }
    assert len(FINAL_WIDGET_RECTS) == 41
    assert expected_rects <= actual_rects


def test_second_printable_page_is_shifted_five_mm_down():
    assert round(SECOND_PRINTABLE_PAGE_OFFSET_Y, 4) == round(-5 * 72 / 25.4, 4)


def test_long_galicia_text_adapts_to_each_widget_width():
    values = values_from_form({
        "nombre": "Ornela Ainara Leal",
        "dni": 12345678,
        "cuil": 27123456786,
        "bruto": 1000000,
        "tna": 60,
        "tasa": "Tradicional",
        "estado_civil": "Soltero",
        "nacionalidad": "Argentina",
        "fecha_nacimiento": "1990-02-10",
        "fecha_armado": "2026-08-18",
        "fecha_vencimiento": "2026-09-10",
        "localidad": "San Patricio del Chañar",
        "calle": "Rio Limay y Volcan Lanin Manzana D1 Casa N° 15",
        "dominio": "AH018XV",
    })
    reader = PdfReader(BytesIO(fill_galicia(values)))
    styles_by_name = {
        "localidad": [],
        "calle": [],
        "dominio": [],
        "monto de prenda en letras": [],
    }

    for page in reader.pages:
        for annotation in page.get("/Annots", []):
            widget = annotation.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            parent_ref = widget.get("/Parent")
            parent = parent_ref.get_object() if parent_ref else None
            target = parent if parent is not None else widget
            if target.get("/FT") != "/Tx":
                continue
            name = str(widget.get("/T") or (parent.get("/T") if parent else ""))
            appearance = widget["/AP"]["/N"].get_object().get_data().decode("latin-1")
            size_match = re.search(r"/Helv\s+([0-9.]+)\s+Tf", appearance)
            scale_match = re.search(r"([0-9.]+)\s+Tz", appearance)
            assert size_match, f"No se encontró el tamaño de fuente de {name}"
            assert scale_match, f"No se encontró la escala horizontal de {name}"
            size = float(size_match.group(1))
            horizontal_scale = float(scale_match.group(1))
            if name in styles_by_name:
                styles_by_name[name].append((size, horizontal_scale))

            rect = widget["/Rect"]
            available_width = abs(float(rect[2]) - float(rect[0])) - 4
            rendered_width = (
                stringWidth(values[name], "Helvetica", size) * horizontal_scale / 100
            )
            assert rendered_width <= available_width + 0.1
            assert size >= 8.0

    assert (10.0, 100.0) in styles_by_name["localidad"]
    assert (10.0, 100.0) in styles_by_name["calle"]
    assert set(styles_by_name["dominio"]) == {(10.0, 100.0)}
    assert set(styles_by_name["monto de prenda en letras"]) == {(10.0, 100.0)}


def test_icbc_packet_uses_manual_pledge_amount_and_oficio_continuation():
    values = values_from_icbc_form({
        "nombre": "Franco Pablo Alejandro",
        "dni": 28024038,
        "cuil": 23280240389,
        "bruto": 32336964.92,
        "monto_prenda": 19210000,
        "cuota": 1347333.55,
        "plazo": 24,
        "tna": 56,
        "tea": 72.48,
        "cftea": 83.05,
        "estado_civil": "Soltero",
        "nacionalidad": "Argentina",
        "fecha_nacimiento": "1980-04-09",
        "fecha_armado": "2026-08-12",
        "fecha_vencimiento": "2026-09-10",
        "calle": "Cuenca de los Barriales Mza E Casa 9",
        "piso_departamento": "225",
        "codigo_postal": "8305",
        "localidad": "San Patricio del Chañar",
        "partido": "Añelo",
        "provincia": "Neuquén",
        "dominio": "AH018XV",
        "marca": "Ford",
        "tipo_vehiculo": "Pick-up",
        "modelo": "Ranger DC XL 2.0L T 4X2 MTD",
        "marca_motor": "Ford",
        "numero_motor": "P02553434331",
        "marca_chasis": "Ford",
        "numero_chasis": "8AF6BA00H783434331",
        "anio": 2025,
        "tipo_uso": "Privado",
        "profesion": "Empleado",
    })
    reader = PdfReader(BytesIO(fill_icbc(values)))

    assert len(reader.pages) == 4
    assert reader.get_fields() is None
    assert all(round(float(page.mediabox.width), 1) == 595.0 for page in reader.pages[:3])
    assert all(round(float(page.mediabox.height), 1) == 842.0 for page in reader.pages[:3])
    assert round(float(reader.pages[3].mediabox.width), 1) == 612.0
    assert round(float(reader.pages[3].mediabox.height), 1) == 936.0
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "30-70944784-6" in text
    assert "$19.210.000,00" in text
    assert "$32.336.964,92" not in text
    assert "$1.347.333,55" in text
    assert "8305" in text
