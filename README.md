# Trial Run · 小试牛刀

> A **public research notebook** for one simulated U.S. equity portfolio: a capped AI
> sleeve, a few sleeves the author knows well, and written rules for rotation and
> rebalancing. **It is a test of a method, not a track record**, and nothing here is
> investment advice.

[![License](https://img.shields.io/badge/license-PolyForm--Noncommercial--1.0.0-4a5d3a)](LICENSE)
[![Status](https://img.shields.io/badge/status-setting%20up-b8893e)](#status)
[![Benchmark](https://img.shields.io/badge/benchmark-SPY-2b5f8f)](#the-question)
[![中文](https://img.shields.io/badge/%E4%B8%AD%E6%96%87-README-2b5f8f)](README.zh.md)

---

## The question

Can a portfolio that leans into AI keep up with SPY over the long run, while written
rules (not mood) decide how much AI it holds, which names it holds, and when it trades?

The working answer is a **core and satellite** structure:

| Sleeve | Role |
|---|---|
| AI chain | The return engine. Total exposure capped, single names capped, names rotated by rule |
| Sectors the author knows | Sports and fintech, held because they are understood, not because they are hedges |
| Defensive and cash flow | Holdings that tended to hold up on the AI chain's worst days, plus a dividend sleeve |
| Remainder | SPY or short-term Treasuries |

Exact weights, the rotation pool and the rebalancing thresholds will be published in a
methodology file **before** the forward record starts, and changed only through dated,
labelled commits.

---

## What it promises, and what it does not

**It does not promise** to beat SPY, QQQ or any other index.

**It promises three things:**

1. **Rules before results.** The methodology is committed before the record starts.
   Rule changes and data updates are separate commits, so anyone can check that the
   rules were not tuned to flatter the numbers.
2. **Sources on every number.** Every figure names its data source and date. When a
   number cannot be computed, the notebook says so instead of estimating it.
3. **Backtests are labelled.** Any backtest that uses today's holdings carries
   look-ahead and survivorship bias, and is marked as such. Drawdown, tracking error
   and turnover are treated as more reliable than excess return.

---

## Status

**Setting up.** This repository currently holds only the README and the license. The
methodology, scripts and data will be added once the rules are final.

---

## License

[PolyForm Noncommercial 1.0.0](LICENSE): free for noncommercial use; commercial use
requires a separate license.

## Disclaimer

Everything in this repository is for informational and research purposes only. It is a
simulated portfolio. It is **not investment advice** and recommends no security.
Markets carry risk; make your own decisions.
