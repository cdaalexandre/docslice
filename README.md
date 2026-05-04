# docslice

Extract text from PDF and EPUB files, slice it into LLM-ready chunks,
and (optionally) upload those chunks to Google Drive as native Google
Docs to use as knowledge sources for NotebookLM, Gemini, or Drive
search.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Type checked: mypy strict](https://img.shields.io/badge/mypy-strict-blue)
![Lint: ruff](https://img.shields.io/badge/ruff-checked-261230)

---

## Features

- **PDF and EPUB ingestion** — handles documents up to ~30,000 pages.
- **Structural text preservation** — paragraphs, titles, chapter
  breaks, and real markdown tables survive extraction.
- **Smart chunking** — splits TXT at paragraph boundaries (default
  ~300 KB), and the original binary at any boundary (default ~3 MB).
- **Google Docs export** *(foundation in current release;
  CLI integration in PR-B)* — converts each chunk to a native Google
  Doc via Drive API, ready for NotebookLM and similar tools.
- **Strict-mode Python** — `mypy --strict`, `ruff` lint+format, full
  type hints, hexagonal architecture, no `mock.patch` in tests.

---

## Quick start

```bash
pip install -e .
docslice path/to/my_book.pdf
```

This produces:

```
my_book_output/
├── my_book.txt                # full normalized text
├── txt_parts/                 # TXT split at paragraph boundaries
│   ├── my_book_part001.txt
│   ├── my_book_part002.txt
│   └── ...
└── original_parts/            # only if input > --max-orig-mb
    ├── my_book_part001.pdf
    └── ...
```

---

## Installation

### From source

```bash
git clone https://github.com/cdaalexandre/docslice.git
cd docslice
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

### Requirements

- Python 3.11, 3.12, or 3.13
- Windows, macOS, or Linux

---

## Usage

### Basic

```bash
docslice path/to/document.pdf
docslice path/to/book.epub
```

### CLI options

| Flag                | Default                | Description                                      |
| ------------------- | ---------------------- | ------------------------------------------------ |
| `input`             | *(required)*           | Path to a PDF or EPUB file                       |
| `-o, --output-dir`  | `<input_stem>_output/` | Output directory                                 |
| `--max-txt-kb`      | `300`                  | TXT chunk size in KB                             |
| `--max-orig-mb`     | `3.0`                  | Original binary chunk size in MB                 |
| `-v, --verbose`     | off                    | Detailed log output                              |
| `-q, --quiet`       | off                    | Suppress informational messages                  |

### Examples

```bash
# Custom output directory
docslice book.pdf -o ./extracted/

# Larger TXT chunks (500 KB) for fewer parts
docslice large_book.epub --max-txt-kb 500

# Verbose logging to debug extraction issues
docslice noisy_scan.pdf -v
```

---

## How it works

### Pipeline

```
PDF / EPUB
    │
    ▼
extract  ──►  raw text
    │
    ▼
normalize  ──►  clean text  (paragraphs, no page noise)
    │
    ▼
write TXT  ──►  my_book.txt
    │
    ├──►  split TXT  ──►  txt_parts/  (~300 KB each)
    │
    └──►  split binary  ──►  original_parts/  (~3 MB each)
```

### Text normalization

The TXT output **preserves**:

- Paragraph structure (double newlines)
- Chapter and section headings
- Real markdown tables (with `|---|---|` separators)

And **removes**:

- Repeated whitespace and form-feed noise
- PDF page headers and footers
- `pymupdf4llm` picture markers (e.g. `![image](...)`)
- Pseudo-tables produced by layout misclassification (rows with no
  real header separator)

### File format

- UTF-8 without BOM
- LF line endings (enforced by `.gitattributes`)

---

## Google Docs export

> **Status**: foundation shipped in PR-A (adapter, protocol, OAuth
> helper, unit tests with Fake Drive service). CLI integration —
> `--gdocs`, `--gdocs-credentials`, `--gdocs-folder-id` flags wired
> into the converter — lands in PR-B.

docslice can upload each TXT chunk (and a consolidated full-text
document) to Google Drive as a native Google Doc, suitable as a
knowledge source for NotebookLM, Gemini, or Drive full-text search.

### How it works

- The Drive API automatically converts the uploaded TXT into a native
  Google Doc when the metadata sets
  `mimeType="application/vnd.google-apps.document"`.
- One API call per file — no `documents.batchUpdate` overhead from
  the Docs API.
- Source size limits: ~50 MB / ~1 million characters per Google Doc.
  Default 300 KB TXT chunks fit with wide margin.
- OAuth scope: `drive.file` — access only to files created or opened
  by docslice. Narrower than full Drive access.

### One-time OAuth setup

1. Visit the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (e.g. `docslice`) or pick an existing one.
3. Go to **APIs & Services** → **Library** and enable **Google Drive
   API**.
4. Go to **APIs & Services** → **Credentials** → **Create credentials**
   → **OAuth client ID**.
5. Choose application type **Desktop app**, give it a name, and
   download the resulting JSON.
6. Save the file as `~/.docslice/credentials.json`. On Windows that
   is `C:\Users\<you>\.docslice\credentials.json`.

On the first upload run, a browser window opens for user consent.
After approval, the access token is cached at `~/.docslice/token.json`
and silently refreshed on subsequent runs.

---

## Architecture

docslice follows the **hexagonal (ports-and-adapters)** pattern from
Percival & Gregory's *Architecture Patterns with Python*.

```
src/docslice/
├── adapters/              # I/O boundaries
│   ├── pdf_reader.py        # PyMuPDF / pymupdf4llm
│   ├── epub_reader.py       # ebooklib + BeautifulSoup
│   ├── file_io.py           # write text, split binary
│   ├── gdocs_auth.py        # Google OAuth flow
│   ├── gdocs_writer.py      # Drive upload with auto-conversion
│   └── protocols.py         # Protocol interfaces (TextExtractor,
│                            #   FileSplitter, GDocsWriter)
├── domain/                # Pure logic — no I/O, no APIs
│   ├── splitter.py          # compute paragraph-aware split points
│   └── text_cleanup.py      # normalize, remove noise, flatten tables
├── service_layer/         # Pipeline orchestration
│   └── converter.py         # extract → clean → split → write
├── entrypoints/           # User interface
│   └── cli.py               # argparse + setup_logging
└── log.py                 # get_logger + setup_logging
```

### Layer rules

- `domain/` depends on **nothing else in the project**. Pure
  functions, fully unit-tested.
- `adapters/` isolates external libraries (PyMuPDF, ebooklib,
  Drive API) behind explicit `Protocol` interfaces in
  `protocols.py`. Swapping a library only touches its adapter.
- `service_layer/converter.py` orchestrates the pipeline by
  composing functions from layers below it. Adapters are **injected
  via parameters**, not imported directly inside the function, so
  the service layer is testable with Fakes.
- `entrypoints/cli.py` is the thinnest possible layer — parses
  arguments, calls `convert()`, formats logs.

### Design references

- Percival & Gregory, *Architecture Patterns with Python* —
  hexagonal layout (Cap. 2), service layer (Cap. 4), dependency
  inversion (Cap. 13)
- Ramalho, *Fluent Python* — `Protocol` and structural subtyping
  (Cap. 13), encoding (Cap. 4), modern type hints (Cap. 8 + 15)

### Testing pattern

Tests use **Fakes with `.calls` lists**, never `mock.patch`:

```python
class FakeExtractor:
    def __init__(self, text: str = "...") -> None:
        self.text = text
        self.calls: list[Path] = []

    def __call__(self, path: Path) -> str:
        self.calls.append(path)
        return self.text
```

Quoting Percival & Gregory: *"every call to mock.patch is a ticking
time bomb"* — over-mocking ties tests to implementation details and
breaks on every refactor. Fakes satisfy the same `Protocol` and stay
stable.

---

## Configuration

All settings live in `pyproject.toml` (PEP 621):

| Section                       | Purpose                                       |
| ----------------------------- | --------------------------------------------- |
| `[build-system]`              | `hatchling.build` backend                     |
| `[tool.hatch.build.targets.wheel]` | `packages = ["src/docslice"]` for src-layout |
| `[project]`                   | metadata, Python version, runtime deps        |
| `[project.optional-dependencies]` | `dev` extras (ruff, mypy, pytest)         |
| `[project.scripts]`           | `docslice` console entrypoint                 |
| `[tool.ruff]`                 | lint + format, line-length 100, double quotes |
| `[tool.mypy]`                 | strict mode, `disallow_untyped_defs`          |
| `[[tool.mypy.overrides]]`     | `ignore_missing_imports` for libs without stubs |
| `[tool.pytest.ini_options]`   | `pythonpath = ["src"]`, `testpaths = ["tests"]` |
| `[tool.coverage.*]`           | source paths and report options               |

### Encoding policy

- All source files are UTF-8 without BOM.
- LF line endings, enforced by `.gitattributes` (`* text=auto eol=lf`).
- Every `open()` and `write_text()` call uses `encoding="utf-8"`
  explicitly — no implicit defaults.
- File-writing helper scripts use `path.write_bytes(text.encode("utf-8"))`
  to bypass Windows' silent CRLF translation that
  `Path.write_text()` performs by default.

---

## Development

### Setup

```bash
git clone https://github.com/cdaalexandre/docslice.git
cd docslice
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
source .venv/bin/activate          # macOS/Linux
pip install -e ".[dev]"
```

### Phase C — quality gates

Every commit must pass all four checks:

```bash
ruff check .                       # linting
ruff format --check .              # formatting
mypy src                           # type checking (strict)
pytest                             # unit + integration tests
```

On Windows PowerShell, chain with `;` (not `&&`):

```powershell
ruff check .; ruff format --check .; mypy src; pytest
```

### Adding a new module

Follow the layer rules:

| Concern                | Lives in            |
| ---------------------- | ------------------- |
| Pure logic, no I/O     | `domain/`           |
| External library / API | `adapters/`         |
| Pipeline orchestration | `service_layer/`    |
| User interface         | `entrypoints/`      |

Every new `.py` starts with:

```python
"""Short description (one line).

Fundamentacao: Author, Book, Cap. X.
'Brief relevant quote.'
"""

from __future__ import annotations
```

Use `if TYPE_CHECKING:` for type-only imports (e.g. `pathlib.Path`
when only used in annotations) — `ruff` rules `TC001`/`TC003` will
catch missed cases.

### Logging

Every module gets its logger from the central factory:

```python
from docslice.log import get_logger

logger = get_logger(__name__)
```

`setup_logging()` is called **once** in the entrypoint. Never use
`print()` in source code — only in throwaway helper scripts.

---

## Continuous integration

GitHub Actions runs on every push and pull request:

- **Matrix**: Python 3.11, 3.12, and 3.13 on `ubuntu-latest`
- **Steps**: install editable → `ruff check` → `ruff format --check`
  → `mypy src` → `pytest --cov=src --cov-report=xml`
- **Environment**: `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`
  (PEP 540) so encoding is consistent across platforms

A green CI run is required before merging to `main`.

---

## Project status

| Component                          | Status                                          |
| ---------------------------------- | ----------------------------------------------- |
| PDF and EPUB extraction            | ✅ Stable                                       |
| Text normalization                 | ✅ Stable                                       |
| TXT and binary splitting           | ✅ Stable                                       |
| Google Docs adapter (foundation)   | ✅ PR-A — Protocol, uploader, OAuth, unit tests |
| Google Docs CLI integration        | 🚧 PR-B — `--gdocs` flag, converter wiring     |
| Coverage expansion                 | 🚧 PR-C — integration tests, edge cases        |

---

## Tech stack

| Concern              | Library                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------ |
| PDF extraction       | [PyMuPDF](https://pymupdf.readthedocs.io/) + [pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) |
| EPUB parsing         | [ebooklib](https://github.com/aerkalov/ebooklib) + [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) |
| Google Drive API     | [google-api-python-client](https://github.com/googleapis/google-api-python-client)         |
| OAuth 2.0            | [google-auth-oauthlib](https://github.com/googleapis/google-auth-library-python-oauthlib) |
| Lint and format      | [ruff](https://docs.astral.sh/ruff/)                                                       |
| Type checking        | [mypy](https://mypy.readthedocs.io/) (strict mode)                                         |
| Testing              | [pytest](https://docs.pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/)      |
| Build backend        | [hatchling](https://hatch.pypa.io/latest/)                                                 |

---

## License

MIT
