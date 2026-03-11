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

import copy
import random
from typing import Any

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
    gerar_lesao,
)
from .qualifying import simulate_qualifying
from .race import simulate_race
from .race_simulator import RaceSimulator, SimulationConfig, get_simulator

# ── Funções legadas (mantidas para compatibilidade com código existente) ───────

try:
    from Dados.constantes import (
        CATEGORIAS,
        CATEGORIAS_CONFIG,
        PONTUACAO_ENDURANCE,
        PONTUACAO_PADRAO,
    )
except ImportError:
    CATEGORIAS = []
    CATEGORIAS_CONFIG = {}
    PONTUACAO_ENDURANCE = {1: 35, 2: 28, 3: 23, 4: 19, 5: 16, 6: 13, 7: 10, 8: 7, 9: 4, 10: 2}
    PONTUACAO_PADRAO = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}

try:
    from Logica.equipes import obter_equipe_piloto, obter_equipes_categoria, calcular_pontos_equipes
except ImportError:
    def obter_equipe_piloto(banco, piloto): return None
    def obter_equipes_categoria(banco, cat): return []
    def calcular_pontos_equipes(banco, cat): pass

try:
    from Logica.pilotos import (
        atualizar_stats_piloto,
        obter_pilotos_categoria,
        resetar_stats_temporada,
    )
except ImportError:
    def atualizar_stats_piloto(p, **kw): return 0
    def obter_pilotos_categoria(banco, cat): return []
    def resetar_stats_temporada(p): pass


def _m4_resolver_fator_lesao(lesao: Any) -> float:
    """
    Normaliza fator de lesao para multiplicador de skill.

    Compatibilidade:
    - schema novo: modifier negativo (ex: -0.15)
    - schema antigo: modifier multiplicativo (ex: 0.88)
    """
    if not isinstance(lesao, dict):
        return 1.0

    penalidade = lesao.get("penalidade_skill")
    try:
        penalidade_f = float(penalidade)
        if penalidade_f >= 0:
            return max(0.1, 1.0 - penalidade_f)
    except (TypeError, ValueError):
        pass

    try:
        modifier = float(lesao.get("modifier", 1.0))
    except (TypeError, ValueError):
        return 1.0

    if modifier < 0:
        return max(0.1, 1.0 + modifier)
    if modifier == 0:
        return 1.0
    return max(0.1, modifier)


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
    lesao_modifier = _m4_resolver_fator_lesao(lesao)

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


def _m4_safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _m4_resolver_classe_equipe(categoria_id: str, equipe: dict[str, Any] | None) -> str:
    if not isinstance(equipe, dict):
        return ""

    categoria = str(categoria_id or "").strip().lower()
    if categoria == "endurance":
        return str(equipe.get("classe_endurance", "gt3") or "gt3").strip().lower()
    if categoria == "production_challenger":
        raw = str(equipe.get("carro_classe") or equipe.get("pro_trilha_marca") or "mazda").strip().lower()
        return "bmw_m2" if raw == "bmw" else raw
    return ""


def _m4_resolver_nome_categoria(categoria_id: str) -> str:
    cat = next(
        (c for c in CATEGORIAS if str(c.get("id", "")).strip() == str(categoria_id).strip()),
        None,
    )
    if isinstance(cat, dict):
        nome = str(cat.get("nome", "") or "").strip()
        if nome:
            return nome
    cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
    return str(cfg.get("nome", categoria_id) or categoria_id)


def _m4_resolver_tier_categoria(categoria_id: str) -> int:
    cat = next(
        (c for c in CATEGORIAS if str(c.get("id", "")).strip() == str(categoria_id).strip()),
        None,
    )
    if isinstance(cat, dict):
        nivel = cat.get("nivel")
        if isinstance(nivel, (int, float)):
            return max(1, int(nivel))

    cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
    nivel_txt = str(cfg.get("nivel", "") or "").strip().lower()
    mapa = {
        "rookie": 1,
        "amador": 2,
        "pro": 3,
        "super_pro": 4,
        "elite": 5,
        "super_elite": 6,
    }
    return mapa.get(nivel_txt, 1)


