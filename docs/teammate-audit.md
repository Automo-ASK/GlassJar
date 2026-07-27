# AcaFund / GlassJar — Code Audit

Scope: `backend/` (FastAPI + SQLAlchemy + Postgres), `frontend/` (React/Vite), deployment
manifests (`render.yaml`, `docker-compose.yml`). Read in full, not sampled.

Two follow-up questions you asked are answered inline where relevant, and summarized at the
bottom: **(1) Monnify → Squad migration** and **(2) pulling the database out from "inside" the
server**.

---

## Update — Alembic + Decimal fixes applied

Since this was written, **§1.2 (Float money columns)** and **§1.3 (no migration tool)** have
been fixed:

- Every currency column (`Payment.amount`, `Collection.amount_per_member`/`target_amount`,
  `CollectionMember.amount_due`, `Expense.amount`, `LedgerEntry.amount`) is now
  `Numeric(14, 2)` instead of `Float`, backed by `Decimal` end-to-end through the request/response
  schemas and ledger arithmetic — no more binary floating-point drift in balances. API responses
  still emit plain JSON numbers (not Decimal-as-string) via a shared `Money` type
  (`app/schemas/types.py`) so the frontend contract is unchanged.
- `get_balance()` (`app/services/ledger.py`) now sums via a SQL `SUM(CASE ...)` instead of
  loading every ledger row into Python — fixes §2.3 as a side effect of the same change.
- `sync_schema()` and the boot-time `Base.metadata.create_all()` are gone from
  `app/main.py`'s lifespan. Schema is now owned by **Alembic** (`backend/alembic/`), with a
  baseline migration (`alembic/versions/..._baseline_schema.py`) capturing current state.
  `alembic upgrade head` runs as an explicit release step — wired into
  `docker-compose.yml` (api service command) for local dev and `render.yaml`
  (`preDeployCommand`) for production — not at app-process boot. This is the fix described in
  §6 as the actual unblock for decoupling "redeploy the API" from "change the schema."
- Full test suite run: 61 passed, 11 failed, 1 skipped. **The 11 failures are pre-existing and
  unrelated to this change** — confirmed by stashing all changes and reproducing the identical
  failure on unmodified `main`. Every one is the same root cause: `respx.models.AllMockedAssertionError:
  ... not mocked!` on `POST https://sandbox.monnify.com/api/v1/auth/login`, i.e. the mocked
  HTTP layer isn't intercepting `MonnifyService`'s calls in this environment's respx/httpx
  version combination (`respx==0.21.1`, `httpx==0.27.0`). Worth a follow-up — it's a live gap in
  test coverage for exactly the payment/webhook/reserved-account code paths flagged as
  highest-risk in §1.1, §1.4.
- Still open: §1.1 (webhook signature/verification gap), §1.4 (public transparency endpoint
  leaks bank details), §2.1 (silent exception handler), §2.2 (CORS wildcard), §2.4 (dead
  expense-threshold config), §2.5 (frontend offline stand-in data), §2.6 (JWT in localStorage),
  and everything in §3–§4. None of those were in scope for this pass.

---

## Update 2 — High + Medium fixes applied

All **High** items and the four **Medium** items from the original list are now fixed, except
the deliberately-scoped-down part of §2.6 (see below — you picked revocation-only, not a full
cookie migration).

