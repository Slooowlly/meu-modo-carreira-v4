from __future__ import annotations

from typing import Any

from Utils.helpers import int_seguro as _int_seguro


def _texto_seguro(valor: Any) -> str:
    return str(valor or "").strip()


def _resultado_e_dnf(resultado: Any) -> bool:
    return _texto_seguro(resultado).upper() == "DNF"


def _resultado_para_posicao(resultado: Any) -> int | None:
    if isinstance(resultado, bool):
        return None

    if isinstance(resultado, (int, float)):
        posicao = int(resultado)
        return posicao if posicao > 0 else None

    texto = _texto_seguro(resultado).upper()
    if not texto or texto == "DNF":
        return None

    try:
        posicao = int(texto)
    except (TypeError, ValueError):
        return None

    return posicao if posicao > 0 else None


def _obter_jogador(banco: dict[str, Any]) -> dict[str, Any] | None:
    for piloto in banco.get("pilotos", []):
        if isinstance(piloto, dict) and piloto.get("is_jogador"):
            return piloto
    return None


def _coletar_temporadas_jogador(
    banco: dict[str, Any],
    jogador: dict[str, Any],
) -> list[dict[str, Any]]:
    jogador_id = jogador.get("id")
    jogador_nome = _texto_seguro(jogador.get("nome")).casefold()
    temporadas: list[dict[str, Any]] = []

    for temporada in banco.get("historico_temporadas_completas", []):
        if not isinstance(temporada, dict):
            continue

        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list):
            continue

        entrada_jogador = None
        for entrada in classificacao:
            if not isinstance(entrada, dict):
                continue

            if jogador_id is not None and entrada.get("piloto_id") == jogador_id:
                entrada_jogador = entrada
                break

            nome_entrada = _texto_seguro(entrada.get("piloto")).casefold()
            if jogador_nome and nome_entrada == jogador_nome:
                entrada_jogador = entrada
                break

        if not isinstance(entrada_jogador, dict):
            continue

        resultados = entrada_jogador.get("resultados", [])
        if not isinstance(resultados, list):
            resultados = []

        temporadas.append(
            {
                "ano": _int_seguro(temporada.get("ano"), 0),
                "categoria_id": _texto_seguro(temporada.get("categoria_id")),
                "posicao": _int_seguro(entrada_jogador.get("posicao"), 999),
                "pontos": _int_seguro(entrada_jogador.get("pontos"), 0),
                "vitorias": _int_seguro(entrada_jogador.get("vitorias"), 0),
                "podios": _int_seguro(entrada_jogador.get("podios"), 0),
                "resultados": resultados,
            }
        )

    return temporadas


def _obter_posicao_atual_jogador(
    banco: dict[str, Any],
    jogador: dict[str, Any],
) -> int | None:
    categoria_atual = _texto_seguro(jogador.get("categoria_atual"))
    if not categoria_atual:
        return None

    pilotos_categoria = [
        piloto
        for piloto in banco.get("pilotos", [])
        if isinstance(piloto, dict)
        and not piloto.get("aposentado", False)
        and _texto_seguro(piloto.get("categoria_atual")) == categoria_atual
    ]
    if not pilotos_categoria:
        return None

    pilotos_ordenados = sorted(
        pilotos_categoria,
        key=lambda p: (
            -_int_seguro(p.get("pontos_temporada"), 0),
            -_int_seguro(p.get("vitorias_temporada"), 0),
            -_int_seguro(p.get("podios_temporada"), 0),
            _texto_seguro(p.get("nome")).casefold(),
        ),
    )

    jogador_id = jogador.get("id")

    for indice, piloto in enumerate(pilotos_ordenados, start=1):
        if jogador_id is not None and piloto.get("id") == jogador_id:
            return indice
        if piloto.get("is_jogador"):
            return indice

    return None


def _contar_temporadas_perfeitas(temporadas: list[dict[str, Any]]) -> int:
    total = 0
    for temporada in temporadas:
        resultados = temporada.get("resultados", [])
        if not isinstance(resultados, list) or not resultados:
            continue

        if all(_resultado_para_posicao(resultado) == 1 for resultado in resultados):
            total += 1

    return total


def _contar_temporadas_sem_dnf(temporadas: list[dict[str, Any]]) -> int:
    total = 0
    for temporada in temporadas:
        resultados = temporada.get("resultados", [])
        if not isinstance(resultados, list) or not resultados:
            continue

        if all(not _resultado_e_dnf(resultado) for resultado in resultados):
            total += 1

    return total


def _teve_recuperacao_heroica(resultados_por_temporada: list[list[Any]]) -> bool:
    for resultados in resultados_por_temporada:
        if not isinstance(resultados, list):
            continue

        for indice in range(1, len(resultados)):
            anterior = resultados[indice - 1]
            atual = resultados[indice]

            posicao_anterior = _resultado_para_posicao(anterior)
            posicao_atual = _resultado_para_posicao(atual)

            corrida_ruim = _resultado_e_dnf(anterior) or (
                posicao_anterior is not None and posicao_anterior >= 15
            )
            podio = posicao_atual is not None and posicao_atual <= 3

            if corrida_ruim and podio:
                return True

    return False


