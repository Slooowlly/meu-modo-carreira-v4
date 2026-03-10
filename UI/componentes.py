from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from UI.temas import Cores, Espacos, Estilos, Fontes


class Card(QFrame):
    clicked = Signal()

    def __init__(self, parent=None, clickable: bool = False):
        super().__init__(parent)
        self._clickable = clickable
        self._setup()

    def _setup(self):
        self.setStyleSheet(Estilos.card())
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(
            Espacos.PADDING_CARD,
            Espacos.PADDING_CARD,
            Espacos.PADDING_CARD,
            Espacos.PADDING_CARD,
        )
        self._layout.setSpacing(Espacos.MARGIN_ITEM)

        if self._clickable:
            self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def add(self, widget_or_layout):
        if isinstance(widget_or_layout, QWidget):
            self._layout.addWidget(widget_or_layout)
            return self

        if isinstance(widget_or_layout, QLayout):
            self._layout.addLayout(widget_or_layout)
            return self

        raise TypeError("Card.add aceita apenas QWidget ou QLayout.")

    def add_stretch(self):
        self._layout.addStretch()
        return self

    @property
    def interno(self):
        return self._layout


class CardTitulo(Card):
    def __init__(self, titulo, subtitulo=None, parent=None, clickable: bool = False):
        super().__init__(parent, clickable)

        self.lbl_titulo = QLabel(str(titulo))
        self.lbl_titulo.setFont(Fontes.titulo_pequeno())
        self.lbl_titulo.setStyleSheet(
            f"color: {Cores.ACCENT_PRIMARY}; border: none; background: transparent;"
        )
        self._layout.addWidget(self.lbl_titulo)

        if subtitulo:
            self.lbl_subtitulo = QLabel(str(subtitulo))
            self.lbl_subtitulo.setFont(Fontes.texto_pequeno())
            self.lbl_subtitulo.setStyleSheet(
                f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
            )
            self._layout.addWidget(self.lbl_subtitulo)
        else:
            self.lbl_subtitulo = None

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Cores.BORDA}; border: none;")
        self._layout.addWidget(sep)

    def set_titulo(self, texto):
        self.lbl_titulo.setText(str(texto))


class CardStat(Card):
    def __init__(self, valor, label, cor=None, parent=None):
        super().__init__(parent)

        cor_valor = cor or Cores.TEXTO_PRIMARY

        self.lbl_valor = QLabel(str(valor))
        self.lbl_valor.setFont(Fontes.numero_destaque())
        self.lbl_valor.setStyleSheet(
            f"color: {cor_valor}; border: none; background: transparent;"
        )
        self.lbl_valor.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self.lbl_valor)

        self.lbl_desc = QLabel(str(label))
        self.lbl_desc.setFont(Fontes.texto_pequeno())
        self.lbl_desc.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        self.lbl_desc.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(self.lbl_desc)

    def set_valor(self, valor, cor=None):
        self.lbl_valor.setText(str(valor))
        if cor:
            self.lbl_valor.setStyleSheet(
                f"color: {cor}; border: none; background: transparent;"
            )


class CardMini(Card):
    def __init__(self, label, valor, cor=None, parent=None):
        super().__init__(parent)

        self._layout.setContentsMargins(
            Espacos.PADDING_CARD_SM,
            Espacos.PADDING_CARD_SM,
            Espacos.PADDING_CARD_SM,
            Espacos.PADDING_CARD_SM,
        )

        cor_valor = cor or Cores.ACCENT_PRIMARY

        lbl = QLabel(str(label).upper())
        lbl.setFont(Fontes.label_campo())
        lbl.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        self._layout.addWidget(lbl)

        self.lbl_valor = QLabel(str(valor))
        self.lbl_valor.setFont(Fontes.numero_medio())
        self.lbl_valor.setStyleSheet(
            f"color: {cor_valor}; border: none; background: transparent;"
        )
        self._layout.addWidget(self.lbl_valor)

    def set_valor(self, valor):
        self.lbl_valor.setText(str(valor))


class BotaoPrimary(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)
        self.setStyleSheet(Estilos.botao_primary())
        self.setFont(Fontes.botao())
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(Espacos.ALTURA_BOTAO)


class BotaoSecondary(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)
        self.setStyleSheet(Estilos.botao_secondary())
        self.setFont(Fontes.botao())
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(Espacos.ALTURA_BOTAO)


class BotaoDanger(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)
        self.setStyleSheet(Estilos.botao_danger())
        self.setFont(Fontes.botao())
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(Espacos.ALTURA_BOTAO)


class BotaoSuccess(QPushButton):
    def __init__(self, texto, parent=None):
        super().__init__(texto, parent)
        self.setStyleSheet(Estilos.botao_success())
        self.setFont(Fontes.botao())
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(Espacos.ALTURA_BOTAO)



