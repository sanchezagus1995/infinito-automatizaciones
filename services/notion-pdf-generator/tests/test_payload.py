from app.notion_payload import operation_from_webhook
from app.template_selector import select_variant

def prop(kind, value):
    if kind in {"title", "rich_text"}:
        return {"type": kind, kind: [{"plain_text": value}]}
    if kind == "multi_select":
        return {"type": kind, kind: [{"name": item} for item in value]}
    if kind == "date":
        return {"type": kind, kind: {"start": value}}
    return {"type": kind, kind: value}


def test_real_webhook_is_normalized():
    payload = {"data": {"id": "3b0778b5-53db-8172-abf4-f44d70228fb9", "properties": {
        "Nro op": prop("rich_text", "3025690"),
        "Banco": prop("multi_select", ["COLUMBIA"]),
        "Neto": prop("number", 7000000),
        "Fecha armada": prop("date", "2026-08-04"),
    }}}
    operation = operation_from_webhook(payload)
    assert operation["nro_op"] == "3025690"
    assert operation["banco"] == "COLUMBIA"
    assert operation["neto"] == "7.000.000"
    assert operation["fecha_armado"] == "04/08/2026"


def test_template_selection_is_exclusive():
    assert select_variant(["CREDITCAR"], "TRADICIONAL") == "seguro_externo"
    assert select_variant(["Nuestra Pampa SA"], "TRADICIONAL") == "seguro_externo"
    assert select_variant(["COLUMBIA"], "TRADICIONAL") == "estandar"
    assert select_variant(["BBVA"], "UVA") == "uva_bbva"
