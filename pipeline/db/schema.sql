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
