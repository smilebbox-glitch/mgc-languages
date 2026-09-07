# Engineer-Only Access — v3.5

## Цель

MGC Engineering AI предназначен только для инженерных подразделений. В production обычный корпоративный пользователь не должен получить ни UI, ни RAG, ни VLM/LLM, ни CAD API даже при знании внутреннего URL.

## Два обязательных слоя доступа

1. **Edge SSO gate (`oauth2-proxy`)** — допускает только пользователей из `engineering-ai-users` или `engineering-ai-admins`.
2. **FastAPI authorization gate** — независимо повторно проверяет подписанный OIDC access token и его group claim на каждом защищённом endpoint.

Модельный сервер, PostgreSQL, Qdrant, Redis, MinIO, Neo4j, API, frontend и базовый gateway не публикуют host-порты в production air-gap topology. Единственная пользовательская точка входа — SSO proxy.

## Группы

```text
engineering-ai-users   — инженер: поиск, документы, CAD, AI, проверки, история
engineering-ai-admins  — инженер-администратор: всё выше + IT/административный раздел
```

Администратор должен оставаться инженерной ролью. Финальные имена групп заменяются на реальные AD/Entra/Keycloak группы компании.

## Запуск production

```bash
cp .env.airgap.example .env
# заполнить OIDC/SSO secrets и approved pinned image references
make up
```

`make up` использует `docker-compose.airgap.yml` + `docker-compose.sso.yml`.

## Запрещённые production-паттерны

- общий пароль или shared API key как пользовательский вход;
- прямой host-port на `gateway`, `api` или `model-server`;
- доверие к `X-Forwarded-User` от произвольного клиента;
- добавление неинженерных групп в `ENGINEER_ACCESS_GROUPS`;
- публикация локального model-server (vLLM/llama.cpp) наружу;
- использование pilot override в production.

`docker-compose.pilot.yml` существует только для локального теста и явно включает API-key mode.

## Проверка перед вводом

Минимальный реальный acceptance test:

1. инженер из разрешённой группы входит — **200 / UI открыт**;
2. сотрудник не из инженерной группы входит через корпоративный IdP — **доступ запрещён**;
3. прямой доступ к `gateway/api/model-server` с рабочей станции отсутствует;
4. пользователь `engineering-ai-users` не видит раздел «Для IT»;
5. пользователь `engineering-ai-admins` видит административный раздел;
6. shared API key в `APP_ENV=prod` отклоняется.

Статические проверки выполняются `make security-preflight`; реальный SSO-тест требует корпоративного IdP.
