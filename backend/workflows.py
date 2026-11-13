"""Executable workflow definitions for every record type (derived from the 21 role workflow infographics)."""


def F(k, l, t="text", req=True, opts=None, src=None, **kw):
    if isinstance(opts, str):
        opts = opts.split("|")
    return {"k": k, "l": l, "t": t, "req": req, "opts": opts or [], "src": src, **kw}


def S(label, tone, nxt="", terminal=False):
    return {"label": label, "tone": tone, "next": nxt, "terminal": terminal}


def A(key, label, frm, to, roles, *fields, who=None, cust=False, ev=0, sub=None, tpl=None, notify=None, meet=None, start=None, danger=False):
    return {"key": key, "label": label, "from": frm, "to": to, "roles": roles, "fields": list(fields), "who": who,
            "cust": cust, "ev": ev, "sub": sub, "tpl": tpl, "notify": notify or [], "meet": meet or [], "start": start or [], "danger": danger}


YN = "Yes|No"
PRI = "P1 - Critical|P2 - High|P3 - Normal|P4 - Low"
CATS = "Air cooler|Water heater|Pump|Room heater|Fan|Kitchen appliance|Power backup|Other"
ISSUES = "Not working|Performance issue|Noise or vibration|Leakage|Physical damage|Installation issue|Electrical fault|Billing or invoice|Delivery issue|Other"
SAFETY = "No hazard reported|Electric shock|Burning smell or smoke|Fire or sparks|Water near live power|Other hazard"
CONTACT = "Phone call|SMS|WhatsApp|Email|Portal message"
CHANNELS = "Phone|Email|WhatsApp|Web chat|Social media|Walk-in|Dealer referral"
STAFF_SRC = "users:staff"
ALL_INTERNAL = ["R04", "R05", "R07", "R08", "R09", "R10", "R11", "R12", "R13", "R14", "R15", "R16", "R20"]
OPEN = "*open"

COMPLAINT_FIELDS = [
    F("product_category", "Product category", "select", opts=CATS), F("model_id", "Model or unknown", "lookup", src="models", req=False),
    F("serial", "Serial number optional", req=False), F("purchase_date", "Purchase date optional", "date", req=False),
    F("issue_category", "Issue category", "select", opts=ISSUES), F("description", "Describe the problem", "textarea", minlen=15),
    F("address", "Service address"), F("pin", "PIN code", pattern=r"^\d{6}$", hint="6 digit PIN code"),
    F("preferred_contact", "Preferred contact", "select", opts=CONTACT), F("safety_concern", "Safety concern", "select", opts=SAFETY),
]

WF = {}

