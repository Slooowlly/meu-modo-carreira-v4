"""
Gerenciamento do banco de dados (JSON).
"""

import copy
import json
import logging
import os

from Dados.constantes import (
    ARQUIVO_BANCO,
    DIFICULDADES,
    PISTAS_IRACING,
    _EQUIPES_POR_CATEGORIA,
)
from Utils.helpers import normalizar_int_positivo as _normalizar_int_positivo
from Utils.iracing_conteudo import (
    conteudo_iracing_padrao as _conteudo_iracing_padrao,
    normalizar_conteudo_iracing as _normalizar_conteudo_iracing,
)


def _recordes_padrao():
    """Retorna a estrutura padrao de recordes."""
    return {
        "mais_titulos": {"nome": None, "valor": 0},
        "mais_vitorias": {"nome": None, "valor": 0},
        "mais_poles": {"nome": None, "valor": 0},
        "piloto_mais_velho": {"nome": None, "valor": 0},
        "piloto_mais_novo_vitoria": {"nome": None, "valor": 99},
    }

logger = logging.getLogger(__name__)


def _normalizar_bool(valor, padrao=False):
    """Converte para bool de forma segura para migracoes antigas."""
    if isinstance(valor, bool):
        return valor

    if isinstance(valor, (int, float)):
        return valor != 0

    if isinstance(valor, str):
        texto = valor.strip().casefold()
        if texto in {"1", "true", "t", "sim", "s", "yes", "y"}:
            return True
        if texto in {"0", "false", "f", "nao", "não", "n", "no"}:
            return False

    return bool(padrao)


CATEGORY_ALIASES = {
    # Legacy root categories
    "mx5": "mazda_rookie",
    "toyotagr86": "toyota_amador",
    "bmwm2cs": "bmw_m2",
    # Legacy intermediate structure
    "mazda_championship": "mazda_amador",
    "toyota_championship": "toyota_amador",
    "production_challenge": "production_challenger",
    "touring_challenger": "production_challenger",
    "touring_pro": "production_challenger",
    "gt4_challenge": "gt4",
    "gt4_pro": "gt4",
    "porsche_cup": "gt3",
    "gt3_challenger": "gt3",
    "gt3_pro": "gt3",
}

_CATEGORY_VALUE_KEYS = {
    "categoria",
    "categoria_id",
    "categoria_atual",
    "categoria_origem",
    "categoria_destino",
    "categoria_origem_id",
    "categoria_destino_id",
}

_CATEGORY_KEYED_BLOCKS = (
    "arquivo_season_por_categoria",
    "max_drivers_por_categoria",
    "volta_rapida_por_rodada",
)


def _normalizar_categoria_id(categoria_id):
    categoria = str(categoria_id or "").strip().lower()
    return CATEGORY_ALIASES.get(categoria, categoria)


def _normalizar_valores_categoria_recursivo(node):
    alterado = False

    if isinstance(node, dict):
        for chave in list(node.keys()):
            valor = node.get(chave)
            if chave in _CATEGORY_VALUE_KEYS and isinstance(valor, str):
                normalizado = _normalizar_categoria_id(valor)
                if normalizado != valor:
                    node[chave] = normalizado
                    alterado = True
                    valor = normalizado

            if _normalizar_valores_categoria_recursivo(valor):
                alterado = True

        return alterado

    if isinstance(node, list):
        for item in node:
            if _normalizar_valores_categoria_recursivo(item):
                alterado = True
        return alterado

    return False


def _normalizar_dict_chaves_categoria(valor_dict):
    if not isinstance(valor_dict, dict):
        return {}, True

    alterado = False
    normalizado = {}
    for chave, valor in valor_dict.items():
        chave_normalizada = _normalizar_categoria_id(chave)
        if chave_normalizada != chave:
            alterado = True

        if chave_normalizada in normalizado:
            atual = normalizado[chave_normalizada]
            if isinstance(atual, dict) and isinstance(valor, dict):
                combinado = dict(valor)
                combinado.update(atual)
                if combinado != atual:
                    normalizado[chave_normalizada] = combinado
                    alterado = True
            else:
                alterado = True
            continue

        normalizado[chave_normalizada] = valor

    return normalizado, alterado


def _normalizar_ids_categoria_banco(banco):
    """Normaliza ids legados de categorias para o schema expandido."""
    alterado = False

    for chave_bloco in _CATEGORY_KEYED_BLOCKS:
        bloco_normalizado, bloco_alterado = _normalizar_dict_chaves_categoria(banco.get(chave_bloco))
        if banco.get(chave_bloco) != bloco_normalizado:
            banco[chave_bloco] = bloco_normalizado
            alterado = True
        elif bloco_alterado:
            alterado = True

    if isinstance(banco.get("categoria_atual"), str):
        categoria_atual = banco.get("categoria_atual")
        categoria_normalizada = _normalizar_categoria_id(categoria_atual)
        if categoria_atual != categoria_normalizada:
            banco["categoria_atual"] = categoria_normalizada
            alterado = True

    chaves_recursivas = (
        "pilotos",
        "equipes",
        "historico_temporadas",
        "historico_temporadas_completas",
        "historico_geral",
        "campeoes",
        "series_especiais",
        "mercado",
    )
    for chave in chaves_recursivas:
        if _normalizar_valores_categoria_recursivo(banco.get(chave)):
            alterado = True

    return alterado


