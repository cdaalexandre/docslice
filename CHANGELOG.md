# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-25

### Added

- Hexagonal architecture: adapters (PDF/EPUB readers, file I/O), domain
  (text cleanup, splitter), service layer (converter), entrypoints (CLI).
- PDF extraction via `pymupdf4llm.to_markdown` (markdown-flavoured output
  preserving headings, lists, tables) with three production tunings:
  `use_ocr=False` (skip Tesseract; image-only pages return empty),
  `ignore_images=True` (no PNG side-files), `show_progress=True`.
- Automatic fallback to plain `fitz` extraction on any pymupdf4llm
  exception. `FileNotFoundError` is raised before the try/except so
  input bugs are never hidden by the fallback.
- EPUB extraction via `ebooklib` + `BeautifulSoup`.
- Domain text cleanup pipeline (4 pure functions):
    - `normalize_text`: line endings, whitespace, form-feed characters.
    - `remove_page_markers`: standalone numbers, "Page N" patterns.
    - `remove_picture_markers`: pymupdf4llm picture-omitted markers and
      Start/End wrappers (kept inner caption text).
    - `flatten_pseudo_tables`: pymupdf-layout misclassified prose-as-tables
      converted back to prose; real markdown tables (with `|---|`
      separator) are preserved untouched.
- Split pipeline: text sliced at paragraph boundaries (`\n\n`), each
  chunk &le; 300 KB. Original PDF/EPUB also sliced into &le; 3 MB binary
  parts when source exceeds 3 MB.
- LF-on-disk invariant: `write_text` uses `write_bytes(text.encode("utf-8"))`
  to bypass Windows `Path.write_text` CRLF translation, ensuring
  `compute_split_points` (in-memory UTF-8 LF) and `split_text_file`
  (on-disk bytes) operate on identical byte sequences.
- CI matrix: Python 3.11, 3.12, 3.13 on `ubuntu-latest`.
- Validation gates: `ruff check`, `ruff format --check`, `mypy --strict`,
  `pytest`.
- 41 unit tests; ~70% of test mass in pure domain layer.

### Validated empirically

- Bates Propedêutica Médica (1,264 pages, 32.7 MB PDF): 9 txt chunks,
  all &le; 300 KB, 69 pseudo-tables flattened to prose, 170 real
  markdown tables preserved.
- Lógica Socrática (6.4 MB EPUB): 4 txt chunks, all &le; 300 KB.
