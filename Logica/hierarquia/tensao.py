"""
Sistema de tensao entre pilotos.
"""

from __future__ import annotations

from typing import Any

from .models import EstadoHierarquia, HistoricoHierarquia, StatusTensao


THRESHOLD_COMPETITIVO = 20.0
THRESHOLD_TENSAO = 40.0
THRESHOLD_REAVALIACAO = 60.0
THRESHOLD_INVERSAO = 75.0
THRESHOLD_CRISE = 90.0

TENSAO_P2_VENCE_DUELO = 3.0
TENSAO_P2_SEQUENCIA_3 = 10.0
TENSAO_P2_SEQUENCIA_5 = 15.0
TENSAO_ORDEM_EMITIDA = 5.0
TENSAO_ORDEM_DESOBEDECIDA = 15.0

TENSAO_P1_VENCE_DUELO = -2.0
TENSAO_P1_SEQUENCIA_3 = -8.0
TENSAO_DECAIMENTO_NATURAL = -1.0


def _get(entidade: Any, campo: str, default=None):
    if isinstance(entidade, dict):
        return entidade.get(campo, default)
    return getattr(entidade, campo, default)


def _get_any(entidade: Any, campos: tuple[str, ...], default=None):
    for campo in campos:
        valor = _get(entidade, campo, None)
        if valor is not None:
            return valor
    return default


def _normalizar_percentual(valor: Any, default: float = 50.0) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return float(default)

    if numero <= 1.0:
        numero *= 100.0
    return max(0.0, min(100.0, numero))


def calcular_tensao_inicial(historico: HistoricoHierarquia) -> float:
    """
    Calcula nivel de tensao inicial baseado no historico.
    """
    tensao = 0.0

    if historico.percentual_p2 > 50.0:
        excesso = historico.percentual_p2 - 50.0
        tensao += excesso * 0.5

    if historico.sequencia_atual_p2 >= 5:
        tensao += TENSAO_P2_SEQUENCIA_5
    elif historico.sequencia_atual_p2 >= 3:
        tensao += TENSAO_P2_SEQUENCIA_3

    if historico.maior_sequencia_p2 >= 5:
        tensao += 10.0

    return min(100.0, max(0.0, tensao))


def atualizar_tensao_pos_corrida(
    estado: EstadoHierarquia,
    p1_venceu_duelo: bool,
    ordem_emitida: bool = False,
    ordem_obedecida: bool = True,
) -> float:
    """
    Atualiza nivel de tensao apos uma corrida.
    """
    delta = 0.0

    if p1_venceu_duelo:
        delta += TENSAO_P1_VENCE_DUELO
        if estado.historico and estado.historico.sequencia_atual_p1 >= 3:
            delta += TENSAO_P1_SEQUENCIA_3 - TENSAO_P1_VENCE_DUELO
    else:
        delta += TENSAO_P2_VENCE_DUELO
        if estado.historico:
            if estado.historico.sequencia_atual_p2 >= 5:
                delta += TENSAO_P2_SEQUENCIA_5 - TENSAO_P2_VENCE_DUELO
            elif estado.historico.sequencia_atual_p2 >= 3:
                delta += TENSAO_P2_SEQUENCIA_3 - TENSAO_P2_VENCE_DUELO

    if ordem_emitida:
        delta += TENSAO_ORDEM_EMITIDA
        estado.ordens_emitidas += 1
        if not ordem_obedecida:
            delta += TENSAO_ORDEM_DESOBEDECIDA
            estado.ordens_desobedecidas += 1

    delta += TENSAO_DECAIMENTO_NATURAL

    estado.nivel_tensao = min(100.0, max(0.0, estado.nivel_tensao + delta))
    estado.status_tensao = determinar_status_tensao(estado.nivel_tensao)
    return estado.nivel_tensao


def determinar_status_tensao(nivel: float) -> StatusTensao:
    """
    Determina status de tensao baseado no nivel.
    """
    if nivel >= THRESHOLD_CRISE:
        return StatusTensao.CRISE
    if nivel >= THRESHOLD_INVERSAO:
        return StatusTensao.INVERSAO_PENDENTE
    if nivel >= THRESHOLD_REAVALIACAO:
        return StatusTensao.REAVALIACAO
    if nivel >= THRESHOLD_TENSAO:
        return StatusTensao.TENSAO
    if nivel >= THRESHOLD_COMPETITIVO:
        return StatusTensao.COMPETITIVO
    return StatusTensao.ESTAVEL


def tensao_afeta_moral_equipe(estado: EstadoHierarquia) -> float:
    """
    Calcula impacto da tensao na moral da equipe.
    """
    impacto = 1.0 - (estado.nivel_tensao / 100.0 * 0.2)
    return max(0.8, impacto)


def deve_emitir_ordem(
    estado: EstadoHierarquia,
    posicao_p1: int,
    posicao_p2: int,
    voltas_restantes: int,
    diferenca_campeonato: int,
) -> bool:
    """
    Decide se a equipe deve emitir ordem para o N2 deixar o N1 passar.
    """
    del estado

    if posicao_p2 >= posicao_p1:
        return False

    diferenca = posicao_p1 - posicao_p2

    if voltas_restantes <= 3 and diferenca <= 2 and diferenca_campeonato < 10:
        return True

    if voltas_restantes <= 5 and diferenca >= 3 and diferenca_campeonato < 20:
        return True

    if posicao_p2 <= 3 and posicao_p1 <= 5 and diferenca <= 2:
        return True

    return False


def calcular_chance_desobediencia(
    piloto: Any,
    tipo_ordem: str,
    posicao_atual: int,
    tensao_atual: float,
) -> float:
    """
    Calcula chance de desobedecer uma ordem.
    """
    del tipo_ordem

    chance = 0.10

    agressividade = _normalizar_percentual(
        _get_any(piloto, ("agressividade", "aggression"), 50.0),
        default=50.0,
    )
    chance += (agressividade - 50.0) / 100.0 * 0.15

    if posicao_atual <= 3:
        chance += 0.20
    elif posicao_atual <= 5:
        chance += 0.10

    chance += (max(0.0, min(100.0, float(tensao_atual))) / 100.0) * 0.15

    experiencia = _normalizar_percentual(
        _get_any(piloto, ("experience", "experiencia"), 50.0),
        default=50.0,
    )
    chance -= (experiencia / 100.0) * 0.10

    return min(0.60, max(0.05, chance))
