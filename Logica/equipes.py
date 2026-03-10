"""
Sistema completo de equipes — Módulo 2
102 equipes fixas, niveladas no início, com promoção/rebaixamento de categoria.
"""

import logging
import random

from Dados.constantes import (
    NIVEIS_CATEGORIA,
    CATEGORIAS_CONFIG,
    REGRAS_PROMOCAO,
    _EQUIPES_POR_CATEGORIA,
    # backward-compat imports
    NOMES_EQUIPES, PREFIXOS_EXTRA, SUFIXOS_EXTRA, CORES_EQUIPES,
)
from Dados.banco import obter_proximo_id

logger = logging.getLogger(__name__)


# ============================================================
# CRIAÇÃO — EQUIPES FIXAS
# ============================================================

def criar_equipe_inicial(banco, nome_info, categoria_id, ano_atual):
    """
    Cria uma equipe a partir de um dict de nome_info (da lista fixa).
    Todas as stats começam em 50 (niveladas).

    Args:
        banco: banco de dados
        nome_info: dict da lista EQUIPES_*
        categoria_id: ID da categoria
        ano_atual: ano atual

    Returns:
        dict: equipe criada
    """
    cfg = CATEGORIAS_CONFIG.get(categoria_id, {})
    nivel = cfg.get("nivel", "amador")
    cores = nome_info.get("cores", ("#FFFFFF", "#000000"))

    equipe = {
        # Identificação
        "id":               obter_proximo_id(banco, "equipe"),
        "nome":             nome_info["nome"],
        "nome_curto":       nome_info.get("nome_curto", nome_info["nome"][:12]),
        "pais_sede":        nome_info.get("pais", "🌍 Internacional"),
        "cor_primaria":     cores[0],
        "cor_secundaria":   cores[1],
        "ano_fundacao":     ano_atual,

        # Categoria
        "categoria":                categoria_id,
        "nivel":                    nivel,
        "temporadas_na_categoria":  0,

        # Marca / classe (depende da categoria)
        "marca":            nome_info.get("marca"),
        "carro_classe":     nome_info.get("carro_classe"),
        "classe_endurance": nome_info.get("classe_endurance"),

        # Pilotos
        "pilotos":          [],
        "piloto_numero_1":  None,
        "piloto_numero_2":  None,
        # backward compat
        "piloto_1":         None,
        "piloto_2":         None,

        # Performance (começa nivelado)
        "car_performance":  50,
        "stats": {
            "chassi":        50,
            "motor":         50,
            "aerodinamica":  50,
            "confiabilidade": 50,
        },

        # Infraestrutura
        "budget":               50,
        "orcamento":            50,   # backward compat alias
        "facilities":           50,
        "engineering_quality":  50,
        "development_rate":     1.0,

        # Atributos iRacing
        "pit_crew":       50,
        "pitcrew_skill":  50,   # backward compat alias
        "strategy_risk":  50,
        "estrategia_risco": 0.5,  # backward compat alias (float)

        # Soft power
        "reputacao":  50,
        "morale":     1.0,

        # Finanças
        "salarios_totais":       0,
        "gastos_desenvolvimento": 0,
        "patrocinadores":        2,

        # Expectativa (sem definição no ano 1)
        "expectativa":          "Sem expectativa definida",
        "expectativa_posicao":  None,

        # DNF
        "chance_dnf": 0.05,

        # Stats carreira (zerável)
        "titulos_construtores":    0,
        "titulos_equipe":          0,   # backward compat alias
        "vitorias_equipe":         0,
        "podios_equipe":           0,
        "poles_equipe":            0,
        "corridas_equipe":         0,
        "pontos_historico":        0,
        "melhor_posicao_campeonato": 99,

        # Stats temporada
        "pontos_temporada":    0,
        "vitorias_temporada":  0,
        "podios_temporada":    0,
        "poles_temporada":     0,
        "corridas_temporada":  0,

        # Históricos
        "pilotos_historico":   [],
        "historico_temporadas": [],
        "historico":           [],   # backward compat alias

        # Performance geral (backward compat alias)
        "performance": 50.0,

        # Extensão
        "atributos_extras": {},

        # Outros campos backward compat
        "tier": _nivel_para_tier(nivel),
        "budget_multiplier": 1.0,
    }

    return equipe


