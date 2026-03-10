# Meu Modo Carreira V4

Aplicacao desktop em Python + PySide6 para simular uma carreira de piloto, com foco em temporadas, evolucao de equipe, mercado de transferencias e regras de promocao entre categorias.

## O que o projeto cobre

- Criacao e continuidade de carreira com persistencia em JSON.
- Simulacao de corrida, classificacao, incidentes, safety car e clima.
- Mercado de pilotos com contratos, propostas, clausulas e janela de transferencias.
- Regras de promocao, convites e historico de desempenho por equipe.
- Exportacao de dados para integracao com roster e ajustes de atributos.

## Estrutura do repositorio

- `Dados/`: persistencia, schema, migracoes e configuracoes.
- `Logica/`: regras de negocio (simulacao, mercado, promocao, hierarquia e afins).
- `UI/`: telas, componentes e acoes da interface (PySide6).
- `Utils/`: funcoes auxiliares reutilizaveis.
- `Projeto/`: entrada principal e arquivos de dados locais.
- `Scripts/`: utilitarios de diagnostico, manutencao e auditoria de padrao.
- `Tests/`: testes unitarios e de comportamento.

## Requisitos

- Python 3.10+
- PySide6

## Setup rapido (Windows / PowerShell)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install PySide6
```

## Como executar

Comando principal:

```bash
python main.py
```

Comando alternativo:

```bash
python Projeto/main.py
```

## Como rodar testes

```bash
python Tests/test_logica.py
python Tests/test_promocao_modulo8.py
```

## Auditoria de padrao

Exemplo de uso do auditor local:

```bash
python Scripts/auditar_padrao.py --root . --paths Logica/mercado/mercado_manager.py
```

## Arquivos de dados importantes

- `Projeto/banco_de_dados_pilotos.json`: estado salvo da carreira.
- `Projeto/config.json`: configuracao local da aplicacao.
- `Dados/config.json`: configuracoes da camada de dados.

## Status

Projeto em evolucao continua.
