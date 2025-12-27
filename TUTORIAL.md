# URL-Spewderman: Complete Usage Tutorial

## Overview

URL-Spewderman is a powerful web crawler designed for extracting clean textual content from organizational websites (universities, companies, etc.) for use with chatbots and LLMs. It features intelligent content filtering, retry logic with exponential backoff, and consolidated output formats.

## Table of Contents

1. [Installation](#installation)
2. [Basic Usage](#basic-usage)
3. [Advanced Features](#advanced-features)
4. [Content Filtering](#content-filtering)
5. [Error Recovery & Retry Logic](#error-recovery--retry-logic)
6. [Output Formats](#output-formats)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)
9. [API Usage](#api-usage)

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### From Source

```bash
# Clone the repository
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### Dependencies

The crawler uses:

- `crawl4ai` for core crawling and content extraction
- `playwright` for JavaScript-heavy sites (automatically installed)
- `pydantic` for configuration validation
- `beautifulsoup4` for improved link extraction

## Basic Usage

### Simple Crawl

```bash
# Basic crawl with default settings (depth=3, concurrency=5)
uv run input https://example.com
```

This will:

1. Crawl `https://example.com` and all internal links up to 3 levels deep
2. Save each page as individual files in the `output/` directory
3. Use default content filtering to remove navigation, headers, footers

### Consolidated Output

```bash
# Save all content to a single file
uv run input https://example.com --output-file my_crawl.txt
```

### View All Options

```bash
uv run input --help
```

## Advanced Features

### Depth Control

```bash
# Crawl only 2 levels deep
uv run input https://example.com --max-depth 2

# Maximum depth (15 levels)
uv run input https://example.com --max-depth 15
```

### Concurrency Control

```bash
# Increase concurrent requests for faster crawling (max 20)
uv run input https://example.com --concurrency 10

# Reduce concurrency for rate-limited sites
uv run input https://example.com --concurrency 2
```

### Request Delay

```bash
# Add delay between requests to be polite
uv run input https://example.com --request-delay 2.0

# Minimum delay (0.1 seconds)
uv run input https://example.com --request-delay 0.1
```

## Content Filtering

### Default Filtering

By default, the crawler uses intelligent content filtering with optimized settings for universal compatibility:

- **Pruning threshold**: 0.3 (balanced - keeps more content than previous 0.5 default)
- **Excluded HTML tags**: `nav`, `footer`, `header`, `aside`, `form`, `script`, `style`, `iframe`, `noscript`, `svg`, `canvas`, and many more
- **External content**: External links excluded by default, images included

The default settings work well for most organizational websites (universities, companies, documentation sites). For challenging websites, you may need to adjust these settings.

### Disable Filtering

```bash
# Keep all content including navigation, headers, footers
uv run input https://example.com --no-content-filter
```

### Customize Filtering Aggressiveness

```bash
# Keep more content (0.0 = minimal filtering)
uv run input https://example.com --pruning-threshold 0.2

# Keep less content (1.0 = aggressive filtering)
uv run input https://example.com --pruning-threshold 0.8
```

### Custom Excluded Tags

```bash
# Exclude specific HTML tags
uv run input https://example.com --exclude-tags "nav,footer,header,aside,form,script,style"

# Exclude only navigation
uv run input https://example.com --exclude-tags "nav"
```

### External Content Control

```bash
# Exclude external links from extracted content (default)
uv run input https://example.com --exclude-external-links

# Include external links
uv run input https://example.com --no-exclude-external-links

# Exclude external images
uv run input https://example.com --exclude-external-images
```

## Error Recovery & Retry Logic

### Default Retry Behavior

By default, the crawler will retry failed requests 3 times with exponential backoff.

### Configure Retries

```bash
# Disable retries
uv run input https://example.com --max-retries 0

# Increase retries for unreliable sites
uv run input https://example.com --max-retries 5

# Custom backoff factor (default: 1.5)
uv run input https://example.com --retry-backoff 2.0
```

### How Retry Logic Works

1. **Transient errors** (timeouts, 5xx server errors, network issues) are retried
2. **Permanent errors** (404, 403, invalid URLs) are not retried
3. **Exponential backoff**: Delay = `request_delay × (backoff_factor ^ (attempt - 1))`
   - Attempt 1: Immediate
   - Attempt 2: `1.0s × 1.5^0 = 1.0s` delay
   - Attempt 3: `1.0s × 1.5^1 = 1.5s` delay
   - Attempt 4: `1.0s × 1.5^2 = 2.25s` delay

## Output Formats

### Text Format (Default)

```bash
# Plain text output
uv run input https://example.com --output-format txt --output-file output.txt
```

### Markdown Format

```bash
# Markdown output (preserves headings, lists, links)
uv run input https://example.com --output-format md --output-file output.md
```

### JSON Format

```bash
# JSON output (structured data)
uv run input https://example.com --output-format json --output-file output.json
```

### Output Structure

All formats include:

- Source URL for each page
- Crawl timestamp
- Cleaned content
- Clear section separators

Example text output:

```
========================================
SOURCE: https://example.com/page1
CRAWLED: 2024-12-27 16:30:00
========================================

[Extracted content...]

========================================
SOURCE: https://example.com/page2
CRAWLED: 2024-12-27 16:31:00
========================================

[Extracted content...]
```

## Examples

### Example 1: Academic Website Crawl

```bash
# Crawl a university website with aggressive filtering
uv run input https://university.edu \
  --max-depth 4 \
  --concurrency 8 \
  --pruning-threshold 0.7 \
  --output-file university_content.md \
  --output-format md
```

### Example 2: Documentation Site

```bash
# Crawl documentation with minimal filtering
uv run input https://docs.example.com \
  --max-depth 5 \
  --pruning-threshold 0.3 \
  --exclude-tags "nav,footer" \
  --max-retries 5 \
  --output-file docs.txt
```

### Example 3: Rate-Limited API Documentation

```bash
# Be extra polite with rate-limited sites
uv run input https://api.example.com/docs \
  --max-depth 3 \
  --concurrency 2 \
  --request-delay 3.0 \
  --max-retries 3 \
  --output-file api_docs.json \
  --output-format json
```

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'crawler'"

```bash
# Make sure you're in the project directory
cd url-spewderman

# Install dependencies
uv sync
```

#### 2. Playwright Browser Not Installed

```bash
# Install playwright browsers
uv run playwright install
```

#### 3. Encoding Errors

- The crawler automatically handles encoding issues
- Content is encoded as UTF-8 with error replacement

#### 4. Slow Crawling

- Reduce concurrency: `--concurrency 2`
- Increase request delay: `--request-delay 2.0`
- Check network connectivity

#### 5. Missing Content

- Disable filtering: `--no-content-filter`
- Reduce pruning threshold: `--pruning-threshold 0.2`
- Check if site requires JavaScript (playwright handles this automatically)

### Logging

The crawler provides detailed logging:

- `INFO`: Page crawling started/completed
- `WARNING`: Content filtering statistics, retry attempts
- `ERROR`: Failed crawls (with retry logic)

## API Usage

You can also use the crawler programmatically:

```python
import asyncio
from crawler.model import CrawlConfig
from crawler.engine import crawl_url

async def main():
    # Create configuration
    config = CrawlConfig(
        url="https://example.com",
        max_depth=3,
        output_format="txt",
        concurrency=5,
        request_delay=1.0,
        # Content filtering
        content_filter_enabled=True,
        pruning_threshold=0.3,
        excluded_tags=["nav", "footer", "header", "aside", "form"],
        exclude_external_links=True,
        # Retry configuration
        max_retries=3,
        retry_backoff_factor=1.5,
    )

    # Run crawl
    results = await crawl_url(config)

    # Process results
    for url, content in results.items():
        print(f"URL: {url}")
        print(f"Content length: {len(content)} chars")
        print("---")

# Run async function
asyncio.run(main())
```

### Available Modules

- `crawler.model.CrawlConfig`: Configuration model
- `crawler.engine.crawl_url()`: Main crawling function
- `crawler.engine.CrawlerEngine`: Advanced crawling engine
- `crawler.cleaner.ContentCleaner`: Content filtering utilities
- `crawler.storage.save_consolidated()`: Save results to file

## Best Practices

1. **Start Small**: Test with `--max-depth 1` before deep crawls
2. **Be Polite**: Use `--request-delay 1.0` or higher for production sites
3. **Monitor Memory**: Large crawls may use significant memory
4. **Use Consolidated Output**: `--output-file` for single-file results
5. **Enable Retries**: Default `--max-retries 3` handles transient failures
6. **Adjust Filtering**: Tune `--pruning-threshold` for your content needs

## Contributing

1. Run tests: `uv run pytest tests/ -v`
2. Follow type hints: All Python code must be typed
3. Write tests: Add tests for new features in `tests/`
4. Update documentation: Keep `spec.md` and this tutorial current

## License

See `LICENSE` file for details.

---

_Last Updated: 2024-12-27_  
_For issues or questions, check the GitHub repository or create an issue._
