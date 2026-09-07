#!/usr/bin/env python3
from __future__ import annotations

import argparse


def semver(value: str):
    try:
        parts = tuple(int(x) for x in value.strip().split('.'))
        return parts if len(parts) == 3 else None
    except Exception:
        return None


def assess(source_version: str, source_schema: str, target_version: str, target_schema: str, *, max_patch: int, rollback: bool) -> tuple[bool, str]:
    if source_schema != target_schema:
        return False, 'schema_mismatch'
    source = semver(source_version); target = semver(target_version)
    if source is None or target is None:
        return False, 'invalid_version'
    if source[:2] != target[:2]:
        return False, 'major_minor_skew'
    delta = target[2] - source[2]
    if rollback:
        if delta > 0:
            return False, 'rollback_target_newer_than_current'
        if abs(delta) > max_patch:
            return False, 'rollback_patch_skew_exceeded'
    else:
        if delta < 0:
            return False, 'candidate_is_older'
        if delta > max_patch:
            return False, 'cutover_patch_skew_exceeded'
    return True, 'compatible'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-version', required=True)
    ap.add_argument('--source-schema', required=True)
    ap.add_argument('--target-version', required=True)
    ap.add_argument('--target-schema', required=True)
    ap.add_argument('--max-patch', type=int, default=1)
    ap.add_argument('--rollback', action='store_true')
    args = ap.parse_args()
    ok, reason = assess(args.source_version, args.source_schema, args.target_version, args.target_schema, max_patch=max(args.max_patch,0), rollback=args.rollback)
    print(f"{'PASS' if ok else 'FAIL'} {reason}: {args.source_version}/{args.source_schema} -> {args.target_version}/{args.target_schema}")
    return 0 if ok else 2

if __name__ == '__main__':
    raise SystemExit(main())
