# MGC Engineering AI Local v6.3.12
## Supply Chain & Reproducible/Offline Builds

v6.3.12 — технический hardening-релиз поверх v6.3.11 без изменения схемы БД. Новых automotive business-domain функций нет. Цель — сделать production build inputs явными, immutable и проверяемыми, не выдавая developer build за сертифицированный корпоративный build.

## Главное

- application version `6.3.12`; database schema остаётся `6.3.11` — миграция БД не требуется;
- обычный `docker compose build` сохранён для разработки и внутренних стендов;
- отдельный strict режим `MGC_REQUIRE_REPRODUCIBLE_BUILD=true` работает fail-closed и не может тихо откатиться к range-based build;
- Core/AI/Advanced получают отдельные exact Python locks с SHA-256 и отдельные wheelhouse manifests;
- strict backend install использует только `pip --no-index --require-hashes`;
- frontend direct dependencies закреплены точными версиями; production требует `package-lock.json` + offline npm cache и `npm ci --offline`;
- base/runtime container images в strict режиме допускаются только как `repo@sha256:<digest>`;
- runtime Debian-библиотеки backend в strict режиме ставятся из отдельного SHA-256-проверенного `.deb` bundle, привязанного к approved `PYTHON_BASE_IMAGE`;
- `docker-compose.reproducible.yml` устанавливает `build.network: none`, поэтому после подготовки dependency/OS artifacts application build не обращается к PyPI/npm/Debian mirror;
- `BUILD_INPUTS.json` фиксирует dependency/build-control files, manifests/bundles и immutable image references;
- BUILD_INPUTS SHA-256 передаётся в OCI provenance labels собранных application images;
- strict build выполняет source/dependency vulnerability gate **до** build и built-image vulnerability gate **после** build;
- build attestation связывает BUILD_INPUTS, SBOM, dependency evidence, OS bundle, CVE reports и IDs реально построенных images;
- attestation всегда содержит `production_authorized=false` — корпоративный change approval остаётся внешним human gate;
- strict air-gap preparation использует тот же reproducible path и не может обойти его старым build wrapper.

## Подготовка корпоративных dependency artifacts

Python:

```bash
python scripts/prepare_python_lock.py --profile core --index-url https://approved-python-mirror/simple
python scripts/prepare_python_lock.py --profile ai --index-url https://approved-python-mirror/simple
python scripts/prepare_python_lock.py --profile advanced --index-url https://approved-python-mirror/simple
```

Frontend:

```bash
NPM_CONFIG_REGISTRY=https://approved-npm-mirror/ ./scripts/prepare_frontend_lock.sh
```

Immutable container images:

```bash
python scripts/resolve_container_digests.py --output .env.reproducible
```

Offline OS package bundle (после фиксации `PYTHON_BASE_IMAGE`):

```bash
set -a
. ./.env.reproducible
set +a
./scripts/prepare_os_package_bundle.sh
```

Затем BUILD_INPUTS необходимо пересчитать уже с approved image references:

```bash
python scripts/generate_build_inputs.py --env .env.reproducible
```

После подготовки и установки approved Trivy/Grype-equivalent scanner:

```bash
make reproducible-build
```

Strict wrapper проверяет locks/digests/OS bundle, выполняет source CVE gate, собирает application images без build network, выполняет image-level CVE gate и формирует/проверяет build attestation.

## Текущий статус исходного пакета

В packaging environment нет доступа к корпоративным npm/Python/Debian/container mirrors и approved CVE scanner. Поэтому package-lock, wheelhouse, OS `.deb` bundle и реальные image digests **не фабрикуются**.

`python scripts/supply_chain_preflight.py` возвращает `CONDITIONAL`, а `--strict` завершается fail-closed до появления корпоративных артефактов. Это ожидаемый security posture, а не ошибка runtime.

Финальный backend regression выполнен из содержимого release ZIP независимыми завершившимися test-группами: **434/434 PASS**, **85/85 test-файлов**, без assertion failures и per-file timeout. В ходе полного прогона дополнительно найден и исправлен legacy Celery compatibility gap: очереди `heavy/background/default` снова принимаются worker-ами как transition aliases, при этом текущие задания продолжают маршрутизироваться через resource-class очереди `cpu/io/maintenance/...`.

Релиз не заявляет completed dependency certification, CVE acceptance или Production GO.
