from tests.conftest import (
    add_roster,
    create_collection,
    create_community,
    get_entries,
    mark_paid,
    register,
)


def test_create_collection_enrolls_whole_roster(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi", "Bola Ade"])

    collection = create_collection(client, rep, community["id"], amount=1500)
    assert collection["status"] == "active"
    assert collection["share_token"]
    assert collection["amount_per_member"] == 1500.0
    assert collection["target_amount"] == 4500.0  # rep + 2 roster members

    entries = get_entries(client, rep, collection["id"])
    assert len(entries) == 3
    assert {e["display_name"] for e in entries} == {"Ada Obi", "Bola Ade", "Class Rep"}
    assert all(e["status"] == "pending" for e in entries)


def test_plain_member_cannot_create_collection(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    other = register(client, "o@example.com", "O")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=other,
    )
    resp = client.post(
        f"/communities/{community['id']}/collections",
        json={"title": "Nope", "amount_per_member": 100},
        headers=other,
    )
    assert resp.status_code == 403


def test_budget_allocation_must_sum_to_100(client):
    rep = register(client)
    community = create_community(client, rep)
    resp = client.post(
        f"/communities/{community['id']}/collections",
        json={
            "title": "Dues",
            "amount_per_member": 100,
            "budget_allocation": {"food": 50, "venue": 30},
        },
        headers=rep,
    )
    assert resp.status_code == 422


def test_dashboard_counts(client):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi", "Bola Ade"])
    collection = create_collection(client, rep, community["id"], amount=1000)

    entries = get_entries(client, rep, collection["id"])
    ada = next(e for e in entries if e["display_name"] == "Ada Obi")
    bola = next(e for e in entries if e["display_name"] == "Bola Ade")

    mark_paid(client, rep, collection["id"], ada["id"])
    resp = client.post(
        f"/collections/{collection['id']}/entries/{bola['id']}/waive",
        json={"note": "hardship"},
        headers=rep,
    )
    assert resp.status_code == 200

    resp = client.get(f"/collections/{collection['id']}/dashboard", headers=rep)
    assert resp.status_code == 200
    dash = resp.json()
    assert dash["total_members"] == 3
    assert dash["paid_count"] == 1
    assert dash["pending_count"] == 1
    assert dash["waived_count"] == 1
    assert dash["amount_collected"] == 1000.0
    assert dash["amount_outstanding"] == 1000.0
    assert dash["percent_target_reached"] == 33.3


def test_close_collection(client):
    rep = register(client)
    community = create_community(client, rep)
    collection = create_collection(client, rep, community["id"])

    resp = client.patch(f"/collections/{collection['id']}/close", headers=rep)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"

    resp = client.patch(f"/collections/{collection['id']}/close", headers=rep)
    assert resp.status_code == 409


def test_entries_sync_enrolls_late_roster_additions(client):
    rep = register(client)
    community = create_community(client, rep)
    collection = create_collection(client, rep, community["id"])
    assert len(get_entries(client, rep, collection["id"])) == 1

    add_roster(client, rep, community["id"], ["Late Comer"])
    resp = client.post(f"/collections/{collection['id']}/entries/sync", headers=rep)
    assert resp.status_code == 200
    assert resp.json()["added"] == 1
    assert len(get_entries(client, rep, collection["id"])) == 2

    # Second sync is a no-op.
    resp = client.post(f"/collections/{collection['id']}/entries/sync", headers=rep)
    assert resp.json()["added"] == 0
