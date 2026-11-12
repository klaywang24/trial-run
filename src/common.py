"""Shared pieces: config, ledger paths, price download, and the two signals (12-1 momentum, 10-month trend).

Every signal for a decision on trading day D uses closes from BEFORE D only. Trades execute at D's close.
"""
from __future__ import annotations
import json, pathlib, datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import yaml

ET = ZoneInfo("America/New_York")
ROOT = pathlib.Path(__file__).resolve().parents[1]
CFG = yaml.safe_load(open(ROOT / "config.yaml"))
LEDGER = ROOT / "data/ledger"
OUTPUT = ROOT / "output"

AI = CFG["ai"]
POOL: list[str] = AI["pool"]
CHIPS: list[str] = AI["chips"]
PARK: str = AI["park"]


def fixed_targets() -> dict[str, tuple[str, float]]:
    """ticker -> (sleeve, target share of portfolio) for every non-rotating holding."""
    out = {}
    for name, s in CFG["sleeves"].items():
        for t, w in (s.get("holdings") or {}).items():
            out[t] = (name, float(w))
    return out


def all_tickers() -> list[str]:
    extra = [CFG["meta"]["benchmark"], *CFG["meta"]["comparisons"], PARK]
    return sorted(set(POOL) | set(fixed_targets()) | set(extra))


def download(tickers, period="3y") -> pd.DataFrame:
    """Adjusted daily closes from Yahoo, indexed by New York trading date. Tickers that come back empty are
    retried one by one (Yahoo intermittently answers 'possibly delisted' for live tickers)."""
    import os, time
    import yfinance as yf
    period = os.environ.get("TRIAL_RUN_PERIOD", period)
    tickers = sorted(set(tickers))

    def grab(ts):
        raw = yf.download(ts, period=period, auto_adjust=True, progress=False, group_by="ticker", threads=True)
        out = {}
        for t in ts:
            try:
                s = raw[t]["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw["Close"]
            except KeyError:
                continue
            if s.dropna().size:
                out[t] = s
        return out

    cols = grab(tickers)
    for attempt in range(3):
        miss = [t for t in tickers if t not in cols]
        if not miss:
            break
        time.sleep(3 * (attempt + 1))
        for t in miss:
            cols.update(grab([t]))
    P = pd.DataFrame(cols)
    idx = P.index
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert(ET).tz_localize(None)
    P.index = pd.DatetimeIndex(idx.normalize())
    return P.sort_index()


def momentum(hist: pd.DataFrame, names=None) -> pd.Series:
    """12-1 momentum from closes strictly before the decision day. Names with <253 days are not ranked."""
    look, skip, need = AI["momentum_lookback_days"], AI["momentum_skip_days"], AI["min_history_days"]
    out = {}
    for k in (names or POOL):
        if k not in hist:
            continue
        s = hist[k].dropna()
        if len(s) >= need:
            out[k] = s.iloc[-1 - skip] / s.iloc[-1 - look] - 1
    return pd.Series(out, dtype=float).sort_values(ascending=False)


def ranks(m: pd.Series) -> pd.Series:
    return pd.Series(range(1, len(m) + 1), index=m.index)


def above_ma(P: pd.DataFrame, d: pd.Timestamp, k: str) -> bool:
    """Month-end close above the average of the last 10 month-ends, using months before D's month.
    Fewer than 10 month-ends of history counts as 'above' (no signal yet)."""
    n = AI["ma_months"]
    m = P[k].dropna().resample("ME").last()
    m = m[m.index < d.replace(day=1)].dropna()
    if len(m) < n:
        return True
    return bool(m.iloc[-1] > m.iloc[-n:].mean())


def read_json(p, default):
    p = pathlib.Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def write_json(p, obj):
    pathlib.Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def et_today() -> str:
    return dt.datetime.now(ET).date().isoformat()
