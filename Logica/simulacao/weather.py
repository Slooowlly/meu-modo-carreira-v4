"""
Sistema de clima para simulação.
Determina condições de chuva e seus efeitos.
"""

import random
from .models import WeatherCondition

try:
    from Dados.constantes import CHANCE_CHUVA_BASE
except ImportError:
    CHANCE_CHUVA_BASE = {"_default": 0.10}

DEFAULT_RAIN_CHANCE = CHANCE_CHUVA_BASE.get("_default", 0.10)


def get_track_rain_chance(track_id: int, track_name: str = "") -> float:
    """Retorna probabilidade de chuva para uma pista, usando CHANCE_CHUVA_BASE se disponível."""
    if track_name and track_name in CHANCE_CHUVA_BASE:
        return CHANCE_CHUVA_BASE[track_name]
    return DEFAULT_RAIN_CHANCE


def determine_weather(
    track_id: int,
    force_condition: WeatherCondition = None,
    track_name: str = ""
) -> WeatherCondition:
    """
    Determina condição climática para a corrida.

    Args:
        track_id: ID da pista
        force_condition: Forçar condição específica
        track_name: Nome da pista (para lookup em CHANCE_CHUVA_BASE)

    Returns:
        WeatherCondition resultante
    """
    if force_condition:
        return force_condition

    rain_chance = get_track_rain_chance(track_id, track_name)
    roll = random.random()

    if roll > rain_chance:
        return WeatherCondition.DRY

    intensity_roll = random.random()
    if intensity_roll < 0.40:
        return WeatherCondition.DAMP
    elif intensity_roll < 0.80:
        return WeatherCondition.WET
    else:
        return WeatherCondition.HEAVY_RAIN


def get_weather_modifier(weather: WeatherCondition) -> float:
    """Retorna multiplicador de dificuldade do clima."""
    modifiers = {
        WeatherCondition.DRY:        1.00,
        WeatherCondition.DAMP:       1.15,
        WeatherCondition.WET:        1.35,
        WeatherCondition.HEAVY_RAIN: 1.60,
    }
    return modifiers.get(weather, 1.0)


def get_rain_skill_penalty(weather: WeatherCondition) -> float:
    """
    Penalidade BASE de skill por chuva (0.0–0.18).
    Será reduzida pelo fator_chuva do piloto.
    """
    penalties = {
        WeatherCondition.DRY:        0.00,
        WeatherCondition.DAMP:       0.06,
        WeatherCondition.WET:        0.12,
        WeatherCondition.HEAVY_RAIN: 0.18,
    }
    return penalties.get(weather, 0.0)


def calculate_pilot_rain_penalty(base_penalty: float, rain_factor: float) -> float:
    """
    Calcula penalidade real de chuva para um piloto.

    Args:
        base_penalty: Penalidade base do clima
        rain_factor: Atributo fator_chuva do piloto (0-100)

    Returns:
        Penalidade ajustada (piloto com rain_factor alto sofre menos)
    """
    absorption = rain_factor / 100 * 0.90
    return base_penalty * (1 - absorption)
