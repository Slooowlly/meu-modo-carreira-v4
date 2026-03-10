# Logica/export/optimism_modifiers.py
"""
Modificadores que afetam o OTIMISMO do piloto.

O otimismo afeta:
- Disposição para arriscar ultrapassagens
- Comportamento conservador vs agressivo
- Reação a situações adversas
"""

from .models import Modifier, ModifierSource, PilotContext, RaceContext


def calculate_positive_momentum(pilot_ctx: PilotContext) -> Modifier:
    """
    Aumento de otimismo por momentum positivo.
    """
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.POSITIVE_MOMENTUM,
            value=0.0,
            description="Sem histórico"
        )

    above = 0
    for result, expected in zip(pilot_ctx.last_5_results[:5], pilot_ctx.last_5_expected[:5]):
        if result < expected - 2:
            above += 1

    if above >= 3:
        return Modifier(
            source=ModifierSource.POSITIVE_MOMENTUM,
            value=6.0,
            description=f"Em grande fase ({above} ótimos resultados)"
        )
    elif above >= 2:
        return Modifier(
            source=ModifierSource.POSITIVE_MOMENTUM,
            value=3.0,
            description=f"Momentum positivo ({above} bons resultados)"
        )

    return Modifier(
        source=ModifierSource.POSITIVE_MOMENTUM,
        value=0.0,
        description="Resultados normais"
    )


def calculate_negative_momentum(pilot_ctx: PilotContext) -> Modifier:
    """
    Redução de otimismo por momentum negativo.
    """
    if not pilot_ctx.last_5_results or not pilot_ctx.last_5_expected:
        return Modifier(
            source=ModifierSource.NEGATIVE_MOMENTUM,
            value=0.0,
            description="Sem histórico"
        )

    below = 0
    for result, expected in zip(pilot_ctx.last_5_results[:5], pilot_ctx.last_5_expected[:5]):
        if result > expected + 3:
            below += 1

    if below >= 3:
        return Modifier(
            source=ModifierSource.NEGATIVE_MOMENTUM,
            value=-8.0,
            description=f"Fase muito ruim ({below} resultados ruins)"
        )
    elif below >= 2:
        return Modifier(
            source=ModifierSource.NEGATIVE_MOMENTUM,
            value=-4.0,
            description=f"Momentum negativo ({below} resultados abaixo)"
        )

    return Modifier(
        source=ModifierSource.NEGATIVE_MOMENTUM,
        value=0.0,
        description="Sem momentum negativo"
    )


def calculate_rookie_modifier(pilot_ctx: PilotContext) -> Modifier:
    """
    Redução de otimismo para rookies.
    """
    if pilot_ctx.is_rookie or pilot_ctx.seasons_in_category == 0:
        return Modifier(
            source=ModifierSource.ROOKIE_IN_CATEGORY,
            value=-8.0,
            description="Rookie - ainda inseguro"
        )

    if pilot_ctx.seasons_in_category == 1:
        return Modifier(
            source=ModifierSource.ROOKIE_IN_CATEGORY,
            value=-4.0,
            description="Segunda temporada - ainda aprendendo"
        )

    if pilot_ctx.races_in_category < 5:
        return Modifier(
            source=ModifierSource.ROOKIE_IN_CATEGORY,
            value=-5.0,
            description="Pouca experiência na categoria"
        )

    return Modifier(
        source=ModifierSource.ROOKIE_IN_CATEGORY,
        value=0.0,
        description="Experiente na categoria"
    )


def calculate_post_dnf(pilot_ctx: PilotContext) -> Modifier:
    """
    Redução de otimismo após DNF.
    """
    if not pilot_ctx.dnf_in_last_race:
        return Modifier(
            source=ModifierSource.POST_DNF,
            value=0.0,
            description="Sem DNF recente"
        )

    if pilot_ctx.dnf_was_collision:
        return Modifier(
            source=ModifierSource.POST_DNF,
            value=-6.0,
            description="DNF por colisão na última corrida"
        )

    return Modifier(
        source=ModifierSource.POST_DNF,
        value=-3.0,
        description="DNF na última corrida"
    )


def calculate_championship_leader(pilot_ctx: PilotContext) -> Modifier:
    """
    Redução de otimismo do líder (mais conservador).
    """
    if pilot_ctx.championship_position == 1:
        return Modifier(
            source=ModifierSource.CHAMPIONSHIP_LEADER,
            value=-4.0,
            description="Líder do campeonato - conservador"
        )

    return Modifier(
        source=ModifierSource.CHAMPIONSHIP_LEADER,
        value=0.0,
        description="Não é líder"
    )


def calculate_championship_chaser(pilot_ctx: PilotContext, race_ctx: RaceContext) -> Modifier:
    """
    Aumento de otimismo do perseguidor.
    """
    if pilot_ctx.championship_position not in [2, 3]:
        return Modifier(
            source=ModifierSource.CHAMPIONSHIP_CHASER,
            value=0.0,
            description="Não está perseguindo"
        )

    value = 5.0
    desc = f"P{pilot_ctx.championship_position} - precisa arriscar"

    if pilot_ctx.points_to_leader <= 10:
        value += 2.0
        desc += ", muito perto do líder"

    return Modifier(
        source=ModifierSource.CHAMPIONSHIP_CHASER,
        value=value,
        description=desc
    )


def calculate_veteran_modifier(pilot_ctx: PilotContext) -> Modifier:
    """
    Bônus de otimismo para veteranos.
    """
    if pilot_ctx.is_veteran or pilot_ctx.seasons_in_category >= 5:
        return Modifier(
            source=ModifierSource.VETERAN,
            value=4.0,
            description="Veterano experiente"
        )

    return Modifier(
        source=ModifierSource.VETERAN,
        value=0.0,
        description="Não é veterano"
    )


def get_all_optimism_modifiers(
    pilot_ctx: PilotContext,
    race_ctx: RaceContext
) -> list[Modifier]:
    """Retorna todos os modificadores de otimismo"""
    return [
        calculate_positive_momentum(pilot_ctx),
        calculate_negative_momentum(pilot_ctx),
        calculate_rookie_modifier(pilot_ctx),
        calculate_post_dnf(pilot_ctx),
        calculate_championship_leader(pilot_ctx),
        calculate_championship_chaser(pilot_ctx, race_ctx),
        calculate_veteran_modifier(pilot_ctx)
    ]
