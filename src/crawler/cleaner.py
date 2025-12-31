"""
Content cleaning module for URL-Spewderman.

Provides content filtering and boilerplate removal using crawl4ai's
PruningContentFilter for non-AI content cleaning.
"""

from typing import Optional, Dict, Any
from crawl4ai import CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from .model import CrawlConfig


class ContentCleaner:
    """Handles content filtering and boilerplate removal for crawled pages."""

    def __init__(self, config: CrawlConfig):
        """
        Initialize the content cleaner with configuration.

        Args:
            config: CrawlConfig instance with content filtering settings
        """
        self.config = config

    def create_crawler_config(self) -> CrawlerRunConfig:
        """
        Create a CrawlerRunConfig with content filtering enabled.

        Returns:
            Configured CrawlerRunConfig instance
        """
        # Handle None excluded_tags by providing empty list
        excluded_tags = self.config.excluded_tags or []
        
        if not self.config.content_filter_enabled:
            # Return basic config without content filtering
            # Use target_elements (not css_selector) to preserve link extraction
            target_elements = [self.config.target_element] if self.config.target_element else None
            return CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                excluded_tags=excluded_tags,
                exclude_external_links=self.config.exclude_external_links,
                exclude_external_images=self.config.exclude_external_images,
                word_count_threshold=10,
                target_elements=target_elements,
            )

        # Create PruningContentFilter with configured threshold
        prune_filter = PruningContentFilter(
            threshold=self.config.pruning_threshold,
            threshold_type="fixed",
            min_word_threshold=10,
        )

        # Create markdown generator with content filter
        md_generator = DefaultMarkdownGenerator(
            content_filter=prune_filter,
            options={
                "ignore_links": self.config.exclude_external_links,
                "body_width": 0,  # No line wrapping
            }
        )

        # Use target_elements (not css_selector) to preserve link extraction
        target_elements = [self.config.target_element] if self.config.target_element else None
        
        # Return comprehensive crawler config
        return CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=md_generator,
            excluded_tags=excluded_tags,
            exclude_external_links=self.config.exclude_external_links,
            exclude_external_images=self.config.exclude_external_images,
            word_count_threshold=10,
            remove_overlay_elements=True,
            process_iframes=False,
            target_elements=target_elements,
        )

    @staticmethod
    def extract_cleaned_content(result) -> str:
        """
        Extract cleaned content from crawl4ai result.

        Args:
            result: crawl4ai CrawlResult object

        Returns:
            Cleaned markdown content, or raw markdown if filtering failed
        """
        if not result.success:
            return f"Error crawling page: {result.error_message}"

        # Try to get filtered markdown first
        if hasattr(result, 'markdown') and result.markdown:
            # Check if we have fit_markdown and it's not empty
            if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown:
                fit_content = result.markdown.fit_markdown
                # Only return fit_markdown if it has meaningful content
                if fit_content and len(fit_content.strip()) > 0:
                    return fit_content
            
            # Fall back to raw_markdown if fit_markdown is empty or doesn't exist
            if hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown:
                raw_content = result.markdown.raw_markdown
                if raw_content and len(raw_content.strip()) > 0:
                    return raw_content
            
            # Fall back to string markdown
            elif isinstance(result.markdown, str):
                str_content = result.markdown
                if str_content and len(str_content.strip()) > 0:
                    return str_content

        # Fallback to cleaned HTML or raw HTML
        if hasattr(result, 'cleaned_html') and result.cleaned_html:
            cleaned_html = result.cleaned_html
            if cleaned_html and len(cleaned_html.strip()) > 0:
                return cleaned_html
        
        if hasattr(result, 'html') and result.html:
            html_content = result.html
            if html_content and len(html_content.strip()) > 0:
                return html_content

        return "No content extracted"

    @staticmethod
    def get_content_stats(result) -> Dict[str, Any]:
        """
        Get statistics about content extraction.

        Args:
            result: crawl4ai CrawlResult object

        Returns:
            Dictionary with content statistics
        """
        stats = {
            "success": result.success if hasattr(result, 'success') else False,
            "has_filtered_content": False,
            "raw_length": 0,
            "filtered_length": 0,
            "reduction_percentage": 0.0,
        }

        if not result.success:
            return stats

        # Calculate lengths
        raw_content = ""
        filtered_content = ""

        if hasattr(result, 'markdown') and result.markdown:
            if hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown:
                raw_content = result.markdown.raw_markdown
                stats["raw_length"] = len(raw_content)

            if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown:
                filtered_content = result.markdown.fit_markdown
                stats["filtered_length"] = len(filtered_content)
                stats["has_filtered_content"] = True

        # Calculate reduction percentage if we have both
        if stats["raw_length"] > 0 and stats["filtered_length"] > 0:
            stats["reduction_percentage"] = (
                (stats["raw_length"] - stats["filtered_length"]) / stats["raw_length"] * 100
            )

        return stats
