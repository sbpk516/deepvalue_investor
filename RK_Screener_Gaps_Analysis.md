# RK Stock Screener — Gaps Analysis and Resolution Plan

**Version:** 1.0  
**Date:** April 2026  
**Status:** Gaps identified post requirements review  
**Related document:** RK_Stock_Screener_Requirements_Spec.md  

---

## Purpose

This document captures everything NOT fully covered in the requirements spec, explains why it was initially classified as a gap, and — where possible — proposes an automated solution using free data sources. Each gap is classified by severity and assigned to a future phase.

---

## Gap Severity Definitions

| Severity | Meaning |
|----------|---------|
| Critical | Missing this causes wrong signals or misleads the user |
| Important | Reduces accuracy or usefulness significantly |
| Enhancement | Nice to have; improves fidelity to RK's method |
| By Design | Cannot be automated; correctly deferred to human judgment |

---

## Gap 1 — Buyer Background Research

### What RK Actually Does
When an insider buys shares, RK does not just note the dollar amount and role. He researches who that specific person is: their prior companies, whether they have domain expertise in the industry, their track record, and how their personal purchase compares to their compensation. A $2M buy by a founder who took a prior energy company from $2 to $40 means something completely different from a $2M buy by a newly appointed CFO with a finance background.

### Why It Was Classified as Manual
Initially assumed this required human judgment and web browsing.

### Why It Is Actually Automatable

**Primary free source: SEC EDGAR DEF 14A (Annual Proxy Statement)**

Every US public company files a DEF 14A (proxy statement) annually with the SEC. This is a required disclosure that contains:
- Full biography of every named executive officer and director
- Prior employers and positions held (going back 5+ years)
- Tenure at current company
- Equity ownership as a percentage of shares outstanding
- Total compensation (salary + bonus + equity) for each named officer
- Any other board memberships

This is structured, machine-readable, and freely available on EDGAR. For most large companies it is also available in XBRL format.

**Secondary sources:**
- Company investor relations page (About / Leadership section) — HTML scrape
- Wikipedia for well-known executives — free API available (`en.wikipedia.org/api/rest_v1/`)
- Crunchbase for startup/tech founders — free tier allows limited queries
- OpenSecrets.org for political connections (niche but relevant for energy/materials)

**What to extract and score:**

| Data Point | Source | How to Use |
|-----------|--------|-----------|
| Prior companies and roles | DEF 14A biography section | Flag if prior company was in same industry → domain expertise bonus |
| Tenure at current company | DEF 14A | Short tenure (< 2yr) + large buy = stronger signal (new mgmt buying in) |
| Compensation vs purchase size | DEF 14A (compensation table) | Purchase > 50% of annual comp = very strong signal |
| Equity ownership % | DEF 14A ownership table | Already tracked in confidence score; cross-verify here |
| Prior company outcomes | Wikipedia / Crunchbase | Did prior company stock do well under this person? Manual flag |

**Automation approach:**

```
1. Get CIK for company from EDGAR
2. Fetch most recent DEF 14A filing URL:
   efts.sec.gov/efts/hit?q="{ticker}"&forms=DEF+14A&dateRange=custom&startdt=2023-01-01
3. Download and parse the filing text
4. Extract biography section for the specific insider who bought shares
   (match by name from Form 4 filing)
5. Use Gemini free tier to parse biography text and extract:
   - prior_companies: list
   - industry_match: true/false (same sector as current company)
   - tenure_years: number
   - compensation_total: number
6. Compute: purchase_to_comp_ratio = insider_buy_$ / compensation_total
7. Display structured buyer profile on Page 3 alongside insider buy transaction
```

**Buyer quality score addition to confidence scoring (suggested +5 bonus points):**

| Condition | Bonus |
|-----------|-------|
| Buyer previously led a company in the same industry | +3 pts |
| Purchase amount > 100% of annual compensation | +3 pts |
| Buyer is a founder (not hired executive) | +2 pts |
| Buyer is new to company (< 2yr) — signals conviction buy-in | +1 pt |
| Buyer has no relevant industry background | 0 pts |

