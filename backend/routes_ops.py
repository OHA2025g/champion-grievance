import csv
import io
import re
from datetime import timedelta
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel
from core import db, now, iso, parse_dt, new_id, fail, audit, DEV_MODE, public_user
from auth import get_current_user, staff_user, role_required
from rbac import ROLES, scope_query, flags, EXTERNAL, ACCESS
from workflows import TERMINAL, meta as wf_meta
from routes_records import build_query
import engine
import screens

router = APIRouter(prefix="/api")


@router.get("/meta")
async def meta(user=Depends(get_current_user)):
    f = await flags()
    roles = {k: {"name": v[0], "workspace": v[1], "scope": v[2], "home": v[3]} for k, v in ROLES.items()}
    return {"user": public_user(user), "roles": roles, "screens": screens.registry(), "workflows": wf_meta(), "flags": f,
            "dev_mode": DEV_MODE, "dev_switcher": DEV_MODE and f.get("dev_role_switcher", True)}


@router.get("/public/config")
async def public_config():
    f = await flags()
    return {"dev_mode": DEV_MODE, "dev_switcher": DEV_MODE and f.get("dev_role_switcher", True), "roles": {k: v[0] for k, v in ROLES.items()}}


# KPI definitions per role: (label, type, state, filter, sub-label)
DASH = {
    "R01": ("case", [("Open complaints", "case", "open", None, "Active service requests"), ("Action needed", "case", "evidence_requested,resolved", None, "Awaiting your response"),
                     ("Visits proposed", "job", "appointment_proposed", None, "Confirm your visit window"), ("Closed", "case", "closed", None, "Completed requests")]),
    "R02": ("case", [("Open customer cases", "case", "open", {"subtype": ["dealer_customer_case"]}, "Registered by your dealership"), ("Open stock claims", "case", "open", {"subtype": ["stock_claim"]}, "Damaged stock"),
                     ("Information requested", "case", "evidence_requested", None, "Evidence needed"), ("Settlements in progress", "settlement", "open", None, "Credit notes and remedies")]),
    "R03": ("case", [("Open bulk cases", "case", "open", {"subtype": ["bulk_grievance"]}, "Business grievances"), ("Units open", "unit", "open,job_created,unresolved", None, "Unit-level work"),
                     ("Units resolved", "unit", "resolved", None, "Verified at site"), ("Ready to reconcile", "case", "resolved", {"subtype": ["bulk_grievance"]}, "Commercial reconciliation")]),
    "R04": ("case", [("New contacts", "contact", "new,in_review", None, "Omnichannel inbox"), ("Safety flags", "case", "open", {"safety_flag": True}, "Requires specialist attention"),
                     ("Awaiting routing", "case", "registered,safety_escalated,reopened", None, "Register and route"), ("Quarantined evidence", None, None, None, "Security scan holds")]),
    "R05": ("case", [("My open cases", "case", "open", {"owner_id": "$me"}, "Accountable ownership"), ("Awaiting my acceptance", "case", "awaiting_owner,reopened", {"proposed_owner_id": "$me"}, "Handoffs"),
                     ("Waiting / blocked", "case", "waiting", None, "Approved waiting periods"), ("Resolved - verify", "case", "resolved", None, "Outcome verification")]),
    "R06": ("job", [("Jobs today", "job", "open", None, "Assigned to you"), ("Completed", "job", "accepted,completed", None, "Reports submitted"),
                    ("Parts pending", "job", "awaiting_parts", None, "Waiting for delivery"), ("Needs correction", "job", "returned", None, "Returned by centre")]),
    "R07": ("job", [("Awaiting allocation", "job", "created,missed", None, "Allocate engineers"), ("Ready for dispatch", "job", "appointment_confirmed", None, "Confirm readiness"),
                    ("Reports to review", "job", "completed", None, "Completion evidence"), ("In the field", "job", "dispatched,on_site,diagnosed,repaired,tested", None, "Live visits")]),
    "R08": ("tech_review", [("Reviews pending", "tech_review", "pending,recommended", None, "Diagnosis review"), ("Further inspection", "tech_review", "further_inspection", None, "Awaiting technician"),
                            ("Approvals for me", "approval", "pending", {"required_role": "R08"}, "Within delegated authority"), ("Referred", "tech_review", "referred", None, "Higher authority")]),
    "R09": ("case", [("Regional open cases", "case", "open", None, "Your region"), ("SLA breached", "case", "open", {"sla_state": "breached"}, "Requires recovery"),
                     ("Open escalations", "escalation", "open", None, "Recovery actions"), ("Approvals for me", "approval", "pending", {"required_role": "R09"}, "Delegated decisions")]),
    "R10": ("escalation", [("National open cases", "case", "open", None, "All regions"), ("Major escalations", "escalation", "referred_national,authorised", None, "National coordination"),
                           ("Open safety incidents", "incident", "open", None, "Quality and safety"), ("Approvals for me", "approval", "pending", {"required_role": "R10"}, "Above regional authority")]),
    "R11": ("warranty", [("Claims to assess", "warranty", "submitted", None, "Evidence check"), ("Clarification requested", "warranty", "clarification_requested", None, "Awaiting information"),
                         ("Decision due", "warranty", "diagnosis_review", None, "Coverage decision"), ("Exceptions pending", "warranty", "exception_approval", None, "Approval route")]),
    "R12": ("requisition", [("To validate", "requisition", "requested", None, "Approved job requests"), ("Awaiting stock", "requisition", "awaiting_stock", None, "Transfer / procure"),
                            ("In transit", "requisition", "dispatched", None, "Shipment tracking"), ("Delivery exceptions", "requisition", "delivery_exception", None, "Recovery needed")]),
    "R13": ("settlement", [("Awaiting validation", "settlement", "pending_validation", None, "Approved settlements"), ("Discrepancies", "settlement", "discrepancy,failed", None, "Investigate"),
                           ("Pending / unknown", "settlement", "pending_confirmation,outcome_unknown", None, "Provider status"), ("To reconcile", "settlement", "executed", None, "Ledger match")]),
    "R14": ("incident", [("Urgent incidents", "incident", "reported,containment", None, "Containment"), ("Investigations", "incident", "investigation,rca_complete", None, "Root cause"),
                         ("Open CAPA", "capa", "open,in_progress,ineffective", None, "Corrective actions"), ("Effectiveness checks", "incident", "effectiveness_check", None, "Verify")]),
    "R15": ("channel_dispute", [("Open disputes", "channel_dispute", "open", None, "Dealer claims and conduct"), ("Clarification pending", "channel_dispute", "clarification_requested", None, "Evidence requested"),
                                ("Referred", "channel_dispute", "referred", None, "Above authority"), ("Recovery in progress", "channel_dispute", "recovery_in_progress,follow_up", None, "Monitor")]),
    "R16": ("appeal", [("New appeals", "appeal", "registered", None, "Assign reviewer"), ("Under review", "appeal", "under_review,explanations_requested", None, "Independent review"),
                       ("Reversal approvals", "appeal", "awaiting_reversal_approval", None, "Authorisation"), ("Remedies in progress", "appeal", "remedy_in_progress", None, "Verify remedy")]),
    "R17": ("mgmt_action", [("Open cases", "case", "open", None, "Aggregated scope"), ("SLA breached", "case", "open", {"sla_state": "breached"}, "Exceptions"),
                            ("Open safety incidents", "incident", "open", None, "Quality exposure"), ("Management actions", "mgmt_action", "open", None, "Accountable actions")]),
    "R18": ("config_change", [("Active users", None, None, None, "Provisioned accounts"), ("Config changes open", "config_change", "open", None, "Controlled release"),
                              ("Failed events", None, None, None, "Integration replay"), ("Legal holds", "legal_hold", "requested,active", None, "Retention")]),
    "R19": ("hr_grievance", [("Restricted cases open", "hr_grievance", "open", None, "Assigned to you"), ("Designated referrals", "hr_grievance", "designated_referral,escalated", None, "Urgent / specialist"),
                             ("Decisions pending", "hr_grievance", "decision_pending", None, "Authorised decision"), ("Follow-ups", "hr_grievance", "implementation,follow_up", None, "Implementation")]),
    "R20": ("supplier_dispute", [("Supplier cases open", "supplier_dispute", "open", None, "Assigned suppliers"), ("Input requested", "supplier_dispute", "input_requested", None, "Team input"),
                                 ("Correction approval", "supplier_dispute", "correction_approval", None, "Approver"), ("Settled", "supplier_dispute", "settled", None, "Closed")]),
    "R21": ("audit_finding", [("Engagements in fieldwork", "audit", "fieldwork,reporting", None, "Evidence review"), ("Open findings", "audit_finding", "open,remediation", None, "Remediation"),
                              ("Awaiting retest", "audit_finding", "submitted", None, "Independent retest"), ("Closed findings", "audit_finding", "closed", None, "Verified")]),
}


