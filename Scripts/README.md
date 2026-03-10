# Scripts do Projeto

Este diretorio concentra utilitarios de apoio ao projeto.

- `auditar_padrao.py`: auditoria leve de padrao tecnico (skill `modo-carreira-padrao`).
- `Manutencao/`: scripts de manutencao recorrente.
- `Diagnostico/`: scripts temporarios de investigacao/debug.

## Uso rapido

Executar sempre a partir da raiz do projeto:

```bash
python Scripts/auditar_padrao.py --root . --paths Dados/banco.py
python Scripts/Manutencao/baixar_bandeiras.py
python Scripts/Diagnostico/check_db.py
```