def criar_todas_equipes(banco, ano_atual):
    """
    Cria as 102 equipes fixas e as adiciona ao banco.

    Args:
        banco: banco de dados (modifica in-place)
        ano_atual: ano atual do jogo

    Returns:
        list: todas as equipes criadas
    """
    if "equipes" not in banco:
        banco["equipes"] = []

    criadas = []
    for categoria_id, lista in _EQUIPES_POR_CATEGORIA.items():
        for nome_info in lista:
            equipe = criar_equipe_inicial(banco, nome_info, categoria_id, ano_atual)
            banco["equipes"].append(equipe)
            criadas.append(equipe)

    logger.info("Criadas %d equipes fixas.", len(criadas))
    return criadas


def _nivel_para_tier(nivel):
    """Converte nivel string para tier int (para backward compat)."""
    mapa = {
        "rookie":      4,
        "amador":      4,
        "pro":         3,
        "super_pro":   3,
        "elite":       2,
        "super_elite": 1,
    }
    return mapa.get(nivel, 3)


# ============================================================
# BUSCA E CONSULTA
# ============================================================

def obter_equipe_piloto(banco, piloto):
    """
    Obtém a equipe de um piloto.

    Args:
        banco: banco de dados
        piloto: dict do piloto ou ID

    Returns:
        dict ou None: dados da equipe
    """
    equipe_id = piloto.get("equipe_id") if isinstance(piloto, dict) else piloto
    if equipe_id:
        return next((e for e in banco.get("equipes", []) if e["id"] == equipe_id), None)
    return None


def obter_equipes_categoria(banco, categoria_id):
    """Retorna todas as equipes de uma categoria."""
    return [e for e in banco.get("equipes", []) if e.get("categoria") == categoria_id]


def obter_classificacao_equipes(banco, categoria_id):
    """Retorna equipes ordenadas por pontos na temporada."""
    equipes = obter_equipes_categoria(banco, categoria_id)
    return sorted(equipes, key=lambda e: (
        -e.get("pontos_temporada", 0),
        -e.get("vitorias_temporada", 0),
    ))


# ============================================================
# EXPECTATIVA
# ============================================================

def calcular_expectativa_equipe(equipe, ano_simulacao):
    """
    Define a expectativa da equipe para a temporada.

    No primeiro ano (temporadas_na_categoria == 0): sem expectativa.
    A partir do ano 2: baseada na posição do campeonato anterior.

    Args:
        equipe: dados da equipe
        ano_simulacao: ano atual (para referência)

    Returns:
        tuple[str, int|None]: (texto, posicao_alvo)
    """
    temporadas = equipe.get("temporadas_na_categoria", 0)
    if temporadas == 0:
        return "Sem expectativa definida", None

    hist = equipe.get("historico_temporadas", [])
    if not hist:
        return "Estabelecer presença na categoria", None

    ultima_pos = hist[-1].get("posicao_campeonato", 99)

    if ultima_pos == 1:
        return "Defender o campeonato", 1
    elif ultima_pos <= 3:
        return "Lutar pelo título", max(1, ultima_pos - 1)
    elif ultima_pos <= 6:
        return "Entrar no pódio do campeonato", max(1, ultima_pos - 2)
    elif ultima_pos <= 10:
        return "Top 5 no campeonato", max(1, ultima_pos - 2)
    else:
        return "Pontuar regularmente", ultima_pos - 3


# ============================================================
# PROMOÇÃO E REBAIXAMENTO
# ============================================================

def promover_equipe(equipe, nova_categoria):
    """
    Promove uma equipe para uma categoria superior.

    Args:
        equipe: dados da equipe
        nova_categoria: ID da nova categoria
    """
    cat_anterior = equipe.get("categoria", "")
    cfg = CATEGORIAS_CONFIG.get(nova_categoria, {})
    novo_nivel = cfg.get("nivel", equipe.get("nivel", "amador"))

    equipe["categoria"] = nova_categoria
    equipe["nivel"] = novo_nivel
    equipe["tier"] = _nivel_para_tier(novo_nivel)
    equipe["temporadas_na_categoria"] = 0
    equipe["expectativa"] = "Sem expectativa definida"
    equipe["expectativa_posicao"] = None

    # Bônus moral por promoção
    equipe["morale"] = min(1.3, equipe.get("morale", 1.0) + 0.1)
    equipe["reputacao"] = min(100, equipe.get("reputacao", 50) + 5)

    logger.info("PROMOÇÃO: %s — %s → %s", equipe.get("nome", "???"), cat_anterior, nova_categoria)


