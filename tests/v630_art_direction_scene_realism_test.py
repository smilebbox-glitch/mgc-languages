from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    base_js_path = ROOT / "static" / "frontend" / "art_direction_v630.js"
    scene_js_path = ROOT / "static" / "frontend" / "art_direction_scenes_v630.js"
    scene_css_path = ROOT / "static" / "art_direction_scenes_v630.css"

    require(base_js_path.exists(), "Art Direction base JS is missing")
    require(scene_js_path.exists(), "Scene Realism JS is missing")
    require(scene_css_path.exists(), "Scene Realism CSS is missing")

    base_js = base_js_path.read_text(encoding="utf-8")
    scene_js = scene_js_path.read_text(encoding="utf-8")
    scene_css = scene_css_path.read_text(encoding="utf-8")

    require("loadSceneRealismAssets" in base_js, "Art Direction base does not load Scene Realism")
    require("/art_direction_scenes_v630.css" in base_js, "Scene Realism CSS path is missing")
    require("/frontend/art_direction_scenes_v630.js" in base_js, "Scene Realism JS path is missing")

    scenes = ["assembly", "welding", "paint", "logistics", "quality", "engineering"]
    for scene in scenes:
        require(f"id:'{scene}'" in scene_js, f"Production Theatre scene missing: {scene}")
        require(f"ad2-env-{scene}" in scene_css, f"Scene environment CSS missing: {scene}")

    require("'ad2-theatre-'+scene" in scene_js,
            "Production Theatre must derive scene classes from the canonical scene id")

    js_markers = [
        "frontend.register('art-direction-scenes-v630'",
        "decorateProductionScenes",
        "markKeyScreens",
        "mgcProductionTheatre",
        "Показать производственные сцены",
        "data-ad2-scene",
        "MGC AUTOMOTIVE LEARNING",
        "MutationObserver",
    ]
    for marker in js_markers:
        require(marker in scene_js, f"Scene Realism JS marker missing: {marker}")

    css_markers = [
        ".ad2-scene-brand",
        ".ad2-mgc-mark",
        ".ad2-theatre",
        ".ad2-theatre-tabs",
        ".ad2-theatre-stage",
        ".ad2-cmm-bridge",
        ".ad2-safety-fence",
        ".ad2-spray-rail",
        ".ad2-agv",
        ".ad2-cad-wall",
        "@media(prefers-reduced-motion:reduce)",
    ]
    for marker in css_markers:
        require(marker in scene_css, f"Scene Realism CSS marker missing: {marker}")

    # Visual layer must never become a second gameplay/runtime implementation.
    forbidden_js = [
        "fetch(", "/api/", "submitAnswer(", "awarded_xp", "spendable_xp",
        "MAX_GAME_ANSWERS", "localStorage.setItem(", "sessionStorage.setItem("
    ]
    for marker in forbidden_js:
        require(marker not in scene_js, f"Scene Realism contains runtime marker: {marker}")

    # No third-party images/fonts/CDNs; scene realism is local DOM/CSS geometry only.
    require("http://" not in scene_js and "https://" not in scene_js,
            "Scene Realism JS must stay local")
    require("http://" not in scene_css and "https://" not in scene_css,
            "Scene Realism CSS must stay local")
    require("url(data:" not in scene_css, "Scene Realism CSS must not embed data-URI assets")

    # Atmosphere must not capture answer clicks.
    require("pointer-events:none" in scene_css,
            "Scene environment must remain non-interactive beneath canonical answer controls")

    require("@media(max-width:960px)" in scene_css and "@media(max-width:700px)" in scene_css,
            "Scene Realism responsive breakpoints are missing")

    print("v6.0.30 Art Direction Scene Realism regression: OK")


if __name__ == "__main__":
    main()
