import json

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import GatewayError
from app.models import Expense, ExpenseStatus, LedgerEntry
from app.services.collections import active_collection_summaries
from app.services.ledger import get_balance

_SYSTEM_PROMPT = """\
You are a treasury assistant for an GlassJar community savings group.
Answer questions ONLY from the financial context provided. If the context
does not contain enough information to answer, say so explicitly — never
guess or invent a number. Be concise and direct."""

NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/llama-3.3-nemotron-super-49b-v1"


def _build_context(db: Session, community_id: int) -> dict:
    balance = get_balance(db, community_id)

    recent_entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.community_id == community_id)
        .order_by(LedgerEntry.created_at.desc())
        .limit(10)
        .all()
    )

    collections_summary = [
        s.model_dump(mode="json")
        for s in active_collection_summaries(db, community_id)
    ]

    pending_expenses = (
        db.query(Expense)
        .filter(
            Expense.community_id == community_id,
            Expense.status.in_([ExpenseStatus.PENDING, ExpenseStatus.AWAITING_OTP]),
        )
        .all()
    )

    return {
        "balance": balance,
        "recent_ledger": [
            {
                "type": e.type,
                "amount": e.amount,
                "description": e.description,
                "created_at": str(e.created_at),
            }
            for e in recent_entries
        ],
        "active_collections": collections_summary,
        "pending_expenses": [
            {
                "id": e.id,
                "title": e.title,
                "amount": e.amount,
                "category": e.category,
            }
            for e in pending_expenses
        ],
    }


async def ask_treasury_assistant(db: Session, community_id: int, question: str) -> str:
    if not settings.nvidia_api_key:
        raise GatewayError("Treasury assistant is not configured")

    context = _build_context(db, community_id)
    user_content = (
        f"Community Treasury Context:\n"
        f"{json.dumps(context, default=str, indent=2)}\n\n"
        f"Question: {question}"
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            NVIDIA_URL,
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 1024,
                "temperature": 0.2,
            },
        )

    if resp.status_code != 200:
        raise GatewayError(f"Assistant API error {resp.status_code}")

    return resp.json()["choices"][0]["message"]["content"]
