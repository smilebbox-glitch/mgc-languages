from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    css_path = ROOT / "static" / "art_direction_v630.css"
    js_path = ROOT / "static" / "frontend" / "art_direction_v630.js"
    index_path = ROOT / "static" / "index.html"

    require(css_path.exists(), "Art Direction CSS is missing")
    require(js_path.exists(), "Art Direction JS is missing")

    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    index = index_path.read_text(encoding="utf-8")

    require('/art_direction_v630.css' in index, "Art Direction CSS is not loaded")
    require('/frontend/art_direction_v630.js' in index, "Art Direction JS is not loaded")
    require(index.index('/art_direction_v630.css') > index.index('/executive_polish_v630.css'),
            "Art Direction CSS must load after Executive Polish")
    require(index.index('/frontend/art_direction_v630.js') > index.index('/frontend/chinese_learning_surface_v630.js'),
            "Art Direction JS must load after Chinese learning presentation layer")

    css_markers = [
        '.mgc-showcase', '.mgc-showcase-slide', '.mgc-showcase-trigger',
        '.mgc-hero-visual', '.mgc-art-car-overlay', '.mgc-showcase-car',
        '.mgc-showcase-kpi', '.mgc-showcase-process', '@media(prefers-reduced-motion:reduce)'
    ]
    for marker in css_markers:
        require(marker in css, f"Art Direction CSS marker missing: {marker}")

    js_markers = [
        "frontend.register('art-direction-v630'", "CAR_SVG", 'vehicle-shell',
        'injectHeroVisual', 'injectJourneyVehicle', 'mgcExecutiveShowcase',
        'data-ad-slide="0"', 'data-ad-slide="3"', 'Factory Journey 2.0',
        '语言连接人与技术', 'yǔyán liánjiē rén yǔ jìshù',
        "ArrowRight", "ArrowLeft", "Escape", "MutationObserver"
    ]
    for marker in js_markers:
        require(marker in js, f"Art Direction JS marker missing: {marker}")

    # Boardroom mode must stay presentation-only and never become a second product runtime.
    forbidden = [
        'fetch(', '/api/', 'submitAnswer(', 'awarded_xp', 'spendable_xp',
        'MAX_GAME_ANSWERS', 'localStorage.setItem(', 'sessionStorage.setItem('
    ]
    for marker in forbidden:
        require(marker not in js, f"Presentation-only showcase contains runtime marker: {marker}")

    # No external web/image/font dependencies; all showcase art is SVG/CSS shipped with the product.
    require('http://' not in css and 'https://' not in css, "Art Direction CSS must stay local")
    require('url(' not in css, "Art Direction CSS must not add external/background image dependencies")
    require('http://' not in js and 'https://' not in js, "Art Direction JS must stay local")
    require('<svg' in js and '<path' in js and '<circle' in js,
            "Realistic digital vehicle must be represented as local SVG geometry")

    # Russian interface + Chinese/pinyin learning example remains explicit in the presentation.
    require('Презентация' in js and 'Закрыть' in js and 'Ценность' in js,
            "Executive showcase controls must be Russian")
    require('扭矩' in js and 'niǔjǔ' in js and 'крутящий момент' in js,
            "Chinese showcase learning example must include hanzi + pinyin + Russian meaning")

    require('@media(max-width:760px)' in css and '@media(max-width:560px)' in css,
            "Art Direction mobile breakpoints are missing")

    print('v6.0.30 Art Direction / Executive Showcase regression: OK')


if __name__ == '__main__':
    main()
