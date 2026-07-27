from httpx import Response

from tests.conftest import (
    MONNIFY,
    create_collection,
    create_community,
    get_balance,
    get_entries,
    mark_paid,
    register,
)


def setup_expense_roles(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)

    treasurer = register(client, "t@example.com", "Tres Person")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=treasurer,
    )
    members = client.get(f"/communities/{community['id']}/members", headers=rep).json()
    target = next(m for m in members if m["display_name"] == "Tres Person")
    resp = client.patch(
        f"/communities/{community['id']}/members/{target['id']}/role",
        json={"role": "treasurer"},
        headers=rep,
    )
    assert resp.status_code == 200, resp.text
    return rep, treasurer, community


def fund_treasury(client, rep, community, amount=1000):
    collection = create_collection(client, rep, community["id"], amount=amount)
    entries = get_entries(client, rep, collection["id"])
    rep_entry = next(e for e in entries if e["display_name"] == "Class Rep")
    mark_paid(client, rep, collection["id"], rep_entry["id"])


def create_expense(client, headers, community_id, amount=800, title="Venue deposit"):
    return client.post(
        f"/communities/{community_id}/expenses",
        json={
            "title": title,
            "amount": amount,
            "category": "logistics",
            "destination_bank_name": "Wema Bank",
            "destination_bank_code": "035",
            "destination_account_number": "1234567890",
            "destination_account_name": "Vendor Co",
        },
        headers=headers,
    )


def mock_disburse(monnify_mock, status="SUCCESS", reference="MNFY-DISB-1"):
    monnify_mock.post(f"{MONNIFY}/api/v2/disbursements/single").mock(
        return_value=Response(
            200, json={"responseBody": {"reference": reference, "status": status}}
        )
    )


def mock_authorize_otp(monnify_mock, status="SUCCESS", reference="MNFY-DISB-1"):
    monnify_mock.post(f"{MONNIFY}/api/v2/disbursements/single/validate-otp").mock(
        return_value=Response(
            200, json={"responseBody": {"reference": reference, "status": status}}
        )
    )


def mock_resend_otp(monnify_mock):
    monnify_mock.post(f"{MONNIFY}/api/v2/disbursements/single/resend-otp").mock(
        return_value=Response(200, json={"responseBody": {}})
    )


def test_expense_creation_requires_manager_role(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community)
    mock_disburse(monnify_mock)
    assert create_expense(client, treasurer, community["id"]).status_code == 201
    assert create_expense(client, rep, community["id"]).status_code == 201

    plain = register(client, "m@example.com", "Plain Member")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=plain,
    )
    assert create_expense(client, plain, community["id"]).status_code == 403


def test_create_expense_pays_immediately_on_success(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community, amount=1000)
    mock_disburse(monnify_mock, status="SUCCESS", reference="MNFY-DISB-1")

    resp = create_expense(client, treasurer, community["id"], amount=800)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "paid_out"
    assert body["payout_reference"] == "MNFY-DISB-1"
    assert body["paid_out_at"] is not None
    assert body["manual_payout"] is False
    assert get_balance(client, rep, community["id"]) == 200.0


def test_create_expense_insufficient_balance_never_calls_gateway(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    # No funding — treasury balance is 0.
    resp = create_expense(client, treasurer, community["id"], amount=500)
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "failed"
    assert get_balance(client, rep, community["id"]) == 0.0


def test_create_expense_awaiting_otp_then_authorized(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community, amount=1000)
    mock_disburse(monnify_mock, status="PENDING_AUTHORIZATION", reference="MNFY-DISB-2")

    resp = create_expense(client, treasurer, community["id"], amount=500)
    assert resp.status_code == 201, resp.text
    expense = resp.json()
    assert expense["status"] == "awaiting_otp"
    assert get_balance(client, rep, community["id"]) == 1000.0  # not debited yet

    mock_resend_otp(monnify_mock)
    resp = client.post(f"/expenses/{expense['id']}/resend-otp", headers=treasurer)
    assert resp.status_code == 204

    mock_authorize_otp(monnify_mock, status="SUCCESS", reference="MNFY-DISB-2")
    resp = client.post(
        f"/expenses/{expense['id']}/authorize-payout",
        json={"otp": "123456"},
        headers=treasurer,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "paid_out"
    assert body["payout_reference"] == "MNFY-DISB-2"
    assert get_balance(client, rep, community["id"]) == 500.0


def test_authorize_payout_requires_awaiting_state(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community)
    mock_disburse(monnify_mock, status="SUCCESS")
    expense = create_expense(client, treasurer, community["id"], amount=100).json()

    resp = client.post(
        f"/expenses/{expense['id']}/authorize-payout",
        json={"otp": "000000"},
        headers=treasurer,
    )
    assert resp.status_code == 409


def test_retry_payout_after_gateway_failure(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community, amount=1000)
    monnify_mock.post(f"{MONNIFY}/api/v2/disbursements/single").mock(
        return_value=Response(500, json={"responseMessage": "gateway down"})
    )

    expense = create_expense(client, treasurer, community["id"], amount=400).json()
    assert expense["status"] == "failed"
    assert get_balance(client, rep, community["id"]) == 1000.0

    mock_disburse(monnify_mock, status="SUCCESS", reference="MNFY-DISB-3")
    resp = client.post(f"/expenses/{expense['id']}/retry-payout", headers=treasurer)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "paid_out"
    assert get_balance(client, rep, community["id"]) == 600.0


def test_mark_paid_manually_fallback(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community, amount=1000)
    monnify_mock.post(f"{MONNIFY}/api/v2/disbursements/single").mock(
        return_value=Response(503, json={"responseMessage": "disbursement not enabled"})
    )
    expense = create_expense(client, treasurer, community["id"], amount=300).json()
    assert expense["status"] == "failed"

    resp = client.post(
        f"/expenses/{expense['id']}/mark-paid-manually",
        json={"payout_reference": "TRF-MANUAL-1"},
        headers=treasurer,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "paid_out"
    assert body["manual_payout"] is True
    assert body["payout_reference"] == "TRF-MANUAL-1"
    assert get_balance(client, rep, community["id"]) == 700.0


def test_ledger_pagination(client, monnify_mock):
    rep, treasurer, community = setup_expense_roles(client)
    fund_treasury(client, rep, community, amount=1000)
    mock_disburse(monnify_mock, status="SUCCESS", reference="MNFY-DISB-4")

    create_expense(client, treasurer, community["id"], amount=300)

    resp = client.get(
        f"/communities/{community['id']}/ledger?skip=0&limit=1", headers=rep
    )
    body = resp.json()
    assert body["total"] == 2
    assert len(body["entries"]) == 1
    assert body["balance"] == 700.0
