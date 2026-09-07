from __future__ import annotations

import hashlib, json
from app.integrations.registry import build_connector
from app.ports.handover import HandoverDeliveryResult

def _canon(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)

class GenericRestHandoverAdapter:
    """Controlled outbound adapter for approved REST integration gateways only."""
    def _connector(self, system):
        connector = build_connector(system.connector_type, system.config_json or {}, system.secret_config_json or {})
        if not hasattr(connector, "request"):
            raise RuntimeError("Selected connector does not implement controlled REST write")
        return connector

    def execute(self, *, system, target, payload, headers):
        if not str(target.write_path or "").startswith("/") or "://" in str(target.write_path):
            raise RuntimeError("Handover write path must be a relative integration-gateway path")
        r = self._connector(system).request("POST", target.write_path, json=payload, headers=headers)
        try: body = r.json() if r.content else {}
        except Exception: body = {"body_sha256": hashlib.sha256(r.content or b"").hexdigest()}
        receipt = str(body.get("receipt_id") or body.get("id") or r.headers.get("X-Request-ID") or "") or None
        return HandoverDeliveryResult(ok=True, status="accepted", external_receipt_id=receipt, response=body)

    def reconcile(self, *, system, target, external_receipt_id, headers):
        template = str(target.reconcile_path_template or "")
        if not template:
            raise RuntimeError("Target has no reconciliation endpoint configured")
        if not template.startswith("/") or "://" in template:
            raise RuntimeError("Handover reconciliation path must be relative")
        path = template.format(receipt_id=external_receipt_id)
        r = self._connector(system).request("GET", path, headers=headers)
        body = r.json() if r.content else {}
        state_hash = body.get("target_state_sha256")
        return HandoverDeliveryResult(ok=True, status=str(body.get("status") or "reconciled"), external_receipt_id=external_receipt_id, response=body, target_state_sha256=state_hash)

class DisabledHandoverAdapter:
    def execute(self, **kwargs):
        raise RuntimeError("External handover write adapter is disabled")
    def reconcile(self, **kwargs):
        raise RuntimeError("External handover reconciliation adapter is disabled")
