import json
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from Dados.constantes import ARQUIVO_BANCO

with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
    banco = json.load(f)
p = banco['pilotos'][0]
print(f"Keys in DB for {p['nome']}:")
for k in ['nome', 'corridas_categoria', 'temporadas_categoria', 'resultados_temporada', 'corridas_temporada', 'corridas_carreira', 'historico_resultados']:
    print(f"{k}: {p.get(k, 'NOT_FOUND')}")
