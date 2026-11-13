import os
from datetime import timedelta
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from core import db, now, iso, new_id, log, set_config, get_config
from auth import hash_password
import engine
import sla
from sla import DEFAULT_SLA, DEFAULT_CALENDAR

DEMO_PASSWORD = "Champion@2026"
D = "@demo.champion.test"
SEED_VERSION = 3

CENTRES = [("org_c1", "Mumbai West ASC (Demo)", "West"), ("org_c2", "Pune ASC (Demo)", "West"), ("org_c3", "Delhi North ASC (Demo)", "North"),
           ("org_c4", "Bengaluru ASC (Demo)", "South"), ("org_c5", "Kolkata ASC (Demo)", "East")]
ORGS = [("org_d1", "Sunrise Electronics (Demo dealer)", "dealer", "West"), ("org_d2", "Metro Appliances (Demo dealer)", "dealer", "North"),
        ("org_b1", "Westline Distribution (Demo distributor)", "distributor", "West"), ("org_s1", "Apex Motor Components (Demo supplier)", "supplier", "West"),
        ("org_s2", "Coolflow Pump Supplies (Demo supplier)", "supplier", "South")]
USERS = [
    ("aarav.sharma", "Aarav Sharma", ["R01"], {"customer_id": "cus_1", "regions": ["West"], "phone": "+919800000001"}),
    ("meera.iyer", "Meera Iyer", ["R01"], {"customer_id": "cus_2", "regions": ["South"], "phone": "+919800000002"}),
    ("dealer.sunrise", "Vijay Kulkarni", ["R02"], {"org_id": "org_d1", "regions": ["West"]}),
    ("ops.westline", "Pooja Shetty", ["R03"], {"org_id": "org_b1", "regions": ["West"]}),
    ("priya.nair", "Priya Nair", ["R04"], {"regions": ["West", "North", "South", "East"]}),
    ("rohan.mehta", "Rohan Mehta", ["R05", "R04"], {"regions": ["West", "North", "South", "East"]}),
    ("anjali.rao", "Anjali Rao", ["R05"], {"regions": ["North"]}),
    ("rahul.verma", "Rahul Verma", ["R06"], {"centre_id": "org_c1", "skills": ["Cooling", "Water heating", "Pumps", "Kitchen"]}),
    ("anita.shah", "Anita Shah", ["R06"], {"centre_id": "org_c1", "skills": ["Heating", "Fans", "Kitchen", "Cooling"]}),
    ("sunil.rao", "Sunil Rao", ["R06"], {"centre_id": "org_c2", "skills": ["Cooling", "Pumps", "Heating", "Power backup"]}),
    ("kiran.das", "Kiran Das", ["R06"], {"centre_id": "org_c4", "skills": ["Cooling", "Water heating", "Pumps", "Heating", "Fans", "Kitchen", "Power backup"]}),
    ("kavita.desai", "Kavita Desai", ["R07"], {"centre_id": "org_c1", "regions": ["West"]}),
    ("vikram.joshi", "Vikram Joshi", ["R08"], {"regions": ["West", "South"]}),
    ("neha.kulkarni", "Neha Kulkarni", ["R09"], {"regions": ["West", "South"]}),
    ("amit.singh", "Amit Singh", ["R09"], {"regions": ["North", "East"]}),
    ("arjun.kapoor", "Arjun Kapoor", ["R10"], {}),
    ("sanjay.gupta", "Sanjay Gupta", ["R11"], {}),
    ("farah.khan", "Farah Khan", ["R12"], {}),
    ("deepak.menon", "Deepak Menon", ["R13"], {}),
    ("lakshmi.pillai", "Lakshmi Pillai", ["R14"], {}),
    ("manoj.patil", "Manoj Patil", ["R15"], {"regions": ["West", "North"]}),
    ("sara.thomas", "Sara Thomas", ["R16"], {}),
    ("joseph.dsouza", "Joseph D'Souza", ["R16"], {}),
    ("anil.bose", "Anil Bose", ["R17"], {}),
    ("admin2.ops", "Second Administrator (Demo)", ["R18"], {}),
    ("ritu.malhotra", "Ritu Malhotra", ["R19"], {"confidentiality": "hr"}),
    ("sameer.jain", "Sameer Jain", ["R20"], {}),
    ("nisha.verma", "Nisha Verma", ["R21"], {}),
]
CUSTOMERS = [("cus_1", "Aarav Sharma", "+919800000001", "aarav.sharma" + D, "Flat 12, Bandra West, Mumbai", "400050", "West", "Email"),
             ("cus_2", "Meera Iyer", "+919800000002", "meera.iyer" + D, "22 Indiranagar, Bengaluru", "560038", "South", "Email"),
             ("cus_3", "Imran Qureshi", "+919800000003", "", "Kothrud, Pune", "411038", "West", "SMS"),
             ("cus_4", "Kavya Reddy", "+919800000004", "kavya.reddy" + D, "Karol Bagh, New Delhi", "110005", "North", "WhatsApp"),
             ("cus_5", "Sneha Patil", "+919800000005", "", "Andheri East, Mumbai", "400069", "West", "SMS"),
             ("cus_6", "Farhan Ali", "+919800000006", "farhan.ali" + D, "Salt Lake, Kolkata", "700091", "East", "Email")]
