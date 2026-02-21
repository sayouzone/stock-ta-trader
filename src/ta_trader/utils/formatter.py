"""
ta_trader/utils/formatter.py
분석 결과 터미널 출력 포매터
"""

from __future__ import annotations

from ta_trader.models import TradingDecision

def make_decision(decision: TradingDecision) -> str:
    """TradingDecision 을 구조화된 형태로 터미널 출력"""
    bar = "=" * 68
    decision_str = (
        f"\n{bar}\n"
        f"  📊  {decision.ticker} ({decision.name}) |  {decision.date}\n"
        f"  |  현재가: {decision.current_price:,.2f}\n"
        f"{bar}\n"
        f"  시장 국면    : {decision.market_regime.value}\n"
        f"  복합 점수    : {decision.composite_score:+.2f}  (-100 ~ +100)\n"
        f"  최종 신호    : ★  {decision.final_signal.value}  ★\n"
    )

    if decision.risk:
        decision_str += (
            f"  손절가       : {decision.stop_loss:,.2f}\n"
            f"  목표가       : {decision.take_profit:,.2f}\n"
            f"  위험보상비율 : 1 : {decision.risk_reward_ratio}\n"
        )

    decision_str += f"\n  ── 개별 지표 ──────────────────────────────────────\n"
    for ind in decision.indicators:
        decision_str += (
            f"  [{ind.name:17s}] {ind.signal.value:6s}"
            f"  점수: {ind.score:+6.1f}  │  {ind.description}\n"
        )

    if decision.summary:
        decision_str += f"\n  📝 {decision.summary}\n"

    # ── LLM 분석 섹션 ──────────────────────────────────
    if decision.llm_analysis:
        decision_str += make_llm_analysis(decision)

    decision_str += f"{bar}\n"

    return decision_str

def make_llm_analysis(decision: TradingDecision) -> str:
    """LLMAnalysis 섹션만 출력"""
    llm = decision.llm_analysis
    if not llm:
        return ""

    thin = "─" * 68
    conf_bar = _confidence_bar(llm.confidence)

    llm_str = f"\n  {'─'*64}\n"
    llm_str += f"  🤖 LLM 분석  [{llm.model}]  신뢰도: {conf_bar} {llm.confidence:.0%}\n"
    llm_str += f"  {'─'*64}\n"

    llm_str += f"\n  【종합 판단】\n"
    for line in _wrap(llm.overall_assessment, width=62):
        llm_str += f"    {line}\n"

    llm_str += f"\n  【신호 근거】\n"
    for line in _wrap(llm.signal_rationale, width=62):
        llm_str += f"    {line}\n"

    if llm.key_risks:
        llm_str += f"\n  【주요 리스크】\n"
        for risk in llm.key_risks:
            llm_str += f"    ⚠  {risk}\n"

    if llm.opportunities:
        llm_str += f"\n  【기회 요인】\n"
        for opp in llm.opportunities:
            llm_str += f"    ✅  {opp}\n"

    if llm.action_plan:
        llm_str += f"\n  【액션 플랜】\n"
        for line in _wrap(llm.action_plan, width=62):
            llm_str += f"    {line}\n"

    llm_str += f"{thin}\n"
    return llm_str

# ── 내부 유틸 ────────────────────────────────────────────

def _confidence_bar(confidence: float, width: int = 10) -> str:
    """신뢰도를 █ 블록 바로 시각화"""
    filled = round(confidence * width)
    return "█" * filled + "░" * (width - filled)


def _wrap(text: str, width: int = 62) -> list[str]:
    """간단한 텍스트 줄바꿈 (공백 기준)"""
    words  = text.split()
    lines  = []
    line   = ""
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines
