# Logica/export/smoothness_modifiers.py
"""
Modificadores que afetam a SUAVIDADE do piloto.

A suavidade afeta:
- Fluidez nas curvas
- Consistência nas trajetórias
- Controle do carro em situações limite
"""

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_experience_modifier(experience: float) -> Modifier:
    """
    Modificador baseado em experiência geral.
    """
    if experience >= 80:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=6.0,
            description=f"Muito experiente ({experience:.0f})"
        )
    elif experience >= 50:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=2.0,
            description=f"Experiência razoável ({experience:.0f})"
        )
    elif experience >= 30:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=0.0,
            description=f"Experiência normal ({experience:.0f})"
        )
    elif experience >= 15:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=-6.0,
            description=f"Pouca experiência ({experience:.0f})"
        )
    else:
        return Modifier(
            source=ModifierSource.EXPERIENCE,
            value=-10.0,
            description=f"Muito inexperiente ({experience:.0f})"
        )


def calculate_frustration_smoothness(pilot_ctx: PilotContext) -> Modifier:
    """
    Redução de suavidade por frustração.
    """
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=0.0,
            description="Sem histórico"
        )

    below = 0
    for result, expected in zip(pilot_ctx.last_5_results[:3], pilot_ctx.last_5_expected[:3]):
        if result > expected + 4:
            below += 1

    if below >= 3:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=-6.0,
            description="Frustrado - menos suave"
        )
    elif below >= 2:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=-3.0,
            description="Um pouco frustrado"
        )

    return Modifier(
        source=ModifierSource.FRUSTRATION,
        value=0.0,
        description="Sem frustração"
    )


def calculate_fatigue_modifier(
    race_ctx: RaceContext,
    races_this_season: int
) -> Modifier:
    """
    Redução de suavidade por fadiga do calendário.
    """
    value = 0.0
    reasons = []

    if races_this_season > 20:
        value -= 6.0
        reasons.append(f"calendário intenso ({races_this_season} corridas)")
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
            description="Sem fadiga"
        )

    return Modifier(
        source=ModifierSource.FATIGUE,
        value=value,
        description=", ".join(reasons)
    )


def calculate_confidence_modifier(pilot_ctx: PilotContext) -> Modifier:
    """
    Modificador de confiança na categoria.
    """
    if not pilot_ctx.last_5_results:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=0.0,
            description="Sem histórico"
        )

    avg_position = sum(pilot_ctx.last_5_results) / len(pilot_ctx.last_5_results)

    if pilot_ctx.championship_position <= 3 and avg_position <= 5:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=5.0,
            description="Dominando a categoria"
        )
    elif avg_position <= 10:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=2.0,
            description="Confiante"
        )
    elif avg_position > 15:
        return Modifier(
            source=ModifierSource.CONFIDENCE,
            value=-5.0,
            description="Falta de confiança"
        )

    return Modifier(
        source=ModifierSource.CONFIDENCE,
        value=0.0,
        description="Confiança normal"
    )


def calculate_rain_insecurity(
    race_ctx: RaceContext,
    rain_factor: float
) -> Modifier:
    """
    Redução de suavidade na chuva para pilotos inseguros.
    """
    if not race_ctx.is_wet:
        return Modifier(
            source=ModifierSource.RAIN_INSECURITY,
            value=0.0,
            description="Pista seca"
        )

    if rain_factor < 30:
        value = -12.0
        desc = "Muito inseguro na chuva"
    elif rain_factor < 40:
        value = -10.0
        desc = "Inseguro na chuva"
    elif rain_factor < 60:
        value = -5.0
        desc = "Desconfortável na chuva"
    elif rain_factor < 80:
        value = -2.0
        desc = "OK na chuva"
    else:
        value = 0.0
        desc = "Confiante na chuva"

    return Modifier(
        source=ModifierSource.RAIN_INSECURITY,
        value=value,
        description=desc
    )


def get_all_smoothness_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    experience: float,
    rain_factor: float,
    races_this_season: int
) -> list[Modifier]:
    """Retorna todos os modificadores de suavidade"""
    return [
        calculate_experience_modifier(experience),
        calculate_frustration_smoothness(pilot_ctx),
        calculate_fatigue_modifier(race_ctx, races_this_season),
        calculate_confidence_modifier(pilot_ctx),
        calculate_rain_insecurity(race_ctx, rain_factor)
    ]
