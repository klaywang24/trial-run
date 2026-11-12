"""Reproducible backtest behind methodology v1.0. Reference only: the pool was chosen in 2026, so every number
here carries look-ahead and survivorship bias. Compare rules with each other; never read a return as an expectation.

Run:  python -m backtest.run_backtest      (downloads Yahoo adjusted closes, ~2 minutes)
Window 2016-01-04 to 2026-11-10. Signals use closes before each day; 10 bp per side inside the AI sleeve,
5 bp per side between sleeves. Writes backtest/results/*.csv and backtest/charts/*.svg.
"""
from __future__ import annotations
import pathlib
import numpy as np
import pandas as pd
from src.common import download
from src.svg import line_chart, hbar_chart, COLORS

HERE = pathlib.Path(__file__).resolve().parent
RES, CH = HERE / "results", HERE / "charts"
START, END = "2016-01-04", "2026-11-10"
FULL_POOL = ["AAPL", "NVDA", "MSFT", "META", "AMZN", "AMD", "NET", "MU", "LRCX", "APP", "GEV", "LITE", "PLTR", "TSM", "AVGO", "SPCX", "GOOGL"]
CHIPS = ["NVDA", "AMD", "MU", "LRCX", "TSM", "AVGO", "LITE"]
REST = {"GRMN": .06, "MSGK": .04, "V": .04, "MA": .03, "AXP": .03, "LLY": .05, "XLE": .05, "SPDV": .10, "KO": .05, "BRK-B": .05}
PRE = {"NVDA": 7.5, "MU": 6, "AAPL": 5.8, "TSM": 5.5, "PLTR": 5.5, "MSGK": 5.5, "NET": 5.4, "LLY": 5, "META": 5, "KO": 5, "GRMN": 5,
       "BRK-B": 4, "MSFT": 4, "V": 5, "AVGO": 4.5, "GEV": 4, "MA": 3, "AXP": 3, "LITE": 2, "AMZN": 1}


class Engine:
    def __init__(self, P, pool, cost_bp=10.0):
        self.pool = pool; self.cols = pool + ["SPY"]; self.cost = cost_bp / 1e4
        self.px = P[self.cols]; self.R = self.px.pct_change().loc[START:END]; self.dates = self.R.index
        self.mo = self.px.resample("ME").last()

    def hist(self, d): return self.px.loc[:d].iloc[:-1]
    def listed(self, d, n): h = self.hist(d); return [k for k in self.pool if h[k].count() >= n]

    def mom(self, d, look=252, skip=21):
        h = self.hist(d); out = {}
        for k in self.listed(d, look + 1):
            s = h[k].dropna(); out[k] = s.iloc[-1 - skip] / s.iloc[-1 - look] - 1
        return pd.Series(out, dtype=float)

    def above_ma(self, d, k, n=10):
        m = self.mo[k][self.mo.index < d.replace(day=1)].dropna()
        return True if len(m) < n else bool(m.iloc[-1] > m.iloc[-n:].mean())

    def run(self, rule):
        w = pd.Series(0.0, index=self.cols); out = []; turn = 0.0; st = {}
        Rv = self.R.fillna(0.0)
        for i, d in enumerate(self.dates):
            p = self.dates[i - 1] if i else None
            fl = {"first": i == 0, "month": i == 0 or d.month != p.month,
                  "quarter": i == 0 or (d.month != p.month and d.month in (1, 4, 7, 10)), "year": i == 0 or d.year != p.year}
            nw = rule(self, d, w, st, fl); cost = 0.0
            if nw is not None:
                nw = nw.reindex(self.cols).fillna(0.0); nw = nw / nw.sum()
                t = float((nw - w).abs().sum() / 2)
                if i: turn += t; cost = 2 * t * self.cost
                w = nw
            r = Rv.loc[d]; out.append(float((w * r).sum()) - cost); w = w * (1 + r); w = w / w.sum()
        return pd.Series(out, index=self.dates), turn / (len(self.dates) / 252)


def cap_redistribute(w, cap, names):
    w = w.copy()
    for _ in range(20):
        over = [k for k in names if w[k] > cap + 1e-12]
        if not over: break
        ex = sum(w[k] - cap for k in over)
        for k in over: w[k] = cap
        under = [k for k in names if 0 < w[k] < cap - 1e-12]
        if not under: w["SPY"] += ex; break
        tot = sum(w[k] for k in under)
        for k in under: w[k] += ex * w[k] / tot
    return w


