import base64
import hashlib
import hmac
import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Nigerian bank codes for the disbursement bank-select dropdown. Flutterwave
# v4's bank-list endpoint isn't documented for us yet, so this mirrors the
# same fallback approach used elsewhere (a small hardcoded list of the major
# NG banks) rather than guessing at an unverified endpoint shape.
FALLBACK_BANKS = [
    {"code": "044", "name": "Access Bank"},
    {"code": "023", "name": "Citibank"},
    {"code": "050", "name": "Ecobank Nigeria"},
    {"code": "070", "name": "Fidelity Bank"},
    {"code": "011", "name": "First Bank of Nigeria"},
    {"code": "214", "name": "First City Monument Bank"},
    {"code": "058", "name": "Guaranty Trust Bank"},
    {"code": "030", "name": "Heritage Bank"},
    {"code": "301", "name": "Jaiz Bank"},
    {"code": "082", "name": "Keystone Bank"},
    {"code": "50515", "name": "Moniepoint MFB"},
    {"code": "076", "name": "Polaris Bank"},
    {"code": "101", "name": "Providus Bank"},
    {"code": "221", "name": "Stanbic IBTC Bank"},
    {"code": "068", "name": "Standard Chartered"},
    {"code": "232", "name": "Sterling Bank"},
    {"code": "033", "name": "United Bank For Africa"},
    {"code": "032", "name": "Union Bank"},
    {"code": "035", "name": "Wema Bank"},
    {"code": "057", "name": "Zenith Bank"},
    {"code": "999992", "name": "OPay"},
    {"code": "999991", "name": "PalmPay"},
    {"code": "50211", "name": "Kuda Bank"},
]


class FlutterwaveError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Flutterwave {status_code}: {message}")


class FlutterwaveService:
    def __init__(self):
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    async def _get_access_token(self, force_refresh: bool = False) -> str:
        now = datetime.now(timezone.utc)
        if (
            not force_refresh
            and self._token
            and self._token_expiry
            and now < self._token_expiry
        ):
            return self._token

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                settings.flutterwave_idp_url,
                data={
                    "client_id": settings.flutterwave_client_id,
                    "client_secret": settings.flutterwave_client_secret,
                    "grant_type": "client_credentials",
                },
            )
        if resp.status_code != 200:
            raise FlutterwaveError(resp.status_code, resp.text)

        body = resp.json()
        self._token = body["access_token"]
        # Flutterwave tokens live 10 minutes — refresh a minute early.
        expires_in = int(body.get("expires_in", 600))
        buffer_seconds = min(60, max(expires_in - 30, 0))
        self._token_expiry = now + timedelta(seconds=expires_in - buffer_seconds)
        return self._token

    def _headers(self, idempotency_key: Optional[str], token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Trace-Id": uuid.uuid4().hex,
            "X-Idempotency-Key": idempotency_key or uuid.uuid4().hex,
        }

    async def _authed_request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
    ) -> httpx.Response:
        token = await self._get_access_token()
        url = f"{settings.flutterwave_base_url}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method, url, headers=self._headers(idempotency_key, token), json=json, params=params
            )
        if resp.status_code == 401:
            token = await self._get_access_token(force_refresh=True)
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method, url, headers=self._headers(idempotency_key, token), json=json, params=params
                )
        if resp.status_code >= 400:
            logger.warning(
                "flutterwave %s %s -> %d: %s", method, path, resp.status_code, resp.text[:500]
            )
        return resp

    # ── Collection: customer + dynamic virtual account ──────────────────────

    async def create_customer(self, email: str, name: Optional[str] = None) -> dict:
        first, _, last = (name or "Guest").strip().partition(" ")
        resp = await self._authed_request(
            "POST",
            "/customers",
            json={
                "email": email,
                "name": {"first": first or "Guest", "last": last or first or "Payer"},
            },
        )
        if resp.status_code not in (200, 201):
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    async def create_virtual_account(
        self,
        *,
        reference: str,
        amount: Decimal,
        customer_id: str,
        narration: str,
        expiry_seconds: int = 1800,
    ) -> dict:
        """Dynamic (one-time) virtual account for a single payment. The payer
        transfers to it directly; `charge.completed` webhook confirms,
        keyed by our `reference`. No BVN required."""
        body = {
            "reference": reference,
            "customer_id": customer_id,
            "amount": float(amount),
            "currency": "NGN",
            "account_type": "dynamic",
            "expiry": max(60, min(expiry_seconds, 31536000)),
            "narration": narration[:100],
        }
        if settings.flutterwave_preferred_bank_code:
            body["bank_code"] = settings.flutterwave_preferred_bank_code
        resp = await self._authed_request(
            "POST", "/virtual-accounts", json=body, idempotency_key=reference
        )
        if resp.status_code not in (200, 201):
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    async def get_charge(self, charge_id: str) -> dict:
        resp = await self._authed_request("GET", f"/charges/{charge_id}")
        if resp.status_code != 200:
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    # ── Disbursement (expense payouts) ───────────────────────────────────────

    async def get_banks(self) -> list[dict]:
        try:
            resp = await self._authed_request("GET", "/banks", params={"country": "NG"})
            if resp.status_code != 200:
                return FALLBACK_BANKS
            raw = resp.json().get("data", [])
            banks = [
                {"code": b["code"], "name": b["name"]}
                for b in raw
                if b.get("code") and b.get("name")
            ]
            return banks or FALLBACK_BANKS
        except (httpx.HTTPError, KeyError, ValueError):
            return FALLBACK_BANKS

    async def validate_account(self, account_number: str, bank_code: str) -> dict:
        """Name enquiry: resolve the account holder's name for a bank +
        account number, so the payer can confirm before money moves."""
        resp = await self._authed_request(
            "POST",
            "/banks/account-resolve",
            json={
                "currency": "NGN",
                "account": {"code": bank_code, "number": account_number},
            },
        )
        if resp.status_code != 200:
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    async def initiate_transfer(
        self,
        *,
        amount: Decimal,
        reference: str,
        narration: str,
        bank_code: str,
        account_number: str,
    ) -> dict:
        resp = await self._authed_request(
            "POST",
            "/direct-transfers",
            json={
                "action": "instant",
                "type": "bank",
                "narration": narration[:100],
                "reference": reference,
                "payment_instruction": {
                    "amount": {"value": float(amount), "applies_to": "destination_currency"},
                    "source_currency": "NGN",
                    "destination_currency": "NGN",
                    "recipient": {
                        "bank": {"code": bank_code, "account_number": account_number},
                    },
                },
            },
            idempotency_key=reference,
        )
        if resp.status_code not in (200, 201):
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    async def get_transfer(self, transfer_id: str) -> dict:
        resp = await self._authed_request("GET", f"/transfers/{transfer_id}")
        if resp.status_code != 200:
            raise FlutterwaveError(resp.status_code, resp.text)
        return resp.json()["data"]

    # ── Webhooks ──────────────────────────────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
        # HMAC-SHA256(secretHash, rawBody), base64-encoded, compared to the
        # `flutterwave-signature` header.
        computed = hmac.new(
            settings.flutterwave_webhook_secret_hash.encode(), raw_body, hashlib.sha256
        ).digest()
        computed_b64 = base64.b64encode(computed).decode()
        return hmac.compare_digest(computed_b64, signature)


flutterwave_service = FlutterwaveService()
