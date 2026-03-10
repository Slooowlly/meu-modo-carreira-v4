"""Utilitarios para resolver bandeiras por nacionalidade."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

MAPA_BANDEIRAS = {
    "britanica": "gb",
    "alema": "de",
    "francesa": "fr",
    "italiana": "it",
    "espanhola": "es",
    "brasileira": "br",
    "holandesa": "nl",
    "australiana": "au",
    "japonesa": "jp",
    "americana": "us",
    "mexicana": "mx",
    "argentina": "ar",
    "finlandesa": "fi",
    "belga": "be",
    "portuguesa": "pt",
    "canadense": "ca",
    "austriaca": "at",
    "suica": "ch",
    "dinamarquesa": "dk",
    "sueca": "se",
    "norueguesa": "no",
    "polonesa": "pl",
    "russa": "ru",
    "chinesa": "cn",
}

MAPA_ROTULO_PARA_CODIGO = {
    "🇬🇧 Britânica": "gb",
    "🇩🇪 Alemã": "de",
    "🇫🇷 Francesa": "fr",
    "🇮🇹 Italiana": "it",
    "🇪🇸 Espanhola": "es",
    "🇧🇷 Brasileira": "br",
    "🇳🇱 Holandesa": "nl",
    "🇦🇺 Australiana": "au",
    "🇯🇵 Japonesa": "jp",
    "🇺🇸 Americana": "us",
    "🇲🇽 Mexicana": "mx",
    "🇦🇷 Argentina": "ar",
    "🇫🇮 Finlandesa": "fi",
    "🇧🇪 Belga": "be",
    "🇵🇹 Portuguesa": "pt",
    "🇨🇦 Canadense": "ca",
    "🇦🇹 Austríaca": "at",
    "🇨🇭 Suíça": "ch",
    "🇩🇰 Dinamarquesa": "dk",
    "🇸🇪 Sueca": "se",
    "🇳🇴 Norueguesa": "no",
    "🇵🇱 Polonesa": "pl",
    "🇷🇺 Russa": "ru",
    "🇨🇳 Chinesa": "cn",
}

_MAPA_ROTULO_NORMALIZADO = {}

TERMO_PARA_CODIGO = {
    "brasil": "br",
    "brazil": "br",
    "reino unido": "gb",
    "inglaterra": "gb",
    "united kingdom": "gb",
    "great britain": "gb",
    "alemanha": "de",
    "germany": "de",
    "franca": "fr",
    "france": "fr",
    "italia": "it",
    "italy": "it",
    "espanha": "es",
    "spain": "es",
    "holanda": "nl",
    "netherlands": "nl",
    "australia": "au",
    "japao": "jp",
    "japan": "jp",
    "eua": "us",
    "usa": "us",
    "estados unidos": "us",
    "united states": "us",
    "mexico": "mx",
    "argentina": "ar",
    "finlandia": "fi",
    "finland": "fi",
    "belgica": "be",
    "belgium": "be",
    "portugal": "pt",
    "austria": "at",
    "austriaca": "at",
    "austrian": "at",
    "suica": "ch",
    "switzerland": "ch",
    "swiss": "ch",
    "dinamarca": "dk",
    "denmark": "dk",
    "suecia": "se",
    "sweden": "se",
    "noruega": "no",
    "norway": "no",
    "polonia": "pl",
    "poland": "pl",
    "russia": "ru",
    "russa": "ru",
    "russian": "ru",
    "china": "cn",
}

CODIGOS_BANDEIRAS_SUPORTADOS = tuple(MAPA_BANDEIRAS.values())
_EMOJI_REGIONAL_A = 0x1F1E6
_EMOJI_REGIONAL_Z = 0x1F1FF
CODIGOS_BANDEIRAS_CORRIDAS = (
    "us",
    "jp",
    "gb",
    "au",
    "de",
    "fr",
    "es",
    "it",
    "br",
    "ca",
)
MAPA_TERMO_CIRCUITO_PARA_CODIGO = (
    (("summit point", "laguna seca", "lime rock", "charlotte", "virginia"), "us"),
    (("daytona", "sebring", "watkins glen", "road america", "road atlanta"), "us"),
    (("okayama", "tsukuba", "suzuka", "fuji", "motegi"), "jp"),
    (("oulton", "snetterton", "silverstone", "brands hatch", "donington"), "gb"),
    (("oran park", "winton", "bathurst", "phillip island", "sandown"), "au"),
    (("oschersleben", "nurburgring", "hockenheim"), "de"),
    (("rudskogen",), "no"),
    (("ledenon", "magny-cours", "paul ricard"), "fr"),
    (("navarra", "jarama", "aragon", "catalunya", "barcelona"), "es"),
    (("interlagos",), "br"),
    (("monza", "imola", "mugello", "misano"), "it"),
    (("spa", "zolder"), "be"),
    (("zandvoort",), "nl"),
    (("red bull ring", "spielberg"), "at"),
    (("hungaroring",), "hu"),
    (("portimao", "algarve", "estoril"), "pt"),
    (("mosport", "canadian tire"), "ca"),
)


def _normalizar_texto(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.casefold()
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def _extrair_codigo_por_emoji(valor: str) -> str:
    regionais = [ch for ch in valor if _EMOJI_REGIONAL_A <= ord(ch) <= _EMOJI_REGIONAL_Z]
    if len(regionais) < 2:
        return ""

    codigo = "".join(
        chr(ord(ch) - _EMOJI_REGIONAL_A + ord("A")) for ch in regionais[:2]
    ).lower()
    if len(codigo) == 2 and codigo.isalpha():
        return codigo
    return ""


for _rotulo, _codigo in MAPA_ROTULO_PARA_CODIGO.items():
    _MAPA_ROTULO_NORMALIZADO[_normalizar_texto(_rotulo)] = _codigo


def obter_codigo_bandeira(nacionalidade: str, fallback: str = "un") -> str:
    """Resolve o codigo ISO (2 letras) da bandeira para a nacionalidade."""
    texto_original = str(nacionalidade or "").strip()
    if not texto_original:
        return fallback

    texto_normalizado = _normalizar_texto(texto_original)

    match_codigo_explicito = re.search(
        r"\b(?:country(?:_code)?|pais(?:_codigo)?|nac|nationality)\s*[:=]?\s*([a-z]{2})\b",
        texto_normalizado,
    )
    if match_codigo_explicito:
        codigo_explicito = match_codigo_explicito.group(1)
        return codigo_explicito

    if len(texto_normalizado) == 2 and texto_normalizado.isalpha():
        return texto_normalizado

    codigo = MAPA_BANDEIRAS.get(texto_normalizado)
    if codigo:
        return codigo

    codigo = MAPA_ROTULO_PARA_CODIGO.get(texto_original)
    if codigo:
        return codigo

    codigo = _extrair_codigo_por_emoji(texto_original)
    if codigo:
        return codigo

    codigo = _MAPA_ROTULO_NORMALIZADO.get(texto_normalizado)
    if codigo:
        return codigo

    for termo, cod in TERMO_PARA_CODIGO.items():
        if termo in texto_normalizado:
            return cod

    return fallback


def codigo_bandeira_para_emoji(codigo: str, fallback: str = "🏳️") -> str:
    """Converte codigo ISO de 2 letras para emoji de bandeira."""
    codigo_norm = str(codigo or "").strip().lower()
    if len(codigo_norm) != 2 or not codigo_norm.isalpha():
        return fallback

    return "".join(chr(ord(letra.upper()) + 127397) for letra in codigo_norm)


def obter_emoji_bandeira(nacionalidade: str, fallback: str = "🏳️") -> str:
    """Resolve nacionalidade para emoji de bandeira."""
    codigo = obter_codigo_bandeira(nacionalidade, fallback="")
    if not codigo:
        return fallback
    return codigo_bandeira_para_emoji(codigo, fallback=fallback)


def _obter_base_recursos() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def _obter_pasta_bandeiras_relativa(base: Path) -> Path:
    candidatos = (
        Path("Assets") / "bandeiras",
        Path("assets") / "bandeiras",
    )
    for candidato in candidatos:
        if (base / candidato).exists():
            return candidato
    return candidatos[0]


def obter_pasta_bandeiras_absoluta() -> Path:
    """Retorna a pasta absoluta onde ficam os PNGs de bandeira."""
    base = _obter_base_recursos()
    return (base / _obter_pasta_bandeiras_relativa(base)).resolve()


def obter_caminho_bandeira(nacionalidade: str, absoluto: bool = False) -> str:
    """Retorna o caminho do PNG da bandeira para a nacionalidade."""
    codigo = obter_codigo_bandeira(nacionalidade)
    base = _obter_base_recursos()
    pasta_relativa = _obter_pasta_bandeiras_relativa(base)
    caminho_relativo = pasta_relativa / f"{codigo}.png"
    if not absoluto:
        return caminho_relativo.as_posix()
    return str((base / caminho_relativo).resolve())


def obter_codigo_bandeira_circuito(circuito: str, indice_fallback: int | None = None) -> str:
    """Resolve o codigo ISO da bandeira com base no nome de circuito."""
    bruto = str(circuito or "").strip()
    if not bruto:
        if indice_fallback is not None:
            return CODIGOS_BANDEIRAS_CORRIDAS[indice_fallback % len(CODIGOS_BANDEIRAS_CORRIDAS)]
        return CODIGOS_BANDEIRAS_CORRIDAS[0]

    codigo_direto = obter_codigo_bandeira(bruto, fallback="")
    if codigo_direto:
        return codigo_direto

    texto = _normalizar_texto(bruto)
    for termos, codigo in MAPA_TERMO_CIRCUITO_PARA_CODIGO:
        if any(termo in texto for termo in termos):
            return codigo

    seed = sum((indice + 1) * ord(ch) for indice, ch in enumerate(texto))
    return CODIGOS_BANDEIRAS_CORRIDAS[seed % len(CODIGOS_BANDEIRAS_CORRIDAS)]
