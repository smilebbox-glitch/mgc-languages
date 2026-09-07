# OIDC / SSO — Engineer-Only Production

## Production policy

Production работает только через корпоративный OIDC/SSO. Shared API key не является пользовательским способом входа и по умолчанию блокируется при `APP_ENV=prod`.

```env
APP_ENV=prod
AUTH_MODE=oidc
ENGINEER_ONLY_ACCESS=true
ENGINEER_ACCESS_GROUPS=engineering-ai-users,engineering-ai-admins
ENGINEERING_ADMIN_GROUPS=engineering-ai-admins
ALLOW_API_KEY_AUTH_IN_PROD=false

OIDC_ISSUER=https://idp.company.example/...
OIDC_AUDIENCE=mgc-engineering-ai
OIDC_GROUPS_CLAIM=groups
OIDC_USER_CLAIM=preferred_username
```

## Два слоя проверки

`oauth2-proxy` является единственной host-published точкой входа и отсекает пользователей не из инженерных групп. После этого FastAPI самостоятельно валидирует подписанный access token и повторно проверяет group claim. Знание URL или прямой HTTP-запрос не заменяют авторизацию.

Разрешённые edge-группы:

```env
ENGINEER_SSO_GROUP=engineering-ai-users
ENGINEERING_ADMIN_SSO_GROUP=engineering-ai-admins
```

Финальные имена должны соответствовать реальным группам корпоративного IdP.

## Запуск

```bash
make up
```

Эквивалентно:

```bash
make up
```

Базовый `gateway` не имеет host-порта. `docker-compose.pilot.yml` публикует его только для явного non-production API-key pilot.

## Active Directory

Для классического on-prem AD используйте корпоративный OIDC federation layer (например, существующий корпоративный IdP), а не LDAP bind из приложения. Группы AD должны попадать в подписанный OIDC group claim.

## Документные ACL

Engineer-only gate отвечает за доступ к сервису. Поверх него document ACL ограничивает, какие инженерные документы видит уже авторизованный инженер. Маркер `all` означает «доступно всем авторизованным инженерам», а не «доступно всем сотрудникам».

## Acceptance

Обязательно протестировать две реальные учётные записи: одну инженерную и одну неинженерную. Первая должна войти; вторая должна быть отклонена. Проверить также отсутствие прямых host-портов `gateway`, `api`, `model-server`.
