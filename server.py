"""
Maharashtra Schools Dashboard Server
Serves the web dashboard and provides /api/data from schools.db.

Usage:
    python server.py          (default port 8080)
    python server.py 5000     (custom port)
"""

import json
import os
import sqlite3
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT   = Path(__file__).parent
DB     = ROOT / "resources" / "schools.db"
WEB    = ROOT / "web"

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ── DB queries ────────────────────────────────────────────────────────────────

def get_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def yearly_data(conn):
    rows = conn.execute("""
        SELECT
            year,
            COUNT(*)                                                              AS total,
            SUM(CASE WHEN CAST(highclass AS INTEGER) BETWEEN 1  AND 5  THEN 1 ELSE 0 END) AS primary_schools,
            SUM(CASE WHEN CAST(highclass AS INTEGER) BETWEEN 6  AND 8  THEN 1 ELSE 0 END) AS upper_primary,
            SUM(CASE WHEN CAST(highclass AS INTEGER) BETWEEN 9  AND 10 THEN 1 ELSE 0 END) AS secondary,
            SUM(CASE WHEN CAST(highclass AS INTEGER) >= 11               THEN 1 ELSE 0 END) AS higher_secondary
        FROM school_profile_1
        GROUP BY year
        ORDER BY year
    """).fetchall()

    result = []
    for i, r in enumerate(rows):
        prev = rows[i - 1]["total"] if i > 0 else None
        change = round((r["total"] - prev) / prev * 100, 2) if prev else None
        result.append({
            "year":             r["year"],
            "total":            r["total"],
            "primary":          r["primary_schools"],
            "upper_primary":    r["upper_primary"],
            "secondary":        r["secondary"],
            "higher_secondary": r["higher_secondary"],
            "change_pct":       change,
        })
    return result


def district_data(conn):
    rows = conn.execute("""
        SELECT
            district,
            COUNT(*)                                                              AS total,
            SUM(CASE WHEN CAST(highclass AS INTEGER) BETWEEN 1  AND 5  THEN 1 ELSE 0 END) AS primary_schools,
            SUM(CASE WHEN CAST(highclass AS INTEGER) BETWEEN 9  AND 10 THEN 1 ELSE 0 END) AS secondary,
            SUM(CASE WHEN CAST(highclass AS INTEGER) >= 11               THEN 1 ELSE 0 END) AS higher_secondary
        FROM school_profile_1
        WHERE year = (SELECT MAX(year) FROM school_profile_1)
          AND district IS NOT NULL AND district != ''
        GROUP BY district
        ORDER BY district
    """).fetchall()

    return [
        {
            "district":        r["district"],
            "total":           r["total"],
            "primary":         r["primary_schools"],
            "secondary":       r["secondary"],
            "higher_secondary":r["higher_secondary"],
        }
        for r in rows
    ]


def management_data(conn):
    rows = conn.execute("""
        SELECT
            CASE
                WHEN CAST(managment AS INTEGER) IN (1, 2, 6) THEN 'Government'
                WHEN CAST(managment AS INTEGER) = 3           THEN 'Local Body'
                WHEN CAST(managment AS INTEGER) = 4           THEN 'Government-Aided'
                WHEN CAST(managment AS INTEGER) IN (5, 7)     THEN 'Private Unaided'
                ELSE 'Other'
            END AS mgmt_type,
            COUNT(*) AS cnt
        FROM school_profile_1
        WHERE year = (SELECT MAX(year) FROM school_profile_1)
        GROUP BY mgmt_type
        ORDER BY cnt DESC
    """).fetchall()

    latest = conn.execute(
        "SELECT MAX(year) FROM school_profile_1"
    ).fetchone()[0]

    total = sum(r["cnt"] for r in rows)
    return {
        "year": latest,
        "types": [
            {
                "type":       r["mgmt_type"],
                "count":      r["cnt"],
                "percentage": round(r["cnt"] / total * 100, 1) if total else 0,
            }
            for r in rows
        ],
    }


def compute_forecast(yd, years_ahead=3):
    if not HAS_NUMPY or len(yd) < 2:
        return {"status": "unavailable", "reason": "numpy not installed or insufficient data"}

    x = np.array(range(len(yd)), dtype=float)
    y = np.array([d["total"] for d in yd], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    y_pred   = slope * x + intercept
    ss_res   = np.sum((y - y_pred) ** 2)
    ss_tot   = np.sum((y - y.mean()) ** 2)
    r_squared = float(1 - ss_res / ss_tot)

    start_yr = int(yd[-1]["year"].split("-")[0])
    forecast_years = []
    for i in range(1, years_ahead + 1):
        pred  = int(round(slope * (len(yd) - 1 + i) + intercept))
        label = f"{start_yr + i}-{str(start_yr + i + 1)[-2:]}"
        forecast_years.append({"year": label, "predicted_total": pred})

    direction = "increasing" if slope > 0 else "decreasing"
    return {
        "method":        "Linear Regression",
        "slope":         round(float(slope), 2),
        "intercept":     round(float(intercept), 2),
        "r_squared":     round(r_squared, 4),
        "trend":         direction,
        "forecast_years": forecast_years,
        "explanation": (
            f"A straight line was fitted through {len(yd)} years of data "
            f"({yd[0]['year']} to {yd[-1]['year']}). "
            f"The trend shows approximately {abs(int(slope)):,} schools "
            f"{'added' if slope > 0 else 'closing'} per year on average. "
            f"R2 = {round(r_squared, 4)} means the model explains "
            f"{round(r_squared * 100, 1)}% of the variation in school counts."
        ),
    }


def build_api_response():
    conn = get_connection()
    try:
        yd   = yearly_data(conn)
        dd   = district_data(conn)
        md   = management_data(conn)
        fc   = compute_forecast(yd)
    finally:
        conn.close()

    return {
        "source_info": {
            "primary_source": "UDISE+ Microdata Portal (microdata.udiseplus.gov.in)",
            "data_coverage":  "Maharashtra State — Government, Local Body & Aided Schools",
            "note":           "Data served live from local SQLite database (schools.db).",
        },
        "data_sources": [
            {
                "name":        "UDISE+ Microdata",
                "url":         "https://microdata.udiseplus.gov.in/getCsvData",
                "description": "Unified District Information System for Education Plus — "
                               "official microdata portal for school-level CSV downloads "
                               "covering enrolment, profile, facility and teacher data across India.",
                "status":      "Active",
            },
        ],
        "yearly_data":          yd,
        "district_data":        dd,
        "management_type_data": md,
        "forecast":             fc,
    }


# ── HTTP handler ──────────────────────────────────────────────────────────────

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        if self.path == "/api/data":
            try:
                data = build_api_response()
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                error = json.dumps({"error": str(exc)}).encode()
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(error)))
                self.end_headers()
                self.wfile.write(error)
        else:
            super().do_GET()

    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080

    if not DB.exists():
        print(f"ERROR: Database not found at {DB}")
        sys.exit(1)

    print(f"Maharashtra Schools Dashboard")
    print(f"  DB   : {DB}")
    print(f"  Web  : {WEB}")
    print(f"  URL  : http://localhost:{port}")
    print(f"  API  : http://localhost:{port}/api/data")
    print()

    server = HTTPServer(("", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
