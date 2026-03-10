"""
Estruturas base para series paralelas.
"""

from __future__ import annotations

import random

from Dados.constantes import CATEGORIAS, PONTOS_POR_POSICAO


PCC_CATEGORIAS_ORIGEM = ("mazda_amador", "toyota_amador", "bmw_m2")
PCC_LIMITE_POR_CATEGORIA = 6
PCC_MESES = (
    (3, "Marco"),
    (5, "Maio"),
    (7, "Julho"),
    (9, "Setembro"),
)


def garantir_series_especiais(banco: dict) -> dict:
    """Garante a estrutura raiz das series paralelas no banco."""
    banco.setdefault("series_especiais", {})
    pcc = banco["series_especiais"].setdefault(
        "production_car_challenge",
        {
            "id": "production_car_challenge",
            "nome": "Production Car Challenge",
            "ativa": True,
            "categorias_origem": list(PCC_CATEGORIAS_ORIGEM),
            "arquivo_season": "",
            "temporadas": {},
            "historico": [],
        },
    )
    pcc.setdefault("arquivo_season", "")
    pcc.setdefault("temporadas", {})
    pcc.setdefault("historico", [])
    return pcc


def inicializar_production_car_challenge(banco: dict, ano: int) -> dict:
    """
    Cria a temporada anual do Production Car Challenge, se ainda nao existir.

    Nesta etapa, a serie nasce apenas como estrutura de calendario, participantes
    base e estado do convite do jogador. Nenhuma corrida e simulada aqui.
    """
    pcc = garantir_series_especiais(banco)
    ano_key = str(int(ano))

    if ano_key in pcc["temporadas"]:
        return pcc["temporadas"][ano_key]

    participantes_base = _coletar_participantes_base(banco)
    temporada = {
        "ano": int(ano),
        "nome": "Production Car Challenge",
        "status": "planejada",
        "categorias_origem": list(PCC_CATEGORIAS_ORIGEM),
        "arquivo_season": "",
        "participantes_base": participantes_base,
        "eventos": _gerar_eventos_pcc(int(ano)),
        "classificacao": [],
        "historico_resultados": [],
        "jogador": _criar_estado_jogador_pcc(banco, int(ano)),
    }

    pcc["temporadas"][ano_key] = temporada
    return temporada


def sincronizar_production_car_challenge(banco: dict) -> bool:
    """
    Atualiza o estado do PCC com base no andamento da temporada principal.

    Nesta etapa:
    - dispara o convite do jogador quando o calendario chega ao mes do evento;
    - marca o proximo evento paralelo relevante para exibicao.
    """
    ano = int(banco.get("ano_atual", 2024))
    temporada = inicializar_production_car_challenge(banco, ano)
    jogador = temporada.setdefault("jogador", _criar_estado_jogador_pcc(banco, ano))
    eventos = temporada.get("eventos", [])
    changed = False

    proximo_evento = _obter_proximo_evento_pcc(eventos)
    if proximo_evento is None:
        temporada["status"] = "encerrada"
        temporada["proximo_evento"] = None
        return changed

    mes_principal = obter_mes_proxima_rodada_principal(
        int(banco.get("rodada_atual", 1)),
        int(banco.get("total_rodadas", 24)),
        bool(banco.get("temporada_concluida", False)),
    )

    if jogador.get("elegivel", False):
        convite_previsto = int(jogador.get("convite_previsto_mes") or 0)
        if convite_previsto and mes_principal >= convite_previsto:
            if jogador.get("status_convite") == "planejado":
                jogador["status_convite"] = "convidado"
                jogador["motivo"] = (
                    f"Convite liberado para {proximo_evento['nome']} "
                    f"em {proximo_evento['mes_nome']}"
                )
                changed = True
            if not proximo_evento.get("convites_disparados", False):
                proximo_evento["convites_disparados"] = True
                changed = True

    temporada["status"] = "ativa"
    temporada["proximo_evento"] = {
        "rodada": proximo_evento.get("rodada"),
        "nome": proximo_evento.get("nome"),
        "mes": proximo_evento.get("mes"),
        "mes_nome": proximo_evento.get("mes_nome"),
        "jogador_convidado": jogador.get("status_convite") == "convidado",
    }
    return changed


