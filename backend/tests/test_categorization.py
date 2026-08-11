from app.categorization import suggest_category
from app.default_categories import OTROS_NAME


def test_mcc_takes_priority_over_keywords():
    assert suggest_category(mcc="5812", remittance_information="MERCADONA MADRID", credit_debit_indicator="DBIT") == "Restaurantes"


def test_transporte_keyword_wins_over_alimentacion_for_branded_gas_stations():
    # Una gasolinera de marca de supermercado no debe caer en Alimentacion.
    assert suggest_category(mcc=None, remittance_information="MERCADONA GASOLINERA", credit_debit_indicator="DBIT") == "Transporte"


def test_keyword_fallback_when_no_mcc():
    assert suggest_category(mcc=None, remittance_information="NETFLIX.COM", credit_debit_indicator="DBIT") == "Suscripciones"


def test_payroll_only_detected_for_credit_transactions():
    assert suggest_category(mcc=None, remittance_information="NOMINA EMPRESA SL", credit_debit_indicator="CRDT") == "Nómina/Ingresos"
    # El mismo texto en un cargo (DBIT) no tiene sentido como nomina.
    assert suggest_category(mcc=None, remittance_information="NOMINA EMPRESA SL", credit_debit_indicator="DBIT") != "Nómina/Ingresos"


def test_unknown_transaction_falls_back_to_otros():
    assert suggest_category(mcc=None, remittance_information="ALGO COMPLETAMENTE DESCONOCIDO", credit_debit_indicator="DBIT") == OTROS_NAME


def test_unknown_mcc_falls_back_to_keywords():
    assert suggest_category(mcc="9999", remittance_information="UBER TRIP", credit_debit_indicator="DBIT") == "Transporte"
