"""
Sistema de crescimento de skills dos pilotos.

Regras principais:
- Crescimento limitado pelo potencial (teto)
- Jovens crescem mais rapido
- Motivacao alta acelera crescimento
- Categoria desafiadora acelera crescimento
- Superar expectativas acelera crescimento
- Maximo +3 por atributo por temporada
"""

import random
from typing import Protocol, runtime_checkable

from .models import ContextoTemporada, EvolucaoAtributo


@runtime_checkable
class PilotProtocol(Protocol):
    """Interface esperada do piloto."""

    id: str
    name: str
    idade: int
    potencial: float
    motivacao: float
    skill: float
    consistencia: float
    racecraft: float
    ritmo_classificacao: float
    gestao_pneus: float
    habilidade_largada: float
    resistencia_mental: float
    adaptabilidade: float
    fitness: float
    fator_chuva: float
    clutch_factor: float
    experience: float


ATRIBUTOS_EVOLUIVEIS = [
    "skill",
    "consistencia",
    "racecraft",
    "ritmo_classificacao",
    "gestao_pneus",
    "habilidade_largada",
    "resistencia_mental",
    "adaptabilidade",
    "fitness",
    "fator_chuva",
    "clutch_factor",
]

MAX_CRESCIMENTO_POR_ATRIBUTO = 3.0
MIN_ATRIBUTO = 20.0

_ALIASES: dict[str, tuple[str, ...]] = {
    "clutch_factor": ("clutch_factor", "fator_clutch"),
    "experience": ("experience", "experiencia"),
}


def _candidatos(atributo: str) -> tuple[str, ...]:
    return _ALIASES.get(atributo, (atributo,))


def _get_valor(pilot, atributo: str, default: float = 0.0) -> float:
    if isinstance(pilot, dict):
        for nome in _candidatos(atributo):
            if nome in pilot:
                try:
                    return float(pilot.get(nome, default))
                except (TypeError, ValueError):
                    return float(default)
        return float(default)

    for nome in _candidatos(atributo):
        if hasattr(pilot, nome):
            try:
                return float(getattr(pilot, nome))
            except (TypeError, ValueError):
                return float(default)
    return float(default)


def _set_valor(pilot, atributo: str, valor: float):
    if isinstance(pilot, dict):
        for nome in _candidatos(atributo):
            if nome in pilot:
                pilot[nome] = valor
                return
        pilot[atributo] = valor
        return

    for nome in _candidatos(atributo):
        if hasattr(pilot, nome):
            setattr(pilot, nome, valor)
            return
    setattr(pilot, atributo, valor)


def calcular_fator_idade(idade: int) -> float:
    """
    Calcula fator de crescimento por idade.

    - 16-20: x1.5
    - 21-24: x1.2
    - 25-28: x1.0
    - 29-32: x0.7
    - 33+: x0.3
    """
    if idade <= 20:
        return 1.5
    if idade <= 24:
        return 1.2
    if idade <= 28:
        return 1.0
    if idade <= 32:
        return 0.7
    return 0.3


def calcular_fator_motivacao(motivacao: float) -> float:
    """
    Calcula fator de crescimento por motivacao.

    Escala linear entre 0.5 e 1.2.
    """
    return 0.5 + (motivacao / 100.0) * 0.7


def calcular_fator_desafio(categoria_tier: int, skill: float) -> float:
    """
    Calcula fator de crescimento baseado no desafio da categoria.
    """
    skill_esperado = {
        1: 45,
        2: 55,
        3: 65,
        4: 70,
        5: 75,
        6: 80,
        7: 85,
    }

    esperado = float(skill_esperado.get(categoria_tier, 60))
    diferenca = esperado - float(skill)

    if diferenca >= 15:
        return 1.3
    if diferenca >= 5:
        return 1.1
    if diferenca >= -5:
        return 1.0
    if diferenca >= -15:
        return 0.9
    return 0.8


