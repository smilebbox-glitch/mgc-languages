# MGC Engineering AI Local v6.3.20
## Multi-host Production Topology & External Load-Balancer Safety

v6.3.20 продолжает v6.3.19 и закрывает следующий эксплуатационный слой: разнесение application-tier по нескольким физическим/VM-хостам и безопасное подключение внешнего load balancer. Automotive business schema не меняется: application **6.3.20**, database schema **6.3.13**.

## Главное

- runtime heartbeat теперь несёт `topology_node_id`, `topology_failure_domain` и operational node role;
- добавлен Engineering Admin snapshot `GET /api/v1/operations/multi-host-topology`;
- проверяется anti-affinity API и обязательных worker roles по независимым failure domains;
- одинаковый `node_id` в разных failure domains считается `UNSAFE`;
- отсутствие одной реплики/домена даёт `DEGRADED`, но не создаёт каскадное выключение оставшегося API;
- добавлен минимальный system endpoint `GET /api/v1/health/lb`: только eligibility/version/schema, без внутренних dependency/topology details;
- reference HAProxy использует active health checks и `retries 0`; non-idempotent request replay/redispatch не включается;
- `docker-compose.multihost.yml` предназначен для запуска отдельно на каждом app host и требует явные `MGC_NODE_ID`, `MGC_FAILURE_DOMAIN`, bind IP, shared PostgreSQL/Redis и v6.3.19 authoritative fencing;
- per-node наружу публикуется только gateway; API/workers не получают host ports;
- добавлены topology reference inventories для 15/30/100 инженеров;
- topology certification проверяет placement/failure-domain policy, но всегда оставляет `performance_certified=false` и `production_authorized=false`;
- deployment guard блокирует следующий drain/cutover, если текущая multi-host topology не `HEALTHY`;
- disruptive host-loss drill требует явного `MGC_MULTHOST_DRILL_CONFIRM=YES` и внешних approved fault-injection/recovery команд;
- privacy-safe Support Bundle получает `multi-host-topology.json`;
- новый topology Operations endpoint защищён Engineering Admin identity;
- external LB health endpoint является пятым явным system/public exception.

## Команды

```bash
make multihost-preflight
make topology-certify PROFILE=30 INVENTORY=ops/multihost/topology.30.example.json
python scripts/multihost_deployment_guard.py --snapshot topology.json
```

Target-host disruptive drill:

```bash
MGC_MULTHOST_DRILL_CONFIRM=YES \
MGC_EXTERNAL_LB_PROBE_URL=https://lb.example/api/v1/health/lb \
MGC_HOST_FAILURE_INJECT_CMD='<approved command>' \
MGC_HOST_RECOVER_CMD='<approved command>' \
make multihost-drill
```

## Production boundary

MGC по-прежнему не выполняет PostgreSQL promotion/ST​ONITH, storage replication, host/zone scheduling или внешний LB quorum. Эти функции должны предоставляться корпоративной инфраструктурой. Профили 15/30/100 — topology references, а не заявление о фактической производительности. Реальный multi-host host-loss/LB drill, нагрузочные тесты и DB/evidence HA failover должны быть выполнены на целевых серверах до Production GO.
