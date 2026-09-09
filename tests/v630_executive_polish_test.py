from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    index = (ROOT / "static/index.html").read_text(encoding="utf-8")
    base = (ROOT / "static/executive_visual_v630.css").read_text(encoding="utf-8")
    polish = (ROOT / "static/executive_polish_v630.css").read_text(encoding="utf-8")

    base_ref = '/executive_visual_v630.css'
    polish_ref = '/executive_polish_v630.css'
    require(base_ref in index, "Executive visual base stylesheet is missing")
    require(polish_ref in index, "Executive polish stylesheet is missing")
    require(index.index(base_ref) < index.index(polish_ref), "Executive polish must load after executive visual base")

    for marker in (
        ".pilot-hero",
        ".pilot-panel:hover",
        ".topic-card:before",
        ".flashcard:before",
        ".game-lab-card:after",
        ".game-session-shell",
        ".arcade-mastery-v620",
        ".factory-journey-v2-v630",
        ".fj2-car:after",
        "@media(max-width:820px)",
        "@media(max-width:560px)",
        "@media(prefers-reduced-motion:reduce)",
    ):
        require(marker in polish, f"Executive polish coverage marker missing: {marker}")

    for animation in ("exec2Reveal", "exec2Sheen", "exec2Scan"):
        require(animation in polish, f"Executive polish motion marker missing: {animation}")

    require("executive" in base.lower(), "Executive visual base identity missing")
    require("Presentation only" in polish, "Executive polish must declare presentation-only contract")
    require("@import" not in polish, "Executive polish must not import external styles")
    require("http://" not in polish and "https://" not in polish, "Executive polish must not depend on external assets")
    require("url(" not in polish, "Executive polish Stage 2 must remain self-contained")
    require("fetch(" not in polish, "CSS presentation layer must never own API calls")
    require("/api/" not in polish, "CSS presentation layer must never reference API paths")

    print("v6.0.30 Executive Polish Stage 2 regression: OK")


if __name__ == "__main__":
    main()
