from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from .html_utils import find_pdf_link_in_html
from .utils import ensure_dir, slugify

logger = logging.getLogger(__name__)


def is_pdf_bytes(data: bytes) -> bool:
    return data.startswith(b"%PDF")


def _unique_path(base_dir: Path, basename: str, ext: str = ".pdf") -> Path:
    p = base_dir / f"{basename}{ext}"
    i = 2
    while p.exists():
        p = base_dir / f"{basename}-{i}{ext}"
        i += 1
    return p


def pick_filename(meta: Dict[str, Any], index: int) -> str:
    parts = []
    if meta.get("title"):
        parts.append(meta["title"])  # type: ignore[index]
    elif meta.get("doi"):
        parts.append(meta["doi"])  # type: ignore[index]
    else:
        parts.append(f"ref-{index:03d}")
    name = "-".join(parts)
    return slugify(name)


def download_pdf_from_url(
    url: str, out_dir: Path, basename: str, timeout: int = 15, session: Optional[requests.Session] = None
) -> Optional[Path]:
    sess = session or requests.Session()
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        )
    }
    try:
        r = sess.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
    except Exception as e:
        logger.debug("GET failed for %s: %s", url, e)
        return None

    content_type = (r.headers.get("Content-Type") or "").lower()
    data = r.content
    if "application/pdf" in content_type or is_pdf_bytes(data):
        ensure_dir(out_dir)
        path = _unique_path(out_dir, basename, ".pdf")
        path.write_bytes(data)
        return path

    # If HTML, try to discover a PDF link
    if "text/html" in content_type:
        pdf_link = find_pdf_link_in_html(r.url, r.text)
        if pdf_link:
            return download_pdf_from_url(pdf_link, out_dir, basename, timeout=timeout, session=sess)

    # Not a PDF
    return None


def attempt_download(
    ref_meta: Dict[str, Any], index: int, out_dir: Path, timeout: int = 15, session: Optional[requests.Session] = None
) -> Dict[str, Any]:
    ensure_dir(out_dir)
    basename = pick_filename(ref_meta, index)
    url = ref_meta.get("pdf_url") or ref_meta.get("urls", [None])[0]
    saved: Optional[Path] = None
    tried: list[str] = []

    sess = session or requests.Session()

    if url:
        tried.append(url)
        saved = download_pdf_from_url(url, out_dir, basename, timeout=timeout, session=sess)

    # If not saved and have DOI, try doi.org URL
    if not saved and ref_meta.get("doi"):
        doi_url = f"https://doi.org/{ref_meta['doi']}"
        tried.append(doi_url)
        saved = download_pdf_from_url(doi_url, out_dir, basename, timeout=timeout, session=sess)

    status = "downloaded" if saved else "skipped"
    return {
        "status": status,
        "saved_path": str(saved) if saved else None,
        "tried": tried,
    }

