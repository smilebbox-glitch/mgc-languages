from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static/frontend/digital_vehicle_3d_v630.js").read_text(encoding="utf-8")
CSS = (ROOT / "static/digital_vehicle_3d_v630.css").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")


def test_assets_are_wired_after_art_direction():
    assert '/digital_vehicle_3d_v630.css' in INDEX
    assert '/frontend/digital_vehicle_3d_v630.js' in INDEX
    assert INDEX.index('/art_direction_v630.css') < INDEX.index('/digital_vehicle_3d_v630.css')
    assert INDEX.index('/frontend/art_direction_v630.js') < INDEX.index('/frontend/digital_vehicle_3d_v630.js')


def test_real_local_webgl_renderer_exists():
    assert "digital-vehicle-3d-v630" in JS
    assert "getContext('webgl'" in JS
    assert "powerPreference:'low-power'" in JS
    assert "VERTEX_SHADER" in JS
    assert "FRAGMENT_SHADER" in JS
    assert "drawElements" in JS
    assert "lookAt" in JS
    assert "perspective" in JS
    assert "pointermove" in JS


def test_eight_learning_zones_have_chinese_and_pinyin():
    expected = {
        'bumper': ('前保险杠', 'qián bǎoxiǎnggàng'),
        'hood': ('发动机盖', 'fādòngjī gài'),
        'windshield': ('挡风玻璃', 'dǎngfēng bōli'),
        'mirror': ('后视镜', 'hòushìjìng'),
        'door': ('车门', 'chēmén'),
        'fender': ('前翼子板', 'qián yìzǐbǎn'),
        'headlamp': ('前照灯', 'qiánzhàodēng'),
        'wheel': ('车轮', 'chēlún'),
    }
    order_match = re.search(r"const ORDER=\[(.*?)\];", JS)
    assert order_match
    order = re.findall(r"'([^']+)'", order_match.group(1))
    assert order == list(expected)
    assert len(order) == len(set(order)) == 8
    for zone, (hanzi, pinyin) in expected.items():
        assert f"{zone}:{{" in JS
        assert f"zh:'{hanzi}'" in JS
        assert f"py:'{pinyin}'" in JS


def test_hotspot_delegates_to_canonical_game_lab_control():
    assert "data-hotspot-zone" in JS
    assert "native.click()" in JS
    assert "interactive:true,scope:stage" in JS
    # The 3D layer must not own the canonical answer/scoring path.
    for forbidden in (
        "submitAnswer(",
        "/api/games/",
        "fetch(",
        "spendable_xp",
        "awarded_xp",
        "MAX_GAME_ANSWERS",
    ):
        assert forbidden not in JS


def test_assembly_and_quality_are_context_layers_only():
    assert ".game-stage.kind-order" in JS
    assert ".game-stage.kind-quality-gate,.game-stage.kind-spec" in JS
    assert "Последовательность остаётся канонической" in JS
    assert "Ответ выбирается в стандартном Quality Gate" in JS
    assert "highlight:'wheel'" not in JS  # highlight comes through contextPanel, not a parallel answer.
    assert "contextPanel('assembly','wheel')" in JS
    assert "contextPanel('quality','door')" in JS


def test_language_surface_keeps_russian_ui_and_chinese_learning_content():
    assert "s.language==='chinese'" in JS
    assert "УЧЕБНЫЙ ОБЪЕКТ" in JS
    assert "Поверните автомобиль мышкой или пальцем" in JS
    assert "Сборочная операция" in JS
    assert "Контроль качества" in JS


def test_safe_fallback_and_performance_controls():
    assert "WebGL unavailable" in JS
    assert "stage.classList.remove('dv3d-enabled')" in JS
    assert "Math.min(root.devicePixelRatio||1,1.75)" in JS
    assert "IntersectionObserver" in JS
    assert "ResizeObserver" in JS
    assert "powerPreference:'low-power'" in JS


def test_no_external_runtime_assets_or_cdn_dependencies():
    combined = JS + '\n' + CSS
    assert not re.search(r"https?://", combined, re.I)
    assert "data:image" not in combined.lower()
    assert "@import" not in CSS.lower()
    assert "three.js" not in combined.lower()
    assert "three.min" not in combined.lower()


def test_mobile_accessibility_and_reduced_motion_contract():
    assert "@media(max-width:900px)" in CSS
    assert "@media(max-width:600px)" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert ":focus-visible" in CSS
    assert "touch-action:none" in CSS


if __name__ == '__main__':
    tests = [value for name, value in sorted(globals().items()) if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
    print(f"Digital Vehicle 3D regression: {len(tests)} checks passed")
