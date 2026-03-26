.PHONY: help dev up down logs test lint clean setup

help: ## 도움말 표시
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────

setup: ## 초기 설정 (env 파일 복사, 의존성 설치)
	@test -f .env || cp .env.example .env
	pip install -e ".[all]"
	@echo "✅ Setup complete. Edit .env with your API keys."

# ── Docker ───────────────────────────────────────────────

up: ## Docker Compose 시작 (전체 스택)
	docker compose up -d
	@echo "✅ API: http://localhost:8000"
	@echo "✅ Docs: http://localhost:8000/docs"

down: ## Docker Compose 중지
	docker compose down

logs: ## 로그 확인 (팔로우)
	docker compose logs -f

logs-api: ## API 서버 로그만 확인
	docker compose logs -f api

logs-telegram: ## 텔레그램 봇 로그만 확인
	docker compose logs -f telegram-bot

rebuild: ## 이미지 재빌드 후 시작
	docker compose up -d --build

# ── Local Dev (Docker 없이) ──────────────────────────────

dev: ## 로컬 API 서버 실행 (hot reload)
	uvicorn interfaces.api.main:app --reload --port 8000

dev-telegram: ## 로컬 텔레그램 봇 실행
	python -m run_telegram

# ── Database ─────────────────────────────────────────────

db-migrate: ## Alembic 마이그레이션 생성
	alembic revision --autogenerate -m "$(msg)"

db-upgrade: ## 마이그레이션 적용
	alembic upgrade head

# ── Quality ──────────────────────────────────────────────

test: ## 테스트 실행
	pytest tests/ -v --cov=. --cov-report=term-missing

lint: ## 코드 린트 (ruff)
	ruff check .
	ruff format --check .

format: ## 코드 포맷팅
	ruff check --fix .
	ruff format .

typecheck: ## 타입 체크 (mypy)
	mypy core/ interfaces/ services/ config/

# ── Utilities ────────────────────────────────────────────

clean: ## 캐시 및 임시 파일 정리
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/

health: ## 서버 헬스체크
	curl -s http://localhost:8000/health | python -m json.tool

token: ## JWT 토큰 발급 (개발용)
	@curl -s -X POST http://localhost:8000/auth/token \
		-H "Content-Type: application/json" \
		-d '{"username":"admin","password":"changeme"}' | python -m json.tool

tunnel: ## Cloudflare Tunnel 시작 (임시)
	cloudflared tunnel --url http://localhost:8000
