"""One-time: turn the pre-launch holdings into the inception target weights, using only closes before inception day.

Transition rule (METHODOLOGY §4.9): the pre-launch AI names are treated as 'held'. The annual-selection rule
then runs once: held names ranked 12 or better stay with their existing relative weights; open slots up to 8
go to the best-ranked names not held; chips cap and single-name cap apply; the market switch applies.
Writes data/ledger/inception_plan.csv. It is committed before the inception close, so the weights are fixed
before the prices that execute them exist.
"""
from __future__ import annotations
import csv
import pandas as pd
from .common import CFG, LEDGER, POOL, CHIPS, fixed_targets, all_tickers, download, momentum, ranks, above_ma
from .rules import annual_selection

INC = pd.Timestamp(CFG["meta"]["inception_date"])


def main():
    pre = {r["ticker"]: float(r["weight"]) for r in csv.DictReader(open(LEDGER / "pre_launch_holdings.csv"))}
    P = download(all_tickers(), period="3y")
    hist = P[P.index < INC]
    asof = hist.index[-1].date()
    mom = momentum(hist)
    rk = ranks(mom)
    held = [k for k in POOL if pre.get(k, 0) > 0]
    frac, names, entr, exits = annual_selection(mom, held, {k: pre[k] for k in held})
    switch_on = above_ma(P, INC, CFG["meta"]["benchmark"])
    if not switch_on:
        for k in names:
            frac[k] *= 0.5
        frac["PARK"] = frac.get("PARK", 0) + 0.5 * sum(frac[k] for k in names)
    ai_t = CFG["sleeves"]["ai"]["target"]
    rows = []
    for k, f in sorted(frac.items(), key=lambda x: -x[1]):
        if f <= 0:
            continue
        t = CFG["ai"]["park"] if k == "PARK" else k
        why = ("park" if k == "PARK" else
               f"held, rank {rk[k]} <= {CFG['ai']['exit_rank']}" if k not in entr else f"entrant, rank {rk[k]}")
        rows.append({"ticker": t, "sleeve": "ai_park_switch" if k == "PARK" else "ai", "target_weight": round(f * ai_t, 6), "reason": why})
    for t, (sl, w) in fixed_targets().items():
        rows.append({"ticker": t, "sleeve": sl, "target_weight": w, "reason": "fixed sleeve"})
    with open(LEDGER / "inception_plan.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ticker", "sleeve", "target_weight", "reason"])
        w.writeheader(); w.writerows(rows)
    with open(LEDGER / "inception_ranking.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["asof_close", "ticker", "mom_12_1", "rank", "above_10m_ma", "chip", "pre_launch_weight", "decision"])
        for k in mom.index:
            dec = "keep" if k in names and k not in entr else "enter" if k in entr else "exit" if k in exits else "not held"
            w.writerow([asof, k, round(mom[k], 4), rk[k], above_ma(P, INC, k), k in CHIPS, pre.get(k, 0), dec])
        for k in POOL:
            if k not in mom.index:
                w.writerow([asof, k, "", "", "", k in CHIPS, pre.get(k, 0), "too new to rank" if pre.get(k, 0) == 0 else "exit (unrankable)"])
    tot = sum(r["target_weight"] for r in rows)
    chips = sum(frac.get(k, 0) for k in CHIPS)
    print(f"signals as of close {asof}; SPY above 10m MA: {switch_on}")
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"total {tot:.4f}; AI names {len(names)}; chips share of AI sleeve {chips:.1%}; exits {exits}; entrants {entr}")


if __name__ == "__main__":
    main()
