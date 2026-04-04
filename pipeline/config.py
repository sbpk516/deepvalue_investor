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
ENABLE_BOND_SCRAPE           = os.getenv("ENABLE_BOND_SCRAPE", "false").lower() == "true"
ENABLE_SWING_PIPELINE        = os.getenv("ENABLE_SWING_PIPELINE", "false").lower() == "true"

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
