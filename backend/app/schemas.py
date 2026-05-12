from pydantic import BaseModel
from typing import Optional, List

# === Feed Models ===
class FeedCreate(BaseModel):
    name: str
    url: str
    type: str = "rss"
    category: Optional[str] = "默认"

class Feed(BaseModel):
    id: int
    name: str
    url: str
    type: str
    category: Optional[str]
    tags: Optional[str]
    last_fetched: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

# === Content Models ===
class Content(BaseModel):
    id: int
    feed_id: int
    title: str
    link: str
    author: Optional[str]
    published: Optional[str]
    summary: Optional[str]
    content: Optional[str]
    ai_summary: Optional[str]
    ai_summary_short: Optional[str]
    ai_summary_long: Optional[str]
    translated_title: Optional[str]
    translated_summary: Optional[str]
    language: str
    is_read: bool
    is_starred: bool
    tags: Optional[str]
    read_progress: float
    fetched_at: str
    audio_url: Optional[str]
    media_type: Optional[str]

    class Config:
        from_attributes = True

class ContentUpdate(BaseModel):
    is_read: Optional[bool] = None
    is_starred: Optional[bool] = None
    tags: Optional[str] = None
    read_progress: Optional[float] = None

class OPMLFeed(BaseModel):
    name: str
    url: str
    type: str = "rss"
    category: Optional[str] = "默认"

class OPMLImport(BaseModel):
    feeds: List[OPMLFeed]

class OPMLExport(BaseModel):
    title: str = "Content Aggregator Feeds"
    feeds: List[OPMLFeed]

# === Summary Models ===
class SummaryRequest(BaseModel):
    content_id: int
    text: str
    length: str = "medium"  # short / medium / long

class SummaryResponse(BaseModel):
    content_id: int
    summary: str
    length: str

# === Translate Models ===
class TranslateRequest(BaseModel):
    content_id: int
    text: str
    target_language: str = "zh"

class TranslateResponse(BaseModel):
    content_id: int
    translated_text: str

# === Daily Pick Models ===
class DailyPick(BaseModel):
    id: int
    date: str
    title: Optional[str]
    content_ids: str
    article_count: int
    generated_at: str

class DailyPickCreate(BaseModel):
    date: str
    force: bool = False
class Settings(BaseModel):
    ai_provider: str = "openai"
    ai_api_key: Optional[str]
    ai_model: str = "gpt-3.5-turbo"
    translate_provider: str = "openai"
    target_language: str = "zh"
