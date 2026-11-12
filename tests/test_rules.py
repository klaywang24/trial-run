"""Offline invariants for the AI-sleeve rules. Run: python -m tests.test_rules"""
import pandas as pd
from src.rules import annual_selection, cap_redistribute, chips_cap, N, EXIT, CAP, CHIPCAP

def mom(names):  # descending momentum in the given order
    return pd.Series({k: 1 - i * 0.01 for i, k in enumerate(names)})

POOL = ["LITE", "MU", "AMD", "LRCX", "GEV", "TSM", "NET", "AAPL", "GOOGL", "META", "NVDA", "MSFT", "PLTR", "AMZN", "AVGO", "APP"]

def test_fresh_start_takes_top_8():
    w, names, entr, exits = annual_selection(mom(POOL), [], {})
    assert names == POOL[:N] and entr == names and exits == []
    assert abs(sum(w.values()) - 1) < 1e-9

def test_buffer_keeps_rank_12_and_sells_13():
    held = ["MSFT", "PLTR"]                     # ranks 12 and 13
    w, names, entr, exits = annual_selection(mom(POOL), held, {"MSFT": 1, "PLTR": 1})
    assert "MSFT" in names and "PLTR" in exits and len(names) == N

def test_more_than_8_kept_names_all_stay():
    held = POOL[:EXIT]
    w, names, entr, exits = annual_selection(mom(POOL), held, {k: 1 for k in held})
    assert set(names) == set(held) and entr == []

def test_caps_hold_and_weights_sum_to_one():
    held = ["NVDA", "MU", "TSM", "AAPL"]
    w, names, *_ = annual_selection(mom(POOL), held, {"NVDA": 10, "MU": 1, "TSM": 1, "AAPL": 1})
    assert max(v for k, v in w.items() if k != "PARK") <= CAP + 1e-9
    assert abs(sum(w.values()) - 1) < 1e-9

def test_chips_cap():
    w = chips_cap({"NVDA": .3, "MU": .3, "TSM": .2, "AAPL": .2})
    assert sum(w[k] for k in ["NVDA", "MU", "TSM"]) <= CHIPCAP + 1e-9 and abs(sum(w.values()) - 1) < 1e-9

def test_cap_overflow_goes_to_park_when_everyone_is_capped():
    w = cap_redistribute({"A": .5, "B": .5}, .2, ["A", "B"])
    assert abs(w["PARK"] - .6) < 1e-9

if __name__ == "__main__":
    for k, f in list(globals().items()):
        if k.startswith("test_"):
            f(); print("ok", k)
