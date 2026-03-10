"""
Modulo 9: Sistema de Hierarquia N1/N2.

Gerencia:
- Definicao de hierarquia
- Avaliacao continua
- Tensao entre pilotos
- Reavaliacao e inversao
- Ordens de equipe (somente corridas simuladas)
- Impactos no mercado e visibilidade
"""

from .avaliacao import (
    avaliar_desempenho_temporada,
    calcular_diferenca_media,
    comparar_resultado_corrida,
    definir_hierarquia_inicial,
    piloto_superando_companheiro,
)
from .hierarquia_manager import (
    HierarquiaManager,
    criar_manager_para_temporada,
    integrar_com_mercado,
    integrar_com_simulacao,
    processar_corrida_todas_equipes,
)
from .impactos import (
    IMPACTOS_NUMERO_1,
    IMPACTOS_NUMERO_2,
    aplicar_modificador_propostas,
    aplicar_modificador_visibilidade,
    calcular_impactos,
    calcular_prioridade_upgrade,
    modificar_duracao_contrato,
    verificar_chance_substituicao,
)
from .models import (
    ComparacaoResultado,
    EstadoHierarquia,
    HistoricoHierarquia,
    ImpactoHierarquia,
    MotivoHierarquia,
    OrdemEquipe,
    Papel,
    RelatorioHierarquiaTemporada,
    RespostaOrdem,
    StatusTensao,
    TipoOrdem,
)
from .ordens_equipe import (
    aplicar_ordem_no_resultado,
    calcular_posicoes_perdidas,
    gerar_ordem_equipe,
    processar_resposta_ordem,
    simular_ordens_corrida,
    verificar_necessidade_ordem,
)
from .reavaliacao import (
    CORRIDAS_PARA_INVERSAO,
    CORRIDAS_PARA_REAVALIACAO,
    PERCENTUAL_MINIMO_INVERSAO,
    aplicar_impacto_inversao,
    calcular_impacto_inversao,
    deve_inverter_hierarquia,
    deve_reavaliar_hierarquia,
    executar_inversao,
)
from .tensao import (
    THRESHOLD_CRISE,
    THRESHOLD_INVERSAO,
    THRESHOLD_REAVALIACAO,
    THRESHOLD_TENSAO,
    atualizar_tensao_pos_corrida,
    calcular_chance_desobediencia,
    calcular_tensao_inicial,
    determinar_status_tensao,
    deve_emitir_ordem,
    tensao_afeta_moral_equipe,
)

__all__ = [
    "Papel",
    "StatusTensao",
    "TipoOrdem",
    "RespostaOrdem",
    "MotivoHierarquia",
    "ComparacaoResultado",
    "HistoricoHierarquia",
    "OrdemEquipe",
    "EstadoHierarquia",
    "ImpactoHierarquia",
    "RelatorioHierarquiaTemporada",
    "comparar_resultado_corrida",
    "definir_hierarquia_inicial",
    "avaliar_desempenho_temporada",
    "calcular_diferenca_media",
    "piloto_superando_companheiro",
    "calcular_tensao_inicial",
    "atualizar_tensao_pos_corrida",
    "determinar_status_tensao",
    "tensao_afeta_moral_equipe",
    "deve_emitir_ordem",
    "calcular_chance_desobediencia",
    "THRESHOLD_TENSAO",
    "THRESHOLD_REAVALIACAO",
    "THRESHOLD_INVERSAO",
    "THRESHOLD_CRISE",
    "deve_reavaliar_hierarquia",
    "deve_inverter_hierarquia",
    "executar_inversao",
    "calcular_impacto_inversao",
    "aplicar_impacto_inversao",
    "CORRIDAS_PARA_REAVALIACAO",
    "CORRIDAS_PARA_INVERSAO",
    "PERCENTUAL_MINIMO_INVERSAO",
    "calcular_impactos",
    "aplicar_modificador_visibilidade",
    "aplicar_modificador_propostas",
    "modificar_duracao_contrato",
    "verificar_chance_substituicao",
    "calcular_prioridade_upgrade",
    "IMPACTOS_NUMERO_1",
    "IMPACTOS_NUMERO_2",
    "gerar_ordem_equipe",
    "processar_resposta_ordem",
    "calcular_posicoes_perdidas",
    "aplicar_ordem_no_resultado",
    "verificar_necessidade_ordem",
    "simular_ordens_corrida",
    "HierarquiaManager",
    "criar_manager_para_temporada",
    "processar_corrida_todas_equipes",
    "integrar_com_mercado",
    "integrar_com_simulacao",
]
