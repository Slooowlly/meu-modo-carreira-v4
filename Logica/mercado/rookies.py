"""
Sistema de geracao de rookies para o mercado.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import random

from Dados.constantes import POOL_NOMES_NACIONALIDADES


ROOKIES_POR_TEMPORADA = (2, 4)
IDADE_ROOKIE = (16, 20)
DISTRIBUICAO_POTENCIAL = {
    "comum": (60, 75),
    "talento": (75, 85),
    "genio": (85, 95),
}
CHANCES_TIPO = {
    "comum": 0.70,
    "talento": 0.25,
    "genio": 0.05,
}


def _pick_pool() -> dict:
    pools = [p for p in (POOL_NOMES_NACIONALIDADES or []) if isinstance(p, dict)]
    if not pools:
        return {}
    pesos = []
    for pool in pools:
        try:
            pesos.append(max(1, int(pool.get("peso", 1))))
        except Exception:
            pesos.append(1)
    return random.choices(pools, weights=pesos, k=1)[0]


def _random_name_from_pool() -> tuple[str, str]:
    pool = _pick_pool()
    nomes_m = list(pool.get("nomes_masculinos", []))
    nomes_f = list(pool.get("nomes_femininos", []))
    sobrenomes = list(pool.get("sobrenomes", []))
    if not sobrenomes:
        sobrenomes = ["Racer"]
    primeiros = nomes_m + nomes_f
    if not primeiros:
        primeiros = ["Pilot"]
    nome = f"{random.choice(primeiros)} {random.choice(sobrenomes)}"
    nacionalidade = str(pool.get("rotulo", "Internacional") or "Internacional")
    return nome, nacionalidade


@dataclass
class RookieGerado:
    """Dados de um rookie gerado."""

    nome: str
    idade: int
    nacionalidade: str
    potencial: float
    skill_inicial: float
    tipo: str
    atributos: dict


def determinar_tipo_rookie() -> str:
    """Determina tipo do rookie (comum/talento/genio)."""
    rand = random.random()
    if rand < CHANCES_TIPO["genio"]:
        return "genio"
    if rand < CHANCES_TIPO["genio"] + CHANCES_TIPO["talento"]:
        return "talento"
    return "comum"


def gerar_potencial(tipo: str) -> float:
    """Gera potencial baseado no tipo."""
    min_pot, max_pot = DISTRIBUICAO_POTENCIAL.get(tipo, DISTRIBUICAO_POTENCIAL["comum"])
    return round(random.uniform(min_pot, max_pot), 1)


def gerar_skill_inicial(potencial: float, idade: int) -> float:
    """Gera skill inicial baseado no potencial e idade."""
    fator_base = random.uniform(0.30, 0.50)
    fator_idade = (idade - 16) * 0.03
    fator_total = min(fator_base + fator_idade, 0.60)
    skill = potencial * fator_total
    return round(max(35.0, min(skill, potencial - 10.0)), 1)


def gerar_atributos_rookie(skill_inicial: float, tipo: str) -> dict:
    """Gera atributos iniciais do rookie."""
    variacao_base = 8 if tipo == "comum" else 6 if tipo == "talento" else 4

    def gerar_atributo(base_offset: float = 0.0) -> float:
        valor = skill_inicial + base_offset + random.uniform(-variacao_base, variacao_base)
        return round(max(30.0, min(85.0, valor)), 1)

    return {
        "skill": skill_inicial,
        "consistencia": gerar_atributo(-5),
        "racecraft": gerar_atributo(-8),
        "ritmo_classificacao": gerar_atributo(0),
        "gestao_pneus": gerar_atributo(-3),
        "habilidade_largada": gerar_atributo(0),
        "resistencia_mental": gerar_atributo(-3),
        "adaptabilidade": gerar_atributo(5),
        "fitness": gerar_atributo(0),
        "fator_chuva": gerar_atributo(-5),
        "fator_clutch": gerar_atributo(0),
        "clutch_factor": gerar_atributo(0),
        "experiencia": round(random.uniform(0, 10), 1),
        "experience": round(random.uniform(0, 10), 1),
        "motivacao": round(random.uniform(70, 95), 1),
        "aggression": gerar_atributo(3),
        "optimism": gerar_atributo(5),
        "smoothness": gerar_atributo(-5),
        # aliases retro-compatíveis
        "agressividade": gerar_atributo(3),
        "otimismo": gerar_atributo(5),
        "suavidade": gerar_atributo(-5),
    }


def gerar_rookie() -> RookieGerado:
    """Gera um rookie completo."""
    tipo = determinar_tipo_rookie()
    potencial = gerar_potencial(tipo)
    idade = random.randint(*IDADE_ROOKIE)
    skill = gerar_skill_inicial(potencial, idade)
    atributos = gerar_atributos_rookie(skill, tipo)
    atributos["potencial"] = potencial
    atributos["potencial_base"] = potencial
    atributos["potencial_bonus"] = 0.0
    nome, nacionalidade = _random_name_from_pool()
    return RookieGerado(
        nome=nome,
        idade=idade,
        nacionalidade=nacionalidade,
        potencial=potencial,
        skill_inicial=skill,
        tipo=tipo,
        atributos=atributos,
    )


def gerar_rookies_temporada(quantidade: Optional[int] = None) -> list[RookieGerado]:
    """Gera rookies para uma temporada."""
    if quantidade is None:
        quantidade = random.randint(*ROOKIES_POR_TEMPORADA)
    quantidade = max(1, int(quantidade))

    rookies: list[RookieGerado] = []
    nomes_usados: set[str] = set()

    for _ in range(quantidade):
        rookie = gerar_rookie()
        while rookie.nome in nomes_usados:
            nome, _nac = _random_name_from_pool()
            rookie.nome = nome
        nomes_usados.add(rookie.nome)
        rookies.append(rookie)

    return rookies
