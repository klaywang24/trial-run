# Methodology v1.0

> Status: frozen, effective 2026-11-12. The record starts at the 2026-11-12 close, base 100.
> `config.yaml` is the executable copy of this file. Its SHA-256 is stored in `FROZEN.sha256` and checked on
> every automated run. If the two disagree, this file governs.
> This is a research record of a simulated portfolio. It is not investment advice.
> 中文：[METHODOLOGY.zh.md](METHODOLOGY.zh.md)

## 1. Goal and benchmark

- Benchmark: SPY, dividends included. Comparisons: QQQ, and the pre-launch holdings left untouched (Pre-launch).
- Horizon: 3 to 5 years. One year's result is never a reason to change a rule.
- Risk budget: no hard drawdown limit. Target tracking error against SPY: 6% to 9% a year.

## 2. Structure

| Sleeve | Target | Holdings | Rotates |
|---|---|---|---|
| AI chain | 40% | Sections 3 and 4 | Yes, by rule |
| Sports | 10% | GRMN 6%, MSGK 4% | No |
| Fintech | 10% | V 4%, MA 3%, AXP 3% | No |
| Health care and energy | 10% | LLY 5%, XLE 5% | No |
| Income | 10% | SPDV | No |
| Defense | 10% | KO 5%, BRK.B 5% | No |
| Reserve | 10% | Short-term Treasuries (BIL) | No |

## 3. AI pool

AAPL, NVDA, MSFT, META, AMZN, GOOGL, AMD, NET, MU, LRCX, APP, GEV, LITE, PLTR, TSM, AVGO, SPCX.

**Admission (reviewed once a year in January, before ranking; all four must hold):**
1. Listed in the U.S., ADRs included.
2. Revenue, or most of its growth, comes from the AI build-out (compute, memory, networking, power equipment,
   cloud and model platforms, AI applications), with a cited source such as segment revenue in a filing.
3. Market cap of at least $10 billion.
4. Average daily dollar volume of at least $50 million over the last three months.

**Removal:** only when the business no longer belongs to the AI chain. A falling price or a low rank is handled by the
rules in section 4.

**New listings:** a name is ranked only after 253 trading days of history (SPCX around June 2027; Anthropic, once
listed, waits the same 253 days).

Every pool change goes into `POOL_CHANGES.md` with its date and reason. History is never rewritten.

## 4. AI sleeve rules

1. **Ranking:** 12-1 momentum, the close 21 trading days ago over the close 252 trading days ago, minus one
   (Yahoo adjusted closes, dividends included). Only closes before the decision day are used.
2. **Annual selection:** on the first trading day of each January, take the top 8.
3. **Buffer:** a held name stays while it ranks 12 or better and is sold only when it falls below 12. Open slots are
   filled from the best-ranked names not held, up to 8. If more than 8 held names qualify to stay, all of them stay.
4. **Weights:** each new name gets 1/8 of the AI sleeve. Names that stay share the rest in their existing proportions;
   they are not reset.
5. **Single-name cap:** a name above 20% of the AI sleeve (about 8% of the portfolio at a 40% sleeve) is cut to 20%,
   and the excess goes pro rata to the other AI holdings. Checked at the annual selection and on the first trading
   day of each quarter.
6. **Quarterly stop:** on the first trading day of April, July and October, a holding whose month-end close is below
   its 10-month average and that ranks outside the top 12 is halved. The proceeds buy SPY and stay inside the AI
   sleeve until the next annual selection. Each name is halved at most once per annual cycle.
7. **Chips cap:** chip names (NVDA, AMD, MU, LRCX, TSM, AVGO, LITE) together hold at most 60% of the AI sleeve; the
   excess goes pro rata to the non-chip AI holdings. Checked at the annual selection.
8. **Market switch:** checked on the first trading day of each month. If SPY's last month-end close is below its
   10-month average, every AI holding is halved and the proceeds buy SPY. When SPY closes a month back above the
   average, that SPY is sold and the money returns to the AI holdings pro rata. If the switch is off on the annual
   selection day, the new selection is halved the same way.
9. **Transition at inception:** on 2026-11-12, the AI names held before launch count as held, and rule 3 runs once
   on the ranking at the 2026-11-11 close:

| Rank | Name | Action |
|---|---|---|
| 1 | LITE | stays |
| 2 | MU | stays |
| 5 | GEV | stays |
| 6 | TSM | stays |
| 7 | NET | stays |
| 8 | AAPL | stays |
| 10 | META | stays |
| 11 | NVDA | stays |
| 12 | MSFT | stays |
| 13 | PLTR | sold |
| 14 | AMZN | sold |
| 15 | AVGO | sold |

