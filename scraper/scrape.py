"""
Maharashtra Government Schools Data Scraper
Sources: UDISE+, data.gov.in, Ministry of Education, Census of India
"""

import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'web', 'data')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
}


def fetch_data_gov_in():
    """
    Search data.gov.in catalog for Maharashtra school datasets, then attempt to
    download actual records from each found dataset to extract real yearly data.
    Returns: (catalog_meta, yearly_data)
    """
    print("[data.gov.in] Searching catalog...")
    catalog_meta = []
    yearly_data = []

    try:
        resp = requests.get(
            "https://api.data.gov.in/catalog/list",
            params={"q": "maharashtra government schools", "format": "json", "count": 10},
            headers=HEADERS, timeout=15
        )
        if resp.status_code == 200:
            catalog = resp.json().get("catalog", [])
            print(f"[data.gov.in] Found {len(catalog)} dataset(s)")
            catalog_meta = [{"title": c.get("title"), "id": c.get("id"), "org": c.get("org")} for c in catalog]

            # Attempt to fetch actual records from each dataset
            for item in catalog_meta:
                resource_id = item.get("id")
                if not resource_id:
                    continue
                try:
                    rec_resp = requests.get(
                        f"https://api.data.gov.in/resource/{resource_id}",
                        params={"format": "json", "limit": 500},
                        headers=HEADERS, timeout=20
                    )
                    if rec_resp.status_code != 200:
                        continue
                    records = rec_resp.json().get("records", [])
                    if not records:
                        continue
                    print(f"[data.gov.in] Resource {resource_id}: {len(records)} record(s)")

                    extracted = []
                    for rec in records:
                        year_val, total_val = None, None
                        for key, val in rec.items():
                            k = key.lower()
                            if year_val is None and ('year' in k or 'yr' in k):
                                year_val = str(val).strip()
                            if total_val is None and any(kw in k for kw in ('total', 'school', 'count', 'number')):
                                try:
                                    total_val = int(str(val).replace(',', '').strip())
                                except (ValueError, TypeError):
                                    pass
                        if year_val and total_val and total_val > 0:
                            extracted.append({"year": year_val, "total": total_val})

                    if extracted:
                        yearly_data = extracted
                        break
                except Exception as e:
                    print(f"[data.gov.in] Resource {resource_id} fetch failed: {e}")

    except Exception as e:
        print(f"[data.gov.in] Catalog search failed: {e}")

    # Sort by year and compute year-on-year change
    yearly_data.sort(key=lambda x: x["year"])
    for i, row in enumerate(yearly_data):
        if i == 0:
            row["change_pct"] = None
        else:
            prev = yearly_data[i - 1]["total"]
            row["change_pct"] = round((row["total"] - prev) / prev * 100, 2) if prev else None

    print(f"[data.gov.in] Extracted {len(yearly_data)} year(s) of real yearly data")
    return catalog_meta, yearly_data


