#!/usr/bin/env python3
"""Deterministic CI-scale benchmark for core engineering data shapes.

This intentionally benchmarks local CPU/SQLite algorithm and index behavior only. Pilot and
enterprise certification must run against the real PostgreSQL/Redis/Qdrant deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"backend"))
from app.services.performance_certification import PROFILES, PERFORMANCE_SCHEMA, percentile  # noqa: E402


def timed(fn, repeat=7):
    vals=[]; result=None
    for _ in range(repeat):
        t=time.perf_counter(); result=fn(); vals.append((time.perf_counter()-t)*1000)
    return result,{"p50_ms":round(percentile(vals,50) or 0,3),"p95_ms":round(percentile(vals,95) or 0,3),"max_ms":round(max(vals),3)}


def populate(conn: sqlite3.Connection, parts:int, edges:int, vins:int, genealogy:int, observations:int):
    conn.executescript('''
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA temp_store=MEMORY;
      CREATE TABLE bom_items(parent_part_number TEXT,parent_revision TEXT,child_part_number TEXT,child_revision TEXT,quantity REAL,position TEXT);
      CREATE INDEX idx_v604_bom_parent_revision_child ON bom_items(parent_part_number,parent_revision,child_part_number);
      CREATE TABLE vehicle_builds(id INTEGER PRIMARY KEY,project_code TEXT,vehicle_identifier TEXT,status TEXT);
      CREATE UNIQUE INDEX idx_v604_vehicle_build_project_vin_status ON vehicle_builds(project_code,vehicle_identifier,status);
      CREATE TABLE build_genealogy_items(build_id INTEGER,part_number TEXT,supplier_code TEXT,lot_number TEXT,revision TEXT);
      CREATE INDEX idx_v604_genealogy_build_part_supplier_lot ON build_genealogy_items(build_id,part_number,supplier_code,lot_number);
      CREATE TABLE series_quality_observations(project_code TEXT,observed_at INTEGER,part_number TEXT,supplier_code TEXT,defect_quantity INTEGER,produced_quantity INTEGER);
      CREATE INDEX idx_v604_series_project_time_part ON series_quality_observations(project_code,observed_at,part_number);
    ''')
    batch=[]
    root_mod=max(1,parts//200)
    for i in range(edges):
        parent=f"P{(i%root_mod):08d}"; child=f"P{(i*17+3)%parts:08d}"
        batch.append((parent,"A",child,chr(65+(i%4)),1.0,str(i%1000)))
        if len(batch)>=5000:
            conn.executemany("INSERT INTO bom_items VALUES (?,?,?,?,?,?)",batch); batch=[]
    if batch: conn.executemany("INSERT INTO bom_items VALUES (?,?,?,?,?,?)",batch)
    conn.executemany("INSERT INTO vehicle_builds(id,project_code,vehicle_identifier,status) VALUES (?,?,?,?)",[(i+1,"P604",f"VIN{i:08d}","completed") for i in range(vins)])
    batch=[]
    for i in range(genealogy):
        batch.append(((i%vins)+1,f"P{(i*19+7)%parts:08d}",f"SUP{i%120:04d}",f"LOT{i%5000:06d}",chr(65+(i%4))))
        if len(batch)>=5000:
            conn.executemany("INSERT INTO build_genealogy_items VALUES (?,?,?,?,?)",batch); batch=[]
    if batch: conn.executemany("INSERT INTO build_genealogy_items VALUES (?,?,?,?,?)",batch)
    batch=[]
    now=1_800_000_000
    for i in range(observations):
        batch.append(("P604",now-(i%2_592_000),f"P{(i*13+11)%parts:08d}",f"SUP{i%120:04d}",1 if i%97==0 else 0,100))
        if len(batch)>=5000:
            conn.executemany("INSERT INTO series_quality_observations VALUES (?,?,?,?,?,?)",batch); batch=[]
    if batch: conn.executemany("INSERT INTO series_quality_observations VALUES (?,?,?,?,?,?)",batch)
    conn.commit()


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--profile",choices=sorted(PROFILES),default="ci")
    ap.add_argument("--scale",type=float,default=1.0,help="Multiplier; CI defaults are safe for packaging verification")
    ap.add_argument("--output",default="")
    args=ap.parse_args(); p=PROFILES[args.profile]
    if args.profile!="ci" and os.getenv("MGC_ALLOW_NONCI_SYNTHETIC")!="YES":
        raise SystemExit("Non-CI synthetic profiles require MGC_ALLOW_NONCI_SYNTHETIC=YES; use real PostgreSQL load certification for pilot/enterprise")
    counts={k:max(1,int(v*args.scale)) for k,v in {"parts":p.parts,"bom_edges":p.bom_edges,"vins":p.vins,"genealogy_rows":p.genealogy_rows,"quality_observations":p.quality_observations}.items()}
    with tempfile.TemporaryDirectory(prefix="mgc-perf-") as td:
        db=Path(td)/"bench.db"; conn=sqlite3.connect(db)
        t=time.perf_counter(); populate(conn,counts["parts"],counts["bom_edges"],counts["vins"],counts["genealogy_rows"],counts["quality_observations"]); load_ms=(time.perf_counter()-t)*1000
        _,bom=timed(lambda:list(conn.execute("SELECT child_part_number,child_revision FROM bom_items WHERE parent_part_number=? AND parent_revision=?",("P00000000","A"))))
        _,vin=timed(lambda:list(conn.execute("SELECT g.part_number,g.revision,g.supplier_code,g.lot_number FROM vehicle_builds b JOIN build_genealogy_items g ON g.build_id=b.id WHERE b.project_code=? AND b.vehicle_identifier=?",("P604","VIN00000042"))))
        _,quality=timed(lambda:list(conn.execute("SELECT part_number,SUM(defect_quantity),SUM(produced_quantity) FROM series_quality_observations WHERE project_code=? AND observed_at>? GROUP BY part_number ORDER BY SUM(defect_quantity) DESC LIMIT 50",("P604",1_800_000_000-604800))))
        result={"schema":PERFORMANCE_SCHEMA,"profile":args.profile,"synthetic":True,"database":"sqlite","counts":counts,"load_ms":round(load_ms,3),"queries":{"bom_children":bom,"vin_genealogy":vin,"series_quality_7d":quality},"db_size_bytes":db.stat().st_size,"governance":{"ci_scale_only":args.profile=="ci","not_enterprise_certification":True,"real_postgresql_load_test_required":True}}
        conn.close()
    text=json.dumps(result,ensure_ascii=False,indent=2); print(text)
    if args.output: Path(args.output).write_text(text+"\n",encoding="utf-8")

if __name__=="__main__": main()
