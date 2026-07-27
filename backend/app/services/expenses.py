from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    ForbiddenError,
    InvalidInputError,
    NotFoundError,
)
from app.core.money import to_money
from app.models import Expense, ExpenseStatus, Member
from app.schemas.expenses import ExpenseCreateIn
from app.services import audit, ledger


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None:
        raise NotFoundError("Expense not found")
    return expense


def create_expense(db: Session, actor: Member, data: ExpenseCreateIn) -> Expense:
    expense = Expense(
        community_id=actor.community_id,
        collection_id=data.collection_id,
        title=data.title.strip(),
        amount=to_money(data.amount),
        category=data.category,
        receipt_url=data.receipt_url,
        requested_by=actor.user_id,
        destination_bank_name=data.destination_bank_name,
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
    return expense


def _decide(
    db: Session,
    actor: Member,
    expense: Expense,
    new_status: ExpenseStatus,
    note: Optional[str],
) -> Expense:
    if expense.status != ExpenseStatus.PENDING:
        raise ConflictError("Expense has already been decided")
    if expense.requested_by == actor.user_id:
        raise ForbiddenError("You cannot decide your own expense request")

    expense.status = new_status
    expense.approved_by = actor.user_id
    expense.decision_note = note
    expense.decided_at = _now()
    audit.log(
        db,
        community_id=expense.community_id,
        actor_user_id=actor.user_id,
        action=f"expense_{new_status.value}",
        entity_type="expense",
        entity_id=expense.id,
        data={"note": note},
    )
    db.commit()
    db.refresh(expense)
    return expense


def approve(db: Session, actor: Member, expense: Expense, note: Optional[str]) -> Expense:
    return _decide(db, actor, expense, ExpenseStatus.APPROVED, note)


def reject(db: Session, actor: Member, expense: Expense, note: Optional[str]) -> Expense:
    return _decide(db, actor, expense, ExpenseStatus.REJECTED, note)


def mark_paid_out(
    db: Session, actor: Member, expense: Expense, payout_reference: str
) -> Expense:
    if expense.status != ExpenseStatus.APPROVED:
        raise ConflictError("Only approved expenses can be paid out")
    balance = ledger.get_balance(db, expense.community_id)
    if expense.amount > balance:
        raise InvalidInputError(
            f"Insufficient treasury balance ({balance}) for this payout"
        )

    expense.status = ExpenseStatus.PAID_OUT
    expense.payout_reference = payout_reference
    expense.paid_out_at = _now()
    expense.paid_out_by = actor.user_id

    ledger.record_debit(
        db,
        community_id=expense.community_id,
        amount=expense.amount,
        reference_type="expense",
        reference_id=expense.id,
        description=f"Expense payout: {expense.title} ({payout_reference})",
    )
    audit.log(
        db,
        community_id=expense.community_id,
        actor_user_id=actor.user_id,
        action="expense_paid_out",
        entity_type="expense",
        entity_id=expense.id,
        data={"payout_reference": payout_reference},
    )
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
