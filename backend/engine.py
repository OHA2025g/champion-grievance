import re
from core import db, now, iso, parse_dt, new_id, next_ref, fail, audit, get_config
from workflows import WF, ACTIONS, TERMINAL, action_from
import rbac
import sla
import notify
import payments

SEED = {"demo": False}
BLOCKING = ["job", "task", "requisition", "settlement", "approval", "unit", "warranty", "replacement", "tech_review"]
DEFAULT_AUTHORITY = {
    "_note": "PLACEHOLDER delegated authority limits (INR) pending BRD/SRS confirmation. null = unlimited.",
    "repair_plan": {"chain": ["R08", "R09", "R10"], "limits": {"R08": 5000, "R09": 25000, "R10": None}},
    "replacement": {"chain": ["R09", "R10"], "limits": {"R09": 30000, "R10": None}},
    "refund": {"chain": ["R09", "R10"], "limits": {"R09": 15000, "R10": None}},
    "credit_note": {"chain": ["R15", "R10"], "limits": {"R15": 25000, "R10": None}},
    "chargeable_repair_waiver": {"chain": ["R08", "R09"], "limits": {"R08": 3000, "R09": None}},
    "goodwill": {"chain": ["R09", "R10"], "limits": {"R09": 5000, "R10": None}},
    "warranty_exception": {"chain": ["R11", "R10"], "limits": {"R11": 10000, "R10": None}},
    "sla_pause": {"chain": ["R08", "R09"], "limits": {"R08": None, "R09": None}},
    "supervised_closure": {"chain": ["R08", "R09"], "limits": {"R08": None, "R09": None}},
    "appeal_reversal": {"chain": ["R16", "R10"], "limits": {"R16": 20000, "R10": None}},
    "supplier_correction": {"chain": ["R10"], "limits": {"R10": None}},
    "settlement_correction": {"chain": ["R09", "R10"], "limits": {"R09": 10000, "R10": None}},
    "channel_decision": {"chain": ["R10"], "limits": {"R10": None}},
    "stock_adjustment": {"chain": ["R09", "R10"], "limits": {"R09": None, "R10": None}},
    "config_release": {"chain": ["R18"], "limits": {"R18": None}},
}
PIN_REGION = {"1": "North", "2": "North", "3": "West", "4": "West", "5": "South", "6": "South", "7": "East", "8": "East"}
OVERRIDES = {}


def coll(rtype):
    return db.hr_records if rtype == "hr_grievance" else db.records


async def find(rid):
    return await db.records.find_one({"id": rid}, {"_id": 0}) or await db.hr_records.find_one({"id": rid}, {"_id": 0})


def state_info(rtype, st):
    return WF[rtype]["states"].get(st, {"label": st, "tone": "info", "next": ""})


def is_terminal(rec):
    return rec["state"] in TERMINAL[rec["type"]]


async def load_overrides():
    OVERRIDES.clear()
    async for c in db.config.find({"key": {"$regex": "^workflow:"}}, {"_id": 0}):
        OVERRIDES[c["key"].split(":", 1)[1]] = c["value"]


def action_roles(rtype, a):
    o = (OVERRIDES.get(rtype) or {}).get("actions", {}).get(a["key"], {})
    return o.get("roles", a["roles"])


# ---------------- validation ----------------
def validate(fields, payload):
    vals, errors = {}, {}
    payload = payload or {}
    for f in fields:
        k, v = f["k"], payload.get(f["k"])
        if v is None or (isinstance(v, str) and not v.strip()) or v == []:
            if f["req"]:
                errors[k] = f"{f['l']} is required"
            continue
        t = f["t"]
        try:
            if t == "number":
                v = float(v)
                if v.is_integer():
                    v = int(v)
                if "min" in f and v < f["min"]:
                    errors[k] = f"Must be at least {f['min']}"
                if "max" in f and v > f["max"]:
                    errors[k] = f"Must be at most {f['max']}"
            elif t in ("date", "datetime"):
                parse_dt(v if t == "datetime" else f"{str(v)[:10]}T00:00:00")
                v = str(v)
            elif t == "select":
                if f["opts"] and v not in f["opts"]:
                    errors[k] = "Choose one of the listed options"
            elif t == "json":
                import json
                v = json.loads(v) if isinstance(v, str) else v
            else:
                v = str(v).strip()
                if len(v) > 5000:
                    errors[k] = "Too long"
                if f.get("pattern") and not re.match(f["pattern"], v):
                    errors[k] = f.get("hint") or "Invalid format"
                if f.get("minlen") and len(v) < f["minlen"]:
                    errors[k] = f"Please provide at least {f['minlen']} characters"
        except Exception:
            errors[k] = "Invalid value"
        vals[k] = v
    if errors:
        fail(422, "Please correct the highlighted fields.", fields=errors)
    return vals


async def label_for(src, val):
    kind = src.split(":")[0]
    if kind == "users":
        d = await db.users.find_one({"id": val}, {"_id": 0, "name": 1})
        return d and d["name"]
    if kind == "customers":
        d = await db.customers.find_one({"id": val}, {"_id": 0, "name": 1})
        return d and d["name"]
    if kind == "models":
        d = await db.product_models.find_one({"id": val}, {"_id": 0})
        return d and f"{d['category']} / {d['model']}"
    if kind in ("centres", "orgs"):
        d = await db.orgs.find_one({"id": val}, {"_id": 0, "name": 1})
        return d and d["name"]
    if kind == "parts":
        d = await db.parts.find_one({"sku": val}, {"_id": 0})
        return d and f"{d['sku']} {d['name']}"
    if kind == "warehouses":
        d = await db.warehouses.find_one({"id": val}, {"_id": 0, "name": 1})
        return d and d["name"]
    if kind == "orders":
        d = await db.orders.find_one({"id": val}, {"_id": 0, "ref": 1})
        return d and d["ref"]
    if kind in ("records", "policies"):
        d = await find(val)
        return d and f"{d['ref']} {d.get('title', '')}".strip()
    return str(val)


async def resolve_labels(fields, vals):
    for f in fields:
        if f["t"] == "lookup" and vals.get(f["k"]):
            lab = await label_for(f["src"], vals[f["k"]])
            if lab is None:
                fail(422, "Please correct the highlighted fields.", fields={f["k"]: f"{f['l']} not found"})
            vals[f["k"] + "_label"] = lab


# ---------------- events ----------------
async def log_event(rec, user, action, label, frm, to, values=None, cust=False, note=None):
    ev = {"id": new_id("ev"), "record_id": rec["id"], "root_id": rec.get("root_id") or rec["id"], "type": rec["type"], "ref": rec["ref"],
          "at": iso(), "actor_id": (user or {}).get("id", "system"), "actor_name": (user or {}).get("name", "System"),
          "actor_role": (user or {}).get("active_role", "system"), "action": action, "label": label, "from": frm, "to": to,
          "from_label": state_info(rec["type"], frm)["label"] if frm else None, "to_label": state_info(rec["type"], to)["label"] if to else None,
          "values": {k: v for k, v in (values or {}).items() if not isinstance(v, (dict, list))}, "visibility": "customer" if cust else "internal", "note": note}
    await (db.hr_events if rec["type"] == "hr_grievance" else db.events).insert_one(dict(ev))
    return ev


async def system_transition(rec, to, label, user=None, set_=None, cust=False):
    upd = {"state": to, "updated_at": iso(), "next_action": state_info(rec["type"], to)["next"], **(set_ or {})}
    await coll(rec["type"]).update_one({"id": rec["id"]}, {"$set": upd, "$inc": {"version": 1}})
    await log_event(rec, user, "system_transition", label, rec["state"], to, cust=cust)
    if to in TERMINAL[rec["type"]]:
        await sla.stop_all(rec["id"])
    return await find(rec["id"])


# ---------------- creation ----------------
async def _customer_fields(rec, cust_id=None, user=None):
    c = None
    if cust_id:
        c = await db.customers.find_one({"id": cust_id}, {"_id": 0})
    elif user and "R01" in user.get("roles", []):
        c = await db.customers.find_one({"user_id": user["id"]}, {"_id": 0})
    if c:
        rec.update({"customer_id": c["id"], "customer_name": c["name"], "customer_user_id": c.get("user_id"), "region": c.get("region") or rec.get("region")})


async def _model_fields(rec, model_id):
    m = await db.product_models.find_one({"id": model_id}, {"_id": 0}) if model_id else None
    if m:
        rec.update({"model_id": m["id"], "model": m["model"], "category": m["category"], "skill": m.get("skill"), "product": f"{m['category']} / {m['model']}"})


async def create_record(user, rtype, subtype, payload, parent=None, system=False, extra=None):
    wf = WF[rtype]
    if not system:
        spec = wf["create"].get(subtype)
        if not spec or user.get("active_role") not in spec["roles"]:
            await audit(user, "create_denied", rtype, "", {"subtype": subtype}, outcome="denied")
            fail(403, "Your role cannot create this record type.", code="forbidden")
        mod = rbac.TYPE_MODULE.get(rtype)
        if mod and not await rbac.module_enabled(mod):
            fail(403, "This module is disabled by an administrator.", code="module_disabled")
        vals = validate(spec["fields"], payload)
        await resolve_labels(spec["fields"], vals)
    else:
        vals = dict(payload or {})
    t = iso()
    rec = {"id": new_id(rtype[:3]), "ref": await next_ref(wf["prefix"]), "type": rtype, "subtype": subtype, "title": vals.get("title") or vals.get("subject") or "",
           "state": wf["initial"], "priority": vals.get("priority") or "P3 - Normal", "data": vals, "created_by": (user or {}).get("id", "system"),
           "created_by_name": (user or {}).get("name", "System"), "created_by_role": (user or {}).get("active_role", "system"), "created_at": t, "updated_at": t,
           "version": 1, "demo": SEED["demo"], "sla": [], "owner_id": None, "owner_name": None, "region": None, "centre_id": None, "org_id": None,
           "parent_id": None, "root_id": None, "safety_flag": False}
    if parent:
        rec.update({"parent_id": parent["id"], "parent_ref": parent["ref"], "parent_type": parent["type"], "root_id": parent.get("root_id") or parent["id"],
                    "root_ref": parent.get("root_ref") or parent["ref"]})
        for k in ["region", "centre_id", "centre_name", "customer_id", "customer_name", "customer_user_id", "org_id", "org_name", "model_id", "model", "category", "product", "skill", "safety_flag"]:
            if parent.get(k) is not None and rec.get(k) in (None, False):
                rec[k] = parent[k]
        rec["priority"] = vals.get("priority") or parent.get("priority") or rec["priority"]
    if user and user.get("org_id") and user.get("active_role") in ("R02", "R03"):
        rec["org_id"], rec["org_name"], rec["region"] = user["org_id"], user.get("org_name"), user.get("regions", [None])[0] if user.get("regions") else rec["region"]
    if vals.get("model_id"):
        await _model_fields(rec, vals["model_id"])
    if extra:
        rec.update(extra)
    pre = PRE_CREATE.get(rtype)
    if pre:
        await pre(user, rec, vals)
    if not rec["region"] and vals.get("pin"):
        rec["region"] = PIN_REGION.get(str(vals["pin"])[0], "West")
    if rec["region"] and not rec.get("centre_id") and rtype in ("case", "job"):
        c = await db.orgs.find_one({"kind": "service_centre", "region": rec["region"]}, {"_id": 0})
        if c:
            rec["centre_id"], rec["centre_name"] = c["id"], c["name"]
    if not rec["title"]:
        rec["title"] = default_title(rec, wf)
    rec["next_action"] = state_info(rtype, rec["state"])["next"]
    await coll(rtype).insert_one(dict(rec))
    await log_event(rec, user, "created", f"{wf['label']} created", None, rec["state"], {k: v for k, v in vals.items() if not k.endswith("_label")} if rtype != "hr_grievance" else {}, cust=rtype in ("case", "appeal"))
    for m in {"case": ["first_response", "resolution"], "appeal": ["review"], "escalation": ["response"], "warranty": ["decision"]}.get(rtype, []):
        await sla.start(rec, m)
    post = POST_CREATE.get(rtype)
    if post:
        await post(user, rec, vals)
    await audit(user, f"create:{rtype}", rtype, rec["id"], {"ref": rec["ref"], "subtype": subtype}, sensitive=rtype == "hr_grievance")
    return await find(rec["id"])


