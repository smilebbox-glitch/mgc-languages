.PHONY: help start install build build-compose build-no-cache up up-cpu up-gpu up-cpu-vision rebuild cpu gpu cpu-vision cpu-check pilot local connected connected-build connected-up down logs ps health backup restore dr-preflight dr-consistency-preflight pitr-status performance-preflight performance-ci load-test sbom secret-scan dependency-lock-preflight cve-scan enterprise-security-preflight supply-chain-preflight test verify security-preflight dockle prepare-models prepare-cpu prepare-cpu-model prepare-bundle bundle bundle-cpu bundle-gpu import-bundle acceptance pilot-acceptance-preflight ux-acceptance-preflight observability-preflight incident-evidence-preflight game-day-preflight corporate-deployment-preflight architecture-simplification-preflight profile-core profile-ai profile-advanced reproducible-build prepare-python-locks prepare-frontend-lock prepare-os-package-bundle resolve-image-digests build-attestation verify-build-attestation

help:
	@echo "MGC Engineering AI Local v6.3.34 — Pilot Readiness & UX Simplification"
	@echo ""
	@echo "Build / start:"
	@echo "  docker compose build   Standard Compose build; installs all app dependencies"
	@echo "  make build-compose     Same command with preflight checks"
	@echo "  ./mgcctl <command>     Unified operations CLI (status/verify/deploy/rollback/backup/restore/certify/provenance/drill/diagnose); deploy is host-assurance gated"
	@echo "  make operations-consolidation-preflight  Validate mgcctl delegation/safety contracts"
	@echo "  make integration-certification-preflight Validate PLM/PDM/ERP/MES/QMS adapter contracts"
	@echo "  make integration-runtime-assurance-preflight Validate bounded cache staleness and recovery-sync guards"
	@echo "  make target-host-assurance-preflight Validate target-host probe/certification/deploy gate"
	@echo "  make integration-certify CONTRACT=ops/integrations/contracts/plm.example.json  Certify one adapter contract"
	@echo "  make build             Hardened air-gap application build"
	@echo "  make start             Build + start selected CPU/GPU production stack"
	@echo "  make rebuild           Rebuild + recreate running production stack"
	@echo ""
	@echo "Runtime:"
	@echo "  make up                Auto-select GPU when available, otherwise CPU"
	@echo "  make cpu               Force CPU mode"
	@echo "  make cpu-check         Show conservative CPU/RAM tuning values"
	@echo "  make cpu-vision        Force CPU + optional multimodal vision server"
	@echo "  make gpu               Force NVIDIA GPU/vLLM mode"
	@echo "  make down              Stop selected runtime"
	@echo "  make health            Show operational readiness from private API"
	@echo "  make backup            Create consistency-verified authoritative backup"
	@echo "  make pitr-status       Show sanitized PostgreSQL WAL/PITR readiness"
	@echo "  make performance-ci    Run deterministic CI-scale performance benchmark"
	@echo "  make performance-preflight  Show capacity envelope + critical-index gate"
	@echo "  make pilot-acceptance-preflight  Validate controlled-pilot/UAT harness (not a real GO decision)"
	@echo "  make ux-acceptance-preflight     Validate role UX / feedback closure boundaries"
	@echo "  make observability-preflight     Validate SLO/support/privacy boundaries"
	@echo "  make incident-evidence-preflight Validate automated incident-evidence boundaries"
	@echo "  make resilience-drill-preflight Validate bounded resilience-drill contracts"
	@echo "  make resilience-certification-preflight Validate v6.3.34 RTO baseline/regression contracts"
	@echo "  make pilot-readiness-preflight Validate v6.3.34 Action Center/navigation/productization contract"
	@echo "  make game-day-preflight          Validate v6.0.9 operations-acceptance/game-day framework"
	@echo "  make corporate-deployment-preflight Validate corporate pilot launch kit"
	@echo "  make architecture-simplification-preflight Validate Core/AI/Advanced architecture boundaries"
	@echo "  make profile-core / profile-ai / profile-advanced  Start simplified runtime profiles"
	@echo "  make load-test         Read-only live HTTP probe (API must be running)"
	@echo "  make ha-preflight      Validate application-tier HA/failover source contracts"
	@echo "  make ha-up             Start optional HA Compose overlay"
	@echo "  MGC_HA_DRILL_CONFIRM=YES make ha-drill  Run disruptive target-host failover drill"
	@echo "  make authoritative-ha-preflight  Validate PostgreSQL/evidence write-fencing contracts"
	@echo "  make multihost-preflight Validate multi-host placement/external-LB safety contracts"
	@echo "  make topology-certify PROFILE=30 INVENTORY=ops/multihost/topology.inventory.example.json"
	@echo "  MGC_MULTHOST_DRILL_CONFIRM=YES make multihost-drill  Run target-host external-LB failover drill"
	@echo "  make production-certification-preflight  Validate v6.3.34 SLO/capacity contracts"
	@echo "  make production-load-certification-preflight  Validate v6.3.34 mixed-load/signature contracts"
	@echo "  make production-load-certify  Run live BOM/WI/Object360/RAG load certification (explicit env confirmation required)"
	@echo "  make production-certify PROFILE=30 TOPOLOGY=... EVIDENCE=... LOAD_EVIDENCE=...  Evaluate signed target-host acceptance"
	@echo "  make production-deployment-guard REPORT=... CONFIRM=APPROVED_CHANGE_WINDOW  Fail-closed rollout guard"
	@echo "  make release-acceptance-preflight  Validate v6.3.34 baseline/regression/evidence-chain contracts"
	@echo "  MGC_RELEASE_ACCEPTANCE_CONFIRM=YES make release-acceptance  Run controlled load + signed release acceptance pipeline"
	@echo "  make acceptance-baseline-promote  Promote a signed technical acceptance after explicit human approval"
	@echo "  make acceptance-chain-verify  Verify ordered signed acceptance evidence chain"
	@echo "  make release-provenance-preflight  Validate v6.3.34 evidence-registry/key-revocation contracts"
	@echo "  make release-provenance-verify REGISTRY=...  Replay hash/object/signature trust chain"
	@echo "  make release-provenance-audit REGISTRY=... OUTPUT=...  Build cross-release audit report"
	@echo "  make release-provenance-governance-preflight  Validate v6.3.34 anchor/WORM/retention contracts"
	@echo "  make release-provenance-checkpoint REGISTRY=...  Create immutable registry checkpoint"
	@echo "  make release-provenance-auditor-export REGISTRY=... OUTPUT=...  Build offline auditor verification bundle"
	@echo "  make authoritative-ha-check      Runtime check: writable primary + active evidence generation"
	@echo "  make authoritative-recovery-point OUTPUT=/path/rp.json  Create consistency-bound HA recovery point"
	@echo "  make restore BACKUP=/path  Restore backup (requires MGC_RESTORE_CONFIRM=RESTORE)"
	@echo ""
	@echo "Offline preparation:"
	@echo "  make prepare-cpu       Stage CPU GGUF + embeddings/reranker/Docling"
	@echo "  make prepare-models    Stage GPU/VLM + embeddings/reranker/Docling models"
	@echo "  make bundle-cpu        Build an air-gap bundle for CPU runtime"
	@echo "  make bundle-gpu        Build an air-gap bundle for NVIDIA/vLLM runtime"
	@echo ""
	@echo "Security:"
	@echo "  make verify"
	@echo "  make security-preflight"
	@echo "  make dockle"
	@echo "  make supply-chain-preflight  SBOM + secret + enterprise security checks"

