"""Regression guards for query complexity: dashboard-style endpoints must
issue a fixed number of SQL statements no matter how many collections or
members a community has. A failure here means an N+1 crept back in."""

from contextlib import contextmanager

from sqlalchemy import event

from app.database import engine
from tests.conftest import (
    add_roster,
    create_collection,
    create_community,
    get_entries,
    mark_paid,
    register,
)


@contextmanager
def count_queries():
    counter = {"n": 0}

    def before_cursor_execute(conn, cursor, statement, params, context, executemany):
        counter["n"] += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def build_busy_community(client, active_collections=8, roster=25):
    rep = register(client)
    community = create_community(client, rep)
    add_roster(client, rep, community["id"], [f"Member {i}" for i in range(roster)])
    for i in range(active_collections):
        collection = create_collection(
            client, rep, community["id"], amount=1000, title=f"Dues {i}"
        )
        entries = get_entries(client, rep, collection["id"])
        mark_paid(client, rep, collection["id"], entries[0]["id"])
    return rep, community, collection


def test_community_dashboard_query_count_is_constant(client):
    rep, community, _ = build_busy_community(client)
    with count_queries() as counter:
        resp = client.get(f"/communities/{community['id']}/dashboard", headers=rep)
    assert resp.status_code == 200
    assert len(resp.json()["active_collections"]) == 8
    # auth user + membership + balance + active collections + one grouped
    # rollup + pending-expense count + recent ledger (+ total) — fixed cost.
    assert counter["n"] <= 9, f"expected constant queries, got {counter['n']}"


def test_collection_dashboard_query_count_is_constant(client):
    rep, _, collection = build_busy_community(client, active_collections=1)
    with count_queries() as counter:
        resp = client.get(f"/collections/{collection['id']}/dashboard", headers=rep)
    assert resp.status_code == 200
    assert counter["n"] <= 6, f"expected constant queries, got {counter['n']}"


def test_transparency_report_query_count_is_constant(client):
    _, _, collection = build_busy_community(client, active_collections=1)
    with count_queries() as counter:
        resp = client.get(f"/collections/{collection['id']}/transparency")
    assert resp.status_code == 200
    assert counter["n"] <= 6, f"expected constant queries, got {counter['n']}"
