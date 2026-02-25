"""
main.py
CLI 진입점 - Click 기반

사용 예:
    python main.py analyze 005930.KS
    python main.py analyze AAPL --save-chart
    python main.py screen --config configs/watchlist.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
import pandas as pd

# PYTHONPATH=src 설정 없이도 동작하도록 보험용 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ta_trader.analyzer import MonthlyTradingAnalyzer
from ta_trader.models import TradingStyle
from ta_trader.utils.formatter import make_decision
from ta_trader.visualization.chart import ChartVisualizer


def _parse_style(style_str: str | None) -> TradingStyle:
    """CLI 문자열을 TradingStyle로 변환"""
    if style_str is None or style_str.lower() in ("swing", "스윙"):
        return TradingStyle.SWING
    if style_str.lower() in ("position", "포지션"):
        return TradingStyle.POSITION
    return TradingStyle.SWING


@click.group()
@click.version_option("1.2.0")
def cli() -> None:
    """TA Trader - ADX/MACD/RSI/Bollinger Bands 기반 트레이딩 분석 도구"""


# ── analyze 명령 ──────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period",     default="6mo",  show_default=True, help="데이터 기간 (예: 3mo, 6mo, 1y)")
@click.option("--interval",   default="1d",   show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--style",      default="swing", show_default=True,
              type=click.Choice(["swing", "position"], case_sensitive=False),
              help="매매 스타일: swing(스윙, 단기) / position(포지션, 중장기)")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report",is_flag=True,   help="분석결과를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def analyze(ticker: str, period: str, interval: str, style: str,
            save_chart: bool, no_chart: bool, save_report: bool,
            llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """단일 종목 기술적 분석

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py analyze 005930.KS
        python main.py analyze AAPL --style position
        python main.py analyze NVDA --llm --llm-stream --save-chart
    """
    trading_style = _parse_style(style)
    analyzer = MonthlyTradingAnalyzer(ticker, period=period, interval=interval,
                                      trading_style=trading_style)
    
    if llm or llm_stream:
        try:
            decision = analyzer.analyze_with_llm(
                provider=llm_provider,
                model=llm_model, 
                stream=llm_stream)
        except Exception as e:
            click.echo(f"⚠ LLM 분석 실패: {e}", err=True)
            click.echo("  기술적 분석만 출력합니다.\n", err=True)
            decision = analyzer.analyze()
    else:
        decision = analyzer.analyze()
    
    decision_str = make_decision(decision)
    print(decision_str)

    if save_report:
        save_path = Path("reports") / f"{ticker.replace('.', '_')}_report_{decision.date.replace('-','')}.txt" if save_chart else None
        with open(save_path, "wt") as file:
            file.write(decision_str)

    if not no_chart:
        save_path = Path("reports") / f"{ticker.replace('.', '_')}_chart_{decision.date.replace('-','')}.png" if save_chart else None
        df = analyzer.calculator.dataframe if analyzer.calculator else None
        if df is not None:
            ChartVisualizer().plot(decision, df, save_path=save_path, show=not save_chart)
            if save_chart and save_path:
                click.echo(f"차트 저장됨: {save_path}")


# ── backtest 명령 ──────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period",     default="2y",   show_default=True, help="백테스팅 기간 (예: 1y, 2y, 5y, max)")
@click.option("--interval",   default="1d",   show_default=True, help="봉 간격")
@click.option("--capital",    default=10_000_000, show_default=True, type=float, help="초기 자본금 (원)")
@click.option("--commission", default=0.015,  show_default=True, type=float, help="편도 수수료 (%)")
@click.option("--slippage",   default=0.05,   show_default=True, type=float, help="슬리피지 (%)")
@click.option("--short",      is_flag=True,   help="공매도 허용")
@click.option("--min-score",  default=20.0,   show_default=True, type=float, help="진입 최소 |score| 임계값")
@click.option("--save-report",is_flag=True,   help="결과를 reports/ 폴더에 저장")
@click.option("--save-chart", is_flag=True,   help="에쿼티 커브 차트 저장")
def backtest(ticker: str, period: str, interval: str, capital: float,
             commission: float, slippage: float, short: bool, min_score: float,
             save_report: bool, save_chart: bool) -> None:
    """종목 백테스팅 실행

    TICKER: 종목 코드 (예: 005930.KS, AAPL, QQQ)

    예시:
        python main.py backtest AAPL --period 2y
        python main.py backtest 005930.KS --period 5y --capital 50000000
        python main.py backtest QQQ --period 3y --short --save-chart
    """
    from ta_trader.backtest import BacktestConfig, BacktestEngine, format_backtest_report

    config = BacktestConfig(
        initial_capital=capital,
        commission_pct=commission,
        slippage_pct=slippage,
        allow_short=short,
        min_score_entry=min_score,
    )

    try:
        engine = BacktestEngine(ticker, period=period, interval=interval, config=config)
        result = engine.run()
    except Exception as e:
        click.echo(f"❌ 백테스팅 실패: {e}", err=True)
        raise SystemExit(1) from e

    report = format_backtest_report(result)
    click.echo(report)

    if save_report or save_chart:
        out_dir = Path("reports")
        out_dir.mkdir(parents=True, exist_ok=True)

    if save_report:
        report_path = out_dir / f"{ticker.replace('.', '_')}_backtest_{period}.txt"
        report_path.write_text(report, encoding="utf-8")
        click.echo(f"보고서 저장됨: {report_path}")

    if save_chart:
        try:
            _save_equity_chart(result, out_dir / f"{ticker.replace('.', '_')}_equity_{period}.png")
        except Exception as e:
            click.echo(f"⚠ 차트 저장 실패: {e}", err=True)


def _save_equity_chart(result, save_path: Path) -> None:
    """에쿼티 커브 차트 저장"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1],
                                    sharex=True, gridspec_kw={"hspace": 0.05})

    dates = result.dates
    equity = result.equity_curve

    # 에쿼티 커브
    ax1.plot(dates, equity, color="#2962FF", linewidth=1.2, label="에쿼티")
    ax1.fill_between(dates, result.config.initial_capital, equity,
                     where=[e >= result.config.initial_capital for e in equity],
                     alpha=0.15, color="#4CAF50")
    ax1.fill_between(dates, result.config.initial_capital, equity,
                     where=[e < result.config.initial_capital for e in equity],
                     alpha=0.15, color="#FF5252")
    ax1.axhline(y=result.config.initial_capital, color="gray", linestyle="--", alpha=0.5)
    ax1.set_ylabel("자본금 (원)")
    ax1.set_title(f"{result.ticker} 백테스팅 에쿼티 커브 ({result.period})")
    ax1.legend(loc="upper left")
    ax1.grid(True, alpha=0.3)

    # 낙폭 (Drawdown)
    peak = equity[0]
    drawdown = []
    for e in equity:
        if e > peak:
            peak = e
        dd = (peak - e) / peak * 100 if peak > 0 else 0
        drawdown.append(-dd)
    ax2.fill_between(dates, 0, drawdown, color="#FF5252", alpha=0.4)
    ax2.set_ylabel("낙폭 (%)")
    ax2.set_xlabel("날짜")
    ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    fig.autofmt_xdate()

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    click.echo(f"에쿼티 차트 저장됨: {save_path}")


