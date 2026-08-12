"""Asigna un color a cada cuenta bancaria vinculada: si el ASPSP coincide con
un banco conocido, usa (aproximadamente) su color de marca real; si no, cae a
una paleta fija elegida de forma determinista (mismo banco desconocido -> el
mismo color siempre), para poder distinguir cuentas en Movimientos.
"""

import hashlib

FALLBACK_PALETTE: list[str] = [
    "#6366F1", "#F97316", "#10B981", "#EC4899", "#0EA5E9",
    "#F59E0B", "#8B5CF6", "#14B8A6", "#EF4444", "#84CC16",
]

# Coincidencia por subcadena (minúsculas) sobre aspsp_name. No pretende ser
# una lista exhaustiva ni pixel-perfect, solo asociar cada banco a un color
# que lo recuerde a simple vista.
KNOWN_BANK_COLORS: list[tuple[str, str]] = [
    ("santander", "#EC0000"),
    ("bbva", "#004481"),
    ("caixabank", "#00AEEF"),
    ("la caixa", "#00AEEF"),
    ("sabadell", "#0099CC"),
    ("bankinter", "#FF6600"),
    ("ing", "#FF6200"),
    ("openbank", "#00AEEF"),
    ("unicaja", "#00953B"),
    ("kutxabank", "#E2001A"),
    ("abanca", "#0066B3"),
    ("ibercaja", "#003DA5"),
    ("evo banco", "#C6007E"),
    ("revolut", "#0666EB"),
    ("n26", "#36A18B"),
    ("wise", "#9FE870"),
    ("cofidis", "#E2001A"),
    ("cetelem", "#00A950"),
    ("bnp paribas", "#00915A"),
    ("deutsche bank", "#0018A8"),
    ("triodos", "#00A19A"),
    ("pibank", "#7B2FF7"),
    ("myinvestor", "#001489"),
    ("imagin", "#FF4D6D"),
]


def resolve_account_color(aspsp_name: str, seed: str) -> str:
    name = (aspsp_name or "").strip().lower()
    for needle, color in KNOWN_BANK_COLORS:
        if needle in name:
            return color
    index = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(FALLBACK_PALETTE)
    return FALLBACK_PALETTE[index]
