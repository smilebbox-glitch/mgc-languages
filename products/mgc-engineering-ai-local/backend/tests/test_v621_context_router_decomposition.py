from pathlib import Path
import ast

from app.core.runtime_contract import APP_VERSION, SCHEMA_VERSION, PROFILE_FEATURES, active_bounded_contexts

ROOT=Path(__file__).resolve().parents[2]
CONTEXTS=ROOT/'backend/app/api/contexts'


def _route_count(path:Path)->int:
    tree=ast.parse(path.read_text())
    total=0
    for n in tree.body:
        if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and isinstance(d.func.value,ast.Name) and d.func.value.id=='router':
                total += 1
    return total


def test_patch_release_keeps_v620_database_schema():
    assert APP_VERSION == '6.3.34'
    assert SCHEMA_VERSION == '6.3.13'


def test_core_mounts_lexical_intelligence_but_not_supplier_field():
    contexts=active_bounded_contexts(PROFILE_FEATURES['core'])
    assert 'intelligence_search' in contexts
    assert 'supplier_field' not in contexts


def test_advanced_mounts_all_six_contexts():
    assert active_bounded_contexts(PROFILE_FEATURES['advanced']) == [
        'engineering_core','configuration_change','manufacturing_quality',
        'supplier_field','intelligence_search','platform_operations'
    ]


def test_legacy_route_monolith_is_physically_decomposed():
    expected={'engineering_core':54,'configuration_change':53,'manufacturing_quality':53,'supplier_field':22,'intelligence_search':20,'platform_operations':45}
    assert {k:_route_count(CONTEXTS/f'{k}.py') for k in expected} == expected
    assert sum(expected.values()) == 247
    assert len((ROOT/'backend/app/api/routes.py').read_text().splitlines()) <= 40
