# Logica/export/aggression_modifiers.py
"""
Modificadores que afetam a AGRESSIVIDADE do piloto.

A agressividade afeta:
- Tentativas de ultrapassagem
- Comportamento em disputas
- Risco assumido em freadas
"""

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_frustration(pilot_ctx: PilotContext) -> Modifier:
    """
    Aumento de agressividade por frustração.
    """
    if not pilot_ctx.last_5_results:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=0.0,
            description="Sem histórico"
        )

    value = 0.0
    reasons = []

    recent = pilot_ctx.last_5_results[:3]
    expected = pilot_ctx.last_5_expected[:3] if pilot_ctx.last_5_expected else [15, 15, 15]

    bad_results = sum(1 for r, e in zip(recent, expected) if r > e + 5)

    if bad_results >= 3:
        value += 12.0
        reasons.append("3 resultados ruins seguidos")
    elif bad_results >= 2:
        value += 8.0
        reasons.append("2 resultados ruins")
    elif bad_results >= 1:
        value += 4.0
        reasons.append("resultado recente ruim")

    if pilot_ctx.dnf_in_last_race:
        value += 6.0
        reasons.append("DNF na última corrida")

    if value == 0:
        return Modifier(
            source=ModifierSource.FRUSTRATION,
            value=0.0,
            description="Sem frustração"
        )

    return Modifier(
        source=ModifierSource.FRUSTRATION,
        value=value,
        description=", ".join(reasons)
    )


def calculate_rivalry(pilot_ctx: PilotContext, race_ctx: RaceContext) -> Modifier:
    """
    Aumento de agressividade por rivalidade.
    """
    if not pilot_ctx.rivals_in_race:
        return Modifier(
            source=ModifierSource.RIVALRY,
            value=0.0,
            description="Sem rivais na corrida"
        )

    total_value = 0.0

    for rival_id in pilot_ctx.rivals_in_race:
        intensity = 50  # Default
        for r1, r2, i in race_ctx.active_rivalries:
            if (r1 == pilot_ctx.pilot_id and r2 == rival_id) or \
               (r2 == pilot_ctx.pilot_id and r1 == rival_id):
                intensity = i
                break

        mod = 5 + (intensity / 100) * 10
        total_value += mod

    total_value = min(total_value, 20.0)

    return Modifier(
        source=ModifierSource.RIVALRY,
        value=total_value,
        description=f"{len(pilot_ctx.rivals_in_race)} rival(is) na corrida"
    )


def calculate_nothing_to_lose(pilot_ctx: PilotContext) -> Modifier:
    """
    Aumento de agressividade quando não tem nada a perder.
    """
    if pilot_ctx.is_eliminated:
        return Modifier(
            source=ModifierSource.NOTHING_TO_LOSE,
            value=10.0,
            description="Matematicamente eliminado do título"
        )

    return Modifier(
        source=ModifierSource.NOTHING_TO_LOSE,
        value=0.0,
        description="Ainda na briga"
    )


def calculate_contract_desperation(pilot_ctx: PilotContext) -> Modifier:
    """
    Aumento de agressividade por desespero contratual.
    """
    if not pilot_ctx.is_in_contract_year:
        return Modifier(
            source=ModifierSource.CONTRACT_DESPERATION,
            value=0.0,
            description="Contrato seguro"
        )

    if pilot_ctx.team_performance_vs_expectations < 0.8:
        return Modifier(
            source=ModifierSource.CONTRACT_DESPERATION,
            value=8.0,
            description="Último ano + abaixo das expectativas"
        )

    return Modifier(
        source=ModifierSource.CONTRACT_DESPERATION,
        value=5.0,
        description="Último ano de contrato"
    )


def calculate_home_race(pilot_ctx: PilotContext) -> Modifier:
    """
    Aumento de agressividade em corrida em casa.
    """
    if not pilot_ctx.is_home_race:
        return Modifier(
            source=ModifierSource.HOME_RACE,
            value=0.0,
            description="Não é corrida em casa"
        )

    return Modifier(
        source=ModifierSource.HOME_RACE,
        value=4.0,
        description="Corrida em casa - quer impressionar"
    )


def calculate_chasing_leader(pilot_ctx: PilotContext, race_ctx: RaceContext) -> Modifier:
    """
    Aumento de agressividade perseguindo o líder.
    """
    rounds_left = race_ctx.total_rounds - race_ctx.round_number

    if rounds_left > 4:
        return Modifier(
            source=ModifierSource.CHASING_LEADER,
            value=0.0,
            description="Muitas corridas restantes"
        )

    if pilot_ctx.championship_position not in [2, 3]:
        return Modifier(
            source=ModifierSource.CHASING_LEADER,
            value=0.0,
            description="Não está perseguindo o líder"
        )

    value = 3.0
    desc = f"P{pilot_ctx.championship_position} no campeonato"

    if pilot_ctx.points_to_leader <= 15:
        value += 2.0
        desc += f", apenas {pilot_ctx.points_to_leader} pts do líder"

    return Modifier(
        source=ModifierSource.CHASING_LEADER,
        value=value,
        description=desc
    )


def get_all_aggression_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext
) -> list[Modifier]:
    """Retorna todos os modificadores de agressividade"""
    return [
        calculate_frustration(pilot_ctx),
        calculate_rivalry(pilot_ctx, race_ctx),
        calculate_nothing_to_lose(pilot_ctx),
        calculate_contract_desperation(pilot_ctx),
        calculate_home_race(pilot_ctx),
        calculate_chasing_leader(pilot_ctx, race_ctx)
    ]
