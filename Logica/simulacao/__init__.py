"""
Módulo 4: Motor de Simulação de Corridas

Uso básico::

    from Logica.simulacao import RaceSimulator, SimulationConfig

    simulator = RaceSimulator()
    result = simulator.simulate_full_event(
        config=SimulationConfig(
            category_id="mazda_rookie",
            category_name="Mazda MX-5 Rookie Cup",
            category_tier=1,
            track_id=0,
            track_name="Lime Rock Park",
            total_laps=18,
            race_duration_minutes=15,
        ),
        pilots=lista_de_pilotos,
        teams=dict_pilot_id_to_team,
    )

Funções legadas (Módulos 1–3)::

    from Logica.simulacao import simular_corrida, simular_temporada_completa
"""

import logging
import random

logger = logging.getLogger(__name__)

# ── Novos exports do Módulo 4 ─────────────────────────────────────────────────
from .models import (
    SessionType,
    IncidentType,
    IncidentSeverity,
    WeatherCondition,
    RaceSegment,
    SegmentResult,
    IncidentResult,
    QualifyingResult,
    RaceDriverResult,
    SafetyCarPeriod,
    RaceResult,
    SimulationContext,
    calculate_points,
    DEFAULT_POINTS_SYSTEM,
)
from .weather import (
    determine_weather,
    get_weather_modifier,
    get_rain_skill_penalty,
    calculate_pilot_rain_penalty,
)
from .incidents import (
    PilotIncidentProfile,
    roll_for_incident,
    calculate_mechanical_failure_chance,
    calculate_driver_error_chance,
    calculate_collision_chance,
)
from .qualifying import simulate_qualifying, calculate_quali_score
from .race import simulate_race, simulate_segment, calculate_segment_score
from .safety_car import (
    should_deploy_safety_car,
    create_safety_car_period,
    apply_safety_car_effect,
)
from .race_simulator import RaceSimulator, SimulationConfig, get_simulator

# ── Funções legadas (mantidas para compatibilidade com código existente) ───────

try:
    from Dados.constantes import CATEGORIAS
except ImportError:
    CATEGORIAS = []

try:
    from Logica.equipes import obter_equipe_piloto, obter_equipes_categoria, calcular_pontos_equipes
except ImportError:
    def obter_equipe_piloto(banco, piloto): return None
    def obter_equipes_categoria(banco, cat): return []
    def calcular_pontos_equipes(banco, cat): pass

try:
    from Logica.pilotos import (
        atualizar_stats_piloto,
        normalizar_aggression,
        obter_pilotos_categoria,
        resetar_stats_temporada,
    )
except ImportError:
    def atualizar_stats_piloto(p, **kw): return 0
    def normalizar_aggression(v): return v
    def obter_pilotos_categoria(banco, cat): return []
    def resetar_stats_temporada(p): pass


def calcular_performance_piloto(piloto, equipe=None):
    """
    Calcula a performance de um piloto numa corrida.
    Mantida para compatibilidade com o código existente.
    """
    skill = piloto.get("skill", 50)
    idade = piloto.get("idade", 25)

    agg_raw = piloto.get("aggression", 0.5)
    if isinstance(agg_raw, (int, float)) and agg_raw > 1.0:
        aggression = agg_raw / 100.0
    else:
        aggression = float(agg_raw)

    if 25 <= idade <= 32:
        exp_bonus = random.uniform(2, 5)
    elif idade < 22:
        exp_bonus = random.uniform(-3, 0)
    elif idade > 36:
        exp_bonus = random.uniform(-2, 1)
    else:
        exp_bonus = random.uniform(0, 2)

    agg_factor = random.uniform(-5, 8) if aggression > 0.7 else random.uniform(-2, 3)

    consistencia = piloto.get("consistencia", 50)
    consist_factor = (consistencia - 50) / 100.0 * random.uniform(1.0, 3.0)

    racecraft = piloto.get("racecraft", 50)
    racecraft_factor = (racecraft - 50) / 100.0 * random.uniform(0.5, 2.0)

    fitness = piloto.get("fitness", 70)
    fitness_factor = (fitness - 50) / 100.0 * random.uniform(0.5, 1.5)

    motivacao = piloto.get("motivacao", 70)
    motiv_factor = (motivacao - 50) / 100.0 * random.uniform(0.5, 1.5)

    lesao = piloto.get("lesao")
    lesao_modifier = lesao.get("modifier", 1.0) if lesao else 1.0

    equipe_bonus = 0.0
    if equipe:
        stats  = equipe.get("stats", {})
        chassi = stats.get("chassi", 50) / 100
        motor  = stats.get("motor", 50) / 100
        aero   = stats.get("aerodinamica", 50) / 100
        confiab = stats.get("confiabilidade", 70) / 100

        equipe_media = (chassi + motor + aero) / 3
        equipe_bonus = equipe_media * random.uniform(4, 10)

        if random.random() > confiab:
            equipe_bonus -= random.uniform(5, 15)

    aleatorio = random.uniform(-12, 12)

    performance = (
        skill
        + exp_bonus
        + agg_factor
        + consist_factor
        + racecraft_factor
        + fitness_factor
        + motiv_factor
        + equipe_bonus
        + aleatorio
    ) * lesao_modifier

    return max(0, performance)


