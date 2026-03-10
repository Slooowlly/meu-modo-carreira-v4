"""Integration helpers for contract clauses on relegation."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple

from Logica.mercado.models import Contrato, StatusContrato, TipoClausula


def _to_contrato(item: Any) -> Contrato | None:
    if isinstance(item, Contrato):
        return item
    if isinstance(item, dict):
        try:
            return Contrato.from_dict(item)
        except Exception:
            return None
    return None


def _index_equipes(banco: dict) -> Dict[str, dict]:
    index: Dict[str, dict] = {}
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        index[str(equipe.get("id", ""))] = equipe
    return index


def _index_pilotos(banco: dict) -> Dict[str, dict]:
    index: Dict[str, dict] = {}
    for piloto in banco.get("pilotos", []):
        if not isinstance(piloto, dict):
            continue
        index[str(piloto.get("id", ""))] = piloto
    return index


def pilotos_com_clausula_rebaixamento(
    contratos_ativos: Iterable[Any],
    equipes_rebaixadas: Set[str],
) -> List[Tuple[str, str, Contrato]]:
    encontrados: List[Tuple[str, str, Contrato]] = []
    equipes_ids = {str(eid) for eid in equipes_rebaixadas}

    for item in contratos_ativos:
        contrato = _to_contrato(item)
        if contrato is None:
            continue
        if contrato.status != StatusContrato.ATIVO:
            continue
        if str(contrato.equipe_id) not in equipes_ids:
            continue
        if not contrato.tem_clausula(TipoClausula.SAIDA_REBAIXAMENTO):
            continue
        encontrados.append((str(contrato.piloto_id), str(contrato.equipe_id), contrato))

    return encontrados


def liberar_pilotos_por_rebaixamento(
    banco: dict,
    equipes_rebaixadas: Iterable[str],
    motivo: str = "clausula_rebaixamento",
) -> List[str]:
    _ = motivo

    equipes_set = {str(eid) for eid in equipes_rebaixadas}
    if not equipes_set:
        return []

    mercado = banco.setdefault("mercado", {})
    contratos_raw = mercado.get("contratos_ativos", [])
    if not isinstance(contratos_raw, list):
        contratos_raw = []
        mercado["contratos_ativos"] = contratos_raw

    alvos = pilotos_com_clausula_rebaixamento(contratos_raw, equipes_set)
    if not alvos:
        return []

    pilotos_index = _index_pilotos(banco)
    equipes_index = _index_equipes(banco)
    liberados: List[str] = []

    for piloto_id, equipe_id, contrato in alvos:
        piloto = pilotos_index.get(str(piloto_id))
        if not piloto:
            continue

        equipe = equipes_index.get(str(equipe_id))
        if equipe:
            equipe["pilotos"] = [pid for pid in equipe.get("pilotos", []) if str(pid) != str(piloto_id)]
            if str(equipe.get("piloto_numero_1")) == str(piloto_id):
                equipe["piloto_numero_1"] = None
                equipe["piloto_1"] = None
            if str(equipe.get("piloto_numero_2")) == str(piloto_id):
                equipe["piloto_numero_2"] = None
                equipe["piloto_2"] = None

        piloto["equipe_id"] = None
        piloto["equipe_nome"] = None
        piloto["papel"] = None
        piloto["contrato_anos"] = 0

        if str(piloto.get("status", "ativo")).strip().lower() != "lesionado":
            piloto["status"] = "livre"

        contrato.status = StatusContrato.RESCINDIDO
        liberados.append(str(piloto_id))

    # Remove rescindidos da lista ativa e preserva demais contratos/clausulas.
    novos_contratos: List[dict] = []
    for item in contratos_raw:
        contrato = _to_contrato(item)
        if contrato is None:
            continue
        if contrato.status == StatusContrato.RESCINDIDO:
            continue
        novos_contratos.append(contrato.to_dict())

    mercado["contratos_ativos"] = novos_contratos

    return liberados
