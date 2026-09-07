from __future__ import annotations

from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, ProjectArea

AREA_CATALOG = [
    {"code": "product_engineering", "name": "R&D / Инжиниринг", "short_name": "R&D", "icon": "◇", "aliases": ["r&d", "engineering", "product-engineering", "design"]},
    {"code": "stamping", "name": "Штамповка", "short_name": "Штамповка", "icon": "▱", "aliases": ["stamping", "press", "press-shop", "штамповка"]},
    {"code": "body_welding", "name": "Кузов / Сварка", "short_name": "Сварка", "icon": "⌁", "aliases": ["welding", "body", "body-shop", "biw", "сварка"]},
    {"code": "paint", "name": "Окраска", "short_name": "Окраска", "icon": "◐", "aliases": ["paint", "paint-shop", "painting", "окраска"]},
    {"code": "assembly", "name": "Сборка", "short_name": "Сборка", "icon": "▦", "aliases": ["assembly", "ga", "general-assembly", "сборка"]},
    {"code": "components", "name": "Компоненты", "short_name": "Компоненты", "icon": "⬡", "aliases": ["components", "supplier", "component", "компоненты"]},
    {"code": "logistics", "name": "Логистика", "short_name": "Логистика", "icon": "⇄", "aliases": ["logistics", "material-flow", "warehouse", "логистика"]},
    {"code": "quality", "name": "Качество", "short_name": "Качество", "icon": "✓", "aliases": ["quality", "qa", "sqe", "качество"]},
    {"code": "manufacturing_engineering", "name": "Технология производства", "short_name": "Технология", "icon": "⚙", "aliases": ["manufacturing-engineering", "process-engineering", "industrialization", "technology", "технолог"]},
    {"code": "testing", "name": "Испытания / Валидация", "short_name": "Испытания", "icon": "△", "aliases": ["testing", "validation", "dv", "pv", "испыт"]},
]
AREA_BY_CODE = {x["code"]: x for x in AREA_CATALOG}

AREA_FOCUS = {
    "product_engineering": ["Требования и назначение детали", "CAD ↔ чертёж ↔ BOM", "Критические характеристики и GD&T", "Результаты испытаний", "ECR/ECO и история ревизий"],
    "stamping": ["Материал и толщина листа", "Радиусы/формообразование и геометрия", "Базы и контрольные точки", "Оснастка и технологичность", "Изменения, влияющие на штамп/инструмент"],
    "body_welding": ["Материал и толщина деталей", "Сварные соединения и обозначения", "Базы/геометрия кузова и fixture points", "Доступность соединений и оснастки", "Изменения, влияющие на кузовную геометрию"],
    "paint": ["Требования к покрытию и поверхности", "Зоны маскирования/неокрашиваемые поверхности", "Совместимость материалов и покрытий", "Дренаж/доступность полостей", "Дефекты поверхности и замечания качества"],
    "assembly": ["Состав BOM и комплектность", "Интерфейсы и посадочные размеры", "Крепёж/момент/последовательность операции", "Доступность инструмента и эргономика", "Изменения, влияющие на сборочную операцию"],
    "components": ["Ревизия поставщика ↔ внутренняя ревизия", "Чертёж/CAD/спецификация компонента", "Критические характеристики", "Испытания и evidence поставщика", "Изменения/локализация компонента"],
    "logistics": ["Масса и габариты", "Упаковка и защита детали", "Маркировка и прослеживаемость", "Material flow / последовательность поставки", "Изменения, влияющие на тару или маршрут"],
    "quality": ["Критические характеристики и GD&T", "Открытые замечания/несоответствия", "Метод измерения и контроль", "Результаты испытаний", "Закрытие рисков перед выпуском"],
    "manufacturing_engineering": ["Маршрут и последовательность операций", "Оборудование/оснастка/инструмент", "Технологичность и доступность", "Контрольные операции", "Impact ECR/ECO на процесс"],
    "testing": ["Покрытие требований испытаниями", "План и условия испытаний", "Результаты/отказы", "Связь отказов с ревизиями", "Повторная валидация после ECR/ECO"],
}


def valid_area(code: str | None) -> bool:
    return code in AREA_BY_CODE if code else True


def ensure_project_areas(db: Session, project: Project) -> list[ProjectArea]:
    existing = {x.code: x for x in db.scalars(select(ProjectArea).where(ProjectArea.project_code == project.code)).all()}
    groups = list(project.acl_groups or ["all"])
    changed = False
    for order, item in enumerate(AREA_CATALOG, 1):
        if item["code"] in existing:
            continue
        row = ProjectArea(
            project_code=project.code, code=item["code"], name=item["name"], status="active",
            acl_groups=groups, sort_order=order * 10, metadata_json={"builtin": True, "icon": item["icon"], "short_name": item["short_name"]},
        )
        db.add(row); existing[item["code"]] = row; changed = True
    if changed:
        db.commit()
    return sorted(existing.values(), key=lambda x: (x.sort_order, x.name))


def area_allowed(area: ProjectArea, groups: Iterable[str]) -> bool:
    return bool(set(area.acl_groups or ["all"]) & set(list(groups) + ["all"]))


def visible_project_areas(db: Session, project: Project, groups: Iterable[str]) -> list[ProjectArea]:
    return [x for x in ensure_project_areas(db, project) if x.status == "active" and area_allowed(x, groups)]


def serialize_area(area: ProjectArea, groups: Iterable[str] | None = None) -> dict:
    item = AREA_BY_CODE.get(area.code, {})
    return {
        "id": area.id, "project_code": area.project_code, "code": area.code, "name": area.name,
        "short_name": (area.metadata_json or {}).get("short_name") or item.get("short_name") or area.name,
        "icon": (area.metadata_json or {}).get("icon") or item.get("icon") or "•",
        "status": area.status, "owner": area.owner, "acl_groups": area.acl_groups or [],
        "sort_order": area.sort_order, "notes": area.notes,
        "allowed": area_allowed(area, groups or []) if groups is not None else True,
        "focus": AREA_FOCUS.get(area.code, []),
    }


def infer_area_codes_from_groups(groups: Iterable[str]) -> list[str]:
    normalized = [str(g).lower().replace("_", "-") for g in groups]
    found = []
    for item in AREA_CATALOG:
        aliases = [a.lower().replace("_", "-") for a in item.get("aliases", [])] + [item["code"].replace("_", "-")]
        if any(any(alias in group for alias in aliases) for group in normalized):
            found.append(item["code"])
    return found


def document_in_area(document, area_code: str | None) -> bool:
    if not area_code:
        return True
    # Unassigned documents are project-common and intentionally visible inside every area.
    return not getattr(document, "manufacturing_area", None) or document.manufacturing_area == area_code
