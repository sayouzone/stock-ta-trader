"""
ta_trader/value/formatter.py
ValueAnalysisResult 터미널 출력 포매터

growth/formatter.py와 동일한 레이아웃:
  1. 요약 테이블 (순위·등급·종목·현재가·점수·스테이지 점수)
  2. 매수 추천 종목 상세
  3. 관망 종목 (간략)
  4. 부적합 종목 (간략)
  5. 면책 조항
"""

from __future__ import annotations

from ta_trader.models.base import StageResult, StageStatus
from ta_trader.models.value import (
    ValueGrade, ValueAnalysisResult,
)
from ta_trader.utils.formatter import _wrap


# ── 복수 종목 보고서 (value-screen용) ─────────────────────

def format_value_report(results: list[ValueAnalysisResult]) -> str:
    """복수 ValueAnalysisResult를 recommend 형식 보고서로 변환"""
    if not results:
        return "분석 결과가 없습니다."

    bar  = "═" * 72
    thin = "─" * 72
    report_date = results[0].date if results else ""

    lines = [
        f"\n{bar}",
        f"  💎 가치 투자 (Value Investing) 종목 추천 보고서  |  {report_date}",
        f"{bar}",
    ]

    # ── 요약 테이블 ──────────────────────────────────────
    lines.append("")
    lines.append(
        f"  {'순위':>4s}  {'등급':7s}  {'종목':8s}  {'현재가':>10s}  "
        f"{'점수':>6s}  {'S1':>5s} {'S2':>5s} {'S3':>5s} {'S4':>5s} {'S5':>5s}  {'종목명':>10s}"
    )
    lines.append(f"  {thin[2:]}")

    for rank, r in enumerate(results, 1):
        s_cols = ""
        for sn in range(1, 6):
            s = r.get_stage(sn)
            if s:
                s_cols += f" {s.score:>2.0f}/{s.max_score:<2.0f}"
            else:
                s_cols += "   - "

        lines.append(
            f"  {rank:>4d}  {r.grade.emoji} {r.grade.value:5s}  "
            f"{r.ticker:8s}  {r.current_price:>10,.2f}  "
            f"{r.total_score:>5.1f} {s_cols:30s} {r.name:>10s}"
        )

    # ── 등급별 분류 ──────────────────────────────────────
    buy_picks = [r for r in results if r.grade in (
        ValueGrade.STRONG_BUY, ValueGrade.BUY, ValueGrade.CONDITIONAL,
    )]
    watch_list = [r for r in results if r.grade == ValueGrade.WATCH]
    avoid_list = [r for r in results if r.grade == ValueGrade.UNFIT]

    # ── 매수 추천 종목 상세 ──────────────────────────────
    if buy_picks:
        lines.append(f"\n{bar}")
        lines.append(f"  🟢 매수 추천 종목 ({len(buy_picks)}건)")
        lines.append(f"{bar}")
        for rank, r in enumerate(buy_picks, 1):
            lines.extend(_format_single_value(r, rank, brief=False))

    # ── 관망 종목 ────────────────────────────────────────
    if watch_list:
        lines.append(f"\n{bar}")
        lines.append(f"  ⚪ 관망 종목 ({len(watch_list)}건)")
        lines.append(f"{bar}")
        for rank, r in enumerate(watch_list, 1):
            lines.extend(_format_single_value(r, rank, brief=True))

    # ── 부적합 종목 ──────────────────────────────────────
    if avoid_list:
        lines.append(f"\n{bar}")
        lines.append(f"  🔴 부적합 종목 ({len(avoid_list)}건)")
        lines.append(f"{bar}")
        for r in avoid_list:
            lines.append(f"    {r.ticker:8s} {r.name:10s}  {r.total_score:>5.1f}점  {r.action}")

    # ── 면책 조항 ────────────────────────────────────────
    lines.append(f"\n{bar}")
    lines.append("  ⚠  면책 조항")
    lines.append(f"{thin}")
    lines.append("본 보고서는 정보 제공 목적으로만 작성되었으며, 투자 권유나 매매 추천이 아닙니다. ")
    lines.append("모든 투자 판단은 본인의 책임하에 이루어져야 합니다. ")
    lines.append("과거의 재무 데이터가 미래 성과를 보장하지 않으며, 가치 투자에서도 '가치 함정(Value Trap)' 위험이 존재합니다.")

    lines.append(f"{bar}\n")

    return "\n".join(lines)


# ── 단일 종목 보고서 ─────────────────────────────────────