def obter_proximo_evento_exibicao(banco: dict) -> dict | None:
    """
    Retorna o proximo evento relevante para a UI.

    Nesta etapa o valor e apenas informativo. A simulacao principal continua
    ligada a _get_corrida_atual() da categoria atual.
    """
    sincronizar_production_car_challenge(banco)

    principal = _obter_proximo_evento_principal(banco)
    pcc = _obter_proximo_evento_pcc_ui(banco)

    if principal is None:
        return pcc
    if pcc is None:
        return principal

    chave_principal = (
        int(principal.get("mes", 99)),
        1,
        int(principal.get("rodada", 999)),
    )
    chave_pcc = (
        int(pcc.get("mes", 99)),
        0,
        int(pcc.get("rodada", 999)),
    )
    return pcc if chave_pcc <= chave_principal else principal


def _coletar_participantes_base(banco: dict) -> list[dict]:
    participantes = []

    for piloto in banco.get("pilotos", []):
        categoria_id = piloto.get("categoria_atual")
        if categoria_id not in PCC_CATEGORIAS_ORIGEM:
            continue
        if piloto.get("aposentado", False):
            continue

        participantes.append(
            {
                "piloto_id": piloto.get("id"),
                "nome": piloto.get("nome", ""),
                "categoria_origem": categoria_id,
                "categoria_nivel": _obter_nivel_categoria(categoria_id),
                "equipe_id": piloto.get("equipe_id"),
                "equipe_nome": piloto.get("equipe_nome", ""),
                "skill": float(piloto.get("skill", 0)),
                "is_jogador": bool(piloto.get("is_jogador", False)),
                "status_convite": (
                    "planejado"
                    if piloto.get("is_jogador", False)
                    else "pool"
                ),
            }
        )

    participantes.sort(
        key=lambda participante: (
            participante["categoria_nivel"],
            -participante["skill"],
            participante["nome"].casefold(),
        )
    )
    return participantes


def _criar_estado_jogador_pcc(banco: dict, ano: int) -> dict:
    jogador = next(
        (piloto for piloto in banco.get("pilotos", []) if piloto.get("is_jogador", False)),
        None,
    )

    if not jogador:
        return {
            "elegivel": False,
            "status_convite": "sem_jogador",
            "convite_previsto_rodada": None,
            "convite_previsto_mes": None,
        }

    categoria_id = jogador.get("categoria_atual")
    elegivel = categoria_id in PCC_CATEGORIAS_ORIGEM

    return {
        "elegivel": elegivel,
        "status_convite": "planejado" if elegivel else "nao_elegivel",
        "motivo": (
            f"Convite previsto para {PCC_MESES[0][1]} de {ano}"
            if elegivel
            else "Categoria atual fora da serie paralela"
        ),
        "piloto_id": jogador.get("id"),
        "categoria_atual": categoria_id,
        "convite_previsto_rodada": 1 if elegivel else None,
        "convite_previsto_mes": PCC_MESES[0][0] if elegivel else None,
    }


def _gerar_eventos_pcc(ano: int) -> list[dict]:
    eventos = []
    for rodada, (mes, mes_nome) in enumerate(PCC_MESES, start=1):
        eventos.append(
            {
                "rodada": rodada,
                "nome": f"Production Car Challenge - Rodada {rodada}",
                "ano": ano,
                "mes": mes,
                "mes_nome": mes_nome,
                "status": "agendada",
                "grid_montado": False,
                "convites_disparados": False,
                "participantes_confirmados": [],
                "resultado_processado": False,
            }
        )
    return eventos


def _obter_proximo_evento_pcc(eventos: list[dict]) -> dict | None:
    for evento in eventos:
        if not evento.get("resultado_processado", False):
            return evento
    return None


def _obter_proximo_evento_pcc_ui(banco: dict) -> dict | None:
    ano = int(banco.get("ano_atual", 2024))
    temporada = (
        banco.get("series_especiais", {})
        .get("production_car_challenge", {})
        .get("temporadas", {})
        .get(str(ano))
    )
    if not temporada:
        return None

    jogador = temporada.get("jogador", {})
    if jogador.get("status_convite") not in {"convidado", "participando"}:
        return None

    evento = _obter_proximo_evento_pcc(temporada.get("eventos", []))
    if not evento:
        return None

    return {
        "tipo_evento": "pcc",
        "nome": evento.get("nome", "Production Car Challenge"),
        "circuito": evento.get("circuito", "Serie paralela invitational"),
        "clima": "-",
        "temperatura": "-",
        "voltas": "-",
        "mes": int(evento.get("mes", 99)),
        "mes_nome": evento.get("mes_nome", ""),
        "rodada": int(evento.get("rodada", 0)),
        "categoria_label": "Production Car Challenge",
        "detalhe": jogador.get("motivo", ""),
    }


