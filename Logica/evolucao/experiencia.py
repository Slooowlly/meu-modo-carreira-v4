"""
Sistema de experiencia.

A experiencia e acumulativa e nunca diminui:
- +0.3 por corrida disputada
- +0.1 bonus se top 5
- +0.2 se sobreviveu corrida com muitos incidentes
- Cap em 100
"""

from dataclasses import dataclass


MAX_EXPERIENCIA = 100.0

GANHO_POR_CORRIDA = 0.3
GANHO_TOP5 = 0.1
GANHO_SOBREVIVER_INCIDENTES = 0.2

THRESHOLD_INCIDENTES = 5


@dataclass
class GanhoExperiencia:
    """Registro de ganho de experiencia."""

    valor: float
    motivo: str

    def __str__(self):
        return f"+{self.valor:.2f} ({self.motivo})"


def calcular_ganho_corrida(
    posicao: int,
    total_incidentes_corrida: int,
    piloto_teve_incidente: bool,
) -> list[GanhoExperiencia]:
    """
    Calcula ganhos de experiencia apos corrida.
    """
    ganhos = [GanhoExperiencia(GANHO_POR_CORRIDA, "corrida disputada")]

    if posicao <= 5:
        ganhos.append(GanhoExperiencia(GANHO_TOP5, "top 5"))

    if total_incidentes_corrida >= THRESHOLD_INCIDENTES and not piloto_teve_incidente:
        ganhos.append(
            GanhoExperiencia(
                GANHO_SOBREVIVER_INCIDENTES,
                "sobreviveu corrida caotica",
            )
        )

    return ganhos


def atualizar_experiencia(
    experiencia_atual: float,
    posicao: int,
    total_incidentes_corrida: int = 0,
    piloto_teve_incidente: bool = False,
) -> tuple[float, list[GanhoExperiencia]]:
    """
    Atualiza experiencia apos corrida.
    """
    ganhos = calcular_ganho_corrida(
        posicao=posicao,
        total_incidentes_corrida=total_incidentes_corrida,
        piloto_teve_incidente=piloto_teve_incidente,
    )

    total = sum(g.valor for g in ganhos)
    nova_experiencia = min(experiencia_atual + total, MAX_EXPERIENCIA)
    return nova_experiencia, ganhos


def calcular_experiencia_temporada(corridas: list[dict]) -> float:
    """
    Calcula experiencia total de uma temporada.
    """
    total = 0.0
    for corrida in corridas:
        ganhos = calcular_ganho_corrida(
            posicao=int(corrida.get("posicao", 20)),
            total_incidentes_corrida=int(corrida.get("incidentes_corrida", 0)),
            piloto_teve_incidente=bool(corrida.get("teve_incidente", False)),
        )
        total += sum(g.valor for g in ganhos)
    return total

