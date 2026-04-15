"""
ta_trader/formatters/swing.py
스윙 트레이딩 6단계 분석 결과 포매터
"""

from __future__ import annotations

from ta_trader.models import OrderSide
from ta_trader.models.swing import (
    SwingAnalysisResult,
    MarketEnvironment, ScreeningGrade,
)

import unicodedata
from typing import TYPE_CHECKING, Optional, Literal

if TYPE_CHECKING:
    from ta_trader.models.llm import LLMAnalysis

# ── 신호 이모지 ───────────────────────────────────────────

_SIGNAL_EMOJI = {
    OrderSide.STRONG_ENTRY: "🟢🟢",
    OrderSide.ENTRY: "🟢",
    OrderSide.HOLD: "🟡",
    OrderSide.PARTIAL_EXIT: "🟠",
    OrderSide.EXIT: "🔴",
    OrderSide.STRONG_EXIT: "🔴🔴",
}

_ENV_EMOJI = {
    MarketEnvironment.BULLISH_TREND: "📈",
    MarketEnvironment.BULLISH_WEAK: "📊",
    MarketEnvironment.BEARISH_TREND: "📉",
    MarketEnvironment.SIDEWAYS: "➡️",
    MarketEnvironment.HIGH_VOLATILITY: "⚡",
}

_GRADE_EMOJI = {
    ScreeningGrade.A_PLUS: "⭐",
    ScreeningGrade.A: "✅",
    ScreeningGrade.B: "🔵",
    ScreeningGrade.C: "⚪",
    ScreeningGrade.F: "❌",
}


# ── 포매팅 함수 ───────────────────────────────────────────

