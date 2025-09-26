# Citation Downloader

Extract references from a research paper (PDF or URL), resolve DOIs/links, and download the cited PDFs. Ships with a CLI: `citation-downloader`.

## Features

- Accepts a local PDF (`--pdf`) or a paper URL (`--url`).
- Extracts the References/Bibliography section using GROBID (high accuracy).
- Resolves references to DOIs via Crossref; also leverages OpenAlex and (optionally) Semantic Scholar for missing DOIs; detects arXiv IDs; parses inline URLs.
- Attempts to find and download open-access PDFs (arXiv, publisher links, Crossref links, Unpaywall optional).
- Writes a JSON report mapping each reference to links and download status.

## Install

Requires Python 3.9+.

Using Poetry (recommended):

```
poetry install
```

Or with pip (inside a venv):

```
pip install -e .
```

## Usage

```
citation-downloader --pdf path/to/paper.pdf --out downloads
```

Or provide a URL (arXiv/DOI/publisher page). The tool will try to locate a PDF:

```
citation-downloader --url https://arxiv.org/abs/XXXX.XXXXX --out downloads
```

Options:

- `--pdf PATH` or `--url URL`: Provide exactly one.
- `--out DIR`: Output directory for downloaded PDFs and `report.json` (default: `downloads`).
- `--max-refs N`: Limit number of references processed.
- `--dry-run`: Don’t download, only extract/resolve and print report.
- `--email EMAIL`: Contact email for Unpaywall; enables Unpaywall resolution for OA links.
- `--timeout SEC`: Network timeout per request (default: 15).
- `--grobid-url URL`: GROBID server URL (default: http://localhost:8070).
- `--grobid-consolidate {0,1,2}`: GROBID citation consolidation level.

### Optional integrations

- OpenAlex: used automatically to help fill in missing DOIs.
- Semantic Scholar: used automatically if the environment variable `SEMANTIC_SCHOLAR_API_KEY` is set. Example:

```
export SEMANTIC_SCHOLAR_API_KEY=sk_...
```

## Notes and Limitations

- GROBID must be running. Start with Docker: `docker run --rm -p 8070:8070 lfoppiano/grobid:latest`
- Some publishers block automated downloads or require authentication. The tool prioritizes open-access sources (arXiv, Crossref-provided links, Unpaywall OA URLs).
- Respect site terms; use `--dry-run` to inspect links before downloading.

## Development

Run formatting and linting:

```
ruff check .
```

Run tests:

```
pytest -q
```