def _m4_resolver_etapa_atual(
    banco: dict[str, Any],
    categoria_id: str,
) -> tuple[int, dict[str, Any]]:
    rodada = max(1, _m4_safe_int(banco.get("rodada_atual", 1), 1))

    try:
        from Logica.aiseason import obter_calendario_predefinido

        calendario_preset = obter_calendario_predefinido(categoria_id)
    except Exception:
        calendario_preset = []

    if isinstance(calendario_preset, list) and 1 <= rodada <= len(calendario_preset):
        etapa = calendario_preset[rodada - 1]
        if isinstance(etapa, dict):
            return rodada, {
                "nome": f"Rodada {rodada}",
                "circuito": etapa.get("nome", f"Track {etapa.get('trackId', 0)}"),
                "trackId": etapa.get("trackId", 0),
            }

    calendario = banco.get("calendario", [])
    if isinstance(calendario, list) and 1 <= rodada <= len(calendario):
        etapa = calendario[rodada - 1]
        if isinstance(etapa, dict):
            return rodada, dict(etapa)

    return rodada, {
        "nome": f"Rodada {rodada}",
        "circuito": "Circuito aleatorio",
        "trackId": 0,
    }


def _m4_resolver_duracao_corrida(
    categoria_id: str,
    rodada: int,
    etapa: dict[str, Any],
) -> int:
    for key in ("duracao_corrida_minutos", "duracao_corrida", "race_minutes"):
        value = etapa.get(key)
        if value is not None:
            duracao = _m4_safe_int(value, 0)
            if duracao > 0:
                return duracao

    cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
    duracao_cfg = cfg.get("duracao_corrida_minutos")
    if duracao_cfg is not None:
        duracao = _m4_safe_int(duracao_cfg, 0)
        if duracao > 0:
            return duracao

    calendario_cfg = cfg.get("calendario", {})
    if isinstance(calendario_cfg, dict):
        pistas = calendario_cfg.get("pistas_fixas", [])
        if isinstance(pistas, list) and 1 <= rodada <= len(pistas):
            item = pistas[rodada - 1]
            if isinstance(item, dict):
                duracao = _m4_safe_int(item.get("duracao_corrida"), 0)
                if duracao > 0:
                    return duracao

    if str(categoria_id or "").strip().lower() == "endurance":
        return 90
    return 30


def _m4_resolver_total_laps(etapa: dict[str, Any], duracao_corrida_min: int) -> int:
    voltas_raw = etapa.get("voltas", etapa.get("laps", etapa.get("total_laps")))
    voltas = _m4_safe_int(voltas_raw, 0)
    if voltas > 0:
        return voltas
    return max(8, int(round(max(10, duracao_corrida_min) * 0.65)))


def _m4_montar_config_simulacao(
    banco: dict[str, Any],
    categoria_id: str,
) -> tuple[SimulationConfig, dict[str, Any]]:
    categoria = str(categoria_id or "").strip()
    rodada, etapa = _m4_resolver_etapa_atual(banco, categoria)

    duracao_corrida_min = _m4_resolver_duracao_corrida(categoria, rodada, etapa)
    total_laps = _m4_resolver_total_laps(etapa, duracao_corrida_min)
    cfg = CATEGORIAS_CONFIG.get(categoria, {})
    sistema = str(cfg.get("sistema_pontuacao", "padrao")).strip().lower()
    points_system = dict(PONTUACAO_ENDURANCE if sistema == "endurance" else PONTUACAO_PADRAO)

    track_name = str(
        etapa.get("circuito")
        or etapa.get("pista")
        or etapa.get("nome")
        or f"Track {etapa.get('trackId', 0)}"
    ).strip()
    if not track_name:
        track_name = "Circuito"

    track_id = _m4_safe_int(
        etapa.get("trackId", etapa.get("track_id", etapa.get("pista_id", 0))),
        0,
    )

    config = SimulationConfig(
        category_id=categoria,
        category_name=_m4_resolver_nome_categoria(categoria),
        category_tier=_m4_resolver_tier_categoria(categoria),
        track_id=track_id,
        track_name=track_name,
        total_laps=total_laps,
        race_duration_minutes=duracao_corrida_min,
        points_system=points_system,
    )
    return config, etapa


