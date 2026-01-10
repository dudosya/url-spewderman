"""
Test depth limiting and recursion in the crawler.
Mocks a fake website structure to verify BFS depth control.
"""
import asyncio
from unittest.mock import AsyncMock, patch
import pytest
from crawler.model import CrawlConfig
from crawler.engine import CrawlerEngine


class MockCrawlResult:
    """Mock result from crawl4ai."""
    
    def __init__(self, markdown=None, html=None):
        self.success = True
        self.markdown = markdown
        self.html = html
        self.cleaned_html = html  # For compatibility with ContentCleaner
        self.error_message = None


def create_mock_page(url: str, links: list[str]) -> MockCrawlResult:
    """Create a mock page with links in its HTML."""
    html_links = "".join(f'<a href="{link}">Link to {link}</a>' for link in links)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><title>{url}</title></head>
    <body>
        <h1>Page {url}</h1>
        <p>This is page {url}</p>
        {html_links}
    </body>
    </html>
    """
    return MockCrawlResult(html=html_content)


@pytest.fixture
def mock_crawler():
    """Fixture to mock AsyncWebCrawler."""
    with patch('crawler.engine.AsyncWebCrawler') as MockCrawlerClass:
        mock_crawler_instance = AsyncMock()
        MockCrawlerClass.return_value.__aenter__.return_value = mock_crawler_instance
        
        # Define the website structure
        # Page A -> Page B -> Page C
        website_structure = {
            'https://example.com/a': ['https://example.com/b'],
            'https://example.com/b': ['https://example.com/c'],
            'https://example.com/c': [],  # No further links
        }
        
        def arun_side_effect(url, **kwargs):
            """Mock arun to return appropriate page based on URL."""
            if url in website_structure:
                return create_mock_page(url, website_structure[url])
            # Return empty page for unknown URLs
            return MockCrawlResult(html=f"<html><body>Page {url}</body></html>")
        
        mock_crawler_instance.arun.side_effect = arun_side_effect
        yield mock_crawler_instance


@pytest.mark.asyncio
async def test_depth_limiting(mock_crawler):
    """Test that crawler stops at max_depth."""
    # Test with max_depth=1: should crawl page A (depth 0) and B (depth 1)
    config = CrawlConfig(
        url='https://example.com/a',
        max_depth=1,
        concurrency=1,
        request_delay=0.1
    )
    
    engine = CrawlerEngine(config)
    results = await engine.run()
    
    # Should crawl page A (depth 0) and B (depth 1)
    assert len(results) == 2
    assert 'https://example.com/a' in results
    assert 'https://example.com/b' in results
    assert 'https://example.com/c' not in results  # Depth 2
    
    # Verify mock was called for A and B
    assert mock_crawler.arun.call_count == 2
    calls = [call[1]['url'] for call in mock_crawler.arun.call_args_list]
    assert 'https://example.com/a' in calls
    assert 'https://example.com/b' in calls


@pytest.mark.asyncio
async def test_depth_two(mock_crawler):
    """Test that crawler follows links up to depth 2."""
    # Test with max_depth=2: should crawl pages A, B, and C
    config = CrawlConfig(
        url='https://example.com/a',
        max_depth=2,
        concurrency=1,
        request_delay=0.1
    )
    
    engine = CrawlerEngine(config)
    results = await engine.run()
    
    # Should crawl pages A (depth 0), B (depth 1), and C (depth 2)
    assert len(results) == 3
    assert 'https://example.com/a' in results
    assert 'https://example.com/b' in results
    assert 'https://example.com/c' in results
    
    # Verify mock was called for A, B, and C
    assert mock_crawler.arun.call_count == 3
    calls = [call[1]['url'] for call in mock_crawler.arun.call_args_list]
    assert 'https://example.com/a' in calls
    assert 'https://example.com/b' in calls
    assert 'https://example.com/c' in calls


@pytest.mark.asyncio
async def test_depth_three(mock_crawler):
    """Test that crawler follows all links with depth 3."""
    # Test with max_depth=3: should crawl pages A, B, and C
    config = CrawlConfig(
        url='https://example.com/a',
        max_depth=3,
        concurrency=1,
        request_delay=0.1
    )
    
    engine = CrawlerEngine(config)
    results = await engine.run()
    
    # Should crawl all pages A, B, C
    assert len(results) == 3
    assert 'https://example.com/a' in results
    assert 'https://example.com/b' in results
    assert 'https://example.com/c' in results
    
    # Verify mock was called for all pages
    assert mock_crawler.arun.call_count == 3
    calls = [call[1]['url'] for call in mock_crawler.arun.call_args_list]
    assert set(calls) == {'https://example.com/a', 'https://example.com/b', 'https://example.com/c'}


@pytest.mark.asyncio
async def test_domain_restriction(mock_crawler):
    """Test that crawler stays within same domain."""
    # Modify mock to include external link
    website_structure = {
        'https://example.com/a': ['https://example.com/b', 'https://external.com/page'],
        'https://example.com/b': [],
    }
    
    def arun_side_effect(url, **kwargs):
        if url in website_structure:
            return create_mock_page(url, website_structure[url])
        return MockCrawlResult(html=f"<html><body>Page {url}</body></html>")
    
    mock_crawler.arun.side_effect = arun_side_effect
    
    config = CrawlConfig(
        url='https://example.com/a',
        max_depth=2,
        concurrency=1,
        request_delay=0.1
    )
    
    engine = CrawlerEngine(config)
    results = await engine.run()
    
    # Should only crawl example.com pages, not external.com
    assert len(results) == 2  # A and B
    assert 'https://example.com/a' in results
    assert 'https://example.com/b' in results
    assert 'https://external.com/page' not in results
    
    # Verify external link was not crawled
    calls = [call[1]['url'] for call in mock_crawler.arun.call_args_list]
    assert 'https://external.com/page' not in calls


@pytest.mark.asyncio
async def test_subdomains_allowed_by_default(mock_crawler):
    """Default policy should treat same registrable domain as internal (subdomains allowed)."""
    website_structure = {
        'https://docs.example.com/a': ['https://www.example.com/b'],
        'https://www.example.com/b': [],
    }

    def arun_side_effect(url, **kwargs):
        if url in website_structure:
            return create_mock_page(url, website_structure[url])
        return MockCrawlResult(html=f"<html><body>Page {url}</body></html>")

    mock_crawler.arun.side_effect = arun_side_effect

    config = CrawlConfig(
        url='https://docs.example.com/a',
        max_depth=2,
        concurrency=1,
        request_delay=0.1,
    )

    engine = CrawlerEngine(config)
    results = await engine.run()

    assert len(results) == 2
    assert 'https://docs.example.com/a' in results
    assert 'https://www.example.com/b' in results


@pytest.mark.asyncio
async def test_host_policy_blocks_subdomains(mock_crawler):
    """Host policy should only allow exact host, blocking different subdomains."""
    website_structure = {
        'https://docs.example.com/a': ['https://www.example.com/b'],
        'https://www.example.com/b': [],
    }

    def arun_side_effect(url, **kwargs):
        if url in website_structure:
            return create_mock_page(url, website_structure[url])
        return MockCrawlResult(html=f"<html><body>Page {url}</body></html>")

    mock_crawler.arun.side_effect = arun_side_effect

    config = CrawlConfig(
        url='https://docs.example.com/a',
        internal_domain_policy='host',
        max_depth=2,
        concurrency=1,
        request_delay=0.1,
    )

    engine = CrawlerEngine(config)
    results = await engine.run()

    assert len(results) == 1
    assert 'https://docs.example.com/a' in results
    assert 'https://www.example.com/b' not in results


@pytest.mark.asyncio
async def test_visited_tracking(mock_crawler):
    """Test that crawler doesn't revisit pages."""
    # Create a circular structure: A -> B -> A
    website_structure = {
        'https://example.com/a': ['https://example.com/b'],
        'https://example.com/b': ['https://example.com/a'],  # Circular link back to A
    }
    
    def arun_side_effect(url, **kwargs):
        if url in website_structure:
            return create_mock_page(url, website_structure[url])
        return MockCrawlResult(html=f"<html><body>Page {url}</body></html>")
    
    mock_crawler.arun.side_effect = arun_side_effect
    
    config = CrawlConfig(
        url='https://example.com/a',
        max_depth=3,  # Enough to potentially cause infinite loop
        concurrency=1,
        request_delay=0.1
    )
    
    engine = CrawlerEngine(config)
    results = await engine.run()
    
    # Should only crawl each page once despite circular link
    assert len(results) == 2  # A and B
    assert 'https://example.com/a' in results
    assert 'https://example.com/b' in results
    
    # Should be called exactly twice (not more due to circular link)
    assert mock_crawler.arun.call_count == 2


# Remove the __main__ block since it has issues with undefined functions
# The tests should be run with pytest
