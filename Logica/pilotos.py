"""
Lógica de gerenciamento de pilotos
Criação, geração de nomes, evolução, aposentadoria, transferências
"""

import copy
import logging
import random
from Dados.constantes import CATEGORIAS, PONTOS_POR_POSICAO, POOL_NOMES_NACIONALIDADES
from Dados.banco import obter_proximo_id

logger = logging.getLogger(__name__)


# ============================================================
# TAXAS DE DECLÍNIO POR ATRIBUTO
# Aplicado após idade 33, quanto maior = mais rápido cai
# ============================================================

TAXAS_DECLINIO = {
  # Caem rápido (físico/reflexo)
  "skill":        1.0,
  "ritmo_classificacao": 1.2,
  "fitness":       1.5,
  "habilidade_largada": 0.8,
  # Caem devagar (experiência compensa)
  "consistencia":    0.3,
  "resistencia_mental": 0.2,
  "fator_clutch":    0.3,
  # Quase não caem (sabedoria)
  "racecraft":      0.1,
  "gestao_pneus":    0.1,
  # Não caem
  "adaptabilidade":   0.0,
  "fator_chuva":     0.2,
  "experiencia":     0.0,
  # iRacing attributes
  "aggression":     0.0,
  "optimism":      0.0,
  "smoothness":     0.1,
}

# ── Tipos de lesão (constante)
TIPOS_LESAO = {
  "leve":   {"corridas_restantes": 2, "modifier": 0.95},
  "moderada": {"corridas_restantes": 4, "modifier": 0.88},
  "grave":  {"corridas_restantes": 8, "modifier": 0.75},
}

# ── Motivos válidos de rivalidade (constante)
MOTIVOS_RIVALIDADE = [
  "disputa_campeonato",
  "colisao",
  "vaga_equipe",
  "declaracao_midia",
  "ultrapassagem_controversa",
]


# ============================================================
# HELPERS
# ============================================================

PILOTO_CAMPOS_OBRIGATORIOS = (
  "id",
  "nome",
  "nacionalidade",
  "idade",
  "ano_inicio_carreira",
  "skill",
  "aggression",
  "optimism",
  "smoothness",
  "consistencia",
  "racecraft",
  "ritmo_classificacao",
  "gestao_pneus",
  "habilidade_largada",
  "fator_chuva",
  "resistencia_mental",
  "fator_clutch",
  "motivacao",
  "fitness",
  "adaptabilidade",
  "experiencia",
  "potencial_base",
  "potencial_bonus",
  "potencial",
  "crescimento",
  "atributos_extras",
  "status",
  "aposentado",
  "is_jogador",
  "equipe_id",
  "equipe_nome",
  "papel",
  "contrato_anos",
  "salario",
  "categoria_atual",
  "temporadas_na_categoria",
  "corridas_na_categoria",
  "lesao",
  "rivalidades",
  "relacao_companheiro",
  "historico_equipes",
  "historico_circuitos",
  "historico_temporadas",
  "titulos",
  "vitorias_carreira",
  "podios_carreira",
  "poles_carreira",
  "voltas_rapidas_carreira",
  "corridas_carreira",
  "pontos_carreira",
  "dnfs_carreira",
  "incidentes_carreira",
  "pontos_temporada",
  "vitorias_temporada",
  "podios_temporada",
  "poles_temporada",
  "voltas_rapidas_temporada",
  "corridas_temporada",
  "dnfs_temporada",
  "incidentes_temporada",
  "melhor_resultado_temporada",
  "resultados_temporada",
)

PILOTO_CAMPOS_PODEM_SER_NULOS = {"equipe_id", "equipe_nome", "papel", "lesao"}


def _int_em_faixa(valor, minimo, maximo, padrao):
  """Converte para int e aplica clamp."""
  try:
    numero = int(round(float(valor)))
  except (TypeError, ValueError):
    numero = int(padrao)

  if numero < minimo:
    return minimo
  if numero > maximo:
    return maximo
  return numero


def _defaults_schema_piloto(piloto):
  """
  Monta defaults do schema completo de piloto com base no estado atual.
  """
  skill = _int_em_faixa(piloto.get("skill", 50), 1, 100, 50)
  idade = _int_em_faixa(piloto.get("idade", 24), 16, 60, 24)
  categoria = str(piloto.get("categoria_atual", "mazda_rookie") or "mazda_rookie")
  status = str(piloto.get("status", "ativo") or "ativo")
  aposentado = bool(piloto.get("aposentado", False)) or status == "aposentado"
  potencial = _int_em_faixa(
    piloto.get("potencial_base", piloto.get("potencial", max(skill + 10, 40))),
    30,
    100,
    max(skill + 10, 40),
  )
  contrato_anos = 0 if aposentado else 1
  idade_referencia = max(idade - 16, 0)
  salario_padrao = calcular_salario_inicial(skill, idade)

  return {
    "id": piloto.get("id"),
    "nome": str(piloto.get("nome", "") or ""),
    "nacionalidade": str(piloto.get("nacionalidade", "🌍 Internacional") or "🌍 Internacional"),
    "idade": idade,
    "ano_inicio_carreira": _int_em_faixa(
      piloto.get("ano_inicio_carreira", piloto.get("ano_atual", 2024)),
      1900,
      3000,
      2024,
    ),
    "skill": skill,
    "aggression": _int_em_faixa(piloto.get("aggression", 50), 0, 100, 50),
    "optimism": _int_em_faixa(piloto.get("optimism", 55), 0, 100, 55),
    "smoothness": _int_em_faixa(piloto.get("smoothness", 55), 0, 100, 55),
    "consistencia": _int_em_faixa(piloto.get("consistencia", skill), 0, 100, skill),
    "racecraft": _int_em_faixa(piloto.get("racecraft", skill), 0, 100, skill),
    "ritmo_classificacao": _int_em_faixa(
      piloto.get("ritmo_classificacao", skill),
      0,
      100,
      skill,
    ),
    "gestao_pneus": _int_em_faixa(piloto.get("gestao_pneus", 55), 0, 100, 55),
    "habilidade_largada": _int_em_faixa(piloto.get("habilidade_largada", 55), 0, 100, 55),
    "fator_chuva": _int_em_faixa(piloto.get("fator_chuva", 50), 0, 100, 50),
    "resistencia_mental": _int_em_faixa(piloto.get("resistencia_mental", 55), 0, 100, 55),
    "fator_clutch": _int_em_faixa(piloto.get("fator_clutch", 55), 0, 100, 55),
    "motivacao": _int_em_faixa(piloto.get("motivacao", 70), 0, 100, 70),
    "fitness": _int_em_faixa(piloto.get("fitness", 85 - max(idade - 28, 0) * 2), 0, 100, 65),
    "adaptabilidade": _int_em_faixa(piloto.get("adaptabilidade", 55), 0, 100, 55),
    "experiencia": _int_em_faixa(
      piloto.get("experiencia", idade_referencia * 4),
      0,
      100,
      idade_referencia * 4,
    ),
    "potencial_base": potencial,
    "potencial_bonus": _int_em_faixa(piloto.get("potencial_bonus", 0), 0, 30, 0),
    "potencial": potencial,
    "crescimento": float(piloto.get("crescimento", 1.0) or 1.0),
    "atributos_extras": {},
    "status": "aposentado" if aposentado else status,
    "aposentado": aposentado,
    "is_jogador": bool(piloto.get("is_jogador", False)),
    "equipe_id": piloto.get("equipe_id"),
    "equipe_nome": piloto.get("equipe_nome"),
    "papel": piloto.get("papel"),
    "contrato_anos": _int_em_faixa(piloto.get("contrato_anos", contrato_anos), 0, 10, contrato_anos),
    "salario": _int_em_faixa(piloto.get("salario", salario_padrao), 0, 10_000_000, salario_padrao),
    "categoria_atual": categoria,
    "temporadas_na_categoria": _int_em_faixa(
      piloto.get("temporadas_na_categoria", 0),
      0,
      100,
      0,
    ),
    "corridas_na_categoria": _int_em_faixa(
      piloto.get("corridas_na_categoria", 0),
      0,
      5000,
      0,
    ),
    "lesao": piloto.get("lesao"),
    "rivalidades": [],
    "relacao_companheiro": _int_em_faixa(piloto.get("relacao_companheiro", 0), -100, 100, 0),
    "historico_equipes": [],
    "historico_circuitos": {},
    "historico_temporadas": [],
    "titulos": _int_em_faixa(piloto.get("titulos", 0), 0, 200, 0),
    "vitorias_carreira": _int_em_faixa(piloto.get("vitorias_carreira", 0), 0, 5000, 0),
    "podios_carreira": _int_em_faixa(piloto.get("podios_carreira", 0), 0, 5000, 0),
    "poles_carreira": _int_em_faixa(piloto.get("poles_carreira", 0), 0, 5000, 0),
    "voltas_rapidas_carreira": _int_em_faixa(
      piloto.get("voltas_rapidas_carreira", 0),
      0,
      5000,
      0,
    ),
    "corridas_carreira": _int_em_faixa(piloto.get("corridas_carreira", 0), 0, 5000, 0),
    "pontos_carreira": _int_em_faixa(piloto.get("pontos_carreira", 0), 0, 500_000, 0),
    "dnfs_carreira": _int_em_faixa(piloto.get("dnfs_carreira", 0), 0, 5000, 0),
    "incidentes_carreira": _int_em_faixa(piloto.get("incidentes_carreira", 0), 0, 5000, 0),
    "pontos_temporada": _int_em_faixa(piloto.get("pontos_temporada", 0), 0, 500_000, 0),
    "vitorias_temporada": _int_em_faixa(piloto.get("vitorias_temporada", 0), 0, 5000, 0),
    "podios_temporada": _int_em_faixa(piloto.get("podios_temporada", 0), 0, 5000, 0),
    "poles_temporada": _int_em_faixa(piloto.get("poles_temporada", 0), 0, 5000, 0),
    "voltas_rapidas_temporada": _int_em_faixa(
      piloto.get("voltas_rapidas_temporada", 0),
      0,
      5000,
      0,
    ),
    "corridas_temporada": _int_em_faixa(piloto.get("corridas_temporada", 0), 0, 5000, 0),
    "dnfs_temporada": _int_em_faixa(piloto.get("dnfs_temporada", 0), 0, 5000, 0),
    "incidentes_temporada": _int_em_faixa(piloto.get("incidentes_temporada", 0), 0, 5000, 0),
    "melhor_resultado_temporada": _int_em_faixa(
      piloto.get("melhor_resultado_temporada", 99),
      1,
      99,
      99,
    ),
    "resultados_temporada": [],
  }

