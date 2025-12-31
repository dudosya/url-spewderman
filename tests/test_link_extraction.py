"""
Tests for improved link extraction using BeautifulSoup.

Tests that the _extract_links method correctly extracts links from HTML
using BeautifulSoup instead of regex.
"""

import pytest
from crawler.engine import CrawlerEngine
from crawler.model import CrawlConfig


class TestLinkExtraction:
    """Test link extraction functionality."""
    
    def test_extract_links_basic(self):
        """Test basic link extraction from HTML."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="/page2">Page 2</a>
            <a href="https://example.com/page3">Page 3</a>
            <a href="https://external.com/page">External</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "https://example.com/page3" in links
        assert "https://external.com/page" in links
        assert len(links) == 4
    
    def test_extract_links_skip_anchors(self):
        """Test that anchor links are skipped."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="#section1">Anchor 1</a>
            <a href="/page1">Page 1</a>
            <a href="#top">Back to top</a>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "#section1" not in links
        assert "#top" not in links
        assert len(links) == 2
    
    def test_extract_links_skip_javascript(self):
        """Test that javascript links are skipped."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="javascript:alert('hello')">JS Link</a>
            <a href="/page1">Page 1</a>
            <a href="javascript:void(0)">JS Void</a>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "javascript:alert('hello')" not in links
        assert "javascript:void(0)" not in links
        assert len(links) == 2
    
    def test_extract_links_skip_mailto_tel(self):
        """Test that mailto and tel links are skipped."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="mailto:test@example.com">Email</a>
            <a href="/page1">Page 1</a>
            <a href="tel:+1234567890">Phone</a>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "mailto:test@example.com" not in links
        assert "tel:+1234567890" not in links
        assert len(links) == 2
    
    def test_extract_links_skip_other_protocols(self):
        """Test that other non-HTTP protocols are skipped."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="ftp://example.com/file">FTP</a>
            <a href="/page1">Page 1</a>
            <a href="file:///local/file">File</a>
            <a href="data:text/plain,Hello">Data URI</a>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "ftp://example.com/file" not in links
        assert "file:///local/file" not in links
        assert "data:text/plain,Hello" not in links
        assert len(links) == 2
    
    def test_extract_links_empty_href(self):
        """Test that empty href attributes are skipped."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="">Empty</a>
            <a href="/page1">Page 1</a>
            <a href="   ">Whitespace</a>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "/page1" in links
        assert "/page2" in links
        assert "" not in links
        assert "   " not in links
        assert len(links) == 2
    
    def test_extract_links_multiple_tag_types(self):
        """Test that link extraction only includes anchor tags, not assets."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <head>
            <link href="/style.css" rel="stylesheet">
            <link href="https://cdn.example.com/lib.css" rel="stylesheet">
        </head>
        <body>
            <a href="/page1">Page 1</a>
            <map name="imagemap">
                <area shape="rect" coords="0,0,50,50" href="/area1">
                <area shape="circle" coords="100,100,50" href="/area2">
            </map>
            <a href="/page2">Page 2</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        # Should only find anchor links, not <link> tags (which are for stylesheets)
        # and not <area> tags (which are typically for image maps, not navigation)
        assert "/page1" in links
        assert "/page2" in links
        # CSS links should be filtered out (they're assets)
        assert "/style.css" not in links
        assert "https://cdn.example.com/lib.css" not in links
        # Note: <area> tags are NOT extracted per the implementation comment
        # "We're NOT including <link> or <area> tags anymore since they're
        # typically for assets (CSS, favicons, image maps) not HTML pages"
        assert len(links) == 2
    
    def test_extract_links_fallback_to_regex(self):
        """Test that fallback to regex works if BeautifulSoup fails."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Invalid HTML that BeautifulSoup might struggle with
        html = "Invalid HTML <a href='/page1'>Page 1</a> <a href='/page2'>Page 2</a>"
        
        # Mock BeautifulSoup to raise an exception
        import bs4
        original_beautifulsoup = bs4.BeautifulSoup
        
        def mock_beautifulsoup(*args, **kwargs):
            raise Exception("BeautifulSoup failed")
        
        bs4.BeautifulSoup = mock_beautifulsoup
        
        try:
            links = engine._extract_links(html, "https://example.com")
            
            # Should still extract links using regex fallback
            assert "/page1" in links
            assert "/page2" in links
            assert len(links) == 2
        finally:
            # Restore original BeautifulSoup
            bs4.BeautifulSoup = original_beautifulsoup
    
    def test_extract_links_relative_urls(self):
        """Test extraction of various relative URL formats."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        html = """
        <html>
        <body>
            <a href="page1.html">Relative</a>
            <a href="./page2.html">Current dir</a>
            <a href="../parent/page3.html">Parent dir</a>
            <a href="subdir/page4.html">Subdirectory</a>
            <a href="//example.com/protocol-relative">Protocol relative</a>
        </body>
        </html>
        """
        
        links = engine._extract_links(html, "https://example.com")
        
        assert "page1.html" in links
        assert "./page2.html" in links
        assert "../parent/page3.html" in links
        assert "subdir/page4.html" in links
        assert "//example.com/protocol-relative" in links
        assert len(links) == 5


class TestURLNormalization:
    """Test URL normalization to prevent duplicate crawls."""
    
    def test_normalize_url_removes_fragment(self):
        """Test that URL fragments (#section) are removed."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        assert engine._normalize_url("https://example.com/page#section") == "https://example.com/page"
        assert engine._normalize_url("https://example.com/page#") == "https://example.com/page"
        assert engine._normalize_url("https://example.com/#top") == "https://example.com/"
    
    def test_normalize_url_trailing_slash(self):
        """Test that trailing slashes are normalized consistently."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Non-root paths should NOT have trailing slash
        assert engine._normalize_url("https://example.com/page/") == "https://example.com/page"
        assert engine._normalize_url("https://example.com/page") == "https://example.com/page"
        
        # Root path SHOULD keep trailing slash
        assert engine._normalize_url("https://example.com/") == "https://example.com/"
        assert engine._normalize_url("https://example.com") == "https://example.com/"
    
    def test_normalize_url_case_insensitive_domain(self):
        """Test that domain is normalized to lowercase."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        assert engine._normalize_url("https://EXAMPLE.COM/page") == "https://example.com/page"
        assert engine._normalize_url("https://Example.Com/Page") == "https://example.com/Page"  # Path case preserved
    
    def test_normalize_url_removes_default_ports(self):
        """Test that default ports are removed."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        assert engine._normalize_url("http://example.com:80/page") == "http://example.com/page"
        assert engine._normalize_url("https://example.com:443/page") == "https://example.com/page"
        # Non-default ports should be kept
        assert engine._normalize_url("https://example.com:8080/page") == "https://example.com:8080/page"
    
    def test_normalize_url_sorts_query_params(self):
        """Test that query parameters are sorted for consistency."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        # Same params in different order should normalize to same URL
        url1 = engine._normalize_url("https://example.com/page?b=2&a=1")
        url2 = engine._normalize_url("https://example.com/page?a=1&b=2")
        assert url1 == url2
        assert url1 == "https://example.com/page?a=1&b=2"
    
    def test_normalize_url_preserves_query_values(self):
        """Test that query parameter values are preserved."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        normalized = engine._normalize_url("https://example.com/search?q=hello+world&page=1")
        assert "q=hello+world" in normalized or "q=hello%20world" in normalized
        assert "page=1" in normalized
    
    def test_duplicate_urls_normalized_to_same(self):
        """Test that various duplicate URL forms normalize to same value."""
        engine = CrawlerEngine(CrawlConfig(url="https://example.com"))
        
        urls = [
            "https://example.com/page",
            "https://example.com/page/",
            "https://example.com/page#section",
            "https://example.com/page/#section",
            "https://EXAMPLE.COM/page",
            "https://example.com:443/page",
        ]
        
        normalized = [engine._normalize_url(url) for url in urls]
        # All should normalize to the same URL
        assert len(set(normalized)) == 1
        assert normalized[0] == "https://example.com/page"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