def _migrar_schema_pilotos(banco):
    """
    Aplica migração defensiva do schema de pilotos para bancos legados.
    """
    pilotos_raw = banco.get("pilotos")
    if not isinstance(pilotos_raw, list):
        return False

    alterado = False
    pilotos = []
    for entrada in pilotos_raw:
        if isinstance(entrada, dict):
            pilotos.append(entrada)
            continue
        alterado = True

    if len(pilotos) != len(pilotos_raw):
        banco["pilotos"] = pilotos

    try:
        from Logica.pilotos import (
            migrar_piloto_schema_antigo,
            preencher_campos_obrigatorios_piloto,
            validar_schema_piloto,
        )
    except Exception as erro:
        logger.error("Falha ao importar migração de pilotos: %s", erro)
        return alterado

    ids_em_uso = set()
    proximo_id = 1

    for piloto in banco.get("pilotos", []):
        snapshot = copy.deepcopy(piloto)

        piloto_id = _normalizar_int_positivo(piloto.get("id"))
        if piloto_id is None or piloto_id in ids_em_uso:
            while proximo_id in ids_em_uso:
                proximo_id += 1
            piloto["id"] = proximo_id
            piloto_id = proximo_id
            proximo_id += 1

        ids_em_uso.add(piloto_id)

        try:
            migrar_piloto_schema_antigo(piloto)
        except Exception as erro:
            logger.warning(
                "Erro na migração automática do piloto id=%s: %s",
                piloto_id,
                erro,
            )
            preencher_campos_obrigatorios_piloto(piloto)

        validacao = validar_schema_piloto(piloto)
        if not validacao["valido"]:
            logger.warning(
                "Piloto id=%s ainda com schema inválido após migração. faltantes=%s nulos=%s",
                piloto_id,
                validacao.get("campos_faltantes", []),
                validacao.get("campos_nulos", []),
            )

        if piloto != snapshot:
            alterado = True

    return alterado


def _migrar_potencial_por_atributos(banco, margem=5.0):
    """
    Ajusta potencial de pilotos ativos para evitar clamp artificial de atributos.

    Regra: quando algum atributo de performance excede potencial, eleva potencial
    para max_atributo + margem (cap em 100), preservando o estado atual do piloto.
    """
    pilotos = banco.get("pilotos")
    if not isinstance(pilotos, list):
        return False

    atributos_skill = (
        "skill",
        "consistencia",
        "racecraft",
        "ritmo_classificacao",
        "gestao_pneus",
        "habilidade_largada",
        "resistencia_mental",
        "fitness",
        "fator_chuva",
        "fator_clutch",
    )

    alterado = False
    ajustados = 0

    def _to_float(valor, padrao=0.0):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return float(padrao)

    margem_real = max(0.0, float(margem))
    for piloto in pilotos:
        if not isinstance(piloto, dict):
            continue
        if bool(piloto.get("aposentado", False)):
            continue
        status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
        if status == "aposentado":
            continue

        potencial_atual = _to_float(
            piloto.get("potencial", piloto.get("potencial_base", 50.0)),
            50.0,
        )
        max_attr = max(_to_float(piloto.get(atributo, 0.0), 0.0) for atributo in atributos_skill)

        if max_attr <= potencial_atual:
            continue

        novo_potencial = min(100.0, max_attr + margem_real)
        novo_potencial_int = int(round(novo_potencial))
        if int(round(potencial_atual)) != novo_potencial_int:
            piloto["potencial"] = novo_potencial_int
            alterado = True

        bonus = max(0.0, _to_float(piloto.get("potencial_bonus", 0.0), 0.0))
        base_atual = _to_float(
            piloto.get("potencial_base", piloto.get("potencial", novo_potencial_int)),
            novo_potencial_int,
        )
        base_minima = max_attr + margem_real - bonus
        nova_base = min(100.0, max(base_atual, base_minima))
        nova_base_int = int(round(nova_base))
        if int(round(base_atual)) != nova_base_int:
            piloto["potencial_base"] = nova_base_int
            alterado = True

        potencial_efetivo = int(round(min(100.0, nova_base + bonus)))
        if int(round(_to_float(piloto.get("potencial", 0.0), 0.0))) != potencial_efetivo:
            piloto["potencial"] = potencial_efetivo
            alterado = True

        ajustados += 1

    if ajustados > 0:
        logger.info("Migracao de potencial aplicada em %d pilotos.", ajustados)

    return alterado


def _normalizar_marca_trilha_pro(valor):
    """Normaliza identificador de marca da trilha PRO."""
    marca = str(valor or "").strip().lower()
    if marca == "bmw_m2":
        return "bmw"
    if marca in {"mazda", "toyota", "bmw"}:
        return marca
    return ""


def _piloto_ativo_para_grid(piloto):
    """Retorna True quando o piloto conta para grid ativo da categoria."""
    if not isinstance(piloto, dict):
        return False
    if bool(piloto.get("aposentado", False)):
        return False
    status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
    return status not in {"aposentado", "reserva_global", "livre", "reserva"}


