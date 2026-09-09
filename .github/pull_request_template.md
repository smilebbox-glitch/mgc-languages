## Изменение

Кратко опишите, что меняется и зачем.

## Security / privacy

- [ ] В diff нет `.env`, токенов, паролей, приватных ключей, внутренних production URL или персональных данных сотрудников.
- [ ] Изменения авторизации, ролей, cookies, CORS, HTTPS/gateway или admin/manager доступа проверены отдельно.
- [ ] Если меняется PWA/service worker: auth/API/private HTML и пользовательские данные не попадают в Cache Storage.
- [ ] Security-critical файлы не ослабляют fail-closed поведение.

## Release freeze

- [ ] Номер версии не повышен, если это явно не является новой согласованной версией.
- [ ] Для текущего пилота сохранён контракт v6.0.29 RC1.
- [ ] `python scripts/release_candidate_guard.py --json` проходит.

## Verification

- [ ] Основной CI проходит.
- [ ] Repository integrity проходит.
- [ ] Server/mobile security gate проходит для security/runtime изменений.
- [ ] CodeQL не показывает новых проблем.

## Risk / rollback

Опишите основной риск изменения и способ отката, если изменение затрагивает runtime, deployment, security или данные.
