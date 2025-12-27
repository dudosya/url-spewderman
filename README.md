# URL-Spewderman 🕷️

A powerful web crawler for extracting clean textual content from organizational websites (universities, companies, etc.) for use with chatbots and LLMs.

> 📖 **New**: Check out the [Complete Tutorial](TUTORIAL.md) for detailed usage examples and configuration guides!

## Features

- **Multi-page crawling**: BFS crawling with depth limiting and domain restriction
- **Intelligent content filtering**: Removes navigation, headers, footers, ads using crawl4ai's PruningContentFilter with optimized defaults for universal compatibility
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

After installation, you have several options:

**Option 1: Using `uv run` (simplest)**

```bash
# Crawl a website with default settings
uv run input https://example.com

# Save to a single file
uv run input https://example.com --output-file my_crawl.txt
```

**Option 2: Activate virtual environment first**

```bash
# On Windows
.venv\Scripts\activate

# Then use input command
input https://example.com
input https://example.com --output-file my_crawl.txt
```

**Option 3: Direct path to script**

```bash
# On Windows
.venv\Scripts\input.exe https://example.com
```

### View All Options

```bash
uv run input --help
```

## 📚 Documentation

| Document                                      | Description                                             |
| --------------------------------------------- | ------------------------------------------------------- |
| **[📖 Complete Tutorial](TUTORIAL.md)**       | Step-by-step usage guide with examples for all features |
| **[📋 Specification](spec.md)**               | Technical requirements and implementation details       |
| **[⚙️ API Reference](TUTORIAL.md#api-usage)** | Programmatic usage examples                             |

**Quick Links:**

- [Installation Guide](TUTORIAL.md#installation)
- [Basic Usage](TUTORIAL.md#basic-usage)
- [Content Filtering](TUTORIAL.md#content-filtering)
- [Error Recovery](TUTORIAL.md#error-recovery--retry-logic)
- [Examples](TUTORIAL.md#examples)

## Example Commands

```bash
# Academic website with aggressive filtering
uv run input https://university.edu \
  --max-depth 4 \
  --concurrency 8 \
  --pruning-threshold 0.7 \
  --output-file university_content.md \
  --output-format md

# Documentation site with retries
uv run input https://docs.example.com \
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

## GitHub Visibility

The [TUTORIAL.md](TUTORIAL.md) file is now prominently featured in this README with:

- A callout banner at the top
- A dedicated documentation section with quick links
- Clear navigation to all tutorial sections

On GitHub, the tutorial will appear:

1. In the repository file list (as `TUTORIAL.md`)
2. Linked from multiple places in the README
3. With proper Markdown rendering for easy reading

To further enhance GitHub visibility:

- The tutorial uses proper Markdown headers and structure
- It includes a table of contents with anchor links
- All code examples are properly formatted

## License

See [LICENSE](LICENSE) file for details.
