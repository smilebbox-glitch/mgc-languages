# MGC v6.3.30 integration contracts

Reference vendor-neutral contracts for PLM/PDM/ERP/MES/QMS corporate gateways.

Production adapters remain pull/read-oriented. MGC does not automatically write back to source systems. Credentials are environment-variable references. Live certification is bounded and read-only.

Examples:

```bash
python scripts/integration_certify.py --contract ops/integrations/contracts/plm.example.json --require-pass
python scripts/integration_certify.py --contract /secure/site/plm.json --live --sample-limit 20 --require-pass
```

A corporate gateway may map Teamcenter, Windchill, 3DEXPERIENCE, SAP, MES or QMS vendor APIs into this contract without coupling MGC core to a vendor SDK.
