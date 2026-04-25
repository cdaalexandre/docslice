# docslice

![CI](https://github.com/cdaalexandre/docslice/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Lint: ruff](https://img.shields.io/badge/lint-ruff-261230)
![Type check: mypy strict](https://img.shields.io/badge/mypy-strict-1f5082)

> Extrai texto de PDF/EPUB e fatia em chunks &le; 300 KB para indexação por LLM.
>
> _Extracts text from PDF/EPUB and slices it into &le; 300 KB chunks for LLM indexing._
> [English summary &rarr;](README.en.md)

CLI Python que recebe um arquivo PDF ou EPUB (testado em livros de até 1.300
páginas; design suporta 30 mil), extrai o texto preservando estrutura
(parágrafos, títulos, listas, tabelas), limpa ruídos de extração e fatia
o resultado em arquivos `.txt` de no máximo 300 KB cada, cortando apenas
em fronteiras de parágrafo. Pensado para alimentar pipelines de RAG e
indexação por LLM.

---

## Recursos

- **PDF** via [pymupdf4llm](https://pypi.org/project/pymupdf4llm/) (saída em
  Markdown, com headings/listas/tabelas preservados); fallback automático
  para `fitz` puro em qualquer falha.
- **EPUB** via `ebooklib` + `BeautifulSoup`.
- **Pipeline de cleanup** em camada de domínio: normalização de
  whitespace, remoção de numeração de página, remoção de marcadores de
  figura do `pymupdf4llm`, conversão de pseudo-tabelas (prose mal
  classificada) de volta em prose.
- **Split garantido em &le; 300 KB**: cortes apenas em fronteiras de
  parágrafo (`\n\n`); validado empiricamente em arquivos reais.
- **Split do binário original** em pedaços de &le; 3 MB para uso
  downstream (upload para serviços com limite de tamanho).
- **41 testes**; ~70% em camada de domínio (lógica pura, sem I/O).

---

## Quickstart

```bash
git clone https://github.com/cdaalexandre/docslice.git
cd docslice
python -m venv .venv
.\.venv\Scripts\activate     # Windows PowerShell
# source .venv/bin/activate    # Unix

pip install -e ".[dev]"

docslice livro.pdf
```

Resultado em `livro_output/`:

```
livro_output/
├── livro.txt                    # texto completo, limpo
├── txt_parts/
│   ├── livro_part001.txt        # cada um <= 300 KB
│   ├── livro_part002.txt
│   └── ...
└── original_parts/              # apenas se PDF/EPUB > 3 MB
    ├── livro_part001.pdf
    └── ...
```

### Flags úteis

```bash
docslice livro.pdf -o saida/             # diretório de output customizado
docslice livro.pdf --max-txt-kb 500      # chunks de TXT maiores
docslice livro.pdf --max-orig-mb 10      # chunks de original maiores
docslice livro.pdf -v                    # log detalhado
docslice livro.pdf -q                    # silencioso
```

---

## Como funciona

```
PDF/EPUB
    |
    v
[extract]                pymupdf4llm + fallback fitz   |   ebooklib + BeautifulSoup
    |
    v
[normalize_text]         LF, whitespace, form-feed
    |
    v
[remove_page_markers]    "42", "Page 5", numeros isolados
    |
    v
[remove_picture_markers] "==> picture omitted <==" do pymupdf4llm
    |
    v
[flatten_pseudo_tables]  pseudo-tabelas (sem |---|) viram prose
    |
    v
[write_text]             LF garantido on-disk (sem traducao CRLF do Windows)
    |
    v
[compute_split_points]   bytes UTF-8, fronteiras de paragrafo
    |
    v
[split_text_file]        livro_part001.txt ... livro_part00N.txt  (cada <= 300 KB)
```

---

## Performance

Números reais de validação empírica:

**PDF — Bates Propedêutica Médica (1.264 páginas, 32.7 MB):**

| Etapa | Tempo | Output |
|---|---|---|
| Extração (pymupdf4llm) | ~4 min | 2.6 MB markdown |
| Pipeline de cleanup | <1 s | 2.6 MB texto limpo |
| Split em chunks de 300 KB | <1 s | 9 arquivos `.txt` |

**EPUB — Lógica Socrática (6.4 MB):**

| Etapa | Tempo | Output |
|---|---|---|
| Extração (ebooklib) | <1 s | 1.0 MB texto |
| Split | <1 s | 4 arquivos `.txt` |

A extração de PDF figura-pesado é o gargalo (`pymupdf-layout` faz análise
AI de layout em cada página). Para livros típicos de 200&ndash;500 páginas:
30&ndash;90 segundos no total.

---

## Arquitetura

Hexagonal (ports & adapters), seguindo Percival & Gregory,
*Architecture Patterns with Python*.

```
src/docslice/
├── adapters/                     I/O - fronteira externa
│   ├── protocols.py              <- typing.Protocol (TextExtractor, FileSplitter)
│   ├── pdf_reader.py             <- pymupdf4llm com fallback fitz
│   ├── epub_reader.py            <- ebooklib + BeautifulSoup
│   └── file_io.py                <- write_text (LF), split_text_file, split_binary_file
├── domain/                       Logica pura - sem I/O
│   ├── text_cleanup.py           <- 4 funcoes de limpeza
│   └── splitter.py               <- compute_split_points em fronteiras de paragrafo
├── service_layer/                Orquestracao
│   └── converter.py              <- pipeline convert()
└── entrypoints/                  Interface
    └── cli.py                    <- argparse
```

Domain não importa adapters nem service. Adapters dependem dos protocols.
Service orquestra. Testes injetam **Fakes** que satisfazem o Protocol —
sem `unittest.mock`. Pirâmide: muitos testes em domain (lógica rápida),
poucos em service layer, mínimos de integração (per *RAM Cap. 5*).

---

## Limitações conhecidas

Honestidade sobre o que não é perfeito:

- **Páginas só-imagem** (capas escaneadas, manuscritos digitalizados, fotos
  clínicas) retornam string vazia. Por design — OCR foi desativado para
  evitar lentidão de aproximadamente 1.000× em livros figura-pesados (a
  doc do `pymupdf4llm` confirma esse fator). Se você precisa OCR, troque
  `use_ocr=False` para `True` em
  `src/docslice/adapters/pdf_reader.py:_extract_via_pymupdf4llm`.
- **Tabelas markdown reais** com células multilinha colapsadas via `<br>`
  permanecem assim — LLM downstream lê o conteúdo OK, e o split preserva
  cada tabela inteira. Pseudo-tabelas (prose mal classificada) são
  detectadas pela presença de `|` sem `|---|` separator e convertidas em
  prose pelo `flatten_pseudo_tables`.
- **Parágrafo único maior que 300 KB** é mantido inteiro (não cortado
  pelo meio). Raríssimo em texto natural.

---

## Licenciamento

`docslice` é distribuído sob **MIT** (veja [LICENSE](LICENSE)).

**Mas atenção**: o projeto depende de [PyMuPDF](https://pymupdf.readthedocs.io/)
e [pymupdf4llm](https://pypi.org/project/pymupdf4llm/), ambos sob
**AGPL-3.0**. Se você redistribuir docslice (público, comercial,
embutido em produto), os termos AGPL se aplicam ao stack inteiro. Para
**uso pessoal**, sem obrigações adicionais. Se isso for problema na sua
situação, alternativas:

- Trocar `pymupdf4llm` por
  [`pypdfium2`](https://pypi.org/project/pypdfium2/) (Apache-2.0). Perde
  o markdown estruturado mas resolve o licenciamento.
- Adquirir licença comercial da Artifex para PyMuPDF.

---

## Desenvolvimento

```bash
pip install -e ".[dev]"

# 4 portoes de validacao - sempre verde antes de commit:
ruff check .
ruff format --check .
mypy src
pytest
```

CI roda os mesmos 4 portões em Python 3.11, 3.12 e 3.13. Veja
[CONTRIBUTING.md](CONTRIBUTING.md) para o workflow completo.

---

## Histórico de versões

Veja [CHANGELOG.md](CHANGELOG.md).

---

## Licença

MIT — veja [LICENSE](LICENSE). © 2026 cdaalexandre.
