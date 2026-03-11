"""Helpers para configurar e validar conteudo possuido no iRacing."""

from __future__ import annotations

from typing import Any
import re
import unicodedata


CATEGORIAS_CONTEUDO_SIMPLIFICADO: list[dict[str, Any]] = [
    {
        "id": "mazda_mx5",
        "label": "Mazda MX-5 (free)",
        "categorias": ["mazda_rookie", "mazda_amador"],
        "free": True,
    },
    {
        "id": "toyota_gr86",
        "label": "Toyota GR86",
        "categorias": ["toyota_rookie", "toyota_amador"],
    },
    {
        "id": "bmw_m2",
        "label": "BMW M2 CS Racing",
        "categorias": ["bmw_m2"],
    },
    {
        "id": "gt4",
        "label": "GT4",
        "categorias": ["gt4"],
    },
    {
        "id": "gt3",
        "label": "GT3",
        "categorias": ["gt3"],
    },
    {
        "id": "lmp2_endurance",
        "label": "LMP2/Endurance",
        "categorias": ["endurance"],
    },
]


PISTAS_PAGAS_OPCOES: list[dict[str, Any]] = [
    {"id": "lime_rock", "label": "Lime Rock Park", "keywords": ["lime rock"]},
    {"id": "watkins_glen", "label": "Watkins Glen", "keywords": ["watkins glen"]},
    {"id": "spa_francorchamps", "label": "Spa-Francorchamps", "keywords": ["spa"]},
    {"id": "road_america", "label": "Road America", "keywords": ["road america"]},
    {"id": "daytona", "label": "Daytona", "keywords": ["daytona"]},
    {"id": "monza", "label": "Monza", "keywords": ["monza"]},
]


_CARRO_LABELS: dict[str, str] = {
    "mazda_mx5": "Mazda MX-5",
    "toyota_gr86": "Toyota GR86",
    "bmw_m2": "BMW M2 CS Racing",
    "gt4": "GT4",
    "gt3": "GT3",
    "lmp2_endurance": "LMP2/Endurance",
}

_PRODUCTION_MARCA_PARA_CARRO: dict[str, str] = {
    "mazda": "mazda_mx5",
    "toyota": "toyota_gr86",
    "bmw": "bmw_m2",
}

_FREE_TRACK_KEYWORDS = (
    "summit point",
    "okayama",
    "charlotte",
)


def slug_texto(valor: Any) -> str:
    texto = str(valor or "").strip().casefold()
    if not texto:
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    return texto.strip("_")


def conteudo_iracing_padrao() -> dict[str, list[str]]:
    return {
        "carros": ["mazda_mx5"],
        "categorias": ["mazda_mx5"],
        "pistas_pagas": [],
    }


def normalizar_conteudo_iracing(raw: Any) -> dict[str, list[str]]:
    conteudo = raw if isinstance(raw, dict) else {}
    base = conteudo_iracing_padrao()
    normalizado: dict[str, list[str]] = {}

    for chave in ("carros", "categorias", "pistas_pagas"):
        valores = conteudo.get(chave, base[chave])
        if not isinstance(valores, list):
            valores = base[chave]
        lista_lida: list[str] = []
        for item in valores:
            slug = slug_texto(item)
            if slug and slug not in lista_lida:
                lista_lida.append(slug)
        normalizado[chave] = lista_lida

    if not normalizado["categorias"]:
        normalizado["categorias"] = list(base["categorias"])
    if not normalizado["carros"]:
        normalizado["carros"] = list(base["carros"])

    return normalizado


def categoria_para_conteudo(
    categoria_id: Any,
    equipe: dict[str, Any] | None = None,
) -> str:
    categoria = str(categoria_id or "").strip().lower()

    if categoria in {"mazda_rookie", "mazda_amador"}:
        return "mazda_mx5"
    if categoria in {"toyota_rookie", "toyota_amador"}:
        return "toyota_gr86"
    if categoria == "bmw_m2":
        return "bmw_m2"
    if categoria == "gt4":
        return "gt4"
    if categoria == "gt3":
        return "gt3"
    if categoria == "endurance":
        classe = str((equipe or {}).get("classe_endurance", "") or "").strip().lower()
        if classe == "gt4":
            return "gt4"
        if classe == "gt3":
            return "gt3"
        return "lmp2_endurance"

    if categoria == "production_challenger":
        marca_raw = (
            str((equipe or {}).get("pro_trilha_marca", "") or "").strip().lower()
            or str((equipe or {}).get("carro_classe", "") or "").strip().lower()
        )
        for chave, carro_id in _PRODUCTION_MARCA_PARA_CARRO.items():
            if chave in marca_raw:
                return carro_id
        return "mazda_mx5"

    return ""


def nome_carro_categoria(categoria_conteudo: Any) -> str:
    chave = slug_texto(categoria_conteudo)
    return _CARRO_LABELS.get(chave, str(categoria_conteudo or "Carro desconhecido"))


def nome_carro_equipe(
    equipe: dict[str, Any] | None,
    categoria_id: Any,
) -> str:
    equipe_dict = equipe if isinstance(equipe, dict) else {}
    marca = str(equipe_dict.get("marca", "") or "").strip()
    if marca:
        categoria = str(categoria_id or "").strip().lower()
        if categoria == "gt4":
            return f"{marca} GT4"
        if categoria == "gt3":
            return f"{marca} GT3"
        if categoria == "endurance":
            classe = str(equipe_dict.get("classe_endurance", "") or "").strip().upper()
            if classe:
                return f"{marca} {classe}"
            return marca
        return marca

    categoria_conteudo = categoria_para_conteudo(categoria_id, equipe_dict)
    return nome_carro_categoria(categoria_conteudo)


def jogador_possui_categoria(
    conteudo_iracing: Any,
    categoria_conteudo: Any,
) -> bool:
    categoria = slug_texto(categoria_conteudo)
    if not categoria:
        return True

    conteudo = normalizar_conteudo_iracing(conteudo_iracing)
    categorias = set(conteudo.get("categorias", []))
    carros = set(conteudo.get("carros", []))
    return categoria in categorias or categoria in carros


def pista_cobranca_slug(circuito: Any) -> str:
    texto = slug_texto(circuito)
    if not texto:
        return ""
    for opcao in PISTAS_PAGAS_OPCOES:
        pista_id = str(opcao.get("id", "") or "").strip()
        keywords = opcao.get("keywords", [])
        if not isinstance(keywords, list):
            continue
        for keyword in keywords:
            chave = slug_texto(keyword)
            if chave and chave in texto:
                return pista_id
    return ""


def pista_eh_free(circuito: Any) -> bool:
    texto = slug_texto(circuito)
    if not texto:
        return False
    for keyword in _FREE_TRACK_KEYWORDS:
        if slug_texto(keyword) in texto:
            return True
    return False


def jogador_possui_pista(conteudo_iracing: Any, circuito: Any) -> bool:
    if pista_eh_free(circuito):
        return True
    slug_pista = pista_cobranca_slug(circuito)
    if not slug_pista:
        return False
    conteudo = normalizar_conteudo_iracing(conteudo_iracing)
    return slug_pista in set(conteudo.get("pistas_pagas", []))

