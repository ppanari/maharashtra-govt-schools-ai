# Maharashtra Government Schools Data AI Project

A Python-based AI/data project to collect, analyze, and visualize data on the total number of government schools in Maharashtra state, India, across all available years.

---

## Project Overview

This project uses Python to:
- Collect data on government schools in Maharashtra from public sources (UDISE+, data.gov.in, Ministry of Education reports)
- Clean and process multi-year datasets across all available years
- Analyze year-on-year trends using statistical and AI/ML techniques
- Generate visualizations and automated reports

---

## Data Sources

| Source | URL | Description |
|--------|-----|-------------|
| UDISE+ Portal | https://udiseplus.gov.in | Unified District Information System for Education |
| data.gov.in | https://data.gov.in | Government of India Open Data Portal |
| Ministry of Education | https://www.education.gov.in | Annual reports and school statistics |
| Census of India | https://censusindia.gov.in | Educational infrastructure data |

> Data coverage: **All available years**, focusing on Maharashtra state government schools (primary, upper-primary, secondary, higher-secondary).

---

## Project Structure

```
maharashtra-govt-schools-ai/
├── src/
│   ├── __init__.py
│   ├── data_collector.py      # Fetch data from APIs and web sources
│   ├── data_processor.py      # Clean and transform raw data
│   ├── analyzer.py            # Statistical analysis and ML models
│   └── visualizer.py          # Charts and dashboards
├── data/
│   ├── raw/                   # Raw downloaded datasets
│   └── processed/             # Cleaned, analysis-ready data
├── notebooks/
│   └── exploratory_analysis.ipynb
├── reports/                   # Auto-generated reports and charts
├── main.py                    # Entry point
├── config.py                  # Configuration and constants
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

### Prerequisites
- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/ppanari/maharashtra-govt-schools-ai.git
cd maharashtra-govt-schools-ai

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Collect Data
```bash
python main.py --mode collect --state Maharashtra
```

### Process & Clean Data
```bash
python main.py --mode process
```

### Run Analysis
```bash
python main.py --mode analyze
```

### Generate Report
```bash
python main.py --mode report
```

### Full Pipeline (collect → process → analyze → report)
```bash
python main.py --mode all
```

---

## Key Features

- **Multi-year data collection**: Automated fetching from UDISE+ and open government portals across all available years
- **School category breakdown**: Primary, Upper-Primary, Secondary, Higher Secondary
- **District-level granularity**: Data broken down by all 36 districts of Maharashtra
- **Management type filter**: Government, Local Body, Government-Aided schools
- **Trend analysis**: Year-on-year growth/decline, enrollment vs infrastructure analysis
- **AI-powered insights**: Anomaly detection, predictive modeling for future school counts
- **Automated reports**: PDF/HTML reports with charts generated on demand

---

## Sample Output

```
Maharashtra Government Schools Summary
======================================
Year    | Total Schools | Primary | Secondary | Change (YoY)
--------|--------------|---------|-----------|-------------
...     |    ...       |  ...    |   ...     |     —
2014-15 |    97,000    |  62,000 |   18,000  |   +x.x%
2015-16 |    96,500    |  61,200 |   18,100  |   -0.5%
...
2023-24 |    98,200    |  63,000 |   19,500  |   +0.8%
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/add-district-analysis`)
3. Commit your changes (`git commit -m 'Add district-level breakdown'`)
4. Push to the branch (`git push origin feature/add-district-analysis`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Author

**Pooja Panari**  
[GitHub](https://github.com/ppanari) | poojapanari@gmail.com

---

## Acknowledgements

- UDISE+ for maintaining comprehensive school data
- data.gov.in for open government datasets
- Ministry of Education, Government of India
