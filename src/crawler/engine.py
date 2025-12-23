import asyncio
from crawler.model import CrawlConfig
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

async def crawl_url(config: CrawlConfig):
    async with AsyncWebCrawler() as crawler:
        results = await crawler.arun(url=str(config.url))
        return str(results.markdown) # type: ignore