"""
ta_trader/utils/sector_filter.py
────────────────
all_sectors_themed.csv 를 로드해서
sector / subsector / theme 조합으로 필터링하는 유틸리티.
 
주요 특이사항:
  - theme 컬럼은 "AI반도체;AI인프라" 처럼 세미콜론으로 복수 태그가 들어 있음
  - filter_by_theme()은 태그 중 하나라도 일치하면 포함 (contains 방식)
"""
 
from __future__ import annotations
 
from pathlib import Path
from typing import Optional
 
import pandas as pd
 
# ────────────────────────────────────────────────
# 상수
# ────────────────────────────────────────────────
 
DEFAULT_CSV = Path(__file__).parent / "data/all_sectors_themed.csv"
 
# sector 전체 목록 (참고용)
SECTORS = [
    "ETF/기타", "경기소비재", "금융", "미분류", "부동산",
    "산업재", "소재", "에너지", "유틸리티", "정보기술",
    "커뮤니케이션서비스", "필수소비재", "헬스케어",
]
 
# theme 전체 목록 (복수 태그 포함 원본 값 제외한 단일 태그)
THEMES = [
    "AI반도체", "AI인프라", "로봇", "방산우주", "양자컴퓨팅", "원전전력",
]
 
 
# ────────────────────────────────────────────────
# 데이터 로더
# ────────────────────────────────────────────────
 
def load_data(csv_path: str | Path = DEFAULT_CSV) -> pd.DataFrame:
    """CSV를 읽어서 DataFrame 반환. theme_tags 컬럼 추가."""
    df = pd.read_csv(csv_path, dtype=str)
 
    # theme 세미콜론 태그를 리스트로 파싱 → 필터링 용도
    df["theme_tags"] = df["theme"].apply(
        lambda x: [t.strip() for t in x.split(";")] if pd.notna(x) else []
    )
 
    return df
 
 
# ────────────────────────────────────────────────
# 필터 함수
# ────────────────────────────────────────────────
 
def filter_stocks(
    df: pd.DataFrame,
    *,
    sector: Optional[str] = None,
    subsector: Optional[str] = None,
    theme: Optional[str] = None,
    market: Optional[str] = None,
    theme_confidence: Optional[str] = None,
    drop_unclassified: bool = False,
    exclude_sectors: Optional[list[str]] = None,
) -> pd.DataFrame:
    """
    여러 조건을 AND 조합으로 필터링한다.
 
    Parameters
    ----------
    sector            : 예) "정보기술"
    subsector         : 예) "반도체"
    theme             : 예) "AI반도체"  (복수 태그 중 하나라도 일치 시 포함)
    market            : 예) "KOSPI" | "KOSDAQ" | "US"
    theme_confidence  : 예) "high"  (태그별 신뢰도 중 하나라도 일치)
    drop_unclassified : True 이면 sector == "미분류" 제외
    exclude_sectors   : 제외할 sector 목록, 예) ["ETF/기타", "미분류"]
    """
    mask = pd.Series([True] * len(df), index=df.index)
 
    if sector is not None:
        mask &= df["sector"].str.strip() == sector.strip()
 
    if subsector is not None:
        mask &= df["subsector"].str.strip() == subsector.strip()
 
    if theme is not None:
        # theme_tags 리스트 안에 해당 테마가 포함된 행만
        mask &= df["theme_tags"].apply(lambda tags: theme.strip() in tags)
 
    if market is not None:
        mask &= df["market"].str.strip().str.upper() == market.strip().upper()
 
    if theme_confidence is not None:
        # "high;high" 같은 복수 신뢰도도 처리
        mask &= df["theme_confidence"].apply(
            lambda x: (
                theme_confidence.strip() in [c.strip() for c in x.split(";")]
                if pd.notna(x)
                else False
            )
        )
 
    if drop_unclassified:
        mask &= df["sector"] != "미분류"
 
    if exclude_sectors:
        normalized = [s.strip() for s in exclude_sectors]
        mask &= ~df["sector"].str.strip().isin(normalized)
 
    result = df[mask].copy()
    # 내부용 컬럼 제거 후 반환
    return result.drop(columns=["theme_tags"])
 
 
# ────────────────────────────────────────────────
# 편의 래퍼
# ────────────────────────────────────────────────
 
def get_sector_list(df: pd.DataFrame) -> list[str]:
    return sorted(df["sector"].dropna().unique().tolist())
 
 
def get_subsector_list(df: pd.DataFrame, sector: Optional[str] = None) -> list[str]:
    src = df if sector is None else df[df["sector"] == sector]
    return sorted(src["subsector"].dropna().unique().tolist())
 
 
def get_theme_list(df: pd.DataFrame) -> list[str]:
    """복수 태그를 분해한 단일 테마 목록 반환."""
    tags: set[str] = set()
    for tag_list in df["theme_tags"]:
        tags.update(tag_list)
    return sorted(tags)