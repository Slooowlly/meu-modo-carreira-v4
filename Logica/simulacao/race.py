"""
Simulação de corrida com 5 segmentos.
Motor principal de simulação.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Optional

from .models import (
    RaceSegment,
    RaceDriverResult,
    SegmentResult,
    QualifyingResult,
    SimulationContext,
    WeatherCondition,
    IncidentResult,
    IncidentType,
    IncidentSeverity,
)
from .incidents import PilotIncidentProfile, roll_for_incident
from .weather import get_rain_skill_penalty, calculate_pilot_rain_penalty


def _get(obj: Any, key: str, default=None):
    """Le atributo em dict ou objeto."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_first(obj: Any, keys: tuple[str, ...], default=None):
    """Le o primeiro campo existente dentre aliases."""
    for key in keys:
        value = _get(obj, key, None)
        if value is not None:
            return value
    return default


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


SEGMENT_ATTRIBUTE_WEIGHTS = {
    RaceSegment.START: {
        "skill":               0.20,
        "habilidade_largada":  0.35,
        "racecraft":           0.25,
        "car_performance":     0.20,
    },
    RaceSegment.EARLY: {
        "skill":           0.35,
        "racecraft":       0.20,
        "car_performance": 0.30,
        "gestao_pneus":   0.15,
    },
    RaceSegment.MID: {
        "skill":           0.35,
        "gestao_pneus":   0.20,
        "car_performance": 0.30,
        "fitness":         0.15,
    },
    RaceSegment.LATE: {
        "skill":               0.25,
        "gestao_pneus":       0.25,
        "fitness":             0.20,
        "car_performance":     0.20,
        "resistencia_mental":  0.10,
    },
    RaceSegment.FINISH: {
        "skill":               0.25,
        "racecraft":           0.25,
        "fator_clutch":        0.20,
        "car_performance":     0.20,
        "resistencia_mental":  0.10,
    },
}


@dataclass
class RaceState:
    """Estado de um piloto durante a corrida."""
    pilot_id: str
    pilot_name: str
    team_id: str
    team_name: str
    class_id: str = ""

    attributes: dict = field(default_factory=dict)
    car_performance: float = 70.0
    car_reliability: float = 85.0

    current_position: int = 0
    cumulative_score: float = 0.0
    tire_wear: float = 1.0
    physical_condition: float = 1.0

    segment_results: list = field(default_factory=list)
    incidents: list = field(default_factory=list)

    is_dnf: bool = False
    dnf_segment: Optional[RaceSegment] = None
    dnf_reason: str = ""
    laps_completed: int = 0
    laps_led: int = 0
    best_lap_time_ms: float = 0

    incident_profile: Optional[PilotIncidentProfile] = None


def _get_attr(state: RaceState, attr_name: str, default: float = 50.0) -> float:
    """Busca atributo do piloto com fallback."""
    # Aliases
    aliases = {
        "habilidade_largada": ["start_skill"],
        "gestao_pneus": ["tire_management"],
        "resistencia_mental": ["mental_resistance"],
        "fator_clutch": ["clutch_factor"],
        "fator_chuva": ["rain_factor"],
        "aggression": ["agressividade"],
        "consistencia": ["consistency"],
        "experiencia": ["experience"],
    }
    value = state.attributes.get(attr_name)
    if value is not None:
        return _to_float(value, default)
    for alias in aliases.get(attr_name, []):
        value = state.attributes.get(alias)
        if value is not None:
            return _to_float(value, default)
    return default


def calculate_segment_score(
    state: RaceState,
    segment: RaceSegment,
    context: SimulationContext,
) -> float:
    weights = SEGMENT_ATTRIBUTE_WEIGHTS[segment]
    score = 0.0

    for attr, weight in weights.items():
        value = state.car_performance if attr == "car_performance" else _get_attr(state, attr)
        score += value * weight

    # Degradação de pneu
    tire_penalty = (1.0 - state.tire_wear) * 0.15
    score *= (1 - tire_penalty)

    # Fadiga física (só LATE e FINISH)
    if segment in (RaceSegment.LATE, RaceSegment.FINISH):
        fatigue_penalty = (1.0 - state.physical_condition) * 0.10
        score *= (1 - fatigue_penalty)

    # Modificador de chuva
    if context.weather != WeatherCondition.DRY:
        rain_penalty = get_rain_skill_penalty(context.weather)
        rain_factor  = _get_attr(state, "fator_chuva")
        score *= (1 - calculate_pilot_rain_penalty(rain_penalty, rain_factor))

    # Variância por consistência
    consistency    = _get_attr(state, "consistencia")
    variance_range = (100 - consistency) / 100 * 5
    score += random.uniform(-variance_range, variance_range)

    return max(score, 5.0)