- **§2.2 CORS** — locked to a single configurable origin instead of `*`. `FRONTEND_ORIGIN`
  (`.env` / `app/config.py`) now defaults to `http://localhost:5173` (Vite's dev port); change
  it there when you need a different origin (e.g. the deployed frontend URL in Render's
  dashboard — `render.yaml` already points at `sync: false` for that var). The duplicate
  hand-written `force_cors` middleware is gone — `CORSMiddleware` alone now handles every
  response, including ones from the exception handler, since it wraps Starlette's exception
  middleware in the stack.
- **§2.1 Silent exception handler** — `app/main.py`'s catch-all now calls `logger.exception(...)`
  before returning the generic 500, so unhandled errors (including in payment/webhook code)
  leave a trace instead of vanishing.
- **§2.4 Dead expense-threshold config** — wired up per your answer (dual control via Admin
  sign-off). Auditor approval alone still works for anything below
  `EXPENSE_APPROVAL_THRESHOLD` (`.env`, default 50000). At or above it, a new
  `POST /expenses/{id}/admin-approve` (Admin role only) must also run before
  `mark-paid-out` will accept the payout — `Expense.admin_approved_by`/`admin_approved_at`
  record who and when. `mark_paid_out` now 409s with a clear message if that sign-off is
  missing.
- **§2.6 JWT revocation** (server-side revocation only, per your answer — storage stays
  `localStorage`, no cookie/CSRF migration) — tokens now carry a `jti` claim
  (`core/security.py`). A new `RevokedToken` table + `POST /auth/logout` lets a token be killed
  immediately instead of staying valid until natural expiry; `get_current_user` checks the
  revocation table on every request. The full httpOnly-cookie fix for the underlying
  XSS-readable-storage risk is still open, by your choice.
- **Medium — email/password validation**: `RegisterIn.email` is now `EmailStr` (rejects
  malformed addresses at the API boundary); `password` requires `min_length=8`.
- **Medium — expense payout destination validation**: `CreateExpenseIn` now requires
  `destination_bank_name`/`destination_account_number`/`destination_account_name` to be
  provided together (not partially), and validates the account number is a 10-digit NUBAN
  before it's ever used as a payout instruction.
- **Medium — rate limiting**: `/auth/login` and `/auth/register` are now limited to 5
  requests/minute per client IP via `slowapi` (in-memory — fine at current single-instance
  scale; needs a shared backend like Redis if the API ever runs multiple instances behind a
  load balancer, noted in `app/core/rate_limit.py`). Disabled under `ENV=test` so the test
  suite's own setup traffic doesn't trip it.
- **Medium — BVN logging**: verified, no code change needed. Grepped every `logger.*`/`print`
  call in the codebase — none log request bodies, and BVN is never persisted (passed through to
  Monnify and discarded). Uvicorn's default access log (unconfigured) only logs
  method/path/status, not bodies either.
- **§2.5 Frontend offline stand-in data**: still returns synthetic data when the backend is
  unreachable (unchanged behavior), but it's no longer silent — a persistent red banner
  (`OfflineBanner.tsx`, mounted in both `AppLayout` and `AuthLayout`) now appears whenever any
  API call falls back to local demo data, and clears the moment a real response comes back.
  Makes it impossible to mistake fabricated state (e.g. a fake "payout marked paid" from
  `markExpensePaidOut`) for something actually saved server-side.
- **Alembic robustness fix found along the way**: the first-pass baseline migration had
  unnamed foreign-key constraints, which is fine for `upgrade()` but breaks `downgrade()` —
  autogenerate can't reference a constraint it can't name. Added a naming convention to
  `Base.metadata` (`app/database.py`) so every future autogenerated constraint gets a
  deterministic name, and squashed the migration history back to a single clean baseline
  reflecting it (safe to do — nothing had shipped from the prior baseline yet). Verified against
  a real local Postgres instance (not just SQLite): `upgrade` → `downgrade` → `upgrade` round-trips
  cleanly, and `alembic check` reports zero drift against current models.
- Full test suite: 61 passed, 11 failed (same 11 pre-existing respx/httpx failures noted above,
  confirmed unrelated), 1 skipped. Frontend: `tsc --noEmit` clean.
- Still open: §1.1 (webhook signature/verification gap — the highest-severity item, not touched
  this round), §1.4 (public transparency endpoint leaks bank account numbers), the httpOnly-cookie
  half of §2.6, and everything in §3–§4 (no rate-limit-adjacent nits, duplicate `ALL_ROLES`, etc.).

---

## Update 3 — Critical items + nits fixed

- **§1.1 Webhook verification gap (the highest-severity item)** — fixed on both halves:
  - **Signature is now mandatory outside Monnify's sandbox.** `is_sandbox = "sandbox" in
    settings.monnify_base_url`; if the request has no `monnify-signature` header and we're not
    talking to sandbox, the webhook is rejected with 400 instead of being processed as
    untrusted. Sandbox behavior is unchanged (Monnify's sandbox doesn't sign webhooks, so it
    stays optional there — this is what the original code's comment was describing, just not
    enforcing).
  - **The reserved-account direct-transfer branch no longer trusts the webhook body at all.**
    It used to credit the ledger straight from `event_data["amountPaid"]` with zero
    corroboration. It now pulls a `paymentReference`/`transactionReference` out of the webhook,
    calls `monnify_service.verify_transaction()` against Monnify's real API (same pattern the
    payment-reference branch already used), and only credits the *verified* amount from that
    response — never the number the webhook claimed. If there's no reference to verify against,
    or verification fails, nothing is credited (`{"status": "unverifiable"}` /
    `{"status": "verification_failed"}`). Combined with mandatory signatures, forging a credit
    now requires both a valid HMAC (needs the shared secret) *and* a real, verifiable Monnify
    transaction — not just a crafted HTTP POST.
  - Added two regression tests (`test_webhook_reserved_account_without_reference_is_not_credited`,
    `test_webhook_missing_signature_rejected_outside_sandbox`) so this can't silently regress.
  - **Residual gap, out of scope for this pass**: there's still no idempotency guard on
    direct-transfer credits specifically — Monnify retrying the same webhook could double-credit,
    since (unlike the payment-reference path, which checks `payment.status == PAID` first) there's
    no local row to dedupe against yet. Would need a migration adding a unique transaction
    reference column to `LedgerEntry` to fix properly; flagging rather than doing it
    unprompted since it's a schema change beyond what was asked.

- **§1.4 Public transparency endpoint** — reassessed, not silently downgraded: on closer look,
  the account number this endpoint exposes is a **receive-only** Nigerian bank account (Monnify
  reserved account). Knowing it lets someone *send* money in, not withdraw — no PIN, BVN, or
  other credential is exposed alongside it, so this isn't a path to draining funds the way §1.1
  was. Showing it here is also the actual point of a page literally named "transparency" — it's
  the "here's where to send dues/donations" info, same as any organization publishing a bank
  account for public contributions. Stripping it would break that use case. What's still a real,
  if lower-severity, concern is **enumerability**: no auth + sequential integer `collection_id`s
  means someone could script through every collection and bulk-harvest every community's account
  details, titles, and expense history at once, which is a scale of exposure the page wasn't
  designed to invite. Fixed that specific gap: the endpoint is now rate-limited (30/min/IP via
  the same `slowapi` limiter added earlier) to blunt bulk scraping, while keeping the account
  details themselves intact. If you want stronger protection later (e.g. unguessable slugs
  instead of sequential IDs so a specific transparency link can be shared deliberately without
  making every other community's page walkable), that's a real option — didn't do it here since
  it's a schema change with product implications (URLs distributed to members would change) and
  is a step further than "fix the leak."

- **Nits**: `ALL_ROLES` was duplicated verbatim in five router files; moved to
  `app/models/enums.py` as `ALL_MEMBER_ROLES`, imported as `ALL_ROLES` everywhere it was used so
  no call sites needed touching.

- Full test suite: 62 passed, 12 failed, 1 skipped — the same 11 pre-existing respx/httpx
  failures plus one new test that touches the same mocked Monnify calls and fails at the exact
  same pre-existing interception point (not in the new verification logic). Confirmed not a
  regression by inspecting the traceback: it fails during test setup (reserved-account creation),
  before the webhook code under test even runs.

- **Still open**: the httpOnly-cookie half of §2.6 (JWT storage — descoped by your earlier
  choice), the respx/httpx test-mocking environment issue (pre-existing, unrelated to any of
  these fixes, blinding 11 payment/webhook tests), and the optional stronger fix for §1.4 noted
  above. Everything else from the original audit list is now addressed.

---

## Update 4 — respx test issue root-caused, idempotency gap closed

- **The respx/httpx test failures were never a code bug — they were my testing environment.**
  Root cause: `httpx` was installed at 0.28.1 in the shell I'd been running `pytest` in, even
  though `requirements.txt` pins `httpx==0.27.0` — an unrelated package (`ddgs`, nothing to do
  with this project) had forced a newer `httpx` into that same shared/global Python environment,
  and `respx==0.21.1` doesn't correctly intercept requests made through httpx 0.28's transport
  changes. Built a clean virtualenv from `backend/requirements.txt` alone (matching what the
  Dockerfile / CI would actually get) and every one of those 11 tests passed. This was never
  something a deploy would hit — Docker builds always install from `requirements.txt` in
  isolation — but it meant I'd been reporting "assumed correct, tests can't confirm it" instead
  of "confirmed correct" for the exact code this whole engagement centers on. Recommend the repo
  gain a committed `.venv`-per-project habit (or a `Makefile`/`tox`/CI step that always installs
  from a clean environment) so this class of false-negative can't happen again locally.
- Fixed one genuine, unrelated pre-existing test bug surfaced once the environment was clean:
  `test_assistant_context_contains_correct_balance` asserted a hardcoded, stale NVIDIA model
  name against the live `MODEL` constant in `app/services/assistant.py`, which had since been
  updated. Now imports `MODEL` instead of hardcoding a copy that can drift again.
- **Idempotency gap closed** (the residual risk flagged in Update 3): added
  `LedgerEntry.provider_reference` — a unique, nullable column holding the Monnify
  transaction/payment reference for entries that don't already have another dedupe mechanism.
  The reserved-account webhook branch now checks for an existing entry with that reference
  *before* calling Monnify to re-verify (cheap short-circuit on retries), and the insert itself
  is wrapped to treat a unique-constraint collision (two concurrent deliveries of the same
  webhook racing each other) as "already credited," not an error. Added
  `test_webhook_reserved_account_retry_does_not_double_credit` to prove a retried webhook
  produces exactly one ledger entry, not two.
- Migration regenerated (schema still pre-launch, safe to squash) and re-verified end-to-end
  against a real local Postgres: `upgrade` → `downgrade` → `upgrade` round-trips cleanly,
  `alembic check` reports zero drift.
- **Full suite, in the clean environment: 75 passed, 1 skipped, 0 failed.** The 1 skip is the
  live-Monnify-credentials smoke test (`test_monnify_live.py`), which is supposed to skip
  without real sandbox credentials — that's correct, not a gap.

**Where things actually stand now**: every item from the original audit is fixed and, for the
first time this session, *verified* rather than reasoned-about — including the payment/webhook
code that's the highest-stakes part of the app. The one remaining known gap is the httpOnly-cookie
migration for JWT storage, which you explicitly deferred earlier. Nothing else is outstanding.

---

## 1. Critical — fix before this touches more real money

### 1.1 Reserved-account webhook credit has no verification path
`backend/app/routers/payments.py:176-241` (`monnify_webhook`)

For normal collection payments, the webhook only *triggers* a check — it then calls
`monnify_service.verify_transaction()` and trusts Monnify's own API response, not the webhook
body. Good pattern.

The **reserved-account / direct-transfer branch does not do this**. It reads `amountPaid` and
`product.reference` straight off the POST body and calls `record_direct_credit()` with no
corroborating call back to Monnify:

```python
if account_reference.startswith("acafund-comm-"):
    ...
    record_direct_credit(db=db, community_id=community.id, amount=amount_paid, ...)
```

Signature verification is also **optional** — `if signature:` — because "sandbox doesn't send
it." That means: in production, anyone who discovers a community's reserved-account reference
(predictable — `acafund-comm-{id}`, sequential ints) can `POST /webhooks/monnify` with no
signature header and an arbitrary `amountPaid`, and the ledger will credit it as real money,
no callback to Monnify required. This is the single highest-severity item in the codebase —
it's a direct path to fabricating treasury balance.

**Fix:** make signature verification mandatory in non-sandbox environments (fail closed, not
open, when the header is absent), and/or require every direct-credit branch to re-query
Monnify's transaction/settlement API before crediting, the same way the payment-reference path
already does.

### 1.2 Money stored as `Float` everywhere
`models/payment.py`, `collection.py`, `expense.py`, `ledger.py` — every currency column is
`Column(Float)`.

Floats can't represent Naira-and-kobo exactly; `_validate_budget`'s own `abs(total - 100.0) >
0.01` tolerance check is a tell that the codebase is already aware floats drift. Balances are
summed by iterating in Python (`get_balance`, §2.3) rather than in SQL, which compounds the same
imprecision. For a ledger this is a correctness bug waiting to surface as "balance doesn't
reconcile" reports.

**Fix:** store amounts as integer kobo (`Integer`/`BigInteger`) or `Numeric(14,2)`, not `Float`.
This is a schema migration — worth doing together with §1.4 (introducing Alembic) rather than
as a live `ALTER COLUMN` on prod.

### 1.3 No schema migration tool — raw `ALTER TABLE` on every boot
`backend/app/database.py:30-53` (`sync_schema`), called from `main.py` lifespan on every
process start.

This diffs live DB columns against the SQLAlchemy models and runs `ALTER TABLE ... ADD COLUMN`
directly, additive-only, every time the app boots. Problems:

- **No down-migrations, no history, no review step.** A column rename in a model silently
  becomes "add new column, old one orphaned" — nobody notices until a report is missing data.
- **Race condition under >1 instance.** Render's `starter` plan can autoscale/restart
  concurrently; two processes running `ALTER TABLE ADD COLUMN` against the same table on boot
  is a real (if narrow) race. `Base.metadata.create_all()` has the same multi-instance boot
  race for first-time table creation.
- It's a hand-rolled substitute for Alembic, which SQLAlchemy projects have for exactly this,
  with transactional, reviewable, revertible migrations.

**Fix:** adopt Alembic. Generate a migration for current state, delete `sync_schema`, run
`alembic upgrade head` as a release step (not app-boot code).

### 1.4 Public transparency endpoint leaks bank details, unauthenticated
`backend/app/routers/reports.py:91-147` (`GET /collections/{collection_id}/transparency`)

Deliberately unauthenticated ("transparency" is the point), but it returns the community's
**live reserved bank account number** (`reserved_account`) plus per-collection financial
detail. Combined with sequential integer `collection_id`s, anyone can enumerate
`/collections/1/transparency`, `/2/...`, `/3/...` and harvest every community's bank account
number and cash position without ever logging in.

**Fix:** decide if account-number exposure is actually intended for "transparency" (probably
not — collected/pending totals and expense history are the transparent part, the account
number is not). Strip `reserved_account.account_number` from the public shape, or move full
detail behind auth and keep only aggregate totals public. Separately, consider opaque/UUID
IDs for anything reachable without auth, since ints make enumeration free.

---

## 2. High — will bite you soon

### 2.1 Global exception handler swallows every error silently
`backend/app/main.py:60-66`

```python
@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"}, ...)
```

Correct instinct (don't leak stack traces to clients, always attach CORS headers so the browser
doesn't misreport a 500 as a CORS failure) but **`exc` is never logged**. Any unhandled
exception — including ones inside payment/webhook code — vanishes with zero trace in your logs.
Add `logger.exception("unhandled error", exc_info=exc)` before returning.

### 2.2 CORS: wildcard origin, duplicated in two places
`backend/app/main.py:27-55` — both `CORSMiddleware(allow_origins=["*"])` *and* a hand-written
`force_cors` middleware that stamps `Access-Control-Allow-Origin: *` on every response,
including the exception handler.

`allow_credentials=False` makes the wildcard technically safe (browsers refuse `*` +
credentialed requests), but:
- `settings.frontend_origin` exists in config and is read... nowhere. It's dead config, same
  shape as §2.6's `expense_approval_threshold`.
- Having both `CORSMiddleware` and a raw middleware doing overlapping work is redundant and
  will confuse the next person who tries to actually lock CORS down — they'll fix one and not
  realize the other still opens it back up.

**Fix:** once you're past sandbox, use `allow_origins=[settings.frontend_origin]` and delete the
duplicate raw middleware (keep only the exception-handler CORS header, which is the one that
actually matters for the failure case being solved).

### 2.3 `get_balance` sums the whole ledger in Python, on every read
`backend/app/services/ledger.py:74-86`, called from every dashboard/report endpoint.

```python
entries = db.query(LedgerEntry).filter(...).all()
for entry in entries: balance += / -= entry.amount
```

Loads the entire ledger history into memory per call. Fine at current scale, won't be once a
community has a year of transactions. Also re-derives a value that should either be a SQL
`SUM(CASE WHEN type='credit' THEN amount ELSE -amount END)` or, better, a maintained running
balance column updated transactionally alongside each ledger insert.

### 2.4 Expense governance: the configured threshold does nothing
`settings.expense_approval_threshold` (`config.py:25`, also in `.env.example`) is **defined and
never read anywhere in the codebase** (confirmed via grep — zero other references). Expenses of
any size go through the exact same single-auditor approval (`routers/expenses.py:153-177`)
regardless of amount. Either the threshold-based extra-approval (e.g. two auditors above a
threshold) was planned and never wired up, or it's leftover config — worth deciding which
before Squad migration, since payout controls are exactly what you want tightened, not
inherited as dead config, going into a new provider integration.

### 2.5 Frontend silently fabricates data when the API is unreachable
`frontend/src/lib/api.ts` — `isOffline()` catches `TypeError` (fetch network failure) and
returns hardcoded "offline stand-in data" (`OFFLINE_USER`, `OFFLINE_COLLECTION`, etc.) instead
of surfacing the error.

For a financial app this is risky: a user whose network drops mid-flow could see a plausible
but entirely fake dashboard/collection state and not know they're looking at synthetic data
rather than a stale cache or an error. Worth confirming this is intentional (demo/offline mode)
and, if so, making it visually unmistakable in the UI — a banner, not silent substitution — so
it can never be confused with real state, especially around payment status.

### 2.6 JWT in `localStorage`, no refresh/revocation
`frontend/src/lib/api.ts:15-23`, `backend/app/core/security.py`

Standard SPA tradeoff, flagging because it's a fintech app: `localStorage` is readable by any
injected script (XSS blast radius = full account takeover, since the token is a bearer token
with no revocation list). There's also no logout-everywhere / token revocation server-side —
`create_access_token` issues a 60-minute JWT with no jti tracked, so a leaked token is valid
until it naturally expires no matter what the user does. Consider httpOnly cookies (needs CSRF
handling in exchange) or at least a server-side revocation/blacklist for compromised-token
response.

---

## 3. Medium

- **`register` has no email format validation** (`auth.py: email: str`, not `EmailStr`) and no
  password strength requirement — anything non-empty passes.
- **`CollectionMember`/expense endpoints trust client-supplied bank details** at expense
  creation (`destination_account_number` etc., `expenses.py:30-32`) with no format/existence
  validation before they're used as payout instructions later.
- **No rate limiting anywhere** — `/auth/login` and `/auth/register` are open to credential
  stuffing / brute force with no lockout, throttle, or CAPTCHA.
- **BVN accepted and stored in a plain request body** (`SetupReservedAccountIn.bvn`) — it's
  forwarded to Monnify and (per the model) not persisted, which is good, but confirm it never
  lands in logs (e.g. via an access-log middleware logging request bodies) since BVN is
  sensitive PII in Nigeria.
- **`sync_schema`'s column-type compile + f-string SQL** (`database.py:49-52`) isn't
  user-input-driven so it's not an injection vector today, but it is a raw SQL string built by
  hand instead of using SQLAlchemy DDL constructs — fragile if someone later parameterizes
  anything here.

## 4. Nits worth doing on the next pass

- `expense_approval_threshold` and `frontend_origin` are examples of config that exists but
  isn't wired up — worth a quick audit of `Settings` vs actual usage before the Squad migration
  adds more.
- Tests are solid in volume (1,646 lines across 9 files, decent endpoint coverage including a
  live-Monnify smoke test) but there's no test exercising the reserved-account webhook path
  without a signature header — i.e. no test currently proves or disproves §1.1.
- `ALL_ROLES` (all four `MemberRole`s) is redefined verbatim in five different router files —
  minor duplication, move to `app/models/enums.py` or a shared constant.

---

## 5. Monnify → Squad migration

Good news: the integration is already reasonably contained — `MonnifyService`
(`services/monnify.py`) is the only place that talks to the provider, and routers depend on it
through `monnify_service.init_transaction / verify_transaction / create_reserved_account`, not
on Monnify's wire format directly (mostly — see below). That's the right shape for a provider
swap. What needs attention:

1. **Provider-shaped fields leaked into the schema and business logic**, not just the service:
   - `Payment.monnify_transaction_reference` (models/payment.py) — provider-specific column
     name baked into the ledger model.
   - `Community.reserved_account_reference/number/bank_name/...` prefixed conceptually around
     Monnify's "reserved account" product — Squad's equivalent (virtual accounts) has different
     semantics (e.g. Squad's are typically merchant-level, not always BVN-gated the same way).
   - The webhook route is literally `/webhooks/monnify` (`payments.py:176`) and its payload
     parsing (`eventData`, `paymentReference`, `product.reference`) is Monnify's exact webhook
     shape, inlined into the router instead of the service.
   - `payment_reference` format `f"acafund-{collection_id}-{current_user.id}-{uuid4().hex[:8]}"`
     and `account_reference` format `f"acafund-comm-{community_id}"` are internal, so those
     survive a provider swap unchanged — that part's fine.

2. **Recommended shape for the migration**, given what's here:
   - Introduce a `PaymentProvider` interface (`init_transaction`, `verify_transaction`,
     `create_reserved_account`/`create_virtual_account`, `verify_webhook_signature`,
     `parse_webhook`) that both `MonnifyService` and a new `SquadService` implement, selected by
     a `PAYMENT_PROVIDER` setting. This turns the current single-provider assumption into a
     one-time abstraction cost instead of a rewrite later if you ever need to run both (e.g.
     during a phased cutover) or switch again.
   - Rename `monnify_transaction_reference` → `provider_transaction_reference`, and the
     reserved-account columns → provider-neutral names, in the same Alembic migration that
     fixes §1.3/§1.2 — don't do three separate risky migrations on a live payments table.
   - Move webhook route to `/webhooks/{provider}` or keep `/webhooks/monnify` alongside a new
     `/webhooks/squad` during cutover (you'll likely need both live briefly for in-flight
     transactions), and fix §1.1 (mandatory signature verification, server-side re-verify) as
     part of building the Squad path — don't carry the same hole into the new integration.
   - Squad's webhook signing scheme differs from Monnify's `SHA-512(secret + body)` — confirm
     Squad's actual signature mechanism before assuming the same pattern transfers.

3. Nothing here should block starting the Squad integration in parallel — the provider surface
   is small (one service file, one router, ~5 model columns) — but doing the interface
   extraction *before* wiring Squad in will save you from hardcoding Squad's shapes into the
   router the same way Monnify's got hardcoded.

---

## 6. Database "as a service," not a function inside the server

Worth separating two things that are currently blurred together, since they need different
fixes:

**What's already correct:** `render.yaml` already provisions Postgres as an independent Render
managed database (`databases: - name: acafund-db`), wired into the API via `DATABASE_URL` from
`fromDatabase`. In production, the database is *not* inside the API process — it's already a
separate managed service with its own lifecycle, backups, and scaling. That part doesn't need
architectural change.

**What's actually coupled — and is the real issue:**
1. **Schema ownership lives inside app boot code.** `main.py`'s `lifespan` calls
   `Base.metadata.create_all()` and `sync_schema()` on every process start (§1.3). That's what
   makes the database *feel* like "part of the server" — the app, not a release pipeline, owns
   and mutates the schema, at request-serving-process boot time, potentially from multiple
   instances at once. Moving to Alembic with migrations run as an explicit release step (Render
   supports a pre-deploy/release command) is what actually decouples "the database" from "the
   server" operationally — the API becomes a pure client of a schema it no longer self-manages.
2. **Local dev (`docker-compose.yml`) bundles Postgres and the API as sibling services in one
   compose file.** This is normal for local dev (not a real coupling — it's two containers, two
   processes, one network) but if the mental model bothering you is "one docker-compose file =
   one deployable unit," it isn't: `postgres` and `api` are already independently
   addressable services with a healthcheck gate between them. Nothing to change here unless you
   want local dev to point at a shared/remote dev database instead of a local container.
3. If the goal is further isolation (e.g. DB team/infra managed independently of app deploys,
   different scaling/patching cadence, or multi-service future where more than one API instance
   shares the DB) — that's already achievable today by just not redeploying the API to change
   the DB. The one thing standing in the way of that today is #1: as long as schema changes
   ride along with app boot, "redeploy the API" and "change the database" are accidentally the
   same event. Fixing the migration story is the actual unblock for the separation you're
   picturing, not moving infrastructure around.

**Recommended order:** Alembic first (§1.3) — it's the dependency for both the money-as-Decimal
fix (§1.2) and for genuinely decoupling deploy-the-API from change-the-schema. Do it before or
alongside the Squad migration's model changes (§5.2) so you're not touching the payments schema
three separate uncoordinated times.
