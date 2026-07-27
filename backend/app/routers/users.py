from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas.communities import CommunityOut
from app.services import communities as communities_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/communities", response_model=list[CommunityOut])
def my_communities(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return [
        communities_service.to_community_out(c)
        for c in communities_service.list_user_communities(db, current_user)
    ]
