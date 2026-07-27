from tests.conftest import add_roster, create_community, get_members, register


def test_create_community_makes_creator_admin(client):
    headers = register(client)
    community = create_community(client, headers)
    assert community["invite_code"]

    members = get_members(client, headers, community["id"])
    assert len(members) == 1
    assert members[0]["role"] == "admin"
    assert members[0]["is_claimed"] is True


def test_admin_adds_roster_members_without_accounts(client):
    headers = register(client)
    community = create_community(client, headers)
    added = add_roster(client, headers, community["id"], ["Ada Obi", "Bola Ade"])
    assert len(added) == 2
    assert all(m["is_claimed"] is False for m in added)

    members = get_members(client, headers, community["id"])
    assert len(members) == 3


def test_non_admin_cannot_add_roster(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)

    other = register(client, "other@example.com", "Other Person")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=other,
    )
    resp = client.post(
        f"/communities/{community['id']}/members",
        json={"display_name": "Sneaky Add"},
        headers=other,
    )
    assert resp.status_code == 403


def test_lookup_shows_unclaimed_members(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Ada Obi"])

    other = register(client, "ada@example.com", "Ada Obi")
    resp = client.get(
        f"/communities/lookup?invite_code={community['invite_code']}", headers=other
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "CSC 101"
    assert [m["display_name"] for m in body["unclaimed_members"]] == ["Ada Obi"]


def test_join_with_claim_links_roster_entry(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    (ada_entry,) = add_roster(client, rep, community["id"], ["Ada Obi"])

    ada = register(client, "ada@example.com", "Ada Obi")
    resp = client.post(
        "/communities/join",
        json={
            "invite_code": community["invite_code"],
            "claim_member_id": ada_entry["id"],
        },
        headers=ada,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == ada_entry["id"]
    assert body["is_claimed"] is True

    members = get_members(client, rep, community["id"])
    assert len(members) == 2  # no duplicate row created


def test_join_auto_claims_matching_email(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    resp = client.post(
        f"/communities/{community['id']}/members",
        json={"display_name": "Ada Obi", "email": "ada@example.com"},
        headers=rep,
    )
    assert resp.status_code == 201

    ada = register(client, "ada@example.com", "Ada Obi")
    resp = client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=ada,
    )
    assert resp.status_code == 200
    assert resp.json()["is_claimed"] is True
    assert len(get_members(client, rep, community["id"])) == 2


def test_join_without_match_creates_new_member(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)

    new = register(client, "new@example.com", "New Person")
    resp = client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=new,
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "New Person"


def test_join_twice_conflicts(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    other = register(client, "o@example.com", "O")
    payload = {"invite_code": community["invite_code"]}
    assert client.post("/communities/join", json=payload, headers=other).status_code == 200
    assert client.post("/communities/join", json=payload, headers=other).status_code == 409


def test_bad_invite_code_not_found(client):
    other = register(client, "o@example.com", "O")
    resp = client.post(
        "/communities/join", json={"invite_code": "nope1234"}, headers=other
    )
    assert resp.status_code == 404


def test_role_changes(client):
    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], ["Unclaimed Person"])

    other = register(client, "t@example.com", "Future Treasurer")
    client.post(
        "/communities/join",
        json={"invite_code": community["invite_code"]},
        headers=other,
    )

    members = get_members(client, rep, community["id"])
    claimed = next(m for m in members if m["display_name"] == "Future Treasurer")
    unclaimed = next(m for m in members if m["display_name"] == "Unclaimed Person")
    me = next(m for m in members if m["display_name"] == "Class Rep")

    # Promote a claimed member: fine.
    resp = client.patch(
        f"/communities/{community['id']}/members/{claimed['id']}/role",
        json={"role": "treasurer"},
        headers=rep,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "treasurer"

    # Unclaimed members cannot hold governance roles.
    resp = client.patch(
        f"/communities/{community['id']}/members/{unclaimed['id']}/role",
        json={"role": "auditor"},
        headers=rep,
    )
    assert resp.status_code == 400

    # Cannot change your own role.
    resp = client.patch(
        f"/communities/{community['id']}/members/{me['id']}/role",
        json={"role": "member"},
        headers=rep,
    )
    assert resp.status_code == 400


def test_remove_member_rules(client):
    from tests.conftest import create_collection

    rep = register(client, "rep@example.com")
    community = create_community(client, rep)
    (ada,) = add_roster(client, rep, community["id"], ["Ada Obi"])

    # With collection history, removal is blocked.
    create_collection(client, rep, community["id"])
    resp = client.delete(
        f"/communities/{community['id']}/members/{ada['id']}", headers=rep
    )
    assert resp.status_code == 409

    # A fresh member without history can be removed.
    (bola,) = add_roster(client, rep, community["id"], ["Bola Ade"])
    resp = client.delete(
        f"/communities/{community['id']}/members/{bola['id']}", headers=rep
    )
    assert resp.status_code == 204
    names = [m["display_name"] for m in get_members(client, rep, community["id"])]
    assert "Bola Ade" not in names
