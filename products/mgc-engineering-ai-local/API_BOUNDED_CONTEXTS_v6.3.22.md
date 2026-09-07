# API Bounded Contexts — v6.3.22

> v6.3.22 adds no automotive bounded-context routes; Production Load Certification remains an Operations/release-engineering concern.

Total bounded-context routes: **247**. Legacy v6.2.0 method/path contracts remain additive-compatible.

v6.3.22 adds no bounded-context engineering routes; the new High Availability endpoint remains in administrative Operations, so automotive-domain ownership is unchanged.

## configuration_change
Routes: **53**

- `GET /changes` — `list_changes`
- `POST /changes` — `create_engineering_change`
- `GET /changes/{change_id}` — `get_engineering_change`
- `GET /changes/{change_id}/diff` — `get_engineering_change_diff`
- `POST /changes/{change_id}/impact` — `analyze_engineering_change`
- `POST /changes/{change_id}/submit` — `submit_engineering_change`
- `POST /changes/{change_id}/decision` — `decide_engineering_change`
- `POST /changes/{change_id}/implementation` — `start_engineering_change_implementation`
- `POST /changes/{change_id}/complete` — `complete_engineering_change`
- `GET /projects/{project_code}/configurations` — `get_configurations`
- `GET /projects/{project_code}/configurations/impact` — `get_configuration_impact`
- `POST /projects/{project_code}/configurations/variants` — `create_vehicle_variant`
- `PATCH /projects/{project_code}/configurations/variants/{variant_id}` — `update_vehicle_variant`
- `POST /projects/{project_code}/configurations/applicability` — `create_configuration_applicability`
- `PATCH /projects/{project_code}/configurations/applicability/{applicability_id}` — `update_configuration_applicability`
- `GET /projects/{project_code}/closed-loop` — `project_closed_loop`
- `POST /projects/{project_code}/closed-loop/decisions` — `create_engineering_decision`
- `PATCH /projects/{project_code}/closed-loop/decisions/{decision_id}` — `update_engineering_decision`
- `POST /projects/{project_code}/closed-loop/production-feedback` — `create_production_feedback`
- `POST /projects/{project_code}/closed-loop/effectiveness` — `create_change_effectiveness`
- `POST /projects/{project_code}/closed-loop/deviations` — `create_engineering_deviation`
- `PATCH /projects/{project_code}/closed-loop/deviations/{deviation_id}` — `update_engineering_deviation`
- `POST /projects/{project_code}/closed-loop/risks` — `create_engineering_risk`
- `PATCH /projects/{project_code}/closed-loop/risks/{risk_id}` — `update_engineering_risk`
- `POST /projects/{project_code}/closed-loop/validation-plan` — `closed_loop_validation_plan`
- `GET /projects/{project_code}/closed-loop/defects/{defect_id}/root-cause` — `closed_loop_root_cause`
- `GET /projects/{project_code}/configuration-assurance` — `get_configuration_assurance`
- `POST /projects/{project_code}/configuration-assurance/ask` — `ask_configuration_assurance`
- `GET /projects/{project_code}/configuration-assurance/release-package` — `get_configuration_release_package`
- `POST /projects/{project_code}/configuration-assurance/mbom` — `create_mbom_item`
- `POST /projects/{project_code}/configuration-assurance/effectivity` — `create_effectivity`
- `POST /projects/{project_code}/configuration-assurance/cutins` — `create_change_cutin`
- `POST /projects/{project_code}/configuration-assurance/as-built` — `create_as_built`
- `POST /projects/{project_code}/configuration-assurance/supersessions` — `create_part_supersession`
- `GET /projects/{project_code}/release-baselines` — `get_release_baselines`
- `POST /projects/{project_code}/release-baselines` — `freeze_release_baseline`
- `GET /projects/{project_code}/release-baselines/comparison` — `compare_release_baseline_api`
- `GET /projects/{project_code}/release-baselines/{baseline_id}` — `get_release_baseline`
- `GET /projects/{project_code}/bom-versions` — `get_bom_versions`
- `GET /projects/{project_code}/bom-compare` — `get_bom_compare`
- `POST /parts/{part_number}/bom/translate` — `translate_part_bom`
- `GET /projects/{project_code}/release-packages` — `list_release_packages`
- `POST /projects/{project_code}/release-packages` — `create_controlled_release_package`
- `GET /projects/{project_code}/release-packages/{package_id}` — `get_controlled_release_package`
- `GET /projects/{project_code}/release-packages/{package_id}/manifest` — `get_controlled_release_manifest`
- `POST /projects/{project_code}/release-packages/{package_id}/submit` — `submit_controlled_release_package`
- `POST /projects/{project_code}/release-packages/{package_id}/release` — `release_controlled_release_package`
- `GET /projects/{project_code}/release-packages/{package_id}/handover-jobs` — `list_release_handover_jobs`
- `POST /projects/{project_code}/release-packages/{package_id}/handover-jobs` — `create_release_handover_job`
- `GET /handover-jobs/{job_id}` — `get_release_handover_job`
- `POST /handover-jobs/{job_id}/authorize` — `authorize_release_handover_job`
- `POST /handover-jobs/{job_id}/execute` — `execute_release_handover_job`
- `POST /handover-jobs/{job_id}/reconcile` — `reconcile_release_handover_job`

