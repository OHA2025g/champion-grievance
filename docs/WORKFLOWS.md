# Workflow definitions (generated from backend/workflows.py)

## Case (`case`, prefix CE)

Initial state: `registered`

| State | Label | Next action | Terminal |
|---|---|---|---|
| registered | Registered | Route to accountable owner |  |
| safety_escalated | Safety escalation | Specialist containment and owner routing |  |
| awaiting_owner | Awaiting owner acceptance | Owner to accept ownership |  |
| in_progress | In progress | Execute case plan |  |
| evidence_requested | Information requested | Complainant to provide information |  |
| waiting | Approved waiting period | Resume when dependency clears |  |
| resolved | Resolved - pending verification | Verify outcome and close |  |
| reopened | Reopened | Owner to re-accept and replan |  |
| closed | Closed |  | yes |
| duplicate | Linked as duplicate |  | yes |

Create forms: customer_complaint (R01), support_ticket (R04), service_request (R05, R04), dealer_customer_case (R02), stock_claim (R02), bulk_grievance (R03)

## Contact (`contact`, prefix CT)

Initial state: `new`

| State | Label | Next action | Terminal |
|---|---|---|---|
| new | New | Open and screen |  |
| in_review | In review | Register or link |  |
| linked | Linked to case |  | yes |
| registered | Registered as case |  | yes |
| closed | Closed |  | yes |

Create forms: manual (R04)

## Task (`task`, prefix TSK)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Start task |  |
| in_progress | In progress | Complete task |  |
| blocked | Blocked | Remove blocker |  |
| done | Done |  | yes |
| cancelled | Cancelled |  | yes |

Create forms: 

## Service job (`job`, prefix JOB)

Initial state: `created`

| State | Label | Next action | Terminal |
|---|---|---|---|
| created | Awaiting allocation | Allocate technician |  |
| allocated | Technician allocated | Propose appointment |  |
| appointment_proposed | Appointment proposed | Customer to confirm |  |
| appointment_confirmed | Appointment confirmed | Confirm dispatch readiness |  |
| dispatched | Dispatched | Record arrival |  |
| on_site | On site | Diagnose product |  |
| diagnosed | Diagnosed | Repair, request parts or estimate |  |
| awaiting_approval | Awaiting approval | Approval decision |  |
| awaiting_parts | Awaiting parts | Parts delivery |  |
| authorised | Repair authorised | Perform approved repair |  |
| repaired | Repair recorded | Run functional and safety tests |  |
| tested | Tests passed | Customer handover |  |
| completed | Completion submitted | Centre review of evidence |  |
| returned | Returned for correction | Correct completion evidence |  |
| missed | Missed visit - recovery | Re-allocate and re-schedule |  |
| accepted | Job accepted |  | yes |
| cancelled | Cancelled |  | yes |

Create forms: 

## Unit (`unit`, prefix UNT)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Create unit job |  |
| job_created | Job in progress | Complete unit job |  |
| resolved | Resolved |  | yes |
| unresolved | Unresolved | Follow up assigned job |  |

Create forms: 

## Technical review (`tech_review`, prefix TR)

Initial state: `pending`

| State | Label | Next action | Terminal |
|---|---|---|---|
| pending | Review pending | Review diagnosis |  |
| further_inspection | Further inspection | Technician to update diagnosis |  |
| recommended | Recommendation recorded | Submit technical decision |  |
| referred | Referred to approver | Higher authority decision |  |
| approved | Technical plan approved |  | yes |
| closed | Closed |  | yes |

Create forms: 

## Approval (`approval`, prefix APR)

Initial state: `pending`

| State | Label | Next action | Terminal |
|---|---|---|---|
| pending | Pending decision | Authorised approver decision |  |
| approved | Approved |  | yes |
| rejected | Rejected |  | yes |
| cancelled | Cancelled |  | yes |

Create forms: 

## Warranty claim (`warranty`, prefix WCL)

Initial state: `submitted`

| State | Label | Next action | Terminal |
|---|---|---|---|
| submitted | Submitted | Check purchase evidence |  |
| clarification_requested | Clarification requested | Await clarification |  |
| diagnosis_review | Diagnosis review | Record coverage decision |  |
| exception_approval | Exception approval | Approver decision |  |
| decision_recorded | Decision recorded | Explain decision and appeal route |  |
| communicated | Decision communicated | Close or route dispute |  |
| disputed | Disputed - appeal routed |  | yes |
| closed | Closed |  | yes |