MODELS = [("mdl_cl55", "Air cooler", "CL-55", ["Cooling pump", "Fan motor", "Cooling pads", "Control board"], "Cooling"),
          ("mdl_gy15", "Water heater", "GY-15", ["Heating element", "Thermostat", "Tank", "Safety valve"], "Water heating"),
          ("mdl_wp10", "Pump", "WP-10", ["Impeller", "Capacitor", "Motor winding", "Seal kit"], "Pumps"),
          ("mdl_rh02", "Room heater", "RH-02", ["Heating coil", "Tip-over switch", "Thermostat"], "Heating"),
          ("mdl_cf48", "Fan", "CF-48", ["Capacitor", "Motor", "Blades"], "Fans"),
          ("mdl_mg75", "Kitchen appliance", "MG-75", ["Motor", "Blade assembly", "Jar coupler"], "Kitchen"),
          ("mdl_ic20", "Kitchen appliance", "IC-20", ["Induction coil", "Power board", "Glass top"], "Kitchen"),
          ("mdl_ib150", "Power backup", "IB-150", ["Battery cells", "Charging board"], "Power backup")]
PARTS = [("CL55-PMP", "Cooling pump motor", ["mdl_cl55"], 650), ("CL55-PAD", "Cooling pad set", ["mdl_cl55"], 420), ("GY15-ELM", "Heating element 2kW", ["mdl_gy15"], 780),
         ("GY15-THM", "Thermostat assembly", ["mdl_gy15"], 560), ("WP10-IMP", "Impeller", ["mdl_wp10"], 890), ("WP10-CAP", "Run capacitor 25uF", ["mdl_wp10", "mdl_cf48"], 240),
         ("RH02-COIL", "Heating coil", ["mdl_rh02"], 520), ("MG75-BLD", "Blade assembly", ["mdl_mg75"], 380), ("IC20-COIL", "Induction coil", ["mdl_ic20"], 1450), ("IB150-CHG", "Charging board", ["mdl_ib150"], 1650)]
WAREHOUSES = [("wh_1", "Bhiwandi Central Warehouse (Demo)", "West"), ("wh_2", "Delhi NCR Warehouse (Demo)", "North"), ("wh_3", "Bengaluru Warehouse (Demo)", "South")]
KNOWLEDGE = [
    ("Air cooler low cooling diagnosis checklist", "Check water level, pump operation, pad saturation and fan speed. Record pump current draw and confirm float valve function before recommending pump replacement.", ["R06", "R08", "R04", "R05"], "Cooling"),
    ("Water heater element and thermostat test", "Isolate supply. Measure element resistance and compare with model specification. Test thermostat cut-off and verify safety valve. Never energise with an empty tank.", ["R06", "R08"], "Water heating"),
    ("Insulation resistance and earth continuity tests", "Perform insulation resistance test between live parts and body, and earth continuity from plug earth pin to exposed metal. Record readings and units on the test form.", ["R06", "R08", "R14"], "Safety"),
    ("Handling burning smell, smoke or shock reports", "Advise the customer to switch off and unplug the product if safe. Do not ask the customer to open the product. Escalate immediately to the safety lead and mark the case as a safety incident.", ["R04", "R05", "R14", "all"], "Safety"),
    ("Pump low pressure and noise troubleshooting", "Check suction line for air leaks, impeller wear and capacitor value. Confirm supply voltage under load.", ["R06", "R08"], "Pumps"),
    ("Explaining an evidence request to customers", "State precisely which document or photo is needed, why it is needed and how to upload it. Offer an alternative proof route where policy allows.", ["R04", "R05", "R11", "R15"], "Communication"),
]


