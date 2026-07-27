# AcaFund

AcaFund is a financial management platform for African student communities. A
class rep creates a community, builds the member roster (no signup needed from
members), opens a collection, and shares one payment link — everyone can see
live who has paid, who hasn't, and where every naira went.

Product vision and technical design: [docs/architecture.md](docs/architecture.md).

## Core loop

1. **Roster-first** — the rep adds every member by name; nobody is forced to
   register just to pay.
2. **One shareable link** — a member opens the public collection page, picks
   their name, and pays through Monnify checkout as a guest.
3. **Self-maintaining list** — payments reconcile via verified webhooks; cash
   or off-platform transfers are manually marked (with a note and audit trail)
   so the list never lies.
4. **Optional accounts** — members can register later and claim their roster
   entry via the invite code, unlocking history and governance roles.
5. **Treasury governance** — ledger for every credit/debit, expense requests
   with independent auditor approval, public transparency reports, and an AI
   treasury assistant grounded in the ledger.

## Stack

| Layer | Tech |
|-------|------|
| API | Python 3.11, FastAPI, SQLAlchemy 2.0 (typed), Pydantic v2 |
| Database | PostgreSQL 16, Alembic migrations (SQLite in-memory for tests) |
| Money | `Decimal` end-to-end, `NUMERIC(12,2)` in the database |
| Auth | PyJWT + bcrypt |
| Payments | Monnify (NGN checkout + reserved accounts), idempotent webhooks |
| AI assistant | NVIDIA Nemotron via the NVIDIA API |
| Container | Docker / docker-compose |
| Deploy | Render (Blueprint via render.yaml) |
| Frontend | React, TypeScript, Vite, Tailwind CSS |

## Backend architecture

```
backend/app/
  routers/    thin HTTP layer — parse, call service, shape response
  schemas/    all Pydantic request/response models
  services/   all business logic and transactions
  models/     SQLAlchemy ORM; constraints live in the database
  core/       security (JWT/bcrypt), dependencies, domain errors, money
```

Integrity guarantees around money:

- Webhook deliveries are deduped by event key (`webhook_events` table); the
  event record, payment transition, and ledger credit commit atomically.
- Payment status transitions take a row lock (`SELECT … FOR UPDATE`).
- The ledger is append-only with a unique reference constraint — the same
  source event can never post twice. Manual marks are reverted with a
  balancing debit, never deleted.
- Every payment (gateway or manual) is a `Payment` row, so every ledger credit
  traces to who paid, how, and who recorded it.

## Local development

```bash
cd backend
cp .env.example .env   # fill in SECRET_KEY (+ Monnify/NVIDIA keys as needed)

docker compose up      # migrations run, then API at http://localhost:8080
```

API docs at `http://localhost:8080/docs`.

### Tests

Tests run on in-memory SQLite with the Monnify API mocked — no services needed.

```bash
cd backend
python -m pytest tests -v
```

### Migrations

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## API overview

| Area | Prefix | Auth |
|---|---|---|
| Auth | `/auth` | none / bearer |
| Communities + roster | `/communities` | bearer, role-gated |
| Collections + entries | `/communities/{id}/collections`, `/collections` | bearer |
| Payments | `/collections/{id}/pay`, `/payments` | bearer |
| Guest (public) | `/public` | none — share token |
| Webhooks | `/webhooks/monnify` | HMAC-SHA512 |
| Expenses + ledger | `/communities/{id}/expenses`, `/expenses` | bearer, role-gated |
| Reports | `/collections/{id}/transparency` (public), `/communities/{id}/dashboard` | mixed |
| Assistant | `/communities/{id}/assistant/ask` | bearer |

Key flows:

```
POST  /communities                                   Create community (creator = admin)
POST  /communities/{id}/members/bulk                 Add roster by name, no accounts needed
GET   /communities/lookup?invite_code=…              Preview community + claimable entries
POST  /communities/join                              Join / claim a roster entry

POST  /communities/{id}/collections                  Open a collection (enrolls whole roster)
GET   /public/collections/{share_token}              Public payment page data
POST  /public/collections/{token}/entries/{id}/pay   Guest checkout, no account
POST  /collections/{id}/entries/{id}/mark-paid       Record cash / off-platform transfer
POST  /collections/{id}/entries/{id}/waive           Excuse a member
POST  /collections/{id}/entries/{id}/revert          Undo a manual mark (balancing debit)

POST  /communities/{id}/expenses                     Treasurer requests spend
POST  /expenses/{id}/approve | /reject               Independent auditor decides
POST  /expenses/{id}/mark-paid-out                   Record payout → ledger debit
GET   /collections/{id}/transparency                 Public accountability report
```

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | yes | PostgreSQL DSN. Render wires this from the managed DB. |
| `SECRET_KEY` | yes | JWT signing secret (32+ chars). |
| `MONNIFY_API_KEY` / `MONNIFY_SECRET_KEY` / `MONNIFY_CONTRACT_CODE` | payments | Monnify merchant credentials. |
| `MONNIFY_BASE_URL` | no | Default sandbox; set `https://api.monnify.com` for production. |
| `NVIDIA_API_KEY` | assistant | Powers the treasury assistant. |
| `FRONTEND_ORIGIN` | no | Comma-separated CORS allowlist. Default `http://localhost:3000`. |

## Deploying to Render

Render Dashboard → New → Blueprint → connect this repo. `render.yaml`
provisions the API (Docker, migrations on boot) and a managed Postgres.
Enter the Monnify/NVIDIA secrets and `FRONTEND_ORIGIN` in the dashboard.
