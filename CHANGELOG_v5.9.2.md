# MGC Languages v5.9.2 — Language Content Router Extraction

Moves five authenticated language-content routes behind `mgc.routers.language_content`:

- `GET /api/language/{language}/summary`
- `GET /api/language/{language}/quiz`
- `GET /api/language/{language}/situations`
- `GET /api/language/{language}/roleplays`
- `GET /api/language/{language}/mgc-scenarios`

The route layer stays thin. Existing summary calculations, quiz generation/randomization, pronunciation helpers and scenario content remain in the existing handlers for this increment.

`mgc_core.language_content_router_bridge` verifies exact route ownership, Auth Core binding, Terminology Service binding, route-name/response-class parity and StaticFiles ordering.

The `v592` shard verifies anonymous `401`, English/Chinese summaries, Putonghua learning standard, quiz count bounds `5..30`, generated four-option questions, situations, roleplays, MGC scenarios, invalid-language `404`, and OpenAPI preservation.

No DB/Alembic change, no runtime APP_VERSION bump, no frontend/content mutation. Putonghua (普通话) remains the primary Chinese-learning standard.

Stacked over v5.9.1; do not merge to main until the preceding chain and full CI/Docker are green.
