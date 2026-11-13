# Champion Service Desk - Architecture, data model and decision register

## Stack
- React 19 SPA (CRA + Tailwind + shadcn/ui, recharts) in `frontend/`.
- FastAPI (async, Motor) in `backend/`, every route under `/api`.
- MongoDB (collections below), evidence binaries in GridFS bucket `evidence_files`.
- Supervisor-managed services; background SLA evaluator loop runs every 60 s inside the API process.

## Backend module map
| Module | Responsibility |
|---|---|
| `core.py` | Mongo client, ids/refs (`CE-2026-00001`), audit log writer, versioned config store |
| `auth.py` | Password login (bcrypt, lockout after 5 failures), JWT httpOnly cookies (active role carried in token), refresh, role switch, DEV role switcher, customer OTP, staff recovery, Emergent Google session exchange (provisioned users only), preferences |
| `rbac.py` | 21 roles, record-type x role scope matrix, object-level scope queries, optional module flags (HR/Supplier/Audit) |
| `workflows.py` | Declarative workflow definitions for 26 record types: states, create forms, actions (from/to, roles, accountable party, evidence requirement, SLA start/meet, customer visibility) |
| `engine.py` | Record creation, validation, action execution with optimistic concurrency + idempotency keys, linked work (jobs, tasks, approvals, settlements, warranty, incidents, appeals), authority-matrix approvals with segregation of duties, closure dependency checks, SLA breach escalation |
| `sla.py` | Business-calendar SLA clocks per milestone, pause/resume, warnings, breaches |
| `notify.py` | In-app notifications; Emergent-managed Resend email (LIVE); SMS/WhatsApp DEV adapters (MOCKED, recorded as not sent); dedupe keys; demo-domain suppression |
| `payments.py` | SIMULATED payment provider (no real funds) with pending/unknown outcomes |
| `ai.py` | Optional Mistral assistance (summary, sentiment, priority, routing, draft reply, root cause, trend, knowledge Q&A from approved articles); suggestions logged, human acceptance audited; HR excluded |
| `routes_records.py` | Generic records API: list (scoped), detail (events, evidence, children, comms, dependencies), create, actions, evidence upload/scan/download, duplicates |
| `routes_ops.py` | Meta/screen registry, dashboards, analytics, lookups, customers, orders, stock, roster, capacity, network, appointments, SLA board, notifications, inbox, knowledge, exports |
| `routes_admin.py` | Users/invitations, permission matrix, config + versions, integrations health, failed events replay, retention & legal holds, audit log, DEV SLA time simulation |
| `screens.py` | Maps each of the 161 reference screens to a renderer, record type, stage filter and focus actions |
| `seed.py` | Idempotent seed: owner admin, 28 demo users across 21 roles, master data, end-to-end demo scenarios |
| `scripts/reset_demo.py` | DEV-only wipe and reseed of demo data |
| `scripts/gen_docs.py` | Regenerates docs in `/app/docs` |

## Frontend structure
- `screens/ScreenHost.jsx` renders `/app/s/:screenId[/:recordId]` by renderer kind and blocks screens of other roles (CE-142).
- Generic renderers: dashboard, list, create, record work queue + detail, upload, kanban, calendar, SLA board; mobile technician PWA screens; specialised admin/ops/analytics screens.
- `components/RecordDetail.jsx` shows state, next action, accountable party, SLA, permitted actions (from the server), tabs for overview, activity, evidence, related work, communications, SLA.

## MongoDB collections
users, orgs, customers, product_models, products, orders, parts, warehouses, stock, movements, records (all workflow records: case, contact, task, job, unit, tech_review, approval, warranty, requisition, return, replacement, settlement, incident, capa, channel_dispute, appeal, correspondence, escalation, mgmt_action, supplier_dispute, audit, audit_finding, config_change, policy, legal_hold), hr_records (restricted HR grievances), events, hr_events, evidence + GridFS evidence_files, communications, notifications, approvals (inside records), payment_instructions, integration_events, idempotency, config, config_versions, audit_logs, knowledge, exports, ai_logs, otp_codes, reset_tokens, login_attempts, user_sessions, counters, meta.

Every workflow record holds: id, ref, type, subtype, title, state, version, parent_id/root_id (linked work tree), owner/assignee/technician/reviewer ids, region/org/centre scope fields, data (intake + each recorded step), sla (clocks), demo flag, timestamps.

## Decision and placeholder register (needs Champion confirmation)
| Item | Current value | Status |
|---|---|---|
| SLA targets per priority and milestone | Defaults in `sla.py` / config `sla_policies` | PLACEHOLDER |
| Business calendar and holidays | Mon-Sat 09:00-18:00 IST, 2 placeholder holidays | PLACEHOLDER |
| Approval authority limits | config `authority_matrix` (e.g. R08 repair plan to INR 5,000, R09 refund to INR 15,000) | PLACEHOLDER |
| Warranty terms and exclusions | 2 demo warranty-term policies, exclusions marked PLACEHOLDER | PLACEHOLDER |
| Reopen window | 30 days | PLACEHOLDER |
| Retention periods | Cases 7 y, settlements 8 y, safety 10 y; automatic deletion disabled | PLACEHOLDER |
| Technician capacity | 6 open jobs | PLACEHOLDER |
| Knowledge articles | 6 demo procedures, labelled "not an approved Champion procedure" | DEMO CONTENT |
| SMS / WhatsApp providers | Not configured - DEV adapters, nothing sent | MOCKED |
| Payment provider | Simulated, no funds move | SIMULATED |
| Malware scanning | Built-in EICAR + magic-byte check | DEV SCANNER |
| ERP / CRM / carrier tracking | No contracts supplied | NOT CONFIGURED |
| Mistral AI | Needs MISTRAL_API_KEY | NOT CONFIGURED until key added |

## Setup and operations
- Environment (backend/.env): MONGO_URL, DB_NAME, JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD, DEV_MODE, EMERGENT_EMAIL_KEY, EMAIL_FROM_NAME, MISTRAL_MODEL, optional MISTRAL_API_KEY.
- Set `DEV_MODE=false` in production: disables the dev role switcher, OTP/recovery code display and SLA time simulation.
- Seeding runs at startup and is idempotent; the owner admin password is re-synced from ADMIN_PASSWORD.
- Indexes are created at startup (`server.py`).
- Regenerate docs: `python backend/scripts/gen_docs.py`.
