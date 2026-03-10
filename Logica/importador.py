"""
Importador de resultados do iRacing
Lê arquivos JSON das AI Seasons e atualiza o banco
"""

import json
import logging
import os
from Utils.helpers import int_seguro as _int_seguro
from Logica.pilotos import atualizar_stats_piloto

logger = logging.getLogger(__name__)

_STATUS_FINALIZADO = {
    "running",
    "finished",
    "complete",
    "completed",
    "checkered",
    "finish",
}



def _status_indica_finalizacao(status_raw) -> bool:
    return str(status_raw or "").strip().casefold() in _STATUS_FINALIZADO


def _detectar_season_mais_recente():
    """
    Detecta o arquivo .json de season mais recentemente modificado
    na pasta configurada de aiseasons.
    """
    try:
        from Dados.config import obter_pasta_aiseasons

        pasta_aiseasons = str(obter_pasta_aiseasons() or "").strip()
    except Exception:
        return ""

    if not pasta_aiseasons or not os.path.isdir(pasta_aiseasons):
        return ""

    try:
        arquivos_json = []
        for nome_arquivo in os.listdir(pasta_aiseasons):
            if not nome_arquivo.lower().endswith(".json"):
                continue
            caminho = os.path.join(pasta_aiseasons, nome_arquivo)
            if os.path.isfile(caminho):
                arquivos_json.append(caminho)
    except Exception:
        return ""

    if not arquivos_json:
        return ""

    arquivos_json.sort(key=lambda caminho: os.path.getmtime(caminho), reverse=True)
    return arquivos_json[0]


def carregar_arquivo_iracing(caminho_arquivo):
    """
    Carrega e valida arquivo JSON do iRacing.
    
    Args:
        caminho_arquivo: caminho do arquivo JSON
    
    Returns:
        dict: dados do arquivo ou None se erro
    """
    if not os.path.exists(caminho_arquivo):
        return None
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            dados = json.load(f)
        return dados
    except Exception as e:
        print(f"Erro ao carregar arquivo: {e}")
        return None


def extrair_corridas(dados_season):
    """
    Extrai todas as corridas de uma AI Season.
    
    Args:
        dados_season: dados do JSON da season
    
    Returns:
        list: lista de corridas com resultados
    """
    corridas = []
    
    eventos = dados_season.get("events", [])
    
    for i, evento in enumerate(eventos):
        resultados = evento.get("results")
        if not resultados:
            continue
        
        track_id = evento.get("trackId", "???")
        sessoes = resultados.get("session_results", [])
        
        for sessao in sessoes:
            tipo = sessao.get("simsession_type_name", "")
            
            # Só pega corridas (Race), não quali
            if tipo != "Race":
                continue
            
            pilotos_resultado = sessao.get("results", [])
            if not pilotos_resultado:
                continue
            
            # Ordena por posição
            pilotos_ordenados = sorted(
                pilotos_resultado,
                key=lambda p: _int_seguro(p.get("finish_position_in_class"), 999999)
            )
            
            corrida = {
                "evento_num": i + 1,
                "track_id": track_id,
                "tipo": tipo,
                "resultados": []
            }
            
            for piloto in pilotos_ordenados:
                posicao = _int_seguro(piloto.get("finish_position_in_class"), 999999)
                if posicao < 0:
                    posicao = 999999

                reason_out = str(piloto.get("reason_out", "Running")).strip() or "Running"
                
                # DNF se não terminou normalmente e posição ruim
                is_dnf = (not _status_indica_finalizacao(reason_out)) and posicao > 20

                incidentes = _int_seguro(piloto.get("incidents", 0), 0)
                if incidentes < 0:
                    incidentes = 0

                voltas = _int_seguro(piloto.get("laps_complete", 0), 0)
                if voltas < 0:
                    voltas = 0

                try:
                    melhor_volta = float(piloto.get("best_lap_time", -1))
                except (TypeError, ValueError):
                    melhor_volta = -1.0
                
                corrida["resultados"].append({
                    "nome": piloto.get("display_name", "???"),
                    "posicao": posicao,  # 0-indexed no iRacing
                    "posicao_final": posicao + 1,  # 1-indexed para exibição
                    "incidentes": incidentes,
                    "voltas": voltas,
                    "melhor_volta": melhor_volta,
                    "dnf": is_dnf,
                    "reason_out": reason_out
                })
            
            corridas.append(corrida)
    
    return corridas


