"""Render the README charts from the ledger: index level vs benchmarks, AI ranking, sleeve allocation."""
from __future__ import annotations
import csv
from .common import CFG, LEDGER, OUTPUT
from .svg import line_chart, hbar_chart, placeholder, COLORS

AI_SLEEVES = ("ai", "ai_park", "ai_park_switch")


def nav_chart():
    p = LEDGER / "nav.csv"
    rows = list(csv.DictReader(open(p))) if p.exists() else []
    out = OUTPUT / "nav_chart.svg"
    if len(rows) < 2:
        inc = CFG["meta"]["inception_date"]
        placeholder(out, "Trial Run vs SPY, QQQ and the pre-launch portfolio",
                    f"The record starts at the {inc} close (base 100). The chart appears after the second trading day.")
        return
    d = [r["date"] for r in rows]
    s = {"Trial Run": [float(r["level"]) for r in rows], "SPY": [float(r["spy"]) for r in rows],
         "QQQ": [float(r["qqq"]) for r in rows], "Pre-launch": [float(r["pre_launch"]) for r in rows]}
    lv = s["Trial Run"]; peak, mdd = lv[0], 0.0
    for v in lv:
        peak = max(peak, v); mdd = min(mdd, v / peak - 1)
    note = (f"{len(rows)} trading days · {lv[-1] - 100:+.2f}% since inception · vs SPY {lv[-1] - s['SPY'][-1]:+.2f} pts · "
            f"max drawdown {mdd * 100:.2f}% · market switch {rows[-1]['market_switch']} · as of {d[-1]}")
    line_chart(out, "Trial Run · index level (base 100)",
               f"inception {d[0]} close · forward record, never backfilled · costs 10 bp per side included", d, s,
               base=100, fmt="{:.1f}", note=note)


def ranking_chart():
    p = LEDGER / "ai_ranking_latest.csv"
    if not p.exists():
        return
    rows = list(csv.DictReader(open(p)))
    ranked = [r for r in rows if r["rank"]]
    held_col, out_col = COLORS[0], "#9aa3ad"
    bars = []
    for r in ranked:
        held = r["held"] == "True"
        tag = ("  held" if held else "") + ("  chip" if r["chip"] == "True" else "") + ("" if r["above_10m_ma"] == "True" else "  below 10m MA")
        bars.append((f"{r['rank']}. {r['ticker']}", float(r["mom_12_1"]) * 100, held_col if held else out_col, tag.replace('  ', ' · ', 1).replace('  ', ' · ') if tag else ''))
    for r in rows:
        if not r["rank"]:
            bars.append((r["ticker"], 0.0, out_col, "  too new to rank"))
    n8, n12 = CFG["ai"]["select_n"], CFG["ai"]["exit_rank"]
    marks = {n8: f"top {n8} line (new buys come from above)", n12: f"exit line: a held name below rank {n12} is sold in January"}
    hbar_chart(OUTPUT / "ai_ranking.svg", "AI pool · 12-1 momentum ranking",
               f"closes through {rows[0]['asof_close']} · the ranking the next decision would use", bars,
               marks=marks, legend=[(held_col, "held"), (out_col, "not held")])


def allocation_from_nav():
    """Sleeve weights at the last close: units x last close, read from the ledger files only."""
    pos = list(csv.DictReader(open(LEDGER / "positions.csv"))) if (LEDGER / "positions.csv").exists() else []
    px_p = LEDGER / "last_close.csv"
    if not pos or not px_p.exists():
        return
    px = {r["ticker"]: float(r["close"]) for r in csv.DictReader(open(px_p))}
    val = {}
    for r in pos:
        sl = "ai" if r["sleeve"] in AI_SLEEVES else r["sleeve"]
        val[sl] = val.get(sl, 0) + float(r["units"]) * px[r["ticker"]]
    tot = sum(val.values())
    rows = []
    for name, s in CFG["sleeves"].items():
        w = val.get(name, 0) / tot * 100
        t = s["target"] * 100
        rows.append((name.replace("_", " + ") if name == "health_energy" else name, w, COLORS[1], f"  target {t:.0f}%"))
    hbar_chart(OUTPUT / "allocation.svg", "Sleeve weights at the last close",
               f"as of {open(px_p).read().splitlines()[1].split(',')[0]} · a holding off target by more than 50% (relative) resets all sleeves",
               rows, fmt="{:.1f}%")


def main():
    OUTPUT.mkdir(exist_ok=True)
    nav_chart(); ranking_chart(); allocation_from_nav()


if __name__ == "__main__":
    main()
