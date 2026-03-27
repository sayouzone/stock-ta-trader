"""
kakao_cards 사용 예시
에이전트 응답에서 카카오톡 카드를 직접 구성하는 방법을 보여줍니다.
"""

from kakao_cards import (
    BasicCard,
    Button,
    CommerceCard,
    ListCard,
    ListItem,
    QuickReply,
    SimpleImage,
    SkillResponse,
    TextCard,
)


# ── 1. 텍스트 카드 ─────────────────────────────────────────────────────────
def example_text_card():
    resp = (
        SkillResponse()
        .add_card(
            TextCard(
                title="OpenClaw AI 어시스턴트",
                description="무엇을 도와드릴까요?",
                buttons=[
                    Button("주식 분석", "message", "주식 분석해줘"),
                    Button("날씨 확인", "message", "오늘 날씨"),
                ],
            )
        )
        .add_quick_reply(QuickReply("취소", "message", "취소"))
        .build()
    )
    return resp


# ── 2. 기본 카드 (이미지 포함) ────────────────────────────────────────────
def example_basic_card():
    return (
        SkillResponse()
        .add_card(
            BasicCard(
                title="삼성전자 (005930)",
                description="현재가: 75,400원 ▲ +1.2%",
                image_url="https://example.com/samsung.png",
                link_url="https://finance.naver.com/item/main.nhn?code=005930",
                buttons=[
                    Button("상세보기", "webLink", web_link_url="https://finance.naver.com/item/main.nhn?code=005930"),
                    Button("분석 요청", "message", "삼성전자 분석해줘"),
                ],
            )
        )
        .build()
    )


# ── 3. 리스트 카드 ────────────────────────────────────────────────────────
def example_list_card():
    return (
        SkillResponse()
        .add_card(
            ListCard(
                header_title="📈 오늘의 추천 종목",
                items=[
                    ListItem(
                        title="삼성전자",
                        description="75,400원 ▲ +1.2%",
                        action="message",
                        message_text="삼성전자 분석",
                    ),
                    ListItem(
                        title="SK하이닉스",
                        description="182,000원 ▲ +2.5%",
                        action="message",
                        message_text="SK하이닉스 분석",
                    ),
                    ListItem(
                        title="NAVER",
                        description="218,500원 ▼ -0.3%",
                        action="message",
                        message_text="NAVER 분석",
                    ),
                ],
                buttons=[
                    Button("전체 리스트", "message", "추천 종목 전체 보기"),
                ],
            )
        )
        .build()
    )


# ── 4. 카루셀 ─────────────────────────────────────────────────────────────
def example_carousel():
    cards = [
        BasicCard(
            title="코스피",
            description="2,650.15 ▲ +15.32",
            image_url="https://example.com/kospi.png",
        ),
        BasicCard(
            title="코스닥",
            description="865.40 ▼ -5.12",
            image_url="https://example.com/kosdaq.png",
        ),
        BasicCard(
            title="S&P 500",
            description="5,215.32 ▲ +28.45",
            image_url="https://example.com/sp500.png",
        ),
    ]
    return SkillResponse().add_carousel(cards).build()


# ── 5. 커머스 카드 ────────────────────────────────────────────────────────
def example_commerce_card():
    return (
        SkillResponse()
        .add_card(
            CommerceCard(
                description="프리미엄 주식 분석 구독권",
                price=29900,
                currency="won",
                discount_rate=20,
                discount_price=23900,
                profile_name="OpenClaw Pro",
                buttons=[
                    Button("구독하기", "webLink", web_link_url="https://example.com/subscribe"),
                ],
            )
        )
        .build()
    )


# ── 6. 에이전트 JSON 응답 → 카드 자동 변환 예시 ─────────────────────────
AGENT_JSON_RESPONSE = """
{
  "listCard": {
    "header": {"title": "분석 결과"},
    "items": [
      {"title": "현재가", "description": "75,400원"},
      {"title": "목표가", "description": "85,000원"},
      {"title": "추천의견", "description": "매수"}
    ]
  },
  "quickReplies": [
    {"label": "차트 보기", "action": "message", "messageText": "차트 보여줘"},
    {"label": "뉴스", "action": "message", "messageText": "관련 뉴스"}
  ]
}
"""


if __name__ == "__main__":
    import json

    print("=== TextCard ===")
    print(json.dumps(example_text_card(), ensure_ascii=False, indent=2))

    print("\n=== ListCard ===")
    print(json.dumps(example_list_card(), ensure_ascii=False, indent=2))

    print("\n=== Carousel ===")
    print(json.dumps(example_carousel(), ensure_ascii=False, indent=2))
