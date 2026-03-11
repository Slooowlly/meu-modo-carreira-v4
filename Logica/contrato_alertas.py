"""Regras de alertas contratuais para aumentar tensao de fim de temporada."""

from __future__ import annotations

from typing import Any

from Logica.expectativas import obter_classificacao_categoria
from Logica.mercado.visibilidade import calcular_visibilidade


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


def _obter_equipe_por_id(banco: dict[str, Any], equipe_id: Any) -> dict[str, Any] | None:
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        if _ids_equivalentes(equipe.get("id"), equipe_id):
            return equipe
    return None


def _extrair_visibilidade(jogador: dict[str, Any], posicao: int, total_pilotos: int) -> int:
    try:
        calc = calcular_visibilidade(
            jogador,
            categoria_tier=1,
            posicao_campeonato=max(1, posicao),
            total_pilotos_categoria=max(1, total_pilotos),
            vitorias_temporada=_safe_int(jogador.get("vitorias_temporada"), 0),
            poles_temporada=_safe_int(jogador.get("poles_temporada"), 0),
            is_advanced_subtier=False,
        )
        vis_final = float(getattr(calc, "visibilidade_final", 0.0) or 0.0)
        return max(0, min(10, int(round(vis_final))))
    except Exception:
        return max(0, min(10, _safe_int(jogador.get("visibilidade"), 5)))


def _cadencia_permite_alerta(
    banco: dict[str, Any],
    *,
    rodada_atual: int,
    categoria_id: str,
    ignorar_cadencia: bool,
) -> bool:
    if ignorar_cadencia:
        return True

    ultimo = banco.get("ultimo_alerta_contrato")
    if not isinstance(ultimo, dict):
        return True

    rodada_ultimo = _safe_int(ultimo.get("rodada"), 0)
    categoria_ultimo = _texto(ultimo.get("categoria_id"))
    if categoria_ultimo and categoria_ultimo != _texto(categoria_id):
        return True
    return (rodada_atual - rodada_ultimo) >= 3


def _tipo_por_avaliacao(
    avaliacao: dict[str, Any] | None,
    *,
    desempenho_bom: bool,
    desempenho_medio: bool,
    desempenho_ruim: bool,
) -> str:
    nivel = _texto((avaliacao or {}).get("nivel")).casefold()
    if nivel in {"impressionada", "satisfeita"}:
        return "positivo"
    if nivel == "preocupada":
        return "alerta"
    if nivel == "insatisfeita":
        return "perigo"

    if desempenho_bom:
        return "positivo"
    if desempenho_ruim:
        return "perigo"
    if desempenho_medio:
        return "alerta"
    return "info"


