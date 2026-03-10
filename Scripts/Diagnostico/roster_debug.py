import os
import sys
import json
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
if str(RAIZ_PROJETO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROJETO))

from UI.carreira_acoes_exportar import ExportarImportarMixin
from Logica.export import calculate_pilot_for_export, build_pilot_context, build_race_context, export_pilot_data
from Dados.constantes import ARQUIVO_BANCO

class MockUI(ExportarImportarMixin):
    def __init__(self):
        with open(ARQUIVO_BANCO, 'r', encoding='utf-8') as f:
            self.banco = json.load(f)
        self.categoria_atual = 'mx5'

mock = MockUI()
pista1 = mock.banco.get('calendario', [{}])[0]
race_ctx1 = build_race_context('mx5', pista1.get('id', 0), pista1.get('nome', ''), 3, 10, mock.banco, None)

for idx, p in enumerate(mock.banco['pilotos']):
    if p.get('categoria_atual') != 'mx5': continue
    
    if p['nome'] == 'Margaux Deschamps':
        pilot_ctx = build_pilot_context(p)
        export_data = export_pilot_data(p, pilot_ctx, race_ctx1, '0', {}, 3)
        print(f"--- Margaux Modifier Report ---")
        if export_data.modifier_report:
            print(export_data.modifier_report.get_summary())
        print(f"\nFinal: skill={export_data.skill} agg={export_data.aggression}")
        
    if p['nome'] == 'Ricardo Cardoso':
        pilot_ctx = build_pilot_context(p)
        export_data = export_pilot_data(p, pilot_ctx, race_ctx1, '0', {}, 3)
        print(f"--- Ricardo Modifier Report ---")
        if export_data.modifier_report:
            print(export_data.modifier_report.get_summary())
        print(f"\nFinal: skill={export_data.skill} agg={export_data.aggression}")
