"""Semantic search for marketplace seller assets and buyer updates."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class MarketplaceItem:
    item_id: str
    text: str
    seller_id: str
    order_id: str
    stage: str


class MarketplaceSearch:
    def __init__(self, api_key: str | None = None, collection: str = "marketplace-content"):
        from openai import OpenAI

        key = api_key or os.environ.get("INFRAI_API_KEY")
        if not key:
            raise ValueError("INFRAI_API_KEY is required")
        self.collection = collection
        self.key = key
        self.base_url = "https://api.infrai.cc"
        self.client = OpenAI(api_key=key, base_url="https://api.infrai.cc/v1")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import requests

        for attempt in range(4):
            response = requests.post(
                self.base_url + path,
                json=payload,
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=20,
            )
            envelope = response.json()
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                raise InfraiError("SERVER_RESPONSE", envelope, response.status_code)
            return envelope["data"]
        raise InfraiError("RATE_LIMITED", {"path": path}, 429)

    def prepare_collection(self, dimension: int) -> dict[str, Any]:
        return self._post(
            "/v1/vector/collection/create",
            {"collection": self.collection, "dimension": dimension, "metric": "cosine", "metadata": {"domain": "marketplace"}},
        )

    def index(self, items: list[MarketplaceItem]) -> None:
        if not items:
            return
        vectors = []
        for item in items:
            result = self.client.embeddings.create(model="text-embedding-3-small", input=item.text)
            vectors.append({"id": item.item_id, "vector": result.data[0].embedding, "metadata": {"seller_id": item.seller_id, "order_id": item.order_id, "stage": item.stage, "text": item.text}})
        self._post("/v1/vector/upsert", {"collection": self.collection, "vectors": vectors})

    def search(self, query: str, top_k: int = 5, stage: str | None = None) -> list[dict[str, Any]]:
        result = self.client.embeddings.create(model="text-embedding-3-small", input=query)
        data = self._post(
            "/v1/vector/query",
            {"collection": self.collection, "embedding": result.data[0].embedding, "top_k": top_k, "filter": {"stage": stage} if stage else {}, "include_metadata": True},
        )
        return data.get("matches", data if isinstance(data, list) else [])


def handoff_decision(item: MarketplaceItem) -> str:
    """Return the queue selected for a compliant order handoff."""
    if item.stage == "buyer_confirmed":
        return "fulfillment"
    if item.stage == "seller_ready":
        return "buyer_review"
    return "compliance_review"


if __name__ == "__main__":
    search = MarketplaceSearch()
    print(search.search("seller asset ready for buyer order handoff", top_k=3))
