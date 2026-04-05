"""
RK Stock Screener — Main Pipeline Entry Point

Usage:
    python pipeline/main.py              # full nightly run
    python pipeline/main.py --ticker GME # single ticker deep dive
    python pipeline/main.py --test       # run on 5 test tickers only
"""
from __future__ import annotations

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
from pipeline.layers.layer3_fundamentals import run as layer3_run, run_all as layer3_run_all
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
    fund_filtered, all_evaluated = layer3_run_all(price_filtered, config.__dict__)
    logger.info(f"Layer 3 complete: {len(fund_filtered)} passed, "
                f"{len(all_evaluated)} evaluated")

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

    # Strip _price_series from intermediate layers too for JSON output
    def _clean(stocks):
        out = []
        for s in stocks:
            c = {k: v for k, v in s.items() if k != "_price_series"}
            out.append(c)
        return out

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
        "parameters": {
            "LAYER2_MIN_DRAWDOWN_PCT": config.LAYER2_MIN_DRAWDOWN_PCT,
            "LAYER3_MAX_PTBV": config.LAYER3_MAX_PTBV,
            "LAYER3_MIN_REVENUE": config.LAYER3_MIN_REVENUE,
            "LAYER3_MAX_OVERHANG_RATIO": config.LAYER3_MAX_OVERHANG_RATIO,
            "LAYER4_MIN_INSIDER_BUY": config.LAYER4_MIN_INSIDER_BUY,
            "LAYER5_BOND_SAFE": config.LAYER5_BOND_SAFE,
            "LAYER5_BOND_CAUTION": config.LAYER5_BOND_CAUTION,
            "LAYER5_BOND_ELEVATED": config.LAYER5_BOND_ELEVATED,
            "LAYER5_BOND_HIGH_RISK": config.LAYER5_BOND_HIGH_RISK,
            "TIER_EXCEPTIONAL": config.TIER_EXCEPTIONAL,
            "TIER_HIGH_CONVICTION": config.TIER_HIGH_CONVICTION,
            "TIER_SPECULATIVE": config.TIER_SPECULATIVE,
            "SCORE_WEIGHTS": config.SCORE_WEIGHTS,
        },
        "pipeline": {
            "layer1_universe": {
                "description": "SEC EDGAR universe — all US-listed stocks",
                "count": len(universe),
                "tickers": [t.get("ticker") for t in universe[:50]],
            },
            "layer2_price": {
                "description": f"Price pain — down {config.LAYER2_MIN_DRAWDOWN_PCT}%+ from 3yr high",
                "count": len(price_filtered),
                "filtered": len(universe) - len(price_filtered),
                "stocks": _clean(price_filtered),
            },
            "layer3_fundamentals": {
                "description": f"Fundamentals — P/TBV < {config.LAYER3_MAX_PTBV}, positive FCF, revenue > ${config.LAYER3_MIN_REVENUE/1e6:.0f}M",
                "count": len(fund_filtered),
                "filtered": len(all_evaluated) - len(fund_filtered),
                "evaluated": len(all_evaluated),
                "no_data": len(price_filtered) - len(all_evaluated),
                "stocks": _clean(fund_filtered),
                "all_evaluated": _clean(all_evaluated),
            },
            "layer4_conviction": {
                "description": f"Conviction — insider buy >= ${config.LAYER4_MIN_INSIDER_BUY/1e3:.0f}K OR value fund OR 20%+ insider ownership",
                "count": len(conviction_filtered),
                "filtered": len(fund_filtered) - len(conviction_filtered),
                "stocks": _clean(conviction_filtered),
            },
            "layer5_bonds": {
                "description": "Bond survival — not in credit distress",
                "count": len(bond_checked),
                "filtered": len(conviction_filtered) - len(bond_checked),
                "stocks": _clean(bond_checked),
            },
            "layer6_technical": {
                "description": "Technical — RSI, sector context, decline type",
                "count": len(final_candidates),
                "filtered": len(bond_checked) - len(final_candidates),
                "stocks": _clean(final_candidates),
            },
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
