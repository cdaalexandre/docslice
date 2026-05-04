# docslice

Extract text from PDF and EPUB files into clean TXT and Word-compatible
.docx, then slice both into LLM-ready chunks. Drop the .docx files into
Google Drive and they auto-convert to native Google Docs - perfect as
knowledge sources for NotebookLM, Gemini, or Drive search.

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Type checked: mypy strict](https://img.shields.io/badge/mypy-strict-blue)
![Lint: ruff](https://img.shields.io/badge/ruff-checked-261230)

---

## Features

- **PDF and EPUB ingestion** - handles documents up to ~30,000 pages.
- **Structural text preservation** - paragraphs, titles, chapter
  breaks, and real markdown tables survive extraction.
- **Smart chunking** - splits TXT at paragraph boundaries (default
  ~300 KB), and the original binary at any boundary (default ~3 MB).
- **Word-compatible .docx output** - one consolidated document plus
  one .docx per chunk, ready to drop into Drive (auto-converts to
  native Google Docs on upload).
- **No cloud dependencies** - everything runs locally. No OAuth, no
  API keys, no network calls.
- **Strict-mode Python** - `mypy --strict`, `ruff` lint+format, full
  type hints, hexagonal architecture, no `mock.patch` in tests.

---

## Quick start

```bash
pip install -e .
docslice path/to/my_book.pdf
```

Output directory layout:

```
my_book_output/
| my_book.txt                # full normalized text
| my_book.docx               # full text as Word doc (Drive-uploadable)
| txt_parts/                 # TXT split at paragraph boundaries
|   | my_book_part001.txt
|   | my_book_part002.txt
|   | ...
| docx_parts/                # one .docx per TXT chunk
|   | my_book_part001.docx
|   | my_book_part002.docx
|   | ...
| original_parts/            # only if input > --max-orig-mb
|   | my_book_part001.pdf
|   | ...
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

## Sending the output to Google Drive

docslice produces standard Word .docx files. Google Drive recognizes
.docx and converts them to native Google Docs on upload or
double-click - no API or OAuth needed.

Suggested workflow:

1. Run `docslice my_book.pdf`.
2. Open `my_book_output/docx_parts/` (or pick the consolidated
   `my_book.docx` if you prefer one document).
3. Drag the files into Drive, or use the Drive desktop client.
4. Right-click any uploaded `.docx` -> **Open with -> Google Docs**.
   Drive creates the Google Docs version next to the original.
5. Reference the Google Docs as sources in NotebookLM, Gemini, or
   Drive search.

For batch conversion, select the .docx files in Drive, right-click,
and choose **Open with -> Google Docs** on each, or upload with
"Convert uploads" enabled in Drive settings (the Google Docs
versions are created automatically).

---

## How it works

### Pipeline

```
PDF / EPUB
    |
    v
extract  -->  raw text
    |
    v
normalize  -->  clean text  (paragraphs, no page noise)
    |
    v
write TXT  -->  my_book.txt
    |
    v
write DOCX  -->  my_book.docx
    |
    +-->  split TXT  -->  txt_parts/  (~300 KB each)
    |        |
    |        +-->  one .docx per chunk  -->  docx_parts/
    |
    +-->  split binary  -->  original_parts/  (~3 MB each, if > 3 MB)
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

### .docx generation

Each blank-line-separated block in the TXT becomes one Word
paragraph in the .docx via the `python-docx` library. No formatting
is applied (default style only) - the goal is clean text that Drive
will index well.

### File format

- UTF-8 without BOM (TXT)
- LF line endings (enforced by `.gitattributes`)
- Office Open XML (.docx, ZIP-based; Word 2007+ and Google Docs)

---

## Architecture

docslice follows the **hexagonal (ports-and-adapters)** pattern from
Percival & Gregory's *Architecture Patterns with Python*.

```
src/docslice/
| adapters/              # I/O boundaries
|   | pdf_reader.py        # PyMuPDF / pymupdf4llm
|   | epub_reader.py       # ebooklib + BeautifulSoup
|   | file_io.py           # write text, split binary
|   | docx_writer.py       # TXT -> .docx via python-docx
|   | protocols.py         # Protocol interfaces (TextExtractor,
|                          #   FileSplitter, DocxWriter)
| domain/                # Pure logic - no I/O, no APIs
|   | splitter.py          # compute paragraph-aware split points
|   | text_cleanup.py      # normalize, remove noise, flatten tables
| service_layer/         # Pipeline orchestration
|   | converter.py         # extract -> clean -> split -> write
| entrypoints/           # User interface
|   | cli.py               # argparse + setup_logging
| log.py                 # get_logger + setup_logging
```

### Layer rules

- `domain/` depends on **nothing else in the project**. Pure
  functions, fully unit-tested.
- `adapters/` isolates external libraries (PyMuPDF, ebooklib,
  python-docx) behind explicit `Protocol` interfaces in
  `protocols.py`. Swapping a library only touches its adapter.
- `service_layer/converter.py` orchestrates the pipeline by
  composing functions from layers below it. Adapters are **injected
  via parameters**, not imported directly inside the function, so
  the service layer is testable with Fakes.
- `entrypoints/cli.py` is the thinnest possible layer - parses
  arguments, calls `convert()`, formats logs.

### Design references

- Percival & Gregory, *Architecture Patterns with Python* -
  hexagonal layout (Cap. 2), service layer (Cap. 4), dependency
  inversion (Cap. 13)
- Ramalho, *Fluent Python* - `Protocol` and structural subtyping
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
time bomb"* - over-mocking ties tests to implementation details and
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
  explicitly - no implicit defaults.
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

### Phase C - quality gates

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
when only used in annotations) - `ruff` rules `TC001`/`TC003` will
catch missed cases.

### Logging

Every module gets its logger from the central factory:

```python
from docslice.log import get_logger

logger = get_logger(__name__)
```

`setup_logging()` is called **once** in the entrypoint. Never use
`print()` in source code - only in throwaway helper scripts.

---

## Continuous integration

GitHub Actions runs on every push and pull request:

- **Matrix**: Python 3.11, 3.12, and 3.13 on `ubuntu-latest`
- **Steps**: install editable -> `ruff check` -> `ruff format --check`
  -> `mypy src` -> `pytest --cov=src --cov-report=xml`
- **Environment**: `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8`
  (PEP 540) so encoding is consistent across platforms

A green CI run is required before merging to `main`.

---

## Tech stack

| Concern              | Library                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| PDF extraction       | [PyMuPDF](https://pymupdf.readthedocs.io/) + [pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) |
| EPUB parsing         | [ebooklib](https://github.com/aerkalov/ebooklib) + [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) |
| .docx generation     | [python-docx](https://python-docx.readthedocs.io/)                      |
| Lint and format      | [ruff](https://docs.astral.sh/ruff/)                                    |
| Type checking        | [mypy](https://mypy.readthedocs.io/) (strict mode)                      |
| Testing              | [pytest](https://docs.pytest.org/) + [pytest-cov](https://pytest-cov.readthedocs.io/) |
| Build backend        | [hatchling](https://hatch.pypa.io/latest/)                              |

---

## License

MIT
