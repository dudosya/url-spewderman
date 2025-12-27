from typing import Set, List, Dict, Optional
from urllib.parse import urlparse, urljoin
import asyncio
import logging
import sys

from crawler.model import CrawlConfig
from crawler.cleaner import ContentCleaner
from crawl4ai import AsyncWebCrawler

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Enhanced crawler engine with BFS, domain restriction, and visited tracking."""

    def __init__(self, config: CrawlConfig):
        self.config = config
        self.visited: Set[str] = set()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: Dict[str, str] = {}
        self.base_domain = self._extract_domain(str(config.url))
        self.cleaner = ContentCleaner(config)
        
        # Initialize queue with starting URL at depth 0
        self.queue.put_nowait((str(config.url), 0))
        
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for domain restriction."""
        parsed = urlparse(url)
        return parsed.netloc
        
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as the base URL."""
        return self._extract_domain(url) == self.base_domain
        
    def _extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content using BeautifulSoup."""
        from bs4 import BeautifulSoup
        
        links = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all anchor tags with href attribute
            for a_tag in soup.find_all('a', href=True):
                href = str(a_tag['href'])
                
                # Skip anchors, javascript, mailto, tel, and other non-HTTP links
                if (href.startswith('#') or 
                    href.startswith('javascript:') or 
                    href.startswith('mailto:') or 
                    href.startswith('tel:') or
                    href.startswith('data:') or
                    href.startswith('file:') or
                    href.startswith('ftp:')):
                    continue
                    
                # Skip empty hrefs
                if not href.strip():
                    continue
                    
                links.append(href)
                
            # Also check for link tags with href (less common but possible)
            for link_tag in soup.find_all('link', href=True):
                href = str(link_tag['href'])
                if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:', 'file:', 'ftp:')):
                    links.append(href)
                    
            # Check for area tags with href (image maps)
            for area_tag in soup.find_all('area', href=True):
                href = str(area_tag['href'])
                if href and not href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:', 'file:', 'ftp:')):
                    links.append(href)
                    
        except Exception as e:
            logger.warning(f"Error parsing HTML for links: {e}")
            # Fallback to regex extraction if BeautifulSoup fails
            import re
            href_pattern = r'href=["\']([^"\']+)["\']'
            for match in re.finditer(href_pattern, html_content, re.IGNORECASE):
                link = match.group(1)
                if (link.startswith('#') or link.startswith('javascript:') or 
                    link.startswith('mailto:') or link.startswith('tel:')):
                    continue
                links.append(link)
                
        return links
        
    async def _crawl_page(self, url: str) -> Optional[str]:
        """Crawl a single page with retry logic and return its cleaned markdown content."""
        # If max_retries is 0, use the original logic without retries
        if self.config.max_retries == 0:
            return await self._crawl_page_single(url)
        
        # Implement retry logic with exponential backoff
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):  # +1 for the initial attempt
            try:
                if attempt > 0:
                    # Calculate exponential backoff delay
                    backoff_delay = self.config.request_delay * (self.config.retry_backoff_factor ** (attempt - 1))
                    logger.info(f"Retry attempt {attempt}/{self.config.max_retries} for {url} after {backoff_delay:.2f}s delay")
                    await asyncio.sleep(backoff_delay)
                
                result = await self._crawl_page_single(url, is_retry=(attempt > 0))
                if result is not None:
                    if attempt > 0:
                        logger.info(f"Successfully crawled {url} on retry attempt {attempt}")
                    return result
                    
            except Exception as e:
                last_exception = e
                # Check if we should retry based on error type
                if not self._should_retry_error(e):
                    logger.warning(f"Permanent error for {url}, not retrying: {e}")
                    break
                    
                if attempt < self.config.max_retries:
                    logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed for {url}: {e}")
        
        return None
    
    def _should_retry_error(self, error: Exception) -> bool:
        """Determine if an error should be retried based on error type."""
        error_str = str(error).lower()
        
        # Permanent errors (should not retry)
        permanent_indicators = [
            "404", "not found",
            "403", "forbidden", 
            "401", "unauthorized",
            "400", "bad request",
            "invalid url",
            "unsupported protocol",
        ]
        
        for indicator in permanent_indicators:
            if indicator in error_str:
                return False
        
        # Transient errors (should retry)
        transient_indicators = [
            "timeout", "timed out",
            "connection", "network",
            "429", "too many requests",
            "500", "502", "503", "504", "server error",
            "gateway", "service unavailable",
        ]
        
        for indicator in transient_indicators:
            if indicator in error_str:
                return True
        
        # Default to retry for unknown errors
        return True
    
    async def _crawl_page_single(self, url: str, is_retry: bool = False) -> Optional[str]:
        """Crawl a single page (without retry logic) and return its cleaned markdown content."""
        # Suppress crawl4ai's output to avoid encoding errors
        import sys
        import io
        
        # Save original stdout/stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        # Redirect to StringIO to capture output
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        
        try:
            # Create crawler config with content filtering
            crawler_config = self.cleaner.create_crawler_config()
            
            async with AsyncWebCrawler() as crawler:
                # Restore stdout/stderr for our logging
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                
                # Add delay to respect rate limiting (unless this is a retry, delay already applied)
                if self.config.request_delay > 0 and not is_retry:
                    await asyncio.sleep(self.config.request_delay)
                    
                # Safe logging
                try:
                    log_msg = f"Crawling: {url}"
                    if is_retry:
                        log_msg = f"Retrying: {url}"
                    logger.info(log_msg)
                except UnicodeEncodeError:
                    logger.info(f"Crawling: [URL with special characters]")
                
                # Redirect again for crawl4ai's operations
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                
                try:
                    # Use the configured crawler config
                    result = await crawler.arun(url=url, config=crawler_config)
                finally:
                    # Restore for our code
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                
                # Check if result is an async generator (handle crawl4ai's async results)
                try:
                    # Try to iterate if it's async
                    if hasattr(result, '__aiter__'):
                        # It's an async generator, get the first item
                        async for item in result: # type: ignore
                            result = item
                            break
                except Exception:
                    # Not an async generator or error during iteration, continue with current result
                    pass
                
                # Extract cleaned content using ContentCleaner
                content = self.cleaner.extract_cleaned_content(result)
                
                # Get content statistics for logging
                stats = self.cleaner.get_content_stats(result)
                
                if content and content != "No content extracted":
                    # Log content statistics
                    if stats["has_filtered_content"] and stats["raw_length"] > 0:
                        reduction = stats["reduction_percentage"]
                        logger.info(
                            f"Content filtered: {stats['raw_length']} → {stats['filtered_length']} "
                            f"chars ({reduction:.1f}% reduction)"
                        )
                    
                    # Ensure content is properly encoded
                    return content.encode('utf-8', errors='replace').decode('utf-8')
                else:
                    logger.warning(f"No content extracted from {url}")
                    return None
                    
        except Exception as e:
            # Restore stdout/stderr in case of error
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
            # Check if it's an encoding error
            if isinstance(e, UnicodeEncodeError):
                # Encoding error, try to get the message without special chars
                try:
                    logger.error(f"Encoding error while crawling {url}")
                except:
                    logger.error("Encoding error while crawling a URL")
            else:
                # Other error
                try:
                    logger.error(f"Failed to crawl {url}: {e}")
                except UnicodeEncodeError:
                    logger.error(f"Failed to crawl [URL]: {e}")
            # Re-raise the exception for retry logic to handle
            raise
        finally:
            # Ensure stdout/stderr are restored
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
    async def run(self) -> Dict[str, str]:
        """Run the BFS crawler and return all crawled content."""
        workers = [
            asyncio.create_task(self._worker())
            for _ in range(min(self.config.concurrency, 10))
        ]
        
        # Wait for all workers to complete
        await self.queue.join()
        
        # Cancel workers
        for worker in workers:
            worker.cancel()
            
        # Wait for all workers to be cancelled
        await asyncio.gather(*workers, return_exceptions=True)
        
        return self.results
        
    async def _worker(self):
        """Worker task that processes URLs from the queue."""
        while True:
            try:
                url, depth = await self.queue.get()
                
                # Skip if already visited
                if url in self.visited:
                    self.queue.task_done()
                    continue
                    
                # Skip if exceeds max depth
                if depth > self.config.max_depth:
                    self.queue.task_done()
                    continue
                    
                # Mark as visited
                self.visited.add(url)
                
                # Crawl the page
                content = await self._crawl_page(url)
                if content:
                    self.results[url] = content
                    
                    # Extract links if not at max depth
                    if depth < self.config.max_depth:
                        links = self._extract_links(content, url)
                        for link in links:
                            # Convert relative to absolute URL
                            absolute_link = urljoin(url, link)
                            
                            # Only add if same domain and not visited
                            if (self._is_same_domain(absolute_link) and 
                                absolute_link not in self.visited):
                                self.queue.put_nowait((absolute_link, depth + 1))
                                
                self.queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")
                self.queue.task_done()


async def crawl_url(config: CrawlConfig) -> Dict[str, str]:
    """
    Crawl a website using BFS with domain restriction and depth limiting.
    
    Args:
        config: Crawl configuration
        
    Returns:
        Dictionary mapping URLs to their markdown content
    """
    engine = CrawlerEngine(config)
    return await engine.run()