def default_title(rec, wf):
    d = rec["data"]
    prod = rec.get("product") or d.get("product_category") or ""
    if rec["type"] == "case":
        return f"{d.get('issue_category') or wf['create'].get(rec['subtype'], {}).get('label', 'Case')} - {prod}".strip(" -")
    if rec["type"] == "job":
        return f"{d.get('job_type', 'Service job')} - {prod}".strip(" -")
    if rec["type"] == "policy":
        return " ".join(str(x) for x in [d.get("title") or d.get("model") or d.get("component"), d.get("version", "")] if x)
    base = d.get("issue") or d.get("category") or d.get("reason") or d.get("approval_type") or wf["label"]
    return f"{base} - {rec.get('parent_ref') or prod}".strip(" -")


async def pre_case(user, rec, vals):
    await _customer_fields(rec, vals.get("customer_id"), user)
    if rec["subtype"] in ("dealer_customer_case", "stock_claim"):
        rec["customer_name"] = vals.get("customer_name") or rec.get("org_name")
        rec["queue"] = "Dealer cases"
    elif rec["subtype"] == "bulk_grievance":
        rec["customer_name"] = rec.get("org_name")
        rec["queue"] = "Business accounts"
    else:
        rec["queue"] = "Service coordination"
    if vals.get("safety_concern") and vals["safety_concern"] != "No hazard reported":
        rec.update({"safety_flag": True, "state": "safety_escalated", "priority": "P1 - Critical", "queue": "Safety coordination"})
    if vals.get("amount"):
        rec["amount"] = vals["amount"]
    ors = [{"customer_id": rec["customer_id"]}] if rec.get("customer_id") else []
    if vals.get("serial"):
        ors.append({"data.serial": vals["serial"]})
    if ors:
        cutoff = iso(now().replace(year=now().year - 1))
        dups = await db.records.find({"type": "case", "$or": ors, "created_at": {"$gte": cutoff}}, {"_id": 0, "id": 1, "ref": 1, "title": 1, "state": 1}).to_list(10)
        rec["possible_duplicates"] = dups


async def post_case(user, rec, vals):
    if rec["safety_flag"]:
        await create_incident_for(user, rec, vals.get("safety_concern"))
    await notify.customer(rec, "ticket_created", actor=user)
    if rec["created_by_role"] in ("R01", "R02", "R03"):
        await notify.to_roles(["R04"], f"New {rec['subtype'].replace('_', ' ')} {rec['ref']}", rec["title"], rec, "urgent" if rec["safety_flag"] else "info")
    if rec["subtype"] in ("dealer_customer_case", "stock_claim"):
        await create_record(user, "channel_dispute", "dispute", {"issue": "Stock damage claim" if rec["subtype"] == "stock_claim" else "Delayed customer service",
                                                                 "description": vals.get("description", ""), "customer_impact": "Medium", "case_id": rec["id"], "amount": vals.get("amount")},
                            parent=rec, system=True, extra={"title": f"Dealer claim assessment - {rec['ref']}"})
        await notify.to_roles(["R15"], f"Dealer claim {rec['ref']} awaiting assessment", rec["title"], rec)


async def create_incident_for(user, rec, hazard):
    if await db.records.find_one({"type": "incident", "root_id": rec.get("root_id") or rec["id"], "state": {"$nin": TERMINAL["incident"]}}):
        return
    inc = await create_record(user, "incident", "incident", {"hazard": hazard, "description": rec["data"].get("description") or rec.get("title"), "case_id": rec["id"]},
                              parent=rec, system=True, extra={"priority": "P1 - Critical", "safety_flag": True, "title": f"{hazard} - {rec.get('product') or rec['title']}"})
    await notify.to_roles(["R14"], f"URGENT safety incident {inc['ref']}", f"{hazard} reported on {rec['ref']}", inc, "urgent")
    await notify.customer(rec, "escalation", "A product safety specialist will contact you. Please keep the product switched off and unplugged.", actor=user)


async def pre_hr(user, rec, vals):
    if vals.get("conflict_declaration") == "Conflict declared":
        fail(409, "Conflict declared - this grievance must be registered and handled by a non-conflicted HR officer.")
    rec.update({"owner_id": user["id"], "owner_name": user["name"], "restricted_to": [user["id"]], "confidential": True,
                "title": f"{vals['category']} - restricted", "priority": "P1 - Critical" if vals.get("urgency") == "Urgent" else "P3 - Normal"})


async def pre_appeal(user, rec, vals):
    case = await find(vals.get("case_id")) if vals.get("case_id") else None
    if case and not rec.get("parent_id"):
        rec.update({"parent_id": case["id"], "parent_ref": case["ref"], "parent_type": "case", "root_id": case["id"], "root_ref": case["ref"],
                    "customer_id": case.get("customer_id"), "customer_name": case.get("customer_name"), "customer_user_id": case.get("customer_user_id"),
                    "org_id": case.get("org_id"), "region": case.get("region")})
    rec["title"] = f"Appeal - {vals.get('original_decision', 'decision')} ({rec.get('root_ref', '')})"


async def post_appeal(user, rec, vals):
    if rec.get("root_id"):
        await db.records.update_one({"id": rec["root_id"]}, {"$set": {"under_appeal": True, "appeal_id": rec["id"]}})
    await notify.to_roles(["R16"], f"New appeal {rec['ref']}", rec["title"], rec)


async def pre_owned(user, rec, vals):
    for k in ("assignee_id", "action_owner_id"):
        if vals.get(k):
            rec[k] = vals[k]
            rec[k.replace("_id", "_name")] = vals.get(k + "_label")
    if vals.get("case_id") and not rec.get("parent_id"):
        case = await find(vals["case_id"])
        if case:
            rec.update({"root_id": case.get("root_id") or case["id"], "root_ref": case.get("root_ref") or case["ref"], "region": case.get("region"),
                        "customer_id": case.get("customer_id"), "customer_name": case.get("customer_name"), "customer_user_id": case.get("customer_user_id")})
    if vals.get("org_id"):
        o = await db.orgs.find_one({"id": vals["org_id"]}, {"_id": 0})
        if o:
            rec.update({"org_id": o["id"], "org_name": o["name"], "region": rec.get("region") or o.get("region")})
    if vals.get("amount"):
        rec["amount"] = vals["amount"]


async def post_owned(user, rec, vals):
    for k in ("assignee_id", "action_owner_id"):
        if rec.get(k):
            await notify.to_users([rec[k]], f"{WF[rec['type']]['label']} assigned: {rec['ref']}", rec["title"], rec)


async def pre_settlement(user, rec, vals):
    if rec["subtype"] == "credit_note" and vals.get("approval_id"):
        ap = await find(vals["approval_id"])
        if not ap or ap["type"] != "approval" or ap["state"] != "approved":
            fail(409, "A credit note requires an approved claim approval.")
        if float(vals["amount"]) > float(ap.get("amount") or 0):
            fail(409, "Credit amount exceeds the approved amount.")
        rec.update({"approval_id": ap["id"], "approval_ref": ap["ref"], "root_id": ap.get("root_id"), "root_ref": ap.get("root_ref"), "org_id": ap.get("org_id"), "region": ap.get("region")})
    rec["amount"] = vals.get("amount", rec.get("amount"))


async def pre_replacement(user, rec, vals):
    if vals.get("approval_id"):
        ap = await find(vals["approval_id"])
        if not ap or ap.get("approval_type") != "replacement" or ap["state"] != "approved":
            fail(409, "A replacement order requires an approved replacement approval.")
        rec.update({"approval_id": ap["id"], "root_id": ap.get("root_id"), "root_ref": ap.get("root_ref")})
    await pre_owned(user, rec, vals)


async def post_return(user, rec, vals):
    if str(vals.get("safety_hold", "")).startswith("Yes"):
        await coll("return").update_one({"id": rec["id"]}, {"$set": {"quarantine": True}})


PRE_CREATE = {"case": pre_case, "hr_grievance": pre_hr, "appeal": pre_appeal, "settlement": pre_settlement, "replacement": pre_replacement,
              **{t: pre_owned for t in ["task", "capa", "mgmt_action", "audit_finding", "channel_dispute", "supplier_dispute", "correspondence", "escalation", "warranty", "incident"]}}
POST_CREATE = {"case": post_case, "appeal": post_appeal, "return": post_return, **{t: post_owned for t in ["task", "capa", "mgmt_action", "audit_finding", "correspondence"]}}


# ---------------- approvals ----------------
async def authority():
    return await get_config("authority_matrix", DEFAULT_AUTHORITY) or DEFAULT_AUTHORITY


async def role_for_amount(atype, amount, after=None):
    m = (await authority()).get(atype) or {"chain": ["R10"], "limits": {"R10": None}}
    chain = m["chain"]
    if after in chain:
        chain = chain[chain.index(after) + 1:]
    for r in chain:
        lim = m["limits"].get(r)
        if lim is None or float(amount or 0) <= float(lim):
            return r
    return None


async def create_approval(user, atype, subject, amount=0, summary="", payload=None, assignee_id=None, after_role=None):
    existing = await db.records.find_one({"type": "approval", "subject_id": subject["id"], "approval_type": atype, "state": "pending"}, {"_id": 0})
    if existing:
        return existing
    role = await role_for_amount(atype, amount, after_role)
    if not role:
        fail(409, "No approver in the authority matrix can approve this amount.")
    extra = {"approval_type": atype, "subject_id": subject["id"], "subject_ref": subject["ref"], "subject_type": subject["type"], "amount": amount,
             "required_role": role, "requested_by": (user or {}).get("id"), "requested_by_name": (user or {}).get("name"), "assignee_id": assignee_id,
             "payload": payload or {}, "title": f"{atype.replace('_', ' ').capitalize()} - {subject['ref']}"}
    ap = await create_record(user, "approval", atype, {"approval_type": atype, "summary": summary, "amount": amount}, parent=subject, system=True, extra=extra)
    targets = [assignee_id] if assignee_id else None
    if targets:
        await notify.to_users(targets, f"Approval requested: {ap['ref']}", ap["title"], ap, "pending")
    else:
        await notify.to_roles([role], f"Approval requested: {ap['ref']}", ap["title"], ap, "pending", region=subject.get("region") if role in ("R09",) else None)
    return ap