async def _count(user, rtype, state, flt):
    q = await build_query(user, rtype, state, None, None, flt)
    return await engine.coll(rtype).count_documents(q)


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    role = user["active_role"]
    primary, kpis = DASH[role]
    out = []
    for label, t, st, flt, sub in kpis:
        if t is None:
            v = {"Quarantined evidence": lambda: db.evidence.count_documents({"scan_state": "quarantined"}), "Active users": lambda: db.users.count_documents({"status": "active"}),
                 "Failed events": lambda: db.integration_events.count_documents({"state": "failed"})}[label]
            out.append({"label": label, "value": await v(), "sub": sub})
        else:
            try:
                out.append({"label": label, "value": await _count(user, t, st, flt), "sub": sub, "type": t, "state": st})
            except Exception:
                out.append({"label": label, "value": "-", "sub": "Not in your scope"})
    q = await build_query(user, primary, None, None, None, None)
    coll = engine.coll(primary)
    since = iso(now() - timedelta(days=7))
    recent = await coll.find({"$and": [q, {"created_at": {"$gte": since}}]}, {"_id": 0, "created_at": 1}).to_list(5000)
    ids = [r["id"] async for r in coll.find(q, {"_id": 0, "id": 1}).limit(5000)]
    evc = db.hr_events if primary == "hr_grievance" else db.events
    done = await evc.find({"record_id": {"$in": ids}, "at": {"$gte": since}, "to": {"$in": TERMINAL[primary]}}, {"_id": 0, "at": 1}).to_list(5000)
    series = []
    for i in range(6, -1, -1):
        d = (now() - timedelta(days=i)).date().isoformat()
        series.append({"day": d[5:], "created": sum(1 for r in recent if r["created_at"][:10] == d), "completed": sum(1 for e in done if e["at"][:10] == d)})
    agg = await coll.aggregate([{"$match": q}, {"$group": {"_id": "$state", "n": {"$sum": 1}}}]).to_list(50)
    from workflows import WF
    tones = {}
    for a in agg:
        tone = WF[primary]["states"].get(a["_id"], {}).get("tone", "info")
        tones[tone] = tones.get(tone, 0) + a["n"]
    table = await coll.find({"$and": [q, {"state": {"$nin": TERMINAL[primary]}}]}, {"_id": 0, "sla": 0, "data": 0}).sort("updated_at", -1).limit(6).to_list(6)
    demo = await coll.count_documents({"$and": [q, {"demo": True}]})
    return {"kpis": out, "series": series, "distribution": tones, "table": table, "primary": primary, "demo_records": demo, "total": sum(a["n"] for a in agg)}


