from core import db, fail, audit, get_config

ROLES = {
    "R01": ("Customer / Complainant", "Customer portal", "Own cases only", "CE-005"),
    "R02": ("Dealer / Retailer", "Channel portal", "Own dealership and authorised customer cases", "CE-015"),
    "R03": ("Distributor / Business Account User", "Channel portal", "Authorised organisation and its sites", "CE-021"),
    "R04": ("Customer Support Agent", "Agent workspace", "Assigned queues and authorised customer records", "CE-027"),
    "R05": ("Case Owner / Service Coordinator", "Case workspace", "Assigned cases and delegated queue", "CE-034"),
    "R06": ("Field Technician / Service Engineer", "Technician PWA", "Assigned jobs and necessary case details", "CE-042"),
    "R07": ("Authorised Service Centre Manager", "Service centre workspace", "Assigned centre jobs and staff", "CE-052"),
    "R08": ("Service Supervisor / Technical Reviewer", "Technical workspace", "Assigned technical reviews", "CE-057"),
    "R09": ("Regional Service Manager", "Regional dashboard", "Assigned region and permitted centres", "CE-062"),
    "R10": ("National Service Head", "National dashboard", "National service scope", "CE-067"),
    "R11": ("Warranty and Claims Officer", "Warranty workspace", "Assigned claims with necessary transaction evidence", "CE-071"),
    "R12": ("Spare Parts / Warehouse / Logistics Officer", "Parts workspace", "Authorised warehouses and requests", "CE-076"),
    "R13": ("Finance and Settlement Officer", "Finance workspace", "Authorised settlements and minimal case evidence", "CE-085"),
    "R14": ("Quality and Product Safety Officer", "Quality workspace", "Assigned incidents and approved product analysis", "CE-093"),
    "R15": ("Dealer / Channel Support Manager", "Channel support workspace", "Assigned channel territory or organisations", "CE-100"),
    "R16": ("Grievance and Appeals Officer", "Appeals workspace", "Assigned appeals and permitted original records", "CE-104"),
    "R17": ("Management / Executive Viewer", "Executive dashboard", "Approved aggregated business scope", "CE-109"),
    "R18": ("System Administrator", "Administration console", "Configuration and user administration scope", "CE-115"),
    "R19": ("HR Grievance Officer", "Restricted HR workspace", "Restricted HR cases only", "CE-127"),
    "R20": ("Procurement / Supplier Relations Officer", "Supplier workspace", "Assigned suppliers and purchase references", "CE-131"),
    "R21": ("Auditor", "Audit workspace", "Approved read scope and separate findings", "CE-135"),
}
EXTERNAL = {"R01", "R02", "R03"}
STAFF = [r for r in ROLES if r not in EXTERNAL]
ROLE_MODULE = {"R19": "hr_module", "R20": "supplier_module", "R21": "audit_module"}
TYPE_MODULE = {"hr_grievance": "hr_module", "supplier_dispute": "supplier_module", "audit": "audit_module", "audit_finding": "audit_module"}
ASSIGNED_ROLES = ["R05", "R07", "R08", "R09", "R11", "R12", "R13", "R14", "R15", "R16", "R20"]

# Scope per record type and role. ro = read-only, never holds actions.
ACCESS = {
    "case": {"R01": "own", "R02": "org", "R03": "org", "R04": "all", "R05": "owner", "R06": "tech_case", "R07": "centre", "R08": "all", "R09": "region", "R10": "all", "R11": "all", "R13": "minimal", "R14": "all", "R15": "all", "R16": "all", "R17": "ro", "R21": "ro"},
    "contact": {"R04": "all", "R21": "ro"},
    "task": {"R05": "all", "R09": "region", "R10": "all", "R21": "ro", **{r: "assigned" for r in ["R07", "R08", "R11", "R12", "R13", "R14", "R15", "R16", "R20"]}},
    "job": {"R01": "customer", "R02": "org", "R03": "org", "R05": "all", "R06": "tech", "R07": "centre", "R08": "all", "R09": "region", "R10": "all", "R11": "all", "R12": "all", "R14": "all", "R21": "ro"},
    "unit": {"R03": "org", "R05": "all", "R09": "region", "R10": "all", "R21": "ro"},
    "tech_review": {"R08": "all", "R05": "all", "R06": "tech", "R09": "region", "R10": "all", "R21": "ro"},
    "approval": {**{r: "approver" for r in ["R05", "R07", "R08", "R09", "R11", "R13", "R14", "R15", "R16", "R18", "R20"]}, "R10": "all", "R21": "ro"},
    "warranty": {"R11": "all", "R05": "all", "R01": "own", "R02": "org", "R09": "region", "R10": "all", "R16": "all", "R21": "ro"},
    "requisition": {"R12": "all", "R06": "tech", "R05": "all", "R07": "centre", "R09": "region", "R10": "all", "R21": "ro"},
    "return": {"R12": "all", "R14": "all", "R21": "ro"},
    "replacement": {"R12": "all", "R05": "all", "R01": "customer", "R10": "all", "R21": "ro"},
    "settlement": {"R13": "all", "R05": "all", "R01": "customer", "R02": "org", "R03": "org", "R09": "region", "R10": "all", "R15": "all", "R16": "all", "R21": "ro"},
    "incident": {"R14": "all", "R05": "all", "R09": "region", "R10": "all", "R12": "all", "R17": "ro", "R21": "ro"},
    "capa": {"R14": "all", "R10": "all", "R21": "ro", **{r: "assigned" for r in ["R05", "R08", "R12", "R20"]}},
    "channel_dispute": {"R15": "all", "R02": "org", "R10": "all", "R21": "ro"},
    "appeal": {"R16": "all", "R01": "own", "R02": "org", "R03": "org", "R10": "all", "R21": "ro"},
    "correspondence": {"R16": "all", "R21": "ro"},
    "escalation": {"R09": "region", "R10": "all", "R05": "all", "R07": "centre", "R17": "ro", "R21": "ro", **{r: "assigned" for r in ["R08", "R14"]}},
    "mgmt_action": {"R17": "all", "R10": "all", "R09": "region", **{r: "assigned" for r in ["R05", "R07", "R08", "R11", "R12", "R13", "R14", "R15", "R16", "R20"]}},
    "supplier_dispute": {"R20": "all", "R21": "ro", **{r: "assigned" for r in ["R13", "R14"]}},
    "hr_grievance": {"R19": "hr"},
    "audit": {"R21": "all"},
    "audit_finding": {"R21": "all", **{r: "assigned" for r in ASSIGNED_ROLES + ["R04", "R10", "R18"]}},
    "config_change": {"R18": "all", "R21": "ro"},
    "policy": {"R18": "all", "R10": "all", "R11": "all", "R08": "ro", "R14": "ro", "R21": "ro"},
    "legal_hold": {"R18": "all", "R21": "ro"},
}