def obter_estado_pcc_atual(banco: dict) -> tuple[dict, dict] | tuple[None, None]:
    ano = int(banco.get("ano_atual", 2024))
    temporada = inicializar_production_car_challenge(banco, ano)
    evento = _obter_proximo_evento_pcc(temporada.get("eventos", []))
    if not evento:
        return None, None
    return temporada, evento


def obter_arquivo_season_pcc(banco: dict) -> str:
    temporada, _ = obter_estado_pcc_atual(banco)
    if not temporada:
        return ""

    arquivo = str(temporada.get("arquivo_season", "")).strip()
    if arquivo:
        return arquivo

    pcc = garantir_series_especiais(banco)
    return str(pcc.get("arquivo_season", "")).strip()


def definir_arquivo_season_pcc(banco: dict, arquivo: str, corridas: list[dict]) -> None:
    pcc = garantir_series_especiais(banco)
    temporada, _ = obter_estado_pcc_atual(banco)
    if not temporada:
        return

    arquivo = str(arquivo or "").strip()
    pcc["arquivo_season"] = arquivo
    temporada["arquivo_season"] = arquivo

    eventos = temporada.get("eventos", [])
    for indice, evento in enumerate(eventos):
        if indice < len(corridas):
            corrida = corridas[indice]
            evento["circuito"] = f"Track ID {corrida.get('track_id', '???')}"
            evento["importado"] = True
        else:
            evento.setdefault("circuito", "Serie paralela invitational")


def obter_grid_proximo_evento_pcc(banco: dict) -> list[dict]:
    temporada, evento = obter_estado_pcc_atual(banco)
    if not temporada or not evento:
        return []

    grid = evento.get("participantes_confirmados", [])
    if grid:
        return grid

    grid = _montar_grid_evento_pcc(banco, temporada)
    evento["participantes_confirmados"] = grid
    evento["grid_montado"] = bool(grid)
    return grid


def simular_proximo_evento_pcc(banco: dict) -> list[dict]:
    temporada, evento = obter_estado_pcc_atual(banco)
    if not temporada or not evento:
        return []

    participantes = obter_grid_proximo_evento_pcc(banco)
    if not participantes:
        return []

    try:
        from Logica.equipes import obter_equipe_piloto
        from Logica.simulacao import calcular_performance_piloto
    except ImportError:
        return []

    resultados = []
    for participante in participantes:
        piloto = _localizar_piloto_global(banco, participante.get("piloto_id"))
        if not piloto:
            continue

        equipe = obter_equipe_piloto(banco, piloto)
        performance = calcular_performance_piloto(piloto, equipe)

        agressividade = float(piloto.get("aggression", 0.5) or 0.5)
        chance_dnf = agressividade * 0.08
        if equipe:
            confiabilidade = equipe.get("stats", {}).get("confiabilidade", 70) / 100
            chance_dnf += (1 - confiabilidade) * 0.05

        dnf = random.random() < chance_dnf
        resultados.append(
            {
                "piloto_id": piloto.get("id"),
                "piloto_nome": piloto.get("nome", "???"),
                "dnf": dnf,
                "performance": 0 if dnf else performance,
            }
        )

    resultados.sort(key=lambda item: (bool(item.get("dnf", False)), -float(item.get("performance", 0))))

    volta_rapida_id = None
    finalistas = [item for item in resultados if not item.get("dnf", False)]
    if finalistas:
        volta_rapida_id = max(finalistas, key=lambda item: float(item.get("performance", 0))).get("piloto_id")

    classificacao = []
    for entrada in resultados:
        classificacao.append(
            {
                "piloto_id": entrada.get("piloto_id"),
                "piloto_nome": entrada.get("piloto_nome", "???"),
                "dnf": bool(entrada.get("dnf", False)),
                "volta_rapida": (
                    not bool(entrada.get("dnf", False))
                    and entrada.get("piloto_id") == volta_rapida_id
                ),
            }
        )

    return classificacao