def _m4_registrar_equipe_por_piloto(
    mapa: dict[Any, dict[str, Any]],
    piloto_id: Any,
    equipe: dict[str, Any],
) -> None:
    if piloto_id in (None, "") or isinstance(piloto_id, bool):
        return
    mapa[piloto_id] = equipe
    mapa[str(piloto_id)] = equipe
    try:
        mapa[int(piloto_id)] = equipe
    except (TypeError, ValueError):
        pass


def _m4_mapear_equipes_por_piloto(
    banco: dict[str, Any],
    categoria_id: str,
    pilotos: list[dict[str, Any]],
) -> dict[Any, dict[str, Any]]:
    equipes = obter_equipes_categoria(banco, categoria_id)
    mapa: dict[Any, dict[str, Any]] = {}

    equipes_por_id: dict[str, dict[str, Any]] = {}
    for equipe in equipes:
        if not isinstance(equipe, dict):
            continue
        equipe_id = equipe.get("id")
        if equipe_id not in (None, ""):
            equipes_por_id[str(equipe_id)] = equipe

        _m4_registrar_equipe_por_piloto(mapa, equipe.get("piloto_numero_1"), equipe)
        _m4_registrar_equipe_por_piloto(mapa, equipe.get("piloto_numero_2"), equipe)

        pilotos_equipe = equipe.get("pilotos", [])
        if isinstance(pilotos_equipe, list):
            for item in pilotos_equipe:
                if isinstance(item, dict):
                    _m4_registrar_equipe_por_piloto(mapa, item.get("id"), equipe)
                else:
                    _m4_registrar_equipe_por_piloto(mapa, item, equipe)

    for piloto in pilotos:
        if not isinstance(piloto, dict):
            continue
        piloto_id = piloto.get("id")
        equipe_id = piloto.get("equipe_id")
        if equipe_id in (None, ""):
            continue
        equipe = equipes_por_id.get(str(equipe_id))
        if isinstance(equipe, dict):
            _m4_registrar_equipe_por_piloto(mapa, piloto_id, equipe)

    return mapa


def _m4_normalizar_piloto_id(piloto_id: Any) -> str:
    if piloto_id in (None, "") or isinstance(piloto_id, bool):
        return ""
    try:
        return str(int(piloto_id))
    except (TypeError, ValueError):
        return str(piloto_id).strip()


def _m4_ids_equivalentes(left: Any, right: Any) -> bool:
    return _m4_normalizar_piloto_id(left) == _m4_normalizar_piloto_id(right)


def _m4_obter_equipe_do_mapa(
    teams_by_pilot: dict[Any, dict[str, Any]],
    piloto_id: Any,
) -> dict[str, Any] | None:
    pid = _m4_normalizar_piloto_id(piloto_id)
    if not pid:
        return None
    for key, equipe in teams_by_pilot.items():
        if _m4_ids_equivalentes(key, pid):
            return equipe
    return None


def _m4_remover_equipe_mapa_por_piloto(
    teams_by_pilot: dict[Any, dict[str, Any]],
    piloto_id: Any,
) -> None:
    pid = _m4_normalizar_piloto_id(piloto_id)
    if not pid:
        return
    for key in list(teams_by_pilot.keys()):
        if _m4_ids_equivalentes(key, pid):
            teams_by_pilot.pop(key, None)


def _m4_lesao_ativa(piloto: dict[str, Any]) -> dict[str, Any] | None:
    lesao = piloto.get("lesao")
    if not isinstance(lesao, dict):
        return None
    try:
        corridas_restantes = int(lesao.get("corridas_restantes", 0) or 0)
    except (TypeError, ValueError):
        corridas_restantes = 0
    if corridas_restantes <= 0:
        return None
    lesao["corridas_restantes"] = corridas_restantes
    lesao["modifier"] = float(lesao.get("modifier", 0.0) or 0.0)
    lesao["perde_corridas"] = bool(lesao.get("perde_corridas", False))
    return lesao


