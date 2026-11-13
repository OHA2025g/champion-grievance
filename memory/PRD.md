# Champion Electricals - Enterprise Grievance, Complaint & Support Ticket Management Platform (PRD)

## Original problem statement (user's words, condensed only where marked)
"Build a complete, database-driven, production-ready Champion Electricals Enterprise Grievance, Complaint & Support Ticket Management Platform" from the uploaded `Champion_Electricals_All_Roles_UI_Screens.zip` (161 screens CE-001..CE-161) and `Champion_Electricals_21_Role_Workflow_Infographics.pdf` (21 role workflows).
- "Do not create a static UI prototype, clickable mockup, or demonstration-only website."
- "Implement all 21 roles defined in the attachments." "Do not merge distinct business roles merely to simplify development."
- "Do not reduce the application to a single linear status progression."
- "Do not invent binding company policies or warranty commitments."
- "Do not execute refunds or financial transfers through mock actions presented as real transactions."
- "Do not pretend a real SMS, email or WhatsApp message has been sent when it has not."
- "Use the exact uploaded UI screens as the visual design baseline."
- "All 161 screens are accounted for and implemented." "All 21 PDF workflows have corresponding executable workflow implementations."
- "Develope complete portal in 1 go"

## User choices
- Sign-in: email/password (JWT) with seeded demo accounts for all 21 roles + dev-only role switcher; Emergent-managed Google social login.
- Optional AI layer: Mistral model (key to be provided through the secure secrets card).
- Evidence storage: "Local server disk" requested -> implemented in MongoDB GridFS (pod-local disk is not persistent on deployment).
- Notifications: real email via Resend now (Emergent-managed), SMS/WhatsApp mocked and clearly labelled, in-app notifications.
- Delivery: all 161 screens and 21 workflows for all 21 roles in one go.
- Owner/admin account uses the signed-in user's real email.

## Architecture
See `/app/docs/ARCHITECTURE.md` (module map, collections, placeholder register). Generated docs: `/app/docs/SCREEN_COVERAGE.md`, `ROLE_PERMISSION_MATRIX.md`, `WORKFLOWS.md`, `API_ENDPOINTS.md` (`python backend/scripts/gen_docs.py`).
- FastAPI + Motor (MongoDB) backend, all routes `/api`; React SPA (Tailwind, shadcn, recharts).
- Declarative workflow engine (26 record types) with RBAC scope matrix, optimistic concurrency, idempotency keys, authority-matrix approvals with segregation of duties, linked work blocking closure, business-calendar SLA clocks with breach escalation, audit log.

## Implemented (2026-10-23)
- 21 roles, 28 demo users + owner admin; JWT cookie auth (active role in token), refresh, lockout, role switch, DEV role switcher, customer OTP, staff recovery, Google session exchange (provisioned users only), preferences.
- All 161 screens mapped to renderers (dashboards, lists, create forms, work queue + record detail with server-permitted actions, uploads, kanban, calendar, SLA board, technician mobile PWA with offline drafts, customer search, orders, roster, capacity, network, stock/count, movements, knowledge + AI Q&A, analytics x3, governed exports, admin users/invite/permissions/models/config/integrations/events/retention/audit, quarantine, forbidden, integration status, component reference).
- Workflows: case (complaint, ticket, service request, dealer, stock claim, bulk), contact, task, job, unit, technical review, approval, warranty, requisition, return, replacement, settlement (SIMULATED provider), incident, CAPA, channel dispute, appeal, correspondence, escalation, management action, supplier dispute, HR grievance (restricted collection), audit, audit finding, config change (two-admin release + stale-rollback guard), policy, legal hold.
- Evidence upload to GridFS with type/size checks, EICAR + magic-byte scan, quarantine and replacement request.
- Notifications: in-app; Emergent Resend email LIVE (demo domain suppressed); SMS/WhatsApp MOCKED dev adapters.
- Mistral AI assist (summary, sentiment, priority, routing, draft reply, root cause, trend, knowledge Q&A) - NOT CONFIGURED until MISTRAL_API_KEY is added; workflows unaffected.
- Testing: iteration 1 (69 backend tests + broad UI), iteration 2 (13 regression tests + config release, reconcile, customer confirm/reject/reopen/appeal, 21-role smoke) all passing; follow-up fixes applied (rollback guard, approval payload shown, appeal button hidden while appeal open, template defaults baseline, navigate to CFG record).
- Demo data reset tool: `python backend/scripts/reset_demo.py` (DEV only).

## Backlog
### P0
- Add MISTRAL_API_KEY via secrets card to enable AI assistance.
- Confirm Champion policies replacing PLACEHOLDER values (SLA targets, authority limits, warranty terms, holidays, retention).
### P1
- Real SMS / WhatsApp providers; real payment provider; AV engine for evidence scanning.
- Shadcn calendar date pickers in dynamic forms; human-readable labels for approval types.
- Split engine.py by domain (maintainability).
### P2
- ERP/CRM/carrier tracking integrations; TTL index on idempotency keys; PWA install manifest/service worker for technicians.

## Production note
Set `DEV_MODE=false` before going live (disables role switcher, on-screen OTP/recovery codes, SLA time simulation).
