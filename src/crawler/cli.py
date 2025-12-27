import typer
from typing import Annotated, Optional
from pathlib import Path
import pydantic
import asyncio
from crawler.model import CrawlConfig
from crawler.engine import crawl_url
from crawler.storage import save_all_pages, save_consolidated

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
        help="Content filter aggressiveness (0.0=keep more, 1.0=keep less, default=0.5)"
    )] = 0.5,
    exclude_tags: Annotated[Optional[str], typer.Option(
        help="HTML tags to exclude (comma-separated, e.g., 'nav,footer,header')"
    )] = None,
    exclude_external_links: Annotated[bool, typer.Option(
        help="Exclude external links from extracted content"
    )] = True,
    exclude_external_images: Annotated[bool, typer.Option(
        help="Exclude external images from extracted content"
    )] = False,
):
    """
    Crawl a website and save the extracted content.
    """
    # Validate output_format
    if output_format not in ["txt", "md", "json"]:
        print(f"Error: output_format must be 'txt', 'md', or 'json', got '{output_format}'")
        raise typer.Exit(code=1)
    
    # Parse excluded tags if provided
    excluded_tags_list = None
    if exclude_tags:
        excluded_tags_list = [tag.strip() for tag in exclude_tags.split(",")]
    
    try:
        crawl_config = CrawlConfig(
            url=url,  # type: ignore
            max_depth=max_depth,
            output_format=output_format,  # type: ignore
            output_file=output_file,
            concurrency=concurrency,
            request_delay=request_delay,
            # Retry configuration
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff,
            # Content filtering configuration
            content_filter_enabled=not no_content_filter,
            pruning_threshold=pruning_threshold,
            excluded_tags=excluded_tags_list if excluded_tags_list else None,
            exclude_external_links=exclude_external_links,
            exclude_external_images=exclude_external_images,
        )
        
        # Print configuration summary
        print(f"Crawling {url} with:")
        print(f"  - Depth: {max_depth}")
        print(f"  - Concurrency: {concurrency}")
        print(f"  - Max retries: {max_retries}")
        if max_retries > 0:
            print(f"  - Retry backoff factor: {retry_backoff}")
        print(f"  - Content filtering: {'Enabled' if not no_content_filter else 'Disabled'}")
        if not no_content_filter:
            print(f"  - Pruning threshold: {pruning_threshold}")
        print(f"  - Exclude external links: {exclude_external_links}")
        if excluded_tags_list:
            print(f"  - Excluded tags: {', '.join(excluded_tags_list)}")
    except pydantic.ValidationError as e:
        print(f"Configuration error: {e}")
        raise typer.Exit(code=1)
    
    try:
        # Crawl the website
        results = asyncio.run(crawl_url(crawl_config))
        
        if not results:
            print("No content was extracted from the website.")
            raise typer.Exit(code=1)
        
        print(f"Successfully crawled {len(results)} pages")
        
        # Save results
        if output_file:
            # If output_file is a simple filename (no directory), prepend "output/"
            output_path = Path(output_file)
            if len(output_path.parents) == 1 and output_path.parent == Path("."):
                # Simple filename, prepend output directory
                output_path = Path("output") / output_path
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save all pages to a single consolidated file
            print(f"Saving consolidated output to {output_path}")
            save_consolidated(results, output_path, format=output_format)
            print(f"Consolidated file saved: {output_path}")
        else:
            # Save each page as individual file in output/ directory
            print(f"Saving {len(results)} pages to output/ directory")
            saved_paths = save_all_pages(results, format=output_format)
            print(f"Saved {len(saved_paths)} files")
            
    except Exception as e:
        print(f"Error during crawling: {e}")
        raise typer.Exit(code=1)
    
    
if __name__ == "__main__":
    app()
