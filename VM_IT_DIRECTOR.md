# MGC Languages — передача IT-директору для установки на VM

Этот документ — основной runbook для установки актуального MGC Languages на внутреннюю виртуальную машину. Профиль рассчитан на корпоративную LAN-сеть, Docker Compose, PostgreSQL и HTTPS. База данных и приложение не публикуют свои внутренние порты наружу; пользователи заходят только через Nginx HTTPS gateway.

## 1. Рекомендуемая виртуальная машина

Для пилота:

- Ubuntu Server 24.04 LTS (22.04 LTS допустим при актуальном Docker);
- 4 vCPU;
- 8 GB RAM;
- 40 GB SSD;
- статический LAN IP или внутреннее DNS-имя;
- синхронизация времени NTP;
- доступ к GitHub/registry на этапе первой установки и обновлений.

Минимально для небольшой тестовой группы: 2 vCPU, 4 GB RAM, 20 GB свободного диска.

ПО на VM:

- Git;
- Docker Engine;
- Docker Compose v2 (`docker compose`);
- `curl`;
- `openssl`.

Рекомендуется Docker Engine 27+ и актуальный Compose v2.

## 2. Сеть и firewall

Разрешить:

- TCP 443 от корпоративной LAN к VM;
- TCP 22 только от администраторской сети/рабочих мест, если используется SSH.

Не публиковать в LAN:

- PostgreSQL 5432;
- Uvicorn/app 8000.

Профиль `docker-compose.vm.prod.yml` сам не публикует 5432 и 8000.

## 3. TLS / сертификат

Для телефонов, PWA и нормальной работы Service Worker рекомендуется сертификат от корпоративного CA на IP/DNS VM.

Есть два варианта.

### Вариант A — корпоративный сертификат (предпочтительно)

Перед первой установкой:

```bash
export MGC_VM_HOST=mgc-languages.company.local
export MGC_TLS_CERT_SOURCE=/path/to/fullchain.pem
export MGC_TLS_KEY_SOURCE=/path/to/private.key
bash deploy/vm/install_vm.sh
```

Скрипт копирует сертификат и ключ в локальный runtime-каталог с ограниченными правами. Они не попадают в Git.

### Вариант B — self-signed для быстрого пилота

```bash
export MGC_VM_HOST=10.20.30.40
bash deploy/vm/install_vm.sh
```

Сертификат будет создан автоматически. Для полноценной PWA на телефонах этот сертификат необходимо добавить в доверенные сертификаты устройств. Простого обхода browser warning для Service Worker может быть недостаточно.

## 4. Первая установка

```bash
git clone https://github.com/smilebbox-glitch/mgc-languages.git
cd mgc-languages
git checkout main
bash deploy/vm/install_vm.sh
```

Скрипт автоматически:

1. проверит Docker, Compose, Git, curl и OpenSSL;
2. создаст `.env.vm`;
3. сгенерирует уникальные PostgreSQL/OIDC/metrics/admin секреты;
4. определит LAN IP VM, либо возьмёт `MGC_VM_HOST`;
5. подготовит TLS;
6. проверит Docker Compose модель;
7. соберёт текущий application image;
8. запустит PostgreSQL, MGC Languages и Nginx;
9. дождётся `/health/ready`;
10. выполнит финальную проверку работоспособности.

Начальные данные администратора сохраняются локально на VM в:

```text
deploy/vm/runtime/initial-admin.txt
```

Файл имеет ограниченные права. После передачи учётных данных владельцу сервиса файл нужно удалить.

## 5. Проверка после установки

```bash
bash deploy/vm/check_vm.sh
```

Проверяется:

- Docker Compose config;
- PostgreSQL readiness;
- внутренний health приложения;
- HTTPS `/health/live` и `/health/ready`;
- web/PWA shell;
- срок действия TLS;
- отсутствие опубликованных портов 5432 и 8000;
- состояние всех контейнеров.

