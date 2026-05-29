"""
main.py
CLI 진입점 - Click 기반

사용 예:
    python main.py analyze 005930.KS
    python main.py analyze AAPL --save-chart
    python main.py screen --config configs/watchlist.yaml
"""

from __future__ import annotations

import click
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import sys
import yaml

from datetime import date
from pathlib import Path

# 프로젝트를 editable 설치하지 않았을 때를 위해 src 경로 추가
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ta_trader.analyzers.growth import GrowthMomentumAnalyzer
from ta_trader.analyzers.short import ShortTermAnalyzer
from ta_trader.analyzers.value import ValueInvestingAnalyzer
from ta_trader.models import TradingStyle
from ta_trader.data.fetcher import DataFetcher
from ta_trader.park.screener import PreMarketScreener, StockData

MARKETS = ["KOSPI", "KOSDAQ", "KRX", "US"]

def _parse_style(style_str: str | None) -> TradingStyle:
    """CLI 문자열을 TradingStyle로 변환"""
    if style_str is None or style_str.lower() in ("swing", "스윙"):
        return TradingStyle.SWING
    if style_str.lower() in ("position", "포지션"):
        return TradingStyle.POSITION
    if style_str.lower() in ("growth", "성장"):
        return TradingStyle.GROWTH
    if style_str.lower() in ("value", "가치"):
        return TradingStyle.VALUE
    if style_str.lower() in ("park", "박병창"):
        return TradingStyle.PARK
    return TradingStyle.SWING


def _resolve_styles(style_str: str | None) -> list[TradingStyle]:
    """CLI 문자열을 TradingStyle 리스트로 변환. 'all'이면 양쪽 모두."""
    if style_str and style_str.lower() in ("all", "전체"):
        return [TradingStyle.SWING, TradingStyle.POSITION, TradingStyle.GROWTH, TradingStyle.VALUE]
    return [_parse_style(style_str)]

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


# ── screener 명령 ───────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--interval",   default="1d",                  show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--style",   default="premarket", show_default=True,
              type=click.Choice(["premarket", "intraday", "all"], case_sensitive=False),
              help="스크리닝 스타일: premarket / intraday / all")
def screener(config: str, output: str, period: str, interval: str, style: str) -> None:

    np.random.seed(0)

    def make_df(trend: float, vol_spike_last: bool = False,
                bounce: bool = False) -> pd.DataFrame:
        n = 120
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        drift = np.linspace(0, trend, n)
        noise = np.cumsum(np.random.randn(n) * 0.02)
        close = np.exp(4.0 + drift + noise) * 1000
        open_ = close * (1 + np.random.randn(n) * 0.005)
        high = np.maximum(close, open_) * (1 + np.abs(np.random.randn(n)) * 0.01)
        low = np.minimum(close, open_) * (1 - np.abs(np.random.randn(n)) * 0.01)
        volume = np.random.gamma(3, 1e6, n).astype(int)
        if vol_spike_last:
            volume[-1] *= 4
        if bounce:
            # 마지막 봉: 장중 깊은 저가 후 종가 회복
            low[-1] = close[-1] * 0.93
            high[-1] = close[-1] * 1.005
        return pd.DataFrame({"Open": open_, "High": high, "Low": low,
                             "Close": close, "Volume": volume}, index=dates)

    stocks = [
        StockData("005930.KS", "삼성전자", make_df(0.5, vol_spike_last=True),
                  sector="반도체", has_news_catalyst=True,
                  is_theme_member=True, theme_name="AI 반도체"),
        StockData("000660.KS", "SK하이닉스",  make_df(0.6),
                  sector="반도체", is_theme_member=True, theme_name="AI 반도체"),
        StockData("035720.KS", "카카오", make_df(-0.4, vol_spike_last=True, bounce=True),
                  sector="인터넷"),
        StockData("051910.KS", "LG화학", make_df(0.05),
                  sector="2차전지"),
    ]
    
    stocks = []


    df = None
    fetcher = DataFetcher(period=period, interval=interval)
    for ticker in ["005930.KS", "000660.KS", "035720.KS", "051910.KS"]:
        df = fetcher.fetch(ticker)
        name, info = fetcher.info(ticker)
        stocks.append(StockData(ticker, name, df, sector=info.get("industry"))) # sector, industry
        #print(df, name, info, data)

    sector_returns = {"반도체": 8.5, "인터넷": -2.0, "2차전지": 1.5}

    premarket_screener = PreMarketScreener(sector_returns=sector_returns)

    print("=" * 70)
    print("장 시작 전 종목 선정 - 4가지 방법별 결과")
    print("=" * 70)
    results = premarket_screener.run(stocks, min_score=30.0)
    for method, res_list in results.items():
        print(f"\n▶ {method.value}")
        if not res_list:
            print("   (통과 종목 없음)")
        for r in res_list:
            print(f"   {r.summary()}")

    print("\n" + "=" * 70)
    print("종합 랭킹 (4가지 방법 점수 합산)")
    print("=" * 70)
    combined = premarket_screener.run_combined(stocks, min_score=50.0)
    for i, (ticker, name, scores) in enumerate(combined, 1):
        total = sum(scores.values())
        detail = ", ".join(f"{m.value.split('/')[0]}={s:.0f}"
                           for m, s in scores.items())
        print(f"{i}. {ticker}({name}) 합계 {total:.0f}  [{detail}]")


