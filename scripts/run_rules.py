from __future__ import annotations

import click
import sys

from pathlib import Path

# 프로젝트를 editable 설치하지 않았을 때를 위해 src 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ta_trader.data.fetcher import DataFetcher
from ta_trader.park.rules.core import CoreRuleEngine


@click.group()
@click.version_option("1.5.0")
def cli() -> None:
    """TA Trader - 4-에이전트 기반 트레이딩 분석 시스템

    에이전트 명령어:
        agent-analyze  : 4-에이전트 파이프라인 단일 종목 분석
        agent-screen   : 4-에이전트 파이프라인 복수 종목 스크리닝
        agent-trade    : 전체 파이프라인 (체결 시뮬레이션 포함)

    레거시 명령어 (하위 호환):
        analyze, screen, recommend, backtest, growth, value 등
    """

# ── Park's Core Rule Engine 명령 ───────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--interval",   default="1d",                  show_default=True, help="봉 간격 (예: 1d, 1wk)")
def rules(ticker: str, period: str, interval: str) -> None:
    engine = CoreRuleEngine()

    fetcher = DataFetcher(period=period, interval=interval)
    #for ticker in ["005930.KS", "000660.KS", "035720.KS", "051910.KS"]:
    df = fetcher.fetch(ticker)
    name, info = fetcher.info(ticker)

    verdict = engine.evaluate(df)
    print("=" * 68)
    price = df['Close'].iloc[-1]
    price_str = f"{price:,.0f}" if ".K" in ticker else f"{price:,.2f}"
    print(f"{name} ({ticker}) 현재가 {price_str}")
    print("=" * 68)
    print(verdict.summary())
    print()


if __name__ == "__main__":
    cli()