def _tem_sequencia_vitorias(
    resultados_por_temporada: list[list[Any]],
    tamanho: int = 3,
) -> bool:
    if tamanho <= 1:
        return True

    for resultados in resultados_por_temporada:
        if not isinstance(resultados, list):
            continue

        consecutivas = 0
        for resultado in resultados:
            if _resultado_para_posicao(resultado) == 1:
                consecutivas += 1
                if consecutivas >= tamanho:
                    return True
            else:
                consecutivas = 0

    return False


def _item(
    id_conquista: str,
    nome: str,
    desbloqueada: bool,
    progresso: str = "",
) -> dict[str, Any]:
    return {
        "id": id_conquista,
        "nome": nome,
        "desbloqueada": bool(desbloqueada),
        "progresso": _texto_seguro(progresso),
    }


def calcular_conquistas(banco: dict[str, Any]) -> dict[str, Any]:
    jogador = _obter_jogador(banco)
    if jogador is None:
        return {
            "desbloqueadas": 0,
            "total": 15,
            "itens": [
                _item("primeira_vitoria", "Primeira Vitória", False),
                _item("primeiro_campeonato", "Primeiro Campeonato", False),
                _item("pole_position", "Pole Position", False),
                _item("corrida_limpa", "Corrida Limpa (0 incidentes)", False),
                _item("volta_mais_rapida", "Volta Mais Rápida", False),
                _item("dez_vitorias", "10 Vitórias", False),
                _item("campeao_3_categorias", "Campeão em 3 categorias", False),
                _item("temporada_perfeita", "Temporada Perfeita (só vitórias)", False),
                _item(
                    "recuperacao_heroica",
                    "Recuperação Heroica (último -> pódio)",
                    False,
                ),
                _item("cinco_podios", "5 Pódios", False),
                _item("cem_pontos", "100 Pontos na Carreira", False),
                _item("vinte_cinco_corridas", "25 Corridas Disputadas", False),
                _item("sem_dnf_temporada", "Temporada sem DNF", False),
                _item("hat_trick_vitorias", "Hat-trick de Vitórias", False),
                _item("top5_campeonato", "Top 5 no Campeonato", False),
            ],
        }

    vitorias_carreira = _int_seguro(jogador.get("vitorias_carreira"), 0)
    podios_carreira = _int_seguro(jogador.get("podios_carreira"), 0)
    poles_carreira = _int_seguro(jogador.get("poles_carreira"), 0)
    corridas_carreira = _int_seguro(jogador.get("corridas_carreira"), 0)
    pontos_carreira = _int_seguro(jogador.get("pontos_carreira"), 0)
    dnfs_carreira = _int_seguro(jogador.get("dnfs_carreira"), 0)
    incidentes_carreira = _int_seguro(jogador.get("incidentes_carreira"), 0)

    corridas_temporada = _int_seguro(jogador.get("corridas_temporada"), 0)
    dnfs_temporada = _int_seguro(jogador.get("dnfs_temporada"), 0)
    incidentes_temporada = _int_seguro(jogador.get("incidentes_temporada"), 0)

    voltas_rapidas_carreira = _int_seguro(
        jogador.get("voltas_rapidas_carreira", poles_carreira),
        poles_carreira,
    )
    corridas_limpas_registradas = _int_seguro(jogador.get("corridas_limpas"), 0)

    historico_jogador = jogador.get("historico_temporadas", [])
    if not isinstance(historico_jogador, list):
        historico_jogador = []

    temporadas_completas_jogador = _coletar_temporadas_jogador(banco, jogador)

    resultados_por_temporada: list[list[Any]] = [
        temporada.get("resultados", [])
        for temporada in temporadas_completas_jogador
        if isinstance(temporada.get("resultados", []), list)
        and temporada.get("resultados")
    ]
    resultados_atuais = jogador.get("resultados_temporada", [])
    if isinstance(resultados_atuais, list) and resultados_atuais:
        resultados_por_temporada.append(resultados_atuais)

    categorias_campeao: set[str] = set()
    titulos_chaves: set[tuple[int, str]] = set()
    top5_historico = False
    temporada_sem_dnf_historico = False

    for temporada in historico_jogador:
        if not isinstance(temporada, dict):
            continue

        ano = _int_seguro(temporada.get("ano"), 0)
        categoria = _texto_seguro(temporada.get("categoria"))
        posicao = _int_seguro(temporada.get("posicao_final"), 999)

        if posicao == 1 and categoria:
            categorias_campeao.add(categoria)
            titulos_chaves.add((ano, categoria))

        if posicao <= 5:
            top5_historico = True

        atividade = (
            _int_seguro(temporada.get("pontos"), 0)
            + _int_seguro(temporada.get("vitorias"), 0)
            + _int_seguro(temporada.get("podios"), 0)
        )
        dnfs = _int_seguro(temporada.get("dnfs"), 0)
        if atividade > 0 and dnfs == 0:
            temporada_sem_dnf_historico = True

    for temporada in temporadas_completas_jogador:
        ano = _int_seguro(temporada.get("ano"), 0)
        categoria = _texto_seguro(temporada.get("categoria_id"))
        posicao = _int_seguro(temporada.get("posicao"), 999)

        if posicao == 1 and categoria:
            categorias_campeao.add(categoria)
            titulos_chaves.add((ano, categoria))

        if posicao <= 5:
            top5_historico = True

    campeonatos_total = len(titulos_chaves)
    categorias_campeao_total = len(categorias_campeao)

    temporadas_perfeitas = _contar_temporadas_perfeitas(temporadas_completas_jogador)
    temporadas_sem_dnf = _contar_temporadas_sem_dnf(temporadas_completas_jogador)
    temporada_atual_sem_dnf = bool(
        isinstance(resultados_atuais, list)
        and resultados_atuais
        and all(not _resultado_e_dnf(resultado) for resultado in resultados_atuais)
    )

    posicao_atual = _obter_posicao_atual_jogador(banco, jogador)
    top5_atual = bool(isinstance(posicao_atual, int) and posicao_atual <= 5)

    corrida_limpa = bool(corridas_limpas_registradas > 0)
    if not corrida_limpa:
        corrida_limpa = bool(
            corridas_temporada > 0
            and incidentes_temporada == 0
            and dnfs_temporada == 0
        )
    if not corrida_limpa:
        corrida_limpa = bool(
            corridas_carreira > 0
            and incidentes_carreira == 0
            and dnfs_carreira == 0
        )

    recuperacao_heroica = _teve_recuperacao_heroica(resultados_por_temporada)
    hat_trick = _tem_sequencia_vitorias(resultados_por_temporada, 3)

    itens = [
        _item(
            "primeira_vitoria",
            "Primeira Vitória",
            vitorias_carreira >= 1,
            f"{min(vitorias_carreira, 1)}/1",
        ),
        _item(
            "primeiro_campeonato",
            "Primeiro Campeonato",
            campeonatos_total >= 1,
            f"{min(campeonatos_total, 1)}/1",
        ),
        _item(
            "pole_position",
            "Pole Position",
            poles_carreira >= 1,
            f"{min(poles_carreira, 1)}/1",
        ),
        _item(
            "corrida_limpa",
            "Corrida Limpa (0 incidentes)",
            corrida_limpa,
            "1/1" if corrida_limpa else "0/1",
        ),
        _item(
            "volta_mais_rapida",
            "Volta Mais Rápida",
            voltas_rapidas_carreira >= 1,
            f"{min(voltas_rapidas_carreira, 1)}/1",
        ),
        _item(
            "dez_vitorias",
            "10 Vitórias",
            vitorias_carreira >= 10,
            f"{min(vitorias_carreira, 10)}/10",
        ),
        _item(
            "campeao_3_categorias",
            "Campeão em 3 categorias",
            categorias_campeao_total >= 3,
            f"{min(categorias_campeao_total, 3)}/3",
        ),
        _item(
            "temporada_perfeita",
            "Temporada Perfeita (só vitórias)",
            temporadas_perfeitas >= 1,
            f"{min(temporadas_perfeitas, 1)}/1",
        ),
        _item(
            "recuperacao_heroica",
            "Recuperação Heroica (último -> pódio)",
            recuperacao_heroica,
            "1/1" if recuperacao_heroica else "0/1",
        ),
        _item(
            "cinco_podios",
            "5 Pódios",
            podios_carreira >= 5,
            f"{min(podios_carreira, 5)}/5",
        ),
        _item(
            "cem_pontos",
            "100 Pontos na Carreira",
            pontos_carreira >= 100,
            f"{min(pontos_carreira, 100)}/100",
        ),
        _item(
            "vinte_cinco_corridas",
            "25 Corridas Disputadas",
            corridas_carreira >= 25,
            f"{min(corridas_carreira, 25)}/25",
        ),
        _item(
            "sem_dnf_temporada",
            "Temporada sem DNF",
            temporadas_sem_dnf >= 1
            or temporada_sem_dnf_historico
            or temporada_atual_sem_dnf,
            "1/1"
            if (temporadas_sem_dnf >= 1 or temporada_sem_dnf_historico or temporada_atual_sem_dnf)
            else "0/1",
        ),
        _item(
            "hat_trick_vitorias",
            "Hat-trick de Vitórias",
            hat_trick,
            "1/1" if hat_trick else "0/1",
        ),
        _item(
            "top5_campeonato",
            "Top 5 no Campeonato",
            top5_historico or top5_atual,
            "1/1" if (top5_historico or top5_atual) else "0/1",
        ),
    ]

    desbloqueadas = sum(1 for item in itens if item.get("desbloqueada"))
    return {
        "desbloqueadas": desbloqueadas,
        "total": len(itens),
        "itens": itens,
    }
