---
description: 프로젝트 의존성을 업데이트하고 requirements.txt를 재생성합니다.
---

# /update-deps 명령어

## 처리 단계
1. 현재 설치된 패키지 버전 확인
2. 최신 버전으로 업그레이드
3. `requirements.txt` 재생성
4. 테스트 실행으로 호환성 검증

## 실행 명령
```bash
pip install --upgrade yfinance ta pandas numpy matplotlib seaborn structlog click pyyaml
pip freeze | grep -E "yfinance|^ta=|pandas|numpy|matplotlib|seaborn|structlog|click|pyyaml" > requirements.txt
pytest tests/ -q
```
