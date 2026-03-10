"""
Sistema de categorias e calendários — Módulo 3.
Gera calendários de temporada, calcula pontuação, determina clima
e produz config de sessão para exportar ao iRacing.
"""

import random
import logging
from datetime import datetime, timedelta

from Dados.constantes import (
    CATEGORIAS_CONFIG,
    DURACAO_CLASSIFICACAO,
    CHANCE_CHUVA_BASE,
    PONTUACAO_PADRAO,
    PONTUACAO_ENDURANCE,
    BONUS_POLE,
    BONUS_VOLTA_RAPIDA,
    BONUS_POSICAO_GERAL_MULTICLASSE,
)

logger = logging.getLogger(__name__)


# ============================================================
# CLASSIFICAÇÃO — DURAÇÃO
# ============================================================

def calcular_duracao_classificacao(comprimento_km: float) -> int:
    """
    Retorna duração da sessão de classificação em minutos
    baseada no comprimento da pista.

    Args:
        comprimento_km: Comprimento da pista em km.

    Returns:
        int: 15, 18 ou 20 minutos.
    """
    if comprimento_km >= 10:
        return 20
    elif comprimento_km >= 6:
        return 18
    else:
        return 15


def obter_duracao_classificacao(pista_nome: str) -> int:
    """
    Retorna duração da classificação para uma pista pelo nome.
    Usa DURACAO_CLASSIFICACAO; se não encontrar, retorna o default (15 min).

    Args:
        pista_nome: Nome da pista.

    Returns:
        int: Duração em minutos.
    """
    return DURACAO_CLASSIFICACAO.get(pista_nome, DURACAO_CLASSIFICACAO["_default"])


# ============================================================
# HORÁRIOS
# ============================================================

def calcular_horario_inicio_sessao(horario_corrida: str, duracao_classificacao_min: int) -> str:
    """
    Calcula o horário de início real da sessão no iRacing.

    O horario_corrida é o que exibimos ao usuário (começo da corrida).
    O horário real = horario_corrida - duracao_classificacao.

    Args:
        horario_corrida: "HH:MM" — hora de início da corrida (exibida ao user).
        duracao_classificacao_min: duração em minutos da classificação.

    Returns:
        str: "HH:MM" — horário de início da sessão (com qualificação).

    Example:
        calcular_horario_inicio_sessao("14:00", 20) → "13:40"
    """
    hora, minuto = map(int, horario_corrida.split(":"))
    dt_corrida = datetime(2024, 1, 1, hora, minuto)
    dt_inicio = dt_corrida - timedelta(minutes=duracao_classificacao_min)
    return dt_inicio.strftime("%H:%M")


# ============================================================
# CLIMA
# ============================================================

def determinar_clima_corrida(pista_nome: str) -> dict:
    """
    Determina aleatoriamente se a corrida ocorrerá com chuva.

    Args:
        pista_nome: Nome da pista.

    Returns:
        dict: {
            "chuva": bool,
            "intensidade": str | None,   # "leve", "moderada", "forte"
            "config_iracing": str,
        }
    """
    chance = CHANCE_CHUVA_BASE.get(pista_nome, CHANCE_CHUVA_BASE["_default"])

    if random.random() < chance:
        intensidade = random.choices(
            ["leve", "moderada", "forte"],
            weights=[50, 35, 15],
        )[0]
        config_map = {
            "forte":    "realistic_rain_heavy",
            "moderada": "realistic_rain_medium",
            "leve":     "realistic_rain_light",
        }
        return {
            "chuva":         True,
            "intensidade":   intensidade,
            "config_iracing": config_map[intensidade],
        }

    return {
        "chuva":         False,
        "intensidade":   None,
        "config_iracing": "realistic",
    }


def obter_config_clima_iracing(corrida: dict) -> str:
    """
    Extrai a configuração de clima para o iRacing de um dict de corrida.

    Args:
        corrida: Dict de corrida contendo chave "clima".

    Returns:
        str: Valor de config_iracing ("realistic", "realistic_rain_heavy", etc.)
    """
    return corrida.get("clima", {}).get("config_iracing", "realistic")


# ============================================================
# CALENDÁRIO
# ============================================================

