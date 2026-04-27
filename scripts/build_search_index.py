#!/usr/bin/env python3
"""
Build search index for Jekyll site.
Run this locally before pushing to GitHub:
    python scripts/build_search_index.py
It scans all Markdown/HTML pages, extracts titles, and writes search.json.
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
OUT = ROOT / "search.json"

# Directories/files to skip
EXCLUDE_DIRS = {
    ".git", "_site", "_includes", "_layouts", "_sass", ".venv", "venv",
    "node_modules", ".qoder", ".trae", "scripts", "assets", "img",
}
EXCLUDE_FILES = {"README.md", "AGENTS.md", "search.json"}

def extract_title(path: Path) -> str | None:
    """Extract page title from front matter or first # heading."""
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None

    # 1. Try front matter
    if content.startswith("---"):
        try:
            _, fm, body = content.split("---", 2)
        except ValueError:
            fm, body = "", content
        m = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
        if m:
            title = m.group(1).strip().strip("\"'").strip()
            if title:
                return title
        content = body

    # 2. Try first Markdown H1
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            # Strip inline HTML / emphasis markers
            title = re.sub(r"</?[^>]+>", "", title)
            title = title.strip("*-_` ")
            if title:
                return title

    # 3. Fallback to filename
    name = path.stem
    if name in ("index", "README"):
        # Use parent directory name
        name = path.parent.name
    return name.replace("-", " ").replace("_", " ")


def url_for(path: Path) -> str | None:
    """Map source file path to site URL."""
    rel = path.relative_to(ROOT)
    parts = list(rel.parts)

    # Skip top-level special pages we don't want in search
    if rel.name in EXCLUDE_FILES and len(parts) == 1:
        return None

    if path.suffix == ".md":
        # Jekyll + jekyll-readme-index behaviour
        if rel.name == "README.md":
            url = "/" + "/".join(parts[:-1])
        elif rel.name == "index.md":
            url = "/" + "/".join(parts[:-1])
        else:
            url = "/" + str(rel.with_suffix(".html"))
    elif path.suffix == ".html":
        if rel.name == "index.html":
            url = "/" + "/".join(parts[:-1])
        else:
            url = "/" + str(rel)
    else:
        return None

    # Ensure trailing slash for directory-like URLs
    if url != "/" and not url.endswith(".html"):
        url += "/"
    return url


def build_index():
    pages = []
    seen_urls = set()

    for ext in ("*.md", "*.html"):
        for p in sorted(ROOT.rglob(ext)):
            rel = p.relative_to(ROOT)

            # Skip excluded directories
            if any(part.startswith(".") or part in EXCLUDE_DIRS for part in rel.parts):
                continue

            url = url_for(p)
            if not url or url in seen_urls:
                continue

            title = extract_title(p)
            if not title:
                continue

            seen_urls.add(url)
            pages.append({"title": title, "url": url})

    # Sort by URL for deterministic output
    pages.sort(key=lambda x: x["url"])

    OUT.write_text(
        json.dumps(pages, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[search-index] Wrote {len(pages)} entries to {OUT}")


if __name__ == "__main__":
    build_index()
