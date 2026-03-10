# Padroes do Projeto Modo Carreira

## Arquitetura alvo

- Manter separacao por camada:
  - `Dados/`: leitura, escrita, schema, migracao e normalizacao de dados.
  - `Logica/`: regras de negocio e orquestracao de simulacao/mercado/promocao.
  - `UI/`: renderizacao PySide6, componentes visuais e handlers de interacao.
  - `Utils/`: funcoes puras de apoio reutilizavel.
- Evitar acoplamento cruzado:
  - Nao mover regra de negocio para `UI/`.
  - Nao importar widget em `Logica/`.

## Convencoes de codigo

- Usar `snake_case` para funcoes, variaveis e nomes de arquivo.
- Usar docstring de modulo em todos os arquivos novos.
- Em modulos novos de `Logica/` e `UI/`, usar:
  - `from __future__ import annotations`
  - type hints em API publica
- Centralizar normalizacoes e conversoes em helpers comuns (`Utils/helpers.py`).
- Evitar duplicar dicionarios de schema entre modulos; manter uma fonte unica.

## Regras por camada

### Dados

- Tratar schema de banco com migracoes idempotentes.
- Preservar retrocompatibilidade com estruturas antigas.
- Salvar com UTF-8 e `ensure_ascii=False` quando JSON precisar manter caracteres.

### Logica

- Priorizar funcoes puras e modelos tipados para regras novas.
- Encapsular orquestracao em `*Manager` quando o fluxo envolver multiplas etapas.
- Evitar efeitos colaterais fora da responsabilidade do modulo.

### UI

- Manter tela focada em composicao visual e despacho de acoes.
- Delegar calculo e decisao para `Logica/`.
- Em refatoracoes, quebrar telas grandes em mixins/componentes para reduzir acoplamento.

### Utils

- Manter funcoes deterministicas e independentes de estado global.
- Evitar dependencia de UI.

## Checklist de revisao

- [ ] Arquivo novo respeita camada correta.
- [ ] Modulo possui docstring.
- [ ] API publica possui type hints quando aplicavel.
- [ ] Nao ha duplicacao de schema/default em mais de um ponto.
- [ ] Testes unitarios da area alterada foram executados.
- [ ] Auditoria `scripts/auditar_padrao.py` foi rodada nos arquivos alterados.

## Hotspots atuais (base observada)

- Arquivos UI muito grandes:
  - `UI/carreira.py` (5588 linhas)
  - `UI/historia.py` (5300 linhas)
  - `UI/fichas.py` (4473 linhas)
- Duplicacao de estrutura de mercado entre:
  - `Dados/banco.py`
  - `Logica/mercado/mercado_manager.py`
- Heterogeneidade entre modulos novos tipados e modulos legados menos tipados.

## Comandos de validacao recomendados

```bash
python scripts/auditar_padrao.py --root . --paths <arquivos_editados>
python test_logica.py
python test_promocao_modulo8.py
```

## Nao fazer

- Nao adicionar novas regras de negocio direto em telas PySide.
- Nao criar novo helper se um helper equivalente ja existe.
- Nao repetir bloco de schema sem justificar e documentar.
