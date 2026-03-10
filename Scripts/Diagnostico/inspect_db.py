import json
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from Dados.constantes import ARQUIVO_BANCO

with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
    banco = json.load(f)
for idx, pista in enumerate(banco.get('calendario', [])[:5]):
    keys = list(pista.keys())
    print(f"Rodada {idx+1}: {pista.get('nome')} | keys: {keys}")
    if 'resultados' in pista:
        print("TEM RESULTADOS.")