def _apply_tire_degradation(state: RaceState, context: SimulationContext):
    tire_mgmt    = _get_attr(state, "gestao_pneus")
    mgmt_factor  = 1.0 - (tire_mgmt / 100 * 0.50)
    duration_factor = max(0.25, context.race_duration_minutes / 30.0)
    actual_deg   = context.tire_degradation_rate * mgmt_factor * duration_factor
    state.tire_wear = max(0.1, state.tire_wear - actual_deg)


def _apply_physical_degradation(state: RaceState, context: SimulationContext):
    fitness      = _get_attr(state, "fitness")
    fit_factor   = 1.0 - (fitness / 100 * 0.60)
    duration_factor = max(0.25, context.race_duration_minutes / 30.0)
    actual_deg   = context.physical_degradation_rate * fit_factor * duration_factor
    state.physical_condition = max(0.2, state.physical_condition - actual_deg)


def _get_nearby_profiles(current: RaceState, all_states: list, positions_range: int = 3) -> list:
    nearby = []
    for state in all_states:
        if state.pilot_id == current.pilot_id or state.is_dnf:
            continue
        if abs(state.current_position - current.current_position) <= positions_range:
            if state.incident_profile:
                nearby.append(state.incident_profile)
    return nearby


def _ids_equivalentes(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if left in (None, "") or right in (None, ""):
        return False
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def _find_state_by_pilot_id(states: list[RaceState], pilot_id: Any) -> Optional[RaceState]:
    for state in states:
        if _ids_equivalentes(state.pilot_id, pilot_id):
            return state
    return None


def _aplicar_consequencias_colisao(
    incident: IncidentResult,
    states: list[RaceState],
    segment: RaceSegment,
) -> None:
    """
    Propaga consequencias para todos os envolvidos na colisao.

    Regras:
    - 40%: DNF
    - 30%: perde 3-5 posicoes
    - 30%: perde 1-2 posicoes
    """
    envolvidos = list(dict.fromkeys(incident.involved_pilots or []))
    if not envolvidos:
        return

    for piloto_id in envolvidos:
        state = _find_state_by_pilot_id(states, piloto_id)
        if state is None or state.is_dnf:
            continue

        roll = random.random()
        perda_posicoes = 0
        virou_dnf = roll < 0.40

        if virou_dnf:
            state.is_dnf = True
            state.dnf_segment = segment
            state.dnf_reason = "Collision DNF"
            severity = IncidentSeverity.MAJOR
        else:
            if roll < 0.70:
                perda_posicoes = random.randint(3, 5)
            else:
                perda_posicoes = random.randint(1, 2)
            state.cumulative_score -= perda_posicoes * 2
            severity = IncidentSeverity.MINOR

        state.incidents.append(
            IncidentResult(
                incident_type=IncidentType.COLLISION,
                severity=severity,
                segment=segment,
                positions_lost=perda_posicoes,
                involved_pilots=envolvidos,
                description="Collision incident",
                causes_injury=(bool(incident.causes_injury) and virou_dnf),
            )
        )


def _pack_position(position: int, total: int) -> str:
    third = total / 3
    if position <= third:
        return "front"
    if position <= third * 2:
        return "midfield"
    return "back"


def _resolve_team_class(category_id: str, team: Any) -> str:
    """
    Resolve a classe do carro para corridas multiclasse.
    """
    category = str(category_id or "").strip().lower()
    if category == "endurance":
        return str(_get_first(team, ("classe_endurance",), "gt3") or "gt3").strip().lower()
    if category == "production_challenger":
        raw = str(_get_first(team, ("carro_classe", "pro_trilha_marca"), "") or "").strip().lower()
        if raw == "bmw":
            return "bmw_m2"
        return raw or "mazda"
    return ""


def _class_perf_multiplier(category_id: str, class_id: str) -> float:
    """
    Multiplicador de performance por classe.

    Endurance:
    - LMP2 mais rapido
    - GT3 base
    - GT4 mais lento
    """
    category = str(category_id or "").strip().lower()
    cls = str(class_id or "").strip().lower()

    if category != "endurance":
        return 1.0

    if cls == "lmp2":
        return 1.30
    if cls == "gt4":
        return 0.85
    return 1.0


def simulate_segment(
    states: list,
    segment: RaceSegment,
    context: SimulationContext,
    is_championship_deciding: bool = False,
) -> tuple:
    """
    Simula um segmento da corrida.

    Returns:
        (estados atualizados, lista de IncidentResult)
    """
    segment_incidents = []
    active_states = [s for s in states if not s.is_dnf]
    total_active  = len(active_states)

    for state in active_states:
        nearby       = _get_nearby_profiles(state, states)
        pack_position = _pack_position(state.current_position, total_active)

        profile = state.incident_profile or PilotIncidentProfile(
            pilot_id=state.pilot_id,
            consistency=_get_attr(state, "consistencia"),
            aggression=_get_attr(state, "aggression"),
            racecraft=_get_attr(state, "racecraft"),
            experience=_get_attr(state, "experiencia", 50),
            rain_factor=_get_attr(state, "fator_chuva"),
            mental_resistance=_get_attr(state, "resistencia_mental"),
        )

        incident = roll_for_incident(
            pilot_id=state.pilot_id,
            profile=profile,
            nearby_profiles=nearby,
            segment=segment,
            weather=context.weather,
            car_reliability=state.car_reliability,
            tire_wear=state.tire_wear,
            physical_condition=state.physical_condition,
            is_under_pressure=is_championship_deciding,
            position_in_pack=pack_position,
        )

        if incident:
            segment_incidents.append(incident)
            if incident.incident_type == IncidentType.COLLISION:
                _aplicar_consequencias_colisao(incident, states, segment)
                if state.is_dnf:
                    continue
            else:
                state.incidents.append(incident)
                if incident.is_dnf:
                    state.is_dnf      = True
                    state.dnf_segment = segment
                    state.dnf_reason  = incident.description
                    continue

        seg_score  = calculate_segment_score(state, segment, context)
        if (
            incident
            and incident.incident_type != IncidentType.COLLISION
            and not incident.is_dnf
        ):
            seg_score -= incident.positions_lost * 2

        state.cumulative_score += seg_score

        state.segment_results.append(SegmentResult(
            segment=segment,
            position=0,
            segment_score=seg_score,
            cumulative_score=state.cumulative_score,
            tire_wear=state.tire_wear,
            physical_condition=state.physical_condition,
            incident=incident,
        ))

        _apply_tire_degradation(state, context)
        _apply_physical_degradation(state, context)

    # Reordenar
    active_after = [s for s in states if not s.is_dnf]
    active_after.sort(key=lambda x: x.cumulative_score, reverse=True)

    for new_pos, state in enumerate(active_after, 1):
        old_pos = state.current_position
        state.current_position = new_pos
        if state.segment_results:
            state.segment_results[-1].position          = new_pos
            state.segment_results[-1].positions_changed = old_pos - new_pos

    dnf_states = [s for s in states if s.is_dnf]
    for i, state in enumerate(dnf_states):
        state.current_position = len(active_after) + i + 1

    return states, segment_incidents


def simulate_race(
    qualifying_results: list,
    pilots: list,
    teams: dict,
    context: SimulationContext,
) -> list:
    """
    Simula corrida completa com 5 segmentos.

    Args:
        qualifying_results: Resultado da classificação
        pilots: Lista de pilotos com atributos
        teams: dict {pilot_id → equipe}
        context: Contexto da simulação

    Returns:
        list[RaceDriverResult] ordenada por posição final
    """
    ATTR_NAMES = [
        "skill", "consistencia", "consistency", "racecraft",
        "habilidade_largada", "start_skill",
        "gestao_pneus", "tire_management",
        "fitness", "resistencia_mental", "mental_resistance",
        "fator_clutch", "clutch_factor",
        "fator_chuva", "rain_factor",
        "aggression", "agressividade",
        "experiencia", "experience",
        "motivacao",
        "optimism", "smoothness",
    ]

    def _get_pilot_id(p):
        return _get(p, "id", str(id(p)))

    def _resolve_team_for_pilot(pilot_id):
        if pilot_id in teams:
            return teams.get(pilot_id)

        pilot_id_str = str(pilot_id)
        if pilot_id_str in teams:
            return teams.get(pilot_id_str)

        try:
            pilot_id_int = int(pilot_id)
        except (TypeError, ValueError):
            pilot_id_int = None

        if pilot_id_int is not None and pilot_id_int in teams:
            return teams.get(pilot_id_int)

        return None

    pilot_map = {_get_pilot_id(p): p for p in pilots}

    states: list[RaceState] = []

    for quali in qualifying_results:
        pilot = pilot_map.get(quali.pilot_id)
        team = _resolve_team_for_pilot(quali.pilot_id)
        if not pilot or not team:
            continue

        attributes = {}
        for attr in ATTR_NAMES:
            v = _get(pilot, attr, None)
            if v is not None:
                attributes[attr] = v

        profile = PilotIncidentProfile(
            pilot_id=quali.pilot_id,
            consistency=attributes.get("consistencia", attributes.get("consistency", 70)),
            aggression=attributes.get("aggression", attributes.get("agressividade", 50)),
            racecraft=attributes.get("racecraft", 60),
            experience=attributes.get("experiencia", attributes.get("experience", 50)),
            rain_factor=attributes.get("fator_chuva", attributes.get("rain_factor", 50)),
            mental_resistance=attributes.get("resistencia_mental",
                                              attributes.get("mental_resistance", 60)),
        )

        team_stats = _get(team, "stats", {})
        if not isinstance(team_stats, dict):
            team_stats = {}

        class_id = _resolve_team_class(context.category_id, team)
        perf_mult = _class_perf_multiplier(context.category_id, class_id)

        car_reliability = (
            _get(team, "reliability", None)
            or _get(team, "confiabilidade", None)
            or team_stats.get("confiabilidade", 85)
        )
        car_performance_base = (
            _get(team, "car_performance", None)
            or _get(team, "performance", None)
            or 70
        )
        car_performance = _to_float(car_performance_base, 70.0) * perf_mult

        states.append(RaceState(
            pilot_id=quali.pilot_id,
            pilot_name=quali.pilot_name,
            team_id=quali.team_id,
            team_name=quali.team_name,
            class_id=class_id,
            attributes=attributes,
            car_performance=float(car_performance),
            car_reliability=_to_float(car_reliability, 85.0),
            current_position=quali.position,
            incident_profile=profile,
        ))

    states.sort(key=lambda x: x.current_position)

    segments = [
        RaceSegment.START, RaceSegment.EARLY, RaceSegment.MID,
        RaceSegment.LATE, RaceSegment.FINISH,
    ]
    laps_per_segment = max(1, context.total_laps // 5)

    for segment in segments:
        states, _ = simulate_segment(
            states, segment, context,
            is_championship_deciding=context.is_championship_deciding,
        )
        for state in states:
            if not state.is_dnf:
                state.laps_completed += laps_per_segment

    # Volta mais rápida
    active = [s for s in states if not s.is_dnf]
    for state in active:
        avg_score = state.cumulative_score / 5
        consistency = _get_attr(state, "consistencia")
        best_lap_var = random.uniform(0.98, max(0.985, 1.02 - consistency / 500))
        time_modifier = (100 - avg_score) * 30
        state.best_lap_time_ms = context.base_lap_time_ms + time_modifier * best_lap_var

    if active:
        active[0].laps_led = max(1, int(context.total_laps * 0.5))

    # Converter
    results = []
    for state in states:
        grid_pos = next(
            (q.position for q in qualifying_results if q.pilot_id == state.pilot_id),
            state.current_position,
        )
        results.append(RaceDriverResult(
            pilot_id=state.pilot_id,
            pilot_name=state.pilot_name,
            team_id=state.team_id,
            team_name=state.team_name,
            grid_position=grid_pos,
            finish_position=state.current_position,
            class_id=state.class_id,
            positions_gained=grid_pos - state.current_position,
            best_lap_time_ms=state.best_lap_time_ms,
            is_dnf=state.is_dnf,
            dnf_reason=state.dnf_reason,
            dnf_segment=state.dnf_segment,
            laps_completed=state.laps_completed,
            laps_led=state.laps_led,
            incidents_count=len(state.incidents),
            incidents=state.incidents,
            segment_history=state.segment_results,
        ))

    results.sort(key=lambda x: x.finish_position)

    # Marcar volta mais rápida
    finished = [r for r in results if r.best_lap_time_ms > 0 and not r.is_dnf]
    if finished:
        min(finished, key=lambda x: x.best_lap_time_ms).has_fastest_lap = True

    return results
