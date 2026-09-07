# Corporate AD/OIDC Checklist — v6.1.0

Before controlled pilot launch:

- create Engineering AI user/admin groups and map them to existing corporate ownership;
- configure HTTPS issuer, audience and JWKS allowlist;
- verify required user/groups claims;
- verify token expiry, wrong audience, wrong issuer, removed-group and disabled-user negative cases;
- validate admin/user separation;
- verify break-glass ownership outside MGC;
- disable API-key and trusted-header human authentication in production;
- synchronize host time with corporate NTP;
- record evidence in the corporate change ticket.

MGC role focus never widens ACL.
