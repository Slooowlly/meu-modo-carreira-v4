"""
Testes unitários para a lógica central do modo carreira.
Cobre: Utils/helpers, Logica/pilotos (atualizar_stats_piloto).
"""

import sys
import os
import unittest

# Garantir que o projeto está no path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntSeguro(unittest.TestCase):
    """Testa Utils.helpers.int_seguro."""

    def setUp(self):
        from Utils.helpers import int_seguro
        self.int_seguro = int_seguro

    def test_valor_inteiro(self):
        self.assertEqual(self.int_seguro(42), 42)

    def test_valor_string(self):
        self.assertEqual(self.int_seguro("10"), 10)

    def test_valor_float(self):
        self.assertEqual(self.int_seguro(3.9), 3)

    def test_valor_none(self):
        self.assertEqual(self.int_seguro(None), 0)

    def test_valor_none_com_padrao(self):
        self.assertEqual(self.int_seguro(None, 5), 5)

    def test_valor_string_invalida(self):
        self.assertEqual(self.int_seguro("abc"), 0)

    def test_valor_bool_true(self):
        # bool deve retornar o padrão (não converter True -> 1)
        self.assertEqual(self.int_seguro(True), 0)

    def test_valor_bool_false(self):
        self.assertEqual(self.int_seguro(False), 0)

    def test_valor_negativo(self):
        self.assertEqual(self.int_seguro(-5), -5)


class TestNormalizarIntPositivo(unittest.TestCase):
    """Testa Utils.helpers.normalizar_int_positivo."""

    def setUp(self):
        from Utils.helpers import normalizar_int_positivo
        self.normalizar = normalizar_int_positivo

    def test_inteiro_positivo(self):
        self.assertEqual(self.normalizar(5), 5)

    def test_inteiro_zero(self):
        self.assertIsNone(self.normalizar(0))

    def test_inteiro_negativo(self):
        self.assertIsNone(self.normalizar(-3))

    def test_float_arredonda(self):
        self.assertEqual(self.normalizar(4.6), 5)

    def test_float_nao_positivo(self):
        self.assertIsNone(self.normalizar(-2.5))

    def test_string_numero(self):
        self.assertEqual(self.normalizar("10"), 10)

    def test_string_vazia(self):
        self.assertIsNone(self.normalizar(""))

    def test_string_com_virgula(self):
        self.assertEqual(self.normalizar("3,0"), 3)

    def test_none(self):
        self.assertIsNone(self.normalizar(None))

    def test_bool(self):
        self.assertIsNone(self.normalizar(True))

    def test_string_nao_inteira(self):
        self.assertIsNone(self.normalizar("abc"))


