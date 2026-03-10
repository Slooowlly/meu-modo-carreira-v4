"""Baixa as bandeiras PNG para Assets/bandeiras."""

from __future__ import annotations

from pathlib import Path
from urllib.request import Request, urlopen

try:
    import requests  # type: ignore
except Exception:
    requests = None

from Utils.bandeiras import MAPA_BANDEIRAS, MAPA_TERMO_CIRCUITO_PARA_CODIGO


def _baixar_com_requests(url: str) -> bytes:
    if requests is None:
        raise RuntimeError("requests nao disponivel")
    resposta = requests.get(url, timeout=10)
    resposta.raise_for_status()
    return bytes(resposta.content)


def _baixar_com_urllib(url: str) -> bytes:
    requisicao = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(requisicao, timeout=10) as resposta:
        return resposta.read()


def baixar_bandeiras() -> None:
    pasta = Path("Assets") / "bandeiras"
    pasta.mkdir(parents=True, exist_ok=True)

    codigos = list(
        dict.fromkeys(
            [*MAPA_BANDEIRAS.values(), *[codigo for _, codigo in MAPA_TERMO_CIRCUITO_PARA_CODIGO]]
        )
    )

    print("Baixando bandeiras PNG...\n")
    for codigo in codigos:
        url = f"https://flagcdn.com/w80/{codigo}.png"
        destino = pasta / f"{codigo}.png"
        try:
            conteudo = _baixar_com_requests(url) if requests else _baixar_com_urllib(url)
            destino.write_bytes(conteudo)
            print(f"OK  {codigo}.png")
        except Exception:
            try:
                conteudo = _baixar_com_urllib(url)
                destino.write_bytes(conteudo)
                print(f"OK  {codigo}.png (urllib fallback)")
            except Exception as erro:
                print(f"ERRO {codigo}.png -> {erro}")

    print(f"\nConcluido. Pasta: {pasta.resolve()}")


if __name__ == "__main__":
    baixar_bandeiras()
