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

        steps.sort(key=lambda s: s["priority"])
        return steps
