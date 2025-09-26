from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _text(el: Optional[ET.Element]) -> Optional[str]:
    if el is None:
        return None
    t = (el.text or "").strip()
    return t or None


def _join_authors(bibl: ET.Element) -> Optional[str]:
    # Prefer analytic authors (article level), else monograph authors
    parts: List[str] = []
    for pers in bibl.findall(".//tei:analytic/tei:author/tei:persName", TEI_NS):
        forename = _text(pers.find("tei:forename", TEI_NS))
        surname = _text(pers.find("tei:surname", TEI_NS))
        if surname and forename:
            parts.append(f"{surname}, {forename}")
        elif surname:
            parts.append(surname)
    if not parts:
        for pers in bibl.findall(".//tei:monogr/tei:author/tei:persName", TEI_NS):
            forename = _text(pers.find("tei:forename", TEI_NS))
            surname = _text(pers.find("tei:surname", TEI_NS))
            if surname and forename:
                parts.append(f"{surname}, {forename}")
            elif surname:
                parts.append(surname)
    return ", ".join(parts) if parts else None


def _title(bibl: ET.Element) -> Optional[str]:
    # Prefer article title
    t = _text(bibl.find(".//tei:analytic/tei:title", TEI_NS))
    if t:
        return t
    # Else monograph title (e.g., conference/journal)
    return _text(bibl.find(".//tei:monogr/tei:title", TEI_NS))


def _year(bibl: ET.Element) -> Optional[str]:
    # Look for date @when or @from
    date = bibl.find(".//tei:monogr/tei:imprint/tei:date", TEI_NS)
    if date is not None:
        y = date.get("when") or date.get("from") or date.text
        if y:
            return y[:4]
    return None


def _idno(bibl: ET.Element, id_type: str) -> Optional[str]:
    el = bibl.find(f".//tei:idno[@type='{id_type}']", TEI_NS)
    if el is not None and el.text:
        return el.text.strip()
    return None


def parse_tei_references(tei_xml: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(tei_xml)
    out: List[Dict[str, Any]] = []
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
        title = _title(bibl)
        authors = _join_authors(bibl)
        year = _year(bibl)
        doi = _idno(bibl, "DOI")
        arxiv_id = _idno(bibl, "arXiv")
        parts = []
        if authors:
            parts.append(authors)
        if year:
            parts.append(f"({year})")
        if title:
            parts.append(title)
        raw = " ".join(parts) if parts else (title or doi or arxiv_id or "")
        out.append({
            "raw": raw,
            "title": title,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "year": year,
        })
    return out


def grobid_process_fulltext(
    pdf_path: Path,
    *,
    url: str = "http://localhost:8070",
    consolidate_citations: int = 0,
    timeout: int = 60,
) -> Optional[str]:
    endpoint = url.rstrip("/") + "/api/processFulltextDocument"
    files = {"input": (pdf_path.name, open(pdf_path, "rb"), "application/pdf")}
    data = {"consolidateCitations": str(consolidate_citations)}
    try:
        r = requests.post(endpoint, files=files, data=data, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.error("GROBID request failed: %s", e)
        return None


def grobid_extract_references(
    pdf_path: Path,
    *,
    url: str = "http://localhost:8070",
    consolidate_citations: int = 0,
    timeout: int = 60,
) -> List[Dict[str, Any]]:
    tei = grobid_process_fulltext(pdf_path, url=url, consolidate_citations=consolidate_citations, timeout=timeout)
    if not tei:
        return []
    try:
        return parse_tei_references(tei)
    except Exception as e:
        logger.error("Failed to parse TEI: %s", e)
        return []
