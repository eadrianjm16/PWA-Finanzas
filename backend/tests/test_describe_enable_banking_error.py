from app.services.enable_banking import EnableBankingError
from app.services.sync import describe_enable_banking_error


def test_401_asks_to_reconnect_the_bank():
    message = describe_enable_banking_error(EnableBankingError(401, "unauthorized"))
    assert "reautorizar" in message


def test_429_with_retry_after_gives_a_precise_wait_time():
    message = describe_enable_banking_error(EnableBankingError(429, "too many requests", retry_after_seconds=300))
    assert "5 min" in message


def test_429_without_retry_after_explains_the_daily_limit():
    message = describe_enable_banking_error(EnableBankingError(429, "too many requests"))
    assert "limitando" in message
    assert "veces al día" in message


def test_5xx_suggests_trying_later():
    message = describe_enable_banking_error(EnableBankingError(503, "service unavailable"))
    assert "más tarde" in message


def test_unknown_status_falls_back_to_a_generic_message():
    message = describe_enable_banking_error(EnableBankingError(418, "teapot"))
    assert message == "No se pudo sincronizar con el banco"
