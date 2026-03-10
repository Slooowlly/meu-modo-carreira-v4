"""
Simulação de corrida com 5 segmentos.
Motor principal de simulação.
"""

import random
from dataclasses import dataclass, field
from typing import Optional

from .models import (
    RaceSegment,
    RaceDriverResult,
    SegmentResult,
    QualifyingResult,
    SimulationContext,
    WeatherCondition,
    IncidentResult,
)
from .incidents import PilotIncidentProfile, roll_for_incident
from .weather import get_rain_skill_penalty, calculate_pilot_rain_penalty


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
        "clutch_factor":       0.20,
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
        "gestao_pneus":       ["tire_management"],
        "resistencia_mental": ["mental_resistance"],
        "clutch_factor":      ["fator_clutch"],
        "rain_factor":        ["fator_chuva"],
        "agressividade":      ["aggression"],
        "consistencia":       ["consistency"],
    }
    value = state.attributes.get(attr_name)
    if value is not None:
        return float(value)
    for alias in aliases.get(attr_name, []):
        value = state.attributes.get(alias)
        if value is not None:
            return float(value)
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
        rain_factor  = _get_attr(state, "rain_factor")
        score *= (1 - calculate_pilot_rain_penalty(rain_penalty, rain_factor))

    # Variância por consistência
    consistency    = _get_attr(state, "consistencia")
    variance_range = (100 - consistency) / 100 * 5
    score += random.uniform(-variance_range, variance_range)

    return max(score, 5.0)


def _apply_tire_degradation(state: RaceState, context: SimulationContext):
    tire_mgmt    = _get_attr(state, "gestao_pneus")
    mgmt_factor  = 1.0 - (tire_mgmt / 100 * 0.50)
    actual_deg   = context.tire_degradation_rate * mgmt_factor
    state.tire_wear = max(0.1, state.tire_wear - actual_deg)


def _apply_physical_degradation(state: RaceState, context: SimulationContext):
    fitness      = _get_attr(state, "fitness")
    fit_factor   = 1.0 - (fitness / 100 * 0.60)
    actual_deg   = context.physical_degradation_rate * fit_factor
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


def _pack_position(position: int, total: int) -> str:
    third = total / 3
    if position <= third:
        return "front"
    if position <= third * 2:
        return "midfield"
    return "back"


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
            aggression=_get_attr(state, "agressividade"),
            racecraft=_get_attr(state, "racecraft"),
            experience=_get_attr(state, "experience", 50),
            rain_factor=_get_attr(state, "rain_factor"),
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
            state.incidents.append(incident)
            segment_incidents.append(incident)
            if incident.is_dnf:
                state.is_dnf      = True
                state.dnf_segment = segment
                state.dnf_reason  = incident.description
                continue

        seg_score  = calculate_segment_score(state, segment, context)
        if incident and not incident.is_dnf:
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
        "clutch_factor", "fator_clutch",
        "rain_factor", "fator_chuva",
        "agressividade", "aggression",
        "experience",
    ]

    def _get_pilot_id(p):
        return (getattr(p, "id", None) or
                (p.get("id") if isinstance(p, dict) else None) or
                str(id(p)))

    pilot_map = {_get_pilot_id(p): p for p in pilots}

    states: list[RaceState] = []

    for quali in qualifying_results:
        pilot = pilot_map.get(quali.pilot_id)
        team  = teams.get(quali.pilot_id)
        if not pilot or not team:
            continue

        attributes = {}
        for attr in ATTR_NAMES:
            if isinstance(pilot, dict):
                v = pilot.get(attr)
            else:
                v = getattr(pilot, attr, None)
            if v is not None:
                attributes[attr] = v

        profile = PilotIncidentProfile(
            pilot_id=quali.pilot_id,
            consistency=attributes.get("consistencia", attributes.get("consistency", 70)),
            aggression=attributes.get("agressividade", attributes.get("aggression", 50)),
            racecraft=attributes.get("racecraft", 60),
            experience=attributes.get("experience", 50),
            rain_factor=attributes.get("rain_factor", attributes.get("fator_chuva", 50)),
            mental_resistance=attributes.get("resistencia_mental",
                                              attributes.get("mental_resistance", 60)),
        )

        car_reliability = (
            getattr(team, "reliability", None)
            or (team.get("reliability") if isinstance(team, dict) else None)
            or (team.get("stats", {}).get("confiabilidade", 85) if isinstance(team, dict) else 85)
        )
        car_performance = (
            getattr(team, "car_performance", None)
            or (team.get("car_performance") if isinstance(team, dict) else None)
            or 70
        )

        states.append(RaceState(
            pilot_id=quali.pilot_id,
            pilot_name=quali.pilot_name,
            team_id=quali.team_id,
            team_name=quali.team_name,
            attributes=attributes,
            car_performance=float(car_performance),
            car_reliability=float(car_reliability),
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
