import json
from core import ROOT

# UI configuration for every reference screen. kind = renderer; t = record type; st = state filter; f = filter; focus = highlighted actions.
O = "open"
CFG = {
    "CE-001": dict(kind="login"), "CE-002": dict(kind="otp"), "CE-003": dict(kind="recover"), "CE-004": dict(kind="prefs"), "CE-146": dict(kind="components"),
    # R01 customer
    "CE-005": dict(kind="dashboard"),
    "CE-006": dict(kind="list", t="case", cols=["ref", "product", "data.issue_category", "state", "next_action"], create="CE-007", row="CE-008"),
    "CE-007": dict(kind="create", t="case", sub="customer_complaint", after="CE-009"),
    "CE-008": dict(kind="record", t="case", variant="timeline", focus=["add_update", "provide_information"]),
    "CE-009": dict(kind="upload", t="case", st=O),
    "CE-010": dict(kind="record", t="job", st="appointment_proposed", focus=["customer_confirm_appointment", "customer_request_reschedule"], cols=["ref", "title", "appointment.start", "state"]),
    "CE-011": dict(kind="record", t="job", f={"estimate_state": "pending"}, focus=["customer_accept_estimate", "customer_decline_estimate"], panels=["estimate"]),
    "CE-012": dict(kind="record", t="case", st="resolved", focus=["customer_confirm", "customer_reject"]),
    "CE-013": dict(kind="record", t="case", st="closed", focus=["reopen"]),
    "CE-014": dict(kind="record", t="case", st="closed,resolved,in_progress", focus=["request_review"]),
    "CE-150": dict(kind="record", t="case", st=O, focus=["submit_verification"]),
    # R02 dealer
    "CE-015": dict(kind="dashboard"),
    "CE-016": dict(kind="create", t="case", sub="dealer_customer_case"),
    "CE-017": dict(kind="create", t="case", sub="stock_claim"),
    "CE-018": dict(kind="record", t="case", sub="dealer_customer_case,stock_claim", st=O, focus=["confirm_sale", "submit_verification"]),
    "CE-019": dict(kind="record", t="case", sub="dealer_customer_case,stock_claim", st="in_progress,resolved", focus=["confirm_handover", "customer_confirm"]),
    "CE-020": dict(kind="list", t="settlement", cols=["ref", "root_ref", "amount", "provider_ref", "state"]),
    # R03 distributor
    "CE-021": dict(kind="dashboard"),
    "CE-022": dict(kind="orders"),
    "CE-023": dict(kind="create", t="case", sub="bulk_grievance", after="CE-024"),
    "CE-024": dict(kind="record", t="case", sub="bulk_grievance", st=O, focus=["validate_units"], panels=["units"]),
    "CE-025": dict(kind="list", t="unit", cols=["data.site", "data.serial", "job_ref", "state", "root_ref"]),
    "CE-026": dict(kind="record", t="case", sub="bulk_grievance", focus=["reconcile_bulk", "customer_confirm"], panels=["units", "reconcile"]),
    # R04 support agent
    "CE-027": dict(kind="dashboard"),
    "CE-028": dict(kind="list", t="contact", cols=["data.channel", "created_at", "data.customer_name", "title", "owner_name", "state"], create_type="contact/manual", row="CE-030"),
    "CE-029": dict(kind="customer_search"),
    "CE-030": dict(kind="record", t="contact", st="new,in_review", focus=["open_contact", "register_case", "link_to_case", "close_contact"]),
    "CE-031": dict(kind="record", t="case", st="registered,awaiting_owner,in_progress,safety_escalated", focus=["escalate_safety"], panels=["safety"]),
    "CE-032": dict(kind="record", t="case", st="registered", focus=["link_duplicate", "not_duplicate"], panels=["duplicates"]),
    "CE-033": dict(kind="record", t="case", st="registered,safety_escalated,reopened", focus=["register_route"]),
    "CE-141": dict(kind="customer_search", variant="empty"),
    "CE-148": dict(kind="record", t="case", st=O, focus=["save_translation"], panels=["translation"]),
    "CE-157": dict(kind="quarantine_evidence"),
    # R05 case owner
    "CE-034": dict(kind="dashboard"),
    "CE-035": dict(kind="record", t="case", st=O, focus=["plan_resolution", "create_service_job", "request_remedy_approval", "request_warranty_review", "escalate_case", "mark_resolved"]),
    "CE-036": dict(kind="kanban", t="task", create_screen="CE-151"),
    "CE-037": dict(kind="calendar"),
    "CE-038": dict(kind="record", t="case", st="awaiting_owner,reopened", focus=["accept_ownership", "decline_ownership"]),
    "CE-039": dict(kind="sla"),
    "CE-040": dict(kind="record", t="case", st="in_progress,resolved,waiting,evidence_requested", focus=["send_update"], panels=["comms"]),
    "CE-041": dict(kind="record", t="case", st="resolved", focus=["verify_and_close"]),
    "CE-140": dict(kind="create", t="case", sub="service_request"),
    "CE-143": dict(kind="record", t="case", st="in_progress,resolved", focus=["mark_resolved", "verify_and_close"], panels=["blocking"]),
    "CE-147": dict(kind="record", t="case", st=O, panels=["ai"], focus=[]),
    "CE-151": dict(kind="record", t="case", st=O, focus=["create_linked_task"]),
    "CE-152": dict(kind="record", t="case", st="in_progress,waiting", focus=["record_waiting", "resume_work"], panels=["sla"]),
    "CE-154": dict(kind="record", t="case", st="resolved", focus=["request_supervised_closure"]),
    # R06 technician (mobile)
    "CE-042": dict(kind="m_dashboard"), "CE-043": dict(kind="m_jobs"),
    "CE-044": dict(kind="m_job", focus=["record_arrival"]), "CE-045": dict(kind="m_job", focus=["submit_diagnosis"]),
    "CE-046": dict(kind="m_job", focus=["request_parts"]), "CE-047": dict(kind="m_job", focus=["submit_estimate"]),
    "CE-048": dict(kind="m_job", focus=["record_repair"]), "CE-049": dict(kind="m_job", focus=["submit_tests"]),
    "CE-050": dict(kind="m_job", focus=["submit_handover"]), "CE-051": dict(kind="m_sync"),
    # R07 centre
    "CE-052": dict(kind="dashboard"),
    "CE-053": dict(kind="roster"),
    "CE-054": dict(kind="record", t="job", st="created,allocated,appointment_proposed,appointment_confirmed", focus=["allocate", "propose_appointment", "confirm_on_behalf", "confirm_dispatch", "request_support"],
                   cols=["ref", "technician_name", "skill", "parts_pending", "appointment.start", "state"]),
    "CE-055": dict(kind="record", t="job", st="completed", focus=["accept_report", "return_for_correction"]),
    "CE-056": dict(kind="record", t="job", st="dispatched,appointment_confirmed,missed", focus=["record_missed_visit", "allocate", "propose_appointment"]),
    # R08 technical
    "CE-057": dict(kind="dashboard"),
    "CE-058": dict(kind="list", t="tech_review", cols=["ref", "root_ref", "product", "data.diagnosis", "repeat_count", "state", "created_at"], row="CE-060"),
    "CE-059": dict(kind="record", t="tech_review", st="pending,recommended", focus=["request_inspection"], panels=["prior_repairs"]),
    "CE-060": dict(kind="record", t="tech_review", st="pending,further_inspection", focus=["record_recommendation", "close_review"], panels=["prior_repairs"]),
    "CE-061": dict(kind="record", t="tech_review", st="recommended", focus=["submit_decision"]),
    "CE-149": dict(kind="knowledge"),
    # R09 regional
    "CE-062": dict(kind="dashboard"),
    "CE-063": dict(kind="list", t="case", st=O, sort="created_at", cols=["region", "ref", "created_at", "priority", "sla_state", "owner_name", "state"], row_generic=True),
    "CE-064": dict(kind="capacity"),
    "CE-065": dict(kind="record", t="escalation", st="open,revision,recovery_assigned", focus=["assign_recovery_owner", "escalate_national"]),
    "CE-066": dict(kind="record", t="escalation", st="verification,recovery_assigned,authorised", focus=["record_recovery_result", "submit_recovery_update"]),
    # R10 national
    "CE-067": dict(kind="dashboard"),
    "CE-068": dict(kind="network"),
    "CE-069": dict(kind="record", t="escalation", st="referred_national,authorised,verification", focus=["coordinate_plan", "record_recovery_result"]),
    "CE-070": dict(kind="list", t="policy", sub="service_standard", cols=["title", "data.version", "data.coverage", "data.effective", "created_by_name", "state"], create_type="policy/service_standard"),
    # R11 warranty
    "CE-071": dict(kind="dashboard"),
    "CE-072": dict(kind="list", t="warranty", cols=["ref", "product", "data.purchase_date", "purchase_verified", "coverage", "sla_due", "state"], row="CE-074"),
    "CE-073": dict(kind="list", t="policy", sub="warranty_term", cols=["data.component", "data.version", "data.coverage_basis", "data.evidence_required", "data.effective", "state"], create="CE-161"),
    "CE-074": dict(kind="record", t="warranty", st="submitted,diagnosis_review,clarification_requested", focus=["check_evidence", "record_coverage_decision"]),
    "CE-075": dict(kind="record", t="warranty", st="decision_recorded,communicated", focus=["explain_decision", "route_dispute", "close_claim"]),
    "CE-161": dict(kind="create", t="policy", sub="warranty_term"),
    # R12 parts
    "CE-076": dict(kind="dashboard"),
    "CE-077": dict(kind="list", t="requisition", cols=["ref", "job_ref", "data.part", "data.quantity", "data.required_by", "state"], row="CE-079"),
    "CE-078": dict(kind="stock"),
    "CE-079": dict(kind="record", t="requisition", st="requested,validated,awaiting_stock", focus=["validate_requisition", "reserve_stock", "mark_unavailable", "receive_stock"]),
    "CE-080": dict(kind="record", t="requisition", st="reserved,dispatched,delivered", focus=["dispatch", "record_delivery", "record_usage"]),
    "CE-081": dict(kind="record", t="requisition", st="delivery_exception", focus=["resolve_exception"]),
    "CE-082": dict(kind="record", t="return", st="expected,received", focus=["record_receipt", "close_return"], cols=["ref", "data.item", "data.batch", "state"]),
    "CE-083": dict(kind="record", t="return", f={"quarantine": True}, focus=["record_receipt", "open_restricted_examination", "close_return"], cols=["ref", "data.item", "data.batch", "parent_ref", "state"]),
    "CE-084": dict(kind="movements"),
    "CE-155": dict(kind="create", t="replacement", sub="replacement"),
    "CE-156": dict(kind="record", t="replacement", focus=["schedule_delivery", "record_replacement_delivery", "record_collection", "record_milestone_exception"]),
    # R13 finance
    "CE-085": dict(kind="dashboard"),
    "CE-086": dict(kind="list", t="settlement", cols=["ref", "root_ref", "amount", "approval_ref", "recipient_verified", "state"], row="CE-087"),
    "CE-087": dict(kind="record", t="settlement", st="pending_validation,discrepancy", focus=["validate_recipient", "resolve_discrepancy"]),
    "CE-088": dict(kind="record", t="settlement", st="recipient_validated,failed", focus=["submit_instruction"]),
    "CE-089": dict(kind="record", t="settlement", st="outcome_unknown", focus=["check_status"]),
    "CE-090": dict(kind="record", t="settlement", st="executed", focus=["reconcile"]),
    "CE-091": dict(kind="create", t="settlement", sub="credit_note"),
    "CE-092": dict(kind="record", t="settlement", st="executed,reconciled", focus=["request_correction"]),
    "CE-144": dict(kind="record", t="settlement", st="pending_confirmation", focus=["check_status"]),
    # R14 quality
    "CE-093": dict(kind="dashboard"),
    "CE-094": dict(kind="list", t="incident", st="reported,containment", cols=["ref", "title", "data.hazard", "severity", "root_ref", "created_at", "state"], row="CE-095", create_type="incident/incident"),
    "CE-095": dict(kind="record", t="incident", st="reported,containment,investigation", focus=["triage", "record_containment", "preserve_evidence"]),
    "CE-096": dict(kind="record", t="incident", st="containment,investigation", focus=["link_units"], panels=["exposure"]),
    "CE-097": dict(kind="record", t="incident", st="investigation", focus=["submit_findings"], panels=["ai_root"]),
    "CE-098": dict(kind="kanban", t="capa"),
    "CE-099": dict(kind="record", t="incident", st="rca_complete,capa_in_progress,effectiveness_check", focus=["plan_capa", "request_verification", "verify_effectiveness"]),
    # R15 channel
    "CE-100": dict(kind="dashboard"),
    "CE-101": dict(kind="list", t="channel_dispute", cols=["ref", "org_name", "title", "data.customer_impact", "next_action", "state"], row="CE-102", create_type="channel_dispute/dispute"),
    "CE-102": dict(kind="record", t="channel_dispute", st="open,clarification_requested,facts_reconciled", focus=["request_clarification", "clarification_received", "record_findings", "decide_dispute"]),
    "CE-103": dict(kind="record", t="channel_dispute", st="recovery_in_progress,follow_up,verification", focus=["assign_recovery", "record_action_status", "verify_outcome"]),
    # R16 appeals
    "CE-104": dict(kind="dashboard"),
    "CE-105": dict(kind="record", t="appeal", st="registered", focus=["assign_reviewer"], cols=["ref", "root_ref", "data.reason", "reviewer_name", "conflict_check", "sla_due"]),
    "CE-106": dict(kind="record", t="appeal", st="under_review,explanations_requested", focus=["record_findings", "request_explanation", "explanation_received"]),
    "CE-107": dict(kind="record", t="appeal", st="under_review,decided_upheld,remedy_in_progress", focus=["issue_decision", "assign_remedy", "verify_remedy", "close_appeal"]),
    "CE-108": dict(kind="list", t="correspondence", cols=["data.reference", "data.authority", "data.received", "data.verified_deadline", "assignee_name", "state"], create_type="correspondence/correspondence", row_generic=True),
    # R17 executive
    "CE-109": dict(kind="dashboard"),
    "CE-110": dict(kind="analytics", variant="product"), "CE-111": dict(kind="analytics", variant="performance"), "CE-112": dict(kind="analytics", variant="costs"),
    "CE-113": dict(kind="kanban", t="mgmt_action", create_type="mgmt_action/action"),
    "CE-114": dict(kind="exports"),
    # R18 admin
    "CE-115": dict(kind="dashboard"), "CE-116": dict(kind="admin_users"), "CE-117": dict(kind="admin_permissions"),
    "CE-118": dict(kind="models"),
    "CE-119": dict(kind="list", t="policy", cols=["title", "subtype", "created_by_name", "data.effective", "state"], create_type="policy/policy", row_generic=True),
    "CE-120": dict(kind="admin_config", key="business_calendar"), "CE-121": dict(kind="admin_config", key="authority_matrix"), "CE-122": dict(kind="admin_config", key="templates"),
    "CE-123": dict(kind="admin_integrations"), "CE-124": dict(kind="admin_events"), "CE-125": dict(kind="admin_retention"), "CE-126": dict(kind="admin_audit"),
    "CE-142": dict(kind="forbidden"), "CE-145": dict(kind="integration_error"),
    "CE-153": dict(kind="record", t="config_change", st="requested,clarification,configured,test_failed,tested,awaiting_release,released", focus=["check_scope", "edit_proposal", "run_tests", "request_release", "release", "rollback"], create_type="config_change/change"),
    "CE-158": dict(kind="invite"), "CE-159": dict(kind="create", t="policy", sub="product_model"), "CE-160": dict(kind="create", t="legal_hold", sub="hold"),
    # R19 HR
    "CE-127": dict(kind="dashboard"), "CE-128": dict(kind="create", t="hr_grievance", sub="grievance"),
    "CE-129": dict(kind="record", t="hr_grievance", st="received,designated_referral,investigation,decision_pending", focus=["triage", "referral_accepted", "save_findings", "submit_for_decision", "record_decision"]),
    "CE-130": dict(kind="record", t="hr_grievance", st="implementation,escalated,follow_up", focus=["record_implementation", "verify_follow_up"]),
    # R20 supplier
    "CE-131": dict(kind="dashboard"), "CE-132": dict(kind="create", t="supplier_dispute", sub="dispute"),
    "CE-133": dict(kind="record", t="supplier_dispute", st="registered,reconciling,input_requested", focus=["reconcile_lines", "request_input", "input_received", "record_commercial_decision"], panels=["lines"]),
    "CE-134": dict(kind="record", t="supplier_dispute", st="correction_approval,correction_in_progress,follow_up", focus=["execute_correction", "verify_settlement"]),
    # R21 audit
    "CE-135": dict(kind="dashboard"),
    "CE-136": dict(kind="record", t="audit", st="scoping", focus=["save_scope"], create_type="audit/engagement"),
    "CE-137": dict(kind="record", t="audit", st="fieldwork,reporting", focus=["record_observation", "complete_fieldwork", "complete_audit"], panels=["sample"]),
    "CE-138": dict(kind="list", t="audit_finding", cols=["ref", "title", "data.severity", "data.record_ref", "action_owner_name", "data.due", "state"], create_type="audit_finding/finding", row="CE-139"),
    "CE-139": dict(kind="record", t="audit_finding", st="submitted,remediation,open", focus=["record_retest"]),
}

_inv = json.loads((ROOT / "data" / "screen_inventory.json").read_text())
_wf = json.loads((ROOT / "data" / "workflow_navigation.json").read_text())
_wf_of = {s: w["name"] for w in _wf for s in w["screens"]}


def registry():
    out = []
    for s in _inv:
        cfg = CFG.get(s["id"], {"kind": "unmapped"})
        out.append({"id": s["id"], "role": "R%02d" % s["role"] if s["role"] else "shared", "title": s["title"], "layout": s["kind"], "fields": s["fields"],
                    "col_labels": s["cols"], "action": s["action"], "fr": s["fr"], "workflow": _wf_of.get(s["id"], "Shared access"), "image": s["filename"], **cfg})
    return out
