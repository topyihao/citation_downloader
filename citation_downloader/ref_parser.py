from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class Reference:
    raw: str
    index: Optional[int] = None


REF_HEADER_PATTERNS = [
    re.compile(r"\breferences\b", re.IGNORECASE),
    re.compile(r"\bbibliography\b", re.IGNORECASE),
    re.compile(r"\bworks\s+cited\b", re.IGNORECASE),
]

ENTRY_START_PATTERNS = [
    re.compile(r"^\s*\[(\d+)\]\s+"),  # [12]
    re.compile(r"^\s*(\d+)[\.)]\s+"),  # 12. or 12)
]


def find_references_block(full_text: str) -> str:
    """Heuristically locate the references section near the end of the text."""
    # Search last 40% of text for a references header
    n = len(full_text)
    start_search = int(n * 0.6)
    tail = full_text[start_search:]

    idx = -1
    header = None
    for pat in REF_HEADER_PATTERNS:
        m = pat.search(tail)
        if m:
            pos = start_search + m.start()
            if idx == -1 or pos < idx:
                idx = pos
                header = m.group(0)
    if idx == -1:
        # fallback: try whole text
        for pat in REF_HEADER_PATTERNS:
            m = pat.search(full_text)
            if m:
                idx = m.start()
                header = m.group(0)
                break
    if idx == -1:
        # return the last quarter as a last resort
        return full_text[int(n * 0.75) :]

    # Trim header line to the end
    return full_text[idx:]


def _split_numbered_entries(text: str) -> List[Reference]:
    lines = [ln.strip() for ln in text.splitlines()]
    entries: List[List[str]] = []
    current: List[str] = []
    current_idx: Optional[int] = None

    def flush():
        nonlocal current
        if current:
            entries.append(current)
            current = []

    for ln in lines:
        if not ln:
            continue
        matched_idx = None
        for pat in ENTRY_START_PATTERNS:
            m = pat.match(ln)
            if m:
                matched_idx = int(m.group(1))
                ln = ln[m.end() :].strip()
                break
        if matched_idx is not None:
            # New entry
            flush()
            current = [ln]
            current_idx = matched_idx
        else:
            # Continuation of current entry
            if current:
                current.append(ln)
            else:
                # Sometimes entries are not numbered at all
                current = [ln]

    flush()

    refs: List[Reference] = []
    running_idx = 1
    for block in entries:
        raw = " ".join(block)
        # compress repeated spaces
        raw = re.sub(r"\s+", " ", raw).strip()
        refs.append(Reference(raw=raw, index=running_idx))
        running_idx += 1
    return refs


def _split_fallback(text: str) -> List[Reference]:
    # Split on double newlines or semicolon + newline combos
    parts = re.split(r"\n\s*\n+", text)
    out: List[Reference] = []
    idx = 1
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) < 20:
            continue
        out.append(Reference(raw=p, index=idx))
        idx += 1
    return out


def extract_references(full_text: str) -> List[Reference]:
    block = find_references_block(full_text)

    # Remove the header word if present
    block = re.sub(r"^(references|bibliography|works\s+cited)\s*", "", block, flags=re.IGNORECASE)

    refs = _split_numbered_entries(block)
    if len(refs) < 3:
        refs = _split_fallback(block)
    return refs

