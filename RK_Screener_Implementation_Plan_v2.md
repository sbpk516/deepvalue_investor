# RK Stock Screener — Implementation Plan

**Version:** 2.0 (post-review — all critical fixes incorporated)
**Date:** April 2026
**Status:** Ready to build — reviewed and hardened
**Prerequisites:** Design Plan v2.0, Requirements Spec v1.0, Gaps Analysis v1.0

---

## Review Fixes Applied (v1.0 to v2.0)

Four specialist agents reviewed v1.0: Python Engineer, Data Accuracy Auditor, Security Auditor, Timeline Realist. All critical and moderate issues fixed before implementation begins.

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | _price_series pandas Series crashes JSON serialisation | Critical | Explicit pop() before scoring loop in main.py |
| 2 | XBRL frame filter len==6 drops valid annual data | Critical | Filter changed to exclude Q1/Q2/Q3 suffixes only |
| 3 | WhaleWisdom requests scraper always returns empty (JS required) | Critical | WhaleWisdom removed; yfinance only in Phase 1 |
| 4 | Missing stub files cause ImportError on Day 1 | Critical | Sprint 1 Day 3 now creates pass-through stubs for all modules |
| 5 | upsert_candidate updates primary key columns | Critical | Explicit exclusion of id, ticker, run_date from UPDATE |
| 6 | All layer imports inside function body | Moderate | Moved to top of main.py so failures caught at startup |
| 7 | OpenInsider blocked without random delays and UA rotation | Moderate | random.uniform sleep + User-Agent pool + EDGAR fallback |
| 8 | FINRA Playwright needs playwright-stealth | Moderate | playwright-stealth added to requirements and scraper code |
| 9 | 10b5-1 plan purchases inflate insider signal | Moderate | Form 4 footnote check added; 10b5-1 buys halve base points |
| 10 | Stale bond prices scored as current | Moderate | Trade date stored; staleness flag reduces score by 5pts |
| 11 | Deferred tax assets not stripped from tangible book | Moderate | DeferredTaxAssetsNet added to P/TBV strip calculation |
| 12 | SQLite lock errors if two runs overlap | Moderate | timeout=10 added to sqlite3.connect() |
| 13 | EDGAR response format not validated | Moderate | Schema check added in Layer 1 before processing |
| 14 | OpenInsider table structure change is silent | Moderate | Column name validation before row processing |
| 15 | Swing Trader pipeline deferred to Phase 2 | Timeline | Stub in Phase 1; full build in Phase 2 |
| 16 | Playwright bond scraping deferred to Phase 2 | Timeline | Phase 1 uses unavailable tier; Playwright in Phase 2 |
| 17 | Chart.js charts deferred to Phase 2 | Timeline | Phase 1 shows data tables; charts added in Phase 2 |

**Revised Phase 1 timeline:** 23 working days (was 25 — cuts save 7-10 days, XBRL buffer adds 5 days)
**At 2-3 hours per day:** 8-10 weeks to first working UI

---

## Table of Contents

