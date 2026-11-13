import os
import secrets
from datetime import timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core import db, now, iso, parse_dt, new_id, fail, audit, get_config, DEV_MODE, public_user
from auth import role_required, hash_password, staff_user
from rbac import ROLES, role_matrix, STAFF
from workflows import WF, TERMINAL
import notify
import sla
import ai
import engine

router = APIRouter(prefix="/api/admin")
admin = role_required("R18")


@router.get("/users")
async def users(user=Depends(admin)):
    items = await db.users.find({}, {"_id": 0, "password_hash": 0}).sort("name", 1).to_list(500)
    return {"items": items}


class InviteIn(BaseModel):
    name: str
    email: str
    role: str
    org_id: str | None = None
    region: str | None = None
    confidentiality: str = "standard"
    effective_from: str | None = None
    approval_reference: str


@router.post("/users")
async def invite(body: InviteIn, user=Depends(admin)):
    if body.role not in ROLES:
        fail(422, "Please correct the highlighted fields.", fields={"role": "Unknown role"})
    if len(body.approval_reference.strip()) < 4:
        fail(422, "Please correct the highlighted fields.", fields={"approval_reference": "Access approval reference required"})
    email = body.email.strip().lower()
    if await db.users.find_one({"email": email}):
        fail(409, "A user with this email already exists.")
    org = await db.orgs.find_one({"id": body.org_id}, {"_id": 0}) if body.org_id else None
    doc = {"id": new_id("usr"), "email": email, "name": body.name, "roles": [body.role], "active_role": body.role, "org_id": org and org["id"], "org_name": org and org["name"],
           "centre_id": org["id"] if org and org["kind"] == "service_centre" else None, "centre_name": org["name"] if org and org["kind"] == "service_centre" else None,
           "regions": [body.region] if body.region else [], "skills": [], "status": "active", "demo": False, "confidentiality": "hr" if body.role == "R19" else body.confidentiality,
           "password_hash": hash_password(secrets.token_urlsafe(24) + "Aa1"), "invited_by": user["id"], "approval_reference": body.approval_reference, "created_at": iso()}
    await db.users.insert_one(dict(doc))
    state = await notify.send_plain_email(email, "You have been invited to Champion Service Desk",
                                          f"An administrator has provisioned your {ROLES[body.role][0]} access. Use 'Recover staff access' on the sign-in page to set your password, or sign in with Google using this email.")
    await audit(user, "user_invited", "user", doc["id"], {"email": email, "role": body.role, "approval_reference": body.approval_reference, "email_delivery": state})
    return {**public_user(doc), "invitation_delivery": state}


class UserPatch(BaseModel):
    status: str | None = None
    roles: list[str] | None = None
    regions: list[str] | None = None
    approval_reference: str


@router.patch("/users/{uid}")
async def patch_user(uid: str, body: UserPatch, user=Depends(admin)):
    if uid == user["id"] and (body.roles is not None or body.status == "disabled"):
        fail(403, "Administrators cannot change their own roles or disable their own account (segregation of duties).", code="forbidden")
    target = await db.users.find_one({"id": uid}, {"_id": 0})
    if not target:
        fail(404, "User not found")
    upd = {}
    if body.status in ("active", "disabled"):
        upd["status"] = body.status
    if body.roles is not None:
        if not body.roles or any(r not in ROLES for r in body.roles):
            fail(422, "Invalid roles")
        upd.update({"roles": body.roles, "active_role": body.roles[0] if target["active_role"] not in body.roles else target["active_role"],
                    "confidentiality": "hr" if "R19" in body.roles else "standard"})
    if body.regions is not None:
        upd["regions"] = body.regions
    await db.users.update_one({"id": uid}, {"$set": upd})
    await audit(user, "user_access_changed", "user", uid, {**{k: v for k, v in upd.items()}, "approval_reference": body.approval_reference}, sensitive=True)
    return {"ok": True}


