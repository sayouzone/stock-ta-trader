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
from ta_trader.utils.formatter import make_decision
from ta_trader.visualization.chart import ChartVisualizer


@click.group()
@click.version_option("1.1.0")
def cli() -> None:
    """TA Trader - ADX/MACD/RSI/Bollinger Bands 기반 트레이딩 분석 도구"""


# ── analyze 명령 ──────────────────────────────────────────
@cli.command()
@click.argument("ticker")
@click.option("--period",     default="6mo",  show_default=True, help="데이터 기간 (예: 3mo, 6mo, 1y)")
@click.option("--interval",   default="1d",   show_default=True, help="봉 간격 (예: 1d, 1wk)")
@click.option("--save-chart", is_flag=True,   help="차트를 reports/ 폴더에 저장")
@click.option("--no-chart",   is_flag=True,   help="차트 표시 안 함")
@click.option("--save-report",is_flag=True,   help="분석결과를 reports/ 폴더에 저장")
@click.option("--llm",        is_flag=True,   help="Anthropic Claude LLM 해석 추가 (ANTHROPIC_API_KEY 필요)")
@click.option("--llm-stream", is_flag=True,   help="LLM 응답을 스트리밍으로 출력")
@click.option("--llm-provider", default=None,
              type=click.Choice(["anthropic", "gemini"], case_sensitive=False),
              help="LLM Provider (기본값: 환경변수 자동 감지)")
@click.option("--llm-model",  default=None,   help="LLM 모델명 (기본값: claude-sonnet-4-20250514)")
def analyze(ticker: str, period: str, interval: str, save_chart: bool, no_chart: bool, save_report: bool,
            llm: bool, llm_stream: bool, llm_provider: str | None, llm_model: str | None) -> None:
    """단일 종목 기술적 분석

    TICKER: 종목 코드 (예: 005930.KS, AAPL)

    예시:
        python main.py analyze 005930.KS
        python main.py analyze AAPL --llm
        python main.py analyze NVDA --llm --llm-stream --save-chart
    """
    analyzer = MonthlyTradingAnalyzer(ticker, period=period, interval=interval)
    
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


# ── screen 명령 ───────────────────────────────────────────
@cli.command()
@click.option("--config",  default="configs/watchlist.yaml", show_default=True, help="종목 목록 YAML")
@click.option("--output",  default="reports",                 show_default=True, help="결과 저장 디렉토리")
@click.option("--period",  default="6mo",                    show_default=True)
def screen(config: str, output: str, period: str) -> None:
    """관심 종목 일괄 스크리닝"""
    import yaml

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
                decision = MonthlyTradingAnalyzer(ticker, period=period).analyze()
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
