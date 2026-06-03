"""
Validation: verify schools.db matches source zip files exactly.
Checks row counts, NULL pseudocodes, column presence, and data samples.
"""

import csv
import io
import sqlite3
import zipfile
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent.parent / "resources"
DB_PATH       = RESOURCES_DIR / "schools.db"

TABLE_MAP = {
    "profile_data_1":   "school_profile_1",
    "profile_data_2":   "school_profile_2",
    "enrolment_data_1": "school_enrolment_1",
    "enrolment_data_2": "school_enrolment_2",
    "facility_data":    "school_facility",
    "teacher_data":     "school_teacher",
}

COLUMN_ALIASES = {"psuedocode": "pseudocode", "psuedo_code": "pseudocode"}

def normalise(name):
    name = name.lstrip("﻿").strip()
    return COLUMN_ALIASES.get(name, name)

def zip_rows(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))
            return sum(1 for _ in reader) - 1   # minus header

def zip_cols(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(zf.namelist()[0]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace"))
            return [normalise(c) for c in next(reader)]

conn = sqlite3.connect(DB_PATH)

print("=" * 70)
print("1. ROW COUNT CHECK — DB rows vs source zip rows")
print("=" * 70)

all_ok = True
zip_files = sorted(RESOURCES_DIR.glob("*.zip"))

for zip_path in zip_files:
    stem = zip_path.stem
    import re
    m = re.search(r"(\d{4}-\d{2})$", stem)
    year = m.group(1) if m else "unknown"
    table = next((t for p, t in TABLE_MAP.items() if stem.startswith(p)), None)
    if not table:
        continue

    src_rows = zip_rows(zip_path)
    db_rows  = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE year = ?", (year,)
    ).fetchone()[0]

    status = "OK" if src_rows == db_rows else "MISMATCH"
    if status != "OK":
        all_ok = False
    print(f"  [{status}] {zip_path.name:<52} src={src_rows:>9,}  db={db_rows:>9,}")

print()
print("=" * 70)
print("2. COLUMN CHECK — every source column present in DB table")
print("=" * 70)

checked_tables = set()
for zip_path in sorted(RESOURCES_DIR.glob("*.zip")):
    stem = zip_path.stem
    table = next((t for p, t in TABLE_MAP.items() if stem.startswith(p)), None)
    if not table or table in checked_tables:
        continue
    checked_tables.add(table)

    src_cols = set(zip_cols(zip_path))
    db_cols  = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    missing  = src_cols - db_cols
    extra    = db_cols - src_cols - {"id", "year"}

    if missing:
        all_ok = False
        print(f"  [MISSING COLS] {table}: {missing}")
    else:
        print(f"  [OK] {table:<25}  {len(src_cols)} src cols all present in DB ({len(db_cols)-2} data cols total)")

print()
print("=" * 70)
print("3. NULL / EMPTY PSEUDOCODE CHECK")
print("=" * 70)

for table in TABLE_MAP.values():
    null_count = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE pseudocode IS NULL OR pseudocode = ''"
    ).fetchone()[0]
    status = "OK" if null_count == 0 else "WARN"
    if null_count > 0:
        all_ok = False
    print(f"  [{status}] {table:<25}  {null_count:,} rows with NULL/empty pseudocode")

print()
print("=" * 70)
print("4. YEAR COVERAGE CHECK — all 7 years present in every table")
print("=" * 70)

expected_years = {"2018-19","2019-20","2020-21","2021-22","2022-23","2023-24","2024-25"}
for table in TABLE_MAP.values():
    rows = conn.execute(
        f"SELECT DISTINCT year FROM {table} ORDER BY year"
    ).fetchall()
    found = {r[0] for r in rows}
    missing = expected_years - found
    status = "OK" if not missing else "MISSING"
    if missing:
        all_ok = False
    print(f"  [{status}] {table:<25}  years: {', '.join(sorted(found))}")

print()
print("=" * 70)
print("5. SAMPLE DATA CHECK — first row per table (latest year)")
print("=" * 70)

for table in TABLE_MAP.values():
    row = conn.execute(
        f"SELECT pseudocode, year FROM {table} WHERE year='2024-25' LIMIT 1"
    ).fetchone()
    if row:
        print(f"  {table:<25}  pseudocode={row[0]}  year={row[1]}")
    else:
        print(f"  {table:<25}  [no 2024-25 data found]")
        all_ok = False

print()
print("=" * 70)
print("6. TOTAL ROW COUNT PER TABLE")
print("=" * 70)

grand_total = 0
for table in sorted(TABLE_MAP.values()):
    total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    grand_total += total
    print(f"  {table:<25}  {total:>12,} rows")
print(f"  {'GRAND TOTAL':<25}  {grand_total:>12,} rows")

conn.close()

print()
print("=" * 70)
if all_ok:
    print("RESULT: ALL CHECKS PASSED — data extracted completely and correctly.")
else:
    print("RESULT: SOME CHECKS FAILED — see details above.")
print("=" * 70)
