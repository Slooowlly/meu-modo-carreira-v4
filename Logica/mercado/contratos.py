"""
Sistema de contratos entre pilotos e equipes.
"""

from __future__ import annotations

from typing import Optional

from .models import (
    Clausula,
    Contrato,
    PapelEquipe,
    StatusContrato,
    TipoClausula,
)


SALARIO_BASE_POR_TIER = {
    1: 10.0,
    2: 15.0,
    3: 25.0,
    4: 35.0,
    5: 50.0,
    6: 70.0,
    7: 100.0,
}

SALARIO_BONUS_SKILL = 0.5
SALARIO_BONUS_NUMERO_1 = 1.3


def calcular_salario(skill: float, categoria_tier: int, papel: PapelEquipe, reputacao_piloto: float = 50.0) -> float:
    """
    Calcula salario sugerido para um piloto.
    """
    base = float(SALARIO_BASE_POR_TIER.get(max(1, categoria_tier), 20.0))
    skill_bonus = max(0.0, float(skill) - 50.0) * SALARIO_BONUS_SKILL
    rep_bonus = (max(0.0, min(100.0, reputacao_piloto)) / 100.0) * base * 0.2
    salario = base + skill_bonus + rep_bonus

    if papel == PapelEquipe.NUMERO_1:
        salario *= SALARIO_BONUS_NUMERO_1
    elif papel == PapelEquipe.RESERVA:
        salario *= 0.3

    return round(salario, 1)


def criar_contrato(
    piloto_id: str,
    piloto_nome: str,
    equipe_id: str,
    equipe_nome: str,
    temporada_inicio: int,
    duracao_anos: int,
    salario_anual: float,
    papel: PapelEquipe,
    incluir_clausula_rebaixamento: bool = True,
    incluir_clausula_performance: bool = False,
    meta_performance: int = 5,
) -> Contrato:
    """
    Cria um novo contrato.
    """
    clausulas: list[Clausula] = []
    if incluir_clausula_rebaixamento:
        clausulas.append(
            Clausula(
                tipo=TipoClausula.SAIDA_REBAIXAMENTO,
                condicao="Piloto pode sair se equipe for rebaixada",
            )
        )
    if incluir_clausula_performance:
        clausulas.append(
            Clausula(
                tipo=TipoClausula.PERFORMANCE,
                condicao=f"Renovacao automatica se terminar top {meta_performance}",
            )
        )

    return Contrato(
        piloto_id=piloto_id,
        piloto_nome=piloto_nome,
        equipe_id=equipe_id,
        equipe_nome=equipe_nome,
        temporada_inicio=temporada_inicio,
        duracao_anos=max(1, min(2, int(duracao_anos))),
        salario_anual=float(salario_anual),
        papel=papel,
        clausulas=clausulas,
        status=StatusContrato.ATIVO,
    )


def verificar_contrato_expira(contrato: Contrato, temporada_atual: int) -> bool:
    """Verifica se contrato expira na temporada atual."""
    return int(contrato.temporada_fim) <= int(temporada_atual)


def verificar_clausula_rebaixamento(contrato: Contrato, equipe_rebaixou: bool) -> bool:
    """Verifica se piloto pode acionar clausula de rebaixamento."""
    if not equipe_rebaixou:
        return False
    return contrato.tem_clausula(TipoClausula.SAIDA_REBAIXAMENTO)


def verificar_clausula_performance(contrato: Contrato, posicao_campeonato: int) -> bool:
    """Verifica se clausula de performance foi ativada."""
    clausula = contrato.get_clausula(TipoClausula.PERFORMANCE)
    if not clausula:
        return False
    try:
        import re

        match = re.search(r"top (\d+)", clausula.condicao)
        if match:
            meta = int(match.group(1))
            return int(posicao_campeonato) <= meta
    except Exception:
        return False
    return False


def rescindir_contrato(contrato: Contrato, motivo: str = "rescisao mutua") -> Contrato:
    """Rescinde um contrato."""
    _ = motivo
    contrato.status = StatusContrato.RESCINDIDO
    return contrato


def renovar_contrato(
    contrato: Contrato,
    temporada_atual: int,
    nova_duracao: int = 1,
    novo_salario: Optional[float] = None,
    novo_papel: Optional[PapelEquipe] = None,
) -> Contrato:
    """Renova um contrato existente."""
    contrato.status = StatusContrato.EXPIRADO
    return Contrato(
        piloto_id=contrato.piloto_id,
        piloto_nome=contrato.piloto_nome,
        equipe_id=contrato.equipe_id,
        equipe_nome=contrato.equipe_nome,
        temporada_inicio=int(temporada_atual) + 1,
        duracao_anos=max(1, min(2, int(nova_duracao))),
        salario_anual=float(novo_salario if novo_salario is not None else contrato.salario_anual),
        papel=novo_papel or contrato.papel,
        clausulas=list(contrato.clausulas),
        status=StatusContrato.ATIVO,
    )


def listar_contratos_expirando(contratos: list[Contrato], temporada_atual: int) -> list[Contrato]:
    """Lista contratos ativos que expiram na temporada atual."""
    return [c for c in contratos if c.esta_ativo and verificar_contrato_expira(c, temporada_atual)]

