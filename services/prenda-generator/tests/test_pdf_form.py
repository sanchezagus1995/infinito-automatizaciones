from app.pdf_form import money, money_words, values_from_form


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
