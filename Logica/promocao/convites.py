"""Invitation system for optional promotions."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import random

from .models import Convite, HistoricoEquipe, MotivoMovimentacao, ResultadoTemporada, StatusConvite
from .regras import get_regra_categoria


def _get(entidade: Any, campo: str, default=None):
    if isinstance(entidade, dict):
        return entidade.get(campo, default)
    return getattr(entidade, campo, default)


def criar_convite(
    equipe: Any,
    categoria_origem: str,
    categoria_destino: str,
    temporada: int,
    motivo: MotivoMovimentacao = MotivoMovimentacao.TOP_3_CONSECUTIVO,
) -> Convite:
    regra_origem = get_regra_categoria(categoria_origem)
    regra_destino = get_regra_categoria(categoria_destino)

    return Convite(
        equipe_id=str(_get(equipe, "id", str(id(equipe)))),
        equipe_nome=str(_get(equipe, "nome", "Unknown")),
        categoria_origem_id=str(categoria_origem),
        categoria_origem_tier=int(regra_origem.tier if regra_origem else 1),
        categoria_destino_id=str(categoria_destino),
        categoria_destino_tier=int(regra_destino.tier if regra_destino else 1),
        temporada=int(temporada),
        motivo=motivo,
        status=StatusConvite.PENDENTE,
        budget_minimo=float(regra_origem.budget_minimo_promocao if regra_origem else 0.0),
        budget_equipe=float(_get(equipe, "budget", 50.0) or 50.0),
    )


def equipe_decide_convite(convite: Convite, equipe: Any) -> bool:
    if not convite.pode_aceitar:
        convite.status = StatusConvite.RECUSADO
        return False

    reputacao = float(_get(equipe, "reputacao", 50.0) or 50.0)
    morale = float(_get(equipe, "morale", 1.0) or 1.0)

    chance = 0.70
    if reputacao > 70:
        chance += 0.10
    elif reputacao < 40:
        chance -= 0.10

    if morale > 1.1:
        chance += 0.08
    elif morale < 0.9:
        chance -= 0.08

    folga = float(convite.budget_equipe - convite.budget_minimo)
    if folga > 20:
        chance += 0.08
    elif folga < 5:
        chance -= 0.12

    chance = max(0.10, min(0.95, chance))
    aceita = random.random() < chance
    convite.status = StatusConvite.ACEITO if aceita else StatusConvite.RECUSADO
    return aceita


def processar_convites(convites: List[Convite], equipes: Dict[str, Any]) -> Tuple[List[Convite], List[Convite]]:
    aceitos: List[Convite] = []
    recusados: List[Convite] = []
    for convite in convites:
        if convite.status != StatusConvite.PENDENTE:
            continue
        equipe = equipes.get(convite.equipe_id)
        if not equipe:
            convite.status = StatusConvite.EXPIRADO
            continue
        if equipe_decide_convite(convite, equipe):
            aceitos.append(convite)
        else:
            recusados.append(convite)
    return aceitos, recusados


def gerar_convites_categoria(
    equipes: List[Any],
    resultados: Dict[str, ResultadoTemporada],
    historicos: Dict[str, HistoricoEquipe],
    categoria_id: str,
    temporada: int,
    vagas_promocao_consumidas: int = 0,
) -> List[Convite]:
    convites: List[Convite] = []

    regra = get_regra_categoria(categoria_id)
    if not regra or not regra.permite_convite:
        return convites

    destino = regra.categoria_destino_promocao
    if not destino:
        return convites

    vagas_automaticas = max(0, int(regra.vagas_promocao) - int(vagas_promocao_consumidas))

    for equipe in equipes:
        equipe_id = str(_get(equipe, "id", str(id(equipe))))
        resultado = resultados.get(equipe_id)
        historico = historicos.get(equipe_id)
        if not resultado or not historico:
            continue

        if resultado.posicao_construtores <= vagas_automaticas:
            continue
        if not resultado.is_top_3:
            continue
        if not historico.is_top_3_consecutivo(regra.temporadas_para_convite):
            continue

        convites.append(
            criar_convite(
                equipe=equipe,
                categoria_origem=categoria_id,
                categoria_destino=destino,
                temporada=temporada,
            )
        )

    return convites
