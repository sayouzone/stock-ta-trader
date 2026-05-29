"""
swing_analysis_storage.py
SwingAnalysisResult + OHLCV DataFrame 저장/로드 유틸리티
지원 방식:
  3. SQLite DB       (다종목 관리)
"""

from __future__ import annotations

import sqlite3

# ──────────────────────────────────────────────
# 방식 3: SQLite DB (다종목 포트폴리오 관리)
# ──────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS swing_analysis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT    NOT NULL,
    name        TEXT,
    date        TEXT    NOT NULL,
    saved_at    TEXT    NOT NULL,
    signal      TEXT,
    score       REAL,
    grade       TEXT,
    environment TEXT,
    summary     TEXT,
    full_json   TEXT    NOT NULL,   -- SwingAnalysisResult 전체 직렬화
    UNIQUE(ticker, date)
);

CREATE TABLE IF NOT EXISTS ohlcv_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT    NOT NULL,
    date            TEXT    NOT NULL,
    open            REAL,
    high            REAL,
    low             REAL,
    close           REAL,
    volume          INTEGER,
    rsi             REAL,
    macd            REAL,
    macd_signal     REAL,
    macd_diff       REAL,
    bb_upper        REAL,
    bb_middle       REAL,
    bb_lower        REAL,
    bb_pct          REAL,
    adx             REAL,
    adx_pos         REAL,
    adx_neg         REAL,
    atr             REAL,
    ema9            REAL,
    ema21           REAL,
    sma50           REAL,
    sma200          REAL,
    UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker_date ON ohlcv_data(ticker, date);
CREATE INDEX IF NOT EXISTS idx_analysis_ticker    ON swing_analysis(ticker);
"""

_OHLCV_COLS = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal", "macd_diff",
    "bb_upper", "bb_middle", "bb_lower", "bb_pct",
    "adx", "adx_pos", "adx_neg", "atr",
    "ema9", "ema21", "sma50", "sma200",
]


class SQLiteStorage:
    """
    단일 .db 파일로 여러 종목의 분석 이력을 관리.

    테이블:
      swing_analysis — 분석 메타 + 전체 JSON
      ohlcv_data     — 정규화된 OHLCV + 주요 지표
    """

    def __init__(self, db_path: str | Path = "swing_trading.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ── 저장 ──────────────────────────────────

    def save(self, result, df: pd.DataFrame) -> None:
        analysis_dict = _to_serializable(result)
        ticker   = analysis_dict.get("ticker", "UNKNOWN")
        name     = analysis_dict.get("name", "")
        date_str = analysis_dict.get("date", "")

        # swing_analysis 행
        analysis_row = {
            "ticker":      ticker,
            "name":        name,
            "date":        date_str,
            "saved_at":    datetime.now().isoformat(),
            "signal":      analysis_dict.get("overall_signal"),
            "score":       analysis_dict.get("overall_score"),
            "grade":       analysis_dict.get("screening", {}).get("grade"),
            "environment": analysis_dict.get("market_env", {}).get("environment"),
            "summary":     analysis_dict.get("summary"),
            "full_json":   json.dumps(analysis_dict, ensure_ascii=False),
        }

        # ohlcv_data 행들
        ohlcv_rows = self._df_to_ohlcv_rows(df, ticker)

        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO swing_analysis
                   (ticker, name, date, saved_at, signal, score, grade, environment, summary, full_json)
                   VALUES (:ticker, :name, :date, :saved_at, :signal, :score, :grade, :environment, :summary, :full_json)""",
                analysis_row,
            )
            conn.executemany(
                f"""INSERT OR REPLACE INTO ohlcv_data
                    (ticker, date, {', '.join(_OHLCV_COLS)})
                    VALUES (:ticker, :date, {', '.join(':' + c for c in _OHLCV_COLS)})""",
                ohlcv_rows,
            )

        print(
            f"[SQLiteStorage] 저장 완료: {ticker} {date_str}  "
            f"({len(ohlcv_rows)}행 OHLCV)"
        )

    @staticmethod
    def _df_to_ohlcv_rows(df: pd.DataFrame, ticker: str) -> list[dict]:
        """DataFrame → ohlcv_data INSERT용 row dict 리스트."""
        df_reset = df.reset_index()
        rows = []
        for _, row in df_reset.iterrows():
            record: dict = {"ticker": ticker, "date": str(row.get("Date", ""))[:10]}
            for col in _OHLCV_COLS:
                # CSV 컬럼명 매핑 (대소문자 유연 처리)
                val = None
                for candidate in [col, col.capitalize(), col.upper()]:
                    if candidate in row.index:
                        val = row[candidate]
                        break
                record[col] = None if (val is None or (isinstance(val, float) and val != val)) else val
            rows.append(record)
        return rows

    # ── 조회 ──────────────────────────────────

    def load_latest(self, ticker: str) -> tuple[dict, pd.DataFrame]:
        """특정 종목의 가장 최근 분석 결과를 반환."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT full_json FROM swing_analysis WHERE ticker=? ORDER BY date DESC LIMIT 1",
                (ticker,),
            ).fetchone()
            if not row:
                raise ValueError(f"{ticker} 분석 결과 없음")
            analysis = json.loads(row["full_json"])

            ohlcv_rows = conn.execute(
                "SELECT * FROM ohlcv_data WHERE ticker=? ORDER BY date",
                (ticker,),
            ).fetchall()

        df = pd.DataFrame([dict(r) for r in ohlcv_rows])
        if not df.empty:
            df["Date"] = pd.to_datetime(df["date"])
            df = df.set_index("Date").drop(columns=["id", "ticker", "date"], errors="ignore")

        print(f"[SQLiteStorage] 로드 완료: {ticker}  (행={len(df)})")
        return analysis, df

    def list_tickers(self) -> pd.DataFrame:
        """저장된 종목 목록과 최신 분석 요약 반환."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT ticker, name, MAX(date) as latest_date,
                          signal, score, grade, environment
                   FROM swing_analysis GROUP BY ticker ORDER BY ticker"""
            ).fetchall()
        return pd.DataFrame([dict(r) for r in rows])