**Severity:** Important  
**Phase:** Phase 2  
**Effort:** Medium (3–4 days — EDGAR DEF 14A parsing + Gemini integration)  
**Cost:** Free (EDGAR + Gemini free tier)

---

## Gap 2 — Earnings Call Transcript Analysis

### What RK Actually Does
RK reads earnings call transcripts specifically to evaluate:
- How management talks about the business — candid vs. defensive tone
- Capital allocation language — are they prioritising shareholder value (buybacks, debt paydown) or making acquisitions at bad prices?
- Whether their guidance is credible based on what they said last quarter
- Specific quotes that reveal management's confidence in the recovery thesis

He says: "If I'm really dialing into a company, I'll read every single quote from the conference call."

### Why It Was Classified as Manual
Initially assumed transcripts required paid sources (Seeking Alpha paywall, Bloomberg).

### Why It Is Actually Automatable

**Free transcript sources:**

| Source | Coverage | Format | Scrapeable? |
|--------|---------|--------|------------|
| The Motley Fool (fool.com) | Most S&P 500 + many mid-caps | HTML | Yes — clean HTML tables |
| Seeking Alpha | Very broad | HTML | Yes for recent ones (delayed paywall) |
| Company IR websites | All companies | PDF or HTML | Yes — find via Google: "[company] earnings transcript Q[n] [year]" |
| SEC EDGAR 8-K filings | All companies | Text (some) | Yes — some companies file full transcripts as 8-K exhibits |

**Best free approach: Motley Fool scrape**

Motley Fool publishes free earnings transcripts within 24–48 hours of the call. URL pattern:
`fool.com/earnings/call-transcripts/[year]/[quarter]/[company-slug]/`

Or search: `site:fool.com "[company name]" "earnings call transcript"`

**Gemini analysis prompt for transcript:**

```
You are analyzing an earnings call transcript for a value investor.
Extract the following in JSON format:
{
  "capital_allocation_signals": {
    "buybacks_mentioned": true/false,
    "buybacks_tone": "committed/exploring/no mention",
    "debt_paydown_mentioned": true/false,
    "acquisition_mentioned": true/false,
    "acquisition_tone": "opportunistic/aggressive/defensive"
  },
  "management_tone": "confident/cautious/defensive/mixed",
  "guidance_change": "raised/maintained/lowered/withdrawn",
  "key_positive_quotes": ["max 2 direct quotes under 20 words"],
  "key_risk_quotes": ["max 2 direct quotes under 20 words"],
  "recovery_thesis_supported": true/false,
  "summary": "2 sentence plain language summary"
}
Return only valid JSON.
```

**What to display on Page 3:**

A "Management Signals" panel showing:
- Management tone badge (Confident / Cautious / Defensive)
- Capital allocation: buybacks mentioned? debt paydown mentioned?
- Guidance direction: Raised / Maintained / Lowered
- 1–2 key quotes (under 20 words each — copyright safe)
- Recovery thesis: Supported / Neutral / Contradicted
- Link to full transcript

**Cost consideration:** Each transcript parse = 1 Gemini API call. At 10–15 final candidates per week = 10–15 calls per week. Well within Gemini free tier (1,500 calls/day).

**Severity:** Important  
**Phase:** Phase 2  
**Effort:** Medium (3–4 days — scraper + Gemini integration + display)  
**Cost:** Free (Motley Fool scrape + Gemini free tier)

---

## Gap 3 — Business Model Assessment (Secular vs Cyclical Decline)

### What RK Actually Does
Before buying a beaten-down stock, RK asks: is this decline permanent (secular — the industry is dying) or temporary (cyclical — the industry is at a trough and will recover)? He would not buy Blockbuster Video in 2010 even if it was trading at 0.1x book. But he would buy a natural gas company at a multi-year low because commodity cycles always turn.

### Why It Was Initially Listed as Manual
"Business model survival judgment" sounds qualitative. But the core question — secular vs. cyclical — is actually measurable.

### Why It Is Actually Partially Automatable

