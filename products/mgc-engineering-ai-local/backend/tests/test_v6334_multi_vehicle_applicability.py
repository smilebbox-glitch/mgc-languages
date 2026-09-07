from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.vehicle_applicability import VEHICLE_CLASSES, merge_vehicle_profile, normalize_vehicle_profile, vehicle_profile
from app.db.models import ConfigurationApplicability, Project, VehicleVariant
from app.db.session import Base
from app.schemas.api import VehicleVariantCreateRequest
from app.services.configuration_management import configuration_workspace, serialize_variant

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src" / "main.tsx"
DEMO = ROOT / "demo" / "seed_demo.py"


def _db() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_supported_vehicle_classes_cover_passenger_and_commercial():
    assert {"passenger_car", "lcv", "truck", "bus", "special_vehicle", "component"} == set(VEHICLE_CLASSES)


def test_vehicle_variant_request_accepts_passenger_and_truck_profiles():
    passenger = VehicleVariantCreateRequest(code="PC-AWD", name="Passenger", vehicle_class="passenger_car", powertrain_type="bev", drivetrain="AWD", wheelbase_mm=2850, battery_kwh=82)
    truck = VehicleVariantCreateRequest(code="TRK-6X4", name="Truck", vehicle_class="truck", powertrain_type="ice", drivetrain="6x4", axle_configuration="6x4", wheelbase_mm=3900, gross_vehicle_weight_t=40, payload_t=20)
    assert passenger.vehicle_class == "passenger_car"
    assert truck.axle_configuration == "6x4"


def test_vehicle_variant_request_rejects_unsupported_class_and_invalid_wheelbase():
    with pytest.raises(Exception):
        VehicleVariantCreateRequest(code="X", name="Invalid", vehicle_class="spaceship")
    with pytest.raises(Exception):
        VehicleVariantCreateRequest(code="X", name="Invalid", vehicle_class="truck", wheelbase_mm=500)


def test_profile_merge_preserves_custom_attributes_and_is_partial_safe():
    merged = merge_vehicle_profile({"customer_program": "MGC-X", "drivetrain": "4x2"}, {"vehicle_class": "truck", "drivetrain": "6x4", "wheelbase_mm": 3900})
    assert merged["customer_program"] == "MGC-X"
    assert merged["vehicle_class"] == "truck"
    assert merged["drivetrain"] == "6x4"
    updated = merge_vehicle_profile(merged, {"wheelbase_mm": 4200}, partial=True)
    assert updated["drivetrain"] == "6x4"
    assert updated["wheelbase_mm"] == 4200


def test_profile_normalization_has_bounded_numeric_ranges():
    out = normalize_vehicle_profile({"vehicle_class": "truck", "gross_vehicle_weight_t": 40, "payload_t": 20, "battery_kwh": None, "wheelbase_mm": 3900})
    assert out["gross_vehicle_weight_t"] == 40.0
    with pytest.raises(ValueError):
        normalize_vehicle_profile({"vehicle_class": "truck", "payload_t": 500})


def test_serializer_exposes_canonical_vehicle_class_and_configuration():
    row = VehicleVariant(project_code="P", code="TRK", name="Truck", attributes_json={"vehicle_class":"truck","axle_configuration":"6x4","wheelbase_mm":3900,"plant":"Kaluga"})
    out = serialize_variant(row, set())
    assert out["vehicle_class"] == "truck"
    assert out["configuration"]["axle_configuration"] == "6x4"
    assert out["configuration"]["wheelbase_mm"] == 3900


def test_configuration_workspace_reports_multi_vehicle_scope_without_new_authority():
    db = _db()
    db.add(Project(code="MV", name="Multi Vehicle", acl_groups=["all"]))
    pc = VehicleVariant(project_code="MV", code="PC", name="Passenger", status="active", attributes_json={"vehicle_class":"passenger_car"})
    tr = VehicleVariant(project_code="MV", code="TRK", name="Truck", status="active", attributes_json={"vehicle_class":"truck","axle_configuration":"6x4"})
    db.add_all([pc,tr]); db.commit(); db.refresh(pc); db.refresh(tr)
    db.add_all([
        ConfigurationApplicability(project_code="MV", variant_id=pc.id, entity_type="part", entity_key="P1", applicability="included"),
        ConfigurationApplicability(project_code="MV", variant_id=tr.id, entity_type="part", entity_key="P2", applicability="included"),
    ]); db.commit()
    out = configuration_workspace(db,"MV",set(),{"P1","P2"})
    assert out["vehicle_scope"]["multi_vehicle"] is True
    assert out["vehicle_scope"]["class_counts"]["passenger_car"] == 1
    assert out["vehicle_scope"]["class_counts"]["truck"] == 1
    assert out["advisory_only"] is True
    assert out["unknown_is_not_included"] is True


def test_frontend_exposes_vehicle_class_and_truck_configuration_without_new_primary_workspace():
    source = FRONTEND.read_text()
    for marker in ["Легковой автомобиль", "Грузовой автомобиль", "Колёсная база, мм", "6x4", "GVW, т", "Payload, т", "Тип кабины"]:
        assert marker in source
    assert "Passenger и Commercial Vehicles используют один Digital Thread" in source


def test_demo_contains_passenger_and_truck_programs():
    source = DEMO.read_text()
    assert "DEMO-PASSENGER" in source
    assert "DEMO-TRUCK" in source
    assert "PC-BEV-AWD" in source
    assert "TRK-6X4-D13-AMT" in source
    assert "6300012345" in source


def test_v6334_requires_no_database_migration_for_multi_vehicle_profile():
    migrations = ROOT / "backend" / "app" / "db" / "migrations" / "versions"
    assert not list(migrations.glob("*6.3.34*")) if migrations.exists() else True