def format_value_result(result: ValueAnalysisResult) -> str:
    """단일 ValueAnalysisResult를 상세 보고서로 변환"""
    bar  = "═" * 72
    thin = "─" * 72

    lines = [
        f"\n{bar}",
        f"  💎 가치 투자 분석 보고서",
        f"  {result.ticker}  {result.name}  |  {result.date}",
        f"{bar}",
        "",
        f"  현재가:  {result.current_price:>12,.2f}",
        f"  등급:    {result.grade.emoji} {result.grade.stars}  {result.grade.value}",
        f"  총점:    {result.total_score:>5.1f} / 100",
    ]

    if result.intrinsic_value:
        lines.append(f"  내재가치: {result.intrinsic_value:>11,.2f}")
    if result.margin_of_safety is not None:
        mos_str = f"{result.margin_of_safety:.1%}"
        lines.append(f"  안전마진: {mos_str:>11s}")

    # 펀더멘털 요약
    f = result.fundamentals
    if f:
        lines.append(f"\n  {thin[2:]}")
        lines.append(f"  📊 펀더멘털 요약")
        lines.append(f"  {thin[2:]}")
        items = []
        if f.trailing_pe is not None:
            items.append(f"PER {f.trailing_pe:.1f}")
        if f.forward_pe is not None:
            items.append(f"F-PER {f.forward_pe:.1f}")
        if f.pbr is not None:
            items.append(f"PBR {f.pbr:.2f}")
        if f.ev_ebitda is not None:
            items.append(f"EV/EBITDA {f.ev_ebitda:.1f}")
        if items:
            lines.append(f"  밸류에이션: {' | '.join(items)}")

        items = []
        if f.roe is not None:
            items.append(f"ROE {f.roe:.1%}")
        if f.operating_margin is not None:
            items.append(f"영업이익률 {f.operating_margin:.1%}")
        if f.fcf_yield is not None:
            items.append(f"FCF Yield {f.fcf_yield:.1%}")
        if items:
            lines.append(f"  수익성:   {' | '.join(items)}")

        items = []
        if f.debt_to_equity is not None:
            items.append(f"D/E {f.debt_to_equity:.1%}")
        if f.current_ratio is not None:
            items.append(f"유동비율 {f.current_ratio:.2f}")
        if f.dividend_yield is not None and f.dividend_yield > 0:
            items.append(f"배당수익률 {f.dividend_yield:.1%}")
        if items:
            lines.append(f"  재무/배당: {' | '.join(items)}")

    # 5단계 분석 상세
    lines.append(f"\n{bar}")
    lines.append(f"  📋 5단계 분석 상세")
    lines.append(f"{bar}")

    for s in result.stages:
        status_icon = {
            StageStatus.PASS:    "✅",
            StageStatus.PARTIAL: "⚠️",
            StageStatus.FAIL:    "❌",
            StageStatus.NO_DATA: "❓",
        }.get(s.status, "?")

        lines.append(f"\n  {status_icon} [{s.stage_num}단계] {s.stage_name}  "
                      f"{s.score:.0f}/{s.max_score:.0f}점  ({s.score_pct:.0f}%)")
        lines.append(f"  {thin[2:]}")

        for c in s.checks:
            if c.name in ("손절가", "목표가"):
                continue  # 리스크 섹션에서 별도 표시
            mark = "✓" if c.passed else "✗"
            score_str = f"[+{c.score:.1f}]" if c.score > 0 else ""
            lines.append(f"    {mark} {c.name:14s} {score_str:>8s}  {c.description}")

    # 리스크 관리
    lines.append(f"\n{bar}")
    lines.append(f"  🛡️ 리스크 관리")
    lines.append(f"{thin}")
    if result.stop_loss:
        lines.append(f"  손절가:       {result.stop_loss:>12,.2f}")
    if result.take_profit:
        lines.append(f"  목표가:       {result.take_profit:>12,.2f}")
    if result.risk_reward:
        lines.append(f"  R:R 비율:     1:{result.risk_reward:.1f}")
    if result.high_52w:
        lines.append(f"  52주 고가:    {result.high_52w:>12,.2f}")
    if result.low_52w:
        lines.append(f"  52주 저가:    {result.low_52w:>12,.2f}")

    # 경고
    if result.warnings:
        lines.append(f"\n  ⚠️  경고 사항")
        for w in result.warnings:
            lines.append(f"    • {w}")

    # 행동 권고
    lines.append(f"\n{bar}")
    lines.append(f"  🎯 {result.action}")
    lines.append(f"{bar}")

    # 면책
    lines.append(f"\n  ⚠  본 분석은 정보 제공 목적이며 투자 권유가 아닙니다.")
    lines.append(f"     가치 함정(Value Trap) 위험을 항상 인지하십시오.\n")

    return "\n".join(lines)


# ── 내부 헬퍼 ─────────────────────────────────────────────

def _format_single_value(
    r: ValueAnalysisResult,
    rank: int,
    brief: bool = False,
) -> list[str]:
    """개별 종목 섹션 포맷"""
    thin = "─" * 72
    lines = [
        f"\n  {thin[2:]}",
        f"  #{rank}  {r.grade.emoji} {r.ticker}  {r.name}  "
        f"│ {r.total_score:.1f}점 {r.grade.value}",
    ]
    lines.append(f"  현재가: {r.current_price:,.2f}")

    if r.fundamentals:
        f = r.fundamentals
        items = []
        if f.trailing_pe is not None:
            items.append(f"PER {f.trailing_pe:.1f}")
        if f.pbr is not None:
            items.append(f"PBR {f.pbr:.2f}")
        if f.roe is not None:
            items.append(f"ROE {f.roe:.1%}")
        if f.dividend_yield and f.dividend_yield > 0:
            items.append(f"배당 {f.dividend_yield:.1%}")
        if items:
            lines.append(f"  지표: {' | '.join(items)}")

    if r.margin_of_safety is not None:
        lines.append(f"  안전마진: {r.margin_of_safety:.1%}")

    if not brief:
        for s in r.stages:
            status_icon = {
                StageStatus.PASS: "✅", StageStatus.PARTIAL: "⚠️",
                StageStatus.FAIL: "❌", StageStatus.NO_DATA: "❓",
            }.get(s.status, "?")
            lines.append(f"    {status_icon} {s.stage_name}: {s.score:.0f}/{s.max_score:.0f}  {s.description}")

    if r.stop_loss and r.take_profit:
        lines.append(f"  손절: {r.stop_loss:,.2f}  │  목표: {r.take_profit:,.2f}  │  R:R 1:{r.risk_reward:.1f}" if r.risk_reward else "")

    lines.append(f"  ▸ {r.action}")

    return lines