class TestAtualizarStatsPiloto(unittest.TestCase):
    """Testa Logica.pilotos.atualizar_stats_piloto."""

    def setUp(self):
        from Logica.pilotos import atualizar_stats_piloto
        self.atualizar = atualizar_stats_piloto
        self.piloto_base = {
            "id": 1,
            "nome": "Test Driver",
            "corridas_temporada": 0,
            "corridas_carreira": 0,
            "pontos_temporada": 0,
            "pontos_carreira": 0,
            "vitorias_temporada": 0,
            "vitorias_carreira": 0,
            "podios_temporada": 0,
            "podios_carreira": 0,
            "voltas_rapidas_temporada": 0,
            "voltas_rapidas_carreira": 0,
            "dnfs_temporada": 0,
            "dnfs_carreira": 0,
            "incidentes_temporada": 0,
            "incidentes_carreira": 0,
            "melhor_resultado_temporada": 99,
            "resultados_temporada": [],
        }

    def test_vitoria(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=1)
        self.assertEqual(pontos, 25)
        self.assertEqual(p["vitorias_temporada"], 1)
        self.assertEqual(p["vitorias_carreira"], 1)
        self.assertEqual(p["podios_temporada"], 1)
        self.assertEqual(p["corridas_temporada"], 1)
        self.assertEqual(p["melhor_resultado_temporada"], 1)
        self.assertIn(1, p["resultados_temporada"])

    def test_segundo_lugar(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=2)
        self.assertEqual(pontos, 18)
        self.assertEqual(p["vitorias_temporada"], 0)
        self.assertEqual(p["podios_temporada"], 1)

    def test_fora_pontos(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=15)
        self.assertEqual(pontos, 0)
        self.assertEqual(p["pontos_temporada"], 0)

    def test_dnf(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=1, dnf=True)
        self.assertEqual(pontos, 0)
        self.assertEqual(p["dnfs_temporada"], 1)
        self.assertEqual(p["corridas_temporada"], 1)
        self.assertIn("DNF", p["resultados_temporada"])

    def test_volta_rapida_top10(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=5, volta_rapida=True)
        # Position 5 = 10 pontos + 1 volta rápida
        self.assertEqual(pontos, 11)
        self.assertEqual(p["voltas_rapidas_temporada"], 1)

    def test_volta_rapida_fora_top10(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        pontos = self.atualizar(p, posicao=12, volta_rapida=True)
        # Fora do top 10, ponto extra não se aplica
        self.assertEqual(pontos, 0)
        # Mas volta rápida é registrada
        self.assertEqual(p["voltas_rapidas_temporada"], 1)

    def test_incidentes(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        self.atualizar(p, posicao=3, incidentes=4)
        self.assertEqual(p["incidentes_temporada"], 4)
        self.assertEqual(p["incidentes_carreira"], 4)

    def test_acumulativo(self):
        p = self.piloto_base.copy()
        p["resultados_temporada"] = []
        self.atualizar(p, posicao=1)
        self.atualizar(p, posicao=3)
        self.assertEqual(p["corridas_temporada"], 2)
        self.assertEqual(p["corridas_carreira"], 2)
        self.assertEqual(p["pontos_temporada"], 25 + 15)  # 1st + 3rd
        self.assertEqual(p["vitorias_temporada"], 1)
        self.assertEqual(p["podios_temporada"], 2)


# ============================================================
# TESTES — MÓDULO 2: EQUIPES
# ============================================================

class TestCriarTodasEquipes(unittest.TestCase):
    """Testa a criação das 102 equipes fixas."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)

    def test_total_102_equipes(self):
        self.assertEqual(len(self.banco["equipes"]), 102)

    def test_todos_tem_id_unico(self):
        ids = [e["id"] for e in self.banco["equipes"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_todos_tem_campos_obrigatorios(self):
        for eq in self.banco["equipes"]:
            self.assertIn("nome", eq)
            self.assertIn("categoria", eq)
            self.assertIn("stats", eq)
            self.assertIn("car_performance", eq)


class TestEquipesComecamNiveladas(unittest.TestCase):
    """Todas as equipes devem começar com stats = 50."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)

    def test_car_performance_inicial(self):
        for eq in self.banco["equipes"]:
            self.assertEqual(eq["car_performance"], 50, eq["nome"])

    def test_budget_inicial(self):
        for eq in self.banco["equipes"]:
            self.assertEqual(eq["budget"], 50, eq["nome"])

    def test_facilities_inicial(self):
        for eq in self.banco["equipes"]:
            self.assertEqual(eq["facilities"], 50, eq["nome"])

    def test_expectativa_inicial(self):
        for eq in self.banco["equipes"]:
            self.assertEqual(eq["expectativa"], "Sem expectativa definida", eq["nome"])


class TestContagemPorCategoria(unittest.TestCase):
    """Verifica a contagem de equipes em cada categoria."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)
        self.contagem = {}
        for eq in self.banco["equipes"]:
            cat = eq["categoria"]
            self.contagem[cat] = self.contagem.get(cat, 0) + 1

    def test_mazda_rookie(self):
        self.assertEqual(self.contagem.get("mazda_rookie"), 6)

    def test_mazda_amador(self):
        self.assertEqual(self.contagem.get("mazda_amador"), 10)

    def test_toyota_rookie(self):
        self.assertEqual(self.contagem.get("toyota_rookie"), 6)

    def test_toyota_amador(self):
        self.assertEqual(self.contagem.get("toyota_amador"), 10)

    def test_bmw_m2(self):
        self.assertEqual(self.contagem.get("bmw_m2"), 10)

    def test_production_challenger(self):
        self.assertEqual(self.contagem.get("production_challenger"), 15)

    def test_gt4(self):
        self.assertEqual(self.contagem.get("gt4"), 10)

    def test_gt3(self):
        self.assertEqual(self.contagem.get("gt3"), 14)

    def test_endurance(self):
        self.assertEqual(self.contagem.get("endurance"), 21)


class TestPromocaoEquipe(unittest.TestCase):
    """Testa promoção de categoria."""

    def test_promover_muda_categoria_e_nivel(self):
        from Logica.equipes import promover_equipe
        equipe = {
            "nome": "Teste",
            "categoria": "mazda_rookie",
            "nivel": "rookie",
            "morale": 1.0,
            "reputacao": 50,
            "temporadas_na_categoria": 1,
        }
        promover_equipe(equipe, "mazda_amador")
        self.assertEqual(equipe["categoria"], "mazda_amador")
        self.assertEqual(equipe["nivel"], "amador")
        self.assertGreater(equipe["morale"], 1.0)
        self.assertEqual(equipe["temporadas_na_categoria"], 0)
        self.assertEqual(equipe["expectativa"], "Sem expectativa definida")

    def test_rebaixar_muda_categoria_e_penaliza_moral(self):
        from Logica.equipes import rebaixar_equipe
        equipe = {
            "nome": "Teste",
            "categoria": "mazda_amador",
            "nivel": "amador",
            "morale": 1.0,
            "reputacao": 50,
            "temporadas_na_categoria": 3,
        }
        rebaixar_equipe(equipe, "mazda_rookie")
        self.assertEqual(equipe["categoria"], "mazda_rookie")
        self.assertLess(equipe["morale"], 1.0)
        self.assertLess(equipe["reputacao"], 50)


class TestMigracaoSchemaAntigo(unittest.TestCase):
    """Testa migração de equipe com schema antigo."""

    def test_migrar_campos_basicos(self):
        from Logica.equipes import migrar_equipe_schema_antigo
        equipe_antiga = {
            "id": 1,
            "nome": "Teste",
            "tier": 2,
            "orcamento": 60,
            "pitcrew_skill": 70,
            "estrategia_risco": 0.5,
            "performance": 55.0,
            "pilotos": [],
        }
        eq = migrar_equipe_schema_antigo(equipe_antiga)
        self.assertIn("nome_curto", eq)
        self.assertEqual(eq["budget"], 60)
        self.assertEqual(eq["pit_crew"], 70)
        self.assertEqual(eq["strategy_risk"], 50)
        self.assertEqual(eq["car_performance"], 55.0)
        self.assertEqual(eq["nivel"], "elite")

    def test_migrar_nao_sobrescreve_existente(self):
        from Logica.equipes import migrar_equipe_schema_antigo
        equipe = {
            "id": 2,
            "nome": "Existente",
            "budget": 80,
            "pit_crew": 90,
            "strategy_risk": 30,
            "pilotos": [],
        }
        eq = migrar_equipe_schema_antigo(equipe)
        self.assertEqual(eq["budget"], 80)    # não sobrescreveu
        self.assertEqual(eq["pit_crew"], 90)  # não sobrescreveu


class TestCamposEquipeCompletos(unittest.TestCase):
    """Verifica que criar_equipe_inicial gera TODOS os campos do schema."""

    def test_todos_campos_obrigatorios(self):
        from Logica.equipes import criar_equipe_inicial
        banco = {"equipes": [], "proximo_id_equipe": 1}
        nome_info = {
            "nome": "Teste", "nome_curto": "TST",
            "pais": "🇧🇷 Brasil", "cores": ("#000000", "#FFFFFF"),
        }
        eq = criar_equipe_inicial(banco, nome_info, "mazda_rookie", 2024)

        campos_obrigatorios = [
            "id", "nome", "nome_curto", "pais_sede", "cor_primaria", "cor_secundaria",
            "ano_fundacao", "categoria", "nivel", "temporadas_na_categoria",
            "marca", "carro_classe", "classe_endurance",
            "pilotos", "piloto_numero_1", "piloto_numero_2",
            "car_performance", "stats", "budget", "facilities", "engineering_quality",
            "development_rate", "pit_crew", "strategy_risk", "reputacao", "morale",
            "salarios_totais", "gastos_desenvolvimento", "patrocinadores",
            "expectativa", "expectativa_posicao", "chance_dnf",
            "titulos_construtores", "vitorias_equipe", "podios_equipe", "poles_equipe",
            "corridas_equipe", "pontos_historico", "melhor_posicao_campeonato",
            "pontos_temporada", "vitorias_temporada", "podios_temporada",
            "poles_temporada", "corridas_temporada",
            "pilotos_historico", "historico_temporadas", "atributos_extras",
        ]

        faltando = [c for c in campos_obrigatorios if c not in eq]
        self.assertEqual(faltando, [], f"Campos faltando: {faltando}")


class TestDefinirHierarquiaPilotos(unittest.TestCase):
    """Verifica que definir_hierarquia_pilotos atualiza piloto['papel']."""

    def test_hierarquia_por_skill(self):
        from Logica.equipes import definir_hierarquia_pilotos
        banco = {
            "equipes": [],
            "pilotos": [
                {"id": 1, "nome": "Piloto A", "skill": 80, "papel": None},
                {"id": 2, "nome": "Piloto B", "skill": 70, "papel": None},
            ],
            "proximo_id_equipe": 1,
        }
        equipe = {
            "id": 1,
            "pilotos": [1, 2],
            "piloto_numero_1": None,
            "piloto_numero_2": None,
            "piloto_1": None,
            "piloto_2": None,
        }
        definir_hierarquia_pilotos(banco, equipe)

        self.assertEqual(equipe["piloto_numero_1"], 1)
        self.assertEqual(equipe["piloto_numero_2"], 2)
        self.assertEqual(banco["pilotos"][0]["papel"], "numero_1")
        self.assertEqual(banco["pilotos"][1]["papel"], "numero_2")


class TestProductionChallengerClasses(unittest.TestCase):
    """Production Challenger deve ter exatamente 5 equipes de cada classe."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)
        self.prod = [e for e in self.banco["equipes"]
                     if e["categoria"] == "production_challenger"]

    def test_tres_classes_presentes(self):
        classes = set(e.get("carro_classe") for e in self.prod)
        self.assertEqual(classes, {"mazda", "toyota", "bmw_m2"})

    def test_cinco_equipes_por_classe(self):
        for classe in ["mazda", "toyota", "bmw_m2"]:
            count = len([e for e in self.prod if e.get("carro_classe") == classe])
            self.assertEqual(count, 5, f"Esperava 5 equipes '{classe}', encontrou {count}")


class TestEnduranceClasses(unittest.TestCase):
    """Endurance deve ter 8 GT3 + 5 GT4 + 8 LMP2 = 21 equipes."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)
        self.end = [e for e in self.banco["equipes"] if e["categoria"] == "endurance"]

    def test_total_endurance(self):
        self.assertEqual(len(self.end), 21)

    def test_gt3_count(self):
        n = len([e for e in self.end if e.get("classe_endurance") == "gt3"])
        self.assertEqual(n, 8)

    def test_gt4_count(self):
        n = len([e for e in self.end if e.get("classe_endurance") == "gt4"])
        self.assertEqual(n, 5)

    def test_lmp2_count(self):
        n = len([e for e in self.end if e.get("classe_endurance") == "lmp2"])
        self.assertEqual(n, 8)


class TestMarcasGT(unittest.TestCase):
    """Todas as equipes GT3/GT4 e Endurance GT3/GT4 devem ter marca definida."""

    def setUp(self):
        from Logica.equipes import criar_todas_equipes
        self.banco = {"equipes": [], "proximo_id_equipe": 1}
        criar_todas_equipes(self.banco, 2024)

    def test_gt3_tem_marca(self):
        for eq in self.banco["equipes"]:
            if eq["categoria"] == "gt3":
                self.assertIsNotNone(eq["marca"], f"{eq['nome']} sem marca")

    def test_gt4_tem_marca(self):
        for eq in self.banco["equipes"]:
            if eq["categoria"] == "gt4":
                self.assertIsNotNone(eq["marca"], f"{eq['nome']} sem marca")

    def test_endurance_gt3_gt4_tem_marca(self):
        for eq in self.banco["equipes"]:
            if eq["categoria"] == "endurance" and eq.get("classe_endurance") in ("gt3", "gt4"):
                self.assertIsNotNone(eq["marca"], f"{eq['nome']} sem marca")

    def test_lmp2_sem_marca(self):
        """LMP2 não usa marca."""
        for eq in self.banco["equipes"]:
            if eq.get("classe_endurance") == "lmp2":
                # Não tem marca (não é GT)
                self.assertIsNone(eq.get("marca"), f"{eq['nome']} não deveria ter marca")


# ============================================================
# TESTES — MÓDULO 3: CATEGORIAS E CALENDÁRIOS
# ============================================================

class TestTodasCategoriasTemCalendario(unittest.TestCase):
    """Todas as categorias devem ter calendário e num_corridas."""

    def test_calendario_e_num_corridas_presentes(self):
        from Dados.constantes import CATEGORIAS_CONFIG
        for cat_id, config in CATEGORIAS_CONFIG.items():
            with self.subTest(cat=cat_id):
                self.assertIn("calendario", config, f"{cat_id} sem 'calendario'")
                self.assertIn("num_corridas", config, f"{cat_id} sem 'num_corridas'")
                self.assertIn("tamanho_grid", config, f"{cat_id} sem 'tamanho_grid'")


class TestCalendarioTemPistasSuficientes(unittest.TestCase):
    """fixas + variáveis ≥ num_corridas em todas as categorias."""

    def test_pistas_suficientes(self):
        from Dados.constantes import CATEGORIAS_CONFIG
        for cat_id, config in CATEGORIAS_CONFIG.items():
            with self.subTest(cat=cat_id):
                cal = config["calendario"]
                fixas = cal.get("pistas_fixas", [])
                n_var = cal.get("num_variaveis", 0)
                total = len(fixas) + n_var
                self.assertGreaterEqual(total, config["num_corridas"],
                    f"{cat_id}: {total} pistas < {config['num_corridas']} corridas")


class TestCategoriasBaseUsaPistasGratuitas(unittest.TestCase):
    """Categorias rookies/amador/challenger usam apenas pistas gratuitas."""

    CATS_GRATUITAS = [
        "mazda_rookie", "toyota_rookie",
        "mazda_amador", "toyota_amador",
        "bmw_m2", "production_challenger",
    ]

    def test_pistas_sao_gratuitas(self):
        from Dados.constantes import CATEGORIAS_CONFIG, PISTAS_GRATUITAS
        nomes_gratuitas = {p["nome"] for p in PISTAS_GRATUITAS}

        for cat_id in self.CATS_GRATUITAS:
            cal = CATEGORIAS_CONFIG[cat_id]["calendario"]
            fixas = cal.get("pistas_fixas", [])
            variaveis = cal.get("pistas_variaveis", [])

            for pista in fixas:
                nome = pista["nome"] if isinstance(pista, dict) else pista
                with self.subTest(cat=cat_id, pista=nome):
                    self.assertIn(nome, nomes_gratuitas)

            for pista in variaveis:
                nome = pista["nome"] if isinstance(pista, dict) else pista
                with self.subTest(cat=cat_id, pista=nome):
                    self.assertIn(nome, nomes_gratuitas)


class TestPontuacaoCorrida(unittest.TestCase):
    """Testa cálculo de pontos com e sem bônus."""

    def test_primeiro_lugar_padrao(self):
        from Logica.categorias import calcular_pontos_corrida
        self.assertEqual(calcular_pontos_corrida(1, "mazda_rookie"), 25)

    def test_pole_bonus(self):
        from Logica.categorias import calcular_pontos_corrida
        self.assertEqual(calcular_pontos_corrida(1, "mazda_rookie", eh_pole=True), 26)

    def test_pole_e_volta_rapida(self):
        from Logica.categorias import calcular_pontos_corrida
        self.assertEqual(calcular_pontos_corrida(1, "mazda_rookie", eh_pole=True, volta_rapida=True), 27)

    def test_endurance_primeiro_lugar(self):
        from Logica.categorias import calcular_pontos_corrida
        self.assertEqual(calcular_pontos_corrida(1, "endurance"), 35)

    def test_multiclasse_bonus_geral(self):
        from Logica.categorias import calcular_pontos_corrida
        # 1º na classe (25) + 1º geral (5) = 30
        pts = calcular_pontos_corrida(1, "production_challenger", posicao_geral=1)
        self.assertEqual(pts, 30)

    def test_fora_pontos_retorna_zero(self):
        from Logica.categorias import calcular_pontos_corrida
        self.assertEqual(calcular_pontos_corrida(15, "gt3"), 0)

    def test_volta_rapida_fora_top10_sem_bonus(self):
        from Logica.categorias import calcular_pontos_corrida
        # 11º + volta rápida → sem bônus (VR só conta se top 10)
        pts = calcular_pontos_corrida(11, "gt3", volta_rapida=True)
        self.assertEqual(pts, 0)


class TestGerarCalendarioTemporada(unittest.TestCase):
    """Testa geração do calendário (lista de corridas)."""

    def test_mazda_rookie_5_corridas(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("mazda_rookie", 1)
        self.assertEqual(len(cal), 5)

    def test_corrida_tem_campos_obrigatorios(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("mazda_rookie", 1)
        campos = [
            "rodada", "nome_evento", "pista",
            "duracao_corrida_minutos", "duracao_classificacao_minutos",
            "horario_corrida", "horario_sessao_iracing",
            "clima", "status",
        ]
        for corrida in cal:
            for campo in campos:
                with self.subTest(campo=campo):
                    self.assertIn(campo, corrida)

    def test_gt3_14_corridas(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("gt3", 1)
        self.assertEqual(len(cal), 14)

    def test_endurance_6_corridas(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("endurance", 1)
        self.assertEqual(len(cal), 6)


class TestHorarioSessaoCalculado(unittest.TestCase):
    """Testa cálculo do horário de início de sessão."""

    def test_14h_menos_15min(self):
        from Logica.categorias import calcular_horario_inicio_sessao
        self.assertEqual(calcular_horario_inicio_sessao("14:00", 15), "13:45")

    def test_14h_menos_20min(self):
        from Logica.categorias import calcular_horario_inicio_sessao
        self.assertEqual(calcular_horario_inicio_sessao("14:00", 20), "13:40")

    def test_10h_menos_15min(self):
        from Logica.categorias import calcular_horario_inicio_sessao
        self.assertEqual(calcular_horario_inicio_sessao("10:00", 15), "09:45")

    def test_00h_menos_20min(self):
        from Logica.categorias import calcular_horario_inicio_sessao
        self.assertEqual(calcular_horario_inicio_sessao("00:10", 20), "23:50")


class TestClimaIracingConfig(unittest.TestCase):
    """Testa extração de config de clima para iRacing."""

    def test_corrida_seca(self):
        from Logica.categorias import obter_config_clima_iracing
        corrida = {"clima": {"chuva": False, "config_iracing": "realistic"}}
        self.assertEqual(obter_config_clima_iracing(corrida), "realistic")

    def test_corrida_chuva_forte(self):
        from Logica.categorias import obter_config_clima_iracing
        corrida = {"clima": {"chuva": True, "intensidade": "forte", "config_iracing": "realistic_rain_heavy"}}
        self.assertEqual(obter_config_clima_iracing(corrida), "realistic_rain_heavy")

    def test_corrida_clima_ausente(self):
        from Logica.categorias import obter_config_clima_iracing
        # Sem chave "clima" → default "realistic"
        self.assertEqual(obter_config_clima_iracing({}), "realistic")


class TestEnduranceNomesEventos(unittest.TestCase):
    """Endurance deve ter nomes de evento corretos."""

    def test_nomes_corretos(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("endurance", 1)
        self.assertEqual(len(cal), 6)
        nomes = [c["nome_evento"] for c in cal]
        self.assertIn("3 Horas de Daytona", nomes)
        self.assertIn("4 Horas de Spa", nomes)
        self.assertIn("4 Horas de Bathurst", nomes)

    def test_duracoes_endurance_variam(self):
        from Logica.categorias import gerar_calendario_temporada
        cal = gerar_calendario_temporada("endurance", 1)
        duracoes = set(c["duracao_corrida_minutos"] for c in cal)
        # Deve ter múltiplas durações (60, 90, 120)
        self.assertGreater(len(duracoes), 1)




# ============================================================
# TESTES — MÓDULO 4: MOTOR DE SIMULAÇÃO
# ============================================================

class TestModelsImportam(unittest.TestCase):
    """Todos os enums e dataclasses do módulo 4 importam."""

    def test_enums_importam(self):
        from Logica.simulacao import (
            SessionType, IncidentType, IncidentSeverity,
            WeatherCondition, RaceSegment,
        )
        self.assertEqual(WeatherCondition.DRY.value, "dry")
        self.assertEqual(RaceSegment.START.value, "start")

    def test_dataclasses_importam(self):
        from Logica.simulacao import (
            QualifyingResult, RaceDriverResult, RaceResult, SimulationContext,
        )
        ctx = SimulationContext(
            category_id="mazda_rookie", category_tier=1,
            track_id=0, track_name="Lime Rock Park",
            weather=WeatherCondition.DRY if False else __import__(
                'Logica.simulacao', fromlist=['WeatherCondition']
            ).WeatherCondition.DRY,
            temperature=25.0, humidity=50.0,
            total_laps=18, race_duration_minutes=15,
        )
        self.assertEqual(ctx.category_id, "mazda_rookie")


class TestQualifyingResultFormatado(unittest.TestCase):
    """QualifyingResult.best_lap_formatted retorna formato correto."""

    def test_tempo_1min30(self):
        from Logica.simulacao import QualifyingResult
        qr = QualifyingResult(
            pilot_id="p1", pilot_name="Test", team_id="t1", team_name="Team",
            position=1, quali_score=80.0,
            best_lap_time_ms=90000, gap_to_pole_ms=0, is_pole=True,
        )
        self.assertTrue(qr.best_lap_formatted.startswith("1:"))

    def test_gap_pole_zero(self):
        from Logica.simulacao import QualifyingResult
        qr = QualifyingResult(
            pilot_id="p1", pilot_name="P", team_id="t", team_name="T",
            position=1, quali_score=80.0, best_lap_time_ms=90000,
            gap_to_pole_ms=0, is_pole=True,
        )
        self.assertEqual(qr.gap_to_pole_ms, 0)


class TestDetermineWeatherForced(unittest.TestCase):
    """determine_weather respeita force_condition."""

    def test_forcar_dry(self):
        from Logica.simulacao import determine_weather, WeatherCondition
        result = determine_weather(0, WeatherCondition.DRY, "Spa")
        self.assertEqual(result, WeatherCondition.DRY)

    def test_forcar_heavy_rain(self):
        from Logica.simulacao import determine_weather, WeatherCondition
        result = determine_weather(0, WeatherCondition.HEAVY_RAIN)
        self.assertEqual(result, WeatherCondition.HEAVY_RAIN)


class TestRainPenaltyAbsorvida(unittest.TestCase):
    """Piloto com rain_factor=100 absorve 90% da penalidade."""

    def test_rain_factor_alto(self):
        from Logica.simulacao import calculate_pilot_rain_penalty
        penalty = calculate_pilot_rain_penalty(0.12, 100)
        self.assertAlmostEqual(penalty, 0.12 * 0.10, places=5)

    def test_rain_factor_zero(self):
        from Logica.simulacao import calculate_pilot_rain_penalty
        penalty = calculate_pilot_rain_penalty(0.12, 0)
        self.assertAlmostEqual(penalty, 0.12, places=5)


class TestCalculatePoints(unittest.TestCase):
    """Calculo de pontos com e sem bonus."""

    def test_primeiro_lugar(self):
        from Logica.simulacao import calculate_points
        self.assertEqual(calculate_points(1), 25)

    def test_pole_bonus(self):
        from Logica.simulacao import calculate_points
        self.assertEqual(calculate_points(1, got_pole=True), 26)

    def test_pole_e_vr(self):
        from Logica.simulacao import calculate_points
        self.assertEqual(calculate_points(1, got_pole=True, got_fastest_lap=True), 27)

    def test_fora_pontos(self):
        from Logica.simulacao import calculate_points
        self.assertEqual(calculate_points(15), 0)


class TestIncidentDNF(unittest.TestCase):
    """IncidentResult com MAJOR/CRITICAL severity define is_dnf=True."""

    def test_major_eh_dnf(self):
        from Logica.simulacao import IncidentResult, IncidentSeverity, IncidentType, RaceSegment
        inc = IncidentResult(
            incident_type=IncidentType.MECHANICAL,
            severity=IncidentSeverity.MAJOR,
            segment=RaceSegment.MID,
        )
        self.assertTrue(inc.is_dnf)

    def test_minor_nao_eh_dnf(self):
        from Logica.simulacao import IncidentResult, IncidentSeverity, IncidentType, RaceSegment
        inc = IncidentResult(
            incident_type=IncidentType.DRIVER_ERROR,
            severity=IncidentSeverity.MINOR,
            segment=RaceSegment.EARLY,
        )
        self.assertFalse(inc.is_dnf)


class TestSimulacaoSimplificada(unittest.TestCase):
    """simulate_simple retorna RaceResult bem formado com pilotos mock."""

    def _make_pilots_and_teams(self, n=6):
        """Cria n pilotos e equipes como dicts simples."""
        pilots = [
            {"id": f"p{i}", "nome": f"Piloto {i}", "skill": 50 + i * 3,
             "consistencia": 60, "ritmo_classificacao": 55, "rain_factor": 50,
             "corridas_na_categoria": 10}
            for i in range(1, n + 1)
        ]
        teams = {
            f"p{i}": {"id": f"t{i}", "nome": f"Equipe {i}", "car_performance": 55 + i}
            for i in range(1, n + 1)
        }

        # Adaptar pilotos para suportar getattr
        class PilotWrapper:
            def __init__(self, d):
                self.__dict__.update(d)
                self.id = d["id"]
                self.name = d["nome"]
                self.skill = d["skill"]
                self.ritmo_classificacao = d["ritmo_classificacao"]
                self.rain_factor = d["rain_factor"]
                self.consistency = d["consistencia"]
                self.corridas_na_categoria = d["corridas_na_categoria"]

        class TeamWrapper:
            def __init__(self, d):
                self.__dict__.update(d)
                self.id = d["id"]
                self.name = d["nome"]
                self.car_performance = d["car_performance"]

        pilot_objs = [PilotWrapper(p) for p in pilots]
        team_dict  = {f"p{i}": TeamWrapper(teams[f"p{i}"]) for i in range(1, n + 1)}
        return pilot_objs, team_dict

    def test_resultado_tem_vencedor(self):
        from Logica.simulacao import RaceSimulator, SimulationConfig, WeatherCondition
        pilots, teams = self._make_pilots_and_teams()
        sim = RaceSimulator()
        cfg = SimulationConfig(
            category_id="mazda_rookie", category_name="Mazda Rookie",
            category_tier=1, track_id=0, track_name="Test Track",
            total_laps=10, race_duration_minutes=15,
            force_weather=WeatherCondition.DRY,
        )
        result = sim.simulate_simple(cfg, pilots, teams)
        self.assertNotEqual(result.winner_id, "")
        self.assertEqual(len(result.race_results), 6)

    def test_grid_posicoes_distintas(self):
        from Logica.simulacao import RaceSimulator, SimulationConfig, WeatherCondition
        pilots, teams = self._make_pilots_and_teams()
        sim = RaceSimulator()
        cfg = SimulationConfig(
            category_id="mazda_rookie", category_name="Mazda Rookie",
            category_tier=1, track_id=0, track_name="Test Track",
            total_laps=10, race_duration_minutes=15,
            force_weather=WeatherCondition.DRY,
        )
        result = sim.simulate_simple(cfg, pilots, teams)
        positions = [r.finish_position for r in result.race_results]
        self.assertEqual(len(positions), len(set(positions)))


class TestHighlightsGerados(unittest.TestCase):
    """simulate_simple gera lista de highlights não vazia."""

    def test_highlights_nao_vazios(self):
        from Logica.simulacao import RaceSimulator, SimulationConfig, WeatherCondition

        class P:
            def __init__(self, i):
                self.id = f"p{i}"; self.name = f"Pilot {i}"; self.nome = self.name
                self.skill = 60; self.ritmo_classificacao = 55; self.rain_factor = 50
                self.consistency = 65; self.corridas_na_categoria = 15
        class T:
            def __init__(self, i):
                self.id = f"t{i}"; self.name = f"Team {i}"; self.car_performance = 60

        pilots = [P(i) for i in range(1, 7)]
        teams  = {f"p{i}": T(i) for i in range(1, 7)}

        sim = RaceSimulator()
        cfg = SimulationConfig(
            category_id="gt3", category_name="GT3",
            category_tier=5, track_id=0, track_name="Spa",
            total_laps=20, race_duration_minutes=50,
            force_weather=WeatherCondition.DRY,
        )
        result = sim.simulate_simple(cfg, pilots, teams)
        self.assertGreater(len(result.highlights), 0)
        self.assertIn("Spa", result.highlights[0])


class TestLogicaExport(unittest.TestCase):
    """Testa Logica.export integration."""

    def test_calculate_pilot_for_export(self):
        from Logica.export import calculate_pilot_for_export, build_pilot_context, build_race_context
        
        piloto = {
            "id": 1,
            "nome": "Test Driver",
            "skill": 50,
            "agressividade": 50,
            "otimismo": 50,
            "suavidade": 50,
            "idade": 25,
            "is_jogador": False
        }
        
        pilot_ctx = build_pilot_context(piloto)
        race_ctx = build_race_context(
            category_id="mx5", track_id=0, track_name="Test", 
            round_number=1, total_rounds=10, 
            championship_data={"ano_atual": 2024},
            weather_data=None
        )
        
        export_data = calculate_pilot_for_export(
            pilot=piloto, pilot_ctx=pilot_ctx, race_ctx=race_ctx,
            races_this_season=0
        )
        
        self.assertIsNotNone(export_data)
        self.assertGreaterEqual(export_data["skill"], 0)
        self.assertLessEqual(export_data["skill"], 10000)


# ============================================================
# TESTES — MÓDULO 7: MERCADO
# ============================================================

class TestMercadoVisibilidade(unittest.TestCase):
    """Testa cálculo de visibilidade por tier/idade/resultado."""

    def test_visibilidade_aumenta_com_resultado(self):
        from Logica.mercado.visibilidade import calcular_visibilidade
        piloto = {"id": 10, "idade": 22, "titulos": 1}
        calc = calcular_visibilidade(
            piloto=piloto,
            categoria_tier=4,
            posicao_campeonato=2,
            total_pilotos_categoria=20,
            vitorias_temporada=3,
            poles_temporada=2,
            is_advanced_subtier=True,
        )
        self.assertGreaterEqual(calc.visibilidade_final, 4.0)


class TestMercadoAvaliacao(unittest.TestCase):
    """Testa avaliação com erro de potencial."""

    def test_avaliacao_potencial_estimado_limites(self):
        from Logica.mercado.avaliacao import avaliar_piloto
        piloto = {
            "id": 1,
            "skill": 65,
            "potencial_base": 82,
            "potencial_bonus": 4,
            "consistencia": 60,
            "experience": 45,
            "idade": 24,
            "salario": 40000,
        }
        equipe = {"id": 100, "engineering_quality": 70, "budget": 80}
        avaliacao = avaliar_piloto(piloto, equipe, visibilidade=7.0)
        self.assertGreaterEqual(avaliacao.potencial_estimado, 40)
        self.assertLessEqual(avaliacao.potencial_estimado, 100)
        self.assertGreaterEqual(avaliacao.margem_erro, 5)
        self.assertLessEqual(avaliacao.margem_erro, 15)


class TestMercadoContratos(unittest.TestCase):
    """Testa salário e ciclo básico de contratos."""

    def test_contrato_expira_e_renova(self):
        from Logica.mercado.contratos import (
            PapelEquipe,
            criar_contrato,
            renovar_contrato,
            verificar_contrato_expira,
        )
        contrato = criar_contrato(
            piloto_id="1",
            piloto_nome="Piloto A",
            equipe_id="9",
            equipe_nome="Equipe X",
            temporada_inicio=1,
            duracao_anos=1,
            salario_anual=50000,
            papel=PapelEquipe.NUMERO_1,
        )
        self.assertTrue(verificar_contrato_expira(contrato, temporada_atual=1))
        novo = renovar_contrato(contrato, temporada_atual=1, nova_duracao=2)
        self.assertEqual(novo.temporada_inicio, 2)
        self.assertEqual(novo.duracao_anos, 2)


class TestMercadoDecisaoPiloto(unittest.TestCase):
    """Testa aceite/recusa de propostas por NPC."""

    def test_piloto_aceita_melhor_proposta(self):
        import random
        from Logica.mercado.decisoes_piloto import piloto_decide_propostas
        from Logica.mercado.models import PapelEquipe, PilotoMercado, Proposta

        random.seed(7)
        piloto = PilotoMercado(
            id="50",
            nome="NPC Test",
            idade=26,
            nacionalidade="Brasil",
            skill=72,
            potencial=85,
            experience=35,
            salario_minimo=30000,
            categoria_tier=3,
        )
        proposta_fraca = Proposta(
            id="a",
            equipe_id="1",
            equipe_nome="Equipe Fraca",
            piloto_id="50",
            piloto_nome="NPC Test",
            salario_anual=20000,
            papel=PapelEquipe.NUMERO_2,
            categoria_tier=2,
            car_performance=35,
            reputacao_equipe=30,
        )
        proposta_forte = Proposta(
            id="b",
            equipe_id="2",
            equipe_nome="Equipe Forte",
            piloto_id="50",
            piloto_nome="NPC Test",
            salario_anual=90000,
            papel=PapelEquipe.NUMERO_1,
            categoria_tier=4,
            car_performance=80,
            reputacao_equipe=75,
        )
        decisao = piloto_decide_propostas(piloto, [proposta_fraca, proposta_forte])
        self.assertIsNotNone(decisao.proposta_aceita)
        self.assertEqual(decisao.proposta_aceita.id, "b")


class TestMercadoManagerIntegracao(unittest.TestCase):
    """Integração mínima do mercado no fim de janela."""

    def _banco_base(self):
        from Dados.banco import criar_banco_vazio
        banco = criar_banco_vazio()
        banco["temporada_atual"] = 1
        banco["ano_atual"] = 2024
        banco["equipes"] = [
            {
                "id": 1,
                "nome": "Equipe A",
                "categoria": "mx5",
                "pilotos": [1, 2],
                "piloto_numero_1": 1,
                "piloto_numero_2": 2,
                "piloto_1": "Jogador",
                "piloto_2": "NPC 2",
                "car_performance": 65,
                "budget": 80,
                "reputacao": 65,
                "expectativa_posicao": 6,
            },
            {
                "id": 2,
                "nome": "Equipe B",
                "categoria": "mx5",
                "pilotos": [],
                "piloto_numero_1": None,
                "piloto_numero_2": None,
                "piloto_1": None,
                "piloto_2": None,
                "car_performance": 62,
                "budget": 78,
                "reputacao": 60,
                "expectativa_posicao": 8,
            },
        ]
        banco["pilotos"] = [
            {
                "id": 1,
                "nome": "Jogador",
                "is_jogador": True,
                "status": "ativo",
                "idade": 24,
                "skill": 70,
                "consistencia": 65,
                "experience": 30,
                "categoria_atual": "mx5",
                "equipe_id": 1,
                "equipe_nome": "Equipe A",
                "papel": "numero_1",
                "contrato_anos": 0,
                "salario": 60000,
                "pontos_temporada": 120,
                "vitorias_temporada": 3,
                "podios_temporada": 5,
                "poles_temporada": 2,
                "potencial_base": 82,
                "potencial_bonus": 3,
                "titulos": 0,
            },
            {
                "id": 2,
                "nome": "NPC 2",
                "is_jogador": False,
                "status": "ativo",
                "idade": 28,
                "skill": 64,
                "consistencia": 62,
                "experience": 36,
                "categoria_atual": "mx5",
                "equipe_id": 1,
                "equipe_nome": "Equipe A",
                "papel": "numero_2",
                "contrato_anos": 1,
                "salario": 50000,
                "pontos_temporada": 90,
                "vitorias_temporada": 1,
                "podios_temporada": 3,
                "poles_temporada": 0,
                "potencial_base": 74,
                "potencial_bonus": 1,
                "titulos": 0,
            },
        ]
        return banco

    def test_jogador_recebe_pendencia_e_decide(self):
        import random
        from Logica.mercado import MercadoManager

        random.seed(11)
        banco = self._banco_base()
        manager = MercadoManager(banco)

        manager.processar_janela_transferencias(temporada=1, jogador_id=1)
        pendencias = manager.obter_pendencias_jogador(1)
        self.assertGreaterEqual(len(pendencias), 1)

        primeira = pendencias[0]
        retorno = manager.aplicar_decisao_jogador("aceitar", proposta_id=primeira.id, jogador_id=1)
        self.assertTrue(retorno.get("ok", False))
        self.assertEqual(len(manager.obter_pendencias_jogador(1)), 0)

        resumo = manager.finalizar_janela(temporada=1)
        self.assertGreaterEqual(resumo.total_propostas, 1)
        self.assertFalse(banco["mercado"]["janela_aberta"])
        jogador = next(p for p in banco["pilotos"] if p.get("is_jogador"))
        self.assertIsNotNone(jogador.get("equipe_id"))

if __name__ == "__main__":
    unittest.main()
