"""
Sistema de Safety Car para simulação.
"""

import random
from .models import RaceSegment, SafetyCarPeriod, IncidentResult, IncidentSeverity


def should_deploy_safety_car(incidents: list) -> bool:
    """
    Determina se deve acionar safety car.
    70% de chance para cada incidente MAJOR/CRITICAL.
    """
    major_incidents = [
        i for i in incidents
        if i.severity in (IncidentSeverity.MAJOR, IncidentSeverity.CRITICAL)
    ]
    if not major_incidents:
        return False
    return any(random.random() < 0.70 for _ in major_incidents)


def calculate_safety_car_laps(total_laps: int) -> int:
    """Calcula quantas voltas o SC fica na pista (2–5)."""
    min_laps = 2
    max_laps = min(5, total_laps // 6)
    return random.randint(min_laps, max(min_laps, max_laps))


def apply_safety_car_effect(pilot_gaps: dict, laps_under_sc: int) -> dict:
    """
    Aplica efeito do safety car nos gaps — compacta o pelotão.

    Args:
        pilot_gaps: {pilot_id → gap_ms}
        laps_under_sc: Voltas sob safety car

    Returns:
        Novos gaps compactados
    """
    if not pilot_gaps:
        return pilot_gaps

    new_gaps = {}
    sorted_pilots = sorted(pilot_gaps.items(), key=lambda x: x[1])

    for i, (pilot_id, _) in enumerate(sorted_pilots):
        new_gaps[pilot_id] = i * random.randint(300, 600)

    return new_gaps


def create_safety_car_period(
    segment: RaceSegment,
    incident: IncidentResult,
    total_laps: int,
) -> SafetyCarPeriod:
    """Cria registro de período de safety car."""
    return SafetyCarPeriod(
        start_segment=segment,
        laps_under_sc=calculate_safety_car_laps(total_laps),
        reason=f"Safety Car due to {incident.incident_type.value}",
        incident_id=incident.incident_id,
    )
