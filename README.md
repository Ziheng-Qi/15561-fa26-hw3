# 15.561 HW3: AI-Assisted Business Data Analysis (Northwind)

Analysis of the course-provided Northwind Traders database, answering four business
questions for a sales and operations manager. The results are published as a webpage
(`docs/index.html`, served with GitHub Pages).

| # | Business question | Key output |
|---|---|---|
| 1 | Which customer markets are growing or shrinking, and where should sales attention go? | `outputs/q1_*.csv` |
| 2 | How dependent is revenue on a few customers, and are any key accounts going quiet? | `outputs/q2_customer_revenue.csv` |
| 3 | Are discounts buying extra volume, or just giving away margin? | `outputs/q3_discount_tiers.csv` |
| 4 | Where do late deliveries come from: the shipper, the sales rep, or the deadline? | `outputs/q4_*.csv` |

## Reproduce everything

Requires Python 3.10+ (tested with 3.12.7).

```bash
git clone https://github.com/Ziheng-Qi/15561-fa26-hw3.git
cd 15561-fa26-hw3
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m hw3.main
```

The single command `python -m hw3.main`:

1. Loads `data/northwind.xlsx`, the unmodified course workbook.
2. Runs the four analyses in `hw3/questions.py`.
3. **Cross-checks** the headline numbers by recomputing them in SQL (SQLite in memory)
   in `hw3/verify.py`. The run stops if any check fails. Expected output:
   ```
   [OK] Total net revenue: pandas=1,265,793.0395 sql=1,265,793.0395
   [OK] Jan-Apr 1997 revenue: pandas=191,321.8775 sql=191,321.8775
   [OK] Jan-Apr 1998 revenue: pandas=422,290.2355 sql=422,290.2355
   [OK] Top-3 customer share: pandas=0.2524 sql=0.2524
   [OK] Total discount cost: pandas=88,665.5505 sql=88,665.5505
   [OK] Late rate, 14-day orders: pandas=0.1765 sql=0.1765
   [OK] Late order count: pandas=37.0000 sql=37.0000
   All cross-checks passed.
   ```
4. Writes every table behind the webpage to `outputs/` as CSV.
5. Regenerates `docs/index.html`. Every number on the page is computed by the code
   at build time, and the charts are Plotly figures generated in Python.

To view the page locally: `python -m http.server --directory docs 8000`, then open
http://localhost:8000.

## Repository layout

```
data/northwind.xlsx     course-provided dataset (unmodified)
hw3/data_prep.py        load sheets, build order-line and order tables, revenue definitions
hw3/questions.py        the four analyses: tables, metrics, statistical tests, figures
hw3/verify.py           independent SQL cross-checks of headline numbers
hw3/build_site.py       renders docs/index.html from the results
hw3/main.py             entry point: runs everything in order
outputs/                CSV tables produced by the run
docs/index.html         the published webpage (GitHub Pages source)
.claude/skills/python-docstrings/SKILL.md   docstring skill used to document the code
```

## Definitions and data decisions

- **Net revenue** = `UnitPrice × Quantity × (1 − Discount)`, using the price recorded on
  each order line. About 30% of lines carry a price that differs from today's list price,
  so the product table's price is not used.
- **Discount rounding.** The workbook stores discounts as 32-bit floats (5% is read as
  `0.0500000007`), so they are rounded to 2 decimals. Without this, 5% lines fall into
  the wrong band.
- **Time window.** Data runs from 1996-07-04 to 1998-05-06. Year-over-year comparisons use
  Jan 1 to Apr 30 in both years, because calendar 1998 is incomplete.
- **Late** = shipped after `RequiredDate`. The 21 orders not yet shipped by the end of the
  data are excluded; none were already past due.
- **Quiet account** = no order in the 90 days before the last date in the data.
  The median gap between a customer's orders is 35 days.
- The workbook's `Product` sheet has extra helper columns (`Cheap`, `NewPrice`, …) from
  an earlier exercise. They are not used.

## Documentation

All functions carry Google-style, PEP 257 docstrings generated with the course
`python-docstrings` skill (copy in `.claude/skills/`). They pass
`pydocstyle --convention=google hw3`.
