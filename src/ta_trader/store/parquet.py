"""
swing_analysis_storage.py
SwingAnalysisResult + OHLCV DataFrame 저장/로드 유틸리티
지원 방식:
  2. Parquet + JSON  (대용량 시계열)
"""

from __future__ import annotations

import json

# ──────────────────────────────────────────────
# 방식 2: Parquet + JSON (대용량 시계열)
# ──────────────────────────────────────────────

class ParquetStorage(BaseStorage[SwingAnalysisResult]):
    """
    analysis.json  — 분석 메타 (경량)
    ohlcv.parquet  — OHLCV + 지표 시계열 (압축 컬럼 포맷)

    같은 디렉터리에 쌍으로 저장됩니다.
    """

    @staticmethod
    def save(
        result,
        df: pd.DataFrame,
        directory: str | Path,
    ) -> Path:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        tag = f"{ticker}_{date_str}" if ticker else "analysis"
        json_path = directory / f"{tag}_meta.json"
        parquet_path = directory / f"{tag}_ohlcv.parquet"

        # 분석 결과 JSON
        meta = {
            "version": "1.0",
            "saved_at": datetime.now().isoformat(),
            "parquet_file": parquet_path.name,
            "analysis": _to_serializable(result),
        }
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # OHLCV Parquet (snappy 압축)
        df.to_parquet(parquet_path, compression="snappy")

        print(
            f"[ParquetStorage] 저장 완료\n"
            f"  meta   : {json_path}  ({json_path.stat().st_size / 1024:.1f} KB)\n"
            f"  parquet: {parquet_path}  ({parquet_path.stat().st_size / 1024:.1f} KB)"
        )
        return directory

    @staticmethod
    def load(json_path: str | Path) -> tuple[dict, pd.DataFrame]:
        json_path = Path(json_path)
        with json_path.open(encoding="utf-8") as f:
            meta = json.load(f)

        parquet_path = json_path.parent / meta["parquet_file"]
        df = pd.read_parquet(parquet_path)

        print(f"[ParquetStorage] 로드 완료 (행={len(df)}, 열={len(df.columns)})")
        return meta["analysis"], df