def aplicar_resultado_pcc(
    banco: dict,
    classificacao: list[dict],
    origem: str = "simulada",
) -> int:
    temporada, evento = obter_estado_pcc_atual(banco)
    if not temporada or not evento:
        return 0

    participantes = obter_grid_proximo_evento_pcc(banco)
    if not participantes:
        return 0

    participantes_por_id = {
        participante.get("piloto_id"): participante
        for participante in participantes
        if participante.get("piloto_id") is not None
    }
    participantes_por_nome = {
        _normalizar_nome(participante.get("nome", "")): participante
        for participante in participantes
    }

    tabela = temporada.setdefault("classificacao", [])
    tabela_por_id = {
        entrada.get("piloto_id"): entrada
        for entrada in tabela
        if entrada.get("piloto_id") is not None
    }

    resultado_evento = []
    aplicados = 0

    for posicao, entrada in enumerate(classificacao, start=1):
        piloto_id = entrada.get("piloto_id", entrada.get("id"))
        participante = participantes_por_id.get(piloto_id)

        if participante is None:
            nome = (
                entrada.get("piloto_nome")
                or entrada.get("piloto")
                or entrada.get("nome")
                or ""
            )
            participante = participantes_por_nome.get(_normalizar_nome(nome))

        if participante is None:
            continue

        piloto_id = participante.get("piloto_id")
        dnf = bool(entrada.get("dnf", False))
        volta_rapida = bool(entrada.get("volta_rapida", False))
        pontos = 0 if dnf else int(PONTOS_POR_POSICAO.get(posicao, 0))
        if volta_rapida and not dnf and posicao <= 10:
            pontos += 1

        registro = tabela_por_id.get(piloto_id)
        if registro is None:
            registro = {
                "piloto_id": piloto_id,
                "nome": participante.get("nome", "???"),
                "categoria_origem": participante.get("categoria_origem", ""),
                "equipe_nome": participante.get("equipe_nome", ""),
                "pontos": 0,
                "vitorias": 0,
                "podios": 0,
                "corridas": 0,
                "dnfs": 0,
                "resultados": [],
            }
            tabela.append(registro)
            tabela_por_id[piloto_id] = registro

        registro["corridas"] += 1
        if dnf:
            registro["dnfs"] += 1
            registro["resultados"].append("DNF")
        else:
            registro["pontos"] += pontos
            registro["resultados"].append(posicao)
            if posicao == 1:
                registro["vitorias"] += 1
            if posicao <= 3:
                registro["podios"] += 1

        resultado_evento.append(
            {
                "posicao": posicao,
                "piloto_id": piloto_id,
                "piloto_nome": participante.get("nome", "???"),
                "categoria_origem": participante.get("categoria_origem", ""),
                "dnf": dnf,
                "volta_rapida": volta_rapida,
                "pontos": pontos,
            }
        )
        aplicados += 1

    tabela.sort(
        key=lambda item: (
            -int(item.get("pontos", 0)),
            -int(item.get("vitorias", 0)),
            -int(item.get("podios", 0)),
            str(item.get("nome", "")).casefold(),
        )
    )
    for indice, item in enumerate(tabela, start=1):
        item["posicao"] = indice

    if aplicados > 0:
        evento["resultado"] = resultado_evento
        evento["resultado_processado"] = True
        evento["status"] = "concluida"
        evento["origem_resultado"] = origem
        temporada.setdefault("historico_resultados", []).append(
            {
                "rodada": evento.get("rodada"),
                "nome": evento.get("nome", ""),
                "origem": origem,
                "resultado": resultado_evento,
            }
        )

        jogador = temporada.setdefault("jogador", {})
        if jogador.get("status_convite") == "convidado":
            jogador["status_convite"] = "participando"
            jogador["motivo"] = f"Participando do {evento.get('nome', 'PCC')}"

        proximo_evento = _obter_proximo_evento_pcc(temporada.get("eventos", []))
        if proximo_evento is None:
            temporada["status"] = "encerrada"
        else:
            temporada["status"] = "ativa"

    return aplicados


