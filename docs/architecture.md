# GlassJar — Product & Architecture Blueprint (v2 rebuild)

This document captures the decisions behind the post-hackathon rebuild: what the
product is, who it serves, and how the backend is structured. The hackathon code
proved the idea; this rebuild makes it production-grade.

## 1. Product

### The core loop

A class rep (or any group organizer) needs to collect money from a known list of
people and always know who has paid and who has not — without chasing transfer
screenshots or maintaining a spreadsheet.

1. Rep creates a **community** and adds every member to its **roster** (names
   first — no signup required from members).
2. Rep creates a **collection** (purpose, amount per member, deadline, optional
   budget breakdown). Every roster member gets an entry.
3. Rep shares one **public payment link**. A member opens it, picks their name,
   and pays through Monnify checkout — no account needed.
4. Payments reconcile automatically via webhook. Cash or direct transfers
   outside the platform are **manually marked paid** by the rep, with a note,
   so the list never lies.
5. Rep sees the live paid / pending / waived list, and members can view a
   public **transparency report** of where the money went.

### Beyond the core loop (treasury scope, kept from the hackathon vision)

- **Ledger**: every naira in or out of a community is a ledger entry; balance is
  derived, never stored ad hoc.
- **Expense governance**: Treasurer submits an expense → an independent Auditor
  approves or rejects → Admin/Treasurer records the payout reference → ledger
  debit. Nobody approves their own request.
- **Reserved accounts**: a community can provision a dedicated Monnify bank
  account; direct transfers into it are credited to the ledger automatically.
- **AI treasury assistant**: Q&A grounded strictly in the community's verified
  ledger context.

### Membership model: hybrid (roster-first + optional accounts)

- A **Member** row is a roster entry: `display_name` always, `user_id` optional.
- Guests can pay against their roster entry with zero signup.
- A member may later register and **claim** their roster entry (via the
  community invite code), gaining login, history, and eligibility for roles.
- Roles (`admin`, `treasurer`, `auditor`) require a claimed (user-linked) member.

## 2. Backend architecture

Stack: Python 3.11+, FastAPI, SQLAlchemy 2.0 (typed), Pydantic v2, PostgreSQL
(SQLite in-memory for tests), Alembic migrations, PyJWT + bcrypt, httpx.

### Layering

```
routers/    thin HTTP layer: parse request, call service, shape response
schemas/    all Pydantic request/response models, per domain
services/   all business logic and transactions
models/     SQLAlchemy ORM, constraints live in the database
core/       security (JWT, bcrypt), dependencies (auth, roles), errors
```

Rules:
- Routers never touch the ORM directly; they call services.
- Services own transactions (commit/rollback) and raise domain errors from
  `core/errors.py`; a single exception handler maps them to HTTP responses.
- Every schema lives in `schemas/` — no inline Pydantic models in routers.

### Money

All monetary values are `Decimal` in Python and `NUMERIC(12,2)` in the
database. Amounts are quantized to 2dp at the service boundary and serialized
as JSON numbers for the frontend. `CHECK (amount >= 0)` on money columns.

### Domain model

- `User` — account (email unique, bcrypt hash).
- `Community` — group; invite code; optional Monnify reserved account fields.
- `Member` — roster entry: `community_id`, `display_name`, optional
  `email`/`phone`, nullable `user_id` (claimed when set), `role`.
  Partial unique index on `(community_id, user_id)` where `user_id` is set.
- `Collection` — a fundraising round; `amount_per_member`, optional
  `target_amount`, `deadline`, `budget_allocation` JSON, `status`
  (draft/active/closed), public `share_token` for the guest payment page.
- `CollectionEntry` — one per (collection, member): `amount_due`, `status`
  (pending/paid/waived), `paid_at`, `marked_by` + `note` for manual actions.
- `Payment` — a money-in attempt: `channel` (`checkout` via Monnify,
  `manual_cash`, `manual_transfer`), unique `payment_reference`, status
  (pending/paid/failed), raw verification payload, `recorded_by` for manual.
- `WebhookEvent` — dedupe log of received Monnify events (unique event key).
- `Expense` — money-out request with approval state machine
  (pending → approved → paid_out, or rejected) and destination bank details.
