from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMessageBox

from Dados.banco import salvar_banco


class ConfigMixin:
    """
    Mixin com acoes de configuracao e utilitarios.
    """

    def _configurar_pastas(self) -> None:
        try:
            from UI.dialogs import DialogConfigurarPastas

            dialogo = DialogConfigurarPastas(self)
            dialogo.exec()
            return
        except ImportError:
            pass
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao abrir o dialogo de configuracao:\n{erro}",
            )
            return

        pasta = QFileDialog.getExistingDirectory(
            self,
            "Selecionar pasta de resultados",
        )
        if not pasta:
            return

        self.banco["pasta_resultados"] = pasta
        salvar_banco(self.banco)

        QMessageBox.information(
            self,
            "Configurado",
            f"Pasta configurada:\n{pasta}",
        )

    def _configurar_conteudo_iracing(self) -> None:
        try:
            from UI.dialogs import DialogConteudoIRacing
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Dialogo de conteudo iRacing indisponivel.",
            )
            return

        try:
            dialogo = DialogConteudoIRacing(self.banco.get("conteudo_iracing", {}), self)
            if dialogo.exec() != dialogo.Accepted:
                return

            self.banco["conteudo_iracing"] = dialogo.resultado()
            salvar_banco(self.banco)

            if hasattr(self, "_atualizar_tudo"):
                self._atualizar_tudo()

            QMessageBox.information(
                self,
                "Conteudo iRacing",
                "Conteudo atualizado com sucesso.",
            )
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao configurar conteudo iRacing:\n{erro}",
            )

    def _abrir_historia(self) -> None:
        try:
            from UI.historia import TelaHistoria
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Tela de historia ainda nao implementada.",
            )
            return

        try:
            if hasattr(self, "takeCentralWidget") and hasattr(self, "setCentralWidget"):
                if getattr(self, "_historia_widget_ativa", None) is not None:
                    return

                central_atual = self.takeCentralWidget()
                if central_atual is None:
                    return

                self._dashboard_widget_antes_historia = central_atual
                self._historia_widget_ativa = TelaHistoria(
                    self.banco,
                    self,
                    ao_voltar=self._voltar_historia_embutida,
                )
                self.setCentralWidget(self._historia_widget_ativa)
                return

            historia = TelaHistoria(self.banco)
            self._historia_widget_ativa = historia
            historia.show()
        except Exception as erro:
            dashboard_widget = getattr(self, "_dashboard_widget_antes_historia", None)
            if dashboard_widget is not None and hasattr(self, "setCentralWidget"):
                self.setCentralWidget(dashboard_widget)
                self._dashboard_widget_antes_historia = None
            self._historia_widget_ativa = None
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao abrir a tela de historia:\n{erro}",
            )

    def _voltar_historia_embutida(self) -> None:
        if not hasattr(self, "setCentralWidget"):
            return

        dashboard_widget = getattr(self, "_dashboard_widget_antes_historia", None)
        if dashboard_widget is None:
            return

        if hasattr(self, "takeCentralWidget"):
            atual = self.takeCentralWidget()
            if atual is not None:
                atual.deleteLater()

        self.setCentralWidget(dashboard_widget)
        self._dashboard_widget_antes_historia = None
        self._historia_widget_ativa = None

        if hasattr(self, "_atualizar_tudo"):
            self._atualizar_tudo()
