# GlassJar Product Requirements Document

**Version:** 2.1
**Status:** Active — 7-Day Live Ship
**Last Updated:** 2026-07-27
**PM:** Sanni Shazily
**Repo:** github.com/Automo-ASK/GlassJar
**Cadence:** Daily morning sync before build starts

---

## Table of Contents

1. [Product Summary](#1-product-summary)
2. [Problem Statement](#2-problem-statement)
3. [Strategic Direction Evolved from Feedback](#3-strategic-direction--evolved-from-feedback)
4. [Target Users and Personas](#4-target-users-and-personas)
5. [Product Vision](#5-product-vision)
6. [Goals and Success Metrics](#6-goals-and-success-metrics)
7. [Functional Requirements](#7-functional-requirements)
8. [Non-Functional Requirements](#8-non-functional-requirements)
9. [Full Feature List](#9-full-feature-list)
10. [Key User Flows](#10-key-user-flows)
11. [Technical Architecture Decisions](#11-technical-architecture-decisions)
12. [Out of Scope Now](#12-out-of-scope-now)
13. [7-Day Sprint Table by Department](#13-7-day-sprint-table-by-department)
14. [Engineering Rules](#14-engineering-rules)

---

## 1. Product Summary

GlassJar (also called GlassJar) is a financial operating system for student communities in Nigeria. A class rep creates a community, builds the member roster without requiring members to sign up, opens a collection for any purpose (class dues, social events, trips, fundraisers), and shares one payment link. Every member can see live who has paid, who has not, and where every naira went. The system is transparent by default, trustless by design, and built for the informal financial reality of African student life.

The product is post-hackathon and shipping live in 5 days. This PRD captures the complete product as it should exist not as it was rushed. Every dev builds from this document, not from the existing codebase.

---

## 2. Problem Statement

In Nigerian universities, class reps and student community treasurers manage collective money through a stack of informal tools: bank transfer details shared on WhatsApp, payment screenshot screenshots flooding DMs, Excel sheets updated manually, and verbal reassurances that funds were spent correctly.

This creates four compounding failures:

**Verification failure.** The rep has no way to auto-verify who actually transferred money versus who claims they did. Every payment requires manual cross-checking.

**Trust failure.** At the end of a collection cycle, the rep cannot prove to the class that they did not misappropriate funds. There is no shared financial record. Accusations are common.

**Efficiency failure.** A single class of 200 students running 5 collections per year generates over 1,000 manual payment verifications per rep per year. This is unpaid administrative work on top of academic responsibilities.

**Accountability failure.** When the class spends collected funds, there is no formal approval chain. A treasurer submits expenses informally and members have to take their word for it.

GlassJar replaces this entire informal stack with one platform. The payment is collected through a verified gateway, reconciled automatically, and logged immutably. The ledger is visible to all members. Expenses require auditor approval and produce a public proof trail. The class rep goes from accountant to administrator.

---

## 3. Strategic Direction Evolved from Feedback

The following decisions reflect where the product is going based on all received feedback. These shape every feature priority in this document.

### 3.1 Expand the Use Case: Not Just Class Dues

The original concept was narrow class reps collecting semester dues. The feedback points to a much broader use case that the infrastructure already supports. GlassJar should be the go-to platform for any informal money collection among a defined group of people in a student context:

- Class dues (original)
- Social events (owambe, outings, dinners)
- Departmental fundraisers
- Club and association collections
- Sports team kits and logistics
- Faculty association levies
- Student election campaign contributions (where legal)
- Study trip deposits
- Project material pooling

The product needs to present itself this way from the landing page through the collection creation flow. Collections should have a "type" that sets the right tone and defaults.

### 3.2 Payment Confirmation Must Be Bulletproof

The single biggest user complaint: "I paid, left the page, came back, and the system does not recognize my payment. I have to start over."

This is a trust-destroying experience. If GlassJar cannot reliably confirm that a payment happened, it fails at its core job. The fix is not a better polling loop. The fix is:

1. Squad webhook is the source of truth. The moment Squad confirms the payment server-side, the entry is marked paid, regardless of whether the user's browser is open.
2. The user's payment session is stored by reference on the backend not in sessionStorage. The browser can crash, the user can close and reopen, and the system still knows where they are.
3. The confirmation page actively polls the backend (not the payment gateway) and reaches a conclusive state: PAID, FAILED, or STILL PROCESSING.
4. "Still processing" is a valid, communicated state with a time expectation. The user is told: "Bank transfers can take up to 30 minutes. We will email you when confirmed."
5. Every confirmed payment sends an email to the payer and a notification to the admin and course rep immediately.

### 3.3 Dispute Resolution Is a Feature, Not a Support Process

A dispute mechanism was mentioned in feedback. This needs to be a first-class product feature, not an email to a support address. Users must be able to submit a dispute from within the app, attach their payment proof, and receive a resolution within 12 to 24 hours. The GlassJar admin team resolves disputes from a dedicated internal dashboard.

### 3.4 Full UI Revamp Is Non-Negotiable Before Launch

The hackathon frontend is a rough draft. Before real users touch this product, every screen needs to be rebuilt with a clear design system. This is the first priority in the build sprint, not the last. A product that looks untrustworthy will not be trusted with money.

### 3.5 Squad API Replaces Monnify

The payment gateway migration from Monnify to Squad is a hard requirement. All payment-related feature work targets Squad from day one. No new Monnify code is written. Existing Monnify code is deprecated after Squad is verified in staging.

### 3.6 The Admin Dashboard Is GlassJar's Control Room

GlassJar needs to know what is happening on the platform at all times. The internal admin dashboard (visible to the GlassJar team, not community admins) shows real-time user activity, payment volumes, dispute queues, and system health. This is both a trust tool and a business intelligence tool.

### 3.7 Revenue Strategy Is Embedded in the Product

GlassJar charges 1.5% per verified transaction. This is collected transparently. The Pro tier at 5,000 naira per community per month unlocks advanced features. Institution licensing is a later play. Every product decision must be compatible with these revenue streams becoming active without disrupting current users.

---

## 4. Target Users and Personas

### Persona 1 Aisha, the Class Rep (Primary)

200-level Economics student at UNILAG. Appointed class rep by her peers. Runs 4 to 6 collections per academic year covering dues, department events, and faculty levies. Currently spends 3 hours per collection manually verifying screenshots on WhatsApp and updating an Excel sheet she shares with no one. Has been accused of mismanagement twice because there was no public record. She uses GlassJar to create a collection, share a link, and never answer "have you confirmed my payment?" again.

**Job to be done:** Run a collection start to finish without manual verification or defending myself against accusations.

### Persona 2 Chidi, the Treasurer (Secondary)

Appointed by the admin. Manages disbursement after collection closes. Needs to submit expenses, get independent approval, and produce a paper trail that proves every kobo was spent correctly. Currently writes expense reports in a Word document and sends them to no one. He uses GlassJar to submit an expense with a receipt, get auditor approval, mark it paid, and point the class to the transparency report.

**Job to be done:** Spend collected funds without anyone questioning my honesty.

### Persona 3 Emeka, the Regular Member (Tertiary)

Third-year student. Gets a WhatsApp link from Aisha. Does not want to download an app or create an account to pay his 5,000 naira dues. Opens the link, finds his name, pays through the gateway, gets an email confirmation, and is done in under 3 minutes. Later, when the class claims only 60% of funds was collected and he wants to verify, he opens the public transparency report.

**Job to be done:** Pay what I owe quickly, get confirmation, and verify that collected money was used correctly.

### Persona 4 The GlassJar Admin (Internal)

The GlassJar team member monitoring the platform. Needs to see all communities, payment volumes, dispute queues, flagged transactions, and system health from one dashboard. Resolves disputes submitted by users within 12 to 24 hours.

**Job to be done:** Keep the platform healthy and resolve user problems before they become public complaints.

---

## 5. Product Vision

GlassJar is the financial operating system for student communities in Africa. Any class, association, or student group can collect money for any purpose, govern spending transparently, and prove accountability to every member from a single shared link. The class rep stops being the cashier. The ledger is the cashier.

In 18 months: active in 10+ Nigerian universities, processing over 100 million naira in verified collections per semester, with the first institution-level licensing agreement signed.

---

## 6. Goals and Success Metrics

### 5-Day Launch Goals

| Goal | Metric | Target |
|------|--------|--------|
| Core payment flow works end to end | Payments verified and ledger updated | 100% success rate in staging |
| Squad integration live | Guest payment via Squad checkout functional | Yes |
| Zero ghost sessions | Auth errors surface correctly, expired JWTs redirect | Pass |
| Email notifications firing | Email to payer within 60s of payment | 100% |
| UI revamp shipped | All core screens rebuilt on design system | Yes |
| Dev process in place | All work on branches, no direct main pushes | Yes |

### 8-Week Post-Launch Goals

| Goal | Metric | Target |
|------|--------|--------|
| UNILAG adoption | Active communities | 20+ |
| Collection completion rate | Collections with over 70% of members paid | 60%+ |
| Payment reliability | Payments requiring manual dispute | Less than 2% |
| Retention | Communities running a second collection | 60%+ |
| Revenue | Transaction fees collected | First naira within week 2 |

### 6-Month Goals

| Goal | Metric | Target |
|------|--------|--------|
| Multi-university presence | Universities with active communities | 5+ |
| Payment volume | Total naira processed | 5M+ |
| NPS | Would recommend to another class rep | 50+ |

---

## 7. Functional Requirements

Functional requirements describe what the system must do. Every feature in section 9 maps to one or more of these.

### FR-01: Authentication and Identity

The system must allow users to register with email and password. Registration must produce a clear error if the email is already in use, if the password is too short, or if any required field is missing. Login must produce a clear error for wrong credentials, not a redirect to the app. A user whose JWT has expired or been revoked must be redirected to the login screen immediately, not kept in the app with a ghost identity. Sessions are server-side revocable at all times.

### FR-02: Community and Roster Management

The system must allow an authenticated user to create a community and become its admin. The admin must be able to add members by name in bulk without those members needing to register. Members must be able to register later and claim their roster entry using the community invite code. The admin must be able to assign roles (treasurer, auditor, member) to any registered member. A member with payment history cannot be removed. The community dashboard must display all key metrics (treasury balance, active collections, pending expenses, member count) in a single view.

### FR-03: Collections

The system must allow the admin or treasurer to create a collection with a name, description, collection type, target amount, per-member amount, deadline, and budget allocation percentages. The collection must generate a unique public share link on creation. The roster is enrolled into the collection automatically. New members added after collection creation can be synced in. The collection can be closed by the admin. Collection status (active, closed) must be clearly surfaced in the UI.

### FR-04: Payments

The system must process guest payments (no account required) through a public share link using the Squad payment gateway. The system must process card payments and bank transfers. The payment session must be persisted on the backend by payment reference so that the user can leave the page, return, and the system still knows the state of their payment. The system must confirm payment via Squad webhook before marking any entry as paid. The confirmation state must reach a conclusive result: PAID, FAILED, or STILL PROCESSING (with a time estimate communicated to the user). The system must mark manual payments (cash, off-platform transfer) with a note and full audit trail. The system must allow waiving a member's payment with a reason. Every waive and revert creates a ledger entry. The treasurer must be able to trigger payment sync, not just the admin.

### FR-05: Notifications

The system must send an email to the payer within 60 seconds of payment confirmation. The system must send an email or in-app notification to the admin and course rep when any payment is received. The system must notify the treasurer when an expense is approved or rejected. The system must notify the expense submitter of approval or rejection. The system must notify the dispute submitter of resolution status.

### FR-06: Expense Management

The system must allow the treasurer to submit an expense with an amount, description, and optional receipt file upload. The system must route the expense to an auditor for independent approval or rejection. The auditor must not be the same person as the treasurer (enforced by role). The system must allow the treasurer to mark an approved expense as paid out with a bank transfer reference. Every approved payout must post a debit entry to the ledger. Rejected expenses must be logged with the rejection reason.

### FR-07: Ledger

The system must maintain an append-only ledger where every credit (payment received, manual mark) and debit (expense payout, revert) is recorded with a timestamp, reference, actor, and running balance. The balance is always derived from ledger entries, never stored as a field. The ledger must support pagination so all historical entries are accessible. The same source event can never post to the ledger twice.

### FR-08: Transparency and Public Reports

The system must expose a public transparency report for any collection accessible without login. The report must show: total collected versus target, breakdown by budget allocation, every approved expense with description, amount, receipt, and payout reference. The report URL is shareable and loads fast with no auth wall.

### FR-09: Disputes

The system must allow any user who believes their payment was not confirmed to submit a dispute from within the app. The dispute must capture: the member name, collection, payment amount, payment method, reference number, and an optional screenshot upload. The GlassJar admin team must receive a notification for every new dispute. The admin dashboard must show all open disputes with status. Every dispute must be resolved within 12 to 24 hours. The submitter must be notified by email on resolution.

### FR-10: AI Treasury Assistant

The system must expose an AI assistant within each community that answers questions grounded in the community's actual ledger data. The assistant must not hallucinate balances or transactions. Starter prompts must be shown. The assistant must answer questions such as how much has been collected, who still has not paid, what the current balance is after approved expenses, and what percentage of the budget has been spent.

### FR-11: Internal Admin Dashboard

The GlassJar team (not community admins) must have access to an internal dashboard that shows: all communities on the platform, total payment volume, active disputes, flagged transactions, new registrations, community health metrics, and system error rates. The dashboard must support searching and filtering by community, date range, and status.

### FR-12: Landing Page

The landing page must accurately represent the product. It must show live or real aggregated stats (communities created, naira processed, members served). It must clearly communicate the three core use cases (class dues, events, fundraisers). It must have a clear call to action for class reps to create their first community. It must be fast, mobile-first, and not contain any hardcoded placeholder numbers.

---

## 8. Non-Functional Requirements

Non-functional requirements describe how the system must behave, not just what it does. These apply to the entire product.

### NFR-01: Reliability

Payment-related operations must have a success rate of 99.5% or higher in production. No payment must be lost due to a webhook delivery failure. Webhook events must be idempotent delivering the same event twice must produce the same outcome as delivering it once. The system must retry failed webhook processing at least 3 times with exponential backoff before alerting.

### NFR-02: Network Error Resilience

Every API call from the frontend must handle network errors explicitly. Network failure must never silently put the user in an inconsistent state. If a payment request fails due to a network error, the user must be told clearly and given a retry path. If the payment went through but the confirmation request failed, the system must recover via the webhook or the dispute flow, not by asking the user to pay again.

### NFR-03: Security

All financial data must be transmitted over HTTPS only. JWT secrets must be at least 32 characters. Passwords must be hashed with bcrypt. The system must validate all webhook signatures using Squad's HMAC before processing any payment event. All endpoints that write financial state must be role-gated at the service layer, not only the router layer. Rate limiting must be Redis-backed in production (not in-memory). No sensitive credentials appear in any frontend code or public repository.

### NFR-04: Performance

The public payment page must load in under 2 seconds on a 4G connection. The community dashboard must load in under 1 second after first render (use the single dashboard endpoint, not 4 separate calls). The transparency report must load in under 1.5 seconds. All API endpoints must respond in under 500ms under normal load.

### NFR-05: Data Integrity

Money amounts must be stored as NUMERIC(12,2) in the database never as floats. Balance must always be derived from the ledger via SUM, never stored. Every ledger entry must have a unique reference constraint. Manual payment marks can be reverted but never deleted revert creates a balancing debit entry. Audit logs must capture every action that changes financial state, including who performed the action and when.

### NFR-06: Scalability

The rate limiter must work correctly across multiple server instances. Sessions must not depend on any single server's memory. Payment reference tracking must be backend-persisted, not browser-persisted.

### NFR-07: Mobile Responsiveness

Every screen must be fully functional and visually correct on a 375px wide mobile screen. The public payment page (the most used screen by members) must be optimized for mobile-first. Touch targets must be at least 44px. No horizontal scrolling on any screen.

### NFR-08: Accessibility

All interactive elements must be keyboard navigable. Color alone must not convey status (use icons + color together). Text must meet WCAG AA contrast ratios.

### NFR-09: Developer Experience

A `.env.local` template must exist and be documented in the README. Any developer must be able to run the full stack locally in under 10 minutes following the README. Migrations must be automated and run on boot. No developer should ever need to manually configure a database connection string beyond copying the env template.

### NFR-10: Observability

All payment events must be logged with enough context to reconstruct what happened. All errors in payment flows must be captured with a stack trace. The admin dashboard must surface error rates and failed webhook deliveries in real time.

---

## 9. Full Feature List

Priority tiers: **SHIP** (live in 5 days), **NEXT** (week 2-3 post launch), **LATER** (post-traction)

Each feature has an acceptance test. A feature is not done until its acceptance test passes.

---

### 9.1 Authentication and Identity

**F-A01: User Registration with Correct Error Handling**
Priority: SHIP
Description: User registers with email and password. If email already exists, the form shows "This email is already registered. Try logging in." If password is under 8 characters, the form shows the rule before submission. Network errors show a retry option. Successful registration lands the user on the communities screen.
Acceptance test: Register with a duplicate email and confirm the 409 error is surfaced as a readable message, not a fake redirect to /communities. Register with a bad password and confirm the error appears before any API call is made.

**F-A02: Login with Correct Error Handling**
Priority: SHIP
Description: User logs in with email and password. Wrong credentials show "Incorrect email or password." Network error shows a retry option. Success redirects to /communities.
Acceptance test: Log in with wrong password and confirm the error message appears. Log in successfully and confirm redirect. Confirm no local-session fallback exists in the codebase.

**F-A03: Session Integrity Expired JWT Redirect**
Priority: SHIP
Description: When the server returns 401 on any request because the JWT is expired or revoked, the user is redirected to /login immediately. No ghost user object is set. No PLACEHOLDER_USER exists in the codebase.
Acceptance test: Manually revoke a token via POST /auth/logout, then make a protected API call in the same browser session. Confirm redirect to /login occurs and no app screen is shown.

**F-A04: Logout**
Priority: SHIP
Description: Logging out calls POST /auth/logout, revokes the token server-side, clears the JWT from localStorage, and redirects to /login.
Acceptance test: Log in, log out, hit the back button. Confirm the protected page does not load.

**F-A05: Per-Community Role System**
Priority: SHIP
Description: Four roles per community: admin, treasurer, auditor, member. Role is embedded in community membership, not global. Admin can assign any role to any registered member. An unclaimed roster entry (no user account linked) cannot hold governance roles.
Acceptance test: Assign treasurer role to a member. Confirm that member can now create collections and submit expenses. Confirm a plain member cannot.

**F-A06: Email Verification on Registration**
Priority: NEXT
Description: After registration, user receives an email with a verification link. Unverified users can browse but cannot create communities or open collections. Verified badge shown on profile.
Acceptance test: Register, do not click verification email, attempt to create a community. Confirm the system blocks with a clear message and prompts to verify.

**F-A07: Password Reset via Email**
Priority: NEXT
Description: User requests password reset from /login. System sends a time-limited reset link (valid 30 minutes). Link leads to a form where user sets a new password. Old password immediately stops working.
Acceptance test: Request reset, use the link, set new password, log in with new password. Confirm old password no longer works.

---

### 9.2 Communities and Roster

**F-C01: Create Community**
Priority: SHIP
Description: Authenticated user creates a community with a name and optional description. Creator automatically becomes admin. System generates a unique invite code. Community is immediately accessible.
Acceptance test: Create a community. Confirm creator role is admin. Confirm invite code is unique and visible.

**F-C02: Bulk Add Members (No Account Required)**
Priority: SHIP
Description: Admin adds members by name (and optional phone/email) in bulk via paste or CSV. These entries exist on the roster without needing a user account. No member is forced to register just to be tracked.
Acceptance test: Add 10 members by name only. Confirm all 10 appear on the roster with status "unclaimed." Confirm none of them need to log in for a payment to be recorded against them.

**F-C03: Add Single Member**
Priority: SHIP
Description: Admin adds one member by name at any time.
Acceptance test: Add one member. Confirm member appears on roster. Confirm the member can be enrolled into any active collection.

**F-C04: Join via Invite Code and Claim Roster Entry**
Priority: SHIP
Description: A registered user enters the invite code, sees the community preview and any claimable roster entries matching their name, and claims their entry. Their account is now linked to that roster entry and they gain visibility into their payment history.
Acceptance test: Create a roster entry for "Emeka Okafor." Register as a user named Emeka Okafor. Join with the invite code. Confirm the claim links the account to the roster entry and payment history is visible.

**F-C05: Role Management**
Priority: SHIP
Description: Admin can change any member's role. Admin cannot demote themselves while they are the only admin (must assign another admin first). Role changes take effect immediately.
Acceptance test: Assign treasurer to member A. Confirm member A can now create collections. Try to demote the only admin and confirm the system blocks it.

**F-C06: Remove Member**
Priority: SHIP
Description: Admin can remove a member from the community. Removal is blocked if the member has any payment history in any collection. Blocked removal shows a clear explanation.
Acceptance test: Try to remove a member with a paid entry. Confirm the system blocks removal and explains why. Remove a member with no payment history and confirm removal succeeds.

**F-C07: Community Dashboard Single API Call**
Priority: SHIP
Description: The community home screen loads via a single call to GET /communities/{id}/dashboard and displays: treasury balance, active collections count, pending expense count, member count, and recent ledger entries.
Acceptance test: Load the community home screen and confirm only one network request is made to the dashboard endpoint. Confirm treasury balance is displayed correctly based on ledger SUM.

**F-C08: Reserved Account Setup (Squad)**
Priority: SHIP
Description: Admin can set up a dedicated bank account for the community via Squad, allowing members to pay by direct bank transfer to a fixed account number. Account details are displayed and copyable.
Acceptance test: Set up a reserved account in the Squad sandbox. Confirm account number is displayed. Confirm a simulated transfer to the reserved account updates the ledger.

---

### 9.3 Collections

**F-CL01: Create Collection Multi-Type**
Priority: SHIP
Description: Admin or treasurer creates a collection with: name, type (class dues, social event, fundraiser, trip, other), description, per-member amount, total target, deadline, and budget allocation percentages that must sum to 100%. The collection is active immediately on creation. A unique public share token is generated.
Acceptance test: Create a collection of type "social event." Confirm it appears in the collection list. Confirm the share link works and loads the public payment page. Confirm budget allocations that do not sum to 100% are rejected.

**F-CL02: List Collections**
Priority: SHIP
Description: Admin, treasurer, and auditor see all collections. Members see active collections they are enrolled in. Closed collections are shown with a clear status badge.
Acceptance test: Create two collections, close one. Log in as a member. Confirm the member sees active collections only from their enrollment. Log in as admin. Confirm both collections are visible.

**F-CL03: Collection Detail with Progress**
Priority: SHIP
Description: The collection detail page shows: total collected, total target, progress bar, list of all members with paid/unpaid/waived status, deadline, and the share link.
Acceptance test: Open a collection with 3 paid, 2 unpaid, 1 waived. Confirm the progress bar reflects 3/6 (or 3/5 if waived is excluded from denominator define this and stick to it). Confirm each member shows correct status.

**F-CL04: Close Collection**
Priority: SHIP
Description: Admin can close a collection. Closed collections accept no new payments. Existing payments remain in the ledger. Transparency report remains accessible.
Acceptance test: Close a collection. Try to pay via the public link. Confirm the system rejects the payment with a message that the collection is closed.

**F-CL05: Sync New Members into Collection**
Priority: SHIP
Description: After a collection is created, if new members are added to the community roster, admin can sync them into active collections. Synced members are added to the collection entries with unpaid status.
Acceptance test: Create a collection with 10 members. Add 2 new members to the roster. Sync. Confirm the collection now shows 12 entries with the 2 new members as unpaid.

**F-CL06: Treasurer Can Create Collections**
Priority: SHIP
Description: The "New Collection" button is visible and functional for users with the treasurer role, not only admin.
Acceptance test: Log in as a treasurer. Confirm "New Collection" button is visible. Create a collection. Confirm it is created successfully.

---

### 9.4 Payments

**F-P01: Guest Payment via Public Share Link (Squad)**
Priority: SHIP
Description: Any person opens the public share link without logging in. They see the collection name, type, and target. They search for their name on the roster. They click Pay. Squad checkout opens. They complete payment by card or bank transfer. The checkout is styled and branded for GlassJar where Squad's API permits.
Acceptance test: Open the share link in an incognito browser. Find a name. Click Pay. Complete payment in Squad sandbox. Confirm the entry is marked paid in the admin view within 30 seconds.

**F-P02: Payment Session Persistence**
Priority: SHIP
Description: When a user is redirected to Squad checkout and then returns (whether they complete payment, close the tab, or refresh), the system knows their payment reference. The confirmation page loads the correct state for that reference without requiring them to search again.
Acceptance test: Start a payment. Before completing, close the tab. Reopen the share link. Navigate to payment return URL with the same reference. Confirm the system shows the correct in-progress or completed state.

**F-P03: Bulletproof Payment Confirmation**
Priority: SHIP
Description: Payment confirmation is driven by Squad webhook server-side. The moment Squad sends a successful event, the entry is marked paid and the ledger is updated, regardless of whether the user's browser is open. The frontend confirmation page polls the backend (not Squad directly) for up to 30 minutes on unresolved sessions, checking every 5 seconds. If payment is confirmed during polling, the page updates immediately. If the 30-minute window expires without confirmation, the user is shown a clear message and the dispute flow is offered.
Acceptance test: Simulate a successful Squad webhook. Confirm the entry is marked paid in the database. Open the confirmation page after the webhook fires. Confirm it shows PAID. Simulate a slow bank transfer where the webhook arrives 5 minutes after checkout. Confirm the polling page updates correctly when the webhook arrives.

**F-P04: Bank Transfer Confirmation "Still Processing" State**
Priority: SHIP
Description: Bank transfers can take minutes. The confirmation page must explicitly tell the user: "Bank transfers can take up to 30 minutes. We are checking automatically. You will receive an email when confirmed." A visible spinner and elapsed time counter are shown. The user can leave the page safely because the webhook will confirm independently.
Acceptance test: Load the confirmation page for an unconfirmed bank transfer. Confirm the "still processing" state is displayed, not an error. Confirm the page continues polling. Fire the webhook manually. Confirm the page transitions to PAID state.

**F-P05: Payment Confirmation Email to Payer**
Priority: SHIP
Description: Within 60 seconds of a payment being confirmed (via webhook or manual mark), an email is sent to the payer's email address (if provided during checkout or from their account). The email includes: community name, collection name, amount paid, date, and transaction reference.
Acceptance test: Complete a payment with an email address provided. Confirm an email is received within 60 seconds. Confirm it contains the correct collection name, amount, and reference.

**F-P06: Payment Notification to Admin and Course Rep**
Priority: SHIP
Description: When any payment is confirmed, the community admin and any member with the course-rep sub-role receive an email or in-app notification with the payer name, amount, and collection name.
Acceptance test: Complete a payment. Log in as admin. Confirm a notification appears in the app or inbox within 60 seconds.

**F-P07: Manual Mark (Cash or Off-Platform Transfer)**
Priority: SHIP
Description: Treasurer or admin can manually mark a member's entry as paid, recording the payment method (cash or transfer), the amount, the date, and a note. The mark is recorded in the audit log with the marker's identity and timestamp.
Acceptance test: Manually mark a member as paid via cash. Confirm the ledger has a credit entry with the correct amount and note. Confirm the audit log shows who marked it and when.

**F-P08: Waive Payment**
Priority: SHIP
Description: Admin can waive a member's payment obligation with a mandatory reason. The waived entry is displayed with a "Waived" badge. The waive is logged in the audit trail.
Acceptance test: Waive a member. Confirm the badge shows "Waived." Try to waive without a reason. Confirm the system blocks it.

**F-P09: Revert Manual Mark or Waive**
Priority: SHIP
Description: Admin can revert a manual mark or a waive. Revert posts a balancing debit to the ledger (never deletes the original entry). The member entry returns to unpaid status.
Acceptance test: Mark a member paid manually. Revert it. Confirm the ledger has both the original credit and a balancing debit. Confirm the member shows unpaid.

**F-P10: Treasurer Payment Sync Permission**
Priority: SHIP
Description: The treasurer role can call POST /payments/{id}/sync. This is currently admin-only, which is inconsistent with the treasurer's other permissions.
Acceptance test: Log in as treasurer. Trigger payment sync on an unresolved session. Confirm the system processes the sync without a 403 error.

**F-P11: Payment Dispute Submission**
Priority: SHIP
Description: Any user who believes their payment was not confirmed can submit a dispute from the app. The dispute form captures: name, collection name, amount, payment method, transaction reference, and an optional screenshot upload. The dispute is stored and the GlassJar admin team is notified.
Acceptance test: Submit a dispute with all required fields. Confirm it appears in the internal admin dashboard. Confirm the submitter sees a "dispute submitted" state with a reference number.

**F-P12: Dispute Resolution by Admin**
Priority: SHIP
Description: The GlassJar admin team views all open disputes in the internal dashboard, can review the submitted reference and screenshot, and resolves the dispute by either confirming the payment (which triggers the manual mark flow) or rejecting it with a reason. The submitter is emailed on resolution.
Acceptance test: Submit a dispute. Open the admin dashboard. Resolve the dispute as confirmed. Confirm the member's entry is marked paid. Confirm the submitter receives an email.

---

### 9.5 Expenses and Ledger

**F-E01: Expense Submission**
Priority: SHIP
Description: Treasurer submits an expense with: description, amount, category, and optional receipt file upload (image or PDF). Expense is created in "pending" status.
Acceptance test: Submit an expense with a receipt file. Confirm it appears in the expense list with "Pending Approval" status. Confirm the auditor sees it in their queue.

**F-E02: Expense Approval and Rejection by Auditor**
Priority: SHIP
Description: Auditor opens an expense from the expense list via a dedicated GET /expenses/{id} endpoint (not a client-side .find() hack). Auditor approves or rejects with a mandatory reason for rejection. Each action is logged with the auditor's identity and timestamp.
Acceptance test: Navigate directly to /expenses/{id} with no query string. Confirm the page loads correctly. Approve the expense. Confirm status changes to "Approved." Reject a different expense with a reason. Confirm status changes to "Rejected" with reason visible.

**F-E03: Mark Expense Paid Out**
Priority: SHIP
Description: Treasurer marks an approved expense as paid out with a bank transfer reference. This posts a debit to the ledger equal to the expense amount. The transparency report updates to include the payout with the bank reference as proof.
Acceptance test: Approve an expense. Mark it paid out with a reference. Confirm the ledger shows a debit entry. Confirm the transparency report shows the expense with the payout reference.

**F-E04: Expense Receipt File Upload**
Priority: SHIP
Description: Treasurer can attach an image (JPG, PNG) or PDF receipt when submitting an expense. The file is stored in cloud storage (Cloudinary or equivalent). The URL is stored against the expense record. Auditors and the transparency report can view the receipt.
Acceptance test: Upload a JPG receipt with an expense. Confirm the file URL is stored. Open the transparency report. Confirm the receipt is linked and viewable.

**F-E05: Ledger with Full Pagination**
Priority: SHIP
Description: The ledger page shows all credit and debit entries in reverse chronological order with a running balance. The user can page through all historical entries (not just the most recent 20). Each entry shows: date, description, amount, type (credit/debit), and actor.
Acceptance test: Create 25 ledger entries. Open the ledger. Confirm you can navigate beyond the first 20. Confirm the running balance is correct on every entry.

**F-E06: Ledger Export**
Priority: NEXT
Description: Admin or treasurer can export the full ledger as a CSV file. Export includes all columns: date, reference, description, credit, debit, balance, actor.
Acceptance test: Export ledger. Open CSV. Confirm all entries are present and the balance column is correct.

---

### 9.6 Transparency and Public Reports

**F-R01: Public Transparency Report**
Priority: SHIP
Description: Every collection has a public transparency URL accessible without login. The report shows: collection name and type, total collected versus target, progress percentage, budget breakdown by allocation category, every approved expense with description, amount, receipt link, and payout bank reference.
Acceptance test: Open the transparency report URL in an incognito browser. Confirm it loads without auth. Confirm it shows correct amounts matching the ledger.

**F-R02: Public Collection Progress Page**
Priority: SHIP
Description: The public payment page shows real-time collection progress: total collected, total target, how many members have paid, how many have not. This is visible to anyone with the link, without login.
Acceptance test: Open the public payment link. Confirm the progress stats are visible and up to date.

---

### 9.7 AI Treasury Assistant

**F-AI01: Ledger-Grounded AI Assistant**
Priority: SHIP
Description: Each community has an AI assistant that answers questions about the community's financial state. The assistant is grounded exclusively in verified ledger data from that community. It must not guess or hallucinate any financial figures. The assistant answers in plain language.
Acceptance test: Ask "How much have we collected?" Confirm the answer matches the ledger SUM exactly. Ask about a payment that did not happen. Confirm the assistant says there is no record of it rather than making one up.

**F-AI02: Starter Prompts**
Priority: SHIP
Description: The assistant UI shows 4 to 6 suggested prompts when opened: "How much have we collected?", "Who still has not paid?", "What is our current balance?", "Show me all approved expenses", "What percentage of the budget is spent?", "How many members have paid this collection?"
Acceptance test: Open the assistant. Confirm starter prompts are shown. Click each one and confirm the assistant responds with correct data.

**F-AI03: Upgrade Assistant to Claude Sonnet**
Priority: NEXT
Description: Replace NVIDIA Nemotron with Claude claude-sonnet-4-6 for better response quality, nuanced financial reasoning, and more natural conversational follow-ups.
Acceptance test: Ask three complex follow-up questions in a single session. Confirm the assistant maintains context and gives accurate answers.

---

### 9.8 Frontend and UX

**F-UX01: Design System**
Priority: SHIP (Day 1)
Description: A consistent design system covering: color palette (primary green, neutrals, error states, success states), typography scale, spacing scale, component library (buttons, inputs, badges, cards, modals, tables, empty states, loading states), and icon set. Every screen is built using this design system no ad-hoc styles.
Acceptance test: Open 5 different screens. Confirm fonts, colors, spacing, and component styles are consistent across all of them.

**F-UX02: Full Frontend Rebuild**
Priority: SHIP
Description: Every screen is rebuilt from scratch using the design system. The hackathon frontend is replaced entirely. Screens covered: Landing, Register, Login, My Communities, Create Community, Join Community, Community Home (dashboard), Members, Collections List, Create Collection, Collection Detail, Expenses List, Create Expense, Expense Approval, Ledger, Treasury Assistant, Public Payment Page, Payment Return, Transparency Report.
Acceptance test: Open every route in the app. Confirm no screen uses unthemed styles, hardcoded colors, or broken layouts. Confirm every screen has a correct loading state and error state.

**F-UX03: Role-Aware UI**
Priority: SHIP
Description: Every UI element that triggers a role-gated action is hidden from users who do not have permission to take that action. Specifically: "New Collection" is visible to admin and treasurer only. "New Expense" FAB is visible to treasurer only. Expense approval actions are visible to auditor only. No user ever reaches a form only to get a 403 on submission.
Acceptance test: Log in as each role (admin, treasurer, auditor, member) and open every screen. Document every action button visible per role. Confirm no button is shown that would 403 on use.

**F-UX04: Error States and Loading States**
Priority: SHIP
Description: Every data-fetching screen has an explicit loading state (skeleton or spinner) and an explicit error state (message + retry action). No screen is ever blank without explanation.
Acceptance test: Disconnect the network mid-session. Navigate to the community dashboard. Confirm a clear error state with a retry button appears rather than a blank screen.

**F-UX05: Mobile-First Responsive Design**
Priority: SHIP
Description: Every screen is designed and tested at 375px width first. Touch targets are at least 44px. No horizontal scroll. The public payment page (highest traffic) is specifically optimized for mobile.
Acceptance test: Open every screen on a physical or simulated iPhone SE screen. Confirm no horizontal scroll, no overflowing text, and all buttons are tappable.

**F-UX06: Real Landing Page**
Priority: SHIP
Description: The landing page communicates what GlassJar does in 10 seconds. It shows the three primary use cases (class dues, social events, fundraisers). It shows real platform stats (pulled from the backend or seeded with real launch data). It has a single clear call to action for class reps. It does not contain placeholder text.
Acceptance test: Show the landing page to someone who has never heard of GlassJar. Within 10 seconds they must be able to describe what it does and what they would do next. Confirm no hardcoded stats appear on the live version.

---

### 9.9 Infrastructure and Platform

**F-INF01: Squad API Integration**
Priority: SHIP
Description: Full migration from Monnify to Squad API covering: checkout initiation, reserved account setup, webhook verification (Squad's signature format), payment reference lookup, and transaction status check. All Monnify code is deleted after Squad is verified in staging.
Acceptance test: Run the full guest payment flow in Squad sandbox from link open to ledger credit with no Monnify code touched. Confirm webhooks are verified using Squad's HMAC signature.

**F-INF02: Email Service Integration**
Priority: SHIP
Description: Integrate a transactional email provider (Resend recommended for developer experience). All emails defined in FR-05 are templated and firing in production. Emails are transactional only.
Acceptance test: Complete a payment. Confirm an email is received within 60 seconds. Confirm the email is correctly formatted and contains accurate information.

**F-INF03: Network Error Handling Frontend**
Priority: SHIP
Description: Every fetch call in the frontend is wrapped in error handling that distinguishes between network errors (no internet, timeout) and API errors (4xx, 5xx). Network errors show a "No connection check your internet and retry" message. 4xx errors show the specific error from the API. 5xx errors show a generic "Something went wrong" with a retry option.
Acceptance test: Disable network in browser devtools. Click any action button. Confirm a clear network error message appears. Re-enable network, retry. Confirm the action succeeds.

**F-INF04: Redis-Backed Rate Limiting**
Priority: SHIP
Description: The rate limiter is backed by Redis, not in-memory. This ensures consistent rate limiting across all server instances in a multi-instance Render deploy.
Acceptance test: Deploy two instances of the backend. Send 100 requests alternating between both instances. Confirm rate limits are applied globally, not per-instance.

**F-INF05: Local Dev Environment Setup**
Priority: SHIP (Day 1)
Description: A `.env.local` template exists in the repo root for frontend and a `.env.example` exists in `/backend`. The README documents exactly how to get the full stack running locally from zero. Any developer must be able to run the stack locally in under 10 minutes.
Acceptance test: Follow the README from a fresh machine clone with no prior project knowledge. Confirm the full stack is running and the app is usable within 10 minutes.

**F-INF06: Internal Admin Dashboard**
Priority: SHIP
Description: A separate dashboard accessible only to the GlassJar team (not community admins). Shows: total communities, total members, payment volume by day/week, active disputes, new signups by day, system error rates, and failed webhook deliveries. Accessible via a separate route with GlassJar-level admin credentials.
Acceptance test: Log in as GlassJar admin. Confirm the dashboard shows real data. Create a payment in staging. Confirm it appears in the volume chart. Submit a dispute. Confirm it appears in the dispute queue.

---

## 10. Key User Flows

### Flow 1: Class Rep Sets Up for the First Time

1. Rep lands on GlassJar.com, reads the landing page, clicks "Create your community"
2. Registers with email and password
3. Creates a community enters class name, level, department
4. Bulk-adds the class roster (200 names) via paste or CSV upload
5. Creates a collection selects type "Class Dues," sets amount, deadline, budget allocations
6. Copies the share link and posts to WhatsApp
7. Done. The system handles everything from here.

### Flow 2: Student Pays via Share Link (No Account)

1. Student opens the WhatsApp link on their phone
2. Public payment page loads shows collection name, type, progress
3. Student types their name, finds their entry in the list
4. Clicks Pay Squad checkout opens (card or bank transfer)
5. Completes payment
6. Returns to confirmation page system checks backend every 5 seconds
7. Payment confirmed via Squad webhook page shows PAID
8. Student receives email confirmation within 60 seconds
9. Course rep receives notification

### Flow 3: Bank Transfer Takes Time

1. Student initiates bank transfer in Squad checkout
2. Returns to confirmation page
3. Page shows "Still checking bank transfers can take up to 30 minutes. We will email you."
4. Student closes the page and goes about their day
5. Squad fires webhook 8 minutes later
6. Backend marks entry paid, posts ledger credit
7. Student receives email confirmation
8. If the student returns before email, they see the PAID state

### Flow 4: Payment Not Confirmed After 30 Minutes

1. Student pays, returns to page, waits 30 minutes, still not confirmed
2. Page surfaces "Having trouble? Submit a dispute."
3. Student submits dispute: name, collection, amount, reference, screenshot
4. GlassJar admin receives notification in internal dashboard
5. Admin reviews reference against Squad records within 12 hours
6. Admin confirms payment entry is manually marked paid
7. Student receives resolution email

### Flow 5: Treasurer Manages Expenses

1. Class trip cost comes in venue deposit of 150,000 naira
2. Treasurer opens Expenses, clicks "New Expense"
3. Fills in description, amount, uploads receipt photo
4. Auditor receives notification, opens expense approval screen at /expenses/{id}
5. Auditor reviews and approves
6. Treasurer marks paid out with bank transfer reference
7. Ledger debits 150,000 naira
8. Transparency report now shows the expense with receipt and payout proof

### Flow 6: Member Checks Where the Money Went

1. After collection closes, a member wants to verify funds were spent correctly
2. Rep shares the transparency report URL
3. Member opens it without logging in
4. Sees: total collected, budget breakdown, each expense with amount, description, receipt link, and payout bank reference
5. Every naira is accounted for with zero explanation from the rep required

---

## 11. Technical Architecture Decisions

### Squad API Migration

All payment work targets Squad API. Monnify code is deleted after Squad is verified. The Squad integration covers: checkout initiation, reserved account creation, webhook verification using Squad's HMAC signature format, transaction status lookup, and payment reference tracking. Squad's webhook format must be read from their documentation before any integration work starts.

### Payment Session Architecture

Payment sessions are tracked on the backend by payment reference. The frontend stores only the reference (not the full session state) in sessionStorage. On page load, the confirmation page sends the reference to the backend and receives the current state. The backend checks the database first, then Squad's API if the database shows no result. This means the session survives browser crashes, page refreshes, and tab closes.

### Payment Confirmation Loop

Backend: webhook-first. Squad sends PAID event, backend processes it atomically (marks entry, posts ledger entry, triggers email). Frontend: polls GET /public/payments/{ref} every 5 seconds for up to 30 minutes. Returns one of three states: PAID, FAILED, PROCESSING. Frontend renders the correct UI per state.

### Email Architecture

Resend is the recommended provider. Every email is a named template: payment-confirmed, payment-notification-admin, dispute-submitted, dispute-resolved, expense-approved, expense-rejected, email-verification, password-reset. Templates are stored in code, not in a dashboard, so they are versioned and reviewable.

### Frontend Architecture

React 19 with TypeScript. Component library decision (shadcn/ui vs Radix primitives vs custom on Tailwind) resolved in morning standup before Day 1 build starts. Design tokens defined in a single CSS variables file. All components live in /components/ui. All screen-level components live in /components/screens. A single api.ts client handles all requests with a unified error handler.

### Database

No schema changes unless explicitly required by a new feature. All existing tables remain. The expenses table gets a receipt_url column. A disputes table is added. No other schema changes in the 5-day sprint.

### Rate Limiting

Redis is provisioned on Render alongside the existing Postgres instance. The rate limiter uses the Redis connection string from the environment. The existing slowapi integration is updated to use the Redis backend.

---

## 12. Out of Scope Now

These will not be built in the current sprint. Raising them is not a priority conversation.

- WhatsApp or SMS notifications (email ships first)
- Native iOS or Android app
- GlassJar Pro subscription billing and enforcement
- Institution-level licensing and contracts
- Multi-currency support
- Third-party API access
- Alumni networks or non-student community types
- Advanced BI or analytics beyond the admin dashboard
- Automated payment reminder sequences
- In-app wallet or stored balances for users
- Draft collection status and publish flow (delete the dead enum value)
- KYC beyond what Squad requires for their checkout

---

## 13. Five-Day Live Ship Plan

The goal is a live, real-user-ready product in 5 days. Every morning starts with a standup where Sanni Shazily assigns tasks for the day. No task is picked up without PM assignment. Every task is on its own branch. Every branch is reviewed before merging.

### Day 1: Foundation (Design System + Dev Environment + Squad Research)

**Goal:** Every dev can run the stack locally. Design system exists. Squad integration plan is locked.

Tasks:
- Set up `.env.local` and `.env.example` templates, document in README (F-INF05)
- Create the full design system: color tokens, typography, spacing, core components (F-UX01)
- Read Squad API documentation cover to cover. Map every Monnify flow to its Squad equivalent. Write the mapping as a document in /docs (F-INF01 research)
- Decide component library (standup decision)
- Delete all Monnify-specific code from backend. Do not replace it yet just remove it so no one builds on top of it

### Day 2: Auth Fixes + Squad Checkout Integration

**Goal:** Auth works correctly. Squad checkout accepts a payment in staging.

Tasks:
- Rebuild auth error handling from first principles (F-A01, F-A02)
- Rebuild session integrity and JWT expiry redirect (F-A03)
- Integrate Squad checkout for guest payment flow (F-P01)
- Integrate Squad webhook handler and HMAC verification (F-INF01)
- Set up Redis rate limiting (F-INF04)

### Day 3: Payment Confirmation + Email + Expense Fixes

**Goal:** Payment confirmation is bulletproof. Email fires on payment. Expense approval works.

Tasks:
- Backend persistent payment session by reference (F-P02)
- Polling confirmation loop with PAID / FAILED / PROCESSING states (F-P03, F-P04)
- Integrate Resend email service (F-INF02)
- Payment confirmation email to payer (F-P05)
- Payment notification to admin (F-P06)
- Add GET /expenses/{id} endpoint (F-E02)
- Fix expense approval UI: remove client-side .find(), fix type error on approve button (F-E02)
- Add receipt file upload to expense submission (F-E04)

### Day 4: Frontend Rebuild

**Goal:** Every screen is rebuilt on the design system. Role-aware UI. Mobile responsive.

Tasks:
- Rebuild all screens on the design system (F-UX02)
- Implement role-aware UI hide all gated actions by role (F-UX03)
- Implement error states and loading states on every screen (F-UX04)
- Mobile responsiveness pass on all screens (F-UX05)
- Wire CommunityHome to single dashboard endpoint (F-C07)
- Fix ledger pagination UI (F-E05)
- Fix treasurer collection creation button (F-CL06)
- Fix treasurer payment sync permission (F-P10)

### Day 5: Collections + Communities + Roster

**Goal:** All community, roster, and collection features complete.

Tasks:
- Full community and roster feature set (F-C01 through F-C08)
- Full collection feature set (F-CL01 through F-CL06)

### Day 6: Disputes + Manual Payments + Expense Governance

**Goal:** Dispute flow live. Full expense governance chain works.

Tasks:
- Manual payment controls (F-P07, F-P08, F-P09)
- Dispute submission and resolution (F-P11, F-P12)
- Full expense governance (F-E01, F-E03)
- Public reports (F-R01, F-R02)

### Day 7: AI + Admin Dashboard + Landing Page + Deploy

**Goal:** Full product live in production.

Tasks:
- AI assistant (F-AI01, F-AI02)
- Internal admin dashboard (F-INF06)
- Real landing page (F-UX06)
- Auth email verification and password reset (F-A06, F-A07)
- Ledger CSV export (F-E06)
- Full end-to-end staging test then production deploy

---

## 13b. 7-Day Sprint Master Table by Department

Every feature from section 9 is assigned to a day and a department. The PM assigns individual devs to each row in the morning standup. One feature = one branch = one dev. Nothing is picked up outside this table without PM approval.

**Departments:** BE = Backend only, FE = Frontend only, FULL = touches both BE and FE, INFRA = infrastructure/devops, PM = PM decision required before any build starts

**Status:** PM updates this daily. Values: TODO / IN PROGRESS / IN REVIEW / DONE

---

### Day 1 — Foundation

**Goal:** Every dev can run the stack locally. Design system locked and built. Squad API fully mapped. Monnify code deleted.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-INF05 | `.env.local` + `.env.example` templates + README setup guide | INFRA | Any dev clones repo and runs full stack in under 10 minutes from scratch | TODO |
| F-UX01 | Design system: color tokens, typography, spacing, full component library | FE | Open 5 screens. Fonts, colors, spacing, and component style are identical across all of them | TODO |
| F-INF01-research | Read Squad API docs. Map every Monnify flow to Squad equivalent. Produce /docs/squad-mapping.md | BE | Document covers checkout, reserved accounts, webhooks, status lookup, and HMAC format | TODO |
| PM-001 | Decide component library: shadcn/ui vs Radix + Tailwind vs custom | PM | Decision recorded in standup notes before FE writes a single component | TODO |
| INFRA-001 | Delete all Monnify code from backend. No replacement yet. | BE | `grep -r "monnify" backend/` returns zero results | TODO |
| INFRA-002 | Provision Redis on Render alongside Postgres | INFRA | Redis connection string in env. Backend boots without error. | TODO |

---

### Day 2 — Auth + Squad Checkout + Rate Limiting

**Goal:** Auth works correctly. Squad checkout accepts a payment in staging.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-A01 | User registration with correct error handling | FULL | Register with duplicate email, confirm 409 surfaces as readable message. No fake redirect to /communities. | TODO |
| F-A02 | Login with correct error handling | FULL | Login with wrong password, confirm error shown. Confirm no local-session fallback exists in codebase. | TODO |
| F-A03 | Session integrity: expired or revoked JWT redirects to /login | FULL | Manually revoke token, make protected API call, confirm immediate redirect to /login with no ghost user | TODO |
| F-A04 | Logout: server-side revocation, localStorage clear, redirect | FULL | Log in, log out, hit back button, confirm protected page does not load | TODO |
| F-P01 | Guest payment via public share link using Squad checkout | FULL | Open share link incognito, find name, pay in Squad sandbox, confirm entry marked paid within 30 seconds | TODO |
| F-INF01 | Squad webhook handler: HMAC verification, idempotent processing, atomic commit | BE | Deliver same webhook twice, confirm ledger entry created exactly once. Tampered signature rejected with 401. | TODO |
| F-INF04 | Redis-backed rate limiting replacing in-memory slowapi | BE + INFRA | Send 100 requests alternating across two server instances. Confirm global limit applied, not per-instance. | TODO |

---

### Day 3 — Payment Confirmation + Email + Expense Rebuild

**Goal:** Payment confirmation is bulletproof regardless of browser state. Email fires on every payment. Expense approval rebuilt from first principles.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-P02 | Backend persistent payment session tracked by reference | BE | Start payment, close tab, reopen confirmation URL with same reference, confirm correct state returned by backend | TODO |
| F-P03 | Polling confirmation loop: PAID / FAILED / PROCESSING states queried from backend | FULL | Fire webhook 5 minutes after checkout. Confirm polling page transitions to PAID state when webhook arrives. | TODO |
| F-P04 | "Still processing" UI state for bank transfers with time expectation | FE | Load confirmation page for unconfirmed bank transfer. Confirm STILL PROCESSING state shows with spinner and message. | TODO |
| F-INF02 | Integrate Resend email service with named templates stored in code | BE + INFRA | Send test email via Resend SDK. Confirm delivery within 60 seconds. Template is a versioned file in /templates. | TODO |
| F-P05 | Payment confirmation email to payer within 60 seconds of webhook | BE | Complete payment with email address provided. Confirm email received within 60 seconds with correct details. | TODO |
| F-P06 | Payment notification email to admin and course rep on every payment | BE | Complete payment, log in as admin, confirm notification in inbox within 60 seconds | TODO |
| F-E02 | Add GET /expenses/{id} backend endpoint + rebuild expense approval UI without .find() hack | FULL | Navigate to /expenses/{id} with no query string. Page loads correctly. Approve expense. Confirm status updates. | TODO |
| F-E04 | Expense receipt file upload (image or PDF) to cloud storage with URL on expense record | FULL | Upload JPG with expense. Confirm URL stored. Open transparency report. Confirm receipt link present. | TODO |
| F-P10 | Grant treasurer permission to POST /payments/{id}/sync | BE | Log in as treasurer, trigger payment sync, confirm no 403 error | TODO |

---

### Day 4 — Full Frontend Rebuild

**Goal:** Every screen rebuilt on the design system. Role-aware. Mobile responsive. Dashboard wired.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-UX02 | Rebuild all 17 screens: Landing, Register, Login, Communities, Community Home, Members, Collections, Collection Detail, Expenses, Expense Approval, Ledger, Assistant, Public Pay, Payment Return, Transparency Report, Create Community, Create Expense | FE | Open every route. No ad-hoc styles, broken layouts, or placeholder colors anywhere. | TODO |
| F-UX03 | Role-aware UI: hide all gated actions based on role (collection create, expense FAB, approval buttons) | FE | Log in as each of the 4 roles. Confirm no button visible that would 403 on submission. | TODO |
| F-UX04 | Error states and loading states on every screen | FE | Disconnect network mid-session. Navigate to any data screen. Confirm clear error state with retry button appears. | TODO |
| F-UX05 | Mobile-first responsive design on all screens | FE | Open every screen at 375px. No horizontal scroll. All touch targets at least 44px. | TODO |
| F-C07 | Wire CommunityHome to GET /communities/{id}/dashboard single endpoint | FE | Load community home. Confirm only one network request. Treasury balance, active collections, pending expenses shown. | TODO |
| F-E05 | Ledger pagination UI wired to backend skip/limit params | FE | Create 25 ledger entries. Navigate past page 1. Confirm running balance is correct on every entry. | TODO |
| F-CL06 | Show "New Collection" button for treasurer role in collections UI | FE | Log in as treasurer. Confirm "New Collection" button visible. Create collection. Confirm success. | TODO |
| F-A05-ui | Role assignment UI: admin can assign any role from member detail screen | FE | Assign treasurer to member. Confirm member sees treasurer-gated buttons on next page load. | TODO |

---

### Day 5 — Communities, Roster, and Collections

**Goal:** All community, roster, and collection features built and acceptance-tested.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-C01 | Create community end to end | FULL | Create community. Confirm creator is admin. Confirm unique invite code generated and shown. | TODO |
| F-C02 | Bulk add members by name via paste or CSV (no account required) | FULL | Add 10 names. Confirm all 10 appear as unclaimed roster entries. Confirm no registration required. | TODO |
| F-C03 | Add single member to roster | FULL | Add one member. Confirm on roster. Confirm enrollable into any active collection. | TODO |
| F-C04 | Join via invite code and claim roster entry | FULL | Create unclaimed entry. Register matching user. Join with code. Confirm account linked to entry. Payment history visible. | TODO |
| F-C05 | Role management with sole-admin demotion block | FULL | Assign treasurer to member. Confirm permissions. Try to demote only admin. Confirm system blocks it. | TODO |
| F-C06 | Remove member blocked if payment history exists | FULL | Try to remove member with a paid entry. Confirm blocked with explanation. Remove member with no history. Confirm success. | TODO |
| F-C08 | Reserved account setup via Squad | FULL | Set up reserved account in Squad sandbox. Confirm account number displayed and copyable. Simulate transfer. Confirm ledger credit. | TODO |
| F-CL01 | Create collection with type, budget allocation, deadline | FULL | Create "social event" collection. Confirm share link works. Confirm budget not summing to 100% is rejected. | TODO |
| F-CL02 | Collection list with role-filtered view | FULL | Member sees only enrolled active collections. Admin sees all collections including closed. | TODO |
| F-CL03 | Collection detail with progress bar and per-member status | FULL | Open collection with 3 paid, 2 unpaid, 1 waived. Confirm progress bar and each member status are correct. | TODO |
| F-CL04 | Close collection | FULL | Close collection. Attempt payment via public link. Confirm rejected with "collection closed" message. | TODO |
| F-CL05 | Sync new members into active collection | FULL | Create collection with 10 members. Add 2 to roster. Sync. Confirm collection now has 12 entries. | TODO |

---

### Day 6 — Disputes, Manual Payments, and Expense Governance

**Goal:** Dispute flow live end to end. Manual payment controls complete. Full expense governance chain tested.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-P07 | Manual mark paid (cash or transfer) with audit trail | FULL | Manually mark member paid. Confirm ledger credit with note. Confirm audit log shows actor and timestamp. | TODO |
| F-P08 | Waive payment with mandatory reason | FULL | Waive member. Confirm "Waived" badge. Attempt waive without reason. Confirm system blocks it. | TODO |
| F-P09 | Revert manual mark or waive (balancing debit, never delete) | FULL | Mark paid. Revert. Confirm ledger has original credit and balancing debit. Member shows unpaid. | TODO |
| F-P11 | Dispute submission: name, collection, amount, method, reference, optional screenshot | FULL | Submit dispute with all required fields. Confirm stored in DB. Reference number shown to submitter. | TODO |
| F-P12 | Dispute resolution in internal admin dashboard with email notification | FULL | Open admin dashboard, resolve dispute as confirmed. Confirm member entry marked paid. Confirm submitter receives email. | TODO |
| F-E01 | Expense submission with category, description, amount, receipt | FULL | Submit expense with receipt. Confirm "Pending Approval" status. Confirm auditor sees it in their queue. | TODO |
| F-E03 | Mark expense paid out with bank reference, posts ledger debit | FULL | Approve expense, mark paid out with reference. Confirm ledger debit. Confirm transparency report shows payout ref. | TODO |
| F-R01 | Public transparency report: collected vs target, budget breakdown, expenses with receipts and payout refs | FULL | Open in incognito. Loads without auth. Amounts match ledger. Receipts linked. Payout refs visible. | TODO |
| F-R02 | Public collection progress: live stats visible to anyone with link | FE | Open public pay link. Confirm progress stats (collected, target, member count) are visible and current. | TODO |

---

### Day 7 — AI Assistant + Admin Dashboard + Landing Page + Deploy

**Goal:** Full product live in production. Every feature acceptance-tested in staging before deploy.

| Feature ID | Feature Name | Dept | Acceptance Test | Status |
|------------|-------------|------|----------------|--------|
| F-AI01 | Ledger-grounded AI assistant: answers from real community data only, no hallucination | FULL | Ask "How much collected?" Confirm answer matches ledger SUM exactly. Ask about nonexistent payment. Confirm denial. | TODO |
| F-AI02 | 6 starter prompts in assistant UI | FE | Open assistant. Confirm 6 prompts visible. Click each. Confirm accurate data-driven responses. | TODO |
| F-INF06 | Internal GlassJar admin dashboard: communities, volume, disputes, signups, error rates | FULL | Log in as GlassJar admin. Create payment in staging. Confirm in volume chart. Submit dispute. Confirm in queue. | TODO |
| F-UX06 | Real landing page: live stats, three use cases (dues, events, fundraisers), CTA, no placeholder text | FE | Show to unfamiliar person. They describe the product in 10 seconds. No hardcoded stats visible in production. | TODO |
| F-A06 | Email verification on registration | FULL | Register, skip email verification, try to create community. Confirm blocked with verification prompt. | TODO |
| F-A07 | Password reset via email with 30-minute link | FULL | Request reset, use link, set new password. Confirm old password no longer works. | TODO |
| F-E06 | Ledger export as CSV | FULL | Export ledger. Open CSV. Confirm all entries present with correct running balance column. | TODO |
| DEPLOY-001 | Full end-to-end staging test script | PM + ALL | Every step passes: create community, add roster, create collection, guest pays, webhook confirms, expense submitted, auditor approves, treasurer marks paid, transparency report correct, dispute submitted and resolved | TODO |
| DEPLOY-002 | Production deploy | INFRA | App loads at production URL. Guest payment completes in production. Email fires in production. | TODO |

---

### Sprint Summary by Department

| Department | Features Owned | Primary Days |
|-----------|---------------|-------------|
| Backend (BE) | Auth, Squad integration, webhooks, email service, payment sessions, expense endpoints, AI assistant backend, admin dashboard backend | Days 2, 3, 5, 6, 7 |
| Frontend (FE) | Design system, all 17 screens, role-aware UI, mobile responsiveness, UI states, ledger pagination, assistant UI, landing page | Days 1, 4, 7 |
| Full Stack (FULL) | Every feature that requires both an API and a UI: payments, communities, collections, expenses, disputes, transparency, roster | Days 2, 3, 5, 6, 7 |
| Infrastructure (INFRA) | Redis, Render config, env templates, email provider, production deploy | Days 1, 2, 7 |
| PM | Component library decision, daily standup, task assignment, staging test sign-off | Every day |

### Feature Count by Day

| Day | Theme | Feature Count |
|-----|-------|--------------|
| 1 | Foundation | 6 |
| 2 | Auth + Squad + Rate Limiting | 7 |
| 3 | Payment Confirmation + Email + Expenses | 9 |
| 4 | Full Frontend Rebuild | 8 |
| 5 | Communities + Roster + Collections | 12 |
| 6 | Disputes + Manual Payments + Governance | 9 |
| 7 | AI + Admin + Landing + Deploy | 9 |
| **Total** | | **60** |

These rules are in effect from the first line of code written under this PRD.

1. One task, one branch, one developer. Branch names follow the pattern: `feature/F-P01-squad-checkout`, `fix/F-A01-auth-error-handling`.

2. No push to `main` directly. Every change goes through a pull request with at least one reviewer.

3. All tasks come from this PRD and are assigned by the PM in the morning standup. If you discover something that needs doing and it is not in this document, open an issue and wait for PM to prioritize it. Do not pick it up unilaterally.

4. A task is not done until its acceptance test passes and has been verified by the PM or a designated reviewer.

5. Breaking changes (DB schema changes, API contract changes, shared model changes) are announced in the team group before the PR is opened. No one merges a breaking change without confirmation from everyone affected.

6. Build from first principles. The existing hackathon code is reference material, not a foundation to patch. If you are assigned a feature that has a broken version in the codebase, read the existing code to understand intent, then build the correct version without hacking on top of the wrong one.

7. Morning standup is mandatory. This is where the PM assigns the day's tasks, unblocks anyone who is stuck, and makes priority calls. Build only starts after standup.

---

*GlassJar is the financial operating system for student communities.*
*Built by Automo-ASK.*
