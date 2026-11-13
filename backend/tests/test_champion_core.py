# Champion Electricals - core backend regression tests (auth, RBAC, workflows, concurrency, AI, admin)
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE_URL + "/api"
_sessions = {}


def sess(role):
    """Dev-login session per role (cached to respect auth rate limit)."""
    if role not in _sessions:
        s = requests.Session()
        r = s.post(f"{API}/auth/dev-login", json={"role": role})
        if r.status_code == 429:
            time.sleep(30)
            r = s.post(f"{API}/auth/dev-login", json={"role": role})
        assert r.status_code == 200, r.text
        _sessions[role] = s
    return _sessions[role]


def case_by_ref(ref, role="R05"):
    r = sess(role).get(f"{API}/records", params={"type": "case", "q": ref})
    items = [i for i in r.json()["items"] if i["ref"] == ref]
    return items[0] if items else None


# --- Health / meta
def test_health():
    r = requests.get(f"{API}/health")
    assert r.status_code == 200


def test_meta_161_screens():
    m = sess("R18").get(f"{API}/meta").json()
    assert len(m["screens"]) == 161
    assert len(m["roles"]) >= 21


# --- Auth
def test_login_owner_admin_and_cookies():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "singh.aghoreshwar@gmail.com", "password": "ChampionAdmin#2026"})
    assert r.status_code == 200, r.text
    assert "R18" in r.json()["roles"]
    sc = r.headers.get("set-cookie", "")
    assert "access_token" in sc and "HttpOnly" in sc
    assert s.get(f"{API}/auth/me").json()["email"] == "singh.aghoreshwar@gmail.com"
    s.post(f"{API}/auth/logout")
    s.cookies.clear()
    assert s.get(f"{API}/auth/me").status_code == 401


def test_login_demo_and_wrong_password():
    r = requests.post(f"{API}/auth/login", json={"email": "rohan.mehta@demo.champion.test", "password": "Champion@2026"})
    assert r.status_code == 200
    r = requests.post(f"{API}/auth/login", json={"email": "priya.nair@demo.champion.test", "password": "wrong-pass"})
    assert r.status_code == 401


def test_otp_flow():
    s = requests.Session()
    r = s.post(f"{API}/auth/otp/request", json={"identifier": "aarav.sharma@demo.champion.test"})
    assert r.status_code == 200
    code = r.json().get("dev_code")
    assert code and len(code) == 6
    r = s.post(f"{API}/auth/otp/verify", json={"identifier": "aarav.sharma@demo.champion.test", "code": code})
    assert r.status_code == 200
    assert r.json()["email"] == "aarav.sharma@demo.champion.test"


def test_recover_returns_dev_token_and_bad_token_rejected():
    r = requests.post(f"{API}/auth/recover", json={"email": "priya.nair@demo.champion.test"})
    assert r.status_code == 200 and r.json().get("dev_token")
    r = requests.post(f"{API}/auth/reset", json={"token": "bogus", "password": "Abcdefgh12"})
    assert r.status_code == 400


@pytest.mark.parametrize("role", [f"R{i:02d}" for i in range(1, 22)])
def test_dev_login_each_role_dashboard(role):
    s = sess(role)
    me = s.get(f"{API}/auth/me").json()
    assert me["active_role"] == role
    d = s.get(f"{API}/dashboard")
    assert d.status_code == 200, d.text


def test_switch_role_multi_role_user():
    s = requests.Session()
    s.post(f"{API}/auth/login", json={"email": "rohan.mehta@demo.champion.test", "password": "Champion@2026"})
    assert s.post(f"{API}/auth/switch-role", json={"role": "R04"}).json()["active_role"] == "R04"
    assert s.post(f"{API}/auth/switch-role", json={"role": "R18"}).status_code == 403
    assert s.post(f"{API}/auth/switch-role", json={"role": "R05"}).json()["active_role"] == "R05"


# --- RBAC
def test_r01_cannot_view_other_customers_case():
    meera = case_by_ref("CE-2026-00003")
    assert meera
    r = sess("R01").get(f"{API}/records/{meera['id']}")
    assert r.status_code == 403


def test_r21_auditor_action_read_only():
    c = case_by_ref("CE-2026-00001")
    r = sess("R21").post(f"{API}/records/{c['id']}/actions/log_call", json={"values": {"direction": "Inbound", "summary": "TEST_x"}})
    assert r.status_code == 403
    assert "read_only" in r.text


def test_r13_minimal_case_view():
    c = case_by_ref("CE-2026-00001")
    r = sess("R13").get(f"{API}/records/{c['id']}")
    assert r.status_code == 200
    assert r.json().get("minimal") is True


def test_hr_grievance_only_r19():
    assert sess("R19").get(f"{API}/records", params={"type": "hr_grievance"}).json()["total"] >= 1
    for role in ("R05", "R18", "R21", "R10"):
        r = sess(role).get(f"{API}/records", params={"type": "hr_grievance"})
        assert r.status_code == 403 or r.json()["total"] == 0, role


