from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static/frontend/digital_truck_3d_v630.js").read_text(encoding="utf-8")
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")


def test_truck_asset_is_wired_after_passenger_vehicle():
    car = '/frontend/digital_vehicle_3d_v630.js'
    truck = '/frontend/digital_truck_3d_v630.js'
    assert car in INDEX and truck in INDEX
    assert INDEX.index(car) < INDEX.index(truck)


def test_generic_shacman_class_reference_without_brand_assets():
    assert "SHACMAN-class reference" in JS
    assert "без логотипа" in JS
    assert "Generic Chinese heavy tractor architecture" in JS
    assert "logo" not in JS.lower().replace("logos", "")


def test_real_local_webgl_heavy_truck_renderer_exists():
    assert "digital-truck-3d-v630" in JS
    assert "getContext('webgl'" in JS
    assert "powerPreference:'low-power'" in JS
    assert "TRUCK_PARTS" in JS
    assert "drawElements" in JS
    assert "pointermove" in JS


def test_eight_truck_learning_zones_have_chinese_and_pinyin():
    expected = {
        'cab': ('驾驶室', 'jiàshǐshì'),
        'grille': ('散热器格栅', 'sànrèqì géshān'),
        'bumper': ('前保险杠', 'qián bǎoxiǎnggàng'),
        'headlamp': ('前照灯', 'qiánzhàodēng'),
        'fuel_tank': ('燃油箱', 'rányóuxiāng'),
        'fifth_wheel': ('第五轮', 'dìwǔlún'),
        'drive_axle': ('驱动桥', 'qūdòngqiáo'),
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


def test_showcase_gets_passenger_and_heavy_vehicle_switching():
    assert "Легковой автомобиль · 3D" in JS
    assert "Грузовик класса SHACMAN · 3D" in JS
    assert "carHost.classList.remove('active')" in JS
    assert "dv3d-truck-host" in JS


def test_truck_layer_is_presentation_only():
    for forbidden in (
        "submitAnswer(",
        "/api/games/",
        "fetch(",
        "spendable_xp",
        "awarded_xp",
        "MAX_GAME_ANSWERS",
        "data-hotspot-zone",
    ):
        assert forbidden not in JS


def test_no_external_assets_or_cdn_runtime():
    assert not re.search(r"https?://", JS, re.I)
    assert "data:image" not in JS.lower()
    assert "three.js" not in JS.lower()
    assert "three.min" not in JS.lower()


if __name__ == '__main__':
    tests = [value for name, value in sorted(globals().items()) if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
    print(f"Digital Truck 3D regression: {len(tests)} checks passed")