def preencher_campos_obrigatorios_piloto(piloto):
  """
  Preenche campos obrigatórios ausentes ou nulos (exceto campos nullable).

  Returns:
    bool: True se algum campo foi preenchido/ajustado.
  """
  if not isinstance(piloto, dict):
    return False

  alterado = False

  agg = piloto.get("aggression")
  if isinstance(agg, float) and agg <= 1.0:
    piloto["aggression"] = _int_em_faixa(agg * 100, 0, 100, 50)
    alterado = True

  if isinstance(piloto.get("skill"), float):
    piloto["skill"] = int(piloto["skill"])
    alterado = True

  defaults = _defaults_schema_piloto(piloto)

  for campo in PILOTO_CAMPOS_OBRIGATORIOS:
    if campo not in piloto:
      piloto[campo] = copy.deepcopy(defaults[campo])
      alterado = True
      continue

    if campo in PILOTO_CAMPOS_PODEM_SER_NULOS:
      continue

    if piloto.get(campo) is None:
      piloto[campo] = copy.deepcopy(defaults[campo])
      alterado = True

  if "potencial" in piloto and piloto.get("potencial_base") is None:
    piloto["potencial_base"] = piloto["potencial"]
    alterado = True

  if "potencial_base" in piloto and piloto.get("potencial") is None:
    piloto["potencial"] = piloto["potencial_base"]
    alterado = True

  if isinstance(piloto.get("atributos_extras"), dict) is False:
    piloto["atributos_extras"] = {}
    alterado = True

  if isinstance(piloto.get("historico_circuitos"), dict) is False:
    piloto["historico_circuitos"] = {}
    alterado = True

  for campo_lista in (
    "rivalidades",
    "historico_equipes",
    "historico_temporadas",
    "resultados_temporada",
  ):
    if isinstance(piloto.get(campo_lista), list) is False:
      piloto[campo_lista] = []
      alterado = True

  return alterado


def validar_schema_piloto(piloto, raise_on_error=False):
  """
  Valida se o piloto segue o schema obrigatório.

  Args:
    piloto: dict de piloto.
    raise_on_error: quando True, lança ValueError em caso de schema inválido.

  Returns:
    dict: {"valido": bool, "campos_faltantes": [...], "campos_nulos": [...]}
  """
  campos_faltantes = []
  campos_nulos = []

  if not isinstance(piloto, dict):
    campos_faltantes = list(PILOTO_CAMPOS_OBRIGATORIOS)
  else:
    for campo in PILOTO_CAMPOS_OBRIGATORIOS:
      if campo not in piloto:
        campos_faltantes.append(campo)
        continue

      if campo in PILOTO_CAMPOS_PODEM_SER_NULOS:
        continue

      if piloto.get(campo) is None:
        campos_nulos.append(campo)

  valido = not campos_faltantes and not campos_nulos
  resultado = {
    "valido": valido,
    "campos_faltantes": campos_faltantes,
    "campos_nulos": campos_nulos,
  }

  if raise_on_error and not valido:
    raise ValueError(
      "Piloto com schema inválido. "
      f"Faltantes: {campos_faltantes}. Nulos: {campos_nulos}."
    )

  return resultado


def normalizar_aggression(valor):
  """
  Normaliza o campo aggression para float 0.0-1.0,
  suportando tanto o formato antigo (float 0.3-0.9)
  quanto o novo (int 0-100).

  Args:
    valor: aggression bruta (int ou float)

  Returns:
    float: valor normalizado 0.0-1.0
  """
  if isinstance(valor, (int, float)) and valor > 1.0:
    return valor / 100.0
  return float(valor)


def migrar_piloto_schema_antigo(piloto):
  """
  Garante que um piloto carregado de um banco antigo
  tenha todos os campos do schema novo com valores default.

  Não sobrescreve campos que já existam.
  Seguro chamar múltiplas vezes (idempotente).

  Args:
    piloto: dict do piloto (modificado in-place)

  Returns:
    dict: mesmo piloto, com campos novos preenchidos
  """
  preencher_campos_obrigatorios_piloto(piloto)
  validar_schema_piloto(piloto, raise_on_error=True)
  return piloto


# ============================================================
# BUSCA E CONSULTA
# ============================================================

