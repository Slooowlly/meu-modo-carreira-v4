"""Header customizado para exibir bandeiras em bloco nas colunas de corrida."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QHeaderView

from Utils.bandeiras import obter_caminho_bandeira


class BandeiraHeaderView(QHeaderView):
    """Renderiza bandeiras em um bloco centralizado, alinhado com os badges da tabela."""

    def __init__(self, orientation: Qt.Orientation, parent=None):
        super().__init__(orientation, parent)
        self._bandeiras_por_coluna: dict[int, str] = {}
        self._estado_por_coluna: dict[int, str] = {}
        self._cache_pixmaps: dict[str, QPixmap] = {}
        self._cor_fundo = QColor("#1e293b")
        self._cor_borda = QColor("#2d3a4f")
        self._cor_texto = QColor("#cbd5e1")
        self._cor_fundo_next = QColor(30, 58, 138, 110)
        self._cor_borda_next = QColor("#3b82f6")
        self._cor_texto_next = QColor("#93c5fd")

    def limpar_bandeiras(self) -> None:
        self._bandeiras_por_coluna.clear()
        self._estado_por_coluna.clear()
        self.viewport().update()

    def definir_bandeira_coluna(self, coluna: int, codigo: str) -> None:
        self._bandeiras_por_coluna[int(coluna)] = str(codigo or "").strip().lower()
        self.updateSection(int(coluna))

    def definir_estado_coluna(self, coluna: int, estado: str) -> None:
        estado_norm = str(estado or "").strip().lower()
        if estado_norm not in {"normal", "past", "next", "future"}:
            estado_norm = "normal"
        self._estado_por_coluna[int(coluna)] = estado_norm
        self.updateSection(int(coluna))

    def _obter_pixmap(self, codigo: str) -> QPixmap:
        codigo_normalizado = str(codigo or "").strip().lower()
        if not codigo_normalizado:
            return QPixmap()

        if codigo_normalizado not in self._cache_pixmaps:
            caminho = obter_caminho_bandeira(codigo_normalizado, absoluto=True)
            self._cache_pixmaps[codigo_normalizado] = QPixmap(caminho)
        return self._cache_pixmaps[codigo_normalizado]

    def paintSection(self, painter, rect, logical_index):  # type: ignore[override]
        super().paintSection(painter, rect, logical_index)

        codigo = self._bandeiras_por_coluna.get(int(logical_index), "")
        if not codigo:
            return

        painter.save()
        estado = self._estado_por_coluna.get(int(logical_index), "normal")

        # Mesmo molde visual dos badges de resultado da tabela.
        bloco = rect.adjusted(1, 4, -1, -4)
        if estado == "next":
            bloco = rect.adjusted(1, 3, -1, -10)
            painter.setPen(self._cor_borda_next)
            painter.setBrush(self._cor_fundo_next)
            painter.drawRect(bloco.adjusted(0, 0, -1, -1))
            painter.setPen(self._cor_borda_next)
            painter.drawLine(rect.left() + 1, rect.bottom() - 1, rect.right() - 1, rect.bottom() - 1)
        else:
            painter.setPen(self._cor_borda)
            painter.setBrush(self._cor_fundo)
            painter.drawRect(bloco.adjusted(0, 0, -1, -1))

        if estado == "future":
            painter.setOpacity(0.5)

        pixmap = self._obter_pixmap(codigo)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                max(10, bloco.width() - 6),
                max(10, bloco.height() - 4),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = bloco.x() + (bloco.width() - pixmap.width()) // 2
            y = bloco.y() + (bloco.height() - pixmap.height()) // 2
            painter.drawPixmap(x, y, pixmap)
        else:
            fonte = painter.font()
            fonte.setBold(True)
            painter.setFont(fonte)
            painter.setPen(self._cor_texto)
            painter.drawText(bloco, Qt.AlignCenter, codigo.upper())

        if estado == "future":
            painter.setOpacity(1.0)

        if estado == "next":
            label_rect = rect.adjusted(2, rect.height() - 10, -2, -1)
            fonte_label = painter.font()
            fonte_label.setBold(True)
            tamanho = fonte_label.pointSizeF()
            if tamanho <= 0:
                tamanho = float(fonte_label.pointSize())
            fonte_label.setPointSizeF(max(6.0, tamanho - 2.0))
            painter.setFont(fonte_label)
            painter.setPen(self._cor_texto_next)
            painter.drawText(label_rect, Qt.AlignCenter, "NEXT")

        painter.restore()
