# Role permission matrix (generated from backend/rbac.py and workflows.py)

Scopes: all, own, org, owner, tech, tech_case, centre, region, assigned, approver, customer, hr, minimal, ro (read-only).

| Role | Name | Workspace | Home | case | contact | task | job | unit | tech_review | approval | warranty | requisition | return | replacement | settlement | incident | capa | channel_dispute | appeal | correspondence | escalation | mgmt_action | supplier_dispute | hr_grievance | audit | audit_finding | config_change | policy | legal_hold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R01 | Customer / Complainant | Customer portal | CE-005 | own |  |  | customer |  |  |  | own |  |  | customer | customer |  |  |  | own |  |  |  |  |  |  |  |  |  |  |
| R02 | Dealer / Retailer | Channel portal | CE-015 | org |  |  | org |  |  |  | org |  |  |  | org |  |  | org | org |  |  |  |  |  |  |  |  |  |  |
| R03 | Distributor / Business Account User | Channel portal | CE-021 | org |  |  | org | org |  |  |  |  |  |  | org |  |  |  | org |  |  |  |  |  |  |  |  |  |  |
| R04 | Customer Support Agent | Agent workspace | CE-027 | all | all |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | assigned |  |  |  |
| R05 | Case Owner / Service Coordinator | Case workspace | CE-034 | owner |  | all | all | all | all | approver | all | all |  | all | all | all | assigned |  |  |  | all | assigned |  |  |  | assigned |  |  |  |
| R06 | Field Technician / Service Engineer | Technician PWA | CE-042 | tech_case |  |  | tech |  | tech |  |  | tech |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| R07 | Authorised Service Centre Manager | Service centre workspace | CE-052 | centre |  | assigned | centre |  |  | approver |  | centre |  |  |  |  |  |  |  |  | centre | assigned |  |  |  | assigned |  |  |  |
| R08 | Service Supervisor / Technical Reviewer | Technical workspace | CE-057 | all |  | assigned | all |  | all | approver |  |  |  |  |  |  | assigned |  |  |  | assigned | assigned |  |  |  | assigned |  | ro |  |
| R09 | Regional Service Manager | Regional dashboard | CE-062 | region |  | region | region | region | region | approver | region | region |  |  | region | region |  |  |  |  | region | region |  |  |  | assigned |  |  |  |
| R10 | National Service Head | National dashboard | CE-067 | all |  | all | all | all | all | all | all | all |  | all | all | all | all | all | all |  | all | all |  |  |  | assigned |  | all |  |
| R11 | Warranty and Claims Officer | Warranty workspace | CE-071 | all |  | assigned | all |  |  | approver | all |  |  |  |  |  |  |  |  |  |  | assigned |  |  |  | assigned |  | all |  |
| R12 | Spare Parts / Warehouse / Logistics Officer | Parts workspace | CE-076 |  |  | assigned | all |  |  |  |  | all | all | all |  | all | assigned |  |  |  |  | assigned |  |  |  | assigned |  |  |  |
| R13 | Finance and Settlement Officer | Finance workspace | CE-085 | minimal |  | assigned |  |  |  | approver |  |  |  |  | all |  |  |  |  |  |  | assigned | assigned |  |  | assigned |  |  |  |
| R14 | Quality and Product Safety Officer | Quality workspace | CE-093 | all |  | assigned | all |  |  | approver |  |  | all |  |  | all | all |  |  |  | assigned | assigned | assigned |  |  | assigned |  | ro |  |
| R15 | Dealer / Channel Support Manager | Channel support workspace | CE-100 | all |  | assigned |  |  |  | approver |  |  |  |  | all |  |  | all |  |  |  | assigned |  |  |  | assigned |  |  |  |
| R16 | Grievance and Appeals Officer | Appeals workspace | CE-104 | all |  | assigned |  |  |  | approver | all |  |  |  | all |  |  |  | all | all |  | assigned |  |  |  | assigned |  |  |  |
| R17 | Management / Executive Viewer | Executive dashboard | CE-109 | ro |  |  |  |  |  |  |  |  |  |  |  | ro |  |  |  |  | ro | all |  |  |  |  |  |  |  |
| R18 | System Administrator | Administration console | CE-115 |  |  |  |  |  |  | approver |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | assigned | all | all | all |
| R19 | HR Grievance Officer | Restricted HR workspace | CE-127 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | hr |  |  |  |  |  |
| R20 | Procurement / Supplier Relations Officer | Supplier workspace | CE-131 |  |  | assigned |  |  |  | approver |  |  |  |  |  |  | assigned |  |  |  |  | assigned | all |  |  | assigned |  |  |  |
| R21 | Auditor | Audit workspace | CE-135 | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro | ro |  | ro |  | all | all | ro | ro | ro |

