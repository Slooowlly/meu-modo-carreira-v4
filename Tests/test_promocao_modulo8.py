import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Dados.banco import _validar_campos_banco, criar_banco_vazio
from Logica.mercado.models import (
    Clausula,
    Contrato,
    PapelEquipe,
    StatusContrato,
    TipoClausula,
)
from Logica.promocao import (
    HistoricoEquipe,
    MotivoMovimentacao,
    PromocaoManager,
    ResultadoTemporada,
    TipoMovimentacao,
)
from Logica.promocao.avaliacao import (
    avaliar_elegibilidade_convite,
    avaliar_elegibilidade_promocao,
    avaliar_equipe,
)


def _team(
    team_id: str,
    name: str,
    category: str,
    budget: float = 80.0,
    classe_endurance: str | None = None,
    carro_classe: str | None = None,
) -> dict:
    equipe = {
        "id": team_id,
        "nome": name,
        "categoria": category,
        "budget": budget,
        "car_performance": 60.0,
        "facilities": 50.0,
        "engineering_quality": 50.0,
        "morale": 1.0,
        "reputacao": 50.0,
        "pontos_temporada": 0,
        "vitorias_temporada": 0,
        "podios_temporada": 0,
        "poles_temporada": 0,
        "pilotos": [],
    }
    if classe_endurance:
        equipe["classe_endurance"] = classe_endurance
    if carro_classe:
        equipe["carro_classe"] = carro_classe
    return equipe