async def apply_approval(user, ap, approved):
    subj = await find(ap["subject_id"])
    t, p = ap["approval_type"], ap.get("payload") or {}
    if not subj and t != "stock_adjustment":
        return
    subj = subj or {"id": ap["subject_id"], "ref": ap.get("subject_ref"), "type": "stock", "state": "", "data": {}}
    root = await find(ap.get("root_id")) if ap.get("root_id") else None
    if approved:
        if t == "repair_plan":
            st = {"repair_authorised": True, "approval_required": False}
            job = subj
            ready = job.get("estimate_state") != "pending"
            if job["state"] == "awaiting_approval" and ready:
                await system_transition(job, "authorised", f"Repair plan approved ({ap['ref']})", user, st)
            else:
                await db.records.update_one({"id": job["id"]}, {"$set": st})
            if p.get("review_id"):
                rv = await find(p["review_id"])
                if rv and rv["state"] == "referred":
                    await system_transition(rv, "approved", f"Approved by higher authority ({ap['ref']})", user)
            await notify.to_users([job.get("technician_id")], f"Repair authorised for {job['ref']}", "You may proceed once parts are ready.", job)
        elif t in ("refund", "goodwill", "credit_note"):
            await create_record(user, "settlement", t, {"amount": ap["amount"], "recipient": p.get("recipient", ""), "kind": t},
                                parent=subj, system=True, extra={"amount": ap["amount"], "approval_id": ap["id"], "approval_ref": ap["ref"], "title": f"{t.replace('_', ' ').capitalize()} settlement - {subj.get('root_ref') or subj['ref']}"})
            await notify.to_roles(["R13"], f"Approved settlement queued from {ap['ref']}", ap["title"], ap)
        elif t == "replacement":
            await create_record(user, "replacement", "replacement", {"case_id": subj.get("root_id") or subj["id"], "approval_id": ap["id"], "old_serial": subj["data"].get("serial", ""), "model_id": subj.get("model_id")},
                                parent=subj, system=True, extra={"approval_id": ap["id"], "title": f"Approved replacement - {subj.get('root_ref') or subj['ref']}"})
            await notify.to_roles(["R12"], f"Replacement approved {ap['ref']}", ap["title"], ap)
        elif t == "chargeable_repair_waiver":
            await db.records.update_one({"id": subj["id"]}, {"$set": {"charge_waived": True}})
        elif t == "warranty_exception":
            await system_transition(subj, "decision_recorded", f"Warranty exception approved ({ap['ref']})", user, {"coverage": "Covered - exception approved"})
        elif t == "sla_pause":
            await sla.pause_all(subj["id"], f"approved waiting period {ap['ref']}")
        elif t == "supervised_closure":
            await system_transition(subj, "closed", f"Supervised closure approved ({ap['ref']}) - customer unreachable", user,
                                    {"closed_at": iso(), "closure_outcome": "Closed - customer unreachable (supervised)"}, cust=True)
            await notify.customer(subj, "closure", actor=user)
        elif t == "appeal_reversal":
            remedy = p.get("remedy") or "None"
            if remedy in ("Refund", "Credit") and ap.get("amount"):
                await create_record(user, "settlement", "refund", {"amount": ap["amount"]}, parent=subj, system=True,
                                    extra={"amount": ap["amount"], "approval_id": ap["id"], "approval_ref": ap["ref"], "title": f"Appeal remedy - {subj['ref']}"})
            if remedy in ("None", "Apology and explanation"):
                await system_transition(subj, "closed", "Amended decision approved - closed", user, cust=True)
            else:
                await system_transition(subj, "remedy_in_progress", f"Reversal approved ({ap['ref']})", user, cust=True)
            await notify.customer(subj, "appeal_outcome", f"The original decision has been {p.get('decision', 'amended').lower().replace(' decision', 'ed')}. Remedy: {remedy}.", actor=user)
        elif t == "supplier_correction":
            await system_transition(subj, "correction_in_progress", f"Correction approved ({ap['ref']})", user)
        elif t == "settlement_correction":
            await create_record(user, "settlement", "correction", {"amount": ap["amount"]}, parent=subj, system=True,
                                extra={"amount": ap["amount"], "approval_id": ap["id"], "approval_ref": ap["ref"], "title": f"Correcting entry for {subj['ref']}"})
            await system_transition(subj, "reconciled", f"Correction approved ({ap['ref']}); correcting entry raised", user)
        elif t == "channel_decision":
            await system_transition(subj, "recovery_in_progress", f"Decision approved ({ap['ref']})", user)
            if ap.get("amount"):
                await apply_approval(user, {**ap, "approval_type": "credit_note", "subject_id": subj.get("parent_id") or subj["id"]}, True)
        elif t == "stock_adjustment":
            await db.stock.update_one({"sku": p["sku"], "warehouse_id": p["warehouse_id"]}, {"$set": {"on_hand": p["counted"]}})
            await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "adjustment", "sku": p["sku"], "warehouse_id": p["warehouse_id"], "qty": p["counted"] - p["system"], "ref": ap["ref"], "approved": True})
        elif t == "config_release":
            await db.records.update_one({"id": subj["id"]}, {"$set": {"release_approved": True, "release_approval_ref": ap["ref"]}})
    else:
        if t == "repair_plan" and subj["state"] == "awaiting_approval":
            await system_transition(subj, "diagnosed", f"Repair plan rejected ({ap['ref']})", user, {"repair_authorised": False})
            await notify.to_users([subj.get("technician_id")], f"Repair plan rejected for {subj['ref']}", "Review diagnosis with your supervisor.", subj, "urgent")
        elif t == "sla_pause" and subj["state"] == "waiting":
            await system_transition(subj, "in_progress", f"Waiting period not approved ({ap['ref']}) - clock continues", user)
        elif t == "warranty_exception":
            await system_transition(subj, "decision_recorded", f"Exception rejected ({ap['ref']})", user, {"coverage": "Chargeable - exception rejected"})
        elif t == "appeal_reversal":
            await system_transition(subj, "under_review", f"Reversal not approved ({ap['ref']})", user)
        elif t == "supplier_correction":
            await system_transition(subj, "reconciling", f"Correction not approved ({ap['ref']})", user)
        elif t == "channel_decision":
            await system_transition(subj, "facts_reconciled", f"Decision not approved ({ap['ref']})", user)
        elif t == "config_release":
            await system_transition(subj, "tested", f"Release not approved ({ap['ref']})", user)
    if root and root.get("owner_id"):
        await notify.to_users([root["owner_id"], ap.get("requested_by")], f"Approval {ap['ref']} {'approved' if approved else 'rejected'}", ap["title"], ap, "done" if approved else "urgent")


async def pending_dependencies(rec):
    items = await db.records.find({"root_id": rec["id"], "type": {"$in": BLOCKING}}, {"_id": 0, "id": 1, "ref": 1, "type": 1, "state": 1, "title": 1, "data.mandatory": 1}).to_list(500)
    out = []
    for i in items:
        if i["state"] in TERMINAL[i["type"]]:
            continue
        if i["type"] == "task" and (i.get("data") or {}).get("mandatory") != "Yes":
            continue
        out.append({"id": i["id"], "ref": i["ref"], "type": i["type"], "title": i.get("title"), "state": state_info(i["type"], i["state"])["label"]})
    return out


async def sla_breach_escalation(rec, clock):
    if rec["type"] != "case" or await db.records.find_one({"type": "escalation", "parent_id": rec["id"], "state": {"$nin": TERMINAL["escalation"]}}):
        return
    esc = await create_record(None, "escalation", "escalation", {"reason": f"SLA breach - {clock['m'].replace('_', ' ')}", "summary": f"{rec['ref']} breached {clock['m']} due {clock['due'][:16]}"},
                              parent=rec, system=True, extra={"title": f"SLA breach - {rec['ref']}", "priority": rec.get("priority")})
    await notify.to_roles(["R09"], f"SLA breach escalation {esc['ref']}", esc["title"], esc, "urgent", region=rec.get("region"))


# ---------------- who / allowed ----------------
def who_ok(a, rec, user):
    w, uid, role = a.get("who"), user["id"], user["active_role"]
    if not w:
        return True
    if w == "owner":
        return rec.get("owner_id") == uid
    if w == "proposed_owner":
        return rec.get("proposed_owner_id") == uid
    if w == "technician":
        return rec.get("technician_id") == uid
    if w == "customer_or_org":
        if role == "R01":
            return rec.get("customer_user_id") == uid or rec.get("created_by") == uid
        return bool(user.get("org_id")) and rec.get("org_id") == user.get("org_id")
    if w == "assignee_or_creator":
        return uid in (rec.get("assignee_id"), rec.get("created_by"), rec.get("owner_id")) or role in ("R05", "R09", "R10", "R14") and rec["type"] in ("task", "capa", "escalation")
    if w == "approver":
        return rec.get("required_role") == role and rec.get("requested_by") != uid and (not rec.get("assignee_id") or rec["assignee_id"] == uid)
    if w == "reviewer":
        return rec.get("reviewer_id") == uid
    if w == "action_owner":
        return rec.get("action_owner_id") == uid
    if w == "creator":
        return rec.get("created_by") == uid
    if w == "not_creator":
        return rec.get("created_by") != uid
    return False


def allowed_actions(rec, user):
    out = []
    for a in WF[rec["type"]]["actions"]:
        if user["active_role"] not in action_roles(rec["type"], a):
            continue
        if rec["state"] not in action_from(a, rec["type"]):
            continue
        if a.get("sub") and rec.get("subtype") not in a["sub"]:
            continue
        if a["key"] == "request_review" and rec.get("under_appeal"):
            continue
        if not who_ok(a, rec, user):
            continue
        out.append({k: a[k] for k in ("key", "label", "fields", "danger", "ev", "cust")})
    return out


