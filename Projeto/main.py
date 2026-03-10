"""
Modo Carreira - Ponto de entrada principal
Integra todas as partes do sistema
"""

from __future__ import annotations

import os
import sys
from PySide6.QtWidgets import QApplication

# Permite executar tambem via `python Projeto/main.py`.
RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, RAIZ_PROJETO)

from Dados.banco import banco_existe, carregar_banco
from UI.inicialconfig import TelaInicialConfig
from UI.carreira import TelaCarreira


class App:
    """Controlador principal da aplicação"""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")

        # Configurações globais
        self.app.setApplicationName("Modo Carreira")
        self.app.setApplicationVersion("2.0")

        # Referências das janelas
        self.tela_config = None
        self.tela_carreira = None

    def iniciar(self):
        """Inicia a aplicação"""

        # Verifica se já existe carreira salva
        if banco_existe():
            banco = carregar_banco()
            self._abrir_carreira(banco)
        else:
            self._abrir_config()

        # Loop principal
        sys.exit(self.app.exec())

    def _abrir_config(self):
        """Abre a tela de criação de carreira"""
        self.tela_config = TelaInicialConfig()
        self.tela_config.carreira_criada.connect(self._ao_criar_carreira)
        self.tela_config.showFullScreen()

    def _ao_criar_carreira(self, banco):
        """Callback quando carreira é criada"""
        if self.tela_config:
            self.tela_config.close()
            self.tela_config = None

        self._abrir_carreira(banco)

    def _abrir_carreira(self, banco):
        """Abre o dashboard principal"""
        self.tela_carreira = TelaCarreira(banco)
        self.tela_carreira.showFullScreen()


def main():
    """Função principal"""
    app = App()
    app.iniciar()


if __name__ == "__main__":
    main()
