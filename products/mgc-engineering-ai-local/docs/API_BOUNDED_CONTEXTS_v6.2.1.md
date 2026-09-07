# API Bounded Context Ownership — v6.2.1

Public paths remain under `/api/v1`; only source ownership/composition changed.

## engineering_core

- `/documents` — `documents`
- `/documents/{document_id}` — `document`
- `/documents/upload` — `upload`
- `/documents/{document_id}/reindex` — `reindex`
- `/documents/{document_id}/preview` — `preview`
- `/parts` — `parts`
- `/parts/{part_number}` — `part_360`
- `/parts/{part_number}/graph` — `graph`
- `/parts/{part_number}/compare` — `compare`
- `/parts/{part_number}/validate` — `validate`
- `/issues` — `issues`
- `/issues/{issue_id}` — `update_issue`
- `/scanner/run` — `scanner_run`
- `/design-reviews` — `create_design_review`
- `/design-reviews/async` — `create_design_review_async`
- `/design-reviews` — `list_design_reviews`
- `/design-reviews/{review_id}/approve` — `approve_design_review`
- `/evidence-packs` — `evidence_pack`
- `/evidence-packs/{pack_id}` — `get_evidence_pack`
- `/documents/{document_id}/history` — `document_history`
- `/documents/{document_id}/history/note` — `add_document_history_note`
- `/documents/{document_id}/engineering-analysis` — `engineering_analysis`
- `/documents/{document_id}/engineering-analyze` — `rerun_engineering_analysis`
- `/documents/{document_id}/geometry-links` — `geometry_links`
- `/documents/{document_id}/link-geometry` — `link_geometry`
- `/documents/{document_id}/visual-inspect` — `visual_inspect`
- `/projects` — `list_projects`
- `/projects` — `create_project`
- `/projects/{project_code}` — `update_project`
- `/projects/{project_code}/workspace` — `get_project_workspace`
- `/projects/{project_code}/areas` — `project_areas`
- `/projects/{project_code}/areas/{area_code}` — `update_project_area`
- `/documents/{document_id}/manufacturing-area` — `update_document_area`
- `/projects/{project_code}/milestones` — `create_project_milestone`
- `/projects/{project_code}/milestones/{milestone_id}` — `update_project_milestone`
- `/projects/{project_code}/requirements-matrix` — `get_requirements_matrix`
- `/projects/{project_code}/requirements` — `create_requirement`
- `/projects/{project_code}/requirements/{requirement_id}` — `update_requirement`
- `/projects/{project_code}/requirements/{requirement_id}/verifications` — `create_requirement_verification`
- `/projects/{project_code}/requirements/verifications/{verification_id}` — `update_requirement_verification`
- `/projects/{project_code}/vehicle-architecture` — `get_vehicle_architecture`
- `/projects/{project_code}/vehicle-architecture/impact` — `get_vehicle_architecture_impact`
- `/projects/{project_code}/vehicle-architecture/nodes` — `create_architecture_node`
- `/projects/{project_code}/vehicle-architecture/nodes/{node_id}` — `update_architecture_node`
- `/projects/{project_code}/vehicle-architecture/interfaces` — `create_interface`
- `/projects/{project_code}/vehicle-architecture/interfaces/{interface_id}` — `update_interface`
- `/projects/{project_code}/vehicle-architecture/interfaces/{interface_id}/verifications` — `create_interface_verification`
- `/projects/{project_code}/vehicle-architecture/verifications/{verification_id}` — `update_interface_verification`
- `/projects/{project_code}/program-control` — `get_program_control`
- `/projects/{project_code}/program-control/dependencies` — `create_program_dependency`
- `/projects/{project_code}/program-control/dependencies/{dependency_id}` — `update_program_dependency`
- `/projects/{project_code}/program-control/dependencies/{dependency_id}` — `delete_program_dependency`
- `/projects/{project_code}/program-control/slip-simulation` — `simulate_program_slip`

## configuration_change