def rebaixar_equipe(equipe, nova_categoria):
    """
    Rebaixa uma equipe para uma categoria inferior.

    Args:
        equipe: dados da equipe
        nova_categoria: ID da nova categoria
    """
    cat_anterior = equipe.get("categoria", "")
    cfg = CATEGORIAS_CONFIG.get(nova_categoria, {})
    novo_nivel = cfg.get("nivel", equipe.get("nivel", "amador"))

    equipe["categoria"] = nova_categoria
    equipe["nivel"] = novo_nivel
    equipe["tier"] = _nivel_para_tier(novo_nivel)
    equipe["temporadas_na_categoria"] = 0
    equipe["expectativa"] = "Sem expectativa definida"
    equipe["expectativa_posicao"] = None

    # Penalidade moral por rebaixamento
    equipe["morale"] = max(0.7, equipe.get("morale", 1.0) - 0.15)
    equipe["reputacao"] = max(0, equipe.get("reputacao", 50) - 8)

    logger.info("REBAIXAMENTO: %s — %s → %s", equipe.get("nome", "???"), cat_anterior, nova_categoria)


def processar_promocao_rebaixamento(banco, categoria_id, ano_atual):
    """
    Processa promoções e rebaixamentos de equipes de uma categoria.

    Usa REGRAS_PROMOCAO para determinar quantas equipes sobem/descem.

    Args:
        banco: banco de dados
        categoria_id: ID da categoria a processar
        ano_atual: ano atual

    Returns:
        dict: {"promovidas": [...], "rebaixadas": [...]}
    """
    regras = REGRAS_PROMOCAO.get(categoria_id)
    if not regras:
        return {"promovidas": [], "rebaixadas": []}

    classificacao = obter_classificacao_equipes(banco, categoria_id)
    resultado = {"promovidas": [], "rebaixadas": []}
    if not classificacao:
        return resultado

    # Tenta usar o fluxo simples do Modulo 8; fallback para regras locais se indisponivel.
    promovidas = []
    rebaixadas = []
    try:
        from Logica.promocao import processar_promocoes_simples

        resultados = {}
        for posicao, equipe in enumerate(classificacao, start=1):
            resultados[str(equipe.get("id", ""))] = {
                "posicao": posicao,
                "pontos": int(equipe.get("pontos_temporada", 0)),
                "total": len(classificacao),
            }

        promovidas, rebaixadas = processar_promocoes_simples(
            equipes=classificacao,
            resultados=resultados,
            temporada=ano_atual,
            categoria_id=categoria_id,
        )
    except Exception:
        # Backward compat: aceita "sobem" e "ssobem".
        n_sobem = int(regras.get("sobem", regras.get("ssobem", 0)) or 0)
        n_descem = int(regras.get("descem", 0) or 0)
        promovidas = classificacao[:n_sobem] if n_sobem > 0 else []
        rebaixadas = classificacao[-n_descem:] if n_descem > 0 else []

    destino_subida = regras.get("destino_subida")
    if destino_subida:
        for equipe in promovidas:
            promover_equipe(equipe, destino_subida)
            salvar_historico_temporada(
                equipe,
                ano_atual,
                posicao_campeonato=classificacao.index(equipe) + 1,
                titulo=False,
            )
            resultado["promovidas"].append(equipe)

    # Backward compat: aceita destino_descida e origem_descida.
    destino_descida = regras.get("destino_descida", regras.get("origem_descida"))
    if destino_descida:
        for equipe in rebaixadas:
            if isinstance(destino_descida, dict):
                classe = equipe.get("classe_endurance") or equipe.get("carro_classe")
                nova_cat = destino_descida.get(classe) if classe else None
            else:
                nova_cat = destino_descida

            if not nova_cat:
                continue

            rebaixar_equipe(equipe, nova_cat)
            salvar_historico_temporada(
                equipe,
                ano_atual,
                posicao_campeonato=classificacao.index(equipe) + 1,
                titulo=False,
            )
            resultado["rebaixadas"].append(equipe)

    return resultado


