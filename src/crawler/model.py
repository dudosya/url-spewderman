import pydantic

class CrawlConfig(pydantic.BaseModel):
    url: pydantic.HttpUrl
    depth: int = pydantic.Field(default=1, ge=1, le=10)