Create forms: claim (R11, R02)

## Parts requisition (`requisition`, prefix REQ)

Initial state: `requested`

| State | Label | Next action | Terminal |
|---|---|---|---|
| requested | Requested | Validate requisition |  |
| validated | Validated | Reserve stock |  |
| awaiting_stock | Awaiting transfer / procurement | Receive and verify stock |  |
| reserved | Reserved | Dispatch |  |
| dispatched | Dispatched | Confirm delivery |  |
| delivery_exception | Delivery exception | Resolve logistics exception |  |
| delivered | Delivered | Record usage or return |  |
| consumed | Used in repair | Reconcile | yes |
| returned | Returned | Reconcile | yes |
| rejected | Rejected |  | yes |
| reconciled | Reconciled |  | yes |

Create forms: 

## Return (`return`, prefix RET)

Initial state: `expected`

| State | Label | Next action | Terminal |
|---|---|---|---|
| expected | Expected | Record receipt |  |
| received | Received | Disposition |  |
| quarantined | Safety quarantine | Restricted examination |  |
| inspected | Examined | Disposition |  |
| closed | Closed |  | yes |

Create forms: return (R12)

## Replacement order (`replacement`, prefix RPL)

Initial state: `created`

| State | Label | Next action | Terminal |
|---|---|---|---|
| created | Created | Schedule delivery |  |
| dispatch_scheduled | Delivery scheduled | Record delivery |  |
| delivered | New unit delivered | Collect old unit |  |
| completed | Completed |  | yes |
| exception | Milestone exception | Review milestone |  |

Create forms: replacement (R12)

## Settlement (`settlement`, prefix STL)

Initial state: `pending_validation`

| State | Label | Next action | Terminal |
|---|---|---|---|
| pending_validation | Awaiting validation | Validate recipient and amount |  |
| discrepancy | Discrepancy | Resolve discrepancy |  |
| recipient_validated | Recipient validated | Submit payment instruction |  |
| pending_confirmation | Pending confirmation | Check operation status |  |
| outcome_unknown | Outcome unknown | Enquire provider status |  |
| failed | Execution failed | Investigate and retry |  |
| executed | Executed | Reconcile |  |
| correction_requested | Correction requested | Correction approval |  |
| reconciled | Reconciled |  | yes |
| cancelled | Cancelled |  | yes |

Create forms: credit_note (R13)

## Safety incident (`incident`, prefix INC)

Initial state: `reported`

| State | Label | Next action | Terminal |
|---|---|---|---|
| reported | Reported | Triage incident |  |
| containment | Containment | Record containment action |  |
| investigation | Investigation | Investigate root cause |  |
| rca_complete | Root cause recorded | Plan corrective action |  |
| capa_in_progress | CAPA in progress | Implement corrective actions |  |
| effectiveness_check | Effectiveness check | Verify effectiveness |  |
| closed | Closed |  | yes |

Create forms: incident (R14)

## Corrective action (`capa`, prefix CAPA)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Start action |  |
| in_progress | In progress | Implement |  |
| implemented | Implemented | Verify |  |
| ineffective | Ineffective - revise | Revise action |  |
| verified | Verified effective |  | yes |

Create forms: 

## Channel dispute (`channel_dispute`, prefix CHD)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Review evidence |  |
| clarification_requested | Clarification requested | Await customer / dealer response |  |
| facts_reconciled | Facts reconciled | Decide within authority |  |
| referred | Referred to higher authority | Await decision |  |
| recovery_in_progress | Recovery in progress | Monitor corrective action |  |
| follow_up | Follow-up required | Remove blockers |  |
| verification | Outcome verification | Verify stakeholder outcome |  |
| closed | Closed |  | yes |
| rejected | Claim not approved |  | yes |

Create forms: dispute (R15)

## Appeal (`appeal`, prefix APL)

Initial state: `registered`

| State | Label | Next action | Terminal |
|---|---|---|---|
| registered | Registered | Assign independent reviewer |  |
| under_review | Under independent review | Review evidence and decide |  |
| explanations_requested | Explanations requested | Await explanations |  |
| decided_upheld | Original decision upheld | Record outcome and review route |  |
| awaiting_reversal_approval | Reversal approval pending | Authorised approval |  |
| remedy_in_progress | Remedy in progress | Verify remedy completion |  |
| closed | Closed |  | yes |

Create forms: appeal (R16)

## External correspondence (`correspondence`, prefix COR)