start install:
	./scripts/one_click.sh

build-compose:
	python scripts/build_preflight.py
	python scripts/dr_preflight.py
	docker compose build

build:
	./scripts/docker_build.sh

build-no-cache:
	./scripts/docker_build.sh --no-cache

rebuild:
	./scripts/docker_build.sh
	./scripts/stack.sh up -d --force-recreate

up:
	./scripts/stack.sh up -d

up-cpu cpu:
	MGC_RUNTIME=cpu ./scripts/stack.sh up -d

up-gpu gpu:
	MGC_RUNTIME=gpu ./scripts/stack.sh up -d

up-cpu-vision cpu-vision:
	MGC_RUNTIME=cpu MGC_CPU_VISION=true ./scripts/stack.sh up -d

cpu-check:
	python scripts/cpu_capacity.py

pilot local:
	DEPLOYMENT_PROFILE=ai docker compose -f docker-compose.airgap.yml -f docker-compose.cpu.yml -f docker-compose.pilot.yml --profile ai up -d

connected-build:
	docker compose -f docker-compose.connected.yml build api worker frontend gateway

connected connected-up:
	docker compose -f docker-compose.connected.yml -f docker-compose.pilot.yml up -d --build

down:
	./scripts/stack.sh down

logs:
	./scripts/stack.sh logs -f api worker model-server