WF["case"] = {
    "label": "Case", "prefix": "CE",
    "states": {
        "registered": S("Registered", "info", "Route to accountable owner"),
        "safety_escalated": S("Safety escalation", "urgent", "Specialist containment and owner routing"),
        "awaiting_owner": S("Awaiting owner acceptance", "pending", "Owner to accept ownership"),
        "in_progress": S("In progress", "info", "Execute case plan"),
        "evidence_requested": S("Information requested", "pending", "Complainant to provide information"),
        "waiting": S("Approved waiting period", "blocked", "Resume when dependency clears"),
        "resolved": S("Resolved - pending verification", "pending", "Verify outcome and close"),
        "reopened": S("Reopened", "urgent", "Owner to re-accept and replan"),
        "closed": S("Closed", "done", "", True),
        "duplicate": S("Linked as duplicate", "muted", "", True),
    },
    "initial": "registered",
    "create": {
        "customer_complaint": {"label": "Customer complaint", "roles": ["R01"], "fields": COMPLAINT_FIELDS},
        "support_ticket": {"label": "Support ticket", "roles": ["R04"], "fields": [
            F("customer_id", "Complainant", "lookup", src="customers"), F("submitting_party", "Submitting party", "select", opts="Customer|Dealer|Distributor|Representative"),
            F("source_channel", "Source channel", "select", opts=CHANNELS), F("source_reference", "Source reference", req=False),
            F("model_id", "Product", "lookup", src="models", req=False), F("serial", "Serial number", req=False),
            F("description", "Original complaint words", "textarea", minlen=10), F("issue_category", "Category", "select", opts=ISSUES),
            F("impact", "Impact", "select", opts="Product unusable|Partially usable|Cosmetic|Business impact"),
            F("priority", "Priority", "select", opts=PRI), F("priority_reason", "Priority reason", req=False),
            F("safety_concern", "Safety screening", "select", opts=SAFETY)]},
        "service_request": {"label": "Service request", "roles": ["R05", "R04"], "fields": [
            F("customer_id", "Customer", "lookup", src="customers"), F("product_category", "Product category", "select", opts=CATS),
            F("model_id", "Model", "lookup", src="models"), F("address", "Service address"), F("pin", "PIN code", pattern=r"^\d{6}$", hint="6 digit PIN code"),
            F("preferred_contact", "Preferred contact", "select", opts=CONTACT), F("description", "Issue description", "textarea", minlen=15),
            F("safety_concern", "Safety concern", "select", opts=SAFETY, req=False)]},
        "dealer_customer_case": {"label": "Dealer customer case", "roles": ["R02"], "fields": [
            F("customer_name", "Customer name"), F("customer_contact", "Verified contact"), F("representation", "Customer representation", "select", opts="Customer consent recorded|Customer present at counter|Authorised representative"),
            F("invoice", "Invoice number"), F("model_id", "Product model", "lookup", src="models"), F("serial", "Serial number"),
            F("issue_category", "Problem category", "select", opts=ISSUES), F("description", "Issue description", "textarea", minlen=10),
            F("address", "Service address"), F("purchase_date", "Purchase date", "date"), F("safety_concern", "Safety concern", "select", opts=SAFETY)]},
        "stock_claim": {"label": "Damaged stock claim", "roles": ["R02"], "fields": [
            F("delivery_ref", "Delivery reference"), F("invoice", "Invoice number"), F("model_id", "Model", "lookup", src="models"),
            F("quantity", "Affected quantity", "number", min=1), F("serials", "Serial or batch numbers", "textarea"),
            F("description", "Damage description", "textarea", minlen=10), F("receipt_date", "Receipt date", "date"),
            F("evidence_note", "Evidence", hint="Upload photos after submission", req=False), F("amount", "Claimed value (INR)", "number", req=False)]},
        "bulk_grievance": {"label": "Bulk grievance", "roles": ["R03"], "fields": [
            F("order_ref", "Order reference", "lookup", src="orders"), F("organisation", "Organisation", req=False),
            F("model_id", "Affected model", "lookup", src="models"), F("quantity", "Affected quantity", "number", min=1),
            F("issue_category", "Issue category", "select", opts=ISSUES), F("business_impact", "Business impact", "textarea"),
            F("requested_outcome", "Requested outcome", "select", opts="Repair at sites|Replacement|Credit note|Mixed outcome"),
            F("primary_contact", "Primary contact")]},
    },
    "actions": [
        A("register_route", "Register and route", ["registered", "safety_escalated", "reopened"], "awaiting_owner", ["R04"],
          F("issue_category", "Category", "select", opts=ISSUES), F("priority", "Priority", "select", opts=PRI),
          F("impact", "Impact", "select", opts="Product unusable|Partially usable|Cosmetic|Business impact"),
          F("priority_reason", "Priority reason", req=False), F("owner_id", "Proposed case owner", "lookup", src="users:R05"),
          F("queue", "Responsible queue", "select", opts="Service coordination|Dealer cases|Business accounts|Safety coordination"),
          tpl="acknowledgement", cust=True, meet=["first_response"], start=["assignment"]),
        A("escalate_safety", "Escalate to safety lead", ["registered", "awaiting_owner", "in_progress", "evidence_requested", "reopened"], "safety_escalated", ["R04", "R05"],
          F("hazard", "Hazard reported", "select", opts=SAFETY[19:]), F("immediate_advice", "Immediate advice given to customer", "textarea"),
          F("power_isolated", "Customer advised to isolate power", "select", opts="Confirmed|Not confirmed|Not applicable"), tpl="escalation", cust=True, danger=True),
        A("link_duplicate", "Link to existing case", ["registered"], "duplicate", ["R04"],
          F("target_id", "Existing case", "lookup", src="records:case"), F("reason", "Matching reason", "select", opts="Same customer and product|Same serial number|Same contact repeated|Dealer and customer reported same issue")),
        A("not_duplicate", "Confirm not a duplicate", ["registered"], None, ["R04"], F("reason", "Reason")),
        A("save_translation", "Save reviewed translation", OPEN, None, ["R04"],
          F("source_language", "Original language", "select", opts="Hindi|Marathi|Tamil|Bengali|Gujarati|Telugu|Other"),
          F("translated_text", "Reviewed English translation", "textarea"), F("reviewer_note", "Reviewer note", req=False)),
        A("log_call", "Log a manual call", OPEN, None, ["R04", "R05"],
          F("direction", "Direction", "select", opts="Inbound|Outbound"), F("summary", "Call summary", "textarea")),
        A("accept_ownership", "Accept ownership", ["awaiting_owner", "reopened"], "in_progress", ["R05"],
          F("acceptance_note", "Acceptance note", req=False), tpl="ownership_assigned", cust=True, meet=["assignment"], start=["initial_assessment"]),
        A("decline_ownership", "Decline handoff", ["awaiting_owner"], "registered", ["R05"], F("reason", "Reason for declining", "textarea"), who="proposed_owner"),
        A("handoff", "Hand off ownership", ["in_progress"], "awaiting_owner", ["R05"], F("owner_id", "New owner", "lookup", src="users:R05"), F("reason", "Handoff reason", "textarea"), who="owner"),
        A("plan_resolution", "Plan resolution", ["in_progress"], None, ["R05"],
          F("plan", "Resolution plan", "textarea"), F("remedy", "Intended remedy", "select", opts="Repair|Replacement|Refund|Credit note|Advice only|Other"),
          F("next_review", "Next review", "datetime"), who="owner", meet=["initial_assessment"]),
        A("create_service_job", "Create service job", ["in_progress"], None, ["R05"],
          F("centre_id", "Service centre", "lookup", src="centres"), F("job_type", "Job type", "select", opts="Field visit|Workshop repair|Installation check|Replacement handover"),
          F("skill", "Required skill", "select", opts="Cooling|Water heating|Pumps|Heating|Fans|Kitchen|Power backup"),
          F("notes", "Instructions", "textarea", req=False), who="owner", start=["technician_scheduling"]),
        A("create_linked_task", "Create linked task", OPEN, None, ["R05", "R15"],
          F("task_type", "Task type", "select", opts="Customer callback|Evidence review|Parts follow-up|Dealer coordination|Approval follow-up|Quality input|Other"),
          F("team", "Assigned team", "select", opts="Service coordination|Service centre|Warranty|Parts and logistics|Finance|Quality|Channel support"),
          F("assignee_id", "Task owner", "lookup", src=STAFF_SRC), F("due", "Due date and time", "datetime"),
          F("mandatory", "Mandatory for closure", "select", opts=YN), F("depends_on", "Dependency (task)", "lookup", src="records:task", req=False),
          F("required_evidence", "Required completion evidence", req=False)),
        A("request_warranty_review", "Request warranty assessment", ["in_progress"], None, ["R05"],
          F("component", "Component"), F("claim_notes", "Notes for warranty officer", "textarea", req=False), who="owner"),
        A("request_technical_review", "Request technical review", ["in_progress"], None, ["R05"], F("question", "Review question", "textarea"), who="owner"),
        A("request_evidence", "Request information", ["registered", "awaiting_owner", "in_progress"], "evidence_requested", ["R04", "R05", "R11", "R15"],
          F("requested_items", "Information required", "textarea"), F("due", "Respond by", "date"), tpl="evidence_request", cust=True),
        A("provide_information", "Provide requested information", ["evidence_requested"], "in_progress", ["R01", "R02", "R03"],
          F("response", "Your response", "textarea"), who="customer_or_org", cust=True),
        A("record_waiting", "Submit waiting record", ["in_progress"], "waiting", ["R05"],
          F("milestone", "Case milestone", "select", opts="resolution|initial_assessment|technician_scheduling"),
          F("waiting_reason", "Waiting reason", "select", opts="Customer unavailable|Parts awaited from supplier|Customer evidence awaited|Third-party access"),
          F("team", "Responsible team"), F("starts", "Waiting starts", "datetime"), F("next_review", "Next review time", "datetime"),
          F("evidence", "Supporting evidence", req=False), F("pause_eligibility", "Pause eligibility", "select", opts="Eligible - request clock pause|Not eligible - clock continues"),
          F("authoriser_id", "Authoriser", "lookup", src="users:R08"), who="owner"),
        A("resume_work", "Resume work", ["waiting"], "in_progress", ["R05"], F("note", "Resumption note"), who="owner"),
        A("escalate_case", "Escalate and arrange recovery", OPEN, None, ["R04", "R05", "R09"],
          F("reason", "Escalation reason", "select", opts="Blocked work|Overdue milestone|Customer escalation|Major impact"),
          F("summary", "Summary", "textarea"), F("recommendation", "Recommended recovery", "textarea", req=False), tpl="escalation"),
        A("send_update", "Send reviewed update", OPEN + "|resolved", None, ["R05"],
          F("channel", "Channel", "select", opts="Portal message|Email|SMS|WhatsApp"), F("message", "Customer update", "textarea", minlen=10), cust=True),
        A("request_remedy_approval", "Request remedy approval", ["in_progress"], None, ["R05"],
          F("remedy", "Remedy", "select", opts="refund|replacement|credit_note|chargeable_repair_waiver|goodwill"),
          F("amount", "Amount (INR)", "number", min=0), F("recipient", "Recipient reference"), F("justification", "Justification", "textarea"), who="owner"),
        A("validate_units", "Validate unit list", ["registered", "awaiting_owner", "in_progress"], None, ["R03"],
          F("units", "Affected units (one per line: site, serial)", "textarea"), sub=["bulk_grievance"], who="customer_or_org"),
        A("create_unit_jobs", "Create unit jobs", ["in_progress"], None, ["R05"], F("centre_id", "Service centre", "lookup", src="centres"), sub=["bulk_grievance"]),
        A("submit_verification", "Submit verification details", OPEN, None, ["R01", "R02"],
          F("model_id", "Product model", "lookup", src="models"), F("serial", "Serial number optional", req=False), F("purchase_date", "Purchase date", "date"),
          F("seller", "Seller or dealer"), F("proof", "Invoice or alternative proof", "select", opts="Tax invoice|Warranty card|Bank or card statement|Delivery note|Other proof"), who="customer_or_org"),
        A("confirm_sale", "Confirm sale record", OPEN, None, ["R02"], F("invoice", "Invoice number"), F("sale_date", "Sale date", "date"),
          F("match", "Sale evidence check", "select", opts="Matches invoice|Discrepancy found"), sub=["dealer_customer_case", "stock_claim"], who="customer_or_org"),
        A("confirm_handover", "Confirm handover", ["in_progress", "resolved"], None, ["R02"],
          F("handover_type", "Handover", "select", opts="Repaired unit returned|Replacement handed over|Collected for service"),
          F("received_by", "Received by"), F("condition", "Condition checked", "select", opts="Good condition|Damage noted"), F("handover_at", "Handover time", "datetime"),
          sub=["dealer_customer_case", "stock_claim"], who="customer_or_org", cust=True),
        A("mark_resolved", "Mark resolved", ["in_progress"], "resolved", ["R05"],
          F("resolution", "Resolution summary", "textarea"), F("remedy_delivered", "Remedy delivered", "select", opts="Repair|Replacement|Refund|Credit note|Advice only|No fault found"),
          who="owner", tpl="resolution", cust=True),
        A("verify_and_close", "Record closure outcome", ["resolved"], "closed", ["R05"],
          F("outcome", "Closure outcome", "select", opts="Resolved - customer confirmed|Resolved - evidence verified|No fault found - explained|Rejected - as per decision"),
          F("verification_note", "Verification evidence summary", "textarea"), F("customer_confirmation", "Customer confirmation", "select", opts="Confirmed|Not reachable - see supervised closure|Disputed"),
          who="owner", tpl="closure", cust=True, meet=["resolution"]),
        A("request_supervised_closure", "Request supervised closure", ["resolved"], None, ["R05"],
          F("attempts", "Contact attempts made", "number", min=3), F("last_attempt", "Last attempt", "datetime"), F("channels_tried", "Channels tried"),
          F("approver_id", "Supervisor", "lookup", src="users:R08"), who="owner"),
        A("customer_confirm", "Confirm resolution and rate", ["resolved"], "closed", ["R01", "R02", "R03"],
          F("rating", "Overall rating", "select", opts="5|4|3|2|1"), F("comment", "Comments", "textarea", req=False), who="customer_or_org", cust=True, meet=["resolution"], tpl="closure"),
        A("customer_reject", "Issue not resolved", ["resolved"], "in_progress", ["R01", "R02", "R03"], F("what_remains", "What remains unresolved", "textarea"), who="customer_or_org", cust=True),
        A("reconcile_bulk", "Confirm reconciliation", ["resolved", "in_progress"], "closed", ["R03"],
          F("expected", "Units expected", "number"), F("received", "Units resolved / received", "number"), F("commercial_outcome", "Commercial outcome", "textarea"),
          sub=["bulk_grievance"], who="customer_or_org", cust=True),
        A("reopen", "Request reopening", ["closed"], "reopened", ["R01", "R02", "R03", "R04", "R05"],
          F("issue_returned_on", "Issue returned on", "date"), F("recurring_symptom", "Recurring symptom"), F("unresolved", "What remains unresolved", "textarea"),
          F("preferred_contact", "Preferred contact", "select", opts=CONTACT), F("additional_evidence", "Additional evidence", req=False, hint="Upload files after submitting"),
          tpl="reopening", cust=True, start=["assignment"]),
        A("request_review", "Submit appeal", ["closed", "resolved", "in_progress"], None, ["R01", "R02", "R03"],
          F("original_decision", "Original decision", "select", opts="Closure outcome|Warranty decision|Claim decision|Remedy offered"),
          F("reason", "Reason for disagreement", "textarea"), F("requested_outcome", "Requested outcome", "select", opts="Repair|Replacement|Refund|Credit|Re-assessment"),
          F("new_evidence", "New evidence", req=False), F("contact_pref", "Contact preference", "select", opts=CONTACT), F("explanation", "Your explanation", "textarea"),
          who="customer_or_org", cust=True),
        A("add_update", "Add an update", OPEN + "|resolved", None, ["R01", "R02", "R03"], F("message", "Your update", "textarea"), who="customer_or_org", cust=True),
    ],
}