def group_cap(w, pool, cap):
    w = w.copy(); g = [k for k in CHIPS if k in w and w[k] > 0]; s = sum(w[k] for k in g)
    if s <= cap: return w
    ex = s - cap
    for k in g: w[k] *= cap / s
    oth = [k for k in pool if k not in CHIPS and w[k] > 0]
    if oth:
        t = sum(w[k] for k in oth)
        for k in oth: w[k] += ex * w[k] / t
    else: w["SPY"] += ex
    return w


def eq_all():
    def f(e, d, w, st, fl):
        if not fl["quarter"]: return None
        a = e.listed(d, 63); return pd.Series(1 / len(a), index=a)
    return f


def topn(N=8, buf=None, drift=False, cap=0.15, look=252, stop=False, bull=None, chips=None):
    def f(e, d, w, st, fl):
        sel = fl["year"]; new_w = None
        if sel:
            m = e.mom(d, look=look).sort_values(ascending=False); rank = pd.Series(range(1, len(m) + 1), index=m.index)
            held = st.get("held", [])
            keep = [k for k in held if k in rank.index and buf is not None and rank[k] <= buf]
            names = list(keep)
            for k in m.index:
                if len(names) >= N: break
                if k not in names: names.append(k)
            entr = [k for k in names if k not in keep]
            t = pd.Series(0.0, index=e.cols)
            if drift and keep:
                cur = w[keep]; cur = cur / cur.sum() if cur.sum() > 0 else pd.Series(1 / len(keep), index=keep)
                for k in entr: t[k] = 1 / N
                for k in keep: t[k] = cur[k] * (1 - len(entr) / N)
            else:
                for k in names: t[k] = 1 / len(names)
            if chips: t = group_cap(t, e.pool, chips)
            t = cap_redistribute(t, cap, names)
            st["held"] = names; st["halved"] = set(); new_w = t
        elif fl["quarter"] and (drift or stop):
            t = w.copy(); changed = False
            if stop:
                m = e.mom(d, look=look).sort_values(ascending=False); rank = pd.Series(range(1, len(m) + 1), index=m.index)
                for k in st.get("held", []):
                    if t[k] > 0 and k not in st["halved"] and not e.above_ma(d, k) and rank.get(k, 99) > (buf or N):
                        t["SPY"] += t[k] / 2; t[k] /= 2; st["halved"].add(k); changed = True
            if drift and (t[e.pool] > cap + 1e-9).any():
                t = cap_redistribute(t, cap, [k for k in st.get("held", []) if t[k] > 0]); changed = True
            new_w = t if changed else None
        if bull and fl["month"]:
            on = e.above_ma(d, "SPY"); base = new_w if new_w is not None else w.copy(); was = st.get("bull_on", True)
            if sel or on != was:
                stocks = base[e.pool].sum()
                if not on and (sel or was):
                    base[e.pool] *= 0.5; base["SPY"] = 1 - base[e.pool].sum()
                elif on and not was and not sel:
                    add = min(base["SPY"], stocks)
                    if stocks > 0: base[e.pool] *= (stocks + add) / stocks; base["SPY"] -= add
                new_w = base
            st["bull_on"] = on
        return new_w
    return f


def band_backtest(R, target_fn, band=0.5, cost_bp=5.0, rebal=None):
    """Sleeve-level portfolio: full reset to target when any holding drifts >band (relative), checked daily."""
    dates = R.index; w = pd.Series(0.0, index=R.columns); out = []; turn = 0.0; tgt = None
    for i, d in enumerate(dates):
        newt = None
        if i == 0 or (rebal == "Q" and d.month != dates[i - 1].month and d.month in (1, 4, 7, 10)):
            newt = pd.Series(target_fn(d))
        elif band is not None and tgt is not None:
            cur = pd.Series(target_fn(d))
            if set(cur[cur > 0].index) != set(tgt[tgt > 0].index): newt = cur
            else:
                rel = (w.reindex(tgt.index).fillna(0) / tgt.where(tgt > 0)) - 1
                if (rel.abs() > band).any(): newt = cur
        cost = 0.0
        if newt is not None:
            newt = newt.reindex(R.columns).fillna(0); t = (newt - w).abs().sum() / 2
            if i > 0: turn += t; cost = t * 2 * cost_bp / 1e4
            w = newt.copy(); tgt = newt.copy()
        day = R.loc[d].fillna(0); out.append(float((w * day).sum()) - cost)
        w = w * (1 + day); s = w.sum(); w = w / s if s else w
    return pd.Series(out, index=dates), turn / (len(dates) / 252)


