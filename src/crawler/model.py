from typing import Optional, Literal, List
from pathlib import Path
import pydantic


class CrawlConfig(pydantic.BaseModel):
    url: pydantic.HttpUrl
    max_depth: int = pydantic.Field(default=3, ge=1, le=15)
    output_format: Literal["txt", "md", "json"] = "txt"
    output_file: Optional[Path] = None
    concurrency: int = pydantic.Field(default=5, ge=1, le=20)
    respect_robots: bool = True
    request_delay: float = pydantic.Field(default=1.0, ge=0.1, le=5.0)
    # Retry configuration
    max_retries: int = pydantic.Field(default=3, ge=0, le=10)
    retry_backoff_factor: float = pydantic.Field(default=1.5, ge=1.0, le=5.0)
    # Content filtering configuration
    content_filter_enabled: bool = True
    pruning_threshold: float = pydantic.Field(default=0.3, ge=0.0, le=1.0)
    excluded_tags: Optional[List[str]] = pydantic.Field(
        default_factory=lambda: [
            "nav", "footer", "header", "aside", "form", "script", "style",
            "iframe", "noscript", "svg", "canvas",  # Interactive/media elements
            "dialog", "menu", "menuitem", "datalist", "output", "progress", "meter",  # Form/UI elements
            "object", "embed", "applet", "param",  # Embedded objects
            "audio", "video", "track", "source",  # Media elements
            "map", "area",  # Image maps
            "fieldset", "legend", "optgroup", "option",  # Form sub-elements
            "col", "colgroup", "caption",  # Table elements
            "figure", "figcaption",  # Figure elements
        ]
    )
    exclude_external_links: bool = True
    exclude_external_images: bool = False