# ============================================================
# PILOTOS — ASSOCIAÇÃO E HISTÓRICO
# ============================================================

def _adicionar_piloto_na_equipe(piloto, equipe, ano_atual=None):
    """
    Adiciona um piloto a uma equipe.
    Atualiza piloto_numero_1/2 (IDs) e mantém piloto_1/2 (nomes) por compat.
    """
    if "pilotos" not in equipe:
        equipe["pilotos"] = []

    if piloto["id"] not in equipe["pilotos"]:
        equipe["pilotos"].append(piloto["id"])

    # Slot IDs (novo schema)
    if equipe.get("piloto_numero_1") is None:
        equipe["piloto_numero_1"] = piloto["id"]
        equipe["piloto_1"] = piloto["nome"]     # backward compat
    elif equipe.get("piloto_numero_2") is None:
        equipe["piloto_numero_2"] = piloto["id"]
        equipe["piloto_2"] = piloto["nome"]     # backward compat

    piloto["equipe_id"] = equipe["id"]
    piloto["equipe_nome"] = equipe["nome"]

    if ano_atual:
        adicionar_piloto_historico(equipe, piloto, ano_atual)


def _remover_piloto_da_equipe(piloto, equipe, ano_atual=None):
    """Remove um piloto de uma equipe."""
    pid = piloto["id"]
    pnome = piloto["nome"]

    #  Limpar slots IDs (novo schema)
    if equipe.get("piloto_numero_1") == pid:
        equipe["piloto_numero_1"] = None
        equipe["piloto_1"] = None
    elif equipe.get("piloto_numero_2") == pid:
        equipe["piloto_numero_2"] = None
        equipe["piloto_2"] = None

    # Backward compat (nome)
    if equipe.get("piloto_1") == pnome:
        equipe["piloto_1"] = None
    if equipe.get("piloto_2") == pnome:
        equipe["piloto_2"] = None

    if pid in equipe.get("pilotos", []):
        equipe["pilotos"].remove(pid)

    piloto["equipe_id"] = None
    piloto["equipe_nome"] = None

    # Resetar relacionamento com o companheiro ao sair da equipe
    piloto["relacao_companheiro"] = 0

    if ano_atual:
        fechar_historico_piloto(equipe, pid, ano_atual)


def adicionar_piloto_historico(equipe, piloto, ano_atual):
    """
    Registra entrada de um piloto no histórico da equipe.

    Args:
        equipe: dados da equipe
        piloto: dict do piloto
        ano_atual: ano de início
    """
    if "pilotos_historico" not in equipe:
        equipe["pilotos_historico"] = []

    # Evitar duplicatas (mesmo piloto com ano_fim=None já existe)
    for entrada in equipe["pilotos_historico"]:
        if entrada.get("piloto_id") == piloto["id"] and entrada.get("ano_fim") is None:
            return

    equipe["pilotos_historico"].append({
        "piloto_id":    piloto["id"],
        "piloto_nome":  piloto.get("nome", ""),
        "ano_inicio":   ano_atual,
        "ano_fim":      None,
        "vitorias":     0,
        "titulos":      0,
    })


def fechar_historico_piloto(equipe, piloto_id, ano_atual):
    """
    Preenche ano_fim na entrada do histórico de um piloto.

    Args:
        equipe: dados da equipe
        piloto_id: ID do piloto que saiu
        ano_atual: ano atual
    """
    for entrada in equipe.get("pilotos_historico", []):
        if entrada.get("piloto_id") == piloto_id and entrada.get("ano_fim") is None:
            entrada["ano_fim"] = ano_atual
            return


