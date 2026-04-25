# docslice

![CI](https://github.com/cdaalexandre/docslice/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> Extracts text from PDF/EPUB and slices it into &le; 300 KB chunks for LLM indexing.

Python CLI that takes a PDF or EPUB file (tested up to 1,264 pages;
designed for 30k), extracts the text preserving structure (paragraphs,
headings, lists, tables), runs a cleanup pipeline, and splits the result
into `.txt` files of at most 300 KB each, breaking only at paragraph
boundaries. Built to feed RAG pipelines and LLM indexing.

The full documentation is in **Portuguese** at [README.md](README.md);
this page is a brief overview in English.

---

## Quick start

```bash
git clone https://github.com/cdaalexandre/docslice.git
cd docslice
python -m venv .venv
source .venv/bin/activate     # Linux/macOS
# .\.venv\Scripts\activate   # Windows PowerShell

pip install -e ".[dev]"

docslice book.pdf
```

Output in `book_output/`:

```
book_output/
├── book.txt                # cleaned full text
├── txt_parts/              # 1 to N files, each <= 300 KB
└── original_parts/         # only if source > 3 MB
```

---

## Pipeline

```
PDF/EPUB
    -> extract                  pymupdf4llm + fitz fallback | ebooklib + bs4
    -> normalize_text           LF, whitespace, form-feed
    -> remove_page_markers      "42", "Page 5"
    -> remove_picture_markers   pymupdf4llm artifacts
    -> flatten_pseudo_tables    misclassified tables -> prose
    -> write_text               LF on disk (Windows-safe)
    -> compute_split_points     UTF-8 bytes, paragraph boundaries
    -> split_text_file          book_part001.txt ... book_part00N.txt
```

---

## Architecture

Hexagonal (ports & adapters) per Percival & Gregory,
*Architecture Patterns with Python*. Domain is pure logic, adapters own
all I/O, service layer orchestrates, entrypoints parse user input.
Tests use Fakes that structurally satisfy `typing.Protocol` interfaces
(no `unittest.mock`). 41 tests; ~70% in pure domain layer.

---

## Performance

Bates Propedêutica Médica (1,264-page medical PDF, 32.7 MB):
~4 min total, 9 chunks all &le; 300 KB.

Lógica Socrática (6.4 MB EPUB): under 1 second total, 4 chunks all
&le; 300 KB.

---

## Licensing

`docslice` is MIT-licensed (see [LICENSE](LICENSE)). It depends on
PyMuPDF and pymupdf4llm, which are AGPL-3.0. If you redistribute
docslice, AGPL terms apply to the bundled stack. For personal use,
no additional obligations.
