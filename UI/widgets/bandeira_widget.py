"""Widget reutilizavel para exibir bandeiras em PNG."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel

from Utils.bandeiras import obter_caminho_bandeira, obter_codigo_bandeira


class BandeiraLabel(QLabel):
    """Label que renderiza a bandeira correspondente a uma nacionalidade."""

    def __init__(
        self,
        nacionalidade: str,
        largura: int = 32,
        altura: int = 24,
        parent=None,
    ):
        super().__init__(parent)
        self._largura = int(largura)
        self._altura = int(altura)
        self._estilo_base = "background: transparent; border: none;"
        self._estilo_fallback = (
            "background: transparent; border: none; color: #94a3b8; font-weight: 700;"
        )
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(self._estilo_base)
        self.carregar_bandeira(nacionalidade)

    def carregar_bandeira(
        self,
        nacionalidade: str,
        largura: int | None = None,
        altura: int | None = None,
    ) -> None:
        """Carrega a bandeira pelo codigo resolvido da nacionalidade."""
        if largura is not None:
            self._largura = int(largura)
        if altura is not None:
            self._altura = int(altura)

        caminho = obter_caminho_bandeira(nacionalidade, absoluto=True)
        pixmap = QPixmap(caminho)

        if not pixmap.isNull():
            self.setStyleSheet(self._estilo_base)
            self.setText("")
            self.setPixmap(
                pixmap.scaled(
                    self._largura,
                    self._altura,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            return

        self.clear()
        self.setStyleSheet(self._estilo_fallback)
        self.setText(obter_codigo_bandeira(nacionalidade).upper())
