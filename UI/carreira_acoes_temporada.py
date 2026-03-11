from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from Dados.banco import _validar_campos_banco, salvar_banco
from Dados.constantes import CATEGORIAS
from Logica.evolucao.evolucao_manager import EvolucaoManager
from Logica.equipes import (
    calcular_pontos_equipes,
    evolucionar_equipes,
    obter_equipes_categoria,
)
from Logica.mercado import MercadoManager
from Logica.pilotos import (
    calcular_posicao_campeonato,
    obter_pilotos_categoria,
)
from Logica.promocao import PromocaoManager, relatorio_to_dict
from Logica.series_especiais import inicializar_production_car_challenge
from UI.carreira_acoes import CarreiraAcoesBaseMixin
from Utils.helpers import obter_nome_categoria


class TemporadaMixin(CarreiraAcoesBaseMixin):
    """
    Mixin de progresso e finalizacao de temporada.
    Espera que a classe final tenha:
        - self.banco
        - self.categoria_atual
        - self._atualizar_tudo()
        - self._obter_jogador()
    """

    def _avancar_rodada(self):
        """Avanca para a proxima rodada."""
        rodada_atual = int(self.banco.get("rodada_atual", 1))
        obter_total = getattr(self, "_obter_total_rodadas_temporada", None)
        if callable(obter_total):
            try:
                total_rodadas = int(obter_total())
            except (TypeError, ValueError):
                total_rodadas = int(self.banco.get("total_rodadas", 24))
        else:
            total_rodadas = int(self.banco.get("total_rodadas", 24))

        if rodada_atual >= total_rodadas:
            self.banco["temporada_concluida"] = True
        else:
            self.banco["rodada_atual"] = rodada_atual + 1
            self.banco["temporada_concluida"] = False

        salvar_banco(self.banco)

    def _finalizar_temporada(self):
        """Processa o encerramento da temporada atual."""
        if self._corridas_restantes() > 0 and not self._temporada_concluida():
            resposta = QMessageBox.question(
                self,
                "Confirmar",
                f"Ainda faltam {self._corridas_restantes()} corridas.\n"
                "Deseja finalizar a temporada mesmo assim?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if resposta != QMessageBox.Yes:
                return

        fechamento = self._estado_fechamento_temporada()

        # 1) Simulacao IA para categorias nao ativas (idempotente).
        if not bool(fechamento.get("simulacao_ai_concluida", False)):
            self._simular_categorias_nao_ativas_fechamento()
            fechamento["simulacao_ai_concluida"] = True

        # 2) Pre-fechamento (historico), processado uma vez.
        ano, aposentados = self._garantir_pre_fechamento_temporada()
        if ano <= 0:
            ano = int(self.banco.get("ano_atual", 2024))

        # 3) Evolucao de pilotos (M6) - idempotente por janela.
        relatorios_evolucao: list[dict[str, Any]] = []
        evolucao_jogador: list[dict[str, Any]] = []
        snapshot_jogador_pre = self._snapshot_atributos_jogador()
        if bool(fechamento.get("evolucao_processada", False)):
            aposentados = list(fechamento.get("aposentados", []))
            payload_relatorios = fechamento.get("relatorios_evolucao", [])
            payload_jogador = fechamento.get("evolucao_jogador", [])
            if isinstance(payload_relatorios, list):
                relatorios_evolucao = [
                    item for item in payload_relatorios if isinstance(item, dict)
                ]
            if isinstance(payload_jogador, list):
                evolucao_jogador = [
                    item for item in payload_jogador if isinstance(item, dict)
                ]
        else:
            aposentados, relatorios_evolucao = self._processar_evolucao_fim_temporada(ano)
            evolucao_jogador = self._comparar_atributos_jogador(snapshot_jogador_pre)
            fechamento["aposentados"] = list(aposentados)
            fechamento["total_aposentadorias"] = len(aposentados)
            fechamento["evolucao_processada"] = True
            fechamento["relatorios_evolucao"] = list(relatorios_evolucao)
            fechamento["evolucao_jogador"] = list(evolucao_jogador)

        # 4) Promocao/rebaixamento de equipes (M8) - idempotente.
        relatorio_promocao: dict[str, Any] = {}
        if bool(fechamento.get("promocao_processada", False)):
            payload = fechamento.get("relatorio_promocao")
            if isinstance(payload, dict):
                relatorio_promocao = dict(payload)
        else:
            relatorio = self._processar_promocao_fim_temporada(ano)
            relatorio_promocao = relatorio_to_dict(relatorio)
            fechamento["promocao_processada"] = True
            fechamento["relatorio_promocao"] = relatorio_promocao

        # 5) Limpeza de rosters antes do mercado.
        self._sincronizar_rosters()

        # 6) Mercado (M7) com clausulas de contrato ja aplicadas no modulo de promocao.
        resultado_mercado = self._processar_mercado_fim_temporada(
            aposentadorias_temporada=int(fechamento.get("total_aposentadorias", len(aposentados)) or len(aposentados))
        )
        if resultado_mercado is None:
            # Pendencia do jogador bloqueia avanco da temporada sem repetir etapas anteriores.
            salvar_banco(self.banco)
            self._atualizar_tudo()
            return

        # 7) Validacao final pos-mercado.
        self._sincronizar_rosters()
        saneamento_pos_mercado = self._sanear_integridade_banco()
        fechamento["saneamento_pos_mercado"] = dict(saneamento_pos_mercado)
        validacao_ecossistema = self._validar_ecossistema_pos_mercado()
        fechamento["validacao_pos_mercado"] = dict(validacao_ecossistema)

        # Evolucao anual de equipes acontece uma unica vez apos fechar mercado.
        evolucionar_equipes(self.banco)

        # Exibe antes de resetar os numeros da temporada.
        self._exibir_resumo_temporada(
            ano,
            aposentados,
            resultado_mercado=resultado_mercado,
            relatorio_promocao=relatorio_promocao,
            evolucao_jogador=evolucao_jogador,
            relatorios_evolucao=relatorios_evolucao,
        )

        self._resetar_stats_temporada()

        self.banco["ano_atual"] = ano + 1
        self.banco["temporada_atual"] = int(self.banco.get("temporada_atual", 1)) + 1
        self.banco["rodada_atual"] = 1
        self.banco["temporada_concluida"] = False
        inicializar_production_car_challenge(self.banco, self.banco["ano_atual"])
        self._sincronizar_rosters()
        saneamento_pos_reset = self._sanear_integridade_banco()
        fechamento["saneamento_pos_reset"] = dict(saneamento_pos_reset)
        self._inicializar_hierarquias(self.banco)
        validacao_final_ok = self._validar_ecossistema_final(self.banco)
        fechamento["validacao_final"] = {
            "ok": bool(validacao_final_ok),
            "ano_validado": int(self.banco.get("ano_atual", ano + 1)),
        }
        self._limpar_estado_fechamento_temporada()

        salvar_banco(self.banco)
        self._atualizar_tudo()

    def _estado_fechamento_temporada(self) -> dict:
        """Retorna o bloco persistente de fechamento da temporada dentro de banco['mercado']."""
        mercado = MercadoManager.garantir_estrutura_mercado_no_banco(self.banco)
        fechamento = mercado.get("fechamento_temporada")
        if not isinstance(fechamento, dict):
            fechamento = {}
            mercado["fechamento_temporada"] = fechamento

        defaults = {
            "em_andamento": False,
            "ano_base": 0,
            "aposentados": [],
            "total_aposentadorias": 0,
            "simulacao_ai_concluida": False,
            "evolucao_processada": False,
            "relatorios_evolucao": [],
            "evolucao_jogador": [],
            "promocao_processada": False,
            "relatorio_promocao": {},
            "saneamento_pos_mercado": {},
            "saneamento_pos_reset": {},
            "validacao_pos_mercado": {},
            "validacao_final": {},
        }
        for chave, valor_padrao in defaults.items():
            if chave not in fechamento:
                fechamento[chave] = valor_padrao

        if not isinstance(fechamento.get("aposentados"), list):
            fechamento["aposentados"] = []
        if not isinstance(fechamento.get("relatorios_evolucao"), list):
            fechamento["relatorios_evolucao"] = []
        if not isinstance(fechamento.get("evolucao_jogador"), list):
            fechamento["evolucao_jogador"] = []
        if not isinstance(fechamento.get("relatorio_promocao"), dict):
            fechamento["relatorio_promocao"] = {}
        if not isinstance(fechamento.get("saneamento_pos_mercado"), dict):
            fechamento["saneamento_pos_mercado"] = {}
        if not isinstance(fechamento.get("saneamento_pos_reset"), dict):
            fechamento["saneamento_pos_reset"] = {}
        if not isinstance(fechamento.get("validacao_pos_mercado"), dict):
            fechamento["validacao_pos_mercado"] = {}
        if not isinstance(fechamento.get("validacao_final"), dict):
            fechamento["validacao_final"] = {}

        fechamento["em_andamento"] = bool(fechamento.get("em_andamento", False))
        fechamento["simulacao_ai_concluida"] = bool(fechamento.get("simulacao_ai_concluida", False))
        fechamento["evolucao_processada"] = bool(fechamento.get("evolucao_processada", False))
        fechamento["promocao_processada"] = bool(fechamento.get("promocao_processada", False))

        try:
            fechamento["ano_base"] = int(fechamento.get("ano_base", 0) or 0)
        except (TypeError, ValueError):
            fechamento["ano_base"] = 0
        try:
            fechamento["total_aposentadorias"] = int(fechamento.get("total_aposentadorias", 0) or 0)
        except (TypeError, ValueError):
            fechamento["total_aposentadorias"] = 0

        return fechamento

    def _garantir_pre_fechamento_temporada(self) -> tuple[int, list[dict]]:
        """
        Garante que historico seja processado uma unica vez
        antes da janela de mercado.
        """
        fechamento = self._estado_fechamento_temporada()
        if fechamento.get("em_andamento", False):
            ano_ref = int(fechamento.get("ano_base", self.banco.get("ano_atual", 2024)))
            aposentados_ref = list(fechamento.get("aposentados", []))
            return ano_ref, aposentados_ref

        ano = int(self.banco.get("ano_atual", 2024))
        self._salvar_historico_temporada(ano)
        aposentados: list[dict] = []

        fechamento["em_andamento"] = True
        fechamento["ano_base"] = ano
        fechamento["aposentados"] = list(aposentados)
        return ano, aposentados

    def _limpar_estado_fechamento_temporada(self):
        """Limpa estado temporario do fechamento apos avanco definitivo de temporada."""
        fechamento = self._estado_fechamento_temporada()
        fechamento["em_andamento"] = False
        fechamento["ano_base"] = 0
        fechamento["aposentados"] = []
        fechamento["total_aposentadorias"] = 0
        fechamento["simulacao_ai_concluida"] = False
        fechamento["evolucao_processada"] = False
        fechamento["relatorios_evolucao"] = []
        fechamento["evolucao_jogador"] = []
        fechamento["promocao_processada"] = False
        fechamento["relatorio_promocao"] = {}
        fechamento["saneamento_pos_mercado"] = {}
        fechamento["saneamento_pos_reset"] = {}
        fechamento["validacao_pos_mercado"] = {}
        fechamento["validacao_final"] = {}

    def _sincronizar_rosters(self) -> None:
        """
        Sincroniza equipes/pilotos removendo ghost IDs e alinhando papeis.
        """
        manager = MercadoManager(self.banco)
        manager._sincronizar_equipes_e_papeis()

    def _sanear_integridade_banco(self) -> dict[str, Any]:
        """
        Reaplica validacoes canonicas de schema/integridade apos etapas de alto impacto.
        """
        banco_saneado, alterado = _validar_campos_banco(self.banco)
        if banco_saneado is not self.banco:
            self.banco = banco_saneado
        if alterado:
            self._sincronizar_rosters()
        return {"alterado": bool(alterado)}

    def _inicializar_hierarquias(self, banco: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """
        Define hierarquia N1/N2 no inicio da temporada com equipes completas.

        Criterio:
        1) Duracao de contrato
        2) Skill
        3) Experiencia
        4) Idade
        """
        banco_ref = banco if isinstance(banco, dict) else self.banco
        pilotos_por_id = {
            self._normalizar_id_hierarquia(p.get("id")): p
            for p in banco_ref.get("pilotos", [])
            if isinstance(p, dict) and not bool(p.get("aposentado", False))
        }

        definidas: list[dict[str, Any]] = []
        for equipe in banco_ref.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if not bool(equipe.get("ativa", True)):
                continue

            pilotos_ids = equipe.get("pilotos", [])
            if not isinstance(pilotos_ids, list):
                continue
            if len(pilotos_ids) != 2:
                continue

            piloto_1 = pilotos_por_id.get(self._normalizar_id_hierarquia(pilotos_ids[0]))
            piloto_2 = pilotos_por_id.get(self._normalizar_id_hierarquia(pilotos_ids[1]))
            if not isinstance(piloto_1, dict) or not isinstance(piloto_2, dict):
                continue

            hierarquia = self._inicializar_hierarquia_equipe(equipe, piloto_1, piloto_2)
            definidas.append(
                {
                    "equipe_id": equipe.get("id"),
                    "equipe_nome": equipe.get("nome"),
                    "n1_id": hierarquia.get("n1_id"),
                    "n2_id": hierarquia.get("n2_id"),
                    "status": hierarquia.get("status", "estavel"),
                }
            )

        return definidas

    @staticmethod
    def _campos_evolucao_jogador() -> list[tuple[str, str]]:
        return [
            ("skill", "Skill"),
            ("consistencia", "Consistencia"),
            ("racecraft", "Racecraft"),
            ("ritmo_classificacao", "Ritmo Quali"),
            ("gestao_pneus", "Gestao Pneus"),
            ("habilidade_largada", "Hab. Largada"),
            ("resistencia_mental", "Resist. Mental"),
            ("fitness", "Fitness"),
            ("fator_chuva", "Fator Chuva"),
            ("fator_clutch", "Fator Clutch"),
            ("experiencia", "Experiencia"),
            ("motivacao", "Motivacao"),
        ]

    def _snapshot_atributos_jogador(self) -> dict[str, int]:
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return {}

        snapshot: dict[str, int] = {}
        for campo, _rotulo in self._campos_evolucao_jogador():
            try:
                snapshot[campo] = int(round(float(jogador.get(campo, 0) or 0)))
            except (TypeError, ValueError):
                snapshot[campo] = 0
        return snapshot

    def _comparar_atributos_jogador(self, snapshot_anterior: dict[str, int]) -> list[dict[str, Any]]:
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return []

        deltas: list[dict[str, Any]] = []
        for campo, rotulo in self._campos_evolucao_jogador():
            valor_antes = int(snapshot_anterior.get(campo, 0) or 0)
            try:
                valor_depois = int(round(float(jogador.get(campo, valor_antes) or valor_antes)))
            except (TypeError, ValueError):
                valor_depois = valor_antes
            deltas.append(
                {
                    "campo": campo,
                    "rotulo": rotulo,
                    "antes": valor_antes,
                    "depois": valor_depois,
                    "delta": valor_depois - valor_antes,
                }
            )
        return deltas

    def _validar_ecossistema_final(self, banco: dict[str, Any]) -> bool:
        erros: list[str] = []

        for equipe in banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if not bool(equipe.get("ativa", True)):
                continue
            pilotos_equipe = equipe.get("pilotos", [])
            total_pilotos = len(pilotos_equipe) if isinstance(pilotos_equipe, list) else 0
            if total_pilotos != 2:
                erros.append(f"{equipe.get('nome', 'Equipe sem nome')}: {total_pilotos} pilotos")

        contagens_esperadas = {
            "mazda_rookie": 6,
            "toyota_rookie": 6,
            "mazda_amador": 10,
            "toyota_amador": 10,
            "bmw_m2": 10,
            "production_challenger": 15,
            "gt4": 10,
            "gt3": 14,
            "endurance": 21,
        }
        for categoria_id, esperado in contagens_esperadas.items():
            real = len(obter_equipes_categoria(banco, categoria_id))
            if real != esperado:
                erros.append(f"{categoria_id}: {real} equipes (esperado {esperado})")

        for equipe in banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if not bool(equipe.get("ativa", True)):
                continue
            pilotos_equipe = equipe.get("pilotos", [])
            if not isinstance(pilotos_equipe, list) or len(pilotos_equipe) != 2:
                continue
            if not isinstance(equipe.get("hierarquia"), dict):
                erros.append(f"{equipe.get('nome', 'Equipe sem nome')}: sem hierarquia")

        for piloto in banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if bool(piloto.get("aposentado", False)):
                continue
            status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
            if status in {"ativo", "lesionado"} and piloto.get("equipe_id") in (None, ""):
                erros.append(
                    f"Piloto {piloto.get('nome', 'Sem nome')} ativo sem equipe"
                )

        if erros:
            print(f"[VALIDACAO] {len(erros)} problemas encontrados")
            for erro in erros:
                print(f"  - {erro}")
            return False

        print("[VALIDACAO] Ecossistema validado: sem problemas")
        return True

    def _validar_ecossistema_pos_mercado(self) -> dict[str, Any]:
        """
        Valida consistencia estrutural apos fechamento da janela de mercado.
        """
        self._sincronizar_rosters()
        pilotos_por_id = {
            str(p.get("id")): p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict)
        }

        distribuicao_equipes: dict[int, int] = {}
        ghost_ids = 0
        equipes_ativas = 0
        equipes_com_2 = 0
        equipes_com_0_ou_1 = 0

        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if not bool(equipe.get("ativa", True)):
                continue

            equipes_ativas += 1
            pilotos_lista = equipe.get("pilotos", [])
            if not isinstance(pilotos_lista, list):
                pilotos_lista = []
                equipe["pilotos"] = pilotos_lista

            qtd = len(pilotos_lista)
            distribuicao_equipes[qtd] = distribuicao_equipes.get(qtd, 0) + 1
            if qtd == 2:
                equipes_com_2 += 1
            if qtd < 2:
                equipes_com_0_ou_1 += 1

            for pid in pilotos_lista:
                piloto = pilotos_por_id.get(str(pid))
                if not piloto:
                    ghost_ids += 1
                    continue
                status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
                if (
                    bool(piloto.get("aposentado", False))
                    or status in {"aposentado", "reserva_global", "reserva", "livre"}
                    or str(piloto.get("equipe_id", "")) != str(equipe.get("id", ""))
                ):
                    ghost_ids += 1

        pilotos_ativos_sem_equipe = 0
        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if bool(piloto.get("aposentado", False)):
                continue
            status = str(piloto.get("status", "ativo") or "ativo").strip().lower()
            if status not in {"ativo", "lesionado"}:
                continue
            if piloto.get("equipe_id") in (None, ""):
                pilotos_ativos_sem_equipe += 1

        contagem_categoria = {
            str(categoria.get("id", "")).strip(): 0
            for categoria in CATEGORIAS
            if str(categoria.get("id", "")).strip()
        }
        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            categoria = str(equipe.get("categoria", equipe.get("categoria_id", "")) or "").strip()
            if categoria in contagem_categoria:
                contagem_categoria[categoria] += 1

        valido = (
            ghost_ids == 0
            and pilotos_ativos_sem_equipe == 0
            and equipes_com_2 == equipes_ativas
        )
        return {
            "valido": valido,
            "distribuicao_pilotos_por_equipe": dict(sorted(distribuicao_equipes.items())),
            "equipes_ativas": equipes_ativas,
            "equipes_com_2": equipes_com_2,
            "equipes_com_0_ou_1": equipes_com_0_ou_1,
            "ghost_ids": ghost_ids,
            "pilotos_ativos_sem_equipe": pilotos_ativos_sem_equipe,
            "contagem_equipes_por_categoria": contagem_categoria,
        }

    def _aplicar_classificacao_categoria(
        self,
        categoria_id: str,
        classificacao: list[dict[str, Any]],
        rodada: int | None = None,
    ) -> int:
        """Aplica classificacao simulada em uma categoria especifica."""
        aplicados = 0
        participantes_evolucao: list[dict[str, Any]] = []
        for posicao, entrada in enumerate(classificacao, start=1):
            piloto_id = entrada.get("piloto_id", entrada.get("id"))
            piloto = self._obter_piloto_por_id(piloto_id, categoria_id)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))
            try:
                posicao_campeonato = int(
                    entrada.get(
                        "posicao_campeonato",
                        entrada.get("posicao_classe", entrada.get("posicao", posicao)),
                    )
                )
            except (TypeError, ValueError):
                posicao_campeonato = posicao

            pontos_override = entrada.get("pontos")
            if isinstance(pontos_override, bool):
                pontos_override = None
            elif pontos_override is not None:
                try:
                    pontos_override = int(pontos_override)
                except (TypeError, ValueError):
                    pontos_override = None

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao_campeonato,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
                pontos_override=pontos_override,
            )
            try:
                incidentes = int(entrada.get("incidentes", 0) or 0)
            except (TypeError, ValueError):
                incidentes = 0
            participantes_evolucao.append(
                {
                    "piloto": piloto,
                    "piloto_id": piloto.get("id"),
                    "posicao": posicao_campeonato,
                    "dnf": bool(entrada.get("dnf", False)),
                    "pole": pole,
                    "incidentes": incidentes,
                    "teve_incidente": bool(incidentes > 0 or entrada.get("incidente", False)),
                    "erro_piloto": bool(
                        entrada.get(
                            "erro_piloto",
                            entrada.get("dnf_erro_proprio", False),
                        )
                    ),
                }
            )
            aplicados += 1

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=categoria_id,
                rodada=rodada,
            )
            self._processar_pos_corrida_evolucao(
                participantes=participantes_evolucao,
                categoria_id=categoria_id,
                rodada=rodada,
            )
            self._atualizar_hierarquia_pos_corrida(
                resultado_corrida=classificacao,
                categoria_id=categoria_id,
                rodada=rodada,
                foi_corrida_jogador=False,
            )

        return aplicados

    def _simular_categorias_nao_ativas_fechamento(self) -> int:
        """
        Simula corridas restantes para categorias nao ativas no fechamento da temporada.
        Retorna o total de simulacoes aplicadas.
        """
        from Logica.simulacao import simular_corrida_categoria
        from Logica.categorias import validar_integridade_rodada

        categorias_alvo = [
            str(categoria.get("id", "")).strip()
            for categoria in CATEGORIAS
            if str(categoria.get("id", "")).strip()
            and str(categoria.get("id", "")).strip() != str(self.categoria_atual)
        ]
        if not categorias_alvo:
            return 0

        total_rodadas = int(self._obter_total_rodadas_temporada())
        corridas_disputadas = int(self._corridas_disputadas())
        corridas_restantes = max(total_rodadas - corridas_disputadas, 0)
        if corridas_restantes <= 0:
            return 0

        validacao_rodada = validar_integridade_rodada(self.banco, categorias_alvo)
        if not validacao_rodada.get("valido", True):
            raise ValueError(
                "Conflito de calendario detectado no fechamento da temporada: "
                f"{validacao_rodada}"
            )

        simuladas = 0
        for indice_rodada in range(corridas_restantes):
            rodada = corridas_disputadas + indice_rodada + 1
            for categoria_id in categorias_alvo:
                resultado = simular_corrida_categoria(self.banco, categoria_id)
                if not isinstance(resultado, list) or not resultado:
                    continue
                aplicados = self._aplicar_classificacao_categoria(
                    categoria_id=categoria_id,
                    classificacao=resultado,
                    rodada=rodada,
                )
                if aplicados > 0:
                    calcular_pontos_equipes(self.banco, categoria_id)
                    simuladas += 1

        return simuladas

    def _sincronizar_categoria_pilotos_por_equipe(self):
        """Sincroniza categoria_atual dos pilotos com a categoria da equipe apos movimentacoes."""
        equipes_index = {
            str(equipe.get("id")): equipe
            for equipe in self.banco.get("equipes", [])
            if isinstance(equipe, dict)
        }

        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if piloto.get("aposentado", False):
                continue

            equipe_id = piloto.get("equipe_id")
            if equipe_id in (None, ""):
                continue

            equipe = equipes_index.get(str(equipe_id))
            if not equipe:
                continue

            categoria_equipe = str(
                equipe.get("categoria", equipe.get("categoria_id", piloto.get("categoria_atual", "")))
                or ""
            ).strip()
            if not categoria_equipe:
                continue

            piloto["categoria_atual"] = categoria_equipe
            piloto["equipe_nome"] = equipe.get("nome", piloto.get("equipe_nome"))

    def _processar_promocao_fim_temporada(self, ano: int):
        """
        Processa promocoes/rebaixamentos de equipes para todas as categorias.
        """
        temporada = int(self.banco.get("temporada_atual", 1))
        manager = PromocaoManager()

        equipes_por_categoria: dict[str, list[dict[str, Any]]] = {}
        for categoria in CATEGORIAS:
            categoria_id = str(categoria.get("id", "")).strip()
            if not categoria_id:
                continue

            calcular_pontos_equipes(self.banco, categoria_id)
            equipes_categoria = list(obter_equipes_categoria(self.banco, categoria_id))
            equipes_por_categoria[categoria_id] = equipes_categoria

            equipes_ordenadas = sorted(
                equipes_categoria,
                key=lambda equipe: (
                    -int(equipe.get("pontos_temporada", 0)),
                    -int(equipe.get("vitorias_temporada", 0)),
                    -int(equipe.get("podios_temporada", 0)),
                    str(equipe.get("nome", "")).casefold(),
                ),
            )

            total_equipes = len(equipes_ordenadas)
            for posicao, equipe in enumerate(equipes_ordenadas, start=1):
                manager.registrar_resultado(
                    equipe=equipe,
                    posicao=posicao,
                    pontos=int(equipe.get("pontos_temporada", 0)),
                    total_equipes=total_equipes,
                    temporada=temporada,
                    vitorias=int(equipe.get("vitorias_temporada", 0)),
                    podios=int(equipe.get("podios_temporada", 0)),
                    poles=int(equipe.get("poles_temporada", 0)),
                )

        relatorio = manager.processar_fim_temporada(
            equipes_por_categoria=equipes_por_categoria,
            temporada=temporada,
            banco=self.banco,
            aplicar_automaticamente=True,
        )

        self._sincronizar_categoria_pilotos_por_equipe()
        manager.limpar_cache_temporada()
        _ = ano
        return relatorio

    def _processar_mercado_fim_temporada(
        self,
        aposentadorias_temporada: int = 0,
    ):
        """
        Executa a janela de transferencias via MercadoManager.

        Retorna:
            ResultadoMercado quando pode concluir a temporada
            None quando ha pendencia do jogador
        """
        jogador = self._obter_jogador()
        jogador_id = jogador.get("id") if jogador else None
        temporada = int(self.banco.get("temporada_atual", 1))

        manager = MercadoManager(self.banco)
        self._sincronizar_rosters()
        manager.processar_janela_transferencias(
            temporada=temporada,
            jogador_id=jogador_id,
            aposentadorias_temporada=max(0, int(aposentadorias_temporada)),
        )
        pendencias = manager.obter_pendencias_jogador(jogador_id=jogador_id)

        if pendencias:
            if hasattr(self, "_mostrar_aba_mercado"):
                try:
                    self._mostrar_aba_mercado()
                except Exception:
                    pass

            QMessageBox.information(
                self,
                "Decisao de Mercado Pendente",
                "Voce recebeu propostas de equipe.\n"
                "Decida na aba 'Mercado' para concluir a temporada.",
            )
            return None

        resultado = manager.finalizar_janela(temporada=temporada)
        self._sincronizar_rosters()
        return resultado

    def _salvar_historico_temporada(self, ano: int):
        """Salva o historico da temporada atual para cada piloto ativo."""
        for piloto in self.banco.get("pilotos", []):
            if piloto.get("aposentado", False):
                continue

            piloto.setdefault("historico_temporadas", [])

            posicao_final = calcular_posicao_campeonato(
                self.banco,
                piloto,
                piloto.get("categoria_atual", "mazda_rookie"),
            )

            piloto["historico_temporadas"].append(
                {
                    "ano": ano,
                    "categoria": piloto.get("categoria_atual", ""),
                    "equipe_nome": piloto.get("equipe_nome", ""),
                    "posicao_final": posicao_final,
                    "pontos": int(piloto.get("pontos_temporada", 0)),
                    "vitorias": int(piloto.get("vitorias_temporada", 0)),
                    "podios": int(piloto.get("podios_temporada", 0)),
                    "poles": int(piloto.get("poles_temporada", 0)),
                    "voltas_rapidas": int(piloto.get("voltas_rapidas_temporada", 0)),
                    "dnfs": int(piloto.get("dnfs_temporada", 0)),
                }
            )

        self.banco.setdefault("historico_temporadas_completas", [])

        for categoria in CATEGORIAS:
            pilotos_categoria = obter_pilotos_categoria(self.banco, categoria["id"])
            pilotos_ordenados = sorted(
                pilotos_categoria,
                key=lambda piloto: (
                    -int(piloto.get("pontos_temporada", 0)),
                    -int(piloto.get("vitorias_temporada", 0)),
                    -int(piloto.get("podios_temporada", 0)),
                    str(piloto.get("nome", "")).casefold(),
                ),
            )

            classificacao = []
            for posicao, piloto in enumerate(pilotos_ordenados):
                classificacao.append(
                    {
                        "posicao": posicao + 1,
                        "piloto": piloto.get("nome", ""),
                        "piloto_id": piloto.get("id"),
                        "equipe": piloto.get("equipe_nome", ""),
                        "pontos": int(piloto.get("pontos_temporada", 0)),
                        "vitorias": int(piloto.get("vitorias_temporada", 0)),
                        "podios": int(piloto.get("podios_temporada", 0)),
                        "poles": int(piloto.get("poles_temporada", 0)),
                        "voltas_rapidas": int(piloto.get("voltas_rapidas_temporada", 0)),
                        "resultados": piloto.get("resultados_temporada", []).copy(),
                    }
                )

            mapa_vmr_categoria_raw = self.banco.get("volta_rapida_por_rodada", {}).get(categoria["id"], {})
            mapa_vmr_categoria: dict[str, dict] = {}
            if isinstance(mapa_vmr_categoria_raw, dict):
                for rodada, registro in mapa_vmr_categoria_raw.items():
                    if isinstance(registro, dict):
                        mapa_vmr_categoria[str(rodada)] = dict(registro)
                    elif isinstance(registro, str):
                        mapa_vmr_categoria[str(rodada)] = {"piloto_nome": registro}

            self.banco["historico_temporadas_completas"].append(
                {
                    "ano": ano,
                    "categoria_id": categoria["id"],
                    "categoria_nome": categoria["nome"],
                    "classificacao": classificacao,
                    "volta_rapida_por_rodada": mapa_vmr_categoria,
                }
            )

    def _processar_evolucao_fim_temporada(self, ano: int) -> tuple[list[dict], list[dict[str, Any]]]:
        """
        Executa pipeline completo do M6 no fechamento da temporada.
        """
        manager = EvolucaoManager()
        temporada = int(self.banco.get("temporada_atual", 1))
        aposentados: list[dict] = []
        relatorios: list[dict[str, Any]] = []

        pilotos_ativos = [
            piloto
            for piloto in self.banco.get("pilotos", [])
            if isinstance(piloto, dict)
            and not bool(piloto.get("aposentado", False))
            and str(piloto.get("status", "ativo") or "ativo").strip().lower() != "aposentado"
        ]

        for piloto in pilotos_ativos:
            pilot_id = str(piloto.get("id", ""))
            temporadas_na_categoria = int(piloto.get("temporadas_na_categoria", 1) or 1)
            manager.iniciar_temporada(
                pilot_id,
                temporadas_na_categoria=max(1, temporadas_na_categoria),
            )

            contexto = manager.construir_contexto_temporada(
                pilot=piloto,
                banco=self.banco,
                temporada=temporada,
            )
            relatorio = manager.processar_fim_temporada(piloto, contexto)

            relatorios.append(
                {
                    "pilot_id": relatorio.pilot_id,
                    "pilot_name": relatorio.pilot_name,
                    "idade": relatorio.idade,
                    "skill_anterior": relatorio.skill_anterior,
                    "skill_novo": relatorio.skill_novo,
                    "motivacao_media": relatorio.motivacao_media,
                    "aposentou": relatorio.aposentou,
                    "causa_aposentadoria": (
                        relatorio.causa_aposentadoria.value
                        if relatorio.causa_aposentadoria is not None
                        else None
                    ),
                }
            )

            if relatorio.aposentou:
                equipe_id = piloto.get("equipe_id")
                categoria_id = piloto.get("categoria_atual")
                manager.aposentar_piloto_no_banco(piloto, banco=self.banco)
                self._sincronizar_rosters()
                aposentados.append(
                    {
                        "nome": piloto.get("nome", "Piloto sem nome"),
                        "idade": int(piloto.get("idade", 0) or 0),
                        "equipe": equipe_id,
                        "categoria": categoria_id,
                        "causa": (
                            relatorio.causa_aposentadoria.value
                            if relatorio.causa_aposentadoria is not None
                            else "desconhecida"
                        ),
                        "ano": ano,
                    }
                )

        self._sincronizar_rosters()
        return aposentados, relatorios

    def _resetar_stats_temporada(self):
        """Zera os numeros da temporada para pilotos e equipes."""
        for piloto in self.banco.get("pilotos", []):
            if piloto.get("aposentado", False):
                continue

            piloto["pontos_temporada"] = 0
            piloto["vitorias_temporada"] = 0
            piloto["podios_temporada"] = 0
            piloto["dnfs_temporada"] = 0
            piloto["corridas_temporada"] = 0
            piloto["resultados_temporada"] = []
            piloto["poles_temporada"] = 0
            piloto["voltas_rapidas_temporada"] = 0
            piloto["incidentes_temporada"] = 0
            piloto["melhor_resultado_temporada"] = 99
            piloto["historico_motivacao_temporada"] = []
            piloto["evolucao_resultados_temporada"] = []
            piloto["evolucao_expectativas_temporada"] = []

        for equipe in self.banco.get("equipes", []):
            equipe["pontos_temporada"] = 0
            equipe["vitorias_temporada"] = 0
            equipe["podios_temporada"] = 0

        # Limpa metadados de volta rapida por rodada para a nova temporada.
        self.banco["volta_rapida_por_rodada"] = {}

    @staticmethod
    def _rotulo_papel_mercado_narrativo(papel_raw: Any) -> str:
        papel = str(papel_raw or "").strip().lower()
        if papel in {"numero_1", "n1"}:
            return "N1"
        if papel in {"numero_2", "n2"}:
            return "N2"
        if papel == "reserva":
            return "Reserva"
        return papel.upper() if papel else "-"

    def _coletar_transferencias_narrativas(self, resultado_mercado: Any) -> list[dict[str, Any]]:
        contratos_novos = list(getattr(resultado_mercado, "contratos_novos", []) or [])
        if not contratos_novos:
            return []

        pilotos_por_id = {
            str(p.get("id")): p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict) and p.get("id") not in (None, "")
        }
        vistos: set[tuple[str, str, str, int]] = set()
        transferencias: list[dict[str, Any]] = []

        for contrato in contratos_novos:
            piloto_id = str(getattr(contrato, "piloto_id", "") or "")
            piloto_nome = str(getattr(contrato, "piloto_nome", "Piloto") or "Piloto")
            destino = str(getattr(contrato, "equipe_nome", "Equipe") or "Equipe")
            duracao = int(getattr(contrato, "duracao_anos", 1) or 1)
            papel = self._rotulo_papel_mercado_narrativo(getattr(contrato, "papel", ""))
            piloto_ref = pilotos_por_id.get(piloto_id, {})

            categoria_destino_id = str(
                piloto_ref.get("categoria_atual", getattr(contrato, "categoria_id", ""))
                or getattr(contrato, "categoria_id", "")
            ).strip()
            categoria_destino = (
                obter_nome_categoria(categoria_destino_id) if categoria_destino_id else "-"
            )

            origem = "Equipe anterior"
            historico_eq = piloto_ref.get("historico_equipes", [])
            if isinstance(historico_eq, list) and historico_eq:
                ult = next(
                    (
                        item
                        for item in reversed(historico_eq)
                        if isinstance(item, dict)
                        and str(item.get("equipe_nome", "") or "").strip()
                    ),
                    None,
                )
                if isinstance(ult, dict):
                    origem = str(ult.get("equipe_nome", origem) or origem)
            elif isinstance(piloto_ref, dict):
                origem = str(
                    piloto_ref.get("equipe_anterior_nome", piloto_ref.get("origem_equipe", origem))
                    or origem
                )

            if origem.strip().casefold() == destino.strip().casefold():
                continue

            chave = (
                piloto_nome.strip().casefold(),
                origem.strip().casefold(),
                destino.strip().casefold(),
                duracao,
            )
            if chave in vistos:
                continue
            vistos.add(chave)
            transferencias.append(
                {
                    "piloto_id": piloto_id,
                    "piloto": piloto_nome,
                    "origem": origem,
                    "destino": destino,
                    "categoria": categoria_destino,
                    "papel": papel,
                    "duracao": duracao,
                }
            )

        return transferencias

    def _coletar_aposentadorias_narrativas(self, aposentados: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(aposentados, list) or not aposentados:
            return []

        aposentadorias: list[dict[str, Any]] = []
        pilotos_nome = {
            str(p.get("nome", "") or "").strip().casefold(): p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict)
        }
        for item in aposentados:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("nome", "Piloto") or "Piloto")
            ref = pilotos_nome.get(nome.strip().casefold(), {})
            historico = ref.get("historico_temporadas", [])
            if isinstance(historico, list):
                temporadas = len(historico)
            else:
                temporadas = 0
            aposentadorias.append(
                {
                    "piloto": nome,
                    "idade": int(item.get("idade", ref.get("idade", 0)) or 0),
                    "temporadas": max(1, temporadas),
                    "titulos": int(ref.get("titulos", 0) or 0),
                    "vitorias": int(ref.get("vitorias_carreira", 0) or 0),
                }
            )
        return aposentadorias

    def _coletar_rookies_narrativos(self, resultado_mercado: Any) -> list[dict[str, Any]]:
        rookies_ids = list(getattr(resultado_mercado, "rookies_gerados", []) or [])
        if not rookies_ids:
            return []
        pilotos_por_id = {
            str(p.get("id")): p for p in self.banco.get("pilotos", []) if isinstance(p, dict)
        }
        saida: list[dict[str, Any]] = []
        for rookie_id in rookies_ids:
            piloto = pilotos_por_id.get(str(rookie_id), {})
            if not isinstance(piloto, dict) or not piloto:
                continue
            categoria_id = str(piloto.get("categoria_atual", "") or "").strip()
            saida.append(
                {
                    "piloto": str(piloto.get("nome", "Rookie") or "Rookie"),
                    "idade": int(piloto.get("idade", 0) or 0),
                    "equipe": str(piloto.get("equipe_nome", "Sem equipe") or "Sem equipe"),
                    "categoria": obter_nome_categoria(categoria_id) if categoria_id else "-",
                }
            )
        return saida

    def _coletar_mapa_promocoes_visual(
        self,
        relatorio_promocao: dict[str, Any] | None,
    ) -> dict[str, Any]:
        elite_categorias = {"gt4", "gt3", "endurance"}
        mapa = {
            "pro": {"promovidas": [], "rebaixadas": []},
            "elite": {"promovidas": [], "rebaixadas": []},
            "equipe_jogador": "",
        }
        jogador = self._obter_jogador()
        if isinstance(jogador, dict):
            mapa["equipe_jogador"] = str(jogador.get("equipe_nome", "") or "").strip()

        if not isinstance(relatorio_promocao, dict) or not relatorio_promocao:
            return mapa

        for tipo_lista, chave_destino in (("promocoes", "promovidas"), ("rebaixamentos", "rebaixadas")):
            movimentos = relatorio_promocao.get(tipo_lista, [])
            if not isinstance(movimentos, list):
                continue
            for mov in movimentos:
                if not isinstance(mov, dict):
                    continue
                origem = str(mov.get("categoria_origem_id", "") or "").strip()
                destino = str(mov.get("categoria_destino_id", "") or "").strip()
                equipe = str(mov.get("equipe_nome", "Equipe") or "Equipe")
                trilha = "elite" if (origem in elite_categorias or destino in elite_categorias) else "pro"
                mapa[trilha][chave_destino].append(
                    {
                        "equipe": equipe,
                        "origem": obter_nome_categoria(origem) if origem else origem or "-",
                        "destino": obter_nome_categoria(destino) if destino else destino or "-",
                        "destaque_jogador": bool(
                            mapa["equipe_jogador"]
                            and equipe.strip().casefold() == mapa["equipe_jogador"].strip().casefold()
                        ),
                    }
                )
        return mapa

    def _registrar_noticias_fim_temporada(
        self,
        *,
        ano: int,
        transferencias: list[dict[str, Any]],
        aposentadorias: list[dict[str, Any]],
        rookies: list[dict[str, Any]],
        mapa_promocoes: dict[str, Any],
    ) -> None:
        gerador = self._obter_gerador_noticias()
        for item in transferencias[:24]:
            if not isinstance(item, dict):
                continue
            gerador.gerar_noticia_mercado(transferencia=item, temporada=ano)
        for item in aposentadorias[:20]:
            if not isinstance(item, dict):
                continue
            gerador.gerar_noticia_aposentadoria(piloto=item, temporada=ano)
        if rookies:
            gerador.gerar_noticia_rookie(rookies=rookies, temporada=ano)

        for trilha in ("pro", "elite"):
            bloco = mapa_promocoes.get(trilha, {})
            if not isinstance(bloco, dict):
                continue
            for mov in bloco.get("promovidas", [])[:20]:
                if not isinstance(mov, dict):
                    continue
                gerador.gerar_noticia_promocao(
                    equipe=str(mov.get("equipe", "Equipe") or "Equipe"),
                    origem=str(mov.get("origem", "-") or "-"),
                    destino=str(mov.get("destino", "-") or "-"),
                    temporada=ano,
                    tipo_evento="promocao",
                )
            for mov in bloco.get("rebaixadas", [])[:20]:
                if not isinstance(mov, dict):
                    continue
                gerador.gerar_noticia_promocao(
                    equipe=str(mov.get("equipe", "Equipe") or "Equipe"),
                    origem=str(mov.get("origem", "-") or "-"),
                    destino=str(mov.get("destino", "-") or "-"),
                    temporada=ano,
                    tipo_evento="rebaixamento",
                )

    def _exibir_resumo_temporada(
        self,
        ano: int,
        aposentados: list[dict],
        resultado_mercado=None,
        relatorio_promocao: dict[str, Any] | None = None,
        evolucao_jogador: list[dict[str, Any]] | None = None,
        relatorios_evolucao: list[dict[str, Any]] | None = None,
    ):
        """Mostra um dialogo com abas de fechamento de temporada."""
        pilotos_cat = obter_pilotos_categoria(self.banco, self.categoria_atual)
        pilotos_ord = self._ordenar_pilotos_campeonato(pilotos_cat)
        campeao = pilotos_ord[0] if pilotos_ord else None

        jogador = self._obter_jogador()
        pos_jogador = None
        if jogador:
            pos_jogador = calcular_posicao_campeonato(
                self.banco,
                jogador,
                jogador.get("categoria_atual", "mazda_rookie"),
            )

        resumo_linhas = [f"Posicao final: P{pos_jogador or '-'}"]
        if jogador:
            resumo_linhas.extend(
                [
                    f"Vitorias: {int(jogador.get('vitorias_temporada', 0) or 0)}",
                    f"Podios: {int(jogador.get('podios_temporada', 0) or 0)}",
                    f"Poles: {int(jogador.get('poles_temporada', 0) or 0)}",
                    f"Pontos: {int(jogador.get('pontos_temporada', 0) or 0)}",
                    f"Melhor resultado: P{int(jogador.get('melhor_resultado_temporada', 99) or 99)}",
                ]
            )
        if campeao:
            resumo_linhas.append("")
            resumo_linhas.append(
                f"Campeao da categoria: {campeao.get('nome', 'Piloto sem nome')}"
            )
        if aposentados:
            resumo_linhas.append("")
            resumo_linhas.append(f"Aposentadorias: {len(aposentados)}")
            for aposentado in aposentados[:10]:
                nome = str(aposentado.get("nome", "Piloto sem nome"))
                idade = int(aposentado.get("idade", 0) or 0)
                resumo_linhas.append(f"- {nome} ({idade} anos)")

        evolucao_linhas = []
        deltas = [
            item for item in (evolucao_jogador or []) if isinstance(item, dict)
        ]
        if deltas:
            cresceu = sum(1 for item in deltas if int(item.get("delta", 0) or 0) > 0)
            declinou = sum(1 for item in deltas if int(item.get("delta", 0) or 0) < 0)
            estavel = sum(1 for item in deltas if int(item.get("delta", 0) or 0) == 0)
            ganho_total = sum(max(0, int(item.get("delta", 0) or 0)) for item in deltas)
            queda_skill_fitness = any(
                str(item.get("campo", "") or "") in {"skill", "fitness"}
                and int(item.get("delta", 0) or 0) < 0
                for item in deltas
            )
            delta_motivacao = next(
                (
                    int(item.get("delta", 0) or 0)
                    for item in deltas
                    if str(item.get("campo", "") or "") == "motivacao"
                ),
                0,
            )

            resumo_evolucao = (
                f"Resumo: {cresceu} atributos cresceram, {declinou} declinaram, {estavel} sem mudanca."
            )
            mensagens_contexto: list[str] = []
            if ganho_total > 5:
                mensagens_contexto.append("Temporada de grande evolucao!")
            if queda_skill_fitness:
                mensagens_contexto.append("Idade comecando a pesar.")
            if delta_motivacao > 0:
                mensagens_contexto.append("Motivacao em alta!")
            elif delta_motivacao < 0:
                mensagens_contexto.append("Motivacao em queda - cuidado.")
            contexto_evolucao = " ".join(mensagens_contexto).strip()

            evolucao_linhas.append("Seus atributos mudaram:")
            evolucao_linhas.append("")
            for item in deltas:
                rotulo = str(item.get("rotulo", item.get("campo", "Atributo")) or "Atributo")
                antes = int(item.get("antes", 0) or 0)
                depois = int(item.get("depois", 0) or 0)
                delta = int(item.get("delta", 0) or 0)
                if delta > 0:
                    simbolo = "UP"
                elif delta < 0:
                    simbolo = "DOWN"
                else:
                    simbolo = "EQ"
                evolucao_linhas.append(f"{rotulo}: {antes} -> {depois} ({delta:+d}) {simbolo}")
            evolucao_linhas.append("")
            evolucao_linhas.append(resumo_evolucao)
            if contexto_evolucao:
                evolucao_linhas.append(contexto_evolucao)
        else:
            resumo_evolucao = "Resumo: sem variacoes registradas."
            contexto_evolucao = ""
            evolucao_linhas.append("Sem mudancas relevantes de atributos do jogador.")

        relatorios = [
            item for item in (relatorios_evolucao or []) if isinstance(item, dict)
        ]
        if relatorios:
            evolucao_linhas.append("")
            evolucao_linhas.append(
                f"Pilotos avaliados pelo M6: {len(relatorios)}"
            )
            total_aposentou = sum(1 for item in relatorios if bool(item.get("aposentou", False)))
            evolucao_linhas.append(f"Aposentaram no M6: {total_aposentou}")

        transferencias_narrativas = self._coletar_transferencias_narrativas(resultado_mercado)
        aposentadorias_narrativas = self._coletar_aposentadorias_narrativas(aposentados)
        rookies_narrativos = self._coletar_rookies_narrativos(resultado_mercado)
        mapa_promocoes_visual = self._coletar_mapa_promocoes_visual(relatorio_promocao)

        mercado_linhas = []
        if resultado_mercado:
            mercado_linhas.extend(
                [
                    f"Propostas recebidas: {int(resultado_mercado.total_propostas)}",
                    f"Aceitas: {int(resultado_mercado.propostas_aceitas)}",
                    f"Recusadas: {int(resultado_mercado.propostas_recusadas)}",
                    f"Sem vaga (reserva global): {len(resultado_mercado.pilotos_sem_vaga)}",
                    f"Rookies gerados: {len(resultado_mercado.rookies_gerados)}",
                    "",
                    "TRANSFERENCIAS PRINCIPAIS:",
                ]
            )
            if transferencias_narrativas:
                for item in transferencias_narrativas[:24]:
                    mercado_linhas.append(
                        f"- {item['piloto']}: {item['origem']} -> {item['destino']} "
                        f"({item['categoria']}) - {item['papel']}, {item['duracao']} ano(s)"
                    )
            else:
                mercado_linhas.append("- Sem transferencias relevantes.")

            mercado_linhas.append("")
            mercado_linhas.append("APOSENTADORIAS:")
            if aposentadorias_narrativas:
                for item in aposentadorias_narrativas[:20]:
                    mercado_linhas.append(
                        f"- {item['piloto']} ({item['idade']}) - {item['temporadas']} temporada(s), "
                        f"{item['titulos']} titulo(s), {item['vitorias']} vitoria(s)"
                    )
            else:
                mercado_linhas.append("- Nenhuma aposentadoria registrada.")

            mercado_linhas.append("")
            mercado_linhas.append("ROOKIES:")
            if rookies_narrativos:
                for item in rookies_narrativos[:20]:
                    mercado_linhas.append(
                        f"- {item['piloto']} ({item['idade']}) -> {item['equipe']} ({item['categoria']})"
                    )
            else:
                mercado_linhas.append("- Nenhum rookie novo nesta janela.")
        else:
            mercado_linhas.append("Mercado sem dados para esta temporada.")

        jogador_nome = str(jogador.get("nome", "Voce") or "Voce") if isinstance(jogador, dict) else "Voce"
        equipe_jogador = str(jogador.get("equipe_nome", "Sem equipe") or "Sem equipe") if isinstance(jogador, dict) else "Sem equipe"
        equipe_ref = next(
            (
                equipe
                for equipe in self.banco.get("equipes", [])
                if isinstance(equipe, dict)
                and str(equipe.get("nome", "") or "").strip().casefold() == equipe_jogador.strip().casefold()
            ),
            {},
        )
        pilotos_equipe = []
        if isinstance(equipe_ref, dict):
            for chave in ("piloto_1", "piloto_2"):
                nome_p = str(equipe_ref.get(chave, "") or "").strip()
                if nome_p:
                    pilotos_equipe.append(nome_p)
        pilotos_equipe_txt = " + ".join(pilotos_equipe) if pilotos_equipe else "line-up indisponivel"
        sua_equipe_antes = f"{equipe_jogador} - {jogador_nome} + companheiro anterior"
        sua_equipe_depois = f"{equipe_jogador} - {pilotos_equipe_txt}"
        entradas_sua_equipe = [
            item
            for item in transferencias_narrativas
            if str(item.get("destino", "") or "").strip().casefold() == equipe_jogador.strip().casefold()
        ]
        if entradas_sua_equipe:
            pilotos_novos = ", ".join(str(item.get("piloto", "Piloto")) for item in entradas_sua_equipe[:2])
            sua_equipe_depois = f"{equipe_jogador} - {jogador_nome} + {pilotos_novos}"

        promocoes_linhas = []
        bloco_pro = mapa_promocoes_visual.get("pro", {})
        bloco_elite = mapa_promocoes_visual.get("elite", {})
        promocoes_linhas.append("PROMOVIDAS/REBAIXADAS")
        for titulo, bloco in (("TRILHA PRO", bloco_pro), ("TRILHA ELITE", bloco_elite)):
            promocoes_linhas.append("")
            promocoes_linhas.append(f"{titulo}:")
            promovidas = bloco.get("promovidas", []) if isinstance(bloco, dict) else []
            rebaixadas = bloco.get("rebaixadas", []) if isinstance(bloco, dict) else []
            promocoes_linhas.append("  Promovidas:")
            if promovidas:
                for mov in promovidas[:20]:
                    if not isinstance(mov, dict):
                        continue
                    destaque = " <SUA EQUIPE>" if bool(mov.get("destaque_jogador", False)) else ""
                    promocoes_linhas.append(
                        f"    - {mov.get('equipe', 'Equipe')}: {mov.get('origem', '-')} -> {mov.get('destino', '-')}{destaque}"
                    )
            else:
                promocoes_linhas.append("    - Nenhuma")
            promocoes_linhas.append("  Rebaixadas:")
            if rebaixadas:
                for mov in rebaixadas[:20]:
                    if not isinstance(mov, dict):
                        continue
                    destaque = " <SUA EQUIPE>" if bool(mov.get("destaque_jogador", False)) else ""
                    promocoes_linhas.append(
                        f"    - {mov.get('equipe', 'Equipe')}: {mov.get('origem', '-')} -> {mov.get('destino', '-')}{destaque}"
                    )
            else:
                promocoes_linhas.append("    - Nenhuma")

        self._registrar_noticias_fim_temporada(
            ano=ano,
            transferencias=transferencias_narrativas,
            aposentadorias=aposentadorias_narrativas,
            rookies=rookies_narrativos,
            mapa_promocoes=mapa_promocoes_visual,
        )

        dados_dialogo = {
            "resumo": "\n".join(resumo_linhas),
            "evolucao": "\n".join(evolucao_linhas),
            "evolucao_detalhada": deltas,
            "evolucao_resumo": resumo_evolucao,
            "evolucao_contexto": contexto_evolucao,
            "mercado": "\n".join(mercado_linhas),
            "promocoes": "\n".join(promocoes_linhas),
            "mercado_narrativo": {
                "transferencias": transferencias_narrativas,
                "aposentadorias": aposentadorias_narrativas,
                "rookies": rookies_narrativos,
                "sua_equipe_antes": sua_equipe_antes,
                "sua_equipe_depois": sua_equipe_depois,
            },
            "promocoes_mapa": mapa_promocoes_visual,
        }

        try:
            from UI.dialogs import DialogFimTemporada

            dialogo = DialogFimTemporada(ano=ano, dados=dados_dialogo, parent=self)
            dialogo.exec()
        except Exception:
            fallback = (
                "\n\n".join(
                    [
                        "=== RESUMO ===\n" + dados_dialogo["resumo"],
                        "=== EVOLUCAO ===\n" + dados_dialogo["evolucao"],
                        "=== MERCADO ===\n" + dados_dialogo["mercado"],
                        "=== PROMOCOES ===\n" + dados_dialogo["promocoes"],
                    ]
                )
                + f"\n\nAvancando para {ano + 1}."
            )
            QMessageBox.information(self, f"Fim da Temporada {ano}", fallback)
