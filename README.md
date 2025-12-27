# URL-Spewderman 🕷️

A powerful web crawler for extracting clean textual content from organizational websites (universities, companies, etc.) for use with chatbots and LLMs.

## Features

- **Multi-page crawling**: BFS crawling with depth limiting and domain restriction
- **Intelligent content filtering**: Removes navigation, headers, footers, ads using crawl4ai's PruningContentFilter
- **Error recovery**: Retry logic with exponential backoff for transient failures
- **Multiple output formats**: TXT, MD, or JSON with consolidated single-file output
- **Configurable**: Depth, concurrency, request delays, filtering aggressiveness
- **Comprehensive testing**: 41 tests covering all functionality

## Quick Start

### Installation

```bash
# Clone and install
git clone https://github.com/dudosya/url-spewderman.git
cd url-spewderman
uv sync
```

### Basic Usage

```bash
# Crawl a website with default settings
uv run python -m crawler.cli proc-input https://example.com

# Save to a single file
uv run python -m crawler.cli proc-input https://example.com --output-file my_crawl.txt
```

### View All Options

```bash
uv run python -m crawler.cli proc-input --help
```

## Documentation

- **[Complete Tutorial](TUTORIAL.md)**: Detailed usage guide with examples
- **[Specification](spec.md)**: Technical requirements and implementation details
- **[API Reference](TUTORIAL.md#api-usage)**: Programmatic usage examples

## Example Commands

```bash
# Academic website with aggressive filtering
uv run python -m crawler.cli proc-input https://university.edu \
  --max-depth 4 \
  --concurrency 8 \
  --pruning-threshold 0.7 \
  --output-file university_content.md \
  --output-format md

# Documentation site with retries
uv run python -m crawler.cli proc-input https://docs.example.com \
  --max-depth 5 \
  --pruning-threshold 0.3 \
  --max-retries 5 \
  --output-file docs.txt
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Check code quality
uv run ruff check src/
uv run ruff format src/
```

## License

See [LICENSE](LICENSE) file for details.
