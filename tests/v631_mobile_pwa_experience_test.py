from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")
CSS = (STATIC / "mobile_experience_v631.css").read_text(encoding="utf-8")
JS = (STATIC / "frontend/mobile_experience_v631.js").read_text(encoding="utf-8")
PWA = (STATIC / "pwa-register.js").read_text(encoding="utf-8")
SW = (STATIC / "service-worker.js").read_text(encoding="utf-8")
MANIFEST = json.loads((STATIC / "manifest.webmanifest").read_text(encoding="utf-8"))


def test_mobile_assets_are_wired_after_product_styles_and_before_pwa_registration():
    assert '<link rel="stylesheet" href="/mobile_experience_v631.css">' in INDEX
    assert '<script src="/frontend/mobile_experience_v631.js" defer></script>' in INDEX
    assert INDEX.index('/mobile_experience_v631.css') > INDEX.index('/factory_digital_thread_v630.css')
    assert INDEX.index('/frontend/mobile_experience_v631.js') < INDEX.index('/pwa-register.js')
    assert 'viewport-fit=cover' in INDEX
    assert 'apple-mobile-web-app-capable' in INDEX


def test_phone_layout_has_safe_area_touch_and_dynamic_viewport_contracts():
    for token in (
        'env(safe-area-inset-top', 'env(safe-area-inset-bottom', '100dvh',
        '@media (max-width:900px)', '(pointer:coarse)', 'min-height:44px',
        '.mgc-mobile-dock', '.mgc-keyboard-open', '.mgc-sim-focus',
        '@media (orientation:landscape)'
    ):
        assert token in CSS


def test_factory_and_3d_surfaces_are_explicitly_mobile_adapted():
    for token in (
        '.ab-shell', '.ptb-shell', '.fps-shell', '.f2-shell', '.fti-shell', '.fdt-shell',
        '.ab-layout', '.ptb-layout', '.fps-layout', '.f2-layout', '.fti-layout', '.fdt-layout',
        '.fti-kpis', '.f2-map', '.fps-route', '.fdt-route'
    ):
        assert token in CSS
    assert 'Режим тренажёра' in JS
    assert 'Для 3D-сцен удобнее альбомная ориентация' in JS
    assert "SIM_SELECTOR='.ab-shell,.ptb-shell,.fps-shell,.f2-shell,.fti-shell,.fdt-shell'" in JS


def test_mobile_navigation_install_and_network_states_exist():
    for token in (
        'mgcMobileDock', 'Главная', 'Темы', 'Игры', 'Сценарии',
        'beforeinstallprompt', 'appinstalled', 'Добавить MGC на iPhone',
        'navigator.onLine', 'visualViewport', 'mgc:pwa-update'
    ):
        assert token in JS
    assert "navigator.standalone===true" in JS
    assert "URLSearchParams(root.location.search)" in JS


def test_mobile_accessibility_and_focus_recovery_are_hardened():
    for token in (
        "aria-current','page'", 'aria-labelledby="mgcMobileSheetTitle"',
        'tabindex="-1"', 'aria-pressed="false"', "b.setAttribute('aria-pressed','true')",
        "e.key!=='Escape'", 'resetFocusMode()', 'closeSheet()',
        "doc.visibilityState==='visible'"
    ):
        assert token in JS
    assert 'lastDialogFocus=doc.activeElement' in JS
    assert 'lastDialogFocus.focus()' in JS
    assert "frontend.register('mobile-web-v631',{install,setViewport,scanScenes,proxyView,resetFocusMode,closeSheet})" in JS


def test_manifest_has_pwa_shortcuts_without_changing_install_identity():
    assert MANIFEST['name'] == 'MGC Language Lab'
    assert MANIFEST['id'] == '/'
    assert MANIFEST['start_url'] == '/'
    assert MANIFEST['scope'] == '/'
    assert MANIFEST['display'] == 'standalone'
    assert MANIFEST['display_override'][:2] == ['window-controls-overlay', 'standalone']
    assert MANIFEST['launch_handler']['client_mode'] == 'navigate-existing'
    urls = {item['url'] for item in MANIFEST['shortcuts']}
    assert {'/?view=games', '/?view=topics', '/?view=roleplay'} <= urls


def test_service_worker_precaches_only_public_mobile_shell_assets_and_remains_private_data_safe():
    assert "mgc-language-static-v631-mobile" in SW
    assert "'/mobile_experience_v631.css'" in SW
    assert "'/frontend/mobile_experience_v631.js'" in SW
    assert "request.headers.has('authorization')" in SW
    assert "request.headers.has('cookie')" in SW
    assert "request.headers.has('range')" in SW
    assert "cacheControl.includes('no-store')" in SW
    assert "cacheControl.includes('private')" in SW
    assert "response.headers.has('set-cookie')" in SW
    assert "isCacheableStaticResponse(response)" in SW
    assert "request.mode === 'navigate'" in SW
    assert "fetch(request, {cache: 'no-store'})" in SW
    assert "'/index.html'" not in SW
    assert "'/app'" not in SW


def test_pwa_update_lifecycle_and_ios_standalone_detection_are_present():
    assert "navigator.standalone === true" in PWA
    assert "(display-mode: window-controls-overlay)" in PWA
    assert "registration.addEventListener('updatefound'" in PWA
    assert "navigator.serviceWorker.addEventListener('controllerchange'" in PWA
    assert "emit('mgc:pwa-update'" in PWA
    assert "updateViaCache: 'none'" in PWA


def test_mobile_layer_does_not_own_scoring_xp_or_network_calls():
    forbidden = (
        'submitAnswer(', '/api/games/', 'fetch(', 'spendable_xp', 'awarded_xp',
        'MAX_GAME_ANSWERS =', 'Three.', 'three.js', 'https://', 'http://'
    )
    for token in forbidden:
        assert token not in JS
    assert "frontend.register('mobile-web-v631'" in JS
    assert 'no API, XP, scoring' in JS
