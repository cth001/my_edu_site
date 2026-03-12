from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: str
    source: Literal["律动", "CoinDesk", "Cointelegraph"]
    category: Literal["news", "social", "regulatory", "forum", "media"]
    title: str
    summary: str
    url: str
    published_at: datetime
    relevance: int = Field(ge=0, le=100)


class PricesResponse(BaseModel):
    btc_usd: float
    eth_usd: float
    updated_at: datetime


class NewsResponse(BaseModel):
    total: int
    items: list[NewsItem]


app = FastAPI(title="Web3 Information Aggregator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sample_news() -> list[NewsItem]:
    now = _now()
    raw = [
        NewsItem(
            id="cd-1",
            source="CoinDesk",
            category="news",
            title="SEC Signals New Timeline for Spot ETF Review as Market Liquidity Rises",
            summary="Regulators released an updated review schedule that may accelerate institutional decision-making.",
            url="https://www.coindesk.com/",
            published_at=now - timedelta(minutes=16),
            relevance=93,
        ),
        NewsItem(
            id="ct-1",
            source="Cointelegraph",
            category="news",
            title="Layer-2 Transaction Volume Hits Monthly High as Fees Stay Compressed",
            summary="Ethereum scaling networks posted strong throughput as DeFi activity increases.",
            url="https://cointelegraph.com/",
            published_at=now - timedelta(minutes=32),
            relevance=84,
        ),
        NewsItem(
            id="lb-1",
            source="律动",
            category="regulatory",
            title="监管动态：亚洲主要市场更新稳定币合规框架与披露要求",
            summary="监管机构发布新指引，强调储备透明度与信息披露。",
            url="https://api.theblockbeats.news/v2/rss/all",
            published_at=now - timedelta(minutes=45),
            relevance=95,
        ),
        NewsItem(
            id="dup-1",
            source="CoinDesk",
            category="news",
            title="Layer-2 Transaction Volume Hits Monthly High as Fees Stay Compressed",
            summary="Duplicate article from syndication feed.",
            url="https://www.coindesk.com/",
            published_at=now - timedelta(minutes=30),
            relevance=60,
        ),
    ]
    return raw


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    title_map: dict[str, NewsItem] = {}
    for item in items:
        key = item.title.strip().lower()
        current = title_map.get(key)
        if current is None or item.published_at > current.published_at:
            title_map[key] = item
    return list(title_map.values())


def _within_time_range(item: NewsItem, time_filter: str) -> bool:
    delta = _now() - item.published_at
    if time_filter == "1h":
        return delta <= timedelta(hours=1)
    if time_filter == "24h":
        return delta <= timedelta(hours=24)
    return delta <= timedelta(days=7)


@app.get("/api/news", response_model=NewsResponse)
def get_news(
    q: str | None = Query(default=None, description="Search keyword"),
    sources: str | None = Query(default=None, description="Comma-separated sources"),
    categories: str | None = Query(default=None, description="Comma-separated categories"),
    time_filter: Literal["1h", "24h", "7d"] = "24h",
    sort_by: Literal["date", "relevance", "source"] = "date",
) -> NewsResponse:
    items = _dedupe(_sample_news())

    allowed_sources = set(s.strip() for s in sources.split(",")) if sources else None
    allowed_categories = set(c.strip().lower() for c in categories.split(",")) if categories else None
    query = q.strip().lower() if q else None

    filtered: list[NewsItem] = []
    for item in items:
        if allowed_sources and item.source not in allowed_sources:
            continue
        if allowed_categories and item.category not in allowed_categories:
            continue
        if not _within_time_range(item, time_filter):
            continue
        if query:
            hay = f"{item.title} {item.summary} {item.source} {item.category}".lower()
            if query not in hay:
                continue
        filtered.append(item)

    if sort_by == "date":
        filtered.sort(key=lambda x: x.published_at, reverse=True)
    elif sort_by == "relevance":
        filtered.sort(key=lambda x: x.relevance, reverse=True)
    else:
        filtered.sort(key=lambda x: x.source)

    return NewsResponse(total=len(filtered), items=filtered)


@app.get("/api/prices", response_model=PricesResponse)
async def get_prices() -> PricesResponse:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        return PricesResponse(
            btc_usd=float(payload["bitcoin"]["usd"]),
            eth_usd=float(payload["ethereum"]["usd"]),
            updated_at=_now(),
        )
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=502, detail=f"Failed to fetch price data: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