MINIMAL_CASE_FIELDS = ["id", "ref", "type", "subtype", "title", "state", "customer_name", "region", "created_at", "owner_name"]


async def flags():
    return await get_config("feature_flags", {}) or {}


async def module_enabled(module):
    return (await flags()).get(module, True)


async def ensure_role_enabled(user):
    mod = ROLE_MODULE.get(user.get("active_role"))
    if mod and not await module_enabled(mod):
        fail(403, f"The {mod.replace('_', ' ')} is disabled by an administrator.", code="module_disabled")


def scope_of(user, rtype):
    return ACCESS.get(rtype, {}).get(user.get("active_role"))


async def scope_query(user, rtype):
    """Mongo filter limiting records of rtype to the user's authorised scope; None = no access."""
    s = scope_of(user, rtype)
    if not s:
        return None
    mod = TYPE_MODULE.get(rtype)
    if mod and not await module_enabled(mod):
        return None
    uid = user["id"]
    if s in ("all", "ro", "minimal"):
        return {}
    if s == "own":
        return {"$or": [{"customer_user_id": uid}, {"created_by": uid}]}
    if s == "customer":
        return {"customer_user_id": uid}
    if s == "org":
        return {"org_id": user.get("org_id") or "__none__"}
    if s == "owner":
        return {"$or": [{"owner_id": uid}, {"proposed_owner_id": uid}, {"owner_id": None}, {"created_by": uid}]}
    if s == "tech":
        return {"$or": [{"technician_id": uid}, {"created_by": uid}]}
    if s == "tech_case":
        ids = await db.records.distinct("root_id", {"type": "job", "technician_id": uid})
        return {"id": {"$in": ids}}
    if s == "centre":
        return {"centre_id": user.get("centre_id") or "__none__"}
    if s == "region":
        return {"region": {"$in": user.get("regions") or []}}
    if s == "assigned":
        return {"$or": [{"assignee_id": uid}, {"owner_id": uid}, {"created_by": uid}, {"action_owner_id": uid}]}
    if s == "approver":
        return {"$or": [{"required_role": user.get("active_role")}, {"requested_by": uid}]}
    if s == "hr":
        if user.get("confidentiality") != "hr":
            return None
        return {"$or": [{"owner_id": uid}, {"created_by": uid}, {"restricted_to": uid}]}
    return None


async def check_view(user, rec, log_denied=True):
    rtype = rec["type"]
    q = await scope_query(user, rtype)
    if q is None:
        if log_denied:
            await audit(user, "access_denied", rtype, rec.get("id"), {"reason": "role scope"}, sensitive=rtype == "hr_grievance", outcome="denied")
        fail(403, "Your role does not have access to this record.", code="forbidden")
    if q:
        coll = db.hr_records if rtype == "hr_grievance" else db.records
        hit = await coll.find_one({"$and": [{"id": rec["id"]}, q]}, {"_id": 0, "id": 1})
        if not hit:
            await audit(user, "access_denied", rtype, rec.get("id"), {"reason": "object scope"}, sensitive=rtype == "hr_grievance", outcome="denied")
            fail(403, "This record is outside your authorised scope.", code="forbidden")
    return scope_of(user, rtype)


def role_matrix():
    rows = []
    for code, (name, ws, scope, home) in ROLES.items():
        rows.append({"role": code, "name": name, "workspace": ws, "scope": scope, "home": home,
                     "optional_module": ROLE_MODULE.get(code),
                     "types": {t: m[code] for t, m in ACCESS.items() if code in m}})
    return rows