- `LedgerEntry` — credit/debit against a community;
  `(reference_type, reference_id, entry_type)` unique so the same source can
  never double-post. Balance = SQL `SUM`, computed in the database.
- `AuditLog` — who did what (role changes, manual marks, approvals, payouts).

### Payment integrity

- **Webhook idempotency**: every incoming Monnify event is recorded in
  `WebhookEvent` keyed by transaction reference (or body hash); duplicates are
  acknowledged and skipped.
- **Row locking**: payment status transitions take `SELECT … FOR UPDATE`
  (no-op on SQLite) so concurrent webhook + manual sync cannot double-credit.
- **Ledger backstop**: the unique constraint on ledger references makes a
  double-post a database error, not silent corruption.
- **Verification, not trust**: webhooks trigger a server-side Monnify
  `verify_transaction` call before any state changes (ported from v1 — this
  part the hackathon got right).
- **Manual marks are first-class**: they create a `Payment` with a manual
  channel and a ledger credit, attributed to the rep who recorded them, and
  can be reverted with a reversing debit (never deleted).

### API surface (prefixes)

| Router | Prefix | Auth |
|---|---|---|
| auth | `/auth` | none / bearer |
| users | `/users` | bearer |
| communities + roster | `/communities` | bearer, role-gated |
| collections + entries | `/communities/{id}/collections`, `/collections` | bearer |
| payments | `/collections/{id}/pay`, `/payments` | bearer |
| public (guest) | `/public` | none (share token / payment reference) |
| webhooks | `/webhooks/monnify` | HMAC-SHA512 signature |
| expenses + ledger | `/communities/{id}/expenses`, `/expenses` | bearer, role-gated |
| reports | `/collections/{id}/transparency` (public), `/communities/{id}/dashboard` | mixed |
| assistant | `/communities/{id}/assistant` | bearer |

New in v2: `/communities/{id}/members` roster CRUD (single + bulk add),
claim-on-join, `/public/collections/{share_token}` guest payment page data,
guest pay initiation, entry `mark-paid` / `waive` / `revert`, entry sync for
late roster additions.

### Operations

- **Migrations**: Alembic (`alembic upgrade head` before app start). The v1
  `create_all + sync_schema()` hack is gone.
- **CORS**: explicit origin allowlist from `FRONTEND_ORIGIN` (comma-separated),
  not `*`.
- **Config**: `pydantic-settings`; no secret defaults in code (the v1 hardcoded
  Monnify contract code default is removed).
- **Auth hardening**: JWTs carry a `jti`; `/auth/logout` records it in
  `revoked_tokens` and every request checks that table, so tokens can be killed
  before natural expiry. Ported from the teammate's audit branch.
- **Rate limiting**: `slowapi` (in-memory) on abuse-prone endpoints — auth
  register/login (5/min), guest pay (10/min), public transparency (30/min).
  Disabled under `ENV=test`. Multi-instance deploys need a shared backend
  (Redis) or each instance enforces its own quota.
- **Tests**: pytest against SQLite in-memory with the Monnify API mocked via
  respx; the suite covers auth (incl. logout revocation), roster, collections,
  payment reconciliation (idempotency + manual marks), expenses, and reports.

### Open questions (from the teammate audit — see docs/teammate-audit.md)

- **Monnify → Squad migration**: whether to switch payment gateway. The Monnify
  integration is isolated in `services/monnify.py` behind one service object, so
  a swap is contained to that module plus the webhook signature check.
- **Pulling the database out of the server**: Alembic already decouples schema
  changes from app redeploys (`alembic upgrade head` is a release step, not a
  boot step). Managed Postgres (Render) is the intended target.

## 3. What was deliberately dropped or changed from v1

- `EXPENSE_APPROVAL_THRESHOLD` config: was never enforced; removed. All
  expenses require auditor approval regardless of size.
- Float money, `python-jose`, `passlib`: replaced (Decimal, PyJWT, bcrypt).
- Members-must-register: replaced by roster-first hybrid onboarding.
- Inline router schemas and business logic in routers: forbidden by structure.