## engineering_core
Routes: **54**

- `GET /documents` — `documents`
- `GET /documents/{document_id}` — `document`
- `GET /documents/{document_id}/content` — `document_content`
- `POST /documents/upload` — `upload`
- `POST /documents/{document_id}/reindex` — `reindex`
- `GET /documents/{document_id}/preview` — `preview`
- `GET /parts` — `parts`
- `GET /parts/{part_number}` — `part_360`
- `GET /parts/{part_number}/graph` — `graph`
- `GET /parts/{part_number}/compare` — `compare`
- `POST /parts/{part_number}/validate` — `validate`
- `GET /issues` — `issues`
- `PATCH /issues/{issue_id}` — `update_issue`
- `POST /scanner/run` — `scanner_run`
- `POST /design-reviews` — `create_design_review`
- `POST /design-reviews/async` — `create_design_review_async`
- `GET /design-reviews` — `list_design_reviews`
- `POST /design-reviews/{review_id}/approve` — `approve_design_review`
- `POST /evidence-packs` — `evidence_pack`
- `GET /evidence-packs/{pack_id}` — `get_evidence_pack`
- `GET /documents/{document_id}/history` — `document_history`
- `POST /documents/{document_id}/history/note` — `add_document_history_note`
- `GET /documents/{document_id}/engineering-analysis` — `engineering_analysis`
- `POST /documents/{document_id}/engineering-analyze` — `rerun_engineering_analysis`
- `GET /documents/{document_id}/geometry-links` — `geometry_links`
- `POST /documents/{document_id}/link-geometry` — `link_geometry`
- `POST /documents/{document_id}/visual-inspect` — `visual_inspect`
- `GET /projects` — `list_projects`
- `POST /projects` — `create_project`
- `PATCH /projects/{project_code}` — `update_project`
- `GET /projects/{project_code}/workspace` — `get_project_workspace`
- `GET /projects/{project_code}/areas` — `project_areas`
- `PATCH /projects/{project_code}/areas/{area_code}` — `update_project_area`
- `PATCH /documents/{document_id}/manufacturing-area` — `update_document_area`
- `POST /projects/{project_code}/milestones` — `create_project_milestone`
- `PATCH /projects/{project_code}/milestones/{milestone_id}` — `update_project_milestone`
- `GET /projects/{project_code}/requirements-matrix` — `get_requirements_matrix`
- `POST /projects/{project_code}/requirements` — `create_requirement`
- `PATCH /projects/{project_code}/requirements/{requirement_id}` — `update_requirement`
- `POST /projects/{project_code}/requirements/{requirement_id}/verifications` — `create_requirement_verification`
- `PATCH /projects/{project_code}/requirements/verifications/{verification_id}` — `update_requirement_verification`
- `GET /projects/{project_code}/vehicle-architecture` — `get_vehicle_architecture`
- `GET /projects/{project_code}/vehicle-architecture/impact` — `get_vehicle_architecture_impact`
- `POST /projects/{project_code}/vehicle-architecture/nodes` — `create_architecture_node`
- `PATCH /projects/{project_code}/vehicle-architecture/nodes/{node_id}` — `update_architecture_node`
- `POST /projects/{project_code}/vehicle-architecture/interfaces` — `create_interface`
- `PATCH /projects/{project_code}/vehicle-architecture/interfaces/{interface_id}` — `update_interface`
- `POST /projects/{project_code}/vehicle-architecture/interfaces/{interface_id}/verifications` — `create_interface_verification`
- `PATCH /projects/{project_code}/vehicle-architecture/verifications/{verification_id}` — `update_interface_verification`
- `GET /projects/{project_code}/program-control` — `get_program_control`
- `POST /projects/{project_code}/program-control/dependencies` — `create_program_dependency`
- `PATCH /projects/{project_code}/program-control/dependencies/{dependency_id}` — `update_program_dependency`
- `DELETE /projects/{project_code}/program-control/dependencies/{dependency_id}` — `delete_program_dependency`
- `POST /projects/{project_code}/program-control/slip-simulation` — `simulate_program_slip`

