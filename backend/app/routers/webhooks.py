import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import payments as payments_service
from app.services.monnify import MonnifyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/monnify", status_code=status.HTTP_200_OK)
async def monnify_webhook(request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()

    # Monnify's sandbox omits the signature header; validate when present.
    signature = request.headers.get("monnify-signature")
    if signature and not MonnifyService.verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {"status": "invalid_json"}

    outcome = await payments_service.handle_webhook(db, payload, raw_body)
    logger.info("monnify webhook outcome: %s", outcome)
    return {"status": outcome}
