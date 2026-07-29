import base64
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import httpx

from app.config import settings


class MonnifyError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Monnify {status_code}: {message}")


def _token_expired_response(resp: httpx.Response) -> bool:
    """True if Monnify rejected the request because our cached bearer token
    is expired/invalid — as opposed to any other 4xx/5xx failure."""
    if resp.status_code == 401:
        return True
    try:
        body = resp.json()
    except ValueError:
        return False
    return body.get("error") == "invalid_token" or "expired" in str(
        body.get("error_description", "")
    ).lower()


class MonnifyService:
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

        credentials = base64.b64encode(
            f"{settings.monnify_api_key}:{settings.monnify_secret_key}".encode()
        ).decode()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.monnify_base_url}/api/v1/auth/login",
                headers={"Authorization": f"Basic {credentials}"},
            )

        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)

        body = resp.json()["responseBody"]
        self._token = body["accessToken"]
        # Trust Monnify's own expiresIn (seconds) rather than assuming a fixed
        # lifetime — sandbox tokens can live far shorter than production ones.
        # Refresh 5 minutes early, floor at 1 minute so a tiny expiresIn still
        # gets some cache benefit instead of a negative/zero window.
        expires_in = int(body.get("expiresIn", 3600))
        buffer_seconds = min(300, max(expires_in - 60, 0))
        self._token_expiry = now + timedelta(seconds=expires_in - buffer_seconds)
        return self._token

    async def _authed_request(
        self, method: str, url: str, *, json: Optional[dict] = None, params: Optional[dict] = None
    ) -> httpx.Response:
        """POST/GET with a cached bearer token, retrying once with a forced
        fresh token if Monnify reports it expired mid-cache-window."""
        token = await self._get_access_token()
        async with httpx.AsyncClient() as client:
            resp = await client.request(
                method, url, headers={"Authorization": f"Bearer {token}"}, json=json, params=params
            )
        if _token_expired_response(resp):
            token = await self._get_access_token(force_refresh=True)
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    method, url, headers={"Authorization": f"Bearer {token}"}, json=json, params=params
                )
        return resp

    async def init_transaction(
        self,
        amount: Decimal,
        customer_name: str,
        customer_email: str,
        payment_reference: str,
        description: str,
        redirect_url: str,
    ) -> dict:
        resp = await self._authed_request(
            "POST",
            f"{settings.monnify_base_url}/api/v1/merchant/transactions/init-transaction",
            json={
                "amount": float(amount),
                "customerName": customer_name,
                "customerEmail": customer_email,
                "paymentReference": payment_reference,
                "paymentDescription": description,
                "currencyCode": "NGN",
                "contractCode": settings.monnify_contract_code,
                "redirectUrl": redirect_url,
            },
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    async def create_reserved_account(
        self,
        community_id: int,
        community_name: str,
    ) -> dict:
        """Create a dedicated reserved bank account for a community.

        No BVN required — mirrors linklock's working Monnify integration,
        which creates reserved accounts with just a name and email.

        Returns dict with keys: account_number, bank_name, account_name,
        status (lowercase).
        """
        account_reference = f"GlassJar-comm-{community_id}"
        customer_email = f"community-{community_id}@GlassJar.app"
        resp = await self._authed_request(
            "POST",
            f"{settings.monnify_base_url}/api/v2/bank-transfer/reserved-accounts",
            json={
                "accountReference": account_reference,
                "accountName": community_name,
                "currencyCode": "NGN",
                "contractCode": settings.monnify_contract_code,
                "customerEmail": customer_email,
                "customerName": community_name,
                "getAllAvailableBanks": True,
            },
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        body = resp.json()["responseBody"]
        accounts = body.get("accounts", [])
        first = accounts[0] if accounts else {}
        raw_status = body.get("status", "ACTIVE")
        return {
            "account_reference": account_reference,
            "account_number": first.get("accountNumber", ""),
            "bank_name": first.get("bankName", ""),
            "account_name": body.get("accountName", community_name),
            "status": raw_status.lower(),
        }

    async def verify_transaction(self, payment_reference: str) -> dict:
        resp = await self._authed_request(
            "GET",
            f"{settings.monnify_base_url}/api/v2/merchant/transactions/query",
            params={"paymentReference": payment_reference},
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    # ── Disbursement (expense payouts) ──────────────────────────────────────

    async def get_banks(self) -> list[dict]:
        resp = await self._authed_request(
            "GET", f"{settings.monnify_base_url}/api/v1/banks"
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    async def validate_account(self, account_number: str, bank_code: str) -> dict:
        """Name enquiry: resolve the account holder's name for a bank + account
        number, so the payer can confirm before money moves."""
        resp = await self._authed_request(
            "GET",
            f"{settings.monnify_base_url}/api/v2/disbursements/account/validate",
            params={"accountNumber": account_number, "bankCode": bank_code},
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    async def disburse_single(
        self,
        *,
        amount: Decimal,
        reference: str,
        narration: str,
        destination_bank_code: str,
        destination_account_number: str,
        destination_account_name: str,
    ) -> dict:
        """Send money out. Returns responseBody with `status` of SUCCESS/
        SUCCESSFUL/COMPLETED (done), PENDING_AUTHORIZATION (needs an OTP via
        authorize_transfer), or anything else (treat as failed)."""
        resp = await self._authed_request(
            "POST",
            f"{settings.monnify_base_url}/api/v2/disbursements/single",
            json={
                "amount": float(amount),
                "reference": reference,
                "narration": narration,
                "destinationBankCode": destination_bank_code,
                "destinationAccountNumber": destination_account_number,
                "destinationAccountName": destination_account_name,
                "currency": "NGN",
                "sourceAccountNumber": settings.monnify_wallet_account_number,
            },
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    async def authorize_transfer(self, reference: str, otp: str) -> dict:
        """Complete a PENDING_AUTHORIZATION disbursement with the OTP Monnify
        sent to the merchant's registered phone/email."""
        resp = await self._authed_request(
            "POST",
            f"{settings.monnify_base_url}/api/v2/disbursements/single/validate-otp",
            json={"reference": reference, "authorizationCode": otp},
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)
        return resp.json()["responseBody"]

    async def resend_transfer_otp(self, reference: str) -> None:
        resp = await self._authed_request(
            "POST",
            f"{settings.monnify_base_url}/api/v2/disbursements/single/resend-otp",
            json={"reference": reference},
        )
        if resp.status_code != 200:
            raise MonnifyError(resp.status_code, resp.text)

    @staticmethod
    def _compute_webhook_signature(raw_body: bytes) -> str:
        # Monnify signs webhooks as SHA-512(secretKey + rawBody)
        combined = settings.monnify_secret_key.encode() + raw_body
        return hashlib.sha512(combined).hexdigest()

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
        computed = MonnifyService._compute_webhook_signature(raw_body)
        return hmac.compare_digest(computed, signature.lower())


monnify_service = MonnifyService()
