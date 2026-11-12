"""P&L dashboard: output/dashboard.html, one self-contained file (data, logos and scripts inline).

Reads only the ledger: nav.csv for the level and the comparison lines, pnl_by_holding.csv for where each day's
P&L came from, trades.csv for events, data/meta/companies.csv and assets/logos/ for names and logos.
Nothing is estimated: a day that is not in the ledger is not on the page.

Contribution of a holding over a period = sum of its daily pnl (index points) / level at the start of the period.
Because a day's pnl rows add up to that day's level change, the contributions of a period add up to its return.
Run: python -m src.dashboard
"""
from __future__ import annotations
import base64, csv, json, pathlib
from .common import CFG, LEDGER

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "dashboard.html"
SHELL = ROOT / "src" / "dashboard_shell.html"

SLEEVES = {
    "ai": ("AI 产业链", "AI chain"), "ai_park": ("AI 仓暂存 (止损)", "AI sleeve park (stop)"),
    "ai_park_switch": ("AI 仓暂存 (开关)", "AI sleeve park (switch)"), "sports": ("体育", "Sports"),
    "fintech": ("fintech", "Fintech"), "health_energy": ("医疗与能源", "Health care and energy"),
    "income": ("现金流", "Income"), "defense": ("防守", "Defense"), "reserve": ("剩余 (短债)", "Reserve (T-bills)"),
    "cost": ("交易成本", "Trading cost"),
}


def rows(path):
    return list(csv.DictReader(open(path))) if path.exists() else []


def logo(rel):
    p = ROOT / rel if rel else None
    if p and p.exists():
        return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()
    return ""


def build():
    nav = rows(LEDGER / "nav.csv")
    pnl = rows(LEDGER / "pnl_by_holding.csv")
    trades = rows(LEDGER / "trades.csv")
    meta = {r["ticker"]: {"en": r["name_en"], "zh": r["name_zh"], "site": r["website"], "logo": logo(r.get("logo", ""))}
            for r in rows(ROOT / "data" / "meta" / "companies.csv")}
    by_day = {}
    for r in pnl:
        by_day.setdefault(r["date"], []).append([r["ticker"], r["sleeve"], float(r["pnl"]), float(r["ret"]),
                                                 float(r["weight_prev"])])
    events = {}
    for r in trades:
        if r["reason"] and r["reason"] != "inception":
            events.setdefault(r["date"], set()).add(r["reason"])
    data = {
        "inception": CFG["meta"]["inception_date"],
        "asof": nav[-1]["date"] if nav else None,
        "nav": [[r["date"], float(r["level"]), float(r["spy"]), float(r["qqq"]), float(r["pre_launch"]),
                 r["events"], float(r["ai_weight"]), r["market_switch"]] for r in nav],
        "pnl": by_day,
        "meta": meta,
        "sleeves": SLEEVES,
        "trades": {d: sorted(v) for d, v in events.items()},
    }
    shell = SHELL.read_text()
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.write_text(shell.replace("/*__DATA__*/null", blob))
    print(f"dashboard: {len(nav)} days, {len(pnl)} pnl rows -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
