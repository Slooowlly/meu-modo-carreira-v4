"""Historical registry for promotion/relegation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .models import HistoricoEquipe, Movimentacao, ResultadoTemporada, TipoMovimentacao


@dataclass
class HistoricoGlobal:
    movimentacoes: List[Movimentacao] = field(default_factory=list)
    historicos_equipes: Dict[str, HistoricoEquipe] = field(default_factory=dict)

    def adicionar_movimentacao(self, mov: Movimentacao):
        self.movimentacoes.append(mov)

    def adicionar_resultado_equipe(self, resultado: ResultadoTemporada):
        equipe_id = str(resultado.equipe_id)
        if equipe_id not in self.historicos_equipes:
            self.historicos_equipes[equipe_id] = HistoricoEquipe(equipe_id=equipe_id)
        self.historicos_equipes[equipe_id].adicionar_resultado(resultado)

    def get_historico_equipe(self, equipe_id: str) -> Optional[HistoricoEquipe]:
        return self.historicos_equipes.get(str(equipe_id))

    def get_movimentacoes_temporada(self, temporada: int) -> List[Movimentacao]:
        return [mov for mov in self.movimentacoes if int(mov.temporada) == int(temporada)]

    def get_movimentacoes_equipe(self, equipe_id: str) -> List[Movimentacao]:
        eid = str(equipe_id)
        return [mov for mov in self.movimentacoes if str(mov.equipe_id) == eid]

    def get_promocoes_temporada(self, temporada: int) -> List[Movimentacao]:
        return [
            mov
            for mov in self.movimentacoes
            if int(mov.temporada) == int(temporada) and mov.tipo == TipoMovimentacao.PROMOCAO
        ]

    def get_rebaixamentos_temporada(self, temporada: int) -> List[Movimentacao]:
        return [
            mov
            for mov in self.movimentacoes
            if int(mov.temporada) == int(temporada) and mov.tipo == TipoMovimentacao.REBAIXAMENTO
        ]

    def to_dict(self) -> dict:
        return {
            "movimentacoes": [asdict(item) for item in self.movimentacoes],
            "historicos_equipes": {
                equipe_id: {
                    "equipe_id": hist.equipe_id,
                    "resultados": [asdict(res) for res in hist.resultados],
                }
                for equipe_id, hist in self.historicos_equipes.items()
            },
        }



def criar_movimentacao(
    equipe: Any,
    tipo: TipoMovimentacao,
    motivo,
    temporada: int,
    categoria_origem: str,
    categoria_destino: str,
    posicao: int = 0,
    pontos: int = 0,
    consequencias=None,
) -> Movimentacao:
    from .regras import get_regra_categoria

    if isinstance(equipe, dict):
        equipe_id = str(equipe.get("id", str(id(equipe))))
        equipe_nome = str(equipe.get("nome", "Unknown"))
    else:
        equipe_id = str(getattr(equipe, "id", str(id(equipe))))
        equipe_nome = str(getattr(equipe, "nome", "Unknown"))

    regra_origem = get_regra_categoria(categoria_origem)
    regra_destino = get_regra_categoria(categoria_destino)

    mov = Movimentacao(
        equipe_id=equipe_id,
        equipe_nome=equipe_nome,
        temporada=int(temporada),
        tipo=tipo,
        motivo=motivo,
        categoria_origem_id=str(categoria_origem),
        categoria_origem_tier=int(regra_origem.tier if regra_origem else 1),
        categoria_destino_id=str(categoria_destino),
        categoria_destino_tier=int(regra_destino.tier if regra_destino else 1),
        posicao_final=int(posicao),
        pontos_final=int(pontos),
    )

    if consequencias is not None:
        mov.car_performance_delta = float(consequencias.car_performance_delta)
        mov.budget_delta = float(consequencias.budget_delta)
        mov.morale_delta = float(consequencias.morale_novo) - 1.0
        mov.facilities_delta = float(consequencias.facilities_delta)
        mov.pilotos_que_sairam = list(consequencias.pilotos_clausula_ativada)

    return mov
