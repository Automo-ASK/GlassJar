from tests.conftest import (
    create_collection,
    create_community,
    get_balance,
    register,
)
from tests.test_payments import mock_init, mock_verify


def setup_shared_collection(client):
    rep = register(client)
    community = create_community(client, rep)
    collection = create_collection(client, rep, community["id"], amount=1000)
    return rep, community, collection


def setup_collection_with_custom_fields(client):
    rep = register(client)
    community = create_community(client, rep)
    collection = create_collection(
        client, rep, community["id"], amount=1000,
        custom_fields=[
            {"key": "phone", "label": "Phone Number", "type": "phone", "required": True},
            {
                "key": "tshirt_size", "label": "T-Shirt Size", "type": "select",
                "required": True, "options": ["S", "M", "L"],
            },
        ],
    )
    return rep, community, collection


def test_public_collection_page_requires_no_auth(client):
    rep, _, collection = setup_shared_collection(client)
    resp = client.get(f"/public/collections/{collection['share_token']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Departmental Dues"
    assert body["community_name"] == "CSC 101"
    assert body["amount_per_member"] == 1000.0
    assert body["amount_collected"] == 0.0
    assert "entries" not in body

    assert client.get("/public/collections/not-a-token").status_code == 404


def test_public_pay_initiates_checkout(client, monnify_mock):
    rep, _, collection = setup_shared_collection(client)

    mock_init(monnify_mock)
    resp = client.post(
        f"/public/collections/{collection['share_token']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["checkout_url"]


def test_public_pay_rejected_when_collection_closed(client):
    rep, _, collection = setup_shared_collection(client)
    client.patch(f"/collections/{collection['id']}/close", headers=rep)

    resp = client.post(
        f"/public/collections/{collection['share_token']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    )
    assert resp.status_code == 400


def test_public_payment_status_and_sync(client, monnify_mock):
    rep, community, collection = setup_shared_collection(client)

    mock_init(monnify_mock)
    pay = client.post(
        f"/public/collections/{collection['share_token']}/pay",
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

    # No CollectionEntry is touched (anonymous payment), but the ledger and
    # public "amount collected" figure both reflect it.
    resp = client.get(f"/public/collections/{collection['share_token']}")
    assert resp.json()["amount_collected"] == 1000.0
    assert get_balance(client, rep, community["id"]) == 1000.0


def test_public_collection_exposes_custom_fields(client):
    rep, _, collection = setup_collection_with_custom_fields(client)
    resp = client.get(f"/public/collections/{collection['share_token']}")
    assert resp.status_code == 200
    fields = resp.json()["custom_fields"]
    assert [f["key"] for f in fields] == ["phone", "tshirt_size"]


def test_payment_form_requires_required_fields(client, monnify_mock):
    rep, _, collection = setup_collection_with_custom_fields(client)

    mock_init(monnify_mock)
    pay = client.post(
        f"/public/collections/{collection['share_token']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    ).json()
    ref = pay["payment_reference"]

    resp = client.get(f"/public/payments/{ref}")
    assert resp.json()["form_submitted"] is False
    assert [f["key"] for f in resp.json()["custom_fields"]] == ["phone", "tshirt_size"]

    # Missing required field
    resp = client.post(f"/public/payments/{ref}/form", json={"values": {"phone": "08012345678"}})
    assert resp.status_code == 400

    # Invalid select value
    resp = client.post(
        f"/public/payments/{ref}/form",
        json={"values": {"phone": "08012345678", "tshirt_size": "XXL"}},
    )
    assert resp.status_code == 400

    # Valid submission
    resp = client.post(
        f"/public/payments/{ref}/form",
        json={"values": {"phone": "08012345678", "tshirt_size": "M"}},
    )
    assert resp.status_code == 200
    assert resp.json()["form_submitted"] is True

    resp = client.get(f"/public/payments/{ref}")
    assert resp.json()["form_submitted"] is True


def test_collection_responses_visible_to_manager_only(client, monnify_mock):
    rep, _, collection = setup_collection_with_custom_fields(client)

    mock_init(monnify_mock)
    pay = client.post(
        f"/public/collections/{collection['share_token']}/pay",
        json={"redirect_url": "http://localhost:3000/payment-return"},
    ).json()
    ref = pay["payment_reference"]
    client.post(
        f"/public/payments/{ref}/form",
        json={"values": {"phone": "08012345678", "tshirt_size": "M"}},
    )
    mock_verify(monnify_mock)
    client.post(f"/public/payments/{ref}/sync")

    resp = client.get(f"/collections/{collection['id']}/responses", headers=rep)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["responses"]) == 1
    assert body["responses"][0]["display_name"] == "Guest"
    assert body["responses"][0]["entry_id"] is None
    assert body["responses"][0]["amount"] == 1000.0
    assert body["responses"][0]["values"]["tshirt_size"] == "M"

    other = register(client, "o@example.com", "O")
    resp = client.get(f"/collections/{collection['id']}/responses", headers=other)
    assert resp.status_code == 403