def fetch_udise_summary():
    """Scrape summary statistics from UDISE+ portal homepage."""
    print("[UDISE+] Fetching homepage...")
    try:
        resp = requests.get("https://udiseplus.gov.in", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            stats = {}
            for el in soup.select('.counter-number, .count, .stat-value, [class*="count"]')[:10]:
                text = el.get_text(strip=True)
                if text and text[0].isdigit():
                    label_el = el.find_next_sibling() or el.parent
                    label = label_el.get_text(strip=True)[:60] if label_el else "stat"
                    stats[label] = text
            title = soup.title.string.strip() if soup.title else "UDISE+"
            print(f"[UDISE+] Page title: {title}, stats found: {len(stats)}")
            return {"page_title": title, "stats": stats}
    except Exception as e:
        print(f"[UDISE+] Failed: {e}")
    return {}


def fetch_education_ministry():
    """Scrape relevant report links from Ministry of Education website."""
    print("[education.gov.in] Fetching...")
    try:
        resp = requests.get("https://www.education.gov.in", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            links = []
            keywords = ['report', 'school', 'statistics', 'udise', 'annual', 'data']
            for a in soup.find_all('a', href=True):
                text = a.get_text(strip=True)
                if text and any(kw in text.lower() for kw in keywords) and len(text) > 5:
                    href = a['href']
                    if not href.startswith('http'):
                        href = 'https://www.education.gov.in' + href
                    links.append({"text": text, "url": href})
            print(f"[education.gov.in] Found {len(links)} relevant link(s)")
            return links[:15]
    except Exception as e:
        print(f"[education.gov.in] Failed: {e}")
    return []


def fetch_census_india():
    """Fetch educational infrastructure metadata from Census of India."""
    print("[censusindia.gov.in] Fetching...")
    try:
        resp = requests.get("https://censusindia.gov.in", headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.title.string.strip() if soup.title else ""
            links = []
            for a in soup.find_all('a', href=True):
                text = a.get_text(strip=True)
                if text and any(kw in text.lower() for kw in ['education', 'school', 'literacy']):
                    links.append({"text": text, "url": a['href']})
            print(f"[censusindia.gov.in] Page: {title}, links: {len(links)}")
            return {"page_title": title, "links": links[:10]}
    except Exception as e:
        print(f"[censusindia.gov.in] Failed: {e}")
    return {}



def compute_forecast(yearly_data, years_ahead=3):
    """
    Trend forecasting using Linear Regression.

    What is Linear Regression?
    --------------------------
    Imagine plotting school counts on a graph year by year.
    Linear regression finds the single best straight line through
    all those dots — the line that minimises the total error.

    Once we have that line, we simply extend it into the future
    to get predictions.

    The maths:
        predicted_total = slope * year_number + intercept
        - slope     : how many schools are added/removed per year on average
        - intercept : the starting value when year_number = 0
        - R²        : how well the line fits (0 = poor, 1.0 = perfect)
    """
    x = np.array(range(len(yearly_data)), dtype=float)
    y = np.array([d['total'] for d in yearly_data], dtype=float)

    # numpy finds the best-fit line in one call
    slope, intercept = np.polyfit(x, y, 1)

    # R² — how much of the variance the line explains
    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = float(1 - ss_res / ss_tot)

    # Predict the next `years_ahead` years
    last_year_str = yearly_data[-1]['year']
    start_yr = int(last_year_str.split('-')[0])

    forecast_years = []
    for i in range(1, years_ahead + 1):
        future_x = len(yearly_data) - 1 + i
        predicted = int(round(slope * future_x + intercept))
        label = f"{start_yr + i}-{str(start_yr + i + 1)[-2:]}"
        forecast_years.append({'year': label, 'predicted_total': predicted})

    direction = 'increasing' if slope > 0 else 'decreasing'
    return {
        'method': 'Linear Regression',
        'slope': round(float(slope), 2),
        'intercept': round(float(intercept), 2),
        'r_squared': round(r_squared, 4),
        'trend': direction,
        'forecast_years': forecast_years,
        'explanation': (
            f"A straight line was fitted through {len(yearly_data)} years of data "
            f"({yearly_data[0]['year']} to {yearly_data[-1]['year']}). "
            f"The trend shows approximately {abs(int(slope)):,} schools "
            f"{'added' if slope > 0 else 'closing'} per year on average. "
            f"R² = {round(r_squared, 4)} means the model explains "
            f"{round(r_squared * 100, 1)}% of the variation in school counts."
        )
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Maharashtra Government Schools — Data Scraper")
    print("=" * 60)

    # Live fetches from real government sources
    data_gov_catalog, yearly_data = fetch_data_gov_in()
    udise_summary                 = fetch_udise_summary()
    education_links               = fetch_education_ministry()
    census_info                   = fetch_census_india()

    # Build dataset from only live-scraped data
    dataset = {
        "source_info": {
            "primary_source": "UDISE+ Portal (udiseplus.gov.in)",
            "secondary_sources": [
                "data.gov.in — Government of India Open Data Portal",
                "Ministry of Education (education.gov.in)",
                "Census of India (censusindia.gov.in)"
            ],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "note": "All data fetched live from official government sources."
        },
        "data_sources": [
            {
                "name": "UDISE+ Portal",
                "url": "https://udiseplus.gov.in",
                "description": "Unified District Information System for Education — primary source for school statistics across India",
                "status": "Active"
            },
            {
                "name": "data.gov.in",
                "url": "https://data.gov.in",
                "description": "Government of India Open Data Portal — open datasets on education infrastructure and school counts",
                "status": "Active"
            },
            {
                "name": "Ministry of Education",
                "url": "https://www.education.gov.in",
                "description": "Annual reports and statistical publications on school education in India",
                "status": "Active"
            },
            {
                "name": "Census of India",
                "url": "https://censusindia.gov.in",
                "description": "Decennial census data on educational infrastructure and literacy across India",
                "status": "Active"
            }
        ],
        "yearly_data": yearly_data,
        "live_data": {
            "udise_live_summary": udise_summary,
            "data_gov_catalog":   data_gov_catalog[:5],
            "ministry_links":     education_links[:10],
            "census_info":        census_info
        }
    }

    # Forecast only if real yearly data was successfully fetched
    if len(yearly_data) >= 2:
        dataset["forecast"] = compute_forecast(yearly_data)
        print(f"\n[Forecast] Method: {dataset['forecast']['method']}")
        print(f"[Forecast] Slope: {dataset['forecast']['slope']} schools/year")
        print(f"[Forecast] R²: {dataset['forecast']['r_squared']}")
        for fy in dataset['forecast']['forecast_years']:
            print(f"[Forecast] {fy['year']}: {fy['predicted_total']:,} schools (predicted)")
    else:
        dataset["forecast"] = {
            "status": "unavailable",
            "reason": "Real yearly data could not be extracted from live sources."
        }
        print("\n[Forecast] Skipped — not enough real yearly data available from live sources.")

    out_path = os.path.join(OUTPUT_DIR, 'schools_data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\nSaved: {out_path}")
    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