**Signals that indicate CYCLICAL decline (positive — buy the dip):**

| Signal | How to Detect | Source |
|--------|--------------|--------|
| Industry has recovered from prior troughs | Sector ETF price history shows prior cycles | yfinance |
| Revenue decline is < 3yr old | Company revenue was growing before the decline | EDGAR XBRL |
| Gross margin stable despite revenue decline | Gross margin not structurally compressing | EDGAR XBRL |
| Commodity-linked business | SIC code in energy, materials, chemicals | SEC EDGAR SIC codes |
| Peers also declining (not company-specific) | Already in sector score modifier | yfinance |
| CapEx being cut across industry | Industry-level CapEx trend | Sector ETF filings (hard) |

**Signals that indicate SECULAR decline (negative — be cautious):**

| Signal | How to Detect | Source |
|--------|--------------|--------|
| Revenue declining for 5+ consecutive years | EDGAR 10yr revenue trend | EDGAR XBRL |
| Gross margin compressing every year | Gross margin declining 3+ years | EDGAR XBRL |
| Share count increasing (dilution to survive) | Shares outstanding rising | EDGAR XBRL |
| Industry category is "disrupted" sectors | SIC code mapping to known secular-decline industries | Manual lookup table |
| Physical retail / print media / legacy telecom | GICS sub-industry classification | yfinance sector data |

**Known secular-decline industry flags (manual lookup table to maintain):**

- Print newspapers and magazines (SIC 2710–2796)
- Video rental (SIC 7841) — historical
- Coal mining (SIC 1220–1221) — structural headwinds
- Department stores (SIC 5311) — structural
- Landline telephone services (SIC 4813)

**Cyclical/recovery-friendly industries (positive flag):**

- Oil and gas exploration (SIC 1311)
- Natural gas distribution (SIC 4924)
- Metal mining (SIC 1000–1499)
- Forest products / lumber (SIC 2400–2499)
- Commodity chemicals (SIC 2800–2869)
- Homebuilders (SIC 1520–1522) — cyclical with housing
- Steel manufacturing (SIC 3310–3399)

**What to display on Page 3:**

A "Decline Type Assessment" indicator:
- Likely Cyclical (green) — revenue decline recent, margins stable, commodity-linked
- Mixed / Unclear (amber) — some cyclical signals, some secular concerns
- Likely Secular (red) — multi-year revenue decline, compressing margins, disrupted industry

**Important caveat:** Display this as an indicator with explanation, not a definitive judgment. GME would have shown "Likely Secular" in 2020 but RK still bought it because of the console cycle catalyst. The indicator informs but does not override the user's judgment.

**Severity:** Important  
**Phase:** Phase 2  
**Effort:** Easy–Medium (2–3 days — EDGAR revenue trend analysis + SIC code lookup table)  
**Cost:** Free

---

## Gap 4 — Debt Ownership Identification

### What RK Actually Does
In Part 2, RK explicitly says "who owns the debt" is a separate and important check, especially when a company might be near bankruptcy. A loan-to-own hedge fund holding 40% of a distressed company's bonds means the equity is likely to be wiped out in restructuring — the fund wants the company, not the coupon. A diversified passive bondholder has no such interest.

### Why It Is Hard to Automate

Unlike equity holders (13F filings), debt holders are NOT required to disclose holdings to the SEC unless they hold more than 5% of a specific debt issuance AND it meets other criteria. There is no equivalent of a 13F for bonds.

**Partial automation approaches:**

| Method | What You Get | Limitation |
|--------|-------------|-----------|
| EDGAR Schedule 13D/13G for debt securities | 5%+ holders of specific debt issuances | Only required for registered debt; misses loans and private placements |
| Company 10-K "Principal Stockholders" section | Sometimes names major debt holders | Not consistently disclosed |
| Bloomberg DDIS (Debt Distribution) | Complete debt holder breakdown | Paid — not free |
| Bankrupty filings (Chapter 11 schedules) | Full creditor list | Only available after bankruptcy filed |
| Loan syndication databases (Refinitiv LPC) | Bank loan holder identity | Paid |

