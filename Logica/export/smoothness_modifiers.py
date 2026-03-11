# Logica/export/smoothness_modifiers.py
"""
Smoothness modifiers used by Module 5 export.
"""

from __future__ import annotations

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_experience_modifier(experiencia: float) -> Modifier:
    """Global experience impact."""
    if experiencia >= 80:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=6.0,
            description=f"Muito experiente ({experiencia:.0f})",
        )
    if experiencia >= 50:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=2.0,
            description=f"Experiencia razoavel ({experiencia:.0f})",
        )
    if experiencia >= 30:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=0.0,
            description=f"Experiencia normal ({experiencia:.0f})",
        )
    if experiencia >= 15:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=-6.0,
            description=f"Pouca experiencia ({experiencia:.0f})",
        )

    return Modifier(
        source=ModifierSource.EXPERIENCE,
        value=-10.0,
        description=f"Muito inexperiente ({experiencia:.0f})",
    )


def calculate_frustration_smoothness(pilot_ctx: PilotContext) -> Modifier:
    """Smoothness loss when driver is frustrated."""
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=0.0,
            description="Sem historico",
        )

    below = 0
    # Usa os 3 resultados mais recentes.
    for result, expected in zip(pilot_ctx.last_5_results[-3:], pilot_ctx.last_5_expected[-3:]):
        if result > expected + 4:
            below += 1

    if below >= 3:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=-6.0,
            description="Frustrado - menos suave",
        )
    if below >= 2:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=-3.0,
            description="Um pouco frustrado",
        )

    return Modifier(
        source=ModifierSource.FRUSTRATION,
        value=0.0,
        description="Sem frustracao",
    )


def calculate_fatigue_modifier(
    race_ctx: RaceContext,
    races_this_season: int,
) -> Modifier:
    """Calendar fatigue impact."""
    value = 0.0
    reasons = []

    if races_this_season > 20:
        value -= 6.0
        reasons.append(f"calendario intenso ({races_this_season} corridas)")
    elif races_this_season > 15:
        value -= 4.0
        reasons.append(f"muitas corridas ({races_this_season})")

    rounds_done = race_ctx.round_number
    if rounds_done > race_ctx.total_rounds - 2:
        value -= 2.0
        reasons.append("reta final da temporada")

    if value == 0:
        return Modifier(
            source=ModifierSource.FATIGUE,
            value=0.0,
            description="Sem fadiga",
        )

    return Modifier(
        source=ModifierSource.FATIGUE,
        value=value,
        description=", ".join(reasons),
    )


def calculate_confidence_modifier(pilot_ctx: PilotContext) -> Modifier:
    """Confidence in category from recent form."""
    if not pilot_ctx.last_5_results:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=0.0,
            description="Sem historico",
        )

    avg_position = sum(pilot_ctx.last_5_results) / len(pilot_ctx.last_5_results)

    if pilot_ctx.championship_position <= 3 and avg_position <= 5:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=5.0,
            description="Dominando a categoria",
        )
    if avg_position <= 10:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=2.0,
            description="Confiante",
        )
    if avg_position > 15:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=-5.0,
            description="Falta de confianca",
        )

    return Modifier(
        source=ModifierSource.CONFIDENCE,
        value=0.0,
        description="Confianca normal",
    )


def calculate_rain_insecurity(
    race_ctx: RaceContext,
    fator_chuva: float,
) -> Modifier:
    """Smoothness loss in wet for low rain skill."""
    if not race_ctx.is_wet:
        return Modifier(
            source=ModifierSource.RAIN_INSECURITY,
            value=0.0,
            description="Pista seca",
        )

    if fator_chuva < 30:
        value = -12.0
        desc = "Muito inseguro na chuva"
    elif fator_chuva < 40:
        value = -10.0
        desc = "Inseguro na chuva"
    elif fator_chuva < 60:
        value = -5.0
        desc = "Desconfortavel na chuva"
    elif fator_chuva < 80:
        value = -2.0
        desc = "OK na chuva"
    else:
        value = 0.0
        desc = "Confiante na chuva"

    return Modifier(
        source=ModifierSource.RAIN_INSECURITY,
        value=value,
        description=desc,
    )


def get_all_smoothness_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    experiencia: float,
    fator_chuva: float,
    races_this_season: int,
) -> list[Modifier]:
    """Return all smoothness modifiers."""
    return [
        calculate_experience_modifier(experiencia),
        calculate_frustration_smoothness(pilot_ctx),
        calculate_fatigue_modifier(race_ctx, races_this_season),
        calculate_confidence_modifier(pilot_ctx),
        calculate_rain_insecurity(race_ctx, fator_chuva),
    ]
