"""
Orquestrador principal do mercado de transferencias.

Integra o modulo 7 ao schema atual (dicts do projeto).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from Dados.banco import obter_proximo_id
from Logica.pilotos import criar_piloto

from .contratos import criar_contrato
from .decisoes_equipe import decidir_renovacao
from .decisoes_piloto import piloto_decide_propostas
from .janela_transferencias import (
    mapear_categoria_para_atual,
    mapear_categoria_para_expandida,
)
from .models import (
    Contrato,
    EstadoMercadoPersistido,
    MotivoRecusa,
    PapelEquipe,
    PilotoMercado,
    Proposta,
    ResultadoMercado,
    StatusPiloto,
    StatusProposta,
    VagaAberta,
)
from .propostas import gerar_propostas_para_piloto
from .rookies import RookieGerado, gerar_rookies_temporada
from .visibilidade import calcular_visibilidade


MERCADO_VERSAO = 1
CHAVE_MERCADO = "mercado"
STATUS_INATIVOS = {"aposentado", "reserva_global", "reserva", "livre"}


def _get(entity: Any, campo: str, default=None):
    if isinstance(entity, dict):
        return entity.get(campo, default)
    return getattr(entity, campo, default)


def _int(valor: Any, default: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def _float(valor: Any, default: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return default


def _papel_from_str(valor: Any, default: PapelEquipe = PapelEquipe.NUMERO_2) -> PapelEquipe:
    texto = str(valor or "").strip().lower()
    if texto in {PapelEquipe.NUMERO_1.value, "n1"}:
        return PapelEquipe.NUMERO_1
    if texto in {PapelEquipe.NUMERO_2.value, "n2"}:
        return PapelEquipe.NUMERO_2
    if texto == PapelEquipe.RESERVA.value:
        return PapelEquipe.RESERVA
    return default


def _papel_to_str(papel: PapelEquipe) -> str:
    if isinstance(papel, PapelEquipe):
        return papel.value
    return str(papel or PapelEquipe.NUMERO_2.value)


def _status_piloto_normalizado(piloto: dict[str, Any]) -> str:
    status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
    if piloto.get("aposentado", False):
        return "aposentado"
    if status in {"reserva", "desempregado"}:
        return "reserva_global"
    if status in {"lesionado", "aposentado", "reserva_global", "livre"}:
        return status
    if piloto.get("equipe_id") in (None, ""):
        return "livre"
    return "ativo"


class MercadoManager:
    """Gerenciador principal do mercado de transferencias."""

    def __init__(self, banco: dict[str, Any]):
        self.banco = banco
        self.garantir_estrutura_mercado_no_banco(self.banco)

    # ============================================================
    # Estrutura/Persistencia
    # ============================================================

    @staticmethod
    def estrutura_mercado_padrao() -> dict[str, Any]:
        base = EstadoMercadoPersistido(versao=MERCADO_VERSAO).to_dict()
        base["resultado_janela_atual"] = {}
        base["ultima_temporada_decrementada"] = 0
        base["fechamento_temporada"] = {
            "em_andamento": False,
            "ano_base": 0,
            "aposentados": [],
            "total_aposentadorias": 0,
            "simulacao_ai_concluida": False,
            "evolucao_processada": False,
            "promocao_processada": False,
            "relatorio_promocao": {},
            "validacao_pos_mercado": {},
        }
        return base

    @classmethod
    def garantir_estrutura_mercado_no_banco(cls, banco: dict[str, Any]) -> dict[str, Any]:
        atual = banco.get(CHAVE_MERCADO)
        if not isinstance(atual, dict):
            banco[CHAVE_MERCADO] = cls.estrutura_mercado_padrao()
            return banco[CHAVE_MERCADO]

        padrao = cls.estrutura_mercado_padrao()
        for chave, valor_padrao in padrao.items():
            if chave not in atual:
                atual[chave] = valor_padrao

        if not isinstance(atual.get("contratos_ativos"), list):
            atual["contratos_ativos"] = []
        if not isinstance(atual.get("historico_janelas"), list):
            atual["historico_janelas"] = []
        if not isinstance(atual.get("propostas_atuais"), list):
            atual["propostas_atuais"] = []
        if not isinstance(atual.get("vagas_abertas"), list):
            atual["vagas_abertas"] = []
        if not isinstance(atual.get("reserva_global"), list):
            atual["reserva_global"] = []
        if not isinstance(atual.get("rookies_gerados"), list):
            atual["rookies_gerados"] = []
        if not isinstance(atual.get("pendencias_jogador"), list):
            atual["pendencias_jogador"] = []
        if not isinstance(atual.get("resultado_janela_atual"), dict):
            atual["resultado_janela_atual"] = {}
        if not isinstance(atual.get("fechamento_temporada"), dict):
            atual["fechamento_temporada"] = {
                "em_andamento": False,
                "ano_base": 0,
                "aposentados": [],
                "total_aposentadorias": 0,
                "simulacao_ai_concluida": False,
                "evolucao_processada": False,
                "promocao_processada": False,
                "relatorio_promocao": {},
                "validacao_pos_mercado": {},
            }
        else:
            fechamento = atual["fechamento_temporada"]
            if "em_andamento" not in fechamento:
                fechamento["em_andamento"] = False
            if "ano_base" not in fechamento:
                fechamento["ano_base"] = 0
            if "aposentados" not in fechamento or not isinstance(fechamento.get("aposentados"), list):
                fechamento["aposentados"] = []
            if "total_aposentadorias" not in fechamento:
                fechamento["total_aposentadorias"] = 0
            if "simulacao_ai_concluida" not in fechamento:
                fechamento["simulacao_ai_concluida"] = False
            if "evolucao_processada" not in fechamento:
                fechamento["evolucao_processada"] = False
            if "promocao_processada" not in fechamento:
                fechamento["promocao_processada"] = False
            if "relatorio_promocao" not in fechamento or not isinstance(fechamento.get("relatorio_promocao"), dict):
                fechamento["relatorio_promocao"] = {}
            if "validacao_pos_mercado" not in fechamento or not isinstance(fechamento.get("validacao_pos_mercado"), dict):
                fechamento["validacao_pos_mercado"] = {}
        atual["versao"] = max(_int(atual.get("versao", MERCADO_VERSAO), MERCADO_VERSAO), MERCADO_VERSAO)
        return atual

    def _estado_persistido(self) -> EstadoMercadoPersistido:
        dados = self.garantir_estrutura_mercado_no_banco(self.banco)
        return EstadoMercadoPersistido.from_dict(dados)

    def _salvar_estado_persistido(self, estado: EstadoMercadoPersistido):
        payload = estado.to_dict()
        atual = self.garantir_estrutura_mercado_no_banco(self.banco)
        for chave, valor in payload.items():
            atual[chave] = valor

    # ============================================================
    # API publica
    # ============================================================

    def processar_janela_transferencias(
        self,
        temporada: Optional[int] = None,
        jogador_id: Optional[Any] = None,
        aposentadorias_temporada: Optional[int] = None,
    ) -> ResultadoMercado:
        temporada_ref = _int(temporada, _int(self.banco.get("temporada_atual", 1), 1))
        jogador = self._obter_jogador()
        jogador_id_str = str(jogador_id if jogador_id is not None else _get(jogador, "id", ""))

        estado = self._estado_persistido()
        mercado_raw = self.garantir_estrutura_mercado_no_banco(self.banco)

        if estado.janela_aberta and estado.temporada_janela == temporada_ref:
            payload = mercado_raw.get("resultado_janela_atual")
            if isinstance(payload, dict) and payload:
                return ResultadoMercado.from_dict(payload)

        self._decrementar_contratos_temporada(temporada_ref)
        self._sincronizar_equipes_e_papeis()

        resultado = ResultadoMercado(temporada=temporada_ref)
        equipes_index = self._index_equipes()
        pilotos_index = self._index_pilotos()

        rankings = self._mapa_resultado_temporada()

        vagas = self._processar_renovacoes(
            temporada=temporada_ref,
            equipes_index=equipes_index,
            pilotos_index=pilotos_index,
            rankings=rankings,
            resultado=resultado,
            jogador_id_str=jogador_id_str,
        )

        # Vagas restantes apos renovacoes e aposentadorias.
        vagas.extend(self._gerar_vagas_abertas(equipes_index, pilotos_index))
        vagas = self._deduplicar_vagas(vagas)

        pilotos_livres = self._pilotos_livres_para_mercado(pilotos_index, rankings)

        propostas_geradas: list[Proposta] = []
        pendencias_jogador: list[Proposta] = []
        reserva_global_ids: set[str] = set(str(pid) for pid in estado.reserva_global)
        vagas_disponiveis = list(vagas)

        # Processa melhores pilotos primeiro.
        pilotos_livres.sort(key=lambda p: (p.skill, p.visibilidade), reverse=True)

        for piloto in pilotos_livres:
            propostas = gerar_propostas_para_piloto(
                piloto=piloto,
                vagas=vagas_disponiveis,
                equipes=equipes_index,
            )
            for proposta in propostas:
                proposta.salario_anual = self._normalizar_salario_escala_jogo(proposta.salario_anual)
            propostas_geradas.extend(propostas)

            if not propostas:
                self._enviar_para_reserva_global(pilotos_index.get(str(piloto.id)), reserva_global_ids)
                resultado.pilotos_sem_vaga.append(str(piloto.id))
                continue

            if jogador_id_str and str(piloto.id) == jogador_id_str:
                pendencias_jogador.extend(propostas)
                for proposta in propostas:
                    vagas_disponiveis = self._consumir_vaga(vagas_disponiveis, proposta)
                continue

            decisao = piloto_decide_propostas(piloto, propostas)
            if decisao.proposta_aceita:
                proposta_aceita = decisao.proposta_aceita
                self._aplicar_proposta_aceita(
                    proposta_aceita,
                    temporada_ref,
                    equipes_index,
                    pilotos_index,
                    resultado,
                )
                vagas_disponiveis = self._consumir_vaga(vagas_disponiveis, proposta_aceita)
            else:
                self._enviar_para_reserva_global(pilotos_index.get(str(piloto.id)), reserva_global_ids)
                resultado.pilotos_sem_vaga.append(str(piloto.id))

        quantidade_rookies = self._calcular_num_rookies(aposentadorias_temporada)
        rookies_ids = self._gerar_e_inserir_rookies(
            temporada_ref,
            vagas_disponiveis,
            equipes_index,
            pilotos_index,
            reserva_global_ids,
            resultado,
            quantidade=quantidade_rookies,
        )

        vagas_disponiveis = self._fase_sobras_preenchimento_forcado(
            temporada=temporada_ref,
            equipes_index=equipes_index,
            pilotos_index=pilotos_index,
            reserva_global_ids=reserva_global_ids,
            resultado=resultado,
        )

        self._sincronizar_equipes_e_papeis()
        contratos_ativos = self._reconstruir_contratos_ativos(temporada_ref)

        estado.contratos_ativos = contratos_ativos
        estado.propostas_atuais = propostas_geradas
        estado.pendencias_jogador = pendencias_jogador
        estado.vagas_abertas = vagas_disponiveis
        estado.rookies_gerados = rookies_ids
        estado.reserva_global = sorted(reserva_global_ids)
        estado.janela_aberta = True
        estado.temporada_janela = temporada_ref

        resultado.total_propostas = len(propostas_geradas)
        resultado.propostas_aceitas = sum(1 for p in propostas_geradas if p.status == StatusProposta.ACEITA)
        resultado.propostas_recusadas = sum(1 for p in propostas_geradas if p.status == StatusProposta.RECUSADA)
        resultado.vagas_nao_preenchidas = len(vagas_disponiveis)
        resultado.vagas_preenchidas = max(0, len(vagas) - resultado.vagas_nao_preenchidas)
        resultado.rookies_gerados = list(rookies_ids)

        if pendencias_jogador:
            resultado.adicionar_destaque("Jogador recebeu propostas e precisa decidir no Mercado.")
        if rookies_ids:
            resultado.adicionar_destaque(f"{len(rookies_ids)} rookies entraram no mercado.")

        self._salvar_estado_persistido(estado)
        mercado_raw["resultado_janela_atual"] = resultado.to_dict()
        mercado_raw["reserva_global"] = sorted(reserva_global_ids)
        return resultado

    def obter_pendencias_jogador(self, jogador_id: Optional[Any] = None) -> list[Proposta]:
        estado = self._estado_persistido()
        jid = str(jogador_id if jogador_id is not None else _get(self._obter_jogador(), "id", ""))
        if not jid:
            return []
        return [p for p in estado.pendencias_jogador if str(p.piloto_id) == jid and p.status == StatusProposta.PENDENTE]

    def aplicar_decisao_jogador(
        self,
        acao: str,
        proposta_id: Optional[str] = None,
        jogador_id: Optional[Any] = None,
    ) -> dict[str, Any]:
        estado = self._estado_persistido()
        mercado_raw = self.garantir_estrutura_mercado_no_banco(self.banco)
        jid = str(jogador_id if jogador_id is not None else _get(self._obter_jogador(), "id", ""))
        if not jid:
            return {"ok": False, "erro": "Jogador não encontrado."}

        pendencias = [p for p in estado.pendencias_jogador if str(p.piloto_id) == jid and p.status == StatusProposta.PENDENTE]
        if not pendencias:
            return {"ok": False, "erro": "Nenhuma pendência do jogador."}

        equipes_index = self._index_equipes()
        pilotos_index = self._index_pilotos()
        temporada_ref = _int(estado.temporada_janela or self.banco.get("temporada_atual", 1), 1)

        if acao == "aceitar":
            alvo = next((p for p in pendencias if str(p.id) == str(proposta_id)), None)
            if alvo is None:
                return {"ok": False, "erro": "Proposta inválida para aceite."}
            alvo.status = StatusProposta.ACEITA
            self._aplicar_proposta_aceita(alvo, temporada_ref, equipes_index, pilotos_index, None)
            estado.reserva_global = [pid for pid in estado.reserva_global if str(pid) != jid]
            for proposta in pendencias:
                if proposta.id == alvo.id:
                    continue
                proposta.status = StatusProposta.RECUSADA
                proposta.motivo_recusa = MotivoRecusa.PREFERE_OUTRA
            motivo = f"Proposta aceita: {alvo.equipe_nome}"
        elif acao == "recusar":
            alvo = next((p for p in pendencias if str(p.id) == str(proposta_id)), None)
            if alvo is None:
                return {"ok": False, "erro": "Proposta inválida para recusa."}
            alvo.status = StatusProposta.RECUSADA
            alvo.motivo_recusa = MotivoRecusa.PREFERE_OUTRA
            pendencias = [p for p in pendencias if p.status == StatusProposta.PENDENTE]
            if not pendencias:
                reserva_ids = set(estado.reserva_global)
                self._enviar_para_reserva_global(pilotos_index.get(jid), reserva_ids)
                estado.reserva_global = sorted(reserva_ids)
                motivo = "Jogador recusou todas as propostas e virou reserva global."
            else:
                motivo = "Proposta recusada."
        elif acao == "recusar_todas":
            for proposta in pendencias:
                proposta.status = StatusProposta.RECUSADA
                proposta.motivo_recusa = MotivoRecusa.PREFERE_OUTRA
            reserva_ids = set(estado.reserva_global)
            self._enviar_para_reserva_global(pilotos_index.get(jid), reserva_ids)
            estado.reserva_global = sorted(reserva_ids)
            motivo = "Jogador recusou todas e virou reserva global."
        else:
            return {"ok": False, "erro": "Ação inválida."}

        # Sincroniza listas persistidas de propostas.
        mapa_status = {p.id: p for p in estado.pendencias_jogador}
        for proposta in estado.propostas_atuais:
            if proposta.id in mapa_status:
                proposta.status = mapa_status[proposta.id].status
                proposta.motivo_recusa = mapa_status[proposta.id].motivo_recusa

        estado.pendencias_jogador = [
            p for p in estado.pendencias_jogador
            if not (str(p.piloto_id) == jid and p.status != StatusProposta.PENDENTE)
        ]
        if acao in {"aceitar", "recusar_todas"}:
            estado.pendencias_jogador = [p for p in estado.pendencias_jogador if str(p.piloto_id) != jid]

        self._sincronizar_equipes_e_papeis()
        estado.contratos_ativos = self._reconstruir_contratos_ativos(temporada_ref)
        self._salvar_estado_persistido(estado)

        resumo_dict = mercado_raw.get("resultado_janela_atual", {})
        resumo = ResultadoMercado.from_dict(resumo_dict) if isinstance(resumo_dict, dict) and resumo_dict else ResultadoMercado(temporada=temporada_ref)
        if motivo:
            resumo.adicionar_destaque(motivo)
        resumo.total_propostas = len(estado.propostas_atuais)
        resumo.propostas_aceitas = sum(1 for p in estado.propostas_atuais if p.status == StatusProposta.ACEITA)
        resumo.propostas_recusadas = sum(1 for p in estado.propostas_atuais if p.status == StatusProposta.RECUSADA)
        mercado_raw["resultado_janela_atual"] = resumo.to_dict()

        return {"ok": True, "mensagem": motivo, "pendencias_restantes": len(self.obter_pendencias_jogador(jid))}

    def finalizar_janela(self, temporada: Optional[int] = None) -> ResultadoMercado:
        estado = self._estado_persistido()
        mercado_raw = self.garantir_estrutura_mercado_no_banco(self.banco)
        temporada_ref = _int(temporada, _int(estado.temporada_janela or self.banco.get("temporada_atual", 1), 1))

        if any(p.status == StatusProposta.PENDENTE for p in estado.pendencias_jogador):
            return ResultadoMercado.from_dict(mercado_raw.get("resultado_janela_atual", {"temporada": temporada_ref}))

        payload = mercado_raw.get("resultado_janela_atual")
        resultado = ResultadoMercado.from_dict(payload) if isinstance(payload, dict) and payload else ResultadoMercado(temporada=temporada_ref)

        self._sincronizar_equipes_e_papeis()
        equipes_index = self._index_equipes()
        pilotos_index = self._index_pilotos()
        vagas_restantes = self._deduplicar_vagas(
            self._gerar_vagas_abertas(equipes_index, pilotos_index)
        )
        reserva_ids = set(str(pid) for pid in estado.reserva_global)
        if vagas_restantes:
            vagas_restantes = self._fase_sobras_preenchimento_forcado(
                temporada=temporada_ref,
                equipes_index=equipes_index,
                pilotos_index=pilotos_index,
                reserva_global_ids=reserva_ids,
                resultado=resultado,
            )
        estado.reserva_global = sorted(reserva_ids)

        resultado.total_propostas = len(estado.propostas_atuais)
        resultado.propostas_aceitas = sum(1 for p in estado.propostas_atuais if p.status == StatusProposta.ACEITA)
        resultado.propostas_recusadas = sum(1 for p in estado.propostas_atuais if p.status == StatusProposta.RECUSADA)
        resultado.vagas_nao_preenchidas = len(vagas_restantes)
        resultado.vagas_preenchidas = max(0, resultado.total_propostas - resultado.vagas_nao_preenchidas)
        resultado.rookies_gerados = list(estado.rookies_gerados)
        resultado.pilotos_sem_vaga = list(estado.reserva_global)

        estado.historico_janelas.append(resultado)
        estado.janela_aberta = False
        estado.temporada_janela = 0
        estado.propostas_atuais = []
        estado.pendencias_jogador = []
        estado.vagas_abertas = [vaga for vaga in vagas_restantes]
        estado.rookies_gerados = []
        estado.contratos_ativos = self._reconstruir_contratos_ativos(temporada_ref)

        self._salvar_estado_persistido(estado)
        mercado_raw["resultado_janela_atual"] = {}
        return resultado

    # ============================================================
    # Helpers de processamento
    # ============================================================

    def _obter_jogador(self) -> Optional[dict[str, Any]]:
        for piloto in self.banco.get("pilotos", []):
            if piloto.get("is_jogador", False):
                return piloto
        return None

    def _index_pilotos(self) -> dict[str, dict[str, Any]]:
        return {str(p.get("id")): p for p in self.banco.get("pilotos", []) if isinstance(p, dict)}

    def _index_equipes(self) -> dict[str, dict[str, Any]]:
        return {str(e.get("id")): e for e in self.banco.get("equipes", []) if isinstance(e, dict)}

    def _decrementar_contratos_temporada(self, temporada: int):
        mercado = self.garantir_estrutura_mercado_no_banco(self.banco)
        ultima = _int(mercado.get("ultima_temporada_decrementada", 0), 0)
        if ultima == temporada:
            return
        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if _status_piloto_normalizado(piloto) in {"aposentado", "reserva_global"}:
                continue
            anos = _int(piloto.get("contrato_anos", 0), 0)
            if anos > 0:
                piloto["contrato_anos"] = anos - 1
        mercado["ultima_temporada_decrementada"] = temporada

    def _mapa_resultado_temporada(self) -> dict[str, dict[str, int]]:
        mapa: dict[str, dict[str, int]] = {}
        por_categoria: dict[str, list[dict[str, Any]]] = {}

        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if _status_piloto_normalizado(piloto) in STATUS_INATIVOS:
                continue
            categoria = str(piloto.get("categoria_atual", "") or "")
            por_categoria.setdefault(categoria, []).append(piloto)

        for categoria, pilotos in por_categoria.items():
            pilotos_ord = sorted(
                pilotos,
                key=lambda p: (
                    -_int(p.get("pontos_temporada", 0), 0),
                    -_int(p.get("vitorias_temporada", 0), 0),
                    -_int(p.get("podios_temporada", 0), 0),
                    str(p.get("nome", "")).casefold(),
                ),
            )
            for pos, piloto in enumerate(pilotos_ord, start=1):
                mapa[str(piloto.get("id"))] = {"categoria": categoria, "posicao": pos}
        return mapa

    def _processar_renovacoes(
        self,
        temporada: int,
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
        rankings: dict[str, dict[str, int]],
        resultado: ResultadoMercado,
        jogador_id_str: str,
    ) -> list[VagaAberta]:
        vagas: list[VagaAberta] = []

        for equipe in equipes_index.values():
            pilotos_equipe = [
                p for p in pilotos_index.values()
                if str(p.get("equipe_id")) == str(equipe.get("id"))
                and _status_piloto_normalizado(p) not in {"aposentado", "reserva_global"}
            ]
            for piloto in pilotos_equipe:
                pid = str(piloto.get("id"))
                anos = _int(piloto.get("contrato_anos", 0), 0)
                if anos > 0:
                    continue

                papel_atual = _papel_from_str(
                    piloto.get("papel")
                    or (
                        PapelEquipe.NUMERO_1.value
                        if str(equipe.get("piloto_numero_1")) == pid
                        else PapelEquipe.NUMERO_2.value
                    ),
                    PapelEquipe.NUMERO_2,
                )

                if jogador_id_str and pid == jogador_id_str:
                    self._liberar_piloto(piloto, equipes_index)
                    vagas.append(self._vaga_para_equipe(equipe, papel_atual))
                    resultado.pilotos_liberados.append(pid)
                    continue

                posicao = _int(rankings.get(pid, {}).get("posicao", 15), 15)
                expectativa = _int(equipe.get("expectativa_posicao", 10), 10)
                contrato_atual = Contrato(
                    piloto_id=pid,
                    piloto_nome=str(piloto.get("nome", "") or ""),
                    equipe_id=str(equipe.get("id", "") or ""),
                    equipe_nome=str(equipe.get("nome", "") or ""),
                    temporada_inicio=max(1, temporada - 1),
                    duracao_anos=1,
                    salario_anual=_float(piloto.get("salario", 0), 0.0),
                    papel=papel_atual,
                )
                decisao = decidir_renovacao(
                    piloto=piloto,
                    contrato=contrato_atual,
                    equipe=equipe,
                    posicao_campeonato=posicao,
                    expectativa_posicao=expectativa,
                    temporada_atual=temporada,
                )
                if decisao.renovar:
                    duracao = 2 if _int(piloto.get("idade", 25), 25) <= 28 else 1
                    piloto["contrato_anos"] = duracao
                    piloto["salario"] = int(round(_float(decisao.novo_salario, _float(piloto.get("salario", 0), 0.0))))
                    piloto["papel"] = _papel_to_str(decisao.novo_papel or papel_atual)
                    papel_novo = _papel_from_str(piloto.get("papel"), papel_atual)
                    contrato_novo = criar_contrato(
                        piloto_id=pid,
                        piloto_nome=str(piloto.get("nome", "") or ""),
                        equipe_id=str(equipe.get("id", "") or ""),
                        equipe_nome=str(equipe.get("nome", "") or ""),
                        temporada_inicio=temporada + 1,
                        duracao_anos=duracao,
                        salario_anual=_float(piloto.get("salario", 0), 0.0),
                        papel=papel_novo,
                        incluir_clausula_rebaixamento=True,
                        incluir_clausula_performance=True,
                        meta_performance=5 if papel_novo == PapelEquipe.NUMERO_1 else 10,
                    )
                    resultado.contratos_renovados.append(contrato_novo)
                else:
                    self._liberar_piloto(piloto, equipes_index)
                    vagas.append(self._vaga_para_equipe(equipe, papel_atual))
                    resultado.pilotos_liberados.append(pid)

        return vagas

    def _pilotos_livres_para_mercado(
        self,
        pilotos_index: dict[str, dict[str, Any]],
        rankings: dict[str, dict[str, int]],
    ) -> list[PilotoMercado]:
        livres: list[PilotoMercado] = []
        total_por_categoria: dict[str, int] = {}
        for piloto in pilotos_index.values():
            categoria = str(piloto.get("categoria_atual", "") or "")
            if categoria:
                total_por_categoria[categoria] = total_por_categoria.get(categoria, 0) + 1

        for piloto in pilotos_index.values():
            if not isinstance(piloto, dict):
                continue
            status = _status_piloto_normalizado(piloto)
            if status in {"aposentado", "lesionado"}:
                continue
            if piloto.get("equipe_id"):
                continue
            livres.append(self._to_piloto_mercado(piloto, rankings, total_por_categoria))
        return livres

    def _to_piloto_mercado(
        self,
        piloto: dict[str, Any],
        rankings: dict[str, dict[str, int]],
        total_por_categoria: dict[str, int],
    ) -> PilotoMercado:
        categoria_atual = str(piloto.get("categoria_atual", "mazda_rookie") or "mazda_rookie")
        categoria_expandida, tier = mapear_categoria_para_expandida(categoria_atual)
        posicao = _int(rankings.get(str(piloto.get("id")), {}).get("posicao", 0), 0)
        total = _int(total_por_categoria.get(categoria_atual, 20), 20)
        vitorias = _int(piloto.get("vitorias_temporada", 0), 0)
        poles = _int(piloto.get("poles_temporada", 0), 0)
        calc_vis = calcular_visibilidade(
            piloto,
            categoria_tier=tier,
            posicao_campeonato=posicao,
            total_pilotos_categoria=total if total > 0 else 20,
            vitorias_temporada=vitorias,
            poles_temporada=poles,
            is_advanced_subtier=(tier >= 4),
        )
        potencial = _float(
            piloto.get("potencial_base", piloto.get("potencial", 70)),
            70.0,
        ) + _float(piloto.get("potencial_bonus", 0), 0.0)
        experiencia = _float(piloto.get("experience", piloto.get("experiencia", 0)), 0.0)
        salario = _float(piloto.get("salario", 10000), 10000.0)
        papel_atual = str(piloto.get("papel", "") or "").strip().lower()
        duelos_total = _int(piloto.get("duelos_internos_total", 0), 0)
        duelos_vencidos = _int(piloto.get("duelos_internos_vencidos", 0), 0)
        n2_superou = bool(piloto.get("n2_superou_n1_temporada", False))
        if not n2_superou and papel_atual in {"numero_2", "n2"}:
            n2_superou = duelos_vencidos >= max(3, duelos_total // 2) and duelos_total > 0

        return PilotoMercado(
            id=str(piloto.get("id")),
            nome=str(piloto.get("nome", "") or ""),
            idade=_int(piloto.get("idade", 25), 25),
            nacionalidade=str(piloto.get("nacionalidade", "") or ""),
            skill=_float(piloto.get("skill", 50), 50.0),
            potencial=max(40.0, min(100.0, potencial)),
            experience=max(0.0, min(100.0, experiencia)),
            status=StatusPiloto.LIVRE,
            equipe_atual_id=None,
            contrato_atual=None,
            visibilidade=calc_vis.visibilidade_final,
            atratividade=50.0 + calc_vis.visibilidade_final * 2.0,
            categoria_atual=categoria_expandida,
            categoria_tier=tier,
            posicao_campeonato=posicao,
            vitorias_temporada=vitorias,
            titulos=_int(piloto.get("titulos", 0), 0),
            salario_minimo=max(10_000.0, salario * 0.9),
            prefere_numero_1=bool(_int(piloto.get("skill", 50), 50) >= 70 or n2_superou),
            papel_atual=papel_atual,
            n2_superou_n1=n2_superou,
            duelos_internos_total=duelos_total,
            duelos_internos_vencidos=duelos_vencidos,
        )

    def _gerar_vagas_abertas(
        self,
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
    ) -> list[VagaAberta]:
        vagas: list[VagaAberta] = []
        for equipe in equipes_index.values():
            if not bool(equipe.get("ativa", True)):
                continue
            equipe_id = str(equipe.get("id", "") or "")
            categoria_bruta = str(equipe.get("categoria", equipe.get("categoria_id", "mazda_rookie")) or "mazda_rookie")
            categoria_expandida, tier = mapear_categoria_para_expandida(categoria_bruta)
            pilotos_equipe = [
                p for p in pilotos_index.values()
                if str(p.get("equipe_id")) == equipe_id
                and _status_piloto_normalizado(p) not in {"aposentado", "reserva_global"}
            ]
            if len(pilotos_equipe) >= 2:
                continue

            papeis_presentes = {
                _papel_from_str(
                    p.get("papel")
                    or (
                        PapelEquipe.NUMERO_1.value
                        if str(equipe.get("piloto_numero_1")) == str(p.get("id"))
                        else PapelEquipe.NUMERO_2.value
                    ),
                    PapelEquipe.NUMERO_2,
                )
                for p in pilotos_equipe
            }
            while len(pilotos_equipe) + len([v for v in vagas if v.equipe_id == equipe_id]) < 2:
                if PapelEquipe.NUMERO_1 not in papeis_presentes:
                    papel = PapelEquipe.NUMERO_1
                    papeis_presentes.add(PapelEquipe.NUMERO_1)
                else:
                    papel = PapelEquipe.NUMERO_2
                vagas.append(
                    VagaAberta(
                        equipe_id=equipe_id,
                        equipe_nome=str(equipe.get("nome", "") or ""),
                        categoria_id=categoria_expandida,
                        categoria_tier=tier,
                        papel=papel,
                        car_performance=_float(equipe.get("car_performance", 50), 50.0),
                        budget_disponivel=_float(equipe.get("budget", 50), 50.0),
                        reputacao=_float(equipe.get("reputacao", 50), 50.0),
                        skill_minimo=max(35.0, 40.0 + (tier - 1) * 6.0),
                        skill_maximo=100.0,
                        idade_maxima=45,
                        prefere_jovem=tier <= 2,
                        prefere_experiente=tier >= 4,
                    )
                )
        return vagas

    def _vaga_para_equipe(self, equipe: dict[str, Any], papel: PapelEquipe) -> VagaAberta:
        categoria_bruta = str(equipe.get("categoria", equipe.get("categoria_id", "mazda_rookie")) or "mazda_rookie")
        categoria_expandida, tier = mapear_categoria_para_expandida(categoria_bruta)
        return VagaAberta(
            equipe_id=str(equipe.get("id", "") or ""),
            equipe_nome=str(equipe.get("nome", "") or ""),
            categoria_id=categoria_expandida,
            categoria_tier=tier,
            papel=papel,
            car_performance=_float(equipe.get("car_performance", 50), 50.0),
            budget_disponivel=_float(equipe.get("budget", 50), 50.0),
            reputacao=_float(equipe.get("reputacao", 50), 50.0),
            skill_minimo=max(35.0, 40.0 + (tier - 1) * 6.0),
            skill_maximo=100.0,
            idade_maxima=45,
        )

    @staticmethod
    def _deduplicar_vagas(vagas: list[VagaAberta]) -> list[VagaAberta]:
        dedup: list[VagaAberta] = []
        chaves: set[tuple[str, str]] = set()
        for vaga in vagas:
            chave = (str(vaga.equipe_id), vaga.papel.value)
            if chave in chaves:
                continue
            chaves.add(chave)
            dedup.append(vaga)
        return dedup

    @staticmethod
    def _consumir_vaga(vagas: list[VagaAberta], proposta: Proposta) -> list[VagaAberta]:
        consumiu = False
        novas: list[VagaAberta] = []
        for vaga in vagas:
            if (
                not consumiu
                and str(vaga.equipe_id) == str(proposta.equipe_id)
                and vaga.papel == proposta.papel
            ):
                consumiu = True
                continue
            novas.append(vaga)
        return novas

    def _aplicar_proposta_aceita(
        self,
        proposta: Proposta,
        temporada: int,
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
        resultado: Optional[ResultadoMercado],
    ):
        piloto = pilotos_index.get(str(proposta.piloto_id))
        equipe = equipes_index.get(str(proposta.equipe_id))
        if piloto is None or equipe is None:
            proposta.status = StatusProposta.RECUSADA
            proposta.motivo_recusa = MotivoRecusa.EQUIPE_FRACA
            return

        self._liberar_piloto(piloto, equipes_index)
        salario = int(round(self._normalizar_salario_escala_jogo(proposta.salario_anual)))
        piloto["equipe_id"] = equipe.get("id")
        piloto["equipe_nome"] = equipe.get("nome")
        piloto["papel"] = proposta.papel.value
        piloto["categoria_atual"] = mapear_categoria_para_atual(proposta.categoria_id)
        piloto["contrato_anos"] = max(1, _int(proposta.duracao_anos, 1))
        piloto["salario"] = max(10_000, salario)
        if _status_piloto_normalizado(piloto) != "lesionado":
            piloto["status"] = "ativo"

        proposta.status = StatusProposta.ACEITA

        contrato_novo = criar_contrato(
            piloto_id=str(piloto.get("id", "")),
            piloto_nome=str(piloto.get("nome", "") or ""),
            equipe_id=str(equipe.get("id", "") or ""),
            equipe_nome=str(equipe.get("nome", "") or ""),
            temporada_inicio=temporada + 1,
            duracao_anos=max(1, _int(proposta.duracao_anos, 1)),
            salario_anual=float(piloto.get("salario", salario)),
            papel=proposta.papel,
            incluir_clausula_rebaixamento=True,
            incluir_clausula_performance=True,
            meta_performance=5 if proposta.papel == PapelEquipe.NUMERO_1 else 10,
        )
        if resultado is not None:
            resultado.contratos_novos.append(contrato_novo)

    def _enviar_para_reserva_global(
        self,
        piloto: Optional[dict[str, Any]],
        reserva_global_ids: set[str],
    ):
        if not isinstance(piloto, dict):
            return
        pid = str(piloto.get("id"))
        self._liberar_piloto(piloto, self._index_equipes())
        piloto["status"] = "reserva_global"
        piloto["papel"] = "reserva"
        piloto["contrato_anos"] = 0
        reserva_global_ids.add(pid)

    def _liberar_piloto(self, piloto: dict[str, Any], equipes_index: dict[str, dict[str, Any]]):
        equipe_id = str(piloto.get("equipe_id", "") or "")
        equipe = equipes_index.get(equipe_id) if equipe_id else None
        if equipe:
            pilotos_ids = [pid for pid in equipe.get("pilotos", []) if str(pid) != str(piloto.get("id"))]
            equipe["pilotos"] = pilotos_ids
            if str(equipe.get("piloto_numero_1")) == str(piloto.get("id")):
                equipe["piloto_numero_1"] = None
                equipe["piloto_1"] = None
            if str(equipe.get("piloto_numero_2")) == str(piloto.get("id")):
                equipe["piloto_numero_2"] = None
                equipe["piloto_2"] = None
        piloto["equipe_id"] = None
        piloto["equipe_nome"] = None
        piloto["papel"] = None
        if _status_piloto_normalizado(piloto) not in {"aposentado", "lesionado", "reserva_global"}:
            piloto["status"] = "livre"

    def _sincronizar_equipes_e_papeis(self):
        equipes_index = self._index_equipes()
        pilotos = [p for p in self.banco.get("pilotos", []) if isinstance(p, dict)]

        pilotos_por_id = {
            str(p.get("id")): p
            for p in pilotos
            if p.get("id") not in (None, "")
        }

        for equipe in equipes_index.values():
            equipe["pilotos"] = []
            equipe["piloto_numero_1"] = None
            equipe["piloto_numero_2"] = None
            equipe["piloto_1"] = None
            equipe["piloto_2"] = None

        for piloto in pilotos:
            status_norm = _status_piloto_normalizado(piloto)
            if status_norm in {"aposentado", "reserva_global", "livre"}:
                continue
            equipe_id = str(piloto.get("equipe_id", "") or "")
            equipe = equipes_index.get(equipe_id)
            if not equipe:
                if status_norm not in {"lesionado"}:
                    piloto["status"] = "livre"
                piloto["equipe_id"] = None
                piloto["equipe_nome"] = None
                piloto["papel"] = None
                continue
            equipe["pilotos"].append(piloto.get("id"))

        for equipe in equipes_index.values():
            ids = []
            ids_vistos: set[str] = set()
            for raw_id in list(equipe.get("pilotos", [])):
                chave = str(raw_id)
                if not chave or chave in ids_vistos:
                    continue
                ids_vistos.add(chave)
                ids.append(raw_id)
            equipe["pilotos"] = ids

            pilotos_equipe = [
                pilotos_por_id.get(str(pid))
                for pid in ids
                if pilotos_por_id.get(str(pid)) is not None
            ]
            pilotos_equipe = [p for p in pilotos_equipe if isinstance(p, dict)]
            pilotos_equipe.sort(key=lambda p: _float(p.get("skill", 0), 0.0), reverse=True)

            p1 = pilotos_equipe[0] if pilotos_equipe else None
            p2 = pilotos_equipe[1] if len(pilotos_equipe) > 1 else None

            hierarquia = equipe.get("hierarquia")
            if isinstance(hierarquia, dict):
                n1_id = str(hierarquia.get("n1_id", "") or "")
                n2_id = str(hierarquia.get("n2_id", "") or "")
                candidato_n1 = pilotos_por_id.get(n1_id)
                candidato_n2 = pilotos_por_id.get(n2_id)
                if candidato_n1 in pilotos_equipe and candidato_n2 in pilotos_equipe and candidato_n1 != candidato_n2:
                    p1 = candidato_n1
                    p2 = candidato_n2
                elif p1 is not None and p2 is not None:
                    hierarquia["n1_id"] = p1.get("id")
                    hierarquia["n2_id"] = p2.get("id")
                    hierarquia.setdefault("status", "estavel")
                    hierarquia.setdefault("corridas_n2_a_frente", 0)
                    hierarquia.setdefault("ultima_reavaliacao", 0)
                    equipe["hierarquia"] = hierarquia

            if p1 is not None:
                p1["papel"] = PapelEquipe.NUMERO_1.value
                equipe["piloto_numero_1"] = p1.get("id")
                equipe["piloto_1"] = p1.get("nome")
            if p2 is not None:
                p2["papel"] = PapelEquipe.NUMERO_2.value
                equipe["piloto_numero_2"] = p2.get("id")
                equipe["piloto_2"] = p2.get("nome")
            # Limita a 2 pilotos por equipe no fluxo atual.
            if len(pilotos_equipe) > 2:
                ids_titulares = {
                    str(p1.get("id")) if isinstance(p1, dict) else "",
                    str(p2.get("id")) if isinstance(p2, dict) else "",
                }
                for extra in pilotos_equipe:
                    if str(extra.get("id")) in ids_titulares:
                        continue
                    extra["equipe_id"] = None
                    extra["equipe_nome"] = None
                    extra["papel"] = "reserva"
                    extra["status"] = "reserva_global"
                    equipe["pilotos"] = [
                        pid for pid in equipe.get("pilotos", [])
                        if str(pid) != str(extra.get("id"))
                    ]

    def _reconstruir_contratos_ativos(self, temporada: int) -> list[Contrato]:
        contratos: list[Contrato] = []
        estado_atual = self._estado_persistido()
        contratos_anteriores = {
            (str(c.piloto_id), str(c.equipe_id)): c
            for c in estado_atual.contratos_ativos
            if c.esta_ativo
        }

        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if _status_piloto_normalizado(piloto) in {"aposentado", "reserva_global"}:
                continue
            equipe_id = piloto.get("equipe_id")
            equipe_nome = piloto.get("equipe_nome")
            anos = _int(piloto.get("contrato_anos", 0), 0)
            if not equipe_id or anos <= 0:
                continue
            papel = _papel_from_str(piloto.get("papel"), PapelEquipe.NUMERO_2)
            piloto_id = str(piloto.get("id", ""))
            chave = (piloto_id, str(equipe_id))
            contrato_prev = contratos_anteriores.get(chave)
            meta_performance = 5 if papel == PapelEquipe.NUMERO_1 else 10
            contrato_novo = criar_contrato(
                piloto_id=piloto_id,
                piloto_nome=str(piloto.get("nome", "") or ""),
                equipe_id=str(equipe_id),
                equipe_nome=str(equipe_nome or ""),
                temporada_inicio=max(1, temporada - anos + 1),
                duracao_anos=anos,
                salario_anual=_float(piloto.get("salario", 0), 0.0),
                papel=papel,
                incluir_clausula_rebaixamento=True,
                incluir_clausula_performance=True,
                meta_performance=meta_performance,
            )
            if contrato_prev is not None and contrato_prev.esta_ativo:
                contrato_novo.id = contrato_prev.id
                if contrato_prev.clausulas:
                    contrato_novo.clausulas = list(contrato_prev.clausulas)

            contratos.append(contrato_novo)
        return contratos

    @staticmethod
    def _calcular_num_rookies(aposentadorias_temporada: Optional[int]) -> Optional[int]:
        if aposentadorias_temporada is None:
            return None
        base = 3
        aposentadorias = max(0, _int(aposentadorias_temporada, 0))
        extra = max(0, aposentadorias - base)
        return min(8, base + extra)

    @staticmethod
    def _tier_por_skill(skill: float) -> int:
        valor = _float(skill, 50.0)
        if valor < 40:
            return 1
        if valor < 50:
            return 2
        if valor < 60:
            return 3
        if valor < 70:
            return 4
        if valor < 80:
            return 5
        return 6

    def _encontrar_piloto_disponivel(
        self,
        categoria_id: str,
        tier: int,
        pilotos_index: dict[str, dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        candidatos: list[tuple[int, int, float, float, dict[str, Any]]] = []
        categoria_alvo = str(categoria_id or "").strip().lower()

        for piloto in pilotos_index.values():
            if not isinstance(piloto, dict):
                continue
            if bool(piloto.get("aposentado", False)):
                continue

            status = str(piloto.get("status", "livre") or "livre").strip().lower()
            if piloto.get("equipe_id") not in (None, ""):
                continue
            if status not in {"reserva", "desempregado", "reserva_global", "livre", "ativo"}:
                continue

            categoria_piloto = str(piloto.get("categoria_atual", "") or "").strip().lower()
            if categoria_piloto:
                _, tier_categoria = mapear_categoria_para_expandida(categoria_piloto)
            else:
                tier_categoria = self._tier_por_skill(_float(piloto.get("skill", 50), 50.0))

            if abs(int(tier_categoria) - int(tier)) > 1:
                continue

            prioridade_status = {
                "reserva": 0,
                "desempregado": 1,
                "reserva_global": 2,
                "livre": 3,
                "ativo": 4,
            }.get(status, 5)
            skill = _float(piloto.get("skill", 0), 0.0)
            experiencia = _float(piloto.get("experience", piloto.get("experiencia", 0)), 0.0)

            # Prioriza compatibilidade direta de categoria dentro do tier.
            bonus_categoria = 0
            if categoria_piloto and categoria_piloto == categoria_alvo:
                bonus_categoria = 1

            candidatos.append((prioridade_status, -bonus_categoria, -skill, -experiencia, piloto))

        if not candidatos:
            return None

        candidatos.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
        return candidatos[0][4]

    def _assinar_contrato_forcado(
        self,
        piloto: dict[str, Any],
        vaga: VagaAberta,
        temporada: int,
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
        resultado: ResultadoMercado,
    ) -> None:
        equipe = equipes_index.get(str(vaga.equipe_id))
        if not isinstance(equipe, dict):
            return

        self._liberar_piloto(piloto, equipes_index)
        salario = max(10_000, int(round(_float(piloto.get("salario", 0), 0.0))))
        if salario <= 10_000:
            salario = max(10_000, int(round(_float(piloto.get("skill", 45), 45.0) * 1_000)))

        piloto["status"] = "ativo"
        piloto["equipe_id"] = equipe.get("id")
        piloto["equipe_nome"] = equipe.get("nome")
        piloto["papel"] = vaga.papel.value
        piloto["contrato_anos"] = 1
        piloto["salario"] = salario
        piloto["categoria_atual"] = mapear_categoria_para_atual(vaga.categoria_id)

        pilotos_ids = list(equipe.get("pilotos", [])) if isinstance(equipe.get("pilotos"), list) else []
        if piloto.get("id") not in pilotos_ids:
            pilotos_ids.append(piloto.get("id"))
        equipe["pilotos"] = pilotos_ids

        contrato = criar_contrato(
            piloto_id=str(piloto.get("id", "")),
            piloto_nome=str(piloto.get("nome", "") or ""),
            equipe_id=str(equipe.get("id", "") or ""),
            equipe_nome=str(equipe.get("nome", "") or ""),
            temporada_inicio=temporada + 1,
            duracao_anos=1,
            salario_anual=float(salario),
            papel=vaga.papel,
            incluir_clausula_rebaixamento=True,
            incluir_clausula_performance=True,
            meta_performance=5 if vaga.papel == PapelEquipe.NUMERO_1 else 10,
        )
        resultado.contratos_novos.append(contrato)
        pilotos_index[str(piloto.get("id"))] = piloto

    def _gerar_piloto_emergencia(
        self,
        categoria_id: str,
        tier: int,
        temporada: int,
        pilotos_index: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        skill_ranges = {
            1: (30, 50),
            2: (40, 60),
            3: (50, 70),
            4: (55, 75),
            5: (60, 85),
            6: (65, 90),
        }
        skill_min, skill_max = skill_ranges.get(int(tier), (40, 60))
        categoria_atual = mapear_categoria_para_atual(categoria_id)
        ano_atual = _int(self.banco.get("ano_atual", 2024), 2024)

        piloto = criar_piloto(
            self.banco,
            categoria_id=categoria_atual,
            skill_min=skill_min,
            skill_max=skill_max,
            idade_min=20,
            idade_max=30,
            ano_atual=ano_atual,
        )
        piloto["id"] = obter_proximo_id(self.banco, "piloto")
        piloto["status"] = "livre"
        piloto["equipe_id"] = None
        piloto["equipe_nome"] = None
        piloto["papel"] = "reserva"
        piloto["contrato_anos"] = 0
        piloto["categoria_atual"] = categoria_atual
        self.banco.setdefault("pilotos", []).append(piloto)
        pilotos_index[str(piloto.get("id"))] = piloto
        _ = temporada
        return piloto

    def _fase_sobras_preenchimento_forcado(
        self,
        temporada: int,
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
        reserva_global_ids: set[str],
        resultado: ResultadoMercado,
    ) -> list[VagaAberta]:
        max_iteracoes = 50
        for _ in range(max_iteracoes):
            self._sincronizar_equipes_e_papeis()
            vagas = self._deduplicar_vagas(
                self._gerar_vagas_abertas(equipes_index, pilotos_index)
            )
            if not vagas:
                return []

            preencheu = False
            for vaga in vagas:
                equipe = equipes_index.get(str(vaga.equipe_id))
                if not isinstance(equipe, dict):
                    continue
                if not bool(equipe.get("ativa", True)):
                    continue

                piloto = self._encontrar_piloto_disponivel(
                    categoria_id=vaga.categoria_id,
                    tier=int(vaga.categoria_tier),
                    pilotos_index=pilotos_index,
                )
                if piloto is None:
                    piloto = self._gerar_piloto_emergencia(
                        categoria_id=vaga.categoria_id,
                        tier=int(vaga.categoria_tier),
                        temporada=temporada,
                        pilotos_index=pilotos_index,
                    )

                if piloto is None:
                    continue

                self._assinar_contrato_forcado(
                    piloto=piloto,
                    vaga=vaga,
                    temporada=temporada,
                    equipes_index=equipes_index,
                    pilotos_index=pilotos_index,
                    resultado=resultado,
                )
                reserva_global_ids.discard(str(piloto.get("id")))
                preencheu = True

            if not preencheu:
                break

        self._sincronizar_equipes_e_papeis()
        return self._deduplicar_vagas(
            self._gerar_vagas_abertas(equipes_index, pilotos_index)
        )

    def _gerar_e_inserir_rookies(
        self,
        temporada: int,
        vagas_disponiveis: list[VagaAberta],
        equipes_index: dict[str, dict[str, Any]],
        pilotos_index: dict[str, dict[str, Any]],
        reserva_global_ids: set[str],
        resultado: ResultadoMercado,
        quantidade: Optional[int] = None,
    ) -> list[str]:
        rookies_ids: list[str] = []
        rookies = gerar_rookies_temporada(quantidade=quantidade)
        categorias_rookie = {"mazda_rookie", "toyota_rookie"}
        vagas_ordenadas = sorted(
            [
                vaga
                for vaga in vagas_disponiveis
                if str(vaga.categoria_id or "").strip().lower() in categorias_rookie
            ],
            key=lambda v: (-v.car_performance, v.equipe_nome.casefold()),
        )

        for rookie in rookies:
            piloto = self._criar_piloto_rookie(rookie, temporada)
            self.banco.setdefault("pilotos", []).append(piloto)
            pilotos_index[str(piloto.get("id"))] = piloto
            rookies_ids.append(str(piloto.get("id")))
            resultado.rookies_gerados.append(str(piloto.get("id")))

            if vagas_ordenadas:
                vaga = vagas_ordenadas.pop(0)
                proposta_virtual = Proposta(
                    equipe_id=str(vaga.equipe_id),
                    equipe_nome=str(vaga.equipe_nome),
                    piloto_id=str(piloto.get("id")),
                    piloto_nome=str(piloto.get("nome", "")),
                    salario_anual=max(10_000.0, _float(piloto.get("salario", 15_000), 15_000.0)),
                    duracao_anos=1,
                    papel=vaga.papel,
                    categoria_id=vaga.categoria_id,
                    categoria_tier=vaga.categoria_tier,
                    car_performance=vaga.car_performance,
                    reputacao_equipe=vaga.reputacao,
                )
                self._aplicar_proposta_aceita(proposta_virtual, temporada, equipes_index, pilotos_index, resultado)
                vagas_disponiveis[:] = self._consumir_vaga(vagas_disponiveis, proposta_virtual)
            else:
                piloto["status"] = "reserva_global"
                piloto["papel"] = "reserva"
                resultado.pilotos_sem_vaga.append(str(piloto.get("id")))
                reserva_global_ids.add(str(piloto.get("id")))

        return rookies_ids

    def _criar_piloto_rookie(self, rookie: RookieGerado, temporada: int) -> dict[str, Any]:
        ano_atual = _int(self.banco.get("ano_atual", 2024), 2024)
        piloto = criar_piloto(
            self.banco,
            categoria_id="mazda_rookie",
            skill_min=35,
            skill_max=65,
            idade_min=16,
            idade_max=20,
            ano_atual=ano_atual,
        )
        piloto["id"] = obter_proximo_id(self.banco, "piloto")
        piloto["nome"] = rookie.nome
        piloto["idade"] = rookie.idade
        piloto["nacionalidade"] = rookie.nacionalidade
        piloto["categoria_atual"] = "mazda_rookie"
        piloto["is_jogador"] = False
        piloto["status"] = "livre"
        piloto["equipe_id"] = None
        piloto["equipe_nome"] = None
        piloto["papel"] = "reserva"
        piloto["contrato_anos"] = 0
        piloto["salario"] = max(10_000, int(round(_float(rookie.skill_inicial, 40.0) * 1_000)))

        for chave, valor in rookie.atributos.items():
            if chave in {"experience", "experiencia"}:
                piloto["experience"] = _float(valor, 0.0)
                piloto["experiencia"] = _float(valor, 0.0)
                continue
            if chave == "clutch_factor":
                piloto["fator_clutch"] = _float(valor, 50.0)
                continue
            piloto[chave] = valor

        potencial = _float(rookie.potencial, 70.0)
        piloto["potencial"] = potencial
        piloto["potencial_base"] = potencial
        piloto["potencial_bonus"] = 0.0
        piloto["temporadas_na_categoria"] = 0
        piloto["ano_inicio_carreira"] = ano_atual
        _ = temporada
        return piloto

    @staticmethod
    def _normalizar_salario_escala_jogo(salario: float) -> float:
        valor = _float(salario, 0.0)
        if valor <= 0:
            return 10_000.0
        if valor <= 250.0:
            return round(valor * 5_000.0, 0)
        return round(valor, 0)
