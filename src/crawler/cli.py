import typer
from typing import Annotated

app = typer.Typer()

@app.command()
def proc_input(
    url: Annotated[str, typer.Argument(help="url string")],
    depth: Annotated[int, typer.Option(help="depth of the crawler")] = 1
):
    print(f"Crawling {url} at depth {depth}")
    
    

if __name__ == "__main__":
    app()