def simular_corrida(pilotos, banco=None):
    """
    Simula uma corrida (função legada).
    Retorna lista de dicts {piloto, dnf, performance}.
    """
    resultados = []
    for piloto in pilotos:
        equipe = obter_equipe_piloto(banco, piloto) if banco else None
        performance = calcular_performance_piloto(piloto, equipe)

        agg_raw = piloto.get("aggression", 0.5)
        agg_norm = agg_raw / 100.0 if isinstance(agg_raw, (int, float)) and agg_raw > 1.0 else float(agg_raw)
        chance_dnf = agg_norm * 0.08

        if equipe:
            confiab = equipe.get("stats", {}).get("confiabilidade", 70) / 100
            chance_dnf += (1 - confiab) * 0.05

        if random.random() < chance_dnf:
            resultados.append({"piloto": piloto, "dnf": True, "performance": 0})
        else:
            resultados.append({"piloto": piloto, "dnf": False, "performance": performance})

    resultados.sort(key=lambda x: (x["dnf"], -x["performance"]))
    return resultados


def simular_corrida_categoria(banco, categoria_id):
    """
    Simula uma corrida para uma categoria (função legada).
    Retorna list[dict] com piloto_id, piloto_nome, dnf e volta_rapida.
    """
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    if not pilotos:
        return []

    resultado_bruto = simular_corrida(pilotos, banco)
    pilotos_terminaram = [item for item in resultado_bruto if not item["dnf"]]

    piloto_vr_id = None
    if pilotos_terminaram:
        piloto_vr_id = max(pilotos_terminaram, key=lambda i: i["performance"])["piloto"]["id"]

    classificacao = []
    for entrada in resultado_bruto:
        piloto = entrada["piloto"]
        classificacao.append({
            "piloto_id":     piloto.get("id"),
            "piloto_nome":   piloto.get("nome", "???"),
            "dnf":           bool(entrada.get("dnf", False)),
            "volta_rapida":  (not bool(entrada.get("dnf", False)) and piloto.get("id") == piloto_vr_id),
        })
    return classificacao


def processar_resultado_corrida(resultado_corrida):
    """Processa resultado de corrida e atualiza stats (função legada)."""
    pilotos_terminaram = [r for r in resultado_corrida if not r["dnf"]]
    melhor_volta_piloto = (
        max(pilotos_terminaram, key=lambda x: x["performance"])["piloto"]
        if pilotos_terminaram else None
    )

    stats_corrida = {"vencedor": None, "pole": melhor_volta_piloto, "dnfs": 0, "classificacao": []}

    for pos, resultado in enumerate(resultado_corrida):
        piloto      = resultado["piloto"]
        posicao     = pos + 1
        is_dnf      = resultado["dnf"]
        volta_rapida = (
            not is_dnf
            and melhor_volta_piloto is not None
            and piloto["id"] == melhor_volta_piloto["id"]
        )

        agg_raw  = piloto.get("aggression", 0.5)
        agg_norm = (agg_raw / 100.0) if isinstance(agg_raw, (int, float)) and agg_raw > 1.0 else float(agg_raw)
        incidentes = random.randint(2, 6) if is_dnf else (random.randint(1, 3) if random.random() < agg_norm * 0.15 else 0)

        pontos = atualizar_stats_piloto(
            piloto,
            posicao=posicao,
            dnf=is_dnf,
            volta_rapida=volta_rapida,
            incidentes=incidentes,
        )

        if is_dnf:
            stats_corrida["dnfs"] += 1
        else:
            if posicao == 1:
                stats_corrida["vencedor"] = piloto["nome"]
            stats_corrida["classificacao"].append({
                "posicao": posicao,
                "piloto":  piloto["nome"],
                "pontos":  pontos,
            })

    return stats_corrida


