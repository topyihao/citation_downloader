from __future__ import annotations

import re
import unicodedata
from pathlib import Path


def slugify(text: str, max_len: int = 120) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-._")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-._")
    return text or "file"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def detect_arxiv_id(text: str) -> str | None:
    # Modern arXiv IDs: 2101.12345, with optional v2; or legacy: cs/9901001
    m = re.search(r"\b(\d{4}\.\d{4,5})(v\d+)?\b", text)
    if m:
        return m.group(1) + (m.group(2) or "")
    m = re.search(r"\b([a-z\-]+/[0-9]{7})(v\d+)?\b", text, flags=re.IGNORECASE)
    if m:
        return m.group(1) + (m.group(2) or "")
    return None


def extract_urls(text: str) -> list[str]:
    pattern = re.compile(
        r"https?://[\w\-\./?%&=#:+~;,@!$'*()]+",
        flags=re.IGNORECASE,
    )
    urls = pattern.findall(text)
    # De-duplicate, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            out.append(u)
            seen.add(u)
    return out