def _u(email):
    return email if "@" in email else email + D


async def user(email, role=None):
    u = await db.users.find_one({"email": _u(email)}, {"_id": 0, "password_hash": 0})
    u["active_role"] = role or u["roles"][0]
    return u


async def act(email, rec, key, vals=None, role=None):
    u = await user(email, role)
    await engine.run_action(u, rec["id"], key, vals or {})
    return await engine.find(rec["id"])


async def child(rec, rtype):
    return await db.records.find_one({"parent_id": rec["id"], "type": rtype}, {"_id": 0}, sort=[("created_at", -1)])


async def evidence(rec, email, name, text):
    u = await user(email)
    eid = new_id("evd")
    fid = await AsyncIOMotorGridFSBucket(db, bucket_name="evidence_files").upload_from_stream(f"{eid}.txt", text.encode(), metadata={"record_id": rec["id"]})
    await db.evidence.insert_one({"id": eid, "record_id": rec["id"], "root_id": rec.get("root_id") or rec["id"], "ref": rec["ref"], "filename": name, "size": len(text), "sha256": "demo",
                                  "mime": "text/plain", "category": "Completion evidence", "visibility": "shared", "scan_state": "clean", "scan_note": "Demo evidence", "uploaded_by": u["id"],
                                  "uploaded_by_name": u["name"], "uploaded_by_role": u["active_role"], "at": iso(), "file_id": str(fid)})


def soon(h):
    return iso(now() + timedelta(hours=h))[:16]