**Free partial solution:**

For the ~10–15 final deep-dive candidates only:
1. Search EDGAR full-text for the company name + "loan agreement" or "credit agreement" → find lender names disclosed in 8-K filings
2. Search for any 13D/13G filings specifically for the company's debt securities (rare but possible)
3. Check if any known distressed debt / loan-to-own funds appear in 13F filings as equity holders too (sometimes a sign of a larger position)

**Display on Page 3:** 
- "Debt holder data: Limited — [EDGAR link to latest debt filings]"
- If a known distressed debt fund appears anywhere in filings: "Warning: [Fund name] detected in filings — possible loan-to-own strategy"

**Known distressed debt / loan-to-own funds to flag** (manual lookup table):
- Aurelius Capital Management
- Oaktree Capital (distressed desk)
- Apollo Global Management (credit)
- Cerberus Capital
- Fortress Investment Group

**Severity:** Important (for near-bankruptcy situations only)  
**Phase:** Phase 3  
**Effort:** Hard (3–5 days — EDGAR debt filing parsing + fund lookup table)  
**Cost:** Free for partial solution; full solution requires Bloomberg

---

## Gap 5 — Cross-Asset Commodity Correlation

### What RK Actually Does
RK tracks commodity prices alongside his equity positions as leading or confirming indicators. He tracked lumber prices to anticipate RFP's moves. He tracked natural gas spot prices against his gas equity positions (RRC, AR, SD). He watched oil prices against his energy holdings. These commodity charts gave him context that pure equity analysis could not.

### Why It Is Easily Automatable

yfinance has commodity futures and ETF data for all major commodities. This was simply not included in the spec — it is an easy addition.

**Commodity tickers available free via yfinance:**

| Commodity | Ticker | Relevant for |
|-----------|--------|-------------|
| Natural gas (futures) | NG=F | Gas E&P stocks (RRC, AR, SWN, SD) |
| Crude oil (futures) | CL=F | Oil E&P and services |
| WTI oil ETF | USO | Oil sector broadly |
| Natural gas ETF | UNG | Gas sector broadly |
| Lumber futures | LBS=F | Forest products (RFP, WFG) |
| Copper futures | HG=F | Mining, industrials, economic indicator |
| Gold futures | GC=F | Precious metals miners (NGD, AEM, KL) |
| Silver futures | SI=F | Silver miners |
| Coal ETF | ARCH, CEIX | Coal companies |
| Steel ETF | SLX | Steel producers |

**Automation approach:**

1. Map each stock's GICS sub-industry to its relevant commodity ticker(s) — maintain a lookup table
2. Fetch 3yr weekly price history for both the stock and its commodity proxy
3. Compute rolling 52-week correlation coefficient between stock price and commodity price
4. Display on Page 3: "Commodity correlation: Natural gas (UNG) — 3yr correlation: 0.82"
5. Show mini chart: stock price vs. commodity price overlaid, last 3 years
6. Flag: "Commodity in multi-year downtrend — supports RK-style recovery thesis"
7. Flag: "Commodity price recently up 15%+ — potential leading indicator for equity recovery"

**What to add to confidence score:**

Add a commodity context bonus (up to +3 points) to the sector context modifier:
- Relevant commodity also at multi-year low: +3 pts (supports recovery thesis)
- Relevant commodity turning up from lows: +2 pts (early signal)
- Relevant commodity neutral: 0 pts
- Relevant commodity at all-time high (stocks may be lagging by design): +1 pt (demand strong)

**Severity:** Enhancement  
**Phase:** Phase 2  
**Effort:** Easy (1–2 days)  
**Cost:** Free (yfinance)

---

## Gap 6 — Historical Cycle Comparison

### What RK Actually Does
When assessing a beaten-down sector in 2020, RK explicitly compared it to the 2015–2016 cycle. He asked: how deep was the drawdown then? How long did the recovery take? What were the best performers? This gave him a template for sizing expectations in the current cycle.

### Automation Approach

**Data needed:** Historical sector ETF and individual stock price data going back 10+ years. Available free via yfinance.

