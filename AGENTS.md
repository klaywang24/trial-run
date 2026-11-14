# AGENTS.md · Trial Run

Last updated 2026-11-12 09:20 -0500 (New York).

Read in this order: `METHODOLOGY.md` (or `.zh.md`), then `README.md`, then this file.

## What runs, and when
- `.github/workflows/daily.yml`, scheduled at 22:17 and 23:43 UTC and 13:11 UTC next morning (odd minutes; GitHub
  dropped every :30 schedule in the first two days): frozen-hash check, tests, `python -m src.daily`,
  `python -m src.render`, `python -m src.dashboard`, then one `data:` commit per trading day, then a heartbeat to an
  outside monitor if the `HC_PING_URL` secret is set. Runs are serialized and idempotent, so a manual
  `gh workflow run daily.yml` is always safe; the owner's machine also dispatches it when the ledger falls behind.
- Check whether schedules fire with `gh api "repos/klaywang24/trial-run/actions/runs?event=schedule"`, not by the
  workflow's active state.
- The live dashboard is served by GitHub Pages from the main branch: `output/dashboard.html`.

## Rules for any agent working here
1. `config.yaml` is frozen. Change it only through a dated `methodology:` commit that also updates `FROZEN.sha256`
   and `ERRATA.md`, and only for the reasons in METHODOLOGY section 7 or a data or calculation error.
2. Never edit or backfill `data/ledger/`. A missing close means a missing day, never an estimate.
3. Automated commits touch only `data/ledger/` and `output/`.
4. Nothing here is investment advice; write results as "the backtest shows" or "in this record".
5. Commits are authored `Klay <klaywang24@gmail.com>`, with no co-author lines.

## Files that are easy to miss
- `data/ledger/pnl_by_holding.csv`: each holding's P&L points per day; a day's rows add up to its level change
  (within 1e-4, as `nav.csv` rounds the level to four decimals).
- `src/dashboard_shell.html`: the dashboard page; `src/dashboard.py` injects the data.
- `tools/fetch_companies.py`: one-off refresh of `data/meta/companies.csv` and `assets/logos/`; not run by CI.
