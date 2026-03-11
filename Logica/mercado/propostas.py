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
from .visibilidade import categoria_permite_mercado_externo


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


def _papel_normalizado(valor: Any) -> str:
    papel = str(valor or "").strip().lower()
    if papel in {"n1", "numero_1"}:
        return "numero_1"
    if papel in {"n2", "numero_2"}:
        return "numero_2"
    return papel


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
    if vaga.papel == PapelEquipe.NUMERO_2:
        duracao = 1
    else:
        duracao = random.choice([1, 2])
        if idade < 24 and avaliacao_score > 75:
            duracao = 2

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
    score_ajustado = float(avaliacao.score_custo_beneficio)

    skill = float(_get(piloto, "skill", 50.0) or 50.0)
    idade = int(_get(piloto, "idade", 25) or 25)
    papel_atual = _papel_normalizado(_get(piloto, "papel_atual", _get(piloto, "papel", "")))
    n2_superou_n1 = bool(_get(piloto, "n2_superou_n1", False))

    if vaga.papel == PapelEquipe.NUMERO_1:
        if papel_atual == "numero_2" and not n2_superou_n1 and random.random() > 0.15:
            return None
        if papel_atual == "numero_1" or n2_superou_n1:
            score_ajustado += 8.0
    elif vaga.papel == PapelEquipe.NUMERO_2:
        if papel_atual == "numero_1" and skill > 80 and random.random() > 0.25:
            return None
        if papel_atual == "numero_2":
            score_ajustado += 3.0

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

    return criar_proposta(equipe, piloto, vaga, score_ajustado)


def gerar_propostas_para_piloto(
    piloto: PilotoMercado,
    vagas: list[VagaAberta],
    equipes: dict[str, Any],
) -> list[Proposta]:
    """
    Gera todas as propostas que um piloto recebe.
    """
    propostas: list[Proposta] = []

    categoria_atual = str(piloto.categoria_atual or "").strip().lower()
    posicao_campeonato = int(getattr(piloto, "posicao_campeonato", 0) or 0)
    destinos_rookie = {
        "mazda_rookie": "mazda_amador",
        "toyota_rookie": "toyota_amador",
    }

    if categoria_atual in destinos_rookie:
        if posicao_campeonato <= 0 or posicao_campeonato > 3:
            return []
        destino_permitido = destinos_rookie[categoria_atual]
    else:
        destino_permitido = None
        if not categoria_permite_mercado_externo(categoria_atual):
            return []

    for vaga in vagas:
        equipe = equipes.get(str(vaga.equipe_id))
        if not equipe:
            continue

        categoria_destino = str(vaga.categoria_id or "").strip().lower()
        if destino_permitido is not None:
            eh_destino_superior = (
                categoria_destino == destino_permitido
                and int(vaga.categoria_tier) == 2
            )
            eh_movimento_mesma_categoria = (
                categoria_destino == categoria_atual
                and int(vaga.categoria_tier) == int(piloto.categoria_tier)
            )
            if not (eh_destino_superior or eh_movimento_mesma_categoria):
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
