"""
Lógica de simulação de corridas e temporadas
Cálculo de performance, resultados, campeonatos
"""

import logging
import random
from Dados.constantes import CATEGORIAS
from Logica.equipes import obter_equipe_piloto
from Logica.pilotos import atualizar_stats_piloto, normalizar_aggression

logger = logging.getLogger(__name__)


def calcular_performance_piloto(piloto, equipe=None):
    """
    Calcula a performance de um piloto numa corrida.
    Incorpora os novos atributos do schema completo.

    Args:
        piloto: dados do piloto
        equipe: dados da equipe (opcional)

    Returns:
        float: valor de performance
    """
    skill = piloto.get("skill", 50)
    idade = piloto.get("idade", 25)

    # --- Normalizar aggression para 0.0–1.0 (suporta formato antigo float e novo int) ---
    agg_raw = piloto.get("aggression", 0.5)
    if isinstance(agg_raw, (int, float)) and agg_raw > 1.0:
        # Novo formato: int 0-100
        aggression = agg_raw / 100.0
    else:
        # Formato antigo: float 0.3-0.9
        aggression = float(agg_raw)

    # Bônus de experiência por idade
    if 25 <= idade <= 32:
        exp_bonus = random.uniform(2, 5)
    elif idade < 22:
        exp_bonus = random.uniform(-3, 0)
    elif idade > 36:
        exp_bonus = random.uniform(-2, 1)
    else:
        exp_bonus = random.uniform(0, 2)

    # Fator agressividade (lógica mantida idêntica)
    if aggression > 0.7:
        agg_factor = random.uniform(-5, 8)
    else:
        agg_factor = random.uniform(-2, 3)

    # ── Novos atributos de simulação ─────────────────────────
    # Consistência reduz variância (bônus pequeno mas estável)
    consistencia = piloto.get("consistencia", 50)
    consist_factor = (consistencia - 50) / 100.0 * random.uniform(1.0, 3.0)

    # Racecraft dá bônus em batalhas (leve ruído positivo)
    racecraft = piloto.get("racecraft", 50)
    racecraft_factor = (racecraft - 50) / 100.0 * random.uniform(0.5, 2.0)

    # Fitness afeta performance no final da corrida (aproximação: ruído reduzido)
    fitness = piloto.get("fitness", 70)
    fitness_factor = (fitness - 50) / 100.0 * random.uniform(0.5, 1.5)

    # Motivação afeta variância geral
    motivacao = piloto.get("motivacao", 70)
    motiv_factor = (motivacao - 50) / 100.0 * random.uniform(0.5, 1.5)

    # Modificador de lesão
    lesao = piloto.get("lesao")
    lesao_modifier = lesao.get("modifier", 1.0) if lesao else 1.0

    # Bônus de equipe
    equipe_bonus = 0.0
    if equipe:
        stats = equipe.get("stats", {})
        chassi = stats.get("chassi", 50) / 100
        motor = stats.get("motor", 50) / 100
        aero = stats.get("aerodinamica", 50) / 100
        confiab = stats.get("confiabilidade", 70) / 100

        equipe_media = (chassi + motor + aero) / 3
        equipe_bonus = equipe_media * random.uniform(4, 10)

        # Falha mecânica
        if random.random() > confiab:
            equipe_bonus -= random.uniform(5, 15)

    # Aleatoriedade
    aleatorio = random.uniform(-12, 12)

    performance = (
        skill
        + exp_bonus
        + agg_factor
        + consist_factor
        + racecraft_factor
        + fitness_factor
        + motiv_factor
        + equipe_bonus
        + aleatorio
    ) * lesao_modifier

    return max(0, performance)


