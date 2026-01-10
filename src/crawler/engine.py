from typing import Set, List, Dict, Optional, Tuple, Any
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from ipaddress import ip_address
import asyncio
import logging
import sys

from crawler.model import CrawlConfig
from crawler.cleaner import ContentCleaner
from crawl4ai import AsyncWebCrawler

try:
    from publicsuffix2 import get_sld  # type: ignore
except Exception:  # pragma: no cover
    get_sld = None  # type: ignore

logger = logging.getLogger(__name__)


class CrawlerEngine:
    """Enhanced crawler engine with BFS, domain restriction, and visited tracking."""

    def __init__(self, config: CrawlConfig):
        self.config = config
        self.visited: Set[str] = set()
        self.queued: Set[str] = set()  # Track URLs already added to queue to prevent duplicates
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: Dict[str, str] = {}
        self.cleaner = ContentCleaner(config)
        self._visited_lock = asyncio.Lock()  # Protect visited/queued sets from race conditions
        
        # Normalize and initialize queue with starting URL at depth 0
        start_url = self._normalize_url(str(config.url))
        self.base_scope = self._scope_key(start_url)
        self.base_domain = self.base_scope
        self.queue.put_nowait((start_url, 0))
        self.queued.add(start_url)
        
    def _extract_domain(self, url: str) -> str:
        """Extract hostname from URL for domain restriction (ignores ports)."""
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname.lower()
        # Fallback to netloc if hostname isn't available
        return parsed.netloc.lower().split(":", 1)[0]

    def _registrable_domain(self, host: str) -> str:
        """Compute registrable domain (eTLD+1) for a host; fallback safely for IP/localhost."""
        host = host.strip(".").lower()
        if not host:
            return host

        if host == "localhost":
            return host

        try:
            ip_address(host)
            return host
        except ValueError:
            pass

        if get_sld is None:
            # Dependency not available; fallback to host-only scoping.
            return host

        try:
            sld = get_sld(host)
            return sld or host
        except Exception:
            return host

    def _scope_key(self, url: str) -> str:
        """Return the key used for internal/external scoping based on config policy."""
        host = self._extract_domain(url)
        policy = getattr(self.config, "internal_domain_policy", "registrable")
        if policy == "host":
            return host
        return self._registrable_domain(host)
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize a URL to prevent duplicate crawls of the same resource.
        
        Normalizations applied:
        - Remove URL fragments (#section)
        - Normalize trailing slashes (remove for non-root paths)
        - Lowercase the scheme and domain
        - Sort query parameters for consistency
        - Remove default ports (80 for http, 443 for https)
        """
        parsed = urlparse(url)
        
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove default ports
        if ':' in netloc:
            host, port = netloc.rsplit(':', 1)
            if (scheme == 'http' and port == '80') or (scheme == 'https' and port == '443'):
                netloc = host
        
        # Normalize path - remove trailing slash unless it's the root
        path = parsed.path
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        # If path is empty, make it '/'
        if not path:
            path = '/'
        
        # Sort query parameters for consistency
        query = parsed.query
        if query:
            # Parse, sort, and re-encode query parameters
            params = parse_qsl(query, keep_blank_values=True)
            params.sort()
            query = urlencode(params)
        
        # Reconstruct URL without fragment
        normalized = urlunparse((scheme, netloc, path, parsed.params, query, ''))
        
        return normalized
        
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as the base URL."""
        return self._scope_key(url) == self.base_scope
    
    def _should_crawl_url(self, url: str) -> bool:
        """
        Check if a URL should be crawled (HTML pages only, not assets).
        
        Returns:
            True if URL appears to be an HTML page, False for assets
        """
        url_lower = url.lower()
        
        # Skip common asset file extensions
        asset_extensions = [
            '.css', '.js', '.json', '.xml', 
            '.ico', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
            '.mp4', '.mp3', '.avi', '.mov', '.wav',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.woff', '.woff2', '.ttf', '.eot', '.otf',
        ]
        
        if any(url_lower.endswith(ext) for ext in asset_extensions):
            return False
        
        # Default to True (crawl it) – keep extension-based filtering only
        return True
        
    def _extract_links(self, html_content: str, base_url: str, result=None) -> List[str]:
        """Extract all links from HTML content using BeautifulSoup, filtering out non-HTML assets.
        
        If result is provided, also extracts links from crawl4ai's result.links for post-JS loaded links.
        """
        from bs4 import BeautifulSoup
        
        links = []
        
        # First, extract links from crawl4ai result if available (includes post-JS loaded links)
        if result and hasattr(result, 'links') and result.links:
            for link_type in ['internal', 'external']:
                for link_dict in result.links.get(link_type, []):
                    if 'href' in link_dict:
                        href = link_dict['href']
                        # Apply basic filtering
                        if (href.startswith('#') or 
                            href.startswith('javascript:') or 
                            href.startswith('mailto:') or 
                            href.startswith('tel:') or
                            href.startswith('data:') or
                            href.startswith('file:') or
                            href.startswith('ftp:')):
                            continue
                        if not href.strip():
                            continue
                        links.append(href)
        
        # Then extract from HTML content
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
                
                # Filter out common asset file extensions
                href_lower = href.lower()
                if any(href_lower.endswith(ext) for ext in [
                    '.css', '.js', '.json', '.xml', 
                    '.ico', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
                    '.mp4', '.mp3', '.avi', '.mov', '.wav',
                    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                    '.zip', '.tar', '.gz', '.rar', '.7z',
                    '.woff', '.woff2', '.ttf', '.eot', '.otf',
                ]):
                    continue
                
                # Keep asset path/query filtering relaxed to avoid dropping deep pages
                
                links.append(href)
                
            # Note: We're NOT including <link> or <area> tags anymore since they're
            # typically for assets (CSS, favicons, image maps) not HTML pages
                    
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
                
                # Apply same filters in regex fallback
                link_lower = link.lower()
                if any(link_lower.endswith(ext) for ext in [
                    '.css', '.js', '.json', '.xml', 
                    '.ico', '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
                    '.mp4', '.mp3', '.avi', '.mov', '.wav',
                    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                    '.zip', '.tar', '.gz', '.rar', '.7z',
                    '.woff', '.woff2', '.ttf', '.eot', '.otf',
                ]):
                    continue
                
                links.append(link)
                
        # Deduplicate links
        unique_links = []
        seen = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
                
        return unique_links
        
    async def _crawl_page(self, url: str) -> Optional[Tuple[str, str, Any]]:
        """
        Crawl a single page with retry logic and return tuple of (cleaned_content, html_content, result).
        
        Returns:
            Tuple of (cleaned_markdown_content, raw_html_content, crawl_result) or None if crawl failed
        """
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
    
    async def _crawl_page_single(self, url: str, is_retry: bool = False) -> Optional[Tuple[str, str, Any]]:
        """
        Crawl a single page (without retry logic) and return tuple of (cleaned_content, html_content, result).
        
        Returns:
            Tuple of (cleaned_markdown_content, raw_html_content, crawl_result) or None if crawl failed
        """
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
                
                # Handle crawl4ai result which might be an async generator
                actual_result = result
                try:
                    # Check if result is an async generator
                    if hasattr(result, '__aiter__'):
                        # It's an async generator, get the first item
                        async for item in result: # type: ignore
                            actual_result = item
                            break
                except Exception:
                    # Not an async generator or error during iteration, continue with current result
                    pass
                
                # Extract cleaned content using ContentCleaner
                content = self.cleaner.extract_cleaned_content(actual_result)
                
                # Get content statistics for logging
                stats = self.cleaner.get_content_stats(actual_result)
                
                # Extract raw HTML from result for link extraction
                html_content = ""
                if hasattr(actual_result, 'html') and actual_result.html:
                    html_content = actual_result.html
                elif hasattr(actual_result, 'cleaned_html') and actual_result.cleaned_html:
                    html_content = actual_result.cleaned_html
                
                if content and content != "No content extracted":
                    # Log content statistics
                    if stats["has_filtered_content"] and stats["raw_length"] > 0:
                        reduction = stats["reduction_percentage"]
                        logger.info(
                            f"Content filtered: {stats['raw_length']} → {stats['filtered_length']} "
                            f"chars ({reduction:.1f}% reduction)"
                        )
                    
                    # Ensure content is properly encoded
                    cleaned_content = content.encode('utf-8', errors='replace').decode('utf-8')
                    return (cleaned_content, html_content, actual_result)
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
        logger.info(f"Starting crawl of {self.base_domain} with max_depth={self.config.max_depth}, concurrency={self.config.concurrency}")
        
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
        
        logger.info(f"Crawl complete: {len(self.results)} pages crawled, {len(self.visited)} URLs visited")
        
        return self.results
        
    async def _worker(self):
        """Worker task that processes URLs from the queue."""
        while True:
            try:
                url, depth = await self.queue.get()
                
                # Normalize the URL to catch duplicates
                normalized_url = self._normalize_url(url)
                
                # Use lock to safely check and update visited set (prevents race conditions)
                async with self._visited_lock:
                    # Skip if already visited
                    if normalized_url in self.visited:
                        self.queue.task_done()
                        continue
                    
                    # Mark as visited immediately to prevent other workers from processing
                    self.visited.add(normalized_url)
                    
                # Skip if exceeds max depth
                if depth > self.config.max_depth:
                    self.queue.task_done()
                    continue
                
                # Skip asset URLs (CSS, JS, images, etc.)
                if not self._should_crawl_url(normalized_url):
                    logger.debug(f"Skipping asset URL: {normalized_url}")
                    self.queue.task_done()
                    continue
                
                # Crawl the page
                crawl_result = await self._crawl_page(normalized_url)
                if crawl_result:
                    # Unpack tuple: (cleaned_content, html_content, actual_result)
                    cleaned_content, html_content, actual_result = crawl_result
                    
                    # Store cleaned content in results
                    self.results[normalized_url] = cleaned_content
                    
                    # Extract links from HTML content if not at max depth
                    if depth < self.config.max_depth and html_content:
                        links = self._extract_links(html_content, normalized_url, actual_result)
                        
                        # Batch process new links with lock to prevent duplicates
                        new_links = []
                        async with self._visited_lock:
                            for link in links:
                                # Convert relative to absolute URL and normalize
                                absolute_link = urljoin(normalized_url, link)
                                normalized_link = self._normalize_url(absolute_link)
                                
                                # Only add if same domain, not visited/queued, and not an asset
                                if (self._is_same_domain(normalized_link) and 
                                    normalized_link not in self.visited and
                                    normalized_link not in self.queued and
                                    self._should_crawl_url(normalized_link)):
                                    self.queued.add(normalized_link)
                                    new_links.append((normalized_link, depth + 1))
                        
                        # Add to queue outside the lock
                        for link_info in new_links:
                            self.queue.put_nowait(link_info)
                                
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