def definir_hierarquia_pilotos(banco, equipe):
    """
    Define piloto_numero_1 (melhor skill) vs piloto_numero_2.

    Args:
        banco: banco de dados
        equipe: dados da equipe
    """
    pilotos_ids = equipe.get("pilotos", [])
    pilotos = [
        p for p in banco.get("pilotos", [])
        if p.get("id") in pilotos_ids
    ]
    if len(pilotos) < 2:
        return

    pilotos_ord = sorted(pilotos, key=lambda p: p.get("skill", 0), reverse=True)
    equipe["piloto_numero_1"] = pilotos_ord[0]["id"]
    equipe["piloto_numero_2"] = pilotos_ord[1]["id"]
    equipe["piloto_1"] = pilotos_ord[0].get("nome")  # backward compat
    equipe["piloto_2"] = pilotos_ord[1].get("nome")  # backward compat

    # Atualizar papel nos pilotos
    pilotos_ord[0]["papel"] = "numero_1"
    pilotos_ord[1]["papel"] = "numero_2"


# ============================================================
# FINANÇAS
# ============================================================

def calcular_budget_livre(equipe):
    """
    Retorna o budget disponível após salários e gastos de desenvolvimento.

    Args:
        equipe: dados da equipe

    Returns:
        int: budget livre (pode ser negativo)
    """
    budget = equipe.get("budget", equipe.get("orcamento", 50))
    salarios = equipe.get("salarios_totais", 0)
    gastos = equipe.get("gastos_desenvolvimento", 0)
    return budget - salarios - gastos


def atualizar_salarios_equipe(banco, equipe):
    """
    Recalcula salarios_totais somando salários dos pilotos vinculados.

    Args:
        banco: banco de dados
        equipe: dados da equipe
    """
    pilotos_ids = equipe.get("pilotos", [])
    total = sum(
        p.get("salario", 0)
        for p in banco.get("pilotos", [])
        if p.get("id") in pilotos_ids
    )
    equipe["salarios_totais"] = total


def atualizar_patrocinadores(equipe):
    """
    Evolui o número de patrocinadores baseado em resultados da temporada.

    Args:
        equipe: dados da equipe
    """
    patros = equipe.get("patrocinadores", 2)
    vits = equipe.get("vitorias_temporada", 0)
    pts = equipe.get("pontos_temporada", 0)

    if vits >= 3 or pts >= 100:
        patros = min(5, patros + 1)
    elif pts < 5:
        patros = max(0, patros - 1)

    equipe["patrocinadores"] = patros


# ============================================================
# HISTÓRICO DE TEMPORADAS
# ============================================================

def salvar_historico_temporada(equipe, ano_atual, posicao_campeonato, titulo):
    """
    Salva o resultado da temporada no histórico da equipe.

    Args:
        equipe: dados da equipe
        ano_atual: ano encerrado
        posicao_campeonato: posição final no campeonato
        titulo: bool — ganhou o título de construtores?
    """
    if "historico_temporadas" not in equipe:
        equipe["historico_temporadas"] = []

    registro = {
        "ano":                  ano_atual,
        "categoria":            equipe.get("categoria", ""),
        "posicao_campeonato":   posicao_campeonato,
        "pontos":               equipe.get("pontos_temporada", 0),
        "vitorias":             equipe.get("vitorias_temporada", 0),
        "titulo":               titulo,
    }
    equipe["historico_temporadas"].append(registro)

    # Atualizar melhor posição
    atual_melhor = equipe.get("melhor_posicao_campeonato", 99)
    equipe["melhor_posicao_campeonato"] = min(atual_melhor, posicao_campeonato)

    if titulo:
        equipe["titulos_construtores"] = equipe.get("titulos_construtores", 0) + 1
        equipe["titulos_equipe"] = equipe.get("titulos_equipe", 0) + 1


# ============================================================
# MIGRAÇÃO DE SCHEMA ANTIGO
# ============================================================

