# docslice

Extract text from PDF/EPUB and slice into ~3 MB chunks for LLM indexing.

## Features

- **PDF extraction** via PyMuPDF (fast, handles large files up to 30k pages)
- **EPUB extraction** via ebooklib + BeautifulSoup
- **Structural preservation**: paragraphs, titles, chapter breaks (no visual noise)
- **Smart splitting**: text sliced at paragraph boundaries (~3 MB chunks)
- **Binary splitting**: original PDF/EPUB also sliced for downstream use

## Install

```bash
pip install -e ".[dev]"
```

## Usage

```bash
# Basic usage (TXT em 300 KB, original em 3 MB)
docslice input.pdf

# Custom output directory
docslice input.epub -o output/

# Chunks de TXT maiores (1 MB) e original em 10 MB
docslice large_book.pdf --max-txt-kb 1000 --max-orig-mb 10

# Verbose output
docslice large_book.pdf -v
```

## Architecture

Hexagonal (ports-and-adapters) following Percival & Gregory,
*Architecture Patterns with Python*.

```
src/docslice/
    adapters/       # I/O: PDF reader, EPUB reader, file operations
    domain/         # Pure logic: text cleanup, split-point calculation
    service_layer/  # Orchestration: convert pipeline
    entrypoints/    # CLI (argparse)
```

## Development

```bash
python -m venv .venv
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest --cov=src
```

## License

MIT