# --- Customer complaint + safety + evidence
def _complaint(safety="No hazard reported"):
    vals = {"product_category": "Fan", "issue_category": "Not working", "description": "TEST_ fan does not start at all since yesterday",
            "address": "TEST_ 12 Test Street Mumbai", "pin": "400001", "preferred_contact": "Email", "safety_concern": safety}
    return sess("R01").post(f"{API}/records/case/customer_complaint", json={"values": vals})


def test_create_complaint_and_evidence():
    r = _complaint()
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    s = sess("R01")
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    r = s.post(f"{API}/records/{rid}/evidence", files={"file": ("test.png", png, "image/png")})
    assert r.status_code == 200 and r.json()["scan_state"] == "clean"
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    r = s.post(f"{API}/records/{rid}/evidence", files={"file": ("eicar.txt", eicar, "text/plain")})
    assert r.status_code == 200 and r.json()["scan_state"] == "quarantined"
    r = s.post(f"{API}/records/{rid}/evidence", files={"file": ("bad.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 422
    g = s.get(f"{API}/records/{rid}").json()
    assert g["record"]["state"] == "registered" and len(g["evidence"]) == 2


def test_invalid_pin_rejected():
    vals = {"product_category": "Fan", "issue_category": "Not working", "description": "TEST_ short pin test description",
            "address": "TEST_", "pin": "12", "preferred_contact": "Email", "safety_concern": "No hazard reported"}
    r = sess("R01").post(f"{API}/records/case/customer_complaint", json={"values": vals})
    assert r.status_code == 422


def test_safety_complaint_creates_incident():
    r = _complaint("Burning smell or smoke")
    assert r.status_code == 200
    assert r.json()["safety_flag"]
    rid = r.json()["id"]
    inc = sess("R14").get(f"{API}/records", params={"type": "incident", "filter": '{"root_id": "%s"}' % rid}).json()
    inc2 = sess("R14").get(f"{API}/records", params={"type": "incident", "filter": '{"parent_id": "%s"}' % rid}).json()
    assert inc["total"] + inc2["total"] >= 1


# --- Closure blocked, concurrency, idempotency
def test_closure_blocked_by_pending_settlement():
    c = case_by_ref("CE-2026-00005")
    r = sess("R05").post(f"{API}/records/{c['id']}/actions/mark_resolved", json={"values": {"resolution": "TEST_ resolution", "remedy_delivered": "Refund"}})
    assert r.status_code in (409, 422), r.text
    assert "detail" in r.json() or "message" in r.json() or "error" in r.json()


def test_stale_version_conflict_and_idempotency():
    c = case_by_ref("CE-2026-00004")
    s = sess("R05")
    full = s.get(f"{API}/records/{c['id']}").json()["record"]
    r = s.post(f"{API}/records/{c['id']}/actions/log_call", json={"values": {"direction": "Inbound", "summary": "TEST_ call"}, "expected_version": full["version"] - 1})
    assert r.status_code == 409 and "conflict" in r.text
    key = str(uuid.uuid4())
    r1 = s.post(f"{API}/records/{c['id']}/actions/log_call", json={"values": {"direction": "Inbound", "summary": "TEST_ idem"}}, headers={"Idempotency-Key": key})
    assert r1.status_code == 200, r1.text
    r2 = s.post(f"{API}/records/{c['id']}/actions/log_call", json={"values": {"direction": "Inbound", "summary": "TEST_ idem"}}, headers={"Idempotency-Key": key})
    assert r2.status_code == 200 and r2.json().get("replayed") is True
    assert r2.json()["version"] == r1.json()["version"]


# --- AI
def test_ai_not_configured():
    s = sess("R04")
    assert s.get(f"{API}/ai/status").json()["configured"] is False
    r = s.post(f"{API}/ai/assist", json={"task": "summary", "record_id": case_by_ref("CE-2026-00001")["id"]})
    assert r.status_code == 503
    assert "not configured" in r.text


# --- Admin
def test_admin_integrations_modes():
    r = sess("R18").get(f"{API}/admin/integrations")
    assert r.status_code == 200
    txt = r.text
    for mode in ("MOCKED", "SIMULATED", "NOT CONFIGURED"):
        assert mode in txt, mode


def test_admin_cannot_change_own_roles():
    s = sess("R18")
    me = s.get(f"{API}/auth/me").json()
    r = s.patch(f"{API}/admin/users/{me['id']}", json={"roles": ["R18", "R05"], "approval_reference": "TEST_APR-1"})
    assert r.status_code in (403, 409, 422), r.text


def test_non_admin_users_forbidden():
    assert sess("R05").get(f"{API}/admin/users").status_code == 403


def test_export_csv():
    s = sess("R17")
    r = s.post(f"{API}/exports", json={"scope": "analytics"})
    assert r.status_code == 200, r.text
    eid = r.json().get("id")
    d = s.get(f"{API}/exports/{eid}/download")
    assert d.status_code == 200 and "," in d.text


def test_global_search_and_notifications():
    s = sess("R05")
    r = s.get(f"{API}/records", params={"type": "case", "q": "CE-2026-00001"})
    assert r.json()["total"] >= 1
    n = s.get(f"{API}/notifications")
    assert n.status_code == 200


def test_export_unknown_scope_not_500():
    r = sess("R17").post(f"{API}/exports", json={"scope": "records:bogus"})
    assert r.status_code < 500, r.text
