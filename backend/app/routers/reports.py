from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.deps import get_membership
from app.core.rate_limit import limiter
from app.database import get_db
from app.models import Member
from app.schemas.reports import CommunityDashboardOut, TransparencyReportOut
from app.services import reports as reports_service

router = APIRouter(tags=["reports"])


@router.get(
    "/collections/{collection_id}/transparency", response_model=TransparencyReportOut
)
@limiter.limit("30/minute")
def transparency_report(
    request: Request, collection_id: int, db: Session = Depends(get_db)
):
    """Public accountability report — intentionally unauthenticated."""
    return reports_service.transparency_report(db, collection_id)


@router.get("/communities/{community_id}/dashboard", response_model=CommunityDashboardOut)
def community_dashboard(
    community_id: int,
    membership: Member = Depends(get_membership),
    db: Session = Depends(get_db),
):
    return reports_service.community_dashboard(db, community_id)