- `/changes` — `list_changes`
- `/changes` — `create_engineering_change`
- `/changes/{change_id}` — `get_engineering_change`
- `/changes/{change_id}/impact` — `analyze_engineering_change`
- `/changes/{change_id}/submit` — `submit_engineering_change`
- `/changes/{change_id}/decision` — `decide_engineering_change`
- `/changes/{change_id}/implementation` — `start_engineering_change_implementation`
- `/changes/{change_id}/complete` — `complete_engineering_change`
- `/projects/{project_code}/configurations` — `get_configurations`
- `/projects/{project_code}/configurations/impact` — `get_configuration_impact`
- `/projects/{project_code}/configurations/variants` — `create_vehicle_variant`
- `/projects/{project_code}/configurations/variants/{variant_id}` — `update_vehicle_variant`
- `/projects/{project_code}/configurations/applicability` — `create_configuration_applicability`
- `/projects/{project_code}/configurations/applicability/{applicability_id}` — `update_configuration_applicability`
- `/projects/{project_code}/closed-loop` — `project_closed_loop`
- `/projects/{project_code}/closed-loop/decisions` — `create_engineering_decision`
- `/projects/{project_code}/closed-loop/decisions/{decision_id}` — `update_engineering_decision`
- `/projects/{project_code}/closed-loop/production-feedback` — `create_production_feedback`
- `/projects/{project_code}/closed-loop/effectiveness` — `create_change_effectiveness`
- `/projects/{project_code}/closed-loop/deviations` — `create_engineering_deviation`
- `/projects/{project_code}/closed-loop/deviations/{deviation_id}` — `update_engineering_deviation`
- `/projects/{project_code}/closed-loop/risks` — `create_engineering_risk`
- `/projects/{project_code}/closed-loop/risks/{risk_id}` — `update_engineering_risk`
- `/projects/{project_code}/closed-loop/validation-plan` — `closed_loop_validation_plan`
- `/projects/{project_code}/closed-loop/defects/{defect_id}/root-cause` — `closed_loop_root_cause`
- `/projects/{project_code}/configuration-assurance` — `get_configuration_assurance`
- `/projects/{project_code}/configuration-assurance/ask` — `ask_configuration_assurance`
- `/projects/{project_code}/configuration-assurance/release-package` — `get_configuration_release_package`
- `/projects/{project_code}/configuration-assurance/mbom` — `create_mbom_item`
- `/projects/{project_code}/configuration-assurance/effectivity` — `create_effectivity`
- `/projects/{project_code}/configuration-assurance/cutins` — `create_change_cutin`
- `/projects/{project_code}/configuration-assurance/as-built` — `create_as_built`
- `/projects/{project_code}/configuration-assurance/supersessions` — `create_part_supersession`
- `/projects/{project_code}/release-baselines` — `get_release_baselines`
- `/projects/{project_code}/release-baselines` — `freeze_release_baseline`
- `/projects/{project_code}/release-baselines/comparison` — `compare_release_baseline_api`
- `/projects/{project_code}/release-baselines/{baseline_id}` — `get_release_baseline`
- `/projects/{project_code}/bom-versions` — `get_bom_versions`
- `/projects/{project_code}/bom-compare` — `get_bom_compare`

## manufacturing_quality

- `/projects/{project_code}/quality` — `project_quality_workspace`
- `/projects/{project_code}/quality/apqp` — `create_apqp_deliverable`
- `/projects/{project_code}/quality/apqp/{item_id}` — `update_apqp_deliverable`
- `/projects/{project_code}/quality/characteristics` — `create_special_characteristic`
- `/projects/{project_code}/quality/characteristics/{item_id}` — `update_special_characteristic`
- `/projects/{project_code}/quality/pfmea` — `create_pfmea_item`
- `/projects/{project_code}/quality/pfmea/{item_id}` — `update_pfmea_item`
- `/projects/{project_code}/quality/control-plan` — `create_control_plan_item`
- `/projects/{project_code}/quality/control-plan/{item_id}` — `update_control_plan_item`
- `/projects/{project_code}/quality/ppap` — `create_ppap`
- `/projects/{project_code}/quality/ppap/{item_id}` — `update_ppap`
- `/projects/{project_code}/quality/8d` — `create_problem_8d`
- `/projects/{project_code}/quality/8d/{item_id}` — `update_problem_8d`
- `/projects/{project_code}/process-thread` — `get_process_thread`
- `/projects/{project_code}/process/lines` — `create_manufacturing_line`
- `/projects/{project_code}/process/lines/{line_id}/stations` — `create_process_station`
- `/projects/{project_code}/process/stations/{station_id}/operations` — `create_process_operation`
- `/projects/{project_code}/process/operations/{operation_id}/assets` — `create_process_asset`
- `/projects/{project_code}/process/operations/{operation_id}/parameters` — `create_process_parameter`
- `/projects/{project_code}/process/defects` — `create_process_defect`
- `/projects/{project_code}/process/defects/{defect_id}` — `update_process_defect`
- `/projects/{project_code}/launch-readiness` — `project_launch_readiness`
- `/projects/{project_code}/launch/checks` — `create_launch_check`
- `/projects/{project_code}/launch/checks/{item_id}` — `update_launch_check`
- `/projects/{project_code}/launch/trials` — `create_launch_trial`
- `/projects/{project_code}/launch/trials/{trial_id}` — `update_launch_trial`
- `/projects/{project_code}/build-launch-intelligence` — `get_build_launch_intelligence`
- `/projects/{project_code}/build-launch-intelligence/builds` — `create_vehicle_build`
- `/projects/{project_code}/build-launch-intelligence/builds/{build_id}/genealogy` — `add_build_genealogy`
- `/projects/{project_code}/build-launch-intelligence/builds/{build_id}/defects` — `link_build_defect`
- `/projects/{project_code}/build-launch-intelligence/safe-launch` — `create_safe_launch_control`
- `/projects/{project_code}/build-launch-intelligence/safe-launch/{control_id}` — `update_safe_launch_control`
- `/projects/{project_code}/series-intelligence` — `get_series_intelligence`
- `/projects/{project_code}/series-intelligence/ask` — `ask_series_intelligence`
- `/projects/{project_code}/series-intelligence/observations` — `create_series_observation`
- `/projects/{project_code}/series-intelligence/capability` — `create_process_capability`
- `/projects/{project_code}/series-intelligence/suspect-population` — `build_suspect_population`
- `/projects/{project_code}/series-intelligence/containments` — `create_series_containment`
- `/projects/{project_code}/series-intelligence/containments/{containment_id}` — `update_series_containment`

