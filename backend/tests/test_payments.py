import hashlib
import json

from httpx import Response

from app.database import SessionLocal
from app.models import Payment
from tests.conftest import (
    MONNIFY,
    create_collection,
    create_community,
    get_balance,
    get_entries,
    register,
)

CHECKOUT_URL = "https://checkout.monnify.com/test"


def mock_init(monnify_mock, tx_ref="MNFY|TX|1"):
    monnify_mock.post(f"{MONNIFY}/api/v1/merchant/transactions/init-transaction").mock(
        return_value=Response(
            200,
            json={
                "responseBody": {
                    "checkoutUrl": CHECKOUT_URL,
                    "transactionReference": tx_ref,
                }
            },
        )
    )


def mock_verify(monnify_mock, status="PAID", amount=1000):
    monnify_mock.get(f"{MONNIFY}/api/v2/merchant/transactions/query").mock(
        return_value=Response(
            200,
            json={"responseBody": {"paymentStatus": status, "amountPaid": amount}},
        )
    )


def sign(raw: bytes) -> str:
    return hashlib.sha512(b"test-monnify-secret" + raw).hexdigest()


def post_webhook(client, payload, signature=None):
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signature is not None:
        headers["monnify-signature"] = signature
    return client.post("/webhooks/monnify", content=raw, headers=headers)


def setup_paying_member(client, monnify_mock):
    rep = register(client)
    community = create_community(client, rep)
    collection = create_collection(client, rep, community["id"], amount=1000)
    mock_init(monnify_mock)
    resp = client.post(
        f"/collections/{collection['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
        headers=rep,
    )
    assert resp.status_code == 201, resp.text
    return rep, community, collection, resp.json()


def test_member_pay_creates_checkout(client, monnify_mock):
    _, _, _, pay = setup_paying_member(client, monnify_mock)
    assert pay["checkout_url"] == CHECKOUT_URL
    assert pay["payment_reference"].startswith("GlassJar-")


def test_pay_reuses_inflight_checkout(client, monnify_mock):
    rep, _, collection, first = setup_paying_member(client, monnify_mock)
    resp = client.post(
        f"/collections/{collection['id']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
        headers=rep,
    )
    assert resp.status_code == 201
    assert resp.json()["payment_reference"] == first["payment_reference"]


