"""Eligibility evaluation for team movements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .models import HistoricoEquipe, MotivoMovimentacao, ResultadoTemporada, TipoMovimentacao
from .regras import get_regra_categoria


@dataclass
class AvaliacaoEquipe:
    equipe_id: str
    equipe_nome: str
    categoria_id: str

    posicao: int
    pontos: int
    total_equipes: int

    tipo_movimentacao: TipoMovimentacao = TipoMovimentacao.PERMANENCIA
    motivo: MotivoMovimentacao = MotivoMovimentacao.MEIO_TABELA
    categoria_destino: Optional[str] = None

    elegivel_promocao: bool = False
    elegivel_rebaixamento: bool = False
    elegivel_convite: bool = False

    bloqueado_budget: bool = False
    budget_necessario: float = 0.0
    budget_atual: float = 0.0


def _get(equipe: Any, campo: str, default=None):
    if isinstance(equipe, dict):
        return equipe.get(campo, default)
    return getattr(equipe, campo, default)


def criar_resultado_temporada(
    equipe: Any,
    posicao: int,
    pontos: int,
    total_equipes: int,
    temporada: int,
    vitorias: int = 0,
    podios: int = 0,
    poles: int = 0,
) -> ResultadoTemporada:
    categoria = _get(equipe, "categoria", _get(equipe, "categoria_id", ""))
    tier = int(_get(equipe, "categoria_tier", _get(equipe, "tier", 1)) or 1)
    classe_endurance = str(_get(equipe, "classe_endurance", "") or "")
    return ResultadoTemporada(
        equipe_id=str(_get(equipe, "id", str(id(equipe)))),
        equipe_nome=str(_get(equipe, "nome", "Unknown")),
        categoria_id=str(categoria),
        categoria_tier=tier,
        temporada=int(temporada),
        posicao_construtores=int(posicao),
        pontos_construtores=int(pontos),
        total_equipes=int(total_equipes),
        vitorias=int(vitorias),
        podios=int(podios),
        poles=int(poles),
        classe_endurance=classe_endurance,
    )


def avaliar_elegibilidade_promocao(
    resultado: ResultadoTemporada,
    budget_equipe: float,
    historico: Optional[HistoricoEquipe] = None,
    vagas_promocao_override: Optional[int] = None,
) -> Tuple[bool, MotivoMovimentacao, bool]:
    regra = get_regra_categoria(resultado.categoria_id)
    if not regra or not regra.categoria_destino_promocao:
        return False, MotivoMovimentacao.MEIO_TABELA, False

    vagas = int(vagas_promocao_override if vagas_promocao_override is not None else regra.vagas_promocao)

    # Evita sobreposição entre zona de promoção e zona de rebaixamento em grids pequenos.
    if int(resultado.total_equipes) > 0 and int(regra.vagas_rebaixamento) > 0:
        max_promovidas = max(0, int(resultado.total_equipes) - int(regra.vagas_rebaixamento))
        vagas = min(vagas, max_promovidas)

    if vagas <= 0:
        return False, MotivoMovimentacao.SEM_VAGA_ACIMA, False

    if resultado.posicao_construtores > vagas:
        return False, MotivoMovimentacao.MEIO_TABELA, False

    if resultado.is_campeao:
        motivo = MotivoMovimentacao.CAMPEAO_CONSTRUTORES
    elif resultado.is_vice:
        motivo = MotivoMovimentacao.VICE_CAMPEAO
    else:
        motivo = MotivoMovimentacao.TOP_3_CONSECUTIVO

    if float(budget_equipe) < float(regra.budget_minimo_promocao):
        return True, motivo, True

    return True, motivo, False


def avaliar_elegibilidade_rebaixamento(
    resultado: ResultadoTemporada,
    historico: Optional[HistoricoEquipe] = None,
) -> Tuple[bool, MotivoMovimentacao]:
    regra = get_regra_categoria(resultado.categoria_id)
    if not regra or regra.is_categoria_base or regra.sem_rebaixamento_local:
        return False, MotivoMovimentacao.MEIO_TABELA

    if regra.vagas_rebaixamento <= 0:
        return False, MotivoMovimentacao.MEIO_TABELA

    if resultado.is_ultimo:
        return True, MotivoMovimentacao.ULTIMO_LUGAR

    if resultado.is_penultimo and historico and historico.is_penultimo_consecutivo(regra.temporadas_para_rebaixamento):
        return True, MotivoMovimentacao.PENULTIMO_CONSECUTIVO

    return False, MotivoMovimentacao.MEIO_TABELA


def avaliar_elegibilidade_convite(
    resultado: ResultadoTemporada,
    budget_equipe: float,
    historico: Optional[HistoricoEquipe] = None,
    vagas_promocao_override: Optional[int] = None,
) -> Tuple[bool, bool]:
    regra = get_regra_categoria(resultado.categoria_id)
    if not regra or not regra.permite_convite:
        return False, False

    vagas = int(vagas_promocao_override if vagas_promocao_override is not None else regra.vagas_promocao)
    if resultado.posicao_construtores <= max(0, vagas):
        return False, False

    if not resultado.is_top_3:
        return False, False

    if not historico or not historico.is_top_3_consecutivo(regra.temporadas_para_convite):
        return False, False

    return True, float(budget_equipe) >= float(regra.budget_minimo_promocao)


def avaliar_equipe(
    equipe: Any,
    resultado: ResultadoTemporada,
    historico: Optional[HistoricoEquipe] = None,
    vagas_promocao_override: Optional[int] = None,
) -> AvaliacaoEquipe:
    equipe_id = str(_get(equipe, "id", str(id(equipe))))
    equipe_nome = str(_get(equipe, "nome", "Unknown"))
    budget = float(_get(equipe, "budget", 50.0) or 50.0)

    avaliacao = AvaliacaoEquipe(
        equipe_id=equipe_id,
        equipe_nome=equipe_nome,
        categoria_id=str(resultado.categoria_id),
        posicao=int(resultado.posicao_construtores),
        pontos=int(resultado.pontos_construtores),
        total_equipes=int(resultado.total_equipes),
        budget_atual=budget,
    )

    regra = get_regra_categoria(resultado.categoria_id)
    if not regra:
        return avaliacao

    elegivel_promo, motivo_promo, bloqueado = avaliar_elegibilidade_promocao(
        resultado=resultado,
        budget_equipe=budget,
        historico=historico,
        vagas_promocao_override=vagas_promocao_override,
    )
    avaliacao.elegivel_promocao = elegivel_promo
    avaliacao.bloqueado_budget = bloqueado
    avaliacao.budget_necessario = float(regra.budget_minimo_promocao)

    elegivel_rebaixa, motivo_rebaixa = avaliar_elegibilidade_rebaixamento(resultado, historico)
    avaliacao.elegivel_rebaixamento = elegivel_rebaixa

    elegivel_convite, _tem_budget = avaliar_elegibilidade_convite(
        resultado=resultado,
        budget_equipe=budget,
        historico=historico,
        vagas_promocao_override=vagas_promocao_override,
    )
    avaliacao.elegivel_convite = elegivel_convite

    if elegivel_promo and not bloqueado:
        avaliacao.tipo_movimentacao = TipoMovimentacao.PROMOCAO
        avaliacao.motivo = motivo_promo
        avaliacao.categoria_destino = regra.categoria_destino_promocao
    elif elegivel_promo and bloqueado:
        avaliacao.tipo_movimentacao = TipoMovimentacao.PERMANENCIA
        avaliacao.motivo = MotivoMovimentacao.BUDGET_INSUFICIENTE
    elif elegivel_rebaixa:
        avaliacao.tipo_movimentacao = TipoMovimentacao.REBAIXAMENTO
        avaliacao.motivo = motivo_rebaixa
        avaliacao.categoria_destino = regra.categoria_destino_rebaixamento
    elif elegivel_convite:
        avaliacao.tipo_movimentacao = TipoMovimentacao.CONVITE
        avaliacao.motivo = MotivoMovimentacao.TOP_3_CONSECUTIVO
        avaliacao.categoria_destino = regra.categoria_destino_promocao

    return avaliacao


def avaliar_todas_equipes(
    equipes: List[Any],
    resultados: Dict[str, ResultadoTemporada],
    historicos: Dict[str, HistoricoEquipe],
    vagas_promocao_override: Optional[int] = None,
) -> List[AvaliacaoEquipe]:
    avaliacoes: List[AvaliacaoEquipe] = []
    for equipe in equipes:
        equipe_id = str(_get(equipe, "id", str(id(equipe))))
        resultado = resultados.get(equipe_id)
        if not resultado:
            continue
        historico = historicos.get(equipe_id)
        avaliacoes.append(
            avaliar_equipe(
                equipe=equipe,
                resultado=resultado,
                historico=historico,
                vagas_promocao_override=vagas_promocao_override,
            )
        )
    return avaliacoes