def stats(r, b):
    yrs = len(r) / 252; nav = (1 + r).cumprod(); bn = (1 + b).cumprod()
    cagr = nav.iloc[-1] ** (1 / yrs) - 1; bc = bn.iloc[-1] ** (1 / yrs) - 1
    dd = lambda a, c: ((nav.loc[a:c] / nav.loc[a:c].cummax() - 1).min()) * 100
    y = (1 + r).groupby(r.index.year).prod() - 1; yb = (1 + b).groupby(b.index.year).prod() - 1
    return {"cagr_pct": cagr * 100, "max_drawdown_pct": ((nav / nav.cummax() - 1).min()) * 100,
            "drawdown_2020_pct": dd("2020-02-19", "2020-04-30"), "drawdown_2022_pct": dd("2022-01-03", "2022-12-30"),
            "drawdown_2025_pct": dd("2025-01-02", "2025-12-31"),
            "excess_vs_spy_pct": (cagr - bc) * 100, "tracking_error_pct": (r - b).std() * np.sqrt(252) * 100,
            "worst_calendar_year_vs_spy_pp": (y - yb).min() * 100}


RULES = {
    "A0 whole pool, equal weight": lambda: eq_all(),
    "B1 top 8, no buffer": lambda: topn(8),
    "B3 top 8 + buffer 12 + let winners run": lambda: topn(8, buf=12, drift=True, cap=0.20),
    "B4 = B3 + quarterly stop": lambda: topn(8, buf=12, drift=True, cap=0.20, stop=True),
    "B5m = B3 + monthly market switch": lambda: topn(8, buf=12, drift=True, cap=0.20, bull="monthly"),
    "B7 = B3 + chips cap + stop + switch (v1.0)": lambda: topn(8, buf=12, drift=True, cap=0.20, chips=0.60, stop=True, bull="monthly"),
}