def _m4_sincronizar_campos_lesao_legado(piloto: dict[str, Any]) -> None:
    lesao = _m4_lesao_ativa(piloto)
    if not lesao:
        piloto["lesao"] = None
        piloto["lesionado"] = False
        piloto["severidade_lesao"] = 0.0
        piloto["corridas_lesao"] = 0
        return

    fator = _m4_resolver_fator_lesao(lesao)
    severidade = max(0.0, min(0.95, 1.0 - fator))
    piloto["lesionado"] = True
    piloto["severidade_lesao"] = round(severidade, 3)
    piloto["corridas_lesao"] = int(lesao.get("corridas_restantes", 0) or 0)


def _m4_consumir_lesao_apos_corrida(piloto: dict[str, Any]) -> None:
    lesao = _m4_lesao_ativa(piloto)
    if not lesao:
        _m4_sincronizar_campos_lesao_legado(piloto)
        return

    corridas_restantes = int(lesao.get("corridas_restantes", 0) or 0) - 1
    if corridas_restantes <= 0:
        piloto["lesao"] = None
        piloto["status"] = "ativo"
        piloto.pop("substituindo_piloto_id", None)
        _m4_sincronizar_campos_lesao_legado(piloto)
        return

    lesao["corridas_restantes"] = corridas_restantes
    piloto["lesao"] = lesao
    _m4_sincronizar_campos_lesao_legado(piloto)


def _m4_sincronizar_substitutos_categoria(
    pilotos_categoria: list[dict[str, Any]],
) -> None:
    """
    Libera reservas que estavam cobrindo titulares ja recuperados.
    """
    pilotos_por_id = {
        _m4_normalizar_piloto_id(p.get("id")): p
        for p in pilotos_categoria
        if isinstance(p, dict)
    }

    for piloto in pilotos_categoria:
        if not isinstance(piloto, dict):
            continue
        titular_id = _m4_normalizar_piloto_id(piloto.get("substituindo_piloto_id"))
        if not titular_id:
            continue

        titular = pilotos_por_id.get(titular_id)
        titular_lesao = _m4_lesao_ativa(titular) if isinstance(titular, dict) else None
        if titular_lesao and bool(titular_lesao.get("perde_corridas", False)):
            continue

        piloto.pop("substituindo_piloto_id", None)
        piloto["status"] = "reserva"
        piloto["equipe_id"] = None
        piloto["equipe_nome"] = None
        piloto["papel"] = None


def _m4_encontrar_reserva_livre(
    pilotos_categoria: list[dict[str, Any]],
    ids_bloqueados: set[str],
) -> dict[str, Any] | None:
    for piloto in pilotos_categoria:
        if not isinstance(piloto, dict):
            continue
        piloto_id = _m4_normalizar_piloto_id(piloto.get("id"))
        if not piloto_id or piloto_id in ids_bloqueados:
            continue
        if bool(piloto.get("aposentado", False)):
            continue
        if piloto.get("equipe_id") not in (None, ""):
            continue
        status = str(piloto.get("status", "reserva") or "reserva").strip().lower()
        if status not in {"reserva", "reserva_global", "livre"}:
            continue
        if _m4_lesao_ativa(piloto):
            continue
        return piloto
    return None


