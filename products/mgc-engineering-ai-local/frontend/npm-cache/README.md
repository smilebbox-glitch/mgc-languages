# Frontend offline npm cache

Generate `frontend/package-lock.json` and this cache from the approved corporate npm registry using `scripts/prepare_frontend_lock.sh`. Reproducible Docker builds use `npm ci --offline` and fail closed when either input is missing.
