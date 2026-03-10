
import json
from pathlib import Path
import sys

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from Logica.aiseason import gerar_aiseason
from Dados.constantes import ARQUIVO_BANCO

with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f: banco = json.load(f)
res = gerar_aiseason(banco, 'mx5', 'MX5 Roster')
if res.get('sucesso'):
    arquivo = res.get('arquivo')
    with open(arquivo, 'r', encoding='utf-8') as f2:
        sd = json.load(f2)
        evs = sd.get('events', [])
        r1 = evs[0].get('results')
        r3 = evs[2].get('results')
        if r1: print('ROUND 1 INJETADO COM DETALHES:', len(r1['session_results'][0]['results']), 'pilotos.')
        else: print('ROUND 1 SEM RESULTADOS')
        if r3: print('ROUND 3 INJETADO COM DETALHES:', len(r3['session_results'][0]['results']), 'pilotos.')
        else: print('ROUND 3 SEM RESULTADOS')