def simular_corrida(pilotos, banco=None):
    """
    Simula uma corrida.
    
    Args:
        pilotos: lista de pilotos
        banco: banco de dados (para usar equipes)
    
    Returns:
        list: resultados ordenados por posição
    """
    resultados = []
    
    for piloto in pilotos:
        equipe = None
        if banco:
            equipe = obter_equipe_piloto(banco, piloto)
        
        performance = calcular_performance_piloto(piloto, equipe)
        
        # Chance de DNF — normaliza aggression (suporta int 0-100 e float antigo)
        agg_raw = piloto.get("aggression", 0.5)
        if isinstance(agg_raw, (int, float)) and agg_raw > 1.0:
            agg_norm = agg_raw / 100.0
        else:
            agg_norm = float(agg_raw)
        chance_dnf = agg_norm * 0.08
        
        if equipe:
            confiab = equipe.get("stats", {}).get("confiabilidade", 70) / 100
            chance_dnf += (1 - confiab) * 0.05
        
        if random.random() < chance_dnf:
            resultados.append({
                "piloto": piloto,
                "dnf": True,
                "performance": 0
            })
        else:
            resultados.append({
                "piloto": piloto,
                "dnf": False,
                "performance": performance
            })
    
    # Ordena: primeiro os que não deram DNF, depois por performance
    resultados.sort(key=lambda x: (x["dnf"], -x["performance"]))
    
    return resultados


def simular_corrida_categoria(banco, categoria_id):
    """
    Simula uma corrida para uma categoria e retorna o formato esperado pela UI.

    Returns:
        list[dict]: classificacao com piloto_id, piloto_nome, dnf e volta_rapida
    """
    from Logica.pilotos import obter_pilotos_categoria

    pilotos = obter_pilotos_categoria(banco, categoria_id)
    if not pilotos:
        return []

    resultado_bruto = simular_corrida(pilotos, banco)
    pilotos_terminaram = [item for item in resultado_bruto if not item["dnf"]]

    piloto_volta_rapida_id = None
    if pilotos_terminaram:
        piloto_volta_rapida_id = max(
            pilotos_terminaram,
            key=lambda item: item["performance"],
        )["piloto"]["id"]

    classificacao = []
    for entrada in resultado_bruto:
        piloto = entrada["piloto"]
        classificacao.append(
            {
                "piloto_id": piloto.get("id"),
                "piloto_nome": piloto.get("nome", "???"),
                "dnf": bool(entrada.get("dnf", False)),
                "volta_rapida": (
                    not bool(entrada.get("dnf", False))
                    and piloto.get("id") == piloto_volta_rapida_id
                ),
            }
        )

    return classificacao


def processar_resultado_corrida(resultado_corrida):
    """
    Processa o resultado de uma corrida e atualiza stats dos pilotos.
    
    Args:
        resultado_corrida: resultado da simulação
    
    Returns:
        dict: estatísticas da corrida
    """
    # Encontra melhor volta (piloto com maior performance)
    pilotos_terminaram = [r for r in resultado_corrida if not r["dnf"]]
    
    melhor_volta_piloto = None
    if pilotos_terminaram:
        melhor_volta_piloto = max(pilotos_terminaram, key=lambda x: x["performance"])["piloto"]
    
    stats_corrida = {
        "vencedor": None,
        "pole": melhor_volta_piloto,
        "dnfs": 0,
        "classificacao": []
    }
    
    for pos, resultado in enumerate(resultado_corrida):
        piloto = resultado["piloto"]
        posicao_1based = pos + 1
        is_dnf = resultado["dnf"]

        # Determinar volta rápida
        volta_rapida = (
            not is_dnf
            and melhor_volta_piloto is not None
            and piloto["id"] == melhor_volta_piloto["id"]
        )

        # Incidentes (simulados)
        agg_raw = piloto.get("aggression", 0.5)
        agg_norm = (agg_raw / 100.0) if isinstance(agg_raw, (int, float)) and agg_raw > 1.0 else float(agg_raw)
        if is_dnf:
            incidentes = random.randint(2, 6)
        elif random.random() < agg_norm * 0.15:
            incidentes = random.randint(1, 3)
        else:
            incidentes = 0

        # Atualizar stats usando função unificada
        pontos = atualizar_stats_piloto(
            piloto,
            posicao=posicao_1based,
            dnf=is_dnf,
            volta_rapida=volta_rapida,
            incidentes=incidentes,
        )

        if is_dnf:
            stats_corrida["dnfs"] += 1
        else:
            if posicao_1based == 1:
                stats_corrida["vencedor"] = piloto["nome"]

            stats_corrida["classificacao"].append({
                "posicao": posicao_1based,
                "piloto": piloto["nome"],
                "pontos": pontos
            })
    
    return stats_corrida


