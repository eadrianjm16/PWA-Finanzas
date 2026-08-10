"""Sugiere una categoria para un movimiento bancario.

Enable Banking no categoriza gastos: solo da merchant_category_code (a menudo
ausente) y texto libre en remittance_information. Este es un motor de reglas
propio: codigo MCC primero (mas fiable cuando esta presente), palabras clave
como fallback, y "Otros" si nada coincide. Nunca se aplica sobre un movimiento
que el usuario ya categorizo a mano (ver services/sync.py).
"""

from .default_categories import OTROS_NAME

_MCC_TABLE: dict[str, str] = {
    "5411": "Alimentación", "5422": "Alimentación", "5462": "Alimentación",
    "5499": "Alimentación", "5451": "Alimentación",
    "5812": "Restaurantes", "5813": "Restaurantes", "5814": "Restaurantes",
    "4111": "Transporte", "4121": "Transporte", "5541": "Transporte",
    "5542": "Transporte", "4112": "Transporte", "7523": "Transporte",
    "4900": "Suministros", "4899": "Suministros",
    "8011": "Salud", "8021": "Salud", "8062": "Salud", "5912": "Salud",
    "7832": "Ocio", "7922": "Ocio", "7996": "Ocio", "7995": "Ocio",
    "5311": "Compras", "5651": "Compras", "5691": "Compras", "5999": "Compras",
    "5964": "Compras", "5732": "Compras",
}

# Orden importa: la primera regla que coincida gana. Transporte va antes que
# Alimentacion a proposito -gasolineras de marca de supermercado deben caer
# en Transporte, no en Alimentacion por culpa de la marca-.
_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["UBER", "CABIFY", "BOLT", "RENFE", "METRO", "EMT", "REPSOL", "CEPSA", "BP ", "SHELL", "GASOLIN"], "Transporte"),
    (["MERCADONA", "CARREFOUR", "LIDL", "DIA ", "ALCAMPO", "EROSKI", "AHORRAMAS"], "Alimentación"),
    ([
        "NETFLIX", "SPOTIFY", "HBO", "DISNEY+", "PRIME VIDEO", "APPLE.COM/BILL", "YOUTUBE PREMIUM",
        "ANTHROPIC", "CLAUDE", "OPENAI", "CHATGPT", "WWW.USE.AI", "AMAZON PRIME",
    ], "Suscripciones"),
    (["COMISION", "MANTENIMIENTO CUENTA", "CUOTA TARJETA", "COMISIÓN"], "Comisiones bancarias"),
    (["FARMACIA", "SEGURO SALUD", "CLINICA", "CLÍNICA", "MUTUA", "VETERINAR"], "Salud"),
    (["AMAZON", "EL CORTE INGLES", "EL CORTE INGLÉS", "ZARA", "IKEA"], "Compras"),
    (["ALQUILER", "COMUNIDAD PROPIETARIOS", "HIPOTECA"], "Vivienda/Hogar"),
    (["IBERDROLA", "ENDESA", "NATURGY", "VODAFONE", "MOVISTAR", "ORANGE", "JAZZTEL", "DIGI"], "Suministros"),
    (["HOTEL", "TRAVELODGE", "AIRBNB", "BOOKING.COM"], "Ocio"),
    (["NOMINA", "NÓMINA", "PAYROLL", "SALARIO"], "Nómina/Ingresos"),
]

_PAYROLL_KEYWORDS = next(keywords for keywords, category in _KEYWORD_RULES if category == "Nómina/Ingresos")


def suggest_category(mcc: str | None, remittance_information: str, credit_debit_indicator: str) -> str:
    upper_info = remittance_information.upper()

    if credit_debit_indicator == "CRDT" and any(keyword in upper_info for keyword in _PAYROLL_KEYWORDS):
        return "Nómina/Ingresos"

    if mcc and mcc in _MCC_TABLE:
        return _MCC_TABLE[mcc]

    for keywords, category in _KEYWORD_RULES:
        if category == "Nómina/Ingresos":
            continue
        if any(keyword in upper_info for keyword in keywords):
            return category

    return OTROS_NAME
