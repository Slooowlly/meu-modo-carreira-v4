"""
Sistema de avaliacao de desempenho comparativo entre pilotos.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .models import ComparacaoResultado, HistoricoHierarquia, MotivoHierarquia


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


def _extrair_id(entidade: Any) -> str:
    valor = _get(entidade, "id", None)
    if valor is not None:
        return str(valor)
    return str(id(entidade))


def _contrato_define_numero_1(contrato: Any) -> bool:
    papel = _get(contrato, "papel", None)
    if papel is None:
        return False

    # Aceita enum de mercado, string simples e enums genericos.
    valor = getattr(papel, "value", papel)
    if isinstance(valor, str):
        return valor.strip().lower() == "numero_1"
    return False


def comparar_resultado_corrida(
    piloto_1: Any,
    piloto_2: Any,
    posicao_1: int,
    posicao_2: int,
    corrida_numero: int,
) -> ComparacaoResultado:
    """
    Compara resultado de uma corrida entre dois pilotos.
    """
    return ComparacaoResultado(
        corrida_numero=int(corrida_numero),
        piloto_1_id=_extrair_id(piloto_1),
        piloto_2_id=_extrair_id(piloto_2),
        posicao_piloto_1=int(posicao_1),
        posicao_piloto_2=int(posicao_2),
    )


def avaliar_desempenho_temporada(historico: HistoricoHierarquia) -> Dict[str, Any]:
    """
    Avalia desempenho comparativo da temporada.
    """
    if not historico.comparacoes:
        return {
            "corridas": 0,
            "p1_dominante": False,
            "p2_dominante": False,
            "equilibrado": True,
            "tendencia": "indefinida",
            "analise": "Sem dados suficientes",
        }

    total = historico.total_corridas
    p1_wins = historico.vitorias_duelo_p1
    p2_wins = historico.vitorias_duelo_p2

    p1_dominante = historico.percentual_p1 >= 65.0
    p2_dominante = historico.percentual_p2 >= 65.0
    equilibrado = not p1_dominante and not p2_dominante

    ultimas_3 = historico.comparacoes[-3:] if len(historico.comparacoes) >= 3 else historico.comparacoes
    tendencia_p1 = sum(1 for comp in ultimas_3 if comp.piloto_1_venceu_duelo)
    tendencia_p2 = len(ultimas_3) - tendencia_p1

    if tendencia_p1 > tendencia_p2:
        tendencia = "p1_subindo"
    elif tendencia_p2 > tendencia_p1:
        tendencia = "p2_subindo"
    else:
        tendencia = "estavel"

    if p1_dominante:
        analise = f"N1 claramente superior ({p1_wins}/{total} duelos)"
    elif p2_dominante:
        analise = f"N2 superando o N1 ({p2_wins}/{total} duelos)"
    elif historico.sequencia_atual_p2 >= 3:
        analise = f"N2 em sequencia de {historico.sequencia_atual_p2} corridas a frente"
    elif equilibrado:
        analise = f"Disputa equilibrada ({p1_wins}x{p2_wins})"
    else:
        analise = "Situacao indefinida"

    return {
        "corridas": total,
        "p1_vitorias": p1_wins,
        "p2_vitorias": p2_wins,
        "p1_percentual": historico.percentual_p1,
        "p2_percentual": historico.percentual_p2,
        "p1_dominante": p1_dominante,
        "p2_dominante": p2_dominante,
        "equilibrado": equilibrado,
        "sequencia_p2": historico.sequencia_atual_p2,
        "tendencia": tendencia,
        "analise": analise,
    }


def definir_hierarquia_inicial(
    piloto_1: Any,
    piloto_2: Any,
    contrato_1: Optional[Any] = None,
    contrato_2: Optional[Any] = None,
) -> Tuple[str, str, MotivoHierarquia]:
    """
    Define hierarquia inicial entre dois pilotos.

    Prioridade:
    1) Contrato
    2) Salario
    3) Skill
    4) Experiencia
    5) Idade (desempate)
    """
    p1_id = _extrair_id(piloto_1)
    p2_id = _extrair_id(piloto_2)

    if contrato_1 and _contrato_define_numero_1(contrato_1):
        return p1_id, p2_id, MotivoHierarquia.CONTRATO

    if contrato_2 and _contrato_define_numero_1(contrato_2):
        return p2_id, p1_id, MotivoHierarquia.CONTRATO

    salario_1 = float(_get_any(contrato_1, ("salario_anual", "salario"), 0.0) or 0.0) if contrato_1 else 0.0
    salario_2 = float(_get_any(contrato_2, ("salario_anual", "salario"), 0.0) or 0.0) if contrato_2 else 0.0
    if salario_1 > salario_2 * 1.2:
        return p1_id, p2_id, MotivoHierarquia.SALARIO
    if salario_2 > salario_1 * 1.2:
        return p2_id, p1_id, MotivoHierarquia.SALARIO

    skill_1 = float(_get(piloto_1, "skill", 50) or 50)
    skill_2 = float(_get(piloto_2, "skill", 50) or 50)
    if skill_1 > skill_2 + 3:
        return p1_id, p2_id, MotivoHierarquia.SKILL
    if skill_2 > skill_1 + 3:
        return p2_id, p1_id, MotivoHierarquia.SKILL

    exp_1 = float(_get_any(piloto_1, ("experience", "experiencia"), 0) or 0)
    exp_2 = float(_get_any(piloto_2, ("experience", "experiencia"), 0) or 0)
    if exp_1 > exp_2 + 10:
        return p1_id, p2_id, MotivoHierarquia.EXPERIENCIA
    if exp_2 > exp_1 + 10:
        return p2_id, p1_id, MotivoHierarquia.EXPERIENCIA

    idade_1 = int(_get_any(piloto_1, ("idade", "age"), 25) or 25)
    idade_2 = int(_get_any(piloto_2, ("idade", "age"), 25) or 25)
    if idade_1 >= idade_2:
        return p1_id, p2_id, MotivoHierarquia.EXPERIENCIA
    return p2_id, p1_id, MotivoHierarquia.EXPERIENCIA


def calcular_diferenca_media(historico: HistoricoHierarquia) -> float:
    """
    Calcula diferenca media de posicoes entre os pilotos.
    """
    if not historico.comparacoes:
        return 0.0

    total_diff = sum(comp.diferenca for comp in historico.comparacoes)
    return total_diff / len(historico.comparacoes)


def piloto_superando_companheiro(
    historico: HistoricoHierarquia,
    piloto_id: str,
    minimo_corridas: int = 3,
) -> bool:
    """
    Verifica se um piloto esta superando o companheiro de forma consistente.
    """
    if historico.total_corridas < minimo_corridas:
        return False

    if str(piloto_id) == str(historico.piloto_numero_1_id):
        return historico.percentual_p1 >= 65.0
    return historico.percentual_p2 >= 65.0