async def base_data():
    t = iso()
    for i, n, r in CENTRES:
        await db.orgs.insert_one({"id": i, "name": n, "kind": "service_centre", "region": r, "demo": True})
    for i, n, k, r in ORGS:
        await db.orgs.insert_one({"id": i, "name": n, "kind": k, "region": r, "demo": True})
    orgs = {o["id"]: o async for o in db.orgs.find({}, {"_id": 0})}
    pw = hash_password(DEMO_PASSWORD)
    seen = set()
    for email, name, roles, extra in USERS:
        o = orgs.get(extra.get("org_id") or extra.get("centre_id"))
        primary = roles[0] not in seen
        seen.add(roles[0])
        await db.users.insert_one({"id": new_id("usr"), "email": _u(email), "name": name, "roles": roles, "active_role": roles[0], "password_hash": pw, "status": "active", "demo": True,
                                   "demo_primary": primary, "org_id": extra.get("org_id"), "org_name": o["name"] if o and extra.get("org_id") else None, "centre_id": extra.get("centre_id"),
                                   "centre_name": o["name"] if o and extra.get("centre_id") else None, "regions": extra.get("regions") or ([o["region"]] if o else []),
                                   "skills": extra.get("skills", []), "phone": extra.get("phone"), "confidentiality": extra.get("confidentiality", "standard"), "created_at": t})
    for cid, n, ph, em, addr, pin, reg, pref in CUSTOMERS:
        u = await db.users.find_one({"email": em}, {"_id": 0, "id": 1}) if em else None
        await db.customers.insert_one({"id": cid, "name": n, "phone": ph, "email": em, "address": addr, "pin": pin, "region": reg, "preferred_contact": pref, "user_id": u and u["id"], "demo": True, "created_at": t})
    for mid, cat, model, comps, skill in MODELS:
        await db.product_models.insert_one({"id": mid, "category": cat, "model": model, "components": comps, "serial_rule": f"^{model.replace('-', '')}[0-9]{{6}}$", "skill": skill, "state": "active", "demo": True})
    serials = [("cus_1", "mdl_cl55", "CL55102345"), ("cus_1", "mdl_gy15", "GY15200871"), ("cus_1", "mdl_mg75", "MG75300112"), ("cus_1", "mdl_ic20", "IC20400520"),
               ("cus_2", "mdl_wp10", "WP10500333"), ("cus_3", "mdl_rh02", "RH02600441"), ("cus_4", "mdl_cl55", "CL55102399"), ("cus_5", "mdl_cf48", "CF48700812"), ("cus_6", "mdl_gy15", "GY15200900")]
    for cid, mid, s in serials:
        await db.products.insert_one({"serial": s, "model_id": mid, "model": mid.split("_")[1].upper(), "customer_id": cid, "purchase_date": "2026-03-14", "demo": True})
    await db.orders.insert_many([{"id": "ord_1", "ref": "ORD-WL-2026-0101", "org_id": "org_b1", "date": "2026-08-02", "site": "Thane depot", "units": 40, "model_id": "mdl_cl55", "demo": True},
                                 {"id": "ord_2", "ref": "ORD-WL-2026-0102", "org_id": "org_b1", "date": "2026-09-11", "site": "Nashik site", "units": 25, "model_id": "mdl_wp10", "demo": True}])
    for sku, n, comp, cost in PARTS:
        await db.parts.insert_one({"sku": sku, "name": n, "compatible_models": comp, "unit_cost": cost, "demo": True})
    for wid, n, r in WAREHOUSES:
        await db.warehouses.insert_one({"id": wid, "name": n, "region": r, "demo": True})
    for i, (sku, *_rest) in enumerate(PARTS):
        for j, (wid, *_w) in enumerate(WAREHOUSES):
            on = 0 if (sku == "GY15-THM" and wid == "wh_1") else (i * 3 + j * 2) % 9 + 2
            await db.stock.insert_one({"sku": sku, "warehouse_id": wid, "on_hand": on, "reserved": 0, "demo": True})
    for i, (title, body, aud, cat) in enumerate(KNOWLEDGE):
        await db.knowledge.insert_one({"id": f"kb_{i + 1}", "title": title + " (demo procedure)", "body": body, "audience": aud, "category": cat, "version": "v1-demo",
                                       "approved": "DEMO CONTENT - not an approved Champion procedure", "demo": True})


async def config_defaults():
    defaults = {"sla_policies": DEFAULT_SLA, "business_calendar": DEFAULT_CALENDAR, "authority_matrix": engine.DEFAULT_AUTHORITY, "reopen_window_days": 30,
                "feature_flags": {"hr_module": True, "supplier_module": True, "audit_module": True, "ai_assist": True, "dev_role_switcher": True},
                "capacity": {"technician_open_jobs": 6, "_note": "PLACEHOLDER capacity rule"},
                "retention_schedules": {"_note": "PLACEHOLDER retention periods pending legal/BRD confirmation; automatic deletion disabled",
                                        "Cases": {"days": 2555, "types": ["case", "job", "task"], "owner": "Service operations"},
                                        "Settlements": {"days": 2920, "types": ["settlement", "approval"], "owner": "Finance"},
                                        "Safety incidents": {"days": 3650, "types": ["incident", "capa"], "owner": "Quality"}}}
    for k, v in defaults.items():
        if await get_config(k) is None:
            await set_config(k, v, None, "Initial default (placeholder)")