@router.get("/permissions")
async def permissions(user=Depends(role_required("R18", "R21"))):
    acts = {t: [{"key": a["key"], "label": a["label"], "roles": engine.action_roles(t, a)} for a in w["actions"]] for t, w in WF.items()}
    return {"roles": role_matrix(), "actions": acts, "types": {t: w["label"] for t, w in WF.items()}}


@router.get("/config")
async def config_all(user=Depends(role_required("R18", "R21"))):
    items = await db.config.find({}, {"_id": 0}).to_list(100)
    return {"items": items, "defaults": {"templates": notify.TEMPLATES}}


@router.get("/config/{key}/versions")
async def config_versions(key: str, user=Depends(role_required("R18", "R21"))):
    return {"items": await db.config_versions.find({"key": key}, {"_id": 0}).sort("version", -1).to_list(50)}


@router.get("/integrations")
async def integrations(user=Depends(admin)):
    async def stats(q):
        last = await db.communications.find_one(q, {"_id": 0, "at": 1}, sort=[("at", -1)])
        return (last or {}).get("at"), await db.communications.count_documents({**q, "state": "failed"}), await db.communications.count_documents({**q, "state": "queued"})
    e_last, e_fail, e_q = await stats({"channel": "email"})
    s_last, _, _ = await stats({"channel": "sms"})
    w_last, _, _ = await stats({"channel": "whatsapp"})
    ai_fail = await db.integration_events.count_documents({"adapter": "Mistral AI", "state": "failed"})
    pay_last = await db.payment_instructions.find_one({}, {"_id": 0, "at": 1}, sort=[("at", -1)])
    email_ok = bool(notify.EMAIL_KEY and notify.EMAIL_FROM_NAME)
    rows = [
        {"adapter": "Email (Emergent managed Resend)", "mode": "LIVE" if email_ok else "NOT CONFIGURED", "last_sync": e_last, "queue_lag": e_q, "failures": e_fail, "owner": "System administrator",
         "health": "Healthy" if email_ok and not e_fail else "Degraded" if email_ok else "Unconfigured", "note": "Demo (.test) recipients are suppressed, never sent"},
        {"adapter": "SMS", "mode": "DEV ADAPTER (MOCKED)", "last_sync": s_last, "queue_lag": 0, "failures": 0, "owner": "System administrator", "health": "Unconfigured", "note": "No SMS provider credentials - messages recorded, not sent"},
        {"adapter": "WhatsApp Business", "mode": "DEV ADAPTER (MOCKED)", "last_sync": w_last, "queue_lag": 0, "failures": 0, "owner": "System administrator", "health": "Unconfigured", "note": "No WhatsApp Business credentials - messages recorded, not sent"},
        {"adapter": "Payment provider", "mode": "SIMULATED", "last_sync": (pay_last or {}).get("at"), "queue_lag": 0, "failures": 0, "owner": "Finance", "health": "Simulated", "note": "No real funds move"},
        {"adapter": "Mistral AI assistance", "mode": "LIVE" if ai.configured() else "NOT CONFIGURED", "last_sync": None, "queue_lag": 0, "failures": ai_fail, "owner": "System administrator",
         "health": "Healthy" if ai.configured() and not ai_fail else "Degraded" if ai.configured() else "Unconfigured", "note": "Optional; workflows run without it"},
        {"adapter": "Malware scanning", "mode": "BUILT-IN SIGNATURE CHECK (DEV)", "last_sync": None, "queue_lag": 0, "failures": 0, "owner": "Security", "health": "Simulated", "note": "Integrate an AV engine for production"},
        {"adapter": "ERP / CRM / Carrier tracking", "mode": "NOT CONFIGURED", "last_sync": None, "queue_lag": 0, "failures": 0, "owner": "Pending integration contract", "health": "Unconfigured", "note": "Contracts not supplied"},
    ]
    return {"items": rows}