def _montar_grid_evento_pcc(banco: dict, temporada: dict) -> list[dict]:
    participantes_por_categoria: dict[str, list[dict]] = {}

    for participante in _coletar_participantes_base(banco):
        categoria_id = participante.get("categoria_origem")
        participantes_por_categoria.setdefault(categoria_id, []).append(participante)

    grid: list[dict] = []
    for categoria_id in PCC_CATEGORIAS_ORIGEM:
        candidatos = participantes_por_categoria.get(categoria_id, [])
        grid.extend(candidatos[:PCC_LIMITE_POR_CATEGORIA])

    jogador = temporada.get("jogador", {})
    jogador_id = jogador.get("piloto_id")
    if jogador.get("status_convite") in {"convidado", "participando"} and jogador_id is not None:
        if not any(item.get("piloto_id") == jogador_id for item in grid):
            piloto_jogador = _localizar_piloto_global(banco, jogador_id)
            if piloto_jogador:
                grid.append(
                    {
                        "piloto_id": piloto_jogador.get("id"),
                        "nome": piloto_jogador.get("nome", ""),
                        "categoria_origem": piloto_jogador.get("categoria_atual", ""),
                        "categoria_nivel": _obter_nivel_categoria(
                            piloto_jogador.get("categoria_atual", "")
                        ),
                        "equipe_id": piloto_jogador.get("equipe_id"),
                        "equipe_nome": piloto_jogador.get("equipe_nome", ""),
                        "skill": float(piloto_jogador.get("skill", 0)),
                        "is_jogador": True,
                        "status_convite": "confirmado",
                    }
                )

    vistos: set[int] = set()
    grid_filtrado = []
    for participante in grid:
        piloto_id = participante.get("piloto_id")
        if piloto_id in vistos or piloto_id is None:
            continue
        vistos.add(piloto_id)
        grid_filtrado.append(participante)

    grid_filtrado.sort(
        key=lambda item: (
            item.get("categoria_nivel", 999),
            -float(item.get("skill", 0)),
            str(item.get("nome", "")).casefold(),
        )
    )
    return grid_filtrado


def _localizar_piloto_global(banco: dict, piloto_id: int | None) -> dict | None:
    if piloto_id is None:
        return None

    for piloto in banco.get("pilotos", []):
        if piloto.get("id") == piloto_id and not piloto.get("aposentado", False):
            return piloto
    return None


def _normalizar_nome(nome: str) -> str:
    return " ".join(str(nome or "").strip().casefold().split())


def _obter_proximo_evento_principal(banco: dict) -> dict | None:
    if bool(banco.get("temporada_concluida", False)):
        return None

    rodada = int(banco.get("rodada_atual", 1))
    total = int(banco.get("total_rodadas", 24))
    if rodada < 1 or rodada > total:
        return None

    calendario = banco.get("calendario", [])
    if calendario and rodada <= len(calendario):
        corrida = dict(calendario[rodada - 1])
    else:
        corrida = {
            "nome": f"Rodada {rodada}",
            "circuito": "Circuito aleatorio",
            "clima": "-",
            "temperatura": "-",
            "voltas": "-",
        }

    corrida["tipo_evento"] = "principal"
    corrida["rodada"] = rodada
    corrida["mes"] = obter_mes_proxima_rodada_principal(rodada, total, False)
    corrida["mes_nome"] = _nome_mes(corrida["mes"])
    corrida["categoria_label"] = "Campeonato principal"
    return corrida


def obter_mes_proxima_rodada_principal(
    rodada_atual: int,
    total_rodadas: int,
    temporada_concluida: bool,
) -> int:
    if temporada_concluida:
        return 99

    sequencia = _gerar_meses_principais(total_rodadas)
    if not sequencia:
        return 99

    indice = max(0, min(int(rodada_atual) - 1, len(sequencia) - 1))
    return sequencia[indice]


def _gerar_meses_principais(total_rodadas: int) -> list[int]:
    total = max(int(total_rodadas), 1)
    meses = list(range(1, min(total, 10) + 1))
    while len(meses) < total:
        for mes in range(3, 11):
            meses.append(mes)
            if len(meses) >= total:
                break
    return meses


def _nome_mes(mes: int) -> str:
    nomes = {
        1: "Janeiro",
        2: "Fevereiro",
        3: "Marco",
        4: "Abril",
        5: "Maio",
        6: "Junho",
        7: "Julho",
        8: "Agosto",
        9: "Setembro",
        10: "Outubro",
        11: "Novembro",
        12: "Dezembro",
    }
    return nomes.get(int(mes), "-")


def _obter_nivel_categoria(categoria_id: str) -> int:
    categoria = next(
        (item for item in CATEGORIAS if item.get("id") == categoria_id),
        None,
    )
    if categoria:
        return int(categoria.get("nivel", 999))
    return 999
