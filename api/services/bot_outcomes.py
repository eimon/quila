from collections.abc import Sequence
from typing import Any

from core.enums import BotFailureReason
from schemas.bot import BotFailure

# Spanish messages the chatbot can relay to the guest
FAILURE_MESSAGES: dict[BotFailureReason, str] = {
    BotFailureReason.UNAVAILABLE: "La cabaña no está disponible en esas fechas.",
    BotFailureReason.OVER_CAPACITY: "La cabaña no admite esa cantidad de huéspedes.",
    BotFailureReason.INVALID_DATES: (
        "Las fechas no son válidas: el check-in no puede ser en el pasado "
        "y el check-out debe ser posterior al check-in."
    ),
    BotFailureReason.PROPERTY_NOT_FOUND: "No encontramos esa cabaña.",
    BotFailureReason.CAPACITY_UNKNOWN: (
        "Todavía no tenemos cargada la capacidad de esta cabaña; un asesor te va a ayudar."
    ),
    BotFailureReason.INVALID_INPUT: (
        "La solicitud no tiene un formato válido: se espera un JSON con los datos de la consulta."
    ),
}


def bot_failure(reason: BotFailureReason) -> BotFailure:
    return BotFailure(reason=reason, message=FAILURE_MESSAGES[reason])


def _invalid_field(loc: Sequence[Any]) -> str | None:
    """Field path of a body validation error (`("body", "check_in")` -> `check_in`)."""
    parts = [str(p) for p in loc[1:]] if loc and loc[0] == "body" else [str(p) for p in loc]
    # JSON syntax errors point at a character offset, not at a field
    if not parts or all(p.isdigit() for p in parts):
        return None
    return ".".join(parts)


def invalid_input_failure(errors: Sequence[dict]) -> BotFailure:
    """`invalid_input` failure naming the invalid fields, so the bot can fix its arguments."""
    fields = list(dict.fromkeys(f for f in (_invalid_field(e.get("loc", ())) for e in errors) if f))
    if not fields:
        return bot_failure(BotFailureReason.INVALID_INPUT)
    return BotFailure(
        reason=BotFailureReason.INVALID_INPUT,
        message=(
            f"Hay datos inválidos o faltantes: {', '.join(fields)}. "
            "Las fechas van en formato YYYY-MM-DD y la cantidad de huéspedes es un número mayor a 0."
        ),
    )
