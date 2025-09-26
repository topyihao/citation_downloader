from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress

from .downloader import attempt_download
from .grobid import grobid_extract_references
from .html_utils import fetch_url, find_pdf_link_in_html
from .reporting import write_report
from .resolver import ResolveConfig, Resolver
from .utils import ensure_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("citation_downloader")


def _fetch_pdf_from_url(url: str, timeout: int = 15) -> Optional[bytes]:
    try:
        resp = fetch_url(url, timeout=timeout)
    except Exception as e:
        logger.error("Failed to fetch URL: %s", e)
        return None
    ct = (resp.headers.get("Content-Type") or "").lower()
    if "application/pdf" in ct or url.lower().endswith(".pdf"):
        return resp.content
    if "text/html" in ct:
        pdf_link = find_pdf_link_in_html(resp.url, resp.text)
        if pdf_link:
            try:
                pdf_resp = fetch_url(pdf_link, timeout=timeout)
                ct2 = (pdf_resp.headers.get("Content-Type") or "").lower()
                if "application/pdf" in ct2:
                    return pdf_resp.content
            except Exception as e:
                logger.error("Failed to fetch PDF from %s: %s", pdf_link, e)
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="citation-downloader",
        description="Extract citations and download cited PDFs from a paper (PDF or URL)",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--pdf", type=Path, help="Path to a local PDF file")
    src.add_argument("--url", type=str, help="URL of a paper (PDF or landing page)")
    p.add_argument("--out", type=Path, default=Path("downloads"), help="Output directory")
    p.add_argument("--max-refs", type=int, default=None, help="Limit number of references processed")
    p.add_argument("--dry-run", action="store_true", help="Only resolve links, do not download")
    p.add_argument("--email", type=str, default=None, help="Contact email to enable Unpaywall API")
    p.add_argument("--timeout", type=int, default=15, help="Network timeout (seconds)")
    p.add_argument("--grobid-url", type=str, default="http://localhost:8070", help="GROBID server URL")
    p.add_argument("--grobid-consolidate", type=int, choices=[0, 1, 2], default=0, help="GROBID consolidateCitations level")
    return p


def run_cli(args: argparse.Namespace) -> int:
    console = Console()
    ensure_dir(args.out)

    local_pdf: Optional[Path] = None
    temp_dir: Optional[tempfile.TemporaryDirectory] = None

    if args.pdf:
        local_pdf = args.pdf
        if not local_pdf.exists():
            console.print(f"[red]PDF not found:[/] {local_pdf}")
            return 2
    else:
        console.print(f"[bold]Fetching URL:[/] {args.url}")
        data = _fetch_pdf_from_url(args.url or "", timeout=args.timeout)
        if not data:
            console.print("[red]Could not locate a PDF at the provided URL")
            return 1
        temp_dir = tempfile.TemporaryDirectory()
        local_pdf = Path(temp_dir.name) / "paper.pdf"
        local_pdf.write_bytes(data)

    console.print(f"[bold]Extracting text from:[/] {local_pdf}")
    refs_raw: list[str] = []
    hints_list: list[dict] = []

    console.print("[bold]Using GROBID for reference extraction[/]")
    grobid_refs = grobid_extract_references(
        local_pdf,
        url=args.grobid_url,
        consolidate_citations=args.grobid_consolidate,
        timeout=max(args.timeout, 30),
    )
    for r in grobid_refs:
        refs_raw.append(r.get("raw") or "")
        hints_list.append({k: r.get(k) for k in ("doi", "arxiv_id", "title", "year") if r.get(k)})

    if not refs_raw:
        console.print("[red]GROBID found no references.")
        return 1

    if args.max_refs is not None:
        refs_raw = refs_raw[: args.max_refs]
        hints_list = hints_list[: args.max_refs]

    console.print(f"[bold]Found references:[/] {len(refs_raw)}")

    import os
    resolver = Resolver(
        ResolveConfig(
            timeout=args.timeout,
            email=args.email,
            s2_api_key=os.environ.get("SEMANTIC_SCHOLAR_API_KEY"),
        )
    )

    report = {
        "input": str(local_pdf if args.pdf else args.url),
        "count": len(refs_raw),
        "engine": "grobid",
        "results": [],
    }

    with Progress() as progress:
        task = progress.add_task("Resolving + downloading", total=len(refs_raw))
        for i, (raw, hints) in enumerate(zip(refs_raw, hints_list), start=1):
            meta = resolver.resolve(raw, hints=hints)
            result = {
                "index": i,
                "reference": raw,
                "meta": meta,
            }
            if not args.dry_run:
                dl = attempt_download(meta, i, args.out, timeout=args.timeout, session=resolver.session)
                result["download"] = dl
            report["results"].append(result)
            progress.advance(task)

    report_path = args.out / "report.json"
    write_report(report_path, report)
    console.print(f"[bold green]Done.[/] Report written to {report_path}")

    if temp_dir is not None:
        temp_dir.cleanup()
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run_cli(args)


if __name__ == "__main__":
    sys.exit(main())
