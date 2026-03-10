---
name: modo-carreira-padrao
description: Padronizar alteracoes no projeto "Modo Carreira" (Python + PySide6), mantendo arquitetura em camadas (Dados/Logica/UI/Utils), convencoes de nomeacao, migracoes seguras de schema JSON e cobertura de testes. Usar ao criar, editar, refatorar ou revisar codigo deste projeto, especialmente em modulos de logica de negocio, persistencia, UI e integracao de mercado/promocao.
---

# Modo Carreira Padrao

Aplicar um fluxo objetivo para manter consistencia tecnica entre modulos legados e modulos novos.

## Fluxo obrigatorio

1. Classificar a alteracao por camada antes de editar.
2. Ler `references/padroes-projeto.md` e selecionar apenas as secoes relevantes.
3. Implementar seguindo as regras da camada e reutilizar helpers/modelos existentes.
4. Auditar com `python Scripts/auditar_padrao.py --root <repo> --paths <arquivos_editados>`.
5. Executar testes focados do modulo alterado.
6. Entregar com resumo de conformidade (o que seguiu padrao, o que ficou como debito tecnico).

## Regras de implementacao

- Preservar fronteiras:
  - `Dados/`: persistencia, schema, migracao.
  - `Logica/`: regras de negocio, sem dependencia de widget.
  - `UI/`: renderizacao e eventos, sem regra de negocio pesada.
  - `Utils/`: funcoes puras e reutilizaveis.
- Preferir `snake_case` em nomes de arquivos, funcoes e variaveis.
- Incluir docstring de modulo e docstring curta em funcoes nao triviais.
- Em modulos novos de `Logica/` e `UI/`, usar `from __future__ import annotations` e type hints.
- Reutilizar conversoes centralizadas (`Utils/helpers.py`) em vez de criar variantes locais.
- Evitar duplicar schema default em multiplos pontos; extrair para funcao unica quando possivel.

## Validacao minima antes de concluir

1. Rodar auditoria:
```bash
python Scripts/auditar_padrao.py --root <repo> --paths <arquivos_editados>
```
2. Rodar testes unitarios relacionados:
```bash
python Tests/test_logica.py
python Tests/test_promocao_modulo8.py
```
3. Se houver mudanca em schema (`Dados/banco.py`), validar migracao com casos legados.

## Recursos

- Regras detalhadas e hotspots: `references/padroes-projeto.md`
- Auditoria automatica de padrao: `Scripts/auditar_padrao.py`
