"""Daily ledger update, run after the US close. Idempotent: a trading day already recorded is skipped.

The ledger stores UNITS. Level = sum(units x adjusted close). Rules fire on calendar flags computed from the
previous recorded trading day, so a missed run still fires the event on the next run:
  - first trading day of January: annual AI selection (rank, buffer, caps, market switch)
  - first trading day of Apr/Jul/Oct: quarterly AI check (stop, single-name trim)
  - first trading day of every month: market switch check
  - every day: 50% relative drift band between holdings (AI sleeve counted as one)
Signals use closes before the day; trades execute at the day's close; 10 bp per traded dollar.
If any needed close is missing, nothing is recorded for that day: a missing day beats an estimated one.
"""
from __future__ import annotations
import csv, sys
import pandas as pd
from .common import (CFG, LEDGER, POOL, PARK, fixed_targets, all_tickers, download, momentum, ranks, above_ma,
                     read_json, write_json, et_today)
from .rules import annual_selection, cap_redistribute, EXIT, CAP

POS, NAV, TRD, STATE = LEDGER / "positions.csv", LEDGER / "nav.csv", LEDGER / "trades.csv", LEDGER / "state.json"
PRE, RANK = LEDGER / "pre_launch_units.csv", LEDGER / "ai_ranking_latest.csv"
INC = pd.Timestamp(CFG["meta"]["inception_date"])
BENCH, COMP = CFG["meta"]["benchmark"], CFG["meta"]["comparisons"]
AI_T = CFG["sleeves"]["ai"]["target"]
BAND = CFG["rebalance"]["relative_band"]
BP = CFG["meta"]["cost_bp_per_side"] / 1e4
AI_SLEEVES = ("ai", "ai_park", "ai_park_switch")
NAV_COLS = ["date", "level", BENCH.lower(), *[c.lower() for c in COMP], "pre_launch", "ai_weight", "ai_names", "market_switch", "events"]
TRD_COLS = ["date", "ticker", "sleeve", "units_before", "units_after", "price", "value_change", "reason"]


def read_pos():
    return {(r["ticker"], r["sleeve"]): float(r["units"]) for r in csv.DictReader(open(POS))} if POS.exists() else {}


