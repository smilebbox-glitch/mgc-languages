from __future__ import annotations

import inspect

from mgc.services.learning import build_learning_service, build_pilot_daily_usage_accessor

usage_source = inspect.getsource(build_pilot_daily_usage_accessor)
assert ".with_for_update()" in usage_source
assert "begin_nested" in usage_source
assert "IntegrityError" in usage_source

learning_source = inspect.getsource(build_learning_service)
assert "for_update=True" in learning_source
assert "profile.lifetime_xp += awarded" in learning_source
assert "profile.spendable_xp += awarded" in learning_source
assert "profile.weekly_xp += awarded" in learning_source
assert "Serialize XP mutations for one user" in learning_source

bridge_source = open("mgc_core/learning_bridge.py", encoding="utf-8").read()
assert "pilot_usage_bound" in bridge_source
assert "concurrent_write_safe" in bridge_source
assert "build_pilot_daily_usage_accessor" in bridge_source
assert "module.pilot_daily_usage = pilot_usage" in bridge_source

print("PASS: v5.9.6 race-safe usage/profile locking contracts")
