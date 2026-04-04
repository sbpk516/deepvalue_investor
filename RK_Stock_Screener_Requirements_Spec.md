# RK Stock Screener — Product Requirements Specification

**Version:** 1.0  
**Date:** April 2026  
**Status:** Draft — Requirements Phase  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Investment Methodology](#3-investment-methodology)
4. [System Architecture](#4-system-architecture)
5. [Data Sources and Pipeline](#5-data-sources-and-pipeline)
6. [Confidence Scoring System](#6-confidence-scoring-system)
7. [Page 1 — RK Scanner](#7-page-1--rk-scanner)
8. [Page 2 — Watchlist](#8-page-2--watchlist)
9. [Page 3 — Stock Deep Dive](#9-page-3--stock-deep-dive)
10. [Page 4 — Swing Trader](#10-page-4--swing-trader)
11. [Hosting and Deployment](#11-hosting-and-deployment)
12. [LLM Integration](#12-llm-integration)
13. [Data Freshness and Scheduling](#13-data-freshness-and-scheduling)
14. [Error Handling and Fallbacks](#14-error-handling-and-fallbacks)
15. [Phase Roadmap](#15-phase-roadmap)
16. [Open Questions](#16-open-questions)

---

## 1. Project Overview

### 1.1 Summary

A stock screening and analysis web application that implements Roaring Kitty's (Keith Gill's) deep value investment methodology. The app automatically screens thousands of US stocks daily, filters them through a multi-layer funnel, assigns a confidence score (0–100) to each candidate, and presents actionable output including a suggested position size and upside multiple estimate.

A secondary module (Page 4) implements a separate swing trading algorithm for growth/momentum stocks — completely independent from the deep value method.

### 1.2 Primary User

Solo retail investor who:
- Wants to find RK-style deep value opportunities without manually screening thousands of stocks
- Understands basic investing concepts (P/B ratio, free cash flow, insider buying)
- Does not want to pay for premium data subscriptions
- Runs the application locally or via GitHub Actions on a zero-cost stack

### 1.3 Core Principle

The application must answer two questions for every stock:

1. **"Does this look like an RK pick?"** — Does it pass the multi-layer funnel?
2. **"How confident should I be, and why?"** — What is the confidence score, what signals fired, what is the upside multiple, and what are the key risks?

A data dashboard that only answers question 1 is not sufficient. The confidence score and actionable output are what make this useful rather than just another screener.

---

## 2. Goals and Non-Goals

### 2.1 Goals

- Automatically screen ~6,000 US stocks daily through a 6-layer RK-style funnel
- Compute a 0–100 confidence score for each candidate based on weighted signal analysis
- Estimate a conservative and bull-case upside multiple for each candidate
- Display actionable next steps dynamically based on which signals are strong or missing
- Allow users to track any stock (whether or not it passed the scanner) via a watchlist
- Alert users when a watchlisted stock's confidence score changes significantly or a new signal fires
- Allow on-demand deep dive analysis of any ticker
- Provide a separate swing trading scanner with its own algorithm and scoring

### 2.2 Non-Goals

- This is NOT a trading platform — no buy/sell execution
- This is NOT a financial advisor — all outputs are educational and informational only
- This does NOT provide real-time data — end-of-day and weekly data is sufficient
- This does NOT implement all aspects of RK's method — qualitative judgment (buyer background research, management tone, covenant interpretation) remains manual
- This does NOT cover non-US stocks in Phase 1
- This does NOT require a paid data subscription in Phase 1

---

## 3. Investment Methodology

### 3.1 Roaring Kitty Deep Value Framework

The application implements the following framework derived from Roaring Kitty's publicly documented process:

**Core philosophy:**
- Hunt in sectors experiencing multi-year pain (3–7 years of decline)
- Buy when the chart looks terrible and no one else wants it
- "Tracking" not "screening" — maintain a living watchlist of stocks to monitor over time
- Lumpy returns — expect flat years punctuated by occasional large winners
- Confidence score drives position sizing — a 20–30% confidence position is valid if the asymmetric upside is large enough

**The 9 deep value techniques:**

| # | Technique | Description |
|---|-----------|-------------|
| 1 | Sector downtrend | Stock down 40%+ from 3yr high; sector context adds/subtracts confidence |
| 2 | Price-to-tangible-book | P/TBV below 1.0 preferred; below 1.5 considered |
| 3 | Simple FCF yield | (Avg 3yr Operating CF − Capex) / Market Cap > 10% |
| 4 | Bond price filter | 90+ safe; 70–85 caution; below 50 high risk |
| 5 | Net common overhang | LT liabilities + ST debt − excess cash; custom dilution calc |
| 6 | Insider buying | Open-market purchases only; $200k+ good; $2M+ very strong |
| 7 | Institutional quality | Value-oriented hedge funds 5%+ stake; not index funds |
| 8 | 10-bagger mental model | Upside multiple = bull FCF target / current price |
| 9 | Weekly chart signals | RSI(14) weekly improving from oversold; sector peer overlay |

### 3.2 Sector Context Logic

Sector context is NOT a hard filter. It is a score modifier:

| Condition | Score Effect |
|-----------|-------------|
| Sector ETF also down 20%+ (systemic pain) | +5 points |
| Sector ETF flat ±10% (company-specific decline) | 0 points |
| Sector ETF up 20%+ while stock is down (possible value trap) | −5 points |
| 3+ sector peers also down 30%+ (peer confirmation) | +3 bonus points |

The only hard filter in Layer 2 is: stock down 40%+ from 3yr high.

### 3.3 ASC 842 Lease Distortion

Post-2019, operating leases appear on balance sheets as liabilities under ASC 842. This inflates the net common overhang metric for retailers, restaurants, airlines, and any company with significant operating leases. The application must:

- Flag when operating lease liabilities represent more than 30% of total long-term liabilities
- Deduct operating lease liabilities from the net common overhang calculation when computing the adjusted figure
- Display a warning label on affected stocks: "Net overhang includes operating leases — may overstate leverage"

---

## 4. System Architecture

### 4.1 Overview

```
┌─────────────────────────────────────────────┐
│           Data Pipeline (Python)             │
│  Runs: nightly (Phase 1: manually / cron)   │
│  Phase 2: GitHub Actions scheduled job      │
│                                              │
│  Layer 1: Universe fetch (6,000 tickers)    │
│  Layer 2: Price pain screen → ~400 stocks   │
│  Layer 3: Fundamental screen → ~100 stocks  │
│  Layer 4: Conviction signals → ~30 stocks   │
│  Layer 5: Bond/survival check → ~15 stocks  │
│  Layer 6: Technical confirmation → ~10–15   │
│                                              │
│  Output: results.json (scored candidates)   │
└──────────────┬──────────────────────────────┘
               │ writes
               ▼
┌─────────────────────────────────────────────┐
│         results.json / SQLite DB            │
│  Stores: scored candidates, watchlist,      │
│  metric history, alert state                │
└──────────────┬──────────────────────────────┘
               │ reads
               ▼
┌─────────────────────────────────────────────┐
│         Frontend (HTML + JS)                │
│  Phase 1: Static HTML reading local JSON    │
│  Phase 2: GitHub Pages serving JSON         │
│  Phase 3: Cloudflare Pages + Workers        │
│                                             │
│  Page 1: RK Scanner                         │
│  Page 2: Watchlist                          │
│  Page 3: Stock Deep Dive                    │
│  Page 4: Swing Trader                       │
└─────────────────────────────────────────────┘
```

### 4.2 Technology Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Data pipeline | Python 3.11+ | Free |
| Fundamentals | SEC EDGAR XBRL API | Free |
| Price history / RSI | yfinance library | Free |
| Insider buying | OpenInsider.com (scrape) | Free |
| Institutional holders | SEC EDGAR 13D/13G + WhaleWisdom (scrape) | Free |
| Bond prices | FINRA TRACE via Playwright (scrape, filtered stocks only) | Free |
| Scheduler (Phase 1) | Local cron / Task Scheduler | Free |
| Scheduler (Phase 2+) | GitHub Actions (2000 min/month free on public repos) | Free |
| Frontend hosting (Phase 1) | Local browser | Free |
| Frontend hosting (Phase 2) | GitHub Pages | Free |
| Frontend hosting (Phase 3) | Cloudflare Pages + Workers | Free |
| Database (Phase 1) | SQLite (local file) | Free |
| Database (Phase 3) | Cloudflare KV | Free |
| LLM (optional, covenant parsing) | Google Gemini API free tier | Free |

---

## 5. Data Sources and Pipeline

### 5.1 The 6-Layer Funnel

#### Layer 1 — Universe Fetch
- **Input:** All US-listed stocks
- **Source:** SEC EDGAR company list (`www.sec.gov/cgi-bin/browse-edgar`) + yfinance
- **Filter:** Active listing (traded in last 30 days), has filed 10-K in last 18 months, market cap $10M+
- **Output:** ~6,000 tickers
- **Frequency:** Monthly refresh
- **Estimated processing time:** 5–10 minutes

#### Layer 2 — Price Pain Screen
- **Input:** ~6,000 tickers from Layer 1
- **Source:** yfinance weekly OHLCV (5yr history)
- **Hard filter:** Stock price down 40%+ from its 3-year high
- **Soft signals computed (for score):** % below 3yr high; sector ETF 3yr return; peer comparison (3–5 same-sector stocks); 52-week low proximity
- **Output:** ~400–600 stocks
- **Frequency:** Nightly
- **Estimated processing time:** 10–15 minutes (bulk yfinance download)

#### Layer 3 — Fundamental Value Screen
- **Input:** ~400–600 from Layer 2
- **Source:** SEC EDGAR XBRL API (`data.sec.gov/api/xbrl/companyfacts/{CIK}.json`)
- **Filters:**
  - P/TBV below 1.5 (tangible book = total assets − intangibles − goodwill − total liabilities)
  - 3yr average Simple FCF positive (Operating CF − Capex, averaged over 3 years)
  - Revenue above $50M (legitimacy check)
  - Net common overhang / 3yr avg FCF ratio below 15x
- **ASC 842 check:** Flag if operating lease liabilities > 30% of total LT liabilities
- **Output:** ~100–150 stocks
- **Frequency:** Quarterly fundamentals update; nightly ratio recompute using cached fundamentals + latest price
- **Estimated processing time:** 20–30 minutes (EDGAR rate limit 10 req/sec, ~1,200 requests)

#### Layer 4 — Conviction Signal Screen
- **Input:** ~100–150 from Layer 3
- **Sources:**
  - OpenInsider.com (pandas.read_html scrape, Form 4 open-market purchases)
  - SEC EDGAR 13D/13G filings (EFTS full-text search API)
  - WhaleWisdom.com (BeautifulSoup scrape, top 13F holders)
- **Filters (OR logic — either passes):**
  - Open-market insider buy of $200k+ by CEO/CFO/Chairman/Director in last 180 days
  - Known value/activist fund holds 5%+ stake (cross-reference against curated value fund CIK lookup table)
  - Insider ownership above 20%
- **Output:** ~30–50 stocks
- **Frequency:** Daily for insider filings; weekly for 13F/13D
- **Estimated processing time:** 5–10 minutes (small scrape on filtered list)

#### Layer 5 — Survival / Bond Check
- **Input:** ~30–50 from Layer 4
- **Sources:**
  - FINRA TRACE via Playwright headless browser (bond prices by company name search)
  - SEC EDGAR 10-K/10-Q debt footnotes (for maturity schedule and covenant flags)
- **Computation:**
  - Fetch most recent bond trade price for each company with public debt
  - Assign bond tier: 90+ (safe), 80–90 (caution), 70–80 (elevated), below 70 (high risk)
  - Compute net common overhang / FCF ratio (adjusted for ASC 842 leases)
  - Flag short debt maturity (any bond maturing within 18 months)
- **Output:** ~15–25 stocks
- **Frequency:** Weekly (bond prices change slowly for non-distressed companies)
- **Estimated processing time:** 5–8 minutes (Playwright on 30–50 tickers)

#### Layer 6 — Technical Confirmation
- **Input:** ~15–25 from Layer 5
- **Source:** yfinance weekly OHLCV
- **Computation:**
  - Weekly RSI(14): compute from weekly closes
  - Flag: RSI was below 30, now trending up 3+ consecutive weeks
  - Sector peer comparison: pull 3–5 sector peers, check if majority also showing RSI improvement
  - Support retest: price touched recent low and bounced (within 5% of 3yr low then recovered 10%+)
  - Compute upside multiple (see Section 6.2)
- **Output:** ~10–15 final scored candidates
- **Frequency:** Weekly RSI recompute; daily price update
- **Estimated processing time:** 2–3 minutes

### 5.2 Sector ETF Mapping

| GICS Sector | ETF Ticker |
|-------------|-----------|
| Energy | XLE |
| Materials | XLB |
| Industrials | XLI |
| Consumer Discretionary | XLY |
| Consumer Staples | XLP |
| Healthcare | XLV |
| Financials | XLF |
| Technology | XLK |
| Real Estate | XLRE |
| Utilities | XLU |
| Communication Services | XLC |
| Natural Gas (sub-sector) | FCG |
| Retail (sub-sector) | XRT |

### 5.3 Value Fund Lookup Table

A manually maintained list of known value/activist fund names and their SEC CIK numbers. Used to cross-reference 13D/13G filers against "respected value shops." Seed list sourced from Dataroma tracked managers. Target: 150–200 funds. Examples:

- Baupost Group (Seth Klarman)
- Greenlight Capital (David Einhorn)
- Fairfax Financial (Prem Watsa)
- Pershing Square (Bill Ackman)
- Gotham Asset Management (Joel Greenblatt)
- Third Point (Dan Loeb)
- ValueAct Capital
- Starboard Value
- Elliott Management

Lookup table stored as a JSON file in the repo. Updated manually on a quarterly basis.

---

## 6. Confidence Scoring System

### 6.1 Score Components (Total: 100 points base + up to 15 bonus points)

#### Component 1 — Insider Buying (30 points)

| Condition | Points |
|-----------|--------|
| No insider buying in last 180 days | 0 |
| Any insider buy $50k–$200k (Director level) | 8 |
| CEO/CFO/Chairman buy $200k–$500k | 15 |
| CEO/CFO/Chairman buy $500k–$2M | 22 |
| CEO/CFO/Chairman buy $2M+ OR 3+ insiders buying simultaneously | 30 |
| **Bonus:** Purchase made when stock within 20% of 3yr low | +5 |
| **Penalty:** Insiders also selling in same 90-day period | −8 |

#### Component 2 — Survival / Bond Safety (25 points)

| Condition | Points |
|-----------|--------|
| No public debt confirmed; low leverage (overhang/FCF < 2x) | 25 |
| Bonds 90+ AND net overhang/FCF below 5x | 25 |
| Bonds 80–90 OR overhang/FCF 5–8x | 18 |
| Bonds 70–80 OR overhang/FCF 8–12x | 10 |
| Bonds 50–70 | 4 |
| Bonds below 50 OR overhang/FCF above 15x | 0 |
| **Warning flag:** ASC 842 lease distortion detected | Display warning, −3 pts |

#### Component 3 — FCF Yield + Valuation Discount (20 points)

| Condition | Points |
|-----------|--------|
| 3yr avg FCF yield above 25% (price < 4× FCF/share) | 20 |
| FCF yield 15–25% AND P/TBV below 0.5 | 20 |
| FCF yield 10–15% OR P/TBV 0.5–1.0 | 14 |
| FCF yield 5–10% AND P/TBV 1.0–1.5 | 8 |
| FCF yield below 5% or negative | 2 |
| **Bonus:** FCF positive for 5+ consecutive years | +3 |

#### Component 4 — Institutional Ownership Quality (15 points)

| Condition | Points |
|-----------|--------|
| Known value/activist fund holds 5%+ AND added shares last 2 quarters | 15 |
| Known value/activist fund holds 5%+ (not recently increased) | 10 |
| Insider ownership above 20% | 8 |
| Only index funds / no notable value holders | 2 |
| No institutional holders | 0 |
| **Bonus:** 2+ independent value funds holding simultaneously | +4 |

#### Component 5 — Technical Trend Confirmation (10 points)

| Condition | Points |
|-----------|--------|
| Weekly RSI was below 30, now trending up 3+ weeks; support retest confirmed | 10 |
| Weekly RSI improving from oversold but not yet confirmed | 6 |
| RSI neutral (30–50), no clear signal | 4 |
| RSI still declining or above 70 | 1 |
| **Bonus:** Sector peers showing same RSI improvement (macro turn signal) | +3 |

#### Sector Context Modifier (applied to total score)

| Condition | Modifier |
|-----------|---------|
| Sector ETF also down 20%+ (systemic pain) | +5 pts |
| Sector ETF flat ±10% | 0 pts |
| Sector ETF up 20%+ while stock is down | −5 pts |
| 3+ sector peers also down 30%+ (peer confirmation) | +3 pts additional |

### 6.2 Score Interpretation and Actionable Output

| Score Range | Tier Label | Suggested Action |
|-------------|-----------|-----------------|
| 0–39 | Watch only | No position. Add to watchlist. Monitor for signal improvement. |
| 40–64 | Speculative position | 1–2% portfolio position. Asymmetric payoff may justify small bet. |
| 65–79 | High conviction | 3–4% portfolio position. Run manual deep dive before sizing up. |
| 80–100 | Exceptional setup | 4–6% portfolio position. Multiple signals firing simultaneously. |

**Important:** These are informational suggestions only, not financial advice. User adjusts based on personal risk tolerance and portfolio context.

### 6.3 Upside Multiple Calculation

```
normalized_fcf_per_share = 3yr_avg_fcf / current_shares_outstanding
peak_cycle_fcf_per_share = best_fcf_year_in_last_10yr / current_shares_outstanding

conservative_target = normalized_fcf_per_share × 12
bull_target = peak_cycle_fcf_per_share × 18

conservative_upside = conservative_target / current_price
bull_upside = bull_target / current_price
```

Both values displayed as "X.Xx — X.Xx" range. If peak cycle FCF is not available (less than 5yr history), display conservative only.

The upside multiple is the critical number that drives position sizing decisions. A 40% confidence score is worth a small position if the bull upside is 8x. The same 40% score on a 1.5x upside is not worth the risk.

### 6.4 Dynamic Actionable Next Steps

The application generates specific next steps for each stock based on which signals are weak or missing:

| Condition | Generated Next Step |
|-----------|-------------------|
| No insider buying detected | "No insider activity yet — set alert for new Form 4 filings on EDGAR" |
| Bond data unavailable | "Bond data not found — check manually at finra.org/investors. Search: [company name]" |
| Bond price 70–85 (caution zone) | "Bonds in caution zone — read debt footnote in latest 10-Q. Check maturity date and covenant terms." |
| Institutional score below 8/15 | "No known value fund holders detected — check WhaleWisdom for recent 13F activity" |
| Technical score below 5/10 | "RSI not yet confirming — wait for weekly RSI to cross above 35 before entering" |
| ASC 842 flag triggered | "Operating leases inflate apparent leverage — subtract lease liabilities for true debt picture" |
| FCF yield below 10% | "FCF yield weak — review 10yr FCF history for cycle context. Is this a cyclical trough?" |
| Score crosses tier boundary | "Score increased from Watch to Speculative — review updated signal breakdown" |

---

## 7. Page 1 — RK Scanner

### 7.1 Purpose

Display the output of the automated daily funnel. Shows all stocks that passed all funnel layers, ranked by confidence score. No user input required — just visit the page and see today's candidates.

### 7.2 Layout

**Header:**
- App name and navigation tabs (RK Scanner | Watchlist | Deep Dive | Swing Trader)
- Last updated timestamp
- Number of stocks screened today / number of candidates found

**Results table (one row per stock):**

| Column | Description |
|--------|-------------|
| Ticker | Stock symbol, clickable → Page 3 |
| Company name | Full name |
| Sector | GICS sector |
| Score | 0–100 confidence score, color-coded (red/amber/green) |
| Tier | Watch / Speculative / High Conviction / Exceptional |
| Upside | "2.4× – 6.1×" conservative to bull range |
| Top signal | Single most important signal that fired (e.g., "CEO bought $1.8M") |
| Watchlist | + button to add to Page 2 watchlist |

**Filters (above table):**
- Filter by sector
- Filter by tier (show only High Conviction or above)
- Sort by: score (default), upside multiple, insider buying date

### 7.3 Behavior

- Table sorted by confidence score descending by default
- Clicking any row opens Page 3 (Stock Deep Dive) for that ticker
- Clicking "+" adds stock to Page 2 watchlist with a confirmation toast
- Page auto-refreshes on load (checks for updated results.json)
- If pipeline has not run today, display: "Last updated [date] — pipeline running nightly"
- Empty state: "No candidates passed all filters today. Check back tomorrow or lower the filters."

---

## 8. Page 2 — Watchlist

### 8.1 Purpose

User-maintained list of stocks to track continuously over time. Any stock can be added — does not have to pass the scanner. Implements RK's "tracking not screening" philosophy: build conviction on a stock by watching it for weeks or months before it triggers.

### 8.2 Layout

**Add stock input:**
- Search box at top: type ticker or company name → autocomplete → Add button
- Shows current score and tier next to each autocomplete result

**Watchlist table (one row per watched stock):**

| Column | Description |
|--------|-------------|
| Ticker | Clickable → Page 3 |
| Score | Current 0–100 with trend arrow (↑ ↓ →) vs last week |
| Score history | Mini sparkline of score over last 8 weeks |
| Insider activity | Last insider buy date + amount, or "None" |
| Bond status | Safe / Caution / High Risk / N/A |
| RSI trend | Oversold-improving / Neutral / Overbought |
| Days watched | How long on watchlist |
| Alert | Bell icon — click to configure alert thresholds |
| Remove | × to remove from watchlist |

**Alert configuration (per stock):**
- Notify when score crosses threshold (configurable: e.g., crosses 65)
- Notify when new insider buy appears
- Notify when bond price drops below 80
- Notify when RSI crosses above 35 from oversold

### 8.3 Behavior

- Alerts stored in local storage (Phase 1) or Cloudflare KV (Phase 3)
- Alert notification shown as a banner on page load: "2 watchlist alerts since your last visit"
- Score sparkline shows week-by-week confidence score — the trend matters as much as the current value
- Stocks that have since passed the full scanner funnel are highlighted with a green border: "Now appearing in RK Scanner"
- Phase 1: alerts displayed as in-page banners on next visit (no push notifications)
- Phase 3: optional email alert via Cloudflare Workers + free email API (e.g., Resend free tier)

---

## 9. Page 3 — Stock Deep Dive

### 9.1 Purpose

On-demand full analysis of any stock. User types any US ticker and gets the complete RK signal breakdown, confidence score, risk flags, upside estimate, and actionable next steps — all in one view. Does not require the stock to have passed the scanner.

### 9.2 Layout

**Search bar:**
- Large ticker input at top
- Submit button → triggers on-demand pipeline run for that ticker
- Results appear below in ~10–15 seconds

**Section 1 — Verdict card:**
- Large confidence score display (e.g., "72 / 100")
- Tier label with color: "High Conviction"
- Suggested action: "3–4% portfolio position"
- Upside range: "Conservative 2.4× · Bull 6.1×"
- One-line summary: "CEO bought $1.8M at 3yr low. Bonds safe at 91. FCF yield 18%."
- Two buttons: "Add to Watchlist" | "View on EDGAR →"

**Section 2 — Score breakdown:**
- Five horizontal meter bars, one per component
- Each bar shows: component name, score/max, fill level, key data point
  - Example: "Insider Buying · 26/30 · CEO bought $1.8M on [date]"
- Sector context modifier shown below bars: "+5 pts (sector also in downtrend)"
- Total score shown at bottom with breakdown arithmetic

**Section 3 — Key metrics panel (historical context):**
- 10-year FCF history bar chart (using EDGAR XBRL data)
- Current P/TBV vs historical P/TBV range
- Net common overhang trend (last 4 quarters)
- Share count trend (is dilution occurring?)
- Short interest % and trend

**Section 4 — Insider buying timeline:**
- List of all open-market buys in last 2 years
- Columns: Date | Buyer name | Role | Shares | Total $ | Stock price at time | Stock price today
- Highlight rows where buyer is CEO/CFO/Chairman in green

**Section 5 — Institutional holders:**
- List of top 10 holders from 13F data
- Flag known value/activist funds with a badge
- Show quarter-over-quarter change (added/reduced/new position)

**Section 6 — Bond status:**
- Bond price (or "No public debt detected")
- Bond maturity date
- Yield to maturity
- Tier label: Safe / Caution / High Risk
- Net common overhang figure (ASC 842 adjusted) and FCF coverage ratio

**Section 7 — Technical chart summary:**
- Weekly RSI current value + trend direction
- Distance from 3yr high (% drawdown)
- Distance from 52wk low
- Sector ETF comparison: stock 3yr return vs sector ETF 3yr return
- Peer comparison: list of 3–5 sector peers with their 3yr returns

**Section 8 — Risk flags:**
- Plain language list of specific risks detected
- Examples:
  - "ASC 842: Operating leases represent 45% of LT liabilities — net overhang may overstate debt"
  - "Bond matures in 14 months — refinancing risk if rates remain elevated"
  - "FCF was negative last quarter — watch next earnings release"
  - "Insider ownership 8% — below RK's 20% preference"
  - "No value fund holders detected in most recent 13F data"

**Section 9 — Actionable next steps:**
- Dynamically generated list of 3–6 specific actions based on weak/missing signals
- Each step includes a direct link where relevant
- Examples:
  - "Read the debt footnote in the latest 10-Q → [EDGAR link]"
  - "Check who the insider buyer is — search '[name]' on LinkedIn"
  - "Watch for sector peer RSI to confirm sector-level turn"
  - "Set watchlist alert for: score crosses 65 or new insider buy"

### 9.3 Behavior

- On-demand trigger: user submits ticker → pipeline runs for that specific stock only
- Results cached for 24 hours — re-running same ticker within 24hrs shows cached result with timestamp
- If ticker not found: "Ticker not found. Check symbol and try again."
- If EDGAR data insufficient (too few years of history): show available data with note "Less than 5 years of EDGAR data — FCF average based on available history"
- All EDGAR links open in new tab
- "Add to Watchlist" persists to Page 2

---

## 10. Page 4 — Swing Trader

### 10.1 Purpose

A completely separate scanner for short-term swing trading opportunities. Different universe, different algorithm, different scoring, different timeframe. Clearly labeled as a separate strategy from RK's deep value method.

### 10.2 Strategy Definition

- **Universe:** US stocks, Nasdaq and NYSE listed, market cap $500M+, avg daily volume > 500k shares
- **Timeframe:** 2–8 week hold target
- **Philosophy:** Buy momentum breakouts or pullbacks to support in growing companies; ride the next leg up

### 10.3 Swing Score Components (100 points)

#### Component 1 — Revenue Growth Momentum (25 points)

| Condition | Points |
|-----------|--------|
| Revenue YoY growth 30%+ last 2 quarters | 25 |
| Revenue YoY growth 20–30% | 18 |
| Revenue YoY growth 15–20% | 12 |
| Revenue growth below 15% or declining | 0 |

#### Component 2 — Technical Setup Quality (25 points)

| Condition | Points |
|-----------|--------|
| Price breaking out of consolidation on above-average volume | 25 |
| Pullback to 21-day or 50-day EMA in uptrend | 20 |
| Price above 50-day MA, 50-day above 200-day | 12 |
| Price below 50-day MA | 0 |

#### Component 3 — Relative Strength (20 points)

| Condition | Points |
|-----------|--------|
| Stock 3-month return in top 10% of market | 20 |
| Top 25% | 14 |
| Top 50% | 8 |
| Below median relative strength | 2 |

#### Component 4 — Earnings Momentum (20 points)

| Condition | Points |
|-----------|--------|
| EPS beat last 2 quarters + guidance raised | 20 |
| EPS beat last 2 quarters (guidance neutral) | 14 |
| EPS beat last 1 quarter | 8 |
| EPS miss or no earnings data | 0 |

#### Component 5 — Volume Confirmation (10 points)

| Condition | Points |
|-----------|--------|
| Volume on up-days 2× average in last 10 days | 10 |
| Volume on up-days 1.5× average | 6 |
| Volume neutral | 3 |
| Volume declining on up-days (distribution) | 0 |

### 10.4 Swing Score Interpretation

| Score | Action |
|-------|--------|
| 0–39 | Skip |
| 40–59 | Watch |
| 60–79 | Potential entry — wait for ideal setup |
| 80–100 | High probability setup — consider entry |

**Entry/exit rules displayed per stock:**
- Entry: suggested entry zone (current price ± %)
- Target: +15–25% from entry
- Stop loss: −7–8% from entry
- Risk/reward ratio displayed

### 10.5 Page Layout

Same structure as Page 1 (RK Scanner) but with swing score columns. Clearly labeled "Swing Trader — Momentum Strategy" with a note: "This page uses a different algorithm from the RK deep value method on Page 1. These are short-term setups, not long-term value investments."

Different visual treatment — use a distinct color scheme (e.g., blue accents instead of green) to ensure users do not confuse swing setups with RK deep value candidates.

---

## 11. Hosting and Deployment

### 11.1 Phase 1 — Local Machine (MVP)

**Goal:** Get the pipeline and UI working end-to-end before thinking about hosting.

**Setup:**
- Python pipeline runs manually or via local cron/Task Scheduler
- Output: `results.json` in project folder
- Frontend: single `index.html` file reading `results.json` via `fetch()`
- Open `index.html` in browser directly — no server needed
- SQLite database file for watchlist persistence

**Limitations:**
- Only accessible on local machine
- Pipeline only runs when machine is on
- No real-time alerts

### 11.2 Phase 2 — GitHub Actions + GitHub Pages (Free, Automated)

**Goal:** Automate the pipeline and make the app accessible via a public URL.

**Setup:**
- GitHub Actions workflow file (`.github/workflows/pipeline.yml`)
- Cron schedule: daily at 11pm EST (after US market close)
- Workflow: checkout repo → install dependencies → run pipeline → commit updated `results.json` → push
- GitHub Pages serves `index.html` which reads `results.json` from the repo
- Public URL: `https://yourusername.github.io/rk-screener`

**Limitations:**
- Repo must be public for free Actions minutes (2000 min/month)
- No server-side computation — watchlist stored in browser localStorage only
- Page 3 (on-demand deep dive) requires a server — defer to Phase 3

### 11.3 Phase 3 — Cloudflare Pages + Workers (Full App, Still Free)

**Goal:** Add server-side capability for Page 2 (persistent watchlist), Page 3 (on-demand search), and alerts.

**Setup:**
- Cloudflare Pages hosts the frontend (deploy from GitHub, auto-deploy on push)
- Cloudflare Workers handle API endpoints:
  - `GET /api/scan` — returns latest results.json from KV
  - `POST /api/watchlist` — read/write user watchlist in KV
  - `GET /api/stock/{ticker}` — triggers on-demand pipeline for one ticker
- Cloudflare KV stores: computed scores, watchlist per user (keyed by session ID), metric history
- GitHub Actions still runs the nightly pipeline → writes output to Cloudflare KV via Workers API

**Cloudflare free tier limits:** 100k Workers requests/day, 1GB KV storage, unlimited Pages requests — more than sufficient for personal use.

---

## 12. LLM Integration

### 12.1 Decision

An LLM is NOT required for the core 4 pages. The confidence scoring system is entirely rule-based and mathematical. No natural language understanding is needed for Layers 1–6 of the funnel.

### 12.2 The One Place LLM Genuinely Helps

**Covenant parsing from 10-K/10-Q debt footnotes.** Covenant terms (e.g., minimum EBITDA, maximum leverage ratio, cross-default provisions) are written in unstructured legal prose in SEC filings. Rule-based regex cannot reliably extract these. An LLM can read the relevant section and output:
- Whether covenants exist
- What the key covenant metrics are
- Whether the company is near breach (based on current financials)

This only runs on the 10–15 final deep-dive candidates, not on all stocks.

### 12.3 LLM Provider

**Google Gemini API free tier:**
- Free tier: 60 requests per minute, 1,500 requests per day (as of 2025 — verify current limits)
- Model: Gemini 1.5 Flash (fast, cheap, sufficient for document parsing)
- Cost: $0 for this use case (10–15 calls per week is far below daily limit)
- No credit card required for free tier

**Fallback (if Gemini unavailable):** Skip covenant parsing and display: "Covenant analysis not available — read debt footnote manually. [EDGAR link]"

**Alternative free options:**
- Groq free tier (LLaMA 3, very fast, 14,400 tokens/day)
- Ollama local (run LLaMA 3 on local machine, no API cost, no rate limits)

### 12.4 Gemini Integration Spec

**Input:** Raw text of debt footnote section from 10-K or 10-Q (extracted via EDGAR full-text search)

**Prompt:**
```
You are analyzing a corporate debt footnote from a SEC filing. 
Extract the following information in JSON format:
{
  "has_covenants": true/false,
  "covenant_types": ["list of covenant names"],
  "nearest_breach_risk": "low/medium/high/unknown",
  "maturity_dates": ["YYYY-MM-DD"],
  "key_concerns": "one sentence summary or null"
}
Return only valid JSON. If information is not found, use null.
```

**Output:** JSON parsed and used to populate the bond/leverage section of Page 3

---

## 13. Data Freshness and Scheduling

| Data Type | Update Frequency | Source | Notes |
|-----------|-----------------|--------|-------|
| Universe (all tickers) | Monthly | SEC EDGAR + yfinance | Changes slowly |
| Price history (OHLCV) | Nightly | yfinance | After market close |
| Weekly RSI | Weekly (Monday AM) | Computed from yfinance | Recomputed from weekly closes |
| Fundamental data (FCF, balance sheet) | Quarterly | SEC EDGAR XBRL | On earnings release detection |
| Insider buying (Form 4) | Daily | OpenInsider scrape | New filings appear same day |
| Institutional holders (13F/13D) | Weekly | EDGAR + WhaleWisdom | 13F filed quarterly; 13D within 10 days |
| Bond prices | Weekly | FINRA TRACE scrape | Only for ~30 filtered stocks |
| Sector ETF prices | Nightly | yfinance | Same batch as price history |
| Confidence scores | Nightly | Computed | Recomputed whenever underlying data updates |
| Watchlist alerts | Checked nightly | Computed from latest scores | Alerts logged for display on next page load |

---

## 14. Error Handling and Fallbacks

### 14.1 yfinance Failures

yfinance is unofficial and may break. Handling:
- Wrap all yfinance calls in try/except with 3 retries and exponential backoff
- If yfinance fails for a specific ticker: skip that ticker, log to error file, continue pipeline
- If yfinance fails globally (API change): fallback to Alpha Vantage free tier (25 calls/day) for critical tickers only
- Display on frontend: "Price data unavailable for [X] stocks today — partial results shown"

### 14.2 SEC EDGAR Rate Limiting

EDGAR enforces 10 req/sec. Handling:
- Add 0.11 second sleep between requests
- If 429 received: exponential backoff starting at 2 seconds
- Batch fundamental data quarterly — daily pipeline only recomputes ratios using cached fundamentals + latest price
- If EDGAR unavailable: use last cached fundamentals with a "data as of [date]" label

### 14.3 OpenInsider Scraping Failures

- If HTTP 403 (blocked): rotate User-Agent string, retry after 60 seconds
- If still blocked: fall back to raw EDGAR Form 4 parsing via EFTS API
- Form 4 EFTS query: `efts.sec.gov/efts/hit?q=%22{ticker}%22&forms=4&dateRange=custom&startdt={90_days_ago}`

### 14.4 FINRA TRACE Playwright Failures

- Playwright timeout (30 seconds default): increase to 60 seconds for FINRA
- If company not found by name: try with shortened name (remove "Inc", "Corp", "Ltd")
- If still not found: display "Bond data unavailable" with manual FINRA link on Page 3
- Log all FINRA failures for manual review

### 14.5 Data Gaps

| Gap Scenario | Handling |
|-------------|---------|
| Less than 3yr FCF history | Use available years; note "X-year average (less than 3yr available)" |
| Negative tangible book | Show value, flag "Negative tangible book — assess asset quality manually" |
| No public bonds found | Score bond component as 25/25 only if D/E ratio below 0.5; else 15/25 with note |
| Ticker not in EDGAR | Skip — EDGAR covers all SEC-registered companies; if missing, likely OTC/ADR |

---

## 15. Phase Roadmap

### Phase 1 — Local MVP (Target: 2 weeks)

**Goal:** Working pipeline + basic display on local machine.

**Deliverables:**
1. Python pipeline: Layer 1 (universe) + Layer 2 (price pain screen)
2. EDGAR XBRL integration: Layer 3 (fundamentals)
3. OpenInsider integration: Layer 4 (insider buying)
4. Bond price Playwright scraper: Layer 5 (survival check)
5. RSI computation: Layer 6 (technical)
6. Confidence score calculator (all 5 components)
7. Upside multiple calculator
8. `results.json` output
9. `index.html` — Page 1 (scanner) only, reads local JSON
10. SQLite schema for watchlist and metric history

**Out of scope for Phase 1:** Page 2 (watchlist UI), Page 3 (deep dive UI), Page 4 (swing trader), GitHub Actions, alerts

### Phase 2 — GitHub Actions + Basic UI (Target: 1 week after Phase 1)

**Goal:** Automated pipeline + Pages 1–3 on GitHub Pages.

**Deliverables:**
1. GitHub Actions workflow (nightly cron)
2. Page 2 (Watchlist) — localStorage based
3. Page 3 (Deep Dive) — runs on-demand from pre-computed JSON; no live computation yet
4. Swing trader score calculator
5. Page 4 (Swing Trader) basic view

### Phase 3 — Cloudflare Full App (Target: when ready to share with others)

**Goal:** Full interactive web app with server-side features.

**Deliverables:**
1. Cloudflare Workers API
2. Page 2 persistent watchlist (Cloudflare KV)
3. Page 3 live on-demand computation (Worker triggers pipeline for single ticker)
4. Alert system
5. Gemini covenant parsing integration
6. Email alerts via Resend free tier

---

## 16. Open Questions

| # | Question | Decision Needed By | Notes |
|---|----------|--------------------|-------|
| 1 | What threshold for "40% vs 50% from 3yr high" in Layer 2 hard filter? | Phase 1 build | 40% is more inclusive (fewer misses), 50% is stricter. Recommend 40% to start. |
| 2 | Value fund lookup table — who maintains it and how often? | Phase 1 build | Start with Dataroma list (~60 managers), expand manually quarterly |
| 3 | Should Page 4 (Swing Trader) share the same pipeline run or be separate? | Phase 2 | Separate pipeline recommended — different universe, different data needs |
| 4 | Gemini API: free tier limits need verification at build time | Phase 3 | Check current limits at ai.google.dev before integrating |
| 5 | Should results.json be committed to a public GitHub repo? | Phase 2 | Computed scores are fine to be public; no personal data involved |
| 6 | How to handle stocks with fiscal years not ending December? | Phase 1 build | Use TTM (trailing twelve months) calculations throughout; EDGAR XBRL supports this |
| 7 | Minimum history requirement: what if a company has only 2yr EDGAR data? | Phase 1 build | Use available data with flag; exclude from FCF scoring component but keep in other components |
| 8 | Canadian stocks (RK held RFP, RRC, MX)? | Phase 2 | EDGAR covers some Canadian cross-listers; InsiderTracking.com for Canadian-only filings. Defer to Phase 2. |

---

*This document covers the requirements phase only. Design mockups, database schema, API contract, and component-level technical specifications will be covered in subsequent phases.*

*All investment methodology described in this document is based on publicly available information from Roaring Kitty's YouTube videos and livestreams. This application is educational and informational only. Nothing in this application constitutes financial advice.*
