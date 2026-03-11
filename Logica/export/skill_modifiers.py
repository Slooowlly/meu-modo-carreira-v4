# Logica/export/skill_modifiers.py
"""
Skill modifiers used by Module 5 export.

All values here are percentage deltas applied over base skill.
"""

from __future__ import annotations

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_category_familiarity(pilot_ctx: PilotContext) -> Modifier:
    """Penalty for low experience in current category."""
    races = pilot_ctx.races_in_category

    if races < 3:
        value = -8.0
        desc = f"Novato na categoria ({races} corridas)"
    elif races < 6:
        value = -5.0
        desc = f"Pouca experiencia ({races} corridas)"
    elif races < 10:
        value = -2.0
        desc = f"Adaptando-se ({races} corridas)"
    else:
        value = 0.0
        desc = "Totalmente adaptado"

    return Modifier(
        source=ModifierSource.CATEGORY_FAMILIARITY,
        value=value,
        description=desc,
    )


def calculate_track_knowledge(pilot_ctx: PilotContext) -> Modifier:
    """Bonus or penalty from circuit history."""
    times = pilot_ctx.times_at_track
    best = pilot_ctx.best_result_at_track

    if times == 0:
        value = -6.0
        desc = "Primeira vez nesta pista"
    elif times == 1:
        value = -3.0
        desc = "Pouca experiencia na pista"
    elif times <= 3:
        value = 0.0
        desc = "Conhece a pista"
    elif times <= 5:
        value = 2.0
        desc = "Experiente na pista"
    else:
        value = 4.0
        desc = f"Especialista ({times} corridas aqui)"

    if best <= 3 and times > 0:
        value += 2.0
        desc += f" + historico forte (P{best})"

    return Modifier(
        source=ModifierSource.TRACK_KNOWLEDGE,
        value=value,
        description=desc,
    )


def calculate_injury_modifier(pilot_ctx: PilotContext) -> Modifier:
    """
    Injury modifier.

    M4 is the source of truth:
    - modifier -0.05 -> -5.0
    - modifier -0.15 -> -15.0
    - modifier -0.30 -> -30.0
    """
    if not pilot_ctx.has_injury:
        return Modifier(
            source=ModifierSource.INJURY,
            value=0.0,
            description="Sem lesao",
        )

    severity = max(0.0, min(1.0, float(pilot_ctx.injury_severity or 0.0)))
    value = -(severity * 100.0)
    desc = (
        f"Lesao ativa ({value:.1f}% no skill, "
        f"{pilot_ctx.injury_races_left} corridas restantes)"
    )

    return Modifier(
        source=ModifierSource.INJURY,
        value=value,
        description=desc,
    )


def calculate_pressure_clutch(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    fator_clutch: float,
) -> Modifier:
    """Pressure x clutch interaction."""
    pressure = 0.0
    pressure_reasons = []

    if race_ctx.is_championship_deciding:
        pressure += 40.0
        pressure_reasons.append("corrida decisiva")

    rounds_left = race_ctx.total_rounds - race_ctx.round_number
    if rounds_left <= 3 and pilot_ctx.championship_position <= 3:
        pressure += 30.0
        pressure_reasons.append("briga pelo titulo")

    if pilot_ctx.points_to_leader <= 20 and pilot_ctx.championship_position <= 5:
        pressure += 20.0
        pressure_reasons.append("gap pequeno")

    if pressure == 0:
        return Modifier(
            source=ModifierSource.PRESSURE_CLUTCH,
            value=0.0,
            description="Sem pressao significativa",
        )

    clutch_effect = (fator_clutch - 50) / 50
    max_effect = 10.0
    value = (pressure / 100) * max_effect * clutch_effect

    if value >= 0:
        desc = f"Brilha sob pressao ({', '.join(pressure_reasons)})"
    else:
        desc = f"Afetado pela pressao ({', '.join(pressure_reasons)})"

    return Modifier(
        source=ModifierSource.PRESSURE_CLUTCH,
        value=value,
        description=desc,
    )


def calculate_momentum(pilot_ctx: PilotContext) -> Modifier:
    """Momentum from last 5 races versus expected."""
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.MOMENTUM,
            value=0.0,
            description="Sem historico suficiente",
        )

    above = 0
    below = 0

    for result, expected in zip(pilot_ctx.last_5_results, pilot_ctx.last_5_expected):
        if result < expected - 2:
            above += 1
        elif result > expected + 2:
            below += 1

    if above >= 3:
        value = 4.0
        desc = f"Em grande fase ({above}/5 acima das expectativas)"
    elif above >= 2:
        value = 2.0
        desc = f"Momentum positivo ({above}/5 acima)"
    elif below >= 3:
        value = -4.0
        desc = f"Fase ruim ({below}/5 abaixo das expectativas)"
    elif below >= 2:
        value = -2.0
        desc = f"Momentum negativo ({below}/5 abaixo)"
    else:
        value = 0.0
        desc = "Resultados dentro do esperado"

    return Modifier(
        source=ModifierSource.MOMENTUM,
        value=value,
        description=desc,
    )


def calculate_rain_skill_modifier(
    race_ctx: RaceContext,
    fator_chuva: float,
) -> Modifier:
    """Rain penalty in skill."""
    if not race_ctx.is_wet:
        return Modifier(
            source=ModifierSource.RAIN,
            value=0.0,
            description="Pista seca",
        )

    base_penalty = 12.0

    if race_ctx.rain_intensity < 0.3:
        intensity_mult = 0.5
        rain_desc = "Chuva leve"
    elif race_ctx.rain_intensity < 0.7:
        intensity_mult = 1.0
        rain_desc = "Chuva moderada"
    else:
        intensity_mult = 1.5
        rain_desc = "Chuva forte"

    absorption = (fator_chuva / 100) * 0.90
    penalty = base_penalty * intensity_mult * (1 - absorption)

    return Modifier(
        source=ModifierSource.RAIN,
        value=-penalty,
        description=f"{rain_desc} (fator chuva: {fator_chuva:.0f})",
    )


def get_all_skill_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    fator_clutch: float,
    fator_chuva: float,
) -> list[Modifier]:
    """Return all skill modifiers."""
    return [
        calculate_category_familiarity(pilot_ctx),
        calculate_track_knowledge(pilot_ctx),
        calculate_injury_modifier(pilot_ctx),
        calculate_pressure_clutch(pilot_ctx, race_ctx, fator_clutch),
        calculate_momentum(pilot_ctx),
        calculate_rain_skill_modifier(race_ctx, fator_chuva),
    ]
