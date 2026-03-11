"""Acoes e UI da aba de mercado com feedback UX opcional."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from Dados.banco import salvar_banco
from Logica.mercado import MercadoManager, Proposta
from UI.carreira_acoes import CarreiraAcoesBaseMixin
from Utils.helpers import obter_nome_categoria


class MercadoMixin(CarreiraAcoesBaseMixin):
    """Acoes e UI da aba Mercado."""

    def _mostrar_aba_mercado(self):
        indice = int(getattr(self, "_indice_aba_mercado", -1))
        if indice >= 0 and hasattr(self, "tabs"):
            self._mostrar_aba(indice)

    def _tem_pendencia_mercado_jogador(self) -> bool:
        jogador = self._obter_jogador()
        if not jogador:
            return False
        manager = MercadoManager(self.banco)
        pendencias = manager.obter_pendencias_jogador(jogador.get("id"))
        return bool(pendencias)

    def _build_tab_mercado(self):
        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        self.lbl_mercado_status = QLabel("Mercado")
        self.lbl_mercado_status.setWordWrap(True)
        self.lbl_mercado_status.setStyleSheet("font-size: 13px; font-weight: 600;")
        root.addWidget(self.lbl_mercado_status)

        acoes = QHBoxLayout()
        acoes.setSpacing(8)

        self.btn_mercado_aceitar = QPushButton("Aceitar Proposta")
        self.btn_mercado_aceitar.clicked.connect(self._mercado_aceitar_proposta_selecionada)
        acoes.addWidget(self.btn_mercado_aceitar)

        self.btn_mercado_recusar = QPushButton("Recusar Proposta")
        self.btn_mercado_recusar.clicked.connect(self._mercado_recusar_proposta_selecionada)
        acoes.addWidget(self.btn_mercado_recusar)

        self.btn_mercado_recusar_todas = QPushButton("Recusar Todas")
        self.btn_mercado_recusar_todas.clicked.connect(self._mercado_recusar_todas)
        acoes.addWidget(self.btn_mercado_recusar_todas)
        acoes.addStretch(1)
        root.addLayout(acoes)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root.addWidget(scroll, 1)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(10)
        scroll.setWidget(body)

        self.tbl_mercado_propostas = self._criar_tabela(
            [
                "ID",
                "Equipe",
                "Categoria",
                "Carro",
                "Perf Carro",
                "Papel",
                "Contrato",
                "Reputacao",
                "Aviso",
                "Status",
            ],
            10,
        )
        body_layout.addWidget(self._secao("Propostas do Jogador", self.tbl_mercado_propostas))

        self.tbl_mercado_vagas = self._criar_tabela(
            ["Equipe", "Categoria", "Papel", "Perf Carro", "Budget", "Reputacao"],
            6,
        )
        body_layout.addWidget(self._secao("Vagas Abertas", self.tbl_mercado_vagas))

        self.tbl_mercado_reserva = self._criar_tabela(
            ["Piloto ID", "Nome", "Status", "Categoria", "Skill"],
            5,
        )
        body_layout.addWidget(self._secao("Pool de Reserva Global", self.tbl_mercado_reserva))

        self.tbl_mercado_rookies = self._criar_tabela(
            ["Piloto ID", "Nome", "Idade", "Potencial", "Equipe Atual"],
            5,
        )
        body_layout.addWidget(self._secao("Rookies da Janela", self.tbl_mercado_rookies))

        self.tbl_mercado_historico = self._criar_tabela(
            ["Temporada", "Propostas", "Aceitas", "Recusadas", "Sem Vaga", "Rookies"],
            6,
        )
        body_layout.addWidget(self._secao("Historico de Janelas", self.tbl_mercado_historico))

        self.lbl_mercado_highlights = QLabel("Highlights")
        self.lbl_mercado_highlights.setWordWrap(True)
        self.lbl_mercado_highlights.setStyleSheet("padding: 8px; border: 1px solid #2a3547; border-radius: 8px;")
        body_layout.addWidget(self._secao("Movimentacoes e Highlights", self.lbl_mercado_highlights))

        return container

    def _criar_tabela(self, colunas: list[str], col_count: int) -> QTableWidget:
        tabela = QTableWidget()
        tabela.setColumnCount(col_count)
        tabela.setHorizontalHeaderLabels(colunas)
        tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabela.verticalHeader().setVisible(False)
        header = tabela.horizontalHeader()
        header.setStretchLastSection(True)
        return tabela

    def _secao(self, titulo: str, widget: QWidget) -> QWidget:
        sec = QWidget()
        lay = QVBoxLayout(sec)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lbl = QLabel(titulo)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
        lay.addWidget(lbl)
        lay.addWidget(widget)
        return sec

    def _mercado_info(self, mensagem: str):
        if hasattr(self, "mostrar_toast_info"):
            self.mostrar_toast_info(mensagem)
            return
        QMessageBox.information(self, "Mercado", mensagem)

    def _mercado_aviso(self, mensagem: str):
        if hasattr(self, "mostrar_toast_aviso"):
            self.mostrar_toast_aviso(mensagem)
            return
        QMessageBox.warning(self, "Mercado", mensagem)

    def _mensagem_loading_mercado(self, acao: str) -> str:
        mensagens = {
            "aceitar": "Processando aceite de proposta...",
            "recusar": "Processando recusa de proposta...",
            "recusar_todas": "Processando recusa de todas as propostas...",
        }
        return mensagens.get(acao, "Processando mercado...")

    @staticmethod
    def _barra_progresso_texto(valor: float, maximo: int = 100, largura: int = 10) -> str:
        try:
            ratio = max(0.0, min(float(valor) / float(maximo), 1.0))
        except (TypeError, ValueError, ZeroDivisionError):
            ratio = 0.0
        preenchidos = int(round(ratio * largura))
        vazios = max(0, largura - preenchidos)
        return ("█" * preenchidos) + ("░" * vazios)

    @staticmethod
    def _rotulo_papel_proposta(papel_raw: Any) -> str:
        papel = str(papel_raw or "").strip().lower()
        if papel in {"numero_1", "n1"}:
            return "N1 (principal)"
        if papel in {"numero_2", "n2"}:
            return "N2"
        if papel == "reserva":
            return "Reserva"
        return papel or "-"

    def _obter_proposta_pendente(
        self,
        proposta_id: str,
        jogador_id: Any,
    ) -> Proposta | None:
        manager = MercadoManager(self.banco)
        pendencias = manager.obter_pendencias_jogador(jogador_id)
        return next(
            (proposta for proposta in pendencias if str(proposta.id) == str(proposta_id)),
            None,
        )

    def _confirmar_aceite_com_aviso_conteudo(
        self,
        proposta: Proposta,
    ) -> bool:
        equipe = self._obter_equipe_por_id_hierarquia(proposta.equipe_id)
        if not self._proposta_requer_conteudo_nao_possuido(proposta.categoria_id, equipe):
            return True

        categoria_nome = obter_nome_categoria(proposta.categoria_id)
        carro = self._descricao_carro_proposta(proposta.categoria_id, equipe)
        resposta = QMessageBox.question(
            self,
            "Aviso de Conteudo iRacing",
            "🏎️ Proposta de equipe\n\n"
            f"Categoria: {categoria_nome}\n"
            f"Carro: {carro}\n\n"
            "⚠️ Voce NAO marcou este conteudo como possuido no iRacing.\n"
            "Voce ainda pode aceitar a proposta.\n\n"
            "Deseja aceitar mesmo assim?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return resposta == QMessageBox.Yes

    def _mercado_aceitar_proposta_selecionada(self):
        proposta_id = self._mercado_proposta_selecionada_id()
        if not proposta_id:
            self._mercado_info("Selecione uma proposta para aceitar.")
            return
        self._aplicar_decisao_mercado("aceitar", proposta_id)

    def _mercado_recusar_proposta_selecionada(self):
        proposta_id = self._mercado_proposta_selecionada_id()
        if not proposta_id:
            self._mercado_info("Selecione uma proposta para recusar.")
            return
        self._aplicar_decisao_mercado("recusar", proposta_id)

    def _mercado_recusar_todas(self):
        resposta = QMessageBox.question(
            self,
            "Mercado",
            "Recusar TODAS as propostas do jogador?\n"
            "Sem proposta aceita, o jogador vira reserva global.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return
        self._aplicar_decisao_mercado("recusar_todas", None)

    def _aplicar_decisao_mercado(self, acao: str, proposta_id: str | None):
        jogador = self._obter_jogador()
        if not jogador:
            self._mercado_aviso("Jogador nao encontrado.")
            return

        if acao == "aceitar" and proposta_id:
            proposta = self._obter_proposta_pendente(proposta_id, jogador.get("id"))
            if proposta is None:
                self._mercado_aviso("Proposta selecionada nao encontrada.")
                return
            if not self._confirmar_aceite_com_aviso_conteudo(proposta):
                return

        def processar():
            manager = MercadoManager(self.banco)
            retorno_local = manager.aplicar_decisao_jogador(
                acao=acao,
                proposta_id=proposta_id,
                jogador_id=jogador.get("id"),
            )
            salvar_banco(self.banco)
            return retorno_local

        def concluir(retorno_local=None):
            retorno = retorno_local if isinstance(retorno_local, dict) else {}
            self._atualizar_aba_mercado()
            self._atualizar_tudo()

            if retorno.get("ok"):
                mensagem = str(retorno.get("mensagem", "Decisao aplicada."))
                if hasattr(self, "mostrar_sucesso_animado"):
                    self.mostrar_sucesso_animado()
                if hasattr(self, "mostrar_notificacao_mercado"):
                    tipo = "contratacao" if acao == "aceitar" else "saida"
                    self.mostrar_notificacao_mercado(mensagem, tipo=tipo)
                else:
                    self._mercado_info(mensagem)
            else:
                self._mercado_aviso(str(retorno.get("erro", "Falha ao aplicar decisao.")))

        def falhar(erro):
            self._mercado_aviso(f"Falha ao processar acao de mercado: {erro}")

        try:
            concluir(processar())
        except Exception as erro:  # noqa: BLE001
            falhar(erro)

    def _mercado_proposta_selecionada_id(self) -> str | None:
        if not hasattr(self, "tbl_mercado_propostas"):
            return None
        tabela: QTableWidget = self.tbl_mercado_propostas
        row = tabela.currentRow()
        if row < 0:
            return None
        item = tabela.item(row, 0)
        if not item:
            return None
        return str(item.text()).strip() or None

    def _atualizar_aba_mercado(self):
        if not hasattr(self, "tbl_mercado_propostas"):
            return

        manager = MercadoManager(self.banco)
        jogador = self._obter_jogador()
        jogador_id = jogador.get("id") if jogador else None
        pendencias = manager.obter_pendencias_jogador(jogador_id)
        mercado = self.banco.get("mercado", {})

        self._popular_propostas(pendencias)
        self._popular_vagas(mercado.get("vagas_abertas", []))
        self._popular_reserva(mercado.get("reserva_global", []))
        self._popular_rookies(mercado.get("rookies_gerados", []))
        self._popular_historico(mercado.get("historico_janelas", []))
        self._popular_highlights(mercado.get("resultado_janela_atual", {}))

        tem_pendencia = len(pendencias) > 0
        self.btn_mercado_aceitar.setEnabled(tem_pendencia)
        self.btn_mercado_recusar.setEnabled(tem_pendencia)
        self.btn_mercado_recusar_todas.setEnabled(tem_pendencia)

        janela_aberta = bool(mercado.get("janela_aberta", False))
        temporada_janela = mercado.get("temporada_janela", "-")
        if tem_pendencia:
            texto = (
                f"Temporada {temporada_janela}: voce tem {len(pendencias)} proposta(s) pendente(s). "
                "Decida para liberar o avanco da temporada."
            )
        elif janela_aberta:
            texto = (
                f"Temporada {temporada_janela}: janela aberta sem pendencia do jogador. "
                "Voce ja pode finalizar a temporada."
            )
        else:
            texto = "Sem pendencias do jogador no mercado."
        self.lbl_mercado_status.setText(texto)

    def _popular_propostas(self, propostas: list[Proposta]):
        tabela: QTableWidget = self.tbl_mercado_propostas
        tabela.setRowCount(len(propostas))
        for row, proposta in enumerate(propostas):
            equipe = self._obter_equipe_por_id_hierarquia(proposta.equipe_id)
            categoria_nome = obter_nome_categoria(proposta.categoria_id)
            carro = self._descricao_carro_proposta(proposta.categoria_id, equipe)
            perf = float(proposta.car_performance or 0.0)
            reputacao = float(proposta.reputacao_equipe or 0.0)
            barra_perf = self._barra_progresso_texto(perf, maximo=100, largura=10)
            aviso_conteudo = self._proposta_requer_conteudo_nao_possuido(
                proposta.categoria_id,
                equipe,
            )
            aviso_texto = "⚠ Conteudo nao possuido" if aviso_conteudo else "OK"

            tabela.setItem(row, 0, QTableWidgetItem(str(proposta.id)))
            tabela.setItem(row, 1, QTableWidgetItem(str(proposta.equipe_nome)))
            tabela.setItem(row, 2, QTableWidgetItem(str(categoria_nome)))
            tabela.setItem(row, 3, QTableWidgetItem(carro))
            tabela.setItem(row, 4, QTableWidgetItem(f"{barra_perf} {int(round(perf))}/100"))
            tabela.setItem(row, 5, QTableWidgetItem(self._rotulo_papel_proposta(proposta.papel.value)))
            tabela.setItem(row, 6, QTableWidgetItem(f"{int(proposta.duracao_anos)} ano(s)"))
            tabela.setItem(row, 7, QTableWidgetItem(f"{int(round(reputacao))}/100"))
            item_aviso = QTableWidgetItem(aviso_texto)
            if aviso_conteudo:
                item_aviso.setToolTip(
                    "Voce pode aceitar esta proposta mesmo sem possuir o conteudo."
                )
            tabela.setItem(row, 8, item_aviso)
            tabela.setItem(row, 9, QTableWidgetItem(str(proposta.status.value)))
        if propostas:
            tabela.selectRow(0)

    def _popular_vagas(self, vagas_raw: list[dict[str, Any]]):
        tabela: QTableWidget = self.tbl_mercado_vagas
        vagas = vagas_raw if isinstance(vagas_raw, list) else []
        tabela.setRowCount(len(vagas))
        for row, vaga in enumerate(vagas):
            tabela.setItem(row, 0, QTableWidgetItem(str(vaga.get("equipe_nome", ""))))
            categoria = f"Tier {vaga.get('categoria_tier', 1)} ({vaga.get('categoria_id', '')})"
            tabela.setItem(row, 1, QTableWidgetItem(categoria))
            tabela.setItem(row, 2, QTableWidgetItem(str(vaga.get("papel", ""))))
            tabela.setItem(row, 3, QTableWidgetItem(f"{float(vaga.get('car_performance', 0)):.1f}"))
            tabela.setItem(row, 4, QTableWidgetItem(f"{float(vaga.get('budget_disponivel', 0)):.1f}"))
            tabela.setItem(row, 5, QTableWidgetItem(f"{float(vaga.get('reputacao', 0)):.1f}"))

    def _popular_reserva(self, ids_reserva: list[Any]):
        tabela: QTableWidget = self.tbl_mercado_reserva
        ids = [str(pid) for pid in (ids_reserva or [])]
        pilotos_map = {str(p.get("id")): p for p in self.banco.get("pilotos", []) if isinstance(p, dict)}
        pilotos = [pilotos_map[pid] for pid in ids if pid in pilotos_map]

        tabela.setRowCount(len(pilotos))
        for row, piloto in enumerate(pilotos):
            tabela.setItem(row, 0, QTableWidgetItem(str(piloto.get("id", ""))))
            tabela.setItem(row, 1, QTableWidgetItem(str(piloto.get("nome", ""))))
            tabela.setItem(row, 2, QTableWidgetItem(str(piloto.get("status", ""))))
            tabela.setItem(row, 3, QTableWidgetItem(str(piloto.get("categoria_atual", ""))))
            tabela.setItem(row, 4, QTableWidgetItem(str(piloto.get("skill", ""))))

    def _popular_rookies(self, ids_rookies: list[Any]):
        tabela: QTableWidget = self.tbl_mercado_rookies
        ids = [str(pid) for pid in (ids_rookies or [])]
        pilotos_map = {str(p.get("id")): p for p in self.banco.get("pilotos", []) if isinstance(p, dict)}
        pilotos = [pilotos_map[pid] for pid in ids if pid in pilotos_map]

        tabela.setRowCount(len(pilotos))
        for row, piloto in enumerate(pilotos):
            potencial = float(piloto.get("potencial_base", piloto.get("potencial", 0)) or 0)
            tabela.setItem(row, 0, QTableWidgetItem(str(piloto.get("id", ""))))
            tabela.setItem(row, 1, QTableWidgetItem(str(piloto.get("nome", ""))))
            tabela.setItem(row, 2, QTableWidgetItem(str(piloto.get("idade", ""))))
            tabela.setItem(row, 3, QTableWidgetItem(f"{potencial:.1f}"))
            tabela.setItem(row, 4, QTableWidgetItem(str(piloto.get("equipe_nome", "Sem equipe"))))

    def _popular_historico(self, historico_raw: list[dict[str, Any]]):
        tabela: QTableWidget = self.tbl_mercado_historico
        historico = historico_raw if isinstance(historico_raw, list) else []
        tabela.setRowCount(len(historico))
        for row, item in enumerate(reversed(historico)):
            tabela.setItem(row, 0, QTableWidgetItem(str(item.get("temporada", ""))))
            tabela.setItem(row, 1, QTableWidgetItem(str(item.get("total_propostas", 0))))
            tabela.setItem(row, 2, QTableWidgetItem(str(item.get("propostas_aceitas", 0))))
            tabela.setItem(row, 3, QTableWidgetItem(str(item.get("propostas_recusadas", 0))))
            tabela.setItem(row, 4, QTableWidgetItem(str(len(item.get("pilotos_sem_vaga", []) or []))))
            tabela.setItem(row, 5, QTableWidgetItem(str(len(item.get("rookies_gerados", []) or []))))

    def _popular_highlights(self, resultado_janela_raw: dict[str, Any]):
        if not isinstance(resultado_janela_raw, dict):
            self.lbl_mercado_highlights.setText("Sem highlights da janela atual.")
            return
        destaques = resultado_janela_raw.get("movimentacoes_destaque", [])
        if not isinstance(destaques, list) or not destaques:
            self.lbl_mercado_highlights.setText("Sem highlights da janela atual.")
            return
        texto = "\n".join(f"- {d}" for d in destaques)
        self.lbl_mercado_highlights.setText(texto)