async def run_job(job, tech_email, owner="rohan.mehta", diag="Repair - covered", accept=True):
    tech = await user(tech_email)
    if job["state"] == "created":
        await db.records.update_one({"id": job["id"]}, {"$set": {"centre_id": tech["centre_id"], "centre_name": tech["centre_name"]}})
        job = await engine.find(job["id"])
        mgr = "kavita.desai" if tech["centre_id"] == "org_c1" else None
        u = await user(mgr) if mgr else {**(await user("kavita.desai")), "centre_id": tech["centre_id"]}
        await engine.run_action(u, job["id"], "allocate", {"technician_id": tech["id"]})
        job = await engine.find(job["id"])
    job = await act(owner, job, "propose_appointment", {"window_start": soon(-30), "window_end": soon(-28)})
    job = await act(owner, job, "confirm_on_behalf", {"call_note": "Customer confirmed by phone"})
    k = await user("kavita.desai")
    await engine.run_action({**k, "centre_id": job["centre_id"]}, job["id"], "confirm_dispatch", {"tools_ready": "Confirmed", "parts_ready": "Not required", "info_ready": "Confirmed"})
    job = await act(tech_email, await engine.find(job["id"]), "record_arrival", {"arrived_at": soon(-29), "customer_present": "Yes"})
    job = await act(tech_email, job, "submit_diagnosis", {"product_serial": job["data"].get("serial") or "N/A", "symptom": "As reported", "installation": "Installation acceptable",
                                                          "reading": "230 V supply", "cause": "Worn component identified on inspection", "recommended": diag})
    if not accept:
        return job
    job = await act(tech_email, job, "record_repair", {"approved_proposal": "Covered repair", "work": "Replaced worn component and cleaned assembly", "labour_minutes": 45})
    job = await act(tech_email, job, "submit_tests", {"functional": "Pass", "insulation": "Pass", "earth": "Pass", "readings": "IR > 2 MOhm; earth 0.1 Ohm"})
    await evidence(job, tech_email, "service_report_demo.txt", "Demo service report - repair completed and tested.")
    job = await act(tech_email, job, "submit_handover", {"signoff_name": "Customer (demo)", "customer_satisfied": "Confirmed working", "handover_note": "Product demonstrated working"})
    k = await user("kavita.desai")
    await engine.run_action({**k, "centre_id": job["centre_id"]}, job["id"], "accept_report", {"review_note": "Evidence adequate"})
    return await engine.find(job["id"])


async def complaint(email, model, issue, desc, pin, safety="No hazard reported", serial=""):
    u = await user(email)
    return await engine.create_record(u, "case", "customer_complaint", {"product_category": (await db.product_models.find_one({"id": model}))["category"], "model_id": model, "serial": serial,
                                                                        "issue_category": issue, "description": desc, "address": "Demo address", "pin": pin, "preferred_contact": "Email", "safety_concern": safety})


async def route_accept(case, owner="rohan.mehta", pri="P3 - Normal"):
    o = await user(owner)
    case = await act("priya.nair", case, "register_route", {"issue_category": case["data"].get("issue_category", "Not working"), "priority": pri, "impact": "Product unusable", "owner_id": o["id"], "queue": "Service coordination"})
    case = await act(owner, case, "accept_ownership", {"acceptance_note": "Accepted"})
    return await act(owner, case, "plan_resolution", {"plan": "Field visit, diagnose and repair", "remedy": "Repair", "next_review": soon(24)})


async def new_job(case, centre, skill, owner="rohan.mehta"):
    await act(owner, case, "create_service_job", {"centre_id": centre, "job_type": "Field visit", "skill": skill})
    return await child(case, "job")


