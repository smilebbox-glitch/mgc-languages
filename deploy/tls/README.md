# TLS material for the secure server edge

This directory intentionally contains **no certificates or private keys in Git**.

On the deployment server, IT should place the trusted certificate and private key here (or point `TLS_CERT_FILE` / `TLS_KEY_FILE` in `.env.pilot` to another protected host path):

- `tls.crt` — certificate chain trusted by employee devices;
- `tls.key` — matching private key.

Requirements for the company server:

- never commit `tls.crt`, `tls.key`, PKCS#12/PFX files, or copied secrets;
- keep the private key readable only by the deployment administrator/root and the container mount;
- use a certificate whose SAN contains the DNS name employees open on their phones;
- renew/rotate the certificate before expiry;
- use the company PKI or another CA already trusted by managed devices; a self-signed certificate is suitable only when the company CA/trust profile is deliberately installed on those devices.

The secure deployment profile mounts both files read-only into the HTTPS gateway.
