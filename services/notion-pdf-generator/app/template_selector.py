from __future__ import annotations


class UnsupportedOperation(ValueError):
    pass


EXTERNAL_INSURANCE_BANKS = {"CREDITCAR", "NUESTRA PAMPA SA"}
UVA_BANKS = {"BBVA", "SUPERVIELLE"}


def select_variant(banks: list[str], rate_type: str) -> str:
    normalized = {bank.strip().upper() for bank in banks if bank}
    if not normalized:
        raise UnsupportedOperation("La operación no tiene una entidad financiera")
    if len(normalized) != 1:
        raise UnsupportedOperation(f"Se esperaba una sola entidad financiera: {sorted(normalized)}")

    bank = next(iter(normalized))
    is_uva = "UVA" in (rate_type or "").upper()
    if bank in EXTERNAL_INSURANCE_BANKS:
        return "seguro_externo"
    if is_uva and bank in UVA_BANKS:
        return f"uva_{bank.lower()}"
    return "estandar"