# ---------------- run action ----------------
async def run_action(user, rid, key, payload, idem=None, expected_version=None):
    rec = await find(rid)
    if not rec:
        fail(404, "Record not found.")
    scope = await rbac.check_view(user, rec)
    if scope == "ro":
        await audit(user, "action_denied", rec["type"], rid, {"action": key, "reason": "read-only scope"}, outcome="denied")
        fail(403, "Your access to this record is read-only.", code="read_only")
    a = ACTIONS[rec["type"]].get(key)
    if not a:
        fail(404, "Unknown action.")
    if user["active_role"] not in action_roles(rec["type"], a):
        await audit(user, "action_denied", rec["type"], rid, {"action": key}, outcome="denied")
        fail(403, "Your role is not permitted to perform this action.", code="forbidden")
    if idem:
        prior = await db.idempotency.find_one({"key": idem}, {"_id": 0})
        if prior:
            if (prior["user_id"], prior["record_id"], prior["action"]) != (user["id"], rid, key):
                fail(409, "This request key was already used for a different action. Reload and retry.", code="idempotency_mismatch")
            return {**prior["result"], "replayed": True}
    if rec["state"] not in action_from(a, rec["type"]) or (a.get("sub") and rec.get("subtype") not in a["sub"]):
        fail(409, f"This action is not available while the record is '{state_info(rec['type'], rec['state'])['label']}'.", code="invalid_state")
    if not who_ok(a, rec, user):
        fail(403, "Only the accountable party for this step can perform this action.", code="not_accountable")
    if expected_version is not None and int(expected_version) != rec["version"]:
        fail(409, "This record was updated by someone else. Reload to see the latest version.", code="conflict", current_version=rec["version"])
    vals = validate(a["fields"], payload)
    await resolve_labels(a["fields"], vals)
    if a.get("ev"):
        n = await db.evidence.count_documents({"record_id": rid, "scan_state": "clean"})
        if n < a["ev"]:
            fail(422, f"Attach at least {a['ev']} clean evidence file(s) before this step.", code="evidence_required")
    ctx = {"user": user, "rec": rec, "vals": vals, "a": a, "to": a["to"], "set": {}, "skip_notify": False}
    pre = PRE.get(f"{rec['type']}.{key}")
    if pre:
        await pre(ctx)
    new_state = ctx["to"] or rec["state"]
    sets = {"state": new_state, "updated_at": iso(), "next_action": state_info(rec["type"], new_state)["next"], f"data.{key}": vals, **ctx["set"]}
    res = await coll(rec["type"]).update_one({"id": rid, "version": rec["version"]}, {"$set": sets, "$inc": {"version": 1}})
    if res.modified_count == 0:
        fail(409, "This record was updated by someone else. Reload and retry.", code="conflict")
    after = await find(rid)
    ev = await log_event(after, user, key, a["label"], rec["state"], new_state, vals, cust=a["cust"])
    ctx["rec"], ctx["before"] = after, rec
    post = POST.get(f"{rec['type']}.{key}")
    if post:
        await post(ctx)
    for m in a["meet"] + MEET_MAP.get(f"{rec['type']}.{key}", []):
        await sla.meet(rid, m)
        if after.get("root_id"):
            await sla.meet(after["root_id"], m)
    for m in a["start"]:
        await sla.start(after, m)
    if new_state in TERMINAL[rec["type"]]:
        await sla.stop_all(rid)
        if rec["type"] == "appeal" and after.get("root_id"):
            await db.records.update_one({"id": after["root_id"], "appeal_id": rid}, {"$set": {"under_appeal": False}})
    after = await find(rid)
    if a["cust"] and not ctx["skip_notify"] and rec["type"] != "hr_grievance" and user["active_role"] not in rbac.EXTERNAL:
        msg = vals.get("message") or vals.get("explanation") or vals.get("requested_items") or vals.get("reasons") or f"{a['label']} recorded on {after['ref']}."
        await notify.customer(after, a["tpl"] or "status_update", msg, vals.get("channel"), user)
    watchers = [x for x in (after.get("owner_id"), after.get("assignee_id"), after.get("technician_id"), after.get("created_by")) if x and x != user["id"] and x != after.get("customer_user_id")]
    await notify.to_users(watchers, f"{after['ref']}: {a['label']}", f"by {user['name']} - now {state_info(after['type'], after['state'])['label']}", after)
    await audit(user, f"action:{key}", rec["type"], rid, {"from": rec["state"], "to": new_state, "ref": rec["ref"]}, sensitive=rec["type"] == "hr_grievance")
    result = {"record_id": rid, "state": after["state"], "version": after["version"], "event_id": ev["id"]}
    if idem:
        await db.idempotency.insert_one({"key": idem, "user_id": user["id"], "record_id": rid, "action": key, "result": result, "at": iso()})
    return result


MEET_MAP = {"appeal.issue_decision": ["review"], "escalation.assign_recovery_owner": ["response"], "escalation.escalate_national": ["response"],
            "warranty.record_coverage_decision": ["decision"], "contact.link_to_case": ["first_response"], "case.link_duplicate": ["first_response", "resolution"]}


def to_if(ctx, cond, state):
    if cond:
        ctx["to"] = state


async def _child(ctx, rtype, subtype, payload, extra=None):
    return await create_record(ctx["user"], rtype, subtype, payload, parent=ctx["rec"], system=True, extra=extra)


# ---- case ----
async def p_case_route(c):
    v = c["vals"]
    c["set"].update({"proposed_owner_id": v["owner_id"], "proposed_owner_name": v["owner_id_label"], "priority": v["priority"], "queue": v["queue"], "category": v["issue_category"]})


async def a_case_route(c):
    await notify.to_users([c["vals"]["owner_id"]], f"Ownership handoff requested: {c['rec']['ref']}", c["rec"]["title"], c["rec"], "pending")


async def p_case_safety(c):
    c["set"].update({"safety_flag": True, "priority": "P1 - Critical", "queue": "Safety coordination"})


async def a_case_safety(c):
    await create_incident_for(c["user"], c["rec"], c["vals"]["hazard"])


async def p_case_dup(c):
    t = await find(c["vals"]["target_id"])
    if not t or t["type"] != "case" or t["id"] == c["rec"]["id"]:
        fail(422, "Choose a different existing case.")
    c["set"].update({"duplicate_of": t["id"], "duplicate_of_ref": t["ref"], "closed_at": iso()})


async def a_case_dup(c):
    t = await find(c["vals"]["target_id"])
    await log_event(t, c["user"], "duplicate_linked", f"Contact from {c['rec']['ref']} linked as duplicate", None, None, {"reason": c["vals"]["reason"]})


async def p_case_accept(c):
    r, u = c["rec"], c["user"]
    if r.get("proposed_owner_id") and r["proposed_owner_id"] != u["id"]:
        fail(403, "This handoff is proposed to another owner.", code="not_accountable")
    c["set"].update({"owner_id": u["id"], "owner_name": u["name"], "proposed_owner_id": None, "proposed_owner_name": None})


async def p_case_decline(c):
    c["set"].update({"proposed_owner_id": None, "proposed_owner_name": None})


async def a_case_decline(c):
    await notify.to_roles(["R04"], f"Ownership declined on {c['rec']['ref']}", c["vals"]["reason"], c["rec"], "urgent")


async def p_case_handoff(c):
    c["set"].update({"proposed_owner_id": c["vals"]["owner_id"], "proposed_owner_name": c["vals"]["owner_id_label"]})


async def a_case_job(c):
    r, v = c["rec"], c["vals"]
    job = await _child(c, "job", "service", {"job_type": v["job_type"], "notes": v.get("notes", ""), "address": r["data"].get("address", ""), "serial": r["data"].get("serial", "")},
                       {"centre_id": v["centre_id"], "centre_name": v["centre_id_label"], "skill": v["skill"]})
    await notify.to_roles(["R07"], f"New job {job['ref']} for allocation", job["title"], job, centre=v["centre_id"])


async def a_case_task(c):
    v = c["vals"]
    await _child(c, "task", "task", {**v, "title": f"{v['task_type']} - {c['rec']['ref']}"},
                 {"assignee_id": v["assignee_id"], "assignee_name": v["assignee_id_label"], "title": f"{v['task_type']} - {c['rec']['ref']}", "due": v["due"], "team": v["team"]})
    await notify.to_users([v["assignee_id"]], f"Task assigned on {c['rec']['ref']}", v["task_type"], c["rec"])


async def a_case_warranty(c):
    r = c["rec"]
    w = await _child(c, "warranty", "claim", {"component": c["vals"]["component"], "claim_notes": c["vals"].get("claim_notes", ""), "serial": r["data"].get("serial", ""),
                                              "purchase_date": r["data"].get("purchase_date", ""), "purchase_evidence": r.get("purchase_evidence", "Not provided")})
    await notify.to_roles(["R11"], f"Warranty assessment requested {w['ref']}", w["title"], w)


async def a_case_review(c):
    await _child(c, "tech_review", "review", {"question": c["vals"]["question"]}, {"title": f"Technical review - {c['rec']['ref']}"})
    await notify.to_roles(["R08"], f"Technical review requested on {c['rec']['ref']}", c["vals"]["question"], c["rec"])


async def a_case_waiting(c):
    v = c["vals"]
    if v["pause_eligibility"].startswith("Eligible"):
        await create_approval(c["user"], "sla_pause", c["rec"], 0, f"{v['waiting_reason']} until {v['next_review']}", assignee_id=v["authoriser_id"])


async def a_case_resume(c):
    await sla.resume_all(c["rec"]["id"])


async def a_case_escalate(c):
    v, r = c["vals"], c["rec"]
    esc = await _child(c, "escalation", "escalation", {"reason": v["reason"], "summary": v["summary"], "recommendation": v.get("recommendation", "")}, {"title": f"{v['reason']} - {r['ref']}"})
    await notify.to_roles(["R09"], f"Escalation {esc['ref']} raised", esc["title"], esc, "urgent", region=r.get("region"))


async def a_case_remedy(c):
    v = c["vals"]
    await create_approval(c["user"], v["remedy"], c["rec"], v["amount"], v["justification"], {"recipient": v["recipient"]})


async def p_case_units(c):
    lines = [ln.strip() for ln in c["vals"]["units"].splitlines() if ln.strip()]
    errors, units, seen = [], [], set()
    for i, ln in enumerate(lines, 1):
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) != 2 or not re.match(r"^[A-Za-z0-9-]{6,20}$", parts[1]):
            errors.append(f"Line {i}: expected 'site, serial' with a 6-20 character serial")
        elif parts[1] in seen or await db.records.find_one({"type": "unit", "root_id": c["rec"]["id"], "data.serial": parts[1]}):
            errors.append(f"Line {i}: duplicate serial {parts[1]}")
        else:
            seen.add(parts[1])
            units.append(parts)
    if errors or not units:
        fail(422, "Unit list validation failed.", fields={"units": "; ".join(errors) or "No units supplied"})
    c["units"] = units


async def a_case_units(c):
    for site, serial in c["units"]:
        await _child(c, "unit", "unit", {"site": site, "serial": serial}, {"title": f"{serial} at {site}"})
    await db.records.update_one({"id": c["rec"]["id"]}, {"$inc": {"unit_count": len(c["units"])}})


async def a_case_unit_jobs(c):
    v = c["vals"]
    n = 0
    async for u in db.records.find({"type": "unit", "parent_id": c["rec"]["id"], "state": "open"}, {"_id": 0}):
        job = await create_record(c["user"], "job", "service", {"job_type": "Field visit", "serial": u["data"]["serial"], "address": u["data"]["site"]},
                                  parent=u, system=True, extra={"centre_id": v["centre_id"], "centre_name": v["centre_id_label"], "skill": c["rec"].get("skill")})
        await system_transition(u, "job_created", f"Job {job['ref']} created", c["user"], {"job_id": job["id"], "job_ref": job["ref"]})
        n += 1
    if not n:
        fail(409, "No open units without jobs.")


async def p_case_verify(c):
    c["set"].update({"purchase_evidence": f"{c['vals']['proof']} submitted - pending verification", "serial": c["vals"].get("serial")})


async def p_case_sale(c):
    c["set"]["sale_verified"] = c["vals"]["match"] == "Matches invoice"


async def _deps_or_fail(rec):
    deps = await pending_dependencies(rec)
    if deps:
        fail(409, "Closure blocked by pending work. Complete or cancel the linked items first.", code="closure_blocked", blocking=deps)


async def p_case_resolve(c):
    await _deps_or_fail(c["rec"])
    c["set"]["resolved_at"] = iso()


async def p_case_close(c):
    await _deps_or_fail(c["rec"])
    if not c["vals"]["outcome"].startswith(("Rejected", "No fault")):
        n = await db.evidence.count_documents({"root_id": c["rec"]["id"], "scan_state": "clean"})
        if n < 1:
            fail(422, "Evidence-based closure requires at least one clean evidence item on the case or its jobs.", code="evidence_required")
    c["set"].update({"closed_at": iso(), "closure_outcome": c["vals"]["outcome"]})


async def p_case_supervised(c):
    pass


async def a_case_supervised(c):
    await create_approval(c["user"], "supervised_closure", c["rec"], 0, f"{c['vals']['attempts']} contact attempts via {c['vals']['channels_tried']}", assignee_id=c["vals"]["approver_id"])


