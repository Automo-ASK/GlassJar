from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import assert_role, get_collection_context, get_current_user
from app.database import get_db
from app.models import Collection, Member, MemberRole, Payment, User
from app.schemas.collections import EntryOut
from app.schemas.payments import PayInitIn, PayInitOut
from app.services import collections as collections_service
from app.services import payments as payments_service

router = APIRouter(tags=["payments"])


@router.post(
    "/collections/{collection_id}/pay",
    status_code=status.HTTP_201_CREATED,
    response_model=PayInitOut,
)
async def initiate_payment(
    body: PayInitIn,
    context=Depends(get_collection_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection, _ = context
    payment = await payments_service.member_pay(
        db, current_user, collection, body.redirect_url
    )
    return PayInitOut(
        checkout_url=payment.checkout_url,
        payment_reference=payment.payment_reference,
    )


@router.post("/payments/{payment_id}/sync")
async def sync_payment(
    payment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    collection = db.get(Collection, payment.collection_id)
    membership = (
        db.query(Member)
        .filter(
            Member.community_id == collection.community_id,
            Member.user_id == current_user.id,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Not a community member")
    assert_role(membership, [MemberRole.ADMIN])
    result = await payments_service.sync_payment(db, payment)
    return {"status": result}


@router.get("/collections/{collection_id}/payments/me", response_model=EntryOut)
def my_payment_status(
    context=Depends(get_collection_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    collection, _ = context
    entry, display_name = payments_service.get_my_entry(db, current_user, collection)
    return collections_service.entry_out(entry, display_name)