WF["contact"] = {
    "label": "Contact", "prefix": "CT",
    "states": {"new": S("New", "info", "Open and screen"), "in_review": S("In review", "pending", "Register or link"),
               "linked": S("Linked to case", "done", "", True), "registered": S("Registered as case", "done", "", True), "closed": S("Closed", "muted", "", True)},
    "initial": "new",
    "create": {"manual": {"label": "Manual contact log", "roles": ["R04"], "fields": [
        F("channel", "Channel", "select", opts=CHANNELS), F("customer_name", "Customer name"), F("contact", "Phone or email"),
        F("subject", "Subject"), F("message", "Message or call notes", "textarea"), F("source_reference", "Source reference", req=False)]}},
    "actions": [
        A("open_contact", "Open contact", ["new"], "in_review", ["R04"]),
        A("register_case", "Register and route", ["new", "in_review"], "registered", ["R04"], *WF["case"]["create"]["support_ticket"]["fields"]),
        A("link_to_case", "Link to existing case", ["new", "in_review"], "linked", ["R04"], F("case_id", "Existing case", "lookup", src="records:case"), F("note", "Contact summary", "textarea")),
        A("close_contact", "Close without case", ["new", "in_review"], "closed", ["R04"], F("reason", "Reason", "select", opts="Spam|Information only|Wrong number|Duplicate message")),
    ],
}

WF["task"] = {
    "label": "Task", "prefix": "TSK",
    "states": {"open": S("Open", "info", "Start task"), "in_progress": S("In progress", "info", "Complete task"), "blocked": S("Blocked", "blocked", "Remove blocker"),
               "done": S("Done", "done", "", True), "cancelled": S("Cancelled", "muted", "", True)},
    "initial": "open", "create": {},
    "actions": [
        A("start_task", "Start task", ["open", "blocked"], "in_progress", ALL_INTERNAL, who="assignee_or_creator"),
        A("block_task", "Mark blocked", ["open", "in_progress"], "blocked", ALL_INTERNAL, F("reason", "Blocker"), who="assignee_or_creator"),
        A("complete_task", "Complete task", ["open", "in_progress"], "done", ALL_INTERNAL, F("completion_note", "Completion evidence summary", "textarea"), who="assignee_or_creator"),
        A("cancel_task", "Cancel task", ["open", "in_progress", "blocked"], "cancelled", ["R05", "R15", "R14", "R16"], F("reason", "Reason"), danger=True),
    ],
}

WF["job"] = {
    "label": "Service job", "prefix": "JOB",
    "states": {
        "created": S("Awaiting allocation", "pending", "Allocate technician"), "allocated": S("Technician allocated", "info", "Propose appointment"),
        "appointment_proposed": S("Appointment proposed", "pending", "Customer to confirm"), "appointment_confirmed": S("Appointment confirmed", "info", "Confirm dispatch readiness"),
        "dispatched": S("Dispatched", "info", "Record arrival"), "on_site": S("On site", "info", "Diagnose product"), "diagnosed": S("Diagnosed", "info", "Repair, request parts or estimate"),
        "awaiting_approval": S("Awaiting approval", "pending", "Approval decision"), "awaiting_parts": S("Awaiting parts", "blocked", "Parts delivery"),
        "authorised": S("Repair authorised", "info", "Perform approved repair"), "repaired": S("Repair recorded", "info", "Run functional and safety tests"),
        "tested": S("Tests passed", "info", "Customer handover"), "completed": S("Completion submitted", "pending", "Centre review of evidence"),
        "returned": S("Returned for correction", "urgent", "Correct completion evidence"), "missed": S("Missed visit - recovery", "urgent", "Re-allocate and re-schedule"),
        "accepted": S("Job accepted", "done", "", True), "cancelled": S("Cancelled", "muted", "", True),
    },
    "initial": "created", "create": {},
    "actions": [
        A("allocate", "Assign available engineer", ["created", "missed"], "allocated", ["R07"], F("technician_id", "Technician", "lookup", src="users:R06"), F("note", "Allocation note", req=False), tpl="technician_assigned"),
        A("request_support", "Request support / reassignment", ["created"], None, ["R07"], F("reason", "Capacity or skill gap", "textarea")),
        A("reassign_centre", "Rebalance to another centre", ["created", "allocated"], "created", ["R09"], F("centre_id", "Target centre", "lookup", src="centres"), F("reason", "Reason")),
        A("propose_appointment", "Propose appointment", ["allocated", "missed"], "appointment_proposed", ["R05", "R07"],
          F("window_start", "Visit window start", "datetime"), F("window_end", "Visit window end", "datetime"), F("note", "Note for customer", req=False),
          tpl="appointment_confirmation", cust=True, meet=["technician_scheduling"]),
        A("customer_confirm_appointment", "Confirm appointment", ["appointment_proposed"], "appointment_confirmed", ["R01", "R02", "R03"],
          F("access_notes", "Access notes", req=False), who="customer_or_org", cust=True),
        A("customer_request_reschedule", "Request another time", ["appointment_proposed"], "allocated", ["R01", "R02", "R03"], F("preferred_window", "Preferred window"), who="customer_or_org", cust=True),
        A("confirm_on_behalf", "Record customer confirmation (call)", ["appointment_proposed"], "appointment_confirmed", ["R05", "R07"], F("call_note", "Call note")),
        A("confirm_dispatch", "Confirm dispatch", ["appointment_confirmed"], "dispatched", ["R07"],
          F("tools_ready", "Tools and skills confirmed", "select", opts="Confirmed"), F("parts_ready", "Parts readiness", "select", opts="Ready|Not required"),
          F("info_ready", "Job information complete", "select", opts="Confirmed")),
        A("record_arrival", "Record arrival", ["dispatched"], "on_site", ["R06"], F("arrived_at", "Arrival time", "datetime"),
          F("customer_present", "Customer present", "select", opts="Yes|Representative present"), F("location_note", "Location note", req=False), who="technician", cust=True),
        A("submit_diagnosis", "Submit diagnosis", ["on_site", "diagnosed"], "diagnosed", ["R06"],
          F("product_serial", "Product and serial"), F("symptom", "Reported symptom"), F("installation", "Installation observations", "textarea"),
          F("reading", "Test reading and unit"), F("cause", "Supported cause", "textarea"),
          F("recommended", "Recommended action", "select", opts="Repair - covered|Repair - chargeable|Replace part|Replace unit|No fault found|Refer to supervisor"), who="technician"),
        A("request_parts", "Request part", ["diagnosed", "on_site", "authorised"], "awaiting_parts", ["R06"],
          F("part_sku", "Compatible part", "lookup", src="parts"), F("quantity", "Quantity", "number", min=1), F("reason", "Reason"),
          F("required_by", "Required by", "date"), F("evidence_note", "Evidence", req=False), who="technician"),
        A("submit_estimate", "Submit for approval", ["diagnosed"], "awaiting_approval", ["R06"],
          F("labour", "Labour (INR)", "number", min=0), F("parts_cost", "Parts (INR)", "number", min=0),
          F("chargeable", "Chargeable to customer", "select", opts=YN), F("proposal", "Repair proposal", "textarea"), who="technician", tpl="approval_request"),
        A("customer_accept_estimate", "Accept estimate", ["awaiting_approval", "authorised"], None, ["R01", "R02", "R03"], F("acceptance", "Acceptance", "select", opts="I accept the estimate"), who="customer_or_org", cust=True),
        A("customer_decline_estimate", "Decline estimate", ["awaiting_approval", "authorised"], "diagnosed", ["R01", "R02", "R03"], F("reason", "Reason", "textarea"), who="customer_or_org", cust=True, danger=True),
        A("record_repair", "Save repair record", ["diagnosed", "authorised"], "repaired", ["R06"],
          F("approved_proposal", "Approved proposal"), F("work", "Work performed", "textarea"), F("part_used", "Part used", req=False),
          F("part_serial", "Part serial or batch", req=False), F("labour_minutes", "Labour time (minutes)", "number", min=1), who="technician"),
        A("submit_tests", "Submit test results", ["repaired"], "tested", ["R06"],
          F("functional", "Functional test", "select", opts="Pass|Fail"), F("insulation", "Insulation resistance", "select", opts="Pass|Fail"),
          F("earth", "Earth continuity", "select", opts="Pass|Fail|Not applicable"), F("readings", "Readings recorded"), who="technician"),
        A("submit_handover", "Submit completion evidence", ["tested", "returned"], "completed", ["R06"],
          F("signoff_name", "Customer sign-off name"), F("customer_satisfied", "Customer confirmation", "select", opts="Confirmed working|Confirmed with remarks"),
          F("handover_note", "Handover note", "textarea"), who="technician", ev=1, cust=True),
        A("accept_report", "Accept job report", ["completed"], "accepted", ["R07"], F("review_note", "Review note")),
        A("return_for_correction", "Return for correction", ["completed"], "returned", ["R07"], F("deficiency", "Evidence deficiency", "textarea"), danger=True),
        A("record_missed_visit", "Approve recovery plan", ["dispatched", "appointment_confirmed"], "missed", ["R07"],
          F("reason", "Missed visit reason", "select", opts="Technician delayed|Customer unavailable|Parts not ready|Access refused"),
          F("contact_attempt", "Customer contact attempt"), F("recovery_technician_id", "Recovery technician", "lookup", src="users:R06"),
          F("new_window", "New visit window"), F("supervisor_note", "Supervisor note", req=False), cust=True),
        A("cancel_job", "Cancel job", ["created", "allocated", "appointment_proposed"], "cancelled", ["R05"], F("reason", "Reason"), danger=True),
    ],
}