**What to compute and display:**

For each sector in the scanner results:

| Metric | Current Cycle | Prior Cycle (2015–2016) |
|--------|--------------|------------------------|
| Sector ETF drawdown from peak | e.g., −58% | −62% |
| Duration of decline so far | e.g., 3.2 years | 2.8 years |
| Recovery from trough (prior cycle) | N/A | +185% over 4 years |
| Best performing stocks in prior cycle | N/A | List top 5 |

**Key reference cycles to pre-compute and store:**

| Sector | Reference Period | Notes |
|--------|----------------|-------|
| Energy / Oil & Gas | 2015–2016 trough | Oil went to $27; huge recovery after |
| Natural Gas E&P | 2015–2020 trough | Multi-year depression; RK's primary reference |
| Gold / Precious Metals | 2015–2016 trough | Gold bottomed at $1050 |
| Homebuilders | 2008–2011 trough | Housing crisis cycle |
| Retail / Consumer | 2017–2020 trough | E-commerce disruption cycle |
| Materials / Commodities | 2015–2016 trough | China slowdown cycle |

**Display on Page 1 and Page 3:**

A "Cycle Context" panel showing:
- "This sector is in year 3 of a downcycle. The comparable 2015–2016 cycle bottomed at −62% and recovered +185% over 4 years. Current drawdown: −58%."
- Visual: timeline bar showing current position in cycle vs. prior cycle length

**Severity:** Enhancement  
**Phase:** Phase 2  
**Effort:** Medium (2–3 days)  
**Cost:** Free (yfinance historical data)

---

## Gap 7 — Chart Specification for Page 3

### What Is Missing
The requirements spec mentions charts on Page 3 (10yr FCF history, weekly price + RSI, sector peer overlay) but does not specify the chart library, dimensions, interactivity, or exact data displayed.

### Full Chart Specification

**Chart 1: 10-Year FCF History (Bar Chart)**
- Library: Chart.js (free, CDN)
- Data: Annual Simple FCF per share for last 10 years (from EDGAR XBRL)
- X-axis: Year (2014–2024)
- Y-axis: FCF per share ($)
- Color: Green bars for positive FCF, red bars for negative FCF
- Overlay line: Current stock price (right Y-axis) for context
- Annotations: Mark the 3yr average as a horizontal dashed line
- Tooltip: Shows exact FCF value and year on hover

**Chart 2: Weekly Price + RSI (Dual Panel)**
- Library: Chart.js with dual Y-axis
- Data: Weekly OHLCV + computed RSI(14) for last 3 years (from yfinance)
- Top panel: Candlestick or line chart of weekly closing price
- Bottom panel: RSI(14) line with oversold zone (below 30) highlighted in light red
- Horizontal lines: RSI 30 (oversold) and RSI 70 (overbought)
- Width: Full page width

**Chart 3: Sector Peer Comparison (Line Chart)**
- Library: Chart.js
- Data: 3yr weekly price history for the stock + 3–5 sector peers + sector ETF
- Normalised to 100 at start date (shows relative performance)
- Each line a different color; stock highlighted with thicker line
- Peers auto-selected: top 5 stocks in same GICS sub-industry by market cap

**Severity:** Important (charts are central to Page 3 usefulness)  
**Phase:** Phase 1 (basic version) / Phase 2 (full interactive)  
**Effort:** Medium (3–4 days)  
**Cost:** Free (Chart.js via CDN)

---

## Gap 8 — Dilution Calculator Formula

### What Is Missing
The requirements spec describes the concept: "if a company is too levered, estimate how many shares would need to be issued to right-size the balance sheet, then adjust FCF per share accordingly." The exact formula is not specced.

### Full Formula

