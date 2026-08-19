from io import BytesIO

from pypdf import PdfReader
from reportlab.pdfbase.pdfmetrics import stringWidth

from app.icbc_pdf import fill_icbc, values_from_icbc_form
from app.galicia_layout import MARK_PLACEMENTS, STATIC_TEXT, TEXT_PLACEMENTS
from app.pdf_form import (
    _fit_text_style,
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
    assert values["TNA / 12"] == "5.00"


def test_final_packet_has_five_vector_pages_without_acroform_or_images():
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
    assert all(not page.get("/Annots") for page in reader.pages)
    assert all("/XObject" not in page["/Resources"] for page in reader.pages)
    assert all(b" BT" in page.get_contents().get_data() for page in reader.pages)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "ADRIANA RAMORA" in text
    assert "BANCO DE GALICIA Y BUENOS AIRES S.A.U." in text
    assert "$15.345.002,34" in text


def test_layout_is_the_physically_corrected_packet():
    assert len(TEXT_PLACEMENTS) == 76
    assert len(MARK_PLACEMENTS) == 5
    assert len(STATIC_TEXT) == 29
    fixed_marks = {
        (text, tuple(round(value, 4) for value in rect))
        for page, text, rect, _, _ in STATIC_TEXT
        if page == 1 and text in {"X", "1"}
    }
    assert fixed_marks == {
        ("X", (458.5725, 175.8862, 466.5645, 189.2782)),
        ("X", (516.8842, 82.6798, 524.8762, 96.0718)),
        ("X", (516.8842, 46.9968, 524.8762, 60.3888)),
        ("1", (377.0563, 71.3499, 383.7283, 84.7419)),
    }


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
    styles_by_name = {
        "localidad": [],
        "calle": [],
        "dominio": [],
        "monto de prenda en letras": [],
    }

    for _, name, rect in TEXT_PLACEMENTS:
        text = values[name]
        size, horizontal_scale = _fit_text_style(text, rect[2] - rect[0])
        if name in styles_by_name:
            styles_by_name[name].append((size, horizontal_scale))

        available_width = rect[2] - rect[0] - 4
        rendered_width = stringWidth(text, "Helvetica", size) * horizontal_scale / 100
        assert rendered_width <= available_width + 0.1
        assert size >= 8.0

    assert (10.0, 100.0) in styles_by_name["localidad"]
    assert (10.0, 100.0) in styles_by_name["calle"]
    assert set(styles_by_name["dominio"]) == {(10.0, 100.0)}
    assert set(styles_by_name["monto de prenda en letras"]) == {(10.0, 100.0)}

    reader = PdfReader(BytesIO(fill_galicia(values)))
    content = b"\n".join(page.get_contents().get_data() for page in reader.pages)
    assert b" Tz" in content
    assert b" Tj" in content


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
