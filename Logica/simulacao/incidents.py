"""
Sistema de incidentes para simulação de corridas.
Determina falhas mecânicas, erros de piloto e colisões.
"""

import random
from dataclasses import dataclass
from typing import Optional
from .models import (
    IncidentType,
    IncidentSeverity,
    IncidentResult,
    RaceSegment,
    WeatherCondition,
)


@dataclass
class PilotIncidentProfile:
    """Perfil de risco de incidente de um piloto."""
    pilot_id: str
    consistency: float
    aggression: float
    racecraft: float
    experience: float
    rain_factor: float
    mental_resistance: float


# Multiplicadores por segmento
SEGMENT_INCIDENT_MULTIPLIERS = {
    RaceSegment.START: {
        "collision":    2.5,
        "driver_error": 1.5,
        "mechanical":   0.5,
    },
    RaceSegment.EARLY: {
        "collision":    1.0,
        "driver_error": 1.0,
        "mechanical":   0.8,
    },
    RaceSegment.MID: {
        "collision":    0.8,
        "driver_error": 1.0,
        "mechanical":   1.0,
    },
    RaceSegment.LATE: {
        "collision":    0.8,
        "driver_error": 1.2,
        "mechanical":   1.2,
    },
    RaceSegment.FINISH: {
        "collision":    1.2,
        "driver_error": 1.5,
        "mechanical":   1.5,
    },
}

BASE_INCIDENT_CHANCES = {
    "mechanical":   0.03,
    "driver_error": 0.08,
    "collision":    0.06,
}


def calculate_mechanical_failure_chance(
    base_chance: float,
    car_reliability: float,
    segment: RaceSegment,
) -> float:
    reliability_modifier = 1.0 - ((car_reliability - 70) / 25 * 0.70)
    segment_mult = SEGMENT_INCIDENT_MULTIPLIERS[segment]["mechanical"]
    return base_chance * reliability_modifier * segment_mult


def calculate_driver_error_chance(
    base_chance: float,
    profile: PilotIncidentProfile,
    segment: RaceSegment,
    weather: WeatherCondition,
    is_under_pressure: bool = False,
    tire_wear: float = 1.0,
    physical_condition: float = 1.0,
) -> float:
    consistency_mod = 1.0 - (profile.consistency / 100 * 0.60)
    experience_mod  = 1.0 - (profile.experience  / 100 * 0.30)

    rain_penalty = 0.0
    if weather != WeatherCondition.DRY:
        rain_base = {
            WeatherCondition.DAMP:       0.30,
            WeatherCondition.WET:        0.60,
            WeatherCondition.HEAVY_RAIN: 1.00,
        }.get(weather, 0.0)
        rain_penalty = rain_base * (1.0 - profile.rain_factor / 100 * 0.80)

    pressure_mod = 1.3 - (profile.mental_resistance / 100 * 0.25) if is_under_pressure else 1.0
    tire_mod     = 1.0 + (1.0 - tire_wear) * 0.5
    fatigue_mod  = 1.0 + (1.0 - physical_condition) * 0.4

    segment_mult = SEGMENT_INCIDENT_MULTIPLIERS[segment]["driver_error"]

    final_chance = (
        base_chance
        * consistency_mod
        * experience_mod
        * (1 + rain_penalty)
        * pressure_mod
        * tire_mod
        * fatigue_mod
        * segment_mult
    )
    return min(final_chance, 0.25)


def calculate_collision_chance(
    base_chance: float,
    profile: PilotIncidentProfile,
    nearby_profiles: list,
    segment: RaceSegment,
    weather: WeatherCondition,
    position_in_pack: str = "midfield",
) -> float:
    aggression_mod = 1.0 + (profile.aggression / 100 * 0.60)
    racecraft_mod  = 1.0 - (profile.racecraft  / 100 * 0.50)

    if nearby_profiles:
        avg_nearby = sum(p.aggression for p in nearby_profiles) / len(nearby_profiles)
        nearby_mod = 1.0 + (avg_nearby / 100 * 0.30)
    else:
        nearby_mod = 1.0

    pack_mod = {"front": 0.7, "midfield": 1.2, "back": 0.9}.get(position_in_pack, 1.0)

    rain_mod = {
        WeatherCondition.DRY:        1.0,
        WeatherCondition.DAMP:       1.2,
        WeatherCondition.WET:        1.4,
        WeatherCondition.HEAVY_RAIN: 1.6,
    }.get(weather, 1.0)

    segment_mult = SEGMENT_INCIDENT_MULTIPLIERS[segment]["collision"]

    final_chance = (
        base_chance
        * aggression_mod
        * racecraft_mod
        * nearby_mod
        * pack_mod
        * rain_mod
        * segment_mult
    )
    return min(final_chance, 0.20)