def main():
    RES.mkdir(exist_ok=True); CH.mkdir(exist_ok=True)
    tick = sorted(set(FULL_POOL) | set(REST) | set(PRE) | {"SPY", "QQQ", "SMH", "BIL"})
    import os; os.environ.setdefault("TRIAL_RUN_PERIOD", "max")
    P = download(tick).loc["2014-01-01":END]
    spy = P["SPY"].pct_change().loc[START:END]

    # 1) AI sleeve rules
    E = Engine(P, FULL_POOL)
    ser, rows = {}, {}
    for name, mk in RULES.items():
        r, to = E.run(mk()); ser[name] = r
        rows[name] = {**stats(r, spy), "turnover_pct": to * 100}
    for t in ["SPY", "QQQ", "SMH"]:
        r = P[t].pct_change().loc[START:END]; ser[f"ref {t}"] = r; rows[f"ref {t}"] = {**stats(r, spy), "turnover_pct": 0.0}
    pd.DataFrame(rows).T.round(2).to_csv(RES / "ai_sleeve_rules.csv")

    # 2) leave the biggest winners out
    lo = {}
    for lab, drop in {"full pool": [], "without NVDA": ["NVDA"], "without NVDA, APP, PLTR": ["NVDA", "APP", "PLTR"]}.items():
        e2 = Engine(P, [k for k in FULL_POOL if k not in drop])
        for name in ["A0 whole pool, equal weight", "B4 = B3 + quarterly stop", "B7 = B3 + chips cap + stop + switch (v1.0)"]:
            r, to = e2.run(RULES[name]()); s = stats(r, spy)
            lo[(lab, name)] = {"cagr_pct": s["cagr_pct"], "max_drawdown_pct": s["max_drawdown_pct"], "turnover_pct": to * 100}
    pd.DataFrame(lo).T.round(2).to_csv(RES / "leave_winners_out.csv")

    # 3) whole portfolio: AI sleeve as one asset at 40%
    R = P.pct_change().loc[START:END].copy(); R["CASH"] = 0.0
    port, pser = {}, {}
    def mk(ai_col, rem):
        def fn(d):
            t, miss = {}, 0.0
            for k, v in REST.items():
                if pd.notna(P.at[d, k]): t[k] = v
                else: miss += v
            t[ai_col] = 0.40; t["SPY"] = t.get("SPY", 0) + miss; t[rem] = t.get(rem, 0) + 0.10
            return t
        return fn
    for name in ["B4 = B3 + quarterly stop", "B7 = B3 + chips cap + stop + switch (v1.0)", "A0 whole pool, equal weight"]:
        R[name] = ser[name]
        r, to = band_backtest(R, mk(name, "BIL")); pser[f"AI {name.split(' ')[0]}, reserve in BIL"] = r
        port[f"AI {name.split(' ')[0]}, reserve in BIL"] = {**stats(r, spy), "turnover_between_sleeves_pct": to * 100}
    cash = (100 - sum(PRE.values())) / 100
    cur = lambda d: {**{k: v / 100 for k, v in PRE.items() if pd.notna(P.at[d, k])},
                     "SPY": sum(v for k, v in PRE.items() if pd.isna(P.at[d, k])) / 100, "CASH": cash}
    r, to = band_backtest(R, cur, band=None, rebal="Q"); pser["Pre-launch holdings, quarterly rebalance"] = r
    port["Pre-launch holdings, quarterly rebalance"] = {**stats(r, spy), "turnover_between_sleeves_pct": to * 100}
    pser["SPY"] = spy; port["SPY"] = {**stats(spy, spy), "turnover_between_sleeves_pct": 0.0}
    pd.DataFrame(port).T.round(2).to_csv(RES / "portfolio.csv")
    yr = pd.DataFrame({k: ((1 + v).groupby(v.index.year).prod() - 1) * 100 for k, v in pser.items()}).round(1)
    yr.to_csv(RES / "portfolio_by_year.csv")

    # charts
    keys = ["AI B7, reserve in BIL", "Pre-launch holdings, quarterly rebalance", "SPY"]
    nav = pd.DataFrame({k: (1 + pser[k]).cumprod() * 100 for k in keys})
    nav = nav.iloc[::3]  # every third day keeps the SVG small
    d = [x.date().isoformat() for x in nav.index]
    lab = {"AI B7, reserve in BIL": "v1.0 rules", "Pre-launch holdings, quarterly rebalance": "Pre-launch", "SPY": "SPY"}
    line_chart(CH / "portfolio_growth.svg", "Backtest · whole portfolio, growth of 100 (log scale)",
               "2016-01 to 2026-11 · AI sleeve 40% on the v1.0 rules · pool picked in 2026: look-ahead bias, compare shapes not levels",
               d, {lab[k]: list(nav[k].round(2)) for k in keys}, log=True, base=100, fmt="{:.0f}")
    dd = {lab[k]: list(((nav[k] / nav[k].cummax() - 1) * 100).round(2)) for k in keys}
    line_chart(CH / "portfolio_drawdown.svg", "Backtest · drawdown from the previous peak (%)",
               "the 2020 crash hits every version alike; the rules help in slow declines such as 2022", d, dd, base=0, fmt="{:.0f}%")
    ar = pd.read_csv(RES / "ai_sleeve_rules.csv", index_col=0)
    bars = [(k.split(" ")[0] if not k.startswith("ref") else k.replace("ref ", ""), ar.at[k, "max_drawdown_pct"],
             COLORS[0] if "v1.0" in k else "#9aa3ad",
             f" · {ar.at[k, 'cagr_pct']:.1f}%/yr · turnover {ar.at[k, 'turnover_pct']:.0f}%") for k in ar.index]
    hbar_chart(CH / "ai_rules_drawdown.svg", "Backtest · AI sleeve alone: max drawdown by rule",
               "each mechanism's job is risk: the buffer cuts turnover, the stop and the switch cut drawdown", bars, fmt="{:.1f}%")
    lw = pd.read_csv(RES / "leave_winners_out.csv", index_col=[0, 1])
    bars = []
    for (pool, rule), r in lw.iterrows():
        short = {"full pool": "all 17", "without NVDA": "no NVDA", "without NVDA, APP, PLTR": "no NVDA/APP/PLTR"}[pool]
        bars.append((f"{short} · {rule.split(' ')[0]}", r["cagr_pct"], COLORS[0] if rule.startswith("B7") else COLORS[1] if rule.startswith("B4") else "#9aa3ad",
                     f" · max drawdown {r['max_drawdown_pct']:.1f}%"))
    hbar_chart(CH / "leave_winners_out.svg", "Backtest · take the biggest winners out of the pool",
               "the return edge needs winners in the pool; the drawdown edge survives without them", bars, fmt="{:.1f}%/yr")
    pd.set_option("display.width", 250)
    for f in ["ai_sleeve_rules", "leave_winners_out", "portfolio"]:
        print(pd.read_csv(RES / f"{f}.csv", index_col=0).round(1).to_string(), "\n")


if __name__ == "__main__":
    main()