def gerar_nome_unico(banco):
  """
  Gera um nome único que não existe no banco.

  Args:
    banco: banco de dados

  Returns:
    tuple[str, str]: nome completo único e nacionalidade
  """
  nomes_existentes = {
    str(p.get("nome", "")).strip()
    for p in banco.get("pilotos", [])
    if p.get("nome")
  }

  pools = POOL_NOMES_NACIONALIDADES or []
  if not pools:
    return "Piloto IA", "🌍 Internacional"

  pesos = [max(0, int(item.get("peso", 0))) for item in pools]
  if not any(pesos):
    pesos = [1 for _ in pools]

  for _ in range(500):
    pool = random.choices(pools, weights=pesos, k=1)[0]
    primeiros_nomes = list(pool.get("nomes_masculinos", [])) + list(
      pool.get("nomes_femininos", [])
    )
    sobrenomes = list(pool.get("sobrenomes", []))
    if not primeiros_nomes or not sobrenomes:
      continue

    base_nome = f"{random.choice(primeiros_nomes)} {random.choice(sobrenomes)}"
    nacionalidade = str(pool.get("rotulo", "🌍 Internacional"))
    if base_nome not in nomes_existentes:
      return base_nome, nacionalidade

    # Mantém a nacionalidade sorteada e só cria sufixo em caso de colisão.
    for sufixo in range(2, 9999):
      nome = f"{base_nome} {sufixo}"
      if nome not in nomes_existentes:
        return nome, nacionalidade

  return "Piloto IA", "🌍 Internacional"


def obter_pilotos_categoria(banco, categoria_id):
  """
  Retorna todos os pilotos ativos de uma categoria.

  Args:
    banco: banco de dados
    categoria_id: ID da categoria

  Returns:
    list: pilotos da categoria
  """
  return [
    p for p in banco.get("pilotos", [])
    if p.get("categoria_atual") == categoria_id
    and p.get("status", "ativo") not in ("aposentado", "reserva_global", "livre", "reserva")
    and not p.get("aposentado", False)
  ]


# ============================================================
# POTENCIAL
# ============================================================

def gerar_potencial_base():
  """
  Gera potencial base com distribuição de raridade.

  Distribuição:
  - Lendário (90-100): 2%
  - Elite (80-89):   8%
  - Muito bom (70-79): 15%
  - Bom (60-69):    25%
  - Mediano (50-59):  30%
  - Limitado (40-49): 15%
  - Fraco (30-39):   5%

  Returns:
    int: potencial base (30-100)
  """
  roll = random.random() * 100

  if roll < 2:
    return random.randint(90, 100)  # Lendário
  elif roll < 10:
    return random.randint(80, 89)  # Elite
  elif roll < 25:
    return random.randint(70, 79)  # Muito bom
  elif roll < 50:
    return random.randint(60, 69)  # Bom
  elif roll < 80:
    return random.randint(50, 59)  # Mediano
  elif roll < 95:
    return random.randint(40, 49)  # Limitado
  else:
    return random.randint(30, 39)  # Fraco


def obter_potencial_efetivo(piloto):
  """
  Retorna o potencial efetivo (teto real de skill).

  potencial_efetivo = min(100, potencial_base + potencial_bonus)
  """
  base = piloto.get("potencial_base", piloto.get("potencial", 50))
  bonus = piloto.get("potencial_bonus", 0)
  return min(100, base + bonus)


def calcular_bonus_potencial(piloto, equipe, resultados_temporada):
  """
  Calcula bônus de potencial baseado em contexto.
  Chamado no fim de cada temporada.

  O bônus acumula até um máximo de 30.
  Representa "desbloquear" potencial latente.

  Args:
    piloto: dict do piloto
    equipe: dict da equipe atual
    resultados_temporada: lista de posições

  Returns:
    int: bônus a adicionar (0-5 por temporada)
  """
  bonus = 0
  bonus_atual = piloto.get("potencial_bonus", 0)
  espaco_restante = 30 - bonus_atual

  if espaco_restante <= 0:
    return 0

  # 1. Equipe com boas instalações (facilities)
  if equipe:
    facilities = equipe.get("facilities", 50)
    if facilities >= 80:
      bonus += 2
    elif facilities >= 60:
      bonus += 1

  # 2. Equipe com bom budget
  if equipe:
    budget = equipe.get("budget", 50)
    if budget >= 80:
      bonus += 1

  # 3. Resultados excepcionais
  if resultados_temporada:
    vitorias = sum(1 for r in resultados_temporada if r == 1)
    podios = sum(1 for r in resultados_temporada if isinstance(r, int) and r <= 3)

    if vitorias >= 5:
      bonus += 2
    elif vitorias >= 3:
      bonus += 1

    if podios >= 8:
      bonus += 1

  # Limitar ao espaço restante
  bonus = min(bonus, espaco_restante)

  # Máximo +5 por temporada
  bonus = min(bonus, 5)

  return bonus


# ============================================================
# SALÁRIO
# ============================================================

def calcular_salario_inicial(skill, idade):
  """
  Calcula salário inicial baseado em skill e idade.

  Range: 10.000 a 500.000 (unidades abstratas)
  """
  base = skill * 1000 # 30k a 100k base

  # Jovens promissores custam mais
  if idade <= 22 and skill >= 50:
    base *= 1.3

  # Veteranos custam menos (menos tempo de carreira pela frente)
  if idade >= 32:
    base *= 0.7

  # Adicionar variação
  base *= random.uniform(0.8, 1.2)

  return int(base)


# ============================================================
# CRIAÇÃO DE PILOTOS
# ============================================================

