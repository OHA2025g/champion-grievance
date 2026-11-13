# Iteration 2 regression: role-in-JWT, idempotency, admin self-protection, config change 2-admin flow, settlement reconcile, customer confirm/reopen/appeal
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = BASE_URL + "/api"
PW = "Champion@2026"
OWNER = ("singh.aghoreshwar@gmail.com", "ChampionAdmin#2026")
ADMIN2 = ("admin2.ops@demo.champion.test", PW)
_s = {}
CTX = {}


def login(email, pw=PW):
    if email not in _s:
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
        if r.status_code == 429:
            time.sleep(40)
            r = s.post(f"{API}/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 200, r.text
        _s[email] = s
    return _s[email]


def rec(s, rid):
    r = s.get(f"{API}/records/{rid}")
    assert r.status_code == 200, r.text
    return r.json()


def do(s, rid, key, values, headers=None):
    return s.post(f"{API}/records/{rid}/actions/{key}", json={"values": values}, headers=headers or {})


def find(s, rtype, pred):
    r = s.get(f"{API}/records", params={"type": rtype, "size": 100}).json()
    items = r.get("items", r) if isinstance(r, dict) else r
    return [i for i in items if pred(i)]


# ---- (a) active role carried in JWT ----
class TestRoleSwitch:
    def test_switch_role_r04(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": "rohan.mehta@demo.champion.test", "password": PW})
        assert r.status_code == 200
        r = s.post(f"{API}/auth/switch-role", json={"role": "R04"})
        assert r.status_code == 200, r.text
        assert r.json()["active_role"] == "R04"
        assert s.get(f"{API}/auth/me").json()["active_role"] == "R04"
        # separate context logs in fresh; first session must keep R04
        s2 = requests.Session()
        r2 = s2.post(f"{API}/auth/login", json={"email": "rohan.mehta@demo.champion.test", "password": PW})
        assert r2.status_code == 200
        assert s.get(f"{API}/auth/me").json()["active_role"] == "R04"
        # switch back in s2 to R05 should not affect s
        s2.post(f"{API}/auth/switch-role", json={"role": "R05"})
        assert s2.get(f"{API}/auth/me").json()["active_role"] == "R05"
        assert s.get(f"{API}/auth/me").json()["active_role"] == "R04"
        # role not held
        assert s.post(f"{API}/auth/switch-role", json={"role": "R18"}).status_code == 403


# ---- (b) idempotency ----
class TestIdempotency:
    def test_idempotency_replay_and_mismatch(self):
        s = login("aarav.sharma@demo.champion.test")
        cases = find(s, "case", lambda i: i["state"] in ("in_progress",))
        assert len(cases) >= 2, cases
        a, b = cases[0]["id"], cases[1]["id"]
        k = "TEST_" + uuid.uuid4().hex
        v = {"message": "TEST_ idempotency update"}
        r1 = do(s, a, "add_update", v, {"Idempotency-Key": k})
        assert r1.status_code == 200, r1.text
        assert not r1.json().get("replayed")
        r2 = do(s, a, "add_update", v, {"Idempotency-Key": k})
        assert r2.status_code == 200 and r2.json().get("replayed") is True, r2.text
        r3 = do(s, b, "add_update", v, {"Idempotency-Key": k})
        assert r3.status_code == 409, r3.text
        assert "idempotency_mismatch" in r3.text


# ---- (c) admin self-protection ----
class TestAdminSelf:
    def test_cannot_disable_self(self):
        s = login(*OWNER)
        me = s.get(f"{API}/auth/me").json()
        r = s.patch(f"{API}/admin/users/{me['id']}", json={"status": "disabled", "approval_reference": "TEST_REF"})
        assert r.status_code == 403, r.text
        r = s.patch(f"{API}/admin/users/{me['id']}", json={"roles": ["R18", "R13"], "approval_reference": "TEST_REF"})
        assert r.status_code == 403
        assert s.get(f"{API}/auth/me").json()["status"] == "active"


# ---- CE-153 config change two-admin release ----
class TestConfigChange:
    def test_01_create_and_prepare(self):
        s = login(*OWNER)
        cfg = s.get(f"{API}/admin/config").json()["items"]
        cur = [c for c in cfg if c["key"] == "reopen_window_days"]
        CTX["v0"] = cur[0]["version"] if cur else None
        CTX["val0"] = cur[0]["value"] if cur else None
        r = s.post(f"{API}/records/config_change/change", json={"values": {
            "target": "reopen_window_days", "change_summary": "TEST_ reopen window to 45", "approval_reference": "TEST_APR",
            "proposed_value": 45}})
        if r.status_code != 200:
            r = s.post(f"{API}/records/config_change/change", json={"values": {
                "target": "reopen_window_days", "change_summary": "TEST_ reopen window to 45", "approval_reference": "TEST_APR",
                "proposed_value": "45"}})
        assert r.status_code in (200, 201), r.text
        body = r.json()
        rid = body.get("id") or body.get("record", {}).get("id")
        CTX["cfg"] = rid
        assert do(s, rid, "check_scope", {"within_scope": "Yes", "note": "TEST_ ok"}).status_code == 200
        r = do(s, rid, "run_tests", {"scenario_note": "TEST_"})
        assert r.status_code == 200, r.text
        g = rec(s, rid)
        assert g["record"]["state"] if "record" in g else g["state"]
        st = (g.get("record") or g)["state"]
        assert st == "tested", f"state {st} results {(g.get('record') or g).get('test_results')}"
        # release before approval must fail
        r = do(s, rid, "request_release", {"note": "TEST_ release"})
        assert r.status_code == 200, r.text

    def test_02_release_blocked_without_approval(self):
        s = login(*OWNER)
        r = do(s, CTX["cfg"], "release", {"note": "TEST_"})
        assert r.status_code == 409, r.text

    def test_03_requester_cannot_approve(self):
        s = login(*OWNER)
        g = rec(s, CTX["cfg"])
        aps = [c for c in g.get("children", []) if c["type"] == "approval"]
        assert aps, g.get("children")
        CTX["apr"] = aps[-1]["id"]
        r = do(s, CTX["apr"], "approve", {"decision_note": "TEST_ self", "evidence_checked": "Yes"})
        assert r.status_code == 403, r.text

    def test_04_second_admin_approves(self):
        s = login(*ADMIN2)
        inbox = s.get(f"{API}/inbox").json()
        CTX["inbox_has"] = CTX["apr"] in str(inbox)
        r = do(s, CTX["apr"], "approve", {"decision_note": "TEST_ second admin", "evidence_checked": "Yes"})
        assert r.status_code == 200, r.text
        assert (rec(s, CTX["cfg"]).get("record") or rec(s, CTX["cfg"]))["release_approved"] is True

    def test_05_release_increments_version(self):
        s = login(*OWNER)
        r = do(s, CTX["cfg"], "release", {"note": "TEST_ go"})
        assert r.status_code == 200, r.text
        cfg = {c["key"]: c for c in s.get(f"{API}/admin/config").json()["items"]}
        assert cfg["reopen_window_days"]["value"] in (45, "45")
        assert cfg["reopen_window_days"]["version"] == (CTX["v0"] or 0) + 1
        vers = s.get(f"{API}/admin/config/reopen_window_days/versions").json()
        assert len(vers.get("items", vers)) >= 2

    def test_06_rollback(self):
        s = login(*OWNER)
        r = do(s, CTX["cfg"], "rollback", {"reason": "TEST_ rollback after regression test"})
        assert r.status_code == 200, r.text
        cfg = {c["key"]: c for c in s.get(f"{API}/admin/config").json()["items"]}
        assert cfg["reopen_window_days"]["value"] == CTX["val0"]


# ---- CE-087/088/090 settlement ----
class TestSettlement:
    def test_settlement_to_reconciled(self):
        s = login("deepak.menon@demo.champion.test")
        st = find(s, "settlement", lambda i: i["state"] == "pending_validation")
        assert st
        rid = st[-1]["id"]
        g = rec(s, rid)
        r0 = g.get("record") or g
        amt = r0.get("amount") or r0.get("data", {}).get("amount")
        r = do(s, rid, "validate_recipient", {"original_transaction": r0.get("data", {}).get("original_transaction") or "TEST_TXN", "approved_amount": amt,
                                             "beneficiary_reference": "TEST_BEN", "account_ending": "1234", "recipient_authority": "Customer",
                                             "verification_evidence": "TEST_ evidence"})
        assert r.status_code == 200, r.text
        st1 = (rec(s, rid).get("record") or rec(s, rid))["state"]
        assert st1 == "recipient_validated", st1
        r = do(s, rid, "submit_instruction", {"method": "Bank transfer (simulated adapter)", "confirm": "I confirm this matches the approved instruction"})
        assert r.status_code == 200, r.text
        cur = rec(s, rid).get("record") or rec(s, rid)
        if cur["state"] != "executed":
            r = do(s, rid, "check_status", {})
            assert r.status_code == 200, r.text
            cur = rec(s, rid).get("record") or rec(s, rid)
        assert cur["state"] == "executed", cur["state"]
        r = do(s, rid, "reconcile", {"ledger_reference": "TEST_LEDGER", "ledger_amount": cur.get("executed_amount") or amt})
        assert r.status_code == 200, r.text
        assert (rec(s, rid).get("record") or rec(s, rid))["state"] == "reconciled"
        CTX["stl"] = r0["ref"]


# ---- CE-012/013/014 customer ----
class TestCustomer:
    def test_01_confirm_resolved(self):
        s = login("aarav.sharma@demo.champion.test")
        c = find(s, "case", lambda i: i["ref"] == "CE-2026-00006")[0]
        assert c["state"] == "resolved"
        r = do(s, c["id"], "customer_confirm", {"rating": "4", "comment": "TEST_ thanks"})
        assert r.status_code == 200, r.text
        assert (rec(s, c["id"]).get("record") or rec(s, c["id"]))["state"] == "closed"
        CTX["c6"] = c["id"]

    def test_02_appeal_on_closed(self):
        s = login("aarav.sharma@demo.champion.test")
        r = do(s, CTX["c6"], "request_review", {"original_decision": "Closure outcome", "reason": "TEST_ disagree with closure",
                                               "requested_outcome": "Re-assessment", "contact_pref": "Email", "explanation": "TEST_ explanation"})
        if r.status_code == 422:
            g = rec(s, CTX["c6"])
            a = [x for x in g["actions"] if x["key"] == "request_review"][0]
            opts = [f for f in a["fields"] if f["k"] == "contact_pref"][0]["opts"]
            r = do(s, CTX["c6"], "request_review", {"original_decision": "Closure outcome", "reason": "TEST_ disagree with closure",
                                                   "requested_outcome": "Re-assessment", "contact_pref": opts[0], "explanation": "TEST_ explanation"})
        assert r.status_code == 200, r.text
        g = rec(s, CTX["c6"])
        assert any(c["type"] == "appeal" for c in g.get("children", [])), g.get("children")

    def test_03_reopen_closed(self):
        s = login("aarav.sharma@demo.champion.test")
        c = find(s, "case", lambda i: i["ref"] == "CE-2026-00007")[0]
        g = rec(s, c["id"])
        a = [x for x in g["actions"] if x["key"] == "reopen"]
        assert a, [x["key"] for x in g["actions"]]
        opts = [f for f in a[0]["fields"] if f["k"] == "preferred_contact"][0]["opts"]
        r = do(s, c["id"], "reopen", {"issue_returned_on": "2026-10-20", "recurring_symptom": "TEST_ same noise",
                                      "unresolved": "TEST_ still not working", "preferred_contact": opts[0]})
        assert r.status_code == 200, r.text
        assert (rec(s, c["id"]).get("record") or rec(s, c["id"]))["state"] == "reopened"
