"""Calculo de expectativas e avaliacao de desempenho do jogador."""

from __future__ import annotations

from typing import Any


def _safe_int(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(padrao)


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _ids_equivalentes(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if left in (None, "") or right in (None, ""):
        return False
    if isinstance(left, bool) or isinstance(right, bool):
        return False
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return str(left) == str(right)


def _piloto_ativo_na_grid(piloto: dict[str, Any], categoria_id: str) -> bool:
    if not isinstance(piloto, dict):
        return False
    if bool(piloto.get("aposentado", False)):
        return False
    categoria = _texto(piloto.get("categoria_atual"))
    if categoria != categoria_id:
        return False
    status = _texto(piloto.get("status", "ativo")).casefold()
    return status not in {"aposentado", "reserva_global", "reserva", "livre"}


def obter_classificacao_categoria(
    banco: dict[str, Any],
    categoria_id: str,
) -> list[dict[str, Any]]:
    """Retorna classificacao da categoria atual (ordenacao por campeonato)."""
    categoria = _texto(categoria_id)
    if not categoria:
        return []

    pilotos = [
        piloto
        for piloto in banco.get("pilotos", [])
        if _piloto_ativo_na_grid(piloto, categoria)
    ]

    pilotos_ordenados = sorted(
        pilotos,
        key=lambda piloto: (
            -_safe_int(piloto.get("pontos_temporada"), 0),
            -_safe_int(piloto.get("vitorias_temporada"), 0),
            -_safe_int(piloto.get("podios_temporada"), 0),
            _texto(piloto.get("nome")).casefold(),
        ),
    )

    classificacao: list[dict[str, Any]] = []
    for indice, piloto in enumerate(pilotos_ordenados, start=1):
        classificacao.append(
            {
                "posicao": indice,
                "piloto_id": piloto.get("id"),
                "pontos": _safe_int(piloto.get("pontos_temporada"), 0),
                "piloto": piloto,
            }
        )
    return classificacao


def _obter_equipe_por_id(
    banco: dict[str, Any],
    equipe_id: Any,
) -> dict[str, Any] | None:
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        if _ids_equivalentes(equipe.get("id"), equipe_id):
            return equipe
    return None


def calcular_expectativa_equipe(
    jogador: dict[str, Any],
    equipe: dict[str, Any] | None,
    banco: dict[str, Any],
) -> dict[str, Any]:
    """
    Calcula a posicao esperada do jogador no campeonato com base em score relativo.
    """
    if not isinstance(jogador, dict):
        return {
            "posicao_esperada": 1,
            "faixa_min": 1,
            "faixa_max": 1,
            "total_pilotos": 1,
            "texto_faixa": "Top 1",
        }

    categoria = _texto(jogador.get("categoria_atual"))
    if not categoria:
        return {
            "posicao_esperada": 1,
            "faixa_min": 1,
            "faixa_max": 1,
            "total_pilotos": 1,
            "texto_faixa": "Top 1",
        }

    pilotos_cat = [
        piloto
        for piloto in banco.get("pilotos", [])
        if _piloto_ativo_na_grid(piloto, categoria) and not bool(piloto.get("is_jogador", False))
    ]

    scores: list[float] = []
    for piloto in pilotos_cat:
        equipe_ref = _obter_equipe_por_id(banco, piloto.get("equipe_id"))
        car_perf = _safe_int((equipe_ref or {}).get("car_performance"), 50)
        skill = _safe_int(piloto.get("skill"), 50)
        score = (skill * 0.6) + (car_perf * 0.4)
        scores.append(score)

    equipe_jogador = equipe if isinstance(equipe, dict) else _obter_equipe_por_id(
        banco,
        jogador.get("equipe_id"),
    )
    car_perf_jogador = _safe_int((equipe_jogador or {}).get("car_performance"), 50)
    score_jogador = (_safe_int(jogador.get("skill"), 50) * 0.6) + (car_perf_jogador * 0.4)

    melhores = sum(1 for score in scores if score > score_jogador)
    posicao_esperada = melhores + 1
    total = len(scores) + 1

    margem = max(2, total // 5)
    faixa_min = max(1, posicao_esperada - margem)
    faixa_max = min(total, posicao_esperada + margem)
    metade_grid = max(1, total // 2)
    if faixa_max <= metade_grid:
        texto_faixa = f"Top {faixa_max}"
    else:
        texto_faixa = f"Posicoes {faixa_min}-{faixa_max}"

    return {
        "posicao_esperada": posicao_esperada,
        "faixa_min": faixa_min,
        "faixa_max": faixa_max,
        "total_pilotos": total,
        "texto_faixa": texto_faixa,
    }


def avaliar_desempenho_vs_expectativa(
    jogador: dict[str, Any],
    expectativa: dict[str, Any],
    banco: dict[str, Any],
) -> dict[str, Any]:
    """
    Compara desempenho real no campeonato com expectativa da equipe.
    """
    if not isinstance(jogador, dict):
        return {"nivel": "neutro", "emoji": ":-|", "texto": "Sem dados suficientes"}

    categoria = _texto(jogador.get("categoria_atual"))
    classificacao = obter_classificacao_categoria(banco, categoria)
    jogador_id = jogador.get("id")
    posicao_real = next(
        (
            _safe_int(item.get("posicao"), 0)
            for item in classificacao
            if isinstance(item, dict) and _ids_equivalentes(item.get("piloto_id"), jogador_id)
        ),
        0,
    )
    if posicao_real <= 0:
        return {"nivel": "neutro", "emoji": ":-|", "texto": "Sem dados suficientes"}

    posicao_esperada = max(1, _safe_int(expectativa.get("posicao_esperada"), posicao_real))
    diferenca = posicao_esperada - posicao_real
    detalhe = f"Esperado: ~{posicao_esperada}o | Real: {posicao_real}o"

    if diferenca >= 5:
        return {
            "nivel": "impressionada",
            "emoji": "😍",
            "texto": "Impressionada - muito acima das expectativas.",
            "detalhe": detalhe,
            "impacto": "Renovacao quase certa. Propostas melhores devem aparecer.",
            "posicao_real": posicao_real,
            "posicao_esperada": posicao_esperada,
        }
    if diferenca >= 2:
        return {
            "nivel": "satisfeita",
            "emoji": "😊",
            "texto": "Satisfeita - desempenho acima do esperado.",
            "detalhe": detalhe,
            "impacto": "Renovacao provavel e boa reputacao de mercado.",
            "posicao_real": posicao_real,
            "posicao_esperada": posicao_esperada,
        }
    if diferenca >= -2:
        return {
            "nivel": "neutra",
            "emoji": ":-|",
            "texto": "Neutra - desempenho dentro do esperado.",
            "detalhe": detalhe,
            "impacto": "Renovacao possivel, sem garantias.",
            "posicao_real": posicao_real,
            "posicao_esperada": posicao_esperada,
        }
    if diferenca >= -5:
        return {
            "nivel": "preocupada",
            "emoji": "😟",
            "texto": "Preocupada - abaixo das expectativas.",
            "detalhe": detalhe,
            "impacto": "Risco de troca se os resultados nao melhorarem.",
            "posicao_real": posicao_real,
            "posicao_esperada": posicao_esperada,
        }
    return {
        "nivel": "insatisfeita",
        "emoji": "😠",
        "texto": "Insatisfeita - muito abaixo das expectativas.",
        "detalhe": detalhe,
        "impacto": "Alto risco de nao renovacao e menos propostas.",
        "posicao_real": posicao_real,
        "posicao_esperada": posicao_esperada,
    }


def registrar_avaliacao_historico(
    banco: dict[str, Any],
    *,
    rodada: int,
    categoria_id: str,
    avaliacao: dict[str, Any],
) -> None:
    """Persiste uma avaliacao por rodada para exibicao historica."""
    historico = banco.get("historico_avaliacoes")
    if not isinstance(historico, list):
        historico = []
        banco["historico_avaliacoes"] = historico

    entrada = {
        "rodada": max(1, _safe_int(rodada, 1)),
        "categoria_id": _texto(categoria_id),
        "nivel": _texto(avaliacao.get("nivel", "neutro")) or "neutro",
        "posicao": _safe_int(avaliacao.get("posicao_real"), 0),
        "expectativa": _safe_int(avaliacao.get("posicao_esperada"), 0),
    }

    for item in historico:
        if not isinstance(item, dict):
            continue
        if (
            _safe_int(item.get("rodada"), 0) == entrada["rodada"]
            and _texto(item.get("categoria_id")) == entrada["categoria_id"]
        ):
            item.update(entrada)
            return

    historico.append(entrada)

