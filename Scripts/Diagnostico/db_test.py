import json
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from Dados.constantes import ARQUIVO_BANCO

with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
    banco = json.load(f)

print(f'Rodada Atual: {banco.get("rodada_atual")}')
cnt = 0
for p in banco.get('pilotos', []):
    if p.get('categoria_atual') == 'mx5':
        print(f"{p['nome']}: pts={p.get('pontos_temporada',0)} hist={p.get('historico_resultados',[])} dnf={p.get('dnf_ultima_corrida')}")
        cnt += 1
        if cnt >= 3:
            break