## intelligence_search
Routes: **20**

- `GET /local-ai/health` — `local_ai_health`
- `POST /search` — `search_api`
- `POST /ask` — `ask_api`
- `POST /agent/run` — `agent_run`
- `POST /impact` — `impact`
- `GET /documents/{document_id}/similar` — `similar`
- `POST /graph/{part_number}/sync` — `graph_sync`
- `GET /graph/{part_number}/neighborhood` — `graph_neighborhood_api`
- `GET /projects/{project_code}/digital-thread` — `project_digital_thread`
- `GET /projects/{project_code}/change-intelligence` — `project_change_intelligence`
- `POST /projects/{project_code}/change-impact-simulate` — `project_change_impact_simulate`
- `POST /projects/{project_code}/digital-thread/ask` — `ask_digital_thread_api`
- `GET /projects/{project_code}/engineering-memory` — `project_engineering_memory`
- `POST /projects/{project_code}/engineering-memory/ask` — `ask_engineering_memory`
- `POST /projects/{project_code}/engineering-memory/lessons/promote` — `promote_engineering_lesson`
- `PATCH /projects/{project_code}/engineering-memory/lessons/{lesson_id}` — `update_engineering_lesson`
- `GET /projects/{project_code}/engineering-os` — `get_engineering_os`
- `POST /projects/{project_code}/engineering-os/ask` — `ask_engineering_os`
- `POST /projects/{project_code}/engineering-os/workflows` — `create_engineering_workflow`
- `PATCH /projects/{project_code}/engineering-os/workflows/{workflow_id}` — `update_engineering_workflow`

## manufacturing_quality
Routes: **53**