WF["unit"] = {
    "label": "Unit", "prefix": "UNT",
    "states": {"open": S("Open", "pending", "Create unit job"), "job_created": S("Job in progress", "info", "Complete unit job"),
               "resolved": S("Resolved", "done", "", True), "unresolved": S("Unresolved", "urgent", "Follow up assigned job")},
    "initial": "open", "create": {},
    "actions": [A("mark_unit_resolved", "Mark unit resolved", ["open", "job_created", "unresolved"], "resolved", ["R05"], F("note", "Resolution evidence")),
                A("mark_unit_unresolved", "Mark unresolved", ["job_created"], "unresolved", ["R05"], F("note", "Reason"))],
}

WF["tech_review"] = {
    "label": "Technical review", "prefix": "TR",
    "states": {"pending": S("Review pending", "pending", "Review diagnosis"), "further_inspection": S("Further inspection", "pending", "Technician to update diagnosis"),
               "recommended": S("Recommendation recorded", "info", "Submit technical decision"), "referred": S("Referred to approver", "pending", "Higher authority decision"),
               "approved": S("Technical plan approved", "done", "", True), "closed": S("Closed", "muted", "", True)},
    "initial": "pending", "create": {},
    "actions": [
        A("request_inspection", "Request further inspection", ["pending", "recommended"], "further_inspection", ["R08"], F("inspection_required", "Inspection or tests required", "textarea")),
        A("inspection_updated", "Submit updated diagnosis", ["further_inspection"], "pending", ["R06", "R05"], F("update", "Updated diagnosis", "textarea")),
        A("record_recommendation", "Record recommendation", ["pending"], "recommended", ["R08"],
          F("diagnosis_supported", "Diagnosis supported", "select", opts=YN), F("recurrence", "Repeat failure assessment", "textarea"),
          F("recommendation", "Recommendation", "select", opts="Repair with replacement part|Replace unit|No fault found|Refer to quality"), F("estimated_cost", "Estimated cost (INR)", "number", min=0)),
        A("submit_decision", "Submit technical decision", ["recommended"], "approved", ["R08"],
          F("decision", "Decision", "select", opts="Approve technical plan|Refer to higher authority"), F("amount", "Plan value (INR)", "number", min=0), F("rationale", "Rationale", "textarea")),
        A("close_review", "Close review", ["pending", "recommended"], "closed", ["R08"], F("reason", "Reason")),
    ],
}

WF["approval"] = {
    "label": "Approval", "prefix": "APR",
    "states": {"pending": S("Pending decision", "pending", "Authorised approver decision"), "approved": S("Approved", "done", "", True),
               "rejected": S("Rejected", "muted", "", True), "cancelled": S("Cancelled", "muted", "", True)},
    "initial": "pending", "create": {},
    "actions": [
        A("approve", "Approve", ["pending"], "approved", ["R05", "R07", "R08", "R09", "R10", "R11", "R13", "R15", "R16", "R18", "R20"],
          F("decision_note", "Decision note"), F("evidence_checked", "Required evidence reviewed", "select", opts="Yes"), who="approver", tpl="approval_decision"),
        A("reject", "Reject", ["pending"], "rejected", ["R05", "R07", "R08", "R09", "R10", "R11", "R13", "R15", "R16", "R18", "R20"],
          F("reason", "Rejection reason", "textarea", minlen=10), who="approver", danger=True, tpl="approval_decision"),
        A("refer", "Refer to higher authority", ["pending"], None, ["R07", "R08", "R09", "R11", "R15", "R16"], F("reason", "Referral reason"), who="approver"),
    ],
}

WF["warranty"] = {
    "label": "Warranty claim", "prefix": "WCL",
    "states": {"submitted": S("Submitted", "info", "Check purchase evidence"), "clarification_requested": S("Clarification requested", "pending", "Await clarification"),
               "diagnosis_review": S("Diagnosis review", "info", "Record coverage decision"), "exception_approval": S("Exception approval", "pending", "Approver decision"),
               "decision_recorded": S("Decision recorded", "info", "Explain decision and appeal route"), "communicated": S("Decision communicated", "done", "Close or route dispute"),
               "disputed": S("Disputed - appeal routed", "urgent", "", True), "closed": S("Closed", "done", "", True)},
    "initial": "submitted",
    "create": {"claim": {"label": "Warranty claim", "roles": ["R11", "R02"], "fields": [
        F("case_id", "Related case", "lookup", src="records:case"), F("model_id", "Product model", "lookup", src="models"), F("serial", "Serial number"),
        F("component", "Component"), F("purchase_date", "Purchase date", "date"), F("purchase_evidence", "Purchase evidence", "select", opts="Tax invoice|Warranty card|Alternative proof|Not provided"),
        F("claim_notes", "Claim notes", "textarea", req=False)]}},
    "actions": [
        A("check_evidence", "Check purchase evidence", ["submitted"], "diagnosis_review", ["R11"],
          F("evidence_sufficient", "Evidence sufficient", "select", opts=YN), F("purchase_verified", "Purchase verification", "select", opts="Verified|Alternative proof accepted|Not verified"),
          F("clarification", "Clarification required (if insufficient)", "textarea", req=False)),
        A("provide_clarification", "Provide clarification", ["clarification_requested"], "submitted", ["R01", "R02", "R05"], F("response", "Clarification", "textarea"), cust=True),
        A("record_coverage_decision", "Record coverage decision", ["diagnosis_review"], "decision_recorded", ["R11"],
          F("policy_id", "Applicable warranty version", "lookup", src="policies:warranty_term"), F("diagnosis_reviewed", "Technical diagnosis reviewed", "select", opts="Yes"),
          F("coverage", "Coverage decision", "select", opts="Covered|Chargeable|Declined|Covered - exception requested"),
          F("reasons", "Eligibility reasons", "textarea", minlen=10), F("amount", "Claim value (INR)", "number", min=0, req=False)),
        A("explain_decision", "Send decision and appeal route", ["decision_recorded"], "communicated", ["R11"],
          F("explanation", "Customer explanation", "textarea", minlen=15), F("appeal_route", "Appeal route", "select", opts="Request a decision review from your complaint page"), cust=True, tpl="status_update"),
        A("route_dispute", "Route dispute to appeals", ["communicated", "decision_recorded"], "disputed", ["R11"], F("grounds", "Dispute grounds", "textarea")),
        A("close_claim", "Close claim", ["communicated"], "closed", ["R11"], F("note", "Closing note")),
    ],
}

WF["requisition"] = {
    "label": "Parts requisition", "prefix": "REQ",
    "states": {"requested": S("Requested", "pending", "Validate requisition"), "validated": S("Validated", "info", "Reserve stock"),
               "awaiting_stock": S("Awaiting transfer / procurement", "blocked", "Receive and verify stock"), "reserved": S("Reserved", "info", "Dispatch"),
               "dispatched": S("Dispatched", "info", "Confirm delivery"), "delivery_exception": S("Delivery exception", "urgent", "Resolve logistics exception"),
               "delivered": S("Delivered", "done", "Record usage or return"), "consumed": S("Used in repair", "done", "Reconcile", True),
               "returned": S("Returned", "done", "Reconcile", True), "rejected": S("Rejected", "muted", "", True), "reconciled": S("Reconciled", "done", "", True)},
    "initial": "requested", "create": {},
    "actions": [
        A("validate_requisition", "Validate requisition", ["requested"], "validated", ["R12"],
          F("valid", "Requisition decision", "select", opts="Valid - approved job|Reject"), F("note", "Validation note", req=False)),
        A("reserve_stock", "Confirm reservation", ["validated"], "reserved", ["R12"], F("warehouse_id", "Warehouse", "lookup", src="warehouses"),
          F("quantity", "Quantity", "number", min=1), F("expiry", "Reservation expiry", "date"), F("issue_note", "Issue note", req=False)),
        A("mark_unavailable", "Transfer or procure stock", ["validated"], "awaiting_stock", ["R12"], F("route", "Route", "select", opts="Transfer from another warehouse|Procure from supplier"), F("eta", "Expected date", "date")),
        A("receive_stock", "Receive and verify stock", ["awaiting_stock"], "validated", ["R12"], F("warehouse_id", "Receiving warehouse", "lookup", src="warehouses"), F("quantity", "Quantity received", "number", min=1)),
        A("dispatch", "Dispatch part", ["reserved"], "dispatched", ["R12"], F("carrier", "Carrier"), F("tracking", "Tracking reference"), F("eta", "Expected delivery", "datetime")),
        A("record_delivery", "Record delivery milestone", ["dispatched"], "delivered", ["R12", "R06"], F("delivered", "Delivered at site", "select", opts=YN), F("received_by", "Received by", req=False), F("note", "Note", req=False)),
        A("resolve_exception", "Assign logistics recovery", ["delivery_exception"], "dispatched", ["R12"],
          F("exception_type", "Exception type", "select", opts="Address issue|Damaged in transit|Lost|Customer unavailable"), F("carrier_update", "Carrier update"),
          F("customer_update", "Customer update", req=False), F("recovery_action", "Recovery action"), F("next_review", "Next review time", "datetime")),
        A("record_usage", "Record usage or return", ["delivered"], "consumed", ["R06", "R12"], F("outcome", "Outcome", "select", opts="Used in repair|Returned unused|Defective part returned"), F("part_serial", "Part serial", req=False)),
        A("reconcile_requisition", "Reconcile", ["consumed", "returned"], "reconciled", ["R12"], F("note", "Reconciliation note")),
    ],
}

