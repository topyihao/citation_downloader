from __future__ import annotations

import logging
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_url(url: str, timeout: int = 15) -> requests.Response:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp


def find_pdf_link_in_html(url: str, html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        logger.debug("HTML parse failed: %s", e)
        return None

    # 1) Standard meta used by many publishers
    meta = soup.find("meta", attrs={"name": "citation_pdf_url"})
    if meta and meta.get("content"):
        return requests.compat.urljoin(url, meta["content"].strip())

    # 2) Anchors with .pdf
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().endswith(".pdf"):
            return requests.compat.urljoin(url, href)

    # 3) arXiv-specific: anchors containing /pdf/
    if "arxiv.org" in (url or ""):
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if "/pdf/" in href:
                return requests.compat.urljoin(url, href)

    # 4) link tags
    for link in soup.find_all("link", href=True):
        href = link["href"].strip()
        if href.lower().endswith(".pdf"):
            return requests.compat.urljoin(url, href)

    # 5) Fallback: anchor text mentions PDF
    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").strip().lower()
        if "pdf" in text:
            return requests.compat.urljoin(url, a["href"].strip())

    return None
