from tests.conftest import (
    add_roster,
    create_collection,
    create_community,
    get_balance,
    get_entries,
    mark_paid,
    register,
)
from tests.test_payments import mock_init, mock_verify, post_webhook


def setup(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi"])
    collection = create_collection(client, rep, community["id"], amount=1000)
    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    return rep, community, collection, ada


def test_mark_paid_cash_credits_ledger(client):
    rep, community, collection, ada = setup(client)
    entry = mark_paid(client, rep, collection["id"], ada["id"], note="paid in class")
    assert entry["status"] == "paid"
    assert entry["note"] == "paid in class"
    assert get_balance(client, rep, community["id"]) == 1000.0


def test_mark_paid_requires_manager_role(client):
    rep, community, collection, ada = setup(client)
    other = register(client, "o@example.com", "O")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=other,
    )
    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/mark-paid",
        json={"channel": "manual_cash"},
        headers=other,
    )
    assert resp.status_code == 403


def test_mark_paid_rejects_checkout_channel(client):
    rep, _, collection, ada = setup(client)
    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/mark-paid",
        json={"channel": "checkout"},
        headers=rep,
    )
    assert resp.status_code == 422


def test_waive_and_revert(client):
    rep, _, collection, ada = setup(client)
    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/waive",
        json={"note": "hardship"},
        headers=rep,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "waived"

    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/revert",
        json={},
        headers=rep,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


def test_waive_non_pending_conflicts(client):
    rep, _, collection, ada = setup(client)
    mark_paid(client, rep, collection["id"], ada["id"])
    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/waive",
        json={},
        headers=rep,
    )
    assert resp.status_code == 409


def test_revert_manual_payment_writes_reversing_debit(client):
    rep, community, collection, ada = setup(client)
    mark_paid(client, rep, collection["id"], ada["id"])
    assert get_balance(client, rep, community["id"]) == 1000.0

    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/revert",
        json={"note": "marked wrong person"},
        headers=rep,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    assert get_balance(client, rep, community["id"]) == 0.0

    ledger = client.get(f"/communities/{community['id']}/ledger", headers=rep).json()
    assert ledger["total"] == 2  # credit + reversing debit, history preserved


def test_revert_gateway_payment_blocked(client, monnify_mock):
    rep, community, collection, ada = setup(client)

    mock_init(monnify_mock)
    pay = client.post(
        f"/public/collections/{collection['share_token']}/entries/{ada['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    ).json()
    mock_verify(monnify_mock)
    post_webhook(
        client,
        {"transactionReference": "MNFY|TX|9", "paymentReference": pay["payment_reference"]},
    )

    resp = client.post(
        f"/collections/{collection['id']}/entries/{ada['id']}/revert",
        json={},
        headers=rep,
    )
    assert resp.status_code == 409
