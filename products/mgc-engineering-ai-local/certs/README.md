# Enterprise TLS material

Do not commit certificate private keys here. For `docker-compose.enterprise-security.yml`, set `MGC_TLS_CERT_DIR` to an externally protected directory containing `server.crt`, `server.key`, and `client-ca.crt` issued/approved by the corporate PKI.
