import csv
from pathlib import Path

from app.core.config import get_settings

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.db.models import BOMItem, Document


ALIASES = {
    "child": {"part", "part_number", "part no", "part number", "pn", "номер детали", "деталь", "child_part_number"},
    "qty": {"qty", "quantity", "количество", "кол-во", "count"},
    "desc": {"description", "name", "наименование", "описание"},
    "rev": {"revision", "rev", "ревизия"},
    "unit": {"unit", "uom", "ед", "единица", "ед. изм."},
    "position": {"position", "pos", "item", "позиция", "поз"},
    "supplier_code": {"supplier_code", "supplier code", "vendor_code", "код поставщика", "поставщик код"},
    "supplier_name": {"supplier", "supplier_name", "vendor", "поставщик", "наименование поставщика"},
    "unit_cost": {"unit_cost", "price", "unit price", "cost", "цена", "стоимость"},
    "currency": {"currency", "curr", "валюта"},
}


def _column(headers: list[str], names: set[str]) -> str | None:
    mapping = {h.lower().strip(): h for h in headers}
    for n in names:
        if n in mapping:
            return mapping[n]
    return None


def ingest_bom_csv(db: Session, doc: Document, path: Path, *, commit: bool = True) -> int:
    if path.suffix.lower() != ".csv" or not doc.part_number:
        return 0
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(4096); f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except Exception:
            dialect = csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        headers = reader.fieldnames or []
        c_part = _column(headers, ALIASES["child"])
        if not c_part:
            return 0
        c_qty, c_desc, c_rev = _column(headers, ALIASES["qty"]), _column(headers, ALIASES["desc"]), _column(headers, ALIASES["rev"])
        c_unit, c_pos = _column(headers, ALIASES["unit"]), _column(headers, ALIASES["position"])
        c_supplier_code, c_supplier_name = _column(headers, ALIASES["supplier_code"]), _column(headers, ALIASES["supplier_name"])
        c_unit_cost, c_currency = _column(headers, ALIASES["unit_cost"]), _column(headers, ALIASES["currency"])
        db.execute(delete(BOMItem).where(BOMItem.source_document_id == doc.id))
        count = 0
        batch = []
        batch_size = max(1, min(int(getattr(get_settings(), "bulk_ingest_batch_size", 500)), 5000))
        for row in reader:
            child = (row.get(c_part) or "").strip()
            if not child:
                continue
            try:
                qty = float((row.get(c_qty) or "1").replace(",", ".")) if c_qty else 1.0
            except Exception:
                qty = 1.0
            unit_cost = None
            if c_unit_cost:
                raw_cost=(row.get(c_unit_cost) or "").strip().replace(" ", "").replace(",", ".")
                try: unit_cost=float(raw_cost) if raw_cost else None
                except Exception: unit_cost=None
            batch.append({
                "parent_part_number": doc.part_number, "parent_revision": doc.revision, "child_part_number": child.upper(),
                "child_revision": ((row.get(c_rev) or "").strip().upper() or None) if c_rev else None,
                "quantity": qty, "unit": ((row.get(c_unit) or "pcs").strip() or "pcs") if c_unit else "pcs",
                "description": ((row.get(c_desc) or "").strip() or None) if c_desc else None,
                "position": ((row.get(c_pos) or "").strip() or None) if c_pos else None,
                "supplier_code": ((row.get(c_supplier_code) or "").strip() or None) if c_supplier_code else None,
                "supplier_name": ((row.get(c_supplier_name) or "").strip() or None) if c_supplier_name else None,
                "unit_cost": unit_cost, "currency": (((row.get(c_currency) or "").strip().upper() or None) if c_currency else None),
                "source_document_id": doc.id,
            })
            count += 1
            if len(batch) >= batch_size:
                db.execute(insert(BOMItem), batch); batch.clear()
        if batch:
            db.execute(insert(BOMItem), batch)
        if commit:
            db.commit()
        return count