def _m4_preparar_pilotos_para_corrida(
    pilotos_categoria: list[dict[str, Any]],
    teams_by_pilot: dict[Any, dict[str, Any]],
) -> tuple[list[dict[str, Any]], set[str]]:
    """
    Prepara lista de pilotos para corrida:
    - aplica modifier de lesao no skill;
    - remove pilotos com lesao que exige perda de corridas;
    - tenta substituir por reserva quando houver.

    Retorna:
    - pilotos para simulacao (copias);
    - ids com lesao pre-existente (para consumir 1 corrida apos o evento).
    """
    preexistentes: set[str] = set()
    suspensos: set[str] = set()
    substitutos_temporarios: list[dict[str, Any]] = []
    ids_substitutos_temporarios: set[str] = set()

    for piloto in pilotos_categoria:
        if not isinstance(piloto, dict):
            continue
        lesao = _m4_lesao_ativa(piloto)
        _m4_sincronizar_campos_lesao_legado(piloto)
        if not lesao:
            continue
        piloto_id = _m4_normalizar_piloto_id(piloto.get("id"))
        if not piloto_id:
            continue
        preexistentes.add(piloto_id)
        if bool(lesao.get("perde_corridas", False)):
            suspensos.add(piloto_id)

    ids_em_uso = {
        _m4_normalizar_piloto_id(p.get("id"))
        for p in pilotos_categoria
        if isinstance(p, dict) and p.get("equipe_id") not in (None, "")
    }

    for piloto in pilotos_categoria:
        if not isinstance(piloto, dict):
            continue
        piloto_id = _m4_normalizar_piloto_id(piloto.get("id"))
        if not piloto_id or piloto_id not in suspensos:
            continue

        equipe = _m4_obter_equipe_do_mapa(teams_by_pilot, piloto_id)
        _m4_remover_equipe_mapa_por_piloto(teams_by_pilot, piloto_id)
        if not isinstance(equipe, dict):
            continue

        reserva = _m4_encontrar_reserva_livre(
            pilotos_categoria,
            ids_bloqueados=(ids_em_uso | suspensos),
        )
        if not isinstance(reserva, dict):
            continue

        reserva_id = _m4_normalizar_piloto_id(reserva.get("id"))
        if not reserva_id:
            continue

        reserva_copia = copy.deepcopy(reserva)
        reserva_copia["status"] = "ativo"
        reserva_copia["equipe_id"] = equipe.get("id")
        reserva_copia["equipe_nome"] = equipe.get("nome")
        reserva_copia["papel"] = "reserva_substituto"
        reserva_copia["substituindo_piloto_id"] = piloto.get("id")
        substitutos_temporarios.append(reserva_copia)
        ids_substitutos_temporarios.add(reserva_id)

        _m4_registrar_equipe_por_piloto(teams_by_pilot, reserva_copia.get("id"), equipe)
        ids_em_uso.add(reserva_id)

    pilotos_simulacao: list[dict[str, Any]] = []
    for piloto in (list(pilotos_categoria) + substitutos_temporarios):
        if not isinstance(piloto, dict):
            continue
        piloto_id = _m4_normalizar_piloto_id(piloto.get("id"))
        if piloto in pilotos_categoria and piloto_id and piloto_id in suspensos:
            continue
        if (
            piloto in pilotos_categoria
            and piloto_id
            and piloto_id in ids_substitutos_temporarios
            and piloto.get("equipe_id") in (None, "")
        ):
            continue
        if _m4_obter_equipe_do_mapa(teams_by_pilot, piloto.get("id")) is None:
            continue

        copia = copy.deepcopy(piloto)
        lesao = _m4_lesao_ativa(piloto)
        if lesao and not bool(lesao.get("perde_corridas", False)):
            fator = _m4_resolver_fator_lesao(lesao)
            try:
                skill_base = float(copia.get("skill", 50) or 50)
            except (TypeError, ValueError):
                skill_base = 50.0
            copia["skill"] = max(1, int(round(skill_base * fator)))
        pilotos_simulacao.append(copia)

    return pilotos_simulacao, preexistentes


