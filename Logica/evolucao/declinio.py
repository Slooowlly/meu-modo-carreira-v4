"""
Sistema de declinio de skills por idade.

Regras principais:
- Declinio comeca aos 33 anos
- Quanto mais velho, mais rapido declina
- Atributos fisicos declinam mais rapido
- Atributos mentais declinam mais devagar
- Fitness alto desacelera declinio geral
- Floor de 20 (nunca abaixo disso)
"""

import random

from .models import EvolucaoAtributo


IDADE_INICIO_DECLINIO = 33
MIN_ATRIBUTO = 20.0

TAXA_DECLINIO_ATRIBUTOS = {
    "fitness": 1.5,
    "ritmo_classificacao": 1.2,
    "skill": 1.0,
    "habilidade_largada": 0.8,
    "consistencia": 0.5,
    "resistencia_mental": 0.4,
    "adaptabilidade": 0.5,
    "racecraft": 0.2,
    "gestao_pneus": 0.2,
    "fator_chuva": 0.3,
    "clutch_factor": 0.3,
}

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


def calcular_fator_idade_declinio(idade: int) -> float:
    """
    Calcula multiplicador de declinio por idade.
    """
    if idade < IDADE_INICIO_DECLINIO:
        return 0.0

    anos_apos_33 = idade - IDADE_INICIO_DECLINIO
    if anos_apos_33 <= 2:
        return 0.5
    if anos_apos_33 <= 5:
        return 1.0
    if anos_apos_33 <= 8:
        return 1.5
    return 2.0


def calcular_protecao_fitness(fitness: float) -> float:
    """
    Calcula protecao contra declinio baseada no fitness.
    """
    protecao = (fitness / 100.0) * 0.4
    return 1.0 - protecao


def calcular_declinio_atributo(
    atributo: str,
    valor_atual: float,
    idade: int,
    fitness: float,
) -> EvolucaoAtributo:
    """
    Calcula declinio de um atributo especifico.
    """
    if idade < IDADE_INICIO_DECLINIO:
        return EvolucaoAtributo(
            atributo=atributo,
            valor_anterior=valor_atual,
            valor_novo=valor_atual,
            variacao=0.0,
            motivo="sem declinio (jovem)",
        )

    taxa_base = TAXA_DECLINIO_ATRIBUTOS.get(atributo, 0.5)
    f_idade = calcular_fator_idade_declinio(idade)
    f_fitness = calcular_protecao_fitness(fitness)

    declinio = taxa_base * f_idade * f_fitness
    declinio += random.uniform(-0.3, 0.3)
    declinio = max(0.0, declinio)

    valor_novo = max(valor_atual - declinio, MIN_ATRIBUTO)
    variacao_real = valor_novo - valor_atual

    motivos: list[str] = []
    if f_idade >= 1.5:
        motivos.append(f"idade avancada ({idade})")
    else:
        motivos.append(f"envelhecimento ({idade})")

    if f_fitness < 0.8:
        motivos.append("fitness ajudando")

    if taxa_base >= 1.0:
        motivos.append("atributo fisico")
    elif taxa_base <= 0.3:
        motivos.append("atributo resiliente")

    return EvolucaoAtributo(
        atributo=atributo,
        valor_anterior=valor_atual,
        valor_novo=valor_novo,
        variacao=variacao_real,
        motivo=", ".join(motivos),
    )


def processar_declinio(pilot) -> list[EvolucaoAtributo]:
    """
    Processa declinio de todos os atributos configurados.
    """
    idade = int(_get_valor(pilot, "idade", 25.0))
    if idade < IDADE_INICIO_DECLINIO:
        return []

    fitness = _get_valor(pilot, "fitness", 50.0)
    evolucoes: list[EvolucaoAtributo] = []

    for atributo in TAXA_DECLINIO_ATRIBUTOS.keys():
        valor_atual = _get_valor(pilot, atributo, 50.0)
        evolucoes.append(
            calcular_declinio_atributo(
                atributo=atributo,
                valor_atual=valor_atual,
                idade=idade,
                fitness=fitness,
            )
        )

    return evolucoes


def aplicar_declinio(pilot, evolucoes: list[EvolucaoAtributo]):
    """
    Aplica declinios ao piloto.
    """
    for evo in evolucoes:
        _set_valor(pilot, evo.atributo, evo.valor_novo)