health:
	./scripts/stack.sh exec -T api python -c "import json,urllib.request; print(json.dumps(json.loads(urllib.request.urlopen('http://127.0.0.1:8080/api/v1/health/ready',timeout=10).read()),indent=2))"

backup:
	./scripts/backup_core.sh

restore:
	@test -n "$(BACKUP)" || (echo "Set BACKUP=/path/to/backup" >&2; exit 2)
	./scripts/restore_core.sh "$(BACKUP)"

dr-preflight:
	python scripts/dr_preflight.py

dr-consistency-preflight:
	python scripts/dr_consistency_preflight.py

pitr-status:
	./scripts/stack.sh exec -T api python -c "import json; from app.db.session import SessionLocal; from app.services.dr_consistency import postgres_pitr_status; db=SessionLocal(); out=postgres_pitr_status(db); db.close(); print(json.dumps(out,indent=2)); raise SystemExit(0 if out.get('pitr_ready') else 3)"

performance-preflight:
	python scripts/performance_preflight.py --profile ci

performance-ci:
	python scripts/synthetic_scale_benchmark.py --profile ci --output performance-ci.json

pilot-acceptance-preflight:
	python scripts/pilot_acceptance_preflight.py
	python scripts/ux_acceptance_preflight.py

ux-acceptance-preflight:
	python scripts/ux_acceptance_preflight.py

observability-preflight:
	python scripts/observability_preflight.py

incident-evidence-preflight:
	python scripts/incident_evidence_preflight.py

game-day-preflight:
	python scripts/game_day_preflight.py

corporate-deployment-preflight:
	python scripts/corporate_deployment_preflight.py

load-test:
	python scripts/http_load_test.py --profile ci --path /api/v1/health/live

ps:
	./scripts/stack.sh ps

test:
	cd backend && PYTHONPATH=. pytest -q

verify:
	cd backend && python -m compileall -q app tests && PYTHONPATH=. pytest -q
	python -c "import yaml; [yaml.safe_load(open(p)) for p in ['docker-compose.yml','docker-compose.airgap.yml','docker-compose.gpu.yml','docker-compose.cpu.yml','docker-compose.cpu-vision.yml','docker-compose.build.yml','docker-compose.connected.yml','docker-compose.pilot.yml','docker-compose.sso.yml','docker-compose.webhooks.yml','docker-compose.debug.yml','docker-compose.integration-demo.yml','docker-compose.enterprise-security.yml','docker-compose.pitr.yml','docker-compose.bluegreen.yml','docker-compose.ha.yml','docker-compose.authoritative-ha.yml','docker-compose.multihost.yml']]; print('compose yaml: OK')"
	bash -n scripts/docker_build.sh scripts/one_click.sh scripts/runtime_lib.sh scripts/stack.sh scripts/docker_rebuild_run.sh scripts/prepare_airgap_bundle.sh scripts/airgap_import.sh scripts/airgap_acceptance.sh scripts/dockle_scan.sh scripts/backup_core.sh scripts/restore_core.sh scripts/vulnerability_scan.sh scripts/multihost_failover_drill.sh
	python scripts/docker_security_preflight.py
	python scripts/compose_security_preflight.py
	python scripts/api_access_preflight.py
	python scripts/cpu_capacity.py --json >/dev/null
	python scripts/build_preflight.py
	python scripts/dr_preflight.py
	python scripts/performance_preflight.py --profile ci --json >/dev/null
	python scripts/generate_sbom.py
	python scripts/secret_scan.py
	python scripts/enterprise_security_preflight.py
	python scripts/dependency_lock_preflight.py
	python scripts/supply_chain_preflight.py
	python scripts/supply_chain_v6_3_12_preflight.py
	python scripts/pilot_acceptance_preflight.py
	python scripts/ux_acceptance_preflight.py
	python scripts/observability_preflight.py
	python scripts/incident_evidence_preflight.py
	python scripts/game_day_preflight.py
	python scripts/corporate_deployment_preflight.py
	python scripts/architecture_simplification_preflight.py
	python scripts/operations_consolidation_preflight.py
	python scripts/integration_certification_preflight.py
	python -m py_compile scripts/mgcctl.py scripts/operations_consolidation_preflight.py
	bash -n mgcctl

