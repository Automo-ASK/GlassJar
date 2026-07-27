from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_token_payload
from app.core.rate_limit import limiter
from app.database import get_db
from app.models import User
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenOut)
@limiter.limit("5/minute")
def register(request: Request, body: RegisterIn, db: Session = Depends(get_db)):
    _, token = auth_service.register(db, body)
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")
def login(request: Request, body: LoginIn, db: Session = Depends(get_db)):
    _, token = auth_service.login(db, body)
    return TokenOut(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)
):
    auth_service.logout(db, payload)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
