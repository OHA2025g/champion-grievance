# Champion Electricals - end-to-end workflow chain tests (case -> job -> approval -> settlement, SoD, closure block)
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE_URL + "/api"
_s = {}
CTX = {}


def sess(role):
    if role not in _s:
        s = requests.Session()
        r = s.post(f"{API}/auth/dev-login", json={"role": role})
        if r.status_code == 429:
            time.sleep(30)
            r = s.post(f"{API}/auth/dev-login", json={"role": role})
        assert r.status_code == 200, r.text
        _s[role] = s
    return _s[role]


def autofill(s, fields, over):
    vals = {}
    for f in fields:
        k = f["k"]
        if k in over:
            vals[k] = over[k]
            continue
        if not f.get("req"):
            continue
        t = f["t"]
        if t == "select":
            vals[k] = f["opts"][0]
        elif t == "lookup":
            opts = s.get(f"{API}/lookup/{f['src']}").json()
            opts = opts if isinstance(opts, list) else opts.get("items", [])
            assert opts, f"no lookup options for {f['src']}"
            vals[k] = opts[0]["value"]
        elif t == "number":
            vals[k] = 500
        elif t == "date":
            vals[k] = "2026-03-01"
        elif t == "datetime":
            vals[k] = "2026-03-01T10:00"
        elif t == "textarea":
            vals[k] = "TEST_ automated workflow detail text"
        else:
            vals[k] = "TEST_value"
    return vals


def act(role, rid, key, expect=200, **over):
    s = sess(role)
    g = s.get(f"{API}/records/{rid}").json()
    a = [x for x in g.get("actions", []) if x["key"] == key]
    fields = a[0]["fields"] if a else []
    r = s.post(f"{API}/records/{rid}/actions/{key}", json={"values": autofill(s, fields, over)})
    if expect:
        assert r.status_code == expect, f"{role} {key}: {r.status_code} {r.text}"
    return r


def children(role, rid, rtype):
    g = sess(role).get(f"{API}/records/{rid}").json()
    return [c for c in g["children"] if c["type"] == rtype]


def lookup_value(role, src, contains):
    opts = sess(role).get(f"{API}/lookup/{src}").json()
    opts = opts if isinstance(opts, list) else opts.get("items", [])
    m = [o for o in opts if contains.lower() in (o["label"] + str(o.get("sub", ""))).lower()]
    assert m, f"{contains} not in {src}: {opts}"
    return m[0]["value"]


class TestCaseChain:
    def test_01_customer_creates(self):
        vals = {"product_category": "Fan", "issue_category": "Not working", "description": "TEST_ chain fan not working at all",
                "address": "TEST_ 1 Chain Road Mumbai", "pin": "400050", "preferred_contact": "Email", "safety_concern": "No hazard reported"}
        r = sess("R01").post(f"{API}/records/case/customer_complaint", json={"values": vals})
        assert r.status_code == 200, r.text
        CTX["case"] = r.json()["id"]

    def test_02_agent_routes_to_rohan(self):
        rohan = lookup_value("R04", "users:R05", "Rohan")
        r = act("R04", CTX["case"], "register_route", owner_id=rohan)
        assert r.json()["state"] == "awaiting_owner"

    def test_03_owner_accepts_plans_creates_job(self):
        assert act("R05", CTX["case"], "accept_ownership").json()["state"] == "in_progress"
        act("R05", CTX["case"], "plan_resolution", remedy="Refund")
        centre = lookup_value("R05", "centres", "Mumbai West")
        act("R05", CTX["case"], "create_service_job", centre_id=centre)
        jobs = children("R05", CTX["case"], "job")
        assert jobs, "service job not linked to case"
        CTX["job"] = jobs[0]["id"]

    def test_04_centre_manager_allocates_and_proposes(self):
        tech = lookup_value("R07", "users:R06", "Rahul")
        assert act("R07", CTX["job"], "allocate", technician_id=tech).json()["state"] == "allocated"
        assert act("R07", CTX["job"], "propose_appointment", window_start="2026-03-02T10:00", window_end="2026-03-02T12:00").json()["state"] == "appointment_proposed"

    def test_05_customer_confirms_appointment(self):
        assert act("R01", CTX["job"], "customer_confirm_appointment").json()["state"] == "appointment_confirmed"

    def test_06_remedy_approval_and_sod(self):
        act("R05", CTX["case"], "request_remedy_approval", remedy="refund", amount=1500, recipient="TEST_UPI-123")
        apps = children("R05", CTX["case"], "approval")
        assert apps, "approval not created"
        CTX["approval"] = apps[0]["id"]
        # requester cannot approve own approval
        r = sess("R05").post(f"{API}/records/{CTX['approval']}/actions/approve", json={"values": {"decision_note": "TEST_", "evidence_checked": "Yes"}})
        assert r.status_code in (403, 409), r.text
        CTX["required_role"] = apps[0].get("required_role")

    def test_07_approver_approves_creates_settlement(self):
        role = CTX.get("required_role") or "R09"
        r = act(role, CTX["approval"], "approve", expect=None)
        assert r.status_code == 200, f"{role} approve: {r.text}"
        st = children("R05", CTX["case"], "settlement")
        assert st, "settlement not created after refund approval"
        CTX["settlement"] = st[0]["id"]

    def test_08_resolution_blocked_by_pending_work(self):
        r = sess("R05").post(f"{API}/records/{CTX['case']}/actions/mark_resolved", json={"values": {"resolution": "TEST_ done", "remedy_delivered": "Refund"}})
        assert r.status_code in (409, 422), r.text

    def test_09_finance_settlement(self):
        assert act("R13", CTX["settlement"], "validate_recipient", account_ending="1234", approved_amount=1500).json()["state"] == "recipient_validated"
        st = act("R13", CTX["settlement"], "submit_instruction").json()["state"]
        assert st in ("pending_confirmation", "executed", "outcome_unknown", "failed"), st
        CTX["settlement_state"] = st
        if st == "pending_confirmation":
            st = act("R13", CTX["settlement"], "check_status").json()["state"]
        if st == "executed":
            amt = sess("R13").get(f"{API}/records/{CTX['settlement']}").json()["record"].get("amount", 1500)
            assert act("R13", CTX["settlement"], "reconcile", ledger_amount=amt).json()["state"] == "reconciled"
        print("final settlement state", st)


def test_r08_sees_pending_approval_in_inbox():
    r = sess("R08").get(f"{API}/inbox")
    assert r.status_code == 200
    assert "APR-" in r.text


def test_config_change_proposal_admin():
    s = sess("R18")
    cfg = s.get(f"{API}/admin/config")
    assert cfg.status_code == 200


def test_dev_sla_age_endpoint_exists():
    c = sess("R05").get(f"{API}/records", params={"type": "case", "q": "CE-2026-00001"}).json()["items"][0]
    r = sess("R05").post(f"{API}/dev/sla/age", json={"record_id": c["id"], "hours": 0})
    assert r.status_code in (200, 422), r.text