def simular_temporada_completa(banco, categoria_id, ano, num_corridas=None):
    """
    Simula uma temporada completa.
    
    Args:
        banco: banco de dados
        categoria_id: categoria a simular
        ano: ano da temporada
        num_corridas: número de corridas (se None, usa random 10-14)
    
    Returns:
        dict: resumo da temporada
    """
    import random
    from Logica.pilotos import obter_pilotos_categoria, resetar_stats_temporada
    from Logica.equipes import obter_equipes_categoria, calcular_pontos_equipes
    
    pilotos = obter_pilotos_categoria(banco, categoria_id)
    
    if not pilotos:
        return None
    
    # Reset stats
    for piloto in pilotos:
        resetar_stats_temporada(piloto)
    
    if num_corridas is None:
        num_corridas = random.randint(10, 14)
    
    corridas_stats = []
    
    # Simula cada corrida
    for i in range(num_corridas):
        resultado = simular_corrida(pilotos, banco)
        stats = processar_resultado_corrida(resultado)
        corridas_stats.append(stats)
    
    # Atualiza pontos das equipes
    tem_equipes = len(banco.get("equipes", [])) > 0
    if tem_equipes:
        calcular_pontos_equipes(banco, categoria_id)
        equipes_cat = obter_equipes_categoria(banco, categoria_id)
        
        for equipe in equipes_cat:
            equipe["pontos_historico"] = equipe.get("pontos_historico", 0) + equipe.get("pontos_temporada", 0)
            equipe["vitorias_equipe"] = equipe.get("vitorias_equipe", 0) + equipe.get("vitorias_temporada", 0)
    
    # Classificação final
    categoria_nome = next((c["nome"] for c in CATEGORIAS if c["id"] == categoria_id), categoria_id)
    
    pilotos_ordenados = sorted(
        pilotos,
        key=lambda p: (-p.get("pontos_temporada", 0), -p.get("vitorias_temporada", 0))
    )
    

    classificacao_completa = []
    
    for pos, piloto in enumerate(pilotos_ordenados):
        posicao_final = pos + 1
        
        classificacao_completa.append({
            "posicao": posicao_final,
            "nome": piloto["nome"],
            "idade": piloto["idade"],
            "pontos": piloto.get("pontos_temporada", 0),
            "vitorias": piloto.get("vitorias_temporada", 0),
            "podios": piloto.get("podios_temporada", 0),
            "poles": piloto.get("poles_temporada", 0),
            "voltas_rapidas": piloto.get("voltas_rapidas_temporada", 0),
            "corridas": num_corridas,
            "incidentes": piloto.get("incidentes_temporada", 0),
            "resultados": piloto.get("resultados_temporada", []).copy(),
            "skill": piloto["skill"],
            "equipe": piloto.get("equipe_nome", "Sem equipe")
        })
    
    campeao = pilotos_ordenados[0]
    campeao["titulos"] = campeao.get("titulos", 0) + 1
    
    # Equipe campeã
    equipe_campea_nome = None
    if tem_equipes:
        equipes_cat = obter_equipes_categoria(banco, categoria_id)
        if equipes_cat:
            equipes_ordenadas = sorted(
                equipes_cat,
                key=lambda e: e.get("pontos_temporada", 0),
                reverse=True
            )
            equipe_campea = equipes_ordenadas[0]
            equipe_campea["titulos_equipe"] = equipe_campea.get("titulos_equipe", 0) + 1
            equipe_campea_nome = equipe_campea["nome"]
    
    return {
        "campeao": campeao["nome"],
        "pontos_campeao": campeao.get("pontos_temporada", 0),
        "vice": pilotos_ordenados[1]["nome"] if len(pilotos_ordenados) > 1 else None,
        "corridas": num_corridas,
        "classificacao_completa": classificacao_completa,
        "equipe_campea": equipe_campea_nome,
        "corridas_stats": corridas_stats
    }
