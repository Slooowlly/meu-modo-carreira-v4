"""
Sistema de propostas de contrato.
"""

from __future__ import annotations

from typing import Any, Optional
import random

from .avaliacao import avaliar_piloto
from .contratos import calcular_salario
from .models import (
    Clausula,
    PapelEquipe,
    PilotoMercado,
    Proposta,
    StatusProposta,
    TipoClausula,
    VagaAberta,
)


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


def criar_proposta(equipe: Any, piloto: Any, vaga: VagaAberta, avaliacao_score: float) -> Proposta:
    """
    Cria uma proposta de contrato.
    """
    equipe_id = str(_get(equipe, "id", id(equipe)))
    equipe_nome = str(_get(equipe, "nome", "Unknown Team"))
    piloto_id = str(_get(piloto, "id", id(piloto)))
    piloto_nome = str(_get(piloto, "nome", _get(piloto, "name", "Unknown")))
    skill = float(_get(piloto, "skill", 50.0) or 50.0)

    salario_base = calcular_salario(skill=skill, categoria_tier=vaga.categoria_tier, papel=vaga.papel)
    fator_score = 0.8 + (max(0.0, min(100.0, avaliacao_score)) / 100.0) * 0.4
    salario_max = float(vaga.budget_disponivel) * 0.4
    salario_oferecido = min(salario_base * fator_score, salario_max)
    salario_oferecido = max(10.0, round(salario_oferecido, 1))

    idade = int(_get(piloto, "idade", 25) or 25)
    duracao = 2 if (idade < 25 or avaliacao_score > 70) else 1

    clausulas: list[Clausula] = []
    if avaliacao_score > 60:
        clausulas.append(
            Clausula(
                tipo=TipoClausula.SAIDA_REBAIXAMENTO,
                condicao="Pode sair se equipe rebaixar",
            )
        )

    return Proposta(
        equipe_id=equipe_id,
        equipe_nome=equipe_nome,
        piloto_id=piloto_id,
        piloto_nome=piloto_nome,
        salario_anual=salario_oferecido,
        duracao_anos=duracao,
        papel=vaga.papel,
        categoria_id=vaga.categoria_id,
        categoria_tier=vaga.categoria_tier,
        car_performance=vaga.car_performance,
        reputacao_equipe=vaga.reputacao,
        clausulas=clausulas,
        status=StatusProposta.PENDENTE,
    )


def equipe_faz_proposta(
    equipe: Any,
    piloto: Any,
    vaga: VagaAberta,
    visibilidade_piloto: float = 5.0,
) -> Optional[Proposta]:
    """
    Equipe avalia piloto e decide se faz proposta.
    """
    avaliacao = avaliar_piloto(piloto, equipe, visibilidade_piloto)

    skill = float(_get(piloto, "skill", 50.0) or 50.0)
    idade = int(_get(piloto, "idade", 25) or 25)

    if skill < vaga.skill_minimo:
        return None
    if skill > vaga.skill_maximo:
        return None
    if idade > vaga.idade_maxima:
        return None

    if vaga.prefere_jovem and idade > 25 and random.random() > 0.3:
        return None
    if vaga.prefere_experiente and idade < 28 and random.random() > 0.3:
        return None

    if not avaliacao.recomendado and random.random() > 0.2:
        return None

    return criar_proposta(equipe, piloto, vaga, avaliacao.score_custo_beneficio)


def gerar_propostas_para_piloto(
    piloto: PilotoMercado,
    vagas: list[VagaAberta],
    equipes: dict[str, Any],
) -> list[Proposta]:
    """
    Gera todas as propostas que um piloto recebe.
    """
    propostas: list[Proposta] = []

    for vaga in vagas:
        equipe = equipes.get(str(vaga.equipe_id))
        if not equipe:
            continue

        diferenca_tier = int(vaga.categoria_tier) - int(piloto.categoria_tier)
        is_prodigio = piloto.skill > 75 and piloto.idade < 23
        max_salto = 2 if is_prodigio else 1
        if diferenca_tier > max_salto:
            continue

        proposta = equipe_faz_proposta(
            equipe=equipe,
            piloto=piloto,
            vaga=vaga,
            visibilidade_piloto=piloto.visibilidade,
        )
        if proposta:
            propostas.append(proposta)

    return propostas


def ordenar_propostas_por_atratividade(propostas: list[Proposta]) -> list[Proposta]:
    """Ordena propostas da mais atrativa para menos."""
    return sorted(propostas, key=lambda item: item.calcular_atratividade(), reverse=True)