WF["return"] = {
    "label": "Return", "prefix": "RET",
    "states": {"expected": S("Expected", "pending", "Record receipt"), "received": S("Received", "info", "Disposition"), "quarantined": S("Safety quarantine", "urgent", "Restricted examination"),
               "inspected": S("Examined", "info", "Disposition"), "closed": S("Closed", "done", "", True)},
    "initial": "expected",
    "create": {"return": {"label": "Defective return", "roles": ["R12"], "fields": [F("item", "Unit or part"), F("batch", "Batch / serial"), F("source_ref", "Source job or case"),
                                                                                    F("safety_hold", "Safety hold", "select", opts="No|Yes - quarantine")]}},
    "actions": [
        A("record_receipt", "Record return receipt", ["expected"], "received", ["R12"], F("condition", "Condition", "select", opts="Defective|Damaged|Unused|Unknown"),
          F("custody", "Custodian / location"), F("destination", "Destination", "select", opts="Supplier return|Refurbish|Scrap|Quality lab")),
        A("open_restricted_examination", "Open restricted examination", ["quarantined"], "inspected", ["R14", "R12"], F("findings", "Examination findings", "textarea")),
        A("close_return", "Close return", ["received", "inspected"], "closed", ["R12"], F("disposition", "Final disposition")),
    ],
}

WF["replacement"] = {
    "label": "Replacement order", "prefix": "RPL",
    "states": {"created": S("Created", "pending", "Schedule delivery"), "dispatch_scheduled": S("Delivery scheduled", "info", "Record delivery"),
               "delivered": S("New unit delivered", "info", "Collect old unit"), "completed": S("Completed", "done", "", True), "exception": S("Milestone exception", "urgent", "Review milestone")},
    "initial": "created",
    "create": {"replacement": {"label": "Approved replacement order", "roles": ["R12"], "fields": [
        F("case_id", "Case reference", "lookup", src="records:case"), F("approval_id", "Replacement approval", "lookup", src="records:approval"),
        F("old_serial", "Old product serial"), F("model_id", "Approved replacement model", "lookup", src="models"), F("new_serial", "New product serial", req=False),
        F("address", "Customer delivery address"), F("collection", "Old unit collection required", "select", opts=YN), F("consent_ref", "Substitution consent reference", req=False)]}},
    "actions": [
        A("schedule_delivery", "Schedule delivery", ["created", "exception"], "dispatch_scheduled", ["R12"], F("delivery_window", "Delivery window"), F("carrier", "Carrier")),
        A("record_replacement_delivery", "Record delivery", ["dispatch_scheduled"], "delivered", ["R12"], F("new_serial", "New unit serial"), F("received_by", "Received by"), cust=True),
        A("record_collection", "Complete milestones", ["delivered"], "completed", ["R12"], F("old_unit", "Old unit collection", "select", opts="Collected|Not required"), F("note", "Note", req=False)),
        A("record_milestone_exception", "Record exception", ["created", "dispatch_scheduled", "delivered"], "exception", ["R12"], F("reason", "Exception", "textarea")),
    ],
}

WF["settlement"] = {
    "label": "Settlement", "prefix": "STL",
    "states": {"pending_validation": S("Awaiting validation", "pending", "Validate recipient and amount"), "discrepancy": S("Discrepancy", "urgent", "Resolve discrepancy"),
               "recipient_validated": S("Recipient validated", "info", "Submit payment instruction"), "pending_confirmation": S("Pending confirmation", "pending", "Check operation status"),
               "outcome_unknown": S("Outcome unknown", "urgent", "Enquire provider status"), "failed": S("Execution failed", "urgent", "Investigate and retry"),
               "executed": S("Executed", "done", "Reconcile"), "correction_requested": S("Correction requested", "pending", "Correction approval"),
               "reconciled": S("Reconciled", "done", "", True), "cancelled": S("Cancelled", "muted", "", True)},
    "initial": "pending_validation",
    "create": {"credit_note": {"label": "Credit note", "roles": ["R13"], "fields": [
        F("approval_id", "Approved claim", "lookup", src="records:approval"), F("invoice_ref", "Invoice reference"), F("amount", "Credit amount (INR)", "number", min=1),
        F("tax_ref", "Tax adjustment reference"), F("reason", "Reason"), F("approval_revision", "Approval revision", req=False)]}},
    "actions": [
        A("validate_recipient", "Confirm recipient validation", ["pending_validation"], "recipient_validated", ["R13"],
          F("original_transaction", "Original transaction"), F("approved_amount", "Approved amount (INR)", "number", min=0),
          F("beneficiary_reference", "Beneficiary reference"), F("account_ending", "Account ending", pattern=r"^\d{4}$", hint="Last 4 digits only"),
          F("recipient_authority", "Recipient authority", "select", opts="Customer|Dealer account|Distributor account|Authorised representative"),
          F("verification_evidence", "Verification evidence")),
        A("resolve_discrepancy", "Resolve discrepancy", ["discrepancy"], "pending_validation", ["R13"], F("resolution", "Resolution", "textarea")),
        A("submit_instruction", "Submit payment instruction", ["recipient_validated", "failed"], "pending_confirmation", ["R13"],
          F("method", "Method", "select", opts="Bank transfer (simulated adapter)|Card reversal (simulated adapter)|Credit note posting (simulated adapter)"),
          F("confirm", "Confirmation", "select", opts="I confirm this matches the approved instruction")),
        A("check_status", "Check operation status", ["pending_confirmation", "outcome_unknown"], None, ["R13"], F("enquiry_reference", "Enquiry note", req=False)),
        A("reconcile", "Confirm reconciliation", ["executed"], "reconciled", ["R13"], F("ledger_reference", "Ledger reference"), F("ledger_amount", "Ledger amount (INR)", "number", min=0)),
        A("request_correction", "Request correction approval", ["executed", "reconciled"], "correction_requested", ["R13"],
          F("correction_type", "Correction type", "select", opts="Reversal|Partial adjustment|Re-issue"), F("reason", "Reason", "textarea"),
          F("amount", "Correcting amount (INR)", "number", min=1), F("evidence", "Supporting evidence")),
    ],
}

WF["incident"] = {
    "label": "Safety incident", "prefix": "INC",
    "states": {"reported": S("Reported", "urgent", "Triage incident"), "containment": S("Containment", "urgent", "Record containment action"),
               "investigation": S("Investigation", "info", "Investigate root cause"), "rca_complete": S("Root cause recorded", "info", "Plan corrective action"),
               "capa_in_progress": S("CAPA in progress", "pending", "Implement corrective actions"), "effectiveness_check": S("Effectiveness check", "pending", "Verify effectiveness"),
               "closed": S("Closed", "done", "", True)},
    "initial": "reported",
    "create": {"incident": {"label": "Safety incident", "roles": ["R14"], "fields": [
        F("hazard", "Hazard", "select", opts=SAFETY[19:]), F("model_id", "Product model", "lookup", src="models"), F("serial", "Serial / batch", req=False),
        F("description", "Incident description", "textarea"), F("case_id", "Related case", "lookup", src="records:case", req=False)]}},
    "actions": [
        A("triage", "Triage incident", ["reported"], "containment", ["R14"], F("urgent", "Urgent safety concern", "select", opts=YN),
          F("severity", "Severity", "select", opts="S1 - Injury or fire|S2 - Serious hazard|S3 - Potential hazard|S4 - Low"), F("specialists", "Specialists engaged", req=False)),
        A("record_containment", "Record containment action", ["containment"], "investigation", ["R14"], F("action", "Containment action", "textarea"),
          F("product_isolated", "Product isolated", "select", opts="Yes|Customer advised|Not possible"), F("customer_advised", "Customer advised", "select", opts=YN)),
        A("preserve_evidence", "Preserve evidence", ["containment", "investigation"], None, ["R14"], F("custody_ref", "Custody reference"), F("location", "Storage location"), F("items", "Items preserved")),
        A("link_units", "Link affected units", ["containment", "investigation"], None, ["R14"], F("batch", "Batch or model scope"), F("case_refs", "Related case references (comma separated)", req=False),
          F("risk", "Exposure risk", "select", opts="High|Medium|Low")),
        A("submit_findings", "Submit investigation findings", ["investigation"], "rca_complete", ["R14"], F("method", "Method", "select", opts="5-Why|Fishbone|Fault tree|Laboratory analysis"),
          F("root_cause", "Root cause", "textarea"), F("contributing", "Contributing factors", "textarea", req=False), F("confidence", "Confidence", "select", opts="Confirmed|Probable|Possible")),
        A("plan_capa", "Assign corrective action", ["rca_complete", "capa_in_progress"], "capa_in_progress", ["R14"], F("title", "Action"),
          F("kind", "Type", "select", opts="Corrective|Preventive"), F("assignee_id", "Action owner", "lookup", src=STAFF_SRC), F("due", "Due date", "date")),
        A("request_verification", "Start effectiveness check", ["capa_in_progress"], "effectiveness_check", ["R14"], F("note", "Note", req=False)),
        A("verify_effectiveness", "Record effectiveness result", ["effectiveness_check"], "closed", ["R14"], F("effective", "Corrective action effective", "select", opts=YN),
          F("evidence_summary", "Evidence summary", "textarea"), F("monitoring_period", "Monitoring period")),
    ],
}