def _avg(xs):
    xs = [x for x in xs if x is not None]
    return round(sum(xs) / len(xs), 1) if xs else None


@router.get("/analytics")
async def analytics(frm: str = None, to: str = None, region: str = None, user=Depends(role_required("R09", "R10", "R17", "R21"))):
    base = {"created_at": {"$gte": frm or "2000", "$lte": (to or "2999") + "T23:59:59"}}
    if user["active_role"] == "R09":
        base["region"] = {"$in": user.get("regions") or []}
    if region:
        base["region"] = region
    cases = await db.records.find({**base, "type": "case"}, {"_id": 0, "data.description": 0}).to_list(20000)
    jobs = await db.records.find({**base, "type": "job"}, {"_id": 0}).to_list(20000)
    term = TERMINAL["case"]
    open_c = [c for c in cases if c["state"] not in term]
    clocks = [k for c in cases for k in c.get("sla", [])]
    met = [k for k in clocks if k["state"] == "met"]
    breached = [k for k in clocks if k.get("breached_at")]
    closed = [c for c in cases if c.get("closed_at")]
    serials = [c["data"].get("serial") for c in cases if c["data"].get("serial")]
    accepted = [j for j in jobs if j["state"] == "accepted"]
    appts = [j for j in jobs if j.get("appointment") or j.get("missed_count")]
    approvals = await db.records.find({**base, "type": "approval", "approval_type": {"$in": ["refund", "replacement", "credit_note", "goodwill"]}, "state": {"$in": ["pending", "approved"]}}, {"_id": 0, "amount": 1, "approval_type": 1, "state": 1}).to_list(5000)
    stl = await db.records.find({**base, "type": "settlement"}, {"_id": 0, "created_at": 1, "executed_at": 1, "amount": 1, "state": 1}).to_list(5000)
    warranty = await db.records.aggregate([{"$match": {**base, "type": "warranty"}}, {"$group": {"_id": {"$ifNull": ["$coverage", "Pending"]}, "n": {"$sum": 1}}}]).to_list(20)
    capa = await db.records.find({**base, "type": "capa"}, {"_id": 0, "state": 1}).to_list(5000)
    stock = await db.stock.find({}, {"_id": 0}).to_list(5000)
    by = lambda items, key: sorted([{"name": k, "value": v} for k, v in __import__("collections").Counter(key(i) for i in items).items() if k], key=lambda x: -x["value"])
    trend = []
    for i in range(13, -1, -1):
        d = (now() - timedelta(days=i)).date().isoformat()
        trend.append({"day": d[5:], "created": sum(1 for c in cases if c["created_at"][:10] == d), "closed": sum(1 for c in closed if c["closed_at"][:10] == d)})
    regions = sorted({c.get("region") for c in cases if c.get("region")})
    hr_open = await db.hr_records.count_documents({"state": {"$ne": "closed"}}) if user["active_role"] in ("R17", "R10") else None
    return {
        "operational": {"total": len(cases), "open": len(open_c), "new": sum(1 for c in cases if c["created_at"] >= iso(now() - timedelta(days=7))),
                        "resolved": sum(1 for c in cases if c["state"] == "resolved"), "closed": sum(1 for c in cases if c["state"] == "closed"),
                        "reopened": sum(1 for c in cases if c.get("reopen_count")), "overdue": sum(1 for c in open_c if c.get("sla_state") == "breached"),
                        "unassigned": sum(1 for c in open_c if not c.get("owner_id")), "escalated": await db.records.count_documents({**base, "type": "escalation", "state": {"$nin": TERMINAL["escalation"]}}),
                        "pending_approvals": await db.records.count_documents({**base, "type": "approval", "state": "pending"}), "blocked": sum(1 for c in open_c if c["state"] == "waiting")},
        "service": {"first_response_min": _avg([(parse_dt(k["met_at"]) - parse_dt(k["start"])).total_seconds() / 60 for k in met if k["m"] == "first_response"]),
                    "avg_resolution_h": _avg([(parse_dt(c["closed_at"]) - parse_dt(c["created_at"])).total_seconds() / 3600 for c in closed]),
                    "sla_compliance_pct": round(100 * len(met) / (len(met) + len(breached)), 1) if (met or breached) else None, "sla_breaches": len(breached),
                    "first_time_fix_pct": round(100 * sum(1 for j in accepted if j.get("first_time_fix")) / len(accepted), 1) if accepted else None,
                    "repeat_complaint_pct": round(100 * sum(1 for s in set(serials) if serials.count(s) > 1) / len(set(serials)), 1) if serials else None,
                    "appointment_adherence_pct": round(100 * sum(1 for j in appts if not j.get("missed_count")) / len(appts), 1) if appts else None,
                    "technician_productivity": by(accepted, lambda j: j.get("technician_name")), "centre_backlog": by([j for j in jobs if j["state"] not in TERMINAL["job"]], lambda j: j.get("centre_name"))},
        "customer": {"csat_avg": _avg([c.get("csat") for c in cases]), "reopen_rate_pct": round(100 * sum(1 for c in cases if c.get("reopen_count")) / len(closed), 1) if closed else None,
                     "feedback_count": sum(1 for c in cases if c.get("csat"))},
        "quality": {"warranty": [{"name": w["_id"], "value": w["n"]} for w in warranty], "exposure_inr": sum(float(a.get("amount") or 0) for a in approvals),
                    "exposure_by_type": by(approvals, lambda a: a["approval_type"]), "settlement_turnaround_h": _avg([(parse_dt(s["executed_at"]) - parse_dt(s["created_at"])).total_seconds() / 3600 for s in stl if s.get("executed_at")]),
                    "settled_inr": sum(float(s.get("amount") or 0) for s in stl if s.get("executed_at")),
                    "product_issues": by(cases, lambda c: c.get("product")), "safety_incidents": await db.records.count_documents({**base, "type": "incident"}),
                    "capa_progress_pct": round(100 * sum(1 for c in capa if c["state"] == "verified") / len(capa), 1) if capa else None,
                    "parts_availability_pct": round(100 * sum(1 for s in stock if s["on_hand"] - s["reserved"] > 0) / len(stock), 1) if stock else None,
                    "repeat_failures": await db.records.count_documents({**base, "type": "tech_review", "repeat_count": {"$gt": 0}})},
        "trend": trend, "by_region": [{"name": r, "open": sum(1 for c in open_c if c.get("region") == r), "breached": sum(1 for c in open_c if c.get("region") == r and c.get("sla_state") == "breached")} for r in regions],
        "hr_open_aggregate": hr_open, "demo_records": sum(1 for c in cases if c.get("demo")), "generated_at": iso(),
    }


