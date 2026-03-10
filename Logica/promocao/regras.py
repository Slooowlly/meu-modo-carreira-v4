"""Promotion/relegation rules by category."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


LEGACY_CATEGORY_ALIASES: Dict[str, str] = {
    "mx5": "mazda_rookie",
    "toyotagr86": "toyota_amador",
    "bmwm2cs": "bmw_m2",
}


@dataclass
class RegraCategoria:
    categoria_id: str
    categoria_nome: str
    tier: int

    categoria_destino_promocao: Optional[str] = None
    vagas_promocao: int = 1
    budget_minimo_promocao: float = 0.0

    categoria_destino_rebaixamento: Optional[str] = None
    vagas_rebaixamento: int = 1

    permite_convite: bool = True
    temporadas_para_convite: int = 2
    temporadas_para_rebaixamento: int = 2

    is_categoria_topo: bool = False
    is_categoria_base: bool = False
    sem_rebaixamento_local: bool = False
    rebaixamento_por_classe: bool = False
    permite_convite_endurance_direto: bool = False
    budget_minimo_convite_endurance: float = 0.0


REGRAS_CATEGORIAS: Dict[str, RegraCategoria] = {
    "mazda_rookie": RegraCategoria(
        categoria_id="mazda_rookie",
        categoria_nome="Mazda MX-5 Rookie Cup",
        tier=1,
        categoria_destino_promocao="mazda_amador",
        vagas_promocao=1,
        budget_minimo_promocao=20.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=0,
        is_categoria_base=True,
    ),
    "toyota_rookie": RegraCategoria(
        categoria_id="toyota_rookie",
        categoria_nome="Toyota GR86 Rookie Cup",
        tier=1,
        categoria_destino_promocao="toyota_amador",
        vagas_promocao=1,
        budget_minimo_promocao=20.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=0,
        is_categoria_base=True,
    ),
    "mazda_amador": RegraCategoria(
        categoria_id="mazda_amador",
        categoria_nome="Mazda MX-5 Championship",
        tier=2,
        categoria_destino_promocao="production_challenger",
        vagas_promocao=3,
        budget_minimo_promocao=30.0,
        categoria_destino_rebaixamento="mazda_rookie",
        vagas_rebaixamento=1,
    ),
    "toyota_amador": RegraCategoria(
        categoria_id="toyota_amador",
        categoria_nome="Toyota GR86 Cup",
        tier=2,
        categoria_destino_promocao="production_challenger",
        vagas_promocao=3,
        budget_minimo_promocao=30.0,
        categoria_destino_rebaixamento="toyota_rookie",
        vagas_rebaixamento=1,
    ),
    "bmw_m2": RegraCategoria(
        categoria_id="bmw_m2",
        categoria_nome="BMW M2 CS Racing",
        tier=3,
        categoria_destino_promocao="production_challenger",
        vagas_promocao=3,
        budget_minimo_promocao=35.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=0,
    ),
    "production_challenger": RegraCategoria(
        categoria_id="production_challenger",
        categoria_nome="Production Car Challenger",
        tier=3,
        categoria_destino_promocao=None,
        vagas_promocao=0,
        budget_minimo_promocao=45.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=9,
    ),
    # GT4/GT3 do not relegate locally. Both can move to endurance through class slots.
    "gt4": RegraCategoria(
        categoria_id="gt4",
        categoria_nome="GT4 Series",
        tier=4,
        categoria_destino_promocao="endurance",
        vagas_promocao=3,
        budget_minimo_promocao=65.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=0,
        sem_rebaixamento_local=True,
        permite_convite=False,
    ),
    "gt3": RegraCategoria(
        categoria_id="gt3",
        categoria_nome="GT3 Championship",
        tier=5,
        categoria_destino_promocao="endurance",
        vagas_promocao=3,
        budget_minimo_promocao=75.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=0,
        sem_rebaixamento_local=True,
        permite_convite=False,
    ),
    "endurance": RegraCategoria(
        categoria_id="endurance",
        categoria_nome="Endurance Championship",
        tier=6,
        categoria_destino_promocao=None,
        vagas_promocao=0,
        budget_minimo_promocao=0.0,
        categoria_destino_rebaixamento=None,
        vagas_rebaixamento=6,
        is_categoria_topo=True,
        rebaixamento_por_classe=True,
        permite_convite=False,
    ),
}


def canonicalizar_categoria_id(categoria_id: str) -> str:
    key = str(categoria_id or "").strip().lower()
    if key in REGRAS_CATEGORIAS:
        return key
    return LEGACY_CATEGORY_ALIASES.get(key, key)


def get_regra_categoria(categoria_id: str) -> Optional[RegraCategoria]:
    return REGRAS_CATEGORIAS.get(canonicalizar_categoria_id(categoria_id))


def get_categoria_destino_promocao(categoria_id: str) -> Optional[str]:
    regra = get_regra_categoria(categoria_id)
    return regra.categoria_destino_promocao if regra else None


def get_categoria_destino_rebaixamento(categoria_id: str) -> Optional[str]:
    regra = get_regra_categoria(categoria_id)
    return regra.categoria_destino_rebaixamento if regra else None


def get_vagas_promocao(categoria_id: str) -> int:
    regra = get_regra_categoria(categoria_id)
    return regra.vagas_promocao if regra else 0


def get_vagas_rebaixamento(categoria_id: str) -> int:
    regra = get_regra_categoria(categoria_id)
    return regra.vagas_rebaixamento if regra else 0


def get_budget_minimo_promocao(categoria_id: str) -> float:
    regra = get_regra_categoria(categoria_id)
    return regra.budget_minimo_promocao if regra else 0.0


def pode_ser_promovida(categoria_id: str) -> bool:
    regra = get_regra_categoria(categoria_id)
    return bool(regra and regra.categoria_destino_promocao)


def pode_ser_rebaixada(categoria_id: str) -> bool:
    regra = get_regra_categoria(categoria_id)
    if not regra:
        return False
    if regra.sem_rebaixamento_local:
        return False
    return bool(regra.categoria_destino_rebaixamento)


def get_todas_categorias() -> List[str]:
    return list(REGRAS_CATEGORIAS.keys())


def get_categorias_por_tier(tier: int) -> List[str]:
    return [cat_id for cat_id, regra in REGRAS_CATEGORIAS.items() if regra.tier == int(tier)]


def resolver_destino_rebaixamento_production(equipe: dict) -> str:
    classe = str(equipe.get("carro_classe") or "").strip().lower()
    if classe == "mazda":
        return "mazda_amador"
    if classe == "toyota":
        return "toyota_amador"
    if classe == "bmw_m2":
        return "bmw_m2"
    return "mazda_amador"
