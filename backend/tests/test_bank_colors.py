from app.bank_colors import FALLBACK_PALETTE, resolve_account_color


def test_known_bank_returns_its_brand_color_case_insensitively():
    assert resolve_account_color("BBVA", "seed-1") == "#004481"
    assert resolve_account_color("Banco Santander, S.A.", "seed-2") == "#EC0000"


def test_unknown_bank_falls_back_to_a_deterministic_palette_color():
    color_a = resolve_account_color("Banco Rural Desconocido", "acc-123")
    color_b = resolve_account_color("Banco Rural Desconocido", "acc-123")
    assert color_a == color_b
    assert color_a in FALLBACK_PALETTE


def test_different_seeds_can_get_different_fallback_colors():
    colors = {resolve_account_color("Banco Ignoto", f"acc-{i}") for i in range(20)}
    assert len(colors) > 1
