"""
Gerenciamento do banco de dados (JSON).
"""

import copy
import json
import logging
import os

from Dados.constantes import ARQUIVO_BANCO, PISTAS_IRACING
from Utils.helpers import normalizar_int_positivo as _normalizar_int_positivo


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
            "simulacao_ai_concluida": False,
            "promocao_processada": False,
            "relatorio_promocao": {},
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
        if "simulacao_ai_concluida" not in fechamento:
            fechamento["simulacao_ai_concluida"] = False
            alterado = True
        if "promocao_processada" not in fechamento:
            fechamento["promocao_processada"] = False
            alterado = True
        if "relatorio_promocao" not in fechamento or not isinstance(fechamento.get("relatorio_promocao"), dict):
            fechamento["relatorio_promocao"] = {}
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
        "campeoes": [],
        "aposentados": [],
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
        "campeoes": [],
        "aposentados": [],
        "recordes": _recordes_padrao(),
        "mercado": _mercado_padrao(),
    }

    for campo, valor_padrao in campos_padrao.items():
        if campo not in banco:
            banco[campo] = copy.deepcopy(valor_padrao)
            alterado = True

    campos_lista = (
        "pilotos",
        "equipes",
        "historico_temporadas",
        "historico_temporadas_completas",
        "historico_geral",
        "campeoes",
        "aposentados",
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
