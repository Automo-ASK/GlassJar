from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import assert_role, get_expense_context, get_membership, require_community_role
from app.database import get_db
from app.models import ExpenseStatus, Member, MemberRole
from app.schemas.expenses import (
    DecisionIn,
    ExpenseCreateIn,
    ExpenseOut,
    LedgerEntryOut,
    LedgerResponse,
    MarkPaidOutIn,
)
from app.services import expenses as expenses_service
from app.services import ledger as ledger_service

router = APIRouter(tags=["expenses"])

MANAGERS = [MemberRole.ADMIN, MemberRole.TREASURER]


@router.post(
    "/communities/{community_id}/expenses",
    status_code=status.HTTP_201_CREATED,
    response_model=ExpenseOut,
)
def create_expense(
    community_id: int,
    body: ExpenseCreateIn,
    membership: Member = Depends(require_community_role(MANAGERS)),
    db: Session = Depends(get_db),
):
    return expenses_service.create_expense(db, membership, body)


@router.get("/communities/{community_id}/expenses", response_model=list[ExpenseOut])
def list_expenses(
    community_id: int,
    status_filter: Optional[ExpenseStatus] = Query(default=None, alias="status"),
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    return expenses_service.list_expenses(db, community_id, status_filter)


@router.post("/expenses/{expense_id}/approve", response_model=ExpenseOut)
def approve_expense(
    body: DecisionIn,
    context=Depends(get_expense_context),
    db: Session = Depends(get_db),
):
    expense, membership = context
    assert_role(membership, [MemberRole.AUDITOR])
    return expenses_service.approve(db, membership, expense, body.note)


@router.post("/expenses/{expense_id}/reject", response_model=ExpenseOut)
def reject_expense(
    body: DecisionIn,
    context=Depends(get_expense_context),
    db: Session = Depends(get_db),
):
    expense, membership = context
    assert_role(membership, [MemberRole.AUDITOR])
    return expenses_service.reject(db, membership, expense, body.note)


@router.post("/expenses/{expense_id}/mark-paid-out", response_model=ExpenseOut)
def mark_expense_paid_out(
    body: MarkPaidOutIn,
    context=Depends(get_expense_context),
    db: Session = Depends(get_db),
):
    expense, membership = context
    assert_role(membership, MANAGERS)
    return expenses_service.mark_paid_out(db, membership, expense, body.payout_reference)


@router.get("/communities/{community_id}/ledger", response_model=LedgerResponse)
def community_ledger(
    community_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    entries, total = ledger_service.list_entries(db, community_id, skip, limit)
    return LedgerResponse(
        entries=[LedgerEntryOut.model_validate(e) for e in entries],
        balance=ledger_service.get_balance(db, community_id),
        total=total,
    )
