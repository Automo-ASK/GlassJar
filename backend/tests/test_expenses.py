from tests.conftest import (
    create_collection,
    create_community,
    get_balance,
    get_entries,
    get_members,
    mark_paid,
    register,
)


def promote(client, admin_headers, community_id, display_name, role):
    members = get_members(client, admin_headers, community_id)
    target = next(m for m in members if m["display_name"] == display_name)
    resp = client.patch(
        f"/communities/{community_id}/members/{target['id']}/role",
        json={"role": role},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    return target


def setup_governance(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)

    treasurer = register(client, "t@example.com", "Tres Person")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=treasurer,
    )
    auditor = register(client, "a@example.com", "Audit Person")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=auditor,
    )
    promote(client, rep, community["id"], "Tres Person", "treasurer")
    promote(client, rep, community["id"], "Audit Person", "auditor")
    return rep, treasurer, auditor, community


def create_expense(client, headers, community_id, amount=800, title="Venue deposit"):
    resp = client.post(
        f"/communities/{community_id}/expenses",
        json={"title": title, "amount": amount, "category": "logistics"},
        headers=headers,
    )
    return resp


def test_expense_creation_roles(client):
    rep, treasurer, auditor, community = setup_governance(client)
    assert create_expense(client, treasurer, community["id"]).status_code == 201
    assert create_expense(client, auditor, community["id"]).status_code == 403

    plain = register(client, "m@example.com", "Plain Member")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=plain,
    )
    assert create_expense(client, plain, community["id"]).status_code == 403


def test_approval_flow(client):
    rep, treasurer, auditor, community = setup_governance(client)
    expense = create_expense(client, treasurer, community["id"]).json()

    # Only auditors decide.
    resp = client.post(f"/expenses/{expense['id']}/approve", json={}, headers=treasurer)
    assert resp.status_code == 403

    resp = client.post(f"/expenses/{expense['id']}/approve", json={}, headers=auditor)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    # Already decided.
    resp = client.post(f"/expenses/{expense['id']}/approve", json={}, headers=auditor)
    assert resp.status_code == 409


def test_reject_with_note(client):
    rep, treasurer, auditor, community = setup_governance(client)
    expense = create_expense(client, treasurer, community["id"]).json()
    resp = client.post(
        f"/expenses/{expense['id']}/reject",
        json={"note": "no receipt attached"},
        headers=auditor,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["decision_note"] == "no receipt attached"


def test_cannot_decide_own_request(client):
    rep, treasurer, auditor, community = setup_governance(client)
    expense = create_expense(client, treasurer, community["id"]).json()
    # The requester later becomes an auditor — still cannot decide their own request.
    promote(client, rep, community["id"], "Tres Person", "auditor")
    resp = client.post(f"/expenses/{expense['id']}/approve", json={}, headers=treasurer)
    assert resp.status_code == 403


def test_payout_requires_approval(client):
    rep, treasurer, auditor, community = setup_governance(client)
    expense = create_expense(client, treasurer, community["id"]).json()
    resp = client.post(
        f"/expenses/{expense['id']}/mark-paid-out",
        json={"payout_reference": "TRF-1"},
        headers=treasurer,
    )
    assert resp.status_code == 409


def test_payout_requires_sufficient_balance(client):
    rep, treasurer, auditor, community = setup_governance(client)
    expense = create_expense(client, treasurer, community["id"], amount=99999).json()
    client.post(f"/expenses/{expense['id']}/approve", json={}, headers=auditor)
    resp = client.post(
        f"/expenses/{expense['id']}/mark-paid-out",
        json={"payout_reference": "TRF-1"},
        headers=treasurer,
    )
    assert resp.status_code == 400


def test_payout_debits_ledger(client):
    rep, treasurer, auditor, community = setup_governance(client)

    collection = create_collection(client, rep, community["id"], amount=1000)
    entries = get_entries(client, rep, collection["id"])
    rep_entry = next(e for e in entries if e["display_name"] == "Class Rep")
    mark_paid(client, rep, collection["id"], rep_entry["id"])
    assert get_balance(client, rep, community["id"]) == 1000.0

    expense = create_expense(client, treasurer, community["id"], amount=800).json()
    client.post(f"/expenses/{expense['id']}/approve", json={}, headers=auditor)
    resp = client.post(
        f"/expenses/{expense['id']}/mark-paid-out",
        json={"payout_reference": "TRF-123"},
        headers=treasurer,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "paid_out"
    assert body["payout_reference"] == "TRF-123"
    assert body["paid_out_at"] is not None
    assert get_balance(client, rep, community["id"]) == 200.0


def test_ledger_pagination(client):
    rep, treasurer, auditor, community = setup_governance(client)
    collection = create_collection(client, rep, community["id"], amount=1000)
    entries = get_entries(client, rep, collection["id"])
    rep_entry = next(e for e in entries if e["display_name"] == "Class Rep")
    mark_paid(client, rep, collection["id"], rep_entry["id"])

    expense = create_expense(client, treasurer, community["id"], amount=300).json()
    client.post(f"/expenses/{expense['id']}/approve", json={}, headers=auditor)
    client.post(
        f"/expenses/{expense['id']}/mark-paid-out",
        json={"payout_reference": "TRF-9"},
        headers=treasurer,
    )

    resp = client.get(
        f"/communities/{community['id']}/ledger?skip=0&limit=1", headers=rep
    )
    body = resp.json()
    assert body["total"] == 2
    assert len(body["entries"]) == 1
    assert body["balance"] == 700.0