async def p_case_cconfirm(c):
    await _deps_or_fail(c["rec"])
    c["set"].update({"csat": int(c["vals"]["rating"]), "closed_at": iso(), "closure_outcome": "Resolved - customer confirmed"})


async def a_notify_owner(c):
    r = c["rec"]
    await notify.to_users([r.get("owner_id")], f"{r['ref']}: {c['a']['label']}", next(iter(c["vals"].values()), "") if c["vals"] else "", r, "pending")


async def p_case_reconcile(c):
    open_units = await db.records.find({"type": "unit", "parent_id": c["rec"]["id"], "state": {"$ne": "resolved"}}, {"_id": 0, "id": 1, "ref": 1, "type": 1, "title": 1, "state": 1}).to_list(500)
    if open_units:
        fail(409, "Bulk case cannot close while units remain unresolved.", code="closure_blocked", blocking=[{**u, "state": state_info("unit", u["state"])["label"]} for u in open_units])
    await _deps_or_fail(c["rec"])
    c["set"].update({"closed_at": iso(), "closure_outcome": "Bulk reconciliation confirmed"})


async def p_case_reopen(c):
    days = await get_config("reopen_window_days", 30)
    closed = c["rec"].get("closed_at")
    if closed and (now() - parse_dt(closed)).days > int(days):
        fail(409, f"The reopening window ({days} days, placeholder policy) has passed. Please request a decision review instead.", code="window_passed")
    c["set"].update({"reopen_count": c["rec"].get("reopen_count", 0) + 1, "closed_at": None, "reopened_at": iso(), "proposed_owner_id": c["rec"].get("owner_id"), "proposed_owner_name": c["rec"].get("owner_name")})


async def a_case_reopen(c):
    await notify.to_users([c["rec"].get("owner_id")], f"{c['rec']['ref']} reopened", c["vals"]["unresolved"], c["rec"], "urgent")
    await sla.start(c["rec"], "resolution")


async def a_case_appeal(c):
    v = c["vals"]
    if await db.records.find_one({"type": "appeal", "root_id": c["rec"]["id"], "state": {"$nin": TERMINAL["appeal"]}}):
        fail(409, "An appeal is already open for this case.")
    await _child(c, "appeal", "appeal", {**v, "case_id": c["rec"]["id"]})


async def a_case_call(c):
    await db.communications.insert_one({"id": new_id("com"), "record_id": c["rec"]["id"], "root_id": c["rec"]["id"], "ref": c["rec"]["ref"], "template": "manual_call", "channel": "call",
                                        "direction": c["vals"]["direction"].lower(), "recipient": c["rec"].get("customer_name"), "subject": "Manual call log", "body": c["vals"]["summary"],
                                        "state": "logged_manually", "at": iso(), "actor": c["user"]["name"], "dedupe_key": new_id("call"), "visibility": "internal"})


# ---- contact ----
async def p_contact_open(c):
    c["set"].update({"owner_id": c["user"]["id"], "owner_name": c["user"]["name"]})


async def a_contact_register(c):
    v = {k: x for k, x in c["vals"].items() if not k.endswith("_label")}
    case = await create_record(c["user"], "case", "support_ticket", v, system=False)
    await db.records.update_one({"id": c["rec"]["id"]}, {"$set": {"case_id": case["id"], "case_ref": case["ref"]}})
    await log_event(case, c["user"], "contact_linked", f"Registered from contact {c['rec']['ref']} ({c['rec']['data'].get('channel')})", None, None)


async def a_contact_link(c):
    case = await find(c["vals"]["case_id"])
    await db.records.update_one({"id": c["rec"]["id"]}, {"$set": {"case_id": case["id"], "case_ref": case["ref"]}})
    await log_event(case, c["user"], "contact_linked", f"New contact {c['rec']['ref']} recorded on existing case", None, None, {"note": c["vals"]["note"]})
    await notify.to_users([case.get("owner_id")], f"New contact on {case['ref']}", c["vals"]["note"], case)


# ---- task ----
async def p_task_dep(c):
    dep = c["rec"]["data"].get("depends_on")
    if dep:
        d = await find(dep)
        if d and d["state"] != "done":
            fail(409, f"Dependency {d['ref']} must be completed first.", code="dependency_pending")


# ---- job ----
async def p_job_allocate(c):
    r, v = c["rec"], c["vals"]
    tech = await db.users.find_one({"id": v["technician_id"], "roles": "R06"}, {"_id": 0})
    if not tech:
        fail(422, "Choose an active technician.")
    if r.get("centre_id") and tech.get("centre_id") != r["centre_id"]:
        fail(409, "Technician belongs to a different service centre. Request support or reassignment.", code="capacity")
    if r.get("skill") and r["skill"] not in (tech.get("skills") or []):
        fail(409, f"{tech['name']} does not hold the '{r['skill']}' skill. Request support or reassignment.", code="skills")
    cap = (await get_config("capacity", {}) or {}).get("technician_open_jobs", 6)
    load = await db.records.count_documents({"type": "job", "technician_id": tech["id"], "state": {"$nin": TERMINAL["job"] + ["created", "completed"]}})
    if load >= cap:
        fail(409, f"{tech['name']} is at capacity ({load}/{cap} open jobs). Request support or reassignment.", code="capacity")
    c["set"].update({"technician_id": tech["id"], "technician_name": tech["name"]})


async def a_job_allocate(c):
    await notify.to_users([c["vals"]["technician_id"]], f"New job assigned {c['rec']['ref']}", c["rec"]["title"], c["rec"])
    await notify.customer(c["rec"], "technician_assigned", actor=c["user"])


async def a_job_support(c):
    r = c["rec"]
    esc = await _child(c, "escalation", "escalation", {"reason": "Capacity or skill gap", "summary": c["vals"]["reason"]}, {"title": f"Capacity support - {r['ref']}"})
    await notify.to_roles(["R09"], f"Centre requests support {esc['ref']}", c["vals"]["reason"], esc, "urgent", region=r.get("region"))


async def p_job_centre(c):
    c["set"].update({"centre_id": c["vals"]["centre_id"], "centre_name": c["vals"]["centre_id_label"], "technician_id": None, "technician_name": None})


async def p_job_appt(c):
    v = c["vals"]
    if parse_dt(v["window_end"]) <= parse_dt(v["window_start"]):
        fail(422, "Please correct the highlighted fields.", fields={"window_end": "Window end must be after start"})
    c["set"]["appointment"] = {"start": v["window_start"], "end": v["window_end"]}


async def p_job_dispatch(c):
    if c["rec"].get("parts_pending"):
        fail(409, "Parts are not ready for this job. Dispatch is blocked until delivery is confirmed.", code="parts_pending")


async def p_job_diag(c):
    rec = c["rec"]
    rv = c["vals"]["recommended"]
    serial = rec["data"].get("serial") or c["vals"]["product_serial"]
    repeat = await db.records.count_documents({"type": "job", "data.serial": serial, "state": "accepted", "id": {"$ne": rec["id"]}}) if serial else 0
    c["set"].update({"approval_required": rv in ("Repair - chargeable", "Replace unit", "Refer to supervisor"), "repeat_count": repeat, "diagnosis": c["vals"]["cause"]})
    c["repeat"] = repeat


async def a_job_diag(c):
    if c["repeat"] >= 1 or c["vals"]["recommended"] == "Refer to supervisor":
        await _child(c, "tech_review", "review", {"question": "Repeat failure" if c["repeat"] else "Technician referral", "diagnosis": c["vals"]["cause"], "repeat_count": c["repeat"]},
                     {"title": f"{'Repeat failure' if c['repeat'] else 'Referral'} review - {c['rec']['ref']}", "repeat_count": c["repeat"]})
        await notify.to_roles(["R08"], f"Technical review needed for {c['rec']['ref']}", c["vals"]["cause"], c["rec"])


async def p_job_parts(c):
    part = await db.parts.find_one({"sku": c["vals"]["part_sku"]}, {"_id": 0})
    mid = c["rec"].get("model_id")
    if mid and mid not in part.get("compatible_models", []):
        fail(422, "Please correct the highlighted fields.", fields={"part_sku": f"{part['sku']} is not compatible with {c['rec'].get('model')}"})
    c["set"]["parts_pending"] = True


async def a_job_parts(c):
    v = c["vals"]
    req = await _child(c, "requisition", "requisition", {"part_sku": v["part_sku"], "part": v["part_sku_label"], "quantity": v["quantity"], "required_by": v["required_by"], "reason": v["reason"]},
                       {"title": f"{v['part_sku_label']} x{v['quantity']} - {c['rec']['ref']}", "technician_id": c["rec"].get("technician_id"), "job_ref": c["rec"]["ref"]})
    await notify.to_roles(["R12"], f"Parts requisition {req['ref']}", req["title"], req)


async def p_job_estimate(c):
    v = c["vals"]
    total = float(v["labour"]) + float(v["parts_cost"])
    c["set"].update({"estimate": {"labour": v["labour"], "parts": v["parts_cost"], "total": total, "chargeable": v["chargeable"]},
                     "estimate_state": "pending" if v["chargeable"] == "Yes" and not c["rec"].get("charge_waived") else "not_required", "approval_required": True})
    c["total"] = total


async def a_job_estimate(c):
    await create_approval(c["user"], "repair_plan", c["rec"], c["total"], c["vals"]["proposal"])
    if c["rec"].get("estimate_state") == "pending":
        await notify.customer(c["rec"], "approval_request", f"Repair estimate of INR {c['total']:.0f} awaits your acceptance.", actor=c["user"])


async def p_job_accept_est(c):
    r = c["rec"]
    if r.get("estimate_state") != "pending":
        fail(409, "There is no estimate awaiting your acceptance.")
    c["set"]["estimate_state"] = "accepted"
    to_if(c, r.get("repair_authorised") and r["state"] == "awaiting_approval", "authorised")


async def p_job_decline_est(c):
    c["set"].update({"estimate_state": "declined", "repair_authorised": False})


async def a_job_decline_est(c):
    root = await find(c["rec"].get("root_id"))
    if root:
        await notify.to_users([root.get("owner_id")], f"Estimate declined on {c['rec']['ref']}", c["vals"]["reason"], root, "urgent")


async def p_job_repair(c):
    r = c["rec"]
    if r.get("approval_required") and not r.get("repair_authorised"):
        fail(409, "This repair requires authorisation before it can proceed.", code="approval_required")
    if (r.get("estimate") or {}).get("chargeable") == "Yes" and r.get("estimate_state") not in ("accepted", "not_required"):
        fail(409, "The customer has not accepted the repair estimate.", code="estimate_pending")
    if r.get("parts_pending"):
        fail(409, "Required parts have not been delivered yet.", code="parts_pending")


async def p_job_tests(c):
    v = c["vals"]
    ok = v["functional"] == "Pass" and v["insulation"] == "Pass" and v["earth"] != "Fail"
    if not ok:
        c["to"] = "diagnosed"
        c["set"].update({"tests_failed_count": c["rec"].get("tests_failed_count", 0) + 1, "repair_authorised": c["rec"].get("repair_authorised", False)})
    c["ok"] = ok


async def a_job_tests(c):
    if not c["ok"]:
        await _child(c, "tech_review", "review", {"question": "Failed functional or safety test", "diagnosis": c["vals"]["readings"]}, {"title": f"Failed test review - {c['rec']['ref']}"})
        await notify.to_roles(["R08"], f"Failed test on {c['rec']['ref']}", "Further diagnosis / supervisor review required", c["rec"], "urgent")


