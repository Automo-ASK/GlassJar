from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import assert_role, get_collection_context, require_community_role
from app.database import get_db
from app.models import CollectionEntry, Member, MemberRole
from app.schemas.collections import (
    CollectionCreateIn,
    CollectionDashboardOut,
    CollectionDetailOut,
    CollectionOut,
    CollectionResponsesOut,
    EntryOut,
)
from app.schemas.payments import ManualMarkIn, NoteIn
from app.services import collections as collections_service
from app.services import payments as payments_service

router = APIRouter(tags=["collections"])

MANAGERS = [MemberRole.ADMIN, MemberRole.TREASURER]


@router.post(
    "/communities/{community_id}/collections",
    status_code=status.HTTP_201_CREATED,
    response_model=CollectionOut,
)
def create_collection(
    community_id: int,
    body: CollectionCreateIn,
    membership: Member = Depends(require_community_role(MANAGERS)),
    db: Session = Depends(get_db),
):
    return collections_service.create_collection(db, membership, body)


@router.get(
    "/communities/{community_id}/collections", response_model=list[CollectionOut]
)
def list_collections(
    community_id: int,
    membership: Member = Depends(require_community_role(list(MemberRole))),
    db: Session = Depends(get_db),
):
    return collections_service.list_collections(db, community_id)


@router.get("/collections/{collection_id}", response_model=CollectionDetailOut)
def get_collection(
    context=Depends(get_collection_context), db: Session = Depends(get_db)
):
    collection, _ = context
    return collections_service.detail_out(db, collection)


@router.get(
    "/collections/{collection_id}/dashboard", response_model=CollectionDashboardOut
)
def collection_dashboard(
    context=Depends(get_collection_context), db: Session = Depends(get_db)
):
    collection, _ = context
    return collections_service.dashboard(db, collection)


@router.patch("/collections/{collection_id}/close", response_model=CollectionOut)
def close_collection(
    context=Depends(get_collection_context), db: Session = Depends(get_db)
):
    collection, membership = context
    assert_role(membership, [MemberRole.ADMIN])
    return collections_service.close_collection(db, membership, collection)


@router.get(
    "/collections/{collection_id}/responses", response_model=CollectionResponsesOut
)
def collection_responses(
    context=Depends(get_collection_context), db: Session = Depends(get_db)
):
    collection, membership = context
    assert_role(membership, MANAGERS)
    return CollectionResponsesOut(
        custom_fields=collection.custom_fields or [],
        responses=collections_service.list_anonymous_payments(db, collection),
    )


@router.post("/collections/{collection_id}/entries/sync")
def sync_entries(context=Depends(get_collection_context), db: Session = Depends(get_db)):
    collection, membership = context
    assert_role(membership, MANAGERS)
    added = collections_service.sync_entries(db, membership, collection)
    return {"added": added}


def _get_entry(db: Session, collection_id: int, entry_id: int) -> CollectionEntry:
    entry = db.get(CollectionEntry, entry_id)
    if entry is None or entry.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


def _entry_response(db: Session, entry: CollectionEntry) -> EntryOut:
    member = db.get(Member, entry.member_id)
    return collections_service.entry_out(entry, member.display_name)


@router.post(
    "/collections/{collection_id}/entries/{entry_id}/mark-paid",
    response_model=EntryOut,
)
def mark_entry_paid(
    entry_id: int,
    body: ManualMarkIn,
    context=Depends(get_collection_context),
    db: Session = Depends(get_db),
):
    collection, membership = context
    assert_role(membership, MANAGERS)
    entry = _get_entry(db, collection.id, entry_id)
    payments_service.mark_paid_manual(db, membership, collection, entry, body)
    return _entry_response(db, entry)


@router.post(
    "/collections/{collection_id}/entries/{entry_id}/waive", response_model=EntryOut
)
def waive_entry(
    entry_id: int,
    body: NoteIn,
    context=Depends(get_collection_context),
    db: Session = Depends(get_db),
):
    collection, membership = context
    assert_role(membership, [MemberRole.ADMIN])
    entry = _get_entry(db, collection.id, entry_id)
    payments_service.waive_entry(db, membership, collection, entry, body.note)
    return _entry_response(db, entry)


@router.post(
    "/collections/{collection_id}/entries/{entry_id}/revert", response_model=EntryOut
)
def revert_entry(
    entry_id: int,
    body: NoteIn,
    context=Depends(get_collection_context),
    db: Session = Depends(get_db),
):
    collection, membership = context
    assert_role(membership, MANAGERS)
    entry = _get_entry(db, collection.id, entry_id)
    payments_service.revert_entry(db, membership, collection, entry, body.note)
    return _entry_response(db, entry)