security-preflight:
	python scripts/docker_security_preflight.py
	python scripts/compose_security_preflight.py
	python scripts/api_access_preflight.py
	python scripts/dr_preflight.py

sbom:
	python scripts/generate_sbom.py

secret-scan:
	python scripts/secret_scan.py

dependency-lock-preflight:
	python scripts/dependency_lock_preflight.py

cve-scan:
	./scripts/vulnerability_scan.sh

enterprise-security-preflight:
	python scripts/enterprise_security_preflight.py

supply-chain-preflight: sbom secret-scan dependency-lock-preflight enterprise-security-preflight
	python scripts/supply_chain_preflight.py
	python scripts/supply_chain_v6_3_12_preflight.py
	./scripts/vulnerability_scan.sh

reproducible-build:
	./scripts/reproducible_build.sh

prepare-python-locks:
	python scripts/prepare_python_lock.py --profile core
	python scripts/prepare_python_lock.py --profile ai
	python scripts/prepare_python_lock.py --profile advanced

prepare-frontend-lock:
	./scripts/prepare_frontend_lock.sh

prepare-os-package-bundle:
	./scripts/prepare_os_package_bundle.sh

resolve-image-digests:
	python scripts/resolve_container_digests.py


dockle:
	./scripts/dockle_scan.sh

prepare-models:
	python scripts/prepare_models.py

prepare-cpu:
	python scripts/prepare_models.py --skip-generative
	python scripts/prepare_cpu_model.py

prepare-cpu-model:
	python scripts/prepare_cpu_model.py

prepare-bundle bundle:
	./scripts/prepare_airgap_bundle.sh

bundle-cpu:
	MGC_RUNTIME=cpu ./scripts/prepare_airgap_bundle.sh

bundle-gpu:
	MGC_RUNTIME=gpu ./scripts/prepare_airgap_bundle.sh

import-bundle:
	./scripts/airgap_import.sh

acceptance:
	./scripts/airgap_acceptance.sh


profile-core:
	@./scripts/profile_up.sh core

profile-ai:
	@./scripts/profile_up.sh ai

profile-advanced:
	@./scripts/profile_up.sh advanced

architecture-simplification-preflight:
	python scripts/architecture_simplification_preflight.py

build-attestation:
	python scripts/generate_build_attestation.py

verify-build-attestation:
	python scripts/verify_build_attestation.py

.PHONY: rolling-upgrade-preflight rolling-upgrade
rolling-upgrade-preflight:
	python scripts/rolling_upgrade_preflight.py

rolling-upgrade:
	./scripts/rolling_upgrade.sh

.PHONY: blue-green-preflight blue-green-cutover blue-green-rollback blue-green-finalize ha-preflight ha-up ha-drill
blue-green-preflight:
	python scripts/blue_green_cutover_preflight.py

blue-green-cutover:
	./scripts/blue_green_cutover.sh

blue-green-rollback:
	./scripts/blue_green_rollback.sh

blue-green-finalize:
	./scripts/blue_green_finalize.sh

ha-preflight:
	python scripts/ha_failover_preflight.py

ha-up:
	docker compose -f docker-compose.yml -f docker-compose.ha.yml up -d

ha-drill:
	./scripts/ha_failover_drill.sh

