from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    css_path = ROOT / "static" / "executive_visual_v630.css"
    polish_path = ROOT / "static" / "executive_polish_v630.css"
    index_path = ROOT / "static" / "index.html"
    manifest_path = ROOT / "RELEASE_MANIFEST_v6.0.30.json"
    changelog_path = ROOT / "CHANGELOG_v6.0.30.md"

    require(css_path.exists(), "Executive visual stylesheet is missing")
    require(polish_path.exists(), "Executive polish stylesheet is missing")
    css = css_path.read_text(encoding="utf-8")
    polish = polish_path.read_text(encoding="utf-8")
    index = index_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changelog = changelog_path.read_text(encoding="utf-8")

    require('/executive_visual_v630.css' in index, "Executive stylesheet is not loaded")
    require('/executive_polish_v630.css' in index, "Executive polish stylesheet is not loaded")
    require(index.index('/executive_visual_v630.css') > index.index('/factory_journey_v2_v630.css'),
            "Executive stylesheet must load after product/module styles")
    require(index.index('/executive_polish_v630.css') > index.index('/executive_visual_v630.css'),
            "Executive polish must load after executive visual base")

    required_tokens = [
        '--ev-bg', '--ev-surface', '--ev-ink', '--ev-blue', '--ev-cyan',
        '--ev-shadow', '--ev-shadow-deep', '--ev-radius-lg'
    ]
    for token in required_tokens:
        require(token in css, f"Executive design token missing: {token}")

    required_surfaces = [
        '.topbar', '.sidebar', '.auth-shell', '.pilot-hero', '.pilot-panel',
        '.topic-card', '.term-card', '.question-card', '.game-lab-card',
        '.game-session-shell', '.arcade-mastery-v620', '.factory-journey-v2-v630'
    ]
    for selector in required_surfaces:
        require(selector in css, f"Executive surface styling missing: {selector}")

    require('@media(prefers-reduced-motion:reduce)' in css,
            "Reduced-motion contract missing from executive visual layer")
    require('@media(max-width:820px)' in css and '@media(max-width:560px)' in css,
            "Mobile executive visual breakpoints are missing")
    require(':focus-visible' in css, "Keyboard focus treatment is missing")
    require('url(' not in css, "Executive visual layer must not introduce external/image asset dependencies")

    contract = manifest.get('executive_visual_system') or {}
    require(contract.get('presentation_only') is True, "Executive layer must remain presentation-only")
    require(contract.get('asset') == 'static/executive_visual_v630.css', "Executive base asset contract drifted")
    require(contract.get('polish_asset') == 'static/executive_polish_v630.css', "Executive polish asset contract drifted")
    require(contract.get('load_order') == 'after-product-module-styles', "Executive base load-order contract drifted")
    require(contract.get('polish_load_order') == 'after-executive-visual', "Executive polish load-order contract drifted")
    require(contract.get('runtime_js') is False, "Executive visual layer must stay CSS-only")
    require(contract.get('api_contract') == 'unchanged', "Executive visual layer must not change API")
    require(contract.get('xp_scoring') == 'unchanged', "Executive visual layer must not change XP/scoring")
    require(contract.get('database') == 'unchanged', "Executive visual layer must not change database")
    require(contract.get('reduced_motion') is True and contract.get('mobile_adaptive') is True,
            "Executive accessibility/responsive contract drifted")
    require('static/executive_visual_v630.css' in manifest['game_world']['assets'],
            "Executive stylesheet missing from release assets")
    require('static/executive_polish_v630.css' in manifest['game_world']['assets'],
            "Executive polish stylesheet missing from release assets")
    require('static/executive_visual_v630.css' in manifest['critical_files'],
            "Executive stylesheet missing from critical files")
    require('static/executive_polish_v630.css' in manifest['critical_files'],
            "Executive polish stylesheet missing from critical files")
    require('Executive Visual System' in changelog, "Executive visual changelog section missing")

    forbidden = ['fetch(', '/api/', 'submitAnswer(', 'awarded_xp', 'spendable_xp']
    for layer_name, layer in (("base", css), ("polish", polish)):
        for marker in forbidden:
            require(marker not in layer, f"CSS-only executive {layer_name} layer contains runtime marker: {marker}")

    print('v6.0.30 Executive Visual System regression: OK')


if __name__ == '__main__':
    main()
