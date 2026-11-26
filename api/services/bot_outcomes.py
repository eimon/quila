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
}


def bot_failure(reason: BotFailureReason) -> BotFailure:
    return BotFailure(reason=reason, message=FAILURE_MESSAGES[reason])