- `GET /projects/{project_code}/quality` — `project_quality_workspace`
- `POST /projects/{project_code}/quality/apqp` — `create_apqp_deliverable`
- `PATCH /projects/{project_code}/quality/apqp/{item_id}` — `update_apqp_deliverable`
- `POST /projects/{project_code}/quality/characteristics` — `create_special_characteristic`
- `PATCH /projects/{project_code}/quality/characteristics/{item_id}` — `update_special_characteristic`
- `POST /projects/{project_code}/quality/pfmea` — `create_pfmea_item`
- `PATCH /projects/{project_code}/quality/pfmea/{item_id}` — `update_pfmea_item`
- `POST /projects/{project_code}/quality/control-plan` — `create_control_plan_item`
- `PATCH /projects/{project_code}/quality/control-plan/{item_id}` — `update_control_plan_item`
- `POST /projects/{project_code}/quality/ppap` — `create_ppap`
- `PATCH /projects/{project_code}/quality/ppap/{item_id}` — `update_ppap`
- `POST /projects/{project_code}/quality/8d` — `create_problem_8d`
- `PATCH /projects/{project_code}/quality/8d/{item_id}` — `update_problem_8d`
- `GET /projects/{project_code}/process-thread` — `get_process_thread`
- `POST /projects/{project_code}/process/lines` — `create_manufacturing_line`
- `POST /projects/{project_code}/process/lines/{line_id}/stations` — `create_process_station`
- `POST /projects/{project_code}/process/stations/{station_id}/operations` — `create_process_operation`
- `POST /projects/{project_code}/process/operations/{operation_id}/assets` — `create_process_asset`
- `POST /projects/{project_code}/process/operations/{operation_id}/parameters` — `create_process_parameter`
- `POST /projects/{project_code}/process/defects` — `create_process_defect`
- `PATCH /projects/{project_code}/process/defects/{defect_id}` — `update_process_defect`
- `GET /projects/{project_code}/launch-readiness` — `project_launch_readiness`
- `POST /projects/{project_code}/launch/checks` — `create_launch_check`
- `PATCH /projects/{project_code}/launch/checks/{item_id}` — `update_launch_check`
- `POST /projects/{project_code}/launch/trials` — `create_launch_trial`
- `PATCH /projects/{project_code}/launch/trials/{trial_id}` — `update_launch_trial`
- `GET /projects/{project_code}/build-launch-intelligence` — `get_build_launch_intelligence`
- `POST /projects/{project_code}/build-launch-intelligence/builds` — `create_vehicle_build`
- `POST /projects/{project_code}/build-launch-intelligence/builds/{build_id}/genealogy` — `add_build_genealogy`
- `POST /projects/{project_code}/build-launch-intelligence/builds/{build_id}/defects` — `link_build_defect`
- `POST /projects/{project_code}/build-launch-intelligence/safe-launch` — `create_safe_launch_control`
- `PATCH /projects/{project_code}/build-launch-intelligence/safe-launch/{control_id}` — `update_safe_launch_control`
- `GET /projects/{project_code}/series-intelligence` — `get_series_intelligence`
- `POST /projects/{project_code}/series-intelligence/ask` — `ask_series_intelligence`
- `POST /projects/{project_code}/series-intelligence/observations` — `create_series_observation`
- `POST /projects/{project_code}/series-intelligence/capability` — `create_process_capability`
- `POST /projects/{project_code}/series-intelligence/suspect-population` — `build_suspect_population`
- `POST /projects/{project_code}/series-intelligence/containments` — `create_series_containment`
- `PATCH /projects/{project_code}/series-intelligence/containments/{containment_id}` — `update_series_containment`
- `PATCH /projects/{project_code}/process/stations/{station_id}` — `update_process_station`
- `GET /projects/{project_code}/work-instructions` — `get_work_instruction_workspace`
- `POST /projects/{project_code}/work-instructions` — `create_work_instruction`
- `POST /projects/{project_code}/work-instructions/import-document` — `import_work_instruction`
- `PATCH /projects/{project_code}/work-instructions/{instruction_id}` — `update_work_instruction`
- `POST /projects/{project_code}/work-instructions/{instruction_id}/revisions` — `create_work_instruction_revision`
- `GET /projects/{project_code}/work-instructions/{instruction_id}/diff` — `diff_work_instruction_revisions`
- `POST /projects/{project_code}/work-instructions/{instruction_id}/translate` — `translate_work_instruction_to_russian`
- `POST /projects/{project_code}/work-instructions/{instruction_id}/translation-review` — `review_work_instruction_translation`
- `POST /projects/{project_code}/work-instructions/ask` — `ask_work_instruction_knowledge`
- `POST /projects/{project_code}/layouts` — `create_manufacturing_layout`
- `POST /projects/{project_code}/layouts/{layout_id}/revisions` — `create_layout_revision`
- `GET /projects/{project_code}/layouts/{layout_id}/diff` — `diff_layout_revisions`
- `POST /projects/{project_code}/layouts/{layout_id}/stations` — `place_station_on_layout`

## platform_operations
Routes: **45**

