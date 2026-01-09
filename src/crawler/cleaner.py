"""
Content cleaning module for URL-Spewderman.

Provides content filtering and boilerplate removal using crawl4ai's
PruningContentFilter for non-AI content cleaning.
"""

from typing import Optional, Dict, Any, List
import json
from crawl4ai import CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from .model import CrawlConfig


class ContentCleaner:
    """Handles content filtering and boilerplate removal for crawled pages."""

    def __init__(self, config: CrawlConfig):
        """Initialize the content cleaner with configuration."""
        self.config = config

    def _build_js_actions(self) -> Optional[List[str]]:
        """Assemble JS actions, including optional auto-expand for collapsibles."""
        actions: List[str] = []

        if self.config.auto_expand:
            selectors = self.config.expand_selectors or [
                "details:not([open])",
                "details[open] summary",
                "[aria-expanded='false']",
                "[role='button'][aria-expanded='false']",
                "[data-accordion]",
                "[data-accordion] [role='button']",
                ".accordion button",
                ".accordion .accordion-button",
                ".accordion-toggle",
                ".collapse-toggle",
                ".faq-toggle",
                ".faq .question",
                ".show-more",
                ".read-more",
                ".expand",
                ".expandable",
            ]

            selectors_json = json.dumps(selectors)
            auto_expand_js = """
(() => {
    const selectors = __SELECTORS__;
    const clicked = new Set();
    const maxClicks = 60;

    selectors.forEach((sel) => {
        document.querySelectorAll(sel).forEach((el) => {
            if (clicked.size >= maxClicks) return;
            try {
                const tag = el.tagName.toLowerCase();
                if (tag === 'details') {
                    el.open = true;
                } else if (typeof el.click === 'function') {
                    el.click();
                } else if (typeof el.dispatchEvent === 'function') {
                    el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                }
                clicked.add(el);
            } catch (_) {}
        });
    });

    try { window.scrollTo(0, document.body.scrollHeight || 1000); } catch (_) {}
})();
""".replace("__SELECTORS__", selectors_json)

            actions.append(auto_expand_js)

        if self.config.js_actions:
            actions.extend(self.config.js_actions)

        return actions or None

    def create_crawler_config(self) -> CrawlerRunConfig:
        """Create a CrawlerRunConfig with content filtering enabled."""
        excluded_tags = self.config.excluded_tags or []

        if not self.config.content_filter_enabled:
            target_elements = [self.config.target_element] if self.config.target_element else None
            config_kwargs = {
                "cache_mode": CacheMode.BYPASS,
                "excluded_tags": excluded_tags,
                "exclude_external_links": self.config.exclude_external_links,
                "exclude_external_images": self.config.exclude_external_images,
                "word_count_threshold": 10,
                "target_elements": target_elements,
                "scan_full_page": self.config.scan_full_page,
            }
            js_actions = self._build_js_actions()
            if js_actions:
                config_kwargs["js_code"] = js_actions

            return CrawlerRunConfig(**config_kwargs)

        prune_filter = PruningContentFilter(
            threshold=self.config.pruning_threshold,
            threshold_type="fixed",
            min_word_threshold=10,
        )

        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={
                "ignore_links": self.config.exclude_external_links,
                "body_width": 0,
            },
        )

        target_elements = [self.config.target_element] if self.config.target_element else None

        config_kwargs = {
            "cache_mode": CacheMode.BYPASS,
            "markdown_generator": md_generator,
            "excluded_tags": excluded_tags,
            "exclude_external_links": self.config.exclude_external_links,
            "exclude_external_images": self.config.exclude_external_images,
            "word_count_threshold": 10,
            "remove_overlay_elements": True,
            "process_iframes": False,
            "target_elements": target_elements,
            "scan_full_page": self.config.scan_full_page,
        }
        js_actions = self._build_js_actions()
        if js_actions:
            config_kwargs["js_code"] = js_actions

        return CrawlerRunConfig(**config_kwargs)

    @staticmethod
    def get_content_stats(result: Any) -> Dict[str, Any]:
        """Summarize markdown lengths and reduction for logging/metrics."""
        stats: Dict[str, Any] = {
            "success": bool(getattr(result, "success", False)),
            "has_filtered_content": False,
            "raw_length": 0,
            "filtered_length": 0,
            "reduction_percentage": 0.0,
        }

        if not stats["success"]:
            return stats

        markdown = getattr(result, "markdown", None)
        if markdown:
            raw_text = getattr(markdown, "raw_markdown", None)
            fit_text = getattr(markdown, "fit_markdown", None)

            if isinstance(markdown, str):
                raw_text = markdown

            stats["raw_length"] = len(raw_text or "")
            stats["filtered_length"] = len(fit_text or "")
            stats["has_filtered_content"] = bool(fit_text and len(fit_text.strip()) > 0)

            if stats["raw_length"] > 0 and stats["filtered_length"] > 0:
                stats["reduction_percentage"] = (
                    (stats["raw_length"] - stats["filtered_length"]) / stats["raw_length"] * 100
                )

        return stats

    @staticmethod
    def extract_cleaned_content(result) -> str:
        """Extract cleaned content from a crawl4ai result."""
        if not result.success:
            return f"Error crawling page: {result.error_message}"

        if hasattr(result, "markdown") and result.markdown:
            if hasattr(result.markdown, "fit_markdown") and result.markdown.fit_markdown:
                fit_content = result.markdown.fit_markdown
                if fit_content and len(fit_content.strip()) > 0:
                    return fit_content

            if hasattr(result.markdown, "raw_markdown") and result.markdown.raw_markdown:
                raw_content = result.markdown.raw_markdown
                if raw_content and len(raw_content.strip()) > 0:
                    return raw_content

            if isinstance(result.markdown, str):
                str_content = result.markdown
                if str_content and len(str_content.strip()) > 0:
                    return str_content

        if hasattr(result, "cleaned_html") and result.cleaned_html:
            cleaned_html = result.cleaned_html
            if cleaned_html and len(cleaned_html.strip()) > 0:
                return cleaned_html

        if hasattr(result, "html") and result.html:
            html_content = result.html
            if html_content and len(html_content.strip()) > 0:
                return html_content

        return ""