def gerar_alerta_contratual(
    jogador: dict[str, Any],
    banco: dict[str, Any],
    rodada_atual: int,
    total_corridas: int,
    *,
    avaliacao: dict[str, Any] | None = None,
    ignorar_cadencia: bool = False,
) -> dict[str, Any] | None:
    """
    Gera alerta de contrato no ultimo ano com variacao por desempenho.
    """
    if not isinstance(jogador, dict):
        return None

    contrato_anos = _safe_int(jogador.get("contrato_anos"), 1)
    if contrato_anos > 1:
        return None

    categoria_id = _texto(jogador.get("categoria_atual"))
    rodada = max(1, _safe_int(rodada_atual, 1))
    total = max(1, _safe_int(total_corridas, 1))
    progresso = float(rodada) / float(total)

    if not _cadencia_permite_alerta(
        banco,
        rodada_atual=rodada,
        categoria_id=categoria_id,
        ignorar_cadencia=ignorar_cadencia,
    ):
        return None

    classificacao = obter_classificacao_categoria(banco, categoria_id)
    total_pilotos = max(1, len(classificacao))
    posicao = next(
        (
            _safe_int(item.get("posicao"), total_pilotos)
            for item in classificacao
            if isinstance(item, dict) and _ids_equivalentes(item.get("piloto_id"), jogador.get("id"))
        ),
        total_pilotos,
    )
    percentil = float(posicao) / float(total_pilotos)

    vis = _extrair_visibilidade(jogador, posicao, total_pilotos)
    equipe = _obter_equipe_por_id(banco, jogador.get("equipe_id")) or {}
    nome_equipe = _texto(equipe.get("nome")) or "Sua equipe"

    desempenho_bom = percentil <= 0.3
    desempenho_medio = percentil <= 0.6
    desempenho_ruim = percentil > 0.6
    tipo = _tipo_por_avaliacao(
        avaliacao,
        desempenho_bom=desempenho_bom,
        desempenho_medio=desempenho_medio,
        desempenho_ruim=desempenho_ruim,
    )

    # Fase 1: metade da temporada.
    if 0.4 <= progresso < 0.55:
        return {
            "tipo": "info",
            "icone": "📋",
            "titulo": "Contrato em Observacao",
            "texto": (
                f"Seu contrato com {nome_equipe} termina no fim da temporada. "
                "Seu desempenho esta em avaliacao."
            ),
            "detalhe": f"Visibilidade no mercado: {vis}/10",
            "categoria_id": categoria_id,
        }

    # Fase 2: tercio final.
    if 0.6 <= progresso < 0.8:
        if tipo == "positivo":
            return {
                "tipo": "positivo",
                "icone": "📋",
                "titulo": "Interesse de Renovacao",
                "texto": (
                    f"{nome_equipe} esta satisfeita com seu rendimento. "
                    "Renovacao e provavel."
                ),
                "detalhe": f"Posicao: {posicao}o | Visibilidade: {vis}/10",
                "categoria_id": categoria_id,
            }
        if tipo == "perigo":
            return {
                "tipo": "perigo",
                "icone": "🚨",
                "titulo": "Risco Contratual",
                "texto": (
                    f"{nome_equipe} demonstra insatisfacao. "
                    "Existe risco real de nao renovacao."
                ),
                "detalhe": f"Posicao: {posicao}o | Visibilidade: {vis}/10",
                "categoria_id": categoria_id,
            }
        return {
            "tipo": "alerta",
            "icone": "⚠️",
            "titulo": "Contrato Incerto",
            "texto": (
                f"{nome_equipe} esta avaliando alternativas. "
                "Melhore os resultados para garantir a vaga."
            ),
            "detalhe": f"Posicao atual: {posicao}o",
            "categoria_id": categoria_id,
        }

    # Fase 3: reta final (obrigatorio ter sinalizacao no ultimo ano).
    if progresso >= 0.8:
        corridas_restantes = max(0, total - rodada)
        if tipo == "positivo":
            if vis >= 7:
                return {
                    "tipo": "positivo",
                    "icone": "🌟",
                    "titulo": "Alta Demanda",
                    "texto": (
                        "Equipes de nivel superior estao observando seu desempenho. "
                        "Propostas fortes podem chegar no fim da temporada."
                    ),
                    "detalhe": f"Visibilidade: {vis}/10",
                    "categoria_id": categoria_id,
                }
            return {
                "tipo": "positivo",
                "icone": "📋",
                "titulo": "Renovacao Provavel",
                "texto": f"{nome_equipe} pretende renovar seu contrato.",
                "detalhe": f"Posicao atual: {posicao}o",
                "categoria_id": categoria_id,
            }

        if tipo == "perigo":
            return {
                "tipo": "perigo",
                "icone": "🚨",
                "titulo": "Futuro Incerto",
                "texto": (
                    "Poucas equipes demonstraram interesse ate agora. "
                    "Existe risco de ficar sem vaga na proxima temporada."
                ),
                "detalhe": (
                    f"Posicao: {posicao}o | Visibilidade: {vis}/10 | "
                    f"Restam {corridas_restantes} corrida(s)"
                ),
                "categoria_id": categoria_id,
            }

        return {
            "tipo": "alerta",
            "icone": "⚠️",
            "titulo": "Ultimas Corridas Decisivas",
            "texto": (
                "As ultimas corridas vao definir sua renovacao. "
                "Cada ponto faz diferenca."
            ),
            "detalhe": f"Posicao: {posicao}o | Visibilidade: {vis}/10",
            "categoria_id": categoria_id,
        }

    return None


def registrar_alerta_contratual(
    banco: dict[str, Any],
    *,
    rodada_atual: int,
    categoria_id: str,
    alerta: dict[str, Any],
) -> None:
    """Salva metadados do ultimo alerta emitido para controlar cadencia."""
    banco["ultimo_alerta_contrato"] = {
        "rodada": max(1, _safe_int(rodada_atual, 1)),
        "categoria_id": _texto(categoria_id),
        "tipo": _texto((alerta or {}).get("tipo", "info")) or "info",
        "icone": _texto((alerta or {}).get("icone", "")),
        "titulo": _texto((alerta or {}).get("titulo", "Contrato")),
        "texto": _texto((alerta or {}).get("texto", "")),
        "detalhe": _texto((alerta or {}).get("detalhe", "")),
    }
