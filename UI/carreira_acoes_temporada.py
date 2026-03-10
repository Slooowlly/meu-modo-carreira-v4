from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from Dados.banco import salvar_banco
from Dados.constantes import CATEGORIAS
from Logica.equipes import (
    calcular_pontos_equipes,
    evolucionar_equipes,
    obter_equipes_categoria,
)
from Logica.mercado import MercadoManager
from Logica.pilotos import (
    aposentar_piloto,
    calcular_posicao_campeonato,
    envelhecer_pilotos,
    obter_pilotos_categoria,
)
from Logica.promocao import PromocaoManager, relatorio_to_dict
from Logica.series_especiais import inicializar_production_car_challenge
from UI.carreira_acoes import CarreiraAcoesBaseMixin


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

        # 2) Pre-fechamento (historico + aposentadorias), processado uma vez.
        ano, aposentados = self._garantir_pre_fechamento_temporada()
        if ano <= 0:
            ano = int(self.banco.get("ano_atual", 2024))

        # 3) Promocao/rebaixamento de equipes (idempotente).
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

        # 4/5) Mercado (com clausulas de contrato ja aplicadas no modulo de promocao).
        resultado_mercado = self._processar_mercado_fim_temporada()
        if resultado_mercado is None:
            # Pendencia do jogador bloqueia avanco da temporada sem repetir simulacao/promocao.
            salvar_banco(self.banco)
            self._atualizar_tudo()
            return

        # 6) Evolucao/reset existentes.
        envelhecer_pilotos(self.banco)
        evolucionar_equipes(self.banco)

        # Exibe antes de resetar os numeros da temporada.
        self._exibir_resumo_temporada(
            ano,
            aposentados,
            resultado_mercado=resultado_mercado,
            relatorio_promocao=relatorio_promocao,
        )

        self._resetar_stats_temporada()

        self.banco["ano_atual"] = ano + 1
        self.banco["temporada_atual"] = int(self.banco.get("temporada_atual", 1)) + 1
        self.banco["rodada_atual"] = 1
        self.banco["temporada_concluida"] = False
        inicializar_production_car_challenge(self.banco, self.banco["ano_atual"])
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
            "simulacao_ai_concluida": False,
            "promocao_processada": False,
            "relatorio_promocao": {},
        }
        for chave, valor_padrao in defaults.items():
            if chave not in fechamento:
                fechamento[chave] = valor_padrao

        if not isinstance(fechamento.get("aposentados"), list):
            fechamento["aposentados"] = []
        if not isinstance(fechamento.get("relatorio_promocao"), dict):
            fechamento["relatorio_promocao"] = {}

        fechamento["em_andamento"] = bool(fechamento.get("em_andamento", False))
        fechamento["simulacao_ai_concluida"] = bool(fechamento.get("simulacao_ai_concluida", False))
        fechamento["promocao_processada"] = bool(fechamento.get("promocao_processada", False))

        try:
            fechamento["ano_base"] = int(fechamento.get("ano_base", 0) or 0)
        except (TypeError, ValueError):
            fechamento["ano_base"] = 0

        return fechamento

    def _garantir_pre_fechamento_temporada(self) -> tuple[int, list[dict]]:
        """
        Garante que historico e aposentadorias sejam processados uma unica vez
        antes da janela de mercado.
        """
        fechamento = self._estado_fechamento_temporada()
        if fechamento.get("em_andamento", False):
            ano_ref = int(fechamento.get("ano_base", self.banco.get("ano_atual", 2024)))
            aposentados_ref = list(fechamento.get("aposentados", []))
            return ano_ref, aposentados_ref

        ano = int(self.banco.get("ano_atual", 2024))
        self._salvar_historico_temporada(ano)
        aposentados = self._processar_aposentadorias(ano)

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
        fechamento["simulacao_ai_concluida"] = False
        fechamento["promocao_processada"] = False
        fechamento["relatorio_promocao"] = {}

    def _aplicar_classificacao_categoria(
        self,
        categoria_id: str,
        classificacao: list[dict[str, Any]],
        rodada: int | None = None,
    ) -> int:
        """Aplica classificacao simulada em uma categoria especifica."""
        aplicados = 0
        for posicao, entrada in enumerate(classificacao, start=1):
            piloto_id = entrada.get("piloto_id", entrada.get("id"))
            piloto = self._obter_piloto_por_id(piloto_id, categoria_id)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
            )
            aplicados += 1

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=categoria_id,
                rodada=rodada,
            )

        return aplicados

    def _simular_categorias_nao_ativas_fechamento(self) -> int:
        """
        Simula corridas restantes para categorias nao ativas no fechamento da temporada.
        Retorna o total de simulacoes aplicadas.
        """
        from Logica.simulacao import simular_corrida_categoria

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

    def _processar_mercado_fim_temporada(self):
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
        manager.processar_janela_transferencias(
            temporada=temporada,
            jogador_id=jogador_id,
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

        return manager.finalizar_janela(temporada=temporada)

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

    def _processar_aposentadorias(self, ano: int) -> list[dict]:
        """Aposenta pilotos que atingiram o limite de idade."""
        idade_limite = int(self.banco.get("idade_aposentadoria", 42))
        aposentados = []

        pilotos_ativos = [
            piloto
            for piloto in self.banco.get("pilotos", [])
            if not piloto.get("aposentado", False)
            and not piloto.get("is_jogador", False)
        ]

        for piloto in pilotos_ativos:
            if piloto.get("aposentado", False):
                continue

            try:
                idade = int(piloto.get("idade", 0))
            except (TypeError, ValueError):
                idade = 0

            if idade >= idade_limite:
                equipe_id = piloto.get("equipe_id")
                categoria_id = piloto.get("categoria_atual")
                aposentar_piloto(self.banco, piloto, ano)
                aposentados.append(
                    {
                        "nome": piloto.get("nome", "Piloto sem nome"),
                        "idade": idade,
                        "equipe": equipe_id,
                        "categoria": categoria_id,
                    }
                )

        return aposentados

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

        for equipe in self.banco.get("equipes", []):
            equipe["pontos_temporada"] = 0
            equipe["vitorias_temporada"] = 0
            equipe["podios_temporada"] = 0

        # Limpa metadados de volta rapida por rodada para a nova temporada.
        self.banco["volta_rapida_por_rodada"] = {}

    def _exibir_resumo_temporada(
        self,
        ano: int,
        aposentados: list[dict],
        resultado_mercado=None,
        relatorio_promocao: dict[str, Any] | None = None,
    ):
        """Mostra o resumo final da temporada."""
        pilotos_cat = obter_pilotos_categoria(self.banco, self.categoria_atual)
        pilotos_ord = self._ordenar_pilotos_campeonato(pilotos_cat)
        campeao = pilotos_ord[0] if pilotos_ord else None

        resumo = f"Resumo da Temporada {ano}\n\n"

        if campeao:
            resumo += f"Campeao: {campeao.get('nome', 'Piloto sem nome')}\n"
            resumo += f"   Pontos: {campeao.get('pontos_temporada', 0)}\n"
            resumo += f"   Vitorias: {campeao.get('vitorias_temporada', 0)}\n\n"

        jogador = self._obter_jogador()
        if jogador:
            pos = calcular_posicao_campeonato(
                self.banco,
                jogador,
                jogador.get("categoria_atual", "mazda_rookie"),
            )
            resumo += f"Sua posicao: P{pos}\n"
            resumo += f"   Pontos: {jogador.get('pontos_temporada', 0)}\n\n"

        if aposentados:
            resumo += f"Aposentadorias: {len(aposentados)}\n"
            for aposentado in aposentados:
                resumo += f"   - {aposentado['nome']} ({aposentado['idade']} anos)\n"
            resumo += "\n"

        if isinstance(relatorio_promocao, dict) and relatorio_promocao:
            promocoes = relatorio_promocao.get("promocoes", [])
            rebaixamentos = relatorio_promocao.get("rebaixamentos", [])
            liberados = int(relatorio_promocao.get("total_pilotos_liberados", 0) or 0)
            resumo += "Promocao/Rebaixamento:\n"
            resumo += f"   Promocoes: {len(promocoes) if isinstance(promocoes, list) else 0}\n"
            resumo += f"   Rebaixamentos: {len(rebaixamentos) if isinstance(rebaixamentos, list) else 0}\n"
            if liberados > 0:
                resumo += f"   Clausulas de saida ativadas: {liberados}\n"
            resumo += "\n"

        if resultado_mercado:
            resumo += "Mercado:\n"
            resumo += f"   Propostas: {resultado_mercado.total_propostas}\n"
            resumo += f"   Aceitas: {resultado_mercado.propostas_aceitas}\n"
            resumo += f"   Recusadas: {resultado_mercado.propostas_recusadas}\n"
            resumo += f"   Sem vaga (reserva global): {len(resultado_mercado.pilotos_sem_vaga)}\n"
            resumo += f"   Rookies gerados: {len(resultado_mercado.rookies_gerados)}\n\n"

        resumo += f"Avancando para {ano + 1}"
        QMessageBox.information(self, f"Fim da Temporada {ano}", resumo)