def _m4_aplicar_lesoes_novas_do_evento(
    pilotos_categoria: list[dict[str, Any]],
    evento: RaceResult,
) -> None:
    pilotos_por_id = {
        _m4_normalizar_piloto_id(p.get("id")): p
        for p in pilotos_categoria
        if isinstance(p, dict)
    }

    for resultado in evento.race_results:
        if not bool(resultado.is_dnf):
            continue
        incidente_lesivo = next(
            (
                incidente
                for incidente in (resultado.incidents or [])
                if (
                    getattr(incidente, "incident_type", None) == IncidentType.COLLISION
                    or str(getattr(incidente, "incident_type", "")).endswith("COLLISION")
                )
                and bool(getattr(incidente, "causes_injury", False))
            ),
            None,
        )
        if incidente_lesivo is None:
            continue

        piloto_id = _m4_normalizar_piloto_id(resultado.pilot_id)
        piloto = pilotos_por_id.get(piloto_id)
        if not isinstance(piloto, dict) or bool(piloto.get("aposentado", False)):
            continue

        lesao = gerar_lesao(incidente_lesivo)
        piloto["lesao"] = lesao
        piloto["status"] = "lesionado" if bool(lesao.get("perde_corridas", False)) else "ativo"
        _m4_sincronizar_campos_lesao_legado(piloto)

        idade = _m4_safe_int(piloto.get("idade"), 0)
        if str(lesao.get("tipo", "")).strip().lower() == "grave" and idade > 38 and random.random() < 0.20:
            piloto["aposentado"] = True
            piloto["status"] = "aposentado"
            piloto["equipe_id"] = None
            piloto["equipe_nome"] = None
            piloto["papel"] = None


def _m4_consumir_lesoes_preexistentes(
    pilotos_categoria: list[dict[str, Any]],
    ids_preexistentes: set[str],
) -> None:
    for piloto in pilotos_categoria:
        if not isinstance(piloto, dict):
            continue
        piloto_id = _m4_normalizar_piloto_id(piloto.get("id"))
        if not piloto_id or piloto_id not in ids_preexistentes:
            continue
        _m4_consumir_lesao_apos_corrida(piloto)


def _m4_converter_resultado_quali(
    quali_results: list[QualifyingResult],
    teams_by_pilot: dict[Any, dict[str, Any]],
    categoria_id: str,
) -> list[dict[str, Any]]:
    categoria_cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
    multiclass = bool(categoria_cfg.get("multiclasse", False))

    saida: list[dict[str, Any]] = []
    for resultado in sorted(quali_results, key=lambda r: r.position):
        equipe = teams_by_pilot.get(resultado.pilot_id) or teams_by_pilot.get(str(resultado.pilot_id))
        classe = _m4_resolver_classe_equipe(categoria_id, equipe)
        saida.append(
            {
                "posicao": int(resultado.position),
                "piloto_id": resultado.pilot_id,
                "piloto_nome": resultado.pilot_name,
                "equipe_id": resultado.team_id,
                "equipe_nome": resultado.team_name,
                "classe": classe,
                "quali_score": float(resultado.quali_score),
                "tempo_ms": float(resultado.best_lap_time_ms),
                "gap_pole_ms": float(resultado.gap_to_pole_ms),
                "pole": bool(resultado.is_pole),
                "posicao_campeonato": int(resultado.position),
                "multiclasse": multiclass,
            }
        )

    return saida


def _m4_converter_resultado_corrida(
    race_result: RaceResult,
    categoria_id: str,
) -> dict[str, Any]:
    categoria_cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
    multiclass = bool(categoria_cfg.get("multiclasse", False))

    classificacao: list[dict[str, Any]] = []
    geral: list[tuple[int, Any, float]] = []
    por_classe: dict[str, list[tuple[int, Any, int]]] = {}

    for resultado in sorted(race_result.race_results, key=lambda r: r.finish_position):
        posicao_geral = int(resultado.finish_position)
        posicao_classe = int(resultado.class_position or posicao_geral)
        classe = str(resultado.class_id or "").strip().lower()
        pontos = int(resultado.points_earned or 0)
        pontos_classe = int(resultado.points_in_class or pontos)
        posicao_campeonato = posicao_classe if multiclass and classe else posicao_geral

        classificacao.append(
            {
                "piloto_id": resultado.pilot_id,
                "piloto_nome": resultado.pilot_name,
                "equipe_id": resultado.team_id,
                "equipe_nome": resultado.team_name,
                "classe": classe,
                "dnf": bool(resultado.is_dnf),
                "motivo_dnf": resultado.dnf_reason,
                "volta_rapida": bool(resultado.has_fastest_lap),
                "pole": bool(resultado.pilot_id == race_result.pole_sitter_id),
                "pontos": pontos,
                "pontos_classe": pontos_classe,
                "posicao_geral": posicao_geral,
                "posicao_classe": posicao_classe,
                "posicao_campeonato": posicao_campeonato,
                "grid": int(resultado.grid_position),
                "melhor_volta_ms": float(resultado.best_lap_time_ms or 0),
                "incidentes": int(resultado.incidents_count or 0),
            }
        )

        tempo_referencia = float(resultado.total_race_time_ms or resultado.best_lap_time_ms or 0)
        geral.append((posicao_geral, resultado.pilot_id, tempo_referencia))
        if classe:
            por_classe.setdefault(classe, []).append(
                (posicao_classe, resultado.pilot_id, pontos_classe)
            )

    for classe_id, linhas in por_classe.items():
        por_classe[classe_id] = sorted(linhas, key=lambda item: item[0])

    return {
        "classificacao": classificacao,
        "geral": geral,
        "por_classe": por_classe,
        "pole_sitter_id": race_result.pole_sitter_id,
        "winner_id": race_result.winner_id,
        "fastest_lap_id": race_result.fastest_lap_id,
    }