## supplier_field

- `/projects/{project_code}/supplier-localization` — `get_supplier_localization`
- `/projects/{project_code}/localization/items` — `create_localization_item`
- `/projects/{project_code}/localization/items/{item_id}` — `update_localization_item`
- `/projects/{project_code}/localization/incoming-quality` — `create_incoming_quality`
- `/projects/{project_code}/localization/incoming-quality/{record_id}` — `update_incoming_quality`
- `/projects/{project_code}/localization/items/{item_id}/evidence-pack` — `create_supplier_evidence_pack`
- `/projects/{project_code}/cost-economics` — `get_cost_economics`
- `/projects/{project_code}/cost/baselines` — `create_cost_baseline`
- `/projects/{project_code}/cost/baselines/{baseline_id}` — `update_cost_baseline`
- `/projects/{project_code}/cost/lines` — `create_cost_line`
- `/projects/{project_code}/cost/lines/{line_id}` — `update_cost_line`
- `/projects/{project_code}/cost/quotes` — `create_supplier_quotation`
- `/projects/{project_code}/cost/quotes/{quote_id}` — `update_supplier_quotation`
- `/projects/{project_code}/cost/baselines/{baseline_id}/evidence-pack` — `create_cost_pack`
- `/projects/{project_code}/series-intelligence/field-claims` — `create_field_quality_claim`
- `/projects/{project_code}/field-intelligence` — `get_field_reliability_intelligence`
- `/projects/{project_code}/field-intelligence/ask` — `ask_field_reliability_intelligence`
- `/projects/{project_code}/field-intelligence/vin/{vehicle_identifier}` — `get_field_vin_trace`
- `/projects/{project_code}/field-intelligence/exposures` — `create_field_reliability_exposure`
- `/projects/{project_code}/field-intelligence/dfmea` — `create_design_fmea_item`
- `/projects/{project_code}/field-intelligence/service-actions` — `create_field_service_action`
- `/projects/{project_code}/field-intelligence/service-actions/{action_id}` — `update_field_service_action`

## intelligence_search

- `/local-ai/health` — `local_ai_health`
- `/search` — `search_api`
- `/ask` — `ask_api`
- `/agent/run` — `agent_run`
- `/impact` — `impact`
- `/documents/{document_id}/similar` — `similar`
- `/graph/{part_number}/sync` — `graph_sync`
- `/graph/{part_number}/neighborhood` — `graph_neighborhood_api`
- `/projects/{project_code}/digital-thread` — `project_digital_thread`
- `/projects/{project_code}/change-intelligence` — `project_change_intelligence`
- `/projects/{project_code}/change-impact-simulate` — `project_change_impact_simulate`
- `/projects/{project_code}/digital-thread/ask` — `ask_digital_thread_api`
- `/projects/{project_code}/engineering-memory` — `project_engineering_memory`
- `/projects/{project_code}/engineering-memory/ask` — `ask_engineering_memory`
- `/projects/{project_code}/engineering-memory/lessons/promote` — `promote_engineering_lesson`
- `/projects/{project_code}/engineering-memory/lessons/{lesson_id}` — `update_engineering_lesson`
- `/projects/{project_code}/engineering-os` — `get_engineering_os`
- `/projects/{project_code}/engineering-os/ask` — `ask_engineering_os`
- `/projects/{project_code}/engineering-os/workflows` — `create_engineering_workflow`
- `/projects/{project_code}/engineering-os/workflows/{workflow_id}` — `update_engineering_workflow`

## platform_operations

- `/me` — `me`
- `/stats` — `stats`
- `/audit` — `audit`
- `/security/posture` — `enterprise_security_posture`
- `/security/audit/export` — `enterprise_audit_export`
- `/security/audit/retention` — `enterprise_audit_retention_preview`
- `/security/audit/retention` — `enterprise_audit_retention_apply`
- `/compute/tasks/{job_id}` — `compute_task_status`