## Workflow actions and permitted roles

### Case (`case`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Register and route | register_route | registered, safety_escalated, reopened | awaiting_owner | R04 |
| Escalate to safety lead | escalate_safety | registered, awaiting_owner, in_progress, evidence_requested, reopened | safety_escalated | R04, R05 |
| Link to existing case | link_duplicate | registered | duplicate | R04 |
| Confirm not a duplicate | not_duplicate | registered | (conditional) | R04 |
| Save reviewed translation | save_translation | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R04 |
| Log a manual call | log_call | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R04, R05 |
| Accept ownership | accept_ownership | awaiting_owner, reopened | in_progress | R05 |
| Decline handoff | decline_ownership | awaiting_owner | registered | R05 |
| Hand off ownership | handoff | in_progress | awaiting_owner | R05 |
| Plan resolution | plan_resolution | in_progress | (conditional) | R05 |
| Create service job | create_service_job | in_progress | (conditional) | R05 |
| Create linked task | create_linked_task | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R05, R15 |
| Request warranty assessment | request_warranty_review | in_progress | (conditional) | R05 |
| Request technical review | request_technical_review | in_progress | (conditional) | R05 |
| Request information | request_evidence | registered, awaiting_owner, in_progress | evidence_requested | R04, R05, R11, R15 |
| Provide requested information | provide_information | evidence_requested | in_progress | R01, R02, R03 |
| Submit waiting record | record_waiting | in_progress | waiting | R05 |
| Resume work | resume_work | waiting | in_progress | R05 |
| Escalate and arrange recovery | escalate_case | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R04, R05, R09 |
| Send reviewed update | send_update | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened, resolved | (conditional) | R05 |
| Request remedy approval | request_remedy_approval | in_progress | (conditional) | R05 |
| Validate unit list | validate_units | registered, awaiting_owner, in_progress | (conditional) | R03 |
| Create unit jobs | create_unit_jobs | in_progress | (conditional) | R05 |
| Submit verification details | submit_verification | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R01, R02 |
| Confirm sale record | confirm_sale | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened | (conditional) | R02 |
| Confirm handover | confirm_handover | in_progress, resolved | (conditional) | R02 |
| Mark resolved | mark_resolved | in_progress | resolved | R05 |
| Record closure outcome | verify_and_close | resolved | closed | R05 |
| Request supervised closure | request_supervised_closure | resolved | (conditional) | R05 |
| Confirm resolution and rate | customer_confirm | resolved | closed | R01, R02, R03 |
| Issue not resolved | customer_reject | resolved | in_progress | R01, R02, R03 |
| Confirm reconciliation | reconcile_bulk | resolved, in_progress | closed | R03 |
| Request reopening | reopen | closed | reopened | R01, R02, R03, R04, R05 |
| Submit appeal | request_review | closed, resolved, in_progress | (conditional) | R01, R02, R03 |
| Add an update | add_update | registered, safety_escalated, awaiting_owner, in_progress, evidence_requested, waiting, resolved, reopened, resolved | (conditional) | R01, R02, R03 |