Initial state: `registered`

| State | Label | Next action | Terminal |
|---|---|---|---|
| registered | Registered | Prepare response |  |
| responding | Response in preparation | Send response |  |
| responded | Responded |  | yes |

Create forms: correspondence (R16)

## Escalation (`escalation`, prefix ESC)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Assign recovery owner |  |
| recovery_assigned | Recovery assigned | Execute recovery plan |  |
| referred_national | Referred to national | National decision |  |
| authorised | Plan authorised | Execute approved plan |  |
| verification | Verification | Verify recovery |  |
| revision | Plan revision | Revise plan |  |
| closed | Closed |  | yes |

Create forms: escalation (R09, R10)

## Management action (`mgmt_action`, prefix MA)

Initial state: `requested`

| State | Label | Next action | Terminal |
|---|---|---|---|
| requested | Requested | Owner to start |  |
| in_progress | In progress | Submit evidence |  |
| evidence_submitted | Evidence submitted | Executive review |  |
| revision_required | Revised plan required | Submit revised plan |  |
| accepted | Accepted |  | yes |

Create forms: action (R17, R10)

## Supplier dispute (`supplier_dispute`, prefix SUP)

Initial state: `registered`

| State | Label | Next action | Terminal |
|---|---|---|---|
| registered | Registered | Reconcile records |  |
| reconciling | Reconciling | Record commercial decision |  |
| input_requested | Team input requested | Await input |  |
| correction_approval | Correction approval | Approver decision |  |
| correction_in_progress | Correction in progress | Verify settlement |  |
| follow_up | Follow-up | Chase outstanding action |  |
| closed_no_action | Closed - no discrepancy |  | yes |
| settled | Settled |  | yes |

Create forms: dispute (R20)

## Confidential HR grievance (`hr_grievance`, prefix HR)

Initial state: `received`

| State | Label | Next action | Terminal |
|---|---|---|---|
| received | Received - restricted | Triage urgency and conflicts |  |
| designated_referral | Designated referral | Specialist process |  |
| investigation | Confidential investigation | Investigate fairly |  |
| decision_pending | Decision pending | Obtain authorised decision |  |
| implementation | Implementation | Implement decision |  |
| escalated | Escalated to authorised owner | Follow up implementation |  |
| follow_up | Follow-up | Verify follow-up |  |
| closed | Closed with review route |  | yes |

Create forms: grievance (R19)

## Audit engagement (`audit`, prefix AUD)

Initial state: `scoping`

| State | Label | Next action | Terminal |
|---|---|---|---|
| scoping | Scoping | Save scope and sample |  |
| fieldwork | Fieldwork | Review evidence |  |
| reporting | Reporting | Conclude |  |
| complete | Complete |  | yes |

Create forms: engagement (R21)

## Audit finding (`audit_finding`, prefix AF)

Initial state: `open`

| State | Label | Next action | Terminal |
|---|---|---|---|
| open | Open | Owner management response |  |
| remediation | Remediation | Submit remediation evidence |  |
| submitted | Remediation submitted | Independent retest |  |
| closed | Closed - verified |  | yes |

Create forms: finding (R21)

## Configuration change (`config_change`, prefix CFG)

Initial state: `requested`

| State | Label | Next action | Terminal |
|---|---|---|---|
| requested | Requested | Check scope |  |
| clarification | Clarification | Clarify with requester |  |
| configured | Configured | Test representative paths |  |
| test_failed | Checks failed | Correct configuration |  |
| tested | Checks passed | Request release approval |  |
| awaiting_release | Awaiting release approval | Second administrator approval |  |
| released | Released | Monitor |  |
| rolled_back | Rolled back |  | yes |

Create forms: change (R18)

## Policy / master version (`policy`, prefix POL)

Initial state: `draft`

| State | Label | Next action | Terminal |
|---|---|---|---|
| draft | Draft | Submit for review |  |
| in_review | In review | Independent reviewer |  |
| published | Published |  |  |
| superseded | Superseded |  | yes |
| rejected | Returned |  | yes |

Create forms: warranty_term (R11), product_model (R18), service_standard (R10, R18), policy (R18)

## Legal hold (`legal_hold`, prefix LH)

Initial state: `requested`

| State | Label | Next action | Terminal |
|---|---|---|---|
| requested | Requested | Second administrator activation |  |
| active | Active hold | Review on date |  |
| released | Released |  | yes |

Create forms: hold (R18)