- `GET /me` — `me`
- `GET /stats` — `stats`
- `GET /audit` — `audit`
- `GET /security/posture` — `enterprise_security_posture`
- `GET /security/audit/export` — `enterprise_audit_export`
- `GET /security/audit/retention` — `enterprise_audit_retention_preview`
- `POST /security/audit/retention` — `enterprise_audit_retention_apply`
- `GET /compute/tasks/{job_id}` — `compute_task_status`
- `GET /compute/tasks` — `list_compute_tasks`
- `POST /compute/tasks/{job_id}/cancel` — `cancel_compute_task`
- `GET /operations/workload` — `operations_workload`
- `POST /operations/workload/{job_id}/retry` — `operations_retry_job`
- `POST /operations/workload/{job_id}/recover` — `operations_recover_orphaned_job`
- `GET /operations/workload/recovery-events` — `operations_workload_recovery_events`
- `GET /approval-policies` — `approval_policies`
- `POST /approval-policies` — `create_approval_policy`
- `POST /projects/{project_code}/approvals/{entity_type}/{entity_id}/submit` — `submit_engineering_approval`
- `GET /approvals/{case_id}` — `get_engineering_approval`
- `POST /approvals/{case_id}/decision` — `decide_engineering_approval`
- `GET /governance/summary` — `approval_governance_summary`
- `GET /identity/policies` — `identity_policies`
- `POST /identity/policies` — `create_identity_policy`
- `GET /identity/delegations` — `identity_delegations`
- `POST /identity/delegations` — `create_identity_delegation`
- `POST /identity/delegations/{delegation_id}/revoke` — `revoke_identity_delegation`
- `GET /handover/targets` — `handover_targets`
- `POST /handover/targets` — `create_controlled_handover_target`
- `GET /handover/summary` — `controlled_handover_summary`
- `GET /lifecycle/summary` — `data_lifecycle_summary`
- `GET /lifecycle/storage-usage` — `data_lifecycle_storage_usage`
- `GET /lifecycle/retention-policies` — `retention_policies`
- `POST /lifecycle/retention-policies` — `create_engineering_retention_policy`
- `GET /lifecycle/legal-holds` — `legal_holds`
- `POST /lifecycle/legal-holds` — `create_legal_hold`
- `POST /lifecycle/legal-holds/{hold_id}/release` — `release_engineering_legal_hold`
- `POST /lifecycle/{entity_type}/{entity_id}/archive` — `archive_engineering_entity`
- `GET /lifecycle/{entity_type}/{entity_id}/lineage` — `engineering_evidence_lineage`
- `GET /lifecycle/purge-requests` — `purge_requests`
- `POST /lifecycle/purge-requests` — `create_engineering_purge_request`
- `POST /lifecycle/purge-requests/{request_id}/authorize` — `authorize_engineering_purge`
- `POST /lifecycle/purge-requests/{request_id}/execute` — `execute_engineering_purge`
- `GET /operations/performance` — `database_performance`
- `GET /audit/cursor` — `audit_cursor`
- `GET /operations/read-models` — `engineering_read_models`
- `POST /operations/read-models/rebuild` — `rebuild_engineering_read_models`

## supplier_field
Routes: **22**

- `GET /projects/{project_code}/supplier-localization` — `get_supplier_localization`
- `POST /projects/{project_code}/localization/items` — `create_localization_item`
- `PATCH /projects/{project_code}/localization/items/{item_id}` — `update_localization_item`
- `POST /projects/{project_code}/localization/incoming-quality` — `create_incoming_quality`
- `PATCH /projects/{project_code}/localization/incoming-quality/{record_id}` — `update_incoming_quality`
- `POST /projects/{project_code}/localization/items/{item_id}/evidence-pack` — `create_supplier_evidence_pack`
- `GET /projects/{project_code}/cost-economics` — `get_cost_economics`
- `POST /projects/{project_code}/cost/baselines` — `create_cost_baseline`
- `PATCH /projects/{project_code}/cost/baselines/{baseline_id}` — `update_cost_baseline`
- `POST /projects/{project_code}/cost/lines` — `create_cost_line`
- `PATCH /projects/{project_code}/cost/lines/{line_id}` — `update_cost_line`
- `POST /projects/{project_code}/cost/quotes` — `create_supplier_quotation`
- `PATCH /projects/{project_code}/cost/quotes/{quote_id}` — `update_supplier_quotation`
- `POST /projects/{project_code}/cost/baselines/{baseline_id}/evidence-pack` — `create_cost_pack`
- `POST /projects/{project_code}/series-intelligence/field-claims` — `create_field_quality_claim`
- `GET /projects/{project_code}/field-intelligence` — `get_field_reliability_intelligence`
- `POST /projects/{project_code}/field-intelligence/ask` — `ask_field_reliability_intelligence`
- `GET /projects/{project_code}/field-intelligence/vin/{vehicle_identifier}` — `get_field_vin_trace`
- `POST /projects/{project_code}/field-intelligence/exposures` — `create_field_reliability_exposure`
- `POST /projects/{project_code}/field-intelligence/dfmea` — `create_design_fmea_item`
- `POST /projects/{project_code}/field-intelligence/service-actions` — `create_field_service_action`
- `PATCH /projects/{project_code}/field-intelligence/service-actions/{action_id}` — `update_field_service_action`

