from tests.conftest import (
    add_roster,
    create_collection,
    create_community,
    get_entries,
    mark_paid,
    register,
)


def test_transparency_report_is_public(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi", "Bola Ade"])
    collection = create_collection(client, rep, community["id"], amount=1000)

    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    bola = next(e for e in entries if e["display_name"] == "Bola Ade")
    mark_paid(client, rep, collection["id"], ada["id"])
    client.post(
        f"/collections/{collection['id']}/entries/{bola['id']}/waive",
        json={"note": "hardship"},
        headers=rep,
    )

    resp = client.get(f"/collections/{collection['id']}/transparency")  # no auth
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Departmental Dues"
    assert body["paid_count"] == 1
    assert body["pending_count"] == 1
    assert body["waived_count"] == 1
    assert body["amount_collected"] == 1000.0
    assert body["expenses"] == []


def test_community_dashboard(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi"])
    collection = create_collection(client, rep, community["id"], amount=1000)

    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    mark_paid(client, rep, collection["id"], ada["id"])

    resp = client.get(f"/communities/{community['id']}/dashboard", headers=rep)
    assert resp.status_code == 200
    body = resp.json()
    assert body["treasury_balance"] == 1000.0
    assert body["pending_expenses_count"] == 0
    assert len(body["active_collections"]) == 1
    summary = body["active_collections"][0]
    assert summary["paid_count"] == 1
    assert summary["pending_count"] == 1
    assert len(body["recent_ledger"]) == 1


def test_dashboard_requires_membership(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    outsider = register(client, "x@example.com", "X")
    resp = client.get(f"/communities/{community['id']}/dashboard", headers=outsider)
    assert resp.status_code == 403


def test_assistant_unconfigured_returns_502(client):
    rep = register(client)
    community = create_community(client, rep)
    resp = client.post(
        f"/communities/{community['id']}/assistant/ask",
        json={"question": "What is our balance?"},
        headers=rep,
    )
    assert resp.status_code == 502