WF["capa"] = {
    "label": "Corrective action", "prefix": "CAPA",
    "states": {"open": S("Open", "info", "Start action"), "in_progress": S("In progress", "info", "Implement"), "implemented": S("Implemented", "pending", "Verify"),
               "ineffective": S("Ineffective - revise", "urgent", "Revise action"), "verified": S("Verified effective", "done", "", True)},
    "initial": "open", "create": {},
    "actions": [A("start_capa", "Start action", ["open", "ineffective"], "in_progress", ALL_INTERNAL, who="assignee_or_creator"),
                A("mark_implemented", "Mark implemented", ["in_progress"], "implemented", ALL_INTERNAL, F("implementation_evidence", "Implementation evidence", "textarea"), who="assignee_or_creator"),
                A("verify_capa", "Verify action", ["implemented"], "verified", ["R14"], F("effective", "Effective", "select", opts=YN), F("note", "Verification note"))],
}

WF["channel_dispute"] = {
    "label": "Channel dispute", "prefix": "CHD",
    "states": {"open": S("Open", "info", "Review evidence"), "clarification_requested": S("Clarification requested", "pending", "Await customer / dealer response"),
               "facts_reconciled": S("Facts reconciled", "info", "Decide within authority"), "referred": S("Referred to higher authority", "pending", "Await decision"),
               "recovery_in_progress": S("Recovery in progress", "info", "Monitor corrective action"), "follow_up": S("Follow-up required", "urgent", "Remove blockers"),
               "verification": S("Outcome verification", "pending", "Verify stakeholder outcome"), "closed": S("Closed", "done", "", True), "rejected": S("Claim not approved", "muted", "", True)},
    "initial": "open",
    "create": {"dispute": {"label": "Dealer conduct / supply dispute", "roles": ["R15"], "fields": [
        F("org_id", "Dealer", "lookup", src="orgs:dealer"), F("issue", "Issue", "select", opts="Stock damage claim|Delayed customer service|Misrepresentation|Supply shortfall|Pricing dispute"),
        F("customer_impact", "Customer impact", "select", opts="High|Medium|Low|None"), F("description", "Description", "textarea"), F("case_id", "Related case", "lookup", src="records:case", req=False)]}},
    "actions": [
        A("request_clarification", "Request additional evidence", ["open", "facts_reconciled"], "clarification_requested", ["R15"],
          F("from_party", "Requested from", "select", opts="Dealer|Customer|Both"), F("questions", "Evidence required", "textarea")),
        A("clarification_received", "Record clarification received", ["clarification_requested"], "open", ["R15"], F("summary", "Summary", "textarea")),
        A("record_findings", "Record supported findings", ["open"], "facts_reconciled", ["R15"], F("customer_account", "Customer account", "textarea"),
          F("dealer_account", "Dealer account", "textarea"), F("findings", "Supported findings", "textarea"), F("evidence_sufficient", "Evidence sufficient", "select", opts=YN)),
        A("decide_dispute", "Record authorised decision", ["facts_reconciled"], "recovery_in_progress", ["R15"],
          F("decision", "Decision", "select", opts="Approve claim|Reject claim|Corrective action against dealer"), F("amount", "Approved value (INR)", "number", min=0), F("reason", "Reasoned decision", "textarea", minlen=10)),
        A("assign_recovery", "Assign recovery action", ["recovery_in_progress", "follow_up"], None, ["R15"], F("title", "Recovery action"), F("assignee_id", "Owner", "lookup", src=STAFF_SRC), F("due", "Due", "datetime")),
        A("record_action_status", "Record action status", ["recovery_in_progress", "follow_up"], "verification", ["R15"], F("completed", "Action completed", "select", opts=YN), F("note", "Note")),
        A("verify_outcome", "Verify outcome and close", ["verification"], "closed", ["R15"], F("acceptance", "Stakeholder acceptance", "select", opts="Accepted by dealer|Accepted by customer|Accepted by both"), F("outcome", "Outcome", "textarea")),
    ],
}

WF["appeal"] = {
    "label": "Appeal", "prefix": "APL",
    "states": {"registered": S("Registered", "pending", "Assign independent reviewer"), "under_review": S("Under independent review", "info", "Review evidence and decide"),
               "explanations_requested": S("Explanations requested", "pending", "Await explanations"), "decided_upheld": S("Original decision upheld", "done", "Record outcome and review route"),
               "awaiting_reversal_approval": S("Reversal approval pending", "pending", "Authorised approval"), "remedy_in_progress": S("Remedy in progress", "info", "Verify remedy completion"),
               "closed": S("Closed", "done", "", True)},
    "initial": "registered",
    "create": {"appeal": {"label": "Appeal", "roles": ["R16"], "fields": [F("case_id", "Original case", "lookup", src="records:case"),
                                                                           F("original_decision", "Original decision"), F("reason", "Grounds", "textarea"), F("requested_outcome", "Requested outcome")]}},
    "actions": [
        A("assign_reviewer", "Assign independent reviewer", ["registered"], "under_review", ["R16"], F("reviewer_id", "Reviewer", "lookup", src="users:R16"),
          F("conflict_declaration", "Conflict check", "select", opts="No conflict declared")),
        A("record_findings", "Record review findings", ["under_review"], None, ["R16"], F("evidence_reviewed", "Evidence reviewed", "textarea"), F("policy_applied", "Policy applied"), F("findings", "Findings", "textarea"), who="reviewer"),
        A("request_explanation", "Request explanation", ["under_review"], "explanations_requested", ["R16"], F("from_party", "From", "select", opts="Case owner|Warranty officer|Dealer|Complainant"), F("questions", "Questions", "textarea"), who="reviewer"),
        A("explanation_received", "Record explanation", ["explanations_requested"], "under_review", ["R16"], F("summary", "Explanation summary", "textarea"), who="reviewer"),
        A("issue_decision", "Issue reasoned decision", ["under_review"], "decided_upheld", ["R16"],
          F("decision", "Decision", "select", opts="Uphold original decision|Amend decision|Reverse decision"), F("reasons", "Reasons", "textarea", minlen=15),
          F("remedy", "Remedy (if amended or reversed)", "select", opts="None|Refund|Replacement|Repair|Credit|Apology and explanation"), F("amount", "Remedy value (INR)", "number", min=0, req=False),
          who="reviewer", cust=True, tpl="appeal_outcome"),
        A("assign_remedy", "Assign remedy execution", ["remedy_in_progress"], None, ["R16"], F("assignee_id", "Responsible owner", "lookup", src=STAFF_SRC), F("note", "Remedy instruction"), F("due", "Due", "datetime")),
        A("verify_remedy", "Verify remedy and close", ["remedy_in_progress"], "closed", ["R16"], F("verification", "Verification", "textarea"), cust=True, tpl="appeal_outcome"),
        A("close_appeal", "Record outcome and close", ["decided_upheld"], "closed", ["R16"], F("note", "Outcome and review route"), cust=True),
    ],
}

WF["correspondence"] = {
    "label": "External correspondence", "prefix": "COR",
    "states": {"registered": S("Registered", "pending", "Prepare response"), "responding": S("Response in preparation", "info", "Send response"), "responded": S("Responded", "done", "", True)},
    "initial": "registered",
    "create": {"correspondence": {"label": "External correspondence", "roles": ["R16"], "fields": [
        F("reference", "Reference"), F("authority", "Authority or channel", "select", opts="Consumer commission|Regulator|Legal notice|Ombudsman|Social media escalation|Other"),
        F("received", "Received", "date"), F("verified_deadline", "Verified deadline", "date"), F("assignee_id", "Response owner", "lookup", src="users:R16"), F("summary", "Summary", "textarea")]}},
    "actions": [A("start_response", "Start response", ["registered"], "responding", ["R16"]),
                A("record_response", "Record response sent", ["responding"], "responded", ["R16"], F("response_ref", "Response reference"), F("sent_on", "Sent on", "date"))],
}

