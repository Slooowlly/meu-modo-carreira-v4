"""
Sistema de decisoes dos pilotos (NPCs) sobre propostas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import random

from .models import MotivoRecusa, PapelEquipe, PilotoMercado, Proposta, StatusProposta


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


@dataclass
class DecisaoPiloto:
    """Resultado da decisao do piloto sobre propostas."""

    piloto_id: str
    proposta_aceita: Optional[Proposta] = None
    propostas_recusadas: list[Proposta] = None
    ficou_sem_vaga: bool = False
    motivo: str = ""

    def __post_init__(self):
        if self.propostas_recusadas is None:
            self.propostas_recusadas = []


def calcular_score_proposta(proposta: Proposta, piloto: Any, salario_minimo: float = 10.0) -> float:
    """
    Calcula score de uma proposta do ponto de vista do piloto.
    """
    score = 0.0
    score += (max(0.0, min(100.0, proposta.car_performance)) / 100.0) * 30.0
    score += (max(1, min(7, proposta.categoria_tier)) / 7.0) * 25.0

    if proposta.papel == PapelEquipe.NUMERO_1:
        score += 15.0
    elif proposta.papel == PapelEquipe.NUMERO_2:
        score += 10.0
    else:
        score += 2.0

    denom = max(salario_minimo * 1.5, 1.0)
    salario_score = min(proposta.salario_anual / denom, 1.0) * 15.0
    score += salario_score

    score += (max(0.0, min(100.0, proposta.reputacao_equipe)) / 100.0) * 10.0
    return score


def piloto_quer_ser_numero_1(piloto: Any) -> bool:
    """Verifica se piloto prefere ser numero 1."""
    skill = float(_get(piloto, "skill", 50.0) or 50.0)
    idade = int(_get(piloto, "idade", 25) or 25)
    return skill > 70 or (skill > 60 and idade > 28)


def piloto_aceita_categoria_menor(piloto: Any, categoria_atual_tier: int, categoria_proposta_tier: int) -> bool:
    """Verifica se piloto aceita ir para categoria menor."""
    status = str(_get(piloto, "status", "livre") or "livre").strip().lower()
    if status in {"livre", "reserva_global", "reserva"}:
        diferenca = int(categoria_atual_tier) - int(categoria_proposta_tier)
        if diferenca <= 1:
            return random.random() < 0.7
        return random.random() < 0.3
    return categoria_proposta_tier >= categoria_atual_tier - 1


def avaliar_proposta(proposta: Proposta, piloto: Any) -> tuple[bool, Optional[MotivoRecusa]]:
    """
    Piloto avalia uma proposta individual.
    """
    salario_minimo = float(_get(piloto, "salario_minimo", _get(piloto, "salario", 10.0)) or 10.0)
    categoria_atual = int(_get(piloto, "categoria_tier", 1) or 1)

    if proposta.salario_anual < salario_minimo * 0.8:
        return False, MotivoRecusa.SALARIO_BAIXO

    if not piloto_aceita_categoria_menor(piloto, categoria_atual, proposta.categoria_tier):
        return False, MotivoRecusa.CATEGORIA_BAIXA

    if piloto_quer_ser_numero_1(piloto) and proposta.papel != PapelEquipe.NUMERO_1:
        if random.random() < 0.5:
            return False, MotivoRecusa.PAPEL_INDESEJADO

    if proposta.car_performance < 40 and random.random() < 0.6:
        return False, MotivoRecusa.EQUIPE_FRACA

    return True, None


def piloto_decide_propostas(piloto: PilotoMercado, propostas: list[Proposta]) -> DecisaoPiloto:
    """
    Piloto decide entre as propostas recebidas.
    """
    decisao = DecisaoPiloto(piloto_id=piloto.id)

    if not propostas:
        decisao.ficou_sem_vaga = True
        decisao.motivo = "Nao recebeu propostas"
        return decisao

    propostas_aceitaveis: list[Proposta] = []
    for proposta in propostas:
        aceitar, motivo = avaliar_proposta(proposta, piloto)
        if aceitar:
            propostas_aceitaveis.append(proposta)
        else:
            proposta.status = StatusProposta.RECUSADA
            proposta.motivo_recusa = motivo
            decisao.propostas_recusadas.append(proposta)

    if not propostas_aceitaveis:
        if random.random() < 0.3:
            melhor = max(propostas, key=lambda item: item.calcular_atratividade())
            melhor.status = StatusProposta.ACEITA
            decisao.proposta_aceita = melhor
            decisao.motivo = "Aceitou por falta de opcoes"
            return decisao

        decisao.ficou_sem_vaga = True
        decisao.motivo = "Recusou todas as propostas"
        return decisao

    scores: list[tuple[Proposta, float]] = []
    for proposta in propostas_aceitaveis:
        score = calcular_score_proposta(
            proposta,
            piloto,
            float(piloto.salario_minimo),
        )
        scores.append((proposta, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    melhor_proposta, melhor_score = scores[0]
    melhor_proposta.status = StatusProposta.ACEITA
    decisao.proposta_aceita = melhor_proposta
    decisao.motivo = f"Escolheu melhor opcao (score: {melhor_score:.1f})"

    for proposta, _ in scores[1:]:
        proposta.status = StatusProposta.RECUSADA
        proposta.motivo_recusa = MotivoRecusa.PREFERE_OUTRA
        decisao.propostas_recusadas.append(proposta)

    return decisao

