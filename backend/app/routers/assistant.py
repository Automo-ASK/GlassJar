from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_membership
from app.database import get_db
from app.models import Member
from app.schemas.assistant import AskIn, AskOut
from app.services.assistant import ask_treasury_assistant

router = APIRouter(tags=["assistant"])


@router.post("/communities/{community_id}/assistant/ask", response_model=AskOut)
async def ask(
    community_id: int,
    body: AskIn,
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    answer = await ask_treasury_assistant(db, community_id, body.question)
    return AskOut(answer=answer)
