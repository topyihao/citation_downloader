from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from .utils import detect_arxiv_id, extract_urls

logger = logging.getLogger(__name__)


DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)


@dataclass
class ResolveConfig:
    timeout: int = 15
    email: Optional[str] = None  # for Unpaywall


def normalize_doi(doi: str | None) -> Optional[str]:
    if not doi:
        return None
    doi = doi.strip()
    # Strip URL prefix if present
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = doi.strip()
    return doi


def extract_doi(text: str) -> Optional[str]:
    m = DOI_RE.search(text)
    if m:
        return normalize_doi(m.group(0))
    return None


class Resolver:
    def __init__(self, config: ResolveConfig):
        self.cfg = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "citation-downloader/0.1 (+https://example.com; bot)"
                )
            }
        )

    def crossref(self, query: str) -> Optional[Dict[str, Any]]:
        url = "https://api.crossref.org/works"
        params = {"query": query, "rows": 1}
        try:
            r = self.session.get(url, params=params, timeout=self.cfg.timeout)
            r.raise_for_status()
            data = r.json()
            items = data.get("message", {}).get("items", [])
            if items:
                return items[0]
        except Exception as e:
            logger.debug("Crossref query failed: %s", e)
        return None

    def unpaywall(self, doi: str) -> Optional[Dict[str, Any]]:
        if not self.cfg.email:
            return None
        url = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": self.cfg.email}
        try:
            r = self.session.get(url, params=params, timeout=self.cfg.timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.debug("Unpaywall failed: %s", e)
            return None

    def resolve(self, ref_text: str, hints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        hints = hints or {}
        urls = extract_urls(ref_text)
        arxiv_id = hints.get("arxiv_id") or detect_arxiv_id(ref_text)
        doi = normalize_doi(hints.get("doi") or extract_doi(ref_text))
        title: Optional[str] = hints.get("title")
        pdf_url: Optional[str] = None
        sources: List[str] = []

        # If no DOI present, try Crossref search
        cr = None
        if not doi:
            # Prefer searching by explicit title if provided
            query = title or ref_text
            cr = self.crossref(query)
            if cr:
                doi = normalize_doi(cr.get("DOI"))
                title_list = cr.get("title") or []
                title = title_list[0] if title_list else None
                # Crossref may include links
                links = cr.get("link") or []
                for l in links:
                    if l.get("content-type") == "application/pdf" and l.get("URL"):
                        pdf_url = l["URL"]
                        break
                if pdf_url:
                    sources.append("crossref")

        else:
            sources.append("inline-doi")

        # If we have a DOI but no PDF link yet, try Unpaywall
        if doi and not pdf_url:
            up = self.unpaywall(doi)
            if up:
                # Prefer oa_location pdf_url, else best_oa_location
                loc = up.get("oa_location") or up.get("best_oa_location")
                if loc and loc.get("url_for_pdf"):
                    pdf_url = loc["url_for_pdf"]
                    sources.append("unpaywall")

        # arXiv direct PDF
        if not pdf_url and arxiv_id:
            pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            sources.append("arxiv")

        # If still nothing, but there are inline URLs, take the first .pdf or first URL
        if not pdf_url:
            for u in urls:
                if u.lower().endswith(".pdf"):
                    pdf_url = u
                    sources.append("inline-url")
                    break
            if not pdf_url and urls:
                pdf_url = urls[0]
                sources.append("inline-url")

        return {
            "title": title,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "urls": urls,
            "pdf_url": pdf_url,
            "sources": sources,
        }
