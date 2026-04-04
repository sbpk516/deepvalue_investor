# RK Stock Screener — Design Plan v2.0

**Version:** 2.0 (revised after UX review)  
**Date:** April 2026  
**Status:** Design Phase — Ready for Implementation  
**Changes from v1.0:** Full UX overhaul based on design review. Progressive disclosure, scoring transparency, mobile breakpoints, accessibility, nav clarity, action-first layout.

---

## What Changed from v1.0 and Why

| Issue | v1.0 Problem | v2.0 Fix |
|-------|-------------|---------|
| Nav labels | "RK Scanner" — jargon | Plain-English subtitles on every tab |
| Page 1 table | 7 equal columns, no hierarchy | Primary + secondary column tiers, score dominant |
| Score display | "72" number alone — meaningless | Score + plain-English label + color as one unit |
| Page 3 layout | 12 sections all visible — overwhelming | 3-zone progressive disclosure |
| Action steps position | Buried at bottom of Page 3 | Moved to Zone 1, directly after verdict |
| Upside display | "2.4× – 6.1×" range confusing | Single number + tooltip for range |
| Scoring transparency | Score shown, reasoning hidden | Every score shows full reasoning chain |
| Mobile | No breakpoints specified | Full responsive column priority rules |
| Accessibility | Color-only tier indicators | Color + shape + text label |
| Alert hierarchy | All alerts look identical | Opportunity alerts green, risk alerts amber/red |
| Watchlist sparklines | Unlabelled — user can't interpret | Trend label alongside every sparkline |
| Page 4 visual | Same layout as Page 1 — confusing | Distinct visual language, different terminology |
| Empty state | 4-sentence apology | Single sentence + one action button |
| Score dial | Decorative arc — cognitive load | Simple large number + horizontal bar |
| Contextual help | Not in design plan | Three-layer inline help: ⓘ tooltips on every metric, "why this matters" in score expansion, full "how it works" modal from footer |

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [System Design](#2-system-design)
3. [Folder Structure](#3-folder-structure)
4. [Database Design](#4-database-design)
5. [Data Pipeline Design](#5-data-pipeline-design)
6. [Confidence Score Engine Design](#6-confidence-score-engine-design)
7. [Scoring Transparency System](#7-scoring-transparency-system)
8. [Contextual Help System](#8-contextual-help-system)
9. [API Contract Design](#9-api-contract-design)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Navigation Design](#11-navigation-design)
12. [UI Design — Page 1: RK Scanner](#12-ui-design--page-1-rk-scanner)
13. [UI Design — Page 2: Watchlist](#13-ui-design--page-2-watchlist)
14. [UI Design — Page 3: Stock Deep Dive](#14-ui-design--page-3-stock-deep-dive)
15. [UI Design — Page 4: Swing Trader](#15-ui-design--page-4-swing-trader)
16. [Component Library](#16-component-library)
17. [Color System and Typography](#17-color-system-and-typography)
18. [Responsive Design — Mobile Breakpoints](#18-responsive-design--mobile-breakpoints)
19. [Accessibility](#19-accessibility)
19. [Error States and Loading States](#19-error-states-and-loading-states)
20. [Build Sequence](#20-build-sequence)

---

## 1. Design Philosophy

### 1.1 The Three Core Principles

**Principle 1 — Zero Thinking Required**
The user should never have to stop and ask: "What does this mean? Where do I go? What should I do?" Every screen answers these questions before the user asks them. Labels are plain English. Actions are obvious. Next steps are explicit.

**Principle 2 — Action Before Data**
Every page surfaces what the user should DO before explaining WHY. The verdict and action steps are always above the fold. The supporting evidence is one scroll away. The full technical detail is always available but never forced.

**Principle 3 — Full Scoring Transparency**
The user should always be able to understand exactly how a score was computed. Every score has a reasoning chain: total score → component breakdown → sub-signal details → raw data. The user can go as deep as they want, but the summary is always clear without going deep.

This is critical for trust. If a user sees "GME: 74/100" and cannot understand why, they will not act on it. If they can see "Insider buying: 22/30 because CEO bought $640k on March 15 when stock was at a 3-year low, which is 84% of annual compensation" — they understand the signal and can judge it themselves.

### 1.2 UX Laws Applied

| Law | Application |
|-----|------------|
| Hick's Law (fewer choices = faster decisions) | Max 3 visible items per zone; everything else collapsed |
| Miller's Law (7±2 items in working memory) | Page 3 split into 3 zones of 3–4 items each |
| Fitts's Law (primary actions large and close) | CTA buttons full-width on mobile, labelled not icon-only |
| Progressive Disclosure | Zone 1 visible, Zone 2 one scroll, Zone 3 collapsed |
| F-pattern reading (users scan top-left first) | Score + action steps in top-left of every stock view |
| Jakob's Law (match existing mental models) | Standard table, search box, tab navigation — familiar patterns |

### 1.3 Design Vocabulary

The app uses consistent language throughout:

| Concept | Always called |
|---------|--------------|
| The score 0–100 | "Signal strength" or "RK Score" |
| Tier label | Plain English signal phrase (see Section 11.3) |
| Conservative upside | "Base case" |
| Bull upside | "Recovery case" |
| Actionable next steps | "Do these next" |
| Risk flags | "Watch out for" |
| Confidence score component | "Signal" |

---

## 2. System Design

### 2.1 Full System Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                     NIGHTLY PIPELINE (Python)                     │
│                                                                    │
│  Layer 1 → Layer 2 → Layer 3 → Layer 4 → Layer 5 → Layer 6      │
│  Universe   Price      Fundament  Conviction  Bond      Technical  │
│  ~6,000     ~400       ~100       ~30-50      ~15-25    ~10-15    │
│                                                                    │
│  ↓ Confidence Score Engine (all 5 components + transparency data) │
│  ↓ Upside Calculator + Dilution Calc + Risk Flags + Action Steps  │
│  ↓ Output Writer → results.json + SQLite                          │
└──────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                      SQLite Database                              │
│  stocks · scanner_runs · candidates · watchlist                   │
│  metric_history · alerts · swing_candidates · value_funds         │
│  score_transparency · edgar_cache                                 │
└──────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                   Frontend (index.html)                           │
│  Page 1: RK Scanner  ·  Page 2: Watchlist                        │
│  Page 3: Deep Dive   ·  Page 4: Swing Trader                     │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow — Nightly Pipeline

Same as v1.0 — see previous spec. Key addition: scoring engine now outputs a `score_transparency` object alongside the score, containing the full reasoning chain for every sub-signal.

---

## 3. Folder Structure

```
rk-screener/
├── pipeline/
│   ├── main.py
│   ├── config.py
│   ├── layers/
│   │   ├── layer1_universe.py
│   │   ├── layer2_price.py
│   │   ├── layer3_fundamentals.py
│   │   ├── layer4_conviction.py
│   │   ├── layer5_bonds.py
│   │   └── layer6_technical.py
│   ├── scoring/
│   │   ├── confidence_score.py
│   │   ├── transparency.py          # NEW: builds reasoning chain per signal
│   │   ├── upside_calc.py
│   │   ├── risk_flags.py
│   │   └── action_steps.py
│   ├── scrapers/
│   │   ├── openinsider.py
│   │   ├── whalewisdom.py
│   │   ├── finra_trace.py
│   │   ├── motleyfool.py
│   │   └── edgar_defm14a.py
│   ├── llm/
│   │   ├── gemini_client.py
│   │   ├── prompts.py
│   │   └── parsers.py
│   ├── data/
│   │   ├── value_funds.json
│   │   ├── sector_etf_map.json
│   │   ├── commodity_map.json
│   │   ├── secular_decline_sic.json
│   │   └── cyclical_sic.json
│   ├── db/
│   │   ├── database.py
│   │   ├── schema.sql
│   │   └── migrations/
│   ├── swing/
│   │   ├── swing_pipeline.py
│   │   └── swing_scoring.py
│   └── utils/
│       ├── edgar.py
│       ├── yfinance_helpers.py
│       ├── cache.py
│       └── logger.py
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── main.css               # CSS variables, reset, typography
│   │   ├── layout.css             # Grid, zones, responsive breakpoints
│   │   ├── components.css         # All reusable components
│   │   ├── pages.css              # Page-specific overrides
│   │   └── accessibility.css      # Focus states, high contrast, reduced motion
│   ├── js/
│   │   ├── app.js                 # Router, nav, theme toggle
│   │   ├── pages/
│   │   │   ├── scanner.js
│   │   │   ├── watchlist.js
│   │   │   ├── deepdive.js
│   │   │   └── swing.js
│   │   ├── components/
│   │   │   ├── scorecard.js       # Verdict card + score bar
│   │   │   ├── score_transparency.js  # NEW: reasoning chain expander
│   │   │   ├── charts.js
│   │   │   ├── table.js
│   │   │   ├── sparkline.js
│   │   │   ├── alerts.js
│   │   │   └── zone_expander.js   # NEW: progressive disclosure controller
│   │   └── utils/
│   │       ├── format.js
│   │       ├── colors.js
│   │       └── storage.js
│   └── assets/
│       └── favicon.ico
│
├── output/
│   ├── results.json
│   ├── swing_results.json
│   └── alerts.json
│
├── cache/
├── logs/
├── rk_screener.db
├── .github/workflows/pipeline.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Database Design

### 4.1 New Table: score_transparency

This table stores the full reasoning chain for every scored candidate — the data that powers the "why this score?" transparency feature.

```sql
CREATE TABLE score_transparency (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    run_date        DATE NOT NULL,

    -- Component 1: Insider buying reasoning
    ins_points          REAL,
    ins_max             INTEGER DEFAULT 30,
    ins_tier_label      TEXT,    -- "CEO/Chairman buy $500k+" etc
    ins_buyer_name      TEXT,
    ins_buyer_role      TEXT,
    ins_buy_amount      REAL,
    ins_buy_date        DATE,
    ins_buy_vs_comp     TEXT,    -- "84% of annual compensation"
    ins_at_3yr_low      BOOLEAN,
    ins_near_low_bonus  REAL,    -- bonus points awarded
    ins_selling_penalty REAL,   -- penalty points deducted
    ins_reasoning       TEXT,   -- plain English: "CEO bought $640k on Mar 15..."

    -- Component 2: Bond safety reasoning
    bond_points         REAL,
    bond_max            INTEGER DEFAULT 25,
    bond_tier_label     TEXT,
    bond_price          REAL,
    bond_maturity       DATE,
    bond_tier           TEXT,
    overhang_ratio      REAL,
    asc842_flag         BOOLEAN,
    asc842_lease_pct    REAL,
    bond_reasoning      TEXT,   -- plain English: "Bonds at 84, caution zone..."

    -- Component 3: FCF / valuation reasoning
    fcf_points          REAL,
    fcf_max             INTEGER DEFAULT 20,
    fcf_tier_label      TEXT,
    fcf_yield           REAL,
    ptbv                REAL,
    fcf_3yr_avg         REAL,
    fcf_per_share       REAL,
    fcf_consecutive_pos INTEGER,
    fcf_consecutive_bonus REAL,
    fcf_reasoning       TEXT,   -- plain English: "FCF yield 14.2%, P/TBV 0.72..."

    -- Component 4: Institutional reasoning
    inst_points         REAL,
    inst_max            INTEGER DEFAULT 15,
    inst_tier_label     TEXT,
    inst_fund_name      TEXT,
    inst_fund_pct       REAL,
    inst_fund_added     BOOLEAN,
    inst_insider_own    REAL,
    inst_multi_fund_bonus REAL,
    inst_reasoning      TEXT,   -- plain English: "Greenlight Capital holds 6.2%..."

    -- Component 5: Technical reasoning
    tech_points         REAL,
    tech_max            INTEGER DEFAULT 10,
    tech_tier_label     TEXT,
    tech_rsi            REAL,
    tech_rsi_trend      TEXT,
    tech_weeks_improving INTEGER,
    tech_peer_confirm   BOOLEAN,
    tech_peer_bonus     REAL,
    tech_support_retest BOOLEAN,
    tech_reasoning      TEXT,   -- plain English: "RSI 34, improving for 4 weeks..."

    -- Sector modifier reasoning
    sector_modifier     REAL,
    sector_etf_return   REAL,
    sector_stock_return REAL,
    sector_peers_down   INTEGER,
    sector_reasoning    TEXT,   -- plain English: "Energy sector also down 41%..."

    -- Final total reasoning
    total_score         REAL,
    total_reasoning     TEXT,   -- one paragraph plain English summary

    UNIQUE(ticker, run_date)
);
```

### 4.2 All Other Tables

Same schema as v1.0 — stocks, scanner_runs, candidates, watchlist, metric_history, alerts, swing_candidates, value_funds, edgar_cache. See v1.0 for full definitions.

---

## 5. Data Pipeline Design

### 5.1 config.py

Same as v1.0. No changes.

### 5.2 Layer Module Interface

Same as v1.0. Each layer takes a list of dicts and returns a filtered list with new fields added.

### 5.3 Caching Strategy

Same as v1.0. No changes.

---

## 6. Confidence Score Engine Design

### 6.1 Score Engine — Updated for Transparency

```python
# scoring/confidence_score.py

class ConfidenceScorer:
    def score(self, stock: dict) -> dict:
        components = {
            "insider":       self._score_insider(stock),
            "bonds":         self._score_bonds(stock),
            "fcf":           self._score_fcf(stock),
            "institutional": self._score_institutional(stock),
            "technical":     self._score_technical(stock),
        }

        sector_modifier = self._sector_modifier(stock)
        base_total = sum(c["points"] for c in components.values())
        total = min(100, base_total + sector_modifier)

        tier = self._get_tier(total)
        upside = UpsideCalc().calculate(stock)
        risk_flags = RiskFlagGenerator().generate(stock)
        action_steps = ActionStepGenerator().generate(stock, components)
        top_signal = self._get_top_signal(components, stock)

        # NEW: build full transparency chain
        transparency = TransparencyBuilder().build(
            stock, components, sector_modifier, total
        )

        return {
            "score_total": round(total, 1),
            "score_tier": tier,
            "score_label": tier["plain_label"],      # NEW: plain English label
            "sector_modifier": sector_modifier,
            "components": components,
            "transparency": transparency,             # NEW: full reasoning chain
            "conservative_upside": upside["conservative"],
            "bull_upside": upside["bull"],
            "diluted_upside": upside["diluted"],
            "dilution_risk_pct": upside["dilution_pct"],
            "risk_flags": risk_flags,
            "action_steps": action_steps,
            "top_signal": top_signal,
            "suggested_position": tier["suggested_position"],
        }

    def _get_tier(self, score: float) -> dict:
        if score >= 80:
            return {
                "label": "Exceptional",
                "plain_label": "Very strong buy signal",
                "suggested_position": "4–6%",
                "color": "exceptional"
            }
        elif score >= 65:
            return {
                "label": "High Conviction",
                "plain_label": "Strong buy signal",
                "suggested_position": "3–4%",
                "color": "high_conviction"
            }
        elif score >= 40:
            return {
                "label": "Speculative",
                "plain_label": "Worth a small position",
                "suggested_position": "1–2%",
                "color": "speculative"
            }
        else:
            return {
                "label": "Watch Only",
                "plain_label": "Not yet — keep watching",
                "suggested_position": "0%",
                "color": "watch"
            }
```

### 6.2 Score Component Points — Same as v1.0

All point breakdowns (insider 30pts, bonds 25pts, FCF 20pts, institutional 15pts, technical 10pts) are unchanged from v1.0. See v1.0 for full tables.

---

## 7. Scoring Transparency System

This is a new section not in v1.0. It defines how the app communicates the scoring reasoning to the user at three levels of depth.

### 7.1 Three Levels of Transparency

**Level 1 — Summary (always visible, no interaction needed)**
A single plain-English sentence per component, shown in the score meter bar:
> "CEO bought $640k on March 15 — at a 3-year low"

**Level 2 — Breakdown (visible on tap/click of component bar)**
The full sub-signal detail for that component:
```
Insider buying: 22 out of 30 points

Why 22?
  Base score:       15 pts  (CEO/CFO buy $200k–$500k)
  +Bonus:           +5 pts  (purchase within 20% of 3yr low)
  +Bonus:           +2 pts  (purchase > 80% of annual compensation)
  Penalty:           0 pts  (no concurrent selling detected)
  ─────────────────────────
  Total:            22 / 30

Raw data:
  Buyer: Jane Smith, Chief Executive Officer
  Amount: $640,000 (84% of $759k annual compensation)
  Date: March 15, 2026
  Stock price at purchase: $27.40
  3yr low: $22.10  ← stock was 24% above 3yr low (qualifies for bonus)
  Open-market purchase: Yes (Form 4, transaction code P)
  Source: SEC EDGAR Form 4 → [link]
```

**Level 3 — Source (always linked)**
Every data point links directly to its source:
- Insider buy → EDGAR Form 4 filing
- Bond price → FINRA TRACE page
- FCF data → EDGAR 10-K filing
- Institutional holder → EDGAR 13F filing
- RSI data → "Computed from weekly closing prices via Yahoo Finance"

### 7.2 TransparencyBuilder Module

```python
# scoring/transparency.py

class TransparencyBuilder:
    def build(self, stock: dict, components: dict,
              sector_modifier: float, total: float) -> dict:
        """
        Builds the full reasoning chain for display on Page 3.
        Returns a dict with three levels per component.
        """
        return {
            "summary": self._build_summary(total, components, sector_modifier),
            "components": {
                name: self._build_component_transparency(name, comp, stock)
                for name, comp in components.items()
            },
            "sector": self._build_sector_transparency(stock, sector_modifier),
            "total_explanation": self._build_total_explanation(
                total, components, sector_modifier
            )
        }

    def _build_total_explanation(self, total, components, modifier) -> str:
        """
        Returns a plain-English paragraph explaining the total score.
        Example:
        "This stock scored 74/100. The strongest signal was insider buying
        (22/30) — the CEO made a large open-market purchase near a 3-year
        low. Bond safety scored 18/25 (caution zone, not ideal but not
        alarming). FCF yield is strong at 14/20. Institutional quality is
        moderate (10/15 — one known value fund holds a stake but hasn't
        recently added). Technical trend is improving (7.5/10 — RSI
        recovering from oversold). The energy sector is also in a
        multi-year downtrend, adding +5 bonus points."
        """
        # Build this dynamically from component scores
        ...
```

### 7.3 How Transparency Appears in the UI

The transparency system drives three specific UI behaviours:

**On Page 1 (Scanner table):**
- Hovering over the score number opens a mini-tooltip showing the top 2 signals that drove the score
- Example: "22/30 insider · 18/25 bonds"

**On Page 3 (Deep Dive), Zone 2:**
- Each score meter bar is clickable
- Clicking expands an inline panel showing Level 2 breakdown
- Panel shows: sub-signal breakdown, raw data values, source links
- Only one panel open at a time (accordion)

**On Page 3, Zone 1:**
- The total score explanation paragraph (Level 1 summary) appears directly below the score bar
- Single paragraph, plain English, tells the full story in 3–5 sentences
- Example: "This stock scored 74 because a large insider buy + safe bonds + strong FCF all fired together. The technical signal is improving but not confirmed yet. Main concern: bonds are in the caution zone."

---

## 8. Contextual Help System

### 8.1 Design Decision — Not a Separate Page

A standalone "Methodology" or "How It Works" page is a documentation anti-pattern. Users visit it once, skim it, and never return. It separates the explanation from the thing being explained, forcing the user to navigate away from their task to understand it.

The correct approach is **contextual help** — the explanation lives exactly where the question arises, one tap away, without leaving the current screen.

The help system has three layers, each serving a different depth of curiosity:

| Layer | Where | What it explains | Who uses it |
|-------|-------|-----------------|-------------|
| 1 | ⓘ icon on every metric | What this number means + why RK cares | Every user, constantly |
| 2 | Inside Level 2 score expansion | Why this signal is weighted this way | Users building conviction |
| 3 | "How this screener works" modal | Full 6-layer funnel + all thresholds | New users + curious users |

### 8.2 Layer 1 — Inline Tooltips on Every Metric

Every metric name displayed anywhere in the app — on Page 1 table headers, on Page 3 score bars, on Page 2 watchlist columns — has a small ⓘ icon immediately to its right. Hovering (desktop) or tapping (mobile) shows an instant tooltip. No navigation. No page change.

**Tooltip structure:**
```
[Metric name — bold]
[1–2 sentences: what this metric measures]
[1 sentence: why RK specifically uses it]
[Threshold: what value passes / fails in this app]
[Source: quote or timestamp from RK video — in small gray text]
```

**Complete tooltip content for every metric:**

| Metric | Tooltip content |
|--------|----------------|
| Signal strength (score) | The overall RK score from 0–100. Combines 5 signals: insider buying (30pts), bond safety (25pts), FCF yield (20pts), institutional quality (15pts), technical trend (10pts). Higher = more signals firing simultaneously. |
| Price-to-tangible-book (P/TBV) | Share price divided by tangible book value per share (total assets minus intangibles, goodwill, and total liabilities). RK anchors valuation to hard assets. Below 1.0 means you're buying $1 of assets for less than $1. Threshold: below 1.5 to pass Layer 3. |
| Simple FCF yield | 3-year average free cash flow (operating cash flow minus capex) divided by current market cap. Shows how much real cash the business generates relative to what you pay for it. RK uses 3-year average to smooth commodity cycles. Threshold: positive to pass; above 10% scores well. |
| Net common overhang | RK's custom metric: long-term liabilities + short-term debt − excess cash. Divided by annual FCF to give a "years to pay off" ratio. Flags overleveraged companies. Important: post-2019 operating leases are included — this app flags when leases distort the number. Threshold: below 15× to pass Layer 3. |
| Bond price | Price of the company's publicly traded bonds (from FINRA trade data). Bond investors are sophisticated — a bond trading at 90+ means credit markets think the company is fine. Below 70 = pricing in significant default risk. "Those bond folks tend to be on the ball." — RK, Part 2 video. Threshold: above 70 to pass Layer 5. |
| Insider buying | Open-market purchases of company stock by CEO, CFO, Chairman, or Directors — from SEC Form 4 filings. Grants and options excluded. RK says: "Sometimes I'll buy just based on that." Dollar amount matters more than share count. Post-selloff timing is the strongest version of this signal. |
| Institutional quality | Whether known value-oriented hedge funds or activist investors hold 5%+ stakes. Not index funds — specifically funds that do fundamental research and take concentrated positions. RK cross-checks whether the fund has a track record in similar situations. |
| Weekly RSI | Relative Strength Index computed on weekly closing prices, 14-period. Below 30 = oversold (potential turning point). RK uses weekly charts (not daily) to match his multi-year time horizon. An RSI that was below 30 and is now trending up = early signal sentiment is turning. |
| Sector context | How the stock's 3-year decline compares to its sector ETF. If the whole sector is also down, the pain is systemic — supply cuts happen, pessimism overshoots, and the rebound is violent. If only this stock is down while peers are up, something is specifically wrong with the company. |
| Upside (recovery case) | Bull-case target price = peak-cycle FCF per share × 18, divided by current price. RK explicitly asks "which of these could be a 10-bagger from the lows?" This gives the answer. It is not a prediction — it is the upside if earnings recover to prior peak levels. |
| Upside (base case) | Conservative target = 3-year average FCF per share × 12, divided by current price. Uses recent average earnings rather than peak, with a lower multiple. More realistic but less exciting than the recovery case. |
| Decline type | Whether the stock's decline looks cyclical (temporary — industry trough, will recover) or secular (permanent — industry is structurally dying). Computed from revenue trend, margin trend, and SIC industry code. A cyclical decline is an opportunity; a secular decline requires much stronger other signals. |
| Short interest % | Percentage of the float that is currently sold short. High short interest in a fundamentally solid company can amplify a recovery — shorts must buy back shares to cover, adding buying pressure. RK noted GME's extreme short interest but says it was not his primary thesis. |
| ASC 842 flag | A warning that operating lease liabilities (rent obligations, store leases, equipment leases) are included in the net common overhang calculation due to post-2019 accounting rules. For retailers, restaurants, and airlines this can make leverage appear higher than it really is. When this flag is shown, subtract lease liabilities for a truer picture. |

### 8.3 Layer 2 — "Why Does This Matter?" Inside Score Expansion

When the user clicks a score component bar to see the Level 2 breakdown (defined in Section 7), a blue "Why RK weights this" panel appears above the arithmetic breakdown. It contains:

1. A 2–3 sentence plain-English explanation of why RK specifically values this signal
2. A direct quote from RK (from his videos or livestreams) if one exists
3. The source: video title + approximate timestamp

**Content for each component:**

**Insider buying (30pts):**
> RK rates insider buying as his single most powerful signal — he gives it the most points (30/100) of any component. His reasoning: when a CEO spends hundreds of thousands of their own dollars buying shares on the open market — not options, not grants — during a period when the stock looks terrible, it means someone with complete knowledge of the business believes the price is deeply wrong. The timing matters too: buying near a multi-year low suggests they see a floor that the market doesn't.
>
> *"A big one for me. I weight this quite heavily. Sometimes I'll buy just based on that."*
> — Roaring Kitty, Investment Style Part 2 (buy criteria), ~5:03

**Bond safety (25pts):**
> Bond prices are RK's primary bankruptcy filter and arguably his most distinctive technique. Most retail investors only look at debt-to-equity ratios. RK goes further: he checks what the bond market itself is saying. Bond investors are professional, sophisticated, and have done detailed credit analysis. If they're selling a company's bonds at 70 cents on the dollar, they're pricing in real default risk. If bonds are near face value, the credit market considers the company safe. "Those bond folks tend to be on the ball with things." — RK Part 2, ~4:07
>
> *"I love that. I didn't used to look at that. Now I find it so helpful."*
> — Roaring Kitty, Investment Style Part 2, ~4:07

**FCF yield (20pts):**
> RK is deliberately simple about valuation. He doesn't build DCF models — he calls that "a waste of my time." Instead he computes one number: how much free cash does this business actually generate relative to what you're paying for it? He uses a 3-year average to avoid being misled by a single unusually good or bad year. For cyclical businesses (energy, materials, forestry) a single year can be wildly unrepresentative. The 3-year average is honest. He also checks price-to-tangible-book as a hard asset anchor — are you paying less than the book value of the physical assets?
>
> *"It only takes me a minute or two to calculate... just get a general idea."*
> — Roaring Kitty, Investment Style Part 1, ~2:00

**Institutional quality (15pts):**
> RK actively looks for respected value-oriented investors who independently arrived at the same conclusion. If a fund he respects — one that does deep fundamental research and takes concentrated positions — holds a 5%+ stake, it provides independent confirmation that the fundamental case holds up under professional scrutiny. He researches the fund itself: their track record, their stated philosophy, whether they've been right on similar situations before. Index funds don't count — they hold everything mechanically.
>
> *"I'm not ashamed to admit how much I lean on the analysis of other folks — some of them are more skilled than me. It's a big part of my process."*
> — Roaring Kitty, Investment Style Part 2, ~8:16

**Technical trend (10pts):**
> RK uses charts as a sentiment gauge, not a primary analysis tool. He gives technical signals the lowest weighting (10pts) of any component. His specific use: weekly RSI recovering from oversold territory signals that the worst of the selling may be over and market sentiment is beginning to turn. He uses weekly charts (not daily) because his time horizon is 1–3 years — daily noise is irrelevant. He also uses the compare function to overlay sector peers: if all peers are recovering together, it confirms a sector-level turn, not just a company-specific bounce.
>
> *"The charts do a good job of illustrating prevailing sentiment and even the fundamental events that are unfolding."*
> — Roaring Kitty, Investment Style Part 1, ~3:22

### 8.4 Layer 3 — "How This Screener Works" Modal

A single link in the app footer: **"How this screener works →"**

Clicking opens a full-page modal (or a dedicated section, depending on screen size). The modal is structured as follows:

**Section A: What this app is**
```
This screener implements the investment approach publicly described by
Keith Gill ("Roaring Kitty") in his YouTube videos and livestreams between
2019 and 2020. It does not represent his current views or activity.

Every stock on the US market is run through 6 filters every night.
Only stocks that pass all 6 appear in "Today's picks."
```

**Section B: The 6-layer funnel (visual)**

Each layer shown as a numbered card with:
- Layer name and plain-English description
- The specific threshold used and why
- How many stocks typically pass
- Which data source powers it

| Layer | Name | Threshold | Typical pass count | Source |
|-------|------|-----------|-------------------|--------|
| 1 | Universe | Active US listing, filed 10-K in 18 months, market cap $10M+ | ~6,000 | SEC EDGAR |
| 2 | Price pain | Down 40%+ from 3yr high | ~400 | Yahoo Finance |
| 3 | Fundamental value | P/TBV below 1.5, positive 3yr avg FCF, revenue above $50M | ~100 | SEC EDGAR XBRL |
| 4 | Conviction signals | Insider buy $200k+ OR value fund holds 5%+ | ~30 | SEC Form 4, 13D/13G |
| 5 | Survival check | Bonds above 70 (or no public debt), overhang/FCF below 15× | ~15 | FINRA TRACE |
| 6 | Technical confirmation | Weekly RSI improving from below 30 | ~10–15 | Yahoo Finance |

**Section C: The confidence score**
```
Stocks that pass all 6 layers are scored 0–100.
The score is not a prediction — it measures how strongly
each of RK's signals is firing for that stock right now.

Component weights:
  Insider buying         30 points  (RK's highest-weighted signal)
  Bond safety            25 points  (bankruptcy filter)
  FCF yield + valuation  20 points  (earnings power vs price)
  Institutional quality  15 points  (are smart investors agreeing?)
  Technical trend        10 points  (is sentiment starting to turn?)
  Sector context         ±5 points  (modifier — is the sector also down?)

Score → suggested position size:
  80–100  Very strong buy signal  → 4–6% of portfolio
  65–79   Strong buy signal       → 3–4% of portfolio
  40–64   Worth a small position  → 1–2% of portfolio
  0–39    Not yet                 → Watch only
```

**Section D: Important limitations**
```
This app automates the quantitative part of RK's process.
It does not and cannot replicate:

  · Judgment about the buyer's background and domain expertise
  · Assessment of management tone from earnings transcripts
  · Whether a business model decline is permanent or temporary
  · Portfolio-level context for position sizing
  · The "gestalt" synthesis RK describes as "comes down to feels"

Use this app to surface candidates efficiently.
Use your own judgment to make the final call.

Nothing on this app is financial advice.
```

**Section E: Data sources and freshness**
```
All data is fetched from free public sources:
  · Fundamentals: SEC EDGAR XBRL API (quarterly filings)
  · Prices + RSI: Yahoo Finance (nightly)
  · Insider buying: SEC EDGAR Form 4 filings (daily)
  · Institutional holders: SEC EDGAR 13D/13G filings (weekly)
  · Bond prices: FINRA TRACE public trade data (weekly)

Pipeline runs nightly after US market close.
Bond prices updated weekly (they change slowly for stable companies).
Fundamental data updated when new 10-K or 10-Q is filed.
```

### 8.5 Implementation Notes

**Tooltip implementation (Layer 1):**
- Built as a pure CSS/JS tooltip — no library needed
- Tooltip content stored in a `data-tooltip` attribute on the ⓘ icon
- Or loaded from a `tooltips.json` lookup file keyed by metric name
- On mobile: tap opens tooltip as a small bottom sheet (not hover)
- Tooltip dismisses on tap-outside or Escape key

```javascript
// tooltips.js — content for every metric tooltip
const TOOLTIPS = {
  "bond_price": {
    title: "Bond price",
    body: "Price of the company's publicly traded bonds from FINRA trade data...",
    threshold: "Above 70 to pass Layer 5",
    source: "RK Part 2 video, ~4:07"
  },
  "fcf_yield": {
    title: "Simple FCF yield",
    body: "3-year average free cash flow divided by current market cap...",
    threshold: "Positive to pass; above 10% scores well",
    source: "RK Part 1 video, ~2:00"
  },
  // ... all metrics
};
```

**"Why this matters" panel (Layer 2):**
- Content stored in `component_explanations.json`
- Loaded into the transparency panel when a meter bar is expanded
- Shown in a visually distinct blue panel above the arithmetic breakdown
- Quote displayed in italic with source attribution below

**Modal (Layer 3):**
- Triggered by footer link `id="how-it-works-link"`
- Modal built as a full-screen overlay div (not `position:fixed` — use a tall normal-flow wrapper)
- Funnel layers rendered from the same `config.py` thresholds used in the pipeline — single source of truth, never out of sync
- Close button top-right + tap-outside + Escape key

### 8.6 What Changed in the "What Changed" Table

Add this row to the v2.0 changelog table at the top of the document:

| Contextual help system | Not in design plan | Three-layer inline help: ⓘ tooltips on every metric, "why this matters" in score expansion, full "how it works" modal from footer |

---

## 9. API Contract Design

Same as v1.0 with one addition: `results.json` now includes a `transparency` object per candidate. See Section 6.2 for the updated results.json structure.

---

## 10. Frontend Architecture

### 9.1 Single Page Application

Same as v1.0 — single `index.html`, vanilla JS, hash-based router.

### 9.2 Zone Expander Component (New)

```javascript
// components/zone_expander.js
// Controls progressive disclosure on Page 3

class ZoneExpander {
  constructor(zoneEl) {
    this.zone = zoneEl;
    this.isExpanded = false;
    this.btn = zoneEl.querySelector('.zone-expand-btn');
    this.content = zoneEl.querySelector('.zone-content');
    this.btn.addEventListener('click', () => this.toggle());
  }

  toggle() {
    this.isExpanded = !this.isExpanded;
    this.content.style.display = this.isExpanded ? 'block' : 'none';
    this.btn.textContent = this.isExpanded
      ? 'Show less ↑'
      : 'Show full evidence — charts, insider timeline, management signals ↓';
    // Smooth scroll to zone when expanding
    if (this.isExpanded) {
      this.zone.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }
}
```

### 9.3 Score Transparency Expander Component (New)

```javascript
// components/score_transparency.js
// Controls the Level 2 accordion on each score meter bar

class ScoreTransparencyExpander {
  constructor(containerEl, transparencyData) {
    this.container = containerEl;
    this.data = transparencyData;
    this.openComponent = null;
    this._bindClicks();
  }

  _bindClicks() {
    this.container.querySelectorAll('.meter-row').forEach(row => {
      row.style.cursor = 'pointer';
      row.setAttribute('title', 'Click to see full breakdown');
      row.addEventListener('click', () => {
        const component = row.dataset.component;
        this.toggle(component, row);
      });
    });
  }

  toggle(component, row) {
    // Close previously open panel
    if (this.openComponent && this.openComponent !== component) {
      this._closePanel(this.openComponent);
    }
    if (this.openComponent === component) {
      this._closePanel(component);
      this.openComponent = null;
    } else {
      this._openPanel(component, row);
      this.openComponent = component;
    }
  }

  _openPanel(component, row) {
    const data = this.data.components[component];
    const panel = document.createElement('div');
    panel.className = 'transparency-panel';
    panel.id = `panel-${component}`;
    panel.innerHTML = this._renderPanel(data);
    row.after(panel);
    // Animate in
    requestAnimationFrame(() => panel.classList.add('panel-open'));
  }

  _renderPanel(data) {
    // Renders Level 2 breakdown: sub-signal points, raw data, source links
    return `
      <div class="transparency-header">How this score was calculated</div>
      <div class="transparency-breakdown">
        ${data.sub_signals.map(s => `
          <div class="transparency-row">
            <span class="t-label">${s.label}</span>
            <span class="t-points ${s.points >= 0 ? 't-positive' : 't-negative'}">
              ${s.points >= 0 ? '+' : ''}${s.points} pts
            </span>
          </div>
          <div class="transparency-reason">${s.reason}</div>
        `).join('')}
        <div class="transparency-total">Total: ${data.points} / ${data.max}</div>
      </div>
      <div class="transparency-raw">
        <div class="t-raw-title">Raw data used</div>
        ${Object.entries(data.raw_data).map(([k, v]) => `
          <div class="transparency-row">
            <span class="t-label">${k}</span>
            <span class="t-value">${v.value}</span>
          </div>
        `).join('')}
      </div>
      <div class="transparency-source">
        Source: <a href="${data.source_url}" target="_blank">${data.source_label} →</a>
      </div>
    `;
  }
}
```

---

## 11. Navigation Design

### 10.1 Updated Nav — Plain English Labels

**Problem in v1.0:** "RK Scanner", "Deep Dive", "Swing Trader" were jargon.

**v2.0 Nav structure:**

```html
<nav class="app-nav">
  <a href="#scanner" class="nav-tab active">
    <span class="nav-icon">◎</span>
    <span class="nav-primary">Today's picks</span>
    <span class="nav-sub">RK deep value scanner</span>
  </a>
  <a href="#watchlist" class="nav-tab">
    <span class="nav-icon">◉</span>
    <span class="nav-primary">My watchlist</span>
    <span class="nav-sub">Stocks you're tracking</span>
  </a>
  <a href="#deepdive" class="nav-tab">
    <span class="nav-icon">⊕</span>
    <span class="nav-primary">Analyse a stock</span>
    <span class="nav-sub">Enter any ticker</span>
  </a>
  <a href="#swing" class="nav-tab nav-tab--swing">
    <span class="nav-icon">↗</span>
    <span class="nav-primary">Swing trades</span>
    <span class="nav-sub">Short-term momentum</span>
  </a>
</nav>
```

**Mobile nav (480px and below):** Show only icons + primary label, hide subtitle. Tabs stack horizontally and scroll if needed.

### 10.2 Active State and Context

The active tab shows a left-border accent and slightly raised background. The page title below the nav repeats the plain-English context:

- Page 1: "Today's deep value picks — updated nightly"
- Page 2: "Stocks you're tracking — 3 stocks on your watchlist"
- Page 3: "Analyse any stock against RK's criteria"
- Page 4: "Short-term swing trade setups — different strategy from Pages 1–3"

---

## 12. UI Design — Page 1: RK Scanner

### 11.1 Layout Structure

```
┌────────────────────────────────────────────────────────────────┐
│  [Today's picks] [My watchlist] [Analyse a stock] [Swing ↗]   │
│  ────────────────────────────────────────────────────────────  │
│  Today's deep value picks                  Updated: Tonight    │
│  5,842 stocks screened · 12 candidates                         │
│  ────────────────────────────────────────────────────────────  │
│  [All sectors ▼]  [All signals ▼]  [Sort: Signal strength ▼]  │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  STOCK              SIGNAL         UPSIDE    ACTION       │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  RRC                ████ 74        5.8×      [Analyse]    │ │
│  │  Range Resources    Strong buy     Recovery  [+ Watch]    │ │
│  │  Energy · 3yr −67%  CEO bought $640k                      │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  RFP                ███░ 68        4.2×      [Analyse]    │ │
│  │  Resolute Forest    Strong buy     Recovery  [+ Watch]    │ │
│  │  Materials · 3yr −58%  Value fund 6% + insider buy        │ │
│  ├───────────────────────────────────────────────────────────┤ │
│  │  GME                ██░░ 61        8.1×      [Analyse]    │ │
│  │  GameStop           Worth watching High upside [+ Watch]  │ │
│  │  Retail · 3yr −81%  FCF yield 18% · high short interest   │ │
│  └───────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### 11.2 Table Row Design — Two-Line Card Style

Each row is a two-line card, not a single-line data row. This gives hierarchy without needing many columns.

**Line 1 (primary):** Ticker large · Score bar · Upside · Analyse button
**Line 2 (secondary):** Full company name · Plain-English signal label · Top signal detail
**Line 3 (context, muted):** Sector · 3yr decline · Sub-signal summary

This is 3 lines per row but they communicate: What is it → How strong is the signal → Why.

### 11.3 Score + Label Display

**Problem in v1.0:** "72 · High Conviction" — two equal-weight items.

**v2.0 approach:** Score bar is the primary visual. Plain-English label below it. Number secondary.

```
████████░░  74                    ← bar first, number inline
Strong buy signal                 ← plain English label, larger than number
```

**Plain-English labels by tier:**

| Score | Internal tier | Plain-English label (shown to user) |
|-------|--------------|-------------------------------------|
| 80–100 | Exceptional | Very strong buy signal |
| 65–79 | High Conviction | Strong buy signal |
| 40–64 | Speculative | Worth a small position |
| 0–39 | Watch Only | Not yet — keep watching |

### 11.4 Column Priority for Responsive Design

| Column | Always visible | Hidden at 768px | Hidden at 480px |
|--------|---------------|-----------------|-----------------|
| Ticker + company | ✓ | ✓ | ✓ |
| Score bar + label | ✓ | ✓ | ✓ |
| Upside | ✓ | ✓ | Hidden |
| Top signal detail | ✓ | Hidden (tooltip) | Hidden |
| Sector + decline | ✓ | Hidden | Hidden |
| Analyse button | ✓ | ✓ | ✓ (icon only) |
| Watch button | ✓ | ✓ | Icon only |

On mobile (480px), each row shows: Ticker · Score bar · Analyse button. Everything else accessible via the expanded row (tap row to expand).

### 11.5 Score Tooltip on Hover

Hovering over the score bar on desktop opens a mini-tooltip:

```
RRC · 74/100

Insider buying:   22/30  CEO bought $640k
Bond safety:      18/25  Bonds at 84
FCF yield:        14/20  FCF yield 14.2%
Institutional:    10/15  Greenlight 6.2%
Technical:        7.5/10 RSI improving
Sector bonus:      +5    Energy also down

→ Click to see full analysis
```

This is Level 1 transparency directly from the table — the user never has to leave Page 1 to understand the score composition.

### 11.6 Filters

**Sector filter:** Dropdown with all sectors present in today's results. "All sectors" default.

**Signal filter:** "All signals" (default) · "Strong buy only (65+)" · "Any candidate (40+)" · "Show everything"

**Sort:** Signal strength (default, highest first) · Upside potential · Most recent insider buy · Sector

### 11.7 Empty State

**Problem in v1.0:** Four-sentence apology.

**v2.0:** One sentence + one action:

```
No strong signals today.
[Show candidates with any score (40+) →]
```

If even that is empty:
```
No candidates passed all filters today.
[Run the pipeline to refresh →]  (only shown if results are > 2 days old)
```

---

## 13. UI Design — Page 2: Watchlist

### 12.1 Layout Structure

```
┌─────────────────────────────────────────────────────────────────┐
│  My watchlist — 4 stocks tracked                                │
│  ────────────────────────────────────────────────────────────── │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Opportunity alert  RRC score crossed 65 — now Strong buy  │ │  ← green
│  │  Risk alert         GME bond price dropped to 78           │ │  ← amber
│  │  [Dismiss all]                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Add stock: [  Ticker or company name...  ] [Add to watchlist +] │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  RRC · Range Resources                        [Analyse] [×] │ │
│  │  ████████░░ 74  Strong buy signal ↑ Improving              │ │
│  │  [score sparkline]  8-week trend: improving steadily        │ │
│  │  Last insider: CEO $640k · Mar 15   Bonds: Caution (84)    │ │
│  │  ★ Now in Today's picks                                     │ │
│  ├─────────────────────────────────────────────────────────────┤ │
│  │  GME · GameStop                               [Analyse] [×] │ │
│  │  ██████░░░░ 61  Worth a small position → Stable             │ │
│  │  [score sparkline]  8-week trend: stable around 58-62      │ │
│  │  Last insider: Director $420k · Apr 2  Bonds: Safe (92)    │ │
│  │  Notes: "Barry bought at $1. Console cycle Q4 catalyst."   │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 Alert Visual Hierarchy

**Problem in v1.0:** All alerts looked identical.

**v2.0:** Two distinct alert types with different visual treatment:

```css
.alert-opportunity {
    background: var(--color-background-success);
    border-left: 3px solid var(--color-border-success);
    /* meaning: something good happened — a score went up, insider bought */
}

.alert-risk {
    background: var(--color-background-warning);
    border-left: 3px solid var(--color-border-warning);
    /* meaning: something changed that needs attention — bond dropped, score fell */
}
```

Alert text format:
- Opportunity: "[Ticker]: [What improved] — [plain English implication]"
  → "RRC: Score crossed 65 — now a strong buy signal (was 58 last week)"
- Risk: "[Ticker]: [What worsened] — [plain English implication]"
  → "GME: Bond price dropped to 78 — entering caution zone, review position"

### 12.3 Sparkline with Trend Label

**Problem in v1.0:** Sparkline had no interpretation label.

**v2.0:** Every sparkline has a trend label:

```
[/\/‾‾‾]  Improving steadily     ← green text
[‾‾‾\/‾]  Declined then stabilised ← gray text
[\/\//‾]  Recovering             ← green text
[‾‾‾\/\]  Declining              ← amber text
[─────]   Stable                 ← gray text
```

The label is computed from the slope of the last 3 data points vs the prior 3.

### 12.4 Inline Settings Panel

Clicking the gear icon (or tapping "Settings" on mobile) expands an inline panel — not a modal — below the stock row:

```
Alert settings for GME
──────────────────────────────────────────
When score crosses:  [65  ] (currently 61)
When new insider buy appears: [✓]
When bond drops below: [75  ] (currently 92 — safe)
When RSI crosses above 35 from oversold: [✓]
──────────────────────────────────────────
Notes — your research on this stock:
┌──────────────────────────────────────────┐
│ Barry Sears bought at ~$1. Console cycle │
│ thesis. Check SA user ValueHunter88.     │
│ Target: $12–15 on recovery scenario.     │
└──────────────────────────────────────────┘
[Save settings]  [Remove from watchlist]
```

### 12.5 "Now in Today's Picks" Indicator

When a watchlisted stock appears in the Page 1 scanner, it gets a star badge: "★ Now in Today's picks". This is the key signal that a stock the user has been patiently watching has crossed all filter thresholds. It is the most actionable alert the app can generate.

---

## 14. UI Design — Page 3: Stock Deep Dive

### 13.1 Three-Zone Progressive Disclosure

**Problem in v1.0:** 12 sections all visible at once — overwhelming.

**v2.0:** Three distinct zones. Zones 1 and 2 always visible. Zone 3 collapsed by default.

```
Search: [  Enter ticker, e.g. RRC, GME, FOSL  ]  [Analyse →]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ZONE 1 — The decision        (always visible)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Verdict card: score + label + upside
  Total score explanation (plain English paragraph)
  Do these 3 things next (action steps)
  Watch out for (3 key risks)
  [+ Add to Watchlist]  [View on EDGAR →]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ZONE 2 — Why this score      (one scroll down)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Score breakdown — 5 clickable meter bars
    ↳ Click any bar → Level 2 transparency panel expands inline
  10-year FCF history chart
  Sector context explanation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ZONE 3 — Full evidence       (collapsed, tap to expand)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Show full evidence ↓]

  When expanded:
  → Weekly price + RSI chart (3 years)
  → Sector peer comparison chart
  → Insider buying timeline (with price at time of purchase)
  → Institutional holders table
  → Bond status detail
  → Decline type assessment (cyclical vs secular)
  → Management signals (from earnings transcript)
  → All risk flags (full list)
  → All action steps (full list)
```

### 13.2 Zone 1 — Verdict Card

**Problem in v1.0:** Score dial (SVG arc) was decorative, not informative.

**v2.0:** Large score number + horizontal bar + plain English label:

```
┌──────────────────────────────────────────────────────────┐
│  RRC  Range Resources Corp               Energy sector   │
│  ─────────────────────────────────────────────────────── │
│                                                           │
│   74                   ████████████████░░░░ 74/100        │
│   Strong buy signal    Suggested: 3–4% of portfolio       │
│                                                           │
│   Recovery case upside: 5.8×    Base case: 2.4×          │
│   (based on historical earnings recovery to 2018 levels) │
│                                                           │
│   "Strong insider buy + safe bonds + solid FCF yield.    │
│    Technical signal improving but not yet confirmed.      │
│    Sector-wide pain adds confidence to recovery thesis."  │
│                                                           │
│  [+ Add to Watchlist]        [View on EDGAR →]           │
└──────────────────────────────────────────────────────────┘
```

The italic paragraph under the score is the `total_explanation` from the transparency system — a plain-English summary of why this stock scored 74. It's generated dynamically, not hand-written.

### 13.3 Zone 1 — Action Steps

**Problem in v1.0:** Action steps were at the bottom of the page.

**v2.0:** Action steps are in Zone 1, immediately after the verdict card. Max 3 shown. User can expand to see all.

```
Do these 3 things next
──────────────────────────────────────────────────────────
1  Read the debt footnote in the latest 10-Q             EDGAR →
   Check covenant terms — bonds are in caution zone

2  Verify the buyer: search "Jane Smith Range Resources"  Search →
   CEO background in energy = stronger conviction signal

3  Wait for weekly RSI to cross above 40
   RSI at 34 and improving — not confirmed yet
```

Each step has: number → action verb → specific detail → link (if applicable). No step is vague. "Read the debt footnote" is specific. "Do more research" would not be acceptable.

### 13.4 Zone 1 — Risk Flags

Max 3 risk flags visible in Zone 1. Prioritised by severity. User can expand to see all.

```
Watch out for
──────────────────────────────────
⚠  Bonds at 84 — caution zone     (amber — needs attention)
○  Insider ownership 8%            (gray — minor concern)
○  RSI not confirmed yet           (gray — timing risk)
```

### 13.5 Zone 2 — Score Breakdown with Transparency

Each score meter bar is clickable. The "Click for breakdown" hint is shown on the first bar only (with a small "↕" icon). After the user clicks one bar, they understand the pattern.

```
Why this score?  Click any bar to see the full calculation.

Insider buying  ████████████████████░░░░  22/30  ↕
  CEO bought $640k on Mar 15 — at 3yr low

Bond safety     ████████████████████░░░░  18/25  ↕
  Bonds at 84 — caution zone, matures 2029

FCF yield       ████████████████░░░░░░░░  14/20  ↕
  FCF yield 14.2% · P/TBV 0.72

Institutional   ██████████████░░░░░░░░░░  10/15  ↕
  Greenlight Capital holds 6.2%

Technical       ████████████████░░░░░░░░  7.5/10 ↕
  RSI 34, improving for 4 weeks

─────────────────────────────────────────────────
Sector bonus: Energy also down 41%          +5 pts
Total:  22 + 18 + 14 + 10 + 7.5 + 5 =  74 / 100
```

The arithmetic is shown explicitly at the bottom. The user can verify the total themselves. Full transparency.

**When a bar is clicked (Level 2 expansion):**

```
▼ Insider buying — 22 out of 30 points

  How the 22 was calculated:
  ┌───────────────────────────────────────────────────┐
  │ CEO/CFO buy $200k–$500k            +15 pts (base) │
  │ Purchase within 20% of 3yr low     + 5 pts (bonus)│
  │ Purchase > 80% of annual comp      + 2 pts (bonus)│
  │ No concurrent insider selling       0 pts (penalty)│
  │ ───────────────────────────────────────────────── │
  │ Total                               22 / 30        │
  └───────────────────────────────────────────────────┘

  Raw data:
  Buyer name: Jane Smith
  Role: Chief Executive Officer (since 2019)
  Amount: $640,000
  Annual compensation: $759,000 — purchase = 84% of annual comp
  Purchase date: March 15, 2026
  Stock price at purchase: $27.40
  3yr low: $22.10 — stock was 24% above 3yr low ✓
  Transaction type: Open-market purchase (Form 4, code P) ✓

  Source: SEC EDGAR Form 4 → [link]
  Filed: March 16, 2026
```

### 13.6 Zone 3 — Full Evidence (Collapsed)

The collapse button text is specific, not generic:

```
[Show full evidence — charts, insider timeline, peer comparison, management signals ↓]
```

When expanded, all remaining sections appear in this order:
1. Weekly price + RSI chart (3yr)
2. Sector peer comparison chart (normalised, 3yr)
3. Insider buying timeline (table with price-at-purchase vs today)
4. Institutional holders table (with value fund badges)
5. Bond status detail (price, maturity, yield, coverage ratio)
6. Decline type assessment (cyclical vs secular with explanation)
7. Management signals panel (Gemini transcript analysis)
8. All remaining risk flags
9. All remaining action steps

### 13.7 Loading State (On-Demand, Phase 3)

```
Analysing RRC...

  ● Fetching price history               ✓ done
  ● Loading fundamentals from EDGAR      ✓ done
  ● Checking insider filings             ✓ done
  ● Fetching bond prices                 ● running...
  ○ Computing confidence score           (waiting)
  ○ Building score explanation           (waiting)

About 10–15 seconds total.
```

Each step checks off as it completes. The user sees progress, not a blank screen.

---

## 15. UI Design — Page 4: Swing Trader

### 14.1 Visual Differentiation from Page 1

**Problem in v1.0:** Same layout as Page 1 — users could confuse strategies.

**v2.0:** Distinct visual language:

| Element | Page 1 (RK Deep Value) | Page 4 (Swing Trader) |
|---------|----------------------|----------------------|
| Accent color | Green (#16a34a) | Cyan/blue (#0891b2) |
| Page background tint | Very light green | Very light blue |
| Score label style | "Strong buy signal" | "Clean setup" / "Trade now" |
| Stock metric shown | FCF yield, P/TBV | Revenue growth, RSI |
| Action shown | "Analyse (deep dive)" | "Entry zone, target, stop" |
| Hold time shown | "1–3 year thesis" | "2–8 week trade" |

### 14.2 Permanent Context Banner

```
┌────────────────────────────────────────────────────────────────┐
│  Swing Trader — short-term momentum strategy                    │
│  2–8 week hold targets. Growing companies, not beaten-down ones.│
│  This is a different strategy from the deep value picks on     │
│  "Today's picks". Do not confuse the two.                      │
└────────────────────────────────────────────────────────────────┘
```

This banner is permanent — not dismissable. It appears on every visit to Page 4.

### 14.3 Table Columns — Momentum Language

| Column | Swing Trader label | Notes |
|--------|-------------------|-------|
| Ticker + company | Same | |
| Score | "Setup strength" | Same 0–100, different label |
| Setup type | "Breakout / Pullback / Consolidation" | New column |
| Entry zone | "$27.40 – $28.20" | Price range to enter |
| Target | "+20% → $33.60" | Profit target |
| Stop | "−8% → $25.98" | Stop loss |
| Risk/reward | "2.5 : 1" | Target gain / stop loss |

### 14.4 Swing Score Labels

| Score | Label |
|-------|-------|
| 80–100 | Trade now |
| 60–79 | Strong setup |
| 40–59 | Developing setup |
| 0–39 | Not ready |

---

## 16. Component Library

### 15.1 Score Bar Component

```html
<div class="score-bar-component" data-score="74" data-max="100">
  <div class="score-bar-top">
    <span class="score-number">74</span>
    <span class="score-bar-track">
      <span class="score-bar-fill" style="width: 74%"></span>
    </span>
    <span class="score-outof">/ 100</span>
  </div>
  <div class="score-label">Strong buy signal</div>
  <div class="score-position">Suggested: 3–4% of portfolio</div>
</div>
```

```css
.score-bar-component { display: flex; flex-direction: column; gap: 4px; }
.score-bar-top { display: flex; align-items: center; gap: 10px; }
.score-number { font-size: 32px; font-weight: 500; color: var(--score-color); min-width: 44px; }
.score-bar-track { flex: 1; height: 8px; background: var(--color-border-tertiary);
                   border-radius: 4px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 4px; background: var(--score-color); }
.score-outof { font-size: 12px; color: var(--color-text-tertiary); }
.score-label { font-size: 15px; font-weight: 500; color: var(--score-color); }
.score-position { font-size: 12px; color: var(--color-text-secondary); }
```

### 15.2 Meter Bar (Zone 2)

```html
<!-- Clickable meter bar with Level 2 transparency -->
<div class="meter-row" data-component="insider" role="button"
     aria-expanded="false" tabindex="0"
     title="Click to see full breakdown of insider buying score">
  <span class="meter-label">Insider buying</span>
  <div class="meter-track" aria-hidden="true">
    <div class="meter-fill" style="width: 73%"></div>
  </div>
  <span class="meter-val">22/30</span>
  <span class="meter-expand-hint" aria-hidden="true">↕</span>
</div>
<div class="meter-detail">CEO bought $640k · Mar 15 · at 3yr low</div>
<!-- Transparency panel injected here by JS when clicked -->
```

### 15.3 Action Step Component

```html
<div class="action-step">
  <div class="action-step-num" aria-hidden="true">1</div>
  <div class="action-step-body">
    <div class="action-step-text">
      Read the debt footnote in the latest 10-Q
    </div>
    <div class="action-step-detail">
      Check covenant terms — bonds are in caution zone (84)
    </div>
  </div>
  <a href="https://www.sec.gov/..." target="_blank"
     class="action-step-link" aria-label="Open EDGAR filing in new tab">
    EDGAR →
  </a>
</div>
```

### 15.4 Risk Flag Component

```html
<!-- Two variants: warning (amber) and note (gray) -->
<div class="risk-flag risk-flag--warning" role="alert">
  <span class="risk-flag-icon" aria-hidden="true"></span>
  <span class="risk-flag-text">
    Bonds at 84 — caution zone. Read debt footnote before sizing up.
  </span>
</div>

<div class="risk-flag risk-flag--note">
  <span class="risk-flag-icon" aria-hidden="true"></span>
  <span class="risk-flag-text">
    Insider ownership 8% — below RK's 20% preference
  </span>
</div>
```

### 15.5 Sparkline with Trend Label

```html
<div class="sparkline-wrapper">
  <canvas class="sparkline-canvas" width="80" height="24"
          aria-label="Score trend over 8 weeks: improving steadily"></canvas>
  <span class="sparkline-trend sparkline-trend--improving">
    Improving steadily
  </span>
</div>
```

### 15.6 Alert Component (Two Types)

```html
<!-- Opportunity alert — green -->
<div class="alert-banner alert-banner--opportunity" role="alert">
  <span class="alert-type">Opportunity</span>
  <span class="alert-message">
    RRC score crossed 65 — now a strong buy signal (was 58 last week)
  </span>
  <button class="alert-dismiss" aria-label="Dismiss alert">×</button>
</div>

<!-- Risk alert — amber -->
<div class="alert-banner alert-banner--risk" role="alert">
  <span class="alert-type">Risk alert</span>
  <span class="alert-message">
    GME bond price dropped to 78 — entering caution zone
  </span>
  <button class="alert-dismiss" aria-label="Dismiss alert">×</button>
</div>
```

---

## 17. Color System and Typography

### 16.1 CSS Variables (Updated)

```css
:root {
  /* Score colors — tied to tier */
  --score-exceptional:     #14532d;
  --score-high-conviction: #166534;
  --score-speculative:     #92400e;
  --score-watch:           #991b1b;

  /* Alert colors */
  --alert-opportunity-bg:   #dcfce7;
  --alert-opportunity-border: #16a34a;
  --alert-opportunity-text:  #166534;
  --alert-risk-bg:          #fef3c7;
  --alert-risk-border:      #d97706;
  --alert-risk-text:        #92400e;

  /* Swing trader theme */
  --swing-primary:   #0891b2;
  --swing-bg-tint:   #f0f9ff;
  --swing-label:     #0e7490;

  /* Transparency panel */
  --transparency-bg:      #f8fafc;
  --transparency-border:  #e2e8f0;
  --transparency-positive: #166534;
  --transparency-negative: #991b1b;

  /* All base colors same as v1.0 */
  --color-primary:   #16a34a;
  --color-warning:   #d97706;
  --color-danger:    #dc2626;
  --color-info:      #2563eb;
  --bg-primary:      #ffffff;
  --bg-secondary:    #f9fafb;
  --text-primary:    #111827;
  --text-secondary:  #6b7280;
  --border-light:    #e5e7eb;
  --font-sans:       -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-mono:       'SF Mono', 'Fira Code', monospace;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg-primary:    #111827;
    --bg-secondary:  #1f2937;
    --text-primary:  #f9fafb;
    --text-secondary: #9ca3af;
    --border-light:  #374151;
    --transparency-bg: #1e293b;
    --transparency-border: #334155;
    --swing-bg-tint: #0c1a24;
  }
}
```

---

## 18. Responsive Design — Mobile Breakpoints

### 17.1 Breakpoint System

```css
/* Mobile first — base styles are mobile */
/* Tablet: 640px+ */
@media (min-width: 640px) { ... }
/* Desktop: 1024px+ */
@media (min-width: 1024px) { ... }
```

### 17.2 Page 1 Scanner — Responsive Behaviour

**Below 480px (mobile):**
- Table becomes card stack — each stock is a card, not a row
- Card shows: Ticker + company (line 1), Score bar + label (line 2), Analyse button (full width)
- Tap card to expand: shows upside, top signal, sector context
- Watchlist add: heart/plus icon in top-right of card

**480px – 768px (tablet):**
- Table layout retained
- Columns: Ticker+company · Score bar+label · Upside · Action buttons
- Top signal detail hidden (accessible via tooltip on hover or row expand)
- Sector context hidden

**Above 768px (desktop):**
- Full table with all columns
- Hover tooltip on score shows mini breakdown
- Both Analyse and Watch buttons visible

### 17.3 Page 3 Deep Dive — Responsive Behaviour

**Below 640px:**
- Zones stack vertically (same as desktop, already natural)
- Zone 3 collapsed by default (same behaviour)
- Score breakdown: meter bars go full width
- Charts: Chart.js responsive mode, height reduced to 160px
- Transparency panels: full-width overlay panels instead of inline expansion

**640px – 1024px:**
- Same as mobile but charts at full height (240px)
- Transparency panels expand inline below the bar

**Above 1024px:**
- Optional: two-column layout for Zone 2 (score bars on left, FCF chart on right)
- Transparency panels expand inline

### 17.4 Navigation — Responsive Behaviour

**Below 640px:**
- 4 tabs in a horizontal scroll row
- Show icon + primary label only (hide sub-label)
- Tab text: "Today" · "Watchlist" · "Analyse" · "Swing"

**640px and above:**
- Full 4-tab nav with primary label + sub-label

---

## 19. Accessibility

### 18.1 Score Tier — Not Color-Only

**Problem in v1.0:** Tier was indicated by color alone (green/amber/red).

**v2.0:** Three layers of differentiation:

1. Color (green / amber / red)
2. Text label ("Strong buy signal" / "Worth watching" / "Not yet")
3. Icon prefix (filled circle ● / half circle ◑ / empty circle ○)

```html
<!-- Color + icon + text — works for color-blind users -->
<span class="tier-badge tier-badge--high-conviction">
  <span class="tier-icon" aria-hidden="true">●</span>
  Strong buy signal
</span>
```

### 18.2 Keyboard Navigation

- All interactive elements (table rows, meter bars, zone expanders, alert dismiss) are keyboard focusable
- Tab order follows visual reading order (left-to-right, top-to-bottom)
- Enter or Space activates buttons and expandable rows
- Escape closes any open panel or tooltip

```css
/* Focus ring — visible in both light and dark mode */
:focus-visible {
  outline: 2px solid var(--color-info);
  outline-offset: 2px;
  border-radius: 4px;
}
```

### 18.3 Screen Reader Support

- Score bars have `aria-label`: "RRC signal strength: 74 out of 100, Strong buy signal"
- Expandable meter bars have `aria-expanded` state
- Alert banners have `role="alert"` so they are announced immediately
- Charts have `aria-label` describing what the chart shows
- Sparklines have `aria-label` with the trend description

### 18.4 Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  .score-bar-fill,
  .meter-fill,
  .transparency-panel,
  .zone-content {
    transition: none;
    animation: none;
  }
}
```

### 18.5 Text Scaling

All sizes use relative units (rem, em) so the layout respects browser font size preferences. No fixed pixel heights on content areas.

---

## 20. Error States and Loading States

### 19.1 Pipeline Not Run

```
Today's picks — no data yet

To see candidates, run the pipeline:

  python pipeline/main.py

Expected time: 30–45 minutes
After it finishes, refresh this page.
```

No apology. Just instructions.

### 19.2 Individual Data Point Unavailable

Each data point that could not be fetched shows a specific fallback — never a generic "error":

| Data point | Fallback display |
|-----------|-----------------|
| Bond price | "Bond data unavailable — [check manually at FINRA →]" |
| Insider data | "No insider filings found in last 180 days" |
| FCF data | "Less than 3yr of EDGAR data — [X]-year average used" |
| Transcript | "Transcript not found — [search on Seeking Alpha →]" |
| Institutional | "No 13F data found — may be below reporting threshold" |

### 19.3 Stale Data Warning

If results.json is more than 36 hours old:

```
┌─────────────────────────────────────────────────────────┐
│  Data from [date] — may be outdated                     │
│  Run pipeline to refresh: python pipeline/main.py       │
└─────────────────────────────────────────────────────────┘
```

Shown as a non-blocking amber banner, not a blocking overlay.

---

## 21. Build Sequence

### 20.1 Phase 1 Build Order — 4 Weeks

```
Week 1 — Pipeline foundation
  Day 1:  Project structure, config.py, SQLite schema, logger, .env
  Day 2:  Layer 1 — universe fetch (EDGAR + yfinance)
  Day 3:  Layer 2 — price pain screen (yfinance bulk OHLCV + sector ETF comparison)
  Day 4:  Layer 3 — EDGAR XBRL fundamentals (FCF, balance sheet, P/TBV)
  Day 5:  Layer 3 cont. — ASC 842 flag, net common overhang, dilution calc

Week 2 — Signals and scoring
  Day 6:  Layer 4 — OpenInsider scraper + Form 4 parsing
  Day 7:  Layer 4 — WhaleWisdom + 13D/13G + value fund lookup table
  Day 8:  Layer 5 — FINRA TRACE Playwright bond scraper
  Day 9:  Layer 6 — RSI(14) weekly computation + sector overlay
  Day 10: Confidence score engine — all 5 components + sector modifier

Week 3 — Outputs and transparency
  Day 11: Upside calc + dilution calc + risk flag generator
  Day 12: Action steps generator
  Day 13: TransparencyBuilder — Level 1, 2, 3 reasoning chains
  Day 14: results.json writer + main.py pipeline wiring
  Day 15: Test full pipeline end-to-end, fix bugs

Week 4 — Frontend
  Day 16: index.html shell — nav, router, CSS variables, dark mode
  Day 17: Page 1 — scanner table with score bars, filters, sort
  Day 18: Page 2 — watchlist with localStorage, sparklines, alerts
  Day 19: Page 3 — 3-zone layout, verdict card, score breakdown with transparency
  Day 20: Page 3 — Chart.js charts, Zone 3 collapsed section
  Day 21: Page 4 — swing trader (separate visual style)
  Day 22: Responsive — mobile breakpoints, touch targets
  Day 23: Accessibility — focus states, aria labels, color-blind fixes
  Day 24: Error states, loading states, empty states
  Day 25: End-to-end testing + bug fixes
```

### 20.2 Python Dependencies

```
yfinance==0.2.38
pandas==2.2.0
numpy==1.26.4
requests==2.31.0
beautifulsoup4==4.12.3
playwright==1.42.0
lxml==5.1.0
google-generativeai==0.5.4
python-dotenv==1.0.1
schedule==1.2.1
tqdm==4.66.2
```

### 20.3 Phase Coverage at Each Milestone

| Milestone | What works | RK method coverage |
|-----------|-----------|-------------------|
| End of Week 2 | Full pipeline, scored JSON output | 72% |
| End of Week 3 | + Transparency system | 76% |
| End of Week 4 | + Full UI, all 4 pages | 76% (same data, better presentation) |
| Phase 2 (GitHub Actions + transcripts + buyer bg) | + 6 gap fixes | 87% |
| Phase 3 (Cloudflare + covenant + portfolio context) | + 4 more fixes | 91% |

---

## 22. Extensibility Design Rules

This section defines the architectural rules that ensure future features can be added without redesigning what is already built. These rules must be followed from Day 1 of implementation even though the features they support are not being built yet.

### 22.1 The Five Invariants

These are non-negotiable rules. Violating any of them creates a redesign debt.

**Invariant 1 — Score component weights must always sum to 100**

The confidence score renders component weights as proportional bar fills. If weights sum to 110, bars overflow. If they sum to 90, there is unexplained "missing" score. Adding or removing a component requires proportional rebalancing of all other weights. Document any weight change with a rationale.

Current weights and rationale:
- Insider buying: 30pts — RK's explicitly highest-weighted signal ("sometimes I'll buy just based on that"). The only signal that represents real money and specific knowledge.
- Bond safety: 25pts — The bankruptcy filter. The most binary signal — either the company survives or it doesn't. Second highest because the downside of getting this wrong is total loss.
- FCF yield: 20pts — The core valuation anchor. Necessary but not sufficient — many cheap stocks are cheap for good reason.
- Institutional quality: 15pts — Independent confirmation signal. Valuable but secondary — institutions can be wrong, and many don't file publicly.
- Technical trend: 10pts — Timing and sentiment gauge only. RK explicitly uses charts as a secondary tool, not a primary one.

**Invariant 2 — Per-component scores are capped at their maximum**

Bonuses can push a component score above its stated maximum (e.g. insider buying base 30 + bonus 5 + bonus 2 = 37). Each component must be capped at its max before summing to total. The total score is separately capped at 100.

```python
# In each _score_X() method:
raw_points = base_points + bonus_points - penalty_points
component["points"] = min(raw_points, component["max"])
```

**Invariant 3 — results.json fields are always optional with null defaults**

New fields added to the candidate output JSON must have a documented null/default value. The frontend uses optional chaining for all field access:
```javascript
const bondPrice = candidate?.bond_data?.price ?? null;
```
This means new pipeline features never break the frontend. Old frontends continue working with new pipeline output.

**Invariant 4 — Never DELETE from the candidates table**

Historical scored candidates are the raw material for future backtesting. Use soft deletion only. Add an `is_current` boolean column (default True) — set to False when a stock no longer appears in the scanner rather than deleting the row. All historical scores remain queryable forever.

```sql
ALTER TABLE candidates ADD COLUMN is_current BOOLEAN DEFAULT 1;
-- Never: DELETE FROM candidates WHERE ...
-- Always: UPDATE candidates SET is_current = 0 WHERE ...
```

**Invariant 5 — Layer modules accept a market parameter**

Every layer function signature includes `market: str = "US"`. Internal data source calls are wrapped in market-routing logic. This means adding Canadian or UK stock support in future only requires adding new data source modules — the layer logic itself does not change.

```python
def run(input_tickers: list[dict], config: dict, market: str = "US") -> list[dict]:
    if market == "US":
        return _run_us(input_tickers, config)
    elif market == "CA":
        return _run_ca(input_tickers, config)  # future
    else:
        raise ValueError(f"Unsupported market: {market}")
```

### 22.2 Future-Proof Architecture Decisions

**Score engine as a base class**

The RK confidence scorer must be implemented as a subclass of a `BaseScorer` abstract class. This makes adding alternative frameworks (e.g. Buffett-style, Lynch-style) a new subclass rather than a rewrite of the existing scorer.

```python
# scoring/base_scorer.py
class BaseScorer:
    def score(self, stock: dict) -> dict:
        raise NotImplementedError

    def _get_tier(self, score: float) -> dict:
        raise NotImplementedError

# scoring/rk_scorer.py
class RKScorer(BaseScorer):
    def score(self, stock: dict) -> dict:
        # RK-specific implementation
        ...
```

The pipeline's `main.py` instantiates the scorer by name:
```python
scorer = RKScorer()  # future: scorer = BuffettScorer()
```

**Score engine accepts optional weight overrides**

The `score()` method accepts an optional weights override dict. If not provided, uses config defaults. This enables future "customise your scoring" UI features without any backend changes.

```python
def score(self, stock: dict,
          weights_override: dict = None) -> dict:
    weights = weights_override or config.SCORE_WEIGHTS
    ...
```

**Navigation overflow strategy**

The current design has 4 tabs. A 5th page (e.g. Portfolio tracker, Sector dashboard, Backtester) will be added in future. The nav must support this without visual overflow.

**Selected strategy: "More ▾" overflow menu**

- Tabs 1–4 always visible in the nav bar
- Tab 5+ appears in a "More ▾" dropdown
- On mobile: all tabs accessible via the dropdown
- Implementation: tab visibility controlled by a `nav_tabs` config array — adding a new page only requires adding one entry to the array

```javascript
// app.js — nav tabs config
const NAV_TABS = [
  { id: 'scanner',   label: 'Today\'s picks',  sub: 'RK deep value scanner',   primary: true },
  { id: 'watchlist', label: 'My watchlist',     sub: 'Stocks you\'re tracking', primary: true },
  { id: 'deepdive',  label: 'Analyse a stock',  sub: 'Enter any ticker',        primary: true },
  { id: 'swing',     label: 'Swing trades',     sub: 'Short-term momentum',     primary: true },
  // Future pages go here with primary: false — they appear in "More ▾"
  // { id: 'portfolio', label: 'Portfolio', sub: 'Track your positions', primary: false },
];
```

### 22.3 Missing Definitions (Flagged by Design Review)

These were undefined in the design plan and must be resolved before implementation begins.

**Missing Definition 1 — total_explanation text template**

The `_build_total_explanation()` function was stubbed. Full template defined here:

```python
def _build_total_explanation(self, total, components, modifier) -> str:
    # Find the strongest and weakest components
    sorted_comps = sorted(components.items(),
                          key=lambda x: x[1]['points'] / x[1]['max'],
                          reverse=True)
    strongest = sorted_comps[0]
    weakest = sorted_comps[-1]

    # Build sentence by sentence
    parts = []

    # Sentence 1: overall verdict
    tier = self._get_tier(total)
    parts.append(
        f"This stock scored {round(total)}/100 — {tier['plain_label'].lower()}."
    )

    # Sentence 2: strongest signal
    parts.append(
        f"The strongest signal: {components[strongest[0]]['reasoning_short']}."
    )

    # Sentence 3: weakest signal (if materially weak)
    weak_pct = weakest[1]['points'] / weakest[1]['max']
    if weak_pct < 0.5:
        parts.append(
            f"Main gap: {components[weakest[0]]['reasoning_short']}."
        )

    # Sentence 4: sector context if significant
    if abs(modifier) >= 3:
        direction = "adds confidence" if modifier > 0 else "reduces confidence"
        parts.append(
            f"Sector context {direction} ({'+' if modifier > 0 else ''}{modifier} pts)."
        )

    return " ".join(parts)
```

Each component's score dict must include a `reasoning_short` field — a 5–8 word plain-English phrase:
- insider: "CEO bought $640k at 3yr low"
- bonds: "Bonds at 84 — caution zone"
- fcf: "FCF yield 14%, P/TBV 0.72"
- institutional: "Greenlight Capital holds 6.2%"
- technical: "RSI 34, improving 4 weeks"

**Missing Definition 2 — action step priority ordering**

When multiple signals are weak, action steps are selected and ordered by this priority:

| Priority | Condition | Action step shown |
|----------|-----------|------------------|
| 1 (highest) | Bond price in caution zone (70–85) | Read debt footnote in 10-Q |
| 2 | Insider buy exists but buyer unverified | Search buyer name and background |
| 3 | Technical RSI not confirmed | Wait for RSI to cross above X before sizing up |
| 4 | No value fund holder detected | Check WhaleWisdom for recent 13F activity |
| 5 | FCF negative last quarter | Review 10yr FCF history for cycle context |
| 6 | ASC 842 flag triggered | Subtract lease liabilities for true leverage picture |
| 7 | Bonds unavailable | Check manually at FINRA |
| 8 (lowest) | Score crossed from Watch to Speculative | Consider small initial position |

Maximum 3 steps shown in Zone 1. Steps 4+ shown in Zone 3 (full evidence section).

**Missing Definition 3 — value_funds.json governance**

Criteria for a fund to be added to the value funds lookup table:
1. Fund explicitly self-identifies as value-oriented or activist in public filings or website
2. Fund has filed at least one 13D or 13G (demonstrating concentrated position-taking)
3. Fund has at least a 3-year operating history
4. Fund manages at least $50M AUM (smaller funds may not have sufficient analytical resources)

Review process: quarterly. Source for new additions: Dataroma tracked managers list + 13D Monitor activist list.

Funds are never automatically removed — only marked `active: false` if the fund closes or stops filing. This preserves historical data integrity.

**Missing Definition 4 — component score cap implementation**

Each scoring method must explicitly cap its output:
```python
MAX_POINTS = {"insider": 30, "bonds": 25, "fcf": 20,
              "institutional": 15, "technical": 10}

def _score_insider(self, stock):
    points = 0
    # ... compute points with bonuses and penalties ...
    return {
        "points": min(points, MAX_POINTS["insider"]),  # cap here
        "max": MAX_POINTS["insider"],
        "reasoning_short": "...",
        "detail": "...",
    }
```

**Missing Definition 5 — nullable user_id for future multi-user support**

Add to SQLite schema from Day 1 (even though always NULL in Phase 1):
```sql
ALTER TABLE watchlist ADD COLUMN user_id TEXT DEFAULT NULL;
ALTER TABLE alerts    ADD COLUMN user_id TEXT DEFAULT NULL;
-- Index for future queries by user
CREATE INDEX idx_watchlist_user ON watchlist(user_id);
CREATE INDEX idx_alerts_user    ON alerts(user_id);
```

**Missing Definition 6 — score weight change log**

Any future change to score component weights must be recorded in a `weight_history.json` file in the data/ folder:
```json
[
  {
    "date": "2026-04-01",
    "version": "1.0",
    "weights": {"insider": 30, "bonds": 25, "fcf": 20,
                "institutional": 15, "technical": 10},
    "rationale": "Initial weights based on RK video analysis"
  }
]
```
This ensures that when backtesting is added, historical scores can be recomputed with the weights that were in effect at that time.

---

## Summary: The Most Important Changes from v1.0

1. **Scoring transparency is now a first-class feature.** Every score is explainable at 3 levels of depth. The user can always answer "why did this score 74?" by reading the plain-English paragraph, clicking a meter bar, or following source links to raw data.

2. **Action steps moved to Zone 1.** The most actionable information is now the first thing the user reads after the score — not the last. The page follows the user's natural decision flow: What is it? → What do I do? → Why?

3. **Progressive disclosure reduces cognitive load.** Page 3 went from 12 always-visible sections to 3 zones. Zone 1 gives the decision. Zone 2 gives the reasoning. Zone 3 is available for those who want it but never forces itself on anyone.

4. **Plain-English labels replace jargon everywhere.** "Strong buy signal" instead of "High Conviction". "Today's picks" instead of "RK Scanner". "Analyse a stock" instead of "Deep Dive". The user understands the app without reading documentation.

5. **Mobile is designed, not an afterthought.** Explicit column priority rules, card-stack layout on mobile, touch-sized targets, and responsive chart heights are all specified before a line of code is written.

---

*Next document: Implementation Guide — Phase 1 code, starting with pipeline/main.py*