def write_pos(pos):
    with open(POS, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker", "sleeve", "units"])
        for (t, s), u in sorted(pos.items(), key=lambda x: (x[0][1], x[0][0])):
            if u > 1e-12:
                w.writerow([t, s, f"{u:.10f}"])


def append(path, cols, rows):
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerows(rows)


def last_date():
    if not NAV.exists():
        return None
    rows = list(csv.DictReader(open(NAV)))
    return pd.Timestamp(rows[-1]["date"]) if rows else None


def open_books(P):
    """Inception: target weights from inception_plan.csv -> units at the inception close. Base 100."""
    px = P.loc[INC]
    plan = list(csv.DictReader(open(LEDGER / "inception_plan.csv")))
    need = sorted({r["ticker"] for r in plan} | {BENCH, *COMP})
    pre = {r["ticker"]: float(r["weight"]) for r in csv.DictReader(open(LEDGER / "pre_launch_holdings.csv"))}
    miss = [t for t in need + [t for t in pre if t != "CASH"] if pd.isna(px.get(t))]
    if miss:
        print(f"WARNING: inception close missing for {miss}; books not opened."); return False
    pos, trades = {}, []
    for r in plan:
        t, s, wgt = r["ticker"], r["sleeve"], float(r["target_weight"])
        u = wgt * 100 / px[t]
        pos[(t, s)] = u
        trades.append({"date": INC.date(), "ticker": t, "sleeve": s, "units_before": 0, "units_after": round(u, 10),
                       "price": round(px[t], 4), "value_change": round(wgt * 100, 4), "reason": "inception"})
    write_pos(pos)
    with open(PRE, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["ticker", "units"])
        for t, wgt in pre.items():
            w.writerow([t, f"{(wgt * 100 if t == 'CASH' else wgt * 100 / px[t]):.10f}"])
    ai_names = sorted({t for (t, s) in pos if s == "ai"})
    write_json(STATE, {"held": ai_names, "halved": [], "market_switch_on": above_ma(P, INC, BENCH),
                       "bench_base": {t: float(px[t]) for t in [BENCH, *COMP]}})
    append(TRD, TRD_COLS, trades)
    append(NAV, NAV_COLS, [{"date": INC.date(), "level": 100.0, BENCH.lower(): 100.0, **{c.lower(): 100.0 for c in COMP},
                            "pre_launch": 100.0, "ai_weight": round(AI_T, 4), "ai_names": len(ai_names),
                            "market_switch": "on" if above_ma(P, INC, BENCH) else "off", "events": "inception"}])
    print(f"{INC.date()} books opened at 100 ({len(pos)} positions, {len(ai_names)} AI names)")
    return True


def process_day(P, d, prev):
    px = P.loc[d]
    hist = P[P.index < d]
    pos, st = read_pos(), read_json(STATE, {})
    need = {t for (t, _) in pos} | {BENCH, *COMP}
    pre = {r["ticker"]: float(r["units"]) for r in csv.DictReader(open(PRE))}
    need |= {t for t in pre if t != "CASH"}
    miss = sorted(t for t in need if pd.isna(px.get(t)))
    if miss:
        print(f"WARNING: {d.date()} not recorded, missing closes for {miss}"); return False
    val = {k: u * px[k[0]] for k, u in pos.items()}
    nav = sum(val.values())
    new = dict(val)                      # target dollar values after today's trades
    events, reasons = [], {}
    month = d.month != prev.month
    year = d.year != prev.year and d.month == CFG["calendar"]["annual_selection_month"]
    quarter = month and d.month in CFG["calendar"]["quarterly_months"]
    ai_keys = lambda: [k for k in new if k[1] in AI_SLEEVES]
    V = lambda: sum(new[k] for k in ai_keys())
    mom = momentum(hist); rk = ranks(mom)
    switch_was = st.get("market_switch_on", True)
    switch_on = above_ma(P, d, BENCH) if month else switch_was

    def set_ai(frac, why):
        Vt = V()
        for k in ai_keys():
            new[k] = 0.0
        for t, f in frac.items():
            key = (PARK, "ai_park") if t == "PARK" else (t, "ai")
            new[key] = new.get(key, 0.0) + f * Vt
            reasons[key] = why

    if year:
        held = st.get("held", [])
        cur = {t: new.get((t, "ai"), 0.0) for t in held}
        frac, names, entr, exits = annual_selection(mom, held, cur)
        set_ai(frac, "annual selection")
        st["held"], st["halved"] = names, []
        events.append(f"annual selection: in {' '.join(entr) or '-'}; out {' '.join(exits) or '-'}")
        if not switch_on:
            for t in names:
                h = new[(t, "ai")] / 2; new[(t, "ai")] -= h
                new[(PARK, "ai_park_switch")] = new.get((PARK, "ai_park_switch"), 0) + h
                reasons[(t, "ai")] = reasons[(PARK, "ai_park_switch")] = "annual selection + market switch off"
            events.append("market switch off: half of AI sleeve in SPY")
    elif quarter:
        halved = set(st.get("halved", []))
        for t in st.get("held", []):
            k = (t, "ai")
            if new.get(k, 0) > 0 and t not in halved and not above_ma(P, d, t) and rk.get(t, 99) > EXIT:
                h = new[k] / 2; new[k] -= h
                new[(PARK, "ai_park")] = new.get((PARK, "ai_park"), 0) + h
                halved.add(t); reasons[k] = reasons[(PARK, "ai_park")] = "quarterly stop: below 10m MA and rank > 12"
                events.append(f"stop halves {t}")
        st["halved"] = sorted(halved)
        Vt = V()
        names = [t for t in st.get("held", []) if new.get((t, "ai"), 0) > 0]
        if Vt > 0 and any(new[(t, "ai")] / Vt > CAP + 1e-9 for t in names):
            frac = {t: new[(t, "ai")] / Vt for t in names}
            frac["PARK"] = (new.get((PARK, "ai_park"), 0)) / Vt
            sw = new.get((PARK, "ai_park_switch"), 0) / Vt
            frac = cap_redistribute(frac, CAP, names)
            for t in names:
                if abs(frac[t] * Vt - new[(t, "ai")]) > 1e-9:
                    reasons[(t, "ai")] = "quarterly trim: above 20% of AI sleeve"
                new[(t, "ai")] = frac[t] * Vt
            new[(PARK, "ai_park")] = frac.get("PARK", 0) * Vt
            new[(PARK, "ai_park_switch")] = sw * Vt
            events.append("single-name trim")
    if month and not year and switch_on != switch_was:
        names = [t for t in st.get("held", []) if new.get((t, "ai"), 0) > 0]
        if not switch_on:
            for t in names:
                h = new[(t, "ai")] / 2; new[(t, "ai")] -= h
                new[(PARK, "ai_park_switch")] = new.get((PARK, "ai_park_switch"), 0) + h
                reasons[(t, "ai")] = reasons[(PARK, "ai_park_switch")] = "market switch off: SPY below 10m MA"
            events.append("market switch off: half of AI sleeve in SPY")
        else:
            back = new.get((PARK, "ai_park_switch"), 0); tot = sum(new[(t, "ai")] for t in names)
            if back > 0 and tot > 0:
                for t in names:
                    new[(t, "ai")] += back * new[(t, "ai")] / tot
                    reasons[(t, "ai")] = "market switch on: SPY back above 10m MA"
                new[(PARK, "ai_park_switch")] = 0.0
                reasons[(PARK, "ai_park_switch")] = "market switch on: SPY back above 10m MA"
            events.append("market switch on: AI sleeve fully invested")
    st["market_switch_on"] = switch_on

    # drift band between holdings (AI sleeve as one), checked daily as in the backtest
    tgt = fixed_targets()
    cur_w = {t: sum(v for (tt, s), v in new.items() if tt == t and s == sl) / nav for t, (sl, _) in tgt.items()}
    cur_w["AI"] = V() / nav
    tw = {t: w for t, (_, w) in tgt.items()}; tw["AI"] = AI_T
    drift = {t: cur_w[t] / tw[t] - 1 for t in tw}
    if any(abs(v) > BAND for v in drift.values()):
        worst = max(drift, key=lambda t: abs(drift[t]))
        scale = AI_T * nav / V()
        for k in ai_keys():
            new[k] *= scale; reasons.setdefault(k, "band rebalance")
        for t, (sl, w) in tgt.items():
            new[(t, sl)] = w * nav; reasons.setdefault((t, sl), "band rebalance")
        events.append(f"band rebalance ({worst} drift {drift[worst]:+.0%})")

    traded = sum(abs(new.get(k, 0) - val.get(k, 0)) for k in set(new) | set(val))
    cost = traded * BP
    keep = 1 - cost / nav if nav > 0 else 1
    trades, newpos = [], {}
    for k in sorted(set(new) | set(val)):
        u_new = new.get(k, 0) / px[k[0]] * keep
        u_old = pos.get(k, 0)
        newpos[k] = u_new
        if abs(new.get(k, 0) - val.get(k, 0)) > 1e-9:
            trades.append({"date": d.date(), "ticker": k[0], "sleeve": k[1], "units_before": round(u_old, 10),
                           "units_after": round(u_new, 10), "price": round(px[k[0]], 4),
                           "value_change": round(new.get(k, 0) - val.get(k, 0), 4), "reason": reasons.get(k, "")})
    level = sum(u * px[t] for (t, _), u in newpos.items())
    if trades:
        append(TRD, TRD_COLS, trades)
    write_pos(newpos); write_json(STATE, st)
    base = st["bench_base"]
    pre_level = sum(u if t == "CASH" else u * px[t] for t, u in pre.items())
    ai_w = sum(u * px[t] for (t, s), u in newpos.items() if s in AI_SLEEVES) / level
    append(NAV, NAV_COLS, [{"date": d.date(), "level": round(level, 4), BENCH.lower(): round(100 * px[BENCH] / base[BENCH], 4),
                            **{c.lower(): round(100 * px[c] / base[c], 4) for c in COMP}, "pre_launch": round(pre_level, 4),
                            "ai_weight": round(ai_w, 4), "ai_names": sum(1 for (t, s), u in newpos.items() if s == "ai" and u > 0),
                            "market_switch": "on" if switch_on else "off", "events": "; ".join(events)}])
    print(f"{d.date()} level {level:.4f}" + (f" | {'; '.join(events)} | cost {cost:.4f}" if events else ""))
    return True


def write_ranking(P, d):
    """Preview: the ranking a decision on the next trading day would see (closes through d)."""
    hist = P[P.index <= d]
    nxt = d + pd.Timedelta(days=1)
    mom = momentum(hist); rk = ranks(mom)
    st = read_json(STATE, {})
    pos = read_pos()
    held = set(st.get("held", []))
    with open(RANK, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["asof_close", "ticker", "mom_12_1", "rank", "above_10m_ma", "chip", "held", "weight_in_portfolio", "zone"])
        lvl = sum(u * P.loc[d, t] for (t, _), u in pos.items())
        for t in mom.index:
            wt = pos.get((t, "ai"), 0) * P.loc[d, t] / lvl if lvl else 0
            zone = "top 8" if rk[t] <= CFG["ai"]["select_n"] else "buffer 9-12" if rk[t] <= EXIT else "outside 12"
            w.writerow([d.date(), t, round(mom[t], 4), rk[t], above_ma(P, nxt, t), t in CFG["ai"]["chips"], t in held, round(wt, 4), zone])
        for t in POOL:
            if t not in mom.index:
                w.writerow([d.date(), t, "", "", "", t in CFG["ai"]["chips"], t in held, 0, "too new to rank"])


def main():
    P = download(all_tickers(), period="3y")
    P = P[P.index <= pd.Timestamp(et_today())]
    import datetime as dt
    from .common import ET
    now = dt.datetime.now(ET)
    if P.index[-1] == pd.Timestamp(et_today()) and (now.hour, now.minute) < (16, 15):
        P = P.iloc[:-1]                  # today's bar is still live: never record an intraday price
    if P.index[-1] < INC:
        print("Before inception; nothing to do."); return
    if not NAV.exists():
        if INC not in P.index:
            print(f"WARNING: no bar for inception day {INC.date()} yet."); return
        if not open_books(P):
            return
    prev = last_date()
    for d in P.index[P.index > prev]:
        if not process_day(P, d, prev):
            break
        prev = d
    d = last_date()
    write_ranking(P, d)
    with open(LEDGER / "last_close.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "ticker", "close"])
        for t in sorted({t for (t, _) in read_pos()}):
            w.writerow([d.date(), t, round(float(P.loc[d, t]), 4)])


if __name__ == "__main__":
    sys.exit(main())