@router.get("/lookup/{src}")
async def lookup(src: str, q: str = "", model_id: str = None, user=Depends(get_current_user)):
    kind, _, arg = src.partition(":")
    rx = {"$regex": re.escape(q), "$options": "i"} if q else None
    if kind == "users":
        roles = [r for r in ACCESS if False] or ([r for r in ROLES if r not in EXTERNAL] if arg == "staff" else arg.split("|"))
        qq = {"roles": {"$in": roles}, "status": "active"}
        if rx:
            qq["name"] = rx
        if user["active_role"] == "R07" and arg == "R06":
            qq["centre_id"] = user.get("centre_id")
        items = await db.users.find(qq, {"_id": 0, "id": 1, "name": 1, "roles": 1, "centre_name": 1, "skills": 1}).limit(30).to_list(30)
        return [{"value": u["id"], "label": u["name"], "sub": ", ".join(ROLES[r][0].split(" /")[0] for r in u["roles"] if r in roles) + (f" - {u['centre_name']}" if u.get("centre_name") else "")} for u in items]
    if kind == "customers":
        if user["active_role"] in EXTERNAL:
            fail(403, "Not permitted", code="forbidden")
        items = await db.customers.find({"$or": [{"name": rx}, {"phone": rx}]} if rx else {}, {"_id": 0}).limit(30).to_list(30)
        return [{"value": c["id"], "label": c["name"], "sub": f"{c.get('phone', '')} - {c.get('region', '')}"} for c in items]
    if kind == "models":
        items = await db.product_models.find({"state": "active", **({"model": rx} if rx else {})}, {"_id": 0}).to_list(100)
        return [{"value": m["id"], "label": f"{m['category']} / {m['model']}", "sub": m.get("skill")} for m in items]
    if kind in ("centres", "orgs"):
        qq = {"kind": "service_centre" if kind == "centres" else arg}
        if rx:
            qq["name"] = rx
        return [{"value": o["id"], "label": o["name"], "sub": o.get("region")} async for o in db.orgs.find(qq, {"_id": 0})]
    if kind == "parts":
        qq = {"compatible_models": model_id} if model_id else {}
        if rx:
            qq["$or"] = [{"name": rx}, {"sku": rx}]
        return [{"value": p["sku"], "label": f"{p['sku']} {p['name']}", "sub": f"INR {p['unit_cost']}"} async for p in db.parts.find(qq, {"_id": 0}).limit(40)]
    if kind == "warehouses":
        return [{"value": w["id"], "label": w["name"], "sub": w.get("region")} async for w in db.warehouses.find({}, {"_id": 0})]
    if kind == "orders":
        qq = {"org_id": user.get("org_id")} if user["active_role"] in EXTERNAL else {}
        return [{"value": o["id"], "label": o["ref"], "sub": f"{o['site']} - {o['units']} units"} async for o in db.orders.find(qq, {"_id": 0})]
    if kind in ("records", "policies"):
        rtype = "policy" if kind == "policies" else arg
        flt = None
        query = await build_query(user, rtype, "published" if kind == "policies" else None, arg if kind == "policies" else None, q or None, flt)
        items = await engine.coll(rtype).find(query, {"_id": 0, "id": 1, "ref": 1, "title": 1, "state": 1, "amount": 1}).sort("created_at", -1).limit(30).to_list(30)
        return [{"value": i["id"], "label": f"{i['ref']} {i.get('title', '')}", "sub": i["state"]} for i in items]
    fail(404, "Unknown lookup")


