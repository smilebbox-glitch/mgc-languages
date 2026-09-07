# Corporate Network / Firewall Matrix — v6.1.0

Default-deny is assumed. The canonical machine-readable example is `deployment/corporate-pilot/firewall-matrix.csv`.

- 443/TCP inbound: corporate browser/SSO to Enterprise Edge.
- 9443/TCP inbound: optional mTLS machine webhook edge.
- 8080, 5432, 6333, 6379, 7687, 9000, 8000: internal-only.
- 443/TCP corporate outbound: OIDC and approved enterprise-system gateways.
- 53 UDP/TCP: corporate DNS.
- 123 UDP: corporate NTP; clock sync is required for OIDC/audit consistency.

No database/vector/queue/model service should be directly published to user networks.
