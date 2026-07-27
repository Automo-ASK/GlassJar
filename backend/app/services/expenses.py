import json
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, GatewayError, InvalidInputError, NotFoundError
from app.core.money import to_money
from app.models import Expense, ExpenseStatus, Member
from app.schemas.expenses import ExpenseCreateIn
from app.services import audit, ledger
from app.services.monnify import MonnifyError, monnify_service

SUCCESS_STATUSES = {"SUCCESS", "SUCCESSFUL", "COMPLETED"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _friendly_monnify_error(raw_text: str) -> str:
    """Monnify error bodies are JSON with a responseMessage — surface that
    instead of a raw HTTP body dump when we can parse it."""
    try:
        body = json.loads(raw_text)
    except (ValueError, TypeError):
        return raw_text[:300]
    if isinstance(body, dict) and body.get("responseMessage"):
        return str(body["responseMessage"])
    return raw_text[:300]


def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


def _check_balance(db: Session, expense: Expense) -> None:
    balance = ledger.get_balance(db, expense.community_id)
    if expense.amount > balance:
        raise InvalidInputError(
            f"Insufficient treasury balance ({balance}) for this payout"
        )


def _complete_payout(db: Session, actor: Member, expense: Expense, reference: str) -> None:
    expense.status = ExpenseStatus.PAID_OUT
    expense.payout_reference = reference
    expense.paid_out_at = _now()
    expense.paid_out_by = actor.user_id
    ledger.record_debit(
        db,
        community_id=expense.community_id,
        amount=expense.amount,
        reference_type="expense",
        reference_id=expense.id,
        description=f"Expense payout: {expense.title} ({reference})",
    )
    audit.log(
        db,
        community_id=expense.community_id,
        actor_user_id=actor.user_id,
        action="expense_paid_out",
        entity_type="expense",
        entity_id=expense.id,
        data={"payout_reference": reference, "manual": expense.manual_payout},
    )


async def _attempt_disbursement(db: Session, actor: Member, expense: Expense) -> Expense:
    """Fire a Monnify disbursement for a PENDING or FAILED expense. Always
    leaves the expense in a terminal-for-now state: PAID_OUT, AWAITING_OTP,
    or FAILED — never raises, so create-and-pay never blocks on a gateway
    hiccup once the expense itself is safely recorded."""
    reference = f"acafund-exp-{expense.id}-{uuid4().hex[:8]}"
    narration = expense.title[:100]
    try:
        result = await monnify_service.disburse_single(
            amount=expense.amount,
            reference=reference,
            narration=narration,
            destination_bank_code=expense.destination_bank_code,
            destination_account_number=expense.destination_account_number,
            destination_account_name=expense.destination_account_name,
        )
    except MonnifyError as e:
        expense.status = ExpenseStatus.FAILED
        expense.payout_reference = reference
        expense.payout_error = _friendly_monnify_error(e.message)
        expense.raw_payout_payload = {"error": e.message}
        db.commit()
        db.refresh(expense)
        return expense

    monnify_status = result.get("status")
    expense.payout_reference = result.get("reference") or reference
    expense.raw_payout_payload = result

    if monnify_status in SUCCESS_STATUSES:
        expense.payout_error = None
        _complete_payout(db, actor, expense, expense.payout_reference)
    elif monnify_status == "PENDING_AUTHORIZATION":
        expense.status = ExpenseStatus.AWAITING_OTP
        expense.payout_error = None
        audit.log(
            db,
            community_id=expense.community_id,
            actor_user_id=actor.user_id,
            action="expense_payout_awaiting_otp",
            entity_type="expense",
            entity_id=expense.id,
        )
    else:
        expense.status = ExpenseStatus.FAILED
        expense.payout_error = (
            result.get("responseMessage") or f"Unexpected status from Monnify: {monnify_status or 'unknown'}"
        )

    db.commit()
    db.refresh(expense)
    return expense


async def create_expense(db: Session, actor: Member, data: ExpenseCreateIn) -> Expense:
    expense = Expense(
        community_id=actor.community_id,
        collection_id=data.collection_id,
        title=data.title.strip(),
        amount=to_money(data.amount),
        category=data.category,
        receipt_url=data.receipt_url,
        requested_by=actor.user_id,
        destination_bank_name=data.destination_bank_name,
        destination_bank_code=data.destination_bank_code,
        destination_account_number=data.destination_account_number,
        destination_account_name=data.destination_account_name,
    )
    db.add(expense)
    db.flush()
    audit.log(
        db,
        community_id=actor.community_id,
        actor_user_id=actor.user_id,
        action="expense_created",
        entity_type="expense",
        entity_id=expense.id,
        data={"amount": float(expense.amount)},
    )
    db.commit()
    db.refresh(expense)

    try:
        _check_balance(db, expense)
    except InvalidInputError as exc:
        expense.status = ExpenseStatus.FAILED
        expense.payout_error = exc.detail
        db.commit()
        db.refresh(expense)
        return expense

    return await _attempt_disbursement(db, actor, expense)


async def retry_payout(db: Session, actor: Member, expense: Expense) -> Expense:
    if expense.status != ExpenseStatus.FAILED:
        raise ConflictError("Only a failed payout can be retried")
    _check_balance(db, expense)
    return await _attempt_disbursement(db, actor, expense)


async def authorize_payout(db: Session, actor: Member, expense: Expense, otp: str) -> Expense:
    if expense.status != ExpenseStatus.AWAITING_OTP:
        raise ConflictError("This expense is not awaiting an authorization code")
    try:
        result = await monnify_service.authorize_transfer(expense.payout_reference, otp)
    except MonnifyError as e:
        raise GatewayError(f"Could not authorize transfer: {e.message}")

    monnify_status = result.get("status")
    if monnify_status not in SUCCESS_STATUSES:
        raise InvalidInputError(
            f"Authorization was not accepted (status: {monnify_status or 'unknown'})"
        )
    expense.raw_payout_payload = result
    _complete_payout(db, actor, expense, result.get("reference") or expense.payout_reference)
    db.commit()
    db.refresh(expense)
    return expense


async def resend_payout_otp(db: Session, expense: Expense) -> None:
    if expense.status != ExpenseStatus.AWAITING_OTP:
        raise ConflictError("This expense is not awaiting an authorization code")
    try:
        await monnify_service.resend_transfer_otp(expense.payout_reference)
    except MonnifyError as e:
        raise GatewayError(f"Could not resend code: {e.message}")


def mark_paid_manually(
    db: Session, actor: Member, expense: Expense, payout_reference: str
) -> Expense:
    """Fallback for when the automated transfer can't be used (e.g. Monnify
    disbursement isn't enabled on this account yet) — the treasurer sent the
    money themselves and is just recording proof of it."""
    if expense.status not in (ExpenseStatus.FAILED, ExpenseStatus.PENDING):
        raise ConflictError("Only a pending or failed expense can be recorded manually")
    _check_balance(db, expense)
    expense.manual_payout = True
    expense.payout_error = None
    _complete_payout(db, actor, expense, payout_reference)
    db.commit()
    db.refresh(expense)
    return expense


def list_expenses(
    db: Session, community_id: int, status: Optional[ExpenseStatus] = None
) -> list[Expense]:
    query = db.query(Expense).filter(Expense.community_id == community_id)
    if status is not None:
        query = query.filter(Expense.status == status)
    return query.order_by(Expense.created_at.desc()).all()
