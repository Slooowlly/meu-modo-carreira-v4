"""
Sistema de lesoes.

Lesoes podem ocorrer apos incidentes:
- Lesao leve: -5% skill por 2 corridas
- Lesao moderada: -10% skill por 3-5 corridas
- Lesao grave: perde corridas + chance de aposentadoria
"""

import random
from typing import Optional

from .models import Lesao, LesaoTipo


CHANCE_LESAO = {
    "colisao": 0.15,
    "capotagem": 0.30,
    "batida_forte": 0.25,
    "saida_pista": 0.05,
}

DISTRIBUICAO_SEVERIDADE = {
    LesaoTipo.LEVE: 0.60,
    LesaoTipo.MODERADA: 0.30,
    LesaoTipo.GRAVE: 0.10,
}

CONFIG_LESAO = {
    LesaoTipo.LEVE: {
        "corridas": (2, 2),
        "penalidade": 0.05,
    },
    LesaoTipo.MODERADA: {
        "corridas": (3, 5),
        "penalidade": 0.10,
    },
    LesaoTipo.GRAVE: {
        "corridas": (6, 10),
        "penalidade": 0.15,
    },
}


def verificar_lesao(
    tipo_incidente: str,
    velocidade_impacto: float = 1.0,
) -> Optional[Lesao]:
    """
    Verifica se um incidente causa lesao.
    """
    chance_base = CHANCE_LESAO.get(tipo_incidente, 0.10)
    chance = chance_base * max(0.0, velocidade_impacto)

    if random.random() >= chance:
        return None

    roll = random.random()
    acumulado = 0.0
    severidade = LesaoTipo.LEVE

    for tipo, prob in DISTRIBUICAO_SEVERIDADE.items():
        acumulado += prob
        if roll < acumulado:
            severidade = tipo
            break

    config = CONFIG_LESAO[severidade]
    corridas_min, corridas_max = config["corridas"]

    return Lesao(
        tipo=severidade,
        corridas_restantes=random.randint(corridas_min, corridas_max),
        penalidade_skill=float(config["penalidade"]),
        causa=tipo_incidente,
    )


def aplicar_penalidade_lesao(skill: float, lesao: Lesao) -> float:
    """
    Aplica penalidade de lesao ao skill.
    """
    if not lesao.esta_ativa:
        return skill
    return skill * (1 - lesao.penalidade_skill)


def processar_lesao_pos_corrida(lesao: Optional[Lesao]) -> Optional[Lesao]:
    """
    Reduz contador da lesao apos corrida.
    """
    if lesao is None:
        return None

    lesao.processar_corrida()
    if not lesao.esta_ativa:
        return None
    return lesao


def criar_lesao_manual(
    tipo: LesaoTipo,
    corridas: int,
    causa: str = "acidente",
) -> Lesao:
    """
    Cria lesao manualmente (testes/eventos especiais).
    """
    config = CONFIG_LESAO.get(tipo, CONFIG_LESAO[LesaoTipo.LEVE])
    return Lesao(
        tipo=tipo,
        corridas_restantes=corridas,
        penalidade_skill=float(config["penalidade"]),
        causa=causa,
    )

