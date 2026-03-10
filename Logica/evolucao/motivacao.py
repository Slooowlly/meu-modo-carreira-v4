"""
Sistema de motivacao dinamica.

A motivacao e atualizada durante a temporada e afeta:
- Taxa de crescimento de skills
- Chance de aposentadoria
- Comportamento em corridas
"""

from dataclasses import dataclass
from typing import Optional

from .models import ContextoTemporada


MIN_MOTIVACAO = 0.0
MAX_MOTIVACAO = 100.0

VARIACOES = {
    "vitoria": 10.0,
    "podio": 5.0,
    "acima_expectativa": 5.0,
    "pole_position": 3.0,
    "promocao": 15.0,
    "renovacao_time_bom": 8.0,
    "titulo": 20.0,
    "resultado_ruim": -3.0,
    "dnf_erro_proprio": -5.0,
    "dnf_mecanico": -2.0,
    "perde_vaga_para_jovem": -10.0,
    "rebaixamento": -8.0,
    "estagnacao": -2.0,
    "nao_renova": -5.0,
}


@dataclass
class AjusteMotivacao:
    """Registro de ajuste de motivacao."""

    valor: float
    motivo: str

    def __str__(self):
        sinal = "+" if self.valor >= 0 else ""
        return f"{sinal}{self.valor:.1f} ({self.motivo})"


def clamp_motivacao(valor: float) -> float:
    """Limita motivacao entre 0 e 100."""
    return max(MIN_MOTIVACAO, min(MAX_MOTIVACAO, valor))


def calcular_ajustes_corrida(
    posicao: int,
    expectativa: int,
    foi_vitoria: bool,
    foi_podio: bool,
    foi_pole: bool,
    foi_dnf: bool,
    dnf_erro_proprio: bool,
) -> list[AjusteMotivacao]:
    """
    Calcula ajustes de motivacao apos uma corrida.
    """
    ajustes: list[AjusteMotivacao] = []

    if foi_vitoria:
        ajustes.append(AjusteMotivacao(VARIACOES["vitoria"], "vitoria"))
    elif foi_podio:
        ajustes.append(AjusteMotivacao(VARIACOES["podio"], "podio"))

    if foi_pole:
        ajustes.append(AjusteMotivacao(VARIACOES["pole_position"], "pole position"))

    if not foi_dnf:
        diferenca = expectativa - posicao
        if diferenca >= 3:
            ajustes.append(
                AjusteMotivacao(VARIACOES["acima_expectativa"], "superou expectativas")
            )
        elif diferenca <= -5:
            ajustes.append(
                AjusteMotivacao(VARIACOES["resultado_ruim"], "abaixo das expectativas")
            )

    if foi_dnf:
        if dnf_erro_proprio:
            ajustes.append(AjusteMotivacao(VARIACOES["dnf_erro_proprio"], "abandono por erro"))
        else:
            ajustes.append(AjusteMotivacao(VARIACOES["dnf_mecanico"], "abandono mecanico"))

    return ajustes


def calcular_ajustes_fim_temporada(ctx: ContextoTemporada) -> list[AjusteMotivacao]:
    """
    Calcula ajustes de motivacao no fim da temporada.
    """
    ajustes: list[AjusteMotivacao] = []

    if ctx.foi_promovido:
        ajustes.append(AjusteMotivacao(VARIACOES["promocao"], "promocao de categoria"))
    elif ctx.foi_rebaixado:
        ajustes.append(AjusteMotivacao(VARIACOES["rebaixamento"], "rebaixamento"))

    if ctx.renovou_contrato:
        if ctx.time_bom:
            ajustes.append(
                AjusteMotivacao(VARIACOES["renovacao_time_bom"], "renovou com time bom")
            )
    else:
        ajustes.append(AjusteMotivacao(VARIACOES["nao_renova"], "nao renovou"))

    if ctx.perdeu_vaga_para_jovem:
        ajustes.append(
            AjusteMotivacao(VARIACOES["perde_vaga_para_jovem"], "perdeu vaga para jovem")
        )

    if ctx.posicao_campeonato == 1:
        ajustes.append(AjusteMotivacao(VARIACOES["titulo"], "titulo"))

    return ajustes


def calcular_estagnacao(
    temporadas_na_categoria: int,
    categoria_tier: int,
) -> Optional[AjusteMotivacao]:
    """
    Calcula penalidade de estagnacao por temporadas na categoria.
    """
    if categoria_tier >= 7:
        return None
    if temporadas_na_categoria <= 2:
        return None

    penalidade = VARIACOES["estagnacao"] * (temporadas_na_categoria - 2)
    return AjusteMotivacao(
        penalidade,
        f"estagnacao ({temporadas_na_categoria} temporadas)",
    )


def atualizar_motivacao_corrida(
    motivacao_atual: float,
    posicao: int,
    expectativa: int,
    foi_vitoria: bool = False,
    foi_podio: bool = False,
    foi_pole: bool = False,
    foi_dnf: bool = False,
    dnf_erro_proprio: bool = False,
) -> tuple[float, list[AjusteMotivacao]]:
    """
    Atualiza motivacao apos corrida.
    """
    ajustes = calcular_ajustes_corrida(
        posicao=posicao,
        expectativa=expectativa,
        foi_vitoria=foi_vitoria,
        foi_podio=foi_podio,
        foi_pole=foi_pole,
        foi_dnf=foi_dnf,
        dnf_erro_proprio=dnf_erro_proprio,
    )

    total = sum(a.valor for a in ajustes)
    return clamp_motivacao(motivacao_atual + total), ajustes


def atualizar_motivacao_fim_temporada(
    motivacao_atual: float,
    ctx: ContextoTemporada,
    temporadas_na_categoria: int,
) -> tuple[float, list[AjusteMotivacao]]:
    """
    Atualiza motivacao no fim da temporada.
    """
    ajustes = calcular_ajustes_fim_temporada(ctx)
    estagnacao = calcular_estagnacao(temporadas_na_categoria, ctx.categoria_tier)
    if estagnacao is not None:
        ajustes.append(estagnacao)

    total = sum(a.valor for a in ajustes)
    return clamp_motivacao(motivacao_atual + total), ajustes


def calcular_motivacao_media_temporada(motivacoes: list[float]) -> float:
    """
    Calcula media de motivacao da temporada.
    """
    if not motivacoes:
        return 50.0
    return sum(motivacoes) / len(motivacoes)

