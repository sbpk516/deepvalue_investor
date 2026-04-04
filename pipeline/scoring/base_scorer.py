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
