"""
Sistema de aposentadoria.

Regras:
- Idade 38+: 15% chance por temporada
- Idade 40+: 30% chance
- Idade 42+: 50% chance
- Motivacao < 20 por 2 temporadas seguidas: aposenta
- Lesao grave: chance de aposentadoria forcada
"""

import random
from typing import Optional

from .models import AposentadoriaCausa, LesaoTipo


CHANCE_APOSENTADORIA_IDADE = {
    38: 0.15,
    39: 0.20,
    40: 0.30,
    41: 0.40,
    42: 0.50,
    43: 0.60,
    44: 0.70,
    45: 0.85,
    46: 0.95,
    47: 1.00,
}

MOTIVACAO_BAIXA_THRESHOLD = 20.0
TEMPORADAS_MOTIVACAO_BAIXA = 2

CHANCE_APOSENTADORIA_LESAO_GRAVE = 0.40


def _to_lesao_tipo(valor) -> LesaoTipo:
    if isinstance(valor, LesaoTipo):
        return valor
    if isinstance(valor, str):
        chave = valor.strip().lower()
        for item in LesaoTipo:
            if item.value == chave:
                return item
    return LesaoTipo.NENHUMA


def verificar_aposentadoria_idade(idade: int) -> tuple[bool, float]:
    """
    Verifica aposentadoria por idade.
    """
    if idade < 38:
        return False, 0.0

    chance = 0.0
    for idade_ref, chance_ref in sorted(CHANCE_APOSENTADORIA_IDADE.items()):
        if idade >= idade_ref:
            chance = chance_ref

    aposentou = random.random() < chance
    return aposentou, chance


def verificar_aposentadoria_motivacao(
    motivacao_atual: float,
    temporadas_com_motivacao_baixa: int,
) -> bool:
    """
    Verifica aposentadoria por motivacao baixa.
    """
    if motivacao_atual >= MOTIVACAO_BAIXA_THRESHOLD:
        return False
    return temporadas_com_motivacao_baixa >= TEMPORADAS_MOTIVACAO_BAIXA


def verificar_aposentadoria_lesao(lesao_tipo: LesaoTipo) -> bool:
    """
    Verifica aposentadoria por lesao grave.
    """
    if lesao_tipo != LesaoTipo.GRAVE:
        return False
    return random.random() < CHANCE_APOSENTADORIA_LESAO_GRAVE


def verificar_aposentadoria(
    idade: int,
    motivacao: float,
    temporadas_motivacao_baixa: int,
    lesao_tipo: LesaoTipo = LesaoTipo.NENHUMA,
) -> tuple[bool, Optional[AposentadoriaCausa]]:
    """
    Verifica todas as condicoes de aposentadoria.
    """
    if verificar_aposentadoria_lesao(lesao_tipo):
        return True, AposentadoriaCausa.LESAO_GRAVE

    if verificar_aposentadoria_motivacao(motivacao, temporadas_motivacao_baixa):
        return True, AposentadoriaCausa.MOTIVACAO_BAIXA

    aposentou_idade, _ = verificar_aposentadoria_idade(idade)
    if aposentou_idade:
        return True, AposentadoriaCausa.IDADE

    return False, None


def processar_aposentadoria(
    pilot,
    temporadas_motivacao_baixa: int = 0,
) -> tuple[bool, Optional[AposentadoriaCausa]]:
    """
    Processa verificacao de aposentadoria para um piloto.
    """
    if isinstance(pilot, dict):
        idade = int(pilot.get("idade", 25))
        motivacao = float(pilot.get("motivacao", 50))
        lesao = pilot.get("lesao")
    else:
        idade = int(getattr(pilot, "idade", 25))
        motivacao = float(getattr(pilot, "motivacao", 50))
        lesao = getattr(pilot, "lesao", None)

    lesao_tipo = LesaoTipo.NENHUMA
    if lesao:
        if isinstance(lesao, dict):
            lesao_tipo = _to_lesao_tipo(lesao.get("tipo"))
        else:
            lesao_tipo = _to_lesao_tipo(getattr(lesao, "tipo", LesaoTipo.NENHUMA))

    return verificar_aposentadoria(
        idade=idade,
        motivacao=motivacao,
        temporadas_motivacao_baixa=temporadas_motivacao_baixa,
        lesao_tipo=lesao_tipo,
    )

