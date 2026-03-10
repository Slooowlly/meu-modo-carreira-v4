"""Data models for team promotion/relegation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import uuid


class TipoMovimentacao(Enum):
    PROMOCAO = "promocao"
    REBAIXAMENTO = "rebaixamento"
    CONVITE = "convite"
    PERMANENCIA = "permanencia"


class MotivoMovimentacao(Enum):
    CAMPEAO_CONSTRUTORES = "campeao_construtores"
    VICE_CAMPEAO = "vice_campeao"
    TOP_3_CONSECUTIVO = "top_3_consecutivo"
    CONVITE_ACEITO = "convite_aceito"

    ULTIMO_LUGAR = "ultimo_lugar"
    PENULTIMO_CONSECUTIVO = "penultimo_consecutivo"
    BUDGET_INSUFICIENTE = "budget_insuficiente"
    DESISTENCIA = "desistencia"

    MEIO_TABELA = "meio_tabela"
    CONVITE_RECUSADO = "convite_recusado"
    SEM_VAGA_ACIMA = "sem_vaga_acima"


class StatusConvite(Enum):
    PENDENTE = "pendente"
    ACEITO = "aceito"
    RECUSADO = "recusado"
    EXPIRADO = "expirado"


@dataclass
class ResultadoTemporada:
    equipe_id: str
    equipe_nome: str
    categoria_id: str
    categoria_tier: int
    temporada: int

    posicao_construtores: int
    pontos_construtores: int
    total_equipes: int

    vitorias: int = 0
    podios: int = 0
    poles: int = 0
    classe_endurance: str = ""

    @property
    def is_campeao(self) -> bool:
        return self.posicao_construtores == 1

    @property
    def is_vice(self) -> bool:
        return self.posicao_construtores == 2

    @property
    def is_top_3(self) -> bool:
        return self.posicao_construtores <= 3

    @property
    def is_ultimo(self) -> bool:
        return self.posicao_construtores == self.total_equipes

    @property
    def is_penultimo(self) -> bool:
        return self.posicao_construtores == max(1, self.total_equipes - 1)


@dataclass
class HistoricoEquipe:
    equipe_id: str
    resultados: List[ResultadoTemporada] = field(default_factory=list)

    def adicionar_resultado(self, resultado: ResultadoTemporada):
        self.resultados.append(resultado)

    def get_ultimas_temporadas(self, n: int) -> List[ResultadoTemporada]:
        return sorted(self.resultados, key=lambda item: item.temporada, reverse=True)[:n]

    def is_top_3_consecutivo(self, temporadas: int = 2) -> bool:
        ultimas = self.get_ultimas_temporadas(temporadas)
        if len(ultimas) < temporadas:
            return False
        return all(item.is_top_3 for item in ultimas)

    def is_penultimo_consecutivo(self, temporadas: int = 2) -> bool:
        ultimas = self.get_ultimas_temporadas(temporadas)
        if len(ultimas) < temporadas:
            return False
        return all(item.is_penultimo for item in ultimas)


@dataclass
class Convite:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    equipe_id: str = ""
    equipe_nome: str = ""

    categoria_origem_id: str = ""
    categoria_origem_tier: int = 0
    categoria_destino_id: str = ""
    categoria_destino_tier: int = 0

    temporada: int = 0
    motivo: MotivoMovimentacao = MotivoMovimentacao.TOP_3_CONSECUTIVO

    status: StatusConvite = StatusConvite.PENDENTE

    budget_minimo: float = 0.0
    budget_equipe: float = 0.0

    @property
    def pode_aceitar(self) -> bool:
        return self.budget_equipe >= self.budget_minimo


@dataclass
class Movimentacao:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    equipe_id: str = ""
    equipe_nome: str = ""
    temporada: int = 0

    tipo: TipoMovimentacao = TipoMovimentacao.PERMANENCIA
    motivo: MotivoMovimentacao = MotivoMovimentacao.MEIO_TABELA

    categoria_origem_id: str = ""
    categoria_origem_tier: int = 0
    categoria_destino_id: str = ""
    categoria_destino_tier: int = 0

    posicao_final: int = 0
    pontos_final: int = 0

    car_performance_delta: float = 0.0
    budget_delta: float = 0.0
    morale_delta: float = 0.0
    facilities_delta: float = 0.0

    pilotos_que_sairam: List[str] = field(default_factory=list)
    pilotos_que_ficaram: List[str] = field(default_factory=list)


@dataclass
class ConsequenciasMovimentacao:
    tipo: TipoMovimentacao

    car_performance_delta: float = 0.0
    budget_delta: float = 0.0
    facilities_delta: float = 0.0
    engineering_delta: float = 0.0
    morale_novo: float = 1.0
    reputacao_delta: float = 0.0

    pilotos_podem_sair: List[str] = field(default_factory=list)
    pilotos_clausula_ativada: List[str] = field(default_factory=list)

    descricao: str = ""


@dataclass
class RelatorioPromocao:
    temporada: int

    promocoes: List[Movimentacao] = field(default_factory=list)
    rebaixamentos: List[Movimentacao] = field(default_factory=list)
    convites_enviados: List[Convite] = field(default_factory=list)
    convites_aceitos: List[Convite] = field(default_factory=list)
    convites_recusados: List[Convite] = field(default_factory=list)

    total_equipes_promovidas: int = 0
    total_equipes_rebaixadas: int = 0
    total_pilotos_liberados: int = 0

    destaques: List[str] = field(default_factory=list)

    def adicionar_destaque(self, texto: str):
        self.destaques.append(str(texto))

    def get_resumo(self) -> str:
        linhas = [
            f"=== Movimentacoes Temporada {self.temporada} ===",
            "",
            f"Promocoes: {len(self.promocoes)}",
            f"Rebaixamentos: {len(self.rebaixamentos)}",
            f"Convites enviados: {len(self.convites_enviados)}",
            f"Convites aceitos: {len(self.convites_aceitos)}",
            "",
            "Destaques:",
        ]
        for destaque in self.destaques:
            linhas.append(f"  - {destaque}")
        return "\n".join(linhas)