# ── recommend 명령 ────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--style",   default="swing", show_default=True,
              type=click.Choice(["swing", "position"], case_sensitive=False),
              help="매매 스타일: swing(스윙) / position(포지션)")
@click.option("--save-report", is_flag=True,                 help="보고서를 reports/ 폴더에 저장")
@click.option("--top-n",   default=0, type=int,              help="상위 N개만 상세 출력 (0=전체)")
def recommend(config: str, output: str, period: str, style: str, save_report: bool, top_n: int) -> None:
    """관심 종목 일괄 분석 후 매수 추천 및 근거 제시

    watchlist.yaml의 종목을 분석하고, 각 종목에 대해
    추세·모멘텀·가격위치·변동성·전략합치도를 종합 평가하여
    추천 등급(적극매수/매수/조건부매수/관망/비추천)을 부여합니다.

    예시:
        python main.py recommend
        python main.py recommend --config my_stocks.yaml --top-n 5
        python main.py recommend --style position --save-report
    """
    import yaml
    from ta_trader.recommend import RecommendationEngine, format_recommendation_report

    trading_style = _parse_style(style)

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

    decisions = []
    with click.progressbar(tickers, label="분석 중") as bar:
        for ticker in bar:
            try:
                decision = MonthlyTradingAnalyzer(
                    ticker, period=period, trading_style=trading_style,
                ).analyze()
                decisions.append(decision)
            except Exception as e:
                click.echo(f"\n[{ticker}] 오류: {e}", err=True)

    if not decisions:
        click.echo("분석 가능한 종목이 없습니다.")
        return

    engine = RecommendationEngine()
    report = engine.analyze(decisions)

    # top-n 필터링
    if top_n > 0:
        report.recommendations = report.recommendations[:top_n]
        report.buy_picks = [r for r in report.buy_picks if r.rank <= top_n]
        report.watch_list = [r for r in report.watch_list if r.rank <= top_n]
        report.avoid_list = [r for r in report.avoid_list if r.rank <= top_n]

    report_str = format_recommendation_report(report)
    click.echo(report_str)

    if save_report:
        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        from datetime import date
        report_path = out_dir / f"recommend_{style}_{date.today().strftime('%Y%m%d')}.txt"
        report_path.write_text(report_str, encoding="utf-8")
        click.echo(f"보고서 저장됨: {report_path}")


# ── screen 명령 ───────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--style",   default="swing", show_default=True,
              type=click.Choice(["swing", "position"], case_sensitive=False),
              help="매매 스타일: swing(스윙) / position(포지션)")
def screen(config: str, output: str, period: str, style: str) -> None:
    """관심 종목 일괄 스크리닝"""
    import yaml

    trading_style = _parse_style(style)

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

    rows = []
    with click.progressbar(tickers, label="스크리닝 중") as bar:
        for ticker in bar:
            try:
                decision = MonthlyTradingAnalyzer(
                    ticker, period=period, trading_style=trading_style,
                ).analyze()
                rows.append(decision.to_dict())
            except Exception as e:
                click.echo(f"\n[{ticker}] 오류: {e}", err=True)

    if not rows:
        click.echo("분석 가능한 종목이 없습니다.")
        return

    df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    click.echo("\n" + df.to_string(index=False))

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    from datetime import date
    csv_path = out_dir / f"screening_{date.today().strftime('%Y%m%d')}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    click.echo(f"\n결과 저장됨: {csv_path}")


if __name__ == "__main__":
    cli()