def migrar_equipe_schema_antigo(equipe):
    """
    Garante que uma equipe do schema antigo tenha todos os campos novos.
    Idempotente — não sobrescreve campos já existentes.

    Args:
        equipe: dict da equipe (modificado in-place)

    Returns:
        dict: equipe com campos novos preenchidos
    """
    # Migrar orcamento → budget
    if "orcamento" in equipe and "budget" not in equipe:
        equipe["budget"] = equipe["orcamento"]
    if "budget" in equipe and "orcamento" not in equipe:
        equipe["orcamento"] = equipe["budget"]

    # Migrar pitcrew_skill → pit_crew
    if "pitcrew_skill" in equipe and "pit_crew" not in equipe:
        equipe["pit_crew"] = int(equipe["pitcrew_skill"])
    if "pit_crew" in equipe and "pitcrew_skill" not in equipe:
        equipe["pitcrew_skill"] = equipe["pit_crew"]

    # Migrar estrategia_risco (float 0-1) → strategy_risk (int 0-100)
    if "estrategia_risco" in equipe and "strategy_risk" not in equipe:
        equipe["strategy_risk"] = int(equipe["estrategia_risco"] * 100)
    if "strategy_risk" in equipe and "estrategia_risco" not in equipe:
        equipe["estrategia_risco"] = equipe["strategy_risk"] / 100.0

    # Migrar tier → nivel
    if "tier" in equipe and "nivel" not in equipe:
        tier_map = {1: "super_elite", 2: "elite", 3: "pro", 4: "amador"}
        equipe["nivel"] = tier_map.get(equipe["tier"], "amador")

    # Migrar performance → car_performance
    if "performance" in equipe and "car_performance" not in equipe:
        equipe["car_performance"] = equipe["performance"]

    # Migrar piloto_1/2 (nomes) → piloto_numero_1/2 (IDs) — não tem como deduzir IDs aqui
    # Pelo menos garantir que os campos existem
    defaults = {
        "nome_curto":            equipe.get("nome", "")[:12],
        "pais_sede":             "🌍 Internacional",
        "cor_secundaria":        "#000000",
        "nivel":                 "amador",
        "temporadas_na_categoria": 0,
        "marca":                 None,
        "carro_classe":          None,
        "classe_endurance":      None,
        "piloto_numero_1":       None,
        "piloto_numero_2":       None,
        "car_performance":       equipe.get("performance", 50),
        "facilities":            50,
        "engineering_quality":   50,
        "development_rate":      1.0,
        "pit_crew":              equipe.get("pitcrew_skill", 50),
        "strategy_risk":         int(equipe.get("estrategia_risco", 0.5) * 100),
        "reputacao":             50,
        "morale":                1.0,
        "salarios_totais":       0,
        "gastos_desenvolvimento": 0,
        "patrocinadores":        2,
        "expectativa_posicao":   None,
        "titulos_construtores":  equipe.get("titulos_equipe", 0),
        "corridas_equipe":       0,
        "melhor_posicao_campeonato": 99,
        "corridas_temporada":    0,
        "pilotos_historico":     [],
        "historico_temporadas":  [],
        "atributos_extras":      {},
    }

    for campo, valor in defaults.items():
        if campo not in equipe:
            equipe[campo] = valor

    return equipe


# ============================================================
# STATS DE TEMPORADA
# ============================================================

def resetar_equipes_temporada(banco):
    """Reseta pontos/stats de temporada de TODAS as equipes."""
    for equipe in banco.get("equipes", []):
        equipe["pontos_temporada"] = 0
        equipe["vitorias_temporada"] = 0
        equipe["podios_temporada"] = 0
        equipe["poles_temporada"] = 0
        equipe["corridas_temporada"] = 0
        equipe["temporadas_na_categoria"] = equipe.get("temporadas_na_categoria", 0) + 1


def calcular_pontos_equipes(banco, categoria_id):
    """
    Calcula os pontos das equipes baseado nos pilotos.

    Args:
        banco: banco de dados
        categoria_id: ID da categoria
    """
    from Logica.pilotos import obter_pilotos_categoria

    equipes = obter_equipes_categoria(banco, categoria_id)
    pilotos = obter_pilotos_categoria(banco, categoria_id)

    for equipe in equipes:
        equipe["pontos_temporada"] = 0
        equipe["vitorias_temporada"] = 0
        equipe["podios_temporada"] = 0
        equipe["corridas_temporada"] = 0

        for piloto in pilotos:
            if piloto.get("equipe_id") == equipe["id"]:
                equipe["pontos_temporada"]   += piloto.get("pontos_temporada", 0)
                equipe["vitorias_temporada"] += piloto.get("vitorias_temporada", 0)
                equipe["podios_temporada"]   += piloto.get("podios_temporada", 0)
                equipe["corridas_temporada"] += piloto.get("corridas_temporada", 0)


