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

## GROBID Setup

This tool requires a running GROBID service (default: `http://localhost:8070`). Choose one option:

### Option A — Docker (recommended)

1) Install and start Docker Desktop

2) Run GROBID:

```
docker run --rm -p 8070:8070 lfoppiano/grobid:latest
```

3) Verify it’s alive:

```
curl http://localhost:8070/api/isalive
```

Keep this terminal running while you use the CLI.

### Option B — Without Docker (Java/Gradle)

1) Install Java 17 and Gradle (macOS examples):

```
brew install openjdk@17 gradle
export JAVA_HOME=$(/usr/libexec/java_home -v 17)
```

2) Clone, build, and run GROBID:

```
git clone https://github.com/kermitt2/grobid.git
cd grobid
./gradlew clean install
./gradlew run
```

3) Verify it’s alive:

```
curl http://localhost:8070/api/isalive
```

Notes:

- The first request may be slower while models load.
- Leave the server running in that terminal; stop with Ctrl+C when done.
- If GROBID runs on a different host/port, pass `--grobid-url` to the CLI.

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