def _ordenar_equipes_para_inativacao(equipes_categoria, nomes_canonicos):
    """Ordena equipes priorizando inativar vagas vazias e nomes nao canonicos."""
    nomes = set(nomes_canonicos or set())

    def _chave(equipe):
        pilotos_ids = equipe.get("pilotos", [])
        if not isinstance(pilotos_ids, list):
            pilotos_ids = []
        tem_pilotos = 1 if len(pilotos_ids) > 0 else 0
        nome = str(equipe.get("nome", "") or "")
        eh_canonica = 1 if nome in nomes else 0
        equipe_id = _normalizar_int_positivo(equipe.get("id")) or 0
        # 1) sem pilotos primeiro, 2) nao canonica primeiro, 3) IDs maiores primeiro.
        return (tem_pilotos, eh_canonica, -equipe_id)

    return sorted(equipes_categoria, key=_chave)


def _migrar_pool_equipes_canonico(banco):
    """
    Migra pool de equipes para o desenho canonico (102 equipes ativas).

    Regras:
    - adiciona equipes faltantes por categoria;
    - marca excedentes como inativas (sem apagar historico);
    - recompõe alocacao de pilotos ativos para manter 2 pilotos por equipe ativa.
    """
    if not isinstance(banco.get("equipes"), list):
        return False
    if not isinstance(banco.get("pilotos"), list):
        return False
    if not banco.get("equipes") and not banco.get("pilotos"):
        return False

    alterado = False

    try:
        from Logica.equipes import criar_equipe_inicial, migrar_equipe_schema_antigo
        from Logica.pilotos import criar_piloto, preencher_campos_obrigatorios_piloto
    except Exception as erro:
        logger.error("Falha ao importar migradores de equipes/pilotos: %s", erro)
        return False

    equipes_somente_dict = []
    for equipe in banco.get("equipes", []):
        if isinstance(equipe, dict):
            equipes_somente_dict.append(equipe)
        else:
            alterado = True
    if len(equipes_somente_dict) != len(banco.get("equipes", [])):
        banco["equipes"] = equipes_somente_dict

    for equipe in banco.get("equipes", []):
        snapshot = copy.deepcopy(equipe)
        migrar_equipe_schema_antigo(equipe)
        equipe["ativa"] = bool(equipe.get("ativa", True))
        categoria = str(equipe.get("categoria", "") or "").strip().lower()

        marca_pro = _normalizar_marca_trilha_pro(
            equipe.get("pro_trilha_marca")
            or equipe.get("carro_classe")
        )
        if categoria == "production_challenger":
            if marca_pro:
                equipe["pro_trilha_marca"] = marca_pro
                equipe["carro_classe"] = "bmw_m2" if marca_pro == "bmw" else marca_pro
            else:
                equipe["pro_trilha_marca"] = None
        else:
            equipe.setdefault("pro_trilha_marca", None)

        if categoria != "endurance":
            equipe.setdefault("classe_endurance", None)

        if equipe != snapshot:
            alterado = True

    categorias_alvo = list(_EQUIPES_POR_CATEGORIA.keys())
    infos_por_categoria = {
        categoria: list(_EQUIPES_POR_CATEGORIA.get(categoria, []))
        for categoria in categorias_alvo
    }
    nomes_canonicos_por_categoria = {
        categoria: {str(info.get("nome", "") or "") for info in infos}
        for categoria, infos in infos_por_categoria.items()
    }

    # Equipes em categorias fora do design atual ficam inativas para preservar save.
    for equipe in banco.get("equipes", []):
        categoria = str(equipe.get("categoria", "") or "").strip().lower()
        if categoria and categoria not in categorias_alvo and equipe.get("ativa", True):
            equipe["ativa"] = False
            alterado = True

    ano_atual = _normalizar_int_positivo(banco.get("ano_atual")) or 2024

    # Ajuste de contagem por categoria (adicionar faltantes / inativar excedentes).
    for categoria_id in categorias_alvo:
        alvo = len(infos_por_categoria.get(categoria_id, []))
        equipes_categoria = [
            equipe
            for equipe in banco.get("equipes", [])
            if str(equipe.get("categoria", "")).strip().lower() == categoria_id
        ]
        ativas = [equipe for equipe in equipes_categoria if bool(equipe.get("ativa", True))]

        if len(ativas) > alvo:
            excedentes = len(ativas) - alvo
            ordenadas = _ordenar_equipes_para_inativacao(
                ativas,
                nomes_canonicos_por_categoria.get(categoria_id, set()),
            )
            for equipe in ordenadas[:excedentes]:
                if equipe.get("ativa", True):
                    equipe["ativa"] = False
                    alterado = True

        equipes_categoria = [
            equipe
            for equipe in banco.get("equipes", [])
            if str(equipe.get("categoria", "")).strip().lower() == categoria_id
        ]
        ativas = [equipe for equipe in equipes_categoria if bool(equipe.get("ativa", True))]

        faltantes = alvo - len(ativas)
        if faltantes > 0:
            nomes_existentes = {
                str(equipe.get("nome", "") or "")
                for equipe in equipes_categoria
            }
            infos_candidatas = list(infos_por_categoria.get(categoria_id, []))
            infos_ordenadas = sorted(
                infos_candidatas,
                key=lambda info: (
                    0 if str(info.get("nome", "") or "") not in nomes_existentes else 1,
                    str(info.get("nome", "") or "").casefold(),
                ),
            )
            for idx in range(faltantes):
                info_base = infos_ordenadas[idx % len(infos_ordenadas)] if infos_ordenadas else {
                    "nome": f"{categoria_id}_team_{idx + 1}",
                    "nome_curto": f"{categoria_id[:8]}_{idx + 1}",
                    "pais": "🌍 Internacional",
                    "cores": ("#FFFFFF", "#000000"),
                }
                info_nova = dict(info_base)
                nome_base = str(info_nova.get("nome", f"{categoria_id}_team") or f"{categoria_id}_team").strip()
                nome_final = nome_base
                sufixo = 2
                while nome_final in nomes_existentes:
                    nome_final = f"{nome_base} {sufixo}"
                    sufixo += 1
                info_nova["nome"] = nome_final
                if not info_nova.get("nome_curto"):
                    info_nova["nome_curto"] = nome_final[:12]

                equipe_nova = criar_equipe_inicial(
                    banco=banco,
                    nome_info=info_nova,
                    categoria_id=categoria_id,
                    ano_atual=ano_atual,
                )
                equipe_nova["ativa"] = True
                banco["equipes"].append(equipe_nova)
                nomes_existentes.add(nome_final)
                alterado = True

    pilotos_dict = [p for p in banco.get("pilotos", []) if isinstance(p, dict)]
    if len(pilotos_dict) != len(banco.get("pilotos", [])):
        banco["pilotos"] = pilotos_dict
        alterado = True

    # Rebalanceia pilotos por categoria para manter 2 por equipe ativa.
    for categoria_id in categorias_alvo:
        equipes_ativas = [
            equipe
            for equipe in banco.get("equipes", [])
            if str(equipe.get("categoria", "")).strip().lower() == categoria_id
            and bool(equipe.get("ativa", True))
        ]
        equipes_ativas = sorted(
            equipes_ativas,
            key=lambda equipe: (
                _normalizar_int_positivo(equipe.get("id")) or 0,
                str(equipe.get("nome", "")).casefold(),
            ),
        )
        capacidade = len(equipes_ativas) * 2
        if capacidade <= 0:
            continue

        pilotos_categoria = [
            piloto
            for piloto in banco.get("pilotos", [])
            if str(piloto.get("categoria_atual", "")).strip().lower() == categoria_id
            and not bool(piloto.get("aposentado", False))
        ]

        pilotos_ativos = [piloto for piloto in pilotos_categoria if _piloto_ativo_para_grid(piloto)]
        pilotos_ativos_ordenados = sorted(
            pilotos_ativos,
            key=lambda piloto: (
                0 if bool(piloto.get("is_jogador", False)) else 1,
                -float(piloto.get("skill", 0) or 0),
                _normalizar_int_positivo(piloto.get("id")) or 0,
            ),
        )

        selecionados = list(pilotos_ativos_ordenados[:capacidade])
        ids_selecionados = {
            _normalizar_int_positivo(piloto.get("id")) for piloto in selecionados
            if _normalizar_int_positivo(piloto.get("id")) is not None
        }

        for piloto in pilotos_ativos_ordenados[capacidade:]:
            piloto["status"] = "reserva"
            piloto["equipe_id"] = None
            piloto["equipe_nome"] = None
            piloto["papel"] = None
            alterado = True

        while len(selecionados) < capacidade:
            novo_piloto = criar_piloto(
                banco=banco,
                categoria_id=categoria_id,
                ano_atual=ano_atual,
            )
            preencher_campos_obrigatorios_piloto(novo_piloto)
            novo_piloto["status"] = "ativo"
            novo_piloto["categoria_atual"] = categoria_id
            novo_piloto["equipe_id"] = None
            novo_piloto["equipe_nome"] = None
            novo_piloto["papel"] = None
            banco["pilotos"].append(novo_piloto)
            selecionados.append(novo_piloto)
            piloto_id = _normalizar_int_positivo(novo_piloto.get("id"))
            if piloto_id is not None:
                ids_selecionados.add(piloto_id)
            alterado = True

        for equipe in equipes_ativas:
            equipe["pilotos"] = []
            equipe["piloto_numero_1"] = None
            equipe["piloto_numero_2"] = None
            equipe["piloto_1"] = None
            equipe["piloto_2"] = None

        equipes_inativas = [
            equipe
            for equipe in banco.get("equipes", [])
            if str(equipe.get("categoria", "")).strip().lower() == categoria_id
            and not bool(equipe.get("ativa", True))
        ]
        for equipe in equipes_inativas:
            equipe["pilotos"] = []
            equipe["piloto_numero_1"] = None
            equipe["piloto_numero_2"] = None
            equipe["piloto_1"] = None
            equipe["piloto_2"] = None

        for indice, piloto in enumerate(selecionados):
            equipe_alvo = equipes_ativas[indice // 2]
            piloto_id = _normalizar_int_positivo(piloto.get("id"))
            if piloto_id is None:
                continue

            equipe_alvo.setdefault("pilotos", [])
            equipe_alvo["pilotos"].append(piloto_id)
            piloto["categoria_atual"] = categoria_id
            piloto["status"] = "ativo"
            piloto["equipe_id"] = equipe_alvo.get("id")
            piloto["equipe_nome"] = equipe_alvo.get("nome")
            contrato_anos = _normalizar_int_positivo(piloto.get("contrato_anos")) or 0
            if contrato_anos <= 0:
                piloto["contrato_anos"] = 1
            if indice % 2 == 0:
                piloto["papel"] = "numero_1"
                equipe_alvo["piloto_numero_1"] = piloto_id
                equipe_alvo["piloto_1"] = piloto.get("nome")
            else:
                piloto["papel"] = "numero_2"
                equipe_alvo["piloto_numero_2"] = piloto_id
                equipe_alvo["piloto_2"] = piloto.get("nome")

        ids_equipes_ativas = {
            _normalizar_int_positivo(equipe.get("id"))
            for equipe in equipes_ativas
        }
        ids_equipes_ativas.discard(None)

        for piloto in pilotos_categoria:
            piloto_id = _normalizar_int_positivo(piloto.get("id"))
            if piloto_id in ids_selecionados:
                continue
            if _piloto_ativo_para_grid(piloto):
                piloto["status"] = "reserva"
            equipe_id = _normalizar_int_positivo(piloto.get("equipe_id"))
            if equipe_id in ids_equipes_ativas:
                piloto["equipe_id"] = None
                piloto["equipe_nome"] = None
            if str(piloto.get("status", "")).strip().lower() in {"reserva", "reserva_global", "livre"}:
                piloto["equipe_id"] = None
                piloto["equipe_nome"] = None
                piloto["papel"] = None

    return alterado


def _mercado_padrao():
    """Estrutura padrao de banco['mercado'] (migracao segura)."""
    return {
        "versao": 1,
        "contratos_ativos": [],
        "historico_janelas": [],
        "propostas_atuais": [],
        "vagas_abertas": [],
        "reserva_global": [],
        "rookies_gerados": [],
        "pendencias_jogador": [],
        "janela_aberta": False,
        "temporada_janela": 0,
        "resultado_janela_atual": {},
        "ultima_temporada_decrementada": 0,
        "fechamento_temporada": {
            "em_andamento": False,
            "ano_base": 0,
            "aposentados": [],
            "total_aposentadorias": 0,
            "simulacao_ai_concluida": False,
            "evolucao_processada": False,
            "promocao_processada": False,
            "relatorio_promocao": {},
            "validacao_pos_mercado": {},
        },
    }


def _normalizar_mercado(mercado_raw):
    """Normaliza a estrutura de mercado preservando compatibilidade com bancos antigos."""
    alterado = False
    padrao = _mercado_padrao()

    if not isinstance(mercado_raw, dict):
        return copy.deepcopy(padrao), True

    mercado = mercado_raw
    for chave, valor_padrao in padrao.items():
        if chave not in mercado:
            mercado[chave] = copy.deepcopy(valor_padrao)
            alterado = True

    campos_lista = (
        "contratos_ativos",
        "historico_janelas",
        "propostas_atuais",
        "vagas_abertas",
        "reserva_global",
        "rookies_gerados",
        "pendencias_jogador",
    )
    for campo in campos_lista:
        if not isinstance(mercado.get(campo), list):
            mercado[campo] = []
            alterado = True

    if not isinstance(mercado.get("resultado_janela_atual"), dict):
        mercado["resultado_janela_atual"] = {}
        alterado = True

    fechamento = mercado.get("fechamento_temporada")
    if not isinstance(fechamento, dict):
        fechamento = copy.deepcopy(padrao["fechamento_temporada"])
        mercado["fechamento_temporada"] = fechamento
        alterado = True
    else:
        if "em_andamento" not in fechamento:
            fechamento["em_andamento"] = False
            alterado = True
        if "ano_base" not in fechamento:
            fechamento["ano_base"] = 0
            alterado = True
        if "aposentados" not in fechamento or not isinstance(fechamento.get("aposentados"), list):
            fechamento["aposentados"] = []
            alterado = True
        if "total_aposentadorias" not in fechamento:
            fechamento["total_aposentadorias"] = 0
            alterado = True
        if "simulacao_ai_concluida" not in fechamento:
            fechamento["simulacao_ai_concluida"] = False
            alterado = True
        if "evolucao_processada" not in fechamento:
            fechamento["evolucao_processada"] = False
            alterado = True
        if "promocao_processada" not in fechamento:
            fechamento["promocao_processada"] = False
            alterado = True
        if "relatorio_promocao" not in fechamento or not isinstance(fechamento.get("relatorio_promocao"), dict):
            fechamento["relatorio_promocao"] = {}
            alterado = True
        if "validacao_pos_mercado" not in fechamento or not isinstance(fechamento.get("validacao_pos_mercado"), dict):
            fechamento["validacao_pos_mercado"] = {}
            alterado = True
        novo_em_andamento = _normalizar_bool(fechamento.get("em_andamento"), False)
        if fechamento.get("em_andamento") != novo_em_andamento:
            fechamento["em_andamento"] = novo_em_andamento
            alterado = True
        ano_base = _normalizar_int_positivo(fechamento.get("ano_base"))
        if ano_base is None:
            ano_base = 0
        if fechamento.get("ano_base") != ano_base:
            fechamento["ano_base"] = ano_base
            alterado = True
        simulacao_ai = _normalizar_bool(fechamento.get("simulacao_ai_concluida"), False)
        if fechamento.get("simulacao_ai_concluida") != simulacao_ai:
            fechamento["simulacao_ai_concluida"] = simulacao_ai
            alterado = True
        promocao_proc = _normalizar_bool(fechamento.get("promocao_processada"), False)
        if fechamento.get("promocao_processada") != promocao_proc:
            fechamento["promocao_processada"] = promocao_proc
            alterado = True
        total_aposentadorias = _normalizar_int_positivo(fechamento.get("total_aposentadorias"))
        if total_aposentadorias is None:
            total_aposentadorias = 0
        if fechamento.get("total_aposentadorias") != total_aposentadorias:
            fechamento["total_aposentadorias"] = total_aposentadorias
            alterado = True
        evolucao_proc = _normalizar_bool(fechamento.get("evolucao_processada"), False)
        if fechamento.get("evolucao_processada") != evolucao_proc:
            fechamento["evolucao_processada"] = evolucao_proc
            alterado = True

    versao = _normalizar_int_positivo(mercado.get("versao"))
    if versao is None:
        versao = 1
    if mercado.get("versao") != versao:
        mercado["versao"] = versao
        alterado = True

    janela_aberta = _normalizar_bool(mercado.get("janela_aberta"), False)
    if mercado.get("janela_aberta") != janela_aberta:
        mercado["janela_aberta"] = janela_aberta
        alterado = True

    temporada_janela = _normalizar_int_positivo(mercado.get("temporada_janela"))
    if temporada_janela is None:
        temporada_janela = 0
    if mercado.get("temporada_janela") != temporada_janela:
        mercado["temporada_janela"] = temporada_janela
        alterado = True

    ultima_decrementada = _normalizar_int_positivo(mercado.get("ultima_temporada_decrementada"))
    if ultima_decrementada is None:
        ultima_decrementada = 0
    if mercado.get("ultima_temporada_decrementada") != ultima_decrementada:
        mercado["ultima_temporada_decrementada"] = ultima_decrementada
        alterado = True

    return mercado, alterado


def _coletar_pistas_validas():
    """Monta uma lista de pistas com trackId valido."""
    pistas = []

    for pista in PISTAS_IRACING:
        if not isinstance(pista, dict):
            continue

        track_id = _normalizar_int_positivo(pista.get("trackId"))
        if track_id is None:
            continue

        nome = str(pista.get("nome", f"Track ID {track_id}") or "").strip()
        if not nome:
            nome = f"Track ID {track_id}"

        pistas.append({"trackId": track_id, "nome": nome})

    return pistas


def _nome_pista_por_track_id(track_id, pistas_validas):
    """Retorna nome de pista para um trackId."""
    for pista in pistas_validas:
        if pista["trackId"] == track_id:
            return pista["nome"]
    return f"Track ID {track_id}"


def _gerar_calendario_padrao(total_rodadas=24):
    """Gera calendario base com trackId para bancos antigos."""
    pistas_validas = _coletar_pistas_validas()
    if not pistas_validas:
        return []

    total = _normalizar_int_positivo(total_rodadas) or 24
    calendario = []

    for indice in range(total):
        pista = pistas_validas[indice % len(pistas_validas)]
        track_id = pista["trackId"]
        calendario.append(
            {
                "nome": f"Rodada {indice + 1}",
                "circuito": pista["nome"],
                "trackId": track_id,
                "voltas": 10,
                "clima": "Seco",
                "temperatura": 26,
            }
        )

    return calendario


def _normalizar_temperatura(valor, padrao=26):
    """Normaliza temperatura para int quando possivel."""
    if isinstance(valor, (int, float)):
        return int(round(valor))

    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return padrao
        if texto in {"-", "—"}:
            return texto

        texto = (
            texto.replace("°C", "")
            .replace("°c", "")
            .replace("C", "")
            .replace("c", "")
            .replace(",", ".")
            .strip()
        )
        try:
            return int(round(float(texto)))
        except (TypeError, ValueError):
            return padrao

    return padrao


def _normalizar_calendario(calendario, total_rodadas):
    """Normaliza calendario e garante trackId em todas as corridas."""
    pistas_validas = _coletar_pistas_validas()
    if not pistas_validas:
        return []

    origem = calendario if isinstance(calendario, list) else []

    total = _normalizar_int_positivo(total_rodadas)
    if total is None:
        total = len(origem) if origem else 24
    total = max(total, 1)

    if origem and total < len(origem):
        total = len(origem)

    corridas = []
    for indice in range(total):
        pista_padrao = pistas_validas[indice % len(pistas_validas)]

        corrida_raw = {}
        if indice < len(origem) and isinstance(origem[indice], dict):
            corrida_raw = origem[indice]

        track_id = _normalizar_int_positivo(corrida_raw.get("trackId"))
        if track_id is None:
            track_id = pista_padrao["trackId"]

        nome = str(corrida_raw.get("nome", "") or "").strip()
        if not nome:
            nome = f"Rodada {indice + 1}"

        circuito = str(corrida_raw.get("circuito", "") or "").strip()
        if not circuito:
            circuito = _nome_pista_por_track_id(track_id, pistas_validas)

        voltas = _normalizar_int_positivo(corrida_raw.get("voltas"))
        if voltas is None:
            voltas = 10

        clima = corrida_raw.get("clima", "Seco")
        clima = str(clima).strip() if clima is not None else "Seco"
        if not clima:
            clima = "Seco"

        temperatura = _normalizar_temperatura(corrida_raw.get("temperatura", 26))

        corridas.append(
            {
                "nome": nome,
                "circuito": circuito,
                "trackId": track_id,
                "voltas": voltas,
                "clima": clima,
                "temperatura": temperatura,
            }
        )

    return corridas


def criar_banco_vazio():
    """Cria a estrutura inicial do banco de dados."""
    return {
        "versao": 3,
        "temporada_atual": 1,
        "ano_atual": 2024,
        "ano_inicio_historico": 2024,
        "rodada_atual": 1,
        "total_rodadas": 24,
        "temporada_concluida": False,
        "nome_jogador": "",
        "conteudo_iracing": _conteudo_iracing_padrao(),
        "idade_aposentadoria": 42,
        "dificuldade": "Médio",
        "pilotos_por_categoria": 20,
        "calendario": _gerar_calendario_padrao(24),
        "pilotos": [],
        "equipes": [],
        "arquivo_season": "",
        "arquivo_season_por_categoria": {},
        "max_drivers_por_categoria": {},
        "volta_rapida_por_rodada": {},
        "series_especiais": {},
        "historico_temporadas": [],
        "historico_temporadas_completas": [],
        "historico_geral": [],
        "historico_avaliacoes": [],
        "historico_milestones": [],
        "campeoes": [],
        "aposentados": [],
        "noticias": [],
        "race_weekend": {},
        "ultimo_alerta_contrato": {},
        "recordes": _recordes_padrao(),
        "mercado": _mercado_padrao(),
    }


def carregar_banco():
    """Carrega o banco de dados do arquivo JSON."""
    if not os.path.exists(ARQUIVO_BANCO):
        return criar_banco_vazio()

    try:
        with open(ARQUIVO_BANCO, "r", encoding="utf-8") as arquivo:
            banco = json.load(arquivo)

        banco, alterado = _validar_campos_banco(banco)
        if alterado:
            salvar_banco(banco)

        return banco
    except json.JSONDecodeError as erro:
        logger.error("Erro ao ler JSON: %s", erro)
        return criar_banco_vazio()
    except Exception as erro:
        logger.error("Erro ao carregar banco: %s", erro)
        return criar_banco_vazio()


def salvar_banco(banco):
    """Salva o banco de dados no arquivo JSON."""
    try:
        with open(ARQUIVO_BANCO, "w", encoding="utf-8") as arquivo:
            json.dump(banco, arquivo, indent=4, ensure_ascii=False)
        return True
    except Exception as erro:
        logger.error("Erro ao salvar banco: %s", erro)
        return False


def banco_existe():
    """Verifica se o arquivo do banco existe."""
    return os.path.exists(ARQUIVO_BANCO)


def deletar_banco():
    """Deleta o arquivo do banco de dados."""
    if not os.path.exists(ARQUIVO_BANCO):
        return True

    try:
        os.remove(ARQUIVO_BANCO)
        return True
    except Exception as erro:
        logger.error("Erro ao deletar banco: %s", erro)
        return False


def _validar_campos_banco(banco):
    """Garante existencia e consistencia dos campos obrigatorios."""
    alterado = False

    campos_padrao = {
        "versao": 3,
        "temporada_atual": 1,
        "ano_atual": 2024,
        "ano_inicio_historico": 2024,
        "rodada_atual": 1,
        "total_rodadas": 24,
        "temporada_concluida": False,
        "nome_jogador": "",
        "conteudo_iracing": _conteudo_iracing_padrao(),
        "idade_aposentadoria": 42,
        "dificuldade": "Médio",
        "pilotos_por_categoria": 20,
        "calendario": [],
        "pilotos": [],
        "equipes": [],
        "arquivo_season": "",
        "arquivo_season_por_categoria": {},
        "max_drivers_por_categoria": {},
        "volta_rapida_por_rodada": {},
        "series_especiais": {},
        "historico_temporadas": [],
        "historico_temporadas_completas": [],
        "historico_geral": [],
        "historico_avaliacoes": [],
        "historico_milestones": [],
        "campeoes": [],
        "aposentados": [],
        "noticias": [],
        "race_weekend": {},
        "ultimo_alerta_contrato": {},
        "recordes": _recordes_padrao(),
        "mercado": _mercado_padrao(),
    }

    for campo, valor_padrao in campos_padrao.items():
        if campo not in banco:
            banco[campo] = copy.deepcopy(valor_padrao)
            alterado = True

    dificuldade_raw = str(banco.get("dificuldade", "Médio") or "").strip()
    aliases_dificuldade = {
        "Fácil": "Fácil",
        "Médio": "Médio",
        "Difícil": "Difícil",
        "Lendário": "Lendário",
        # Compatibilidade com valores legados salvos com mojibake.
        "F\u00c3\u00a1cil": "Fácil",
        "M\u00c3\u00a9dio": "Médio",
        "Dif\u00c3\u00adcil": "Difícil",
        "Lend\u00c3\u00a1rio": "Lendário",
    }
    dificuldade_normalizada = aliases_dificuldade.get(dificuldade_raw, dificuldade_raw)
    if dificuldade_normalizada not in DIFICULDADES:
        dificuldade_normalizada = "Médio"
    if banco.get("dificuldade") != dificuldade_normalizada:
        banco["dificuldade"] = dificuldade_normalizada
        alterado = True

    conteudo_normalizado = _normalizar_conteudo_iracing(banco.get("conteudo_iracing"))
    if banco.get("conteudo_iracing") != conteudo_normalizado:
        banco["conteudo_iracing"] = conteudo_normalizado
        alterado = True

    campos_lista = (
        "pilotos",
        "equipes",
        "historico_temporadas",
        "historico_temporadas_completas",
        "historico_geral",
        "historico_avaliacoes",
        "historico_milestones",
        "campeoes",
        "aposentados",
        "noticias",
        "calendario",
    )
    for campo in campos_lista:
        if not isinstance(banco.get(campo), list):
            banco[campo] = []
            alterado = True

    campos_dict = (
        "series_especiais",
        "arquivo_season_por_categoria",
        "max_drivers_por_categoria",
        "volta_rapida_por_rodada",
        "race_weekend",
        "ultimo_alerta_contrato",
    )
    for campo in campos_dict:
        if not isinstance(banco.get(campo), dict):
            banco[campo] = {}
            alterado = True

    if not isinstance(banco.get("arquivo_season"), str):
        banco["arquivo_season"] = str(banco.get("arquivo_season", "") or "")
        alterado = True

    total_rodadas = _normalizar_int_positivo(banco.get("total_rodadas"))
    if total_rodadas is None:
        if banco.get("calendario"):
            total_rodadas = len(banco["calendario"])
        else:
            total_rodadas = 24
    if banco.get("total_rodadas") != total_rodadas:
        banco["total_rodadas"] = total_rodadas
        alterado = True

    calendario_normalizado = _normalizar_calendario(
        banco.get("calendario"),
        banco.get("total_rodadas", 24),
    )
    if banco.get("calendario") != calendario_normalizado:
        banco["calendario"] = calendario_normalizado
        alterado = True

    total_calendario = len(calendario_normalizado)
    if total_calendario > 0 and banco.get("total_rodadas") != total_calendario:
        banco["total_rodadas"] = total_calendario
        alterado = True

    rodada_atual = _normalizar_int_positivo(banco.get("rodada_atual")) or 1
    limite_rodada = max(1, int(banco.get("total_rodadas", 1)))
    if rodada_atual > limite_rodada:
        rodada_atual = limite_rodada
    if banco.get("rodada_atual") != rodada_atual:
        banco["rodada_atual"] = rodada_atual
        alterado = True

    temporada_concluida = _normalizar_bool(
        banco.get("temporada_concluida"),
        False,
    )
    if banco.get("temporada_concluida") != temporada_concluida:
        banco["temporada_concluida"] = temporada_concluida
        alterado = True

    recordes = banco.get("recordes")
    if not isinstance(recordes, dict):
        banco["recordes"] = _recordes_padrao()
        alterado = True
    else:
        base_recordes = _recordes_padrao()
        for chave, valor_padrao in base_recordes.items():
            atual = recordes.get(chave)
            if not isinstance(atual, dict):
                recordes[chave] = copy.deepcopy(valor_padrao)
                alterado = True
                continue

            if "nome" not in atual:
                atual["nome"] = valor_padrao["nome"]
                alterado = True
            if "valor" not in atual:
                atual["valor"] = valor_padrao["valor"]
                alterado = True

    mercado_normalizado, mercado_alterado = _normalizar_mercado(banco.get("mercado"))
    if banco.get("mercado") != mercado_normalizado:
        banco["mercado"] = mercado_normalizado
        alterado = True
    elif mercado_alterado:
        alterado = True

    if _normalizar_ids_categoria_banco(banco):
        alterado = True

    if _migrar_schema_pilotos(banco):
        alterado = True

    if _migrar_potencial_por_atributos(banco):
        alterado = True

    if _migrar_pool_equipes_canonico(banco):
        alterado = True

    return banco, alterado


def obter_proximo_id(banco, tipo="piloto"):
    """Gera o proximo ID unico para piloto ou equipe."""
    if tipo == "piloto":
        lista = banco.get("pilotos", [])
    elif tipo == "equipe":
        lista = banco.get("equipes", [])
    else:
        return 1

    if not lista:
        return 1

    max_id = max((item.get("id", 0) for item in lista), default=0)
    return max_id + 1
