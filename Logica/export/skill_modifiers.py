# Logica/export/skill_modifiers.py
"""
Modificadores que afetam o SKILL (velocidade) do piloto.

O skill afeta diretamente a velocidade do carro no iRacing.
Modificadores são aplicados como PORCENTAGEM do skill base.
"""

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_category_familiarity(pilot_ctx: PilotContext) -> Modifier:
    """
    Penalidade por inexperiência na categoria.
    """
    races = pilot_ctx.races_in_category

    if races < 3:
        value = -8.0
        desc = f"Novato na categoria ({races} corridas)"
    elif races < 6:
        value = -5.0
        desc = f"Pouca experiência ({races} corridas)"
    elif races < 10:
        value = -2.0
        desc = f"Adaptando-se ({races} corridas)"
    else:
        value = 0.0
        desc = "Totalmente adaptado"

    return Modifier(
        source=ModifierSource.CATEGORY_FAMILIARITY,
        value=value,
        description=desc
    )


def calculate_track_knowledge(pilot_ctx: PilotContext) -> Modifier:
    """
    Bônus/penalidade por conhecimento do circuito.
    """
    times = pilot_ctx.times_at_track
    best = pilot_ctx.best_result_at_track

    if times == 0:
        value = -6.0
        desc = "Primeira vez nesta pista"
    elif times == 1:
        value = -3.0
        desc = "Pouca experiência na pista"
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
        desc += f" + histórico forte (P{best})"

    return Modifier(
        source=ModifierSource.TRACK_KNOWLEDGE,
        value=value,
        description=desc
    )


def calculate_injury_modifier(pilot_ctx: PilotContext) -> Modifier:
    """
    Penalidade por lesão ativa.
    """
    if not pilot_ctx.has_injury:
        return Modifier(
            source=ModifierSource.INJURY,
            value=0.0,
            description="Sem lesão"
        )

    severity = pilot_ctx.injury_severity

    if severity < 0.3:
        value = -5.0
        desc = f"Lesão leve ({pilot_ctx.injury_races_left} corridas restantes)"
    elif severity < 0.6:
        value = -10.0
        desc = f"Lesão moderada ({pilot_ctx.injury_races_left} corridas restantes)"
    else:
        value = -15.0
        desc = f"Lesão grave ({pilot_ctx.injury_races_left} corridas restantes)"

    return Modifier(
        source=ModifierSource.INJURY,
        value=value,
        description=desc
    )


def calculate_pressure_clutch(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    clutch_factor: float
) -> Modifier:
    """
    Modificador de pressão × clutch factor.
    """
    pressure = 0.0
    pressure_reasons = []

    if race_ctx.is_championship_deciding:
        pressure += 40.0
        pressure_reasons.append("corrida decisiva")

    rounds_left = race_ctx.total_rounds - race_ctx.round_number
    if rounds_left <= 3 and pilot_ctx.championship_position <= 3:
        pressure += 30.0
        pressure_reasons.append("briga pelo título")

    if pilot_ctx.points_to_leader <= 20 and pilot_ctx.championship_position <= 5:
        pressure += 20.0
        pressure_reasons.append("gap pequeno")

    if pressure == 0:
        return Modifier(
            source=ModifierSource.PRESSURE_CLUTCH,
            value=0.0,
            description="Sem pressão significativa"
        )

    # Clutch effect: -1 a +1
    clutch_effect = (clutch_factor - 50) / 50

    # Pressão máxima = ±10%
    max_effect = 10.0
    value = (pressure / 100) * max_effect * clutch_effect

    if value >= 0:
        desc = f"Brilha sob pressão ({', '.join(pressure_reasons)})"
    else:
        desc = f"Afetado pela pressão ({', '.join(pressure_reasons)})"

    return Modifier(
        source=ModifierSource.PRESSURE_CLUTCH,
        value=value,
        description=desc
    )


def calculate_momentum(pilot_ctx: PilotContext) -> Modifier:
    """
    Modificador de momentum baseado nos últimos 5 resultados.
    """
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.MOMENTUM,
            value=0.0,
            description="Sem histórico suficiente"
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
        description=desc
    )


def calculate_rain_skill_modifier(
    race_ctx: RaceContext,
    rain_factor: float
) -> Modifier:
    """
    Penalidade de chuva no skill.
    """
    if not race_ctx.is_wet:
        return Modifier(
            source=ModifierSource.RAIN,
            value=0.0,
            description="Pista seca"
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

    absorption = (rain_factor / 100) * 0.90
    penalty = base_penalty * intensity_mult * (1 - absorption)

    return Modifier(
        source=ModifierSource.RAIN,
        value=-penalty,
        description=f"{rain_desc} (rain skill: {rain_factor:.0f})"
    )


def get_all_skill_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    clutch_factor: float,
    rain_factor: float
) -> list[Modifier]:
    """Retorna todos os modificadores de skill"""
    return [
        calculate_category_familiarity(pilot_ctx),
        calculate_track_knowledge(pilot_ctx),
        calculate_injury_modifier(pilot_ctx),
        calculate_pressure_clutch(pilot_ctx, race_ctx, clutch_factor),
        calculate_momentum(pilot_ctx),
        calculate_rain_skill_modifier(race_ctx, rain_factor)
    ]