async def p_job_accept(c):
    r = c["rec"]
    c["set"].update({"first_time_fix": not r.get("tests_failed_count") and not r.get("missed_count") and not r.get("returned_count"), "completed_at": iso()})


async def a_job_accept(c):
    r = c["rec"]
    root = await find(r.get("root_id"))
    if root:
        await log_event(root, c["user"], "job_accepted", f"Job {r['ref']} accepted by service centre", None, None)
        await notify.to_users([root.get("owner_id")], f"Job {r['ref']} accepted", "Verify the outcome with the customer.", root)
    if r.get("parent_type") == "unit":
        u = await find(r["parent_id"])
        if u and u["state"] != "resolved":
            await system_transition(u, "resolved", f"Unit job {r['ref']} accepted", c["user"])


async def p_job_return(c):
    c["set"]["returned_count"] = c["rec"].get("returned_count", 0) + 1


async def a_job_return(c):
    await notify.to_users([c["rec"].get("technician_id")], f"Job {c['rec']['ref']} returned for correction", c["vals"]["deficiency"], c["rec"], "urgent")


async def p_job_missed(c):
    v = c["vals"]
    c["set"].update({"missed_count": c["rec"].get("missed_count", 0) + 1, "technician_id": v["recovery_technician_id"], "technician_name": v["recovery_technician_id_label"], "appointment": None})


# ---- technical review ----
async def a_tr_inspect(c):
    job = await find(c["rec"]["parent_id"]) if c["rec"].get("parent_type") == "job" else None
    if job and job["state"] in ("awaiting_approval", "authorised", "repaired"):
        await system_transition(job, "diagnosed", f"Further inspection requested by {c['user']['name']}", c["user"], {"repair_authorised": False})
    if job:
        await notify.to_users([job.get("technician_id")], f"Further inspection requested on {job['ref']}", c["vals"]["inspection_required"], job, "urgent")


async def p_tr_decide(c):
    v = c["vals"]
    if v["decision"] == "Refer to higher authority":
        c["to"] = "referred"
        return
    m = (await authority())["repair_plan"]
    lim = m["limits"].get(c["user"]["active_role"])
    if lim is not None and float(v["amount"]) > float(lim):
        fail(409, f"INR {v['amount']} is outside your delegated authority (INR {lim}). Refer to a higher approver.", code="outside_authority")


async def a_tr_decide(c):
    r, v = c["rec"], c["vals"]
    job = await find(r["parent_id"]) if r.get("parent_type") == "job" else None
    if not job:
        return
    if c["to"] == "referred":
        await create_approval(c["user"], "repair_plan", job, v["amount"], v["rationale"], {"review_id": r["id"]}, after_role="R08")
    else:
        await apply_approval(c["user"], {"approval_type": "repair_plan", "subject_id": job["id"], "ref": r["ref"], "payload": {}, "root_id": r.get("root_id"), "title": r["title"]}, True)


# ---- approval ----
async def p_ap_approve(c):
    r, role = c["rec"], c["user"]["active_role"]
    m = (await authority()).get(r["approval_type"], {"limits": {}})
    if role not in m.get("limits", {}):
        fail(403, "Your role holds no delegated authority for this approval type.", code="outside_authority")
    lim = m["limits"][role]
    if lim is not None and float(r.get("amount") or 0) > float(lim):
        fail(409, f"Amount INR {r.get('amount')} exceeds your delegated limit of INR {lim}. Refer to a higher authority.", code="outside_authority")
    c["set"].update({"decided_by": c["user"]["id"], "decided_by_name": c["user"]["name"], "decided_at": iso()})


async def a_ap_approve(c):
    await apply_approval(c["user"], c["rec"], True)


async def p_ap_reject(c):
    c["set"].update({"decided_by": c["user"]["id"], "decided_by_name": c["user"]["name"], "decided_at": iso(), "rejection_reason": c["vals"]["reason"]})


async def a_ap_reject(c):
    await apply_approval(c["user"], c["rec"], False)


async def p_ap_refer(c):
    r = c["rec"]
    nxt = await role_for_amount(r["approval_type"], r.get("amount"), r["required_role"])
    if not nxt:
        fail(409, "No higher authority is configured for this approval type.")
    c["set"].update({"required_role": nxt, "assignee_id": None, "referred_from": r["required_role"]})
    c["next_role"] = nxt


async def a_ap_refer(c):
    await notify.to_roles([c["next_role"]], f"Approval referred to you: {c['rec']['ref']}", c["rec"]["title"], c["rec"], "pending")


# ---- warranty ----
async def p_w_check(c):
    if c["vals"]["evidence_sufficient"] == "No":
        if not c["vals"].get("clarification"):
            fail(422, "Please correct the highlighted fields.", fields={"clarification": "Describe the clarification required"})
        c["to"] = "clarification_requested"
    c["set"]["purchase_verified"] = c["vals"]["purchase_verified"]


async def a_w_check(c):
    if c["to"] == "clarification_requested":
        await notify.customer(c["rec"], "evidence_request", c["vals"]["clarification"], actor=c["user"])


async def p_w_decide(c):
    v = c["vals"]
    lim = (await authority())["warranty_exception"]["limits"].get("R11")
    if v["coverage"] == "Covered - exception requested" or (v["coverage"] == "Covered" and lim is not None and float(v.get("amount") or 0) > lim):
        c["to"] = "exception_approval"
    c["set"]["coverage"] = v["coverage"]


async def a_w_decide(c):
    if c["to"] == "exception_approval":
        await create_approval(c["user"], "warranty_exception", c["rec"], c["vals"].get("amount") or 0, c["vals"]["reasons"])


async def a_w_explain(c):
    root = await find(c["rec"].get("root_id"))
    if root:
        await notify.to_users([root.get("owner_id")], f"Warranty decision on {root['ref']}: {c['rec'].get('coverage')}", c["vals"]["explanation"], root)


async def a_w_dispute(c):
    root = await find(c["rec"].get("root_id"))
    if root:
        await create_record(c["user"], "appeal", "appeal", {"case_id": root["id"], "original_decision": "Warranty decision", "reason": c["vals"]["grounds"], "requested_outcome": "Re-assessment"},
                            parent=root, system=True)


# ---- requisition ----
async def p_req_validate(c):
    if c["vals"]["valid"] == "Reject":
        c["to"] = "rejected"


async def a_req_validate(c):
    if c["to"] == "rejected":
        job = await find(c["rec"]["parent_id"])
        if job:
            await db.records.update_one({"id": job["id"]}, {"$set": {"parts_pending": False}})
            await notify.to_users([job.get("technician_id")], f"Requisition {c['rec']['ref']} rejected", c["vals"].get("note", ""), job, "urgent")


async def p_req_reserve(c):
    v, sku = c["vals"], c["rec"]["data"]["part_sku"]
    q = int(v["quantity"])
    res = await db.stock.update_one({"sku": sku, "warehouse_id": v["warehouse_id"], "$expr": {"$gte": [{"$subtract": ["$on_hand", "$reserved"]}, q]}}, {"$inc": {"reserved": q}})
    if res.modified_count == 0:
        fail(409, "Insufficient available stock in this warehouse. Transfer or procure stock.", code="no_stock")
    await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "reserve", "sku": sku, "warehouse_id": v["warehouse_id"], "qty": q, "ref": c["rec"]["ref"]})
    c["set"].update({"warehouse_id": v["warehouse_id"], "warehouse_name": v["warehouse_id_label"], "reserved_qty": q})


async def p_req_receive(c):
    v, sku = c["vals"], c["rec"]["data"]["part_sku"]
    await db.stock.update_one({"sku": sku, "warehouse_id": v["warehouse_id"]}, {"$inc": {"on_hand": int(v["quantity"])}, "$setOnInsert": {"reserved": 0}}, upsert=True)
    await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "receipt", "sku": sku, "warehouse_id": v["warehouse_id"], "qty": int(v["quantity"]), "ref": c["rec"]["ref"]})


async def p_req_dispatch(c):
    r = c["rec"]
    q = r.get("reserved_qty", 1)
    await db.stock.update_one({"sku": r["data"]["part_sku"], "warehouse_id": r["warehouse_id"]}, {"$inc": {"on_hand": -q, "reserved": -q}})
    await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "issue", "sku": r["data"]["part_sku"], "warehouse_id": r["warehouse_id"], "qty": -q, "ref": r["ref"]})
    c["set"]["shipment"] = {"carrier": c["vals"]["carrier"], "tracking": c["vals"]["tracking"], "eta": c["vals"]["eta"]}


async def p_req_deliver(c):
    to_if(c, c["vals"]["delivered"] == "No", "delivery_exception")


async def a_req_deliver(c):
    if c["to"] != "delivered":
        return
    job = await find(c["rec"]["parent_id"])
    if not job:
        return
    pending = await db.records.count_documents({"type": "requisition", "parent_id": job["id"], "state": {"$in": ["requested", "validated", "awaiting_stock", "reserved", "dispatched", "delivery_exception"]}})
    if not pending:
        st = {"parts_pending": False, "parts_ready": True}
        if job["state"] == "awaiting_parts":
            await system_transition(job, "authorised" if job.get("repair_authorised") else "diagnosed", "All requested parts delivered", c["user"], st)
        else:
            await db.records.update_one({"id": job["id"]}, {"$set": st})
        await notify.to_users([job.get("technician_id")], f"Parts delivered for {job['ref']}", c["rec"]["title"], job)


async def p_req_usage(c):
    r = c["rec"]
    if c["vals"]["outcome"] == "Returned unused":
        c["to"] = "returned"
        q = r.get("reserved_qty", 1)
        await db.stock.update_one({"sku": r["data"]["part_sku"], "warehouse_id": r.get("warehouse_id")}, {"$inc": {"on_hand": q}})
        await db.movements.insert_one({"id": new_id("mov"), "at": iso(), "type": "return", "sku": r["data"]["part_sku"], "warehouse_id": r.get("warehouse_id"), "qty": q, "ref": r["ref"]})


async def a_req_usage(c):
    if c["vals"]["outcome"] == "Defective part returned":
        await _child(c, "return", "return", {"item": c["rec"]["data"]["part"], "batch": c["vals"].get("part_serial", ""), "source_ref": c["rec"]["ref"], "safety_hold": "Yes - quarantine" if c["rec"].get("safety_flag") else "No"},
                     {"title": f"Defective return - {c['rec']['data']['part']}", "quarantine": bool(c["rec"].get("safety_flag"))})


async def p_ret_receipt(c):
    to_if(c, c["rec"].get("quarantine"), "quarantined")


async def a_rpl_collect(c):
    if c["vals"]["old_unit"] == "Collected":
        await _child(c, "return", "return", {"item": f"Old unit {c['rec']['data'].get('old_serial', '')}", "batch": c["rec"]["data"].get("old_serial", ""), "source_ref": c["rec"]["ref"], "safety_hold": "No"},
                     {"title": f"Collected old unit - {c['rec']['ref']}"})


# ---- settlement ----
async def p_stl_validate(c):
    r, v = c["rec"], c["vals"]
    ap = await find(r.get("approval_id")) if r.get("approval_id") else None
    reason = None
    if not ap or ap["state"] != "approved":
        reason = "No approved authorisation linked to this settlement"
    elif abs(float(v["approved_amount"]) - float(r.get("amount") or 0)) > 0.009:
        reason = f"Entered amount INR {v['approved_amount']} does not match approved amount INR {r.get('amount')}"
    if reason:
        c["to"] = "discrepancy"
        c["set"]["discrepancy"] = reason
    else:
        c["set"].update({"recipient_verified": True, "beneficiary_reference": v["beneficiary_reference"], "account_ending": v["account_ending"], "discrepancy": None})


