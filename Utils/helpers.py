"""
Funções auxiliares reutilizáveis
Formatação, cores, conversões, etc.
"""

import re

from Dados.constantes import CATEGORIAS


# ============================================================
# CONVERSÕES SEGURAS (unificadas para todo o projeto)
# ============================================================

def int_seguro(valor, padrao=0):
    """
    Converte valor para inteiro de forma segura.

    Args:
        valor: valor a converter
        padrao: valor padrão se conversão falhar

    Returns:
        int: valor convertido ou padrão
    """
    if isinstance(valor, bool):
        return int(padrao)
    try:
        return int(valor)
    except (TypeError, ValueError):
        return int(padrao)


def normalizar_int_positivo(valor):
    """
    Converte para inteiro positivo, retornando None se inválido.
    Trata int, float, strings com vírgula/ponto.

    Args:
        valor: valor a converter

    Returns:
        int ou None: inteiro positivo ou None
    """
    if isinstance(valor, bool):
        return None

    if isinstance(valor, int):
        return valor if valor > 0 else None

    if isinstance(valor, float):
        inteiro = int(round(valor))
        return inteiro if inteiro > 0 else None

    texto = str(valor or "").strip()
    if not texto:
        return None

    if re.fullmatch(r"[+]?\d+", texto):
        inteiro = int(texto)
        return inteiro if inteiro > 0 else None

    texto_float = texto.replace(",", ".")
    try:
        numero = float(texto_float)
    except (TypeError, ValueError):
        return None

    if not numero.is_integer():
        return None

    inteiro = int(numero)
    return inteiro if inteiro > 0 else None


def formatar_tempo(tempo_ms):
    """
    Converte milissegundos para formato mm:ss.sss
    
    Args:
        tempo_ms: tempo em milissegundos
    
    Returns:
        str: tempo formatado (ex: "1:23.456")
    """
    if tempo_ms <= 0:
        return "Sem tempo"
    
    minutos = int(tempo_ms / 1000) // 60
    segundos = (tempo_ms / 1000) % 60
    return f"{minutos}:{segundos:06.3f}"


def get_cor_skill(skill):
    """
    Retorna cor baseada no skill do piloto.
    
    Args:
        skill: valor de skill (0-100)
    
    Returns:
        str: código de cor hexadecimal
    """
    if skill >= 90:
        return "#ffd700"  # Ouro
    elif skill >= 75:
        return "#00ff88"  # Verde claro
    elif skill >= 50:
        return "#00d4ff"  # Azul
    elif skill >= 30:
        return "#ffaa00"  # Laranja
    else:
        return "#ff6b6b"  # Vermelho


def get_cor_aggression(aggression):
    """
    Retorna cor baseada na agressividade do piloto.
    
    Args:
        aggression: valor de 0.0 a 1.0
    
    Returns:
        str: código de cor hexadecimal
    """
    if aggression >= 0.8:
        return "#ff6b6b"  # Vermelho (muito agressivo)
    elif aggression >= 0.6:
        return "#ffaa00"  # Laranja (moderado)
    else:
        return "#00ff88"  # Verde (calmo)


def get_cor_posicao(posicao):
    """
    Retorna cor e emoji baseado na posição final.
    
    Args:
        posicao: posição final (1, 2, 3, etc)
    
    Returns:
        tuple: (cor, emoji)
    """
    if posicao == 1:
        return "#ffd700", "🥇"
    elif posicao == 2:
        return "#c0c0c0", "🥈"
    elif posicao == 3:
        return "#cd7f32", "🥉"
    elif posicao <= 5:
        return "#00ff88", "✅"
    elif posicao <= 10:
        return "#00d4ff", ""
    else:
        return "white", ""


def obter_nome_categoria(categoria_id):
    """
    Retorna nome legível da categoria.
    
    Args:
        categoria_id: ID da categoria (ex: "mx5")
    
    Returns:
        str: nome da categoria (ex: "Mazda MX-5 Cup")
    """
    categoria = next((c for c in CATEGORIAS if c["id"] == categoria_id), None)
    return categoria["nome"] if categoria else categoria_id