# ── screen 명령 ───────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--style",   default="swing", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
def screen(config: str, output: str, period: str, style: str) -> None:
    """관심 종목 일괄 스크리닝

    예시:
        python main.py screen
        python main.py screen --style all
    """
    fetcher = DataFetcher()

    styles = _resolve_styles(style)
    is_multi = len(styles) > 1

    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"설정 파일을 찾을 수 없습니다: {config}", err=True)
        sys.exit(1)

    with config_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    tickers = cfg.get("watchlist", [])
    if not tickers:
        click.echo("watchlist 항목이 없습니다.", err=True)
        sys.exit(1)

    for idx, trading_style in enumerate(styles):
        if is_multi:
            click.echo(f"\n{'━'*68}")
            click.echo(f"  ▶ [{idx+1}/{len(styles)}] {trading_style.description}")
            click.echo(f"{'━'*68}")
        
        screenings = []
        label = f"스크리닝 중 ({trading_style.value})" if len(styles) > 1 else "스크리닝 중"
        with click.progressbar(tickers, label=label, show_pos=True) as bar:
            for ticker in bar:
                name, _ = fetcher.info(ticker)
                click.echo(f"\nTicker {ticker} ({name})")
                try:
                    if trading_style in [TradingStyle.SWING, TradingStyle.POSITION]:
                        decision = ShortTermAnalyzer(
                            ticker, period=period, trading_style=trading_style,
                        ).analyze()
                    elif trading_style == TradingStyle.GROWTH:
                        decision = GrowthMomentumAnalyzer(ticker, period=period).analyze()
                    elif trading_style == TradingStyle.VALUE:
                        decision = ValueInvestingAnalyzer(ticker, period=period).analyze()
                    
                    screenings.append(decision.to_dict())
                except Exception as e:
                    click.echo(f"\n[{ticker}] 오류: {e}", err=True)

        if not screenings:
            click.echo("분석 가능한 종목이 없습니다.")
            return

        #df = pd.DataFrame(screenings).sort_values(["Style", "Score"], ascending=[True, False]).reset_index(drop=True)
        df = pd.DataFrame(screenings).sort_values(["Score"], ascending=[False]).reset_index(drop=True)
        click.echo("\n" + df.to_string(index=False))

        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        style_tag = style.lower()
        csv_path = out_dir / f"screening_{style_tag}_{date.today().strftime('%Y%m%d')}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        click.echo(f"\n결과 저장됨: {csv_path}")


if __name__ == "__main__":
    cli()
