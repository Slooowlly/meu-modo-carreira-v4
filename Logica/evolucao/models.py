"""
Modelos de dados para o sistema de evolucao.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EvolucaoTipo(Enum):
    """Tipo de evolucao de atributo."""

    CRESCIMENTO = "crescimento"
    DECLINIO = "declinio"
    ESTAGNACAO = "estagnacao"


class LesaoTipo(Enum):
    """Tipos de lesao."""

    NENHUMA = "nenhuma"
    LEVE = "leve"  # -5% skill por 2 corridas
    MODERADA = "moderada"  # -10% skill por 3-5 corridas
    GRAVE = "grave"  # perde corridas + chance de aposentadoria


class AposentadoriaCausa(Enum):
    """Causas de aposentadoria."""

    IDADE = "idade"
    MOTIVACAO_BAIXA = "motivacao_baixa"
    LESAO_GRAVE = "lesao_grave"
    VOLUNTARIA = "voluntaria"


@dataclass
class EvolucaoAtributo:
    """Evolucao de um atributo especifico."""

    atributo: str
    valor_anterior: float
    valor_novo: float
    variacao: float
    motivo: str

    @property
    def tipo(self) -> EvolucaoTipo:
        if self.variacao > 0.1:
            return EvolucaoTipo.CRESCIMENTO
        if self.variacao < -0.1:
            return EvolucaoTipo.DECLINIO
        return EvolucaoTipo.ESTAGNACAO


@dataclass
class RelatorioEvolucao:
    """Relatorio completo de evolucao de um piloto."""

    pilot_id: str
    pilot_name: str
    idade: int
    temporada: int

    evolucoes: list[EvolucaoAtributo] = field(default_factory=list)

    skill_anterior: float = 0.0
    skill_novo: float = 0.0
    potencial: float = 0.0
    motivacao_media: float = 0.0

    aposentou: bool = False
    causa_aposentadoria: Optional[AposentadoriaCausa] = None
    lesao_ativa: bool = False
    lesao_tipo: LesaoTipo = LesaoTipo.NENHUMA

    def get_summary(self) -> str:
        """Retorna resumo textual do relatorio."""
        lines = [
            f"=== Evolucao: {self.pilot_name} (Idade {self.idade}) ===",
            f"Temporada: {self.temporada}",
            f"Skill: {self.skill_anterior:.1f} -> {self.skill_novo:.1f}",
            f"Potencial: {self.potencial:.1f}",
            f"Motivacao media: {self.motivacao_media:.1f}",
            "",
            "Atributos:",
        ]

        for evo in self.evolucoes:
            sinal = "+" if evo.variacao >= 0 else ""
            lines.append(
                f"  {evo.atributo}: {evo.valor_anterior:.1f} -> "
                f"{evo.valor_novo:.1f} ({sinal}{evo.variacao:.1f})"
            )

        if self.aposentou and self.causa_aposentadoria:
            lines.append(f"\n[APOSENTOU] {self.causa_aposentadoria.value}")

        if self.lesao_ativa:
            lines.append(f"\n[LESAO] {self.lesao_tipo.value}")

        return "\n".join(lines)


@dataclass
class Lesao:
    """Dados de uma lesao ativa."""

    tipo: LesaoTipo
    corridas_restantes: int
    penalidade_skill: float
    causa: str

    @property
    def esta_ativa(self) -> bool:
        return self.corridas_restantes > 0 and self.tipo != LesaoTipo.NENHUMA

    def processar_corrida(self):
        """Reduz contador apos uma corrida."""
        if self.corridas_restantes > 0:
            self.corridas_restantes -= 1
        if self.corridas_restantes == 0:
            self.tipo = LesaoTipo.NENHUMA
            self.penalidade_skill = 0.0


@dataclass
class ContextoTemporada:
    """Contexto da temporada para calculo de evolucao."""

    temporada: int
    categoria_id: str
    categoria_tier: int

    corridas_disputadas: int = 0
    vitorias: int = 0
    podios: int = 0
    poles: int = 0
    dnfs: int = 0
    posicao_campeonato: int = 0

    resultados: list[int] = field(default_factory=list)
    expectativas: list[int] = field(default_factory=list)
    motivacao_media_temporada: float = 50.0

    foi_promovido: bool = False
    foi_rebaixado: bool = False

    renovou_contrato: bool = False
    time_bom: bool = False
    perdeu_vaga_para_jovem: bool = False

    @property
    def media_resultados(self) -> float:
        if not self.resultados:
            return 15.0
        return sum(self.resultados) / len(self.resultados)

    @property
    def superou_expectativas(self) -> bool:
        if not self.resultados or not self.expectativas:
            return False
        acima = sum(
            1
            for resultado, esperado in zip(self.resultados, self.expectativas)
            if resultado < esperado - 2
        )
        return acima >= len(self.resultados) * 0.5

    @property
    def abaixo_expectativas(self) -> bool:
        if not self.resultados or not self.expectativas:
            return False
        abaixo = sum(
            1
            for resultado, esperado in zip(self.resultados, self.expectativas)
            if resultado > esperado + 2
        )
        return abaixo >= len(self.resultados) * 0.5