.PHONY: authoritative-ha-preflight authoritative-ha-check authoritative-recovery-point authoritative-ha-up
authoritative-ha-preflight:
	python scripts/db_evidence_ha_preflight.py

authoritative-ha-check:
	PYTHONPATH=backend python scripts/authoritative_ha_runtime_check.py

authoritative-recovery-point:
	@test -n "$(OUTPUT)" || (echo "Set OUTPUT=/path/to/recovery-point.json" >&2; exit 2)
	PYTHONPATH=backend python scripts/authoritative_recovery_point.py --output "$(OUTPUT)"

authoritative-ha-up:
	docker compose -f docker-compose.yml -f docker-compose.ha.yml -f docker-compose.authoritative-ha.yml up -d

.PHONY: multihost-preflight topology-certify multihost-drill
multihost-preflight:
	python scripts/multihost_topology_preflight.py

topology-certify:
	@test -n "$(PROFILE)" || (echo "Set PROFILE=15,30,100" >&2; exit 2)
	@test -n "$(INVENTORY)" || (echo "Set INVENTORY=/path/topology.json" >&2; exit 2)
	python scripts/topology_certify.py --profile "$(PROFILE)" --inventory "$(INVENTORY)"

multihost-drill:
	./scripts/multihost_failover_drill.sh
.PHONY: production-certification-preflight production-load-certification-preflight production-load-certify production-certify production-deployment-guard
production-certification-preflight:
	python scripts/production_certification_preflight.py

production-load-certification-preflight:
	python scripts/production_load_certification_preflight.py

production-load-certify:
	@test -n "$(PROFILE)" || (echo "Set PROFILE=15|30|100" >&2; exit 2)
	@test -n "$(BASE_URL)" || (echo "Set BASE_URL=https://target" >&2; exit 2)
	@test -n "$(PROJECT_CODE)" || (echo "Set PROJECT_CODE=<certification fixture project>" >&2; exit 2)
	@test -n "$(PART_NUMBER)" || (echo "Set PART_NUMBER=<certification fixture part>" >&2; exit 2)
	@test -n "$(OUTPUT)" || (echo "Set OUTPUT=/path/load-evidence.json" >&2; exit 2)
	python scripts/production_load_certify.py --profile "$(PROFILE)" --base-url "$(BASE_URL)" --project-code "$(PROJECT_CODE)" --part-number "$(PART_NUMBER)" --output "$(OUTPUT)" $(if $(SIGNING_KEY),--signing-key "$(SIGNING_KEY)",)

production-certify:
	@test -n "$(PROFILE)" || (echo "Set PROFILE=15|30|100" >&2; exit 2)
	@test -n "$(TOPOLOGY)" || (echo "Set TOPOLOGY=/path/topology.json" >&2; exit 2)
	@test -n "$(EVIDENCE)" || (echo "Set EVIDENCE=/path/evidence.json" >&2; exit 2)
	@test -n "$(LOAD_EVIDENCE)" || (echo "Set LOAD_EVIDENCE=/path/load-evidence.json" >&2; exit 2)
	@test -n "$(LOAD_SIGNATURE)" || (echo "Set LOAD_SIGNATURE=/path/load-evidence.json.sig" >&2; exit 2)
	@test -n "$(LOAD_PUBLIC_KEY)" || (echo "Set LOAD_PUBLIC_KEY=/path/public-key.pem" >&2; exit 2)
	python scripts/production_certify.py --profile "$(PROFILE)" --topology "$(TOPOLOGY)" --evidence "$(EVIDENCE)" --load-evidence "$(LOAD_EVIDENCE)" --load-signature "$(LOAD_SIGNATURE)" --load-public-key "$(LOAD_PUBLIC_KEY)" --output production-certification.json --require-go

production-deployment-guard:
	@test -n "$(REPORT)" || (echo "Set REPORT=/path/production-certification.json" >&2; exit 2)
	python scripts/production_deployment_guard.py --report "$(REPORT)" --confirm "$(CONFIRM)"


