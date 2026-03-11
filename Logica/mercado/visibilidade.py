"""
Sistema de visibilidade de pilotos no mercado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VISIBILIDADE_CONFIG = {
    "posicao_top_3": 4.0,
    "posicao_top_5": 3.0,
    "posicao_top_10": 2.0,
    "posicao_top_50_pct": 1.0,
    "tier_bonus_por_nivel": 0.3,
    "idade_jovem_bonus": 2.0,
    "idade_prime_bonus": 1.0,
    "idade_veterano_penalty": -1.0,
    "vitoria_bonus": 0.5,
    "titulo_bonus": 2.0,
    "pole_bonus": 0.2,
    "sub_tier_advanced": 1.5,
    "producao_talento": 1.0,
}

MIN_VISIBILIDADE = 0.0
MAX_VISIBILIDADE = 10.0

CATEGORIAS_INVISIVEIS = ["mazda_rookie", "toyota_rookie"]


def _get(piloto: Any, campo: str, default=None):
    if isinstance(piloto, dict):
        return piloto.get(campo, default)
    return getattr(piloto, campo, default)


def _papel_normalizado(piloto: Any) -> str:
    papel = str(_get(piloto, "papel", "") or "").strip().lower()
    if papel in {"n1", "numero_1"}:
        return "numero_1"
    if papel in {"n2", "numero_2"}:
        return "numero_2"
    return papel


@dataclass
class CalculoVisibilidade:
    """Detalhes do calculo de visibilidade."""

    piloto_id: str
    visibilidade_base: float = 3.0
    bonus_posicao: float = 0.0
    bonus_tier: float = 0.0
    bonus_idade: float = 0.0
    bonus_vitorias: float = 0.0
    bonus_titulos: float = 0.0
    bonus_outros: float = 0.0
    penalidades: float = 0.0
    visibilidade_final: float = 0.0

    def calcular_total(self) -> float:
        total = (
            self.visibilidade_base
            + self.bonus_posicao
            + self.bonus_tier
            + self.bonus_idade
            + self.bonus_vitorias
            + self.bonus_titulos
            + self.bonus_outros
            + self.penalidades
        )
        self.visibilidade_final = max(MIN_VISIBILIDADE, min(MAX_VISIBILIDADE, total))
        return self.visibilidade_final


def calcular_bonus_posicao(posicao: int, total_pilotos: int) -> float:
    """Calcula bonus baseado na posicao no campeonato."""
    if posicao <= 0 or total_pilotos <= 0:
        return 0.0

    if posicao <= 3:
        return VISIBILIDADE_CONFIG["posicao_top_3"]
    if posicao <= 5:
        return VISIBILIDADE_CONFIG["posicao_top_5"]
    if posicao <= 10:
        return VISIBILIDADE_CONFIG["posicao_top_10"]
    if posicao <= total_pilotos * 0.5:
        return VISIBILIDADE_CONFIG["posicao_top_50_pct"]
    return 0.0


def calcular_bonus_idade(idade: int) -> float:
    """Calcula bonus/penalidade por idade."""
    if idade < 23:
        return VISIBILIDADE_CONFIG["idade_jovem_bonus"]
    if idade <= 28:
        return VISIBILIDADE_CONFIG["idade_prime_bonus"]
    if idade > 35:
        return VISIBILIDADE_CONFIG["idade_veterano_penalty"]
    return 0.0


def calcular_bonus_resultados(vitorias: int, titulos: int, poles: int = 0) -> tuple[float, float]:
    """Calcula bonus por resultados."""
    bonus_vitorias = min(vitorias, 3) * VISIBILIDADE_CONFIG["vitoria_bonus"]
    bonus_titulos = min(titulos, 2) * VISIBILIDADE_CONFIG["titulo_bonus"]
    bonus_poles = min(poles, 2) * VISIBILIDADE_CONFIG["pole_bonus"]
    return bonus_vitorias + bonus_poles, bonus_titulos


def calcular_visibilidade(
    piloto: Any,
    categoria_tier: int = 1,
    posicao_campeonato: int = 0,
    total_pilotos_categoria: int = 20,
    vitorias_temporada: int = 0,
    poles_temporada: int = 0,
    is_advanced_subtier: bool = False,
) -> CalculoVisibilidade:
    """
    Calcula visibilidade completa de um piloto.
    """
    calc = CalculoVisibilidade(piloto_id=str(_get(piloto, "id", id(piloto))))

    idade = int(_get(piloto, "idade", 25) or 25)
    calc.bonus_idade = calcular_bonus_idade(idade)

    calc.bonus_posicao = calcular_bonus_posicao(posicao_campeonato, total_pilotos_categoria)

    calc.bonus_tier = (max(1, categoria_tier) - 1) * VISIBILIDADE_CONFIG["tier_bonus_por_nivel"]

    titulos = int(_get(piloto, "titulos", 0) or 0)
    calc.bonus_vitorias, calc.bonus_titulos = calcular_bonus_resultados(
        vitorias_temporada,
        titulos,
        poles_temporada,
    )

    if is_advanced_subtier:
        calc.bonus_outros += VISIBILIDADE_CONFIG["sub_tier_advanced"]

    # M9: piloto N2 perde exposicao no mercado.
    if _papel_normalizado(piloto) == "numero_2":
        calc.penalidades -= 2.0

    calc.calcular_total()
    return calc


def piloto_e_visivel_para_categoria(
    visibilidade: float,
    categoria_origem_tier: int,
    categoria_destino_tier: int,
    is_prodigio: bool = False,
) -> bool:
    """
    Verifica se piloto e visivel para uma categoria de destino.
    """
    if visibilidade < 4.0:
        return False

    diferenca = int(categoria_destino_tier) - int(categoria_origem_tier)
    max_salto = 2 if is_prodigio else 1
    return diferenca <= max_salto


def filtrar_pilotos_visiveis(pilotos: list[Any], categoria_destino_tier: int) -> list[Any]:
    """Filtra pilotos visiveis para a categoria de destino."""
    visiveis: list[Any] = []
    for piloto in pilotos:
        visibilidade = float(_get(piloto, "visibilidade", 5.0) or 5.0)
        tier_atual = int(_get(piloto, "categoria_tier", 1) or 1)
        is_prodigio = bool(_get(piloto, "is_prodigio", False))
        if piloto_e_visivel_para_categoria(
            visibilidade,
            tier_atual,
            categoria_destino_tier,
            is_prodigio,
        ):
            visiveis.append(piloto)
    return visiveis


def categoria_permite_mercado_externo(categoria_id: str) -> bool:
    """Verifica se categoria permite visibilidade externa."""
    return str(categoria_id or "").strip().lower() not in CATEGORIAS_INVISIVEIS