def criar_piloto(banco, categoria_id="mazda_rookie", skill_min=30, skill_max=70,
         idade_min=18, idade_max=26, ano_atual=None):
  """
  Cria um novo piloto com todos os atributos do schema completo.

  Args:
    banco: banco de dados
    categoria_id: ID da categoria inicial
    skill_min: skill mínimo
    skill_max: skill máximo
    idade_min: idade mínima
    idade_max: idade máxima
    ano_atual: ano atual (se None, pega do banco)

  Returns:
    dict: dados do piloto
  """
  if ano_atual is None:
    ano_atual = banco.get("ano_atual", 2024)

  nome, nacionalidade = gerar_nome_unico(banco)
  idade = random.randint(idade_min, idade_max)

  # Potencial base com raridade
  potencial_base = gerar_potencial_base()

  # Skill inicial: percentual do potencial, ajustado pela idade
  if idade <= 20:
    skill_pct = random.uniform(0.45, 0.65)
  elif idade <= 25:
    skill_pct = random.uniform(0.60, 0.80)
  else:
    skill_pct = random.uniform(0.75, 0.95)

  skill_base = int(potencial_base * skill_pct)
  skill_base = max(skill_min, min(skill_max, skill_base))

  # Atributos de simulação (correlacionados onde faz sentido)
  consistencia = int(30 + (idade - 16) * 1.5 + random.gauss(0, 10))
  consistencia = max(20, min(90, consistencia))

  racecraft = int(20 + (idade - 16) * 2 + random.gauss(0, 8))
  racecraft = max(20, min(90, racecraft))

  experiencia = min(100, (idade - 16) * 4 + random.randint(-5, 10))
  experiencia = max(0, experiencia)

  fitness = int(85 - max(0, (idade - 28)) * 2 + random.gauss(0, 5))
  fitness = max(40, min(100, fitness))

  # Atributos independentes
  aggression = random.randint(20, 90)
  optimism = random.randint(30, 80)
  smoothness = random.randint(30, 90)

  ritmo_classificacao = int(skill_base * random.uniform(0.85, 1.15))
  ritmo_classificacao = max(20, min(100, ritmo_classificacao))

  gestao_pneus = random.randint(30, 80)
  habilidade_largada = random.randint(30, 80)
  fator_chuva = random.randint(20, 90)
  resistencia_mental = random.randint(30, 80)
  fator_clutch = random.randint(30, 80)
  adaptabilidade = random.randint(30, 80)
  motivacao = random.randint(60, 85)

  # Correlações: agressividade alta tende a suavidade baixa
  if aggression > 70:
    smoothness = max(20, smoothness - random.randint(5, 15))
  elif aggression < 40:
    smoothness = min(95, smoothness + random.randint(5, 10))

  piloto = {
    # ── Identificação ──
    "id": obter_proximo_id(banco, "piloto"),
    "nome": nome,
    "nacionalidade": nacionalidade,
    "idade": idade,
    "ano_inicio_carreira": ano_atual,

    # ── iRacing (0-100 inteiros) ──
    "skill": skill_base,
    "aggression": aggression,
    "optimism": optimism,
    "smoothness": smoothness,

    # ── Simulação - Performance ──
    "consistencia": consistencia,
    "racecraft": racecraft,
    "ritmo_classificacao": ritmo_classificacao,
    "gestao_pneus": gestao_pneus,
    "habilidade_largada": habilidade_largada,
    "fator_chuva": fator_chuva,

    # ── Simulação - Mental ──
    "resistencia_mental": resistencia_mental,
    "fator_clutch": fator_clutch,
    "motivacao": motivacao,

    # ── Simulação - Físico ──
    "fitness": fitness,
    "adaptabilidade": adaptabilidade,

    # ── Simulação - Experiência ──
    "experiencia": experiencia,

    # ── Potencial ──
    "potencial_base": potencial_base,
    "potencial_bonus": 0,
    # compatibilidade com código antigo que usa "potencial"
    "potencial": potencial_base,
    "crescimento": round(random.uniform(0.5, 2.0), 2),

    # ── Reservado para expansão ──
    "atributos_extras": {},

    # ── Status e Contrato ──
    "status": "ativo",
    "aposentado": False,  # mantido para compatibilidade retroativa
    "is_jogador": False,

    "equipe_id": None,
    "equipe_nome": None,
    "papel": None,
    "contrato_anos": random.randint(1, 2),
    "salario": calcular_salario_inicial(skill_base, idade),

    "categoria_atual": categoria_id,
    "temporadas_na_categoria": 0,
    "corridas_na_categoria": 0,

    # ── Lesão ──
    "lesao": None,

    # ── Relacionamentos ──
    "rivalidades": [],
    "relacao_companheiro": 0,

    # ── Históricos ──
    "historico_equipes": [],
    "historico_circuitos": {},
    "historico_temporadas": [],

    # ── Stats Carreira ──
    "titulos": 0,
    "vitorias_carreira": 0,
    "podios_carreira": 0,
    "poles_carreira": 0,
    "voltas_rapidas_carreira": 0,
    "corridas_carreira": 0,
    "pontos_carreira": 0,
    "dnfs_carreira": 0,
    "incidentes_carreira": 0,

    # ── Stats Temporada ──
    "pontos_temporada": 0,
    "vitorias_temporada": 0,
    "podios_temporada": 0,
    "poles_temporada": 0,
    "voltas_rapidas_temporada": 0,
    "corridas_temporada": 0,
    "dnfs_temporada": 0,
    "incidentes_temporada": 0,
    "melhor_resultado_temporada": 99,
    "resultados_temporada": [],
  }

  preencher_campos_obrigatorios_piloto(piloto)
  validar_schema_piloto(piloto, raise_on_error=True)
  return piloto


def criar_piloto_lenda(banco, categoria_id, ano_atual):
  """
  Cria um piloto lendário com stats elevadas.

  Args:
    banco: banco de dados
    categoria_id: categoria do piloto
    ano_atual: ano atual

  Returns:
    dict: piloto lendário
  """
  lenda = criar_piloto(
    banco, categoria_id,
    skill_min=90, skill_max=100,
    idade_min=28, idade_max=35,
    ano_atual=ano_atual - random.randint(5, 10)
  )

  lenda["titulos"] = random.randint(2, 5)
  lenda["vitorias_carreira"] = random.randint(15, 40)
  lenda["podios_carreira"] = random.randint(30, 70)
  lenda["poles_carreira"] = random.randint(10, 30)
  lenda["voltas_rapidas_carreira"] = random.randint(8, 25)
  lenda["corridas_carreira"] = random.randint(80, 150)
  lenda["pontos_carreira"] = random.randint(500, 1500)

  return lenda


def gerar_piloto_substituto(banco, equipe_id=None, categoria_id="mazda_rookie",
               ano_atual=None):
  """
  Gera um novo piloto jovem para substituir aposentado.

  Args:
    banco: banco de dados
    equipe_id: equipe para o novo piloto (ou None)
    categoria_id: categoria inicial
    ano_atual: ano atual

  Returns:
    dict: novo piloto gerado
  """
  piloto = criar_piloto(
    banco, categoria_id,
    skill_min=30, skill_max=65,
    idade_min=17, idade_max=21,
    ano_atual=ano_atual
  )

  piloto["equipe_id"] = equipe_id

  # Encontrar nome da equipe
  if equipe_id:
    equipe = next(
      (eq for eq in banco.get("equipes", []) if eq.get("id") == equipe_id),
      None
    )
    if equipe:
      piloto["equipe_nome"] = equipe.get("nome", "")

  banco["pilotos"].append(piloto)
  logger.info("%s entrou na %s", piloto['nome'], categoria_id)

  return piloto


# ============================================================
# POPULAÇÃO DE CATEGORIAS
# ============================================================

def popular_categoria(banco, categoria_id, quantidade=20, ano_atual=None):
  """
  Popula uma categoria com pilotos gerados.

  Args:
    banco: banco de dados
    categoria_id: ID da categoria
    quantidade: número de pilotos a criar
    ano_atual: ano atual (se None, pega do banco)

  Returns:
    list: pilotos criados
  """
  categoria = next((c for c in CATEGORIAS if c["id"] == categoria_id), None)
  if not categoria:
    return []

  nivel = categoria["nivel"]

  if nivel == 1:
    skill_min, skill_max = 25, 70
    idade_min, idade_max = 18, 24
  elif nivel == 2:
    skill_min, skill_max = 40, 78
    idade_min, idade_max = 20, 26
  elif nivel == 3:
    skill_min, skill_max = 50, 85
    idade_min, idade_max = 22, 28
  elif nivel == 4:
    skill_min, skill_max = 60, 92
    idade_min, idade_max = 24, 30
  else:
    skill_min, skill_max = 70, 99
    idade_min, idade_max = 26, 34

  pilotos_criados = []
  for _ in range(quantidade):
    piloto = criar_piloto(
      banco, categoria_id, skill_min, skill_max,
      idade_min, idade_max, ano_atual
    )
    banco["pilotos"].append(piloto)
    pilotos_criados.append(piloto)

  return pilotos_criados


# ============================================================
# STATS DE TEMPORADA
# ============================================================

def resetar_stats_temporada(piloto):
  """
  Reseta as estatísticas de temporada de um piloto.

  Args:
    piloto: dados do piloto
  """
  piloto["pontos_temporada"] = 0
  piloto["vitorias_temporada"] = 0
  piloto["podios_temporada"] = 0
  piloto["poles_temporada"] = 0
  piloto["voltas_rapidas_temporada"] = 0
  piloto["corridas_temporada"] = 0
  piloto["dnfs_temporada"] = 0
  piloto["incidentes_temporada"] = 0
  piloto["melhor_resultado_temporada"] = 99
  piloto["resultados_temporada"] = []