.PHONY: release-acceptance-preflight release-acceptance acceptance-baseline-promote acceptance-chain-verify release-provenance-preflight release-provenance-governance-preflight release-provenance-init release-provenance-key-register release-provenance-key-revoke release-provenance-verify release-provenance-audit release-provenance-compare release-provenance-retention-set release-provenance-hold-place release-provenance-hold-release release-provenance-checkpoint release-provenance-anchor release-provenance-worm-seal release-provenance-governance release-provenance-auditor-export release-provenance-auditor-verify
release-acceptance-preflight:
	python scripts/release_acceptance_preflight.py

release-acceptance:
	./scripts/automated_release_acceptance.sh

acceptance-baseline-promote:
	@test -n "$(ACCEPTANCE)" || (echo "Set ACCEPTANCE=/path/release-acceptance.json" >&2; exit 2)
	@test -n "$(ACCEPTANCE_SIGNATURE)" || (echo "Set ACCEPTANCE_SIGNATURE=/path/release-acceptance.json.sig" >&2; exit 2)
	@test -n "$(ACCEPTANCE_PUBLIC_KEY)" || (echo "Set ACCEPTANCE_PUBLIC_KEY=/path/public.pem" >&2; exit 2)
	@test -n "$(APPROVAL_REFERENCE)" || (echo "Set APPROVAL_REFERENCE=<approved change reference>" >&2; exit 2)
	@test -n "$(BASELINE_OUTPUT)" || (echo "Set BASELINE_OUTPUT=/path/baseline.json" >&2; exit 2)
	@test -n "$(BASELINE_SIGNING_KEY)" || (echo "Set BASELINE_SIGNING_KEY=/secure/path/key.pem" >&2; exit 2)
	python scripts/promote_acceptance_baseline.py --acceptance "$(ACCEPTANCE)" --acceptance-signature "$(ACCEPTANCE_SIGNATURE)" --acceptance-public-key "$(ACCEPTANCE_PUBLIC_KEY)" --approval-reference "$(APPROVAL_REFERENCE)" --confirm "$(CONFIRM)" --output "$(BASELINE_OUTPUT)" --signing-key "$(BASELINE_SIGNING_KEY)"

acceptance-chain-verify:
	@test -n "$(PUBLIC_KEY)" || (echo "Set PUBLIC_KEY=/path/public.pem" >&2; exit 2)
	@test -n "$(ACCEPTANCE_FILES)" || (echo "Set ACCEPTANCE_FILES='file1.json file2.json ...'" >&2; exit 2)
	python scripts/verify_acceptance_chain.py --public-key "$(PUBLIC_KEY)" $(ACCEPTANCE_FILES)

release-provenance-preflight:
	python scripts/release_provenance_preflight.py

release-provenance-governance-preflight:
	python scripts/external_trust_retention_preflight.py

release-provenance-init:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(REGISTRY_ID)" || (echo "Set REGISTRY_ID=<registry-id>" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" init --registry-id "$(REGISTRY_ID)"

