"""
카카오톡 카드 메시지 모델 및 유틸리티
Kakao i 오픈빌더 SkillResponse v2 데이터 모델
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# 버튼 액션 타입
# ---------------------------------------------------------------------------
ActionType = Literal["message", "webLink", "phone", "share", "block", "operator"]


@dataclass
class Button:
    label: str
    action: ActionType = "message"
    message_text: str | None = None
    web_link_url: str | None = None
    phone_number: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"label": self.label, "action": self.action}
        if self.message_text:
            d["messageText"] = self.message_text
        if self.web_link_url:
            d["webLinkUrl"] = self.web_link_url
        if self.phone_number:
            d["phoneNumber"] = self.phone_number
        return d


@dataclass
class QuickReply:
    label: str
    action: ActionType = "message"
    message_text: str | None = None
    block_id: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"label": self.label, "action": self.action}
        if self.message_text:
            d["messageText"] = self.message_text
        if self.block_id:
            d["blockId"] = self.block_id
        return d


# ---------------------------------------------------------------------------
# 카드 타입
# ---------------------------------------------------------------------------
@dataclass
class TextCard:
    """텍스트 카드 (텍스트 + 버튼)."""
    title: str
    description: str | None = None
    buttons: list[Button] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {"title": self.title}
        if self.description:
            d["description"] = self.description
        if self.buttons:
            d["buttons"] = [b.to_dict() for b in self.buttons]
        return {"textCard": d}


@dataclass
class BasicCard:
    """기본 카드 (이미지 + 텍스트 + 버튼)."""
    title: str | None = None
    description: str | None = None
    image_url: str | None = None
    link_url: str | None = None
    buttons: list[Button] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {}
        if self.title:
            d["title"] = self.title
        if self.description:
            d["description"] = self.description
        if self.image_url:
            d["thumbnail"] = {
                "imageUrl": self.image_url,
                **({"link": {"web": self.link_url}} if self.link_url else {}),
            }
        if self.buttons:
            d["buttons"] = [b.to_dict() for b in self.buttons]
        return {"basicCard": d}


@dataclass
class ListItem:
    title: str
    description: str | None = None
    image_url: str | None = None
    action: ActionType = "message"
    message_text: str | None = None
    web_link_url: str | None = None

    def to_dict(self) -> dict:
        d: dict = {"title": self.title, "action": self.action}
        if self.description:
            d["description"] = self.description
        if self.image_url:
            d["imageUrl"] = self.image_url
        if self.message_text:
            d["messageText"] = self.message_text
        if self.web_link_url:
            d["webLinkUrl"] = self.web_link_url
        return d


@dataclass
class ListCard:
    """리스트 카드."""
    header_title: str
    items: list[ListItem] = field(default_factory=list)
    buttons: list[Button] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "header": {"title": self.header_title},
            "items": [item.to_dict() for item in self.items],
        }
        if self.buttons:
            d["buttons"] = [b.to_dict() for b in self.buttons]
        return {"listCard": d}


@dataclass
class CommerceCard:
    """커머스 카드 (상품 카드)."""
    description: str
    price: int
    currency: str = "won"
    discount: int = 0
    discount_rate: int = 0
    discount_price: int = 0
    profile_name: str | None = None
    profile_image_url: str | None = None
    image_urls: list[str] = field(default_factory=list)
    buttons: list[Button] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
        }
        if self.discount:
            d["discount"] = self.discount
        if self.discount_rate:
            d["discountRate"] = self.discount_rate
        if self.discount_price:
            d["discountedPrice"] = self.discount_price
        if self.profile_name:
            d["profile"] = {
                "title": self.profile_name,
                **({"imageUrl": self.profile_image_url} if self.profile_image_url else {}),
            }
        if self.image_urls:
            d["thumbnails"] = [{"imageUrl": u} for u in self.image_urls]
        if self.buttons:
            d["buttons"] = [b.to_dict() for b in self.buttons]
        return {"commerceCard": d}


@dataclass
class SimpleImage:
    """이미지 카드."""
    image_url: str
    alt_text: str = "이미지"

    def to_dict(self) -> dict:
        return {
            "simpleImage": {
                "imageUrl": self.image_url,
                "altText": self.alt_text,
            }
        }


# ---------------------------------------------------------------------------
# SkillResponse 빌더
# ---------------------------------------------------------------------------
class SkillResponse:
    """
    카카오 i 오픈빌더 SkillResponse v2 빌더.

    예시:
        resp = (
            SkillResponse()
            .add_text_card(TextCard("안녕하세요", buttons=[Button("더보기", "message", "더보기")]))
            .add_quick_reply(QuickReply("취소", "message", "취소"))
            .build()
        )
    """

    def __init__(self) -> None:
        self._outputs: list[dict] = []
        self._quick_replies: list[dict] = []
        self._context: dict | None = None

    def add_text(self, text: str) -> "SkillResponse":
        for chunk in _split(text, 990):
            self._outputs.append({"simpleText": {"text": chunk}})
        return self

    def add_image(self, image_url: str, alt_text: str = "") -> "SkillResponse":
        self._outputs.append({"simpleImage": {"imageUrl": image_url, "altText": alt_text}})
        return self

    def add_card(self, card: TextCard | BasicCard | ListCard | CommerceCard | SimpleImage) -> "SkillResponse":
        self._outputs.append(card.to_dict())
        return self

    def add_carousel(
        self,
        cards: list[BasicCard | CommerceCard],
        carousel_type: str = "basicCard",
    ) -> "SkillResponse":
        self._outputs.append({
            "carousel": {
                "type": carousel_type,
                "items": [list(c.to_dict().values())[0] for c in cards],
            }
        })
        return self

    def add_quick_reply(self, qr: QuickReply) -> "SkillResponse":
        self._quick_replies.append(qr.to_dict())
        return self

    def set_context(self, name: str, lifespan: int = 5, params: dict | None = None) -> "SkillResponse":
        self._context = {"name": name, "lifespan": lifespan, "params": params or {}}
        return self

    def build(self) -> dict:
        template: dict = {"outputs": self._outputs}
        if self._quick_replies:
            template["quickReplies"] = self._quick_replies
        result: dict = {"version": "2.0", "template": template}
        if self._context:
            result["context"] = {"values": [self._context]}
        return result


def _split(text: str, max_len: int) -> list[str]:
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks
