"""
Modelos de dados para o sistema de hierarquia numero 1/2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import uuid


class Papel(Enum):
    """Papel do piloto na equipe."""

    NUMERO_1 = "numero_1"
    NUMERO_2 = "numero_2"
    INDEFINIDO = "indefinido"


class StatusTensao(Enum):
    """Status de tensao entre pilotos."""

    ESTAVEL = "estavel"
    COMPETITIVO = "competitivo"
    TENSAO = "tensao"
    REAVALIACAO = "reavaliacao"
    INVERSAO_PENDENTE = "inversao"
    CRISE = "crise"


class TipoOrdem(Enum):
    """Tipos de ordens de equipe."""

    MANTER_POSICAO = "manter_posicao"
    DEIXAR_PASSAR = "deixar_passar"
    NAO_ATACAR = "nao_atacar"
    GESTAO_PNEUS = "gestao_pneus"
    RITMO_CONSERVADOR = "ritmo_conservador"


class RespostaOrdem(Enum):
    """Resposta do piloto para uma ordem de equipe."""

    OBEDECEU = "obedeceu"
    IGNOROU = "ignorou"
    RECUSOU_RADIO = "recusou_radio"


class MotivoHierarquia(Enum):
    """Motivo da definicao da hierarquia."""

    CONTRATO = "contrato"
    SKILL = "skill"
    HISTORICO = "historico"
    SALARIO = "salario"
    EXPERIENCIA = "experiencia"
    RESULTADOS = "resultados"
    INVERSAO = "inversao"


@dataclass
class ComparacaoResultado:
    """Comparacao de resultado entre dois pilotos."""

    corrida_numero: int
    piloto_1_id: str
    piloto_2_id: str
    posicao_piloto_1: int
    posicao_piloto_2: int

    @property
    def piloto_1_venceu_duelo(self) -> bool:
        return self.posicao_piloto_1 < self.posicao_piloto_2

    @property
    def piloto_2_venceu_duelo(self) -> bool:
        return self.posicao_piloto_2 < self.posicao_piloto_1

    @property
    def diferenca(self) -> int:
        # Positivo => P1 melhor, negativo => P2 melhor
        return self.posicao_piloto_2 - self.posicao_piloto_1


@dataclass
class HistoricoHierarquia:
    """Historico de comparacoes da temporada."""

    equipe_id: str
    temporada: int
    piloto_numero_1_id: str
    piloto_numero_2_id: str
    comparacoes: List[ComparacaoResultado] = field(default_factory=list)

    vitorias_duelo_p1: int = 0
    vitorias_duelo_p2: int = 0

    sequencia_atual_p1: int = 0
    sequencia_atual_p2: int = 0
    maior_sequencia_p2: int = 0

    status_tensao: StatusTensao = StatusTensao.ESTAVEL
    houve_inversao: bool = False
    corrida_inversao: Optional[int] = None

    def adicionar_resultado(self, comparacao: ComparacaoResultado):
        self.comparacoes.append(comparacao)

        if comparacao.piloto_1_venceu_duelo:
            self.vitorias_duelo_p1 += 1
            self.sequencia_atual_p1 += 1
            self.sequencia_atual_p2 = 0
        elif comparacao.piloto_2_venceu_duelo:
            self.vitorias_duelo_p2 += 1
            self.sequencia_atual_p2 += 1
            self.sequencia_atual_p1 = 0
            self.maior_sequencia_p2 = max(self.maior_sequencia_p2, self.sequencia_atual_p2)

    @property
    def total_corridas(self) -> int:
        return len(self.comparacoes)

    @property
    def percentual_p1(self) -> float:
        if self.total_corridas == 0:
            return 50.0
        return (self.vitorias_duelo_p1 / self.total_corridas) * 100.0

    @property
    def percentual_p2(self) -> float:
        if self.total_corridas == 0:
            return 50.0
        return (self.vitorias_duelo_p2 / self.total_corridas) * 100.0

    @property
    def p2_dominando(self) -> bool:
        return self.percentual_p2 > 60.0


@dataclass
class OrdemEquipe:
    """Registro de uma ordem de equipe."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    corrida_numero: int = 0
    equipe_id: str = ""

    tipo: TipoOrdem = TipoOrdem.MANTER_POSICAO
    piloto_alvo_id: str = ""
    piloto_beneficiado_id: str = ""

    posicao_alvo: int = 0
    posicao_beneficiado: int = 0

    resposta: Optional[RespostaOrdem] = None
    posicoes_perdidas: int = 0

    impacto_moral_equipe: float = 0.0
    impacto_relacao_pilotos: float = 0.0


@dataclass
class EstadoHierarquia:
    """Estado atual da hierarquia de uma equipe."""

    equipe_id: str
    equipe_nome: str
    temporada: int

    piloto_1_id: str = ""
    piloto_1_nome: str = ""
    piloto_2_id: str = ""
    piloto_2_nome: str = ""

    motivo: MotivoHierarquia = MotivoHierarquia.SKILL
    status_tensao: StatusTensao = StatusTensao.ESTAVEL
    nivel_tensao: float = 0.0
    historico: Optional[HistoricoHierarquia] = None

    hierarquia_definida: bool = False
    inversao_ocorreu: bool = False
    ordens_emitidas: int = 0
    ordens_desobedecidas: int = 0


@dataclass
class ImpactoHierarquia:
    """Impactos de ser numero 1 ou numero 2."""

    papel: Papel
    visibilidade_mod: float = 0.0
    propostas_mod: float = 0.0
    duracao_contrato_mod: int = 0
    prioridade_upgrade: int = 0
    chance_ser_trocado: float = 0.0
    descricao: str = ""


@dataclass
class RelatorioHierarquiaTemporada:
    """Relatorio de hierarquia da temporada."""

    temporada: int
    estados: Dict[str, EstadoHierarquia] = field(default_factory=dict)
    inversoes: List[Tuple[str, int]] = field(default_factory=list)
    crises: List[str] = field(default_factory=list)
    total_ordens: int = 0
    ordens_obedecidas: int = 0
    ordens_ignoradas: int = 0
    destaques: List[str] = field(default_factory=list)

    def adicionar_destaque(self, texto: str):
        self.destaques.append(texto)
