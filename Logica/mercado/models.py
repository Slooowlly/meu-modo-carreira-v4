"""
Modelos de dados para o sistema de mercado de transferencias.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class StatusPiloto(Enum):
    """Status do piloto no mercado."""

    CONTRATADO = "contratado"
    LIVRE = "livre"
    RESERVA = "reserva"
    APOSENTADO = "aposentado"
    LESIONADO = "lesionado"


class StatusContrato(Enum):
    """Status de um contrato."""

    ATIVO = "ativo"
    EXPIRADO = "expirado"
    RESCINDIDO = "rescindido"
    PENDENTE = "pendente"


class PapelEquipe(Enum):
    """Papel do piloto na equipe."""

    NUMERO_1 = "numero_1"
    NUMERO_2 = "numero_2"
    RESERVA = "reserva"


class TipoClausula(Enum):
    """Tipos de clausulas contratuais."""

    SAIDA_REBAIXAMENTO = "saida_rebaixamento"
    PERFORMANCE = "performance"
    COMPRA = "compra"


class StatusProposta(Enum):
    """Status de uma proposta."""

    PENDENTE = "pendente"
    ACEITA = "aceita"
    RECUSADA = "recusada"
    EXPIRADA = "expirada"
    RETIRADA = "retirada"


class MotivoRecusa(Enum):
    """Motivos de recusa de proposta."""

    SALARIO_BAIXO = "salario_baixo"
    EQUIPE_FRACA = "equipe_fraca"
    PAPEL_INDESEJADO = "papel_indesejado"
    CATEGORIA_BAIXA = "categoria_baixa"
    PREFERE_OUTRA = "prefere_outra"
    QUER_APOSENTAR = "quer_aposentar"
    LEALDADE_EQUIPE = "lealdade_equipe"


def _enum_value(value):
    if isinstance(value, Enum):
        return value.value
    return value


def _enum_from_value(enum_cls, value, default):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        for item in enum_cls:
            if item.value == normalized:
                return item
    return default


def normalizar_salario_mercado(salario: float) -> float:
    """
    Normaliza salario para score de mercado.

    Compatibilidade:
    - escala curta (10-100)
    - escala longa do jogo (~10k-500k+)
    """
    if salario <= 0:
        return 0.0
    if salario <= 250.0:
        return min(salario / 100.0, 1.0)
    return min(salario / 500_000.0, 1.0)


@dataclass
class Clausula:
    """Uma clausula contratual."""

    tipo: TipoClausula
    valor: Optional[float] = None
    condicao: str = ""
    ativa: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tipo": self.tipo.value,
            "valor": self.valor,
            "condicao": self.condicao,
            "ativa": bool(self.ativa),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Clausula":
        return cls(
            tipo=_enum_from_value(
                TipoClausula,
                data.get("tipo"),
                TipoClausula.PERFORMANCE,
            ),
            valor=data.get("valor"),
            condicao=str(data.get("condicao", "") or ""),
            ativa=bool(data.get("ativa", True)),
        )


@dataclass
class Contrato:
    """Contrato entre piloto e equipe."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    piloto_id: str = ""
    piloto_nome: str = ""
    equipe_id: str = ""
    equipe_nome: str = ""

    temporada_inicio: int = 0
    duracao_anos: int = 1
    temporada_fim: int = 0
    salario_anual: float = 0.0
    papel: PapelEquipe = PapelEquipe.NUMERO_2

    clausulas: list[Clausula] = field(default_factory=list)

    status: StatusContrato = StatusContrato.ATIVO

    def __post_init__(self):
        if self.temporada_fim == 0:
            self.temporada_fim = self.temporada_inicio + self.duracao_anos - 1

    @property
    def esta_ativo(self) -> bool:
        return self.status == StatusContrato.ATIVO

    def tem_clausula(self, tipo: TipoClausula) -> bool:
        return any(c.tipo == tipo and c.ativa for c in self.clausulas)

    def get_clausula(self, tipo: TipoClausula) -> Optional[Clausula]:
        for item in self.clausulas:
            if item.tipo == tipo and item.ativa:
                return item
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "piloto_id": self.piloto_id,
            "piloto_nome": self.piloto_nome,
            "equipe_id": self.equipe_id,
            "equipe_nome": self.equipe_nome,
            "temporada_inicio": int(self.temporada_inicio),
            "duracao_anos": int(self.duracao_anos),
            "temporada_fim": int(self.temporada_fim),
            "salario_anual": float(self.salario_anual),
            "papel": self.papel.value,
            "clausulas": [c.to_dict() for c in self.clausulas],
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contrato":
        clausulas_raw = data.get("clausulas", [])
        clausulas: list[Clausula] = []
        if isinstance(clausulas_raw, list):
            for item in clausulas_raw:
                if isinstance(item, dict):
                    clausulas.append(Clausula.from_dict(item))

        return cls(
            id=str(data.get("id", "") or str(uuid.uuid4())[:8]),
            piloto_id=str(data.get("piloto_id", "") or ""),
            piloto_nome=str(data.get("piloto_nome", "") or ""),
            equipe_id=str(data.get("equipe_id", "") or ""),
            equipe_nome=str(data.get("equipe_nome", "") or ""),
            temporada_inicio=int(data.get("temporada_inicio", 0) or 0),
            duracao_anos=max(1, int(data.get("duracao_anos", 1) or 1)),
            temporada_fim=int(data.get("temporada_fim", 0) or 0),
            salario_anual=float(data.get("salario_anual", 0.0) or 0.0),
            papel=_enum_from_value(PapelEquipe, data.get("papel"), PapelEquipe.NUMERO_2),
            clausulas=clausulas,
            status=_enum_from_value(StatusContrato, data.get("status"), StatusContrato.ATIVO),
        )


