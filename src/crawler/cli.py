import typer
from typing import Annotated
from crawler.model import CrawlConfig
import pydantic
import asyncio
from crawler.engine import crawl_url

app = typer.Typer()

@app.command()
def proc_input(
    url: Annotated[str, typer.Argument(help="url string")],
    depth: Annotated[int, typer.Option(help="depth of the crawler")] = 1
):
    try:
        crawl_config = CrawlConfig(url=url,depth=depth) # type: ignore
        print(f"Crawling {url} at depth {depth}")
    except pydantic.ValidationError as e:
        print(e)
        raise typer.Exit(code=1)
        
    result = asyncio.run(crawl_url(crawl_config))
    print(result)
    
if __name__ == "__main__":
    app()