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
import pandas as pd
import sys
import yaml

from datetime import date
from pathlib import Path

# PYTHONPATH=src 설정 없이도 동작하도록 보험용 경로 추가
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ta_trader.analyzers.growth import GrowthMomentumAnalyzer
from ta_trader.analyzers.short import ShortTermAnalyzer
from ta_trader.analyzers.value import ValueInvestingAnalyzer
from ta_trader.analyzers.swing import SwingTradingAnalyzer
from ta_trader.analyzers.position import PositionTradingAnalyzer
from ta_trader.formatters.short import make_decision, make_summary
from ta_trader.formatters.growth import format_growth_report, format_growth_result
from ta_trader.formatters.value import format_value_report, format_value_result
from ta_trader.formatters.swing import format_swing_result, format_swing_report
from ta_trader.formatters.position import format_position_result, format_position_report
from ta_trader.models import TradingStyle
from ta_trader.recommend import RecommendationEngine, format_recommendation_report
from ta_trader.visualization.chart import ChartVisualizer
from ta_trader.visualization.swing import SwingChartVisualizer
from ta_trader.visualization.position import PositionChartVisualizer
from ta_trader.visualization.growth import GrowthChartVisualizer
from ta_trader.visualization.value import ValueChartVisualizer

from ta_trader.data.krx_stock_fetcher import KRXStockFetcher

MARKETS = ["KOSPI", "KOSDAQ", "US"]

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