@router.get("/customers/search")
async def customer_search(q: str, user=Depends(role_required("R04", "R05"))):
    rx = {"$regex": re.escape(q.strip()), "$options": "i"}
    serial_hits = [p["customer_id"] async for p in db.products.find({"serial": rx}, {"_id": 0, "customer_id": 1})]
    custs = await db.customers.find({"$or": [{"name": rx}, {"phone": rx}, {"email": rx}, {"id": {"$in": serial_hits}}]}, {"_id": 0}).limit(20).to_list(20)
    out = []
    for c in custs:
        cs = await db.records.find({"type": "case", "customer_id": c["id"]}, {"_id": 0, "ref": 1, "id": 1, "updated_at": 1, "state": 1}).sort("updated_at", -1).to_list(50)
        prods = await db.products.find({"customer_id": c["id"]}, {"_id": 0, "serial": 1, "model": 1}).to_list(10)
        out.append({**c, "previous_cases": len(cs), "last_activity": cs[0]["updated_at"] if cs else None, "cases": cs[:5], "products": prods})
    await audit(user, "customer_search", "customer", "", {"q": q, "hits": len(out)})
    return {"items": out}


class CustomerIn(BaseModel):
    name: str
    phone: str
    email: str = ""
    address: str = ""
    pin: str


