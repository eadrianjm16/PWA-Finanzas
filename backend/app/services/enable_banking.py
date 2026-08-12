from datetime import date, datetime, timedelta, timezone

import httpx

from ..security import make_eb_application_token

BASE_URL = "https://api.enablebanking.com"

# Orden de preferencia de saldo: primero un disponible real con retenciones ya
# descontadas (codigos ISO 20022 BalanceStatus XPCD/ITAV/CLAV/OPAV); si el banco
# no los expone -como Santander via Enable Banking, que solo da OPBD/CLBD-,
# caemos al saldo contable acumulado (CLBD) en vez del de apertura del dia (OPBD).
BALANCE_PRIORITY = ["XPCD", "ITAV", "CLAV", "OPAV", "CLBD"]


class EnableBankingError(Exception):
    def __init__(self, status: int, body: str, retry_after_seconds: int | None = None):
        self.status = status
        self.body = body
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Enable Banking error {status}: {body}")


def pick_available_balance(balances: list[dict]) -> dict | None:
    for balance_type in BALANCE_PRIORITY:
        for balance in balances:
            if balance.get("balance_type") == balance_type:
                return balance
    return balances[0] if balances else None


class EnableBankingClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {make_eb_application_token()}",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        headers = kwargs.pop("headers", {})
        headers.update(self._headers())
        try:
            response = await self._client.request(method, path, headers=headers, **kwargs)
        except httpx.HTTPError as error:
            raise EnableBankingError(502, f"No se pudo contactar con Enable Banking: {error}") from error
        if not (200 <= response.status_code < 300):
            retry_after = None
            raw_retry_after = response.headers.get("Retry-After")
            if raw_retry_after and raw_retry_after.isdigit():
                retry_after = int(raw_retry_after)
            raise EnableBankingError(response.status_code, response.text, retry_after_seconds=retry_after)
        return response.json()

    async def list_aspsps(self, country: str | None = None) -> list[dict]:
        params = {"country": country} if country else None
        data = await self._request("GET", "/aspsps", params=params)
        return data["aspsps"]

    async def start_authorization(self, aspsp: dict, state: str, redirect_url: str) -> str:
        valid_until = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        body = {
            "access": {"valid_until": valid_until, "balances": True, "transactions": True},
            "aspsp": aspsp,
            "state": state,
            "redirect_url": redirect_url,
            "psu_type": "personal",
        }
        data = await self._request("POST", "/auth", json=body)
        return data["url"]

    async def create_session(self, code: str) -> dict:
        return await self._request("POST", "/sessions", json={"code": code})

    async def fetch_balances(self, account_uid: str) -> list[dict]:
        data = await self._request("GET", f"/accounts/{account_uid}/balances")
        return data["balances"]

    async def fetch_transactions_page(
        self,
        account_uid: str,
        date_from: date | None = None,
        date_to: date | None = None,
        continuation_key: str | None = None,
    ) -> tuple[list[dict], str | None]:
        params: dict[str, str] = {}
        if date_from:
            params["date_from"] = date_from.strftime("%Y-%m-%d")
        if date_to:
            params["date_to"] = date_to.strftime("%Y-%m-%d")
        if continuation_key:
            params["continuation_key"] = continuation_key
        data = await self._request("GET", f"/accounts/{account_uid}/transactions", params=params)
        return data["transactions"], data.get("continuation_key")

    async def fetch_all_transactions(
        self, account_uid: str, date_from: date | None = None, date_to: date | None = None
    ) -> list[dict]:
        all_transactions: list[dict] = []
        continuation_key: str | None = None
        while True:
            page, continuation_key = await self.fetch_transactions_page(
                account_uid, date_from, date_to, continuation_key
            )
            all_transactions += page
            if not continuation_key:
                break
        return all_transactions
