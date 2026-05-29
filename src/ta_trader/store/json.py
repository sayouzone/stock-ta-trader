"""
json.py
SwingAnalysisResult + OHLCV DataFrame 저장/로드 유틸리티
지원 방식:
  1. JSON 복합 포맷  (권장 - 단일 파일)
"""

from __future__ import annotations

import json

from ta_trader.models.swing import SwingAnalysisResult

# ──────────────────────────────────────────────
# 방식 1: JSON 복합 포맷 (권장)
# ──────────────────────────────────────────────

class JsonStorage(BaseStorage[InputT]):
    """
    단일 .json 파일에 분석 결과 + OHLCV 시계열을 함께 저장.

    구조:
    {
      "version": "1.0",
      "saved_at": "ISO 타임스탬프",
      "analysis": { SwingAnalysisResult 직렬화 },
      "ohlcv": [ { Date, Open, High, Low, Close, Volume, ... } ]
    }
    """

    @staticmethod
    def save(
        result,           # SwingAnalysisResult 인스턴스
        df: pd.DataFrame,
        path: str | Path,
        indent: int = 2,
    ) -> Path:
        """
        result + df → JSON 파일 저장.

        Args:
            result : AnalysisResult 인스턴스
            df     : OHLCV + 지표 DataFrame
            path   : 저장 경로 (.json)
            indent : JSON 들여쓰기

        Returns:
            실제 저장된 Path
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        type_tag = self._type_tag(InputT)
        df_reset = df.reset_index()  # Date 인덱스를 컬럼으로
        payload = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "analysis": self._to_serializable(result),
            "ohlcv": self._df_to_records(df_reset),
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=indent)

        print(f"[JsonStorage] 저장 완료: {path}  ({path.stat().st_size / 1024:.1f} KB)")
        return path

    @staticmethod
    def load(path: str | Path) -> tuple[dict, pd.DataFrame]:
        """
        Returns:
            analysis_dict: 분석 결과 dict (필요 시 dataclass 재구성 가능)
            df: OHLCV + 지표 DataFrame
        """
        path = Path(path)
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)

        df = _records_to_df(payload["ohlcv"])
        print(f"[JsonStorage] 로드 완료: {path}  (행={len(df)}, 열={len(df.columns)})")
        return payload["analysis"], df


    def _type_tag(self, result) -> str:
        if isinstance(result, SwingAnalysisResult):
            return "swing"
        elif isinstance(result, SwingAnalysisResult):
            return "swing"
        elif isinstance(result, SwingAnalysisResult):
            return "swing"
        elif isinstance(result, SwingAnalysisResult):
            return "swing"
        elif isinstance(result, SwingAnalysisResult):
            return "swing"