Для пользователей адрес будет:

```text
https://<VM-IP-or-DNS>
```

Если используется нестандартный `MGC_HTTPS_PORT`, порт будет добавлен к URL.

## 6. Backup

Перед обновлениями и регулярно по расписанию:

```bash
bash deploy/vm/backup_vm.sh
```

Результат:

```text
backups/vm/mgc_languages_<UTC_TIMESTAMP>.sql.gz
backups/vm/mgc_languages_<UTC_TIMESTAMP>.sql.gz.meta
```

`.meta` содержит commit SHA и SHA-256 дампа. Рекомендуется копировать backup за пределы самой VM согласно политике компании.

## 7. Restore

```bash
bash deploy/vm/restore_vm.sh backups/vm/mgc_languages_YYYYMMDDTHHMMSSZ.sql.gz
```

Скрипт запросит подтверждение `RESTORE`, остановит app/nginx, восстановит PostgreSQL, снова запустит сервис и выполнит health-check.

Для автоматизированного восстановления:

```bash
bash deploy/vm/restore_vm.sh <backup.sql.gz> --yes
```

## 8. Обновление сервиса

На `main` без локальных изменений:

```bash
bash deploy/vm/update_vm.sh
```

Процедура:

1. создаёт backup БД;
2. делает `git fetch`;
3. применяет только fast-forward `origin/main`;
4. пересобирает image;
5. запускает актуальные контейнеры;
6. выполняет readiness и полный VM check.

## 9. Запуск и остановка

Запуск:

```bash
bash deploy/vm/start_vm.sh
```

Остановка без удаления БД:

```bash
bash deploy/vm/stop_vm.sh
```

`stop_vm.sh` никогда не использует `docker compose down -v`, поэтому PostgreSQL volume сохраняется.

## 10. Диагностика

Состояние:

```bash
docker compose --env-file .env.vm -f docker-compose.vm.prod.yml ps
```

Логи:

```bash
docker compose --env-file .env.vm -f docker-compose.vm.prod.yml logs --tail 200 app nginx db
```

Проверка повторно:

```bash
bash deploy/vm/check_vm.sh
```

## 11. Что хранится где

- приложение — Docker image, собираемый из текущего Git commit;
- PostgreSQL — named volume `vm_pgdata`;
- секреты — `.env.vm`, только на VM;
- TLS — `deploy/vm/runtime/certs/`, только на VM;
- начальные admin credentials — `deploy/vm/runtime/initial-admin.txt`, удалить после передачи;
- backups — `backups/vm/`, не входят в Git.

## 12. Что IT не нужно менять

Для стандартного пилота не требуется менять код, API, игровые настройки, PWA, XP/scoring или базу вручную. Миграции БД выполняются штатным `scripts/entrypoint.sh` через безопасный migration preflight.

## 13. Приёмочный чек-лист

Перед передачей пользователям:

- [ ] VM имеет статический IP/DNS;
- [ ] TCP 443 доступен из корпоративной LAN;
- [ ] 5432 и 8000 недоступны извне;
- [ ] `bash deploy/vm/check_vm.sh` завершён без ошибок;
- [ ] корпоративный сертификат установлен или self-signed сертификат доверен тестовым устройствам;
- [ ] web-версия открывается с ПК;
- [ ] PWA открывается с телефона по HTTPS;
- [ ] вход администратора работает;
- [ ] выполнен первый backup;
- [ ] backup скопирован/зарегистрирован согласно политике компании;
- [ ] `initial-admin.txt` удалён после передачи credentials.

## Быстрая команда для первой установки

Если Docker и остальные prerequisites уже установлены, а self-signed TLS допустим для тестовой VM:

```bash
MGC_VM_HOST=<IP_ИЛИ_DNS_VM> bash deploy/vm/install_vm.sh
```

После завершения запустить:

```bash
bash deploy/vm/check_vm.sh
```