Nine names stay, more than 8, so AMD and LRCX (ranks 3 and 4) do not enter this time. The nine share the 40% sleeve
in their pre-launch proportions. Chips are 46.5% of the sleeve, under the 60% cap. SPY is above its 10-month
average, so the switch is on. MSFT (12-1 momentum 8.28%) and PLTR (7.78%) are 0.5 points apart; both were checked
against Longbridge data and the two sources agree (`data/ledger/inception_crosscheck.csv`).

## 5. Rebalancing

- After every close: if any holding (the AI sleeve counted as one) is off its target by more than 50% relative (a
  10% target below 5% or above 15%), every sleeve is reset to target, with the AI sleeve's internal mix unchanged.
- The index is time-weighted and ignores new money. In a real account, each month's new money should buy the
  most underweight holding first, so that less has to be sold.
- Costs: 10 basis points on every dollar bought or sold.

## 6. Data and execution

- Prices: Yahoo adjusted closes. The workflow runs three times after each close: 17:17 and 18:43 New York time
  (an hour later in summer), plus a catch-up run at 08:11 the next morning. GitHub can drop scheduled runs, so the
  maintainer's machine also starts the same workflow when the ledger falls behind. A day already recorded is never
  recorded twice, and the run time never changes the prices recorded.
- Signals use closes up to the previous trading day. Trades fill at the decision day's close.
- If any needed close is missing, the day is not recorded and the next run catches up. A missing day beats an
  estimated price.
- After each January selection, the ranking is checked by hand against a second source (Longbridge) and the check
  is committed. If the sources order two names differently across the 8 or 12 line, Yahoo governs and the
  disagreement is recorded.

## 7. Kill criteria

Written in advance and executed when triggered, without a fresh debate.
1. The AI sleeve trails SMH by more than 15 points in each of 3 consecutive calendar years: drop the momentum rules,
   weight the whole pool by market cap with a 15% single-name cap, publish v2.0.
2. The whole portfolio trails SPY by more than 15 points in each of 3 consecutive calendar years: cut the AI sleeve
   to 20%, put the freed 20% in SPY, publish v2.0.
3. Apart from these two, rules never change because of results. Only data or calculation errors are fixed, and each
   fix goes into `ERRATA.md`.

## 8. Annual review

Each January:
- Split the excess return over SPY into five parts: AI stock selection, the 40% AI allocation, the other sleeves,
  the reserve, and trading costs.
- Record what each mechanism (buffer, single-name cap, quarterly stop, chips cap, market switch) added or cost that year.
- Compare with the Pre-launch line: did the rules help or hurt this year?

## 9. Freezing

- The SHA-256 of `config.yaml` is stored in `FROZEN.sha256`. The workflow checks it first and stops the day if it
  does not match.
- This version is tagged `methodology-v1.0` and submitted to the Internet Archive as a third-party timestamp.
- The workflow only makes `data:` commits that touch `data/ledger/` and `output/`. It never touches rule files.
- Rules change in two cases only: a kill criterion in section 7 fires (v2.0), or a data or calculation error is found
  (ERRATA). Each change is a dated `methodology:` commit that updates `config.yaml`, `FROZEN.sha256` and `ERRATA.md`
  together.

## 10. Backtest notes

- Window 2016-01-04 to 2026-11-10, Yahoo adjusted closes. Anyone can rerun it with `python -m backtest.run_backtest`.
  Results are in `backtest/results/`, charts in `backtest/charts/`.
- The pool was chosen in 2026, so the backtest carries look-ahead and survivorship bias. Its returns are not
  expectations. Drawdown, tracking error and turnover are more useful.
- With the v1.0 rules the portfolio returned 31.4% a year, with a −31.5% maximum drawdown and −21.7% in 2022. The
  pre-launch holdings (rebalanced quarterly) did 32.1%, −32.8% and −31.9%. SPY did 14.6%, −33.7% and −24.5%.
- Where the rules did not help: in fast crashes such as 2020 and 2025, the switch reacts too late. In 2025 the v1.0
  portfolio fell −26.6% from its peak, deeper than the −23.3% of the pre-launch holdings.
- With NVDA, APP and PLTR (the three biggest winners) removed from the pool, the v1.0 AI sleeve's return falls from
  47.2% to 28.8% a year, below the 41.0% of an equal-weight whole pool, while its maximum drawdown (−37.0%) stays
  smaller than the equal-weight pool's (−46.4%). The return depends on the winners being in the pool; the rules
  control risk while holding.
