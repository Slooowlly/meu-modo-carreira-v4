"""
Impactos de ser numero 1 ou numero 2.
"""

from __future__ import annotations

from typing import Any, Tuple

from .models import ImpactoHierarquia, Papel


IMPACTOS_NUMERO_1 = {
    "visibilidade_mod": +2.0,
    "propostas_mod": +15.0,
    "duracao_contrato_mod": +1,
    "prioridade_upgrade": 1,
    "chance_ser_trocado": 0.05,
    "descricao": "Piloto principal da equipe",
}

IMPACTOS_NUMERO_2 = {
    "visibilidade_mod": -2.0,
    "propostas_mod": -10.0,
    "duracao_contrato_mod": 0,
    "prioridade_upgrade": 2,
    "chance_ser_trocado": 0.25,
    "descricao": "Segundo piloto da equipe",
}


def _get(entidade: Any, campo: str, default=None):
    if isinstance(entidade, dict):
        return entidade.get(campo, default)
    return getattr(entidade, campo, default)


def calcular_impactos(papel: Papel) -> ImpactoHierarquia:
    """
    Calcula impactos baseados no papel.
    """
    if papel == Papel.NUMERO_1:
        config = IMPACTOS_NUMERO_1
    elif papel == Papel.NUMERO_2:
        config = IMPACTOS_NUMERO_2
    else:
        return ImpactoHierarquia(papel=papel, descricao="Papel ainda nao definido")

    return ImpactoHierarquia(
        papel=papel,
        visibilidade_mod=float(config["visibilidade_mod"]),
        propostas_mod=float(config["propostas_mod"]),
        duracao_contrato_mod=int(config["duracao_contrato_mod"]),
        prioridade_upgrade=int(config["prioridade_upgrade"]),
        chance_ser_trocado=float(config["chance_ser_trocado"]),
        descricao=str(config["descricao"]),
    )


def aplicar_modificador_visibilidade(visibilidade_base: float, papel: Papel) -> float:
    """
    Aplica modificador de visibilidade.
    """
    impactos = calcular_impactos(papel)
    nova = float(visibilidade_base) + impactos.visibilidade_mod
    return max(0.0, min(10.0, nova))


def aplicar_modificador_propostas(atratividade_proposta: float, papel: Papel) -> float:
    """
    Aplica modificador na atratividade das propostas.
    """
    impactos = calcular_impactos(papel)
    modificador = 1.0 + (impactos.propostas_mod / 100.0)
    return float(atratividade_proposta) * modificador


def modificar_duracao_contrato(duracao_base: int, papel: Papel) -> int:
    """
    Modifica duracao de contrato oferecido (limite 1-2 anos).
    """
    impactos = calcular_impactos(papel)
    nova = int(duracao_base) + impactos.duracao_contrato_mod
    return max(1, min(2, nova))


def verificar_chance_substituicao(
    piloto: Any,
    papel: Papel,
    rookie_disponivel: bool,
    desempenho_temporada: float,
) -> Tuple[bool, str]:
    """
    Verifica se piloto corre risco de ser substituido.
    """
    if not rookie_disponivel:
        return False, ""

    _ = calcular_impactos(papel)

    if papel == Papel.NUMERO_1 and desempenho_temporada >= 60.0:
        return False, ""

    if papel == Papel.NUMERO_2 and desempenho_temporada < 50.0:
        return True, "Desempenho abaixo do esperado como N2"

    idade = int(_get(piloto, "idade", _get(piloto, "age", 25)) or 25)
    if papel == Papel.NUMERO_2 and idade > 32:
        return True, "Veterano na posicao de N2"

    if papel == Papel.NUMERO_2 and desempenho_temporada < 60.0 and idade > 28:
        return True, "Custo-beneficio desfavoravel"

    return False, ""


def calcular_prioridade_upgrade(
    piloto_1_id: str,
    piloto_2_id: str,
    piloto_solicitante_id: str,
) -> int:
    """
    Retorna prioridade para upgrade de carro.
    """
    if str(piloto_solicitante_id) == str(piloto_1_id):
        return 1
    if str(piloto_solicitante_id) == str(piloto_2_id):
        return 2
    return 3