@router.get("/events")
async def events(user=Depends(admin)):
    return {"items": await db.integration_events.find({}, {"_id": 0}).sort("at", -1).to_list(200)}


@router.post("/events/{eid}/replay")
async def replay(eid: str, user=Depends(admin)):
    ev = await db.integration_events.find_one({"id": eid}, {"_id": 0})
    if not ev:
        fail(404, "Event not found")
    if not ev.get("comm_id"):
        fail(409, "This event type has no safe automated replay. Open a recovery task instead.", code="unsafe_replay")
    c = await db.communications.find_one({"id": ev["comm_id"]}, {"_id": 0})
    if not c or c["state"] == "sent":
        await db.integration_events.update_one({"id": eid}, {"$set": {"state": "resolved"}})
        fail(409, "Message already delivered - replay suppressed to avoid a duplicate notification.", code="duplicate")
    await notify.deliver_email(c["id"])
    c = await db.communications.find_one({"id": ev["comm_id"]}, {"_id": 0})
    if c["state"] == "sent":
        await db.integration_events.update_one({"id": eid}, {"$set": {"state": "resolved", "resolved_at": iso()}})
    await audit(user, "event_replayed", "integration_event", eid, {"result": c["state"]})
    return {"state": c["state"]}


@router.get("/retention")
async def retention(user=Depends(role_required("R18", "R21"))):
    sched = await get_config("retention_schedules", {}) or {}
    holds = await db.records.find({"type": "legal_hold"}, {"_id": 0, "sla": 0}).to_list(100)
    held = {h["data"].get("record_ref") for h in holds if h["state"] == "active"}
    rows = []
    for cls, s in sched.items():
        if cls.startswith("_"):
            continue
        cutoff = iso(now() - timedelta(days=int(s["days"])))
        types = s.get("types", [])
        n = await db.records.count_documents({"type": {"$in": types}, "closed_at": {"$lt": cutoff}, "ref": {"$nin": list(held)}}) if types else 0
        rows.append({"class": cls, "schedule": f"{s['days']} days after closure", "hold_status": "Holds active" if any(h["data"].get("record_class") == cls for h in holds if h["state"] == "active") else "None",
                     "eligible": n, "owner": s.get("owner"), "next_run": "Manual review (automatic deletion disabled)"})
    return {"items": rows, "holds": holds, "note": sched.get("_note")}


@router.get("/audit")
async def audit_logs(actor: str = "", action: str = "", page: int = 1, user=Depends(role_required("R18", "R21"))):
    q = {}
    if actor:
        q["actor"] = {"$regex": actor, "$options": "i"}
    if action:
        q["action"] = {"$regex": action, "$options": "i"}
    items = await db.audit_logs.find(q, {"_id": 0}).sort("at", -1).skip((page - 1) * 50).limit(50).to_list(50)
    await audit(user, "audit_log_viewed", "audit_logs", "", {"filter": q})
    return {"items": items, "total": await db.audit_logs.count_documents(q)}


@router.post("/sla/run")
async def sla_run(user=Depends(role_required("R18", "R09", "R10"))):
    await sla.tick()
    return {"ok": True, "at": iso()}


class AgeIn(BaseModel):
    record_id: str
    minutes: int


dev = APIRouter(prefix="/api/dev")


@dev.post("/sla/age")
async def sla_age(body: AgeIn, user=Depends(staff_user)):
    if not DEV_MODE:
        fail(404, "Not available")
    rec = await engine.find(body.record_id)
    if not rec:
        fail(404, "Record not found")
    await sla.age(rec["id"], body.minutes)
    await audit(user, "dev_sla_time_simulation", rec["type"], rec["id"], {"minutes": body.minutes})
    await sla.tick()
    fresh = await engine.find(rec["id"])
    return {"sla": fresh.get("sla"), "sla_state": fresh.get("sla_state")}
