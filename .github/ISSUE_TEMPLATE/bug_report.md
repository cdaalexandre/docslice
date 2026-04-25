---
name: Bug report
about: Reportar um problema com docslice
title: '[BUG] '
labels: bug
---

## Descrição

O que aconteceu? O que era esperado?

## Reprodução

1. ...
2. ...
3. ...

## Comando exato

```bash
docslice ...
```

## Output

Cole o erro/log relevante (use ` ``` ` para preservar formatação):

```
...
```

## Ambiente

- SO: Windows 11 / Ubuntu 22.04 / macOS 14 / ...
- Python: (output de `python --version`)
- docslice: (output de `pip show docslice` &mdash; campo Version)

## Arquivo de entrada

- Tipo: PDF / EPUB
- Tamanho: ___ MB
- Páginas (se PDF): ___
- Características relevantes (figura-pesado, scaneado, multi-coluna, etc.)

## Já tentou?

- [ ] Reinstalar com `pip install -e ".[dev]"`
- [ ] Verificar que os 4 portões passam:
      `ruff check . ; ruff format --check . ; mypy src ; pytest`