@dataclass
class Proposta:
    """Proposta de contrato."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    equipe_id: str = ""
    equipe_nome: str = ""
    piloto_id: str = ""
    piloto_nome: str = ""

    salario_anual: float = 0.0
    duracao_anos: int = 1
    papel: PapelEquipe = PapelEquipe.NUMERO_2
    categoria_id: str = ""
    categoria_tier: int = 1

    car_performance: float = 50.0
    reputacao_equipe: float = 50.0

    clausulas: list[Clausula] = field(default_factory=list)

    status: StatusProposta = StatusProposta.PENDENTE
    motivo_recusa: Optional[MotivoRecusa] = None

    data_criacao: str = field(default_factory=lambda: datetime.now().isoformat())
    prioridade: int = 0

    def calcular_atratividade(self) -> float:
        """
        Calcula atratividade da proposta para o piloto.
        """
        score = 0.0

        score += (max(0.0, min(100.0, self.car_performance)) / 100.0) * 30.0
        score += (max(1, min(7, self.categoria_tier)) / 7.0) * 25.0

        if self.papel == PapelEquipe.NUMERO_1:
            score += 15.0
        elif self.papel == PapelEquipe.NUMERO_2:
            score += 8.0

        score += normalizar_salario_mercado(self.salario_anual) * 15.0
        score += (max(0.0, min(100.0, self.reputacao_equipe)) / 100.0) * 10.0
        score += max(1, min(2, int(self.duracao_anos))) * 2.5

        return float(score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "equipe_id": self.equipe_id,
            "equipe_nome": self.equipe_nome,
            "piloto_id": self.piloto_id,
            "piloto_nome": self.piloto_nome,
            "salario_anual": float(self.salario_anual),
            "duracao_anos": int(self.duracao_anos),
            "papel": self.papel.value,
            "categoria_id": self.categoria_id,
            "categoria_tier": int(self.categoria_tier),
            "car_performance": float(self.car_performance),
            "reputacao_equipe": float(self.reputacao_equipe),
            "clausulas": [c.to_dict() for c in self.clausulas],
            "status": self.status.value,
            "motivo_recusa": self.motivo_recusa.value if self.motivo_recusa else None,
            "data_criacao": self.data_criacao,
            "prioridade": int(self.prioridade),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Proposta":
        clausulas_raw = data.get("clausulas", [])
        clausulas: list[Clausula] = []
        if isinstance(clausulas_raw, list):
            for item in clausulas_raw:
                if isinstance(item, dict):
                    clausulas.append(Clausula.from_dict(item))

        motivo_raw = data.get("motivo_recusa")
        motivo = None
        if motivo_raw is not None:
            motivo = _enum_from_value(MotivoRecusa, motivo_raw, None)

        return cls(
            id=str(data.get("id", "") or str(uuid.uuid4())[:8]),
            equipe_id=str(data.get("equipe_id", "") or ""),
            equipe_nome=str(data.get("equipe_nome", "") or ""),
            piloto_id=str(data.get("piloto_id", "") or ""),
            piloto_nome=str(data.get("piloto_nome", "") or ""),
            salario_anual=float(data.get("salario_anual", 0.0) or 0.0),
            duracao_anos=max(1, int(data.get("duracao_anos", 1) or 1)),
            papel=_enum_from_value(PapelEquipe, data.get("papel"), PapelEquipe.NUMERO_2),
            categoria_id=str(data.get("categoria_id", "") or ""),
            categoria_tier=max(1, int(data.get("categoria_tier", 1) or 1)),
            car_performance=float(data.get("car_performance", 50.0) or 50.0),
            reputacao_equipe=float(data.get("reputacao_equipe", 50.0) or 50.0),
            clausulas=clausulas,
            status=_enum_from_value(StatusProposta, data.get("status"), StatusProposta.PENDENTE),
            motivo_recusa=motivo,
            data_criacao=str(data.get("data_criacao", "") or datetime.now().isoformat()),
            prioridade=int(data.get("prioridade", 0) or 0),
        )


@dataclass
class VagaAberta:
    """Uma vaga aberta em uma equipe."""

    equipe_id: str
    equipe_nome: str
    categoria_id: str
    categoria_tier: int
    papel: PapelEquipe
    car_performance: float
    budget_disponivel: float
    reputacao: float

    skill_minimo: float = 40.0
    skill_maximo: float = 100.0
    idade_maxima: int = 45
    prefere_jovem: bool = False
    prefere_experiente: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "equipe_id": self.equipe_id,
            "equipe_nome": self.equipe_nome,
            "categoria_id": self.categoria_id,
            "categoria_tier": int(self.categoria_tier),
            "papel": self.papel.value,
            "car_performance": float(self.car_performance),
            "budget_disponivel": float(self.budget_disponivel),
            "reputacao": float(self.reputacao),
            "skill_minimo": float(self.skill_minimo),
            "skill_maximo": float(self.skill_maximo),
            "idade_maxima": int(self.idade_maxima),
            "prefere_jovem": bool(self.prefere_jovem),
            "prefere_experiente": bool(self.prefere_experiente),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VagaAberta":
        return cls(
            equipe_id=str(data.get("equipe_id", "") or ""),
            equipe_nome=str(data.get("equipe_nome", "") or ""),
            categoria_id=str(data.get("categoria_id", "") or ""),
            categoria_tier=max(1, int(data.get("categoria_tier", 1) or 1)),
            papel=_enum_from_value(PapelEquipe, data.get("papel"), PapelEquipe.NUMERO_2),
            car_performance=float(data.get("car_performance", 50.0) or 50.0),
            budget_disponivel=float(data.get("budget_disponivel", 50.0) or 50.0),
            reputacao=float(data.get("reputacao", 50.0) or 50.0),
            skill_minimo=float(data.get("skill_minimo", 40.0) or 40.0),
            skill_maximo=float(data.get("skill_maximo", 100.0) or 100.0),
            idade_maxima=int(data.get("idade_maxima", 45) or 45),
            prefere_jovem=bool(data.get("prefere_jovem", False)),
            prefere_experiente=bool(data.get("prefere_experiente", False)),
        )


@dataclass
class PilotoMercado:
    """Representacao de um piloto no mercado."""

    id: str
    nome: str
    idade: int
    nacionalidade: str

    skill: float
    potencial: float
    experience: float

    status: StatusPiloto = StatusPiloto.LIVRE
    equipe_atual_id: Optional[str] = None
    contrato_atual: Optional[Contrato] = None

    visibilidade: float = 5.0
    atratividade: float = 50.0

    categoria_atual: str = ""
    categoria_tier: int = 1
    posicao_campeonato: int = 0
    vitorias_temporada: int = 0
    titulos: int = 0

    salario_minimo: float = 10.0
    prefere_numero_1: bool = False

    propostas: list[Proposta] = field(default_factory=list)

    @property
    def esta_disponivel(self) -> bool:
        return self.status in (StatusPiloto.LIVRE, StatusPiloto.RESERVA)

    def adicionar_proposta(self, proposta: Proposta):
        self.propostas.append(proposta)

    def get_melhor_proposta(self) -> Optional[Proposta]:
        pendentes = [p for p in self.propostas if p.status == StatusProposta.PENDENTE]
        if not pendentes:
            return None
        return max(pendentes, key=lambda item: item.calcular_atratividade())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nome": self.nome,
            "idade": int(self.idade),
            "nacionalidade": self.nacionalidade,
            "skill": float(self.skill),
            "potencial": float(self.potencial),
            "experience": float(self.experience),
            "status": self.status.value,
            "equipe_atual_id": self.equipe_atual_id,
            "contrato_atual": self.contrato_atual.to_dict() if self.contrato_atual else None,
            "visibilidade": float(self.visibilidade),
            "atratividade": float(self.atratividade),
            "categoria_atual": self.categoria_atual,
            "categoria_tier": int(self.categoria_tier),
            "posicao_campeonato": int(self.posicao_campeonato),
            "vitorias_temporada": int(self.vitorias_temporada),
            "titulos": int(self.titulos),
            "salario_minimo": float(self.salario_minimo),
            "prefere_numero_1": bool(self.prefere_numero_1),
            "propostas": [p.to_dict() for p in self.propostas],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PilotoMercado":
        contrato_raw = data.get("contrato_atual")
        contrato = Contrato.from_dict(contrato_raw) if isinstance(contrato_raw, dict) else None
        propostas_raw = data.get("propostas", [])
        propostas: list[Proposta] = []
        if isinstance(propostas_raw, list):
            for item in propostas_raw:
                if isinstance(item, dict):
                    propostas.append(Proposta.from_dict(item))

        return cls(
            id=str(data.get("id", "") or ""),
            nome=str(data.get("nome", "") or ""),
            idade=int(data.get("idade", 25) or 25),
            nacionalidade=str(data.get("nacionalidade", "") or ""),
            skill=float(data.get("skill", 50.0) or 50.0),
            potencial=float(data.get("potencial", 70.0) or 70.0),
            experience=float(data.get("experience", 0.0) or 0.0),
            status=_enum_from_value(StatusPiloto, data.get("status"), StatusPiloto.LIVRE),
            equipe_atual_id=data.get("equipe_atual_id"),
            contrato_atual=contrato,
            visibilidade=float(data.get("visibilidade", 5.0) or 5.0),
            atratividade=float(data.get("atratividade", 50.0) or 50.0),
            categoria_atual=str(data.get("categoria_atual", "") or ""),
            categoria_tier=int(data.get("categoria_tier", 1) or 1),
            posicao_campeonato=int(data.get("posicao_campeonato", 0) or 0),
            vitorias_temporada=int(data.get("vitorias_temporada", 0) or 0),
            titulos=int(data.get("titulos", 0) or 0),
            salario_minimo=float(data.get("salario_minimo", 10.0) or 10.0),
            prefere_numero_1=bool(data.get("prefere_numero_1", False)),
            propostas=propostas,
        )


@dataclass
class ResultadoMercado:
    """Resultado completo da janela de transferencias."""

    temporada: int

    contratos_renovados: list[Contrato] = field(default_factory=list)
    contratos_novos: list[Contrato] = field(default_factory=list)
    pilotos_liberados: list[str] = field(default_factory=list)
    pilotos_aposentados: list[str] = field(default_factory=list)
    pilotos_sem_vaga: list[str] = field(default_factory=list)

    rookies_gerados: list[str] = field(default_factory=list)

    total_propostas: int = 0
    propostas_aceitas: int = 0
    propostas_recusadas: int = 0

    vagas_preenchidas: int = 0
    vagas_nao_preenchidas: int = 0

    movimentacoes_destaque: list[str] = field(default_factory=list)

    def adicionar_destaque(self, texto: str):
        self.movimentacoes_destaque.append(str(texto))

    def to_dict(self) -> dict[str, Any]:
        return {
            "temporada": int(self.temporada),
            "contratos_renovados": [c.to_dict() for c in self.contratos_renovados],
            "contratos_novos": [c.to_dict() for c in self.contratos_novos],
            "pilotos_liberados": list(self.pilotos_liberados),
            "pilotos_aposentados": list(self.pilotos_aposentados),
            "pilotos_sem_vaga": list(self.pilotos_sem_vaga),
            "rookies_gerados": list(self.rookies_gerados),
            "total_propostas": int(self.total_propostas),
            "propostas_aceitas": int(self.propostas_aceitas),
            "propostas_recusadas": int(self.propostas_recusadas),
            "vagas_preenchidas": int(self.vagas_preenchidas),
            "vagas_nao_preenchidas": int(self.vagas_nao_preenchidas),
            "movimentacoes_destaque": list(self.movimentacoes_destaque),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResultadoMercado":
        renovados = [
            Contrato.from_dict(item)
            for item in data.get("contratos_renovados", [])
            if isinstance(item, dict)
        ]
        novos = [
            Contrato.from_dict(item)
            for item in data.get("contratos_novos", [])
            if isinstance(item, dict)
        ]
        return cls(
            temporada=int(data.get("temporada", 0) or 0),
            contratos_renovados=renovados,
            contratos_novos=novos,
            pilotos_liberados=list(data.get("pilotos_liberados", []) or []),
            pilotos_aposentados=list(data.get("pilotos_aposentados", []) or []),
            pilotos_sem_vaga=list(data.get("pilotos_sem_vaga", []) or []),
            rookies_gerados=list(data.get("rookies_gerados", []) or []),
            total_propostas=int(data.get("total_propostas", 0) or 0),
            propostas_aceitas=int(data.get("propostas_aceitas", 0) or 0),
            propostas_recusadas=int(data.get("propostas_recusadas", 0) or 0),
            vagas_preenchidas=int(data.get("vagas_preenchidas", 0) or 0),
            vagas_nao_preenchidas=int(data.get("vagas_nao_preenchidas", 0) or 0),
            movimentacoes_destaque=list(data.get("movimentacoes_destaque", []) or []),
        )


@dataclass
class EstadoMercadoPersistido:
    """Estado persistido em banco['mercado']."""

    versao: int = 1
    contratos_ativos: list[Contrato] = field(default_factory=list)
    historico_janelas: list[ResultadoMercado] = field(default_factory=list)
    propostas_atuais: list[Proposta] = field(default_factory=list)
    vagas_abertas: list[VagaAberta] = field(default_factory=list)
    reserva_global: list[str] = field(default_factory=list)
    rookies_gerados: list[str] = field(default_factory=list)
    pendencias_jogador: list[Proposta] = field(default_factory=list)
    janela_aberta: bool = False
    temporada_janela: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "versao": int(self.versao),
            "contratos_ativos": [c.to_dict() for c in self.contratos_ativos],
            "historico_janelas": [h.to_dict() for h in self.historico_janelas],
            "propostas_atuais": [p.to_dict() for p in self.propostas_atuais],
            "vagas_abertas": [v.to_dict() for v in self.vagas_abertas],
            "reserva_global": list(self.reserva_global),
            "rookies_gerados": list(self.rookies_gerados),
            "pendencias_jogador": [p.to_dict() for p in self.pendencias_jogador],
            "janela_aberta": bool(self.janela_aberta),
            "temporada_janela": int(self.temporada_janela),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EstadoMercadoPersistido":
        contratos = [
            Contrato.from_dict(item)
            for item in data.get("contratos_ativos", [])
            if isinstance(item, dict)
        ]
        historico = [
            ResultadoMercado.from_dict(item)
            for item in data.get("historico_janelas", [])
            if isinstance(item, dict)
        ]
        propostas = [
            Proposta.from_dict(item)
            for item in data.get("propostas_atuais", [])
            if isinstance(item, dict)
        ]
        vagas = [
            VagaAberta.from_dict(item)
            for item in data.get("vagas_abertas", [])
            if isinstance(item, dict)
        ]
        pendencias = [
            Proposta.from_dict(item)
            for item in data.get("pendencias_jogador", [])
            if isinstance(item, dict)
        ]
        return cls(
            versao=max(1, int(data.get("versao", 1) or 1)),
            contratos_ativos=contratos,
            historico_janelas=historico,
            propostas_atuais=propostas,
            vagas_abertas=vagas,
            reserva_global=list(data.get("reserva_global", []) or []),
            rookies_gerados=list(data.get("rookies_gerados", []) or []),
            pendencias_jogador=pendencias,
            janela_aberta=bool(data.get("janela_aberta", False)),
            temporada_janela=int(data.get("temporada_janela", 0) or 0),
        )


def estado_mercado_padrao_dict() -> dict[str, Any]:
    """Retorna estrutura padrao serializavel de mercado."""
    return EstadoMercadoPersistido().to_dict()

