from tests.conftest import (
    add_roster,
    create_collection,
    create_community,
    get_entries,
    mark_paid,
    register,
)
from tests.test_payments import mock_init, mock_verify


def setup_shared_collection(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi"])
    collection = create_collection(client, rep, community["id"], amount=1000)
    return rep, community, collection


def test_public_collection_page_requires_no_auth(client):
    rep, _, collection = setup_shared_collection(client)
    resp = client.get(f"/public/collections/{collection['share_token']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Departmental Dues"
    assert body["community_name"] == "CSC 101"
    assert body["amount_per_member"] == 1000.0
    assert {e["display_name"] for e in body["entries"]} == {"Ada Obi", "Class Rep"}

    assert client.get("/public/collections/not-a-token").status_code == 404


def test_guest_pay_initiates_checkout(client, monnify_mock):
    rep, _, collection = setup_shared_collection(client)
    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")

    mock_init(monnify_mock)
    resp = client.post(
        f"/public/collections/{collection['share_token']}/entries/{ada['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["checkout_url"]


def test_guest_pay_rejected_when_not_pending(client, monnify_mock):
    rep, _, collection = setup_shared_collection(client)
    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    mark_paid(client, rep, collection["id"], ada["id"])

    resp = client.post(
        f"/public/collections/{collection['share_token']}/entries/{ada['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    )
    assert resp.status_code == 400


def test_public_payment_status_and_sync(client, monnify_mock):
    rep, _, collection = setup_shared_collection(client)
    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")

    mock_init(monnify_mock)
    pay = client.post(
        f"/public/collections/{collection['share_token']}/entries/{ada['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    ).json()
    ref = pay["payment_reference"]

    resp = client.get(f"/public/payments/{ref}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"

    mock_verify(monnify_mock)
    resp = client.post(f"/public/payments/{ref}/sync")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paid"

    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    assert ada["status"] == "paid"
