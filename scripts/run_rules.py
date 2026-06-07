from __future__ import annotations

import click
import sys
import yaml

from pathlib import Path

# 프로젝트를 editable 설치하지 않았을 때를 위해 src 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ta_trader.data.fetcher import DataFetcher
from ta_trader.park.rules.core import CoreRuleEngine
from ta_trader.park.rules.bollinger_rule import BollingerRule, compare_signals


MARKETS = ["KOSPI", "KOSDAQ", "KRX", "ETF", "US", "PARK"]

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


# ── Park's Core Rule Engine 명령 ───────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--config",     default="configs/watchlist_park.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--period",  default="3mo",                    show_default=True)
@click.option("--interval",   default="1d",                  show_default=True, help="봉 간격 (예: 1d, 1wk, 5m)")
def bollinger(ticker: str, config: str, period: str, interval: str) -> None:
    fetcher = DataFetcher(period=period, interval=interval)

    if ticker in MARKETS:
        config_path = Path(config)

        if not config_path.exists():
            click.echo(f"설정 파일을 찾을 수 없습니다: {config}", err=True)
            sys.exit(1)

        cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        tickers = cfg.get("watchlist", [])

        if not tickers:
            click.echo("watchlist 항목이 없습니다.", err=True)
            sys.exit(1)

        MARKET_FILTERS = {
            "KOSPI": lambda t: ".KS" in t,
            "KOSDAQ": lambda t: ".KQ" in t,
            "KRX": lambda t: ".KS" in t or ".KQ" in t,
            "ETF": lambda t: ".KS" in t,
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
            "PARK": lambda t: True,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        tickers = [ticker]

    comparisons = []
    for ticker in tickers:
        df = fetcher.fetch(ticker)
        name, info = fetcher.info(ticker)

        comparison = compare_signals(ticker, name, df)
        comparisons.append(comparison)

    print("\n".join(comparisons))


if __name__ == "__main__":
    cli()