def simular_temporada_completa(banco, categoria_id, ano, num_corridas=None):
    """Simula uma temporada completa (função legada)."""
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    if not pilotos:
        return None

    for piloto in pilotos:
        resetar_stats_temporada(piloto)

    if num_corridas is None:
        num_corridas = random.randint(10, 14)

    corridas_stats = []
    for _ in range(num_corridas):
        resultado = simular_corrida(pilotos, banco)
        stats     = processar_resultado_corrida(resultado)
        corridas_stats.append(stats)

    tem_equipes = len(banco.get("equipes", [])) > 0
    if tem_equipes:
        calcular_pontos_equipes(banco, categoria_id)
        for equipe in obter_equipes_categoria(banco, categoria_id):
            equipe["pontos_historico"]  = equipe.get("pontos_historico", 0)  + equipe.get("pontos_temporada", 0)
            equipe["vitorias_equipe"]   = equipe.get("vitorias_equipe",  0)  + equipe.get("vitorias_temporada", 0)

    categoria_nome = next((c["nome"] for c in CATEGORIAS if c["id"] == categoria_id), categoria_id)

    pilotos_ordenados = sorted(
        pilotos,
        key=lambda p: (-p.get("pontos_temporada", 0), -p.get("vitorias_temporada", 0)),
    )

    classificacao_completa = [
        {
            "posicao":       pos + 1,
            "nome":          piloto["nome"],
            "idade":         piloto["idade"],
            "pontos":        piloto.get("pontos_temporada", 0),
            "vitorias":      piloto.get("vitorias_temporada", 0),
            "podios":        piloto.get("podios_temporada", 0),
            "poles":         piloto.get("poles_temporada", 0),
            "voltas_rapidas": piloto.get("voltas_rapidas_temporada", 0),
            "corridas":      num_corridas,
            "incidentes":    piloto.get("incidentes_temporada", 0),
            "resultados":    piloto.get("resultados_temporada", []).copy(),
            "skill":         piloto["skill"],
            "equipe":        piloto.get("equipe_nome", "Sem equipe"),
        }
        for pos, piloto in enumerate(pilotos_ordenados)
    ]

    campeao = pilotos_ordenados[0]
    campeao["titulos"] = campeao.get("titulos", 0) + 1

    equipe_campea_nome = None
    if tem_equipes:
        equipes_cat = obter_equipes_categoria(banco, categoria_id)
        if equipes_cat:
            equipe_campea = max(equipes_cat, key=lambda e: e.get("pontos_temporada", 0))
            equipe_campea["titulos_equipe"] = equipe_campea.get("titulos_equipe", 0) + 1
            equipe_campea_nome = equipe_campea["nome"]

    return {
        "campeao":               campeao["nome"],
        "pontos_campeao":        campeao.get("pontos_temporada", 0),
        "vice":                  pilotos_ordenados[1]["nome"] if len(pilotos_ordenados) > 1 else None,
        "corridas":              num_corridas,
        "classificacao_completa": classificacao_completa,
        "equipe_campea":         equipe_campea_nome,
        "corridas_stats":        corridas_stats,
    }


__all__ = [
    # Módulo 4 — novos
    "RaceSimulator", "SimulationConfig", "get_simulator",
    "SessionType", "IncidentType", "IncidentSeverity", "WeatherCondition", "RaceSegment",
    "SegmentResult", "IncidentResult", "QualifyingResult", "RaceDriverResult",
    "SafetyCarPeriod", "RaceResult", "SimulationContext",
    "PilotIncidentProfile", "roll_for_incident",
    "simulate_qualifying", "simulate_race", "determine_weather", "calculate_points",
    # Legado
    "calcular_performance_piloto", "simular_corrida", "simular_corrida_categoria",
    "processar_resultado_corrida", "simular_temporada_completa",
]