@router.post("/customers")
async def create_customer(body: CustomerIn, user=Depends(role_required("R04", "R05"))):
    if not re.match(r"^\d{6}$", body.pin) or not re.match(r"^\+?\d{10,13}$", body.phone.replace(" ", "")):
        fail(422, "Please correct the highlighted fields.", fields={"pin": "6 digit PIN" if not re.match(r"^\d{6}$", body.pin) else "", "phone": "10-13 digit phone"})
    if await db.customers.find_one({"phone": body.phone}):
        fail(409, "A customer with this phone number already exists. Search and link instead.")
    doc = {"id": new_id("cus"), **body.model_dump(), "region": engine.PIN_REGION.get(body.pin[0], "West"), "preferred_contact": "SMS", "created_at": iso(), "created_by": user["id"], "demo": False}
    await db.customers.insert_one(dict(doc))
    await audit(user, "customer_registered", "customer", doc["id"])
    return doc


@router.get("/orders")
async def orders(user=Depends(get_current_user)):
    if user["active_role"] not in ("R03", "R15", "R05", "R10"):
        fail(403, "Not permitted", code="forbidden")
    q = {"org_id": user.get("org_id")} if user["active_role"] == "R03" else {}
    out = await db.orders.find(q, {"_id": 0}).to_list(200)
    for o in out:
        o["claims"] = await db.records.count_documents({"type": "case", "data.order_ref": o["id"]})
    return {"items": out}


@router.get("/stock")
async def stock(user=Depends(role_required("R12", "R07", "R09", "R10", "R21"))):
    parts = {p["sku"]: p async for p in db.parts.find({}, {"_id": 0})}
    whs = {w["id"]: w async for w in db.warehouses.find({}, {"_id": 0})}
    rows = []
    async for s in db.stock.find({}, {"_id": 0}):
        av = s["on_hand"] - s["reserved"]
        rows.append({**s, "part": parts.get(s["sku"], {}).get("name"), "warehouse": whs.get(s["warehouse_id"], {}).get("name"), "available": av, "status": "Out of stock" if av <= 0 else "Low" if av <= 2 else "Available"})
    return {"items": rows}


@router.get("/movements")
async def movements(user=Depends(role_required("R12", "R09", "R10", "R21"))):
    return {"items": await db.movements.find({}, {"_id": 0}).sort("at", -1).to_list(200)}


class CountIn(BaseModel):
    sku: str
    warehouse_id: str
    counted: int


@router.post("/stock/reconcile")
async def reconcile(body: CountIn, user=Depends(role_required("R12"))):
    s = await db.stock.find_one({"sku": body.sku, "warehouse_id": body.warehouse_id}, {"_id": 0})
    if not s:
        fail(404, "Stock line not found")
    diff = body.counted - s["on_hand"]
    if diff == 0:
        await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "count_confirmed", "sku": body.sku, "warehouse_id": body.warehouse_id, "qty": 0, "ref": "COUNT"})
        return {"difference": 0, "approval": None}
    subj = {"id": f"stock:{body.sku}:{body.warehouse_id}", "ref": f"STOCK-{body.sku}", "type": "stock", "state": "", "data": {}}
    ap = await engine.create_approval(user, "stock_adjustment", subj, abs(diff), f"Count {body.counted} vs system {s['on_hand']}", {"sku": body.sku, "warehouse_id": body.warehouse_id, "counted": body.counted, "system": s["on_hand"]})
    return {"difference": diff, "approval": ap["ref"]}


async def _tech_rows(q):
    cap = (await engine.get_config("capacity", {}) or {}).get("technician_open_jobs", 6)
    out = []
    async for t in db.users.find({**q, "roles": "R06", "status": "active"}, {"_id": 0, "password_hash": 0}):
        jobs = await db.records.find({"type": "job", "technician_id": t["id"], "state": {"$nin": TERMINAL["job"]}}, {"_id": 0, "ref": 1, "state": 1, "appointment": 1, "id": 1}).to_list(50)
        out.append({"id": t["id"], "name": t["name"], "centre": t.get("centre_name"), "centre_id": t.get("centre_id"), "skills": t.get("skills", []), "capacity": cap, "open_jobs": len(jobs), "jobs": jobs,
                    "available": len(jobs) < cap})
    return out


@router.get("/roster")
async def roster(user=Depends(role_required("R07", "R09", "R10"))):
    q = {"centre_id": user.get("centre_id")} if user["active_role"] == "R07" else {"regions": {"$in": user.get("regions") or []}} if user["active_role"] == "R09" else {}
    unalloc = await db.records.find({"type": "job", "state": {"$in": ["created", "missed"]}, **({"centre_id": user.get("centre_id")} if user["active_role"] == "R07" else {})}, {"_id": 0, "sla": 0}).to_list(100)
    return {"technicians": await _tech_rows(q), "unallocated": unalloc}


