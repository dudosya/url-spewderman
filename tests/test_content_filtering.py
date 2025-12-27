"""
Integration tests for content filtering functionality.

Tests the integration between CrawlConfig, ContentCleaner, and CrawlerEngine
to ensure content filtering works correctly.
"""

import pytest
from pathlib import Path
from crawler.model import CrawlConfig
from crawler.cleaner import ContentCleaner
from crawl4ai import CrawlerRunConfig


class TestCrawlConfigContentFiltering:
    """Test CrawlConfig with content filtering fields."""
    
    def test_default_content_filtering(self):
        """Test that content filtering is enabled by default."""
        config = CrawlConfig(url="https://example.com")
        assert config.content_filter_enabled is True
        assert config.pruning_threshold == 0.5
        assert config.excluded_tags == ["nav", "footer", "header", "aside", "form", "script", "style"]
        assert config.exclude_external_links is True
        assert config.exclude_external_images is False
    
    def test_disable_content_filtering(self):
        """Test disabling content filtering."""
        config = CrawlConfig(
            url="https://example.com",
            content_filter_enabled=False,
            pruning_threshold=0.8,
        )
        assert config.content_filter_enabled is False
        assert config.pruning_threshold == 0.8
    
    def test_custom_excluded_tags(self):
        """Test custom excluded tags."""
        config = CrawlConfig(
            url="https://example.com",
            excluded_tags=["nav", "footer", "ads"],
        )
        assert config.excluded_tags == ["nav", "footer", "ads"]
    
    def test_no_excluded_tags(self):
        """Test with no excluded tags (None)."""
        config = CrawlConfig(
            url="https://example.com",
            excluded_tags=None,
        )
        assert config.excluded_tags is None


class TestContentCleaner:
    """Test ContentCleaner functionality."""
    
    @pytest.fixture
    def default_config(self):
        """Create a default CrawlConfig for testing."""
        return CrawlConfig(url="https://example.com")
    
    @pytest.fixture
    def disabled_filter_config(self):
        """Create a CrawlConfig with content filtering disabled."""
        return CrawlConfig(
            url="https://example.com",
            content_filter_enabled=False,
        )
    
    def test_cleaner_initialization(self, default_config):
        """Test ContentCleaner initialization."""
        cleaner = ContentCleaner(default_config)
        assert cleaner.config == default_config
    
    def test_create_crawler_config_enabled(self, default_config):
        """Test creating crawler config with content filtering enabled."""
        cleaner = ContentCleaner(default_config)
        config = cleaner.create_crawler_config()
        
        assert isinstance(config, CrawlerRunConfig)
        assert config.markdown_generator is not None
        assert config.excluded_tags == default_config.excluded_tags
        assert config.exclude_external_links == default_config.exclude_external_links
    
    def test_create_crawler_config_disabled(self, disabled_filter_config):
        """Test creating crawler config with content filtering disabled."""
        cleaner = ContentCleaner(disabled_filter_config)
        config = cleaner.create_crawler_config()
        
        assert isinstance(config, CrawlerRunConfig)
        # When content filtering is disabled, markdown_generator may still exist
        # but should not have a content filter
        if config.markdown_generator is not None:
            # If there's a markdown generator, it shouldn't have a content filter
            assert config.markdown_generator.content_filter is None
        # Should use the default excluded tags from config
        assert config.excluded_tags == disabled_filter_config.excluded_tags
    
    def test_create_crawler_config_no_excluded_tags(self):
        """Test creating crawler config with no excluded tags."""
        config = CrawlConfig(
            url="https://example.com",
            excluded_tags=None,
        )
        cleaner = ContentCleaner(config)
        crawler_config = cleaner.create_crawler_config()
        
        assert crawler_config.excluded_tags == []
    
    def test_extract_cleaned_content_success(self):
        """Test extracting cleaned content from successful result."""
        # Mock result object
        class MockResult:
            success = True
            markdown = type('Markdown', (), {
                'fit_markdown': 'Filtered content',
                'raw_markdown': 'Raw content',
            })()
        
        result = MockResult()
        content = ContentCleaner.extract_cleaned_content(result)
        assert content == 'Filtered content'
    
    def test_extract_cleaned_content_fallback(self):
        """Test extracting cleaned content with fallback to raw markdown."""
        # Mock result object without fit_markdown
        class MockResult:
            success = True
            markdown = type('Markdown', (), {
                'raw_markdown': 'Raw content',
            })()
        
        result = MockResult()
        content = ContentCleaner.extract_cleaned_content(result)
        assert content == 'Raw content'
    
    def test_extract_cleaned_content_error(self):
        """Test extracting cleaned content from failed result."""
        # Mock result object with error
        class MockResult:
            success = False
            error_message = 'Connection failed'
        
        result = MockResult()
        content = ContentCleaner.extract_cleaned_content(result)
        assert 'Error crawling page' in content
    
    def test_get_content_stats(self):
        """Test getting content statistics."""
        # Mock result object with content
        class MockMarkdown:
            raw_markdown = 'Raw content ' * 10  # 120 characters (12 * 10)
            fit_markdown = 'Filtered content'  # 16 characters
        
        class MockResult:
            success = True
            markdown = MockMarkdown()
        
        result = MockResult()
        stats = ContentCleaner.get_content_stats(result)
        
        assert stats['success'] is True
        assert stats['has_filtered_content'] is True
        assert stats['raw_length'] == 120  # 'Raw content ' is 12 chars * 10 = 120
        assert stats['filtered_length'] == 16
        # Calculate expected reduction: (120 - 16) / 120 * 100 = 86.666...
        assert stats['reduction_percentage'] == pytest.approx(86.67, rel=0.1)


class TestIntegration:
    """Integration tests for the complete content filtering pipeline."""
    
    def test_config_to_cleaner_to_engine(self):
        """Test that configuration flows correctly through the system."""
        # Create config with custom settings
        config = CrawlConfig(
            url="https://example.com",
            content_filter_enabled=True,
            pruning_threshold=0.7,
            excluded_tags=["nav", "footer"],
            exclude_external_links=False,
            exclude_external_images=True,
        )
        
        # Create cleaner
        cleaner = ContentCleaner(config)
        
        # Verify cleaner uses config correctly
        assert cleaner.config == config
        
        # Create crawler config
        crawler_config = cleaner.create_crawler_config()
        
        # Verify crawler config reflects our settings
        assert crawler_config.markdown_generator is not None
        assert crawler_config.excluded_tags == ["nav", "footer"]
        assert crawler_config.exclude_external_links is False
        assert crawler_config.exclude_external_images is True
    
    def test_content_filtering_disabled_flow(self):
        """Test the flow when content filtering is disabled."""
        config = CrawlConfig(
            url="https://example.com",
            content_filter_enabled=False,
        )
        
        cleaner = ContentCleaner(config)
        crawler_config = cleaner.create_crawler_config()
        
        # When content filtering is disabled, markdown_generator may exist
        # but should not have a content filter
        if crawler_config.markdown_generator is not None:
            assert crawler_config.markdown_generator.content_filter is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
