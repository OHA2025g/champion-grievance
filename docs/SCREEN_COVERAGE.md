# Screen coverage report (generated from backend/screens.py)

Total screens: 161 · mapped: 161

| Screen | Role | Title | Renderer | Record type | Focus actions | Workflow | FR |
|---|---|---|---|---|---|---|---|
| CE-001 | shared | Welcome to Champion Service | login |  |  | Shared access | FR001 to FR003 |
| CE-002 | shared | Verify your contact | otp |  |  | Shared access | FR001 |
| CE-003 | shared | Recover staff access | recover |  |  | Shared access | FR001 |
| CE-004 | shared | Notifications and preferences | prefs |  |  | Shared access | FR023 |
| CE-005 | R01 | Your service overview | dashboard |  |  | Customer complaint | FR056 to FR059 |
| CE-006 | R01 | My complaints | list | case |  | Shared access | FR056 to FR059 |
| CE-007 | R01 | Raise a product complaint | create | case |  | Customer complaint | FR056 to FR059 |
| CE-008 | R01 | Your complaint timeline | record | case | add_update, provide_information | Customer complaint | FR056 to FR059 |
| CE-009 | R01 | Upload supporting evidence | upload | case |  | Shared access | FR056 to FR059 |
| CE-010 | R01 | Confirm your service visit | record | job | customer_confirm_appointment, customer_request_reschedule | Customer complaint | FR056 to FR059 |
| CE-011 | R01 | Review repair estimate | record | job | customer_accept_estimate, customer_decline_estimate | Customer complaint | FR056 to FR059 |
| CE-012 | R01 | Rate your service experience | record | case | customer_confirm, customer_reject | Customer complaint | FR056 to FR059 |
| CE-013 | R01 | Reopen a service request | record | case | reopen | Appeal and reopening | FR056 to FR059 |
| CE-014 | R01 | Request a decision review | record | case | request_review | Appeal and reopening | FR056 to FR059 |
| CE-015 | R02 | Dealer service overview | dashboard |  |  | Dealer assistance and claim | FR053 to FR055 |
| CE-016 | R02 | Register a customer case | create | case |  | Dealer assistance and claim | FR053 to FR055 |
| CE-017 | R02 | Damaged stock claim | create | case |  | Dealer assistance and claim | FR053 to FR055 |
| CE-018 | R02 | Verify sale evidence | record | case | confirm_sale, submit_verification | Dealer assistance and claim | FR053 to FR055 |
| CE-019 | R02 | Product handover record | record | case | confirm_handover, customer_confirm | Dealer assistance and claim | FR053 to FR055 |
| CE-020 | R02 | Dealer claim settlement | list | settlement |  | Dealer assistance and claim | FR053 to FR055 |
| CE-021 | R03 | Business account overview | dashboard |  |  | Distributor bulk grievance | FR053 to FR055 |
| CE-022 | R03 | Find a business order | orders |  |  | Distributor bulk grievance | FR053 to FR055 |
| CE-023 | R03 | Create a bulk grievance | create | case |  | Distributor bulk grievance | FR053 to FR055 |
| CE-024 | R03 | Upload affected units | record | case | validate_units | Distributor bulk grievance | FR053 to FR055 |
| CE-025 | R03 | Track units and sites | list | unit |  | Distributor bulk grievance | FR053 to FR055 |
| CE-026 | R03 | Business reconciliation | record | case | reconcile_bulk, customer_confirm | Distributor bulk grievance | FR053 to FR055 |
| CE-027 | R04 | Support command desk | dashboard |  |  | Contact intake and safety | FR007 to FR019 |
| CE-028 | R04 | Omnichannel contact inbox | list | contact |  | Contact intake and safety | FR007 to FR019 |
| CE-029 | R04 | Search customer and product | customer_search |  |  | Contact intake and safety | FR007 to FR019 |
| CE-030 | R04 | Register and classify contact | record | contact | open_contact, register_case, link_to_case, close_contact | Contact intake and safety | FR007 to FR019 |
| CE-031 | R04 | Immediate safety screening | record | case | escalate_safety | Contact intake and safety | FR007 to FR019 |
| CE-032 | R04 | Review possible duplicates | record | case | link_duplicate, not_duplicate | Contact intake and safety | FR007 to FR019 |
| CE-033 | R04 | Route and accept ownership | record | case | register_route | Contact intake and safety | FR007 to FR019 |
| CE-034 | R05 | My case workspace | dashboard |  |  | Owned case coordination | FR017 to FR027 |
| CE-035 | R05 | Case detail and next actions | record | case | plan_resolution, create_service_job, request_remedy_approval, request_warranty_review, escalate_case, mark_resolved | Owned case coordination | FR017 to FR027 |
| CE-036 | R05 | Case tasks and dependencies | kanban | task |  | Owned case coordination | FR017 to FR027 |
| CE-037 | R05 | Service appointment scheduler | calendar |  |  | Owned case coordination | FR017 to FR027 |
| CE-038 | R05 | Ownership handoff acceptance | record | case | accept_ownership, decline_ownership | Owned case coordination | FR017 to FR027 |
| CE-039 | R05 | SLA and waiting queue | sla |  |  | Shared access | FR017 to FR027 |
| CE-040 | R05 | Compose a customer update | record | case | send_update | Owned case coordination | FR017 to FR027 |
| CE-041 | R05 | Verify outcome and close | record | case | verify_and_close | Owned case coordination | FR017 to FR027 |
| CE-042 | R06 | Today on the field | m_dashboard |  |  | Technician job | FR028 to FR034 |
| CE-043 | R06 | My assigned service jobs | m_jobs |  |  | Technician job | FR028 to FR034 |
| CE-044 | R06 | Visit details and attendance | m_job |  | record_arrival | Technician job | FR028 to FR034 |
| CE-045 | R06 | Product diagnosis | m_job |  | submit_diagnosis | Technician job | FR028 to FR034 |
| CE-046 | R06 | Request spare parts | m_job |  | request_parts | Technician job | FR028 to FR034 |
| CE-047 | R06 | Prepare a repair estimate | m_job |  | submit_estimate | Technician job | FR028 to FR034 |
| CE-048 | R06 | Repair work record | m_job |  | record_repair | Technician job | FR028 to FR034 |
| CE-049 | R06 | Functional and safety tests | m_job |  | submit_tests | Technician job | FR028 to FR034 |
| CE-050 | R06 | Customer handover | m_job |  | submit_handover | Technician job | FR028 to FR034 |
| CE-051 | R06 | Offline drafts and sync review | m_sync |  |  | Technician job | FR028 to FR034 |
| CE-052 | R07 | Service centre overview | dashboard |  |  | Service centre dispatch | FR028 to FR034 |
| CE-053 | R07 | Technician roster and capacity | roster |  |  | Service centre dispatch | FR028 to FR034 |
| CE-054 | R07 | Service dispatch readiness | record | job | allocate, propose_appointment, confirm_on_behalf, confirm_dispatch, request_support | Service centre dispatch | FR028 to FR034 |
| CE-055 | R07 | Review completed job evidence | record | job | accept_report, return_for_correction | Service centre dispatch | FR028 to FR034 |
| CE-056 | R07 | Missed visit recovery | record | job | record_missed_visit, allocate, propose_appointment | Service centre dispatch | FR028 to FR034 |
| CE-057 | R08 | Technical review overview | dashboard |  |  | Technical decision | FR035 to FR041 |
| CE-058 | R08 | Technical review queue | list | tech_review |  | Technical decision | FR035 to FR041 |
| CE-059 | R08 | Compare diagnosis and prior repairs | record | tech_review | request_inspection | Technical decision | FR035 to FR041 |
| CE-060 | R08 | Review a repeat failure | record | tech_review | record_recommendation, close_review | Technical decision | FR035 to FR041 |
| CE-061 | R08 | Remedy approval request | record | tech_review | submit_decision | Technical decision | FR035 to FR041 |
| CE-062 | R09 | Regional service overview | dashboard |  |  | Regional recovery | FR024 to FR027 |
| CE-063 | R09 | Regional backlog and ageing | list | case |  | Regional recovery | FR024 to FR027 |
| CE-064 | R09 | Regional service capacity | capacity |  |  | Regional recovery | FR024 to FR027 |
| CE-065 | R09 | Regional escalation detail | record | escalation | assign_recovery_owner, escalate_national | Regional recovery | FR024 to FR027 |
| CE-066 | R09 | Verify a recovery plan | record | escalation | record_recovery_result, submit_recovery_update | Regional recovery | FR024 to FR027 |
| CE-067 | R10 | National service overview | dashboard |  |  | National service governance | FR066 to FR069 |
| CE-068 | R10 | National service network | network |  |  | National service governance | FR066 to FR069 |
| CE-069 | R10 | Major escalation coordination | record | escalation | coordinate_plan, record_recovery_result | National service governance | FR066 to FR069 |
| CE-070 | R10 | Service standards and coverage | list | policy |  | National service governance | FR066 to FR069 |
| CE-071 | R11 | Warranty claims overview | dashboard |  |  | Warranty decision | FR035 to FR037 |
| CE-072 | R11 | Warranty claim queue | list | warranty |  | Warranty decision | FR035 to FR037 |
| CE-073 | R11 | Product and component warranty terms | list | policy |  | Warranty decision | FR035 to FR037 |
| CE-074 | R11 | Assess warranty eligibility | record | warranty | check_evidence, record_coverage_decision | Warranty decision | FR035 to FR037 |
| CE-075 | R11 | Explain a coverage decision | record | warranty | explain_decision, route_dispute, close_claim | Warranty decision | FR035 to FR037 |
| CE-076 | R12 | Parts and logistics overview | dashboard |  |  | Parts and replacement | FR042 to FR048 |
| CE-077 | R12 | Parts requisition queue | list | requisition |  | Parts and replacement | FR042 to FR048 |
| CE-078 | R12 | Stock availability by warehouse | stock |  |  | Parts and replacement | FR042 to FR048 |
| CE-079 | R12 | Reserve and issue a compatible part | record | requisition | validate_requisition, reserve_stock, mark_unavailable, receive_stock | Parts and replacement | FR042 to FR048 |
| CE-080 | R12 | Shipment tracking and delivery | record | requisition | dispatch, record_delivery, record_usage | Parts and replacement | FR042 to FR048 |
| CE-081 | R12 | Delivery exception handling | record | requisition | resolve_exception | Parts and replacement | FR042 to FR048 |
| CE-082 | R12 | Defective returns and custody | record | return | record_receipt, close_return | Parts and replacement | FR042 to FR048 |
| CE-083 | R12 | Safety quarantine inventory | record | return | record_receipt, open_restricted_examination, close_return | Parts and replacement | FR042 to FR048 |
| CE-084 | R12 | Stock movement reconciliation | movements |  |  | Parts and replacement | FR042 to FR048 |
| CE-085 | R13 | Finance settlement overview | dashboard |  |  | Financial remedy | FR049 to FR052 |
| CE-086 | R13 | Approved settlement queue | list | settlement |  | Financial remedy | FR049 to FR052 |
| CE-087 | R13 | Validate refund recipient | record | settlement | validate_recipient, resolve_discrepancy | Financial remedy | FR049 to FR052 |
| CE-088 | R13 | Execute approved payment instruction | record | settlement | submit_instruction | Financial remedy | FR049 to FR052 |
| CE-089 | R13 | Unknown payment outcome review | record | settlement | check_status | Financial remedy | FR049 to FR052 |
| CE-090 | R13 | Payment reconciliation | record | settlement | reconcile | Financial remedy | FR049 to FR052 |
| CE-091 | R13 | Issue a credit note | create | settlement |  | Financial remedy | FR049 to FR052 |
| CE-092 | R13 | Settlement correcting entry | record | settlement | request_correction | Financial remedy | FR049 to FR052 |
| CE-093 | R14 | Quality and safety overview | dashboard |  |  | Safety and recurrence prevention | FR063 to FR065 |
| CE-094 | R14 | Urgent safety incident inbox | list | incident |  | Safety and recurrence prevention | FR063 to FR065 |
| CE-095 | R14 | Safety incident detail and containment | record | incident | triage, record_containment, preserve_evidence | Safety and recurrence prevention | FR063 to FR065 |
| CE-096 | R14 | Related units and batch exposure | record | incident | link_units | Safety and recurrence prevention | FR063 to FR065 |
| CE-097 | R14 | Root cause investigation | record | incident | submit_findings | Safety and recurrence prevention | FR063 to FR065 |
| CE-098 | R14 | Corrective and preventive action plan | kanban | capa |  | Safety and recurrence prevention | FR063 to FR065 |
| CE-099 | R14 | Verify corrective action effectiveness | record | incident | plan_capa, request_verification, verify_effectiveness | Safety and recurrence prevention | FR063 to FR065 |
| CE-100 | R15 | Channel support overview | dashboard |  |  | Channel recovery | FR053 to FR055 |
| CE-101 | R15 | Dealer conduct and supply disputes | list | channel_dispute |  | Channel recovery | FR053 to FR055 |
| CE-102 | R15 | Review customer and dealer evidence | record | channel_dispute | request_clarification, clarification_received, record_findings, decide_dispute | Channel recovery | FR053 to FR055 |
| CE-103 | R15 | Channel service recovery plan | record | channel_dispute | assign_recovery, record_action_status, verify_outcome | Channel recovery | FR053 to FR055 |
| CE-104 | R16 | Appeals overview | dashboard |  |  | Appeal and reopening | FR060 to FR062 |
| CE-105 | R16 | Appeals intake queue | record | appeal | assign_reviewer | Appeal and reopening | FR060 to FR062 |
| CE-106 | R16 | Independent appeal evidence review | record | appeal | record_findings, request_explanation, explanation_received | Appeal and reopening | FR060 to FR062 |
| CE-107 | R16 | Appeal decision and remedy | record | appeal | issue_decision, assign_remedy, verify_remedy, close_appeal | Appeal and reopening | FR060 to FR062 |
| CE-108 | R16 | External correspondence register | list | correspondence |  | Appeal and reopening | FR060 to FR062 |
| CE-109 | R17 | Executive service overview | dashboard |  |  | Executive review | FR066 to FR069 |
| CE-110 | R17 | Product complaint incidence | analytics |  |  | Executive review | FR066 to FR069 |
| CE-111 | R17 | Service performance and trends | analytics |  |  | Executive review | FR066 to FR069 |
| CE-112 | R17 | Remedy costs and exposure | analytics |  |  | Executive review | FR066 to FR069 |
| CE-113 | R17 | Management action tracking | kanban | mgmt_action |  | Executive review | FR066 to FR069 |
| CE-114 | R17 | Export requests and downloads | exports |  |  | Executive review | FR066 to FR069 |
| CE-115 | R18 | Administration overview | dashboard |  |  | Controlled administration | FR070 to FR073 |
| CE-116 | R18 | User and access administration | admin_users |  |  | Controlled administration | FR070 to FR073 |
| CE-117 | R18 | Role scopes and confidentiality | admin_permissions |  |  | Controlled administration | FR070 to FR073 |
| CE-118 | R18 | Product model and component masters | models |  |  | Controlled administration | FR070 to FR073 |
| CE-119 | R18 | Policy version publication | list | policy |  | Controlled administration | FR070 to FR073 |
| CE-120 | R18 | Service calendars and holidays | admin_config |  |  | Controlled administration | FR070 to FR073 |
| CE-121 | R18 | Approval authority matrix | admin_config |  |  | Controlled administration | FR070 to FR073 |
| CE-122 | R18 | Customer communication templates | admin_config |  |  | Controlled administration | FR070 to FR073 |
| CE-123 | R18 | Integration health and event lag | admin_integrations |  |  | Controlled administration | FR070 to FR073 |
| CE-124 | R18 | Failed events and controlled replay | admin_events |  |  | Controlled administration | FR070 to FR073 |
| CE-125 | R18 | Retention schedules and legal holds | admin_retention |  |  | Controlled administration | FR070 to FR073 |
| CE-126 | R18 | Access and business audit history | admin_audit |  |  | Controlled administration | FR070 to FR073 |
| CE-127 | R19 | Confidential HR overview | dashboard |  |  | Confidential HR | FR074 to FR076 |
| CE-128 | R19 | Confidential HR grievance intake | create | hr_grievance |  | Confidential HR | FR074 to FR076 |
| CE-129 | R19 | Restricted HR investigation | record | hr_grievance | triage, referral_accepted, save_findings, submit_for_decision, record_decision | Confidential HR | FR074 to FR076 |
| CE-130 | R19 | HR decision implementation and follow up | record | hr_grievance | record_implementation, verify_follow_up | Confidential HR | FR074 to FR076 |
| CE-131 | R20 | Supplier relations overview | dashboard |  |  | Supplier resolution | FR077 to FR079 |
| CE-132 | R20 | Supplier grievance registration | create | supplier_dispute |  | Supplier resolution | FR077 to FR079 |
| CE-133 | R20 | Purchase and quality dispute reconciliation | record | supplier_dispute | reconcile_lines, request_input, input_received, record_commercial_decision | Supplier resolution | FR077 to FR079 |
| CE-134 | R20 | Supplier correction and settlement | record | supplier_dispute | execute_correction, verify_settlement | Supplier resolution | FR077 to FR079 |
| CE-135 | R21 | Audit overview | dashboard |  |  | Independent audit | FR080 to FR082 |
| CE-136 | R21 | Audit scope and sample selection | record | audit | save_scope | Independent audit | FR080 to FR082 |
| CE-137 | R21 | Read only case evidence review | record | audit | record_observation, complete_fieldwork, complete_audit | Independent audit | FR080 to FR082 |
| CE-138 | R21 | Audit findings and management response | list | audit_finding |  | Independent audit | FR080 to FR082 |
| CE-139 | R21 | Independent remediation retest | record | audit_finding | record_retest | Independent audit | FR080 to FR082 |
| CE-140 | R05 | Form validation and preserved draft | create | case |  | Exceptions and assisted work | FR008 FR020 |
| CE-141 | R04 | No matching customer records | customer_search |  |  | Exceptions and assisted work | FR014 |
| CE-142 | R18 | Restricted access response | forbidden |  |  | Exceptions and assisted work | FR002 |
| CE-143 | R05 | Closure blocked by pending work | record | case | mark_resolved, verify_and_close | Exceptions and assisted work | FR056 FR057 |
| CE-144 | R13 | Payment submitted and pending confirmation | record | settlement | check_status | Financial remedy | FR050 FR051 |
| CE-145 | R18 | Integration unavailable and recovery | integration_error |  |  | Exceptions and assisted work | FR072 |
| CE-146 | shared | Interface components and state reference | components |  |  | Shared access | Shared interface system |
| CE-147 | R05 | Reviewed assistance and case summary | record | case |  | Exceptions and assisted work | FR083 to FR085 |
| CE-148 | R04 | Original and translated complaint | record | case | save_translation | Exceptions and assisted work | FR083 to FR085 |
| CE-149 | R08 | Approved service knowledge search | knowledge |  |  | Technical decision | FR083 to FR085 |
| CE-150 | R01 | Product and purchase verification | record | case | submit_verification | Customer complaint | FR008 FR035 |
| CE-151 | R05 | Create a linked operational task | record | case | create_linked_task | Owned case coordination | FR019 |
| CE-152 | R05 | Record an approved waiting period | record | case | record_waiting, resume_work | Owned case coordination | FR025 FR027 |
| CE-153 | R18 | Validate policy change before publication | record | config_change | check_scope, edit_proposal, run_tests, request_release, release, rollback | Controlled administration | FR006 FR070 |
| CE-154 | R05 | Customer unreachable closure review | record | case | request_supervised_closure | Shared access | FR057 |
| CE-155 | R12 | Create an approved replacement order | create | replacement |  | Parts and replacement | FR046 to FR048 |
| CE-156 | R12 | Replacement delivery and collection milestones | record | replacement | schedule_delivery, record_replacement_delivery, record_collection, record_milestone_exception | Parts and replacement | FR046 to FR048 |
| CE-157 | R04 | Evidence quarantine and scan review | quarantine_evidence |  |  | Exceptions and assisted work | FR020 FR021 |
| CE-158 | R18 | Invite a user with scoped access | invite |  |  | Controlled administration | FR001 to FR003 |
| CE-159 | R18 | Create a product model master | create | policy |  | Controlled administration | FR004 FR006 |
| CE-160 | R18 | Place a controlled legal hold | create | legal_hold |  | Controlled administration | FR073 |
| CE-161 | R11 | Configure component warranty terms | create | policy |  | Warranty decision | FR005 FR006 |
