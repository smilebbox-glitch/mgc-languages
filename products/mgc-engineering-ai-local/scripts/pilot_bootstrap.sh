#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-http://localhost:3000}"

post_json(){ curl -fsS -X POST "$1" -H 'Content-Type: application/json' -d "$2"; }
create(){
  local payload="$1"
  local code="$2"
  echo "Registering $code ..."
  status=$(curl -sS -o /tmp/mgc_connector.json -w '%{http_code}' -X POST "$BASE/api/v1/integrations" -H 'Content-Type: application/json' -d "$payload")
  if [[ "$status" != "200" && "$status" != "409" ]]; then cat /tmp/mgc_connector.json; exit 1; fi
}

create '{"code":"engineering-share","name":"Engineering Read-only Share","connector_type":"mounted_folder","config":{"path":"/integrations/share","extensions":[".pdf",".docx",".xlsx",".pptx",".txt",".csv",".step",".stp",".stl",".catpart",".prt",".jt"]},"acl_groups":["all"]}' engineering-share
create '{"code":"mock-plm","name":"PLM Integration Simulator","connector_type":"plm_rest","config":{"base_url":"http://integration-simulator:8090","health_path":"/health","list_path":"/api/assets"},"secrets":{"webhook_secret_env":"PLM_WEBHOOK_SECRET"},"acl_groups":["all"]}' mock-plm
create '{"code":"mock-erp","name":"ERP / BOM Simulator","connector_type":"bom_rest","config":{"base_url":"http://integration-simulator:8090","health_path":"/health","list_path":"/api/boms","detail_path_template":"/api/boms/{external_id}"},"acl_groups":["all"]}' mock-erp
create '{"code":"mock-cad","name":"Licensed CAD Gateway Simulator","connector_type":"cad_gateway","config":{"base_url":"http://integration-simulator:8090","health_path":"/health","capabilities_path":"/capabilities","convert_path":"/convert"},"acl_groups":["all"]}' mock-cad

systems=$(curl -fsS "$BASE/api/v1/integrations")
python - "$BASE" "$systems" <<'PY'
import json, subprocess, sys
base, raw = sys.argv[1], sys.argv[2]
for s in json.loads(raw):
    subprocess.run(["curl","-fsS","-X","POST",f"{base}/api/v1/integrations/{s['id']}/health"],check=True,stdout=subprocess.DEVNULL)
    if s["connector_type"] != "cad_gateway":
        subprocess.run(["curl","-fsS","-X","POST",f"{base}/api/v1/integrations/{s['id']}/sync","-H","Content-Type: application/json","-d",'{"page_limit":100,"max_pages":20}'],check=True,stdout=subprocess.DEVNULL)
PY

echo "Uploading native CAD placeholder ..."
upload=$(curl -fsS -X POST "$BASE/api/v1/documents/upload" \
  -F 'file=@samples/integrations/8450012345_REV_D_demo.CATPart' \
  -F 'part_number=8450012345' -F 'revision=D' -F 'project_code=DEMO-RD' -F 'acl_groups=all')
doc_id=$(python -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"$upload")

echo "Converting native CAD through simulator gateway ..."
post_json "$BASE/api/v1/cad/convert" "{\"document_id\":\"$doc_id\",\"gateway_system_code\":\"mock-cad\",\"target_format\":\"step\"}" >/tmp/mgc_convert.json
cat /tmp/mgc_convert.json

echo
echo "Pilot integration bootstrap complete. Open $BASE and check Operations / Knowledge Base / Part 360°."