WF["escalation"] = {
    "label": "Escalation", "prefix": "ESC",
    "states": {"open": S("Open", "urgent", "Assign recovery owner"), "recovery_assigned": S("Recovery assigned", "info", "Execute recovery plan"),
               "referred_national": S("Referred to national", "pending", "National decision"), "authorised": S("Plan authorised", "info", "Execute approved plan"),
               "verification": S("Verification", "pending", "Verify recovery"), "revision": S("Plan revision", "urgent", "Revise plan"), "closed": S("Closed", "done", "", True)},
    "initial": "open",
    "create": {"escalation": {"label": "Escalation", "roles": ["R09", "R10"], "fields": [F("case_id", "Case", "lookup", src="records:case", req=False),
                                                                                   F("reason", "Reason"), F("summary", "Summary", "textarea")]}},
    "actions": [
        A("assign_recovery_owner", "Assign recovery owner", ["open", "revision"], "recovery_assigned", ["R09", "R10"], F("assignee_id", "Recovery owner", "lookup", src=STAFF_SRC),
          F("action_plan", "Recovery action plan", "textarea"), F("target", "Target date", "datetime")),
        A("escalate_national", "Escalate to national lead", ["open", "revision", "recovery_assigned"], "referred_national", ["R09"], F("summary", "Summary", "textarea"), F("recommendation", "Recommendation", "textarea")),
        A("coordinate_plan", "Coordinate approved plan", ["referred_national"], "authorised", ["R10"], F("functions", "Functions coordinated", hint="e.g. service, finance, quality, channel"),
          F("plan", "Approved plan", "textarea"), F("within_delegation", "Within delegated authority", "select", opts="Yes|No - executive decision reference attached"), F("executive_reference", "Executive decision reference", req=False)),
        A("submit_recovery_update", "Submit recovery update", ["recovery_assigned", "authorised"], "verification", ["R05", "R07", "R08", "R09", "R10", "R12", "R14"], F("actions_taken", "Actions taken", "textarea"), who="assignee_or_creator"),
        A("record_recovery_result", "Record recovery result", ["verification"], "closed", ["R09", "R10"], F("successful", "Recovery successful", "select", opts=YN), F("result", "Result", "textarea")),
    ],
}

WF["mgmt_action"] = {
    "label": "Management action", "prefix": "MA",
    "states": {"requested": S("Requested", "pending", "Owner to start"), "in_progress": S("In progress", "info", "Submit evidence"), "evidence_submitted": S("Evidence submitted", "pending", "Executive review"),
               "revision_required": S("Revised plan required", "urgent", "Submit revised plan"), "accepted": S("Accepted", "done", "", True)},
    "initial": "requested",
    "create": {"action": {"label": "Accountable action request", "roles": ["R17", "R10"], "fields": [
        F("title", "Action requested"), F("scope", "Scope", "select", opts="Region|Product line|Service centre|Channel|National"),
        F("assignee_id", "Accountable owner", "lookup", src="users:R09|R10|R14|R05|R07|R15|R11"), F("expected_outcome", "Expected outcome", "textarea"), F("due", "Due", "date")]}},
    "actions": [A("start_action", "Start action", ["requested", "revision_required"], "in_progress", ALL_INTERNAL, F("plan", "Plan", "textarea"), who="assignee_or_creator"),
                A("submit_evidence", "Submit evidence", ["in_progress"], "evidence_submitted", ALL_INTERNAL, F("evidence_summary", "Evidence of improvement", "textarea"),
                  F("metric_before", "Indicator before"), F("metric_after", "Indicator after"), who="assignee_or_creator"),
                A("review_progress", "Review performance action", ["evidence_submitted"], "accepted", ["R17", "R10"], F("improvement", "Evidence shows improvement", "select", opts=YN), F("feedback", "Feedback", "textarea"))],
}

WF["supplier_dispute"] = {
    "label": "Supplier dispute", "prefix": "SUP",
    "states": {"registered": S("Registered", "info", "Reconcile records"), "reconciling": S("Reconciling", "info", "Record commercial decision"),
               "input_requested": S("Team input requested", "pending", "Await input"), "correction_approval": S("Correction approval", "pending", "Approver decision"),
               "correction_in_progress": S("Correction in progress", "info", "Verify settlement"), "follow_up": S("Follow-up", "urgent", "Chase outstanding action"),
               "closed_no_action": S("Closed - no discrepancy", "muted", "", True), "settled": S("Settled", "done", "", True)},
    "initial": "registered",
    "create": {"dispute": {"label": "Supplier grievance", "roles": ["R20"], "fields": [
        F("org_id", "Supplier", "lookup", src="orgs:supplier"), F("po", "Purchase order"), F("invoice", "Invoice"), F("grn", "Goods receipt"),
        F("issue", "Issue category", "select", opts="Quantity shortfall|Quality rejection|Price variance|Payment dispute|Late delivery"),
        F("amount", "Disputed amount (INR)", "number", min=0), F("description", "Description", "textarea"), F("supporting_records", "Supporting records", req=False)]}},
    "actions": [
        A("reconcile_lines", "Reconcile records", ["registered", "reconciling"], "reconciling", ["R20"], F("lines", "Lines (record, supplier claim, internal record)", "textarea"), F("note", "Note", req=False)),
        A("request_input", "Request team input", ["registered", "reconciling"], "input_requested", ["R20"], F("team", "Team", "select", opts="Finance|Quality|Operations"),
          F("assignee_id", "Input owner", "lookup", src="users:R13|R14"), F("question", "Question", "textarea")),
        A("input_received", "Record input received", ["input_requested"], "reconciling", ["R20"], F("summary", "Input summary", "textarea")),
        A("record_commercial_decision", "Record commercial decision", ["reconciling"], "correction_approval", ["R20"],
          F("discrepancy", "Discrepancy established", "select", opts=YN), F("correction", "Correction", "select", opts="Credit note|Payment adjustment|Replacement goods|Debit note|None"),
          F("amount", "Correction amount (INR)", "number", min=0), F("explanation", "Evidence-based explanation", "textarea", minlen=10)),
        A("execute_correction", "Record executed correction", ["correction_in_progress", "follow_up"], None, ["R20"], F("reference", "Correction reference"), F("executed_amount", "Executed amount (INR)", "number", min=0)),
        A("verify_settlement", "Verify approved settlement", ["correction_in_progress", "follow_up"], "settled", ["R20"], F("complete", "Settlement complete", "select", opts=YN), F("verification", "Verification", "textarea")),
    ],
}

WF["hr_grievance"] = {
    "label": "Confidential HR grievance", "prefix": "HR",
    "states": {"received": S("Received - restricted", "pending", "Triage urgency and conflicts"), "designated_referral": S("Designated referral", "urgent", "Specialist process"),
               "investigation": S("Confidential investigation", "info", "Investigate fairly"), "decision_pending": S("Decision pending", "pending", "Obtain authorised decision"),
               "implementation": S("Implementation", "info", "Implement decision"), "escalated": S("Escalated to authorised owner", "urgent", "Follow up implementation"),
               "follow_up": S("Follow-up", "pending", "Verify follow-up"), "closed": S("Closed with review route", "done", "", True)},
    "initial": "received",
    "create": {"grievance": {"label": "Confidential HR grievance", "roles": ["R19"], "fields": [
        F("restricted_reference", "Restricted case reference", req=False), F("category", "Report category", "select", opts="Harassment|Discrimination|Workplace safety|Pay and benefits|Misconduct|Other"),
        F("complainant_contact", "Complainant contact (restricted)"), F("urgency", "Urgency", "select", opts="Urgent|Standard"),
        F("conflict_declaration", "Conflict declaration", "select", opts="No conflict|Conflict declared"),
        F("designated_process", "Designated process", "select", opts="Standard confidential investigation|Senior HR|Legal|External investigator"),
        F("summary", "Restricted summary", "textarea"), F("evidence_access", "Evidence access", "select", opts="Assigned HR officer only|HR officer and legal")]}},
    "actions": [
        A("triage", "Record triage", ["received"], "investigation", ["R19"], F("urgent_or_specialist", "Urgent or specialist process required", "select", opts=YN), F("referral_to", "Referral to", req=False), F("rationale", "Rationale", "textarea")),
        A("referral_accepted", "Record referral outcome", ["designated_referral"], "investigation", ["R19"], F("referral_reference", "Referral reference")),
        A("save_findings", "Save restricted findings", ["investigation"], None, ["R19"], F("interviews", "Interviews held"), F("evidence", "Evidence considered"), F("findings", "Findings", "textarea")),
        A("submit_for_decision", "Submit for authorised decision", ["investigation"], "decision_pending", ["R19"], F("recommendation", "Recommendation", "textarea")),
        A("record_decision", "Record authorised decision", ["decision_pending"], "implementation", ["R19"], F("decision_authority", "Decision authority"), F("decision_reference", "Decision reference"), F("decision_summary", "Decision summary", "textarea")),
        A("record_implementation", "Record authorised follow up", ["implementation", "escalated"], "follow_up", ["R19"], F("implemented", "Action implemented as required", "select", opts=YN), F("note", "Note", "textarea")),
        A("verify_follow_up", "Verify follow-up and close", ["follow_up"], "closed", ["R19"], F("effective", "Follow-up confirmed", "select", opts="Yes"), F("review_route", "Review route communicated")),
    ],
}