class TestPromocaoModulo8(unittest.TestCase):
    def test_promocao_bloqueada_por_budget(self):
        equipe = _team("e1", "Mazda One", "mazda_rookie", budget=10.0)
        resultado = ResultadoTemporada(
            equipe_id="e1",
            equipe_nome="Mazda One",
            categoria_id="mazda_rookie",
            categoria_tier=1,
            temporada=2026,
            posicao_construtores=1,
            pontos_construtores=120,
            total_equipes=10,
        )

        elegivel, motivo, bloqueado = avaliar_elegibilidade_promocao(resultado, budget_equipe=10.0)
        self.assertTrue(elegivel)
        self.assertEqual(motivo, MotivoMovimentacao.CAMPEAO_CONSTRUTORES)
        self.assertTrue(bloqueado)

        avaliacao = avaliar_equipe(equipe, resultado)
        self.assertEqual(avaliacao.tipo_movimentacao, TipoMovimentacao.PERMANENCIA)
        self.assertEqual(avaliacao.motivo, MotivoMovimentacao.BUDGET_INSUFICIENTE)

    def test_convite_top3_consecutivo(self):
        resultado_atual = ResultadoTemporada(
            equipe_id="e2",
            equipe_nome="Toyota Prime",
            categoria_id="mazda_rookie",
            categoria_tier=1,
            temporada=2026,
            posicao_construtores=3,
            pontos_construtores=88,
            total_equipes=10,
        )
        historico = HistoricoEquipe(equipe_id="e2")
        historico.adicionar_resultado(
            ResultadoTemporada(
                equipe_id="e2",
                equipe_nome="Toyota Prime",
                categoria_id="mazda_rookie",
                categoria_tier=1,
                temporada=2025,
                posicao_construtores=3,
                pontos_construtores=80,
                total_equipes=10,
            )
        )
        historico.adicionar_resultado(resultado_atual)

        elegivel, tem_budget = avaliar_elegibilidade_convite(
            resultado_atual,
            budget_equipe=40.0,
            historico=historico,
        )
        self.assertTrue(elegivel)
        self.assertTrue(tem_budget)

    def test_gt3_gt4_sem_rebaixamento_local(self):
        equipe_gt3 = _team("g3", "GT3 Last", "gt3", budget=90.0)
        resultado_gt3 = ResultadoTemporada(
            equipe_id="g3",
            equipe_nome="GT3 Last",
            categoria_id="gt3",
            categoria_tier=5,
            temporada=2026,
            posicao_construtores=10,
            pontos_construtores=1,
            total_equipes=10,
        )
        avaliacao_gt3 = avaliar_equipe(equipe_gt3, resultado_gt3)
        self.assertNotEqual(avaliacao_gt3.tipo_movimentacao, TipoMovimentacao.REBAIXAMENTO)

        equipe_gt4 = _team("g4", "GT4 Last", "gt4", budget=80.0)
        resultado_gt4 = ResultadoTemporada(
            equipe_id="g4",
            equipe_nome="GT4 Last",
            categoria_id="gt4",
            categoria_tier=4,
            temporada=2026,
            posicao_construtores=8,
            pontos_construtores=2,
            total_equipes=8,
        )
        avaliacao_gt4 = avaliar_equipe(equipe_gt4, resultado_gt4)
        self.assertNotEqual(avaliacao_gt4.tipo_movimentacao, TipoMovimentacao.REBAIXAMENTO)

    def test_endurance_vagas_por_classe(self):
        manager = PromocaoManager()

        gt3_a = _team("gt3a", "GT3 A", "gt3", budget=95.0)
        gt3_b = _team("gt3b", "GT3 B", "gt3", budget=70.0)
        gt4_a = _team("gt4a", "GT4 A", "gt4", budget=85.0)
        gt4_b = _team("gt4b", "GT4 B", "gt4", budget=60.0)

        e_gt3_1 = _team("e_gt31", "End GT3 1", "endurance", budget=90.0, classe_endurance="gt3")
        e_gt3_2 = _team("e_gt32", "End GT3 2", "endurance", budget=90.0, classe_endurance="gt3")
        e_gt4_1 = _team("e_gt41", "End GT4 1", "endurance", budget=90.0, classe_endurance="gt4")
        e_gt4_2 = _team("e_gt42", "End GT4 2", "endurance", budget=90.0, classe_endurance="gt4")
        e_lmp2 = _team("e_lmp2", "End LMP2", "endurance", budget=90.0, classe_endurance="lmp2")

        # GT3 standings
        manager.registrar_resultado(gt3_a, posicao=1, pontos=100, total_equipes=2, temporada=1)
        manager.registrar_resultado(gt3_b, posicao=2, pontos=60, total_equipes=2, temporada=1)

        # GT4 standings
        manager.registrar_resultado(gt4_a, posicao=1, pontos=90, total_equipes=2, temporada=1)
        manager.registrar_resultado(gt4_b, posicao=2, pontos=40, total_equipes=2, temporada=1)

        # Endurance overall standings
        manager.registrar_resultado(e_gt3_1, posicao=1, pontos=210, total_equipes=5, temporada=1)
        manager.registrar_resultado(e_gt4_1, posicao=2, pontos=160, total_equipes=5, temporada=1)
        manager.registrar_resultado(e_lmp2, posicao=3, pontos=150, total_equipes=5, temporada=1)
        manager.registrar_resultado(e_gt3_2, posicao=4, pontos=8, total_equipes=5, temporada=1)
        manager.registrar_resultado(e_gt4_2, posicao=5, pontos=7, total_equipes=5, temporada=1)

        relatorio = manager.processar_fim_temporada(
            equipes_por_categoria={
                "gt3": [gt3_a, gt3_b],
                "gt4": [gt4_a, gt4_b],
                "endurance": [e_gt3_1, e_gt3_2, e_gt4_1, e_gt4_2, e_lmp2],
            },
            temporada=1,
            aplicar_automaticamente=False,
        )

        promocoes = {mov.equipe_id: mov for mov in relatorio.promocoes}
        rebaixamentos = {mov.equipe_id: mov for mov in relatorio.rebaixamentos}

        self.assertIn("gt3a", promocoes)
        self.assertEqual(promocoes["gt3a"].categoria_destino_id, "endurance")
        self.assertIn("gt4a", promocoes)
        self.assertEqual(promocoes["gt4a"].categoria_destino_id, "endurance")

        self.assertIn("e_gt32", rebaixamentos)
        self.assertIn("e_gt42", rebaixamentos)
        self.assertEqual(rebaixamentos["e_gt32"].categoria_destino_id, "gt3")
        self.assertEqual(rebaixamentos["e_gt42"].categoria_destino_id, "gt4")

    def test_production_rebaixamento_3_por_classe(self):
        manager = PromocaoManager()

        equipes_production = []
        classes = [("mazda", "mz"), ("toyota", "ty"), ("bmw_m2", "bm")]
        posicao_global = 1

        for classe, prefixo in classes:
            for idx in range(1, 6):
                equipe = _team(
                    f"{prefixo}{idx}",
                    f"{classe.upper()} {idx}",
                    "production_challenger",
                    budget=80.0,
                    carro_classe=classe,
                )
                equipes_production.append(equipe)
                manager.registrar_resultado(
                    equipe,
                    posicao=posicao_global,
                    pontos=120 - (idx * 10),
                    total_equipes=15,
                    temporada=1,
                )
                posicao_global += 1

        relatorio = manager.processar_fim_temporada(
            equipes_por_categoria={
                "production_challenger": equipes_production,
            },
            temporada=1,
            aplicar_automaticamente=False,
        )

        self.assertEqual(len(relatorio.rebaixamentos), 9)
        destinos = [mov.categoria_destino_id for mov in relatorio.rebaixamentos]
        self.assertEqual(destinos.count("mazda_amador"), 3)
        self.assertEqual(destinos.count("toyota_amador"), 3)
        self.assertEqual(destinos.count("bmw_m2"), 3)

    def test_clausula_saida_rebaixamento_libera_piloto(self):
        manager = PromocaoManager()

        equipe_campea = _team("ma1", "Mazda A", "mazda_amador", budget=80.0)
        equipe_rebaixada = _team("ma2", "Mazda B", "mazda_amador", budget=60.0)

        banco = {
            "equipes": [equipe_campea, equipe_rebaixada],
            "pilotos": [
                {
                    "id": "p100",
                    "nome": "Driver Clause",
                    "equipe_id": "ma2",
                    "equipe_nome": "Mazda B",
                    "categoria_atual": "mazda_amador",
                    "status": "ativo",
                    "contrato_anos": 2,
                }
            ],
            "mercado": {
                "contratos_ativos": [
                    Contrato(
                        piloto_id="p100",
                        piloto_nome="Driver Clause",
                        equipe_id="ma2",
                        equipe_nome="Mazda B",
                        temporada_inicio=1,
                        duracao_anos=2,
                        salario_anual=10000.0,
                        papel=PapelEquipe.NUMERO_2,
                        clausulas=[Clausula(tipo=TipoClausula.SAIDA_REBAIXAMENTO)],
                        status=StatusContrato.ATIVO,
                    ).to_dict()
                ]
            },
        }

        manager.registrar_resultado(equipe_campea, posicao=1, pontos=120, total_equipes=2, temporada=1)
        manager.registrar_resultado(equipe_rebaixada, posicao=2, pontos=30, total_equipes=2, temporada=1)

        relatorio = manager.processar_fim_temporada(
            equipes_por_categoria={"mazda_amador": [equipe_campea, equipe_rebaixada]},
            temporada=1,
            banco=banco,
            aplicar_automaticamente=True,
        )

        piloto = banco["pilotos"][0]
        self.assertIsNone(piloto.get("equipe_id"))
        self.assertEqual(piloto.get("contrato_anos"), 0)
        self.assertEqual(str(piloto.get("status", "")).lower(), "livre")

        self.assertGreaterEqual(relatorio.total_pilotos_liberados, 1)
        mov_rebaixamento = next((m for m in relatorio.rebaixamentos if m.equipe_id == "ma2"), None)
        self.assertIsNotNone(mov_rebaixamento)
        self.assertIn("p100", mov_rebaixamento.pilotos_que_sairam)

    def test_migracao_ids_legados_para_expandidos(self):
        banco = criar_banco_vazio()
        banco["pilotos"] = [{"id": 1, "nome": "P", "categoria_atual": "mx5"}]
        banco["equipes"] = [{"id": 10, "nome": "E", "categoria": "toyotagr86"}]
        banco["arquivo_season_por_categoria"] = {"mx5": "a.json", "bmwm2cs": "b.json"}
        banco["max_drivers_por_categoria"] = {"toyotagr86": 20}
        banco["volta_rapida_por_rodada"] = {"mx5": {"1": {"piloto_nome": "P"}}}
        banco["mercado"]["vagas_abertas"] = [{"categoria_id": "bmwm2cs"}]
        banco["mercado"]["fechamento_temporada"] = {
            "em_andamento": False,
            "ano_base": 2026,
            "aposentados": [],
        }

        banco_validado, alterado = _validar_campos_banco(banco)

        self.assertTrue(alterado)
        self.assertEqual(banco_validado["pilotos"][0]["categoria_atual"], "mazda_rookie")
        self.assertEqual(banco_validado["equipes"][0]["categoria"], "toyota_amador")

        self.assertIn("mazda_rookie", banco_validado["arquivo_season_por_categoria"])
        self.assertIn("bmw_m2", banco_validado["arquivo_season_por_categoria"])
        self.assertIn("toyota_amador", banco_validado["max_drivers_por_categoria"])
        self.assertIn("mazda_rookie", banco_validado["volta_rapida_por_rodada"])

        fechamento = banco_validado["mercado"]["fechamento_temporada"]
        self.assertIn("simulacao_ai_concluida", fechamento)
        self.assertIn("promocao_processada", fechamento)
        self.assertIn("relatorio_promocao", fechamento)


if __name__ == "__main__":
    unittest.main()