async def p_stl_submit(c):
    r = c["rec"]
    if r.get("executed_at"):
        fail(409, "This settlement has already been executed. Duplicate execution prevented.", code="duplicate_execution")
    attempt = r.get("attempts", 0) + 1
    res = await payments.submit(r, f"{r['id']}:{attempt}")
    c["set"].update({"attempts": attempt, "instruction_ref": res["reference"], "adapter": payments.ADAPTER_NAME, "submitted_at": iso()})


async def p_stl_status(c):
    r = c["rec"]
    out = await payments.status(r)
    c["to"] = {"executed": "executed", "failed": "failed", "unknown": "outcome_unknown", "pending": r["state"]}[out["state"]]
    c["set"]["provider_status"] = out
    if out["state"] == "executed":
        c["set"].update({"executed_at": iso(), "provider_ref": out["provider_ref"], "executed_amount": r.get("amount")})


async def a_stl_status(c):
    if c["to"] == "executed":
        root = await find(c["rec"].get("root_id"))
        if root:
            await notify.to_users([root.get("owner_id")], f"Settlement {c['rec']['ref']} executed (simulated adapter)", f"Provider ref {c['set']['provider_ref']}", root)
            await notify.customer(root, "status_update", f"Your approved settlement {c['rec']['ref']} has been recorded as executed. (Development environment: simulated payment adapter - no real funds moved.)", actor=c["user"])


async def p_stl_reconcile(c):
    r = c["rec"]
    if abs(float(c["vals"]["ledger_amount"]) - float(r.get("executed_amount") or r.get("amount") or 0)) > 0.009:
        fail(409, "Ledger amount differs from the executed amount. Investigate before reconciling.", code="reconciliation_mismatch")
    c["set"]["reconciled_at"] = iso()


async def a_stl_reconcile(c):
    root = await find(c["rec"].get("root_id"))
    if root:
        await notify.to_users([root.get("owner_id")], f"Settlement {c['rec']['ref']} reconciled", "Case may proceed to outcome verification.", root, "done")


async def a_stl_correction(c):
    await create_approval(c["user"], "settlement_correction", c["rec"], c["vals"]["amount"], c["vals"]["reason"])


# ---- incident / capa ----
async def p_inc_triage(c):
    to_if(c, c["vals"]["urgent"] == "No", "investigation")
    c["set"]["severity"] = c["vals"]["severity"]


async def p_inc_link(c):
    refs = [x.strip() for x in (c["vals"].get("case_refs") or "").split(",") if x.strip()]
    found = await db.records.find({"type": "case", "ref": {"$in": refs}}, {"_id": 0, "id": 1, "ref": 1}).to_list(100)
    missing = set(refs) - {f["ref"] for f in found}
    if missing:
        fail(422, "Please correct the highlighted fields.", fields={"case_refs": f"Unknown references: {', '.join(missing)}"})
    c["set"]["related_cases"] = list({x["ref"]: x for x in (c["rec"].get("related_cases") or []) + found}.values())


async def a_inc_capa(c):
    v = c["vals"]
    await _child(c, "capa", v["kind"].lower(), {**v}, {"title": v["title"], "assignee_id": v["assignee_id"], "assignee_name": v["assignee_id_label"], "due": v["due"]})
    await notify.to_users([v["assignee_id"]], f"Corrective action assigned on {c['rec']['ref']}", v["title"], c["rec"])


async def p_inc_req_verify(c):
    open_ = await db.records.count_documents({"type": "capa", "parent_id": c["rec"]["id"], "state": {"$nin": ["implemented", "verified"]}})
    if open_ or not await db.records.count_documents({"type": "capa", "parent_id": c["rec"]["id"]}):
        fail(409, "All corrective actions must be implemented before the effectiveness check.", code="dependency_pending")


async def p_inc_verify(c):
    to_if(c, c["vals"]["effective"] == "No", "capa_in_progress")


async def a_inc_verify(c):
    if c["to"] == "capa_in_progress":
        async for cp in db.records.find({"type": "capa", "parent_id": c["rec"]["id"], "state": {"$in": ["implemented", "verified"]}}, {"_id": 0}):
            await system_transition(cp, "ineffective", "Incident effectiveness check failed - revise action", c["user"])


async def p_capa_verify(c):
    to_if(c, c["vals"]["effective"] == "No", "ineffective")


# ---- channel ----
async def a_chd_clarify(c):
    case = await find(c["rec"].get("parent_id")) if c["rec"].get("parent_type") == "case" else None
    if case and case["state"] in ("registered", "awaiting_owner", "in_progress"):
        await system_transition(case, "evidence_requested", f"Channel support requested evidence ({c['rec']['ref']})", c["user"], cust=True)
    if case:
        await notify.customer(case, "evidence_request", c["vals"]["questions"], actor=c["user"])


async def p_chd_decide(c):
    v = c["vals"]
    if v["decision"] == "Reject claim":
        c["to"] = "rejected"
        return
    lim = (await authority())["credit_note"]["limits"].get("R15")
    if float(v.get("amount") or 0) and lim is not None and float(v["amount"]) > lim:
        c["to"] = "referred"


async def a_chd_decide(c):
    v, r, u = c["vals"], c["rec"], c["user"]
    case = await find(r.get("parent_id")) if r.get("parent_type") == "case" else None
    if c["to"] == "referred":
        await create_approval(u, "channel_decision", r, v["amount"], v["reason"])
    elif c["to"] == "rejected":
        if case and case["state"] not in TERMINAL["case"]:
            await system_transition(case, "closed", "Claim not approved - reasoned decision issued", u, {"closed_at": iso(), "closure_outcome": "Rejected - as per decision"}, cust=True)
            await notify.customer(case, "status_update", f"Claim decision: not approved. Reason: {v['reason']}. You may request a review of this decision.", actor=u)
    elif float(v.get("amount") or 0) > 0:
        ap = await create_record(u, "approval", "credit_note", {"approval_type": "credit_note", "amount": v["amount"], "summary": v["reason"]}, parent=r, system=True,
                                 extra={"approval_type": "credit_note", "subject_id": (case or r)["id"], "subject_ref": (case or r)["ref"], "subject_type": (case or r)["type"], "amount": v["amount"],
                                        "required_role": "R15", "requested_by": u["id"], "requested_by_name": u["name"], "state": "approved", "decided_by": u["id"], "decided_by_name": u["name"],
                                        "decided_at": iso(), "title": f"Credit note within channel authority - {r['ref']}", "payload": {}})
        await apply_approval(u, ap, True)
        if case:
            await notify.customer(case, "status_update", f"Claim approved for INR {v['amount']}. A credit settlement has been queued.", actor=u)


async def a_chd_recovery(c):
    v = c["vals"]
    await _child(c, "task", "task", {"task_type": "Dealer coordination", "team": "Channel support", "mandatory": "Yes"},
                 {"title": v["title"], "assignee_id": v["assignee_id"], "assignee_name": v["assignee_id_label"], "due": v["due"], "team": "Channel support"})


async def p_chd_status(c):
    to_if(c, c["vals"]["completed"] == "No", "follow_up")


# ---- appeal ----
async def p_apl_reviewer(c):
    rid = c["vals"]["reviewer_id"]
    root = c["rec"].get("root_id")
    involved = set(await db.events.distinct("actor_id", {"root_id": root, "record_id": {"$ne": c["rec"]["id"]}})) if root else set()
    if rid in involved or rid == c["rec"].get("customer_user_id"):
        fail(409, "Reviewer is not independent of the original decision. Reassign to an independent reviewer.", code="not_independent")
    c["set"].update({"reviewer_id": rid, "reviewer_name": c["vals"]["reviewer_id_label"], "conflict_check": "Passed - no involvement in original case"})


async def p_apl_decide(c):
    if c["vals"]["decision"] != "Uphold original decision":
        c["to"] = "awaiting_reversal_approval"
        c["skip_notify"] = True
    c["set"]["decision"] = c["vals"]["decision"]


async def a_apl_decide(c):
    v = c["vals"]
    if c["to"] == "awaiting_reversal_approval":
        await create_approval(c["user"], "appeal_reversal", c["rec"], v.get("amount") or 0, v["reasons"], {"remedy": v.get("remedy"), "decision": v["decision"]})


async def a_apl_remedy(c):
    v = c["vals"]
    await _child(c, "task", "task", {"task_type": "Appeal remedy", "mandatory": "Yes"}, {"title": f"Remedy: {v['note'][:60]}", "assignee_id": v["assignee_id"], "assignee_name": v["assignee_id_label"], "due": v["due"]})


async def p_apl_verify(c):
    open_ = await db.records.find({"parent_id": c["rec"]["id"], "type": {"$in": ["task", "settlement"]}, "state": {"$nin": TERMINAL["task"] + TERMINAL["settlement"]}}, {"_id": 0, "ref": 1, "type": 1, "id": 1, "state": 1}).to_list(50)
    if open_:
        fail(409, "Remedy actions are still open.", code="closure_blocked", blocking=open_)


# ---- escalation / mgmt ----
async def p_esc_assign(c):
    c["set"].update({"assignee_id": c["vals"]["assignee_id"], "assignee_name": c["vals"]["assignee_id_label"]})


async def a_esc_assign(c):
    await notify.to_users([c["vals"]["assignee_id"]], f"Recovery owner for {c['rec']['ref']}", c["vals"]["action_plan"], c["rec"], "urgent")


async def p_esc_coord(c):
    if c["vals"]["within_delegation"].startswith("No") and not c["vals"].get("executive_reference"):
        fail(422, "Please correct the highlighted fields.", fields={"executive_reference": "Executive decision reference is required outside delegated authority"})
    c["set"]["level"] = "national"


async def a_esc_national(c):
    await notify.to_roles(["R10"], f"Escalation referred to national: {c['rec']['ref']}", c["vals"]["summary"], c["rec"], "urgent")


async def p_esc_result(c):
    to_if(c, c["vals"]["successful"] == "No", "revision")


async def p_ma_review(c):
    to_if(c, c["vals"]["improvement"] == "No", "revision_required")


# ---- supplier ----
async def p_sup_lines(c):
    lines, errs = [], []
    for i, ln in enumerate([x for x in c["vals"]["lines"].splitlines() if x.strip()], 1):
        p = [x.strip() for x in ln.split(",")]
        try:
            lines.append({"record": p[0], "supplier": float(p[1]), "internal": float(p[2]), "difference": float(p[1]) - float(p[2])})
        except (IndexError, ValueError):
            errs.append(f"Line {i}: expected 'record, supplier value, internal value'")
    if errs:
        fail(422, "Please correct the highlighted fields.", fields={"lines": "; ".join(errs)})
    c["set"]["lines"] = lines


async def p_sup_input(c):
    c["set"].update({"assignee_id": c["vals"]["assignee_id"], "assignee_name": c["vals"]["assignee_id_label"]})


async def a_sup_input(c):
    await notify.to_users([c["vals"]["assignee_id"]], f"Input requested on supplier case {c['rec']['ref']}", c["vals"]["question"], c["rec"])


async def p_sup_decide(c):
    to_if(c, c["vals"]["discrepancy"] == "No", "closed_no_action")


async def a_sup_decide(c):
    if c["to"] != "closed_no_action":
        await create_approval(c["user"], "supplier_correction", c["rec"], c["vals"]["amount"], c["vals"]["explanation"])


