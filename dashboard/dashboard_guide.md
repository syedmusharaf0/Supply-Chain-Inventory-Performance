# Dashboard Guide

Three ways to view this project's dashboards — same data, same KPIs:

1. **Interactive HTML dashboard** — `dashboard/dashboard.html`
   Complete, self-contained executive dashboard (open in any browser, no
   licence needed): KPI cards, key insights, warehouse table, monthly
   growth (LAG) table and 5 charts. Regenerate with
   `python dashboard/build_dashboard.py`. Can be published free through
   GitHub Pages (repo Settings → Pages → deploy from the `main` branch).

2. **Power BI dashboard** — build the `.pbix` in Power BI Desktop using
   `dashboard/powerbi_build_guide.md` (page-by-page spec, theme, formatting),
   `dashboard/power_query_m.txt` (data load) and
   `dashboard/dax_measures.dax` (all measures incl. WoW / MoM / YoY growth).

3. **Result tables** — `outputs/*.csv` for the raw KPI numbers behind every
   visual, including `weekly_trend.csv`, `monthly_trend.csv` and
   `yearly_summary.csv` with LAG-based growth percentages.

## Refresh
Re-run `python/etl_pipeline.py`, then `python/kpi_analysis.py`, then
`python dashboard/build_dashboard.py` whenever the data extracts change.
In Power BI, one click on **Refresh** reloads the same CSVs.
