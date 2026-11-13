# Champion Electricals - role-specific workflow tests (R11, R12, R14, R16, R17, R18, R19, R20, R21)
import os
import uuid
import pytest
import requests
from test_champion_workflows import sess, act, autofill

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE_URL + "/api"


def meta():
    return sess("R18").get(f"{API}/meta").json()["workflows"]


def first(role, rtype, state):
    r = sess(role).get(f"{API}/records", params={"type": rtype, "state": state})
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    return items[0] if items else None


def create(role, rtype, sub, **over):
    s = sess(role)
    fields = meta()[rtype]["create"][sub]["fields"]
    vals = autofill(s, fields, over)
    for k, v in list(vals.items()):
        if isinstance(v, str) and v == "TEST_value":
            vals[k] = f"TEST_{uuid.uuid4().hex[:6]}"
    return s.post(f"{API}/records/{rtype}/{sub}", json={"values": vals})


# --- R11 warranty
def test_r11_check_evidence():
    w = first("R11", "warranty", "submitted")
    if not w:
        pytest.skip("no submitted warranty claim")
    assert act("R11", w["id"], "check_evidence").json()["state"] == "diagnosis_review"


# --- R12 parts
def test_r12_validate_and_reserve():
    rq = first("R12", "requisition", "requested")
    if not rq:
        pytest.skip("no requested requisition")
    act("R12", rq["id"], "validate_requisition")
    r = act("R12", rq["id"], "reserve_stock", expect=None)
    assert r.status_code in (200, 409, 422), r.text
    print("reserve:", r.status_code, r.text[:200])


def test_r12_stock_list():
    r = sess("R12").get(f"{API}/stock")
    assert r.status_code == 200


# --- R14 quality
def test_r14_triage_incident():
    inc = first("R14", "incident", "reported")
    assert inc, "no reported incidents"
    assert act("R14", inc["id"], "triage").json()["state"] == "containment"


# --- R16 appeals: conflict check
def test_r16_assign_reviewer():
    ap = first("R16", "appeal", "registered")
    if not ap:
        pytest.skip("no registered appeal")
    opts = sess("R16").get(f"{API}/lookup/users:R16").json()
    opts = opts if isinstance(opts, list) else opts.get("items", [])
    results = []
    for o in opts:
        r = act("R16", ap["id"], "assign_reviewer", expect=None, reviewer_id=o["value"])
        results.append((o["label"], r.status_code, r.text[:150]))
        if r.status_code == 200:
            break
    print(results)
    assert any(x[1] == 200 for x in results), results


# --- R17 analytics read-only
def test_r17_analytics_and_cannot_act():
    s = sess("R17")
    a = s.get(f"{API}/analytics")
    assert a.status_code == 200
    r = s.post(f"{API}/records/case/customer_complaint", json={"values": {}})
    assert r.status_code in (403, 422)


# --- R18 admin
def test_r18_invite_user_and_disable_reenable():
    s = sess("R18")
    email = f"test_{uuid.uuid4().hex[:6]}@example.com"
    r = s.post(f"{API}/admin/users", json={"email": email, "name": "TEST_ Invitee", "role": "R04", "approval_reference": "TEST_APR-99"})
    assert r.status_code == 200, r.text
    uid = r.json()["id"]
    r = s.post(f"{API}/admin/users", json={"email": email, "name": "TEST_ dup", "role": "R04", "approval_reference": "TEST_APR-99"})
    assert r.status_code == 409
    assert s.patch(f"{API}/admin/users/{uid}", json={"status": "disabled", "approval_reference": "TEST_APR-99"}).status_code == 200
    lst = s.get(f"{API}/admin/users", params={"q": email}).json()
    assert "disabled" in str(lst)


def test_r18_invite_requires_approval_reference():
    r = sess("R18").post(f"{API}/admin/users", json={"email": "test_noref@example.com", "name": "TEST_", "role": "R04", "approval_reference": ""})
    assert r.status_code == 422


def test_r18_permissions_config_audit():
    s = sess("R18")
    for ep in ("permissions", "config", "audit", "events", "retention"):
        assert s.get(f"{API}/admin/{ep}").status_code == 200, ep


def test_r18_config_change_create():
    r = create("R18", "config_change", "change", proposed_value="{\"value\": 1}")
    assert r.status_code == 200, r.text


# --- R19 HR grievance restricted
def test_r19_create_hr_grievance_restricted():
    r = create("R19", "hr_grievance", "grievance", complainant_contact="9876543210")
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    g = sess("R19").get(f"{API}/records/{rid}").json()
    assert "****" in g["record"]["data"].get("complainant_contact", "****")
    assert sess("R18").get(f"{API}/records/{rid}").status_code == 403
    assert sess("R21").get(f"{API}/records/{rid}").status_code == 403


# --- R20 supplier dispute
def test_r20_supplier_dispute():
    assert sess("R20").get(f"{API}/records", params={"type": "supplier_dispute"}).json()["total"] >= 1
    r = create("R20", "supplier_dispute", "dispute")
    assert r.status_code == 200, r.text


# --- R21 auditor
def test_r21_audit_engagements_and_findings():
    s = sess("R21")
    assert s.get(f"{API}/records", params={"type": "audit"}).json()["total"] >= 1
    assert s.get(f"{API}/records", params={"type": "audit_finding"}).status_code == 200
    assert s.get(f"{API}/admin/audit").status_code in (200, 403)
