# Contribuindo

Obrigado pelo interesse em contribuir com `docslice`. Este documento
descreve o workflow e os padrões esperados.

## Setup local

```bash
git clone https://github.com/cdaalexandre/docslice.git
cd docslice
python -m venv .venv
.\.venv\Scripts\activate     # Windows PowerShell
# source .venv/bin/activate    # Linux/macOS

pip install -e ".[dev]"
```

## Os 4 portões de validação

Antes de qualquer commit, todos devem estar verdes:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

CI roda os mesmos 4 portões em Python 3.11, 3.12 e 3.13. PR só é
mergeado com tudo verde.

## Arquitetura

Veja a seção *Arquitetura* do [README.md](README.md). Resumindo:
hexagonal, sem dependências cruzadas (domain não conhece adapters).

- Lógica pura &rarr; `domain/`
- I/O externo &rarr; `adapters/` (sempre via Protocol em
  `adapters/protocols.py`)
- Orquestração &rarr; `service_layer/`
- Interface &rarr; `entrypoints/`

Se sua mudança não cabe nesse mapa, é sinal de que falta um Protocol
ou está no arquivo errado.

## Padrões de código

- `from __future__ import annotations` em todo `.py`.
- Type hints modernos: `str | None`, `list[X]`, `dict[str, Y]`. Nunca
  `Optional`, `List`, `Dict` (PEP 604, RAM Cap. 8).
- Imports apenas no topo do módulo (zero `import X` dentro de função).
- Aspas duplas, line-length &le; 100, encoding UTF-8 sem BOM, line
  endings LF (`.gitattributes` enforça).
- Docstrings estilo Google em funções públicas; module docstring com
  fundamentação (livro + capítulo) quando relevante.
- Em adapters: nunca `print()`, sempre
  `from docslice.log import get_logger`.
- Adapters só conhecem o que está em `protocols.py`. Service layer
  importa Protocol via `if TYPE_CHECKING:`.

## Testes

- pytest, classes `TestXxx` com métodos `test_xxx(self) -> None:`.
- **Fakes**, não Mocks. Fakes implementam o Protocol estruturalmente
  (per RAM Cap. 3, *every call to mock.patch is a ticking time bomb*).
- Pirâmide: muitos unitários de domain (lógica rápida), poucos de
  integração com Fakes em service layer, mínimos E2E.
- Cada feature/fix vem com teste novo.

## Mensagens de commit

Convenção:

```
tipo: assunto curto (<= 72 chars)

Corpo opcional explicando o porque. Linhas <= 72 chars.
Inclua numeros empiricos quando relevante.
```

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

**Atomicidade**: 1 commit = 1 mudança coerente. Se o diff inclui
feature + fix independentes, separe em commits.

## Pull Requests

- Branch a partir de `main`.
- Descreva o problema e a abordagem (o *porquê*, não só o *o quê*).
- Confirme que os 4 portões passam localmente.
- Use o template em
  [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).

## Reportando bugs

Use o template em
[`.github/ISSUE_TEMPLATE/bug_report.md`](.github/ISSUE_TEMPLATE/bug_report.md).
Inclua: SO, versão Python, comando exato, output, e (se possível)
características do PDF/EPUB que reproduz o problema.

## Sugerindo features

Use
[`.github/ISSUE_TEMPLATE/feature_request.md`](.github/ISSUE_TEMPLATE/feature_request.md).
Descreva o **caso de uso real**, não só a feature abstrata.
