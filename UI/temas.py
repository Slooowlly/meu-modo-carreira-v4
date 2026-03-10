"""
Sistema de temas - Dark mode clean e minimalista
Tamanhos otimizados para monitor/VR sem exagero
"""

from PySide6.QtGui import QFont


# ============================================================
# PALETA DE CORES
# ============================================================

class Cores:
    # Fundos
    FUNDO_APP = "#0d1117"
    FUNDO_CARD = "#161b22"
    FUNDO_CARD_HOVER = "#1c2333"
    FUNDO_INPUT = "#0d1117"
    FUNDO_HEADER = "#0d1117"
    
    # Texto
    TEXTO_PRIMARY = "#e6edf3"
    TEXTO_SECONDARY = "#7d8590"
    TEXTO_MUTED = "#484f58"
    TEXTO_INVERSE = "#0d1117"
    
    # Accent
    ACCENT_PRIMARY = "#58a6ff"
    ACCENT_HOVER = "#79b8ff"
    ACCENT_PRESSED = "#388bfd"
    
    # Status
    VERDE = "#3fb950"
    VERDE_HOVER = "#56d364"
    AMARELO = "#d29922"
    VERMELHO = "#f85149"
    VERMELHO_HOVER = "#ff6b61"
    LARANJA = "#db6d28"
    ROXO = "#bc8cff"
    
    # Bordas
    BORDA = "#21262d"
    BORDA_HOVER = "#30363d"
    BORDA_FOCUS = "#58a6ff"
    
    # Posições do pódio
    OURO = "#ffd700"
    PRATA = "#c0c0c0"
    BRONZE = "#cd7f32"
    
    # Equipes F1 (para cards coloridos)
    EQUIPE_CORES = {
        "Red Bull": "#3671C6",
        "Mercedes": "#27F4D2",
        "Ferrari": "#E8002D",
        "McLaren": "#FF8700",
        "Aston Martin": "#229971",
        "Alpine": "#FF87BC",
        "Williams": "#64C4FF",
        "RB": "#6692FF",
        "Kick Sauber": "#52E252",
        "Haas": "#B6BABD",
    }


# ============================================================
# FONTES
# ============================================================

class Fontes:
    FAMILIA = "Segoe UI"
    FAMILIA_MONO = "Consolas"
    
    @staticmethod
    def titulo_grande():
        f = QFont(Fontes.FAMILIA, 18)
        f.setBold(True)
        return f
    
    @staticmethod
    def titulo_medio():
        f = QFont(Fontes.FAMILIA, 15)
        f.setBold(True)
        return f
    
    @staticmethod
    def titulo_pequeno():
        f = QFont(Fontes.FAMILIA, 12)
        f.setBold(True)
        return f
    
    @staticmethod
    def texto_normal():
        return QFont(Fontes.FAMILIA, 10)
    
    @staticmethod
    def texto_pequeno():
        return QFont(Fontes.FAMILIA, 9)
    
    @staticmethod
    def texto_grande():
        return QFont(Fontes.FAMILIA, 11)
    
    @staticmethod
    def numero_destaque():
        f = QFont(Fontes.FAMILIA_MONO, 22)
        f.setBold(True)
        return f
    
    @staticmethod
    def numero_medio():
        f = QFont(Fontes.FAMILIA_MONO, 16)
        f.setBold(True)
        return f
    
    @staticmethod
    def botao():
        f = QFont(Fontes.FAMILIA, 10)
        f.setBold(True)
        return f
    
    @staticmethod
    def label_campo():
        f = QFont(Fontes.FAMILIA, 9)
        f.setBold(True)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.5)
        return f


# ============================================================
# ESPAÇAMENTOS
# ============================================================

class Espacos:
    # Padding
    PADDING_JANELA = 20
    PADDING_CARD = 16
    PADDING_CARD_SM = 12
    PADDING_INPUT = 8
    
    # Margens
    MARGIN_SECTION = 16
    MARGIN_ITEM = 8
    MARGIN_SMALL = 4
    
    # Alturas
    ALTURA_BOTAO = 36
    ALTURA_BOTAO_SM = 30
    ALTURA_INPUT = 34
    ALTURA_HEADER = 48
    
    # Bordas
    RAIO_CARD = 8
    RAIO_BOTAO = 6
    RAIO_INPUT = 6
    RAIO_BADGE = 4


# ============================================================
# ESTILOS (StyleSheets compostos)
# ============================================================

