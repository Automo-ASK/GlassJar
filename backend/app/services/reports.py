from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import EntryStatus, Expense, ExpenseStatus
from app.schemas.expenses import LedgerEntryOut
from app.schemas.reports import (
    CommunityDashboardOut,
    TransparencyExpenseOut,
    TransparencyReportOut,
)
from app.services import ledger
from app.services import payments as payments_service
from app.services.collections import (
    active_collection_summaries,
    entry_rollup,
    get_collection,
)
from app.services.communities import get_community, to_community_out

ZERO = Decimal("0.00")


def transparency_report(db: Session, collection_id: int) -> TransparencyReportOut:
    collection = get_collection(db, collection_id)
    community = get_community(db, collection.community_id)

    agg = entry_rollup(db, collection.id)
    paid_n, _ = agg.get(EntryStatus.PAID, (0, ZERO))
    pending_n, _ = agg.get(EntryStatus.PENDING, (0, ZERO))
    waived_n, _ = agg.get(EntryStatus.WAIVED, (0, ZERO))
    collected = payments_service.total_collected(db, collection.id)

    expenses = (
        db.query(Expense)
        .filter(Expense.community_id == community.id)
        .order_by(Expense.created_at.desc())
        .all()
    )

    return TransparencyReportOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        target_amount=collection.target_amount,
        amount_collected=collected,
        paid_count=paid_n,
        pending_count=pending_n,
        waived_count=waived_n,
        budget_allocation=collection.budget_allocation,
        expenses=[
            TransparencyExpenseOut(
                title=e.title,
                amount=e.amount,
                category=e.category,
                status=e.status,
                payout_reference=e.payout_reference,
                paid_out_at=e.paid_out_at,
            )
            for e in expenses
        ],
        reserved_account=to_community_out(community).reserved_account,
    )


def community_dashboard(db: Session, community_id: int) -> CommunityDashboardOut:
    balance = ledger.get_balance(db, community_id)
    summaries = active_collection_summaries(db, community_id)

    pending_expenses = (
        db.query(Expense)
        .filter(
            Expense.community_id == community_id,
            Expense.status.in_([ExpenseStatus.PENDING, ExpenseStatus.AWAITING_OTP]),
        )
        .count()
    )

    recent, _ = ledger.list_entries(db, community_id, skip=0, limit=10)
    return CommunityDashboardOut(
        treasury_balance=balance,
        active_collections=summaries,
        pending_expenses_count=pending_expenses,
        recent_ledger=[LedgerEntryOut.model_validate(e) for e in recent],
    )