def calcular_fator_resultado(ctx: ContextoTemporada) -> float:
    """
    Calcula fator de crescimento baseado em resultado vs expectativa.
    """
    if not ctx.resultados or not ctx.expectativas:
        return 1.0

    diferencas = []
    for resultado, esperado in zip(ctx.resultados, ctx.expectativas):
        diferencas.append(esperado - resultado)

    media = sum(diferencas) / len(diferencas) if diferencas else 0.0
    if media >= 5:
        return 1.2
    if media >= 2:
        return 1.1
    if media >= -2:
        return 1.0
    return 0.9


def calcular_espaco_crescimento(valor_atual: float, potencial: float) -> float:
    """
    Calcula multiplicador de espaco restante ate o potencial.
    """
    if potencial <= valor_atual:
        return 0.0

    espaco = potencial - valor_atual
    percentual = espaco / max(1.0, potencial)

    if percentual >= 0.5:
        return 1.0
    if percentual >= 0.25:
        return 0.7
    if percentual >= 0.10:
        return 0.4
    return 0.1


def calcular_crescimento_atributo(
    atributo: str,
    valor_atual: float,
    potencial: float,
    idade: int,
    motivacao: float,
    ctx: ContextoTemporada,
) -> EvolucaoAtributo:
    """
    Calcula crescimento de um atributo especifico.
    """
    base = 1.5

    f_idade = calcular_fator_idade(idade)
    f_motivacao = calcular_fator_motivacao(motivacao)
    f_desafio = calcular_fator_desafio(ctx.categoria_tier, valor_atual)
    f_resultado = calcular_fator_resultado(ctx)
    f_espaco = calcular_espaco_crescimento(valor_atual, potencial)

    crescimento = base * f_idade * f_motivacao * f_desafio * f_resultado * f_espaco
    crescimento += random.uniform(-0.5, 0.5)
    crescimento = min(crescimento, MAX_CRESCIMENTO_POR_ATRIBUTO)

    valor_novo = min(valor_atual + crescimento, potencial)
    valor_novo = max(valor_novo, MIN_ATRIBUTO)
    variacao_real = valor_novo - valor_atual

    motivos: list[str] = []
    if f_idade > 1.0:
        motivos.append("jovem")
    elif f_idade < 0.5:
        motivos.append("veterano")
    if f_motivacao > 1.1:
        motivos.append("motivado")
    if f_desafio > 1.0:
        motivos.append("desafiado")
    if f_resultado > 1.0:
        motivos.append("superou expectativas")
    if f_espaco < 0.5:
        motivos.append("perto do teto")

    motivo = ", ".join(motivos) if motivos else "evolucao natural"

    return EvolucaoAtributo(
        atributo=atributo,
        valor_anterior=valor_atual,
        valor_novo=valor_novo,
        variacao=variacao_real,
        motivo=motivo,
    )


def processar_crescimento(pilot, ctx: ContextoTemporada) -> list[EvolucaoAtributo]:
    """
    Processa crescimento de todos os atributos evolutiveis.
    """
    evolucoes: list[EvolucaoAtributo] = []

    potencial = _get_valor(pilot, "potencial", _get_valor(pilot, "potencial_base", 85.0))
    idade = int(_get_valor(pilot, "idade", 25.0))
    motivacao_media_ctx = getattr(ctx, "motivacao_media_temporada", None)
    if isinstance(motivacao_media_ctx, (int, float)):
        motivacao = float(motivacao_media_ctx)
    else:
        motivacao = _get_valor(pilot, "motivacao", 50.0)

    for atributo in ATRIBUTOS_EVOLUIVEIS:
        valor_atual = _get_valor(pilot, atributo, 50.0)
        evolucao = calcular_crescimento_atributo(
            atributo=atributo,
            valor_atual=valor_atual,
            potencial=potencial,
            idade=idade,
            motivacao=motivacao,
            ctx=ctx,
        )
        evolucoes.append(evolucao)

    return evolucoes


def aplicar_crescimento(pilot, evolucoes: list[EvolucaoAtributo]):
    """
    Aplica evolucoes de crescimento ao piloto.
    """
    for evo in evolucoes:
        _set_valor(pilot, evo.atributo, evo.valor_novo)