# ============================================================
# ATRIBUIÇÃO DE PILOTOS
# ============================================================

def atribuir_pilotos_equipes(banco, categoria_id):
    """
    Atribui pilotos às equipes de uma categoria.
    Prioriza melhores pilotos para melhores equipes.

    Args:
        banco: banco de dados
        categoria_id: ID da categoria
    """
    from Logica.pilotos import obter_pilotos_categoria

    ano_atual = banco.get("ano_atual", 2024)
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    equipes = obter_equipes_categoria(banco, categoria_id)

    if not pilotos or not equipes:
        return

    pilotos_sem_equipe = [p for p in pilotos if not p.get("equipe_id")]
    pilotos_ordenados = sorted(pilotos_sem_equipe, key=lambda p: p.get("skill", 0), reverse=True)

    # Ordena equipes por reputação (melhor reputação fica com melhor piloto)
    equipes_ordenadas = sorted(equipes, key=lambda e: -e.get("reputacao", 50))

    piloto_idx = 0
    for equipe in equipes_ordenadas:
        pilotos_na_equipe = len([p for p in pilotos if p.get("equipe_id") == equipe["id"]])

        while pilotos_na_equipe < 2 and piloto_idx < len(pilotos_ordenados):
            piloto = pilotos_ordenados[piloto_idx]
            _adicionar_piloto_na_equipe(piloto, equipe, ano_atual)
            piloto_idx += 1
            pilotos_na_equipe += 1

    # Definir hierarquia (nº1 / nº2)
    for equipe in equipes_ordenadas:
        definir_hierarquia_pilotos(banco, equipe)


# ============================================================
# EVOLUÇÃO
# ============================================================

def evolucionar_equipes(banco):
    """
    Evolui as stats das equipes entre temporadas.

    - Evolução interna: budget, pit_crew, strategy_risk
    - Convergência competitiva: equipes fracas melhoram mais
    - Atualiza car_performance e chance_dnf
    - Calcula expectativa para o próximo ano
    """
    print("  🔧 Evoluindo equipes...")

    equipes = banco.get("equipes", [])
    if not equipes:
        return

    ano_atual = banco.get("ano_atual", 2024)

    def _soma_stats(e):
        s = e.get("stats", {})
        return s.get("chassi", 50) + s.get("motor", 50) + s.get("aerodinamica", 50)

    equipes_ord = sorted(equipes, key=_soma_stats, reverse=True)
    total = len(equipes_ord)

    for posicao, equipe in enumerate(equipes_ord):
        budget = equipe.get("budget", equipe.get("orcamento", 50))
        fator_dev = budget / 100

        # Fator de convergência (equipes fracas melhoram mais)
        fator_conv = 0.5 + (posicao / max(1, total - 1)) * 1.5
        fator_conv *= equipe.get("budget_multiplier", 1.0)

        # Evolução budget
        mudanca_orc = random.randint(-8, 8)
        if equipe.get("vitorias_temporada", 0) > 0:
            mudanca_orc += random.randint(2, 6)
        budget_novo = max(15, min(100, budget + mudanca_orc))
        equipe["budget"] = budget_novo
        equipe["orcamento"] = budget_novo

        # Evolução pit_crew
        mudanca_pit = random.uniform(-3, 5) * fator_dev
        pit = int(max(30, min(100, equipe.get("pit_crew", equipe.get("pitcrew_skill", 50)) + mudanca_pit)))
        equipe["pit_crew"] = pit
        equipe["pitcrew_skill"] = pit

        # Evolução strategy_risk
        sr = equipe.get("strategy_risk", 50) + random.randint(-5, 5)
        sr = max(10, min(95, sr))
        equipe["strategy_risk"] = sr
        equipe["estrategia_risco"] = round(sr / 100, 2)

        # Evolução stats do carro (com convergência)
        if "stats" not in equipe:
            equipe["stats"] = {"chassi": 50, "motor": 50, "aerodinamica": 50, "confiabilidade": 50}

        for stat in ["chassi", "motor", "aerodinamica", "confiabilidade"]:
            valor = equipe["stats"].get(stat, 50)
            mudanca = random.uniform(-3, 5) * fator_conv * fator_dev
            if valor > 85:
                mudanca -= random.uniform(0, 3)
            elif valor < 40:
                mudanca += random.uniform(0, 3)
            equipe["stats"][stat] = round(max(20, min(100, valor + mudanca)), 1)

        # car_performance (avg das 3 stats principais)
        s = equipe["stats"]
        perf = (s.get("chassi", 50) + s.get("motor", 50) + s.get("aerodinamica", 50)) / 3
        equipe["car_performance"] = round(perf, 1)
        equipe["performance"] = round(perf, 1)

        # chance_dnf
        confiab = s.get("confiabilidade", 50)
        equipe["chance_dnf"] = round(max(0.01, 0.15 - (confiab / 1000)), 4)

        # Expectativa para próxima temporada
        texto_exp, pos_alvo = calcular_expectativa_equipe(equipe, ano_atual)
        equipe["expectativa"] = texto_exp
        equipe["expectativa_posicao"] = pos_alvo

        # Morale decai levemente para o centro ao longo do tempo
        morale = equipe.get("morale", 1.0)
        equipe["morale"] = round(max(0.8, min(1.2, 1.0 + (morale - 1.0) * 0.9)), 3)