### Contact (`contact`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Open contact | open_contact | new | in_review | R04 |
| Register and route | register_case | new, in_review | registered | R04 |
| Link to existing case | link_to_case | new, in_review | linked | R04 |
| Close without case | close_contact | new, in_review | closed | R04 |

### Task (`task`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Start task | start_task | open, blocked | in_progress | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Mark blocked | block_task | open, in_progress | blocked | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Complete task | complete_task | open, in_progress | done | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Cancel task | cancel_task | open, in_progress, blocked | cancelled | R05, R15, R14, R16 |

### Service job (`job`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Assign available engineer | allocate | created, missed | allocated | R07 |
| Request support / reassignment | request_support | created | (conditional) | R07 |
| Rebalance to another centre | reassign_centre | created, allocated | created | R09 |
| Propose appointment | propose_appointment | allocated, missed | appointment_proposed | R05, R07 |
| Confirm appointment | customer_confirm_appointment | appointment_proposed | appointment_confirmed | R01, R02, R03 |
| Request another time | customer_request_reschedule | appointment_proposed | allocated | R01, R02, R03 |
| Record customer confirmation (call) | confirm_on_behalf | appointment_proposed | appointment_confirmed | R05, R07 |
| Confirm dispatch | confirm_dispatch | appointment_confirmed | dispatched | R07 |
| Record arrival | record_arrival | dispatched | on_site | R06 |
| Submit diagnosis | submit_diagnosis | on_site, diagnosed | diagnosed | R06 |
| Request part | request_parts | diagnosed, on_site, authorised | awaiting_parts | R06 |
| Submit for approval | submit_estimate | diagnosed | awaiting_approval | R06 |
| Accept estimate | customer_accept_estimate | awaiting_approval, authorised | (conditional) | R01, R02, R03 |
| Decline estimate | customer_decline_estimate | awaiting_approval, authorised | diagnosed | R01, R02, R03 |
| Save repair record | record_repair | diagnosed, authorised | repaired | R06 |
| Submit test results | submit_tests | repaired | tested | R06 |
| Submit completion evidence | submit_handover | tested, returned | completed | R06 |
| Accept job report | accept_report | completed | accepted | R07 |
| Return for correction | return_for_correction | completed | returned | R07 |
| Approve recovery plan | record_missed_visit | dispatched, appointment_confirmed | missed | R07 |
| Cancel job | cancel_job | created, allocated, appointment_proposed | cancelled | R05 |

### Unit (`unit`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Mark unit resolved | mark_unit_resolved | open, job_created, unresolved | resolved | R05 |
| Mark unresolved | mark_unit_unresolved | job_created | unresolved | R05 |

### Technical review (`tech_review`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Request further inspection | request_inspection | pending, recommended | further_inspection | R08 |
| Submit updated diagnosis | inspection_updated | further_inspection | pending | R06, R05 |
| Record recommendation | record_recommendation | pending | recommended | R08 |
| Submit technical decision | submit_decision | recommended | approved | R08 |
| Close review | close_review | pending, recommended | closed | R08 |

### Approval (`approval`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Approve | approve | pending | approved | R05, R07, R08, R09, R10, R11, R13, R15, R16, R18, R20 |
| Reject | reject | pending | rejected | R05, R07, R08, R09, R10, R11, R13, R15, R16, R18, R20 |
| Refer to higher authority | refer | pending | (conditional) | R07, R08, R09, R11, R15, R16 |

### Warranty claim (`warranty`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Check purchase evidence | check_evidence | submitted | diagnosis_review | R11 |
| Provide clarification | provide_clarification | clarification_requested | submitted | R01, R02, R05 |
| Record coverage decision | record_coverage_decision | diagnosis_review | decision_recorded | R11 |
| Send decision and appeal route | explain_decision | decision_recorded | communicated | R11 |
| Route dispute to appeals | route_dispute | communicated, decision_recorded | disputed | R11 |
| Close claim | close_claim | communicated | closed | R11 |