```
# Step 1: Determine if dilution is likely needed
overhang_to_fcf_ratio = net_common_overhang / avg_3yr_fcf

# If ratio > 8x, the company may need to issue equity to survive
# RK's threshold: above 8x = potential dilution risk

# Step 2: Estimate shares needed to bring ratio to 4x (target)
target_overhang = avg_3yr_fcf * 4
excess_overhang = net_common_overhang - target_overhang
issue_price = current_price * 0.80  # assume 20% discount on new issuance
shares_to_issue = excess_overhang / issue_price

# Step 3: Compute diluted share count
diluted_shares = current_shares + shares_to_issue
dilution_pct = (shares_to_issue / current_shares) * 100

# Step 4: Recompute FCF per share on diluted basis
diluted_fcf_per_share = avg_3yr_fcf / diluted_shares
diluted_fcf_yield = diluted_fcf_per_share / current_price

# Step 5: Recompute upside multiple on diluted basis
diluted_conservative_target = diluted_fcf_per_share * 12
diluted_upside = diluted_conservative_target / current_price
```

**Display on Page 3:**
- If dilution_pct < 10%: no flag needed
- If dilution_pct 10–30%: "Moderate dilution risk — FCF per share may be overstated by ~[X]%"
- If dilution_pct > 30%: "High dilution risk — show diluted upside ([X]×) alongside headline upside"

**Severity:** Important  
**Phase:** Phase 1  
**Effort:** Easy (half a day — formula already described, just needs coding)  
**Cost:** Free

---

## Gap 9 — Ratings Agency Research Links

### What Is Missing
The spec mentions ratings agency research as a manual step but does not automate surfacing the link.

### Automation Approach

**Free public rating sources:**

| Source | What Is Free | URL Pattern |
|--------|-------------|------------|
| Moody's | Press releases on rating actions (not full reports) | moodys.com/research (search by company) |
| S&P Global | Rating history and recent actions (limited) | spglobal.com/ratings |
| Fitch | Some public research | fitchratings.com |
| EDGAR 8-K | Companies must disclose rating changes in 8-K filings | EDGAR full-text search |

**Best free approach: EDGAR 8-K rating disclosure**

When a ratings agency changes a company's rating, the company is often required to file an 8-K. Search:
```
efts.sec.gov/efts/hit?q="{company_name}"+("Moody's"+"rating"+"OR"+"S%26P"+"rating")&forms=8-K
```

This surfaces any 8-K filings where the company disclosed a rating action — free, reliable, and on EDGAR.

**Also:** Google Custom Search (free tier: 100 queries/day):
```
query = f"Moody's OR S&P rating {company_name} 2024 OR 2025"
```
Display the top result as a "Ratings Research" link on Page 3.

**Severity:** Enhancement  
**Phase:** Phase 2  
**Effort:** Easy (1 day)  
**Cost:** Free

---

## Gap 10 — User Notes Field on Watchlist

### What Is Missing
RK tracks insights from Seeking Alpha commenters and articles over time. The app has no place for users to capture qualitative notes per stock.

### Proposed Feature

Add a free-text notes field to each watchlisted stock on Page 2:

- "Notes" expandable section per stock row
- User can type or paste any text: SA commenter insight, management quote, thesis note, concern
- Notes saved to SQLite (Phase 1/2) or Cloudflare KV (Phase 3)
- Notes displayed on Page 3 when the same stock is viewed in deep dive
- Optional: timestamp each note entry (date added)

**This is the lightest-weight way to capture the qualitative layer that cannot be automated.** It turns the watchlist into a research journal per stock.

**Severity:** Enhancement  
**Phase:** Phase 1  
**Effort:** Easy (half a day — simple textarea + localStorage/SQLite save)  
**Cost:** Free

---

## Gap 11 — Portfolio Context for Position Sizing

### What Is Missing
RK sizes positions in the context of his full portfolio. A 3% position in a gas stock means something different if he already has 15% in gas vs. if gas is his only sector bet. The app recommends position sizes per stock without knowing what else the user owns.

### Proposed Feature

A lightweight portfolio exposure tracker:

- User can optionally input current holdings by sector (not individual stocks — just sector weights)
- Example: "I currently have 12% in Energy, 5% in Materials"
- When a new candidate appears in a sector, the app shows: "Adding this would bring your Energy exposure to ~15% — above the 10% single-sector guideline"
- Not a full portfolio manager — just a sector concentration warning
- Stored in localStorage (Phase 1/2)