release-provenance-key-register:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(KEY_ID)" || (echo "Set KEY_ID=<trust-key-id>" >&2; exit 2)
	@test -n "$(PUBLIC_KEY)" || (echo "Set PUBLIC_KEY=/path/public.pem" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" key-register --key-id "$(KEY_ID)" --public-key "$(PUBLIC_KEY)"

release-provenance-key-revoke:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(KEY_ID)" || (echo "Set KEY_ID=<trust-key-id>" >&2; exit 2)
	@test -n "$(REASON)" || (echo "Set REASON=<revocation reason>" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" key-revoke --key-id "$(KEY_ID)" --reason "$(REASON)"

release-provenance-verify:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" verify

release-provenance-audit:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" audit $(if $(OUTPUT),--output "$(OUTPUT)",)

release-provenance-compare:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(PROFILE)" || (echo "Set PROFILE=15|30|100" >&2; exit 2)
	@test -n "$(RELEASE_A)" || (echo "Set RELEASE_A=x.y.z" >&2; exit 2)
	@test -n "$(RELEASE_B)" || (echo "Set RELEASE_B=x.y.z" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" compare --profile "$(PROFILE)" --release-a "$(RELEASE_A)" --release-b "$(RELEASE_B)"

release-provenance-retention-set:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(POLICY_ID)" || (echo "Set POLICY_ID=<retention-policy-id>" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" retention-set --policy-id "$(POLICY_ID)" --retention-json '$${RETENTION_JSON:-{}}'

release-provenance-hold-place:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(HOLD_ID)" || (echo "Set HOLD_ID=<legal-hold-id>" >&2; exit 2)
	@test -n "$(REASON)" || (echo "Set REASON=<legal-hold-reason>" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" hold-place --hold-id "$(HOLD_ID)" --reason "$(REASON)" $${RELEASE:+--release "$${RELEASE}"} $${OBJECT_SHA256:+--object-sha256 "$${OBJECT_SHA256}"}

release-provenance-hold-release:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(HOLD_ID)" || (echo "Set HOLD_ID=<legal-hold-id>" >&2; exit 2)
	@test -n "$(REASON)" || (echo "Set REASON=<release-reason>" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" hold-release --hold-id "$(HOLD_ID)" --reason "$(REASON)"

release-provenance-checkpoint:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" checkpoint

release-provenance-anchor:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(ADAPTER_COMMAND_JSON)" || (echo "Set ADAPTER_COMMAND_JSON='[\"/approved/anchor-adapter\"]'" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" anchor --adapter-command-json '$(ADAPTER_COMMAND_JSON)' --provider "$${PROVIDER:-external}"

release-provenance-worm-seal:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(ADAPTER_COMMAND_JSON)" || (echo "Set ADAPTER_COMMAND_JSON='[\"/approved/worm-adapter\"]'" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" worm-seal --adapter-command-json '$(ADAPTER_COMMAND_JSON)' --provider "$${PROVIDER:-external-worm}" --retain-days "$${RETAIN_DAYS:-3650}" --lock-mode "$${LOCK_MODE:-COMPLIANCE}"

release-provenance-governance:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" governance $${REQUIRE_EXTERNAL_ANCHOR:+--require-external-anchor} $${REQUIRE_WORM_RECEIPT:+--require-worm-receipt}

release-provenance-auditor-export:
	@test -n "$(REGISTRY)" || (echo "Set REGISTRY=/controlled/release-provenance" >&2; exit 2)
	@test -n "$(OUTPUT)" || (echo "Set OUTPUT=/path/offline-auditor.zip" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$(REGISTRY)" auditor-export --output "$(OUTPUT)"

release-provenance-auditor-verify:
	@test -n "$(BUNDLE)" || (echo "Set BUNDLE=/path/offline-auditor.zip" >&2; exit 2)
	python scripts/release_provenance_registry.py --registry "$${REGISTRY:-.}" auditor-verify --bundle "$(BUNDLE)"

.PHONY: operations-consolidation-preflight mgcctl-status mgcctl-verify resilience-drill-preflight resilience-certification-preflight resilience-sign-evidence resilience-baseline resilience-campaign resilience-certify
operations-consolidation-preflight:
	python scripts/operations_consolidation_preflight.py
	python scripts/integration_certification_preflight.py
	python scripts/resilience_drill_preflight.py
	python scripts/resilience_certification_preflight.py

resilience-drill-preflight:
	python scripts/resilience_drill_preflight.py

resilience-certification-preflight:
	python scripts/resilience_certification_preflight.py

resilience-sign-evidence:
	@test -n "$(EVIDENCE)" -a -n "$(PRIVATE_KEY)" -a -n "$(SIGNATURE)" || (echo "Set EVIDENCE, PRIVATE_KEY, SIGNATURE" >&2; exit 2)
	python scripts/resilience_certify.py sign-evidence --evidence "$(EVIDENCE)" --private-key "$(PRIVATE_KEY)" --signature-output "$(SIGNATURE)"

resilience-baseline:
	@test -n "$(EVIDENCE)" -a -n "$(SIGNATURE)" -a -n "$(PUBLIC_KEY)" -a -n "$(OUTPUT)" -a -n "$(APPROVAL_REF)" -a -n "$(APPROVED_AT)" -a -n "$(APPROVED_BY_ROLE)" || (echo "Set EVIDENCE SIGNATURE PUBLIC_KEY OUTPUT APPROVAL_REF APPROVED_AT APPROVED_BY_ROLE" >&2; exit 2)
	python scripts/resilience_certify.py baseline --evidence "$(EVIDENCE)" --signature "$(SIGNATURE)" --public-key "$(PUBLIC_KEY)" --approval-reference "$(APPROVAL_REF)" --approved-at "$(APPROVED_AT)" --approved-by-role "$(APPROVED_BY_ROLE)" --confirm APPROVE-BASELINE --output "$(OUTPUT)"

resilience-campaign:
	@test -n "$(BASELINE)" -a -n "$(OUTPUT)" -a -n "$(CAMPAIGN_ID)" -a -n "$(SCENARIOS)" -a -n "$(APPROVAL_REF)" -a -n "$(APPROVED_AT)" -a -n "$(APPROVED_BY_ROLE)" || (echo "Set BASELINE OUTPUT CAMPAIGN_ID SCENARIOS APPROVAL_REF APPROVED_AT APPROVED_BY_ROLE" >&2; exit 2)
	python scripts/resilience_certify.py campaign --baseline "$(BASELINE)" --campaign-id "$(CAMPAIGN_ID)" $(foreach S,$(SCENARIOS),--scenario $(S)) --profile "$${PROFILE:-core}" --tier "$${TIER:-production}" --approval-reference "$(APPROVAL_REF)" --approved-at "$(APPROVED_AT)" --approved-by-role "$(APPROVED_BY_ROLE)" --confirm APPROVE-CAMPAIGN --output "$(OUTPUT)"

resilience-certify:
	@test -n "$(EVIDENCE)" -a -n "$(SIGNATURE)" -a -n "$(PUBLIC_KEY)" -a -n "$(BASELINE)" -a -n "$(CAMPAIGN)" -a -n "$(OUTPUT)" || (echo "Set EVIDENCE SIGNATURE PUBLIC_KEY BASELINE CAMPAIGN OUTPUT" >&2; exit 2)
	python scripts/resilience_certify.py certify --evidence "$(EVIDENCE)" --signature "$(SIGNATURE)" --public-key "$(PUBLIC_KEY)" --baseline "$(BASELINE)" --campaign "$(CAMPAIGN)" --output "$(OUTPUT)" $(if $(REQUIRE_GO),--require-go,)

mgcctl-status:
	./mgcctl status

mgcctl-verify:
	./mgcctl verify --scope quick

.PHONY: integration-certification-preflight integration-runtime-assurance-preflight integration-certify
integration-certification-preflight:
	python scripts/integration_certification_preflight.py

integration-runtime-assurance-preflight:
	python scripts/integration_runtime_assurance_preflight.py

integration-certify:
	@test -n "$(CONTRACT)" || (echo "Set CONTRACT=/path/to/integration-contract.json" >&2; exit 2)
	python scripts/integration_certify.py --contract "$(CONTRACT)" $(if $(LIVE),--live,) $(if $(REQUIRE_PASS),--require-pass,)

.PHONY: target-host-assurance-preflight target-host-probe target-host-certify
target-host-assurance-preflight:
	python scripts/target_host_assurance_preflight.py

target-host-probe:
	@test -n "$(NODE_ID)" || (echo "Set NODE_ID=mgc-app-a" >&2; exit 2)
	@test -n "$(PROFILE)" || (echo "Set PROFILE=15|30|100" >&2; exit 2)
	@test -n "$(OUTPUT)" || (echo "Set OUTPUT=/path/target-host-evidence.json" >&2; exit 2)
	python scripts/target_host_probe.py --node-id "$(NODE_ID)" --profile "$(PROFILE)" --storage-path "$${STORAGE_PATH:-.}" --output "$(OUTPUT)"

target-host-certify:
	@echo "Use ./mgcctl certify target-host --profile ... --topology ... --evidence ... --output ..."

.PHONY: pilot-readiness-preflight
pilot-readiness-preflight:
	@python scripts/pilot_readiness_preflight.py
