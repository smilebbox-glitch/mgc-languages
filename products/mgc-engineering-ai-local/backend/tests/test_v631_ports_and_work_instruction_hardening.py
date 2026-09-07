from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.registry import (
    get_ai_analysis_port,
    get_graph_projection_port,
    get_object_storage_port,
    get_search_port,
    get_translation_provider_port,
)
from app.core.config import Settings
from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, runtime_contract
from app.core.security import Identity
from app.db import models  # noqa: F401
from app.db.models import Project, WorkInstruction
from app.db.session import Base
from app.ports.translation import TranslationBatch
from app.schemas.api import WorkInstructionUpdateRequest
from app.services.engineering_translation import translate_texts
from app.services.work_instructions import (
    current_translation_fingerprint,
    instruction_translation_fingerprint,
    translation_is_current,
)
from app.api.contexts.manufacturing_quality import update_work_instruction


def _db():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return sessionmaker(bind=eng)()


def test_v631_runtime_uses_ports_and_keeps_v630_schema():
    assert APP_VERSION == "6.3.34"
    assert SCHEMA_VERSION == "6.3.13"
    cfg = Settings(deployment_profile="core")
    out = runtime_contract(cfg)
    assert out["governance"]["dependency_inversion"] is True
    assert out["adapters"]["architecture"] == "ports_and_adapters"
    assert out["adapters"]["search"]["adapter"] == "core_lexical_postgres"
    assert out["adapters"]["graph"]["adapter"] == "disabled"
    assert out["adapters"]["object_storage"]["adapter"] == "local_evidence_only"
    assert out["adapters"]["ai_analysis"]["available"] is False


def test_profile_registry_selects_interfaces_without_instantiating_concrete_clients():
    core = Settings(deployment_profile="core")
    assert get_search_port(core).mode == "core_lexical_postgres"
    assert get_graph_projection_port(core).mode == "disabled"
    assert get_object_storage_port(core).mode == "local_evidence_only"
    assert get_ai_analysis_port(core).mode == "disabled"
    assert get_translation_provider_port(core).mode == "disabled"


class _FakeTranslationPort:
    mode = "test_translation_adapter"
    available = True

    async def translate_items(self, items: list[dict], target_language: str) -> TranslationBatch:
        return TranslationBatch(
            {str(x["id"]): f"Перевод {x['text']}" for x in items},
            "test-model",
            self.mode,
        )


@pytest.mark.asyncio
async def test_translation_application_service_accepts_injected_provider_port():
    db = _db()
    result = await translate_texts(
        db,
        ["Install PN-123 bracket 25 Nm"],
        project_code="P1",
        manufacturing_area="assembly",
        scope="work_instruction",
        target_language="ru",
        source_language="en",
        user="tester",
        translation_port=_FakeTranslationPort(),
    )
    assert result[0]["provider"] == "test-model"
    assert result[0]["translation"].startswith("Перевод")
    assert result[0]["warnings"] == []


def test_translation_fingerprint_detects_changed_foreign_source():
    wi = WorkInstruction(
        project_code="P1", manufacturing_area="assembly", code="WI-CN", title="CN",
        source_language="zh", translation_status="reviewed", original_text="安装支架",
        steps_json=[{"sequence": 10, "text": "安装支架"}], metadata_json={},
    )
    fp = current_translation_fingerprint(wi)
    wi.metadata_json = {"translation_source_fingerprint": fp}
    assert translation_is_current(wi) is True
    assert fp == instruction_translation_fingerprint(wi.original_text, wi.steps_json)
    wi.original_text = "安装前保险杠"
    assert translation_is_current(wi) is False


def test_editing_foreign_source_marks_reviewed_translation_stale():
    db = _db()
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-admins"]))
    wi = WorkInstruction(
        project_code="P1", manufacturing_area="assembly", code="WI-CN", title="CN",
        source_language="zh", translation_status="reviewed", original_text="安装支架",
        translated_text_ru="Установить кронштейн", steps_json=[{"sequence": 10, "text": "安装支架"}],
        metadata_json={}, status="draft",
    )
    db.add(wi); db.flush()
    wi.metadata_json = {"translation_source_fingerprint": current_translation_fingerprint(wi)}
    db.commit(); db.refresh(wi)

    out = update_work_instruction(
        "P1", wi.id, WorkInstructionUpdateRequest(original_text="安装前保险杠"),
        Identity("admin", ["engineering-ai-admins"]), db,
    )
    assert out["translation_status"] == "stale"
    assert out["metadata"]["translation_stale"] is True


def test_approved_work_instruction_is_immutable_except_obsolete_transition():
    db = _db()
    db.add(Project(code="P1", name="Car", acl_groups=["engineering-ai-admins"]))
    wi = WorkInstruction(
        project_code="P1", manufacturing_area="assembly", code="WI-RU", title="Approved",
        source_language="ru", translation_status="not_required", original_text="Установить деталь",
        steps_json=[{"sequence": 10, "text": "Установить деталь"}], status="approved",
    )
    db.add(wi); db.commit(); db.refresh(wi)
    with pytest.raises(HTTPException) as exc:
        update_work_instruction(
            "P1", wi.id, WorkInstructionUpdateRequest(title="Changed after approval"),
            Identity("admin", ["engineering-ai-admins"]), db,
        )
    assert exc.value.status_code == 409

    out = update_work_instruction(
        "P1", wi.id, WorkInstructionUpdateRequest(status="obsolete"),
        Identity("admin", ["engineering-ai-admins"]), db,
    )
    assert out["status"] == "obsolete"