class CampoTexto(QWidget):
    textChanged = Signal(str)

    def __init__(self, label, placeholder="", parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if label:
            lbl = QLabel(str(label).upper())
            lbl.setFont(Fontes.label_campo())
            lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
            layout.addWidget(lbl)

        self.input = QLineEdit()
        self.input.setStyleSheet(Estilos.input_field())
        self.input.setFont(Fontes.texto_normal())
        self.input.setPlaceholderText(str(placeholder))
        self.input.setMinimumHeight(Espacos.ALTURA_INPUT)
        self.input.textChanged.connect(self.textChanged.emit)
        layout.addWidget(self.input)

    def text(self):
        return self.input.text()

    def setText(self, texto):
        self.input.setText(str(texto))

    def setPlaceholderText(self, texto):
        self.input.setPlaceholderText(str(texto))

    def clear(self):
        self.input.clear()



class CampoCombo(QWidget):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, label, opcoes=None, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        if label:
            lbl = QLabel(str(label).upper())
            lbl.setFont(Fontes.label_campo())
            lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
            layout.addWidget(lbl)

        self.combo = QComboBox()
        self.combo.setStyleSheet(Estilos.input_field())
        self.combo.setFont(Fontes.texto_normal())
        self.combo.setMinimumHeight(Espacos.ALTURA_INPUT)

        if opcoes:
            self.combo.addItems([str(item) for item in opcoes])

        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        self.combo.currentTextChanged.connect(self.currentTextChanged.emit)
        layout.addWidget(self.combo)

    def currentText(self):
        return self.combo.currentText()

    def currentIndex(self):
        return self.combo.currentIndex()

    def setCurrentIndex(self, indice):
        self.combo.setCurrentIndex(int(indice))

    def setCurrentText(self, texto):
        self.combo.setCurrentText(str(texto))

    def addItems(self, items):
        self.combo.addItems([str(item) for item in items])

    def clear(self):
        self.combo.clear()


class CampoSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, label, minimo=0, maximo=100, valor=50, sufixo="", parent=None):
        super().__init__(parent)
        self._sufixo = str(sufixo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()

        if label:
            lbl = QLabel(str(label).upper())
            lbl.setFont(Fontes.label_campo())
            lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
            header.addWidget(lbl)

        header.addStretch()

        self.lbl_valor = QLabel(f"{int(valor)}{self._sufixo}")
        self.lbl_valor.setFont(Fontes.titulo_pequeno())
        self.lbl_valor.setStyleSheet(f"color: {Cores.ACCENT_PRIMARY};")
        header.addWidget(self.lbl_valor)

        layout.addLayout(header)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(int(minimo), int(maximo))
        self.slider.setValue(int(valor))
        self.slider.setStyleSheet(
            f"""
            QSlider::groove:horizontal {{
                background: {Cores.BORDA};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {Cores.ACCENT_PRIMARY};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {Cores.ACCENT_HOVER};
            }}
            QSlider::sub-page:horizontal {{
                background: {Cores.ACCENT_PRIMARY};
                border-radius: 2px;
            }}
        """
        )
        self.slider.valueChanged.connect(self._ao_mudar)
        layout.addWidget(self.slider)

    def _ao_mudar(self, valor):
        self.lbl_valor.setText(f"{valor}{self._sufixo}")
        self.valueChanged.emit(valor)

    def value(self):
        return self.slider.value()

    def setValue(self, valor):
        self.slider.setValue(int(valor))

    def setRange(self, minimo, maximo):
        self.slider.setRange(int(minimo), int(maximo))


class CampoCheck(QCheckBox):
    def __init__(self, texto, checked=False, parent=None):
        super().__init__(str(texto), parent)
        self.setFont(Fontes.texto_normal())
        self.setChecked(bool(checked))
        self.setStyleSheet(
            f"""
            QCheckBox {{
                color: {Cores.TEXTO_PRIMARY};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {Espacos.RAIO_BADGE}px;
                border: 1px solid {Cores.BORDA};
                background: {Cores.FUNDO_INPUT};
            }}
            QCheckBox::indicator:checked {{
                background: {Cores.ACCENT_PRIMARY};
                border-color: {Cores.ACCENT_PRIMARY};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Cores.BORDA_HOVER};
            }}
        """
        )


class LabelTitulo(QLabel):
    def __init__(self, texto, parent=None):
        super().__init__(str(texto), parent)
        self.setFont(Fontes.titulo_grande())
        self.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")


class LabelSubtitulo(QLabel):
    def __init__(self, texto, parent=None):
        super().__init__(str(texto), parent)
        self.setFont(Fontes.texto_normal())
        self.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")




class BarraProgresso(QWidget):
    def __init__(self, label, valor=0, maximo=100, cor=None, parent=None):
        super().__init__(parent)
        self._cor = cor or Cores.ACCENT_PRIMARY

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl = QLabel(str(label))
        lbl.setFont(Fontes.texto_pequeno())
        lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        lbl.setFixedWidth(70)
        layout.addWidget(lbl)

        self.barra = QProgressBar()
        self.barra.setRange(0, int(maximo))
        self.barra.setValue(int(valor))
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(6)
        self.barra.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {Cores.BORDA};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {self._cor};
                border-radius: 3px;
            }}
        """
        )
        layout.addWidget(self.barra)

        self.lbl_valor = QLabel(str(int(valor)))
        self.lbl_valor.setFont(Fontes.texto_pequeno())
        self.lbl_valor.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        self.lbl_valor.setFixedWidth(28)
        self.lbl_valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.lbl_valor)

    def set_valor(self, valor):
        valor_int = int(valor)
        self.barra.setValue(valor_int)
        self.lbl_valor.setText(str(valor_int))


class Separador(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {Cores.BORDA};")


class Espacador(QWidget):
    def __init__(self, altura=None, parent=None):
        super().__init__(parent)
        if altura is not None:
            self.setFixedHeight(int(altura))
        else:
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class LinhaInfo(QWidget):
    def __init__(self, label, valor, cor_valor=None, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self.lbl = QLabel(str(label))
        self.lbl.setFont(Fontes.texto_normal())
        self.lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        layout.addWidget(self.lbl)

        layout.addStretch()

        cor = cor_valor or Cores.TEXTO_PRIMARY
        self.lbl_valor = QLabel(str(valor))
        self.lbl_valor.setFont(Fontes.texto_normal())
        self.lbl_valor.setStyleSheet(f"color: {cor}; font-weight: bold;")
        layout.addWidget(self.lbl_valor)

    def set_valor(self, valor, cor=None):
        self.lbl_valor.setText(str(valor))
        if cor:
            self.lbl_valor.setStyleSheet(f"color: {cor}; font-weight: bold;")

