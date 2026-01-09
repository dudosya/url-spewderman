import typer
from typing import Annotated, Optional
from pathlib import Path
import pydantic
import asyncio
import logging
from crawler.model import CrawlConfig
from crawler.engine import crawl_url
from crawler.storage import save_all_pages, save_consolidated

# Configure logging for CLI usage
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)

app = typer.Typer()

@app.command()
def proc_input(
    url: Annotated[str, typer.Argument(help="URL to crawl")],
    max_depth: Annotated[int, typer.Option(help="Maximum crawl depth (1-15)")] = 3,
    output_format: Annotated[str, typer.Option(
        help="Output format: txt, md, or json",
        case_sensitive=False
    )] = "txt",
    output_file: Annotated[Optional[Path], typer.Option(help="Custom output file path")] = None,
    concurrency: Annotated[int, typer.Option(help="Number of concurrent requests (1-20)")] = 5,
    request_delay: Annotated[float, typer.Option(help="Delay between requests in seconds (0.1-5.0)")] = 1.0,
    # Retry options
    max_retries: Annotated[int, typer.Option(
        help="Maximum number of retries for failed requests (0-10, default=3)"
    )] = 3,
    retry_backoff: Annotated[float, typer.Option(
        help="Exponential backoff factor for retries (1.0-5.0, default=1.5)"
    )] = 1.5,
    # Content filtering options
    no_content_filter: Annotated[bool, typer.Option(
        help="Disable content filtering (keep all content including navigation, headers, footers)"
    )] = False,
    pruning_threshold: Annotated[float, typer.Option(
        help="Content filter aggressiveness (0.0=keep more, 1.0=keep less, default=0.3)"
    )] = 0.3,
    exclude_tags: Annotated[Optional[str], typer.Option(
        help="HTML tags to exclude (comma-separated, e.g., 'nav,footer,header')"
    )] = None,
    exclude_external_links: Annotated[bool, typer.Option(
        help="Exclude external links from extracted content"
    )] = True,
    exclude_external_images: Annotated[bool, typer.Option(
        help="Exclude external images from extracted content"
    )] = False,
    target_element: Annotated[Optional[str], typer.Option(
        help="CSS selector for main content area (e.g., 'article', '.md-content', 'main')"
    )] = None,
    scan_full_page: Annotated[bool, typer.Option(
        help="Scan full page by scrolling to load dynamic content"
    )] = True,
    scroll_delay: Annotated[float, typer.Option(
        help="Delay between scrolls when scanning full page (0.0-10.0 seconds)"
    )] = 0.5,
    auto_expand: Annotated[bool, typer.Option(
        help="Automatically expand accordions/collapsibles before extraction"
    )] = True,
    expand_selectors: Annotated[Optional[str], typer.Option(
        help="Custom selectors (comma-separated) to click/open for expansion"
    )] = None,
    js_actions: Annotated[Optional[str], typer.Option(
        help="JavaScript actions to execute (comma-separated strings)"
    )] = None,
):
    """
    Crawl a website and save the extracted content.
    """
    # Validate output_format
    if output_format not in ["txt", "md", "json"]:
        typer.echo(f"Error: output_format must be 'txt', 'md', or 'json', got '{output_format}'")
        raise typer.Exit(code=1)
    
    # Parse excluded tags if provided
    excluded_tags_list = None
    if exclude_tags:
        excluded_tags_list = [tag.strip() for tag in exclude_tags.split(",")]
    
    try:
        # Build config dict, only including excluded_tags if user explicitly provided them
        config_kwargs = {
            "url": url,
            "max_depth": max_depth,
            "output_format": output_format,
            "output_file": output_file,
            "concurrency": concurrency,
            "request_delay": request_delay,
            "max_retries": max_retries,
            "retry_backoff_factor": retry_backoff,
            "content_filter_enabled": not no_content_filter,
            "pruning_threshold": pruning_threshold,
            "exclude_external_links": exclude_external_links,
            "exclude_external_images": exclude_external_images,
        }
        
        # Only override excluded_tags if user explicitly provided them
        if excluded_tags_list:
            config_kwargs["excluded_tags"] = excluded_tags_list
        
        # Add target_element if provided
        if target_element:
            config_kwargs["target_element"] = target_element
        # Otherwise, let the model use its default
        
        # Add dynamic content options
        config_kwargs["scan_full_page"] = scan_full_page
        config_kwargs["scroll_delay"] = scroll_delay
        config_kwargs["auto_expand"] = auto_expand
        if expand_selectors:
            config_kwargs["expand_selectors"] = [sel.strip() for sel in expand_selectors.split(",") if sel.strip()]
        if js_actions:
            config_kwargs["js_actions"] = [action.strip() for action in js_actions.split(",")]
        
        crawl_config = CrawlConfig(**config_kwargs)  # type: ignore
        
        # Print configuration summary
        typer.echo(f"Crawling {url} with:")
        typer.echo(f"  - Depth: {max_depth}")
        typer.echo(f"  - Concurrency: {concurrency}")
        typer.echo(f"  - Max retries: {max_retries}")
        if max_retries > 0:
            typer.echo(f"  - Retry backoff factor: {retry_backoff}")
        typer.echo(f"  - Content filtering: {'Enabled' if not no_content_filter else 'Disabled'}")
        if not no_content_filter:
            typer.echo(f"  - Pruning threshold: {pruning_threshold}")
        typer.echo(f"  - Exclude external links: {exclude_external_links}")
        # Show actual excluded tags (either user-provided or model defaults)
        actual_tags = crawl_config.excluded_tags
        if actual_tags:
            typer.echo(f"  - Excluded tags: {', '.join(actual_tags)}")
        typer.echo(f"  - Scan full page: {scan_full_page}")
        typer.echo(f"  - Auto-expand accordions: {auto_expand}")
        if expand_selectors:
            typer.echo(f"  - Expand selectors: {expand_selectors}")
        if scan_full_page:
            typer.echo(f"  - Scroll delay: {scroll_delay}s")
        if js_actions:
            typer.echo(f"  - JS actions: {js_actions}")
    except pydantic.ValidationError as e:
        typer.echo(f"Configuration error: {e}")
        raise typer.Exit(code=1)
    
    try:
        # Crawl the website
        results = asyncio.run(crawl_url(crawl_config))
        
        if not results:
            typer.echo("No content was extracted from the website.")
            raise typer.Exit(code=1)

        typer.echo(f"Successfully crawled {len(results)} pages")
        
        # Determine output path - default to consolidated file
        if output_file:
            output_path = Path(output_file)
        else:
            # Generate default filename from domain
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace(":", "_").replace(".", "_")
            default_filename = f"{domain}.{output_format}"
            output_path = Path("output") / default_filename
        
        # If output_path is a simple filename (no directory), prepend "output/"
        if len(output_path.parents) == 1 and output_path.parent == Path("."):
            output_path = Path("output") / output_path
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save all pages to a single consolidated file (default behavior)
        save_consolidated(results, output_path, format=output_format)
        
        # Log where file was saved with absolute path
        absolute_path = output_path.resolve()
        typer.echo(f"Saved to: {absolute_path}")
            
    except Exception as e:
        typer.echo(f"Error during crawling: {e}")
        raise typer.Exit(code=1)
    
    
if __name__ == "__main__":
    app()
