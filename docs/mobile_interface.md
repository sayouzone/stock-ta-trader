# Stock TA Trader — Mobile Interface

**Four Agent System** (`DataAgent`, `StrategyAgent`, `RiskAgent`, `ExecutionAgent`) 기반
트레이딩 시스템을 스마트폰에서 접근할 수 있도록 확장한 프로젝트입니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  Mobile Clients                                     │
│  PWA  │  Telegram Bot  │  KakaoTalk  │  Push(ntfy)  │
└───────┴───────┬────────┴─────────────┴──────────────┘
                │
┌───────────────▼──────────────────────────────────────┐
│  API Gateway (FastAPI)                               │
│  REST + WebSocket + JWT Auth + Rate Limiting         │
└───────────────┬──────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────┐
│  Service Layer                                       │
│  AgentService │ NotificationService │ Scheduler      │
└───────────────┬──────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────┐
│  Four Agent System (Existing Core)                   │
│  DataAgent │ StrategyAgent │ RiskAgent │ Execution   │
│  SwingTradingAnalyzer │ GrowthMomentumAnalyzer       │
└──────────────────────────────────────────────────────┘
```

## 빠른 시작

### 1. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

### 2. Docker Compose로 실행

```bash
# 전체 스택 시작 (API + Telegram Bot + PostgreSQL + Redis)
make up

# API 서버 확인
curl http://localhost:8000/health

# Swagger 문서
open http://localhost:8000/docs
```

### 3. 로컬 개발 (Docker 없이)

```bash
# 의존성 설치
make setup

# Redis, PostgreSQL은 별도로 실행 필요
# API 서버 (hot reload)
make dev

# 텔레그램 봇
make dev-telegram
```

## 주요 API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `POST` | `/auth/token` | JWT 토큰 발급 |
| `POST` | `/api/v1/analysis/` | 종목 분석 제출 (비동기) |
| `GET` | `/api/v1/analysis/jobs/{id}` | 분석 결과 조회 |
| `POST` | `/api/v1/analysis/screening` | 시장 스크리닝 |
| `GET` | `/api/v1/analysis/recommendations` | 추천 종목 |
| `POST` | `/api/v1/alerts/send` | 알림 발송 |
| `POST` | `/api/v1/alerts/test` | 알림 테스트 |
| `WS` | `/api/v1/ws` | 실시간 분석 결과 스트림 |

## 텔레그램 봇 명령어

| 명령어 | 설명 |
|--------|------|
| `/start` | 시작 및 도움말 |
| `/analyze {종목}` | 스윙 분석 |
| `/growth {종목}` | 성장 모멘텀 분석 |
| `/full {종목}` | 종합 분석 |
| `/screen` | 시장 스크리닝 |
| `/recommend` | 추천 종목 |
| `/status {job_id}` | 작업 상태 확인 |

## 기존 코어와의 연결

`core/` 디렉토리의 스텁을 실제 stock-ta-trader 모듈로 교체하세요:

```python
# core/agents/__init__.py에서
# 스텁 클래스를 제거하고 실제 import로 교체:

from stock_ta_trader.agents.data_agent import DataAgent
from stock_ta_trader.agents.strategy_agent import StrategyAgent
from stock_ta_trader.agents.risk_agent import RiskAgent
from stock_ta_trader.agents.execution_agent import ExecutionAgent
```

## 외부 접근 (Cloudflare Tunnel)

```bash
# 임시 터널 (개발용)
make tunnel

# 영구 터널 설정
cloudflared tunnel create sta-trader
cloudflared tunnel route dns sta-trader your-domain.com
# docker-compose.yml에서 cloudflared 서비스 활성화
```

## 프로젝트 구조

```
stock-ta-trader/
├── src/ta_trader/
│   ├── config/             # 환경 설정 (pydantic-settings)
│   ├── core/               # 에이전트 코어 (스텁 → 기존 코드 연결)
│   │   ├── agents/         # Four Agent System
│   │   └── orchestrator.py # AgentOrchestrator
│   ├── interfaces/
│   │   ├── api/            # FastAPI REST/WebSocket
│   │   │   ├── routers/    # 분석, 알림, WebSocket 라우터
│   │   │   ├── auth.py     # JWT 인증
│   │   │   ├── schemas.py  # Pydantic 스키마
│   │   │   └── main.py     # 앱 엔트리포인트
│   │   ├── telegram/       # 텔레그램 봇
│   │   └── cli/            # 기존 Click CLI (연결용)
│   ├── services/
│   │   ├── agent_service.py    # Orchestrator 래퍼 (캐싱, 비동기 작업)
│   │   ├── notification.py     # 다중 채널 알림 (Strategy Pattern)
│   │   └── scheduler.py        # 정기 분석 스케줄러
│   ├── infra/
│   │   ├── cache.py        # Redis 캐시 (시장 인지 TTL)
│   │   └── db.py           # SQLAlchemy async 모델
├── tests/
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
└── .env.example
```

## 개발 명령어

```bash
make help        # 전체 명령어 목록
make test        # 테스트 실행
make lint        # 코드 린트
make format      # 코드 포맷팅
make health      # 서버 헬스체크
make token       # JWT 토큰 발급 (개발용)
```