@router.get("/capacity")
async def capacity(user=Depends(role_required("R09", "R10", "R07"))):
    q = {"kind": "service_centre"}
    if user["active_role"] == "R09":
        q["region"] = {"$in": user.get("regions") or []}
    out = []
    async for c in db.orgs.find(q, {"_id": 0}):
        techs = await _tech_rows({"centre_id": c["id"]})
        open_jobs = await db.records.count_documents({"type": "job", "centre_id": c["id"], "state": {"$nin": TERMINAL["job"]}})
        unalloc = await db.records.count_documents({"type": "job", "centre_id": c["id"], "state": {"$in": ["created", "missed"]}})
        breached = await db.records.count_documents({"type": "case", "centre_id": c["id"], "sla_state": "breached", "state": {"$nin": TERMINAL["case"]}})
        acc = await db.records.find({"type": "job", "centre_id": c["id"], "state": "accepted"}, {"_id": 0, "first_time_fix": 1}).to_list(1000)
        capsum = sum(t["capacity"] for t in techs)
        out.append({"id": c["id"], "name": c["name"], "region": c["region"], "technicians": len(techs), "capacity": capsum, "open_jobs": open_jobs, "unallocated": unalloc, "breached_cases": breached,
                    "utilisation_pct": round(100 * sum(t["open_jobs"] for t in techs) / capsum, 1) if capsum else None,
                    "ftf_pct": round(100 * sum(1 for a in acc if a.get("first_time_fix")) / len(acc), 1) if acc else None})
    return {"centres": out}


@router.get("/network")
async def network(user=Depends(role_required("R10", "R17"))):
    cen = (await capacity(user={**user, "active_role": "R10"}))["centres"]
    regions = {}
    for c in cen:
        r = regions.setdefault(c["region"], {"region": c["region"], "centres": 0, "technicians": 0, "open_jobs": 0, "breached_cases": 0})
        for k in ("technicians", "open_jobs", "breached_cases"):
            r[k] += c[k]
        r["centres"] += 1
    return {"regions": list(regions.values()), "centres": cen}


@router.get("/appointments")
async def appointments(user=Depends(role_required("R05", "R07", "R09"))):
    q = await build_query(user, "job", "open", None, None, None)
    items = await db.records.find({"$and": [q, {"appointment": {"$ne": None}}]}, {"_id": 0, "sla": 0}).to_list(300)
    pending = await db.records.find({"$and": [q, {"state": {"$in": ["allocated", "missed"]}}]}, {"_id": 0, "sla": 0}).to_list(100)
    return {"items": items, "to_schedule": pending}


@router.get("/sla/clocks")
async def sla_clocks(user=Depends(staff_user)):
    q = await build_query(user, "case", None, None, None, None)
    rows = []
    async for c in db.records.find({"$and": [q, {"sla": {"$elemMatch": {"state": {"$in": ["running", "paused"]}}}}]}, {"_id": 0}).limit(300):
        for k in c["sla"]:
            if k["state"] in ("running", "paused"):
                rows.append({"id": c["id"], "ref": c["ref"], "milestone": k["m"], "due": k["due"], "state": k["state"], "waiting_reason": (c["data"].get("record_waiting") or {}).get("waiting_reason"),
                             "owner_name": c.get("owner_name") or c.get("proposed_owner_name"), "risk": "Breached" if k.get("breached_at") else "At risk" if k.get("warned") else "On track", "calendar": k["calendar"], "history": k["history"]})
    return {"items": sorted(rows, key=lambda r: r["due"])}


@router.get("/notifications")
async def notifications(user=Depends(get_current_user)):
    items = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("at", -1).limit(40).to_list(40)
    return {"items": items, "unread": await db.notifications.count_documents({"user_id": user["id"], "read": False})}