def atualizar_stats_piloto(piloto, posicao, dnf=False, volta_rapida=False, incidentes=0):
  """
  Atualiza as stats de um piloto após uma corrida.
  Função unificada usada tanto pela simulação quanto pelo importador.

  Args:
    piloto: dict do piloto
    posicao: posição final (1-based, ex: 1 = vencedor)
    dnf: se o piloto abandonou
    volta_rapida: se fez a volta mais rápida da corrida
    incidentes: número de incidentes na corrida

  Returns:
    int: pontos ganhos na corrida
  """
  # Corridas
  piloto["corridas_temporada"] = piloto.get("corridas_temporada", 0) + 1
  piloto["corridas_carreira"] = piloto.get("corridas_carreira", 0) + 1
  piloto["corridas_na_categoria"] = piloto.get("corridas_na_categoria", 0) + 1

  # Atualizar lesão (reduz contador após cada corrida)
  atualizar_lesao(piloto)

  # Incidentes
  if incidentes > 0:
    piloto["incidentes_carreira"] = piloto.get("incidentes_carreira", 0) + incidentes
    piloto["incidentes_temporada"] = piloto.get("incidentes_temporada", 0) + incidentes

  # Resultados da temporada
  if "resultados_temporada" not in piloto:
    piloto["resultados_temporada"] = []

  if dnf:
    piloto["dnfs_temporada"] = piloto.get("dnfs_temporada", 0) + 1
    piloto["dnfs_carreira"] = piloto.get("dnfs_carreira", 0) + 1
    piloto["resultados_temporada"].append("DNF")
    return 0

  # Registrar posição
  piloto["resultados_temporada"].append(posicao)
  piloto["melhor_resultado_temporada"] = min(
    int(piloto.get("melhor_resultado_temporada", 99)),
    posicao,
  )

  # Pontos (1-based)
  pontos = PONTOS_POR_POSICAO.get(posicao, 0)
  if volta_rapida and posicao <= 10:
    pontos += 1
  piloto["pontos_temporada"] = piloto.get("pontos_temporada", 0) + pontos
  piloto["pontos_carreira"] = piloto.get("pontos_carreira", 0) + pontos

  # Vitória
  if posicao == 1:
    piloto["vitorias_carreira"] = piloto.get("vitorias_carreira", 0) + 1
    piloto["vitorias_temporada"] = piloto.get("vitorias_temporada", 0) + 1

  # Pódio
  if posicao <= 3:
    piloto["podios_carreira"] = piloto.get("podios_carreira", 0) + 1
    piloto["podios_temporada"] = piloto.get("podios_temporada", 0) + 1

  # Volta rápida (separado de pole)
  if volta_rapida:
    piloto["voltas_rapidas_carreira"] = piloto.get("voltas_rapidas_carreira", 0) + 1
    piloto["voltas_rapidas_temporada"] = piloto.get("voltas_rapidas_temporada", 0) + 1

  return pontos


# ============================================================
# POSIÇÃO NO CAMPEONATO
# ============================================================

def calcular_posicao_campeonato(banco, piloto, categoria_id="mazda_rookie"):
  """
  Calcula a posição atual do piloto no campeonato.

  Args:
    banco: banco de dados
    piloto: dict do piloto
    categoria_id: categoria para filtrar

  Returns:
    int: posição (1 = líder)
  """
  pilotos_cat = obter_pilotos_categoria(banco, categoria_id)

  pilotos_cat.sort(
    key=lambda p: (
      -p.get("pontos_temporada", 0),
      -p.get("vitorias_temporada", 0),
      -p.get("podios_temporada", 0),
      p.get("melhor_resultado_temporada", 99)
    )
  )

  for i, p in enumerate(pilotos_cat, start=1):
    if p.get("id") == piloto.get("id"):
      return i

  return len(pilotos_cat) + 1


# ============================================================
# ENVELHECIMENTO E EVOLUÇÃO
# ============================================================

def envelhecer_piloto(piloto):
  """
  Envelhece um piloto em 1 ano.
  Aplica declínio de múltiplos atributos se necessário (após 33 anos).

  Args:
    piloto: dados do piloto
  """
  piloto["idade"] = piloto.get("idade", 20) + 1
  piloto["temporadas_na_categoria"] = piloto.get("temporadas_na_categoria", 0) + 1

  idade = piloto["idade"]
  if idade > 33:
    _degradar_por_idade(piloto, idade)


def envelhecer_pilotos(banco):
  """
  Incrementa a idade de todos os pilotos ativos.

  Args:
    banco: banco de dados
  """
  for piloto in banco.get("pilotos", []):
    if not piloto.get("aposentado", False) and piloto.get("status", "ativo") != "aposentado":
      envelhecer_piloto(piloto)


def _degradar_por_idade(piloto, idade):
  """
  Reduz múltiplos atributos de pilotos mais velhos, com base
  em TAXAS_DECLINIO por atributo.

  Quanto mais velho, maior a chance e intensidade do declínio.

  Args:
    piloto: dados do piloto
    idade: idade atual
  """
  chance_degradar = min(0.8, (idade - 32) * 0.12)

  if random.random() >= chance_degradar:
    return

  for atributo, taxa in TAXAS_DECLINIO.items():
    if taxa <= 0.0:
      continue

    valor_atual = piloto.get(atributo)
    if valor_atual is None:
      continue

    # Declínio proporcional à taxa
    declinio = random.uniform(0.3, 1.5) * taxa
    novo_valor = valor_atual - declinio

    # Manter dentro de limites razoáveis
    if atributo == "skill":
      piloto[atributo] = round(max(20, novo_valor), 1)
    else:
      piloto[atributo] = max(10, int(novo_valor))


def evoluir_piloto(piloto, ganho_skill=None):
  """
  Evolui o skill de um piloto.

  Leva em conta o potencial efetivo: se o skill está abaixo do potencial,
  o crescimento é maior; se está acima, é menor.

  Args:
    piloto: dados do piloto
    ganho_skill: quanto evoluir (se None, calcula automaticamente)
  """
  if ganho_skill is None:
    potencial = obter_potencial_efetivo(piloto)
    skill_atual = piloto.get("skill", 50)
    taxa_crescimento = piloto.get("crescimento", 1.0)

    # Crescimento maior se está longe do potencial
    diferenca = potencial - skill_atual
    if diferenca > 0:
      ganho_skill = random.uniform(0.5, 3.0) * taxa_crescimento
      # Reduz ganho conforme se aproxima do potencial
      ganho_skill *= min(1.0, diferenca / 30)
    else:
      # Já atingiu o potencial, crescimento mínimo ou nulo
      ganho_skill = random.uniform(-0.5, 0.5)

  piloto["skill"] = round(min(100, max(20, piloto["skill"] + ganho_skill)), 1)


# ============================================================
# PROMOÇÃO
# ============================================================

def promover_piloto(piloto, proxima_categoria_id, ano_atual=None):
  """
  Promove um piloto para a próxima categoria.

  Args:
    piloto: dados do piloto
    proxima_categoria_id: ID da nova categoria
    ano_atual: ano atual (para registrar no histórico de equipes)
  """
  cat_anterior = piloto.get("categoria_atual", "")
  piloto["categoria_atual"] = proxima_categoria_id
  piloto["temporadas_na_categoria"] = 0
  piloto["corridas_na_categoria"] = 0

  # Registrar saída da equipe no histórico antes de limpar
  if piloto.get("equipe_id") and ano_atual:
    atualizar_historico_equipe(
      piloto,
      nova_equipe_id=None,
      nova_equipe_nome=None,
      categoria=proxima_categoria_id,
      ano=ano_atual,
      papel=None,
    )

  piloto["equipe_id"] = None
  piloto["equipe_nome"] = None
  piloto["papel"] = None
  piloto["relacao_companheiro"] = 0
  piloto["contrato_anos"] = random.randint(1, 2)

  # Bônus de skill por promoção
  evoluir_piloto(piloto, random.uniform(1.5, 4.0))

  logger.info("%s: %s -> %s", piloto.get('nome', '???'), cat_anterior, proxima_categoria_id)


# ============================================================
# APOSENTADORIA
# ============================================================