async def scenarios():
    S = {}
    # A: proposed appointment awaiting customer
    a = await route_accept(await complaint("aarav.sharma", "mdl_cl55", "Performance issue", "Air cooler runs but cooling is weak even with full water tank.", "400050", serial="CL55102345"))
    ja = await new_job(a, "org_c1", "Cooling")
    ja = await act("kavita.desai", ja, "allocate", {"technician_id": (await user("rahul.verma"))["id"]})
    await act("kavita.desai", ja, "propose_appointment", {"window_start": soon(26), "window_end": soon(28)})
    # B: safety complaint
    b = await complaint("aarav.sharma", "mdl_gy15", "Electrical fault", "Burning smell from water heater when switched on, switched off at the mains.", "400050", "Burning smell or smoke", "GY15200871")
    inc = await child(b, "incident")
    await act("lakshmi.pillai", inc, "triage", {"urgent": "Yes", "severity": "S2 - Serious hazard", "specialists": "EHS lead"})
    # C: chargeable estimate pending approval + customer acceptance
    c = await route_accept(await complaint("meera.iyer", "mdl_wp10", "Noise or vibration", "Pump makes loud grinding noise and pressure dropped.", "560038", serial="WP10500333"))
    jc = await new_job(c, "org_c4", "Pumps")
    jc = await run_job(jc, "kiran.das", diag="Repair - chargeable", accept=False)
    await act("kiran.das", jc, "submit_estimate", {"labour": 800, "parts_cost": 1200, "chargeable": "Yes", "proposal": "Replace impeller (seal damaged by dry running)"})
    # D: agent ticket, parts requisition, warranty and technical review
    agent = await user("priya.nair")
    d = await engine.create_record(agent, "case", "support_ticket", {"customer_id": "cus_3", "submitting_party": "Customer", "source_channel": "Phone", "model_id": "mdl_rh02", "serial": "RH02600441",
                                                                     "description": "Room heater stops heating after ten minutes.", "issue_category": "Not working", "impact": "Product unusable", "priority": "P2 - High", "safety_concern": "No hazard reported"})
    d = await route_accept(d, pri="P2 - High")
    jd = await new_job(d, "org_c2", "Heating")
    jd = await run_job(jd, "sunil.rao", accept=False)
    await act("sunil.rao", jd, "request_parts", {"part_sku": "RH02-COIL", "quantity": 1, "reason": "Open circuit coil", "required_by": soon(48)[:10]})
    await act("rohan.mehta", d, "request_warranty_review", {"component": "Heating coil", "claim_notes": "Purchased 7 months ago"})
    await act("rohan.mehta", d, "request_technical_review", {"question": "Second coil failure in a year - confirm root cause"})
    # E: completed job, refund approved -> settlement pending -> closure blocked
    e = await route_accept(await complaint("aarav.sharma", "mdl_cf48", "Not working", "Ceiling fan stopped and hums when switched on.", "400050"))
    je = await new_job(e, "org_c1", "Fans")
    await run_job(je, "anita.shah")
    await act("rohan.mehta", e, "request_remedy_approval", {"remedy": "refund", "amount": 1200, "recipient": "BEN-DEMO-0001", "justification": "Goodwill refund of visit charge (demo)"})
    ap = await child(e, "approval")
    await act("neha.kulkarni", ap, "approve", {"decision_note": "Within regional authority", "evidence_checked": "Yes"})
    # F: resolved awaiting customer verification
    f = await route_accept(await complaint("aarav.sharma", "mdl_mg75", "Not working", "Mixer grinder stops under load after a few seconds.", "400050", serial="MG75300112"))
    await run_job(await new_job(f, "org_c1", "Kitchen"), "rahul.verma")
    await act("rohan.mehta", f, "mark_resolved", {"resolution": "Motor coupling replaced, tested under load", "remedy_delivered": "Repair"})
    # G: closed then appealed; refund approval pending
    g = await route_accept(await complaint("aarav.sharma", "mdl_ic20", "Not working", "Induction cooktop shows error E3 and does not heat.", "400050", serial="IC20400520"))
    await run_job(await new_job(g, "org_c1", "Kitchen"), "rahul.verma")
    await act("rohan.mehta", g, "mark_resolved", {"resolution": "Power board reseated", "remedy_delivered": "Repair"})
    await act("rohan.mehta", g, "verify_and_close", {"outcome": "Resolved - evidence verified", "verification_note": "Service report and test readings reviewed", "customer_confirmation": "Confirmed"})
    await act("aarav.sharma", await engine.find(g["id"]), "request_review", {"original_decision": "Closure outcome", "reason": "Error returned after two days; I want a replacement.", "requested_outcome": "Replacement", "contact_pref": "Email", "explanation": "Second failure."})
    # H: overdue P2 awaiting owner (North) -> breach + escalation
    h = await engine.create_record(agent, "case", "support_ticket", {"customer_id": "cus_4", "submitting_party": "Customer", "source_channel": "WhatsApp", "model_id": "mdl_cl55", "serial": "CL55102399",
                                                                     "description": "Air cooler leaking water onto floor.", "issue_category": "Leakage", "impact": "Partially usable", "priority": "P2 - High", "safety_concern": "No hazard reported"})
    await act("priya.nair", h, "register_route", {"issue_category": "Leakage", "priority": "P2 - High", "impact": "Partially usable", "owner_id": (await user("anjali.rao"))["id"], "queue": "Service coordination"})
    await sla.age(h["id"], 6000)
    # I: case approaching breach
    i = await engine.create_record(agent, "case", "support_ticket", {"customer_id": "cus_6", "submitting_party": "Customer", "source_channel": "Email", "model_id": "mdl_gy15", "serial": "GY15200900",
                                                                     "description": "Water heater takes too long to heat.", "issue_category": "Performance issue", "impact": "Partially usable", "priority": "P3 - Normal", "safety_concern": "No hazard reported"})
    await sla.age(i["id"], 220)
    # Dealer stock claim and dealer customer case
    dealer = await user("dealer.sunrise")
    sc = await engine.create_record(dealer, "case", "stock_claim", {"delivery_ref": "DLV-DEMO-7781", "invoice": "INV-DEMO-5521", "model_id": "mdl_cl55", "quantity": 3, "serials": "CL55109001, CL55109002, CL55109003",
                                                                    "description": "Three units received with cracked outer body panels.", "receipt_date": "2026-10-12", "amount": 9000})
    dc = await engine.create_record(dealer, "case", "dealer_customer_case", {"customer_name": "Rakesh Jain (demo)", "customer_contact": "+919800000099", "representation": "Customer present at counter",
                                                                             "invoice": "INV-DEMO-4410", "model_id": "mdl_wp10", "serial": "WP10500999", "issue_category": "Not working", "description": "Pump does not start after installation.",
                                                                             "address": "Dadar, Mumbai", "purchase_date": "2026-09-30", "safety_concern": "No hazard reported"})
    chd = await child(dc, "channel_dispute")
    await act("manoj.patil", chd, "record_findings", {"customer_account": "Pump never started", "dealer_account": "Installed as per guide", "findings": "Faulty capacitor at delivery - supply defect", "evidence_sufficient": "Yes"})
    await act("manoj.patil", await engine.find(chd["id"]), "decide_dispute", {"decision": "Approve claim", "amount": 3000, "reason": "Supply defect confirmed; dealer credited for replacement unit"})
    # Distributor bulk grievance
    dist = await user("ops.westline")
    bg = await engine.create_record(dist, "case", "bulk_grievance", {"order_ref": "ord_1", "model_id": "mdl_cl55", "quantity": 3, "issue_category": "Not working", "business_impact": "Units at depot cannot be sold",
                                                                     "requested_outcome": "Repair at sites", "primary_contact": "Pooja Shetty"})
    bg = await act("ops.westline", bg, "validate_units", {"units": "Thane depot, CL55110001\nThane depot, CL55110002\nNashik site, CL55110003"})
    bg = await route_accept(bg)
    await act("rohan.mehta", bg, "create_unit_jobs", {"centre_id": "org_c2"})
    # Supplier dispute, HR grievance, audit, management action, correspondence, contacts
    sup = await engine.create_record(await user("sameer.jain"), "supplier_dispute", "dispute", {"org_id": "org_s1", "po": "PO-DEMO-3301", "invoice": "SINV-DEMO-881", "grn": "GRN-DEMO-120",
                                                                                               "issue": "Quantity shortfall", "amount": 24000, "description": "Invoice for 200 motors; 180 received."})
    await act("sameer.jain", sup, "reconcile_lines", {"lines": "Motor qty, 200, 180\nInvoice value, 130000, 117000"})
    hr = await engine.create_record(await user("ritu.malhotra"), "hr_grievance", "grievance", {"category": "Misconduct", "complainant_contact": "+919811112222", "urgency": "Standard",
                                                                                               "conflict_declaration": "No conflict", "designated_process": "Standard confidential investigation",
                                                                                               "summary": "Demo restricted summary - fictional", "evidence_access": "Assigned HR officer only"})
    await act("ritu.malhotra", hr, "triage", {"urgent_or_specialist": "No", "rationale": "Standard process applies"})
    aud = await engine.create_record(await user("nisha.verma"), "audit", "engagement", {"title": "Q3 closure evidence audit (demo)", "area": "Case handling", "period_from": "2026-07-01", "period_to": "2026-10-31",
                                                                                        "criteria": "Closed cases must hold verification evidence"})
    await act("nisha.verma", aud, "save_scope", {"record_type": "case", "sample_size": 5, "method": "Random"})
    await engine.create_record(await user("nisha.verma"), "audit_finding", "finding", {"title": "Closure verification note missing on sampled case", "severity": "Medium", "engagement_id": aud["id"],
                                                                                        "record_ref": g["ref"], "condition": "Verification note lacks test readings", "criteria": "Closure evidence standard (demo)",
                                                                                        "action_owner_id": (await user("rohan.mehta"))["id"], "due": soon(240)[:10]})
    await engine.create_record(await user("anil.bose"), "mgmt_action", "action", {"title": "Reduce West region assignment backlog", "scope": "Region", "assignee_id": (await user("neha.kulkarni"))["id"],
                                                                                  "expected_outcome": "Unassigned cases under 5", "due": soon(336)[:10]})
    await engine.create_record(await user("sara.thomas"), "correspondence", "correspondence", {"reference": "CF-DEMO-2026-118", "authority": "Consumer commission", "received": "2026-10-10",
                                                                                               "verified_deadline": "2026-11-09", "assignee_id": (await user("sara.thomas"))["id"], "summary": "Notice regarding delayed repair (fictional)"})
    for ch, name, contact, subj, msg in [("WhatsApp", "Aarav Sharma", "+919800000001", "Cooler still weak", "Following up on my cooler complaint - when is the visit?"),
                                         ("Email", "Farhan Ali", "farhan.ali" + D, "Geyser slow heating", "My geyser takes an hour to heat."),
                                         ("Phone", "Unknown caller", "+919800000077", "Shock from fan regulator", "Caller reports a mild shock from fan regulator."),
                                         ("Web chat", "Sneha Patil", "+919800000005", "Invoice copy", "Need a copy of my service invoice.")]:
        await engine.create_record(agent, "contact", "manual", {"channel": ch, "customer_name": name, "contact": contact, "subject": subj, "message": msg})
    # Policies (warranty terms placeholders)
    for comp, mid in [("Cooling pump", "mdl_cl55"), ("Heating element", "mdl_gy15")]:
        pol = await engine.create_record(await user("sanjay.gupta"), "policy", "warranty_term", {"model_id": mid, "component": comp, "version": "DEMO-v1", "coverage_basis": "Months from purchase",
                                                                                                 "coverage_months": 12, "evidence_required": "Tax invoice or warranty card", "exclusion": "PLACEHOLDER - exclusions pending Champion warranty policy",
                                                                                                 "effective": "2026-01-01", "reviewer_id": (await user("arjun.kapoor"))["id"]})
        pol = await act("sanjay.gupta", pol, "submit_for_review")
        await act("arjun.kapoor", pol, "publish", {"review_note": "Demo placeholder published for evaluation"})
    await engine.create_record(await user("admin2.ops"), "config_change", "change", {"target": "reopen_window_days", "change_summary": "Confirm 30 day reopening window (placeholder)",
                                                                                      "approval_reference": "CR-DEMO-001", "proposed_value": 30})
    await sla.tick()
    return S


