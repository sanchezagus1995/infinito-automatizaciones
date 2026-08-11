from io import BytesIO

from pypdf import PdfReader

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
    for field in (reader.get_fields() or {}).values():
        if field.get("/FT") == "/Tx":
            assert int(field.get("/Ff", 0)) & 16777216 == 0


def test_second_printable_page_is_shifted_five_mm_down():
    assert round(SECOND_PRINTABLE_PAGE_OFFSET_Y, 4) == round(-5 * 72 / 25.4, 4)