# ============================================================
# BACKWARD COMPAT — gerar_equipe (deprecada)
# ============================================================

def _gerar_nome_unico_equipe(nomes_usados):
    """Gera um nome de equipe único (backward compat)."""
    for _ in range(200):
        nome = f"{random.choice(PREFIXOS_EXTRA)} {random.choice(SUFIXOS_EXTRA)}"
        if nome not in nomes_usados:
            return nome
    return f"Team #{random.randint(100, 999)}"


def gerar_equipe(banco, nome, tier, categoria_id, ano_atual):
    """
    [DEPRECATED] Gera uma equipe com stats baseadas no tier.
    Use criar_equipe_inicial() para novas equipes.
    Mantida para compatibilidade com código existente.
    """
    fake_info = {
        "nome":        nome,
        "nome_curto":  nome[:12],
        "pais":        "🌍 Internacional",
        "cores":       (random.choice(CORES_EQUIPES), "#000000"),
    }
    equipe = criar_equipe_inicial(banco, fake_info, categoria_id, ano_atual)
    equipe["tier"] = tier
    equipe["nivel"] = {1: "super_elite", 2: "elite", 3: "pro", 4: "amador"}.get(tier, "amador")
    return equipe


def criar_equipes_categoria(banco, categoria_id, quantidade_equipes):
    """
    [DEPRECATED] Cria equipes para uma categoria.
    Use criar_todas_equipes() para inicializar o jogo.
    Mantida para compatibilidade.
    """
    ano_atual = banco.get("ano_atual", 2024)
    if "equipes" not in banco:
        banco["equipes"] = []

    lista_fixa = _EQUIPES_POR_CATEGORIA.get(categoria_id, [])
    nomes_ja_usados = [e["nome"] for e in banco["equipes"]]
    criadas = []

    for i in range(quantidade_equipes):
        if i < len(lista_fixa):
            info = lista_fixa[i]
            if info["nome"] not in nomes_ja_usados:
                equipe = criar_equipe_inicial(banco, info, categoria_id, ano_atual)
                banco["equipes"].append(equipe)
                criadas.append(equipe)
                nomes_ja_usados.append(info["nome"])
                continue

        # Fallback: nome gerado
        nome_g = _gerar_nome_unico_equipe(nomes_ja_usados)
        nomes_ja_usados.append(nome_g)
        fake_info = {"nome": nome_g, "nome_curto": nome_g[:12], "pais": "🌍 Internacional", "cores": (random.choice(CORES_EQUIPES), "#000000")}
        equipe = criar_equipe_inicial(banco, fake_info, categoria_id, ano_atual)
        banco["equipes"].append(equipe)
        criadas.append(equipe)

    return criadas
