import os

# Test environment must be pinned before app.config is imported; direct env
# vars outrank the .env file in pydantic-settings priority.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-0123456789"
os.environ["MONNIFY_API_KEY"] = "test-api-key"
os.environ["MONNIFY_SECRET_KEY"] = "test-monnify-secret"
os.environ["MONNIFY_CONTRACT_CODE"] = "0000000000"
os.environ["MONNIFY_BASE_URL"] = "https://sandbox.monnify.com"
os.environ["NVIDIA_API_KEY"] = ""

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from app.database import Base, engine
from app.main import app
from app.services.monnify import monnify_service

MONNIFY = "https://sandbox.monnify.com"


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _fresh_monnify_token():
    monnify_service._token = None
    monnify_service._token_expiry = None


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def monnify_mock():
    with respx.mock(assert_all_called=False) as mock:
        mock.post(f"{MONNIFY}/api/v1/auth/login").mock(
            return_value=Response(
                200, json={"responseBody": {"accessToken": "test-token"}}
            )
        )
        yield mock


# ── Helpers ───────────────────────────────────────────────────────────────────

def register(client, email="rep@example.com", full_name="Class Rep") -> dict:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": full_name},
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def create_community(client, headers, name="CSC 101") -> dict:
    resp = client.post("/communities", json={"name": name}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def add_roster(client, headers, community_id, names) -> list[dict]:
    resp = client.post(
        f"/communities/{community_id}/members/bulk",
        json={"members": [{"display_name": n} for n in names]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def create_collection(client, headers, community_id, amount=1000, **kwargs) -> dict:
    payload = {"title": "Departmental Dues", "amount_per_member": amount, **kwargs}
    resp = client.post(
        f"/communities/{community_id}/collections", json=payload, headers=headers
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def get_members(client, headers, community_id) -> list[dict]:
    resp = client.get(f"/communities/{community_id}/members", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


def get_entries(client, headers, collection_id) -> list[dict]:
    resp = client.get(f"/collections/{collection_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["entries"]


def get_balance(client, headers, community_id) -> float:
    resp = client.get(f"/communities/{community_id}/ledger", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["balance"]


def mark_paid(client, headers, collection_id, entry_id, channel="manual_cash", note=None):
    resp = client.post(
        f"/collections/{collection_id}/entries/{entry_id}/mark-paid",
        json={"channel": channel, "note": note},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()