### Parts requisition (`requisition`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Validate requisition | validate_requisition | requested | validated | R12 |
| Confirm reservation | reserve_stock | validated | reserved | R12 |
| Transfer or procure stock | mark_unavailable | validated | awaiting_stock | R12 |
| Receive and verify stock | receive_stock | awaiting_stock | validated | R12 |
| Dispatch part | dispatch | reserved | dispatched | R12 |
| Record delivery milestone | record_delivery | dispatched | delivered | R12, R06 |
| Assign logistics recovery | resolve_exception | delivery_exception | dispatched | R12 |
| Record usage or return | record_usage | delivered | consumed | R06, R12 |
| Reconcile | reconcile_requisition | consumed, returned | reconciled | R12 |

### Return (`return`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Record return receipt | record_receipt | expected | received | R12 |
| Open restricted examination | open_restricted_examination | quarantined | inspected | R14, R12 |
| Close return | close_return | received, inspected | closed | R12 |

### Replacement order (`replacement`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Schedule delivery | schedule_delivery | created, exception | dispatch_scheduled | R12 |
| Record delivery | record_replacement_delivery | dispatch_scheduled | delivered | R12 |
| Complete milestones | record_collection | delivered | completed | R12 |
| Record exception | record_milestone_exception | created, dispatch_scheduled, delivered | exception | R12 |

### Settlement (`settlement`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Confirm recipient validation | validate_recipient | pending_validation | recipient_validated | R13 |
| Resolve discrepancy | resolve_discrepancy | discrepancy | pending_validation | R13 |
| Submit payment instruction | submit_instruction | recipient_validated, failed | pending_confirmation | R13 |
| Check operation status | check_status | pending_confirmation, outcome_unknown | (conditional) | R13 |
| Confirm reconciliation | reconcile | executed | reconciled | R13 |
| Request correction approval | request_correction | executed, reconciled | correction_requested | R13 |

### Safety incident (`incident`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Triage incident | triage | reported | containment | R14 |
| Record containment action | record_containment | containment | investigation | R14 |
| Preserve evidence | preserve_evidence | containment, investigation | (conditional) | R14 |
| Link affected units | link_units | containment, investigation | (conditional) | R14 |
| Submit investigation findings | submit_findings | investigation | rca_complete | R14 |
| Assign corrective action | plan_capa | rca_complete, capa_in_progress | capa_in_progress | R14 |
| Start effectiveness check | request_verification | capa_in_progress | effectiveness_check | R14 |
| Record effectiveness result | verify_effectiveness | effectiveness_check | closed | R14 |

### Corrective action (`capa`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Start action | start_capa | open, ineffective | in_progress | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Mark implemented | mark_implemented | in_progress | implemented | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Verify action | verify_capa | implemented | verified | R14 |

### Channel dispute (`channel_dispute`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Request additional evidence | request_clarification | open, facts_reconciled | clarification_requested | R15 |
| Record clarification received | clarification_received | clarification_requested | open | R15 |
| Record supported findings | record_findings | open | facts_reconciled | R15 |
| Record authorised decision | decide_dispute | facts_reconciled | recovery_in_progress | R15 |
| Assign recovery action | assign_recovery | recovery_in_progress, follow_up | (conditional) | R15 |
| Record action status | record_action_status | recovery_in_progress, follow_up | verification | R15 |
| Verify outcome and close | verify_outcome | verification | closed | R15 |

### Appeal (`appeal`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Assign independent reviewer | assign_reviewer | registered | under_review | R16 |
| Record review findings | record_findings | under_review | (conditional) | R16 |
| Request explanation | request_explanation | under_review | explanations_requested | R16 |
| Record explanation | explanation_received | explanations_requested | under_review | R16 |
| Issue reasoned decision | issue_decision | under_review | decided_upheld | R16 |
| Assign remedy execution | assign_remedy | remedy_in_progress | (conditional) | R16 |
| Verify remedy and close | verify_remedy | remedy_in_progress | closed | R16 |
| Record outcome and close | close_appeal | decided_upheld | closed | R16 |