def ler_resultado_aiseason(banco, categoria_id):
    """
    Le o resultado da rodada atual diretamente do JSON da AI Season.

    Retorno padrao:
        {
            "sucesso": bool,
            "erro": str (opcional),
            "aviso": str (opcional),
            "classificacao": list[dict] (quando sucesso),
            "rodada": int,
            "arquivo": str,
            "vencedor": str,
        }
    """
    try:
        from Dados.config import definir_season_atual, obter_season_atual
    except Exception:
        return {
            "sucesso": False,
            "erro": "Nao foi possivel carregar o modulo de configuracao das seasons.",
        }

    caminho_arquivo = str(obter_season_atual(categoria_id) or "").strip()
    if not caminho_arquivo:
        caminho_detectado = _detectar_season_mais_recente()
        if caminho_detectado:
            caminho_arquivo = caminho_detectado
            try:
                definir_season_atual(categoria_id, caminho_arquivo)
            except Exception:
                pass

    if not caminho_arquivo:
        return {
            "sucesso": False,
            "erro": (
                f"Nenhum arquivo de season configurado para a categoria '{categoria_id}'. "
                "Exporte a Season primeiro."
            ),
        }

    if not os.path.isfile(caminho_arquivo):
        caminho_detectado = _detectar_season_mais_recente()
        if caminho_detectado and os.path.isfile(caminho_detectado):
            caminho_arquivo = caminho_detectado
            try:
                definir_season_atual(categoria_id, caminho_arquivo)
            except Exception:
                pass

    if not os.path.isfile(caminho_arquivo):
        return {
            "sucesso": False,
            "erro": f"Arquivo de season nao encontrado:\n{caminho_arquivo}",
        }

    dados_season = carregar_arquivo_iracing(caminho_arquivo)
    if not isinstance(dados_season, dict):
        return {
            "sucesso": False,
            "erro": "Nao foi possivel ler o arquivo JSON da AI Season.",
        }

    try:
        rodada_atual = int(banco.get("rodada_atual", 1))
    except (TypeError, ValueError):
        rodada_atual = 1
    rodada_atual = max(1, rodada_atual)
    indice_rodada = rodada_atual - 1

    eventos = dados_season.get("events", [])
    if not isinstance(eventos, list):
        return {
            "sucesso": False,
            "erro": "Formato invalido da AI Season: campo 'events' ausente.",
        }

    if indice_rodada >= len(eventos):
        return {
            "sucesso": False,
            "erro": (
                f"A rodada {rodada_atual} nao existe no arquivo selecionado. "
                f"Total de eventos no JSON: {len(eventos)}."
            ),
        }

    evento = eventos[indice_rodada]
    if not isinstance(evento, dict):
        return {
            "sucesso": False,
            "erro": f"Evento invalido no indice da rodada {rodada_atual}.",
        }

    bloco_resultados = evento.get("results")
    if not isinstance(bloco_resultados, dict):
        return {
            "sucesso": False,
            "aviso": f"A corrida da rodada {rodada_atual} ainda nao foi concluida no iRacing.",
        }

    sessoes = bloco_resultados.get("session_results", [])
    if not isinstance(sessoes, list):
        return {
            "sucesso": False,
            "aviso": f"A corrida da rodada {rodada_atual} ainda nao foi concluida no iRacing.",
        }

    sessao_race = next(
        (
            sessao
            for sessao in sessoes
            if str(sessao.get("simsession_type_name", "")).strip().casefold() == "race"
        ),
        None,
    )

    if not isinstance(sessao_race, dict):
        return {
            "sucesso": False,
            "aviso": f"A corrida da rodada {rodada_atual} ainda nao foi concluida no iRacing.",
        }

    resultados_pilotos = sessao_race.get("results", [])
    if not isinstance(resultados_pilotos, list) or not resultados_pilotos:
        return {
            "sucesso": False,
            "aviso": f"A corrida da rodada {rodada_atual} ainda nao foi concluida no iRacing.",
        }

    classificacao = []
    for piloto in resultados_pilotos:
        if not isinstance(piloto, dict):
            continue

        nome = str(piloto.get("display_name", "")).strip()
        if not nome:
            continue

        try:
            posicao_classe = int(piloto.get("finish_position_in_class", 999999))
        except (TypeError, ValueError):
            continue

        try:
            incidentes = int(piloto.get("incidents", 0))
        except (TypeError, ValueError):
            incidentes = 0

        try:
            melhor_volta = float(piloto.get("best_lap_time", -1))
        except (TypeError, ValueError):
            melhor_volta = -1.0

        reason_out = str(piloto.get("reason_out", "Running")).strip() or "Running"
        dnf = bool(piloto.get("dnf", False))
        if not dnf:
            dnf = not _status_indica_finalizacao(reason_out)

        classificacao.append(
            {
                "piloto": nome,
                "posicao_iracing": posicao_classe + 1,
                "incidentes": incidentes,
                "reason_out": reason_out,
                "dnf": dnf,
                "best_lap_time": melhor_volta,
            }
        )

    classificacao.sort(
        key=lambda item: (
            int(item.get("posicao_iracing", 999999)),
            str(item.get("piloto", "")).casefold(),
        )
    )

    indice_volta_rapida = None
    melhor_tempo = None
    for indice, item in enumerate(classificacao):
        if bool(item.get("dnf", False)):
            continue
        try:
            tempo = float(item.get("best_lap_time", -1))
        except (TypeError, ValueError):
            continue
        if tempo <= 0:
            continue
        if melhor_tempo is None or tempo < melhor_tempo:
            melhor_tempo = tempo
            indice_volta_rapida = indice

    for indice, item in enumerate(classificacao):
        item["volta_rapida"] = indice == indice_volta_rapida
        item.pop("best_lap_time", None)

    if not classificacao:
        return {
            "sucesso": False,
            "erro": "Nenhum piloto valido foi encontrado na sessao Race da rodada atual.",
        }

    vencedor = str(classificacao[0].get("piloto", "")).strip()
    return {
        "sucesso": True,
        "classificacao": classificacao,
        "rodada": rodada_atual,
        "arquivo": caminho_arquivo,
        "vencedor": vencedor,
    }


