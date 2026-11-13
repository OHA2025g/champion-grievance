import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import screens  # noqa: E402
from rbac import ROLES, ACCESS  # noqa: E402
from workflows import WF, meta as wf_meta  # noqa: E402
import engine  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "docs"
OUT.mkdir(exist_ok=True)
reg = screens.registry()

lines = ["# Screen coverage report (generated from backend/screens.py)", "", f"Total screens: {len(reg)} · mapped: {sum(1 for s in reg if s['kind'] != 'unmapped')}", "",
         "| Screen | Role | Title | Renderer | Record type | Focus actions | Workflow | FR |", "|---|---|---|---|---|---|---|---|"]
for s in reg:
    lines.append(f"| {s['id']} | {s['role']} | {s['title']} | {s['kind']} | {s.get('t', '')} | {', '.join(s.get('focus') or [])} | {s['workflow']} | {s['fr']} |")
(OUT / "SCREEN_COVERAGE.md").write_text("\n".join(lines) + "\n")

types = list(ACCESS)
lines = ["# Role permission matrix (generated from backend/rbac.py and workflows.py)", "", "Scopes: all, own, org, owner, tech, tech_case, centre, region, assigned, approver, customer, hr, minimal, ro (read-only).", "",
         "| Role | Name | Workspace | Home | " + " | ".join(types) + " |", "|" + "---|" * (4 + len(types))]
for code, (name, ws, scope, home) in ROLES.items():
    lines.append(f"| {code} | {name} | {ws} | {home} | " + " | ".join(ACCESS[t].get(code, "") for t in types) + " |")
lines += ["", "## Workflow actions and permitted roles", ""]
for t, w in WF.items():
    lines += [f"### {w['label']} (`{t}`)", "", "| Action | Key | From | To | Roles |", "|---|---|---|---|---|"]
    m = wf_meta()[t]
    for a in m["actions"]:
        lines.append(f"| {a['label']} | {a['key']} | {', '.join(a['from'])} | {a['to'] or '(conditional)'} | {', '.join(engine.action_roles(t, a))} |")
    lines.append("")
(OUT / "ROLE_PERMISSION_MATRIX.md").write_text("\n".join(lines) + "\n")

lines = ["# Workflow definitions (generated from backend/workflows.py)", ""]
for t, w in WF.items():
    lines += [f"## {w['label']} (`{t}`, prefix {w['prefix']})", "", f"Initial state: `{w['initial']}`", "", "| State | Label | Next action | Terminal |", "|---|---|---|---|"]
    for k, s in w["states"].items():
        lines.append(f"| {k} | {s['label']} | {s['next']} | {'yes' if s['terminal'] else ''} |")
    lines += ["", "Create forms: " + ", ".join(f"{k} ({', '.join(v['roles'])})" for k, v in w["create"].items()), ""]
(OUT / "WORKFLOWS.md").write_text("\n".join(lines) + "\n")

from server import app  # noqa: E402
lines = ["# API endpoint inventory (generated from FastAPI routes)", "", "All endpoints are prefixed with /api. Interactive docs: /docs on the backend.", "", "| Method | Path | Handler |", "|---|---|---|"]
for r in app.routes:
    if getattr(r, "methods", None) and r.path.startswith("/api"):
        for mth in sorted(r.methods - {"HEAD", "OPTIONS"}):
            lines.append(f"| {mth} | {r.path} | {r.name} |")
(OUT / "API_ENDPOINTS.md").write_text("\n".join(lines) + "\n")
print("docs written to", OUT)