def aposentar_piloto(banco, piloto, ano_atual):
  """
  Aposenta um piloto, movendo-o para a lista de aposentados.

  Args:
    banco: banco de dados
    piloto: dados do piloto
    ano_atual: ano da aposentadoria

  Returns:
    bool: True se aposentou com sucesso
  """
  # Marcar como aposentado (ambos os campos para compatibilidade)
  piloto["aposentado"] = True
  piloto["status"] = "aposentado"

  # Adiciona aos aposentados
  if "aposentados" not in banco:
    banco["aposentados"] = []

  registro = {
    "id": piloto.get("id"),
    "nome": piloto["nome"],
    "ano_aposentadoria": ano_atual,
    "idade": piloto["idade"],
    "skill_final": piloto.get("skill", 0),
    "titulos": piloto.get("titulos", 0),
    "vitorias": piloto.get("vitorias_carreira", 0),
    "podios": piloto.get("podios_carreira", 0),
    "poles": piloto.get("poles_carreira", 0),
    "voltas_rapidas": piloto.get("voltas_rapidas_carreira", 0),
    "corridas": piloto.get("corridas_carreira", 0),
    "pontos": piloto.get("pontos_carreira", 0),
    "categoria_final": piloto.get("categoria_atual", ""),
    "ultima_equipe": piloto.get("equipe_nome", "Sem equipe"),
    "historico": piloto.get("historico_temporadas", []),
  }
  banco["aposentados"].append(registro)

  # Limpar vinculo com equipe ANTES de remover da lista
  piloto["equipe_id"] = None
  piloto["equipe_nome"] = None

  # Remove da lista de pilotos ativos
  if piloto in banco["pilotos"]:
    banco["pilotos"].remove(piloto)

  logger.info("%s se aposentou aos %d anos", piloto.get('nome', '???'), piloto['idade'])

  return True


def verificar_aposentadorias(banco, ano_atual):
  """
  Verifica quais pilotos devem se aposentar neste ano.

  Critérios:
  - Idade > 42: aposentadoria quase certa
  - Idade > 38: chance crescente
  - Skill muito baixo + idade alta: maior chance

  Args:
    banco: banco de dados
    ano_atual: ano atual

  Returns:
    list: pilotos aposentados
  """
  aposentados = []

  # Cópia para iterar com segurança (remove durante loop)
  pilotos_ativos = [
    p for p in banco.get("pilotos", [])
    if not p.get("aposentado", False)
    and p.get("status", "ativo") != "aposentado"
    and not p.get("is_jogador", False)
  ]

  for piloto in pilotos_ativos:
    idade = piloto.get("idade", 20)
    skill = piloto.get("skill", 50)

    deve_aposentar = False

    if idade >= 42:
      deve_aposentar = True
    elif idade >= 38:
      chance = (idade - 37) * 0.2 # 20% a 80%
      if skill < 40:
        chance += 0.2
      deve_aposentar = random.random() < chance
    elif idade >= 36:
      chance = 0.05
      if skill < 35:
        chance = 0.3
      deve_aposentar = random.random() < chance

    if deve_aposentar:
      aposentar_piloto(banco, piloto, ano_atual)
      aposentados.append(piloto)

  return aposentados


# ============================================================
# TRANSFERÊNCIAS
# ============================================================

def transferir_pilotos_entre_equipes(banco, categoria_id):
  """
  Processa transferencias de pilotos entre equipes numa categoria.

  Logica:
  - Vagas abertas (aposentadorias) sao preenchidas primeiro
  - Pilotos com contrato expirado podem trocar de equipe
  - Jogador nao e transferido automaticamente
  - No fim, saneia distribuicao para evitar equipes superlotadas

  Args:
    banco: banco de dados
    categoria_id: identificador da categoria

  Returns:
    int: numero de ajustes/transferencias realizados
  """
  pilotos_cat = obter_pilotos_categoria(banco, categoria_id)

  equipes_cat = [
    eq for eq in banco.get("equipes", [])
    if eq.get("categoria") == categoria_id
  ]

  if not pilotos_cat or not equipes_cat:
    return 0

  transferencias = 0

  # 1. Preencher vagas abertas.
  transferencias += _preencher_vagas(
    banco, pilotos_cat, equipes_cat, categoria_id
  )

  # Atualiza snapshot apos possivel inclusao de pilotos novos/promovidos.
  pilotos_cat = obter_pilotos_categoria(banco, categoria_id)

  # 2. Transferencias por desempenho (chance aleatoria).
  transferencias += _transferencias_desempenho(
    banco, pilotos_cat, equipes_cat
  )

  # 3. Saneamento final da distribuicao (evita equipe com 3 pilotos).
  transferencias += sanear_distribuicao_pilotos_categoria(
    banco,
    categoria_id,
  )

  return transferencias


def sanear_distribuicao_pilotos_categoria(banco, categoria_id):
  """
  Garante distribuicao valida de pilotos por equipe numa categoria.

  Regras:
  - remove excedentes (equipes com > max_pilotos) mantendo os pilotos mais fortes
  - preenche vagas de equipes com menos pilotos
  - ajusta vinculos invalidos de equipe para pilotos da categoria

  Returns:
    int: quantidade de ajustes de vinculo realizados
  """
  pilotos_cat = obter_pilotos_categoria(banco, categoria_id)
  equipes_cat = [
    eq for eq in banco.get("equipes", [])
    if eq.get("categoria") == categoria_id
  ]
  if not equipes_cat:
    return 0

  equipe_ids_validos = {eq.get("id") for eq in equipes_cat}
  ajustes = 0

  # Pilotos com equipe invalida viram "sem equipe" para redistribuicao.
  pilotos_sem_equipe = []
  sem_equipe_ids = set()
  for piloto in pilotos_cat:
    equipe_id = piloto.get("equipe_id")
    if equipe_id and equipe_id not in equipe_ids_validos:
      piloto["equipe_id"] = None
      piloto["equipe_nome"] = None
      ajustes += 1
      equipe_id = None

    if not equipe_id:
      pid = piloto.get("id")
      if pid not in sem_equipe_ids:
        pilotos_sem_equipe.append(piloto)
        sem_equipe_ids.add(pid)

  def _prioridade_manter(p):
    return (
      1 if p.get("is_jogador", False) else 0,
      int(p.get("pontos_temporada", 0) or 0),
      int(p.get("skill", 0) or 0),
    )

  # Remove excedentes de equipes superlotadas.
  for equipe in equipes_cat:
    limite = int(equipe.get("max_pilotos", 2) or 2)
    if limite < 1:
      limite = 1

    pilotos_equipe = [
      p for p in pilotos_cat
      if p.get("equipe_id") == equipe.get("id")
    ]
    if len(pilotos_equipe) <= limite:
      continue

    pilotos_ordenados = sorted(
      pilotos_equipe,
      key=_prioridade_manter,
      reverse=True,
    )
    excedentes = pilotos_ordenados[limite:]

    for piloto in excedentes:
      piloto["equipe_id"] = None
      piloto["equipe_nome"] = None
      pid = piloto.get("id")
      if pid not in sem_equipe_ids:
        pilotos_sem_equipe.append(piloto)
        sem_equipe_ids.add(pid)
      ajustes += 1

  # Melhores sem equipe ocupam vagas primeiro.
  pilotos_sem_equipe.sort(
    key=lambda p: (
      int(p.get("skill", 0) or 0),
      int(p.get("pontos_temporada", 0) or 0),
    ),
    reverse=True,
  )

  for equipe in equipes_cat:
    limite = int(equipe.get("max_pilotos", 2) or 2)
    if limite < 1:
      limite = 1

    while True:
      pilotos_equipe = [
        p for p in pilotos_cat
        if p.get("equipe_id") == equipe.get("id")
      ]
      if len(pilotos_equipe) >= limite:
        break

      candidato = None
      if pilotos_sem_equipe:
        candidato = pilotos_sem_equipe.pop(0)
        sem_equipe_ids.discard(candidato.get("id"))
      else:
        candidato = _buscar_candidato(banco, categoria_id, equipe)
        if candidato is None:
          break
        if (
          candidato.get("categoria_atual") == categoria_id
          and candidato.get("status", "ativo") != "aposentado"
          and not candidato.get("aposentado", False)
          and candidato not in pilotos_cat
        ):
          pilotos_cat.append(candidato)

      candidato["categoria_atual"] = categoria_id
      candidato["equipe_id"] = equipe.get("id")
      candidato["equipe_nome"] = equipe.get("nome", "")
      candidato["relacao_companheiro"] = 0
      if int(candidato.get("contrato_anos", 0) or 0) <= 0:
        candidato["contrato_anos"] = random.randint(1, 2)
      ajustes += 1

  return ajustes

