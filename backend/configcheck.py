import re
from datetime import datetime, timezone
from rbac import ROLES
from workflows import WF, ACTIONS


def _c(name, ok, detail=""):
    return {"check": name, "passed": bool(ok), "detail": detail}


async def run(target, value, wf_type=None):
    out = [_c("Proposed value is a JSON object", isinstance(value, (dict, int)), type(value).__name__)]
    if not out[0]["passed"]:
        return out
    if target == "sla_policies":
        bad = [f"{t}.{p}.{m}" for t, pr in value.items() if isinstance(pr, dict) for p, row in pr.items() if isinstance(row, dict)
               for m, v in row.items() if m != "calendar" and not (isinstance(v, (int, float)) and v > 0)]
        out.append(_c("All milestone targets are positive minutes", not bad, ", ".join(bad)))
        out.append(_c("Calendar modes valid", all(row.get("calendar", "business") in ("business", "24x7") for pr in value.values() if isinstance(pr, dict) for row in pr.values() if isinstance(row, dict))))
    elif target == "business_calendar":
        t = re.compile(r"^\d{2}:\d{2}$")
        out.append(_c("Start and end are HH:MM with start < end", t.match(str(value.get("start", ""))) and t.match(str(value.get("end", ""))) and value["start"] < value["end"]))
        out.append(_c("Workdays are 0-6", all(isinstance(d, int) and 0 <= d <= 6 for d in value.get("workdays", [None]))))
        hol_ok = True
        for h in value.get("holidays", []):
            try:
                datetime.strptime(h, "%Y-%m-%d")
            except Exception:
                hol_ok = False
        out.append(_c("Holidays are YYYY-MM-DD dates", hol_ok))
        if all(c["passed"] for c in out):
            from sla import add_business_minutes
            due = add_business_minutes(datetime.now(timezone.utc), 600, value)
            out.append(_c("Scenario: 10 business hours from now", True, due.isoformat()[:16]))
    elif target == "authority_matrix":
        for k, m in value.items():
            if k.startswith("_"):
                continue
            chain_ok = isinstance(m, dict) and all(r in ROLES for r in m.get("chain", [])) and m.get("chain")
            lim_ok = chain_ok and all(r in m.get("limits", {}) and (m["limits"][r] is None or float(m["limits"][r]) >= 0) for r in m["chain"])
            out.append(_c(f"{k}: chain roles and limits valid", lim_ok))
    elif target == "feature_flags":
        out.append(_c("All flags are booleans", all(isinstance(v, bool) for v in value.values())))
    elif target == "templates":
        out.append(_c("Each template has subject and body text", all(isinstance(v, dict) and v.get("subject") and v.get("body") for v in value.values())))
        out.append(_c("No form or input markup", "<form" not in str(value).lower() and "<input" not in str(value).lower()))
    elif target == "reopen_window_days":
        out.append(_c("Window is 1-365 days", isinstance(value, int) and 1 <= value <= 365))
    elif target == "workflow":
        if wf_type not in WF:
            out.append(_c("Workflow type exists", False, str(wf_type)))
        else:
            acts = value.get("actions", {})
            out.append(_c("Action keys exist in workflow", all(k in ACTIONS[wf_type] for k in acts), ", ".join(k for k in acts if k not in ACTIONS[wf_type])))
            out.append(_c("Roles are valid", all(r in ROLES for a in acts.values() for r in a.get("roles", []))))
            out.append(_c("No action left without roles", all(a.get("roles", [1]) for a in acts.values())))
    else:
        out.append(_c("Structure accepted", True))
    return out