def processar_resultado_corrida(banco, resultado_corrida, categoria_id):
    """
    Processa resultado de uma corrida e atualiza o banco.
    
    Args:
        banco: banco de dados
        resultado_corrida: dados da corrida
        categoria_id: categoria atual
    
    Returns:
        dict: estatísticas da importação
    """
    from Logica.pilotos import obter_pilotos_categoria
    
    pilotos_categoria = obter_pilotos_categoria(banco, categoria_id)
    
    # Cria mapa de nomes para pilotos
    mapa_pilotos = {p["nome"]: p for p in pilotos_categoria}
    
    stats = {
        "pilotos_encontrados": 0,
        "pilotos_nao_encontrados": [],
        "vencedor": None,
        "pontos_distribuidos": 0
    }

    melhor_volta_nome = None
    melhor_tempo = None
    for resultado in resultado_corrida.get("resultados", []):
        if bool(resultado.get("dnf", False)):
            continue
        try:
            tempo = float(resultado.get("melhor_volta", -1))
        except (TypeError, ValueError):
            continue
        if tempo <= 0:
            continue
        if melhor_tempo is None or tempo < melhor_tempo:
            melhor_tempo = tempo
            melhor_volta_nome = resultado.get("nome")
    
    for resultado in resultado_corrida.get("resultados", []):
        nome = str(resultado.get("nome", "")).strip()
        if not nome:
            continue
        
        # Procura piloto no banco
        piloto = mapa_pilotos.get(nome)
        
        if not piloto:
            stats["pilotos_nao_encontrados"].append(nome)
            continue
        
        stats["pilotos_encontrados"] += 1

        posicao_0based = _int_seguro(resultado.get("posicao"), 999)
        if posicao_0based < 0:
            posicao_0based = 999
        posicao = posicao_0based + 1  # converter para 1-based

        incidentes = _int_seguro(resultado.get("incidentes", 0), 0)
        if incidentes < 0:
            incidentes = 0

        is_dnf = bool(resultado.get("dnf", False))
        volta_rapida = not is_dnf and nome == melhor_volta_nome

        # Atualizar stats usando função unificada (1-based)
        pontos = atualizar_stats_piloto(
            piloto,
            posicao=posicao,
            dnf=is_dnf,
            volta_rapida=volta_rapida,
            incidentes=incidentes,
        )

        if not is_dnf:
            stats["pontos_distribuidos"] += pontos
            if posicao == 1:
                stats["vencedor"] = nome
    
    return stats


def importar_season_completa(banco, caminho_arquivo, categoria_id):
    """
    Importa todas as corridas de uma AI Season.
    
    Args:
        banco: banco de dados
        caminho_arquivo: caminho do JSON
        categoria_id: categoria para atualizar
    
    Returns:
        dict: resumo da importação
    """
    from Logica.equipes import calcular_pontos_equipes
    
    # Carrega arquivo
    dados = carregar_arquivo_iracing(caminho_arquivo)
    if not dados:
        return {"sucesso": False, "erro": "Não foi possível carregar o arquivo"}
    
    # Extrai corridas
    corridas = extrair_corridas(dados)
    if not corridas:
        return {"sucesso": False, "erro": "Nenhuma corrida encontrada no arquivo"}
    
    # Processa cada corrida
    total_pilotos = 0
    total_pontos = 0
    vencedores = []
    nao_encontrados = set()
    
    for corrida in corridas:
        stats = processar_resultado_corrida(banco, corrida, categoria_id)
        total_pilotos += stats["pilotos_encontrados"]
        total_pontos += stats["pontos_distribuidos"]
        if stats["vencedor"]:
            vencedores.append(stats["vencedor"])
        nao_encontrados.update(stats["pilotos_nao_encontrados"])
    
    # Atualiza pontos das equipes
    calcular_pontos_equipes(banco, categoria_id)
    
    # Info da season
    nome_season = dados.get("name", "Season Desconhecida")
    carro = dados.get("car_name", "Carro Desconhecido")
    
    return {
        "sucesso": True,
        "nome_season": nome_season,
        "carro": carro,
        "corridas_importadas": len(corridas),
        "pilotos_atualizados": total_pilotos,
        "pontos_distribuidos": total_pontos,
        "vencedores": vencedores,
        "nao_encontrados": list(nao_encontrados)
    }
