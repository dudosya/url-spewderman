# URL-Spewderman 🕷️

A powerful web crawler for extracting clean textual content from websites for use with chatbots and LLMs. Perfect for creating knowledge bases from documentation sites, company websites, and more.

## Quick Start (30 seconds)

```bash
# 1. Clone and install
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman
uv sync

# 2. Crawl any website
uv run input https://docs.example.com
```

That's it! Your content will be saved to `output/docs_example_com.txt`.

---

## Features

- 🕸️ **Multi-page crawling** - BFS crawling with configurable depth and domain restriction
- 🧹 **Smart content filtering** - Automatically removes navigation, headers, footers, ads
- 🔄 **Error recovery** - Retry logic with exponential backoff for unreliable connections
- 📄 **Consolidated output** - All pages combined into one LLM-ready file
- 🚀 **Concurrent crawling** - Fast parallel requests with rate limiting
- 🔗 **URL deduplication** - Intelligent normalization prevents duplicate pages

---

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Install

```bash
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman
uv sync
```

If you need Playwright browsers for JavaScript-heavy sites:

```bash
uv run playwright install
```

---

## Usage Examples

### Basic Crawl

```bash
# Crawl with all defaults - saves to output/<domain>.txt
uv run input https://docs.python.org
```

### Specify Output File

```bash
# Custom output filename
uv run input https://docs.python.org --output-file python_docs.txt

# Different format (md or json)
uv run input https://docs.python.org --output-file docs.md --output-format md
```

### Control Crawl Depth

```bash
# Shallow crawl (faster, less content)
uv run input https://example.com --max-depth 1

# Deep crawl (slower, more comprehensive)
uv run input https://example.com --max-depth 5
```

### Faster Crawling

```bash
# Increase concurrency for faster crawling
uv run input https://example.com --concurrency 10 --request-delay 0.5
```

### Aggressive Content Filtering

```bash
# Keep only main content, remove more boilerplate
uv run input https://example.com --pruning-threshold 0.7
```

### Disable Filtering (Keep Everything)

```bash
# Keep all content including nav, headers, footers
uv run input https://example.com --no-content-filter
```

---

## Command Reference

```bash
uv run input <URL> [OPTIONS]
```

### All Parameters

| Parameter                   | Default    | Description                                         |
| --------------------------- | ---------- | --------------------------------------------------- |
| `URL`                       | (required) | The website URL to crawl                            |
| `--max-depth`               | `3`        | How many links deep to crawl (1-15)                 |
| `--output-format`           | `txt`      | Output format: `txt`, `md`, or `json`               |
| `--output-file`             | auto       | Custom output filename (default: `<domain>.txt`)    |
| `--concurrency`             | `5`        | Number of parallel requests (1-20)                  |
| `--request-delay`           | `1.0`      | Seconds between requests (0.1-5.0)                  |
| `--max-retries`             | `3`        | Retry attempts for failed requests (0-10)           |
| `--retry-backoff`           | `1.5`      | Exponential backoff multiplier (1.0-5.0)            |
| `--no-content-filter`       | `false`    | Disable content filtering (keep everything)         |
| `--pruning-threshold`       | `0.3`      | Filter aggressiveness: 0.0=keep more, 1.0=keep less |
| `--exclude-tags`            | (defaults) | Comma-separated HTML tags to remove                 |
| `--exclude-external-links`  | `true`     | Remove links to other domains                       |
| `--exclude-external-images` | `false`    | Remove images from other domains                    |

### Parameter Details

#### `--max-depth`

Controls how many levels of links to follow from the starting URL.

- `1` = Only the starting page
- `2` = Starting page + pages it links to
- `3` = Default, good balance of coverage and speed

#### `--pruning-threshold`

How aggressively to filter out boilerplate content:

- `0.0-0.2` = Keep almost everything (minimal filtering)
- `0.3` = Default, balanced for most sites
- `0.5-0.7` = Aggressive, removes more sidebar/footer content
- `0.8-1.0` = Very aggressive, may remove useful content

#### `--concurrency` and `--request-delay`

Balance speed vs. server load:

- High concurrency + low delay = Fast but may overwhelm servers
- Low concurrency + high delay = Slow but polite
- Default (`5` + `1.0s`) works for most sites

---

## Real-World Examples

### Documentation Site

```bash
uv run input https://docs.python.org \
  --max-depth 4 \
  --output-file python_docs.txt
```

### Company Website

```bash
uv run input https://company.com \
  --max-depth 3 \
  --pruning-threshold 0.5 \
  --output-file company_info.md \
  --output-format md
```

### Large Site (Be Polite)

```bash
uv run input https://large-site.com \
  --max-depth 5 \
  --concurrency 3 \
  --request-delay 2.0 \
  --max-retries 5
```

### Quick Single-Page Scrape

```bash
uv run input https://example.com/specific-page \
  --max-depth 1 \
  --output-file single_page.txt
```

---

## Output Format

The crawler produces a consolidated file with all pages separated by markers:

**TXT format:**

```
=== URL: https://example.com/ ===

# Main content here...

==================================================

=== URL: https://example.com/about ===

# About page content...

==================================================
```

**MD format:**

```markdown
## https://example.com/

Main content here...

---

## https://example.com/about

About page content...

---
```

**JSON format:**

```json
{
  "pages": [
    { "url": "https://example.com/", "content": "..." },
    { "url": "https://example.com/about", "content": "..." }
  ]
}
```

---

## Programmatic Usage (Python API)

```python
import asyncio
from crawler.model import CrawlConfig
from crawler.engine import crawl_url
from crawler.storage import save_consolidated

async def main():
    config = CrawlConfig(
        url="https://example.com",
        max_depth=3,
        concurrency=5,
        pruning_threshold=0.3,
    )

    results = await crawl_url(config)
    save_consolidated(results, "output.txt", format="txt")

    print(f"Crawled {len(results)} pages")

asyncio.run(main())
```

---

## Troubleshooting

### "No content extracted"

- Try lowering `--pruning-threshold` to `0.1` or `0.2`
- Try `--no-content-filter` to see raw content
- The site may require JavaScript - ensure Playwright is installed

### Slow crawling

- Increase `--concurrency` (up to 20)
- Decrease `--request-delay` (minimum 0.1)
- Reduce `--max-depth` if you don't need deep crawling

### Getting blocked/rate limited

- Decrease `--concurrency` to 2-3
- Increase `--request-delay` to 2-3 seconds
- Increase `--max-retries` to 5

### Duplicate content

- This has been fixed! The crawler now normalizes URLs to prevent duplicates

---

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Check code quality
uv run ruff check src/
uv run ruff format src/
```

---

## License

See [LICENSE](LICENSE) file for details.
