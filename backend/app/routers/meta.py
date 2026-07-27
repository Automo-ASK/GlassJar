import time

from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.errors import GatewayError
from app.schemas.expenses import AccountLookupOut, BankOut
from app.services.monnify import MonnifyError, monnify_service

router = APIRouter(prefix="/meta", tags=["meta"])

_banks_cache: dict = {"at": None, "data": None}
_CACHE_TTL_SECONDS = 24 * 60 * 60


@router.get("/banks", response_model=list[BankOut])
async def list_banks(_=Depends(get_current_user)):
    now = time.monotonic()
    if _banks_cache["data"] is not None and now - _banks_cache["at"] < _CACHE_TTL_SECONDS:
        return _banks_cache["data"]

    try:
        raw = await monnify_service.get_banks()
        banks = [
            BankOut(code=b["code"], name=b["name"])
            for b in raw
            if b.get("code") and b.get("name")
        ]
    except MonnifyError as e:
        raise GatewayError(f"Could not load bank list: {e.message}")

    _banks_cache["data"] = banks
    _banks_cache["at"] = now
    return banks


@router.get("/banks/resolve", response_model=AccountLookupOut)
async def resolve_account(account_number: str, bank_code: str, _=Depends(get_current_user)):
    try:
        result = await monnify_service.validate_account(account_number, bank_code)
    except MonnifyError as e:
        raise GatewayError(f"Could not resolve this account: {e.message}")
    return AccountLookupOut(
        account_number=result.get("accountNumber", account_number),
        account_name=result.get("accountName", ""),
        bank_code=result.get("bankCode", bank_code),
    )