async def p_sup_verify(c):
    to_if(c, c["vals"]["complete"] == "No", "follow_up")


# ---- HR ----
async def p_hr_triage(c):
    to_if(c, c["vals"]["urgent_or_specialist"] == "Yes", "designated_referral")


async def p_hr_impl(c):
    to_if(c, c["vals"]["implemented"] == "No", "escalated")


# ---- audit ----
async def p_aud_scope(c):
    v = c["vals"]
    pipeline = [{"$match": {"type": v["record_type"]}}, {"$sample": {"size": int(v["sample_size"])}}, {"$project": {"_id": 0, "id": 1, "ref": 1, "title": 1, "state": 1, "type": 1}}]
    sample = await db.records.aggregate(pipeline).to_list(100)
    if not sample:
        fail(409, "No records available in the selected population.")
    c["set"]["sample"] = sample


async def p_aud_obs(c):
    if c["vals"]["sampled_ref"] not in {s["ref"] for s in c["rec"].get("sample", [])}:
        fail(422, "Please correct the highlighted fields.", fields={"sampled_ref": "Reference is not in the audit sample"})
    c["set"]["observations"] = (c["rec"].get("observations") or []) + [{**c["vals"], "at": iso(), "by": c["user"]["name"]}]


async def p_af_retest(c):
    to_if(c, c["vals"]["effective"] == "No", "remediation")


# ---- configuration ----
async def p_cfg_scope(c):
    to_if(c, c["vals"]["within_scope"] == "No", "clarification")


async def p_cfg_edit(c):
    c["set"]["data.proposed_value"] = c["vals"]["proposed_value"]


async def p_cfg_tests(c):
    import configcheck
    rec = c["rec"]
    results = await configcheck.run(rec["data"]["target"], rec["data"].get("proposed_value"), rec["data"].get("workflow_type"))
    c["set"]["test_results"] = results
    if any(not r["passed"] for r in results):
        c["to"] = "test_failed"


async def a_cfg_release_req(c):
    d = c["rec"]["data"]
    await create_approval(c["user"], "config_release", c["rec"], 0, d.get("change_summary", ""),
                          {"target": cfg_key(c["rec"]), "change_summary": d.get("change_summary"), "proposed_value": d.get("proposed_value")})


async def p_cfg_rollback(c):
    rec = c["rec"]
    cur = await db.config.find_one({"key": cfg_key(rec)}, {"_id": 0, "version": 1})
    if (cur or {}).get("version") != rec.get("released_version"):
        fail(409, "A newer configuration version has been released since this change. Raise a new change request instead of rolling back.", code="stale_rollback")


async def p_cfg_release(c):
    rec = c["rec"]
    if not rec.get("release_approved"):
        fail(409, "Release requires approval by a second administrator.", code="approval_required")
    key = cfg_key(rec)
    cur = await db.config.find_one({"key": key}, {"_id": 0})
    c["set"].update({"previous_version": (cur or {}).get("version"), "released_at": iso()})


def cfg_key(rec):
    t = rec["data"]["target"]
    return f"workflow:{rec['data'].get('workflow_type')}" if t == "workflow" else t


async def a_cfg_release(c):
    from core import set_config
    rec = c["rec"]
    ver = await set_config(cfg_key(rec), rec["data"]["proposed_value"], c["user"], f"Released via {rec['ref']}")
    await db.records.update_one({"id": rec["id"]}, {"$set": {"released_version": ver}})
    await load_overrides()


async def a_cfg_rollback(c):
    from core import set_config
    rec, key = c["rec"], cfg_key(c["rec"])
    prev = rec.get("previous_version")
    doc = await db.config_versions.find_one({"key": key, "version": prev}, {"_id": 0}) if prev else None
    if doc:
        await set_config(key, doc["value"], c["user"], f"Rollback of {rec['ref']}")
    else:
        await db.config.delete_one({"key": key})
    await load_overrides()


# ---- policy ----
async def p_pol_publish(c):
    rv = c["rec"]["data"].get("reviewer_id")
    if rv and rv != c["user"]["id"]:
        fail(403, "Only the designated reviewer can publish this version.", code="not_accountable")
    c["set"]["published_at"] = iso()


async def a_pol_publish(c):
    r = c["rec"]
    d = r["data"]
    if r["subtype"] == "product_model":
        await db.product_models.insert_one({"id": new_id("mdl"), "category": d["category"], "model": d["model"], "components": [x.strip() for x in d["components"].split(",")],
                                            "serial_rule": d["serial_rule"], "skill": d["skill"], "state": "active", "demo": r.get("demo", False), "policy_ref": r["ref"]})
    if r["subtype"] == "warranty_term":
        async for old in db.records.find({"type": "policy", "subtype": "warranty_term", "state": "published", "data.model_id": d.get("model_id"), "data.component": d.get("component"), "id": {"$ne": r["id"]}}, {"_id": 0}):
            await system_transition(old, "superseded", f"Superseded by {r['ref']}", c["user"])


PRE = {
    "case.register_route": p_case_route, "case.escalate_safety": p_case_safety, "case.link_duplicate": p_case_dup, "case.accept_ownership": p_case_accept,
    "case.decline_ownership": p_case_decline, "case.handoff": p_case_handoff, "case.validate_units": p_case_units, "case.submit_verification": p_case_verify,
    "case.confirm_sale": p_case_sale, "case.mark_resolved": p_case_resolve, "case.verify_and_close": p_case_close, "case.customer_confirm": p_case_cconfirm,
    "case.reconcile_bulk": p_case_reconcile, "case.reopen": p_case_reopen,
    "contact.open_contact": p_contact_open, "task.start_task": p_task_dep, "task.complete_task": p_task_dep,
    "job.allocate": p_job_allocate, "job.reassign_centre": p_job_centre, "job.propose_appointment": p_job_appt, "job.confirm_dispatch": p_job_dispatch,
    "job.submit_diagnosis": p_job_diag, "job.request_parts": p_job_parts, "job.submit_estimate": p_job_estimate, "job.customer_accept_estimate": p_job_accept_est,
    "job.customer_decline_estimate": p_job_decline_est, "job.record_repair": p_job_repair, "job.submit_tests": p_job_tests, "job.accept_report": p_job_accept,
    "job.return_for_correction": p_job_return, "job.record_missed_visit": p_job_missed,
    "tech_review.submit_decision": p_tr_decide, "approval.approve": p_ap_approve, "approval.reject": p_ap_reject, "approval.refer": p_ap_refer,
    "warranty.check_evidence": p_w_check, "warranty.record_coverage_decision": p_w_decide,
    "requisition.validate_requisition": p_req_validate, "requisition.reserve_stock": p_req_reserve, "requisition.receive_stock": p_req_receive,
    "requisition.dispatch": p_req_dispatch, "requisition.record_delivery": p_req_deliver, "requisition.record_usage": p_req_usage, "return.record_receipt": p_ret_receipt,
    "settlement.validate_recipient": p_stl_validate, "settlement.submit_instruction": p_stl_submit, "settlement.check_status": p_stl_status, "settlement.reconcile": p_stl_reconcile,
    "incident.triage": p_inc_triage, "incident.link_units": p_inc_link, "incident.request_verification": p_inc_req_verify, "incident.verify_effectiveness": p_inc_verify,
    "capa.verify_capa": p_capa_verify, "channel_dispute.decide_dispute": p_chd_decide, "channel_dispute.record_action_status": p_chd_status,
    "appeal.assign_reviewer": p_apl_reviewer, "appeal.issue_decision": p_apl_decide, "appeal.verify_remedy": p_apl_verify,
    "escalation.assign_recovery_owner": p_esc_assign, "escalation.coordinate_plan": p_esc_coord, "escalation.record_recovery_result": p_esc_result,
    "mgmt_action.review_progress": p_ma_review, "supplier_dispute.reconcile_lines": p_sup_lines, "supplier_dispute.request_input": p_sup_input,
    "supplier_dispute.record_commercial_decision": p_sup_decide, "supplier_dispute.verify_settlement": p_sup_verify,
    "hr_grievance.triage": p_hr_triage, "hr_grievance.record_implementation": p_hr_impl,
    "audit.save_scope": p_aud_scope, "audit.record_observation": p_aud_obs, "audit_finding.record_retest": p_af_retest,
    "config_change.check_scope": p_cfg_scope, "config_change.edit_proposal": p_cfg_edit, "config_change.run_tests": p_cfg_tests, "config_change.release": p_cfg_release, "config_change.rollback": p_cfg_rollback,
    "policy.publish": p_pol_publish,
}
POST = {
    "case.register_route": a_case_route, "case.escalate_safety": a_case_safety, "case.link_duplicate": a_case_dup, "case.decline_ownership": a_case_decline,
    "case.create_service_job": a_case_job, "case.create_linked_task": a_case_task, "case.request_warranty_review": a_case_warranty,
    "case.request_technical_review": a_case_review, "case.record_waiting": a_case_waiting, "case.resume_work": a_case_resume, "case.escalate_case": a_case_escalate,
    "case.request_remedy_approval": a_case_remedy, "case.validate_units": a_case_units, "case.create_unit_jobs": a_case_unit_jobs,
    "case.request_supervised_closure": a_case_supervised, "case.customer_reject": a_notify_owner, "case.provide_information": a_notify_owner,
    "case.add_update": a_notify_owner, "case.reopen": a_case_reopen, "case.request_review": a_case_appeal, "case.log_call": a_case_call,
    "contact.register_case": a_contact_register, "contact.link_to_case": a_contact_link,
    "job.allocate": a_job_allocate, "job.request_support": a_job_support, "job.submit_diagnosis": a_job_diag, "job.request_parts": a_job_parts,
    "job.submit_estimate": a_job_estimate, "job.customer_decline_estimate": a_job_decline_est, "job.submit_tests": a_job_tests, "job.accept_report": a_job_accept,
    "job.return_for_correction": a_job_return,
    "tech_review.request_inspection": a_tr_inspect, "tech_review.submit_decision": a_tr_decide,
    "approval.approve": a_ap_approve, "approval.reject": a_ap_reject, "approval.refer": a_ap_refer,
    "warranty.check_evidence": a_w_check, "warranty.record_coverage_decision": a_w_decide, "warranty.explain_decision": a_w_explain, "warranty.route_dispute": a_w_dispute,
    "requisition.validate_requisition": a_req_validate, "requisition.record_delivery": a_req_deliver, "requisition.record_usage": a_req_usage,
    "replacement.record_collection": a_rpl_collect, "settlement.check_status": a_stl_status, "settlement.reconcile": a_stl_reconcile, "settlement.request_correction": a_stl_correction,
    "incident.plan_capa": a_inc_capa, "incident.verify_effectiveness": a_inc_verify,
    "channel_dispute.request_clarification": a_chd_clarify, "channel_dispute.decide_dispute": a_chd_decide, "channel_dispute.assign_recovery": a_chd_recovery,
    "appeal.issue_decision": a_apl_decide, "appeal.assign_remedy": a_apl_remedy,
    "escalation.assign_recovery_owner": a_esc_assign, "escalation.escalate_national": a_esc_national,
    "supplier_dispute.request_input": a_sup_input, "supplier_dispute.record_commercial_decision": a_sup_decide,
    "config_change.request_release": a_cfg_release_req, "config_change.release": a_cfg_release, "config_change.rollback": a_cfg_rollback,
    "policy.publish": a_pol_publish,
}
