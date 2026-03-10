"""
Sistema de decisoes das equipes sobre pilotos.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import random

from .contratos import verificar_contrato_expira
from .models import Contrato, PapelEquipe, VagaAberta


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


@dataclass
class DecisaoRenovacao:
    """Decisao de renovacao de um piloto."""

    piloto_id: str
    piloto_nome: str
    contrato_atual: Contrato
    renovar: bool
    motivo: str
    novo_papel: Optional[PapelEquipe] = None
    novo_salario: Optional[float] = None


def avaliar_desempenho_piloto(
    piloto: Any,
    equipe: Any,
    posicao_campeonato: int,
    expectativa_posicao: int,
) -> float:
    """
    Avalia desempenho do piloto na temporada.
    """
    _ = equipe
    score = 50.0
    diferenca = int(expectativa_posicao) - int(posicao_campeonato)

    if diferenca >= 5:
        score += 30
    elif diferenca >= 2:
        score += 15
    elif diferenca >= -2:
        score += 0
    elif diferenca >= -5:
        score -= 15
    else:
        score -= 30

    vitorias = int(_get(piloto, "vitorias_temporada", 0) or 0)
    score += min(vitorias * 5, 15)

    consistencia = float(_get(piloto, "consistencia", 50.0) or 50.0)
    score += (consistencia - 50.0) / 5.0

    return max(0.0, min(100.0, score))


def decidir_renovacao(
    piloto: Any,
    contrato: Contrato,
    equipe: Any,
    posicao_campeonato: int,
    expectativa_posicao: int,
    temporada_atual: int,
) -> DecisaoRenovacao:
    """
    Equipe decide se renova contrato do piloto.
    """
    _ = temporada_atual
    piloto_id = str(_get(piloto, "id", ""))
    piloto_nome = str(_get(piloto, "nome", _get(piloto, "name", "Unknown")))
    idade = int(_get(piloto, "idade", 25) or 25)
    _skill = float(_get(piloto, "skill", 50.0) or 50.0)

    desempenho = avaliar_desempenho_piloto(
        piloto,
        equipe,
        posicao_campeonato=posicao_campeonato,
        expectativa_posicao=expectativa_posicao,
    )

    renovar = True
    motivo = "Desempenho satisfatorio"

    if idade > 36:
        if desempenho < 60:
            renovar = False
            motivo = "Idade avancada com desempenho em queda"
        elif desempenho < 75 and random.random() > 0.5:
            renovar = False
            motivo = "Buscando rejuvenescimento do time"

    if desempenho < 35:
        renovar = False
        motivo = "Desempenho muito abaixo das expectativas"
    elif desempenho < 50 and random.random() > 0.4:
        renovar = False
        motivo = "Desempenho abaixo das expectativas"

    budget = float(_get(equipe, "budget", 50.0) or 50.0)
    if contrato.salario_anual > budget * 0.35 and desempenho < 70:
        renovar = False
        motivo = "Custo muito alto para o desempenho"

    novo_papel = contrato.papel
    novo_salario = float(contrato.salario_anual)

    if renovar:
        if desempenho > 80:
            novo_salario *= 1.15
            motivo = "Desempenho excelente - aumento concedido"
            if contrato.papel == PapelEquipe.NUMERO_2:
                novo_papel = PapelEquipe.NUMERO_1
                motivo += " e promocao a n1"
        elif desempenho > 60:
            novo_salario *= 1.05
            motivo = "Bom desempenho - pequeno aumento"
        else:
            novo_salario *= 0.95
            motivo = "Desempenho mediano - salario ajustado"

    return DecisaoRenovacao(
        piloto_id=piloto_id,
        piloto_nome=piloto_nome,
        contrato_atual=contrato,
        renovar=renovar,
        motivo=motivo,
        novo_papel=novo_papel,
        novo_salario=round(novo_salario, 1),
    )


def processar_decisoes_renovacao(
    equipe: Any,
    pilotos_equipe: list[Any],
    contratos: dict[str, Contrato],
    resultados_temporada: dict[str, dict],
    temporada_atual: int,
) -> tuple[list[DecisaoRenovacao], list[VagaAberta]]:
    """
    Processa todas as decisoes de renovacao de uma equipe.
    """
    decisoes: list[DecisaoRenovacao] = []
    vagas: list[VagaAberta] = []

    equipe_id = str(_get(equipe, "id", ""))
    equipe_nome = str(_get(equipe, "nome", ""))
    categoria_id = str(_get(equipe, "categoria", _get(equipe, "categoria_id", "")))
    categoria_tier = int(_get(equipe, "categoria_tier", 1) or 1)

    for piloto in pilotos_equipe:
        piloto_id = str(_get(piloto, "id", ""))
        contrato = contratos.get(piloto_id)
        if not contrato:
            continue
        if not verificar_contrato_expira(contrato, temporada_atual):
            continue

        resultado = resultados_temporada.get(piloto_id, {})
        posicao = int(resultado.get("posicao", 15) or 15)
        expectativa = int(resultado.get("expectativa", 10) or 10)

        decisao = decidir_renovacao(
            piloto=piloto,
            contrato=contrato,
            equipe=equipe,
            posicao_campeonato=posicao,
            expectativa_posicao=expectativa,
            temporada_atual=temporada_atual,
        )
        decisoes.append(decisao)

        if not decisao.renovar:
            vagas.append(
                VagaAberta(
                    equipe_id=equipe_id,
                    equipe_nome=equipe_nome,
                    categoria_id=categoria_id,
                    categoria_tier=categoria_tier,
                    papel=contrato.papel,
                    car_performance=float(_get(equipe, "car_performance", 50.0) or 50.0),
                    budget_disponivel=float(_get(equipe, "budget", 50.0) or 50.0),
                    reputacao=float(_get(equipe, "reputacao", 50.0) or 50.0),
                )
            )

    return decisoes, vagas


def definir_prioridades_contratacao(equipe: Any, vagas: list[VagaAberta]) -> list[VagaAberta]:
    """
    Define prioridades para preenchimento de vagas.
    """
    _ = equipe
    return sorted(
        vagas,
        key=lambda vaga: (
            0 if vaga.papel == PapelEquipe.NUMERO_1 else 1,
            -vaga.car_performance,
        ),
    )

