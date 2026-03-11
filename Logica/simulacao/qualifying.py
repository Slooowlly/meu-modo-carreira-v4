"""
Simulacao de sessao de classificacao.
"""

from __future__ import annotations

import random
from typing import Any

from .models import QualifyingResult, SimulationContext, WeatherCondition
from .weather import calculate_pilot_rain_penalty, get_rain_skill_penalty


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


def _normalize_track_affinity(raw_value) -> float:
    """
    Normaliza afinidade de pista para fator 0.5-1.5.

    Aceita:
    - fator direto (0.5-1.5)
    - percentual (0-100), onde 50 = neutro (1.0)
    """
    value = _to_float(raw_value, 1.0)
    if value <= 2.0:
        return max(0.5, min(1.5, value))
    return max(0.5, min(1.5, 0.5 + (value / 100.0)))


def _resolve_track_affinity(pilot: Any, track_id: int) -> float:
    """
    Resolve afinidade do piloto na pista.

    Prioridade:
    1) metodo get_track_affinity(track_id)
    2) historico_circuitos[track_id]["afinidade"]
    3) campo direto afinidade_circuito/track_affinity
    """
    getter = getattr(pilot, "get_track_affinity", None)
    if callable(getter):
        try:
            return _normalize_track_affinity(getter(track_id))
        except Exception:
            pass

    historical = _get(pilot, "historico_circuitos", {})
    if isinstance(historical, dict):
        for key in (track_id, str(track_id)):
            record = historical.get(key)
            if isinstance(record, dict) and "afinidade" in record:
                return _normalize_track_affinity(record.get("afinidade"))

    direct = _get_first(pilot, ("afinidade_circuito", "track_affinity"), None)
    if direct is not None:
        return _normalize_track_affinity(direct)

    return 1.0


def _resolve_team_for_pilot(teams: dict, pilot_id):
    """Busca equipe por pilot_id com fallback de tipo (int/str)."""
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


def calculate_quali_score(pilot, team, context: SimulationContext) -> float:
    """
    Calcula score de classificacao para um piloto.

    Pesos: skill 40%, ritmo_classificacao 25%, car_performance 25%, track_affinity 10%.
    """
    skill_component = _to_float(_get(pilot, "skill", 50), 50) * 0.40
    quali_raw = _get_first(pilot, ("ritmo_classificacao", "qualifying_pace"), 50)
    quali_component = _to_float(quali_raw, 50) * 0.25
    car_component = _to_float(_get(team, "car_performance", 60), 60) * 0.25

    track_affinity = _resolve_track_affinity(pilot, int(context.track_id))
    track_component = 50 * track_affinity * 0.10

    base_score = skill_component + quali_component + car_component + track_component

    # Modificador de chuva
    if context.weather != WeatherCondition.DRY:
        rain_penalty = get_rain_skill_penalty(context.weather)
        rain_factor = _to_float(_get_first(pilot, ("fator_chuva", "rain_factor"), 50), 50)
        actual_penalty = calculate_pilot_rain_penalty(rain_penalty, rain_factor)
        base_score *= (1 - actual_penalty)

    # Penalidade de inexperiencia
    races = _get_first(pilot, ("corridas_na_categoria", "races_in_category"), None)
    if races is not None:
        try:
            races_int = int(races)
        except (TypeError, ValueError):
            races_int = 10
        if races_int < 10:
            base_score *= (1 - (10 - races_int) * 0.005)

    # Variancia por consistencia
    consistency = _to_float(_get_first(pilot, ("consistencia", "consistency"), 70), 70)
    variance_range = (100 - consistency) / 100 * 8
    base_score += random.uniform(-variance_range, variance_range)

    return max(base_score, 10)


def simulate_qualifying(
    pilots: list,
    teams: dict,
    context: SimulationContext,
) -> list:
    """
    Simula sessao de classificacao completa.

    Args:
        pilots: Lista de pilotos
        teams: dict {pilot_id -> equipe}
        context: Contexto da simulacao

    Returns:
        list[QualifyingResult] ordenado por posicao
    """
    scored = []

    for pilot in pilots:
        pilot_id = _get_first(pilot, ("id",), str(id(pilot)))
        team = _resolve_team_for_pilot(teams, pilot_id)
        if not team:
            continue
        score = calculate_quali_score(pilot, team, context)
        scored.append({"pilot": pilot, "team": team, "score": score, "pilot_id": pilot_id})

    scored.sort(key=lambda x: x["score"], reverse=True)

    pole_score = scored[0]["score"] if scored else 0
    base_time_ms = context.base_lap_time_ms
    quali_results = []

    for position, entry in enumerate(scored, 1):
        score_diff = pole_score - entry["score"]
        time_ms = base_time_ms + score_diff * 50

        pilot_name = str(_get_first(entry["pilot"], ("name", "nome"), str(entry["pilot_id"])))
        team_id = _get_first(entry["team"], ("id", "nome"), str(id(entry["team"])))
        team_name = str(_get_first(entry["team"], ("name", "nome"), str(team_id)))

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
