"""
Dados/config.py
Gerenciamento de configurações do aplicativo
"""

import functools
import json
import os

# Caminho do arquivo de configuração
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


@functools.lru_cache(maxsize=1)
def carregar_config():
    """Carrega as configurações do arquivo com cache na memória."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def salvar_config(config):
    """Salva as configurações no arquivo e invalida o cache."""
    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        carregar_config.cache_clear()
        return True
    except IOError:
        return False



# ══════════════════════════════════════════════════════════
# PASTAS DO IRACING
# ══════════════════════════════════════════════════════════

def obter_pasta_airosters():
    """Retorna o caminho da pasta airosters configurada."""
    config = carregar_config()
    return config.get("pasta_airosters", "")


def definir_pasta_airosters(pasta):
    """Define o caminho da pasta airosters."""
    config = carregar_config()
    config["pasta_airosters"] = pasta
    return salvar_config(config)


def obter_pasta_aiseasons():
    """Retorna o caminho da pasta aiseasons configurada."""
    config = carregar_config()
    return config.get("pasta_aiseasons", "")


def definir_pasta_aiseasons(pasta):
    """Define o caminho da pasta aiseasons."""
    config = carregar_config()
    config["pasta_aiseasons"] = pasta
    return salvar_config(config)


# ══════════════════════════════════════════════════════════
# SEASONS ATUAIS POR CATEGORIA
# ══════════════════════════════════════════════════════════

def obter_season_atual(categoria_id):
    """
    Retorna o caminho do arquivo de season atual para uma categoria.
    
    Args:
        categoria_id: ID da categoria (ex: "mx5", "gt4", "gt3")
    
    Returns:
        str: Caminho do arquivo ou string vazia se não definido
    """
    config = carregar_config()
    seasons = config.get("seasons_atuais", {})
    return seasons.get(categoria_id, "")


def definir_season_atual(categoria_id, caminho_arquivo):
    """
    Define o arquivo de season atual para uma categoria.
    
    Args:
        categoria_id: ID da categoria
        caminho_arquivo: Caminho completo do arquivo .json da season
    
    Returns:
        bool: True se salvo com sucesso
    """
    config = carregar_config()
    if "seasons_atuais" not in config:
        config["seasons_atuais"] = {}
    config["seasons_atuais"][categoria_id] = caminho_arquivo
    return salvar_config(config)
# ══════════════════════════════════════════════════════════
# FUNÇÕES AUXILIARES
# ══════════════════════════════════════════════════════════

def obter_todas_seasons():
    """Retorna todas as seasons configuradas."""
    config = carregar_config()
    return config.get("seasons_atuais", {})