def simular_classificacao_categoria(banco, categoria_id):
    """
    Simula apenas a classificacao usando o RaceSimulator (M4).
    """
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    if not pilotos:
        return []

    simulator = get_simulator()
    config, _ = _m4_montar_config_simulacao(banco, categoria_id)
    teams_by_pilot = _m4_mapear_equipes_por_piloto(banco, categoria_id, pilotos)
    context = simulator.create_context(config)
    quali_results = simulator.simulate_qualifying_session(pilotos, teams_by_pilot, context)
    return _m4_converter_resultado_quali(quali_results, teams_by_pilot, categoria_id)


def simular_corrida_categoria_detalhada(banco, categoria_id):
    """
    Simula corrida completa via RaceSimulator (M4) e retorna payload detalhado.
    """
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    if not pilotos:
        return {"classificacao": [], "geral": [], "por_classe": {}}

    simulator = get_simulator()
    config, etapa = _m4_montar_config_simulacao(banco, categoria_id)
    teams_by_pilot = _m4_mapear_equipes_por_piloto(banco, categoria_id, pilotos)
    pilotos_evento, lesoes_preexistentes = _m4_preparar_pilotos_para_corrida(
        pilotos,
        teams_by_pilot,
    )
    evento = simulator.simulate_full_event(
        config=config,
        pilots=pilotos_evento,
        teams=teams_by_pilot,
    )

    # Lesoes antigas consomem 1 corrida; novas lesoes sao geradas por incidentes.
    _m4_consumir_lesoes_preexistentes(pilotos, lesoes_preexistentes)
    _m4_aplicar_lesoes_novas_do_evento(pilotos, evento)

    resultado = _m4_converter_resultado_corrida(evento, categoria_id)
    resultado["etapa"] = etapa
    resultado["duracao_corrida_minutos"] = int(config.race_duration_minutes)
    resultado["categoria_id"] = str(categoria_id)
    return resultado


def simular_corrida_categoria(banco, categoria_id):
    """
    Simula corrida para a categoria via RaceSimulator (M4).
    Mantem compatibilidade de retorno com a UI legada (list[dict]).
    """
    resultado = simular_corrida_categoria_detalhada(banco, categoria_id)
    classificacao = resultado.get("classificacao", [])
    return classificacao if isinstance(classificacao, list) else []


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
        incidentes = (
            random.randint(2, 6)
            if is_dnf
            else (random.randint(1, 3) if random.random() < agg_norm * 0.15 else 0)
        )

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
    "get_weather_modifier", "get_rain_skill_penalty", "calculate_pilot_rain_penalty",
    # Legado
    "calcular_performance_piloto", "simular_corrida",
    "simular_classificacao_categoria",
    "simular_corrida_categoria", "simular_corrida_categoria_detalhada",
    "processar_resultado_corrida", "simular_temporada_completa",
]