**Alternatively (simpler):** On Page 3, display a static warning when multiple candidates in the same sector appear in the scanner: "3 energy stocks currently in scanner — adding all would create sector concentration."

**Severity:** Enhancement  
**Phase:** Phase 3  
**Effort:** Medium (2–3 days for basic version)  
**Cost:** Free

---

## Summary Table

| # | Gap | Severity | Automatable? | Phase | Effort | Cost |
|---|-----|---------|-------------|-------|--------|------|
| 1 | Buyer background research | Important | Yes — DEF 14A + Gemini | Phase 2 | Medium | Free |
| 2 | Earnings transcript analysis | Important | Yes — Motley Fool + Gemini | Phase 2 | Medium | Free |
| 3 | Business model: secular vs cyclical | Important | Partially — revenue trend + SIC codes | Phase 2 | Easy–Medium | Free |
| 4 | Debt ownership identification | Important | Partially — EDGAR 8-K only | Phase 3 | Hard | Free (partial) |
| 5 | Cross-asset commodity correlation | Enhancement | Yes — yfinance commodity ETFs | Phase 2 | Easy | Free |
| 6 | Historical cycle comparison | Enhancement | Yes — yfinance 10yr history | Phase 2 | Medium | Free |
| 7 | Chart specification for Page 3 | Important | Yes — Chart.js | Phase 1/2 | Medium | Free |
| 8 | Dilution calculator formula | Important | Yes — formula now fully defined | Phase 1 | Easy | Free |
| 9 | Ratings agency research links | Enhancement | Partially — EDGAR 8-K + Google | Phase 2 | Easy | Free |
| 10 | User notes field on watchlist | Enhancement | N/A — user input feature | Phase 1 | Easy | Free |
| 11 | Portfolio sector concentration | Enhancement | Partially — sector warning only | Phase 3 | Medium | Free |

---

## Revised Coverage Estimate After Addressing Gaps

| Phase | Gaps Addressed | Estimated Coverage |
|-------|--------------|-------------------|
| Current spec (as written) | None | 72% |
| After Phase 1 additions (gaps 7, 8, 10) | Charts, dilution calc, notes | 76% |
| After Phase 2 additions (gaps 1, 2, 3, 5, 6, 9) | Buyer bg, transcripts, commodity, cycle | 87% |
| After Phase 3 additions (gaps 4, 11) | Debt ownership, portfolio context | 91% |

**The remaining ~9% is genuinely non-automatable:**
- Gestalt judgment: synthesising all factors into a final conviction call
- Real-time news and catalyst awareness (company announcements mid-cycle)
- Seeking Alpha commenter relationship tracking (specific people RK follows)
- Qualitative assessment of management credibility beyond transcript keywords
- RK's "feels" — the experienced investor's pattern recognition built over years

These are correctly deferred to human judgment. The app's job is to surface all the data and signals; the investor's job is to make the final call.

---

## Action Items for Requirements Spec Update

The following items from this gaps document should be incorporated into the next version of the requirements spec (v1.1):

1. Add DEF 14A parsing to Layer 4 (Conviction Signals) data pipeline
2. Add buyer quality score to confidence score component 1 (Insider Buying) — up to +5 bonus pts
3. Add earnings transcript fetch (Motley Fool) and Gemini analysis to Page 3 spec
4. Add secular vs. cyclical decline indicator to Page 3 spec
5. Add commodity correlation panel to Page 3 spec
6. Add historical cycle comparison panel to Page 1 and Page 3 spec
7. Add full chart specifications (Chart.js) to Page 3 spec
8. Add complete dilution calculator formula to Section 6 (Confidence Scoring)
9. Add ratings agency EDGAR 8-K search to Page 3 actionable next steps
10. Add user notes textarea to Page 2 (Watchlist) spec
11. Update phase roadmap to reflect gaps being addressed in Phase 2

---

*This document is a living reference. As gaps are addressed in the codebase, mark them as resolved with the date and commit reference.*
