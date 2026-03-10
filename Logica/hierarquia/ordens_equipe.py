"""
Sistema de ordens de equipe em corridas simuladas.

Importante: ordens de equipe so afetam corridas simuladas.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple
import random

from .models import EstadoHierarquia, OrdemEquipe, RespostaOrdem, TipoOrdem
from .tensao import calcular_chance_desobediencia


def gerar_ordem_equipe(
    estado: EstadoHierarquia,
    tipo: TipoOrdem,
    posicao_p1: int,
    posicao_p2: int,
    corrida_numero: int,
) -> OrdemEquipe:
    """
    Gera uma ordem de equipe.
    """
    return OrdemEquipe(
        corrida_numero=int(corrida_numero),
        equipe_id=str(estado.equipe_id),
        tipo=tipo,
        piloto_alvo_id=str(estado.piloto_2_id),
        piloto_beneficiado_id=str(estado.piloto_1_id),
        posicao_alvo=int(posicao_p2),
        posicao_beneficiado=int(posicao_p1),
    )


def processar_resposta_ordem(ordem: OrdemEquipe, piloto: Any, tensao_atual: float) -> OrdemEquipe:
    """
    Processa resposta do piloto a uma ordem.
    """
    chance = calcular_chance_desobediencia(
        piloto=piloto,
        tipo_ordem=ordem.tipo.value,
        posicao_atual=ordem.posicao_alvo,
        tensao_atual=tensao_atual,
    )

    roll = random.random()
    if roll < chance * 0.3:
        ordem.resposta = RespostaOrdem.RECUSOU_RADIO
        ordem.posicoes_perdidas = calcular_posicoes_perdidas(ordem.tipo)
        ordem.impacto_moral_equipe = -0.01
        ordem.impacto_relacao_pilotos = -5.0
    elif roll < chance:
        ordem.resposta = RespostaOrdem.IGNOROU
        ordem.posicoes_perdidas = 0
        ordem.impacto_moral_equipe = -0.03
        ordem.impacto_relacao_pilotos = -15.0
    else:
        ordem.resposta = RespostaOrdem.OBEDECEU
        ordem.posicoes_perdidas = calcular_posicoes_perdidas(ordem.tipo)
        ordem.impacto_moral_equipe = 0.01
        ordem.impacto_relacao_pilotos = -2.0

    return ordem


def calcular_posicoes_perdidas(tipo: TipoOrdem) -> int:
    """
    Calcula quantas posicoes o piloto perde ao obedecer.
    """
    if tipo == TipoOrdem.DEIXAR_PASSAR:
        return 1
    if tipo == TipoOrdem.MANTER_POSICAO:
        return 0
    if tipo == TipoOrdem.NAO_ATACAR:
        return 0
    if tipo == TipoOrdem.GESTAO_PNEUS:
        return random.randint(0, 2)
    if tipo == TipoOrdem.RITMO_CONSERVADOR:
        return random.randint(1, 3)
    return 0


def aplicar_ordem_no_resultado(posicao_atual: int, ordem: OrdemEquipe) -> int:
    """
    Aplica efeito da ordem na posicao final.
    """
    if ordem.resposta == RespostaOrdem.IGNOROU:
        return int(posicao_atual)
    return int(posicao_atual) + int(ordem.posicoes_perdidas)


def verificar_necessidade_ordem(
    estado: EstadoHierarquia,
    posicao_p1: int,
    posicao_p2: int,
    voltas_restantes: int,
    diferenca_campeonato: int,
    posicao_p2_original: int,
) -> Optional[TipoOrdem]:
    """
    Verifica se deve emitir ordem de equipe.
    """
    del estado, posicao_p2_original

    if posicao_p2 >= posicao_p1:
        return None

    if voltas_restantes > 10:
        return None

    diferenca = posicao_p1 - posicao_p2

    if 0 <= diferenca_campeonato <= 25:
        if diferenca <= 2 and voltas_restantes <= 5:
            return TipoOrdem.DEIXAR_PASSAR
        if diferenca <= 1:
            return TipoOrdem.DEIXAR_PASSAR
    elif -30 <= diferenca_campeonato < 0:
        if voltas_restantes <= 3:
            return TipoOrdem.DEIXAR_PASSAR

    if posicao_p2 <= 3 and posicao_p1 <= 5 and diferenca == 1:
        if voltas_restantes <= 5:
            return TipoOrdem.DEIXAR_PASSAR

    if diferenca == 1 and voltas_restantes > 5:
        return TipoOrdem.NAO_ATACAR

    return None


def simular_ordens_corrida(
    estado: EstadoHierarquia,
    resultado_p1: int,
    resultado_p2: int,
    piloto_2: Any,
    corrida_numero: int,
    diferenca_campeonato: int,
) -> Tuple[List[OrdemEquipe], int, int]:
    """
    Simula ordens de equipe em uma corrida simulada.
    """
    ordens: List[OrdemEquipe] = []

    if resultado_p2 >= resultado_p1:
        return ordens, resultado_p1, resultado_p2

    tipo_ordem = verificar_necessidade_ordem(
        estado=estado,
        posicao_p1=resultado_p1,
        posicao_p2=resultado_p2,
        voltas_restantes=5,
        diferenca_campeonato=diferenca_campeonato,
        posicao_p2_original=resultado_p2,
    )

    if not tipo_ordem:
        return ordens, resultado_p1, resultado_p2

    ordem = gerar_ordem_equipe(
        estado=estado,
        tipo=tipo_ordem,
        posicao_p1=resultado_p1,
        posicao_p2=resultado_p2,
        corrida_numero=corrida_numero,
    )
    ordem = processar_resposta_ordem(ordem=ordem, piloto=piloto_2, tensao_atual=estado.nivel_tensao)
    ordens.append(ordem)

    if ordem.resposta != RespostaOrdem.IGNOROU:
        resultado_p2_novo = resultado_p2 + ordem.posicoes_perdidas
        if ordem.tipo == TipoOrdem.DEIXAR_PASSAR:
            resultado_p1_novo = resultado_p2
            resultado_p2 = resultado_p2_novo
            resultado_p1 = resultado_p1_novo

    return ordens, resultado_p1, resultado_p2
