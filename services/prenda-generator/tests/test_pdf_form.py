from io import BytesIO

from pypdf import PdfReader

from app.icbc_pdf import fill_icbc, values_from_icbc_form
from app.pdf_form import (
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
    assert reader.get_fields() is None
    assert "/AcroForm" not in reader.trailer["/Root"]
    assert all(
        annotation.get_object().get("/Subtype") != "/Widget"
        for page in reader.pages
        for annotation in page.get("/Annots", [])
    )


def test_second_printable_page_is_shifted_five_mm_down():
    assert round(SECOND_PRINTABLE_PAGE_OFFSET_Y, 4) == round(-5 * 72 / 25.4, 4)


def test_icbc_packet_has_four_static_a4_pages():
    values = values_from_icbc_form({
        "nombre": "Franco Pablo Alejandro",
        "dni": 28024038,
        "cuil": 23280240389,
        "bruto": 32336964.92,
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
    assert all(round(float(page.mediabox.width), 1) == 595.0 for page in reader.pages)
    assert all(round(float(page.mediabox.height), 1) == 842.0 for page in reader.pages)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "30-70944784-6" in text
    assert "$1.347.333,55" in text
    assert "8305" in text
