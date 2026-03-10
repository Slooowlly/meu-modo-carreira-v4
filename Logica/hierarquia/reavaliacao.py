"""
Sistema de reavaliacao e inversao de hierarquia.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from .avaliacao import avaliar_desempenho_temporada
from .models import EstadoHierarquia, MotivoHierarquia, StatusTensao


CORRIDAS_PARA_REAVALIACAO = 5
CORRIDAS_PARA_INVERSAO = 8
PERCENTUAL_MINIMO_INVERSAO = 65.0
SEQUENCIA_MINIMA_INVERSAO = 4


def deve_reavaliar_hierarquia(
    estado: EstadoHierarquia,
    corrida_atual: int,
    total_corridas: int,
) -> Tuple[bool, str]:
    """
    Verifica se deve reavaliar a hierarquia.
    """
    del corrida_atual, total_corridas

    if not estado.historico:
        return False, ""

    historico = estado.historico

    if estado.inversao_ocorreu:
        return False, "Ja houve inversao esta temporada"

    if historico.total_corridas < CORRIDAS_PARA_REAVALIACAO:
        return False, "Corridas insuficientes para reavaliacao"

    avaliacao = avaliar_desempenho_temporada(historico)

    if historico.sequencia_atual_p2 >= SEQUENCIA_MINIMA_INVERSAO:
        return True, f"N2 a frente por {historico.sequencia_atual_p2} corridas consecutivas"

    if avaliacao["p2_percentual"] >= 60.0 and historico.total_corridas >= CORRIDAS_PARA_REAVALIACAO:
        return True, f"N2 vencendo {avaliacao['p2_percentual']:.0f}% dos duelos"

    if estado.status_tensao in (StatusTensao.REAVALIACAO, StatusTensao.INVERSAO_PENDENTE):
        return True, f"Tensao alta: {estado.status_tensao.value}"

    return False, ""


def deve_inverter_hierarquia(
    estado: EstadoHierarquia,
    corrida_atual: int,
    total_corridas: int,
) -> Tuple[bool, str]:
    """
    Verifica se deve inverter a hierarquia.
    """
    if not estado.historico:
        return False, ""

    historico = estado.historico

    if estado.inversao_ocorreu:
        return False, "Ja houve inversao"

    if historico.total_corridas < CORRIDAS_PARA_INVERSAO:
        return False, "Corridas insuficientes"

    metade = max(1, int(total_corridas) // 2)
    avaliacao = avaliar_desempenho_temporada(historico)

    if historico.sequencia_atual_p2 >= 5:
        return True, f"N2 superior por {historico.sequencia_atual_p2} corridas seguidas"

    if corrida_atual >= metade and avaliacao["p2_percentual"] >= PERCENTUAL_MINIMO_INVERSAO:
        return True, f"N2 vencendo {avaliacao['p2_percentual']:.0f}% apos metade da temporada"

    if estado.status_tensao == StatusTensao.CRISE:
        return True, "Situacao de crise insustentavel"

    return False, ""


def executar_inversao(estado: EstadoHierarquia, corrida_numero: int) -> EstadoHierarquia:
    """
    Executa inversao de hierarquia (troca N1 <-> N2).
    """
    estado.piloto_1_id, estado.piloto_2_id = estado.piloto_2_id, estado.piloto_1_id
    estado.piloto_1_nome, estado.piloto_2_nome = estado.piloto_2_nome, estado.piloto_1_nome

    if estado.historico:
        estado.historico.piloto_numero_1_id, estado.historico.piloto_numero_2_id = (
            estado.historico.piloto_numero_2_id,
            estado.historico.piloto_numero_1_id,
        )
        estado.historico.houve_inversao = True
        estado.historico.corrida_inversao = int(corrida_numero)
        estado.historico.sequencia_atual_p1 = 0
        estado.historico.sequencia_atual_p2 = 0

    estado.inversao_ocorreu = True
    estado.motivo = MotivoHierarquia.INVERSAO
    estado.nivel_tensao = max(0.0, estado.nivel_tensao - 30.0)
    estado.status_tensao = StatusTensao.COMPETITIVO
    return estado


def calcular_impacto_inversao(piloto_rebaixado: Any, piloto_promovido: Any) -> Dict[str, Dict[str, Any]]:
    """
    Calcula impactos de inversao nos dois pilotos.
    """
    del piloto_rebaixado, piloto_promovido

    impacto_rebaixado = {
        "motivacao_delta": -10.0,
        "confianca_delta": -8.0,
        "relacao_equipe_delta": -5.0,
        "descricao": "Perdeu status de numero 1",
    }
    impacto_promovido = {
        "motivacao_delta": +15.0,
        "confianca_delta": +10.0,
        "relacao_equipe_delta": +5.0,
        "descricao": "Promovido a numero 1",
    }
    return {"rebaixado": impacto_rebaixado, "promovido": impacto_promovido}


def _get(entidade: Any, campo: str, default=None):
    if isinstance(entidade, dict):
        return entidade.get(campo, default)
    return getattr(entidade, campo, default)


def _set(entidade: Any, campo: str, valor):
    if isinstance(entidade, dict):
        entidade[campo] = valor
    else:
        setattr(entidade, campo, valor)


def aplicar_impacto_inversao(piloto: Any, foi_promovido: bool) -> Dict[str, Dict[str, float]]:
    """
    Aplica impacto de inversao em um piloto.
    """
    mudancas: Dict[str, Dict[str, float]] = {}

    if _get(piloto, "motivacao", None) is not None:
        antes = float(_get(piloto, "motivacao", 0.0) or 0.0)
        delta = 15.0 if foi_promovido else -10.0
        depois = max(0.0, min(100.0, antes + delta))
        _set(piloto, "motivacao", depois)
        mudancas["motivacao"] = {"antes": antes, "depois": depois}

    return mudancas