def _preencher_vagas(banco, pilotos_cat, equipes_cat, categoria_id):
  """
  Preenche vagas sem piloto (pós-aposentadoria).

  Args:
    banco: banco de dados
    pilotos_cat: pilotos da categoria
    equipes_cat: equipes da categoria
    categoria_id: ID da categoria

  Returns:
    int: número de vagas preenchidas
  """
  transferencias = 0

  for equipe in equipes_cat:
    max_pilotos = equipe.get("max_pilotos", 2)
    pilotos_equipe = [
      p for p in pilotos_cat
      if p.get("equipe_id") == equipe.get("id")
    ]

    vagas = max_pilotos - len(pilotos_equipe)

    for _ in range(vagas):
      candidato = _buscar_candidato(banco, categoria_id, equipe)
      if candidato:
        candidato["equipe_id"] = equipe["id"]
        candidato["equipe_nome"] = equipe.get("nome", "")
        candidato["categoria_atual"] = categoria_id
        candidato["contrato_anos"] = random.randint(1, 2)
        candidato["relacao_companheiro"] = 0
        transferencias += 1
        print(
          f"  [VAGA] {candidato.get('nome', '???')} "
          f"-> {equipe.get('nome', '???')}"
        )

  return transferencias


def _transferencias_desempenho(banco, pilotos_cat, equipes_cat):
  """
  Transferências baseadas em desempenho (probabilístico).

  Pilotos com contrato expirado podem trocar de equipe.
  Chance base de 15% por piloto elegível.

  Args:
    banco: banco de dados
    pilotos_cat: pilotos da categoria
    equipes_cat: equipes da categoria

  Returns:
    int: número de transferências
  """
  transferencias = 0

  equipes_ordenadas = sorted(
    equipes_cat,
    key=lambda e: e.get("pontos_temporada", 0),
    reverse=True
  )

  for piloto in pilotos_cat:
    # Jogador não transfere automaticamente
    if piloto.get("is_jogador", False):
      continue

    # Verificar contrato
    contrato = piloto.get("contrato_anos", 0)
    if contrato > 0:
      piloto["contrato_anos"] = contrato - 1
      if piloto["contrato_anos"] > 0:
        continue

    # Chance de transferência: 15%
    if random.random() > 0.15:
      continue

    equipe_atual_id = piloto.get("equipe_id")
    equipe_atual_nome = piloto.get("equipe_nome", "???")

    for equipe in equipes_ordenadas:
      if equipe["id"] == equipe_atual_id:
        continue

      pilotos_eq = [
        p for p in pilotos_cat
        if p.get("equipe_id") == equipe["id"]
      ]

      if len(pilotos_eq) < equipe.get("max_pilotos", 2):
        piloto["equipe_id"] = equipe["id"]
        piloto["equipe_nome"] = equipe.get("nome", "")
        piloto["contrato_anos"] = random.randint(1, 2)
        piloto["relacao_companheiro"] = 0
        transferencias += 1
        print(
          f"  [TRANSFER] {piloto.get('nome', '???')}: "
          f"{equipe_atual_nome} -> {equipe.get('nome', '???')}"
        )
        break

  return transferencias


def _buscar_candidato(banco, categoria_id, equipe):
  """
  Busca um candidato para preencher vaga numa equipe.

  Prioridade:
  1. Pilotos sem equipe na mesma categoria
  2. Promover melhor piloto da categoria inferior
  3. Gerar piloto substituto novo

  Args:
    banco: banco de dados
    categoria_id: ID da categoria
    equipe: dict da equipe com vaga

  Returns:
    dict ou None: piloto candidato
  """
  # 1. Pilotos sem equipe na mesma categoria
  sem_equipe = [
    p for p in banco.get("pilotos", [])
    if p.get("categoria_atual") == categoria_id
    and not p.get("equipe_id")
    and not p.get("aposentado", False)
    and p.get("status", "ativo") != "aposentado"
  ]

  if sem_equipe:
    return random.choice(sem_equipe)

  # 2. Promover da categoria inferior
  cat_inferior = _categoria_inferior(categoria_id)
  if cat_inferior:
    candidatos = [
      p for p in banco.get("pilotos", [])
      if p.get("categoria_atual") == cat_inferior
      and not p.get("aposentado", False)
      and p.get("status", "ativo") != "aposentado"
      and not p.get("is_jogador", False)
    ]
    if candidatos:
      candidatos.sort(
        key=lambda p: p.get("pontos_temporada", 0),
        reverse=True
      )
      melhor = candidatos[0]
      promover_piloto(melhor, categoria_id)
      return melhor

  # 3. Gerar piloto novo
  ano_atual = banco.get("ano_atual", 2024)
  novo = gerar_piloto_substituto(
    banco,
    equipe_id=equipe.get("id"),
    categoria_id=_categoria_mais_baixa(),
    ano_atual=ano_atual
  )
  return novo


def _categoria_inferior(categoria_id):
  """
  Retorna a categoria imediatamente abaixo.

  Usa a lista CATEGORIAS ordenada por nível para determinar
  a hierarquia.

  Args:
    categoria_id: ID da categoria atual

  Returns:
    str ou None: ID da categoria inferior
  """
  categorias_ordenadas = sorted(CATEGORIAS, key=lambda c: c["nivel"])

  for i, cat in enumerate(categorias_ordenadas):
    if cat["id"] == categoria_id and i > 0:
      return categorias_ordenadas[i - 1]["id"]

  return None


def _categoria_mais_baixa():
  """
  Retorna o ID da categoria de nível mais baixo.

  Returns:
    str: ID da categoria mais baixa
  """
  if not CATEGORIAS:
    return "mazda_rookie"

  categorias_ordenadas = sorted(CATEGORIAS, key=lambda c: c["nivel"])
  return categorias_ordenadas[0]["id"]


# ============================================================
# PROCESSAMENTO DE FIM DE TEMPORADA
# ============================================================

