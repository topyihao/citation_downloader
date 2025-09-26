from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(path: Path) -> str:
    """Extract text from a PDF using PyPDF2 first, then pdfminer as fallback.

    Returns the concatenated text of all pages.
    """
    text_parts: list[str] = []

    # Try PyPDF2
    try:
        from PyPDF2 import PdfReader  # type: ignore

        with open(path, "rb") as f:
            reader = PdfReader(f)
            for page in reader.pages:
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t:
                    text_parts.append(t)
        if text_parts:
            return "\n".join(text_parts)
    except Exception as e:
        logger.debug("PyPDF2 extraction failed: %s", e)

    # Fallback to pdfminer.six
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        t = extract_text(str(path)) or ""
        return t
    except Exception as e:
        logger.warning("pdfminer extraction failed: %s", e)

    return ""