def format_swing_result(result: SwingAnalysisResult) -> str:
    """스윙 트레이딩 6단계 분석 결과를 터미널용 문자열로 변환"""
    W = 70
    lines: list[str] = []

    # 헤더
    lines.append("━" * W)
    lines.append(f"  🔄 스윙 트레이딩 분석: {result.name} ({result.ticker})")
    lines.append(f"  📅 {result.date}  |  💰 현재가: {result.current_price:,.0f}")
    lines.append("━" * W)

    # ── 1단계: 시장 환경 ──
    env = result.market_env
    e_emoji = _ENV_EMOJI.get(env.environment, "")
    lines.append(f"\n{'─'*W}")
    lines.append(f"  📊 1단계: 시장 환경 판단  [{env.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  {e_emoji} 환경: {env.environment.value}")
    lines.append(f"     {env.detail}")

    fav = "✅ 유리" if env.is_favorable else "⚠️  불리"
    lines.append(f"  → 스윙 매매 환경: {fav}")

    # ── 2단계: 종목 스크리닝 ──
    scr = result.screening
    g_emoji = _GRADE_EMOJI.get(scr.grade, "")
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🔍 2단계: 종목 스크리닝  [{scr.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  {g_emoji} 등급: {scr.grade.value}  ({scr.checks_passed}/{scr.checks_total} 통과)")
    lines.append(f"     {scr.detail}")

    # ── 3단계: 진입 타이밍 ──
    ent = result.entry
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🎯 3단계: 진입 타이밍  [{ent.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    for sig in ent.signals:
        mark = "✅" if sig.triggered else "  "
        score_str = f"+{sig.score:.0f}" if sig.score > 0 else f"{sig.score:.0f}"
        lines.append(f"  {mark} {sig.name:<18} {score_str:>5}점  {sig.description}")
    lines.append(f"  → 진입 신호: {_SIGNAL_EMOJI.get(ent.signal, '')} {ent.signal.value} ({ent.detail})")

    # ── 4단계: 포지션 사이징 ──
    pos = result.position
    lines.append(f"\n{'─'*W}")
    lines.append(f"  💼 4단계: 포지션 사이징  [{pos.score:.0f}/100점]")
    lines.append(f"{'─'*W}")
    lines.append(f"  진입가:   {pos.entry_price:>12,.0f}")
    lines.append(f"  손절가:   {pos.stop_loss:>12,.0f}  (ATR×{POSITION_ATR_SL_MULT})")
    lines.append(f"  익절가:   {pos.take_profit:>12,.0f}  (ATR×{POSITION_ATR_TP_MULT})")
    lines.append(f"  R배수:    1:{pos.risk_reward_ratio}  {'✅ 적합' if pos.is_acceptable else '⚠️  부적합'}")
    lines.append(f"  매수수량: {pos.position_size:>8,}주  ({pos.position_value:,.0f}원)")
    lines.append(f"  비중:     {pos.portfolio_pct:>8.1f}%  (자본금: {pos.capital:,.0f}원)")
    lines.append(f"  최대손실: {pos.max_loss:>12,.0f}원  (자본의 {pos.max_loss/pos.capital*100:.1f}%)")
    if pos.fibo_target_161 > 0:
        lines.append(f"  피보목표: 161.8%={pos.fibo_target_161:,.0f}  261.8%={pos.fibo_target_261:,.0f}")

    # ── 5단계: 익절/청산 전략 ──
    ext = result.exit_strategy
    lines.append(f"\n{'─'*W}")
    lines.append(f"  🚪 5단계: 익절/청산 전략  [청산압력 {ext.score:.0f}/100]")
    lines.append(f"{'─'*W}")
    lines.append(f"  트레일링 스톱:  {ext.trailing_stop:>10,.0f}")
    lines.append(f"  1차 부분익절:   {ext.partial_exit_price:>10,.0f}  (50% 매도)")
    lines.append(f"  전량 청산가:    {ext.full_exit_price:>10,.0f}")
    lines.append(f"     {ext.detail}")
    if ext.should_partial_exit:
        lines.append(f"  ⚠️  현재 부분 익절 권장")
    if ext.should_full_exit:
        lines.append(f"  🚨 현재 전량 청산 권장")

    # ── 종합 ──
    lines.append(f"\n{'━'*W}")
    sig_emoji = _SIGNAL_EMOJI.get(result.overall_signal, "")
    lines.append(f"  {sig_emoji} 종합 신호: {result.overall_signal.value}  ({result.overall_score:.1f}/100)")
    lines.append(f"{'━'*W}")
    lines.append(f"  {result.summary}")
    if result.is_actionable:
        lines.append(f"  ✅ 매수 실행 가능 조건 충족")
    else:
        lines.append(f"  ⏸️  매수 실행 조건 미충족 - 관망 권장")

    # ── LLM 분석 섹션 ──────────────────────────────────
    if result.llm_analysis:
        lines.append(f"\n{'━'*W}")
        lines.append(make_llm_analysis(result.llm_analysis))

    lines.append("━" * W)

    return "\n".join(lines)


# 상수 참조 (detail 표시용)
from ta_trader.constants.swing import (
    POSITION_ATR_SL_MULTIPLIER as POSITION_ATR_SL_MULT,
    POSITION_ATR_TP_MULTIPLIER as POSITION_ATR_TP_MULT,
)


def format_swing_report(results: list[SwingAnalysisResult]) -> str:
    """복수 종목 스윙 분석 요약 보고서"""
    if not results:
        return "분석 결과 없음"

    # ── 컬럼 레이아웃 정의 (헤더명, 화면폭, 정렬) ────────────────────────────────
    #   "🟢🟢 강력진입" → _wlen = 2+2+1+8 = 13   →  진입/종합 컬럼 폭 14
    #   "🟠 부분청산"   → _wlen = 2+1+8   = 11   ┘
    #   "약한강세"      → _wlen = 8              →  시장/섹터 컬럼 폭 10
    _COLS: list[tuple[str, int, Literal['<', '>', '^']]] = [
        ("진입",  14, '^'),   # emoji + signal
        ("점수",   5, '>'),
        ("가격",  10, '>'),
        ("시장",  10, '^'),
        #("섹터",  10, '^'),
        ("등급",   4, '^'),
        ("손절",  10, '>'),
        ("익절",  10, '>'),
        ("RR",    5, '>'),
        ("수량",  10, '>'),
        ("종합",  14, '^'),   # emoji + signal
        ("점수",   6, '>'),
        ("종목",   0, '<'),   # 자유폭 (마지막 컬럼)
    ]
    _W   = 120   # 구분선 폭
    _SEP = "  "  # 컬럼 사이 구분자

    W = _W
    lines: list[str] = []
    lines.append("━" * W)
    lines.append(f"  🔄 스윙 트레이딩 스크리닝 보고서  ({len(results)}종목)")
    lines.append("━" * W)

    # 요약 테이블 헤더
    """
    header = (
        f"{'진입':^8} {'점수':>5} {'가격':>10} {'시장':^8} "
        f"{'등급':^4} {'손절':>10} {'익절':>10} {'RR':>5} "
        f"{'수량':>6} {'종합':^8} {'점수':>5} {'종목':<18}"
    )
    """
    """
    header = (
        f"{'진입':^14} {'점수':>5} {'가격':>10} {'시장':^10} "
        f"{'등급':^4} {'손절':>10} {'익절':>10} {'RR':>5} "
        f"{'수량':>10} {'종합':^14} {'점수':>6} {'종목':<0}"
    )

    lines.append(header)
    lines.append("─" * W)
    """

    # ── 헤더 ─────────────────────────────────────────────────────────────────
    header_parts = [_wfmt(h, w, a) for h, w, a in _COLS[:-1]]
    header_parts.append(_COLS[-1][0])   # 종목 헤더 (패딩 없음)
    lines.append(_SEP.join(header_parts))
    lines.append("─" * W)

    # 점수 내림차순 정렬
    #sorted_results = sorted(results, key=lambda r: r.overall_score, reverse=True)
    sorted_results = sorted(results, key=lambda r: (r.entry.score, r.overall_score), reverse=True)
    #sorted_results = sorted(results, key=lambda r: (r.overall_score, r.entry.score), reverse=True)

    for r in sorted_results:
        sig_emoji = _SIGNAL_EMOJI.get(r.overall_signal, "")
        ent_emoji = _SIGNAL_EMOJI.get(r.entry.signal, "")
        name = r.name[:18] if len(r.name) > 18 else r.name
        """
        line = (
            f"{ent_emoji}{r.entry.signal.value:^6} {r.entry.score:>5.0f} "
            f"{r.current_price:>10,.0f} {r.market_env.environment.value:^8} "
            f"{r.screening.grade.value:^4} {r.position.stop_loss:>10,.0f} "
            f"{r.position.take_profit:>10,.0f} {r.position.risk_reward_ratio:>5.1f} "
            f"{r.position.position_size:>6,} {sig_emoji}{r.overall_signal.value:^6} "
            f"{r.overall_score:>5.1f} {name:<18}"
        )
        """
        """
        line = (
            f"{ent_emoji}{r.entry.signal.value:^8} {r.entry.score:>5.0f} "
            f"{r.current_price:>10,.0f} {r.market_env.environment.value:^10} "
            f"{r.screening.grade.value:^4} {r.position.stop_loss:>10,.0f} "
            f"{r.position.take_profit:>10,.0f} {r.position.risk_reward_ratio:>5.1f} "
            f"{r.position.position_size:>10,} {sig_emoji}{r.overall_signal.value:^8} "
            f"{r.overall_score:>6.1f} {name:<18}"
        )

        lines.append(line)
        """
        values = [
            f"{ent_emoji} {r.entry.signal.value}",        # 진입
            f"{r.entry.score:.0f}",                       # 점수
            f"{r.current_price:,.0f}",                    # 가격
            r.market_env.environment.value,               # 시장
            #r.sector.strength.value,                     # 섹터
            r.screening.grade.value,                      # 등급
            f"{r.position.stop_loss:,.0f}",               # 손절
            f"{r.position.take_profit:,.0f}",             # 익절
            f"{r.position.risk_reward_ratio:.1f}",        # RR
            f"{r.position.position_size:,}",              # 수량
            f"{sig_emoji} {r.overall_signal.value}",      # 종합
            f"{r.overall_score:.1f}",                     # 점수
            f"{r.name} ({r.ticker})",                     # 종목명
        ]
        row_parts = [_wfmt(v, w, a) for v, (_, w, a) in zip(values[:-1], _COLS[:-1])]
        row_parts.append(values[-1])   # 종목명 패딩 없이 추가
        lines.append(_SEP.join(row_parts))

    lines.append("─" * W)

    # 매수 가능 종목 하이라이트
    actionable = [r for r in sorted_results if r.is_actionable]
    if actionable:
        lines.append(f"\n  ✅ 매수 실행 가능 종목: {len(actionable)}개")
        for r in actionable:
            lines.append(f"     → {r.name} ({r.ticker}) 점수={r.overall_score:.1f}")
    else:
        lines.append(f"\n  ⏸️  현재 매수 실행 가능 종목 없음")

    lines.append("━" * W)
    
    # ── 등급별 분류 ──────────────────────────────────────
    entry_picks = [r for r in results if r.entry.signal in (
        OrderSide.STRONG_ENTRY, OrderSide.ENTRY
    )]
    hold_list = [r for r in results if r.entry.signal == OrderSide.HOLD]
    exit_list = [r for r in results if r.entry.signal in (
        OrderSide.PARTIAL_EXIT, OrderSide.EXIT, OrderSide.STRONG_EXIT
    )]

    # ── 진입 종목 상세 ──────────────────────────────
    if entry_picks:
        lines.append("─" * W)
        lines.append(f"  🟢 진입 종목 ({len(entry_picks)}건)")
        lines.append("─" * W)
        for rank, r in enumerate(entry_picks, 1):
            lines.extend(_format_single_swing(r, rank, brief=False))

    # ── 보류 종목 상세 ──────────────────────────────
    if hold_list:
        lines.append("─" * W)
        lines.append(f"  🟡 보류 종목 ({len(hold_list)}건)")
        lines.append("─" * W)
        for rank, r in enumerate(hold_list, 1):
            lines.extend(_format_single_swing(r, rank, brief=False))

    # ── 매도 종목 상세 ──────────────────────────────
    if exit_list:
        lines.append("─" * W)
        lines.append(f"  🟡 분할 매도 종목 ({len(exit_list)}건)")
        lines.append("─" * W)
        for rank, r in enumerate(exit_list, 1):
            lines.extend(_format_single_swing(r, rank, brief=False))
    
    return "\n".join(lines)

# ── 단일 종목 내부 포매터 ────────────────────────────────

def _format_single_swing(
    r: SwingAnalysisResult, rank: int, brief: bool = False,
) -> list[str]:
    """단일 종목 결과를 recommend/_format_single_recommendation 스타일로 포매팅"""
    sig_emoji = _SIGNAL_EMOJI.get(r.overall_signal, "")
    ent_emoji = _SIGNAL_EMOJI.get(r.entry.signal, "")
    name = r.name[:18] if len(r.name) > 10 else r.name
    lines = [
        "",
        f"  ┌{'─' * 66}┐",
        f"  │  {ent_emoji}  #{rank}  {r.ticker} ({r.name})  —  "
        f"{r.screening.grade.value} {r.overall_signal.value}  ({r.overall_score:5.1f})",
        f"  │  현재가: {r.current_price:,.2f}",
        f"  └{'─' * 66}┘",
    ]

    pos = r.position
    pos_parts = []
    pos_parts.append(f"진입가: {pos.entry_price:>9,.0f}")
    pos_parts.append(f"손절가: {pos.stop_loss:>9,.0f} (ATR×{POSITION_ATR_SL_MULT})")
    pos_parts.append(f"익절가: {pos.take_profit:>9,.0f} (ATR×{POSITION_ATR_TP_MULT})")
    pos_parts.append(f"R배수: 1:{pos.risk_reward_ratio} {'✅ 적합' if pos.is_acceptable else '⚠️  부적합'}")
    pos_parts.append(f"매수수량: {pos.position_size:>6,}주 ({pos.position_value:,.0f}원)")
    if pos_parts:
        lines.append(f"   💼 {' | '.join(pos_parts)}")

    pos_parts = []
    pos_parts.append(f"비중: {pos.portfolio_pct:>5.1f}% (자본금: {pos.capital:,.0f}원)")
    pos_parts.append(f"최대손실: {pos.max_loss:>9,.0f}원 (자본의 {pos.max_loss/pos.capital*100:.1f}%)")
    if pos.fibo_target_161 > 0:
        pos_parts.append(f"피보목표: 161.8%={pos.fibo_target_161:,.0f} 261.8%={pos.fibo_target_261:,.0f}")
    if pos_parts:
        lines.append(f"      {' | '.join(pos_parts)}")

    ext = r.exit_strategy
    pos_parts = []
    pos_parts.append(f"트레일링 스톱: {ext.trailing_stop:>9,.0f}")
    pos_parts.append(f"1차 부분익절: {ext.partial_exit_price:>9,.0f} (50% 매도)")
    pos_parts.append(f"전량 청산가: {ext.full_exit_price:>9,.0f}")
    pos_parts.append(f"{ext.detail}")
    if ext.should_partial_exit:
        pos_parts.append(f"  ⚠️  현재 부분 익절 권장")
    if ext.should_full_exit:
        pos_parts.append(f"  🚨 현재 전량 청산 권장")
    if pos_parts:
        lines.append(f"   🚪 {' | '.join(pos_parts)}")

    lines.append(f"   {sig_emoji} 종합 신호: {r.overall_signal.value}  ({r.overall_score:.1f}/100)")
    if not brief:
        lines.append(f"     {r.summary}")
        if r.is_actionable:
            lines.append(f"   ✅ 매수 실행 가능 조건 충족")
        else:
            lines.append(f"   ⏸️  매수 실행 조건 미충족 - 관망 권장")

    return lines

def make_llm_analysis(llm: Optional["LLMAnalysis"] = None) -> str:
    """LLMAnalysis 섹션만 출력"""

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

# ── Wide-char 폭 보정 유틸 ────────────────────────────────────────────────────

def _wlen(s: str) -> int:
    """문자열의 화면 표시 폭 반환 (한글·CJK·이모지 = 2칸, 나머지 = 1칸)."""
    return sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in s)


def _wfmt(s: str, width: int, align: Literal['<', '>', '^'] = '<') -> str:
    """화면 폭(display width) 기준으로 문자열을 정렬·패딩."""
    pad = max(0, width - _wlen(s))
    if align == '>':
        return ' ' * pad + s
    elif align == '^':
        lp = pad // 2
        return ' ' * lp + s + ' ' * (pad - lp)
    return s + ' ' * pad  # '<'