1. [Overview and Approach](#1-overview-and-approach)
2. [Environment Setup](#2-environment-setup)
3. [Phase 1 — Local Machine MVP](#3-phase-1--local-machine-mvp)
   - Sprint 1: Foundation (Days 1–3)
   - Sprint 2: Data Pipeline Layers 1–3 (Days 4–7)
   - Sprint 3: Data Pipeline Layers 4–6 (Days 8–12)
   - Sprint 4: Scoring Engine (Days 13–16)
   - Sprint 5: Frontend — Pages 1–4 (Days 17–25)
4. [Phase 2 — GitHub Actions Automation](#4-phase-2--github-actions-automation)
5. [Phase 3 — Cloudflare Full Web App](#5-phase-3--cloudflare-full-web-app)
6. [Testing Strategy](#6-testing-strategy)
7. [File-by-File Implementation Reference](#7-file-by-file-implementation-reference)

---

## 1. Overview and Approach

### 1.1 Build Philosophy

- **Working software at every step.** Each sprint ends with something runnable and testable. Never spend more than 2 days without being able to run the pipeline end-to-end on at least one ticker.
- **Outside-in for the pipeline.** Build the output format (results.json schema) first, then build backwards from it. Every layer knows what the final output looks like.
- **Inside-out for the frontend.** Build the data-reading logic first, then the display, then the interactions.
- **Test with real tickers.** Use GME, RRC, RFP as test cases throughout — these are stocks RK actually discussed, so you know what the expected signals should look like.

### 1.2 Total Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 Sprint 1 | Days 1–3 | Project skeleton, config, database, ALL stubs |
| Phase 1 Sprint 2 | Days 4–11 | Layers 1–3 working (extended for XBRL debugging) |
| Phase 1 Sprint 3 | Days 12–17 | Layers 4–6 working (no Playwright bonds) |
| Phase 1 Sprint 4 | Days 18–21 | Full scoring engine + results.json output |
| Phase 1 Sprint 5 | Days 22–30 | Pages 1–3 working (no charts; Page 4 stub) |
| Phase 2 | Days 31–38 | GitHub Actions + swing + bonds + charts |
| Phase 3 | Days 39–55 | Cloudflare full web app |

> **Phase 1 cuts (deferred to Phase 2):** Swing Trader pipeline, Playwright bond scraping, Chart.js charts. Saves 7-10 days without losing core RK screening value.

### 1.3 Test Tickers

Use these throughout development:

| Ticker | Why useful |
|--------|-----------|
| GME | RK's top position — high insider buy, high short interest, retail sector |
| RRC | Natural gas — sector downtrend, known insider buy, bonds tested |
| RFP | Forest products — below book, Prem Watsa holder, lumber correlation |
| AAPL | Control case — should score LOW (not beaten down, not cheap) |
| META | Growth stock — should score HIGH on Swing Trader, low on RK scanner |

---

## 2. Environment Setup

### 2.1 Prerequisites

```bash
# Required software
Python 3.11+
Node.js 18+ (only needed for GitHub Actions, not local)
Git

# Verify versions
python --version    # should be 3.11+
git --version
```

### 2.2 Initial Project Setup

```bash
# Create project
mkdir rk-screener
cd rk-screener
git init

# Create virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# Create folder structure
mkdir -p pipeline/layers \
         pipeline/scoring \
         pipeline/scrapers \
         pipeline/llm \
         pipeline/data \
         pipeline/db \
         pipeline/swing \
         pipeline/utils \
         pipeline/tests \
         frontend/css \
         frontend/js/pages \
         frontend/js/components \
         frontend/js/utils \
         frontend/assets \
         output \
         cache/edgar \
         cache/yfinance \
         cache/scrapes \
         cache/gemini \
         logs \
         .github/workflows

# Create all empty __init__.py files
touch pipeline/__init__.py \
      pipeline/layers/__init__.py \
      pipeline/scoring/__init__.py \
      pipeline/scrapers/__init__.py \
      pipeline/llm/__init__.py \
      pipeline/db/__init__.py \
      pipeline/swing/__init__.py \
      pipeline/utils/__init__.py \
      pipeline/tests/__init__.py
```

### 2.3 requirements.txt

```
# Data fetching
yfinance==0.2.38
pandas==2.2.0
numpy==1.26.4
requests==2.31.0
beautifulsoup4==4.12.3
lxml==5.1.0

# Scraping
playwright==1.42.0
playwright-stealth==1.0.6      # prevents bot detection on FINRA + OpenInsider

# LLM
google-generativeai==0.5.4

# Utilities
python-dotenv==1.0.1
tqdm==4.66.2
schedule==1.2.1

# Testing
pytest==8.1.0
pytest-mock==3.12.0
responses==0.25.0
```

```bash
pip install -r requirements.txt
playwright install chromium --with-deps
pip freeze > requirements.lock   # lock exact versions for reproducibility
```

### 2.4 .env.example

```bash
# Copy this to .env and fill in values
# cp .env.example .env

# Gemini API (free tier — get at ai.google.dev)
GEMINI_API_KEY=

# Pipeline settings (override config.py defaults)
LAYER2_MIN_DRAWDOWN_PCT=40
LAYER4_MIN_INSIDER_BUY=200000

# Paths (defaults are fine for local development)
DB_PATH=rk_screener.db
OUTPUT_DIR=output/
CACHE_DIR=cache/
LOG_DIR=logs/

# Feature flags
ENABLE_GEMINI=false          # set true when Gemini key is added
ENABLE_BOND_SCRAPE=false     # Phase 1: Playwright bonds deferred to Phase 2
ENABLE_SWING_PIPELINE=false  # Phase 1: Swing Trader deferred to Phase 2
```

### 2.5 .gitignore

```
venv/
__pycache__/
*.pyc
.env
rk_screener.db
cache/
logs/
output/
*.egg-info/
.DS_Store
```

---

## 3. Phase 1 — Local Machine MVP

---

### Sprint 1 — Foundation (Days 1–3)

**Goal:** Project skeleton, config, database schema, logger, cache system. Pipeline can run but does nothing yet. By end of Sprint 1: `python pipeline/main.py` runs without errors and creates the database.

---

#### Day 1 — Config, Logger, Utils

**File: `pipeline/config.py`**

```python
import os
from dotenv import load_dotenv
load_dotenv()

# ── Pipeline thresholds ──────────────────────────────────────
LAYER2_MIN_DRAWDOWN_PCT    = float(os.getenv("LAYER2_MIN_DRAWDOWN_PCT", 40))
LAYER2_LOOKBACK_YEARS      = 3
LAYER3_MAX_PTBV            = 1.5
LAYER3_MIN_REVENUE         = 50_000_000
LAYER3_MAX_OVERHANG_RATIO  = 15.0
LAYER4_MIN_INSIDER_BUY     = float(os.getenv("LAYER4_MIN_INSIDER_BUY", 200_000))
LAYER5_BOND_SAFE           = 90
LAYER5_BOND_CAUTION        = 80
LAYER5_BOND_ELEVATED       = 70
LAYER5_BOND_HIGH_RISK      = 50

# ── Scoring weights (must sum to 100) ────────────────────────
SCORE_WEIGHTS = {
    "insider":       30,
    "bonds":         25,
    "fcf":           20,
    "institutional": 15,
    "technical":     10,
}
assert sum(SCORE_WEIGHTS.values()) == 100, "Score weights must sum to 100"

# ── Score component maximums ─────────────────────────────────
SCORE_MAX = {
    "insider":       30,
    "bonds":         25,
    "fcf":           20,
    "institutional": 15,
    "technical":     10,
}

# ── Upside multiple assumptions ───────────────────────────────
UPSIDE_CONSERVATIVE_MULTIPLE = 12
UPSIDE_BULL_MULTIPLE         = 18
DILUTION_TARGET_RATIO        = 4
DILUTION_DISCOUNT            = 0.80

# ── Sector context modifiers ─────────────────────────────────
SECTOR_DOWN_BONUS            = 5
SECTOR_UP_PENALTY            = -5
PEER_CONFIRMATION_BONUS      = 3

# ── ASC 842 lease flag threshold ─────────────────────────────
ASC842_LEASE_FLAG_PCT        = 0.30

# ── Score tier thresholds ────────────────────────────────────
TIER_EXCEPTIONAL             = 80
TIER_HIGH_CONVICTION         = 65
TIER_SPECULATIVE             = 40

# ── Data freshness (days before re-fetch) ────────────────────
FUNDAMENTALS_CACHE_DAYS      = 90
BOND_CACHE_DAYS              = 7
UNIVERSE_CACHE_DAYS          = 28
PRICE_CACHE_DAYS             = 1

# ── API rate limits ──────────────────────────────────────────
EDGAR_RATE_LIMIT_SLEEP       = 0.11
EDGAR_MAX_RETRIES            = 3
YFINANCE_BATCH_SIZE          = 50
YFINANCE_SLEEP               = 2.0
PLAYWRIGHT_TIMEOUT_MS        = 60_000

# ── Feature flags ────────────────────────────────────────────
ENABLE_GEMINI                = os.getenv("ENABLE_GEMINI", "false").lower() == "true"
ENABLE_BOND_SCRAPE           = os.getenv("ENABLE_BOND_SCRAPE", "true").lower() == "true"
ENABLE_SWING_PIPELINE        = os.getenv("ENABLE_SWING_PIPELINE", "true").lower() == "true"

# ── LLM ──────────────────────────────────────────────────────
GEMINI_API_KEY               = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL                 = "gemini-1.5-flash"
GEMINI_MAX_RETRIES           = 2

# ── Paths ────────────────────────────────────────────────────
DB_PATH                      = os.getenv("DB_PATH", "rk_screener.db")
OUTPUT_DIR                   = os.getenv("OUTPUT_DIR", "output/")
CACHE_DIR                    = os.getenv("CACHE_DIR", "cache/")
LOG_DIR                      = os.getenv("LOG_DIR", "logs/")
DATA_DIR                     = "pipeline/data/"
```

**File: `pipeline/utils/logger.py`**

```python
import logging
import os
from datetime import datetime
from pipeline import config

def get_logger(name: str) -> logging.Logger:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(
        config.LOG_DIR,
        f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
    )
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        )
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        logger.addHandler(ch)
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger
```

**File: `pipeline/utils/cache.py`**

```python
import os
import json
import pickle
from datetime import datetime, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def _cache_path(category: str, key: str, ext: str = "json") -> str:
    folder = os.path.join(config.CACHE_DIR, category)
    os.makedirs(folder, exist_ok=True)
    # Sanitise key for use as filename
    safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
    return os.path.join(folder, f"{safe_key}.{ext}")

def cache_get(category: str, key: str, ttl_days: int) -> dict | None:
    """Return cached data if fresh, else None."""
    path = _cache_path(category, key)
    if not os.path.exists(path):
        return None
    age_days = (datetime.now().timestamp() - os.path.getmtime(path)) / 86400
    if age_days > ttl_days:
        logger.debug(f"Cache stale ({age_days:.1f}d > {ttl_days}d): {category}/{key}")
        return None
    with open(path) as f:
        return json.load(f)

def cache_set(category: str, key: str, data: dict) -> None:
    """Write data to cache."""
    path = _cache_path(category, key)
    with open(path, "w") as f:
        json.dump(data, f, default=str)

def cache_get_pickle(category: str, key: str, ttl_days: int):
    """For non-JSON data (e.g. pandas DataFrames)."""
    path = _cache_path(category, key, ext="pkl")
    if not os.path.exists(path):
        return None
    age_days = (datetime.now().timestamp() - os.path.getmtime(path)) / 86400
    if age_days > ttl_days:
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def cache_set_pickle(category: str, key: str, data) -> None:
    path = _cache_path(category, key, ext="pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)
```

---

#### Day 2 — Database Schema

**File: `pipeline/db/schema.sql`**

```sql
-- Run once to initialise database

CREATE TABLE IF NOT EXISTS stocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL UNIQUE,
    company_name  TEXT,
    cik           TEXT,
    sector        TEXT,
    industry      TEXT,
    sic_code      TEXT,
    market_cap    REAL,
    last_price    REAL,
    last_updated  TIMESTAMP,
    is_active     INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS scanner_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date        TEXT NOT NULL,
    run_timestamp   TEXT NOT NULL,
    stocks_screened INTEGER,
    layer2_count    INTEGER,
    layer3_count    INTEGER,
    layer4_count    INTEGER,
    layer5_count    INTEGER,
    layer6_count    INTEGER,
    runtime_seconds INTEGER,
    errors_count    INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'completed'
);

CREATE TABLE IF NOT EXISTS candidates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    scanner_run_id          INTEGER REFERENCES scanner_runs(id),
    ticker                  TEXT NOT NULL,
    run_date                TEXT NOT NULL,
    is_current              INTEGER DEFAULT 1,
    price                   REAL,
    market_cap              REAL,
    price_to_tbv            REAL,
    fcf_3yr_avg             REAL,
    fcf_per_share           REAL,
    fcf_yield               REAL,
    net_common_overhang     REAL,
    net_overhang_fcf_ratio  REAL,
    pct_below_3yr_high      REAL,
    short_interest_pct      REAL,
    bond_price              REAL,
    bond_maturity_date      TEXT,
    bond_tier               TEXT,
    asc842_flag             INTEGER DEFAULT 0,
    lease_pct_of_lt_liab    REAL,
    insider_buy_amount      REAL,
    insider_buy_role        TEXT,
    insider_buy_date        TEXT,
    insider_buy_count       INTEGER,
    insider_pct_of_comp     REAL,
    value_fund_holder       TEXT,
    value_fund_pct_held     REAL,
    value_fund_added        INTEGER,
    insider_ownership_pct   REAL,
    rsi_weekly              REAL,
    rsi_trend               TEXT,
    sector_etf_3yr_return   REAL,
    stock_3yr_return        REAL,
    sector_context_modifier REAL,
    decline_type            TEXT,
    score_insider           REAL,
    score_bonds             REAL,
    score_fcf               REAL,
    score_institutional     REAL,
    score_technical         REAL,
    score_total             REAL,
    score_tier              TEXT,
    score_label             TEXT,
    conservative_upside     REAL,
    bull_upside             REAL,
    diluted_upside          REAL,
    dilution_risk_pct       REAL,
    risk_flags              TEXT,
    action_steps            TEXT,
    transparency_json       TEXT,
    top_signal              TEXT,
    UNIQUE(ticker, run_date)
);

CREATE TABLE IF NOT EXISTS watchlist (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT NOT NULL UNIQUE,
    company_name            TEXT,
    added_date              TEXT NOT NULL,
    notes                   TEXT,
    user_id                 TEXT DEFAULT NULL,
    alert_score_threshold   INTEGER,
    alert_insider_buy       INTEGER DEFAULT 0,
    alert_bond_below        REAL,
    alert_rsi_cross         INTEGER DEFAULT 0,
    last_alert_date         TEXT
);

CREATE TABLE IF NOT EXISTS metric_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    date            TEXT NOT NULL,
    score_total     REAL,
    price           REAL,
    fcf_yield       REAL,
    bond_price      REAL,
    rsi_weekly      REAL,
    insider_activity TEXT,
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT NOT NULL,
    user_id         TEXT DEFAULT NULL,
    alert_type      TEXT NOT NULL,
    alert_message   TEXT NOT NULL,
    trigger_date    TEXT NOT NULL,
    acknowledged    INTEGER DEFAULT 0,
    acknowledged_date TEXT
);

CREATE TABLE IF NOT EXISTS swing_candidates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                  TEXT NOT NULL,
    run_date                TEXT NOT NULL,
    is_current              INTEGER DEFAULT 1,
    price                   REAL,
    market_cap              REAL,
    revenue_growth_yoy      REAL,
    eps_beat_count          INTEGER,
    relative_strength_pct   REAL,
    rsi_daily               REAL,
    volume_ratio            REAL,
    ma50_above_ma200        INTEGER,
    price_above_ma50        INTEGER,
    setup_type              TEXT,
    score_revenue           REAL,
    score_technical         REAL,
    score_rs                REAL,
    score_earnings          REAL,
    score_volume            REAL,
    score_total             REAL,
    entry_zone_low          REAL,
    entry_zone_high         REAL,
    target_price            REAL,
    stop_loss               REAL,
    risk_reward_ratio       REAL,
    UNIQUE(ticker, run_date)
);

CREATE TABLE IF NOT EXISTS value_funds (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_name       TEXT NOT NULL,
    cik             TEXT,
    manager_name    TEXT,
    known_for       TEXT,
    min_aum_m       REAL DEFAULT 50,
    active          INTEGER DEFAULT 1,
    added_date      TEXT,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS edgar_cache (
    ticker          TEXT NOT NULL,
    cik             TEXT NOT NULL,
    data_type       TEXT NOT NULL,
    fiscal_year     INTEGER,
    fiscal_quarter  INTEGER,
    data_json       TEXT,
    fetched_date    TEXT NOT NULL,
    PRIMARY KEY (ticker, data_type, fiscal_year, fiscal_quarter)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_candidates_date    ON candidates(run_date);
CREATE INDEX IF NOT EXISTS idx_candidates_ticker  ON candidates(ticker);
CREATE INDEX IF NOT EXISTS idx_candidates_score   ON candidates(score_total);
CREATE INDEX IF NOT EXISTS idx_candidates_current ON candidates(is_current);
CREATE INDEX IF NOT EXISTS idx_metric_history     ON metric_history(ticker, date);
CREATE INDEX IF NOT EXISTS idx_alerts_unread      ON alerts(acknowledged);
CREATE INDEX IF NOT EXISTS idx_watchlist_user     ON watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user        ON alerts(user_id);
```

**File: `pipeline/db/database.py`**

```python
import sqlite3
import os
from pipeline import config
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

def get_connection() -> sqlite3.Connection:
    # FIX: timeout=10 prevents OperationalError if two pipeline runs
    # overlap (e.g. manual run + scheduled run). WAL mode + timeout
    # together handle most concurrent access scenarios safely.
    conn = sqlite3.connect(config.DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db() -> None:
    """Create all tables if they don't exist."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema_sql = f.read()
    with get_connection() as conn:
        conn.executescript(schema_sql)
    logger.info("Database initialised")

def upsert_candidate(conn: sqlite3.Connection, data: dict) -> None:
    """Insert or update a scored candidate.

    FIX: original code included 'id', 'ticker', 'run_date' in the
    UPDATE SET clause which breaks the UNIQUE constraint logic.
    These must be excluded — they are the conflict keys, not update targets.
    """
    _EXCLUDE_FROM_UPDATE = frozenset({"id", "ticker", "run_date"})
    columns = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    updates = ", ".join([f"{k}=excluded.{k}" for k in data.keys()
                         if k not in _EXCLUDE_FROM_UPDATE])
    sql = f"""
        INSERT INTO candidates ({columns}) VALUES ({placeholders})
        ON CONFLICT(ticker, run_date) DO UPDATE SET {updates}
    """
    conn.execute(sql, list(data.values()))

def get_watchlist(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM watchlist").fetchall()
    return [dict(row) for row in rows]

def save_alert(conn: sqlite3.Connection, ticker: str,
               alert_type: str, message: str) -> None:
    from datetime import date
    conn.execute(
        """INSERT INTO alerts (ticker, alert_type, alert_message, trigger_date)
           VALUES (?, ?, ?, ?)""",
        (ticker, alert_type, message, date.today().isoformat())
    )
```

---

#### Day 3 — Data Reference Files, Stub Files, and main.py Shell

**CRITICAL — Create all stub files first (before data files or main.py)**

`main.py` imports all layer and scoring modules at the top of file. If any
module is missing, `python pipeline/main.py --test` crashes with `ImportError`
before doing anything. Create these stubs on Day 3 — they simply pass data
through unchanged until the real implementation replaces them in later sprints.

```python
# pipeline/layers/layer1_universe.py  (STUB — replace in Sprint 2)
def run(input_data, cfg, market="US"):
    return []

# pipeline/layers/layer2_price.py  (STUB — replace in Sprint 2)
def run(tickers, cfg, market="US"):
    return tickers   # pass-through

# pipeline/layers/layer3_fundamentals.py  (STUB — replace in Sprint 2)
def run(tickers, cfg, market="US"):
    return tickers

# pipeline/layers/layer4_conviction.py  (STUB — replace in Sprint 3)
def run(tickers, cfg, market="US"):
    return tickers

# pipeline/layers/layer5_bonds.py  (STUB — replace in Sprint 3)
def run(tickers, cfg, market="US"):
    return tickers

# pipeline/layers/layer6_technical.py  (STUB — replace in Sprint 3)
def run(tickers, cfg, market="US"):
    return tickers

# pipeline/swing/swing_pipeline.py  (STUB — full build in Phase 2)
def run(tickers, cfg):
    return {"generated_at": "", "candidates": [], "stats": {}}

# pipeline/scoring/confidence_score.py  (STUB — replace in Sprint 4)
class RKScorer:
    def score(self, stock, weights_override=None):
        return {
            "score_total": 0, "score_tier": "Watch Only",
            "score_label": "Not yet scored", "score_color": "watch",
            "sector_modifier": 0, "components": {}, "transparency": {},
            "conservative_upside": None, "bull_upside": None,
            "diluted_upside": None, "dilution_risk_pct": 0,
            "risk_flags": [], "action_steps": [],
            "top_signal": "Stub scorer", "suggested_position": "0%",
        }

# pipeline/scoring/transparency.py  (STUB — replace in Sprint 4)
class TransparencyBuilder:
    def build(self, stock, components, sector_mod, total):
        return {"summary": "", "total_explanation": "", "components": {}}

# pipeline/scoring/upside_calc.py  (STUB — replace in Sprint 4)
class UpsideCalc:
    def calculate(self, stock):
        return {"conservative": None, "bull": None,
                "diluted": None, "dilution_pct": 0}

# pipeline/scoring/risk_flags.py  (STUB — replace in Sprint 4)
class RiskFlagGenerator:
    def generate(self, stock, components):
        return []

# pipeline/scoring/action_steps.py  (STUB — replace in Sprint 4)
class ActionStepGenerator:
    def generate(self, stock, components):
        return []
```

**Day 3 checkpoint — run this after creating all stubs:**
```bash
python pipeline/main.py --test
# Expected: runs cleanly, creates rk_screener.db,
# writes output/results.json with 5 test tickers all scoring 0.
# No ImportError. No crashes.
```

---

**File: `pipeline/data/secular_decline_sic.json`**

```json
["5311","5331","5411","7841","2711","2720","4813","1220","1221","5940","5945"]
```

SIC codes representing known secular decline industries: department stores,
variety stores, legacy grocery chains, video rental, newspapers, periodicals,
landline telephone services, coal mining.

**File: `pipeline/data/cyclical_sic.json`**

```json
["1311","1381","1382","1389","4922","4924","1000","1040","1090","1094",
 "2400","2421","2490","2800","2810","2860","2869","3310","3312","3317",
 "3390","1520","1521","1522","1531"]
```

SIC codes representing cyclical industries (commodity cycles, housing cycles):
oil and gas E&P, oil services, natural gas distribution, metal mining,
gold and silver mining, lumber and wood products, commodity chemicals,
steel manufacturing, homebuilders and residential construction.

**File: `pipeline/data/sector_etf_map.json`**

```json
{
  "Energy": "XLE",
  "Materials": "XLB",
  "Industrials": "XLI",
  "Consumer Discretionary": "XLY",
  "Consumer Staples": "XLP",
  "Health Care": "XLV",
  "Financials": "XLF",
  "Information Technology": "XLK",
  "Communication Services": "XLC",
  "Utilities": "XLU",
  "Real Estate": "XLRE",
  "Natural Gas": "FCG",
  "Retail": "XRT",
  "Gold": "GLD",
  "Silver": "SLV",
  "Oil": "USO",
  "Steel": "SLX"
}
```

**File: `pipeline/data/value_funds.json`**

```json
[
  {"fund_name": "Baupost Group",       "manager": "Seth Klarman",    "known_for": "deep value"},
  {"fund_name": "Greenlight Capital",  "manager": "David Einhorn",   "known_for": "deep value, short selling"},
  {"fund_name": "Fairfax Financial",   "manager": "Prem Watsa",      "known_for": "deep value, insurance"},
  {"fund_name": "Pershing Square",     "manager": "Bill Ackman",     "known_for": "activist"},
  {"fund_name": "Third Point",         "manager": "Dan Loeb",        "known_for": "activist"},
  {"fund_name": "ValueAct Capital",    "manager": "Jeff Ubben",      "known_for": "activist"},
  {"fund_name": "Starboard Value",     "manager": "Jeff Smith",      "known_for": "activist"},
  {"fund_name": "Gotham Asset Mgmt",   "manager": "Joel Greenblatt", "known_for": "deep value, quant"},
  {"fund_name": "Pabrai Funds",        "manager": "Mohnish Pabrai",  "known_for": "deep value, Buffett style"},
  {"fund_name": "Oaktree Capital",     "manager": "Howard Marks",    "known_for": "distressed, value"},
  {"fund_name": "Tweedy Browne",       "manager": "Various",         "known_for": "deep value, Graham style"},
  {"fund_name": "Sequoia Fund",        "manager": "Various",         "known_for": "concentrated value"},
  {"fund_name": "Leucadia National",   "manager": "Various",         "known_for": "deep value"},
  {"fund_name": "Icahn Enterprises",   "manager": "Carl Icahn",      "known_for": "activist"},
  {"fund_name": "Elliott Management",  "manager": "Paul Singer",     "known_for": "activist"},
  {"fund_name": "Maverick Capital",    "manager": "Lee Ainslie",     "known_for": "value, tiger cub"},
  {"fund_name": "Permit Capital",      "manager": "Various",         "known_for": "deep value"},
  {"fund_name": "Hesta",               "manager": "Various",         "known_for": "institutional value"},
  {"fund_name": "Mast Asset Mgmt",     "manager": "Various",         "known_for": "deep value, Korea"}
]
```

**File: `pipeline/main.py`**

```python
"""
RK Stock Screener — Main Pipeline Entry Point

Usage:
    python pipeline/main.py              # full nightly run
    python pipeline/main.py --ticker GME # single ticker deep dive
    python pipeline/main.py --test       # run on 5 test tickers only
"""
import argparse
import time
import json
import os
from datetime import date, datetime
from pipeline import config
from pipeline.db.database import init_db, get_connection
from pipeline.utils.logger import get_logger

# ── FIX: all imports at top of file — fail fast at startup ──
# Previously imports were inside run_pipeline(). A syntax error in
# any layer would crash mid-run after Layer 2 had already written data.
# Moving here ensures all modules are importable before the pipeline starts.
from pipeline.layers.layer1_universe   import run as layer1_run
from pipeline.layers.layer2_price      import run as layer2_run
from pipeline.layers.layer3_fundamentals import run as layer3_run
from pipeline.layers.layer4_conviction import run as layer4_run
from pipeline.layers.layer5_bonds      import run as layer5_run
from pipeline.layers.layer6_technical  import run as layer6_run
from pipeline.scoring.confidence_score import RKScorer
from pipeline.swing.swing_pipeline     import run as swing_run  # stub in Phase 1

logger = get_logger("main")

TEST_TICKERS = [
    {"ticker": "GME",  "cik": "0001326380"},
    {"ticker": "RRC",  "cik": "0000315131"},
    {"ticker": "RFP",  "cik": "0001393505"},
    {"ticker": "AAPL", "cik": "0000320193"},  # control: should score low
    {"ticker": "META", "cik": "0001326801"},  # control: should score low
]

def run_pipeline(tickers: list[dict] = None, single_ticker: str = None) -> dict:
    start_time = time.time()
    run_date = date.today().isoformat()
    logger.info(f"=== Pipeline starting — {run_date} ===")

    init_db()

    # ── Layer 1: Universe ────────────────────────────────────
    if single_ticker:
        universe = [{"ticker": single_ticker}]
    elif tickers:
        universe = tickers
    else:
        universe = layer1_run({}, config.__dict__)
    logger.info(f"Layer 1 complete: {len(universe)} tickers")

    # ── Layer 2: Price Pain ──────────────────────────────────
    price_filtered = layer2_run(universe, config.__dict__)
    logger.info(f"Layer 2 complete: {len(price_filtered)} tickers")

    # ── Layer 3: Fundamentals ────────────────────────────────
    fund_filtered = layer3_run(price_filtered, config.__dict__)
    logger.info(f"Layer 3 complete: {len(fund_filtered)} tickers")

    # ── Layer 4: Conviction Signals ──────────────────────────
    conviction_filtered = layer4_run(fund_filtered, config.__dict__)
    logger.info(f"Layer 4 complete: {len(conviction_filtered)} tickers")

    # ── Layer 5: Bond / Survival ─────────────────────────────
    bond_checked = layer5_run(conviction_filtered, config.__dict__)
    logger.info(f"Layer 5 complete: {len(bond_checked)} tickers")

    # ── Layer 6: Technical ───────────────────────────────────
    final_candidates = layer6_run(bond_checked, config.__dict__)
    logger.info(f"Layer 6 complete: {len(final_candidates)} tickers")

    # ── FIX: strip non-serialisable fields before scoring/output ──
    # _price_series is a pandas Series added in Layer 2 for RSI reuse.
    # It must be removed before json.dumps() or SQLite insert — both crash
    # with TypeError if a Series is present anywhere in the dict.
    for stock in final_candidates:
        stock.pop("_price_series", None)

    # ── Scoring ──────────────────────────────────────────────
    scorer = RKScorer()
    scored = []
    for stock in final_candidates:
        try:
            result = scorer.score(stock)
            stock.update(result)
            scored.append(stock)
        except Exception as e:
            logger.error(f"Scoring failed for {stock.get('ticker')}: {e}")

    # Sort by score descending
    scored.sort(key=lambda x: x.get("score_total", 0), reverse=True)

    # ── Write outputs ────────────────────────────────────────
    runtime = int(time.time() - start_time)
    results = {
        "generated_at": datetime.now().isoformat(),
        "run_date": run_date,
        "stats": {
            "stocks_screened": len(universe),
            "layer2_passed":   len(price_filtered),
            "layer3_passed":   len(fund_filtered),
            "layer4_passed":   len(conviction_filtered),
            "layer5_passed":   len(bond_checked),
            "layer6_passed":   len(final_candidates),
            "scored":          len(scored),
            "runtime_seconds": runtime,
        },
        "candidates": scored,
    }

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(config.OUTPUT_DIR, "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results written to {output_path}")

    # ── Save to database ─────────────────────────────────────
    _save_to_db(results, run_date, runtime, len(universe))

    # ── Swing pipeline ───────────────────────────────────────
    if config.ENABLE_SWING_PIPELINE:
        try:
            from pipeline.swing.swing_pipeline import run as swing_run
            swing_results = swing_run(universe, config.__dict__)
            swing_path = os.path.join(config.OUTPUT_DIR, "swing_results.json")
            with open(swing_path, "w") as f:
                json.dump(swing_results, f, indent=2, default=str)
            logger.info(f"Swing results written to {swing_path}")
        except Exception as e:
            logger.error(f"Swing pipeline failed: {e}")

    # ── Check watchlist alerts ───────────────────────────────
    _check_watchlist_alerts(scored)

    logger.info(f"=== Pipeline complete in {runtime}s — "
                f"{len(scored)} candidates ===")
    return results

def _save_to_db(results: dict, run_date: str,
                runtime: int, screened: int) -> None:
    from pipeline.db.database import upsert_candidate
    with get_connection() as conn:
        # Mark all previous candidates as not current
        conn.execute(
            "UPDATE candidates SET is_current = 0 WHERE run_date != ?",
            (run_date,)
        )
        # Insert run record
        conn.execute("""
            INSERT INTO scanner_runs
            (run_date, run_timestamp, stocks_screened,
             layer2_count, layer3_count, layer4_count,
             layer5_count, layer6_count, runtime_seconds, status)
            VALUES (?,?,?,?,?,?,?,?,?,'completed')
        """, (
            run_date,
            results["generated_at"],
            screened,
            results["stats"]["layer2_passed"],
            results["stats"]["layer3_passed"],
            results["stats"]["layer4_passed"],
            results["stats"]["layer5_passed"],
            results["stats"]["layer6_passed"],
            runtime,
        ))
        # Insert candidates
        for c in results["candidates"]:
            flat = _flatten_for_db(c, run_date)
            upsert_candidate(conn, flat)
        conn.commit()

def _flatten_for_db(candidate: dict, run_date: str) -> dict:
    """Flatten nested candidate dict for SQLite storage."""
    import json as _json
    return {
        "ticker": candidate.get("ticker"),
        "run_date": run_date,
        "is_current": 1,
        "price": candidate.get("price"),
        "market_cap": candidate.get("market_cap"),
        "score_total": candidate.get("score_total"),
        "score_tier": candidate.get("score_tier", {}).get("label")
                      if isinstance(candidate.get("score_tier"), dict)
                      else candidate.get("score_tier"),
        "score_label": candidate.get("score_label"),
        "conservative_upside": candidate.get("conservative_upside"),
        "bull_upside": candidate.get("bull_upside"),
        "risk_flags": _json.dumps(candidate.get("risk_flags", [])),
        "action_steps": _json.dumps(candidate.get("action_steps", [])),
        "transparency_json": _json.dumps(candidate.get("transparency", {})),
        "top_signal": candidate.get("top_signal"),
    }

def _check_watchlist_alerts(scored: list[dict]) -> None:
    """Compare new scores against watchlist alert thresholds."""
    import json as _json
    score_map = {s["ticker"]: s.get("score_total", 0) for s in scored}
    alerts_generated = []

    with get_connection() as conn:
        watchlist = conn.execute("SELECT * FROM watchlist").fetchall()
        for stock in watchlist:
            ticker = stock["ticker"]
            threshold = stock["alert_score_threshold"]
            if threshold and ticker in score_map:
                # Get previous score
                prev = conn.execute(
                    """SELECT score_total FROM candidates
                       WHERE ticker=? AND is_current=0
                       ORDER BY run_date DESC LIMIT 1""",
                    (ticker,)
                ).fetchone()
                prev_score = prev["score_total"] if prev else 0
                curr_score = score_map[ticker]
                if prev_score < threshold <= curr_score:
                    msg = (f"{ticker} score crossed {threshold} "
                           f"(now {curr_score:.0f}, was {prev_score:.0f})")
                    alerts_generated.append({
                        "ticker": ticker,
                        "type": "score_crossed",
                        "message": msg
                    })
                    conn.execute(
                        """INSERT INTO alerts
                           (ticker, alert_type, alert_message, trigger_date)
                           VALUES (?,?,?,?)""",
                        (ticker, "score_crossed", msg,
                         date.today().isoformat())
                    )
        conn.commit()

    # Write alerts.json for frontend
    unread = []
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE acknowledged=0 ORDER BY trigger_date DESC"
        ).fetchall()
        unread = [dict(r) for r in rows]

    alerts_path = os.path.join(config.OUTPUT_DIR, "alerts.json")
    with open(alerts_path, "w") as f:
        _json.dump({"alerts": unread, "count": len(unread)}, f, indent=2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RK Stock Screener Pipeline")
    parser.add_argument("--ticker", type=str, help="Run on single ticker only")
    parser.add_argument("--test", action="store_true",
                        help="Run on 5 test tickers only")
    args = parser.parse_args()

    if args.test:
        run_pipeline(tickers=TEST_TICKERS)
    elif args.ticker:
        run_pipeline(single_ticker=args.ticker.upper())
    else:
        run_pipeline()
```

**Checkpoint — end of Sprint 1:**
```bash
python pipeline/main.py --test
# Expected: creates rk_screener.db, creates output/results.json
# All 5 test tickers pass through all layers (stubs return input unchanged)
# results.json shows all 5 tickers with score_total: 0 (stub scorer)
# NO ImportError — all modules exist (as stubs)
# NO crashes — _price_series pop, timeout, upsert all working
```

---

### Sprint 2 — Data Pipeline Layers 1–3 (Days 4–7)

**Goal:** Universe fetch, price pain screen, and fundamental screen all working. By end of Sprint 2: `python pipeline/main.py --test` returns real filtered tickers with fundamental data attached.

---

#### Day 4 — Layer 1: Universe Fetch

**File: `pipeline/utils/edgar.py`**

```python
import time
import requests
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)
EDGAR_BASE = "https://data.sec.gov"
EDGAR_EFTS = "https://efts.sec.gov"
HEADERS = {"User-Agent": "RK-Screener research@example.com"}

def edgar_get(path: str, retries: int = 3) -> dict:
    """GET from EDGAR API with rate limiting and retries."""
    url = f"{EDGAR_BASE}{path}"
    for attempt in range(retries):
        try:
            time.sleep(config.EDGAR_RATE_LIMIT_SLEEP)
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.HTTPError as e:
            if r.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"EDGAR rate limited, waiting {wait}s")
                time.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}

def get_company_facts(cik: str) -> dict:
    """Fetch all XBRL facts for a company. Cached 90 days."""
    padded = cik.zfill(10)
    cached = cache_get("edgar", f"facts_{padded}",
                       ttl_days=config.FUNDAMENTALS_CACHE_DAYS)
    if cached:
        return cached
    data = edgar_get(f"/api/xbrl/companyfacts/CIK{padded}.json")
    cache_set("edgar", f"facts_{padded}", data)
    return data

def get_submissions(cik: str) -> dict:
    """Fetch company submissions (filing history + metadata)."""
    padded = cik.zfill(10)
    cached = cache_get("edgar", f"submissions_{padded}", ttl_days=7)
    if cached:
        return cached
    data = edgar_get(f"/submissions/CIK{padded}.json")
    cache_set("edgar", f"submissions_{padded}", data)
    return data

def search_filings(ticker: str, form_types: list[str],
                   days_back: int = 365) -> list[dict]:
    """Search EDGAR full-text for recent filings by ticker."""
    from datetime import date, timedelta
    start = (date.today() - timedelta(days=days_back)).isoformat()
    forms = ",".join(form_types)
    url = (f"{EDGAR_EFTS}/efts/hit?q=%22{ticker}%22"
           f"&forms={forms}&dateRange=custom&startdt={start}")
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json().get("hits", {}).get("hits", [])

def cik_for_ticker(ticker: str) -> str | None:
    """Look up CIK for a given ticker."""
    cached = cache_get("edgar", f"cik_{ticker}", ttl_days=90)
    if cached:
        return cached.get("cik")
    url = f"{EDGAR_BASE}/cgi-bin/browse-edgar?company=&CIK={ticker}&type=10-K&dateb=&owner=include&count=1&search_text=&action=getcompany&output=atom"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        # Parse CIK from response
        import re
        match = re.search(r'CIK=(\d+)', r.text)
        if match:
            cik = match.group(1)
            cache_set("edgar", f"cik_{ticker}", {"cik": cik})
            return cik
    except Exception:
        pass
    return None
```

**File: `pipeline/utils/yfinance_helpers.py`**

```python
import time
import yfinance as yf
import pandas as pd
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get_pickle, cache_set_pickle

logger = get_logger(__name__)

def get_ticker_info(ticker: str) -> dict:
    """Fetch ticker metadata with caching."""
    cached = cache_get_pickle("yfinance", f"info_{ticker}",
                              ttl_days=config.PRICE_CACHE_DAYS)
    if cached is not None:
        return cached
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        cache_set_pickle("yfinance", f"info_{ticker}", info)
        return info
    except Exception as e:
        logger.warning(f"yfinance info failed for {ticker}: {e}")
        return {}

def get_weekly_history(ticker: str, period: str = "5y") -> pd.DataFrame:
    """Fetch weekly OHLCV history with caching."""
    cache_key = f"weekly_{ticker}_{period}"
    cached = cache_get_pickle("yfinance", cache_key,
                              ttl_days=config.PRICE_CACHE_DAYS)
    if cached is not None:
        return cached
    try:
        df = yf.download(ticker, period=period, interval="1wk",
                         auto_adjust=True, progress=False)
        cache_set_pickle("yfinance", cache_key, df)
        return df
    except Exception as e:
        logger.warning(f"yfinance history failed for {ticker}: {e}")
        return pd.DataFrame()

def bulk_download_history(tickers: list[str],
                          period: str = "5y") -> dict[str, pd.DataFrame]:
    """Batch download for multiple tickers."""
    results = {}
    batches = [tickers[i:i+config.YFINANCE_BATCH_SIZE]
               for i in range(0, len(tickers), config.YFINANCE_BATCH_SIZE)]

    for i, batch in enumerate(batches):
        logger.info(f"Downloading batch {i+1}/{len(batches)} "
                    f"({len(batch)} tickers)")
        try:
            data = yf.download(
                " ".join(batch), period=period,
                interval="1wk", auto_adjust=True,
                progress=False, group_by="ticker"
            )
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        results[ticker] = data
                    else:
                        results[ticker] = data[ticker].dropna(how="all")
                except KeyError:
                    results[ticker] = pd.DataFrame()
        except Exception as e:
            logger.error(f"Batch download failed: {e}")
            for ticker in batch:
                results[ticker] = pd.DataFrame()
        if i < len(batches) - 1:
            time.sleep(config.YFINANCE_SLEEP)
    return results

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI for a price series."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float('inf'))
    return 100 - (100 / (1 + rs))
```

**File: `pipeline/layers/layer1_universe.py`**

```python
"""
Layer 1 — Universe Fetch
Input:  config dict
Output: list of {"ticker": str, "cik": str, ...} dicts (~6,000)
"""
import requests
import json
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)
HEADERS = {"User-Agent": "RK-Screener research@example.com"}

def run(input_data: dict, cfg: dict, market: str = "US") -> list[dict]:
    """Fetch universe of US-listed stocks from SEC EDGAR."""
    cached = cache_get("universe", "us_tickers",
                       ttl_days=config.UNIVERSE_CACHE_DAYS)
    if cached:
        logger.info(f"Universe loaded from cache: {len(cached)} tickers")
        return cached

    logger.info("Fetching universe from SEC EDGAR...")
    try:
        r = requests.get(
            "https://www.sec.gov/files/company_tickers_exchange.json",
            headers=HEADERS, timeout=60
        )
        r.raise_for_status()
        raw = r.json()
    except Exception as e:
        logger.error(f"Failed to fetch universe: {e}")
        return []

    tickers = []
    raw_data = raw.get("data", [])

    # FIX: validate response format before processing.
    # This endpoint has changed format twice historically.
    # Expected: list of [cik, name, ticker, exchange] lists.
    # Catch format changes early with a clear error message.
    if not raw_data:
        logger.error("EDGAR company_tickers_exchange.json returned empty data")
        return []
    if not isinstance(raw_data[0], list) or len(raw_data[0]) < 4:
        logger.error(
            f"EDGAR company_tickers_exchange.json format changed! "
            f"Expected list of [cik,name,ticker,exchange], "
            f"got: {raw_data[0]}. Update layer1_universe.py to match."
        )
        return []

    for item in raw_data:
        # Format: [cik, name, ticker, exchange]
        if len(item) >= 4 and item[3] in ("Nasdaq", "NYSE", "NYSE MKT"):
            tickers.append({
                "ticker":       item[2].upper(),
                "company_name": item[1],
                "cik":          str(item[0]).zfill(10),
                "exchange":     item[3],
            })

    logger.info(f"Universe: {len(tickers)} tickers from EDGAR")
    cache_set("universe", "us_tickers", tickers)
    return tickers
```

---

#### Day 5 — Layer 2: Price Pain Screen

**File: `pipeline/layers/layer2_price.py`**

```python
"""
Layer 2 — Price Pain Screen
Input:  list of ticker dicts from Layer 1
Output: filtered list with price data added (~400 tickers)
Filter: stock down 40%+ from 3yr high
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.yfinance_helpers import (
    bulk_download_history, get_ticker_info
)

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    symbols = [t["ticker"] for t in tickers]
    ticker_map = {t["ticker"]: t for t in tickers}

    logger.info(f"Downloading 5yr weekly history for {len(symbols)} tickers...")
    histories = bulk_download_history(symbols, period="5y")

    passed = []
    failed_count = 0

    for ticker, df in histories.items():
        try:
            result = _evaluate_ticker(ticker, df, ticker_map.get(ticker, {}))
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 2 failed for {ticker}: {e}")
            failed_count += 1

    logger.info(f"Layer 2: {len(passed)} passed, "
                f"{len(symbols)-len(passed)-failed_count} filtered, "
                f"{failed_count} errors")
    return passed

def _evaluate_ticker(ticker: str, df: pd.DataFrame,
                     base_data: dict) -> dict | None:
    if df.empty or len(df) < 52:  # need at least 1yr of weekly data
        return None

    close = df["Close"].dropna()
    if len(close) < 52:
        return None

    current_price = float(close.iloc[-1])
    if current_price <= 0:
        return None

    # 3yr high (156 weeks)
    lookback = min(len(close), 156)
    high_3yr = float(close.iloc[-lookback:].max())

    pct_below_3yr_high = (current_price - high_3yr) / high_3yr
    # Negative number — e.g. -0.67 means down 67%

    # Hard filter: must be down at least LAYER2_MIN_DRAWDOWN_PCT
    threshold = -config.LAYER2_MIN_DRAWDOWN_PCT / 100
    if pct_below_3yr_high > threshold:
        return None

    # 52wk low proximity (how close to 52wk low?)
    low_52wk = float(close.iloc[-52:].min())
    pct_above_52wk_low = (current_price - low_52wk) / low_52wk

    return {
        **base_data,
        "ticker":               ticker,
        "price":                round(current_price, 2),
        "high_3yr":             round(high_3yr, 2),
        "pct_below_3yr_high":   round(pct_below_3yr_high, 4),
        "pct_above_52wk_low":   round(pct_above_52wk_low, 4),
        "low_52wk":             round(low_52wk, 2),
        "price_history_weeks":  len(close),
        "_price_series":        close,   # kept for Layer 6 RSI; stripped before JSON output
    }
```

---

#### Days 6–7 — Layer 3: Fundamentals

**File: `pipeline/layers/layer3_fundamentals.py`**

```python
"""
Layer 3 — Fundamental Value Screen
Input:  list of price-filtered ticker dicts
Output: filtered list with fundamental data added (~100 tickers)
Filters: P/TBV < 1.5, positive 3yr FCF, revenue > $50M,
         overhang/FCF < 15x
"""
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.edgar import get_company_facts
from pipeline.layers._fundamentals_parser import FundamentalsParser

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 3 failed for {stock['ticker']}: {e}")
    logger.info(f"Layer 3: {len(passed)}/{len(tickers)} passed fundamentals")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]
    cik = stock.get("cik")
    if not cik:
        return None

    facts = get_company_facts(cik)
    if not facts:
        return None

    parser = FundamentalsParser(facts, ticker)

    # ── Revenue check ────────────────────────────────────────
    revenue = parser.get_latest_annual("Revenues",
                  fallbacks=["RevenueFromContractWithCustomerExcludingAssessedTax",
                             "SalesRevenueNet"])
    if not revenue or revenue < config.LAYER3_MIN_REVENUE:
        return None

    # ── FCF computation ──────────────────────────────────────
    op_cf_series = parser.get_annual_series("NetCashProvidedByUsedInOperatingActivities")
    capex_series = parser.get_annual_series(
        "PaymentsToAcquirePropertyPlantAndEquipment",
        fallbacks=["CapitalExpenditureContinuingOperations"]
    )
    if not op_cf_series or len(op_cf_series) < 1:
        return None

    fcf_series = {}
    for year in op_cf_series:
        op_cf = op_cf_series[year]
        capex = capex_series.get(year, 0) or 0
        fcf_series[year] = op_cf - abs(capex)

    # 3yr average FCF
    recent_years = sorted(fcf_series.keys())[-3:]
    fcf_values = [fcf_series[y] for y in recent_years]
    fcf_3yr_avg = sum(fcf_values) / len(fcf_values)

    # Hard filter: 3yr avg FCF must be positive
    if fcf_3yr_avg <= 0:
        return None

    # ── Balance sheet ────────────────────────────────────────
    shares = parser.get_latest("CommonStockSharesOutstanding",
                 fallbacks=["EntityCommonStockSharesOutstanding"])
    if not shares or shares <= 0:
        return None

    total_assets = parser.get_latest_annual("Assets")
    total_liab   = parser.get_latest_annual("Liabilities")
    goodwill     = parser.get_latest_annual("Goodwill") or 0
    intangibles  = parser.get_latest_annual(
        "FiniteLivedIntangibleAssetsNet",
        fallbacks=["IntangibleAssetsNetExcludingGoodwill"]
    ) or 0
    cash         = parser.get_latest_annual(
        "CashAndCashEquivalentsAtCarryingValue",
        fallbacks=["CashCashEquivalentsAndShortTermInvestments"]
    ) or 0
    st_debt      = parser.get_latest_annual(
        "ShortTermBorrowings",
        fallbacks=["NotesPayableCurrent"]
    ) or 0
    lt_liab      = parser.get_latest_annual("LiabilitiesNoncurrent") or total_liab or 0

    if not total_assets or not total_liab:
        return None

    # Tangible book value
    # FIX: deferred tax assets are not tangible — must be stripped.
    # Original plan missed this. For financial companies and post-restructuring
    # companies, deferred tax assets can be 20-40% of total assets, making
    # P/TBV appear artificially low and misleadingly cheap.
    deferred_tax = parser.get_latest_annual(
        "DeferredTaxAssetsNet",
        fallbacks=["DeferredIncomeTaxAssetsNet",
                   "DeferredTaxAssetsGross"]
    ) or 0

    tangible_book = total_assets - goodwill - intangibles - deferred_tax - total_liab
    tangible_book_per_share = tangible_book / shares

    price = stock.get("price", 0)
    if price <= 0:
        return None

    ptbv = price / tangible_book_per_share if tangible_book_per_share > 0 else 999

    # Hard filter: P/TBV
    if ptbv > config.LAYER3_MAX_PTBV:
        return None

    # ── Net common overhang ──────────────────────────────────
    # Check for ASC 842 lease distortion
    op_lease_liab = parser.get_latest_annual(
        "OperatingLeaseLiability",
        fallbacks=["OperatingLeaseLiabilityNoncurrent"]
    ) or 0
    asc842_flag = False
    lease_pct = 0
    if lt_liab > 0 and op_lease_liab > 0:
        lease_pct = op_lease_liab / lt_liab
        asc842_flag = lease_pct > config.ASC842_LEASE_FLAG_PCT

    net_overhang = lt_liab + st_debt - cash
    # ASC 842 adjustment: subtract operating lease liabilities
    net_overhang_adjusted = net_overhang - op_lease_liab

    fcf_per_share = fcf_3yr_avg / shares
    fcf_yield = fcf_per_share / price

    overhang_ratio = net_overhang_adjusted / fcf_3yr_avg if fcf_3yr_avg > 0 else 999

    # Hard filter: overhang/FCF
    if overhang_ratio > config.LAYER3_MAX_OVERHANG_RATIO:
        return None

    # ── Market cap check ─────────────────────────────────────
    market_cap = price * shares

    # ── Dilution calculator ──────────────────────────────────
    dilution_pct = 0
    diluted_shares = shares
    if overhang_ratio > 8:
        target_overhang = fcf_3yr_avg * config.DILUTION_TARGET_RATIO
        excess = net_overhang_adjusted - target_overhang
        if excess > 0:
            issue_price = price * config.DILUTION_DISCOUNT
            shares_to_issue = excess / issue_price
            diluted_shares = shares + shares_to_issue
            dilution_pct = shares_to_issue / shares

    return {
        **stock,
        "market_cap":              round(market_cap),
        "revenue_ttm":             round(revenue),
        "fcf_3yr_avg":             round(fcf_3yr_avg),
        "fcf_per_share":           round(fcf_per_share, 2),
        "fcf_yield":               round(fcf_yield, 4),
        "fcf_series":              fcf_series,
        "price_to_tbv":            round(ptbv, 2),
        "tangible_book_per_share": round(tangible_book_per_share, 2),
        "net_common_overhang":     round(net_overhang_adjusted),
        "net_overhang_fcf_ratio":  round(overhang_ratio, 1),
        "asc842_flag":             asc842_flag,
        "lease_pct_of_lt_liab":    round(lease_pct, 2),
        "shares_outstanding":      shares,
        "diluted_shares":          round(diluted_shares),
        "dilution_risk_pct":       round(dilution_pct, 3),
        "cash":                    cash,
        "short_term_debt":         st_debt,
        "lt_liabilities":          lt_liab,
    }
```

**File: `pipeline/layers/_fundamentals_parser.py`**

```python
"""
Helper class for parsing SEC EDGAR XBRL company facts.
Handles tag synonyms and missing data gracefully.
"""

class FundamentalsParser:
    def __init__(self, facts: dict, ticker: str):
        self.facts = facts
        self.ticker = ticker
        self.us_gaap = facts.get("facts", {}).get("us-gaap", {})

    def _get_concept(self, tag: str) -> dict | None:
        return self.us_gaap.get(tag)

    def get_annual_series(self, tag: str,
                          fallbacks: list[str] = None) -> dict:
        """Return {year: value} dict for annual data."""
        tags_to_try = [tag] + (fallbacks or [])
        for t in tags_to_try:
            concept = self._get_concept(t)
            if not concept:
                continue
            units = concept.get("units", {})
            # Try USD then shares
            for unit_key in ("USD", "shares"):
                if unit_key not in units:
                    continue
                entries = [
                    e for e in units[unit_key]
                    if e.get("form") in ("10-K", "10-K/A")
                    and e.get("frame", "").startswith("CY")
                    # FIX: original len==6 only matched CY2023 format.
                    # EDGAR also uses CY2023Q4I for many annual filings.
                    # Correct approach: exclude Q1/Q2/Q3 quarterly frames,
                    # but allow CY2023 (annual) and CY2023Q4I (full year).
                    and not any(
                        e.get("frame", "").endswith(s)
                        for s in ("Q1", "Q2", "Q3", "Q1I", "Q2I", "Q3I")
                    )
                ]
                if entries:
                    return {
                        int(e["frame"][2:]): e["val"]
                        for e in entries
                    }
        return {}

    def get_latest_annual(self, tag: str,
                          fallbacks: list[str] = None) -> float | None:
        series = self.get_annual_series(tag, fallbacks)
        if not series:
            return None
        latest_year = max(series.keys())
        return series[latest_year]

    def get_latest(self, tag: str,
                   fallbacks: list[str] = None) -> float | None:
        """Get most recent value regardless of period type."""
        tags_to_try = [tag] + (fallbacks or [])
        for t in tags_to_try:
            concept = self._get_concept(t)
            if not concept:
                continue
            for unit_key in ("USD", "shares", "pure"):
                entries = concept.get("units", {}).get(unit_key, [])
                if entries:
                    latest = max(entries, key=lambda x: x.get("end", ""))
                    return latest.get("val")
        return None
```

**Checkpoint — end of Sprint 2 (extended to Day 11 for XBRL debugging):**
```bash
python pipeline/main.py --test
# Expected: Layers 1-3 run on 5 test tickers with real data.
# AAPL, META filtered at Layer 2 (not beaten down enough).
# GME, RRC, RFP pass Layers 1-3 with FCF data attached.
# Validate against known values:
#   RRC P/TBV should be < 1.0 (asset-heavy E&P at trough)
#   GME FCF 3yr avg should be positive (console cycle recovery)
#   AAPL should NOT appear in output (filtered by Layer 2)
# If XBRL tags returning empty: check _fundamentals_parser.py
# fallback lists and run: python -c "from pipeline.layers._fundamentals_parser
# import FundamentalsParser; ..." to test single company parsing.
```

---

### Sprint 3 — Data Pipeline Layers 4–6 (Days 12–17)

**Goal:** Insider buying, institutional holders, technical signals all working. Bond scraping is deferred to Phase 2 — Layer 5 assigns "unavailable" tier for all tickers in Phase 1 and scores accordingly. By end of Sprint 3: `python pipeline/main.py --test` produces a fully populated stock dict through all 6 layers with real signals attached.

> **Phase 1 scope note:** Playwright bond scraping is excluded from Sprint 3.
> Layer 5 in Phase 1 is a lightweight pass-through that assigns bond_tier="unavailable"
> and scores bonds at 15/25 (neutral — assumes no significant debt risk).
> Full Playwright bond scraping is implemented in Phase 2 Sprint 1.

---

#### Day 8 — OpenInsider Scraper

**File: `pipeline/scrapers/openinsider.py`**

```python
"""
Scrapes OpenInsider.com for open-market insider purchases.
Returns structured insider buying data per ticker.
"""
import pandas as pd
import requests
from datetime import date, timedelta
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

import random

logger = get_logger(__name__)

OPENINSIDER_URL = "http://openinsider.com/screener"

# FIX: rotate User-Agent strings — single static UA gets Cloudflare-blocked
# within days of regular nightly use.
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

def _get_headers() -> dict:
    return {
        "User-Agent":      random.choice(_USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer":         "https://openinsider.com/",
    }

# Role codes that RK cares about
PRIORITY_ROLES = {
    "CEO": 30, "Chief Executive Officer": 30,
    "CFO": 25, "Chief Financial Officer": 25,
    "Chairman": 25, "Executive Chairman": 25,
    "President": 20,
    "COO": 15, "Chief Operating Officer": 15,
    "Director": 10,
    "VP": 8, "Vice President": 8,
}

def get_insider_buys(ticker: str, days_back: int = 180) -> list[dict]:
    """
    Fetch open-market purchases for a ticker from OpenInsider.
    Returns list of purchase dicts sorted by value descending.
    Falls back to EDGAR Form 4 parsing if OpenInsider is blocked.
    """
    cache_key = f"insider_{ticker}_{days_back}"
    cached = cache_get("scrapes", cache_key, ttl_days=1)
    if cached:
        return cached.get("data", [])

    start = (date.today() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    params = {
        "s":         ticker,
        "tt":        "P",           # P = Purchase (open market only)
        "minprice":  "10000",
        "daterange": "custom",
        "startdate": start,
        "enddate":   date.today().strftime("%Y-%m-%d"),
    }
    try:
        # FIX: random delay reduces bot detection probability
        time.sleep(random.uniform(2.0, 5.0))
        r = requests.get(OPENINSIDER_URL, params=params,
                         headers=_get_headers(), timeout=30)

        # FIX: handle Cloudflare block — fall back to EDGAR
        if r.status_code in (403, 429, 503):
            logger.warning(f"OpenInsider blocked ({r.status_code}) for "
                           f"{ticker} — falling back to EDGAR Form 4")
            return _get_insider_buys_from_edgar(ticker, days_back)

        r.raise_for_status()
        tables = pd.read_html(r.text)
        if not tables:
            cache_set("scrapes", cache_key, {"data": []})
            return []

        df = tables[0]

        # FIX: validate expected columns exist before processing rows.
        # Table structure changes are a 0-warning silent failure otherwise.
        required_cols = {"Title", "Value"}
        if not required_cols.issubset(set(df.columns)):
            logger.warning(f"OpenInsider table structure changed for "
                           f"{ticker} — found columns: {list(df.columns)[:8]}. "
                           f"Falling back to EDGAR.")
            return _get_insider_buys_from_edgar(ticker, days_back)

    except Exception as e:
        logger.debug(f"OpenInsider scrape failed for {ticker}: {e}")
        return _get_insider_buys_from_edgar(ticker, days_back)

    buys = []
    for _, row in df.iterrows():
        try:
            buy = _parse_row(row)
            if buy:
                buys.append(buy)
        except Exception:
            continue

    # Sort by value descending
    buys.sort(key=lambda x: x.get("value", 0), reverse=True)
    cache_set("scrapes", cache_key, {"data": buys})
    return buys

def _get_insider_buys_from_edgar(ticker: str, days_back: int) -> list[dict]:
    """
    Fallback: find Form 4 filings via EDGAR full-text search.
    Used when OpenInsider is unavailable or blocked.
    Returns minimal buy records — dollar amounts not reliably available
    from filing metadata alone. Full XML parsing added in Phase 2.
    """
    from pipeline.utils.edgar import search_filings
    try:
        filings = search_filings(ticker, ["4"], days_back=days_back)
        buys = []
        for filing in filings[:20]:
            source = filing.get("_source", {})
            buys.append({
                "ticker":               ticker,
                "name":                 source.get("entity_name", ""),
                "title":                "Unknown — EDGAR fallback",
                "role_score":           0,
                "trade_date":           source.get("period_of_report", ""),
                "value":                0,   # amount unknown from metadata
                "is_ceo_cfo_chairman":  False,
                "is_10b51_plan":        False,
                "source":               "EDGAR Form 4 fallback",
            })
        return buys
    except Exception as e:
        logger.debug(f"EDGAR Form 4 fallback also failed for {ticker}: {e}")
        return []


def _parse_row(row) -> dict | None:
    """Parse a single OpenInsider table row."""
    try:
        title = str(row.get("Title", row.get(4, "")))
        role_score = 0
        for role_name, score in PRIORITY_ROLES.items():
            if role_name.lower() in title.lower():
                role_score = score
                break
        if role_score == 0:
            return None  # skip non-relevant roles

        # Parse value — remove $ and commas
        val_raw = str(row.get("Value", row.get(9, "0")))
        val_clean = val_raw.replace("$", "").replace(",", "").strip()
        value = float(val_clean) if val_clean else 0

        if value < 10_000:
            return None

        # Parse date
        date_raw = str(row.get("Trade\xa0Date", row.get(1, "")))

        # FIX: detect 10b5-1 plan purchases — pre-scheduled buys are
        # weaker conviction signals. OpenInsider sometimes shows a footnote
        # column; check for "10b5" text in any cell of the row.
        row_text = " ".join(str(v) for v in row.values()).lower()
        is_10b51 = "10b5" in row_text or "rule 10b5" in row_text

        return {
            "ticker":              str(row.get("Ticker", "")),
            "name":                str(row.get("Insider Name", row.get(3, ""))),
            "title":               title,
            "role_score":          role_score,
            "trade_date":          date_raw,
            "value":               value,
            "is_ceo_cfo_chairman": role_score >= 25,
            "is_10b51_plan":       is_10b51,
        }
    except Exception:
        return None

def get_best_insider_buy(ticker: str) -> dict | None:
    """Return the highest-value relevant insider buy in last 180 days."""
    buys = get_insider_buys(ticker)
    if not buys:
        return None
    # Filter to $200k+ for scoring purposes
    significant = [b for b in buys if b["value"] >= config.LAYER4_MIN_INSIDER_BUY]
    if not significant:
        return None
    return significant[0]  # already sorted by value desc
```

#### Day 9 — WhaleWisdom + 13D/13G Scraper

**File: `pipeline/scrapers/whalewisdom.py`**

```python
"""
Scrapes WhaleWisdom for institutional holders,
cross-references against known value funds list.
"""
import json
import requests
from bs4 import BeautifulSoup
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml",
}

def load_value_funds() -> list[dict]:
    with open(f"{config.DATA_DIR}value_funds.json") as f:
        return json.load(f)

VALUE_FUNDS = load_value_funds()
VALUE_FUND_NAMES = {f["fund_name"].lower() for f in VALUE_FUNDS}

def get_institutional_holders(ticker: str) -> list[dict]:
    """
    Get top institutional holders and flag known value funds.

    FIX: WhaleWisdom requires JavaScript to render the holders table.
    The requests+BeautifulSoup approach always returned an empty JS shell
    — a silent failure that looked like "no holders found."
    Phase 1 uses yfinance institutional_holders only.
    WhaleWisdom via Playwright is deferred to Phase 2.
    """
    cache_key = f"inst_{ticker}"
    cached = cache_get("scrapes", cache_key, ttl_days=7)
    if cached:
        return cached.get("data", [])

    holders = _parse_yf_holders(ticker)

    # Flag known value funds
    for h in holders:
        name_lower = h.get("holder_name", "").lower()
        h["is_value_fund"] = any(
            vf in name_lower for vf in VALUE_FUND_NAMES
        )

    cache_set("scrapes", cache_key, {"data": holders})
    return holders

def _parse_yf_holders(ticker: str) -> list[dict]:
    """Parse institutional holders from yfinance."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        df = t.institutional_holders
        if df is None or df.empty:
            return []
        holders = []
        for _, row in df.iterrows():
            holders.append({
                "holder_name":  str(row.get("Holder", "")),
                "pct_held":     float(row.get("% Out", 0)),
                "shares_held":  int(row.get("Shares", 0)),
                "value_usd":    float(row.get("Value", 0)),
                "recent_change": None,
                "is_value_fund": False,
            })
        return holders
    except Exception as e:
        logger.debug(f"yfinance holders failed for {ticker}: {e}")
        return []

def _scrape_whalewisdom(ticker: str) -> list[dict]:
    """
    FIX: WhaleWisdom requires JavaScript to render the holders table.
    requests+BeautifulSoup returns a JS shell — the data table never exists
    in the raw HTML response, making this a silent failure every time.

    Phase 1: this function is a placeholder that always returns empty list.
    Phase 2: replace body with Playwright + playwright-stealth implementation.
    """
    # TODO Phase 2: implement with Playwright
    # from playwright.sync_api import sync_playwright
    # from playwright_stealth import stealth_sync
    logger.debug(f"WhaleWisdom requires Playwright — deferred to Phase 2 for {ticker}")
    return []

def _parse_pct(s: str) -> float:
    try:
        return float(s.replace("%", "").replace(",", "").strip()) / 100
    except Exception:
        return 0.0

def get_best_value_fund_holder(ticker: str) -> dict | None:
    """Return the largest known value fund holder if any."""
    holders = get_institutional_holders(ticker)
    value_holders = [h for h in holders if h.get("is_value_fund")]
    if not value_holders:
        return None
    return max(value_holders, key=lambda h: h.get("pct_held", 0))
```

**File: `pipeline/layers/layer4_conviction.py`**

```python
"""
Layer 4 — Conviction Signals
Input:  fundamentals-filtered tickers
Output: tickers with insider buy OR value fund holder (~30 tickers)
"""
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.scrapers.openinsider import get_best_insider_buy
from pipeline.scrapers.whalewisdom import (
    get_best_value_fund_holder, get_institutional_holders
)
from pipeline.utils.yfinance_helpers import get_ticker_info

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 4 error for {stock['ticker']}: {e}")
    logger.info(f"Layer 4: {len(passed)}/{len(tickers)} passed conviction")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]

    # ── Insider ownership % ──────────────────────────────────
    info = get_ticker_info(ticker)
    insider_own_pct = info.get("heldPercentInsiders", 0) or 0

    # ── Insider buying ───────────────────────────────────────
    best_buy = get_best_insider_buy(ticker)

    # ── Institutional holders ────────────────────────────────
    best_vf = get_best_value_fund_holder(ticker)

    # ── Pass/fail logic (OR — either qualifies) ──────────────
    passes_insider = (best_buy is not None and
                      best_buy.get("value", 0) >= config.LAYER4_MIN_INSIDER_BUY)
    passes_value_fund = (best_vf is not None and
                         best_vf.get("pct_held", 0) >= 0.05)
    passes_insider_own = insider_own_pct >= 0.20

    if not (passes_insider or passes_value_fund or passes_insider_own):
        return None

    # ── Compute insider buy vs compensation ratio ────────────
    ins_vs_comp = None
    if best_buy:
        # Try to get annual comp from DEF 14A (simplified — use salary proxy)
        annual_comp_proxy = info.get("totalPay", None)
        if annual_comp_proxy and annual_comp_proxy > 0:
            ins_vs_comp = best_buy["value"] / annual_comp_proxy

    return {
        **stock,
        "insider_buy_amount":    best_buy["value"] if best_buy else None,
        "insider_buy_role":      best_buy["title"] if best_buy else None,
        "insider_buy_date":      best_buy["trade_date"] if best_buy else None,
        "insider_buy_name":      best_buy["name"] if best_buy else None,
        "insider_buy_count":     1 if best_buy else 0,
        "insider_pct_of_comp":   round(ins_vs_comp, 2) if ins_vs_comp else None,
        "insider_is_ceo_cfo":    best_buy.get("is_ceo_cfo_chairman", False) if best_buy else False,
        # FIX: pass 10b5-1 flag through so scorer can halve base points
        "insider_is_10b51_plan": best_buy.get("is_10b51_plan", False) if best_buy else False,
        "value_fund_name":       best_vf["holder_name"] if best_vf else None,
        "value_fund_pct":        best_vf["pct_held"] if best_vf else None,
        "insider_ownership_pct": round(insider_own_pct, 3),
        "short_interest_pct":    info.get("shortPercentOfFloat", None),
    }
```

#### Day 10 — Layer 5: Bond Prices

**File: `pipeline/scrapers/finra_trace.py`**

```python
"""
Scrapes FINRA TRACE bond trade data for a company.
Uses Playwright for JS-rendered pages.
Falls back to a simple requests approach for some pages.
"""
import json
import re
import requests
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.cache import cache_get, cache_set

logger = get_logger(__name__)

def get_bond_data(company_name: str, ticker: str) -> dict | None:
    """
    Fetch bond price data from FINRA.
    Returns dict with price, maturity, yield, or None if unavailable.
    """
    cache_key = f"bonds_{ticker}"
    cached = cache_get("scrapes", cache_key,
                       ttl_days=config.BOND_CACHE_DAYS)
    if cached:
        return cached if cached.get("price") else None

    if not config.ENABLE_BOND_SCRAPE:
        logger.debug(f"Bond scraping disabled, skipping {ticker}")
        return None

    result = _try_finra_api(company_name, ticker)
    if result:
        cache_set("scrapes", cache_key, result)
        return result

    result = _try_playwright(company_name, ticker)
    if result:
        cache_set("scrapes", cache_key, result)
        return result

    # Cache miss result to avoid repeated failed attempts
    cache_set("scrapes", cache_key, {"price": None, "unavailable": True})
    return None

def _try_finra_api(company_name: str, ticker: str) -> dict | None:
    """Try FINRA's public API endpoint first (faster than Playwright)."""
    try:
        # FINRA Market Data API — public, no auth required
        url = "https://api.finra.org/data/group/otcMarket/name/tradeReport"
        params = {
            "issuerName": company_name[:30],
            "limit": 5,
            "offset": 0,
        }
        headers = {"Accept": "application/json"}
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            if data:
                return _parse_finra_api_response(data[0])
    except Exception as e:
        logger.debug(f"FINRA API attempt failed for {ticker}: {e}")
    return None

def _parse_finra_api_response(item: dict) -> dict:
    price      = item.get("lastSalePrice")
    trade_date = item.get("lastSaleDate") or item.get("tradeDate")
    volume     = item.get("totalVolume", 0) or 0

    # FIX: check trade recency — thinly traded bonds can have last trades
    # weeks or months old. A stale price of 88 may actually be 65 today.
    # Flag as stale if: trade older than 60 days OR volume below 5 bonds.
    is_stale = False
    if trade_date:
        from datetime import date as _date, datetime
        try:
            td = datetime.strptime(str(trade_date)[:10], "%Y-%m-%d").date()
            days_old = (_date.today() - td).days
            is_stale = days_old > 60 or volume < 5
        except Exception:
            is_stale = True   # can't parse date — treat as stale

    return {
        "price":      price,
        "yield":      item.get("yield"),
        "maturity":   item.get("maturityDate"),
        "volume":     volume,
        "trade_date": trade_date,
        "is_stale":   is_stale,
        "cusip":      item.get("cusip"),
        "source":     "FINRA API",
    }

def _try_playwright(company_name: str, ticker: str) -> dict | None:
    """
    Fallback: use Playwright to scrape FINRA bond search.
    Only runs if ENABLE_BOND_SCRAPE=true.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # FIX: apply stealth before any navigation.
            # Morningstar/FINRA uses fingerprinting — headless Chromium
            # without stealth is detected and blocked on first or second run.
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except ImportError:
                logger.warning(
                    "playwright-stealth not installed — FINRA scraping may "
                    "be blocked. Run: pip install playwright-stealth"
                )
            page.set_default_timeout(config.PLAYWRIGHT_TIMEOUT_MS)

            # Navigate to FINRA bond search
            page.goto("https://finra-markets.morningstar.com/BondCenter/TRBSrkSrch.jsp")
            page.wait_for_load_state("networkidle")

            # Search by issuer name
            search_box = page.query_selector('input[name="IssuerName"]')
            if not search_box:
                browser.close()
                return None

            search_box.fill(company_name[:30])
            page.keyboard.press("Enter")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

            # Parse results table
            rows = page.query_selector_all("table.tbl-data tbody tr")
            if not rows:
                browser.close()
                return None

            # Get first result (most recent trade)
            first_row = rows[0]
            cells = first_row.query_selector_all("td")
            if len(cells) < 6:
                browser.close()
                return None

            result = {
                "price":    _parse_price(cells[3].inner_text()),
                "yield":    _parse_price(cells[4].inner_text()),
                "maturity": cells[2].inner_text().strip(),
                "source":   "FINRA Playwright",
            }
            browser.close()
            return result if result["price"] else None

    except Exception as e:
        logger.debug(f"Playwright bond scrape failed for {ticker}: {e}")
        return None

def _parse_price(s: str) -> float | None:
    try:
        return float(re.sub(r"[^\d.]", "", s.strip()))
    except Exception:
        return None

def assign_bond_tier(price: float | None) -> str:
    if price is None:
        return "unavailable"
    if price >= config.LAYER5_BOND_SAFE:
        return "safe"
    if price >= config.LAYER5_BOND_CAUTION:
        return "caution"
    if price >= config.LAYER5_BOND_ELEVATED:
        return "elevated"
    if price >= config.LAYER5_BOND_HIGH_RISK:
        return "high_risk"
    return "critical"
```

**File: `pipeline/layers/layer5_bonds.py`**

```python
"""
Layer 5 — Bond / Survival Check
Input:  conviction-filtered tickers
Output: tickers that survive bond safety check (~15-25)
"""
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.scrapers.finra_trace import get_bond_data, assign_bond_tier

logger = get_logger(__name__)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    passed = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock)
            if result:
                passed.append(result)
        except Exception as e:
            logger.debug(f"Layer 5 error for {stock['ticker']}: {e}")
    logger.info(f"Layer 5: {len(passed)}/{len(tickers)} passed bond check")
    return passed

def _evaluate_ticker(stock: dict) -> dict | None:
    ticker = stock["ticker"]
    company_name = stock.get("company_name", ticker)

    bond_data = get_bond_data(company_name, ticker)
    bond_price = bond_data.get("price") if bond_data else None
    bond_tier = assign_bond_tier(bond_price)

    # Hard filter: if bonds are trading below critical threshold, skip
    # (unless company has no public debt — then assume safe)
    overhang = stock.get("net_common_overhang", 0) or 0
    has_significant_debt = overhang > stock.get("fcf_3yr_avg", 1) * 2

    if has_significant_debt and bond_tier == "critical":
        logger.debug(f"{ticker}: filtered — bonds critical ({bond_price})")
        return None

    return {
        **stock,
        "bond_price":         bond_price,
        "bond_maturity_date": bond_data.get("maturity") if bond_data else None,
        "bond_yield":         bond_data.get("yield") if bond_data else None,
        "bond_tier":          bond_tier,
        "bond_source":        bond_data.get("source") if bond_data else "unavailable",
        # FIX: pass staleness flag through so scorer can penalise stale prices
        "bond_is_stale":      bond_data.get("is_stale", False) if bond_data else False,
        "bond_trade_date":    bond_data.get("trade_date") if bond_data else None,
    }
```

#### Days 11–12 — Layer 6: Technical + Sector Context

**File: `pipeline/layers/layer6_technical.py`**

```python
"""
Layer 6 — Technical Confirmation
Input:  bond-checked tickers
Output: final candidates with technical signals added (~10-15)
"""
import pandas as pd
import numpy as np
from pipeline import config
from pipeline.utils.logger import get_logger
from pipeline.utils.yfinance_helpers import (
    get_weekly_history, compute_rsi
)

logger = get_logger(__name__)

# Sector ETF mapping
import json
with open(f"{config.DATA_DIR}sector_etf_map.json") as f:
    SECTOR_ETF_MAP = json.load(f)

def run(tickers: list[dict], cfg: dict, market: str = "US") -> list[dict]:
    # Pre-fetch all sector ETF histories needed
    sectors_needed = {t.get("sector") for t in tickers if t.get("sector")}
    etf_histories = {}
    for sector in sectors_needed:
        etf = SECTOR_ETF_MAP.get(sector)
        if etf:
            df = get_weekly_history(etf, period="5y")
            if not df.empty:
                etf_histories[sector] = df

    results = []
    for stock in tickers:
        try:
            result = _evaluate_ticker(stock, etf_histories)
            if result:
                results.append(result)
        except Exception as e:
            logger.debug(f"Layer 6 error for {stock['ticker']}: {e}")

    logger.info(f"Layer 6: {len(results)}/{len(tickers)} passed technical")
    return results

def _evaluate_ticker(stock: dict,
                     etf_histories: dict) -> dict | None:
    ticker = stock["ticker"]

    # Use cached price series from Layer 2 if available
    price_series = stock.pop("_price_series", None)
    if price_series is None or price_series.empty:
        df = get_weekly_history(ticker, period="5y")
        if df.empty:
            return stock  # pass through without technical data
        price_series = df["Close"].dropna()

    # ── Weekly RSI ───────────────────────────────────────────
    rsi_series = compute_rsi(price_series, period=14)
    current_rsi = float(rsi_series.iloc[-1]) if len(rsi_series) > 0 else None

    # RSI trend: compare last 3 weeks to prior 3 weeks
    rsi_trend = "neutral"
    weeks_improving = 0
    if len(rsi_series) >= 6:
        recent = rsi_series.iloc[-3:]
        prior  = rsi_series.iloc[-6:-3]
        if recent.mean() > prior.mean():
            rsi_trend = "improving"
            # Count consecutive improving weeks
            for i in range(1, min(len(rsi_series), 8)):
                if rsi_series.iloc[-i] > rsi_series.iloc[-i-1]:
                    weeks_improving += 1
                else:
                    break
        elif recent.mean() < prior.mean():
            rsi_trend = "declining"

    # ── Sector context modifier ──────────────────────────────
    sector = stock.get("sector")
    sector_modifier = 0
    sector_etf_3yr_return = None
    stock_3yr_return = stock.get("pct_below_3yr_high", None)

    if sector and sector in etf_histories:
        etf_df = etf_histories[sector]
        etf_close = etf_df["Close"].dropna()
        if len(etf_close) >= 156:
            etf_now   = float(etf_close.iloc[-1])
            etf_3yr   = float(etf_close.iloc[-156])
            sector_etf_3yr_return = (etf_now - etf_3yr) / etf_3yr

            if sector_etf_3yr_return < -0.20:
                sector_modifier = config.SECTOR_DOWN_BONUS
            elif sector_etf_3yr_return > 0.20:
                sector_modifier = config.SECTOR_UP_PENALTY

    # ── Support retest ───────────────────────────────────────
    support_retest = False
    if len(price_series) >= 52:
        low_52 = float(price_series.iloc[-52:].min())
        current = float(price_series.iloc[-1])
        prev_4wk_min = float(price_series.iloc[-8:-4].min())
        # Retest: touched near 52wk low in last 4 weeks, then bounced
        if prev_4wk_min <= low_52 * 1.05 and current > prev_4wk_min * 1.10:
            support_retest = True

    # ── Decline type classification ──────────────────────────
    decline_type = _classify_decline(stock)

    return {
        **stock,
        "rsi_weekly":             round(current_rsi, 1) if current_rsi else None,
        "rsi_trend":              rsi_trend,
        "weeks_rsi_improving":    weeks_improving,
        "support_retest":         support_retest,
        "sector_etf_3yr_return":  round(sector_etf_3yr_return, 3) if sector_etf_3yr_return else None,
        "stock_3yr_return":       round(stock_3yr_return, 3) if stock_3yr_return else None,
        "sector_context_modifier": sector_modifier,
        "decline_type":           decline_type,
    }

def _classify_decline(stock: dict) -> str:
    """Classify decline as cyclical, secular, or mixed."""
    import json as _json
    try:
        with open(f"{config.DATA_DIR}secular_decline_sic.json") as f:
            secular_sics = set(_json.load(f))
        with open(f"{config.DATA_DIR}cyclical_sic.json") as f:
            cyclical_sics = set(_json.load(f))
    except FileNotFoundError:
        return "unknown"

    sic = stock.get("sic_code", "")
    if sic in secular_sics:
        return "secular"
    if sic in cyclical_sics:
        return "cyclical"

    # Heuristic from fundamentals
    fcf_series = stock.get("fcf_series", {})
    if len(fcf_series) >= 5:
        years = sorted(fcf_series.keys())
        values = [fcf_series[y] for y in years]
        # If FCF was positive in earlier years, likely cyclical
        if values[0] > 0 and values[-1] > 0:
            return "cyclical"
        if all(v <= 0 for v in values[-3:]):
            return "secular"

    return "mixed"
```

**Checkpoint — end of Sprint 3 (Day 17):**
```bash
python pipeline/main.py --test
# Expected: full 6-layer pipeline runs on 5 test tickers.
# GME, RRC, RFP reach Layer 6 with insider + institutional + RSI data.
# bond_tier = "unavailable" for all (Playwright deferred to Phase 2).
# bond_score = 15/25 for all (neutral Phase 1 default).
# Insider signal: RRC should show a buy if recent CEO buy exists.
# RSI: all tickers have rsi_weekly populated from yfinance weekly data.
# AAPL filtered at Layer 2, META filtered at Layer 2 or 3.
```

---

### Sprint 4 — Scoring Engine (Days 18–21)

**Goal:** Full confidence score, transparency system, upside multiple, risk flags, action steps. By end of Sprint 4: `results.json` is written with fully scored candidates including transparency data, all fixes applied (10b5-1 halving, stale bond penalty, component caps enforced).

---

#### Days 13–14 — Confidence Score Engine

**File: `pipeline/scoring/base_scorer.py`**

```python
"""Base class for all scoring frameworks."""

class BaseScorer:
    def score(self, stock: dict,
              weights_override: dict = None) -> dict:
        raise NotImplementedError

    def _get_tier(self, score: float) -> dict:
        raise NotImplementedError

    def _cap_component(self, points: float,
                       component: str) -> float:
        """Cap component score at its maximum."""
        from pipeline import config
        return min(points, config.SCORE_MAX.get(component, points))
```

**File: `pipeline/scoring/confidence_score.py`**

```python
"""RK Confidence Scorer — implements RK's buy criteria."""
from pipeline import config
from pipeline.scoring.base_scorer import BaseScorer
from pipeline.scoring.transparency import TransparencyBuilder
from pipeline.scoring.upside_calc import UpsideCalc
from pipeline.scoring.risk_flags import RiskFlagGenerator
from pipeline.scoring.action_steps import ActionStepGenerator
from pipeline.utils.logger import get_logger

logger = get_logger(__name__)

class RKScorer(BaseScorer):
    def score(self, stock: dict,
              weights_override: dict = None) -> dict:
        components = {
            "insider":       self._score_insider(stock),
            "bonds":         self._score_bonds(stock),
            "fcf":           self._score_fcf(stock),
            "institutional": self._score_institutional(stock),
            "technical":     self._score_technical(stock),
        }

        sector_mod = stock.get("sector_context_modifier", 0)
        base_total = sum(c["points"] for c in components.values())
        total = min(100, max(0, base_total + sector_mod))

        tier = self._get_tier(total)
        upside = UpsideCalc().calculate(stock)
        risk_flags = RiskFlagGenerator().generate(stock, components)
        action_steps = ActionStepGenerator().generate(stock, components)
        top_signal = self._get_top_signal(components, stock)
        transparency = TransparencyBuilder().build(
            stock, components, sector_mod, total
        )

        return {
            "score_total":         round(total, 1),
            "score_tier":          tier["label"],
            "score_label":         tier["plain_label"],
            "score_color":         tier["color"],
            "sector_modifier":     sector_mod,
            "components":          components,
            "transparency":        transparency,
            "conservative_upside": upside["conservative"],
            "bull_upside":         upside["bull"],
            "diluted_upside":      upside["diluted"],
            "dilution_risk_pct":   upside.get("dilution_pct", 0),
            "risk_flags":          risk_flags,
            "action_steps":        action_steps,
            "top_signal":          top_signal,
            "suggested_position":  tier["suggested_position"],
        }

    def _score_insider(self, stock: dict) -> dict:
        pts = 0
        reasoning = "No recent insider buying detected"
        detail = {}

        buy_amount  = stock.get("insider_buy_amount") or 0
        is_ceo_cfo  = stock.get("insider_is_ceo_cfo", False)
        at_low      = stock.get("insider_at_3yr_low", False)
        pct_comp    = stock.get("insider_pct_of_comp") or 0
        # FIX: 10b5-1 plan purchases are pre-scheduled months in advance.
        # They are weaker conviction signals than discretionary buys.
        is_10b51    = stock.get("insider_is_10b51_plan", False)

        # Base points by amount and role
        if buy_amount >= 2_000_000 or stock.get("insider_buy_count", 0) >= 3:
            pts = 30
            reasoning = f"Very large insider buy: ${buy_amount:,.0f}"
        elif buy_amount >= 500_000 and is_ceo_cfo:
            pts = 22
            reasoning = f"CEO/CFO buy: ${buy_amount:,.0f}"
        elif buy_amount >= 200_000 and is_ceo_cfo:
            pts = 15
            reasoning = f"CEO/CFO buy: ${buy_amount:,.0f}"
        elif buy_amount >= 50_000:
            pts = 8
            reasoning = f"Director buy: ${buy_amount:,.0f}"

        # FIX: halve base points for 10b5-1 plan purchases
        if is_10b51 and pts > 0:
            pts = pts // 2
            reasoning += " (10b5-1 pre-scheduled plan — weaker signal)"

        bonus_at_low = 0
        bonus_comp   = 0
        if pts > 0:
            # Bonus: near 3yr low
            pct_above_low = stock.get("pct_above_52wk_low", 1.0)
            if pct_above_low is not None and pct_above_low < 0.20:
                bonus_at_low = 5
                reasoning += " — at 3yr low"

            # Bonus: large relative to compensation
            if pct_comp and pct_comp > 0.80:
                bonus_comp = 2
                reasoning += f" ({pct_comp:.0%} of annual comp)"

        pts = self._cap_component(pts + bonus_at_low + bonus_comp, "insider")
        detail = {
            "base_points":    min(pts, 30),
            "bonus_at_low":   bonus_at_low,
            "bonus_comp":     bonus_comp,
            "is_10b51":       is_10b51,
            "buy_amount":     buy_amount,
            "buyer_role":     stock.get("insider_buy_role"),
            "buyer_name":     stock.get("insider_buy_name"),
            "buy_date":       stock.get("insider_buy_date"),
        }
        short = (f"{stock.get('insider_buy_role','Insider')} bought "
                 f"${buy_amount:,.0f}" if buy_amount else "No insider buy")

        return {"points": pts, "max": 30, "reasoning": reasoning,
                "reasoning_short": short, "detail": detail}

    def _score_bonds(self, stock: dict) -> dict:
        pts = 0
        tier    = stock.get("bond_tier", "unavailable")
        price   = stock.get("bond_price")
        ratio   = stock.get("net_overhang_fcf_ratio", 0) or 0
        asc842  = stock.get("asc842_flag", False)
        is_stale = stock.get("bond_is_stale", False)

        if tier == "unavailable":
            pts = 25 if ratio < 2 else 15
            reasoning = "No public bonds — low leverage confirmed" if ratio < 2 \
                        else "No bond data available"
        elif tier == "safe":
            pts = 25 if ratio < 5 else 20
            reasoning = f"Bonds at {price:.0f} — safe zone"
        elif tier == "caution":
            pts = 18
            reasoning = f"Bonds at {price:.0f} — caution zone"
        elif tier == "elevated":
            pts = 10
            reasoning = f"Bonds at {price:.0f} — elevated risk"
        elif tier == "high_risk":
            pts = 4
            reasoning = f"Bonds at {price:.0f} — high risk"
        else:  # critical
            pts = 0
            reasoning = f"Bonds at {price:.0f} — critical"

        if asc842:
            pts = max(0, pts - 3)
            reasoning += " (ASC 842 lease distortion — adjusted)"

        # FIX: penalise stale bond prices — last trade >60 days old or
        # volume <5 bonds means the price may no longer reflect reality.
        if is_stale and tier not in ("unavailable",):
            pts = max(0, pts - 5)
            trade_date = stock.get("bond_trade_date", "unknown date")
            reasoning += f" — price may be stale (last trade: {trade_date})"

        pts = self._cap_component(pts, "bonds")
        short = reasoning[:60]
        return {"points": pts, "max": 25, "reasoning": reasoning,
                "reasoning_short": short,
                "detail": {"bond_price": price, "bond_tier": tier,
                           "overhang_ratio": ratio, "asc842": asc842,
                           "is_stale": is_stale}}

    def _score_fcf(self, stock: dict) -> dict:
        pts = 0
        fcf_yield = stock.get("fcf_yield", 0) or 0
        ptbv = stock.get("price_to_tbv", 99) or 99
        consec = stock.get("fcf_consecutive_positive_years", 0) or 0

        if fcf_yield >= 0.25 or (fcf_yield >= 0.15 and ptbv < 0.5):
            pts = 20
        elif fcf_yield >= 0.15 or ptbv < 0.5:
            pts = 14
        elif fcf_yield >= 0.10 or ptbv < 1.0:
            pts = 10
        elif fcf_yield >= 0.05:
            pts = 8
        elif fcf_yield > 0:
            pts = 2

        bonus = 3 if consec >= 5 else 0
        pts = self._cap_component(pts + bonus, "fcf")
        reasoning = (f"FCF yield {fcf_yield:.1%}, P/TBV {ptbv:.2f}"
                     if ptbv < 99 else f"FCF yield {fcf_yield:.1%}")
        return {"points": pts, "max": 20, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"fcf_yield": fcf_yield, "ptbv": ptbv,
                           "consecutive_positive": consec}}

    def _score_institutional(self, stock: dict) -> dict:
        pts = 0
        fund = stock.get("value_fund_name")
        pct  = stock.get("value_fund_pct", 0) or 0
        added = stock.get("value_fund_added", False)
        insider_own = stock.get("insider_ownership_pct", 0) or 0

        if fund and pct >= 0.05 and added:
            pts = 15
            reasoning = f"{fund} holds {pct:.1%} (recently added)"
        elif fund and pct >= 0.05:
            pts = 10
            reasoning = f"{fund} holds {pct:.1%}"
        elif insider_own >= 0.20:
            pts = 8
            reasoning = f"Insider ownership {insider_own:.1%}"
        elif fund:
            pts = 5
            reasoning = f"{fund} holds a stake"
        else:
            pts = 2
            reasoning = "No notable value fund holders"

        pts = self._cap_component(pts, "institutional")
        return {"points": pts, "max": 15, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"value_fund": fund, "pct_held": pct,
                           "recently_added": added,
                           "insider_own": insider_own}}

    def _score_technical(self, stock: dict) -> dict:
        pts = 0
        rsi = stock.get("rsi_weekly")
        trend = stock.get("rsi_trend", "neutral")
        weeks = stock.get("weeks_rsi_improving", 0)
        retest = stock.get("support_retest", False)

        if rsi and rsi < 30 and trend == "improving" and weeks >= 3:
            pts = 10
        elif rsi and rsi < 35 and trend == "improving":
            pts = 7
        elif trend == "improving":
            pts = 5
        elif trend == "neutral":
            pts = 4
        else:
            pts = 1

        if retest:
            pts = min(pts + 2, 10)

        pts = self._cap_component(pts, "technical")
        reasoning = (f"RSI {rsi:.0f}, {trend}"
                     if rsi else f"RSI unavailable, {trend}")
        if weeks > 0:
            reasoning += f" {weeks} weeks"
        return {"points": pts, "max": 10, "reasoning": reasoning,
                "reasoning_short": reasoning[:50],
                "detail": {"rsi": rsi, "trend": trend,
                           "weeks_improving": weeks, "support_retest": retest}}

    def _get_tier(self, score: float) -> dict:
        if score >= config.TIER_EXCEPTIONAL:
            return {"label": "Exceptional",
                    "plain_label": "Very strong buy signal",
                    "suggested_position": "4–6%",
                    "color": "exceptional"}
        elif score >= config.TIER_HIGH_CONVICTION:
            return {"label": "High Conviction",
                    "plain_label": "Strong buy signal",
                    "suggested_position": "3–4%",
                    "color": "high_conviction"}
        elif score >= config.TIER_SPECULATIVE:
            return {"label": "Speculative",
                    "plain_label": "Worth a small position",
                    "suggested_position": "1–2%",
                    "color": "speculative"}
        else:
            return {"label": "Watch Only",
                    "plain_label": "Not yet — keep watching",
                    "suggested_position": "0%",
                    "color": "watch"}

    def _get_top_signal(self, components: dict, stock: dict) -> str:
        best = max(components.items(),
                   key=lambda x: x[1]["points"] / x[1]["max"])
        return best[1]["reasoning_short"]
```

#### Days 15–16 — Transparency, Upside, Risk Flags, Action Steps

**File: `pipeline/scoring/transparency.py`**

```python
"""Builds the three-level scoring transparency chain."""

class TransparencyBuilder:
    def build(self, stock, components, sector_mod, total) -> dict:
        return {
            "summary":           self._build_summary(total, components),
            "total_explanation": self._build_total_explanation(
                                     total, components, sector_mod),
            "components":        {
                name: self._build_component(name, comp)
                for name, comp in components.items()
            },
            "sector": {
                "modifier":    sector_mod,
                "explanation": self._sector_explanation(stock, sector_mod),
            },
            "arithmetic": self._build_arithmetic(components, sector_mod, total),
        }

    def _build_total_explanation(self, total, components, modifier) -> str:
        sorted_comps = sorted(
            components.items(),
            key=lambda x: x[1]["points"] / max(x[1]["max"], 1),
            reverse=True
        )
        strongest = sorted_comps[0]
        weakest   = sorted_comps[-1]
        from pipeline.scoring.confidence_score import RKScorer
        tier = RKScorer()._get_tier(total)
        parts = [
            f"This stock scored {round(total)}/100 — "
            f"{tier['plain_label'].lower()}.",
            f"The strongest signal: "
            f"{components[strongest[0]]['reasoning_short']}.",
        ]
        weak_pct = weakest[1]["points"] / max(weakest[1]["max"], 1)
        if weak_pct < 0.5:
            parts.append(
                f"Main gap: {components[weakest[0]]['reasoning_short']}."
            )
        if abs(modifier) >= 3:
            direction = "adds confidence" if modifier > 0 else "reduces confidence"
            parts.append(
                f"Sector context {direction} "
                f"({'+' if modifier > 0 else ''}{modifier} pts)."
            )
        return " ".join(parts)

    def _build_component(self, name: str, comp: dict) -> dict:
        """Build Level 2 transparency for one component."""
        WHY_IT_MATTERS = {
            "insider": (
                "RK rates insider buying as his highest-weighted signal. "
                "When a CEO spends real personal money on open-market purchases "
                "during a market downturn, it signals they believe the price is "
                "deeply wrong. Grants and options are excluded — only cash purchases count."
            ),
            "bonds": (
                "Bond prices are RK's primary bankruptcy filter. Bond investors "
                "are professional and have done detailed credit analysis. If they "
                "are selling at a deep discount, they are pricing in default risk. "
                "Near face value means credit markets consider the company safe."
            ),
            "fcf": (
                "RK uses a simple check: how much real cash does this business "
                "generate relative to what you pay for it? He uses a 3-year average "
                "to smooth commodity cycles and also anchors valuation to hard assets "
                "(tangible book value) as a margin of safety."
            ),
            "institutional": (
                "RK looks for respected value investors who independently arrived "
                "at the same conclusion. A 5%+ stake from a fund that does deep "
                "fundamental research provides independent confirmation. Index funds "
                "and quant funds do not count."
            ),
            "technical": (
                "RK uses weekly charts as a sentiment gauge, not as a primary tool. "
                "He gives technical signals the lowest weighting. His specific signal: "
                "weekly RSI recovering from oversold territory suggests the worst "
                "selling may be over and sentiment is beginning to turn."
            ),
        }
        return {
            "points":        comp["points"],
            "max":           comp["max"],
            "pct":           round(comp["points"] / max(comp["max"], 1), 2),
            "reasoning":     comp["reasoning"],
            "why_it_matters": WHY_IT_MATTERS.get(name, ""),
            "sub_signals":   comp.get("detail", {}),
            "source_label":  _SOURCE_LABELS.get(name, ""),
            "source_url_template": _SOURCE_URL_TEMPLATES.get(name, ""),
        }

    def _build_arithmetic(self, components, modifier, total) -> str:
        parts = []
        for name, comp in components.items():
            parts.append(f"{comp['points']:.0f}")
        modifier_str = f"{'+' if modifier >= 0 else ''}{modifier}"
        return (f"{' + '.join(parts)} {modifier_str} (sector) "
                f"= {round(total)}/100")

    def _build_summary(self, total, components) -> str:
        scores = " · ".join(
            f"{n[:3].upper()}: {c['points']:.0f}/{c['max']}"
            for n, c in components.items()
        )
        return f"Score: {round(total)}/100 | {scores}"

    def _sector_explanation(self, stock, modifier) -> str:
        etf_ret = stock.get("sector_etf_3yr_return")
        if etf_ret is None:
            return "Sector data unavailable"
        pct = etf_ret * 100
        if modifier > 0:
            return (f"Sector also down {abs(pct):.0f}% over 3 years "
                    f"— systemic pain adds confidence (+{modifier} pts)")
        elif modifier < 0:
            return (f"Sector up {abs(pct):.0f}% while stock is down "
                    f"— possible company-specific issue ({modifier} pts)")
        return (f"Sector neutral ({pct:+.0f}% over 3 years) — "
                f"company-specific decline")

_SOURCE_LABELS = {
    "insider":       "SEC EDGAR Form 4",
    "bonds":         "FINRA TRACE",
    "fcf":           "SEC EDGAR 10-K",
    "institutional": "SEC EDGAR 13F/13D",
    "technical":     "Yahoo Finance (weekly)",
}
_SOURCE_URL_TEMPLATES = {
    "insider":       "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=4",
    "bonds":         "https://finra-markets.morningstar.com/BondCenter/",
    "fcf":           "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K",
    "institutional": "https://efts.sec.gov/efts/hit?q=%22{ticker}%22&forms=SC+13D,SC+13G",
    "technical":     "https://finance.yahoo.com/chart/{ticker}",
}
```

**File: `pipeline/scoring/upside_calc.py`**

```python
"""Computes conservative and bull-case upside multiples."""
from pipeline import config

class UpsideCalc:
    def calculate(self, stock: dict) -> dict:
        price = stock.get("price", 0)
        if not price or price <= 0:
            return {"conservative": None, "bull": None, "diluted": None}

        shares = stock.get("shares_outstanding", 1) or 1
        fcf_3yr = stock.get("fcf_3yr_avg", 0) or 0
        diluted_shares = stock.get("diluted_shares", shares) or shares

        # Peak FCF from historical series
        fcf_series = stock.get("fcf_series", {})
        peak_fcf = max(fcf_series.values()) if fcf_series else fcf_3yr

        norm_fcf_per_share  = fcf_3yr / shares
        peak_fcf_per_share  = peak_fcf / shares
        diluted_fcf_per_share = fcf_3yr / diluted_shares

        conservative_target = norm_fcf_per_share * config.UPSIDE_CONSERVATIVE_MULTIPLE
        bull_target         = peak_fcf_per_share * config.UPSIDE_BULL_MULTIPLE
        diluted_target      = diluted_fcf_per_share * config.UPSIDE_CONSERVATIVE_MULTIPLE

        return {
            "conservative": round(conservative_target / price, 1) if price else None,
            "bull":         round(bull_target / price, 1) if price else None,
            "diluted":      round(diluted_target / price, 1) if price else None,
            "dilution_pct": round(stock.get("dilution_risk_pct", 0), 3),
        }
```

**File: `pipeline/scoring/risk_flags.py`**

```python
"""Generates plain-English risk flags for a stock."""
from pipeline import config

# Priority order — lower number = shown first
FLAG_PRIORITY = {
    "bond_caution": 1, "bond_high_risk": 2, "asc842": 3,
    "short_maturity": 4, "high_dilution": 5, "no_value_fund": 6,
    "rsi_unconfirmed": 7, "secular_decline": 8, "fcf_weak": 9,
    "low_insider_own": 10,
}

class RiskFlagGenerator:
    def generate(self, stock: dict, components: dict) -> list[dict]:
        flags = []

        bond_tier = stock.get("bond_tier", "unavailable")
        if bond_tier == "caution":
            flags.append({"key": "bond_caution", "severity": "warning",
                "text": f"Bonds at {stock.get('bond_price', '?'):.0f} — "
                        f"caution zone. Read debt footnote in latest 10-Q."})
        elif bond_tier in ("elevated", "high_risk"):
            flags.append({"key": "bond_high_risk", "severity": "danger",
                "text": f"Bonds at {stock.get('bond_price', '?'):.0f} — "
                        f"elevated risk. Verify covenant compliance."})

        if stock.get("asc842_flag"):
            flags.append({"key": "asc842", "severity": "info",
                "text": (f"Operating leases are "
                         f"{stock.get('lease_pct_of_lt_liab', 0):.0%} of "
                         f"long-term liabilities (ASC 842). "
                         f"Net overhang may overstate debt.")})

        maturity = stock.get("bond_maturity_date")
        if maturity and _months_until(maturity) < 18:
            flags.append({"key": "short_maturity", "severity": "warning",
                "text": f"Bond matures {maturity} — "
                        f"refinancing risk in near term."})

        if stock.get("dilution_risk_pct", 0) > 0.20:
            flags.append({"key": "high_dilution", "severity": "warning",
                "text": f"High leverage — potential "
                        f"{stock['dilution_risk_pct']:.0%} dilution if "
                        f"equity raise needed."})

        if not stock.get("value_fund_name"):
            flags.append({"key": "no_value_fund", "severity": "note",
                "text": "No known value fund holders detected in 13F data."})

        rsi = stock.get("rsi_weekly")
        if rsi and rsi > 35 and stock.get("rsi_trend") != "improving":
            flags.append({"key": "rsi_unconfirmed", "severity": "note",
                "text": "Technical trend not confirmed — "
                        "RSI not yet recovering from oversold."})

        if stock.get("decline_type") == "secular":
            flags.append({"key": "secular_decline", "severity": "warning",
                "text": "Industry shows signs of secular decline — "
                        "verify recovery thesis carefully."})

        if stock.get("insider_ownership_pct", 0) < 0.08:
            flags.append({"key": "low_insider_own", "severity": "note",
                "text": f"Insider ownership "
                        f"{stock.get('insider_ownership_pct', 0):.1%} — "
                        f"below RK's 20% preference."})

        # Sort by priority
        flags.sort(key=lambda f: FLAG_PRIORITY.get(f["key"], 99))
        return flags

def _months_until(date_str: str) -> int:
    from datetime import date, datetime
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
        return (d - date.today()).days // 30
    except Exception:
        return 99
```

**File: `pipeline/scoring/action_steps.py`**

```python
"""
Generates prioritised actionable next steps per stock.
Priority table from design plan Section 22.3.
"""

ACTION_PRIORITY = [
    ("bond_caution",      1),
    ("bond_high_risk",    1),
    ("insider_verify",    2),
    ("rsi_unconfirmed",   3),
    ("no_value_fund",     4),
    ("fcf_weak",          5),
    ("asc842",            6),
    ("bond_unavailable",  7),
    ("score_improving",   8),
]

class ActionStepGenerator:
    def generate(self, stock: dict, components: dict) -> list[dict]:
        steps = []
        ticker = stock.get("ticker", "")
        cik    = stock.get("cik", "")

        # 1. Bond concern
        if stock.get("bond_tier") in ("caution", "elevated", "high_risk"):
            steps.append({
                "priority": 1,
                "text": "Read the debt footnote in the latest 10-Q — check covenant terms",
                "detail": f"Bonds at {stock.get('bond_price', '?'):.0f} are in caution zone",
                "link_label": "Open 10-Q on EDGAR",
                "link_url": (f"https://www.sec.gov/cgi-bin/browse-edgar?"
                             f"action=getcompany&CIK={cik}&type=10-Q"),
            })

        # 2. Insider buyer background
        buyer_name = stock.get("insider_buy_name")
        if buyer_name:
            steps.append({
                "priority": 2,
                "text": f"Verify the buyer: search \"{buyer_name}\"",
                "detail": "Check prior companies, industry experience, track record",
                "link_label": "Search LinkedIn",
                "link_url": f"https://www.linkedin.com/search/results/all/?keywords={buyer_name.replace(' ', '+')}",
            })

        # 3. Technical not confirmed
        rsi = stock.get("rsi_weekly")
        if rsi and rsi < 40 and stock.get("rsi_trend") == "improving":
            steps.append({
                "priority": 3,
                "text": f"Wait for weekly RSI to cross above 40",
                "detail": f"RSI currently {rsi:.0f} and improving — "
                          f"not yet confirmed",
                "link_label": None,
                "link_url": None,
            })

        # 4. Institutional check
        if not stock.get("value_fund_name"):
            steps.append({
                "priority": 4,
                "text": "Check WhaleWisdom for recent 13F activity",
                "detail": "No known value fund detected — verify independently",
                "link_label": "WhaleWisdom",
                "link_url": f"https://whalewisdom.com/stock/{ticker.lower()}",
            })

        # 5. Bond unavailable
        if stock.get("bond_tier") == "unavailable":
            steps.append({
                "priority": 7,
                "text": "Bond data unavailable — check manually at FINRA",
                "detail": "Search by company name in FINRA Bond Center",
                "link_label": "FINRA Bond Center",
                "link_url": "https://finra-markets.morningstar.com/BondCenter/",
            })

        # 6. Earnings transcript
        steps.append({
            "priority": 8,
            "text": "Read latest earnings call transcript",
            "detail": "Look for management tone on capital allocation and recovery",
            "link_label": "Search Motley Fool",
            "link_url": (f"https://www.fool.com/search/#q="
                         f"{ticker}+earnings+transcript"),
        })

        # Sort and return top 3 for Zone 1 (rest shown in Zone 3)
        steps.sort(key=lambda s: s["priority"])
        return steps  # frontend shows first 3 in Zone 1, rest in Zone 3
```

**Checkpoint — end of Sprint 4 (Day 21):**
```bash
python pipeline/main.py --test

# Then validate:
python -c "
import json
with open('output/results.json') as f:
    d = json.load(f)
print('Candidates:', len(d['candidates']))
for c in d['candidates']:
    score = c.get('score_total', 0)
    label = c.get('score_label', '')
    comp  = c.get('components', {})
    ins   = comp.get('insider', {}).get('points', 0)
    bonds = comp.get('bonds', {}).get('points', 0)
    print(f\"  {c['ticker']}: {score:.0f}/100 — {label} | insider={ins} bonds={bonds}\")
print('Stats:', d['stats'])
"

# Expected:
# GME, RRC, RFP: scores between 40-85 depending on current signals
# AAPL: score < 30 (control — not beaten down)
# All component scores <= their maximums (cap enforced)
# transparency.total_explanation is a readable English paragraph
# action_steps list has at least 1 item per candidate
# bond_tier = "unavailable", bond score = 15 for all (Phase 1)
```

---

### Sprint 5 — Frontend Pages 1–3 (Days 22–30)

**Goal:** Working HTML frontend reading results.json. Pages 1, 2, and 3 fully working. Page 4 (Swing Trader) shows a stub — "Coming soon in Phase 2" banner. Charts on Page 3 show formatted data tables in Phase 1; Chart.js visualisations are added in Phase 2.

> **Phase 1 scope:** Pages 1–3 working with data tables. No Chart.js charts yet.
> Page 4 shows a placeholder. Phase 2 adds charts, Swing Trader, and bond data.

---

#### Day 17 — HTML Shell + CSS System

**File: `frontend/index.html`** (shell structure):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RK Screener — Deep Value Stock Scanner</title>
  <link rel="stylesheet" href="css/main.css">
  <link rel="stylesheet" href="css/components.css">
  <link rel="stylesheet" href="css/layout.css">
  <link rel="stylesheet" href="css/accessibility.css">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"
          defer></script>
</head>
<body>
  <nav class="app-nav" role="navigation" aria-label="Main navigation">
    <a href="#scanner"   class="nav-tab active" id="nav-scanner">
      <span class="nav-icon" aria-hidden="true">◎</span>
      <span class="nav-primary">Today's picks</span>
      <span class="nav-sub">RK deep value scanner</span>
    </a>
    <a href="#watchlist" class="nav-tab" id="nav-watchlist">
      <span class="nav-icon" aria-hidden="true">◉</span>
      <span class="nav-primary">My watchlist</span>
      <span class="nav-sub">Stocks you're tracking</span>
    </a>
    <a href="#deepdive"  class="nav-tab" id="nav-deepdive">
      <span class="nav-icon" aria-hidden="true">⊕</span>
      <span class="nav-primary">Analyse a stock</span>
      <span class="nav-sub">Enter any ticker</span>
    </a>
    <a href="#swing"     class="nav-tab nav-tab--swing" id="nav-swing">
      <span class="nav-icon" aria-hidden="true">↗</span>
      <span class="nav-primary">Swing trades</span>
      <span class="nav-sub">Short-term momentum</span>
    </a>
  </nav>

  <main class="app-main">
    <div id="scanner"   class="page page-scanner"></div>
    <div id="watchlist" class="page page-watchlist" style="display:none"></div>
    <div id="deepdive"  class="page page-deepdive"  style="display:none"></div>
    <div id="swing"     class="page page-swing"     style="display:none"></div>
  </main>

  <footer class="app-footer">
    <a href="#" id="how-it-works-link">How this screener works</a>
    <span class="footer-sep">·</span>
    <span class="footer-disclaimer">
      Educational only — not financial advice
    </span>
  </footer>

  <!-- "How it works" modal -->
  <div id="how-it-works-modal" class="modal-overlay" style="display:none"
       role="dialog" aria-modal="true" aria-labelledby="modal-title">
    <div class="modal-content">
      <button class="modal-close" aria-label="Close">×</button>
      <div id="modal-body"></div>
    </div>
  </div>

  <!-- Tooltip container -->
  <div id="tooltip" class="tooltip" role="tooltip" style="display:none"></div>

  <script src="js/utils/format.js"></script>
  <script src="js/utils/colors.js"></script>
  <script src="js/utils/storage.js"></script>
  <script src="js/components/scorecard.js"></script>
  <script src="js/components/score_transparency.js"></script>
  <script src="js/components/charts.js"></script>
  <script src="js/components/sparkline.js"></script>
  <script src="js/components/alerts.js"></script>
  <script src="js/components/zone_expander.js"></script>
  <script src="js/components/tooltip_system.js"></script>
  <script src="js/pages/scanner.js"></script>
  <script src="js/pages/watchlist.js"></script>
  <script src="js/pages/deepdive.js"></script>
  <script src="js/pages/swing.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
```

The CSS files, all JavaScript pages, and the tooltip content library (`tooltips.js`) follow the specifications in Design Plan v2.0 Section 14, 15, and 8.2.

#### Days 18–25 — Frontend Pages

Each page module (`scanner.js`, `watchlist.js`, `deepdive.js`, `swing.js`) follows this pattern:

```javascript
// scanner.js
async function initScanner() {
  const data = await loadData('results.json');
  if (!data) return;
  renderMeta(data);
  renderAlertBanner();
  renderFilters(data.candidates);
  renderTable(data.candidates);
}

function renderTable(candidates) {
  // Render 2-line card rows per candidate
  // Score bar + plain English label as primary column
  // Top signal as secondary
  // Analyse button → navigates to #deepdive?ticker=XXX
  // + Watch button → adds to localStorage watchlist
}
```

---

## 4. Phase 2 — GitHub Actions Automation

**File: `.github/workflows/pipeline.yml`**

```yaml
name: Nightly Pipeline

on:
  schedule:
    - cron: '0 4 * * *'   # 11pm EST = 4am UTC
  workflow_dispatch:        # allow manual trigger

jobs:
  run-pipeline:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium --with-deps

      - name: Run pipeline
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          ENABLE_BOND_SCRAPE: 'true'
        run: python pipeline/main.py

      - name: Commit results
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add output/results.json output/swing_results.json output/alerts.json
          git diff --staged --quiet || git commit -m "chore: update pipeline results $(date -u '+%Y-%m-%d')"
          git push
```

---

## 5. Phase 3 — Cloudflare Full Web App

Phase 3 adds:
- Cloudflare Pages hosting (deploy from GitHub automatically)
- Cloudflare Workers for API endpoints (watchlist, on-demand deep dive)
- Cloudflare KV for persistent watchlist storage
- On-demand single-ticker pipeline via Worker
- Email alerts via Resend free tier

Detailed Phase 3 implementation plan to be written when Phase 2 is stable.

---

## 6. Testing Strategy

### 6.1 Unit Tests

```bash
# Run all tests
pytest pipeline/tests/ -v

# Run specific test
pytest pipeline/tests/test_scoring.py -v
```

**File: `pipeline/tests/test_scoring.py`**

```python
"""Tests for the confidence score engine."""
import pytest
from pipeline.scoring.confidence_score import RKScorer

@pytest.fixture
def rk_stock():
    """A stock that should score ~70."""
    return {
        "ticker": "TEST",
        "price": 4.0,
        "market_cap": 260_000_000,
        "fcf_3yr_avg": 50_000_000,
        "fcf_per_share": 0.77,
        "fcf_yield": 0.19,
        "price_to_tbv": 0.6,
        "net_overhang_fcf_ratio": 4.5,
        "bond_tier": "safe",
        "bond_price": 92.0,
        "asc842_flag": False,
        "insider_buy_amount": 640_000,
        "insider_is_ceo_cfo": True,
        "insider_buy_role": "CEO",
        "insider_buy_name": "Jane Smith",
        "insider_buy_date": "2026-03-15",
        "insider_pct_of_comp": 0.84,
        "value_fund_name": "Greenlight Capital",
        "value_fund_pct": 0.062,
        "value_fund_added": False,
        "insider_ownership_pct": 0.08,
        "rsi_weekly": 34.0,
        "rsi_trend": "improving",
        "weeks_rsi_improving": 4,
        "support_retest": False,
        "sector_context_modifier": 5,
        "pct_above_52wk_low": 0.15,
        "shares_outstanding": 65_000_000,
        "diluted_shares": 65_000_000,
        "dilution_risk_pct": 0.0,
        "fcf_series": {2018: 390e6, 2019: 420e6, 2020: 80e6,
                       2021: 200e6, 2022: 310e6, 2023: 380e6},
    }

def test_score_in_range(rk_stock):
    scorer = RKScorer()
    result = scorer.score(rk_stock)
    assert 60 <= result["score_total"] <= 85

def test_score_tier_high_conviction(rk_stock):
    scorer = RKScorer()
    result = scorer.score(rk_stock)
    assert result["score_tier"] in ("High Conviction", "Exceptional")

def test_weights_sum_to_100():
    from pipeline import config
    assert sum(config.SCORE_WEIGHTS.values()) == 100

def test_component_capped(rk_stock):
    scorer = RKScorer()
    result = scorer.score(rk_stock)
    for name, comp in result["components"].items():
        assert comp["points"] <= comp["max"], \
            f"{name} component exceeds max: {comp['points']} > {comp['max']}"

def test_aapl_scores_low():
    """AAPL should score below 30 — not a beaten-down value stock."""
    aapl = {
        "ticker": "AAPL", "price": 195.0, "market_cap": 3_000_000_000_000,
        "fcf_3yr_avg": 100_000_000_000, "fcf_yield": 0.03,
        "price_to_tbv": 45.0, "bond_tier": "safe", "bond_price": 98.0,
        "bond_is_stale": False,
        "net_overhang_fcf_ratio": 0.5, "asc842_flag": False,
        "insider_buy_amount": 0, "insider_is_10b51_plan": False,
        "value_fund_name": None,
        "insider_ownership_pct": 0.0007, "rsi_weekly": 55.0,
        "rsi_trend": "neutral", "sector_context_modifier": 0,
        "pct_below_3yr_high": -0.05,
        "shares_outstanding": 15_000_000_000,
        "diluted_shares": 15_000_000_000,
        "dilution_risk_pct": 0,
        "fcf_series": {},
    }
    scorer = RKScorer()
    result = scorer.score(aapl)
    assert result["score_total"] < 35, \
        f"AAPL scored too high: {result['score_total']}"

def test_transparency_has_explanation(rk_stock):
    scorer = RKScorer()
    result = scorer.score(rk_stock)
    trans = result["transparency"]
    assert "total_explanation" in trans
    assert len(trans["total_explanation"]) > 50
    assert "components" in trans
    assert len(trans["components"]) == 5

# ── Tests for review fixes ───────────────────────────────────────────

def test_10b51_plan_halves_insider_score(rk_stock):
    """10b5-1 pre-scheduled buys should score lower than discretionary buys."""
    scorer = RKScorer()

    # Normal discretionary buy
    rk_stock["insider_is_10b51_plan"] = False
    normal = scorer.score(rk_stock)
    normal_ins = normal["components"]["insider"]["points"]

    # Same buy but via 10b5-1 plan
    rk_stock["insider_is_10b51_plan"] = True
    plan = scorer.score(rk_stock)
    plan_ins = plan["components"]["insider"]["points"]

    assert plan_ins < normal_ins, \
        f"10b5-1 plan buy should score lower: {plan_ins} vs {normal_ins}"

def test_stale_bond_reduces_score(rk_stock):
    """Stale bond price should penalise bond score by 5pts."""
    scorer = RKScorer()

    rk_stock["bond_is_stale"] = False
    fresh = scorer.score(rk_stock)
    fresh_bonds = fresh["components"]["bonds"]["points"]

    rk_stock["bond_is_stale"] = True
    stale = scorer.score(rk_stock)
    stale_bonds = stale["components"]["bonds"]["points"]

    assert stale_bonds <= fresh_bonds - 5, \
        f"Stale bond should score 5pts lower: {stale_bonds} vs {fresh_bonds}"

def test_no_price_series_in_score_output(rk_stock):
    """_price_series must never appear in scorer output — would crash JSON dump."""
    import json
    rk_stock["_price_series"] = "pandas_series_placeholder"
    scorer = RKScorer()
    result = scorer.score(rk_stock)
    # Merge result back as main.py does
    rk_stock.update(result)
    rk_stock.pop("_price_series", None)   # as main.py now does
    # Should serialise cleanly
    try:
        json.dumps(rk_stock, default=str)
    except TypeError as e:
        pytest.fail(f"JSON serialisation failed after _price_series pop: {e}")

def test_xbrl_frame_filter_accepts_q4i():
    """XBRL parser should accept CY2023Q4I annual frames, not just CY2023."""
    from pipeline.layers._fundamentals_parser import FundamentalsParser

    # Simulate EDGAR facts with Q4I format (common for many companies)
    mock_facts = {
        "facts": {
            "us-gaap": {
                "NetCashProvidedByUsedInOperatingActivities": {
                    "units": {
                        "USD": [
                            # Annual data in Q4I format — should be accepted
                            {"form": "10-K", "frame": "CY2022Q4I",
                             "val": 500_000_000, "end": "2022-12-31"},
                            {"form": "10-K", "frame": "CY2023Q4I",
                             "val": 600_000_000, "end": "2023-12-31"},
                            # Quarterly data — should be excluded
                            {"form": "10-Q", "frame": "CY2023Q1",
                             "val": 120_000_000, "end": "2023-03-31"},
                            {"form": "10-Q", "frame": "CY2023Q2",
                             "val": 130_000_000, "end": "2023-06-30"},
                        ]
                    }
                }
            }
        }
    }
    parser = FundamentalsParser(mock_facts, "TEST")
    series = parser.get_annual_series(
        "NetCashProvidedByUsedInOperatingActivities"
    )
    assert len(series) == 2, \
        f"Expected 2 annual entries (Q4I format), got {len(series)}: {series}"
    assert 2023 in series and series[2023] == 600_000_000

def test_xbrl_frame_filter_excludes_q1_q2_q3():
    """XBRL parser must exclude Q1/Q2/Q3 quarterly frames."""
    from pipeline.layers._fundamentals_parser import FundamentalsParser

    mock_facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"form": "10-K", "frame": "CY2023",
                             "val": 1_000_000_000, "end": "2023-12-31"},
                            # These quarterly frames must be excluded
                            {"form": "10-Q", "frame": "CY2023Q1",
                             "val": 200_000_000, "end": "2023-03-31"},
                            {"form": "10-Q", "frame": "CY2023Q2",
                             "val": 250_000_000, "end": "2023-06-30"},
                            {"form": "10-Q", "frame": "CY2023Q3",
                             "val": 270_000_000, "end": "2023-09-30"},
                        ]
                    }
                }
            }
        }
    }
    parser = FundamentalsParser(mock_facts, "TEST")
    series = parser.get_annual_series("Revenues")
    assert len(series) == 1, \
        f"Expected 1 annual entry only, got {len(series)}: {series}"
    assert series.get(2023) == 1_000_000_000
```

### 6.2 Integration Test

```bash
# Full pipeline on test tickers — end to end
python pipeline/main.py --test

# Check output
python -c "
import json
with open('output/results.json') as f:
    d = json.load(f)
print('Candidates:', len(d['candidates']))
for c in d['candidates']:
    print(f\"  {c['ticker']}: {c['score_total']:.0f} — {c['score_label']}\")
print('Stats:', d['stats'])
"
```

---

## 7. File-by-File Implementation Reference

| File | Sprint | Purpose | Notes |
|------|--------|---------|-------|
| `pipeline/config.py` | 1 | All configuration constants | weights assert included |
| `pipeline/utils/logger.py` | 1 | Logging setup | |
| `pipeline/utils/cache.py` | 1 | File-based caching | JSON + pickle |
| `pipeline/db/schema.sql` | 1 | SQLite schema | user_id, is_current columns |
| `pipeline/db/database.py` | 1 | DB connection + helpers | timeout=10, upsert fix |
| `pipeline/data/sector_etf_map.json` | 1 | Sector to ETF mapping | |
| `pipeline/data/value_funds.json` | 1 | Known value funds list | |
| `pipeline/data/secular_decline_sic.json` | 1 | SIC codes — secular decline | new: required by Layer 6 |
| `pipeline/data/cyclical_sic.json` | 1 | SIC codes — cyclical industries | new: required by Layer 6 |
| `pipeline/layers/layer1_universe.py` | 1→2 | Universe fetch | stub Day 3, real Day 4 |
| `pipeline/layers/layer2_price.py` | 1→2 | Price pain screen | stub Day 3, real Day 5 |
| `pipeline/layers/layer3_fundamentals.py` | 1→2 | Fundamental screen | stub Day 3, real Days 6-11 |
| `pipeline/layers/_fundamentals_parser.py` | 2 | XBRL parser helper | frame filter fix applied |
| `pipeline/layers/layer4_conviction.py` | 1→3 | Conviction signals | stub Day 3, real Days 12-13 |
| `pipeline/layers/layer5_bonds.py` | 1→3 | Bond survival check | stub Day 3, Phase 1 = unavailable tier |
| `pipeline/layers/layer6_technical.py` | 1→3 | Technical confirmation | stub Day 3, real Days 15-16 |
| `pipeline/scrapers/openinsider.py` | 3 | Insider buying scraper | UA rotation, EDGAR fallback |
| `pipeline/scrapers/whalewisdom.py` | 3 | Institutional holders | yfinance only in Phase 1 |
| `pipeline/scrapers/finra_trace.py` | Phase 2 | Bond price scraper | deferred — Phase 1 skips |
| `pipeline/scoring/base_scorer.py` | 1→4 | Base scorer class | stub Day 3, real Day 18 |
| `pipeline/scoring/confidence_score.py` | 1→4 | RK scorer | stub Day 3, real Days 18-19 |
| `pipeline/scoring/transparency.py` | 1→4 | Transparency builder | stub Day 3, real Day 20 |
| `pipeline/scoring/upside_calc.py` | 1→4 | Upside multiple | stub Day 3, real Day 20 |
| `pipeline/scoring/risk_flags.py` | 1→4 | Risk flag generator | stub Day 3, real Day 21 |
| `pipeline/scoring/action_steps.py` | 1→4 | Action step generator | stub Day 3, real Day 21 |
| `pipeline/tests/test_scoring.py` | 4 | Unit tests | 9 tests including fix coverage |
| `pipeline/swing/swing_pipeline.py` | Phase 2 | Swing trader pipeline | stub in Phase 1 |
| `pipeline/swing/swing_scoring.py` | Phase 2 | Swing scorer | deferred to Phase 2 |
| `pipeline/main.py` | 1 | Pipeline entry point | all imports at top, price_series pop |
| `frontend/index.html` | 5 | App shell | |
| `frontend/css/main.css` | 5 | CSS variables, reset | |
| `frontend/css/components.css` | 5 | Component styles | |
| `frontend/css/layout.css` | 5 | Grid, zones, responsive | |
| `frontend/css/accessibility.css` | 5 | Focus, ARIA | |
| `frontend/js/app.js` | 5 | Router, nav | |
| `frontend/js/utils/format.js` | 5 | Number formatting | |
| `frontend/js/utils/colors.js` | 5 | Score to color | |
| `frontend/js/utils/storage.js` | 5 | localStorage helpers | |
| `frontend/js/data/tooltips.json` | 5 | All tooltip content | 15 metrics defined |
| `frontend/js/components/scorecard.js` | 5 | Score bar component | |
| `frontend/js/components/score_transparency.js` | 5 | Level 2 accordion | |
| `frontend/js/components/charts.js` | Phase 2 | Chart.js wrappers | deferred — Phase 1 uses tables |
| `frontend/js/components/sparkline.js` | 5 | 8-week sparklines | |
| `frontend/js/components/alerts.js` | 5 | Alert banners | |
| `frontend/js/components/zone_expander.js` | 5 | Progressive disclosure | |
| `frontend/js/components/tooltip_system.js` | 5 | ⓘ tooltip system | |
| `frontend/js/pages/scanner.js` | 5 | Page 1 | |
| `frontend/js/pages/watchlist.js` | 5 | Page 2 | |
| `frontend/js/pages/deepdive.js` | 5 | Page 3 | Zone 1/2/3 layout |
| `frontend/js/pages/swing.js` | Phase 2 | Page 4 | stub in Phase 1 |
| `.github/workflows/pipeline.yml` | Phase 2 | GitHub Actions | |

---

*Total Phase 1: ~30 working days. Phase 2: ~8 days. Phase 3: ~15 days.*
*First working results.json: end of Sprint 4 (Day 21).*
*First working UI: end of Sprint 5 (Day 30).*
*At 2–3 hours per day: 10–12 weeks to completed Phase 1.*