from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import CollectionEntry, Member
from app.schemas.payments import PayInitOut
from app.schemas.public import (
    GuestPayIn,
    PublicCollectionOut,
    PublicEntryOut,
    PublicPaymentOut,
)
from app.services import collections as collections_service
from app.services import communities as communities_service
from app.services import payments as payments_service

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/collections/{share_token}", response_model=PublicCollectionOut)
def public_collection(share_token: str, db: Session = Depends(get_db)):
    collection = collections_service.get_collection_by_share_token(db, share_token)
    community = communities_service.get_community(db, collection.community_id)
    rows = (
        db.query(CollectionEntry, Member.display_name)
        .join(Member, CollectionEntry.member_id == Member.id)
        .filter(CollectionEntry.collection_id == collection.id)
        .order_by(Member.display_name)
        .all()
    )
    return PublicCollectionOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        community_name=community.name,
        amount_per_member=collection.amount_per_member,
        deadline=collection.deadline,
        status=collection.status,
        entries=[
            PublicEntryOut(id=e.id, display_name=name, status=e.status)
            for e, name in rows
        ],
    )


@router.post(
    "/collections/{share_token}/entries/{entry_id}/pay",
    status_code=status.HTTP_201_CREATED,
    response_model=PayInitOut,
)
async def guest_pay(
    share_token: str,
    entry_id: int,
    body: GuestPayIn,
    db: Session = Depends(get_db),
):
    collection = collections_service.get_collection_by_share_token(db, share_token)
    payment = await payments_service.guest_pay(
        db, collection, entry_id, body.redirect_url, body.payer_email
    )
    return PayInitOut(
        checkout_url=payment.checkout_url,
        payment_reference=payment.payment_reference,
    )


@router.get("/payments/{payment_reference}", response_model=PublicPaymentOut)
def public_payment_status(payment_reference: str, db: Session = Depends(get_db)):
    payment = payments_service.get_payment_by_reference(db, payment_reference)
    return PublicPaymentOut(
        payment_reference=payment.payment_reference,
        status=payment.status,
        amount=payment.amount,
        paid_at=payment.paid_at,
    )


@router.post("/payments/{payment_reference}/sync", response_model=PublicPaymentOut)
async def public_payment_sync(payment_reference: str, db: Session = Depends(get_db)):
    """Called by the payment-return page so a guest's payment reflects
    immediately even when the webhook is delayed."""
    payment = payments_service.get_payment_by_reference(db, payment_reference)
    await payments_service.sync_payment(db, payment)
    db.refresh(payment)
    return PublicPaymentOut(
        payment_reference=payment.payment_reference,
        status=payment.status,
        amount=payment.amount,
        paid_at=payment.paid_at,
    )
