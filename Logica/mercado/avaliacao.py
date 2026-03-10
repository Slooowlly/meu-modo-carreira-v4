"""
Sistema de avaliacao de pilotos pelas equipes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


ERRO_POTENCIAL_BASE = 10.0
ERRO_POTENCIAL_MIN = 5.0
ERRO_POTENCIAL_MAX = 15.0


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


@dataclass
class AvaliacaoPiloto:
    """Avaliacao de um piloto por uma equipe."""

    piloto_id: str
    equipe_id: str

    skill_real: float = 0.0
    potencial_real: float = 0.0

    skill_estimado: float = 0.0
    potencial_estimado: float = 0.0

    score_atual: float = 0.0
    score_futuro: float = 0.0
    score_custo_beneficio: float = 0.0

    margem_erro: float = 0.0

    recomendado: bool = False
    motivo: str = ""


def calcular_margem_erro(engineering_quality: float, experiencia_piloto: float, visibilidade_piloto: float) -> float:
    """
    Calcula margem de erro na avaliacao de potencial.
    """
    erro_base = ERRO_POTENCIAL_BASE
    reducao_eng = (engineering_quality / 100.0) * ERRO_POTENCIAL_BASE * 0.3
    reducao_exp = (experiencia_piloto / 100.0) * ERRO_POTENCIAL_BASE * 0.2
    reducao_vis = (visibilidade_piloto / 10.0) * ERRO_POTENCIAL_BASE * 0.1
    erro_final = erro_base - reducao_eng - reducao_exp - reducao_vis
    return max(ERRO_POTENCIAL_MIN, min(ERRO_POTENCIAL_MAX, erro_final))


def estimar_potencial(potencial_real: float, margem_erro: float) -> float:
    """Estima potencial com margem de erro."""
    erro = random.uniform(-margem_erro, margem_erro)
    estimado = potencial_real + erro
    return max(40.0, min(100.0, estimado))


def calcular_score_atual(skill: float, consistencia: float, experience: float) -> float:
    """Calcula score de performance atual."""
    return skill * 0.60 + consistencia * 0.25 + experience * 0.15


def calcular_score_futuro(skill: float, potencial_estimado: float, idade: int) -> float:
    """Calcula score de potencial futuro."""
    espaco = max(0.0, potencial_estimado - skill)
    if idade < 25:
        anos_produtivos = 10
    elif idade < 30:
        anos_produtivos = 7
    elif idade < 35:
        anos_produtivos = 4
    else:
        anos_produtivos = 2
    fator_tempo = anos_produtivos / 10.0
    return skill + (espaco * fator_tempo * 0.5)


def calcular_custo_beneficio(score_atual: float, score_futuro: float, salario_pretendido: float, budget_equipe: float) -> float:
    """Calcula relacao custo-beneficio."""
    if salario_pretendido <= 0:
        salario_pretendido = 10.0
    score_combinado = score_atual * 0.7 + score_futuro * 0.3
    proporcao_budget = salario_pretendido / max(1.0, budget_equipe)
    fator_custo = 1.0 - min(proporcao_budget, 1.0)
    return score_combinado * (0.5 + fator_custo * 0.5)


def avaliar_piloto(piloto: Any, equipe: Any, visibilidade: float = 5.0) -> AvaliacaoPiloto:
    """
    Equipe avalia um piloto para possivel contratacao.
    """
    piloto_id = str(_get(piloto, "id", id(piloto)))
    skill_real = float(_get(piloto, "skill", 50.0) or 50.0)

    potencial_base = float(_get(piloto, "potencial_base", _get(piloto, "potencial", 70.0)) or 70.0)
    potencial_bonus = float(_get(piloto, "potencial_bonus", 0.0) or 0.0)
    potencial_real = max(30.0, min(100.0, potencial_base + potencial_bonus))

    consistencia = float(_get(piloto, "consistencia", 50.0) or 50.0)
    experience = float(_get(piloto, "experience", _get(piloto, "experiencia", 0.0)) or 0.0)
    idade = int(_get(piloto, "idade", 25) or 25)

    salario_pretendido = float(
        _get(
            piloto,
            "salario_pretendido",
            _get(piloto, "salario", 20.0),
        )
        or 20.0
    )

    equipe_id = str(_get(equipe, "id", id(equipe)))
    engineering = float(_get(equipe, "engineering_quality", 50.0) or 50.0)
    budget = float(_get(equipe, "budget", 50.0) or 50.0)

    margem = calcular_margem_erro(engineering, experience, visibilidade)
    potencial_estimado = estimar_potencial(potencial_real, margem)
    skill_estimado = max(20.0, min(100.0, skill_real + random.uniform(-2.0, 2.0)))

    score_atual = calcular_score_atual(skill_estimado, consistencia, experience)
    score_futuro = calcular_score_futuro(skill_estimado, potencial_estimado, idade)
    score_cb = calcular_custo_beneficio(score_atual, score_futuro, salario_pretendido, budget)

    recomendado = score_cb >= 50.0
    if score_cb >= 70:
        motivo = "Excelente custo-beneficio"
    elif score_cb >= 55:
        motivo = "Bom investimento"
    elif score_cb >= 45:
        motivo = "Aceitavel"
    else:
        motivo = "Custo-beneficio baixo"

    return AvaliacaoPiloto(
        piloto_id=piloto_id,
        equipe_id=equipe_id,
        skill_real=skill_real,
        potencial_real=potencial_real,
        skill_estimado=skill_estimado,
        potencial_estimado=potencial_estimado,
        score_atual=score_atual,
        score_futuro=score_futuro,
        score_custo_beneficio=score_cb,
        margem_erro=margem,
        recomendado=recomendado,
        motivo=motivo,
    )

