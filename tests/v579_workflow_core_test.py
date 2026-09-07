from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mgc.services.practice_games import (  # noqa: E402
    chunk_chinese,
    practice_raw_xp,
    score_game_answers,
)

assert practice_raw_xp("quiz", 5, 5) == 40
assert practice_raw_xp("quiz", 9, 10) == 30
assert practice_raw_xp("quiz", 8, 10) == 20
assert practice_raw_xp("scenario", 3, 5) == 15
assert practice_raw_xp("pair", 0, 1) == 1
assert practice_raw_xp("pair", 1, 1) == 5
assert practice_raw_xp("course_day", 5, 5) == 35
assert practice_raw_xp("tone_lab", 5, 5) == 25
assert practice_raw_xp("exam", 6, 10) == 25
assert practice_raw_xp("exam", 7, 10) == 100
assert practice_raw_xp("exam", 9, 10) == 150

assert chunk_chinese("检查焊点质量") == ["检查", "焊点", "质量"]
assert chunk_chinese("你好 世界") == ["你好", "世界"]

assert score_game_answers(["a", "b", "c"], ["a", "x", "c"]) == 2
assert score_game_answers([["请", "检查"], 2], [["请", "检查"], 2]) == 2
assert score_game_answers([1, 2, 3], [1]) == 1

assert "app" not in sys.modules
print("OK: v5.7.9 workflow scoring/chunking contracts are dependency-light and preserve legacy semantics")