# ── analyze 명령 ──────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--period",     default="6mo",  show_default=True, help="데이터 기간 (예: 3mo, 6mo, 1y)")
@click.option("--interval",   default="1d",   show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--style",      default="swing", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / all(양쪽 모두)")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report",is_flag=True,   help="분석결과를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def analyze(ticker: str, config: str, period: str, interval: str, style: str,
            save_chart: bool, no_chart: bool, save_report: bool,
            llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """단일 종목 기술적 분석

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py analyze 005930.KS
        python main.py analyze AAPL --style position
        python main.py analyze NVDA --style all
        python main.py analyze KOSPI --style all --save-report --save-chart
        python main.py analyze KOSDAQ --save-report --save-chart
        python main.py analyze US --save-report --save-chart
        python main.py analyze NVDA --llm --llm-stream --save-chart
    """
    krx_fetcher = KRXStockFetcher()
    krx_fetcher.load()

    styles = _resolve_styles(style)
    is_multi = len(styles) > 1

    config_path = Path(config)
    if ticker in MARKETS:
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
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        tickers = [ticker]

    for idx, trading_style in enumerate(styles):
        if is_multi:
            click.echo(f"\n{'━'*68}")
            click.echo(f"  ▶ [{idx+1}/{len(styles)}] {trading_style.description}")
            click.echo(f"{'━'*68}")

        label = f"분석 중 ({trading_style.value})" if is_multi else "분석 중"
        with click.progressbar(tickers, label=label, show_pos=True) as bar:
            for ticker in bar:
                info = krx_fetcher.get_info(ticker)
                name = info.name if info else ""
                click.echo(f"\nTicker {ticker} ({name})")
                analyzer = ShortTermAnalyzer(ticker, period=period, interval=interval,
                                                trading_style=trading_style)

                if llm or llm_stream:
                    try:
                        decision = analyzer.analyze_with_llm(
                            provider=llm_provider,
                            model=llm_model,
                            stream=llm_stream)
                    #except Exception as e:
                    #    click.echo(f"⚠ LLM 분석 실패: {e}", err=True)
                    #    click.echo("  기술적 분석만 출력합니다.\n", err=True)
                    #    decision = analyzer.analyze()
                    finally:
                        pass
                else:
                    try:
                        decision = analyzer.analyze()
                    except Exception as e:
                        click.echo(f"⚠ 기술 분석 실패: {e}", err=True)
                        continue
                    finally:
                        pass

                decision_str = make_decision(decision)
                print(decision_str)

                style_tag = trading_style.name.lower()

                if save_report:
                    out_dir = Path("reports")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    report_path = out_dir / f"{ticker.replace('.', '_')}_{style_tag}_{decision.date.replace('-','')}.txt"
                    report_path.write_text(decision_str, encoding="utf-8")
                    click.echo(f"보고서 저장됨: {report_path}")

                    summary_path = out_dir / f"summary_{style_tag}_{decision.date.replace('-','')}.txt"
                    with summary_path.open("a", encoding="utf-8") as file:
                        file.write(make_summary(decision) + "\n")

                if not no_chart:
                    chart_path = (
                        Path("reports") / f"{ticker.replace('.', '_')}_{style_tag}_{decision.date.replace('-','')}.png"
                        if save_chart else None
                    )
                    df = analyzer.calculator.dataframe if analyzer.calculator else None
                    if df is not None:
                        ChartVisualizer().plot(decision, df, save_path=chart_path, show=not save_chart)
                        if save_chart and chart_path:
                            click.echo(f"차트 저장됨: {chart_path}")


# ── recommend 명령 ────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--style",   default="swing", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
@click.option("--save-report", is_flag=True,                 help="보고서를 reports/ 폴더에 저장")
@click.option("--top-n",   default=0, type=int,              help="상위 N개만 상세 출력 (0=전체)")
@click.option("--min-score", default=0.0, type=float, help="최소 점수 필터")
def recommend(config: str, output: str, period: str, style: str, save_report: bool, top_n: int, min_score: float) -> None:
    """관심 종목 일괄 분석 후 매수 추천 및 근거 제시

    watchlist.yaml의 종목을 분석하고, 각 종목에 대해
    추세·모멘텀·가격위치·변동성·전략합치도를 종합 평가하여
    추천 등급(적극매수/매수/조건부매수/관망/비추천)을 부여합니다.

    예시:
        python main.py recommend
        python main.py recommend --config my_stocks.yaml --top-n 5
        python main.py recommend --style position --save-report
    """
    krx_fetcher = KRXStockFetcher()
    krx_fetcher.load()

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

        decisions = []
        label = f"분석 중 ({trading_style.value})" if is_multi else "분석 중"
        with click.progressbar(tickers, label=label, show_pos=True) as bar:
            for ticker in bar:
                info = krx_fetcher.get_info(ticker)
                name = info.name if info else ""
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
                    
                    decisions.append(decision)
                except Exception as e:
                    click.echo(f"\n[{ticker}] 오류: {e}", err=True)
                #finally:
                #    pass

        if not decisions:
            click.echo("분석 가능한 종목이 없습니다.")
            continue

        if trading_style in [TradingStyle.SWING, TradingStyle.POSITION]:
            engine = RecommendationEngine()
            report = engine.analyze(decisions)

            # top-n 필터링
            if top_n > 0:
                report.recommendations = report.recommendations[:top_n]
                report.buy_picks = [r for r in report.buy_picks if r.rank <= top_n]
                report.watch_list = [r for r in report.watch_list if r.rank <= top_n]
                report.avoid_list = [r for r in report.avoid_list if r.rank <= top_n]

            report_str = format_recommendation_report(trading_style, report)
        elif trading_style == TradingStyle.GROWTH:
            # 점수 필터링 및 정렬
            decisions.sort(key=lambda r: r.total_score, reverse=True)
            if min_score > 0:
                decisions = [r for r in decisions if r.total_score >= min_score]
            if top_n > 0:
                decisions = decisions[:top_n]

            # recommend 형식 보고서 출력
            report_str = format_growth_report(decisions)
        elif trading_style == TradingStyle.VALUE:
            # 점수 필터링 및 정렬
            decisions.sort(key=lambda r: r.total_score, reverse=True)
            if min_score > 0:
                decisions = [r for r in decisions if r.total_score >= min_score]
            if top_n > 0:
                decisions = decisions[:top_n]

            # recommend 형식 보고서 출력
            report_str = format_value_report(decisions)
        
        click.echo(report_str)

        if save_report:
            out_dir = Path(output)
            out_dir.mkdir(parents=True, exist_ok=True)
            from datetime import date
            style_tag = trading_style.name.lower()
            report_path = out_dir / f"recommend_{style_tag}_{date.today().strftime('%Y%m%d')}.txt"
            report_path.write_text(report_str, encoding="utf-8")
            click.echo(f"보고서 저장됨: {report_path}")


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
    krx_fetcher = KRXStockFetcher()
    krx_fetcher.load()

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
                info = krx_fetcher.get_info(ticker)
                name = info.name if info else ""
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
        #df = pd.DataFrame(screenings).reset_index(drop=True)
        #print(df.columns)
        click.echo("\n" + df.to_string(index=False))

        out_dir = Path(output)
        out_dir.mkdir(parents=True, exist_ok=True)
        style_tag = style.lower()
        csv_path = out_dir / f"screening_{style_tag}_{date.today().strftime('%Y%m%d')}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        click.echo(f"\n결과 저장됨: {csv_path}")


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


# ── growth 명령 ───────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period", default="1y", show_default=True, help="데이터 기간 (예: 1y, 2y)")
@click.option("--style", default="growth", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report", is_flag=True, help="보고서를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def growth(ticker: str, period: str, style: str,
        config: str, save_chart: bool, no_chart: bool, save_report: bool,
        llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """100% 상승 후보 6단계 분석 (단일 종목)

    이익가속·스테이지·기술적진입·리스크·건강도를 종합 평가하여
    GrowthScore (0~100)와 등급(적극매수~부적합)을 산출합니다.

    TICKER: 종목 코드 (예: AAPL, NVDA, 005930.KS)

    예시:
        python main.py growth NVDA
        python main.py growth AAPL --period 2y --save-report
    """
    styles = _resolve_styles(style)
    is_multi = len(styles) > 1

    fetcher = KRXStockFetcher()
    fetcher.load()

    tickers = None
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
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        info = fetcher.get_info(ticker)
        #click.echo(f"Info: {info}", err=True)
        if not info:
            tickers = [ticker]
        else:
            tickers = [info.yahoo_ticker]
    
    with click.progressbar(tickers) as bar:
        for ticker in bar:
            try:
                analyzer = GrowthMomentumAnalyzer(ticker, period=period)

                if llm or llm_stream:
                    result = analyzer.analyze_with_llm(
                            provider=llm_provider,
                            model=llm_model,
                            stream=llm_stream)
                else:
                    result = analyzer.analyze()

                report_str = format_growth_result(result)
                click.echo(report_str)

                stock_name = result.name.replace(" ", "_")

                if save_report:
                    out_dir = Path("reports")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    report_path = out_dir / f"{ticker.replace('.', '_')}_{style}_{result.date.replace('-','')}_{stock_name}.txt"
                    report_path.write_text(report_str, encoding="utf-8")
                    click.echo(f"보고서 저장됨: {report_path}")

                if not no_chart:
                    chart_path = (
                        Path("reports") / f"{ticker.replace('.', '_')}_{style}_{result.date.replace('-','')}_{stock_name}.png"
                        if save_chart else None
                    )
                    df = analyzer.calculator.dataframe if analyzer.calculator else None
                    if df is not None:
                        GrowthChartVisualizer().plot(result, df, save_path=chart_path, show=not save_chart)
                        if save_chart and chart_path:
                            click.echo(f"차트 저장됨: {chart_path}")
            #except Exception as e:
            #    click.echo(f"❌ 분석 실패 [{ticker}]: {e}", err=True)
            #    raise SystemExit(1) from e
            finally:
                pass


# ── growth-screen 명령 ────────────────────────────────────
@cli.command("growth-screen")
@click.option("--config", default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output", default="reports", show_default=True, help="결과 저장 디렉토리")
@click.option("--period", default="1y", show_default=True)
@click.option("--top-n", default=0, type=int, help="상위 N개만 출력 (0=전체)")
@click.option("--min-score", default=0.0, type=float, help="최소 점수 필터")
@click.option("--save-report", is_flag=True, help="보고서를 reports/ 폴더에 저장")
def growth_screen(config: str, output: str, period: str, top_n: int, min_score: float, save_report: bool) -> None:
    """관심 종목 일괄 Growth 스크리닝

    watchlist.yaml의 종목을 6단계 프로세스로 분석하여
    GrowthScore 기준으로 정렬합니다.

    예시:
        python main.py growth-screen
        python main.py growth-screen --config my_stocks.yaml --top-n 10
        python main.py growth-screen --min-score 50
    """
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

    results = []
    with click.progressbar(tickers, label="Growth 스크리닝 중") as bar:
        for ticker in bar:
            try:
                result = GrowthMomentumAnalyzer(ticker, period=period).analyze()
                results.append(result)
            except Exception as e:
                click.echo(f"\n[{ticker}] 오류: {e}", err=True)

    if not results:
        click.echo("분석 가능한 종목이 없습니다.")
        return

    # 점수 필터링 및 정렬
    results.sort(key=lambda r: r.total_score, reverse=True)
    if min_score > 0:
        results = [r for r in results if r.total_score >= min_score]
    if top_n > 0:
        results = results[:top_n]

    # recommend 형식 보고서 출력
    report_str = format_growth_report(results)
    click.echo(report_str)

    # 보고서/CSV 저장
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if save_report:
        from datetime import date
        rpt_path = out_dir / f"recommend_growth_{date.today().strftime('%Y%m%d')}.txt"
        rpt_path.write_text(report_str, encoding="utf-8")
        click.echo(f"보고서 저장됨: {rpt_path}")

    rows = [r.to_dict() for r in results]
    df = pd.DataFrame(rows)
    from datetime import date
    csv_path = out_dir / f"recommend_growth_{date.today().strftime('%Y%m%d')}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    click.echo(f"결과 저장됨: {csv_path}")


# ── value 명령 ────────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period", default="2y", show_default=True, help="데이터 기간 (예: 2y, 3y)")
@click.option("--style", default="value", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report", is_flag=True, help="보고서를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def value(ticker: str, period: str, style: str,
        config: str, save_chart: bool, no_chart: bool, save_report: bool,
        llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """가치 투자 5단계 분석 (단일 종목)

    밸류에이션·수익성·재무건전성·안전마진·진입타이밍을 종합 평가하여
    ValueScore (0~100)와 등급(적극매수~부적합)을 산출합니다.

    TICKER: 종목 코드 (예: AAPL, JNJ, 005930.KS)

    예시:
        python main.py value AAPL
        python main.py value 005930.KS --period 3y --save-report
    """
    styles = _resolve_styles(style)
    is_multi = len(styles) > 1

    fetcher = KRXStockFetcher()
    fetcher.load()

    tickers = None
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
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        info = fetcher.get_info(ticker)
        #click.echo(f"Info: {info}", err=True)
        if not info:
            tickers = [ticker]
        else:
            tickers = [info.yahoo_ticker]
    
    with click.progressbar(tickers) as bar:
        for ticker in bar:
            try:
                analyzer = ValueInvestingAnalyzer(ticker, period=period)

                if llm or llm_stream:
                    result = analyzer.analyze_with_llm(
                            provider=llm_provider,
                            model=llm_model,
                            stream=llm_stream)
                else:
                    result = analyzer.analyze()

                report_str = format_value_result(result)
                click.echo(report_str)

                stock_name = result.name.replace(" ", "_")

                if save_report:
                    out_dir = Path("reports")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    report_path = out_dir / f"{ticker.replace('.', '_')}_{style}_{result.date.replace('-','')}_{stock_name}.txt"
                    report_path.write_text(report_str, encoding="utf-8")
                    click.echo(f"보고서 저장됨: {report_path}")

                if not no_chart:
                    chart_path = (
                        Path("reports") / f"{ticker.replace('.', '_')}_{style}_{result.date.replace('-','')}_{stock_name}.png"
                        if save_chart else None
                    )
                    df = analyzer.calculator.dataframe if analyzer.calculator else None
                    if df is not None:
                        ValueChartVisualizer().plot(result, df, save_path=chart_path, show=not save_chart)
                        if save_chart and chart_path:
                            click.echo(f"차트 저장됨: {chart_path}")
            #except Exception as e:
            #    click.echo(f"❌ 분석 실패 [{ticker}]: {e}", err=True)
            #    raise SystemExit(1) from e
            finally:
                pass


# ── value-screen 명령 ─────────────────────────────────────
@cli.command("value-screen")
@click.option("--config", default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output", default="reports", show_default=True, help="결과 저장 디렉토리")
@click.option("--period", default="2y", show_default=True)
@click.option("--top-n", default=0, type=int, help="상위 N개만 출력 (0=전체)")
@click.option("--min-score", default=0.0, type=float, help="최소 점수 필터")
@click.option("--save-report", is_flag=True, help="보고서를 reports/ 폴더에 저장")
def value_screen(config: str, output: str, period: str, top_n: int, min_score: float, save_report: bool) -> None:
    """관심 종목 일괄 Value 스크리닝

    watchlist.yaml의 종목을 5단계 가치 투자 프로세스로 분석하여
    ValueScore 기준으로 정렬합니다.

    예시:
        python main.py value-screen
        python main.py value-screen --config my_stocks.yaml --top-n 10
        python main.py value-screen --min-score 50
    """
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

    results = []
    with click.progressbar(tickers, label="Value 스크리닝 중") as bar:
        for ticker in bar:
            try:
                result = ValueInvestingAnalyzer(ticker, period=period).analyze()
                results.append(result)
            except Exception as e:
                click.echo(f"\n[{ticker}] 오류: {e}", err=True)

    if not results:
        click.echo("분석 가능한 종목이 없습니다.")
        return

    # 점수 필터링 및 정렬
    results.sort(key=lambda r: r.total_score, reverse=True)
    if min_score > 0:
        results = [r for r in results if r.total_score >= min_score]
    if top_n > 0:
        results = results[:top_n]

    # recommend 형식 보고서 출력
    report_str = format_value_report(results)
    click.echo(report_str)

    # 보고서/CSV 저장
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if save_report:
        from datetime import date
        rpt_path = out_dir / f"recommend_value_{date.today().strftime('%Y%m%d')}.txt"
        rpt_path.write_text(report_str, encoding="utf-8")
        click.echo(f"보고서 저장됨: {rpt_path}")

    rows = [r.to_dict() for r in results]
    df = pd.DataFrame(rows)
    from datetime import date
    csv_path = out_dir / f"recommend_value_{date.today().strftime('%Y%m%d')}.csv"
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    click.echo(f"결과 저장됨: {csv_path}")


# ── agent-analyze 명령 ─────────────────────────────────────
@cli.command("agent-analyze")
@click.argument("ticker")
@click.option("--period",     default="6mo",  show_default=True, help="데이터 기간")
@click.option("--interval",   default="1d",   show_default=True, help="봉 간격")
@click.option("--style",      default="swing", show_default=True,
              type=click.Choice(["swing", "position", "all"], case_sensitive=False),
              help="매매 스타일")
@click.option("--capital",    default=10_000_000, show_default=True, type=float,
              help="총 투자 자본금 (원)")
@click.option("--risk-pct",   default=2.0, show_default=True, type=float,
              help="1회 거래 최대 리스크 (%)")
@click.option("--sizing",     default="fixed_ratio", show_default=True,
              type=click.Choice(["fixed_ratio", "kelly", "equal_weight"]),
              help="포지션 사이징 방법")
@click.option("--llm",        is_flag=True,   help="LLM 해석 추가")
@click.option("--llm-stream", is_flag=True,   help="LLM 스트리밍 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False))
@click.option("--llm-model",  default=None,   help="LLM 모델명")
@click.option("--save-report", is_flag=True,  help="보고서 저장")
@click.option("--save-chart", is_flag=True,   help="차트 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
def agent_analyze(ticker: str, period: str, interval: str, style: str,
                  capital: float, risk_pct: float, sizing: str,
                  llm: bool, llm_stream: bool, llm_provider: str | None,
                  llm_model: str | None, save_report: bool,
                  save_chart: bool, no_chart: bool) -> None:
    """4-에이전트 파이프라인으로 단일 종목 분석

    Data Agent → Strategy Agent → Risk Agent 파이프라인을 순차 실행하여
    매매 시그널 + 리스크 검증 결과를 출력합니다.

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py agent-analyze AAPL
        python main.py agent-analyze 005930.KS --capital 50000000 --sizing kelly
        python main.py agent-analyze NVDA --llm --llm-stream --style all
    """
    from ta_trader.agents import AgentOrchestrator, OrchestratorConfig
    from ta_trader.agents.risk_agent import RiskConfig
    from ta_trader.formatters.agent import format_pipeline_result

    styles = _resolve_styles(style)

    for idx, trading_style in enumerate(styles):
        if len(styles) > 1:
            click.echo(f"\n{'━'*68}")
            click.echo(f"  ▶ [{idx+1}/{len(styles)}] {trading_style.description}")
            click.echo(f"{'━'*68}")

        risk_cfg = RiskConfig(
            total_capital=capital,
            max_risk_per_trade_pct=risk_pct / 100,
            sizing_method=sizing,
        )

        config = OrchestratorConfig(
            trading_style=trading_style,
            period=period,
            interval=interval,
            use_llm=(llm or llm_stream),
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_stream=llm_stream,
            risk_config=risk_cfg,
        )

        orchestrator = AgentOrchestrator(config=config)

        try:
            result = orchestrator.run(ticker)
        except Exception as e:
            click.echo(f"❌ 분석 실패: {e}", err=True)
            raise SystemExit(1) from e
        #finally:
        #    pass

        output = format_pipeline_result(result)
        click.echo(output)

        style_tag = trading_style.name.lower()

        if save_report:
            out_dir = Path("reports")
            out_dir.mkdir(parents=True, exist_ok=True)
            report_path = out_dir / f"{ticker.replace('.', '_')}_agent_{style_tag}_{result.date.replace('-','')}.txt"
            report_path.write_text(output, encoding="utf-8")
            click.echo(f"보고서 저장됨: {report_path}")

        if not no_chart:
            decision = result.to_trading_decision()
            if decision and result.market_data:
                chart_path = (
                    Path("reports") / f"{ticker.replace('.', '_')}_chart_{style_tag}_{result.date.replace('-','')}.png"
                    if save_chart else None
                )
                ChartVisualizer().plot(
                    decision, result.market_data.ohlcv_df,
                    save_path=chart_path, show=not save_chart,
                )
                if save_chart and chart_path:
                    click.echo(f"차트 저장됨: {chart_path}")


# ── agent-screen 명령 ──────────────────────────────────────
@cli.command("agent-screen")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
@click.option("--style",   default="swing", show_default=True,
              type=click.Choice(["swing", "position", "all"], case_sensitive=False))
@click.option("--capital",    default=10_000_000, show_default=True, type=float,
              help="총 투자 자본금 (원)")
@click.option("--risk-pct",   default=2.0, show_default=True, type=float,
              help="1회 거래 최대 리스크 (%)")
@click.option("--sizing",     default="fixed_ratio", show_default=True,
              type=click.Choice(["fixed_ratio", "kelly", "equal_weight"]))
@click.option("--top-n",   default=0, type=int,              help="상위 N개만 출력")
@click.option("--save-report", is_flag=True,                 help="보고서 저장")
def agent_screen(config: str, output: str, period: str, style: str,
                 capital: float, risk_pct: float, sizing: str,
                 top_n: int, save_report: bool) -> None:
    """4-에이전트 파이프라인으로 복수 종목 스크리닝

    watchlist.yaml의 종목을 4-에이전트 파이프라인으로 분석하고,
    리스크 검증 결과를 포함한 종합 리포트를 출력합니다.

    예시:
        python main.py agent-screen
        python main.py agent-screen --capital 50000000 --sizing kelly --top-n 5
        python main.py agent-screen --style all --save-report
    """
    import yaml
    from ta_trader.agents import AgentOrchestrator, OrchestratorConfig
    from ta_trader.agents.risk_agent import RiskConfig
    from ta_trader.formatters.agent import format_screening_results

    styles = _resolve_styles(style)

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
        if len(styles) > 1:
            click.echo(f"\n{'━'*68}")
            click.echo(f"  ▶ [{idx+1}/{len(styles)}] {trading_style.description}")
            click.echo(f"{'━'*68}")

        risk_cfg = RiskConfig(
            total_capital=capital,
            max_risk_per_trade_pct=risk_pct / 100,
            sizing_method=sizing,
        )

        orch_config = OrchestratorConfig(
            trading_style=trading_style,
            period=period,
            risk_config=risk_cfg,
        )

        orchestrator = AgentOrchestrator(config=orch_config)

        results = []
        label = f"에이전트 분석 중 ({trading_style.value})" if len(styles) > 1 else "에이전트 분석 중"
        with click.progressbar(tickers, label=label) as bar:
            for ticker in bar:
                try:
                    result = orchestrator.run(ticker)
                    results.append(result)
                except Exception as e:
                    click.echo(f"\n[{ticker}] 오류: {e}", err=True)

        if not results:
            click.echo("분석 가능한 종목이 없습니다.")
            continue

        # 점수 기준 정렬
        results.sort(
            key=lambda r: r.trade_signal.composite_score if r.trade_signal else -999,
            reverse=True,
        )
        if top_n > 0:
            results = results[:top_n]

        report_str = format_screening_results(results)
        click.echo(report_str)

        if save_report:
            out_dir = Path(output)
            out_dir.mkdir(parents=True, exist_ok=True)
            from datetime import date
            style_tag = trading_style.name.lower()
            report_path = out_dir / f"agent_screen_{style_tag}_{date.today().strftime('%Y%m%d')}.txt"
            report_path.write_text(report_str, encoding="utf-8")
            click.echo(f"보고서 저장됨: {report_path}")

        # CSV 저장
        rows = []
        for r in results:
            ts = r.trade_signal
            ra = r.risk_approval
            if ts:
                row = {
                    "Ticker": ts.ticker,
                    "Name": ts.name,
                    "Price": ts.current_price,
                    "Score": ts.composite_score,
                    "Signal": ts.signal.value,
                    "Side": ts.side.value,
                    "Regime": ts.market_regime.value,
                    "Strategy": ts.strategy_type.value,
                    "RR_Ratio": ts.suggested_rr_ratio,
                    "Approved": ra.approved if ra else False,
                    "Shares": ra.position_size.shares if ra and ra.position_size else 0,
                    "RiskPct": ra.position_size.risk_pct if ra and ra.position_size else 0,
                }
                rows.append(row)

        if rows:
            df = pd.DataFrame(rows)
            out_dir = Path(output)
            out_dir.mkdir(parents=True, exist_ok=True)
            from datetime import date
            style_tag = trading_style.name.lower()
            csv_path = out_dir / f"agent_screen_{style_tag}_{date.today().strftime('%Y%m%d')}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            click.echo(f"CSV 저장됨: {csv_path}")


# ── agent-trade 명령 (시뮬레이션) ──────────────────────────
@cli.command("agent-trade")
@click.argument("ticker")
@click.option("--period",     default="6mo",  show_default=True, help="데이터 기간")
@click.option("--style",      default="swing", show_default=True,
              type=click.Choice(["swing", "position"], case_sensitive=False))
@click.option("--capital",    default=10_000_000, show_default=True, type=float,
              help="총 투자 자본금 (원)")
@click.option("--risk-pct",   default=2.0, show_default=True, type=float,
              help="1회 거래 최대 리스크 (%)")
@click.option("--sizing",     default="fixed_ratio", show_default=True,
              type=click.Choice(["fixed_ratio", "kelly", "equal_weight"]))
@click.option("--slippage",   default=0.05, show_default=True, type=float,
              help="시뮬레이션 슬리피지 (%)")
@click.option("--commission", default=0.015, show_default=True, type=float,
              help="편도 수수료 (%)")
def agent_trade(ticker: str, period: str, style: str,
                capital: float, risk_pct: float, sizing: str,
                slippage: float, commission: float) -> None:
    """4-에이전트 전체 파이프라인 (체결 시뮬레이션 포함)

    Data → Strategy → Risk → Execution 전체 파이프라인을 실행하여
    시뮬레이션 체결 결과까지 출력합니다.

    TICKER: 종목 코드 (예: AAPL, 005930.KS)

    예시:
        python main.py agent-trade AAPL
        python main.py agent-trade NVDA --capital 50000000 --sizing kelly
    """
    from ta_trader.agents import AgentOrchestrator, OrchestratorConfig
    from ta_trader.agents.risk_agent import RiskConfig
    from ta_trader.agents.execution_agent import DryRunBackend, ExecutionConfig
    from ta_trader.formatters.agent import format_pipeline_result

    trading_style = _parse_style(style)

    risk_cfg = RiskConfig(
        total_capital=capital,
        max_risk_per_trade_pct=risk_pct / 100,
        sizing_method=sizing,
    )

    exec_cfg = ExecutionConfig(dry_run=True)
    backend = DryRunBackend(slippage_pct=slippage, commission_pct=commission)

    config = OrchestratorConfig(
        trading_style=trading_style,
        period=period,
        risk_config=risk_cfg,
        execution_config=exec_cfg,
        execution_backend=backend,
        execute_trades=True,
    )

    orchestrator = AgentOrchestrator(config=config)

    try:
        result = orchestrator.run(ticker)
    except Exception as e:
        click.echo(f"❌ 실행 실패: {e}", err=True)
        raise SystemExit(1) from e

    output = format_pipeline_result(result)
    click.echo(output)


# ── swing 명령 (6단계 스윙 트레이딩) ──────────────────────

@cli.command()
@click.argument("ticker")
@click.option("--period", default="1y", show_default=True, help="데이터 기간 (예: 6mo, 1y, 2y)")
@click.option("--interval", default="1d", show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--capital", default=10_000_000, show_default=True, type=float,
              help="투입 자본금 (원)")
@click.option("--risk-pct", default=0.02, show_default=True, type=float,
              help="1회 거래 최대 손실 비율 (0.02 = 2%)")
@click.option("--style", default="swing", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report",is_flag=True,   help="분석결과를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def swing(ticker: str, period: str, interval: str, capital: float, risk_pct: float, style: str,
            config: str, save_chart: bool, no_chart: bool, save_report: bool,
            llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """스윙 트레이딩 6단계 분석 (단일 종목)

    6단계 프로세스:
      1. 시장 환경 판단  (ADX, SMA200, 정배열, ATR%)
      2. 종목 스크리닝   (거래량, RS, +DI/-DI, 정배열)
      3. 진입 타이밍     (MACD, RSI, BB, 피보나치, EMA)
      4. 포지션 사이징   (ATR 손절/익절, R배수, 자본 배분)
      5. 익절/청산 전략  (트레일링 스톱, RSI/MACD/BB)
      6. 매매 복기       (종합 요약)

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py swing 005930.KS
        python main.py swing AAPL --capital 50000000
        python main.py swing NVDA --period 2y --risk-pct 0.01
    """
    styles = _resolve_styles(style)
    is_multi = len(styles) > 1

    fetcher = KRXStockFetcher()
    fetcher.load()

    tickers = None
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
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        info = fetcher.get_info(ticker)
        #click.echo(f"Info: {info}", err=True)
        if not info:
            tickers = [ticker]
        else:
            tickers = [info.yahoo_ticker]
    
    with click.progressbar(tickers) as bar:
        for ticker in bar:
            try:
                analyzer = SwingTradingAnalyzer(
                    ticker, period=period, interval=interval,
                    capital=capital, risk_pct=risk_pct,
                )

                if llm or llm_stream:
                    decision = analyzer.analyze_with_llm(
                            provider=llm_provider,
                            model=llm_model,
                            stream=llm_stream)
                else:
                    decision = analyzer.analyze()
                
                decision_str = format_swing_result(decision)
                click.echo(decision_str)

                stock_name = decision.name.replace(" ", "_")

                if save_report:
                    out_dir = Path("reports")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    report_path = out_dir / f"{ticker.replace('.', '_')}_{style}_{decision.date.replace('-','')}_{stock_name}.txt"
                    report_path.write_text(decision_str, encoding="utf-8")
                    click.echo(f"보고서 저장됨: {report_path}")
                
                if not no_chart:
                    chart_path = (
                        Path("reports") / f"{ticker.replace('.', '_')}_{style}_{decision.date.replace('-','')}_{stock_name}.png"
                        if save_chart else None
                    )
                    df = analyzer.calculator.dataframe if analyzer.calculator else None
                    if df is not None:
                        #ChartVisualizer().plot(decision, df, save_path=chart_path, show=not save_chart)
                        SwingChartVisualizer().plot(decision, df, save_path=chart_path, show=not save_chart)
                        if save_chart and chart_path:
                            click.echo(f"차트 저장됨: {chart_path}")
            except Exception as e:
                click.echo(f"❌ 스윙 분석 실패 [{ticker}]: {e}", err=True)
                #raise SystemExit(1) from e
                continue
            finally:
                pass


@cli.command("swing-screen")
@click.option("--config", default="configs/watchlist.yaml", show_default=True,
              help="종목 목록 YAML")
@click.option("--market", default=None,
              type=click.Choice(["KOSPI", "KOSDAQ", "US"], case_sensitive=False),
              help="시장 필터 (KOSPI / KOSDAQ / US)")
@click.option("--period", default="1y", show_default=True, help="데이터 기간")
@click.option("--interval", default="1d", show_default=True, help="봉 간격")
@click.option("--capital", default=10_000_000, show_default=True, type=float,
              help="투입 자본금 (원)")
@click.option("--risk-pct", default=0.02, show_default=True, type=float,
              help="1회 거래 최대 손실 비율")
@click.option("--top", default=10, show_default=True, type=int,
              help="상위 N개 종목만 출력")
def swing_screen(config: str, market: str | None, period: str, interval: str,
                 capital: float, risk_pct: float, top: int) -> None:
    """스윙 트레이딩 6단계 복수 종목 스크리닝

    watchlist.yaml의 종목을 일괄 분석하여 스윙 매수 적합 종목을 선별합니다.

    예시:
        python main.py swing-screen
        python main.py swing-screen --market KOSPI --capital 50000000
        python main.py swing-screen --config my_list.yaml --top 5
    """
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"설정 파일을 찾을 수 없습니다: {config}", err=True)
        sys.exit(1)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    tickers = cfg.get("watchlist", [])
    if not tickers:
        click.echo("watchlist 항목이 없습니다.", err=True)
        sys.exit(1)

    # 시장 필터
    if market:
        MARKET_FILTERS = {
            "KOSPI": lambda t: ".KS" in t,
            "KOSDAQ": lambda t: ".KQ" in t,
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        filt = MARKET_FILTERS.get(market.upper())
        if filt:
            tickers = [t for t in tickers if filt(t)]

    results = []
    with click.progressbar(tickers, label="스윙 스크리닝 중") as bar:
        for ticker in bar:
            try:
                analyzer = SwingTradingAnalyzer(
                    ticker, period=period, interval=interval,
                    capital=capital, risk_pct=risk_pct,
                )
                result = analyzer.analyze()
                results.append(result)
            except Exception as e:
                click.echo(f"\n⚠ {ticker} 실패: {e}", err=True)

    # 상위 N개
    results.sort(key=lambda r: r.overall_score, reverse=True)
    output = format_swing_report(results[:top])
    click.echo(output)

    # 개별 상세 (매수 가능 종목만)
    actionable = [r for r in results[:top] if r.is_actionable]
    if actionable:
        click.echo(f"\n{'═'*70}")
        click.echo(f"  매수 실행 가능 종목 상세 ({len(actionable)}개)")
        click.echo(f"{'═'*70}")
        for r in actionable:
            click.echo(format_swing_result(r))


# ── position 명령 (7단계 포지션 트레이딩) ─────────────────

@cli.command()
@click.argument("ticker")
@click.option("--period", default="1y", show_default=True, help="데이터 기간 (예: 6mo, 1y, 2y)")
@click.option("--interval", default="1d", show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--capital", default=10_000_000, show_default=True, type=float,
              help="투입 자본금 (원)")
@click.option("--risk-pct", default=0.02, show_default=True, type=float,
              help="1회 거래 최대 손실 비율 (0.02 = 2%)")
@click.option("--style", default="position", show_default=True,
              type=click.Choice(["swing", "position", "growth", "value", "all"], case_sensitive=False),
              help="매매 스타일: swing / position / growth / value / all(양쪽 모두)")
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report", is_flag=True, help="분석결과를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "google"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def position(ticker: str, period: str, interval: str, capital: float, risk_pct: float, style: str,
             config: str, save_chart: bool, no_chart: bool, save_report: bool,
             llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """포지션 트레이딩 7단계 분석 (단일 종목)

    7단계 프로세스:
      1. 시장 환경 판단   (200MA, ADX, 정배열, SMA50>SMA200)
      2. 섹터/테마 선정   (섹터 RS, 자금 흐름)
      3. 종목 선정        (RS, Stage2, ADX≥25, 52주 신고가)
      4. 매수 타이밍      (MA Pullback, Breakout, MACD, BB Squeeze)
      5. 리스크 관리      (ATR×2.5 손절, 분할매수 1/3, 포지션 사이징)
      6. 보유 관리        (트레일링 스톱, SAR, 피라미딩)
      7. 매도/청산        (50MA 이탈, 다이버전스, ADX 하락)

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py position 005930.KS
        python main.py position AAPL --capital 50000000
        python main.py position NVDA --period 2y --risk-pct 0.01
    """
    styles = _resolve_styles(style)
    is_multi = len(styles) > 1
    
    fetcher = KRXStockFetcher()
    fetcher.load()

    tickers = None
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
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        market_filter = MARKET_FILTERS.get(ticker)
        if market_filter:
            tickers = [t for t in tickers if market_filter(t)]
    else:
        info = fetcher.get_info(ticker)
        if not info:
            tickers = [ticker]
        else:
            tickers = [info.yahoo_ticker]

    with click.progressbar(tickers) as bar:
        for ticker in bar:
            try:
                analyzer = PositionTradingAnalyzer(
                    ticker, period=period, interval=interval,
                    capital=capital, risk_pct=risk_pct,
                )

                if llm or llm_stream:
                    decision = analyzer.analyze_with_llm(
                            provider=llm_provider,
                            model=llm_model,
                            stream=llm_stream)
                else:
                    decision = analyzer.analyze()
                
                decision_str = format_position_result(decision)
                click.echo(decision_str)

                stock_name = decision.name.replace(" ", "_")

                if save_report:
                    out_dir = Path("reports")
                    out_dir.mkdir(parents=True, exist_ok=True)
                    report_path = out_dir / f"{ticker.replace('.', '_')}_{style}_{decision.date.replace('-','')}_{stock_name}.txt"
                    report_path.write_text(decision_str, encoding="utf-8")
                    click.echo(f"보고서 저장됨: {report_path}")

                if not no_chart:
                    chart_path = (
                        Path("reports") / f"{ticker.replace('.', '_')}_{style}_{decision.date.replace('-','')}_{stock_name}.png"
                        if save_chart else None
                    )
                    df = analyzer.calculator.dataframe if analyzer.calculator else None
                    if df is not None:
                        PositionChartVisualizer().plot(decision, df, save_path=chart_path, show=not save_chart)
                        if save_chart and chart_path:
                            click.echo(f"차트 저장됨: {chart_path}")
            except Exception as e:
                click.echo(f"\n⚠ {ticker} 분석 실패: {e}", err=True)
                continue
            finally:
                pass


@cli.command("position-screen")
@click.option("--config", default="configs/watchlist.yaml", show_default=True,
              help="종목 목록 YAML")
@click.option("--market", default=None,
              type=click.Choice(["KOSPI", "KOSDAQ", "US"], case_sensitive=False),
              help="시장 필터 (KOSPI / KOSDAQ / US)")
@click.option("--period", default="1y", show_default=True, help="데이터 기간")
@click.option("--interval", default="1d", show_default=True, help="봉 간격")
@click.option("--capital", default=10_000_000, show_default=True, type=float,
              help="투입 자본금 (원)")
@click.option("--risk-pct", default=0.02, show_default=True, type=float,
              help="1회 거래 최대 손실 비율")
@click.option("--top", default=10, show_default=True, type=int,
              help="상위 N개 종목만 출력")
def position_screen(config: str, market: str | None, period: str, interval: str,
                    capital: float, risk_pct: float, top: int) -> None:
    """포지션 트레이딩 7단계 복수 종목 스크리닝

    watchlist.yaml의 종목을 일괄 분석하여 포지션 매수 적합 종목을 선별합니다.

    예시:
        python main.py position-screen
        python main.py position-screen --market KOSPI --capital 50000000
        python main.py position-screen --config my_list.yaml --top 5
    """
    config_path = Path(config)
    if not config_path.exists():
        click.echo(f"설정 파일을 찾을 수 없습니다: {config}", err=True)
        sys.exit(1)

    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    tickers = cfg.get("watchlist", [])
    if not tickers:
        click.echo("watchlist 항목이 없습니다.", err=True)
        sys.exit(1)

    # 시장 필터
    if market:
        MARKET_FILTERS = {
            "KOSPI": lambda t: ".KS" in t,
            "KOSDAQ": lambda t: ".KQ" in t,
            "US": lambda t: ".KS" not in t and ".KQ" not in t,
        }
        filt = MARKET_FILTERS.get(market.upper())
        if filt:
            tickers = [t for t in tickers if filt(t)]

    results = []
    with click.progressbar(tickers, label="포지션 스크리닝 중") as bar:
        for ticker in bar:
            try:
                analyzer = PositionTradingAnalyzer(
                    ticker, period=period, interval=interval,
                    capital=capital, risk_pct=risk_pct,
                )
                result = analyzer.analyze()
                results.append(result)
            except Exception as e:
                click.echo(f"\n⚠ {ticker} 실패: {e}", err=True)

    # 상위 N개
    results.sort(key=lambda r: r.overall_score, reverse=True)
    output = format_position_report(results[:top])
    click.echo(output)

    # 개별 상세 (매수 가능 종목만)
    actionable = [r for r in results[:top] if r.is_actionable]
    if actionable:
        click.echo(f"\n{'═'*72}")
        click.echo(f"  매수 실행 가능 종목 상세 ({len(actionable)}개)")
        click.echo(f"{'═'*72}")
        for r in actionable:
            click.echo(format_position_result(r))

if __name__ == "__main__":
    cli()
