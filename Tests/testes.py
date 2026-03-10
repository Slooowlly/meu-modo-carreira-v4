import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from UI.temas import Estilos
from UI.componentes import (
    CardTitulo,
    BotaoPrimary,
    BotaoSecondary,
    CampoTexto,
    CampoSlider,
    CampoCombo,
    LabelTitulo,
    LabelSubtitulo,
    LinhaInfo,
)


class TesteUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Teste UI - Modo Carreira")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(Estilos.janela_principal() + Estilos.tooltip())

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        layout.addWidget(LabelTitulo("Teste de Componentes"))
        layout.addWidget(LabelSubtitulo("Visualizacao dos componentes da UI"))

        card_stats = CardTitulo("Estatisticas")
        card_stats.add(LinhaInfo("Pilotos", "20"))
        card_stats.add(LinhaInfo("Equipes", "10"))
        card_stats.add(LinhaInfo("Temporada", "2024"))
        layout.addWidget(card_stats)

        card_input = CardTitulo("Configuracoes")
        card_input.add(CampoTexto("Nome", "Digite seu nome..."))
        card_input.add(CampoSlider("Idade", 16, 40, 18, " anos"))
        card_input.add(CampoCombo("Dificuldade", ["Facil", "Medio", "Dificil", "Lendario"]))
        layout.addWidget(card_input)

        card_btns = CardTitulo("Acoes")
        card_btns.add(BotaoPrimary("Iniciar Carreira"))
        card_btns.add(BotaoSecondary("Carregar Carreira"))
        layout.addWidget(card_btns)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela = TesteUI()
    janela.show()
    sys.exit(app.exec())

