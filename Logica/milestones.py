"""Sistema de marcos da carreira (milestones)."""

from __future__ import annotations

from typing import Any, Callable


def _safe_int(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(padrao)


def _categoria(valor: Any) -> str:
    return str(valor or "").strip().lower()


def _bool(valor: Any) -> bool:
    return bool(valor)


MilestoneCheck = Callable[[dict[str, Any]], bool]


MILESTONES: list[dict[str, Any]] = [
    {
        "id": "primeira_corrida",
        "titulo": "Estreia",
        "descricao": "Sua primeira corrida na carreira!",
        "icone": "🏁",
        "check": lambda jogador: _safe_int(jogador.get("corridas_carreira"), 0) >= 1,
        "progresso": ("corridas_carreira", 1),
    },
    {
        "id": "primeiro_top10",
        "titulo": "No Top 10",
        "descricao": "Primeiro resultado no top 10!",
        "icone": "🎯",
        "check": lambda jogador: _safe_int(jogador.get("melhor_resultado_temporada"), 99) <= 10,
        "progresso": ("melhor_resultado_temporada_invertido", 10),
    },
    {
        "id": "primeiro_top5",
        "titulo": "Top 5!",
        "descricao": "Primeiro resultado no top 5 da carreira!",
        "icone": "⭐",
        "check": lambda jogador: _safe_int(jogador.get("melhor_resultado_carreira"), 99) <= 5,
        "progresso": ("melhor_resultado_carreira_invertido", 5),
    },
    {
        "id": "primeiro_podio",
        "titulo": "Primeiro Podio!",
        "descricao": "Seu primeiro podio na carreira!",
        "icone": "🥉",
        "check": lambda jogador: _safe_int(jogador.get("podios_carreira"), 0) >= 1,
        "progresso": ("podios_carreira", 1),
    },
    {
        "id": "primeira_vitoria",
        "titulo": "Primeira Vitoria!",
        "descricao": "Sua primeira vitoria! Momento inesquecivel!",
        "icone": "🏆",
        "check": lambda jogador: _safe_int(jogador.get("vitorias_carreira"), 0) >= 1,
        "progresso": ("vitorias_carreira", 1),
    },
    {
        "id": "primeira_pole",
        "titulo": "Pole Position!",
        "descricao": "Sua primeira pole position!",
        "icone": "⏱️",
        "check": lambda jogador: _safe_int(jogador.get("poles_carreira"), 0) >= 1,
        "progresso": ("poles_carreira", 1),
    },
    {
        "id": "10_corridas",
        "titulo": "10 Corridas",
        "descricao": "10 corridas disputadas na carreira!",
        "icone": "🔟",
        "check": lambda jogador: _safe_int(jogador.get("corridas_carreira"), 0) >= 10,
        "progresso": ("corridas_carreira", 10),
    },
    {
        "id": "25_corridas",
        "titulo": "25 Corridas",
        "descricao": "Veterano em formacao - 25 corridas!",
        "icone": "🏅",
        "check": lambda jogador: _safe_int(jogador.get("corridas_carreira"), 0) >= 25,
        "progresso": ("corridas_carreira", 25),
    },
    {
        "id": "50_corridas",
        "titulo": "50 Corridas",
        "descricao": "Meio centenario! 50 corridas na carreira!",
        "icone": "🎖️",
        "check": lambda jogador: _safe_int(jogador.get("corridas_carreira"), 0) >= 50,
        "progresso": ("corridas_carreira", 50),
    },
    {
        "id": "100_corridas",
        "titulo": "Centenario",
        "descricao": "100 corridas! Uma carreira lendaria!",
        "icone": "💯",
        "check": lambda jogador: _safe_int(jogador.get("corridas_carreira"), 0) >= 100,
        "progresso": ("corridas_carreira", 100),
    },
    {
        "id": "5_vitorias",
        "titulo": "5 Vitorias",
        "descricao": "5 vitorias na carreira!",
        "icone": "🏆",
        "check": lambda jogador: _safe_int(jogador.get("vitorias_carreira"), 0) >= 5,
        "progresso": ("vitorias_carreira", 5),
    },
    {
        "id": "10_vitorias",
        "titulo": "10 Vitorias",
        "descricao": "Duplo digito! 10 vitorias!",
        "icone": "🏆🏆",
        "check": lambda jogador: _safe_int(jogador.get("vitorias_carreira"), 0) >= 10,
        "progresso": ("vitorias_carreira", 10),
    },
    {
        "id": "10_podios",
        "titulo": "10 Podios",
        "descricao": "10 podios na carreira!",
        "icone": "🥇",
        "check": lambda jogador: _safe_int(jogador.get("podios_carreira"), 0) >= 10,
        "progresso": ("podios_carreira", 10),
    },
    {
        "id": "promo_amador",
        "titulo": "Promocao ao Amador",
        "descricao": "Voce subiu para o nivel Amador!",
        "icone": "⬆️",
        "check": lambda jogador: _categoria(jogador.get("categoria_atual")) in {"mazda_amador", "toyota_amador", "bmw_m2"},
        "progresso": None,
    },
    {
        "id": "promo_production",
        "titulo": "Production Challenger",
        "descricao": "Voce chegou ao topo da Trilha PRO!",
        "icone": "⬆️⬆️",
        "check": lambda jogador: _categoria(jogador.get("categoria_atual")) == "production_challenger",
        "progresso": None,
    },
    {
        "id": "promo_gt4",
        "titulo": "GT4 Challenge",
        "descricao": "Voce entrou no mundo GT!",
        "icone": "🏎️",
        "check": lambda jogador: _categoria(jogador.get("categoria_atual")) == "gt4",
        "progresso": None,
    },
    {
        "id": "promo_gt3",
        "titulo": "GT3 Championship",
        "descricao": "O mais alto nivel! GT3 Championship!",
        "icone": "🏎️🏎️",
        "check": lambda jogador: _categoria(jogador.get("categoria_atual")) == "gt3",
        "progresso": None,
    },
    {
        "id": "promo_endurance",
        "titulo": "Endurance",
        "descricao": "Corridas de endurance! O apice do automobilismo!",
        "icone": "🏁🏁",
        "check": lambda jogador: _categoria(jogador.get("categoria_atual")) == "endurance",
        "progresso": None,
    },
    {
        "id": "primeiro_titulo",
        "titulo": "Campeao!",
        "descricao": "Seu primeiro titulo de campeonato!",
        "icone": "👑",
        "check": lambda jogador: _safe_int(jogador.get("titulos"), 0) >= 1,
        "progresso": ("titulos", 1),
    },
    {
        "id": "2_titulos",
        "titulo": "Bicampeao",
        "descricao": "Dois titulos na carreira!",
        "icone": "👑👑",
        "check": lambda jogador: _safe_int(jogador.get("titulos"), 0) >= 2,
        "progresso": ("titulos", 2),
    },
    {
        "id": "3_titulos",
        "titulo": "Tricampeao",
        "descricao": "Tres titulos! Lenda!",
        "icone": "👑👑👑",
        "check": lambda jogador: _safe_int(jogador.get("titulos"), 0) >= 3,
        "progresso": ("titulos", 3),
    },
    {
        "id": "sobrevivente",
        "titulo": "Sobrevivente",
        "descricao": "Terminou uma corrida com 5+ incidentes sem ser afetado!",
        "icone": "🛡️",
        "check": None,
        "progresso": None,
    },
    {
        "id": "comeback",
        "titulo": "Comeback King",
        "descricao": "Venceu apos largar de P10 ou pior!",
        "icone": "🔥",
        "check": None,
        "progresso": None,
    },
    {
        "id": "n2_para_n1",
        "titulo": "Superacao",
        "descricao": "Comecou como N2 e foi promovido a N1!",
        "icone": "💪",
        "check": None,
        "progresso": None,
    },
]


def _obter_milestone_por_id(milestone_id: str) -> dict[str, Any] | None:
    for milestone in MILESTONES:
        if milestone.get("id") == milestone_id:
            return milestone
    return None


def _registrar_historico_milestone(
    jogador: dict[str, Any],
    banco: dict[str, Any],
    milestone: dict[str, Any],
    *,
    rodada: int | None = None,
) -> None:
    historico = banco.get("historico_milestones")
    if not isinstance(historico, list):
        historico = []
        banco["historico_milestones"] = historico

    marco_id = str(milestone.get("id", "") or "")
    if not marco_id:
        return

    if any(isinstance(item, dict) and item.get("id") == marco_id for item in historico):
        return

    registro = {
        "id": marco_id,
        "titulo": str(milestone.get("titulo", "Marco") or "Marco"),
        "descricao": str(milestone.get("descricao", "") or ""),
        "icone": str(milestone.get("icone", "🏆") or "🏆"),
        "temporada": _safe_int(banco.get("ano_atual"), 0),
        "rodada": _safe_int(rodada if rodada is not None else banco.get("rodada_atual"), 0),
        "categoria_id": str(jogador.get("categoria_atual", "") or ""),
    }
    historico.append(registro)


def verificar_milestones(
    jogador: dict[str, Any],
    banco: dict[str, Any],
    contexto: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Verifica e retorna marcos novos atingidos, evitando repeticao.
    """
    if not isinstance(jogador, dict):
        return []

    desbloqueados_raw = jogador.get("milestones_desbloqueados")
    if not isinstance(desbloqueados_raw, list):
        desbloqueados_raw = []
    desbloqueados = set(str(item) for item in desbloqueados_raw if str(item).strip())

    novos: list[dict[str, Any]] = []
    rodada_contexto = _safe_int((contexto or {}).get("rodada"), _safe_int(banco.get("rodada_atual"), 0))

    for milestone in MILESTONES:
        marco_id = str(milestone.get("id", "") or "")
        check = milestone.get("check")
        if not marco_id or marco_id in desbloqueados:
            continue
        if callable(check) and bool(check(jogador)):
            novos.append(milestone)
            desbloqueados.add(marco_id)
            _registrar_historico_milestone(jogador, banco, milestone, rodada=rodada_contexto)

    contexto = contexto or {}
    tipo_contexto = str(contexto.get("tipo", "") or "")

    if tipo_contexto == "pos_corrida":
        resultado = contexto.get("resultado", {})
        total_incidentes = _safe_int(contexto.get("total_incidentes"), 0)

        if (
            "sobrevivente" not in desbloqueados
            and total_incidentes >= 5
            and not _bool((resultado or {}).get("dnf"))
        ):
            milestone = _obter_milestone_por_id("sobrevivente")
            if milestone:
                novos.append(milestone)
                desbloqueados.add("sobrevivente")
                _registrar_historico_milestone(jogador, banco, milestone, rodada=rodada_contexto)

        if (
            "comeback" not in desbloqueados
            and _safe_int((resultado or {}).get("posicao"), 99) == 1
            and _safe_int((resultado or {}).get("grid"), 1) >= 10
        ):
            milestone = _obter_milestone_por_id("comeback")
            if milestone:
                novos.append(milestone)
                desbloqueados.add("comeback")
                _registrar_historico_milestone(jogador, banco, milestone, rodada=rodada_contexto)

    if tipo_contexto == "hierarquia":
        if (
            "n2_para_n1" not in desbloqueados
            and _bool(contexto.get("invertido"))
            and _bool(contexto.get("jogador_virou_n1"))
        ):
            milestone = _obter_milestone_por_id("n2_para_n1")
            if milestone:
                novos.append(milestone)
                desbloqueados.add("n2_para_n1")
                _registrar_historico_milestone(jogador, banco, milestone, rodada=rodada_contexto)

    jogador["milestones_desbloqueados"] = sorted(desbloqueados)
    return novos


def obter_historico_milestones(banco: dict[str, Any]) -> list[dict[str, Any]]:
    historico = banco.get("historico_milestones")
    if not isinstance(historico, list):
        return []
    return [item for item in historico if isinstance(item, dict)]


def _progresso_milestone(jogador: dict[str, Any], milestone: dict[str, Any]) -> tuple[int, int] | None:
    progresso = milestone.get("progresso")
    if not isinstance(progresso, tuple) or len(progresso) != 2:
        return None

    campo, alvo_raw = progresso
    alvo = max(1, _safe_int(alvo_raw, 1))
    campo_texto = str(campo or "")

    if campo_texto == "melhor_resultado_temporada_invertido":
        melhor = _safe_int(jogador.get("melhor_resultado_temporada"), 99)
        atual = 0 if melhor > alvo else alvo - max(0, melhor - 1)
        return atual, alvo
    if campo_texto == "melhor_resultado_carreira_invertido":
        melhor = _safe_int(jogador.get("melhor_resultado_carreira"), 99)
        atual = 0 if melhor > alvo else alvo - max(0, melhor - 1)
        return atual, alvo

    atual = max(0, _safe_int(jogador.get(campo_texto), 0))
    return atual, alvo


def obter_proximo_milestone(jogador: dict[str, Any]) -> dict[str, Any] | None:
    """Retorna o proximo milestone numerico ainda nao desbloqueado."""
    desbloqueados = set(
        str(item)
        for item in (jogador.get("milestones_desbloqueados") or [])
        if str(item).strip()
    )

    candidatos: list[tuple[float, dict[str, Any], int, int]] = []
    for milestone in MILESTONES:
        marco_id = str(milestone.get("id", "") or "")
        if not marco_id or marco_id in desbloqueados:
            continue
        progresso = _progresso_milestone(jogador, milestone)
        if not progresso:
            continue
        atual, alvo = progresso
        if atual >= alvo:
            continue
        distancia = float(alvo - atual) / float(alvo)
        candidatos.append((distancia, milestone, atual, alvo))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: (item[0], item[1].get("titulo", "")))
    _distancia, milestone, atual, alvo = candidatos[0]
    return {
        "id": milestone.get("id"),
        "titulo": milestone.get("titulo", "Proximo marco"),
        "icone": milestone.get("icone", "🏁"),
        "descricao": milestone.get("descricao", ""),
        "atual": atual,
        "alvo": alvo,
    }

