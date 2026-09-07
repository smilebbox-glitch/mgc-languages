from app.services.native_cad import (
    gateway_config_supports,
    native_cad_metadata,
    native_cad_profile,
    preferred_conversion_target,
)


def test_kompas_native_formats_are_classified():
    assert native_cad_profile('.m3d').product == 'КОМПАС-3D'
    assert native_cad_profile('.m3d').document_kind == 'model'
    assert preferred_conversion_target('.m3d') == 'step'
    assert native_cad_profile('.a3d').document_kind == 'assembly'
    assert native_cad_profile('.t3d').document_kind == 'technology_assembly'
    assert native_cad_profile('.cdw').document_kind == 'drawing'
    assert preferred_conversion_target('.cdw') == 'pdf'
    assert native_cad_profile('.spw').document_kind == 'specification'
    assert native_cad_profile('.kdw').document_kind == 'text_document'


def test_tflex_grb_keeps_auto_target_for_gateway_inspection():
    p = native_cad_profile('.grb')
    assert p.product == 'T-FLEX CAD'
    assert p.document_kind == 'mixed'
    assert p.preferred_target == 'auto'
    assert {'step', 'pdf', 'dxf'}.issubset(set(p.alternate_targets))


def test_native_metadata_is_explainable():
    meta = native_cad_metadata('.cdw')
    assert meta['native_cad'] is True
    assert meta['conversion_required'] is True
    assert meta['vendor'] == 'kompas'
    assert meta['preferred_target'] == 'pdf'


def test_vendor_gateway_matching_is_strict_when_declared():
    kompas = {'vendor': 'kompas', 'extensions': ['.m3d', '.a3d', '.cdw']}
    tflex = {'vendor': 'tflex', 'extensions': ['.grb']}
    assert gateway_config_supports(kompas, '.m3d')
    assert not gateway_config_supports(kompas, '.grb')
    assert gateway_config_supports(tflex, '.grb')
    assert not gateway_config_supports(tflex, '.cdw')