def gerar_calendario_temporada(categoria_id: str, temporada_num: int) -> list:
    """
    Gera o calendário de uma temporada para uma categoria.

    - Seleciona pistas variáveis aleatoriamente.
    - Embaralha a ordem se `ordem_varia=True`.
    - Para o Endurance, cada entrada do calendário é um dict com nome_evento e duracao.

    Args:
        categoria_id: ID da categoria (ex: "mazda_rookie").
        temporada_num: Número da temporada (para seed reprodutível opcional).

    Returns:
        list[dict]: Lista de corridas com todas as informações necessárias.
    """
    config = CATEGORIAS_CONFIG.get(categoria_id)
    if not config:
        logger.error("Categoria desconhecida: %s", categoria_id)
        return []

    calendario = config.get("calendario", {})
    pistas_fixas_raw = calendario.get("pistas_fixas", [])
    pistas_variaveis_raw = calendario.get("pistas_variaveis", [])
    num_variaveis = calendario.get("num_variaveis", 0)
    num_corridas = calendario.get("num_corridas", config.get("num_corridas", 5))
    duracao_padrao = calendario.get("duracao_corrida_minutos",
                                    config.get("duracao_corrida_minutos", 30))
    ordem_varia = calendario.get("ordem_varia", False)

    # Converter pistas fixas para lista de dicts normalizados
    pistas = []
    for p in pistas_fixas_raw:
        if isinstance(p, dict):
            pistas.append(p)
        else:
            pistas.append({"nome": p, "duracao_corrida": duracao_padrao, "nome_evento": None})

    # Selecionar e adicionar variáveis
    if num_variaveis > 0 and pistas_variaveis_raw:
        n = min(num_variaveis, len(pistas_variaveis_raw))
        variaveis = random.sample(pistas_variaveis_raw, n)
        for v in variaveis:
            pistas.append({"nome": v, "duracao_corrida": duracao_padrao, "nome_evento": None})

    # Limitar ao número de corridas
    pistas = pistas[:num_corridas]

    # Embaralhar se necessário
    if ordem_varia:
        random.shuffle(pistas)

    # Montar corridas
    corridas = []
    horario_base = "14:00"

    for i, pista_info in enumerate(pistas, 1):
        nome_pista = pista_info["nome"]
        duracao_corrida = pista_info.get("duracao_corrida") or duracao_padrao
        nome_evento = pista_info.get("nome_evento") or f"Rodada {i}"

        dur_classif = obter_duracao_classificacao(nome_pista)
        clima = determinar_clima_corrida(nome_pista)
        horario_sessao = calcular_horario_inicio_sessao(horario_base, dur_classif)

        corrida = {
            "rodada":                         i,
            "nome_evento":                    nome_evento,
            "pista":                          nome_pista,
            "pista_id":                       None,
            "duracao_corrida_minutos":        duracao_corrida,
            "duracao_classificacao_minutos":  dur_classif,
            "horario_corrida":                horario_base,
            "horario_sessao_iracing":         horario_sessao,
            "clima":                          clima,
            "status":                         "pendente",
            "resultados":                     None,
            "resultados_por_classe":          None,
        }
        corridas.append(corrida)

    return corridas


# ============================================================
# PONTUAÇÃO
# ============================================================

def calcular_pontos_corrida(
    posicao: int,
    categoria_id: str,
    eh_pole: bool = False,
    volta_rapida: bool = False,
    posicao_geral: int | None = None,
) -> int:
    """
    Calcula o total de pontos de uma corrida para uma posição.

    Args:
        posicao: Posição final na classe (ou geral em mono-classe).
        categoria_id: ID da categoria.
        eh_pole: Piloto conquistou a pole position?
        volta_rapida: Piloto fez a volta mais rápida?
        posicao_geral: Posição geral (apenas para multiclasse; None se N/A).

    Returns:
        int: Total de pontos ganhos.
    """
    config = CATEGORIAS_CONFIG.get(categoria_id, {})
    sistema = config.get("sistema_pontuacao", "padrao")

    tabela = PONTUACAO_ENDURANCE if sistema == "endurance" else PONTUACAO_PADRAO
    pontos = tabela.get(posicao, 0)

    if eh_pole and config.get("bonus_pole", False):
        pontos += BONUS_POLE

    if volta_rapida and posicao <= 10 and config.get("bonus_volta_rapida", False):
        pontos += BONUS_VOLTA_RAPIDA

    if posicao_geral is not None and config.get("bonus_posicao_geral", False):
        pontos += BONUS_POSICAO_GERAL_MULTICLASSE.get(posicao_geral, 0)

    return pontos


# ============================================================
# EXPORTAÇÃO iRACING
# ============================================================

def gerar_config_sessao_iracing(corrida: dict, categoria_id: str) -> dict:
    """
    Gera a configuração completa de sessão para exportar ao iRacing.

    Args:
        corrida: Dict de corrida (gerado por gerar_calendario_temporada).
        categoria_id: ID da categoria.

    Returns:
        dict: Configuração de sessão para o JSON do iRacing.
    """
    config = CATEGORIAS_CONFIG.get(categoria_id, {})

    return {
        "track_name":          corrida["pista"],
        "track_id":            corrida.get("pista_id"),
        "session_start_time":  corrida["horario_sessao_iracing"],
        "qualifying_enabled":  True,
        "qualifying_minutes":  corrida["duracao_classificacao_minutos"],
        "race_minutes":        corrida["duracao_corrida_minutos"],
        "weather_type":        corrida["clima"]["config_iracing"],
        "max_drivers":         config.get("tamanho_grid", 20),
        "multiclass":          config.get("multiclasse", False),
        "classes":             config.get("classes", []),
    }
