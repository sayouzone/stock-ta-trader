# 

카카오 i 오픈빌더 → Python 릴레이 서버 → OpenClaw Gateway 흐름으로 동작합니다.

## 🏗️ 아키텍처

```
카카오 i 오픈빌더
    │  POST /webhook/kakao
    ▼
[Python 릴레이 서버 :8000]
    │  POST /api/sessions/{id}/messages
    ▼
[OpenClaw Gateway :18789]
    │  Bearer Token 인증
    ▼
[OpenClaw 에이전트]
```

## 🚀 실행 방법

```bash
pip install fastapi uvicorn httpx python-dotenv

cp .env.example .env
# .env 편집: OPENCLAW_GATEWAY_URL, OPENCLAW_GATEWAY_TOKEN 설정

uvicorn main:app --host 0.0.0.0 --port 8000
```

## 🔑 주요 기능

* **페어링 시스템** — OpenClaw가 코드를 먼저 생성하고 카카오톡 채팅창에 /pair ABCD-12 형식으로 입력해 연결 GitHub하는 방식을 그대로 구현했습니다.
* **DM 정책** — pairing (기본, 페어링된 사용자만) / open (모두 허용) / allowlist / disabled 4가지 지원.
* **카드 자동 변환** — 에이전트가 JSON 형식으로 응답하면 카카오톡 카드로 자동 변환 GitHub됩니다. textCard, basicCard, listCard, commerceCard, carousel 모두 지원.
* **Admin API** — POST /admin/pair/generate로 OpenClaw 측에서 페어링 코드를 발급받을 수 있습니다.