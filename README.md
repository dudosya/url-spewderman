# URL-Spewderman

Web crawler for extracting text content from websites. Outputs consolidated files for LLM ingestion.

## Quick Start

```bash
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman
uv sync

uv run input https://docs.example.com
```

Output saved to `output/docs_example_com.txt`.

## Installation

Requires Python 3.13+ and [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman
uv sync
```

For JavaScript-heavy sites:

```bash
uv run playwright install
```

## Usage

```bash
uv run input <URL> [OPTIONS]
```

### Examples

```bash
# Basic crawl
uv run input https://docs.python.org

# Custom output file
uv run input https://docs.python.org --output-file python_docs.txt

# Shallow crawl (single page)
uv run input https://example.com --max-depth 1

# Deep crawl with more filtering
uv run input https://example.com --max-depth 5 --pruning-threshold 0.7

# Restrict crawling to the exact host only (no subdomains)
uv run input https://example.com --internal-domain-policy host

# Faster crawling
uv run input https://example.com --concurrency 10 --request-delay 0.5

# Keep all content (no filtering)
uv run input https://example.com --no-content-filter
```

## Parameters

| Parameter                   | Default       | Description                                               |
| --------------------------- | ------------- | --------------------------------------------------------- |
| `URL`                       | required      | Website URL to crawl                                      |
| `--max-depth`               | `3`           | Link depth to crawl (1-15)                                |
| `--output-format`           | `txt`         | Format: `txt`, `md`, `json`                               |
| `--output-file`             | auto          | Output filename                                           |
| `--concurrency`             | `5`           | Parallel requests (1-20)                                  |
| `--request-delay`           | `1.0`         | Delay between requests in seconds                         |
| `--max-retries`             | `3`           | Retry attempts for failures                               |
| `--retry-backoff`           | `1.5`         | Backoff multiplier                                        |
| `--no-content-filter`       | `false`       | Disable content filtering                                 |
| `--pruning-threshold`       | `0.3`         | Filter aggressiveness (0.0-1.0)                           |
| `--exclude-tags`            | defaults      | HTML tags to remove                                       |
| `--exclude-external-links`  | `true`        | Remove external links                                     |
| `--exclude-external-images` | `false`       | Remove external images                                    |
| `--internal-domain-policy`  | `registrable` | Crawl scope: `registrable` (subdomains allowed) or `host` |

### Key Parameters

**--max-depth**: How many levels of links to follow.

- `1` = starting page only
- `3` = default
- Higher = more pages, slower

**--pruning-threshold**: Content filter aggressiveness.

- `0.0-0.2` = minimal filtering
- `0.3` = default
- `0.7-1.0` = aggressive filtering

**--concurrency / --request-delay**: Speed vs. politeness tradeoff.

## Output Formats

**TXT:**

```
=== URL: https://example.com/ ===

Content here...

==================================================
```

**MD:**

```markdown
## https://example.com/

Content here...

---
```

**JSON:**

```json
{
  "pages": [{ "url": "https://example.com/", "content": "..." }]
}
```

## Python API

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

asyncio.run(main())
```

## Troubleshooting

**No content extracted:**

- Lower `--pruning-threshold` to `0.1`
- Try `--no-content-filter`
- Install Playwright for JS sites

**Slow crawling:**

- Increase `--concurrency`
- Decrease `--request-delay`

**Getting blocked:**

- Decrease `--concurrency` to 2-3
- Increase `--request-delay` to 2-3s

## Development

```bash
uv run pytest tests/ -v
uv run ruff check src/
```

## License

See [LICENSE](LICENSE).
