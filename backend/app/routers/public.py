from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import limiter
from app.database import get_db
from app.models import Collection
from app.schemas.payments import PayInitOut
from app.schemas.public import (
    GuestPayIn,
    PaymentFormIn,
    PublicCollectionOut,
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
    return PublicCollectionOut(
        id=collection.id,
        title=collection.title,
        description=collection.description,
        community_name=community.name,
        amount_per_member=collection.amount_per_member,
        target_amount=collection.target_amount,
        amount_collected=payments_service.total_collected(db, collection.id),
        deadline=collection.deadline,
        status=collection.status,
        custom_fields=collection.custom_fields,
    )


@router.post(
    "/collections/{share_token}/pay",
    status_code=status.HTTP_201_CREATED,
    response_model=PayInitOut,
)
@limiter.limit("10/minute")
async def public_pay(
    request: Request,
    share_token: str,
    body: GuestPayIn,
    db: Session = Depends(get_db),
):
    collection = collections_service.get_collection_by_share_token(db, share_token)
    payment = await payments_service.public_pay(
        db, collection, body.redirect_url, body.payer_email
    )
    return PayInitOut(
        checkout_url=payment.checkout_url,
        payment_reference=payment.payment_reference,
    )


def _public_payment_out(db: Session, payment) -> PublicPaymentOut:
    collection = db.get(Collection, payment.collection_id)
    return PublicPaymentOut(
        payment_reference=payment.payment_reference,
        status=payment.status,
        amount=payment.amount,
        paid_at=payment.paid_at,
        custom_fields=collection.custom_fields if collection else None,
        form_submitted=payment.form_submitted_at is not None,
    )


@router.get("/payments/{payment_reference}", response_model=PublicPaymentOut)
def public_payment_status(payment_reference: str, db: Session = Depends(get_db)):
    payment = payments_service.get_payment_by_reference(db, payment_reference)
    return _public_payment_out(db, payment)


@router.post("/payments/{payment_reference}/form", response_model=PublicPaymentOut)
@limiter.limit("10/minute")
async def submit_payment_form(
    request: Request, payment_reference: str, body: PaymentFormIn, db: Session = Depends(get_db)
):
    payment = payments_service.get_payment_by_reference(db, payment_reference)
    collection = db.get(Collection, payment.collection_id)
    payment = payments_service.submit_payment_form(db, payment, collection, body.values)
    return _public_payment_out(db, payment)


@router.post("/payments/{payment_reference}/sync", response_model=PublicPaymentOut)
async def public_payment_sync(payment_reference: str, db: Session = Depends(get_db)):
    """Called by the payment-return page so a guest's payment reflects
    immediately even when the webhook is delayed."""
    payment = payments_service.get_payment_by_reference(db, payment_reference)
    await payments_service.sync_payment(db, payment)
    db.refresh(payment)
    return _public_payment_out(db, payment)