async def seed():
    meta = await db.meta.find_one({"_id": "seed"})
    owner_email = os.environ["ADMIN_EMAIL"].lower()
    if not await db.users.find_one({"email": owner_email}):
        await db.users.insert_one({"id": new_id("usr"), "email": owner_email, "name": "Platform Owner", "roles": ["R18"], "active_role": "R18", "password_hash": hash_password(os.environ["ADMIN_PASSWORD"]),
                                   "status": "active", "demo": False, "regions": [], "skills": [], "confidentiality": "standard", "created_at": iso()})
    else:
        from auth import verify_password
        u = await db.users.find_one({"email": owner_email})
        if not verify_password(os.environ["ADMIN_PASSWORD"], u.get("password_hash", "")):
            await db.users.update_one({"email": owner_email}, {"$set": {"password_hash": hash_password(os.environ["ADMIN_PASSWORD"])}})
    await config_defaults()
    if meta and meta.get("version") == SEED_VERSION:
        return
    log.info("Seeding demo data v%s", SEED_VERSION)
    if not await db.orgs.find_one({}):
        await base_data()
    engine.SEED["demo"] = True
    try:
        await scenarios()
        await db.meta.update_one({"_id": "seed"}, {"$set": {"version": SEED_VERSION, "at": iso()}}, upsert=True)
    except Exception as e:
        log.exception("Demo scenario seeding failed: %s", e)
    finally:
        engine.SEED["demo"] = False
