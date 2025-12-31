"""
Storage module for saving crawled content in various formats.
"""
import json
from pathlib import Path
import re
from typing import Dict, Any
import urllib.parse
import logging
import hashlib

logger = logging.getLogger(__name__)


def url_to_filename(url: str) -> str:
    """Convert URL to safe filename."""
    parsed = urllib.parse.urlparse(url)
    # Use netloc + path
    netloc = parsed.netloc.replace(":", "_")
    path = parsed.path
    # Combine netloc and path, and preserve extension if present
    if path == "/" or not path:
        base = netloc
        ext = ""
    else:
        # Remove leading slash and convert
        path_clean = path[1:] if path.startswith("/") else path
        ext = Path(path_clean).suffix
        # Remove extension from path_clean for filename sanitization
        if ext:
            path_no_ext = path_clean[: -len(ext)]
            full_path = f"{netloc}_{path_no_ext}"
        else:
            full_path = f"{netloc}_{path_clean}"

        base = full_path

    # Replace unsafe characters
    filename = re.sub(r"[^\w\-\.]+", "_", base)
    filename = filename.strip("_")

    # Ensure not empty
    if not filename:
        filename = "index"

    # Append short hash to avoid collisions
    short_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]

    # Reconstruct filename with extension (if any)
    filename_with_hash = f"{filename}_{short_hash}{ext}"

    # Limit total length
    if len(filename_with_hash) > 200:
        # keep the end of the hash and extension intact
        excess = len(filename_with_hash) - 200
        filename_part = filename[:-excess]
        filename_with_hash = f"{filename_part}_{short_hash}{ext}"

    return filename_with_hash


def save_content(
    url: str,
    content: str,
    base_dir: Path | str = "output",
    format: str = "txt"
) -> Path:
    """
    Save content from a single URL.
    
    Args:
        url: Source URL
        content: Extracted content
        base_dir: Output directory
        format: Output format (txt, md, json)
    
    Returns:
        Path to saved file
    """
    output_dir = Path(base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename_base = url_to_filename(url)
    
    if format == "txt":
        file_path = output_dir / f"{filename_base}.txt"
        file_path.write_text(content, encoding="utf-8")
    
    elif format == "md":
        file_path = output_dir / f"{filename_base}.md"
        file_path.write_text(content, encoding="utf-8")
    
    elif format == "json":
        file_path = output_dir / f"{filename_base}.json"
        data = {
            "url": url,
            "content": content,
            "metadata": {
                "filename": filename_base,
                "format": format
            }
        }
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    return file_path


def save_all_pages(
    results: Dict[str, str],
    base_dir: Path | str = "output",
    format: str = "txt"
) -> Dict[str, Path]:
    """
    Save content from multiple URLs.
    
    Args:
        results: Dictionary mapping URL -> content
        base_dir: Output directory
        format: Output format (txt, md, json)
    
    Returns:
        Dictionary mapping URL -> file path
    """
    saved_paths = {}
    
    for url, content in results.items():
        try:
            file_path = save_content(url, content, base_dir, format)
            saved_paths[url] = file_path
            logger.info("Saved %s to %s", url, file_path)
        except Exception:
            logger.exception("Error saving %s", url)
    
    return saved_paths


def save_consolidated(
    results: Dict[str, str],
    output_file: Path | str,
    format: str = "txt"
) -> Path:
    """
    Save all content to a single consolidated file.
    
    Args:
        results: Dictionary mapping URL -> content
        output_file: Output file path
        format: Output format (txt, md, json)
    
    Returns:
        Path to saved file
    """
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format == "txt":
        with output_path.open("w", encoding="utf-8") as f:
            for url, content in results.items():
                f.write(f"=== URL: {url} ===\n\n")
                f.write(content)
                f.write("\n\n" + "=" * 50 + "\n\n")
    
    elif format == "md":
        with output_path.open("w", encoding="utf-8") as f:
            for url, content in results.items():
                f.write(f"## {url}\n\n")
                f.write(content)
                f.write("\n\n---\n\n")
    
    elif format == "json":
        data = {
            "pages": [
                {"url": url, "content": content}
                for url, content in results.items()
            ]
        }
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    return output_path


def main():
    """Test the storage functions."""
    test_results = {
        "https://example.com/": "# Home Page\n\nWelcome to example.com",
        "https://example.com/about": "# About Us\n\nWe are a company.",
        "https://example.com/contact": "# Contact\n\nGet in touch.",
    }
    
    logger.info("Testing save_all_pages (individual files):")
    saved = save_all_pages(test_results, format="md")
    logger.info("Saved %d files", len(saved))

    logger.info("Testing save_consolidated (single file):")
    consolidated = save_consolidated(test_results, "output/consolidated.md", format="md")
    logger.info("Saved consolidated file: %s", consolidated)


if __name__ == "__main__":
    main()