def test_webhook_reconciles_payment(client, monnify_mock):
    rep, community, collection, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock)

    resp = post_webhook(
        client,
        {
            "transactionReference": "MNFY|TX|1",
            "paymentReference": pay["payment_reference"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

    (entry,) = get_entries(client, rep, collection["id"])
    assert entry["status"] == "paid"
    assert entry["paid_at"] is not None
    assert get_balance(client, rep, community["id"]) == 1000.0

    me = client.get(f"/collections/{collection['id']}/payments/me", headers=rep)
    assert me.json()["status"] == "paid"


def test_webhook_duplicate_delivery_is_ignored(client, monnify_mock):
    rep, community, _, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock)
    payload = {
        "transactionReference": "MNFY|TX|1",
        "paymentReference": pay["payment_reference"],
    }
    assert post_webhook(client, payload).json()["status"] == "ok"
    assert post_webhook(client, payload).json()["status"] == "duplicate"

    assert get_balance(client, rep, community["id"]) == 1000.0
    ledger = client.get(f"/communities/{community['id']}/ledger", headers=rep).json()
    assert ledger["total"] == 1


def test_webhook_eventdata_wrapped_shape(client, monnify_mock):
    rep, community, collection, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock)
    resp = post_webhook(
        client,
        {
            "eventType": "SUCCESSFUL_TRANSACTION",
            "eventData": {
                "transactionReference": "MNFY|TX|2",
                "paymentReference": pay["payment_reference"],
            },
        },
    )
    assert resp.json()["status"] == "ok"
    (entry,) = get_entries(client, rep, collection["id"])
    assert entry["status"] == "paid"


def test_webhook_bad_signature_rejected(client, monnify_mock):
    _, _, _, pay = setup_paying_member(client, monnify_mock)
    resp = post_webhook(
        client,
        {"transactionReference": "MNFY|TX|1", "paymentReference": pay["payment_reference"]},
        signature="deadbeef",
    )
    assert resp.status_code == 400


def test_webhook_valid_signature_accepted(client, monnify_mock):
    _, _, _, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock)
    payload = {
        "transactionReference": "MNFY|TX|1",
        "paymentReference": pay["payment_reference"],
    }
    raw = json.dumps(payload).encode()
    resp = client.post(
        "/webhooks/monnify",
        content=raw,
        headers={"Content-Type": "application/json", "monnify-signature": sign(raw)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_webhook_underpaid_not_reconciled(client, monnify_mock):
    rep, community, collection, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock, amount=500)
    resp = post_webhook(
        client,
        {"transactionReference": "MNFY|TX|1", "paymentReference": pay["payment_reference"]},
    )
    assert resp.json()["status"] == "not_paid"
    (entry,) = get_entries(client, rep, collection["id"])
    assert entry["status"] == "pending"
    assert get_balance(client, rep, community["id"]) == 0.0


def _mock_reserved_account(monnify_mock, account_number="1234567890", bank_name="Wema Bank", status="ACTIVE"):
    monnify_mock.post(f"{MONNIFY}/api/v2/bank-transfer/reserved-accounts").mock(
        return_value=Response(
            200,
            json={
                "responseBody": {
                    "accounts": [
                        {"accountNumber": account_number, "bankName": bank_name}
                    ],
                    "accountName": "CSC 101",
                    "status": status,
                }
            },
        )
    )


def test_community_creation_auto_creates_reserved_account(client, monnify_mock):
    _mock_reserved_account(monnify_mock)
    rep = register(client)
    community = create_community(client, rep)

    assert community["reserved_account"]["status"] == "active"
    assert community["reserved_account"]["account_number"] == "1234567890"


def test_reserved_account_creation_failure_does_not_block_community(client, monnify_mock):
    monnify_mock.post(f"{MONNIFY}/api/v2/bank-transfer/reserved-accounts").mock(
        return_value=Response(500, json={"responseMessage": "nope"})
    )
    rep = register(client)
    community = create_community(client, rep)
    assert community["reserved_account"]["status"] == "failed"

    resp = client.get(f"/communities/{community['id']}/reserved-account", headers=rep)
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"

    # Admin can retry once Monnify is reachable again.
    _mock_reserved_account(monnify_mock)
    resp = client.post(f"/communities/{community['id']}/reserved-account", headers=rep)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "active"


def test_reserved_account_direct_transfer_credits_ledger(client, monnify_mock):
    _mock_reserved_account(monnify_mock)
    rep = register(client)
    community = create_community(client, rep)
    assert community["reserved_account"]["account_number"] == "1234567890"

    resp = post_webhook(
        client,
        {
            "transactionReference": "MNFY|RT|1",
            "amountPaid": 5000,
            "product": {
                "reference": f"GlassJar-comm-{community['id']}",
                "type": "RESERVED_ACCOUNT",
            },
        },
    )
    assert resp.json()["status"] == "reserved_account_credit_recorded"
    assert get_balance(client, rep, community["id"]) == 5000.0


def test_admin_sync_reconciles(client, monnify_mock):
    rep, _, _, pay = setup_paying_member(client, monnify_mock)
    mock_verify(monnify_mock)

    with SessionLocal() as db:
        payment_id = (
            db.query(Payment)
            .filter(Payment.payment_reference == pay["payment_reference"])
            .one()
            .id
        )

    resp = client.post(f"/payments/{payment_id}/sync", headers=rep)
    assert resp.status_code == 200
    assert resp.json()["status"] == "reconciled"

    resp = client.post(f"/payments/{payment_id}/sync", headers=rep)
    assert resp.json()["status"] == "already_paid"