WF["audit"] = {
    "label": "Audit engagement", "prefix": "AUD",
    "states": {"scoping": S("Scoping", "info", "Save scope and sample"), "fieldwork": S("Fieldwork", "info", "Review evidence"), "reporting": S("Reporting", "pending", "Conclude"), "complete": S("Complete", "done", "", True)},
    "initial": "scoping",
    "create": {"engagement": {"label": "Audit engagement", "roles": ["R21"], "fields": [
        F("title", "Engagement title"), F("area", "Audit area", "select", opts="Case handling|Warranty decisions|Settlements|Parts custody|Safety incidents|Access control"),
        F("period_from", "Period from", "date"), F("period_to", "Period to", "date"), F("criteria", "Criteria", "textarea")]}},
    "actions": [
        A("save_scope", "Save audit scope", ["scoping"], "fieldwork", ["R21"], F("record_type", "Population", "select", opts="case|warranty|settlement|requisition|incident|approval"),
          F("sample_size", "Sample size", "number", min=1, max=50), F("method", "Sampling method", "select", opts="Random|Risk-based|Full population")),
        A("record_observation", "Record audit observation", ["fieldwork"], None, ["R21"], F("sampled_ref", "Sampled record reference"),
          F("control", "Control tested", "select", opts="Approval evidence present|Segregation of duties|SLA adherence|Evidence retention|Access appropriate"),
          F("result", "Result", "select", opts="Control effective|Control gap found"), F("observation", "Observation", "textarea")),
        A("complete_fieldwork", "Complete fieldwork", ["fieldwork"], "reporting", ["R21"], F("note", "Summary")),
        A("complete_audit", "Record supported conclusion", ["reporting"], "complete", ["R21"], F("conclusion", "Conclusion", "textarea")),
    ],
}

WF["audit_finding"] = {
    "label": "Audit finding", "prefix": "AF",
    "states": {"open": S("Open", "urgent", "Owner management response"), "remediation": S("Remediation", "info", "Submit remediation evidence"),
               "submitted": S("Remediation submitted", "pending", "Independent retest"), "closed": S("Closed - verified", "done", "", True)},
    "initial": "open",
    "create": {"finding": {"label": "Audit finding", "roles": ["R21"], "fields": [
        F("title", "Finding"), F("severity", "Severity", "select", opts="High|Medium|Low"), F("engagement_id", "Engagement", "lookup", src="records:audit", req=False),
        F("record_ref", "Record reference"), F("condition", "Condition observed", "textarea"), F("criteria", "Criteria"),
        F("action_owner_id", "Action owner", "lookup", src=STAFF_SRC), F("due", "Due", "date")]}},
    "actions": [
        A("accept_finding", "Record management response", ["open"], "remediation", ALL_INTERNAL + ["R18"], F("response", "Management response", "textarea"), who="action_owner"),
        A("submit_remediation", "Submit remediation evidence", ["remediation"], "submitted", ALL_INTERNAL + ["R18"], F("remediation", "Remediation summary", "textarea"), who="action_owner", ev=1),
        A("record_retest", "Record independent retest", ["submitted"], "closed", ["R21"], F("effective", "Remediation effective", "select", opts=YN), F("method", "Retest method"), F("conclusion", "Conclusion", "textarea")),
    ],
}

CONFIG_TARGETS = "sla_policies|business_calendar|authority_matrix|templates|feature_flags|reopen_window_days|capacity|retention_schedules|workflow"
WF["config_change"] = {
    "label": "Configuration change", "prefix": "CFG",
    "states": {"requested": S("Requested", "pending", "Check scope"), "clarification": S("Clarification", "pending", "Clarify with requester"),
               "configured": S("Configured", "info", "Test representative paths"), "test_failed": S("Checks failed", "urgent", "Correct configuration"),
               "tested": S("Checks passed", "info", "Request release approval"), "awaiting_release": S("Awaiting release approval", "pending", "Second administrator approval"),
               "released": S("Released", "done", "Monitor"), "rolled_back": S("Rolled back", "muted", "", True)},
    "initial": "requested",
    "create": {"change": {"label": "Configuration change request", "roles": ["R18"], "fields": [
        F("target", "Configuration target", "select", opts=CONFIG_TARGETS), F("workflow_type", "Workflow type (if target is workflow)", req=False),
        F("change_summary", "Change summary", "textarea"), F("approval_reference", "Approval reference"), F("proposed_value", "Proposed value (JSON)", "json")]}},
    "actions": [
        A("check_scope", "Check request scope", ["requested"], "configured", ["R18"], F("within_scope", "Request within scope", "select", opts=YN), F("note", "Scope note")),
        A("edit_proposal", "Correct configuration", ["clarification", "test_failed", "configured"], "configured", ["R18"], F("proposed_value", "Proposed value (JSON)", "json")),
        A("run_tests", "Submit release evidence", ["configured", "test_failed"], "tested", ["R18"], F("scenario_note", "Scenario tested", req=False)),
        A("request_release", "Request release approval", ["tested"], "awaiting_release", ["R18"], F("note", "Release note")),
        A("release", "Release approved version", ["awaiting_release"], "released", ["R18"], F("note", "Release note", req=False)),
        A("rollback", "Roll back release", ["released"], "rolled_back", ["R18"], F("reason", "Rollback reason", "textarea"), danger=True),
    ],
}

WF["policy"] = {
    "label": "Policy / master version", "prefix": "POL",
    "states": {"draft": S("Draft", "info", "Submit for review"), "in_review": S("In review", "pending", "Independent reviewer"), "published": S("Published", "done", ""),
               "superseded": S("Superseded", "muted", "", True), "rejected": S("Returned", "muted", "", True)},
    "initial": "draft",
    "create": {
        "warranty_term": {"label": "Component warranty terms", "roles": ["R11"], "fields": [
            F("model_id", "Product model", "lookup", src="models"), F("component", "Component"), F("version", "Policy version"),
            F("coverage_basis", "Coverage basis", "select", opts="Months from purchase|Months from installation|Usage hours|Not covered"),
            F("coverage_months", "Coverage period (months) - placeholder pending BRD", "number", min=0), F("evidence_required", "Required purchase evidence"),
            F("exclusion", "Exclusion condition", "textarea"), F("effective", "Effective from", "date"), F("reviewer_id", "Authorised reviewer", "lookup", src="users:R11|R10")]},
        "product_model": {"label": "Product model master", "roles": ["R18"], "fields": [
            F("category", "Product category", "select", opts=CATS), F("model", "Approved model name"), F("components", "Component catalogue (comma separated)"),
            F("serial_rule", "Serial identification rule", hint="Regex e.g. ^CL55[0-9]{6}$"), F("skill", "Service skills required", "select", opts="Cooling|Water heating|Pumps|Heating|Fans|Kitchen|Power backup"),
            F("effective", "Active from", "date"), F("owner", "Business owner"), F("approval_reference", "Master approval reference")]},
        "service_standard": {"label": "Service standard", "roles": ["R10", "R18"], "fields": [
            F("title", "Policy"), F("version", "Version"), F("coverage", "Coverage"), F("effective", "Effective date", "date"), F("content", "Standard", "textarea")]},
        "policy": {"label": "Policy version", "roles": ["R18"], "fields": [
            F("title", "Policy"), F("version", "Version"), F("effective", "Effective date", "date"), F("content", "Policy content", "textarea"), F("reviewer_id", "Reviewer", "lookup", src="users:R18|R10")]},
    },
    "actions": [
        A("submit_for_review", "Submit for review", ["draft"], "in_review", ["R18", "R10", "R11"], who="creator"),
        A("publish", "Publish version", ["in_review"], "published", ["R18", "R10", "R11"], F("review_note", "Review evidence"), who="not_creator"),
        A("return_draft", "Return to maker", ["in_review"], "draft", ["R18", "R10", "R11"], F("reason", "Reason"), who="not_creator"),
        A("supersede", "Supersede", ["published"], "superseded", ["R18", "R10", "R11"], F("reason", "Reason")),
    ],
}

WF["legal_hold"] = {
    "label": "Legal hold", "prefix": "LH",
    "states": {"requested": S("Requested", "pending", "Second administrator activation"), "active": S("Active hold", "urgent", "Review on date"), "released": S("Released", "done", "", True)},
    "initial": "requested",
    "create": {"hold": {"label": "Controlled legal hold", "roles": ["R18"], "fields": [
        F("record_class", "Record class", "select", opts="Cases|Communications|Evidence|Settlements|Audit logs"), F("record_ref", "Case or record reference"),
        F("reason", "Hold reason", "textarea"), F("hold_owner", "Authorised hold owner"), F("starts", "Hold starts", "date"), F("review_date", "Review date", "date"),
        F("scope", "Permitted scope"), F("approval_evidence", "Approval evidence")]}},
    "actions": [A("activate_hold", "Activate hold", ["requested"], "active", ["R18"], F("note", "Activation note"), who="not_creator"),
                A("release_hold", "Release hold", ["active"], "released", ["R18"], F("reason", "Release reason", "textarea"), who="not_creator")],
}

TERMINAL = {t: [s for s, d in w["states"].items() if d["terminal"]] for t, w in WF.items()}
ACTIONS = {t: {a["key"]: a for a in w["actions"]} for t, w in WF.items()}


def action_from(a, wf_type):
    frm = a["from"]
    if isinstance(frm, str):
        parts = frm.split("|")
        out = []
        for p in parts:
            if p == "*open":
                out += [s for s in WF[wf_type]["states"] if s not in TERMINAL[wf_type]]
            else:
                out.append(p)
        return out
    return frm


def meta():
    return {t: {"label": w["label"], "prefix": w["prefix"], "states": w["states"], "initial": w["initial"],
                "create": {k: {"label": v["label"], "roles": v["roles"], "fields": v["fields"]} for k, v in w["create"].items()},
                "actions": [{**a, "from": action_from(a, t)} for a in w["actions"]]} for t, w in WF.items()}
