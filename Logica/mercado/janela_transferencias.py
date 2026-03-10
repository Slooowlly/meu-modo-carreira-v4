"""
Orquestrador de fases da janela de transferencias.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .decisoes_piloto import piloto_decide_propostas
from .models import PilotoMercado, Proposta, StatusProposta, VagaAberta
from .propostas import gerar_propostas_para_piloto


MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA: dict[str, tuple[str, int]] = {
    # Canonical expanded IDs
    "mazda_rookie": ("mazda_rookie", 1),
    "toyota_rookie": ("toyota_rookie", 1),
    "mazda_amador": ("mazda_amador", 2),
    "toyota_amador": ("toyota_amador", 2),
    "bmw_m2": ("bmw_m2", 3),
    "production_challenger": ("production_challenger", 3),
    "gt4": ("gt4", 4),
    "gt3": ("gt3", 5),
    "endurance": ("endurance", 6),
    # Legacy aliases
    "mx5": ("mazda_rookie", 1),
    "toyotagr86": ("toyota_amador", 2),
    "bmwm2cs": ("bmw_m2", 3),
}

MAPA_CATEGORIA_EXPANDIDA_PARA_ATUAL: dict[str, str] = {
    "mazda_rookie": "mazda_rookie",
    "toyota_rookie": "toyota_rookie",
    "mazda_amador": "mazda_amador",
    "toyota_amador": "toyota_amador",
    "bmw_m2": "bmw_m2",
    "production_challenger": "production_challenger",
    "gt4": "gt4",
    "gt3": "gt3",
    "endurance": "endurance",
}


def mapear_categoria_para_expandida(categoria_id: str) -> tuple[str, int]:
    """Mapeia categoria atual para modelo expandido interno do mercado."""
    categoria = str(categoria_id or "").strip().lower()
    if categoria in MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA:
        return MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA[categoria]
    if categoria in MAPA_CATEGORIA_EXPANDIDA_PARA_ATUAL:
        atual = MAPA_CATEGORIA_EXPANDIDA_PARA_ATUAL[categoria]
        return MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA.get(atual, (categoria, 1))
    return categoria, 1


def mapear_categoria_para_atual(categoria_expandida: str) -> str:
    """Mapeia categoria para id canonico do projeto (schema expandido)."""
    categoria = str(categoria_expandida or "").strip().lower()
    if categoria in MAPA_CATEGORIA_EXPANDIDA_PARA_ATUAL:
        return MAPA_CATEGORIA_EXPANDIDA_PARA_ATUAL[categoria]
    if categoria in MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA:
        return MAPA_CATEGORIA_ATUAL_PARA_EXPANDIDA[categoria][0]
    return "mazda_rookie"


@dataclass
class EstadoMercado:
    """Estado atual do mercado durante processamento."""

    temporada: int
    pilotos_livres: list[PilotoMercado] = field(default_factory=list)
    vagas_abertas: list[VagaAberta] = field(default_factory=list)
    propostas_geradas: list[Proposta] = field(default_factory=list)
    propostas_aceitas_npc: list[Proposta] = field(default_factory=list)
    propostas_recusadas_npc: list[Proposta] = field(default_factory=list)
    pendencias_jogador: list[Proposta] = field(default_factory=list)
    pilotos_sem_vaga: list[str] = field(default_factory=list)


def executar_fase_mercado_aberto(
    estado: EstadoMercado,
    equipes_index: dict[str, Any],
    jogador_id: str | None = None,
) -> EstadoMercado:
    """
    Executa a fase de mercado aberto (propostas e decisoes).
    """
    for piloto in estado.pilotos_livres:
        propostas = gerar_propostas_para_piloto(
            piloto=piloto,
            vagas=estado.vagas_abertas,
            equipes=equipes_index,
        )
        piloto.propostas = list(propostas)
        estado.propostas_geradas.extend(propostas)

        if not propostas:
            estado.pilotos_sem_vaga.append(piloto.id)
            continue

        if jogador_id is not None and str(piloto.id) == str(jogador_id):
            estado.pendencias_jogador.extend(propostas)
            continue

        decisao = piloto_decide_propostas(piloto, propostas)
        if decisao.proposta_aceita:
            estado.propostas_aceitas_npc.append(decisao.proposta_aceita)
            for proposta in propostas:
                if proposta.id != decisao.proposta_aceita.id and proposta.status == StatusProposta.PENDENTE:
                    proposta.status = StatusProposta.RECUSADA
                    estado.propostas_recusadas_npc.append(proposta)
        else:
            estado.propostas_recusadas_npc.extend(decisao.propostas_recusadas)
            estado.pilotos_sem_vaga.append(piloto.id)

    return estado
