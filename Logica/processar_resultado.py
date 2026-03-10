"""
Processamento de resultados JSON exportados pelo iRacing.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Callable

from Utils.helpers import int_seguro

logger = logging.getLogger(__name__)


def ler_resultado(caminho_arquivo: str) -> dict | None:
    """Le e retorna um JSON de resultado."""
    caminho = str(caminho_arquivo or "").strip()
    if not caminho or not os.path.isfile(caminho):
        return None

    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except (OSError, json.JSONDecodeError) as erro:
        logger.error("Erro ao ler resultado (%s): %s", caminho, erro)
        return None

    return dados if isinstance(dados, dict) else None


def _normalizar_int(valor: Any) -> int | None:
    """Wrapper de int_seguro que retorna None em vez de 0 para valores inválidos."""
    if isinstance(valor, bool):
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _normalizar_piloto(entrada: dict, indice: int) -> dict | None:
    nome = ""
    for chave in ("display_name", "driverName", "driver_name", "nome", "name"):
        candidato = str(entrada.get(chave, "") or "").strip()
        if candidato:
            nome = candidato
            break

    if not nome:
        return None

    posicao_raw = None
    for chave in (
        "finish_position_in_class",
        "finishPosition",
        "finish_position",
        "position",
        "posicao",
    ):
        if chave in entrada:
            posicao_raw = _normalizar_int(entrada.get(chave))
            if posicao_raw is not None:
                break

    incidentes = _normalizar_int(entrada.get("incidents"))
    if incidentes is None:
        incidentes = _normalizar_int(entrada.get("incidentes"))
    if incidentes is None:
        incidentes = 0

    voltas = _normalizar_int(entrada.get("laps_complete"))
    if voltas is None:
        voltas = _normalizar_int(entrada.get("lapsCompleted"))
    if voltas is None:
        voltas = _normalizar_int(entrada.get("laps"))
    if voltas is None:
        voltas = 0

    melhor_volta = entrada.get("best_lap_time", entrada.get("bestLapTime"))
    reason_out = str(entrada.get("reason_out", entrada.get("status", "")) or "").strip()
    is_player = bool(entrada.get("isPlayer", entrada.get("is_player", False)))

    dnf = bool(entrada.get("dnf", False))
    if not dnf and reason_out:
        running_labels = {"running", "finished", "complete", "completed"}
        if reason_out.casefold() not in running_labels:
            dnf = True

    return {
        "nome": nome,
        "posicao_raw": posicao_raw,
        "incidentes": incidentes,
        "voltas": voltas,
        "melhor_volta": melhor_volta,
        "reason_out": reason_out or "Running",
        "dnf": dnf,
        "is_player": is_player,
        "_ordem": indice,
    }


def _coletar_resultados_de_sessoes(sessoes: Any) -> list[dict]:
    if not isinstance(sessoes, list):
        return []

    candidatos: list[list[dict]] = []
    for sessao in sessoes:
        if not isinstance(sessao, dict):
            continue

        resultados = sessao.get("results")
        if not isinstance(resultados, list) or not resultados:
            continue

        tipo = str(
            sessao.get("simsession_type_name")
            or sessao.get("sessionType")
            or sessao.get("type")
            or ""
        ).strip()

        if tipo and "race" in tipo.casefold():
            return resultados

        candidatos.append(resultados)

    return candidatos[0] if candidatos else []


def _extrair_lista_resultados(resultado: dict) -> list[dict]:
    resultados_topo = resultado.get("results")
    if isinstance(resultados_topo, list) and resultados_topo:
        return resultados_topo

    if isinstance(resultados_topo, dict):
        resultados = _coletar_resultados_de_sessoes(resultados_topo.get("session_results"))
        if resultados:
            return resultados

    resultados = _coletar_resultados_de_sessoes(resultado.get("session_results"))
    if resultados:
        return resultados

    resultados = _coletar_resultados_de_sessoes(resultado.get("sessions"))
    if resultados:
        return resultados

    eventos = resultado.get("events")
    if isinstance(eventos, list):
        for evento in eventos:
            if not isinstance(evento, dict):
                continue

            bloco_resultados = evento.get("results")
            if isinstance(bloco_resultados, list) and bloco_resultados:
                return bloco_resultados

            if isinstance(bloco_resultados, dict):
                resultados_evento = _coletar_resultados_de_sessoes(
                    bloco_resultados.get("session_results")
                )
                if resultados_evento:
                    return resultados_evento

    return []


def _normalizar_posicoes(pilotos: list[dict]) -> list[dict]:
    posicoes_validas = [
        int(p["posicao_raw"])
        for p in pilotos
        if isinstance(p.get("posicao_raw"), int) and int(p["posicao_raw"]) >= 0
    ]
    ajuste_base = 1 if posicoes_validas and min(posicoes_validas) == 0 else 0

    for piloto in pilotos:
        posicao_raw = piloto.get("posicao_raw")
        if isinstance(posicao_raw, int) and posicao_raw >= 0:
            piloto["posicao"] = int(posicao_raw) + ajuste_base
        else:
            piloto["posicao"] = int(piloto.get("_ordem", 0)) + 1

    pilotos.sort(
        key=lambda p: (
            int(p.get("posicao", 999999)),
            str(p.get("nome", "")).casefold(),
        )
    )
    return pilotos


def extrair_dados_corrida(resultado: dict) -> dict | None:
    """
    Extrai dados relevantes do JSON de resultado em formatos comuns.
    """
    if not isinstance(resultado, dict):
        return None

    resultados_brutos = _extrair_lista_resultados(resultado)
    if not resultados_brutos:
        return None

    pilotos: list[dict] = []
    for indice, entrada in enumerate(resultados_brutos):
        if not isinstance(entrada, dict):
            continue
        piloto = _normalizar_piloto(entrada, indice)
        if piloto:
            pilotos.append(piloto)

    if not pilotos:
        return None

    pilotos = _normalizar_posicoes(pilotos)
    indice_volta_rapida = -1
    melhor_tempo = None
    for indice, piloto in enumerate(pilotos):
        if bool(piloto.get("dnf", False)):
            continue
        try:
            tempo = float(piloto.get("melhor_volta", -1))
        except (TypeError, ValueError):
            continue
        if tempo <= 0:
            continue
        if melhor_tempo is None or tempo < melhor_tempo:
            melhor_tempo = tempo
            indice_volta_rapida = indice

    classificacao = []
    for indice, piloto in enumerate(pilotos):
        nome_piloto = str(piloto.get("nome", "")).strip()
        if not nome_piloto:
            continue
        dnf = bool(piloto.get("dnf", False))
        classificacao.append(
            {
                "piloto": nome_piloto,
                "dnf": dnf,
                "incidentes": int(piloto.get("incidentes", 0)),
                "volta_rapida": (not dnf and indice == indice_volta_rapida),
            }
        )

    if not classificacao:
        return None

    jogador = next((p for p in pilotos if bool(p.get("is_player", False))), None)
    track_info = resultado.get("track")
    track_name = ""
    if isinstance(track_info, dict):
        track_name = str(
            track_info.get("track_name")
            or track_info.get("name")
            or track_info.get("display_name")
            or ""
        ).strip()

    if not track_name:
        track_name = str(resultado.get("trackName", resultado.get("track_name", "")) or "").strip()

    track_id = _normalizar_int(resultado.get("trackId"))
    if track_id is None and isinstance(track_info, dict):
        track_id = _normalizar_int(track_info.get("track_id"))

    return {
        "season_name": str(resultado.get("name", resultado.get("season_name", "")) or "").strip(),
        "track_id": track_id if track_id is not None else 0,
        "track_name": track_name,
        "classificacao": classificacao,
        "pilotos": pilotos,
        "posicao_final": int(jogador.get("posicao")) if jogador else None,
        "voltas_completadas": int(jogador.get("voltas", 0)) if jogador else 0,
        "melhor_volta": jogador.get("melhor_volta") if jogador else None,
        "incidentes": int(jogador.get("incidentes", 0)) if jogador else 0,
        "vencedor": str(classificacao[0].get("piloto", "")).strip(),
    }





def _normalizar_aplicados(retorno_callback: Any, total_resultados: int) -> int:
    if isinstance(retorno_callback, bool):
        return total_resultados if retorno_callback else 0
    if isinstance(retorno_callback, int):
        return max(0, retorno_callback)
    return total_resultados


def processar_resultado_corrida(
    caminho_arquivo: str,
    categoria_id: str,
    atualizar_standings_callback: Callable[[str, dict], Any],
) -> dict:
    """
    Processa um arquivo de resultado e aplica atualizacoes via callback.
    """
    resultado_raw = ler_resultado(caminho_arquivo)
    if not resultado_raw:
        return {
            "sucesso": False,
            "erro": "Nao foi possivel ler o arquivo de resultado.",
        }

    dados = extrair_dados_corrida(resultado_raw)
    if not dados:
        return {
            "sucesso": False,
            "erro": "Nao foi possivel extrair dados validos do resultado.",
        }

    classificacao = dados.get("classificacao", [])
    total_resultados = len(classificacao) if isinstance(classificacao, list) else 0
    if total_resultados <= 0:
        return {
            "sucesso": False,
            "erro": "Arquivo de resultado sem classificacao valida.",
        }

    try:
        retorno = atualizar_standings_callback(categoria_id, dados)
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": f"Erro ao atualizar standings: {erro}",
        }

    aplicados = _normalizar_aplicados(retorno, total_resultados)
    if aplicados <= 0:
        return {
            "sucesso": False,
            "erro": "Nenhum resultado foi aplicado aos standings.",
            "aplicados": 0,
            "total_resultados": total_resultados,
        }

    return {
        "sucesso": True,
        "categoria_id": categoria_id,
        "arquivo": os.path.normpath(str(caminho_arquivo)),
        "vencedor": str(dados.get("vencedor", "")).strip(),
        "posicao": dados.get("posicao_final"),
        "voltas": int(dados.get("voltas_completadas", 0)),
        "incidentes": int(dados.get("incidentes", 0)),
        "melhor_volta": dados.get("melhor_volta"),
        "aplicados": aplicados,
        "total_resultados": total_resultados,
    }
