import sys, json, os
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from UI.carreira_acoes_exportar import ExportarImportarMixin
from Logica.export import calculate_pilot_for_export, build_pilot_context, build_race_context
from Dados.constantes import ARQUIVO_BANCO

# Mock class to call the function
class MockUI(ExportarImportarMixin):
    def __init__(self):
        with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
            self.banco = json.load(f)
        self.categoria_atual = 'mx5'
        
mock = MockUI()
pista = mock.banco.get('calendario', [{}])[0]
race_ctx = build_race_context('mx5', pista.get('id', 0), pista.get('nome', ''), 3, 10, mock.banco, None)

res_list = []
for idx, p in enumerate(mock.banco['pilotos'][:3]):
    if p.get('categoria_atual') != 'mx5': continue
    carro_config = {'carPath': '...', 'carId': 1, 'carClassId': 1}
    res = mock._criar_driver_iracing(p, idx, carro_config, {}, race_ctx)
    res_list.append(res)

for d in res_list:
    print(f"{d['driverName']}: skill={d['driverSkill']} agg={d['driverAggression']} opt={d['driverOptimism']} smooth={d['driverSmoothness']}")
