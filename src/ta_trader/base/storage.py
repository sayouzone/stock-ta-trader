"""
ta_trader/base/storage.py
스토리지 기반 추상 클래스

모든 스토리지는 이 클래스를 상속합니다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from ta_trader.utils.logger import get_logger

InputT = TypeVar("InputT")


class BaseStorage(ABC, Generic[InputT]):
    """
    에이전트 기반 추상 클래스.

    각 에이전트는 단일 책임 원칙에 따라 하나의 역할만 수행합니다:
      - DataAgent:      데이터 수집 + 지표 연산 → MarketDataReport
      - StrategyAgent:  전략 수립 + 시그널 생성 → TradeSignal
      - RiskAgent:      리스크 평가 + 승인/거부 → RiskApproval
      - ExecutionAgent: 주문 실행 + 체결 관리   → ExecutionResult
    """

    def __init__(self) -> None:
        self._logger = get_logger(self.__class__.__name__)
        self._df: Optional[pd.DataFrame] = None

    @abstractmethod
    def load(self,
        path: str | Path) -> tuple[InputT, pd.DataFrame]:
        """
        파일에서 AnalysisResult, DataFrame으로 복원

        Args:
            path: .json / *_meta.json / .db 파일 경로

        Returns:
            SwingAnalysisResult, PositionAnalysisResult, GrowthAnalysisResult, ValueAnalysisResult
            df     : OHLCV + 지표 DataFrame (Date 인덱스)
        """

    @abstractmethod
    def save(self,
        result: InputT,
        df: pd.DataFrame,
        path: str | Path,
        indent: int = 2) -> Path:
        """
        에이전트 메인 실행 로직.

        Args:
            result: SwingAnalysisResult, PositionAnalysisResult, GrowthAnalysisResult, ValueAnalysisResult
            df
            path
            indent

        Returns:
            저장 경로
        """

    # ── 데이터 변환 ───────────────────────────────────────
    
    def _to_serializable(self, obj: Any) -> Any:
        """dataclass / Enum / float 등을 JSON 직렬화 가능한 타입으로 재귀 변환."""
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "__dataclass_fields__"):
            return {k: _to_serializable(v) for k, v in asdict(obj).items()}
        if isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_to_serializable(i) for i in obj]
        if isinstance(obj, float) and (obj != obj):  # NaN
            return None
        return obj

    def _df_to_records(self, df: pd.DataFrame) -> list[dict]:
        """DataFrame → JSON 직렬화 가능한 레코드 리스트 변환."""
        records = []
        for _, row in df.iterrows():
            record = {}
            for col, val in row.items():
                if pd.isna(val):
                    record[col] = None
                elif isinstance(val, (pd.Timestamp,)):
                    record[col] = val.isoformat()
                else:
                    record[col] = val
            records.append(record)
        return records

    #def _records_to_df(records: list[dict]) -> pd.DataFrame:
    #    """레코드 리스트 → DataFrame 복원."""
    #    df = pd.DataFrame(records)
    #    if "Date" in df.columns:
    #        df["Date"] = pd.to_datetime(df["Date"])
    #        df = df.set_index("Date")
    #    return df

    def _records_to_df(records: list[dict]) -> pd.DataFrame:
        """레코드 리스트 → 타입 보정된 DataFrame."""
        df = pd.DataFrame(records)
        if df.empty:
            return df

        # Date 인덱스 복원
        date_col = next((c for c in ["Date", "date"] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df = df.rename(columns={date_col: "Date"}).set_index("Date")

        # 수치 컬럼 float 변환 (None → NaN)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors="ignore")
            except Exception:
                pass

        return df.sort_index()

    def on_error(self, error: Exception, input_data: InputT) -> None:
        """에러 발생 시 훅 (기본: 로깅)"""
        self._logger.error(
            f"{self.name} 에러",
            error=str(error),
            agent=self.__class__.__name__,
        )

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.name}>"
