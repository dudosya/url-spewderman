from pathlib import Path
import re
import urllib.parse

def save_markdown(url: str, content: str, base_dir: Path | str = "output"):
    # make sure the output dir exists
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    
    # extract different parts of url
    url_path = urllib.parse.urlparse(url).path
    
    # convert url path to filename
    filename = re.sub(r"[^\w-]+", "-", url_path)
    filename = filename.strip("-")
    if len(filename) == 0:
        filename = "index"
    
    # write content to the file
    file_path = output_dir / f"{filename}.md"
    file_path.write_text(content, encoding='utf-8')
    
def main():
    url = "https://example.com/blog/post-1"
    content = "# Hello"
    
    save_markdown(url, content)
    
if __name__ == "__main__":
    main()
    
    