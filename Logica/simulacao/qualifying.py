"""
Simulação de sessão de classificação.
"""

import random
from .models import QualifyingResult, SimulationContext, WeatherCondition
from .weather import get_rain_skill_penalty, calculate_pilot_rain_penalty


def calculate_quali_score(pilot, team, context: SimulationContext) -> float:
    """
    Calcula score de classificação para um piloto.

    Pesos: skill 40%, ritmo_classificacao 25%, car_performance 25%, track_affinity 10%.
    """
    skill_component = getattr(pilot, "skill", 50) * 0.40
    quali_component = getattr(pilot, "ritmo_classificacao",
                              getattr(pilot, "qualifying_pace", 50)) * 0.25
    car_component   = getattr(team, "car_performance", 60) * 0.25

    try:
        track_affinity = pilot.get_track_affinity(context.track_id)
    except Exception:
        track_affinity = 1.0
    track_component = 50 * track_affinity * 0.10

    base_score = skill_component + quali_component + car_component + track_component

    # Modificador de chuva
    if context.weather != WeatherCondition.DRY:
        rain_penalty  = get_rain_skill_penalty(context.weather)
        rain_factor   = getattr(pilot, "rain_factor", getattr(pilot, "fator_chuva", 50))
        actual_penalty = calculate_pilot_rain_penalty(rain_penalty, rain_factor)
        base_score *= (1 - actual_penalty)

    # Penalidade de inexperiência
    races = getattr(pilot, "races_in_category", None) or getattr(pilot, "corridas_na_categoria", None)
    if races is not None and races < 10:
        base_score *= (1 - (10 - races) * 0.005)

    # Variância por consistência
    consistency   = getattr(pilot, "consistency", getattr(pilot, "consistencia", 70))
    variance_range = (100 - consistency) / 100 * 8
    base_score += random.uniform(-variance_range, variance_range)

    return max(base_score, 10)


def simulate_qualifying(
    pilots: list,
    teams: dict,
    context: SimulationContext,
) -> list:
    """
    Simula sessão de classificação completa.

    Args:
        pilots: Lista de pilotos
        teams: dict {pilot_id → equipe}
        context: Contexto da simulação

    Returns:
        list[QualifyingResult] ordenado por posição
    """
    scored = []

    for pilot in pilots:
        pilot_id = getattr(pilot, "id", pilot.get("id") if isinstance(pilot, dict) else str(id(pilot)))
        team = teams.get(pilot_id)
        if not team:
            continue
        score = calculate_quali_score(pilot, team, context)
        scored.append({"pilot": pilot, "team": team, "score": score, "pilot_id": pilot_id})

    scored.sort(key=lambda x: x["score"], reverse=True)

    pole_score     = scored[0]["score"] if scored else 0
    base_time_ms   = context.base_lap_time_ms
    quali_results  = []

    for position, entry in enumerate(scored, 1):
        score_diff = pole_score - entry["score"]
        time_ms    = base_time_ms + score_diff * 50

        pilot_name = (
            getattr(entry["pilot"], "name", None)
            or getattr(entry["pilot"], "nome", None)
            or str(entry["pilot_id"])
        )
        team_id = getattr(entry["team"], "id", None) or getattr(entry["team"], "nome", str(id(entry["team"])))
        team_name = getattr(entry["team"], "name", None) or getattr(entry["team"], "nome", str(team_id))

        quali_results.append(QualifyingResult(
            pilot_id=entry["pilot_id"],
            pilot_name=pilot_name,
            team_id=str(team_id),
            team_name=str(team_name),
            position=position,
            quali_score=entry["score"],
            best_lap_time_ms=time_ms,
            gap_to_pole_ms=time_ms - base_time_ms,
            is_pole=(position == 1),
        ))

    return quali_results
