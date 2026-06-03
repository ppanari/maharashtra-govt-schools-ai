"""
ETL: UDISE+ Maharashtra CSV zips -> SQLite database

Reads all zip files from resources/, extracts CSVs in-memory,
and loads data into schools.db with one table per data type.

Tables created:
  school_profile_1   -- school identity, location, type, medium, affiliation
  school_profile_2   -- schemes, inspections, SMC, grants
  school_enrolment_1 -- enrolment by class/gender (category groups 1-7)
  school_enrolment_2 -- enrolment by class/gender (category groups 8+)
  school_facility    -- infrastructure, toilets, labs, ICT equipment
  school_teacher     -- teacher counts by gender, category, qualification

Note: UDISE+ changed column names between academic years (e.g. 'psuedocode'
typo in 2018-21 files corrected to 'pseudocode' from 2021-22 onwards).
This script normalises all known aliases and uses ALTER TABLE ADD COLUMN
to absorb new columns introduced in later years.
"""

import csv
import io
import re
import sqlite3
import zipfile
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent.parent / "resources"
DB_PATH       = RESOURCES_DIR / "schools.db"
BATCH_SIZE    = 5000

# Zip filename prefix -> table name
TABLE_MAP = {
    "profile_data_1":    "school_profile_1",
    "profile_data_2":    "school_profile_2",
    "enrolment_data_1":  "school_enrolment_1",
    "enrolment_data_2":  "school_enrolment_2",
    "facility_data":     "school_facility",
    "teacher_data":      "school_teacher",
}

# Known column name typos / renames across UDISE+ years
COLUMN_ALIASES = {
    "psuedocode":  "pseudocode",   # typo in 2018-19 to ~2021-22 files
    "psuedo_code": "pseudocode",
}

# Columns stored as TEXT; everything else becomes REAL
TEXT_COLS = {
    "pseudocode", "year", "state", "district", "block",
    "lgd_urban_local_body_name", "lgd_ward_name", "lgd_vill_name",
    "lgd_vill_panchayat_name", "lgd_block_name", "pincode",
    "city", "municipality", "panchyat", "assembly", "parliamentary",
}


def normalise_col(name: str) -> str:
    """Strip BOM, whitespace, and apply known alias corrections."""
    name = name.lstrip("﻿￾").strip()
    return COLUMN_ALIASES.get(name, name)


def col_type(name: str) -> str:
    return "TEXT" if name in TEXT_COLS else "REAL"


def resolve_zip(filename: str):
    """Return (table_name, academic_year) for a zip filename, or (None, None)."""
    stem = Path(filename).stem
    match = re.search(r"(\d{4}-\d{2})$", stem)
    year = match.group(1) if match else "unknown"
    for prefix, table in TABLE_MAP.items():
        if stem.startswith(prefix):
            return table, year
    return None, None


def get_existing_columns(conn: sqlite3.Connection, table: str) -> set:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def ensure_table(conn: sqlite3.Connection, table: str, columns: list):
    """Create table if absent; add any new columns via ALTER TABLE."""
    col_defs = ",\n    ".join(f'"{c}" {col_type(c)}' for c in columns)
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            year    TEXT    NOT NULL,
            {col_defs}
        )
    """)

    # Add any columns present in this CSV that the table doesn't yet have
    existing = get_existing_columns(conn, table)
    for col in columns:
        if col not in existing:
            conn.execute(f'ALTER TABLE {table} ADD COLUMN "{col}" {col_type(col)}')

    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_pseudo ON {table}(pseudocode)"
    )
    conn.execute(
        f"CREATE INDEX IF NOT EXISTS idx_{table}_year ON {table}(year)"
    )
    conn.commit()


def load_zip(conn: sqlite3.Connection, zip_path: Path, table: str, year: str) -> int:
    with zipfile.ZipFile(zip_path) as zf:
        csv_name = zf.namelist()[0]
        with zf.open(csv_name) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace")
            )
            # Normalise column names (fix typos, strip BOM)
            raw_fields  = reader.fieldnames or []
            norm_fields = [normalise_col(c) for c in raw_fields]

            # Patch the reader so DictReader uses normalised keys
            reader.fieldnames = norm_fields

            ensure_table(conn, table, norm_fields)

            # Delete existing rows for this year so the script is re-runnable
            conn.execute(f"DELETE FROM {table} WHERE year = ?", (year,))

            # Build INSERT using only columns the table actually has
            table_cols  = get_existing_columns(conn, table) - {"id"}
            insert_cols = ["year"] + [c for c in norm_fields if c in table_cols]
            placeholders = ", ".join(["?"] * len(insert_cols))
            col_clause   = ", ".join(f'"{c}"' for c in insert_cols)
            sql = f"INSERT INTO {table} ({col_clause}) VALUES ({placeholders})"

            batch, count = [], 0
            for row in reader:
                values = [year] + [row.get(c) for c in insert_cols[1:]]
                batch.append(values)
                count += 1
                if len(batch) >= BATCH_SIZE:
                    conn.executemany(sql, batch)
                    batch.clear()

            if batch:
                conn.executemany(sql, batch)
            conn.commit()
            return count


def print_summary(conn: sqlite3.Connection):
    print("\n-- Database summary ------------------------------------------")
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence' ORDER BY name"
    ).fetchall()
    for (t,) in tables:
        rows  = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        years = conn.execute(
            f"SELECT GROUP_CONCAT(year, ', ') FROM (SELECT DISTINCT year FROM {t} ORDER BY year)"
        ).fetchone()[0]
        ncols = len(conn.execute(f"PRAGMA table_info({t})").fetchall())
        print(f"  {t:<25} {rows:>10,} rows   {ncols:>3} cols   years: {years}")
    print()


def main():
    zip_files = sorted(RESOURCES_DIR.glob("*.zip"))
    print(f"Found {len(zip_files)} zip file(s) in {RESOURCES_DIR}\n")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    total_rows, errors = 0, []

    for zip_path in zip_files:
        table, year = resolve_zip(zip_path.name)
        if not table:
            print(f"  [SKIP]  {zip_path.name}")
            continue

        print(
            f"  Loading {zip_path.name:<50} -> {table} (year={year}) ...",
            end=" ", flush=True
        )
        try:
            rows = load_zip(conn, zip_path, table, year)
            print(f"{rows:,} rows")
            total_rows += rows
        except Exception as exc:
            print(f"ERROR: {exc}")
            errors.append((zip_path.name, exc))

    print_summary(conn)
    conn.close()

    db_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"Saved : {DB_PATH}")
    print(f"Total : {total_rows:,} rows   |   DB size: {db_mb:.1f} MB")
    if errors:
        print(f"\n{len(errors)} error(s):")
        for name, exc in errors:
            print(f"  {name}: {exc}")


if __name__ == "__main__":
    main()
