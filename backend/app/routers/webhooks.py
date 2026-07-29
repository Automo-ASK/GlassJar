import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import payments as payments_service
from app.services.flutterwave import flutterwave_service
from app.services.monnify import MonnifyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/flutterwave", status_code=status.HTTP_200_OK)
async def flutterwave_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()

    signature = request.headers.get("flutterwave-signature")
    if not signature or not flutterwave_service.verify_webhook_signature(raw_body, signature):
        logger.warning(
            "flutterwave webhook signature mismatch: body_len=%d headers=%s",
            len(raw_body), dict(request.headers),
        )
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "invalid_json"}

    outcome = await payments_service.handle_webhook(db, payload, raw_body)
    logger.info("flutterwave webhook outcome: %s", outcome)
    return {"status": outcome}


@router.post("/monnify", status_code=status.HTTP_200_OK)
async def monnify_webhook(request: Request, db: Session = Depends(get_db)):
    """Dormant — kept only so a rollback to Monnify doesn't need this route
    re-added. Flutterwave (above) is the active payment rail."""
    raw_body = await request.body()

    signature = request.headers.get("monnify-signature")
    if signature and not MonnifyService.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "invalid_json"}

    logger.info("monnify webhook received but this rail is inactive — ignoring")
    return {"status": "ignored_inactive_rail"}