### External correspondence (`correspondence`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Start response | start_response | registered | responding | R16 |
| Record response sent | record_response | responding | responded | R16 |

### Escalation (`escalation`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Assign recovery owner | assign_recovery_owner | open, revision | recovery_assigned | R09, R10 |
| Escalate to national lead | escalate_national | open, revision, recovery_assigned | referred_national | R09 |
| Coordinate approved plan | coordinate_plan | referred_national | authorised | R10 |
| Submit recovery update | submit_recovery_update | recovery_assigned, authorised | verification | R05, R07, R08, R09, R10, R12, R14 |
| Record recovery result | record_recovery_result | verification | closed | R09, R10 |

### Management action (`mgmt_action`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Start action | start_action | requested, revision_required | in_progress | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Submit evidence | submit_evidence | in_progress | evidence_submitted | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20 |
| Review performance action | review_progress | evidence_submitted | accepted | R17, R10 |

### Supplier dispute (`supplier_dispute`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Reconcile records | reconcile_lines | registered, reconciling | reconciling | R20 |
| Request team input | request_input | registered, reconciling | input_requested | R20 |
| Record input received | input_received | input_requested | reconciling | R20 |
| Record commercial decision | record_commercial_decision | reconciling | correction_approval | R20 |
| Record executed correction | execute_correction | correction_in_progress, follow_up | (conditional) | R20 |
| Verify approved settlement | verify_settlement | correction_in_progress, follow_up | settled | R20 |

### Confidential HR grievance (`hr_grievance`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Record triage | triage | received | investigation | R19 |
| Record referral outcome | referral_accepted | designated_referral | investigation | R19 |
| Save restricted findings | save_findings | investigation | (conditional) | R19 |
| Submit for authorised decision | submit_for_decision | investigation | decision_pending | R19 |
| Record authorised decision | record_decision | decision_pending | implementation | R19 |
| Record authorised follow up | record_implementation | implementation, escalated | follow_up | R19 |
| Verify follow-up and close | verify_follow_up | follow_up | closed | R19 |

### Audit engagement (`audit`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Save audit scope | save_scope | scoping | fieldwork | R21 |
| Record audit observation | record_observation | fieldwork | (conditional) | R21 |
| Complete fieldwork | complete_fieldwork | fieldwork | reporting | R21 |
| Record supported conclusion | complete_audit | reporting | complete | R21 |

### Audit finding (`audit_finding`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Record management response | accept_finding | open | remediation | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20, R18 |
| Submit remediation evidence | submit_remediation | remediation | submitted | R04, R05, R07, R08, R09, R10, R11, R12, R13, R14, R15, R16, R20, R18 |
| Record independent retest | record_retest | submitted | closed | R21 |

### Configuration change (`config_change`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Check request scope | check_scope | requested | configured | R18 |
| Correct configuration | edit_proposal | clarification, test_failed, configured | configured | R18 |
| Submit release evidence | run_tests | configured, test_failed | tested | R18 |
| Request release approval | request_release | tested | awaiting_release | R18 |
| Release approved version | release | awaiting_release | released | R18 |
| Roll back release | rollback | released | rolled_back | R18 |

### Policy / master version (`policy`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Submit for review | submit_for_review | draft | in_review | R18, R10, R11 |
| Publish version | publish | in_review | published | R18, R10, R11 |
| Return to maker | return_draft | in_review | draft | R18, R10, R11 |
| Supersede | supersede | published | superseded | R18, R10, R11 |

### Legal hold (`legal_hold`)

| Action | Key | From | To | Roles |
|---|---|---|---|---|
| Activate hold | activate_hold | requested | active | R18 |
| Release hold | release_hold | active | released | R18 |

