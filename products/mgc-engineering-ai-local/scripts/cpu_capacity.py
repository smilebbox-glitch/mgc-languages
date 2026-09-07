#!/usr/bin/env python3
"""Small dependency-free CPU sizing helper for the offline Engineering AI runtime."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def memory_gib() -> float | None:
    p = Path('/proc/meminfo')
    if p.exists():
        for line in p.read_text(encoding='utf-8', errors='ignore').splitlines():
            if line.startswith('MemTotal:'):
                try:
                    return int(line.split()[1]) / 1024 / 1024
                except Exception:
                    return None
    try:
        pages = os.sysconf('SC_PHYS_PAGES')
        page_size = os.sysconf('SC_PAGE_SIZE')
        return pages * page_size / (1024 ** 3)
    except Exception:
        return None


def recommend(cpus: int, ram: float | None) -> dict:
    # Conservative defaults: keep spare cores/RAM for CAD, OCR, DB and the OS.
    if cpus <= 4 or (ram is not None and ram < 12):
        profile = 'minimal'
        llm_threads = max(1, min(cpus, 4))
        aux_threads = 1 if cpus <= 2 else 2
        context = 4096
        reranker = False
        worker = 1
    elif cpus <= 12 or (ram is not None and ram < 28):
        profile = 'standard'
        llm_threads = max(4, min(8, cpus - 2 if cpus > 6 else cpus))
        aux_threads = max(2, min(4, cpus // 3))
        context = 6144 if ram is not None and ram < 24 else 8192
        reranker = True
        worker = 1
    else:
        profile = 'heavy'
        llm_threads = min(16, max(8, cpus - 4))
        aux_threads = min(6, max(3, cpus // 4))
        context = 8192
        reranker = True
        worker = 2 if cpus >= 24 and (ram is None or ram >= 48) else 1
    return {
        'profile': profile,
        'detected_logical_cpus': cpus,
        'detected_ram_gib': round(ram, 1) if ram is not None else None,
        'CPU_THREADS': llm_threads,
        'CPU_THREADS_BATCH': llm_threads,
        'CPU_AUX_THREADS': aux_threads,
        'CPU_WORKER_CONCURRENCY': worker,
        'CPU_CONTEXT_SIZE': context,
        'CPU_PARALLEL': 1,
        'CPU_RERANKER_ENABLED': reranker,
        'note': 'Starting recommendation only; validate latency and memory on the real engineering workload.',
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    rec = recommend(cpu_count(), memory_gib())
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return
    print('MGC CPU capacity check')
    print(f"Profile: {rec['profile']}")
    print(f"Logical CPU: {rec['detected_logical_cpus']}")
    print(f"RAM GiB: {rec['detected_ram_gib'] if rec['detected_ram_gib'] is not None else 'unknown'}")
    print('Recommended .env starting values:')
    for key in ['CPU_THREADS','CPU_THREADS_BATCH','CPU_AUX_THREADS','CPU_WORKER_CONCURRENCY','CPU_CONTEXT_SIZE','CPU_PARALLEL','CPU_RERANKER_ENABLED']:
        value = rec[key]
        if isinstance(value, bool): value = str(value).lower()
        print(f'{key}={value}')
    if rec['profile'] == 'minimal':
        print('WARNING: CPU-only LLM generation will be slow on this host. CAD/OCR/search remain usable; keep CPU Vision disabled.')

if __name__ == '__main__':
    main()