class Estilos:
    
    @staticmethod
    def janela_principal():
        return f"""
            QMainWindow, QWidget#central {{
                background-color: {Cores.FUNDO_APP};
            }}
            QScrollArea {{
                border: none;
                background-color: {Cores.FUNDO_APP};
            }}
            QScrollBar:vertical {{
                background: {Cores.FUNDO_APP};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {Cores.BORDA};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Cores.BORDA_HOVER};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                height: 0px;
            }}
        """
    
    @staticmethod
    def card():
        return f"""
            QFrame {{
                background-color: {Cores.FUNDO_CARD};
                border: 1px solid {Cores.BORDA};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
            QFrame:hover {{
                border-color: {Cores.BORDA_HOVER};
            }}
        """
    
    @staticmethod
    def card_sem_hover():
        return f"""
            QFrame {{
                background-color: {Cores.FUNDO_CARD};
                border: 1px solid {Cores.BORDA};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
        """
    
    @staticmethod
    def card_destaque(cor_borda=None):
        cor = cor_borda or Cores.ACCENT_PRIMARY
        return f"""
            QFrame {{
                background-color: {Cores.FUNDO_CARD};
                border: 1px solid {cor};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
        """
    
    @staticmethod
    def botao_primary():
        return f"""
            QPushButton {{
                background-color: {Cores.ACCENT_PRIMARY};
                color: {Cores.TEXTO_INVERSE};
                border: none;
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Cores.ACCENT_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Cores.ACCENT_PRESSED};
            }}
            QPushButton:disabled {{
                background-color: {Cores.BORDA};
                color: {Cores.TEXTO_MUTED};
            }}
        """
    
    @staticmethod
    def botao_secondary():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {Cores.FUNDO_CARD};
                border-color: {Cores.BORDA_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {Cores.BORDA};
            }}
        """
    
    @staticmethod
    def botao_danger():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Cores.VERMELHO};
                border: 1px solid {Cores.VERMELHO};
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {Cores.VERMELHO};
                color: {Cores.TEXTO_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Cores.VERMELHO_HOVER};
            }}
        """
    
    @staticmethod
    def botao_success():
        return f"""
            QPushButton {{
                background-color: {Cores.VERDE};
                color: {Cores.TEXTO_INVERSE};
                border: none;
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Cores.VERDE_HOVER};
            }}
        """
    
    @staticmethod
    def botao_ghost():
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {Cores.TEXTO_SECONDARY};
                border: none;
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                color: {Cores.TEXTO_PRIMARY};
                background-color: {Cores.FUNDO_CARD};
            }}
        """
    
    @staticmethod
    def input_field():
        return f"""
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {Cores.FUNDO_INPUT};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: {Espacos.RAIO_INPUT}px;
                padding: 4px 10px;
                selection-background-color: {Cores.ACCENT_PRIMARY};
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border-color: {Cores.BORDA_FOCUS};
            }}
            QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
                border-color: {Cores.BORDA_HOVER};
            }}
            QLineEdit::placeholder {{
                color: {Cores.TEXTO_MUTED};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 28px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {Cores.TEXTO_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                selection-background-color: {Cores.ACCENT_PRIMARY};
                selection-color: {Cores.TEXTO_INVERSE};
                outline: none;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                border: none;
                background: transparent;
            }}
            QSpinBox::up-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 4px solid {Cores.TEXTO_SECONDARY};
            }}
            QSpinBox::down-arrow {{
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {Cores.TEXTO_SECONDARY};
            }}
        """
    
    @staticmethod
    def tabela():
        return f"""
            QTableWidget {{
                background-color: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: {Espacos.RAIO_CARD}px;
                gridline-color: {Cores.BORDA};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 6px 10px;
                border-bottom: 1px solid {Cores.BORDA};
            }}
            QTableWidget::item:selected {{
                background-color: {Cores.ACCENT_PRIMARY};
                color: {Cores.TEXTO_INVERSE};
            }}
            QHeaderView::section {{
                background-color: {Cores.FUNDO_APP};
                color: {Cores.TEXTO_SECONDARY};
                border: none;
                border-bottom: 1px solid {Cores.BORDA};
                padding: 6px 10px;
                font-weight: bold;
                font-size: 9pt;
                text-transform: uppercase;
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: {Cores.FUNDO_APP};
                border: none;
            }}
        """
    
    @staticmethod
    def tooltip():
        return f"""
            QToolTip {{
                background-color: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 9pt;
            }}
        """