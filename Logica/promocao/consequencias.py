"""Movement consequences and preview/apply helpers."""

from __future__ import annotations

from typing import Any, Dict
import random

from .models import ConsequenciasMovimentacao, TipoMovimentacao


PROMOCAO_CONFIG = {
    "car_performance": {"min": 5, "max": 10},
    "budget": {"min": 5, "max": 15},
    "facilities": {"min": 0, "max": 5},
    "engineering": {"min": 0, "max": 3},
    "morale": 1.15,
    "reputacao": {"min": 3, "max": 8},
}

REBAIXAMENTO_CONFIG = {
    "car_performance": {"min": -8, "max": -3},
    "budget": {"min": -15, "max": -5},
    "facilities": {"min": -3, "max": 0},
    "engineering": {"min": -5, "max": -1},
    "morale": 0.75,
    "reputacao": {"min": -10, "max": -5},
}


def _roll(config: dict, key: str) -> int:
    return random.randint(int(config[key]["min"]), int(config[key]["max"]))


def calcular_consequencias_promocao(equipe: Any, categoria_destino_tier: int) -> ConsequenciasMovimentacao:
    _ = equipe
    _ = categoria_destino_tier
    config = PROMOCAO_CONFIG
    car_delta = _roll(config, "car_performance")
    budget_delta = _roll(config, "budget")
    facilities_delta = _roll(config, "facilities")
    engineering_delta = _roll(config, "engineering")
    reputacao_delta = _roll(config, "reputacao")
    return ConsequenciasMovimentacao(
        tipo=TipoMovimentacao.PROMOCAO,
        car_performance_delta=car_delta,
        budget_delta=budget_delta,
        facilities_delta=facilities_delta,
        engineering_delta=engineering_delta,
        morale_novo=float(config["morale"]),
        reputacao_delta=reputacao_delta,
        descricao=(
            f"Promocao: car +{car_delta}, budget +{budget_delta}, "
            f"facilities +{facilities_delta}."
        ),
    )


def calcular_consequencias_rebaixamento(equipe: Any, categoria_destino_tier: int) -> ConsequenciasMovimentacao:
    _ = equipe
    _ = categoria_destino_tier
    config = REBAIXAMENTO_CONFIG
    car_delta = _roll(config, "car_performance")
    budget_delta = _roll(config, "budget")
    facilities_delta = _roll(config, "facilities")
    engineering_delta = _roll(config, "engineering")
    reputacao_delta = _roll(config, "reputacao")
    return ConsequenciasMovimentacao(
        tipo=TipoMovimentacao.REBAIXAMENTO,
        car_performance_delta=car_delta,
        budget_delta=budget_delta,
        facilities_delta=facilities_delta,
        engineering_delta=engineering_delta,
        morale_novo=float(config["morale"]),
        reputacao_delta=reputacao_delta,
        descricao=(
            f"Rebaixamento: car {car_delta}, budget {budget_delta}, "
            f"facilities {facilities_delta}."
        ),
    )


def _get(equipe: Any, campo: str, default=None):
    if isinstance(equipe, dict):
        return equipe.get(campo, default)
    return getattr(equipe, campo, default)


def _set(equipe: Any, campo: str, valor):
    if isinstance(equipe, dict):
        equipe[campo] = valor
    else:
        setattr(equipe, campo, valor)


def aplicar_consequencias(equipe: Any, consequencias: ConsequenciasMovimentacao) -> Dict[str, Dict[str, float]]:
    mudancas: Dict[str, Dict[str, float]] = {}

    def apply_delta(campo: str, delta: float, min_v: float, max_v: float):
        atual = float(_get(equipe, campo, 0.0) or 0.0)
        novo = max(min_v, min(max_v, atual + float(delta)))
        _set(equipe, campo, round(novo, 3))
        mudancas[campo] = {"antes": atual, "depois": novo}

    if _get(equipe, "car_performance", None) is not None:
        apply_delta("car_performance", consequencias.car_performance_delta, 30, 100)

    if _get(equipe, "budget", None) is not None:
        apply_delta("budget", consequencias.budget_delta, 10, 100)
        if _get(equipe, "orcamento", None) is not None:
            _set(equipe, "orcamento", _get(equipe, "budget", 10))

    if _get(equipe, "facilities", None) is not None:
        apply_delta("facilities", consequencias.facilities_delta, 20, 100)

    if _get(equipe, "engineering_quality", None) is not None:
        apply_delta("engineering_quality", consequencias.engineering_delta, 20, 100)

    if _get(equipe, "morale", None) is not None:
        atual = float(_get(equipe, "morale", 1.0) or 1.0)
        novo = float(consequencias.morale_novo)
        _set(equipe, "morale", round(novo, 3))
        mudancas["morale"] = {"antes": atual, "depois": novo}

    if _get(equipe, "reputacao", None) is not None:
        apply_delta("reputacao", consequencias.reputacao_delta, 0, 100)

    return mudancas


def simular_impacto(equipe: Any, tipo: TipoMovimentacao, categoria_destino_tier: int) -> ConsequenciasMovimentacao:
    if tipo == TipoMovimentacao.PROMOCAO:
        return calcular_consequencias_promocao(equipe, categoria_destino_tier)
    if tipo == TipoMovimentacao.REBAIXAMENTO:
        return calcular_consequencias_rebaixamento(equipe, categoria_destino_tier)
    return ConsequenciasMovimentacao(tipo=TipoMovimentacao.PERMANENCIA)
