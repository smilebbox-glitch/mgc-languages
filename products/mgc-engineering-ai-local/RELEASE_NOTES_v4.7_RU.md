# MGC Engineering AI Local v4.8.0 — Release Notes

## Основное
Добавлен слой Vehicle / System Architecture & Interface Management для автопрома. Сервис теперь связывает автомобиль, системы, подсистемы, сборки и компоненты, а интерфейсы между ними становятся отдельными инженерными объектами с требованиями, V&V evidence и ECR/ECO.

## Что нового
- Vehicle → System → Subsystem → Assembly → Component.
- Mechanical / Electrical / Fluid / Thermal / Data / Control / Packaging interfaces.
- Critical-interface gate: требование + evidence-backed verification.
- PASSED без evidence не считается подтверждением.
- Fingerprint verification: изменение интерфейса или сопряжённого узла делает старое подтверждение stale.
- Part-level impact: соседние узлы/интерфейсы, requirements, open ECR/ECO, cost и localization references.
- Один компактный блок в Project Workspace, без нового пункта основного меню.
- Engineer-only SSO и ACL по проекту/зоне/документу сохранены.

## Governance
Модуль носит рекомендательный характер и не заменяет PLM/PDM, formal system engineering approval или release authority.
