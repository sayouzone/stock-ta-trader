from dataclasses import dataclass

import pandas as pd

from .fifty_percent_rule import FiftyPercentRule, FiftyRuleResult, RuleSignal, MAZone, RuleVerdict
from .ma_position_rule import MABuyRule, MASellRule, ensure_ma, classify_ma_zone

# ─────────────────────────────────────────────────────────────
# 통합 평가기
# ─────────────────────────────────────────────────────────────
class CoreRuleEngine:
    """50% 룰 + 매수 3원칙 + 매도 2원칙 통합 실행기."""
 
    def __init__(self, use_full_range_fifty: bool = False):
        self.fifty_rule = FiftyPercentRule(use_full_range=use_full_range_fifty)
        self.buy_rule = MABuyRule(self.fifty_rule)
        self.sell_rule = MASellRule(self.fifty_rule)
 
    def evaluate(self, df: pd.DataFrame) -> RuleVerdict:
        d = ensure_ma(df)
        curr = d.iloc[-1]
        zone = classify_ma_zone(float(curr["Close"]),
                                float(curr["ma5"]), float(curr["ma20"]))
        return RuleVerdict(
            fifty=self.fifty_rule.evaluate(df),
            buy_signal=self.buy_rule.evaluate(df),
            sell_signal=self.sell_rule.evaluate(df),
            zone=zone,
        )