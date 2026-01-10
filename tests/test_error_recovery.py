"""
Tests for error recovery and retry logic functionality.

Tests that the crawler properly retries failed requests with exponential backoff.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
from crawler.model import CrawlConfig
from crawler.engine import CrawlerEngine


class TestErrorRecovery:
    """Test error recovery and retry functionality."""
    
    def test_retry_config_defaults(self):
        """Test that retry configuration has correct defaults."""
        config = CrawlConfig(url="https://example.com")
        
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 1.5
    
    def test_retry_config_custom(self):
        """Test custom retry configuration."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=5,
            retry_backoff_factor=2.0,
        )
        
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 2.0
    
    def test_retry_config_zero_retries(self):
        """Test disabling retries with max_retries=0."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=0,
        )
        
        assert config.max_retries == 0
    
    def test_should_retry_error_transient(self):
        """Test that transient errors should be retried."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Transient errors
        transient_errors = [
            Exception("Connection timeout"),
            Exception("Network error"),
            Exception("429 Too Many Requests"),
            Exception("500 Internal Server Error"),
            Exception("502 Bad Gateway"),
            Exception("503 Service Unavailable"),
            Exception("504 Gateway Timeout"),
            Exception("Server error occurred"),
        ]
        
        for error in transient_errors:
            assert engine._should_retry_error(error) is True
    
    def test_should_retry_error_permanent(self):
        """Test that permanent errors should not be retried."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Permanent errors
        permanent_errors = [
            Exception("404 Not Found"),
            Exception("403 Forbidden"),
            Exception("401 Unauthorized"),
            Exception("400 Bad Request"),
            Exception("Invalid URL"),
            Exception("Unsupported protocol"),
        ]
        
        for error in permanent_errors:
            assert engine._should_retry_error(error) is False
    
    def test_should_retry_error_unknown(self):
        """Test that unknown errors default to retry."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Unknown errors (should default to retry)
        unknown_errors = [
            Exception("Some random error"),
            Exception("Unexpected issue"),
            Exception(""),
        ]
        
        for error in unknown_errors:
            assert engine._should_retry_error(error) is True
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_on_first_attempt(self):
        """Test retry logic when first attempt succeeds."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        
        engine = CrawlerEngine(config)
        
        # Mock _crawl_page_single to succeed on first attempt
        mock_content = "Mock content"
        engine._crawl_page_single = AsyncMock(return_value=mock_content)
        
        result = await engine._crawl_page("https://example.com/page")
        
        assert result == mock_content
        engine._crawl_page_single.assert_called_once_with("https://example.com/page", is_retry=False)
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_on_retry(self):
        """Test retry logic when success occurs after retries."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        
        engine = CrawlerEngine(config)
        
        # Mock _crawl_page_single to fail twice then succeed
        mock_content = "Mock content"
        engine._crawl_page_single = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),  # First attempt fails
                Exception("Network error"),       # Second attempt fails  
                mock_content,                     # Third attempt succeeds
            ]
        )
        
        result = await engine._crawl_page("https://example.com/page")
        
        assert result == mock_content
        assert engine._crawl_page_single.call_count == 3
        # Verify calls with correct is_retry parameter
        calls = engine._crawl_page_single.call_args_list
        assert calls[0] == call("https://example.com/page", is_retry=False)
        assert calls[1] == call("https://example.com/page", is_retry=True)
        assert calls[2] == call("https://example.com/page", is_retry=True)
    
    @pytest.mark.asyncio
    async def test_retry_logic_all_attempts_fail(self):
        """Test retry logic when all attempts fail."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=2,
            retry_backoff_factor=1.5,
        )
        
        engine = CrawlerEngine(config)
        
        # Mock _crawl_page_single to always fail
        engine._crawl_page_single = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),
                Exception("Network error"),
                Exception("Server error"),
            ]
        )
        
        result = await engine._crawl_page("https://example.com/page")
        
        assert result is None
        assert engine._crawl_page_single.call_count == 3  # Initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_retry_logic_permanent_error_no_retry(self):
        """Test that permanent errors don't trigger retries."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=3,
            retry_backoff_factor=1.5,
        )
        
        engine = CrawlerEngine(config)
        
        # Mock _crawl_page_single to raise permanent error
        engine._crawl_page_single = AsyncMock(
            side_effect=Exception("404 Not Found")
        )
        
        result = await engine._crawl_page("https://example.com/page")
        
        assert result is None
        # Should only be called once (no retries for permanent error)
        engine._crawl_page_single.assert_called_once_with("https://example.com/page", is_retry=False)
    
    @pytest.mark.asyncio
    async def test_retry_disabled_with_zero_max_retries(self):
        """Test that retry logic is disabled when max_retries=0."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=0,  # Disable retries
        )
        
        engine = CrawlerEngine(config)
        
        # Mock _crawl_page_single to fail
        engine._crawl_page_single = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        
        # When max_retries=0, exceptions should propagate
        with pytest.raises(Exception, match="Connection timeout"):
            await engine._crawl_page("https://example.com/page")
        
        # Should only be called once (no retries)
        # Note: When called without is_retry parameter, default is False
        engine._crawl_page_single.assert_called_once_with("https://example.com/page")
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_calculation(self):
        """Test exponential backoff delay calculation."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=3,
            request_delay=1.0,
            retry_backoff_factor=2.0,
        )
        
        engine = CrawlerEngine(config)
        
        # Track sleep calls
        sleep_calls = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            sleep_calls.append(delay)
            return await original_sleep(0)  # Don't actually sleep in tests
        
        # Mock _crawl_page_single to fail twice then succeed
        mock_content = "Mock content"
        engine._crawl_page_single = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),
                Exception("Network error"),
                mock_content,
            ]
        )
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await engine._crawl_page("https://example.com/page")
        
        assert result == mock_content
        # Verify exponential backoff delays
        # Attempt 1: immediate (no delay)
        # Attempt 2: 1.0 * (2.0^0) = 1.0s delay
        # Attempt 3: 1.0 * (2.0^1) = 2.0s delay
        assert len(sleep_calls) == 2  # Two retries = two delays
        assert sleep_calls[0] == 1.0  # First retry delay
        assert sleep_calls[1] == 2.0  # Second retry delay
    
    @pytest.mark.asyncio
    async def test_retry_with_different_backoff_factors(self):
        """Test retry with different backoff factors."""
        config = CrawlConfig(
            url="https://example.com",
            max_retries=2,
            request_delay=2.0,
            retry_backoff_factor=1.5,
        )
        
        engine = CrawlerEngine(config)
        
        # Track sleep calls
        sleep_calls = []
        original_sleep = asyncio.sleep
        
        async def mock_sleep(delay):
            sleep_calls.append(delay)
            return await original_sleep(0)
        
        engine._crawl_page_single = AsyncMock(
            side_effect=[
                Exception("Connection timeout"),
                Exception("Network error"),
                "Mock content",
            ]
        )
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await engine._crawl_page("https://example.com/page")
        
        # Verify delays with backoff factor 1.5
        # Attempt 1: immediate (no delay)
        # Attempt 2: 2.0 * (1.5^0) = 2.0s delay
        # Attempt 3: 2.0 * (1.5^1) = 3.0s delay
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 2.0  # First retry: 2.0 * 1.5^0 = 2.0
        assert sleep_calls[1] == 3.0  # Second retry: 2.0 * 1.5^1 = 3.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
