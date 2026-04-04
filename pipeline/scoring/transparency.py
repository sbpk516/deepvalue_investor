"""Builds the three-level scoring transparency chain."""


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