def determine_incident_severity(
    incident_type: IncidentType,
    segment: RaceSegment,
) -> IncidentSeverity:
    roll = random.random()

    if incident_type == IncidentType.MECHANICAL:
        return IncidentSeverity.MAJOR if roll < 0.85 else IncidentSeverity.MINOR

    if incident_type == IncidentType.DRIVER_ERROR:
        return IncidentSeverity.MAJOR if roll < 0.30 else IncidentSeverity.MINOR

    if incident_type == IncidentType.COLLISION:
        if roll < 0.05:
            return IncidentSeverity.CRITICAL
        if roll < 0.45:
            return IncidentSeverity.MAJOR
        return IncidentSeverity.MINOR

    return IncidentSeverity.MINOR


def calculate_positions_lost(severity: IncidentSeverity) -> int:
    if severity == IncidentSeverity.MINOR:
        return random.randint(1, 4)
    return 0


def check_injury_from_incident(
    incident_type: IncidentType,
    severity: IncidentSeverity,
) -> bool:
    if severity != IncidentSeverity.CRITICAL:
        return False
    return incident_type == IncidentType.COLLISION and random.random() < 0.40


def roll_for_incident(
    pilot_id: str,
    profile: PilotIncidentProfile,
    nearby_profiles: list,
    segment: RaceSegment,
    weather: WeatherCondition,
    car_reliability: float,
    tire_wear: float,
    physical_condition: float,
    is_under_pressure: bool,
    position_in_pack: str,
) -> Optional[IncidentResult]:
    """Rola dados para verificar se ocorre incidente."""
    base_per_segment = {k: v / 5 for k, v in BASE_INCIDENT_CHANCES.items()}

    # 1. Falha mecânica
    mech_chance = calculate_mechanical_failure_chance(
        base_per_segment["mechanical"], car_reliability, segment
    )
    if random.random() < mech_chance:
        severity = determine_incident_severity(IncidentType.MECHANICAL, segment)
        return IncidentResult(
            incident_type=IncidentType.MECHANICAL,
            severity=severity,
            segment=segment,
            positions_lost=0 if severity != IncidentSeverity.MINOR else 2,
            involved_pilots=[pilot_id],
            description=f"Mechanical failure in {segment.value}",
        )

    # 2. Erro do piloto
    error_chance = calculate_driver_error_chance(
        base_per_segment["driver_error"], profile, segment, weather,
        is_under_pressure, tire_wear, physical_condition,
    )
    if random.random() < error_chance:
        severity = determine_incident_severity(IncidentType.DRIVER_ERROR, segment)
        return IncidentResult(
            incident_type=IncidentType.DRIVER_ERROR,
            severity=severity,
            segment=segment,
            positions_lost=calculate_positions_lost(severity),
            involved_pilots=[pilot_id],
            description=f"Driver error in {segment.value}",
        )

    # 3. Colisão
    collision_chance = calculate_collision_chance(
        base_per_segment["collision"], profile, nearby_profiles,
        segment, weather, position_in_pack,
    )
    if random.random() < collision_chance:
        severity = determine_incident_severity(IncidentType.COLLISION, segment)
        causes_injury = check_injury_from_incident(IncidentType.COLLISION, severity)

        other_involved = []
        if nearby_profiles:
            num_others = min(random.randint(1, 2), len(nearby_profiles))
            other_involved = [p.pilot_id for p in random.sample(nearby_profiles, num_others)]

        return IncidentResult(
            incident_type=IncidentType.COLLISION,
            severity=severity,
            segment=segment,
            positions_lost=calculate_positions_lost(severity),
            involved_pilots=[pilot_id] + other_involved,
            description=f"Collision in {segment.value}",
            causes_injury=causes_injury,
        )

    return None
