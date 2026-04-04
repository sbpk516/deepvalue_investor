from __future__ import annotations

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
