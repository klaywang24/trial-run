"""AI-sleeve rules as pure functions on fractions of the AI sleeve (sum = 1). Same logic as backtest/engine.py.

Keys are tickers plus the special key 'PARK' (SPY held inside the AI sleeve).
"""
from __future__ import annotations
import pandas as pd
from .common import AI, CHIPS

N, EXIT, CAP, CHIPCAP = AI["select_n"], AI["exit_rank"], AI["stock_cap_of_sleeve"], AI["chips_cap_of_sleeve"]


def cap_redistribute(w: dict, cap: float, names: list[str]) -> dict:
    """Cut names above cap to cap and hand the excess pro rata to names below cap; if none, to PARK."""
    w = dict(w)
    for _ in range(50):
        over = [k for k in names if w.get(k, 0) > cap + 1e-12]
        if not over:
            break
        ex = sum(w[k] - cap for k in over)
        for k in over:
            w[k] = cap
        under = [k for k in names if 0 < w.get(k, 0) < cap - 1e-12]
        if not under:
            w["PARK"] = w.get("PARK", 0) + ex
            break
        tot = sum(w[k] for k in under)
        for k in under:
            w[k] += ex * w[k] / tot
    return w


def chips_cap(w: dict) -> dict:
    """Chip names together at most CHIPCAP of the sleeve; excess goes pro rata to non-chip holdings (else PARK)."""
    w = dict(w)
    g = [k for k in CHIPS if w.get(k, 0) > 0]
    s = sum(w[k] for k in g)
    if s <= CHIPCAP:
        return w
    ex = s - CHIPCAP
    for k in g:
        w[k] *= CHIPCAP / s
    oth = [k for k in w if k not in CHIPS and k != "PARK" and w[k] > 0]
    if oth:
        t = sum(w[k] for k in oth)
        for k in oth:
            w[k] += ex * w[k] / t
    else:
        w["PARK"] = w.get("PARK", 0) + ex
    return w


def annual_selection(mom: pd.Series, held: list[str], cur_values: dict) -> tuple[dict, list, list, list]:
    """Return (sleeve fractions, names, entrants, exits).

    held: names currently held; cur_values: their current dollar values (for 'keep relative weights')."""
    rank = pd.Series(range(1, len(mom) + 1), index=mom.index)
    keep = [k for k in held if k in rank.index and rank[k] <= EXIT]
    names = list(keep)
    for k in mom.index:
        if len(names) >= N:
            break
        if k not in names:
            names.append(k)
    entr = [k for k in names if k not in keep]
    w: dict = {}
    if keep:
        tot = sum(cur_values.get(k, 0) for k in keep)
        rel = {k: (cur_values.get(k, 0) / tot if tot > 0 else 1 / len(keep)) for k in keep}
        for k in entr:
            w[k] = 1 / N
        for k in keep:
            w[k] = rel[k] * (1 - len(entr) / N)
    else:
        for k in names:
            w[k] = 1 / len(names)
    w = chips_cap(w)
    w = cap_redistribute(w, CAP, names)
    exits = [k for k in held if k not in names]
    return w, names, entr, exits