def processar_fim_temporada_pilotos(banco, ano_atual):
  """
  Processa todas as ações de fim de temporada para pilotos.

  Ordem:
  1. Salvar histórico da temporada
  2. Envelhecer pilotos
  3. Evoluir pilotos jovens
  4. Verificar aposentadorias
  5. Processar transferências
  6. Resetar stats de temporada

  Args:
    banco: banco de dados
    ano_atual: ano que acabou de terminar

  Returns:
    dict: resumo do processamento
  """
  resumo = {
    "aposentados": [],
    "promovidos": [],
    "substitutos": [],
    "transferencias": 0,
  }

  print(f"\n[SEASON] Processando fim de temporada {ano_atual} para pilotos...")

  # 1. Salvar histórico
  for piloto in banco.get("pilotos", []):
    if piloto.get("aposentado", False) or piloto.get("status") == "aposentado":
      continue

    historico = {
      "ano": ano_atual,
      "categoria": piloto.get("categoria_atual", ""),
      "equipe": piloto.get("equipe_nome", ""),
      "pontos": piloto.get("pontos_temporada", 0),
      "vitorias": piloto.get("vitorias_temporada", 0),
      "podios": piloto.get("podios_temporada", 0),
      "poles": piloto.get("poles_temporada", 0),
      "voltas_rapidas": piloto.get("voltas_rapidas_temporada", 0),
      "posicao_final": calcular_posicao_campeonato(
        banco, piloto, piloto.get("categoria_atual", "")
      ),
      "titulo": False, # será atualizado pelo sistema de campeonato
    }

    if "historico_temporadas" not in piloto:
      piloto["historico_temporadas"] = []
    piloto["historico_temporadas"].append(historico)

    # Decair rivalidades anualmente
    decair_rivalidades(piloto)

    # Calcular bônus de potencial
    equipe_atual = None
    if piloto.get("equipe_id"):
      equipe_atual = next(
        (eq for eq in banco.get("equipes", []) if eq.get("id") == piloto["equipe_id"]),
        None
      )
    bonus = calcular_bonus_potencial(
      piloto, equipe_atual, piloto.get("resultados_temporada", [])
    )
    if bonus > 0:
      piloto["potencial_bonus"] = piloto.get("potencial_bonus", 0) + bonus

  # 2. Envelhecer
  envelhecer_pilotos(banco)

  # 3. Evoluir jovens
  for piloto in banco.get("pilotos", []):
    if piloto.get("aposentado", False) or piloto.get("status") == "aposentado":
      continue
    if piloto.get("idade", 30) < 28:
      evoluir_piloto(piloto)

  # 4. Aposentadorias
  aposentados = verificar_aposentadorias(banco, ano_atual)
  resumo["aposentados"] = [p.get("nome", "???") for p in aposentados]

  # 5. Transferências por categoria
  for cat in sorted(CATEGORIAS, key=lambda c: c["nivel"], reverse=True):
    cat_id = cat["id"]
    t = transferir_pilotos_entre_equipes(banco, cat_id)
    resumo["transferencias"] += t

  # 6. Resetar stats de temporada
  for piloto in banco.get("pilotos", []):
    if not piloto.get("aposentado", False) and piloto.get("status", "ativo") != "aposentado":
      resetar_stats_temporada(piloto)

  logger.info("%d aposentadorias, %d transferencias", len(resumo['aposentados']), resumo['transferencias'])

  return resumo


# ============================================================
# LESÃO
# ============================================================

def aplicar_lesao(piloto, tipo):
  """
  Aplica uma lesão ao piloto.

  Tipos:
  - "leve": 2 corridas, modifier 0.95
  - "moderada": 4 corridas, modifier 0.88
  - "grave": 8 corridas, modifier 0.75
  """
  configs = {
    "leve":   {"corridas_restantes": 2, "modifier": 0.95},
    "moderada": {"corridas_restantes": 4, "modifier": 0.88},
    "grave":  {"corridas_restantes": 8, "modifier": 0.75},
  }

  config = configs.get(tipo, configs["leve"])

  piloto["lesao"] = {
    "tipo": tipo,
    "corridas_restantes": config["corridas_restantes"],
    "modifier": config["modifier"],
  }

  piloto["status"] = "lesionado"


def atualizar_lesao(piloto):
  """
  Reduz contador de lesão após cada corrida.
  Remove lesão quando chegar a 0.
  """
  if not piloto.get("lesao"):
    return

  piloto["lesao"]["corridas_restantes"] -= 1

  # Recuperação gradual
  if piloto["lesao"]["corridas_restantes"] <= 2:
    piloto["lesao"]["modifier"] = min(1.0, piloto["lesao"]["modifier"] + 0.03)

  if piloto["lesao"]["corridas_restantes"] <= 0:
    piloto["lesao"] = None
    piloto["status"] = "ativo"


# ============================================================
# RIVALIDADES
# ============================================================

def adicionar_rivalidade(piloto, rival_id, motivo, intensidade_inicial=3):
  """
  Adiciona ou intensifica uma rivalidade.
  """
  if "rivalidades" not in piloto:
    piloto["rivalidades"] = []

  # Verificar se já existe
  for riv in piloto["rivalidades"]:
    if riv["rival_id"] == rival_id:
      # Intensificar
      riv["intensidade"] = min(10, riv["intensidade"] + 2)
      riv["motivo"] = motivo # Atualiza motivo
      return

  # Nova rivalidade
  piloto["rivalidades"].append({
    "rival_id": rival_id,
    "intensidade": intensidade_inicial,
    "motivo": motivo,
  })

  # Limite de 5 rivalidades ativas
  if len(piloto["rivalidades"]) > 5:
    # Remove a mais fraca
    piloto["rivalidades"].sort(key=lambda r: r["intensidade"], reverse=True)
    piloto["rivalidades"] = piloto["rivalidades"][:5]


def decair_rivalidades(piloto):
  """
  Reduz intensidade das rivalidades ao fim da temporada.
  Remove as que chegaram a 0.
  """
  if "rivalidades" not in piloto:
    return

  for riv in piloto["rivalidades"]:
    riv["intensidade"] = max(0, riv["intensidade"] - 1)

  # Remover as que zeraram
  piloto["rivalidades"] = [r for r in piloto["rivalidades"] if r["intensidade"] > 0]


# ============================================================
# HISTÓRICO DE CIRCUITOS
# ============================================================

def atualizar_historico_circuito(piloto, circuito_id, posicao, pole=False, dnf=False):
  """
  Atualiza o histórico do piloto em um circuito específico.
  Chamado após cada corrida.
  """
  if "historico_circuitos" not in piloto:
    piloto["historico_circuitos"] = {}

  if circuito_id not in piloto["historico_circuitos"]:
    piloto["historico_circuitos"][circuito_id] = {
      "corridas": 0,
      "vitorias": 0,
      "podios": 0,
      "poles": 0,
      "dnfs": 0,
      "melhor_resultado": 99,
      "afinidade": 50, # Começa neutro
    }

  hist = piloto["historico_circuitos"][circuito_id]
  hist["corridas"] += 1

  if dnf:
    hist["dnfs"] += 1
    # Afinidade cai levemente com DNF
    hist["afinidade"] = max(20, hist["afinidade"] - 2)
  else:
    hist["melhor_resultado"] = min(hist["melhor_resultado"], posicao)

    if posicao == 1:
      hist["vitorias"] += 1
      hist["afinidade"] = min(100, hist["afinidade"] + 5)

    if posicao <= 3:
      hist["podios"] += 1
      hist["afinidade"] = min(100, hist["afinidade"] + 3)
    elif posicao <= 5:
      hist["afinidade"] = min(100, hist["afinidade"] + 1)
    elif posicao > 15:
      hist["afinidade"] = max(20, hist["afinidade"] - 1)

    if pole:
      hist["poles"] += 1
      hist["afinidade"] = min(100, hist["afinidade"] + 2)


# ============================================================
# HISTÓRICO DE EQUIPES
# ============================================================

def atualizar_historico_equipe(piloto, nova_equipe_id, nova_equipe_nome,
                categoria, ano, papel):
  """
  Registra mudança de equipe no histórico.
  Chamado quando piloto troca de equipe.
  """
  if "historico_equipes" not in piloto:
    piloto["historico_equipes"] = []

  # Fechar registro anterior (se existir)
  for hist in piloto["historico_equipes"]:
    if hist.get("ano_fim") is None:
      hist["ano_fim"] = ano

  # Novo registro
  piloto["historico_equipes"].append({
    "equipe_id": nova_equipe_id,
    "equipe_nome": nova_equipe_nome,
    "categoria": categoria,
    "ano_inicio": ano,
    "ano_fim": None,
    "papel": papel,
  })