@router.post("/notifications/read")
async def read_all(user=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@router.get("/inbox")
async def inbox(user=Depends(staff_user)):
    uid, role = user["id"], user["active_role"]
    out = {}
    if await scope_query(user, "approval") is not None:
        out["approvals"] = await db.records.find({"type": "approval", "state": "pending", "required_role": role, "requested_by": {"$ne": uid}, "$or": [{"assignee_id": None}, {"assignee_id": uid}]}, {"_id": 0, "sla": 0}).to_list(100)
    for t in ("task", "capa", "audit_finding", "mgmt_action", "escalation", "supplier_dispute"):
        if await scope_query(user, t) is None:
            continue
        out[t] = await db.records.find({"type": t, "state": {"$nin": TERMINAL[t]}, "$or": [{"assignee_id": uid}, {"action_owner_id": uid}]}, {"_id": 0, "sla": 0}).to_list(100)
    return out


@router.get("/knowledge")
async def knowledge(q: str = "", user=Depends(staff_user)):
    qq = {"audience": {"$in": [user["active_role"], "all"]}}
    if q:
        qq["$text"] = {"$search": q}
    return {"items": await db.knowledge.find(qq, {"_id": 0}).limit(20).to_list(20)}


@router.get("/products/history")
async def product_history(serial: str, user=Depends(staff_user)):
    jobs = await db.records.find({"type": "job", "data.serial": serial}, {"_id": 0, "sla": 0}).sort("created_at", -1).to_list(50)
    cases = await db.records.find({"type": "case", "data.serial": serial}, {"_id": 0, "ref": 1, "id": 1, "title": 1, "state": 1, "created_at": 1}).to_list(50)
    return {"jobs": jobs, "cases": cases}


@router.get("/incidents/{rid}/exposure")
async def exposure(rid: str, user=Depends(role_required("R14", "R10"))):
    inc = await engine.find(rid)
    if not inc or inc["type"] != "incident":
        fail(404, "Incident not found")
    cases = await db.records.find({"type": "case", "model_id": inc.get("model_id")}, {"_id": 0, "ref": 1, "id": 1, "data.serial": 1, "safety_flag": 1, "state": 1}).to_list(500) if inc.get("model_id") else []
    linked = {c["ref"] for c in inc.get("related_cases") or []}
    groups = {}
    for c in cases:
        b = (c["data"].get("serial") or "UNKNOWN")[:6]
        g = groups.setdefault(b, {"model": inc.get("model"), "batch": b, "cases": 0, "safety": 0, "linked": 0, "refs": []})
        g["cases"] += 1
        g["safety"] += 1 if c.get("safety_flag") else 0
        g["linked"] += 1 if c["ref"] in linked else 0
        g["refs"].append(c["ref"])
    return {"items": [{**g, "risk": "High" if g["safety"] > 1 else "Medium" if g["safety"] else "Low"} for g in groups.values()]}


class ExportIn(BaseModel):
    scope: str


@router.post("/exports")
async def request_export(body: ExportIn, user=Depends(role_required("R17", "R18", "R21", "R10"))):
    role = user["active_role"]
    if body.scope == "audit" and role not in ("R18", "R21"):
        fail(403, "Audit history export is limited to administrators and auditors.", code="forbidden")
    buf = io.StringIO()
    w = csv.writer(buf)
    wm = f"CONFIDENTIAL - exported by {user['email']} ({role}) at {iso()[:19]} UTC - authorised scope: {body.scope}"
    w.writerow([wm])
    if body.scope == "audit":
        w.writerow(["time", "actor", "role", "action", "object_type", "object_id", "outcome"])
        async for a in db.audit_logs.find({}, {"_id": 0}).sort("at", -1).limit(5000):
            w.writerow([a["at"], a["actor"], a["role"], a["action"], a["object_type"], a["object_id"], a["outcome"]])
    elif body.scope == "analytics":
        data = await analytics(user={**user, "active_role": role if role != "R18" else "R17"}) if role != "R18" else None
        if not data:
            fail(403, "Not permitted", code="forbidden")
        w.writerow(["family", "metric", "value"])
        for fam in ("operational", "service", "customer", "quality"):
            for k, v in data[fam].items():
                if not isinstance(v, list):
                    w.writerow([fam, k, v])
    else:
        t = body.scope.replace("records:", "")
        q = await build_query(user, t, None, None, None, None)
        w.writerow(["ref", "type", "title", "state", "region", "created_at"])
        async for r in engine.coll(t).find(q, {"_id": 0}).limit(5000):
            w.writerow([r["ref"], r["type"], r["title"], r["state"], r.get("region"), r["created_at"]])
    doc = {"id": new_id("exp"), "scope": body.scope, "requested_by": user["id"], "requested_by_name": user["name"], "watermark": wm, "state": "ready", "at": iso(), "expires_at": iso(now() + timedelta(days=7)), "content": buf.getvalue()}
    await db.exports.insert_one(dict(doc))
    await audit(user, "export_generated", "export", doc["id"], {"scope": body.scope}, sensitive=True)
    doc.pop("content")
    return doc


@router.get("/exports")
async def list_exports(user=Depends(role_required("R17", "R18", "R21", "R10"))):
    return {"items": await db.exports.find({"requested_by": user["id"]}, {"_id": 0, "content": 0}).sort("at", -1).to_list(50)}


@router.get("/exports/{eid}/download")
async def download_export(eid: str, user=Depends(get_current_user)):
    e = await db.exports.find_one({"id": eid, "requested_by": user["id"]}, {"_id": 0})
    if not e:
        fail(404, "Export not found")
    if parse_dt(e["expires_at"]) < now():
        fail(410, "Export expired")
    await audit(user, "export_downloaded", "export", eid, sensitive=True)
    return Response(content=e["content"], media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{eid}.csv"'})
