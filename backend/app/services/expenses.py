from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.core.money import to_money
from app.models import Expense, ExpenseStatus, Member
from app.schemas.expenses import ExpenseCreateIn
from app.services import audit, ledger
from app.services.flutterwave import FlutterwaveError, flutterwave_service

SUCCESS_STATUSES = {"SUCCESS", "SUCCESSFUL", "COMPLETED"}
# Flutterwave transfers start here and only reach a terminal state once the
# transfer.disburse webhook arrives — there's no synchronous OTP step here
# the way Monnify had.
IN_FLIGHT_STATUSES = {"NEW", "PENDING", "PROCESSING"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


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


def _complete_payout(db: Session, actor_user_id: int, expense: Expense, reference: str) -> None:
    expense.status = ExpenseStatus.PAID_OUT
    expense.payout_reference = reference
    expense.paid_out_at = _now()
    expense.paid_out_by = actor_user_id
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
        actor_user_id=actor_user_id,
        action="expense_paid_out",
        entity_type="expense",
        entity_id=expense.id,
        data={"payout_reference": reference, "manual": expense.manual_payout},
    )


async def _attempt_disbursement(db: Session, actor: Member, expense: Expense) -> Expense:
    """Fire a Flutterwave transfer for a PENDING or FAILED expense. Leaves
    the expense PENDING (awaiting the transfer.disburse webhook) on a normal
    in-flight response, or FAILED if the gateway rejects it outright —
    create-and-pay never blocks on a gateway hiccup once the expense itself
    is safely recorded."""
    reference = f"GlassJar-exp-{expense.id}-{uuid4().hex[:8]}"
    narration = expense.title[:100]
    try:
        result = await flutterwave_service.initiate_transfer(
            amount=expense.amount,
            reference=reference,
            narration=narration,
            bank_code=expense.destination_bank_code,
            account_number=expense.destination_account_number,
        )
    except FlutterwaveError as e:
        expense.status = ExpenseStatus.FAILED
        expense.payout_reference = reference
        expense.payout_error = e.message[:300]
        expense.raw_payout_payload = {"error": e.message}
        db.commit()
        db.refresh(expense)
        return expense

    flw_status = str(result.get("status", "")).upper()
    expense.payout_reference = result.get("reference") or reference
    expense.flw_transfer_id = result.get("id")
    expense.raw_payout_payload = result

    if flw_status in SUCCESS_STATUSES:
        expense.payout_error = None
        _complete_payout(db, actor.user_id, expense, expense.payout_reference)
    elif flw_status in IN_FLIGHT_STATUSES:
        expense.status = ExpenseStatus.PENDING
        expense.payout_error = None
    else:
        expense.status = ExpenseStatus.FAILED
        provider_message = result.get("provider_response", {}).get("message")
        expense.payout_error = (
            provider_message or f"Unexpected status from Flutterwave: {flw_status or 'unknown'}"
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


def process_transfer_webhook(db: Session, data: dict) -> str:
    """Handle a `transfer.disburse` / `transfer.reversal` webhook — the only
    way a Flutterwave payout reaches a terminal state after initiation."""
    reference = data.get("reference")
    if not reference:
        return "ignored"
    expense = (
        db.query(Expense).filter(Expense.payout_reference == reference).first()
    )
    if expense is None:
        return "ignored"
    if expense.status == ExpenseStatus.PAID_OUT:
        return "already_paid"

    flw_status = str(data.get("status", "")).upper()
    expense.raw_payout_payload = data
    expense.flw_transfer_id = data.get("id") or expense.flw_transfer_id

    if flw_status in SUCCESS_STATUSES:
        expense.payout_error = None
        _complete_payout(db, expense.requested_by, expense, reference)
    elif flw_status in IN_FLIGHT_STATUSES:
        return "still_pending"
    else:
        expense.status = ExpenseStatus.FAILED
        provider_message = data.get("provider_response", {}).get("message")
        expense.payout_error = (
            provider_message or f"Transfer failed (status: {flw_status or 'unknown'})"
        )

    db.commit()
    return "ok"


def mark_paid_manually(
    db: Session, actor: Member, expense: Expense, payout_reference: str
) -> Expense:
    """Fallback for when the automated transfer can't be used (e.g.
    disbursement isn't enabled on this account yet) — the treasurer sent the
    money themselves and is just recording proof of it."""
    if expense.status not in (ExpenseStatus.FAILED, ExpenseStatus.PENDING):
        raise ConflictError("Only a pending or failed expense can be recorded manually")
    _check_balance(db, expense)
    expense.manual_payout = True
    expense.payout_error = None
    _complete_payout(db, actor.user_id, expense, payout_reference)
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
