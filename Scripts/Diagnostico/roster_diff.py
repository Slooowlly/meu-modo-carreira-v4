import sys, json, os
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from UI.carreira_acoes_exportar import ExportarImportarMixin
from Logica.export import calculate_pilot_for_export, build_pilot_context, build_race_context
from Dados.constantes import ARQUIVO_BANCO

class MockUI(ExportarImportarMixin):
    def __init__(self):
        with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
            self.banco = json.load(f)
        self.categoria_atual = 'mx5'
        
mock = MockUI()
pista = mock.banco.get('calendario', [{}])[0]
race_ctx = build_race_context('mx5', pista.get('id', 0), pista.get('nome', ''), 3, 10, mock.banco, None)

for idx, p in enumerate(mock.banco['pilotos'][:3]):
    if p.get('categoria_atual') != 'mx5': continue
    res = mock._criar_driver_iracing(p, idx, {'carPath': '', 'carId': 1, 'carClassId': 1}, {}, race_ctx)
    print(f"{res['driverName']}:")
    print(f"  BASE    -> sk={p.get('skill')} ag={p.get('agressividade', p.get('aggression'))} op={p.get('otimismo', p.get('optimism'))} sm={p.get('suavidade', p.get('smoothness'))}")
    print(f"  EXPORT  -> sk={res['driverSkill']} ag={res['driverAggression']} op={res['driverOptimism']} sm={res['driverSmoothness']}")
