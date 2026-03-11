from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import traceback
from time import monotonic
import unicodedata
from typing import Any, Callable

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor, QBrush, QFont, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QGridLayout,
    QPushButton,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QStyledItemDelegate,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from Dados.constantes import CATEGORIAS, PONTOS_POR_POSICAO
from Logica.milestones import obter_historico_milestones, obter_proximo_milestone
from UI.componentes import (
    BotaoSecondary,
    CampoCombo,
    CampoTexto,
    Card,
    CardStat,
    CardTitulo,
    LinhaInfo,
    Separador,
)
from UI.temas import Cores, Espacos, Fontes
from UI.ux_helpers import UXMixin
from Utils.bandeiras import (
    CODIGOS_BANDEIRAS_SUPORTADOS,
    obter_emoji_bandeira,
    obter_codigo_bandeira,
    obter_codigo_bandeira_circuito,
    obter_pasta_bandeiras_absoluta,
)
from UI.widgets.bandeira_header import BandeiraHeaderView


# Paleta dedicada da tela História (isolada da tela principal/carreira).
HIST_BG_APP = "#0f0d0d"
HIST_BG_HEADER = "#181312"
HIST_BG_CARD = "#221a19"
HIST_BG_CARD_HOVER = "#2b2221"
HIST_BG_SURFACE = "#161211"
HIST_BG_SURFACE_ALT = "#2a211f"
HIST_BORDER = "#4a3632"
HIST_BORDER_HOVER = "#6b4b44"
HIST_TEXT_PRIMARY = "#f5f7fb"
HIST_TEXT_SECONDARY = "#b3bccb"
HIST_TEXT_MUTED = "#7f8a9b"
HIST_ACCENT = "#ff6a3d"
HIST_ACCENT_HOVER = "#ff8a68"


class BadgeResultadoDelegate(QStyledItemDelegate):
    ROLE_BADGE = Qt.UserRole + 11
    ROLE_INLINE_SUFFIX = Qt.UserRole + 13
    ROLE_SEPARADOR_ESQ = Qt.UserRole + 14
    ROLE_EQUIPE_INFO = Qt.UserRole + 15
    ROLE_INLINE_PREFIX = Qt.UserRole + 16
    ROLE_BANDEIRA_CODIGO = Qt.UserRole + 17
    ROLE_TROFEUS_INFO = Qt.UserRole + 18
    ROLE_EQUIPE_CHAVE = Qt.UserRole + 19
    ROLE_EQUIPE_COR = Qt.UserRole + 20
    _cache_trofeus: dict[str, QPixmap] = {}
    _cache_bandeiras: dict[str, QPixmap] = {}

    def _obter_pixmap_trofeu(self, tipo: str) -> QPixmap:
        tipo_norm = str(tipo or "").strip().casefold()
        if tipo_norm not in {"ouro", "prata", "bronze"}:
            return QPixmap()

        if tipo_norm not in self._cache_trofeus:
            caminho = Path(__file__).resolve().parent / "widgets" / f"{tipo_norm}.png"
            self._cache_trofeus[tipo_norm] = QPixmap(str(caminho))
        return self._cache_trofeus[tipo_norm]

    def _obter_pixmap_bandeira(self, codigo: str) -> QPixmap:
        codigo_norm = str(codigo or "").strip().lower()
        if len(codigo_norm) != 2 or not codigo_norm.isalpha():
            return QPixmap()

        if codigo_norm not in self._cache_bandeiras:
            caminho = obter_pasta_bandeiras_absoluta() / f"{codigo_norm}.png"
            self._cache_bandeiras[codigo_norm] = QPixmap(str(caminho))
        return self._cache_bandeiras[codigo_norm]

    def paint(self, painter, option, index):
        payload = index.data(self.ROLE_BADGE)

        painter.save()

        fundo_item = index.data(Qt.BackgroundRole)
        if isinstance(fundo_item, QBrush):
            painter.fillRect(option.rect, fundo_item)
        elif isinstance(fundo_item, QColor):
            painter.fillRect(option.rect, fundo_item)
        else:
            painter.fillRect(option.rect, QColor(HIST_BG_CARD))

        if bool(index.data(self.ROLE_SEPARADOR_ESQ)):
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top() + 1, 2, max(1, option.rect.height() - 2)),
                QColor(HIST_BORDER_HOVER),
            )

        if not isinstance(payload, dict):
            texto = str(index.data(Qt.DisplayRole) or "")
            alinhamento = index.data(Qt.TextAlignmentRole)
            if not isinstance(alinhamento, int):
                alinhamento = int(Qt.AlignVCenter | Qt.AlignLeft)

            cor_texto = QColor(HIST_TEXT_PRIMARY)
            foreground_item = index.data(Qt.ForegroundRole)
            if isinstance(foreground_item, QBrush):
                cor_texto = foreground_item.color()
            elif isinstance(foreground_item, QColor):
                cor_texto = foreground_item

            fonte = option.font
            fonte_item = index.data(Qt.FontRole)
            if isinstance(fonte_item, QFont):
                fonte = fonte_item

            codigo_bandeira = str(index.data(self.ROLE_BANDEIRA_CODIGO) or "").strip()
            if codigo_bandeira:
                pixmap_bandeira = self._obter_pixmap_bandeira(codigo_bandeira)
                if not pixmap_bandeira.isNull():
                    area = option.rect.adjusted(2, 2, -2, -2)
                    alvo_altura = max(11, min(16, area.height() - 2))
                    alvo_largura = max(14, int(alvo_altura * 1.45))
                    bandeira_escalada = pixmap_bandeira.scaled(
                        alvo_largura,
                        alvo_altura,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    x = area.left() + (area.width() - bandeira_escalada.width()) // 2
                    y = area.top() + (area.height() - bandeira_escalada.height()) // 2
                    painter.drawPixmap(x, y, bandeira_escalada)
                    painter.restore()
                    return

            payload_equipe = index.data(self.ROLE_EQUIPE_INFO)
            if isinstance(payload_equipe, dict):
                nome_equipe = str(payload_equipe.get("nome", "") or "").strip()
                pontos_equipe = int(payload_equipe.get("pontos", 0) or 0)
                area = option.rect.adjusted(6, 0, -6, 0)
                trofeus_raw = payload_equipe.get("trofeus", {})
                trofeus = trofeus_raw if isinstance(trofeus_raw, dict) else {}
                tipo_ordem = ("ouro", "prata", "bronze")
                cor_plus = {
                    "ouro": QColor("#fbbf24"),
                    "prata": QColor("#cbd5e1"),
                    "bronze": QColor("#d97706"),
                }

                fonte_nome = QFont(fonte)
                painter.setFont(fonte_nome)
                metricas_nome = painter.fontMetrics()

                fonte_pontos = QFont(fonte)
                fonte_pontos.setBold(True)
                tamanho_pontos = fonte_pontos.pointSizeF()
                if tamanho_pontos <= 0:
                    tamanho_pontos = float(fonte_pontos.pointSize())
                fonte_pontos.setPointSizeF(max(9.2, tamanho_pontos + 0.8))
                painter.setFont(fonte_pontos)
                metricas_pontos = painter.fontMetrics()

                fonte_plus = QFont(fonte)
                tamanho_plus = fonte_plus.pointSizeF()
                if tamanho_plus <= 0:
                    tamanho_plus = float(fonte_plus.pointSize())
                fonte_plus.setPointSizeF(max(7.0, tamanho_plus - 0.2))
                painter.setFont(fonte_plus)
                metricas_plus = painter.fontMetrics()

                texto_pontos = f"{pontos_equipe} pts"
                largura_pontos = max(18, metricas_pontos.horizontalAdvance(texto_pontos))
                tamanho_icone = max(15, min(19, area.height() - 4))
                gap_icone = 1
                gap_grupo = 8
                gap_bloco = 8

                grupos: list[tuple[str, int, int, int]] = []
                for tipo in tipo_ordem:
                    qtd = int(trofeus.get(tipo, 0) or 0)
                    if qtd <= 0:
                        continue
                    exibidas = min(5, qtd)
                    largura = exibidas * tamanho_icone + max(0, exibidas - 1) * gap_icone
                    extra = qtd - exibidas
                    if extra > 0:
                        largura += 4 + metricas_plus.horizontalAdvance(f"+{extra}")
                    grupos.append((tipo, qtd, exibidas, largura))

                largura_trofeus = 0
                if grupos:
                    largura_trofeus = sum(grupo[3] for grupo in grupos) + gap_grupo * (len(grupos) - 1)

                largura_nome = max(
                    56,
                    area.width() - largura_pontos - largura_trofeus - (gap_bloco * 2),
                )
                texto_nome = metricas_nome.elidedText(nome_equipe, Qt.ElideRight, largura_nome)

                rect_nome = QRect(area.left(), area.top(), largura_nome, area.height())
                x_trofeus = rect_nome.right() + 1 + gap_bloco
                x_pontos = area.right() - largura_pontos + 1
                rect_pontos = QRect(x_pontos, area.top(), largura_pontos, area.height())

                painter.setFont(fonte_nome)
                painter.setPen(cor_texto)
                painter.drawText(rect_nome, Qt.AlignVCenter | Qt.AlignLeft, texto_nome)

                cursor_x = x_trofeus
                for tipo, qtd, exibidas, _largura in grupos:
                    pixmap = self._obter_pixmap_trofeu(tipo)
                    for _ in range(exibidas):
                        if not pixmap.isNull():
                            pixmap_escalado = pixmap.scaled(
                                tamanho_icone,
                                tamanho_icone,
                                Qt.KeepAspectRatio,
                                Qt.SmoothTransformation,
                            )
                            y_icone = area.top() + (area.height() - pixmap_escalado.height()) // 2
                            painter.drawPixmap(cursor_x, y_icone, pixmap_escalado)
                        cursor_x += tamanho_icone + gap_icone

                    extra = qtd - exibidas
                    if extra > 0:
                        painter.setFont(fonte_plus)
                        painter.setPen(cor_plus.get(tipo, QColor("#cbd5e1")))
                        rect_extra = QRect(
                            cursor_x + 2,
                            area.top(),
                            metricas_plus.horizontalAdvance(f"+{extra}") + 2,
                            area.height(),
                        )
                        painter.drawText(rect_extra, Qt.AlignVCenter | Qt.AlignLeft, f"+{extra}")
                        cursor_x += 4 + metricas_plus.horizontalAdvance(f"+{extra}")

                    cursor_x += gap_grupo

                painter.setFont(fonte_pontos)
                painter.setPen(QColor("#e2e8f0"))
                painter.drawText(rect_pontos, Qt.AlignVCenter | Qt.AlignRight, texto_pontos)

                painter.restore()
                return

            payload_trofeus = index.data(self.ROLE_TROFEUS_INFO)
            if isinstance(payload_trofeus, dict):
                area = option.rect.adjusted(6, 0, -6, 0)
                trofeus = payload_trofeus
                lider_ouro = bool(trofeus.get("lider_ouro", False))
                ganhos_raw = trofeus.get("ganhos", {})
                ganhos = ganhos_raw if isinstance(ganhos_raw, dict) else {}
                setas_tipos_raw = trofeus.get("setas_tipos", {})
                if isinstance(setas_tipos_raw, dict):
                    setas_tipos = {
                        "ouro": bool(setas_tipos_raw.get("ouro", False)),
                        "prata": bool(setas_tipos_raw.get("prata", False)),
                        "bronze": bool(setas_tipos_raw.get("bronze", False)),
                    }
                else:
                    setas_tipos = {"ouro": False, "prata": False, "bronze": False}
                tipo_ordem = ("ouro", "prata", "bronze")
                base_icone = max(13, min(20, area.height() - 4))
                tamanhos = {
                    "ouro": base_icone,
                    "prata": max(12, base_icone - 3),
                    "bronze": max(11, base_icone - 6),
                }

                fonte_mult = QFont(fonte)
                tamanho_mult = fonte_mult.pointSizeF()
                if tamanho_mult <= 0:
                    tamanho_mult = float(fonte_mult.pointSize())
                fonte_mult.setPointSizeF(max(8.2, tamanho_mult + 0.2))
                fonte_mult.setBold(True)
                painter.setFont(fonte_mult)
                metricas_mult = painter.fontMetrics()

                gap_icone_texto = 4
                gap_grupo = 14
                gap_estrela = 3
                largura_estrela = metricas_mult.horizontalAdvance("★")

                if all(int(trofeus.get(tipo, 0) or 0) <= 0 for tipo in tipo_ordem):
                    painter.setFont(fonte)
                    painter.setPen(cor_texto)
                    painter.drawText(area, Qt.AlignCenter, "—")
                    painter.restore()
                    return

                largura_mult_slot = max(28, metricas_mult.horizontalAdvance("x999"))
                largura_slot_ouro = (
                    (largura_estrela + gap_estrela)
                    + tamanhos["ouro"]
                    + gap_icone_texto
                    + largura_mult_slot
                )
                largura_slot_prata = tamanhos["prata"] + gap_icone_texto + largura_mult_slot
                largura_slot_bronze = tamanhos["bronze"] + gap_icone_texto + largura_mult_slot
                largura_slots = {
                    "ouro": largura_slot_ouro,
                    "prata": largura_slot_prata,
                    "bronze": largura_slot_bronze,
                }

                largura_total = (
                    largura_slot_ouro
                    + largura_slot_prata
                    + largura_slot_bronze
                    + (gap_grupo * 2)
                )
                cursor_x = area.left() + max(0, (area.width() - largura_total) // 2)

                for tipo in tipo_ordem:
                    qtd = int(trofeus.get(tipo, 0) or 0)
                    largura_grupo = largura_slots[tipo]
                    if qtd <= 0:
                        cursor_x += largura_grupo + gap_grupo
                        continue

                    pixmap = self._obter_pixmap_trofeu(tipo)
                    tamanho_icone = tamanhos[tipo]
                    x_inicio_icone = cursor_x
                    if tipo == "ouro":
                        x_inicio_icone += largura_estrela + gap_estrela
                    if tipo == "ouro" and lider_ouro:
                        painter.setFont(fonte_mult)
                        painter.setPen(QColor("#facc15"))
                        rect_estrela = QRect(
                            cursor_x,
                            area.top(),
                            largura_estrela,
                            area.height(),
                        )
                        painter.drawText(rect_estrela, Qt.AlignVCenter | Qt.AlignLeft, "★")
                    if not pixmap.isNull():
                        pixmap_escalado = pixmap.scaled(
                            tamanho_icone,
                            tamanho_icone,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation,
                        )
                        y_icone = area.top() + (area.height() - pixmap_escalado.height()) // 2
                        painter.drawPixmap(x_inicio_icone, y_icone, pixmap_escalado)

                    x_texto = x_inicio_icone + tamanho_icone + gap_icone_texto
                    painter.setFont(fonte_mult)
                    painter.setPen(QColor("#f8fafc"))
                    rect_texto = QRect(
                        x_texto,
                        area.top(),
                        max(8, largura_grupo - (x_texto - cursor_x)),
                        area.height(),
                    )
                    painter.drawText(rect_texto, Qt.AlignVCenter | Qt.AlignLeft, f"x{qtd}")

                    ganho_tipo = int(ganhos.get(tipo, 0) or 0)
                    if ganho_tipo > 0 or setas_tipos.get(tipo, False):
                        fonte_seta = QFont(fonte_mult)
                        tamanho_seta = fonte_seta.pointSizeF()
                        if tamanho_seta <= 0:
                            tamanho_seta = float(fonte_seta.pointSize())
                        fonte_seta.setPointSizeF(max(6.8, tamanho_seta - 1.4))
                        painter.setFont(fonte_seta)
                        painter.setPen(QColor("#22c55e"))
                        rect_seta = QRect(
                            x_inicio_icone + max(0, tamanho_icone - 8),
                            area.top() + 1,
                            10,
                            10,
                        )
                        painter.drawText(rect_seta, Qt.AlignCenter, "▲")
                    cursor_x += largura_grupo + gap_grupo

                painter.restore()
                return

            payload_prefix = index.data(self.ROLE_INLINE_PREFIX)
            payload_suffix = index.data(self.ROLE_INLINE_SUFFIX)
            if isinstance(payload_prefix, dict) or isinstance(payload_suffix, dict):
                sufixos: list[tuple[str, QColor, int]] = []
                seta_sobre_trofeu = False
                cor_seta_sobre_trofeu = QColor("#22c55e")
                if isinstance(payload_suffix, dict):
                    seta_sobre_trofeu = bool(payload_suffix.get("seta_sobre_trofeu", False))
                    cor_seta_sobre_trofeu = QColor(
                        str(payload_suffix.get("cor_seta_sobre_trofeu", "#22c55e"))
                    )
                    itens = payload_suffix.get("itens")
                    if isinstance(itens, list):
                        for item_sufixo in itens:
                            if not isinstance(item_sufixo, dict):
                                continue
                            texto_sufixo = str(item_sufixo.get("texto", "") or "").strip()
                            if not texto_sufixo:
                                continue
                            sufixos.append(
                                (
                                    texto_sufixo,
                                    QColor(str(item_sufixo.get("cor_texto", "#f97316"))),
                                    int(item_sufixo.get("gap", 4)),
                                )
                            )
                    else:
                        sufixo = str(payload_suffix.get("texto", "") or "").strip()
                        if sufixo:
                            sufixos.append(
                                (
                                    sufixo,
                                    QColor(str(payload_suffix.get("cor_texto", "#f97316"))),
                                    int(payload_suffix.get("gap", 6)),
                                )
                            )

                prefix_tamanho = 0
                gap_prefix = 6
                cor_prefix = QColor(HIST_BORDER_HOVER)
                cor_prefix_borda = QColor(HIST_BG_SURFACE)
                if isinstance(payload_prefix, dict):
                    prefix_tamanho = int(payload_prefix.get("tamanho", 9))
                    prefix_tamanho = max(6, min(12, prefix_tamanho))
                    gap_prefix = int(payload_prefix.get("gap", 6))
                    cor_prefix = QColor(str(payload_prefix.get("cor_fundo", HIST_BORDER_HOVER)))
                    cor_prefix_borda = QColor(str(payload_prefix.get("cor_borda", HIST_BG_SURFACE)))

                painter.setFont(fonte)
                metricas = painter.fontMetrics()
                area = option.rect.adjusted(6, 0, -6, 0)

                deslocamento_esquerda = 0
                if prefix_tamanho > 0:
                    deslocamento_esquerda = prefix_tamanho + max(0, gap_prefix)

                largura_sufixos = 0
                if sufixos:
                    for indice_sufixo, (texto_sufixo, _cor_sufixo, gap_item) in enumerate(sufixos):
                        if indice_sufixo > 0:
                            largura_sufixos += max(0, int(gap_item))
                        largura_sufixos += max(8, metricas.horizontalAdvance(texto_sufixo))
                x_sufixo = area.right() - largura_sufixos + 1 if sufixos else area.right() + 1

                inicio_texto = area.left() + deslocamento_esquerda
                limite_texto = (x_sufixo - 6) if sufixos else (area.right() + 1)
                largura_base = max(8, limite_texto - inicio_texto)
                texto_base = metricas.elidedText(texto, Qt.ElideRight, largura_base)
                rect_base = QRect(inicio_texto, area.top(), largura_base, area.height())

                if prefix_tamanho > 0:
                    y_prefix = area.top() + (area.height() - prefix_tamanho) // 2
                    rect_prefix = QRect(area.left(), y_prefix, prefix_tamanho, prefix_tamanho)
                    painter.setPen(cor_prefix_borda)
                    painter.setBrush(cor_prefix)
                    painter.drawRect(rect_prefix)

                painter.setPen(cor_texto)
                painter.drawText(rect_base, Qt.AlignVCenter | Qt.AlignLeft, texto_base)

                indice_trofeu = texto_base.rfind("🏆")
                x_trofeu = -1
                largura_trofeu = 0
                if indice_trofeu >= 0:
                    texto_antes_trofeu = texto_base[:indice_trofeu]
                    x_trofeu = rect_base.left() + metricas.horizontalAdvance(texto_antes_trofeu)
                    largura_trofeu = max(8, metricas.horizontalAdvance("🏆"))
                else:
                    indice_x = texto_base.rfind(" x")
                    if indice_x >= 0:
                        sufixo_titulo = texto_base[indice_x + 2 :]
                        if sufixo_titulo.isdigit():
                            inicio_espacos = indice_x
                            while inicio_espacos > 0 and texto_base[inicio_espacos - 1] == " ":
                                inicio_espacos -= 1
                            texto_antes_trofeu = texto_base[:inicio_espacos]
                            faixa_espacos = texto_base[inicio_espacos : indice_x + 1]
                            x_trofeu = rect_base.left() + metricas.horizontalAdvance(texto_antes_trofeu)
                            largura_trofeu = max(10, metricas.horizontalAdvance(faixa_espacos))

                if x_trofeu >= 0 and largura_trofeu > 0:
                    pixmap_trofeu = self._obter_pixmap_trofeu("ouro")
                    if not pixmap_trofeu.isNull():
                        tamanho_trofeu = max(10, min(rect_base.height() - 4, largura_trofeu + 4))
                        pixmap_trofeu_escalado = pixmap_trofeu.scaled(
                            tamanho_trofeu,
                            tamanho_trofeu,
                            Qt.KeepAspectRatio,
                            Qt.SmoothTransformation,
                        )
                        x_trofeu_draw = x_trofeu + max(
                            0,
                            (largura_trofeu - pixmap_trofeu_escalado.width()) // 2,
                        )
                        y_trofeu_draw = (
                            rect_base.top()
                            + (rect_base.height() - pixmap_trofeu_escalado.height()) // 2
                        )
                        painter.drawPixmap(x_trofeu_draw, y_trofeu_draw, pixmap_trofeu_escalado)

                if seta_sobre_trofeu:
                    if indice_trofeu >= 0:
                        fonte_seta = QFont(fonte)
                        tamanho_seta = fonte_seta.pointSizeF()
                        if tamanho_seta <= 0:
                            tamanho_seta = float(fonte_seta.pointSize())
                        fonte_seta.setPointSizeF(max(6.6, tamanho_seta - 1.5))
                        fonte_seta.setBold(True)
                        painter.setFont(fonte_seta)
                        painter.setPen(cor_seta_sobre_trofeu)
                        rect_seta_trofeu = QRect(
                            x_trofeu + max(0, (largura_trofeu // 2) - 4),
                            rect_base.top() + 1,
                            9,
                            9,
                        )
                        painter.drawText(rect_seta_trofeu, Qt.AlignCenter, "▲")

                if sufixos:
                    cursor_sufixo = x_sufixo
                    for indice_sufixo, (texto_sufixo, cor_sufixo, gap_item) in enumerate(sufixos):
                        if indice_sufixo > 0:
                            cursor_sufixo += max(0, int(gap_item))
                        largura_item = max(8, metricas.horizontalAdvance(texto_sufixo))
                        rect_sufixo = QRect(cursor_sufixo, area.top(), largura_item, area.height())
                        painter.setPen(cor_sufixo)
                        painter.drawText(rect_sufixo, Qt.AlignVCenter | Qt.AlignLeft, texto_sufixo)
                        cursor_sufixo += largura_item

                painter.restore()
                return

            painter.setFont(fonte)
            painter.setPen(cor_texto)
            rect_texto = option.rect.adjusted(6, 0, -6, 0)
            painter.drawText(rect_texto, alinhamento, texto)
            painter.restore()
            return

        # Margem de 1px em cada lateral: gera respiro de 2px entre badges.
        badge_rect = option.rect.adjusted(1, 6, -1, -6)
        cor_fundo = str(payload.get("cor_fundo", HIST_BG_CARD))
        cor_borda = str(payload.get("cor_borda", HIST_BORDER))
        cor_texto = str(payload.get("cor_texto", HIST_TEXT_PRIMARY))
        texto = str(payload.get("texto", ""))
        negrito = bool(payload.get("negrito", False))
        marcador_vmr = bool(payload.get("marcador_vmr", False))

        painter.setPen(QColor(cor_borda))
        painter.setBrush(QColor(cor_fundo))
        painter.drawRect(badge_rect.adjusted(0, 0, -1, -1))

        fonte = option.font
        fonte.setBold(negrito)
        painter.setFont(fonte)
        painter.setPen(QColor(cor_texto))
        painter.drawText(badge_rect, Qt.AlignCenter, texto)

        if marcador_vmr:
            tamanho_ponto = max(3, min(5, badge_rect.height() // 3))
            rect_ponto = QRect(
                badge_rect.right() - tamanho_ponto - 2,
                badge_rect.bottom() - tamanho_ponto - 2,
                tamanho_ponto,
                tamanho_ponto,
            )
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#a855f7"))
            painter.drawEllipse(rect_ponto)

        painter.restore()


class TelaHistoria(QWidget, UXMixin):
    def __init__(
        self,
        banco,
        parent=None,
        ao_voltar: Callable[[], None] | None = None,
    ):
        super().__init__(parent)

        self.banco = banco
        self._ao_voltar = ao_voltar
        self._arquivo_anos_expandidos: dict[int, bool] = {}
        self._arquivo_modo_filtro = "Todas"
        self._arquivo_categoria_filtro = "Todas"
        self._arquivo_ordem_filtro = "Mais Recente"
        self._classificacao_temporadas_atual: list[dict[str, Any]] = []
        self._piloto_id_destacado_temporadas: Any = None
        self._piloto_nome_destacado_temporadas: str = ""
        self._destacar_somente_piloto_temporadas: bool = False
        self._equipe_chave_destacada_temporadas: str = ""
        self._cor_equipe_destacada_temporadas: str = ""
        self._ultimo_clique_linha_temporadas: int = -1
        self._ultimo_clique_ts_temporadas: float = 0.0
        self._ultimo_open_ficha_piloto_ts: float = 0.0
        self._estilos_controles_janela_parent: dict[str, str] = {}

        self.setWindowTitle("Historia do Modo Carreira")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        self.setObjectName("tela_historia")
        self.setStyleSheet(
            f"""
            QWidget#tela_historia,
            QWidget#historia_area_conteudo,
            QWidget#historia_tab_page {{
                background-color: {HIST_BG_APP};
            }}
            QLabel {{
                color: {HIST_TEXT_PRIMARY};
            }}
            QLineEdit, QComboBox {{
                background-color: {HIST_BG_SURFACE};
                color: {HIST_TEXT_PRIMARY};
                border: 1px solid {HIST_BORDER};
                border-radius: 8px;
                padding: 5px 8px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {HIST_ACCENT};
            }}
            QComboBox QAbstractItemView {{
                background-color: {HIST_BG_CARD};
                color: {HIST_TEXT_PRIMARY};
                border: 1px solid {HIST_BORDER};
                selection-background-color: {HIST_BG_SURFACE_ALT};
                selection-color: {HIST_TEXT_PRIMARY};
            }}
            """
        )

        self._build_ui()
        self._aplicar_tema_controles_janela_parent()
        self._setup_ux()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_top_navigation_historia())

        area_conteudo = QWidget()
        area_conteudo.setObjectName("historia_area_conteudo")
        layout_conteudo = QVBoxLayout(area_conteudo)
        layout_conteudo.setContentsMargins(14, 12, 14, 12)
        layout_conteudo.setSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabs_historia")
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{
                border: none;
                background: {HIST_BG_APP};
            }}
            QTabBar::tab {{
                max-height: 0px;
                max-width: 0px;
                margin: 0px;
                padding: 0px;
                border: none;
            }}
        """
        )

        self.tab_temporadas = self._build_tab_temporadas()
        self.tab_temporadas.setObjectName("historia_tab_page")
        self.tabs.addTab(self.tab_temporadas, "Temporadas")

        self.tab_arquivo = self._build_tab_arquivo()
        self.tab_arquivo.setObjectName("historia_tab_page")
        self.tabs.addTab(self.tab_arquivo, "Arquivo")

        self.tab_trofeus = self._build_tab_trofeus()
        self.tab_trofeus.setObjectName("historia_tab_page")
        self.tabs.addTab(self.tab_trofeus, "Sala de Trofeus")

        self.tab_rivalidades = self._build_tab_rivalidades_ia()
        self.tab_rivalidades.setObjectName("historia_tab_page")
        self.tabs.addTab(self.tab_rivalidades, "Rivais")
        self.tabs.setCurrentWidget(self.tab_temporadas)
        self.tabs.currentChanged.connect(self._atualizar_navegacao_historia_ativa)

        layout_conteudo.addWidget(self.tabs, stretch=1)
        layout.addWidget(area_conteudo, stretch=1)

        self._atualizar_navegacao_historia_ativa()
        self._atualizar_header_historia()

    def _build_top_navigation_historia(self):
        header = QFrame()
        header.setObjectName("header_historia")
        header.setFixedHeight(92)
        header.setStyleSheet(
            f"""
            QFrame#header_historia {{
                background-color: {HIST_BG_HEADER};
                border-bottom: 1px solid {HIST_BORDER};
            }}
            QPushButton#btn_tab_hist {{
                background-color: transparent;
                color: {HIST_TEXT_SECONDARY};
                border: none;
                border-radius: 16px;
                padding: 6px 14px;
                font-size: 10pt;
                font-weight: 600;
            }}
            QPushButton#btn_tab_hist:hover {{
                color: {HIST_TEXT_PRIMARY};
                background-color: {HIST_BG_CARD};
            }}
            QPushButton#btn_tab_hist:checked {{
                color: {HIST_ACCENT};
                background-color: {HIST_BG_SURFACE_ALT};
            }}
            QPushButton#btn_fechar_hist {{
                background-color: {HIST_BG_SURFACE};
                color: {HIST_TEXT_SECONDARY};
                border: 1px solid {HIST_BORDER};
                border-radius: 8px;
                min-height: 34px;
                padding: 0 14px;
                font-weight: 600;
            }}
            QPushButton#btn_fechar_hist:hover {{
                color: {HIST_TEXT_PRIMARY};
                border-color: {HIST_ACCENT};
            }}
        """
        )

        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 10, 18, 10)
        layout.setSpacing(12)

        branding = QWidget()
        branding_layout = QVBoxLayout(branding)
        branding_layout.setContentsMargins(0, 0, 0, 0)
        branding_layout.setSpacing(1)

        lbl_brand = QLabel("HISTORIA DA CARREIRA")
        fonte_brand = QFont("Bahnschrift SemiBold", 16)
        fonte_brand.setBold(True)
        fonte_brand.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        lbl_brand.setFont(fonte_brand)
        lbl_brand.setStyleSheet(f"color: {HIST_TEXT_PRIMARY}; border: none;")
        branding_layout.addWidget(lbl_brand)

        self.lbl_header_subtitulo = QLabel("Arquivo consolidado da sua trajetória")
        self.lbl_header_subtitulo.setFont(Fontes.texto_pequeno())
        self.lbl_header_subtitulo.setStyleSheet(
            f"color: {HIST_TEXT_SECONDARY}; border: none;"
        )
        branding_layout.addWidget(self.lbl_header_subtitulo)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.nav_hist_buttons: list[QPushButton] = []
        abas = [
            ("Temporadas", 0),
            ("Arquivo", 1),
            ("Trofeus", 2),
            ("Rivais", 3),
        ]
        for titulo, indice in abas:
            botao = self._criar_botao_navegacao_historia(titulo, indice)
            self.nav_hist_buttons.append(botao)
            nav_layout.addWidget(botao)

        btn_fechar = QPushButton("Voltar")
        btn_fechar.setObjectName("btn_fechar_hist")
        btn_fechar.setCursor(Qt.PointingHandCursor)
        btn_fechar.clicked.connect(self._voltar_para_dashboard)

        largura_reserva_direita = btn_fechar.sizeHint().width() + 28
        parent_widget = self.parentWidget()
        top_right_widget = getattr(parent_widget, "_top_right_widget", None)
        if top_right_widget is not None and top_right_widget.width() > largura_reserva_direita:
            largura_reserva_direita = top_right_widget.width()

        bloco_direito = QWidget()
        bloco_direito.setFixedWidth(largura_reserva_direita)
        layout_bloco_direito = QHBoxLayout(bloco_direito)
        layout_bloco_direito.setContentsMargins(0, 0, 0, 0)
        layout_bloco_direito.addWidget(btn_fechar, 0, Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(branding, 0, Qt.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(nav_widget, 0, Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(bloco_direito, 0, Qt.AlignRight | Qt.AlignVCenter)

        return header

    def _criar_botao_navegacao_historia(self, texto: str, indice: int) -> QPushButton:
        botao = QPushButton(texto)
        botao.setObjectName("btn_tab_hist")
        botao.setCheckable(True)
        botao.setCursor(Qt.PointingHandCursor)
        botao.clicked.connect(
            lambda _checked=False, idx=indice: self._mostrar_aba_historia(idx)
        )
        return botao

    def _build_action_bar_historia(self):
        painel = QFrame()
        painel.setObjectName("painel_historia")
        painel.setStyleSheet(
            f"""
            QFrame#painel_historia {{
                background-color: {HIST_BG_CARD};
                border: 1px solid {HIST_BORDER};
                border-radius: 11px;
            }}
        """
        )
        painel.setFixedHeight(52)

        layout = QHBoxLayout(painel)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.lbl_resumo_arquivo = QLabel("Carregando histórico...")
        self.lbl_resumo_arquivo.setFont(Fontes.texto_normal())
        self.lbl_resumo_arquivo.setStyleSheet(
            f"color: {HIST_TEXT_SECONDARY}; border: none; background: transparent;"
        )
        self.lbl_resumo_arquivo.setWordWrap(False)
        layout.addWidget(self.lbl_resumo_arquivo, stretch=1)

        self.stat_hist_temporadas = None
        self.stat_hist_titulos = None
        self.stat_hist_podios = None
        self.stat_hist_rivais = None

        btn_atualizar = BotaoSecondary("Atualizar Dados")
        btn_atualizar.setMinimumWidth(130)
        btn_atualizar.clicked.connect(self._atualizar_dados_historia)
        layout.addWidget(btn_atualizar)

        btn_fechar = BotaoSecondary("Voltar")
        btn_fechar.setMinimumWidth(130)
        btn_fechar.clicked.connect(self._voltar_para_dashboard)
        layout.addWidget(btn_fechar)

        return painel

    def _voltar_para_dashboard(self):
        self._restaurar_tema_controles_janela_parent()
        if callable(self._ao_voltar):
            self._ao_voltar()
            return
        self.close()

    def closeEvent(self, event):
        self._restaurar_tema_controles_janela_parent()
        super().closeEvent(event)

    def showEvent(self, event):
        self._aplicar_tema_controles_janela_parent()
        super().showEvent(event)

    def _aplicar_tema_controles_janela_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        barra = getattr(parent, "_barra_controles_fullscreen", None)
        if isinstance(barra, QWidget):
            self._estilos_controles_janela_parent.setdefault("barra", barra.styleSheet() or "")
            barra.setStyleSheet(
                f"""
                QFrame#barra_controles_fullscreen {{
                    background-color: rgba(24, 19, 18, 0.96);
                    border: 1px solid {HIST_BORDER};
                    border-radius: 9px;
                }}
                """
            )

        estilo_btn_base = f"""
            QPushButton {{
                background-color: transparent;
                color: {HIST_TEXT_PRIMARY};
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 10pt;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {HIST_BG_SURFACE_ALT};
                border-color: {HIST_BORDER_HOVER};
            }}
        """
        botoes = {
            "janela": getattr(parent, "_btn_janela_modo", None),
            "min": getattr(parent, "_btn_minimizar_fullscreen", None),
            "close": getattr(parent, "_btn_fechar_fullscreen", None),
        }
        for chave, botao in botoes.items():
            if not isinstance(botao, QPushButton):
                continue
            self._estilos_controles_janela_parent.setdefault(
                f"btn_{chave}",
                botao.styleSheet() or "",
            )
            if chave == "close":
                botao.setStyleSheet(
                    estilo_btn_base
                    + f"""
                    QPushButton:hover {{
                        background-color: {Cores.VERMELHO};
                        border-color: {Cores.VERMELHO};
                        color: #ffffff;
                    }}
                    """
                )
            else:
                botao.setStyleSheet(estilo_btn_base)

    def _restaurar_tema_controles_janela_parent(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        barra = getattr(parent, "_barra_controles_fullscreen", None)
        if isinstance(barra, QWidget) and "barra" in self._estilos_controles_janela_parent:
            barra.setStyleSheet(self._estilos_controles_janela_parent.get("barra", ""))

        mapa_botoes = {
            "btn_janela": getattr(parent, "_btn_janela_modo", None),
            "btn_min": getattr(parent, "_btn_minimizar_fullscreen", None),
            "btn_close": getattr(parent, "_btn_fechar_fullscreen", None),
        }
        for chave, botao in mapa_botoes.items():
            if isinstance(botao, QPushButton) and chave in self._estilos_controles_janela_parent:
                botao.setStyleSheet(self._estilos_controles_janela_parent.get(chave, ""))

    def _coletar_resumo_header_historia(self) -> dict[str, int]:
        historico = self._coletar_temporadas_historico()
        titulos = 0
        podios = 0
        participacoes = 0

        for temporada in historico:
            entrada = self._obter_entrada_jogador_temporada(temporada)
            if not entrada:
                continue
            participacoes += 1
            posicao = self._safe_int(entrada.get("posicao"), default=0)
            if posicao == 1:
                titulos += 1
            if 1 <= posicao <= 3:
                podios += 1

        ultimo_ano = max(
            [self._safe_int(item.get("ano"), default=0) for item in historico],
            default=0,
        )
        temporadas_validas = [item for item in historico if self._safe_int(item.get("ano"), default=0) > 0]
        anos_unicos = {self._safe_int(item.get("ano"), default=0) for item in temporadas_validas}

        return {
            "temporadas": len(historico),
            "titulos": titulos,
            "podios": podios,
            "participacoes": participacoes,
            "ultimo_ano": ultimo_ano,
            "rivais": max(len(anos_unicos), 0),
        }

    def _atualizar_header_historia(self):
        resumo = self._coletar_resumo_header_historia()

        ultimo_ano = int(resumo.get("ultimo_ano", 0))
        if ultimo_ano > 0:
            subtitulo = (
                f"Temporadas: {resumo['temporadas']} • "
                f"Títulos: {resumo['titulos']} • "
                f"Último ano: {ultimo_ano}"
            )
        else:
            subtitulo = "Arquivo consolidado da sua trajetória"

        if hasattr(self, "lbl_header_subtitulo"):
            self.lbl_header_subtitulo.setText(subtitulo)
        if hasattr(self, "lbl_resumo_arquivo"):
            self.lbl_resumo_arquivo.setText(
                f"Participações registradas: {resumo['participacoes']}"
            )

        if hasattr(self, "stat_hist_temporadas") and self.stat_hist_temporadas is not None:
            self.stat_hist_temporadas.set_valor(resumo["temporadas"])
        if hasattr(self, "stat_hist_titulos") and self.stat_hist_titulos is not None:
            self.stat_hist_titulos.set_valor(resumo["titulos"])
        if hasattr(self, "stat_hist_podios") and self.stat_hist_podios is not None:
            self.stat_hist_podios.set_valor(resumo["podios"])
        if hasattr(self, "stat_hist_rivais") and self.stat_hist_rivais is not None:
            self.stat_hist_rivais.set_valor(resumo["rivais"])

    def _atualizar_dados_historia(self):
        def _executar_atualizacao():
            if hasattr(self, "_atualizar_arquivo_temporadas"):
                self._atualizar_arquivo_temporadas()
            if hasattr(self, "_atualizar_tabela_temporadas"):
                self._atualizar_tabela_temporadas()
            if hasattr(self, "_atualizar_sala_trofeus"):
                self._atualizar_sala_trofeus()
            if hasattr(self, "_atualizar_rivalidades_ia"):
                self._atualizar_rivalidades_ia()
            self._atualizar_header_historia()

        if getattr(self, "_ux_initialized", False):
            self.executar_com_loading(
                operacao=_executar_atualizacao,
                mensagem="Atualizando dados da historia...",
                callback_sucesso=lambda: self.mostrar_toast_sucesso("Dados da historia atualizados."),
            )
            return

        _executar_atualizacao()

    def _mostrar_aba_historia(self, indice: int):
        if 0 <= indice < self.tabs.count():
            if getattr(self, "_ux_initialized", False) and hasattr(self, "transicao_para_aba"):
                self.transicao_para_aba(indice)
                self._atualizar_navegacao_historia_ativa()
            else:
                self.tabs.setCurrentIndex(indice)
                self._atualizar_navegacao_historia_ativa()
            return
        self._atualizar_navegacao_historia_ativa()

    def _atualizar_navegacao_historia_ativa(self, *_):
        botoes = getattr(self, "nav_hist_buttons", [])
        if not botoes or not hasattr(self, "tabs"):
            return

        indice_ativo = self.tabs.currentIndex()
        for indice, botao in enumerate(botoes):
            botao.setChecked(indice == indice_ativo)

    def _estilo_tabela_historia(self) -> str:
        return f"""
            QTableWidget {{
                background-color: {HIST_BG_SURFACE};
                color: {HIST_TEXT_PRIMARY};
                border: 1px solid {HIST_BORDER};
                border-radius: 10px;
                gridline-color: {HIST_BORDER};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 5px 9px;
                border-bottom: 1px solid {HIST_BORDER};
            }}
            QTableWidget::item:selected {{
                color: {HIST_TEXT_PRIMARY};
                border-bottom: 1px solid {HIST_BORDER};
            }}
            QHeaderView::section {{
                background-color: {HIST_BG_SURFACE_ALT};
                color: {HIST_TEXT_SECONDARY};
                border: none;
                border-bottom: 1px solid {HIST_BORDER};
                padding: 7px 8px;
                font-weight: 700;
                text-transform: uppercase;
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: {HIST_BG_SURFACE_ALT};
                border: none;
            }}
        """

    def _estilo_scroll_historia(self) -> str:
        return f"""
            QScrollArea {{
                border: 1px solid {HIST_BORDER};
                border-radius: {Espacos.RAIO_CARD}px;
                background-color: {HIST_BG_SURFACE};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {HIST_BORDER_HOVER};
                border-radius: 4px;
                min-height: 28px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """

    def _alternar_categoria_temporadas(self, passo: int):
        if not hasattr(self, "combo_categoria"):
            return
        categorias = getattr(self, "_categorias_temporadas_nomes", None)
        total = len(categorias) if isinstance(categorias, list) else 0
        if total <= 0 and hasattr(self.combo_categoria, "combo"):
            total = int(self.combo_categoria.combo.count())
        if total <= 0:
            return
        indice_atual = int(self.combo_categoria.currentIndex())
        if indice_atual < 0:
            indice_atual = 0
        self.combo_categoria.setCurrentIndex((indice_atual + passo) % total)

    def _alternar_ano_temporadas(self, passo: int):
        if not hasattr(self, "combo_ano"):
            return
        anos = getattr(self, "_anos_temporadas_disponiveis", None)
        total = len(anos) if isinstance(anos, list) else 0
        if total <= 0 and hasattr(self.combo_ano, "combo"):
            total = int(self.combo_ano.combo.count())
        if total <= 0:
            return
        indice_atual = int(self.combo_ano.currentIndex())
        if indice_atual < 0:
            indice_atual = 0
        self.combo_ano.setCurrentIndex((indice_atual + passo) % total)

    def _alternar_ano_rivalidades(self, passo: int):
        if not hasattr(self, "combo_ano_rival"):
            return
        anos = getattr(self, "_anos_rivalidades_disponiveis", None)
        total = len(anos) if isinstance(anos, list) else 0
        if total <= 0 and hasattr(self.combo_ano_rival, "combo"):
            total = int(self.combo_ano_rival.combo.count())
        if total <= 0:
            return
        indice_atual = int(self.combo_ano_rival.currentIndex())
        if indice_atual < 0:
            indice_atual = 0
        self.combo_ano_rival.setCurrentIndex((indice_atual + passo) % total)

    def _alternar_categoria_rivalidades(self, passo: int):
        if not hasattr(self, "combo_categoria_rival"):
            return
        categorias = getattr(self, "_categorias_rivalidades_nomes", None)
        total = len(categorias) if isinstance(categorias, list) else 0
        if total <= 0 and hasattr(self.combo_categoria_rival, "combo"):
            total = int(self.combo_categoria_rival.combo.count())
        if total <= 0:
            return
        indice_atual = int(self.combo_categoria_rival.currentIndex())
        if indice_atual < 0:
            indice_atual = 0
        self.combo_categoria_rival.setCurrentIndex((indice_atual + passo) % total)

    def _build_tab_temporadas(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        titulo = QLabel("TEMPORADAS COMPLETAS")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {HIST_ACCENT};")
        layout.addWidget(titulo)

        layout.addWidget(Separador())

        filtros_widget = QWidget()
        filtros_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout = QHBoxLayout(filtros_widget)
        filtros_layout.setContentsMargins(0, 0, 0, 0)
        filtros_layout.setSpacing(6)

        historico = self.banco.get("historico_temporadas_completas", [])
        anos_disponiveis = sorted({h["ano"] for h in historico}, reverse=True)

        estilo_seta = f"""
            QToolButton {{
                background-color: {HIST_BG_SURFACE_ALT};
                color: {HIST_TEXT_SECONDARY};
                border: 1px solid {HIST_BORDER};
                border-radius: 4px;
                font-weight: 700;
            }}
            QToolButton:hover {{
                background-color: {HIST_BG_CARD_HOVER};
                color: {HIST_TEXT_PRIMARY};
                border-color: {HIST_BORDER_HOVER};
            }}
            QToolButton:pressed {{
                background-color: {HIST_BG_SURFACE};
            }}
        """

        self.combo_ano = CampoCombo("Ano", [str(ano) for ano in anos_disponiveis])
        self._anos_temporadas_disponiveis = [str(ano) for ano in anos_disponiveis]
        self.combo_ano.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if anos_disponiveis:
            self.combo_ano.setCurrentIndex(0)
        self.combo_ano.currentTextChanged.connect(self._atualizar_tabela_temporadas)

        ano_controles = QWidget()
        ano_controles.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        ano_controles_layout = QHBoxLayout(ano_controles)
        ano_controles_layout.setContentsMargins(0, 0, 0, 0)
        ano_controles_layout.setSpacing(4)
        ano_controles_layout.addWidget(self.combo_ano)

        setas_ano_layout = QVBoxLayout()
        setas_ano_layout.setContentsMargins(0, 20, 0, 0)
        setas_ano_layout.setSpacing(2)

        btn_ano_cima = QToolButton()
        btn_ano_cima.setText("▲")
        btn_ano_cima.setCursor(Qt.PointingHandCursor)
        btn_ano_cima.setToolTip("Ano anterior")
        btn_ano_cima.setFixedSize(22, 16)
        btn_ano_cima.setStyleSheet(estilo_seta)
        btn_ano_cima.clicked.connect(lambda: self._alternar_ano_temporadas(-1))
        setas_ano_layout.addWidget(btn_ano_cima)

        btn_ano_baixo = QToolButton()
        btn_ano_baixo.setText("▼")
        btn_ano_baixo.setCursor(Qt.PointingHandCursor)
        btn_ano_baixo.setToolTip("Proximo ano")
        btn_ano_baixo.setFixedSize(22, 16)
        btn_ano_baixo.setStyleSheet(estilo_seta)
        btn_ano_baixo.clicked.connect(lambda: self._alternar_ano_temporadas(1))
        setas_ano_layout.addWidget(btn_ano_baixo)

        ano_controles_layout.addLayout(setas_ano_layout)
        filtros_layout.addWidget(ano_controles)

        categorias_nomes = [categoria["nome"] for categoria in CATEGORIAS]
        self._categorias_temporadas_nomes = list(categorias_nomes)
        self.combo_categoria = CampoCombo("Categoria", categorias_nomes)
        self.combo_categoria.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo_categoria.currentTextChanged.connect(
            self._atualizar_tabela_temporadas
        )
        categoria_controles = QWidget()
        categoria_controles.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        categoria_controles_layout = QHBoxLayout(categoria_controles)
        categoria_controles_layout.setContentsMargins(0, 0, 0, 0)
        categoria_controles_layout.setSpacing(4)
        categoria_controles_layout.addWidget(self.combo_categoria)

        setas_layout = QVBoxLayout()
        setas_layout.setContentsMargins(0, 20, 0, 0)
        setas_layout.setSpacing(2)

        btn_categoria_cima = QToolButton()
        btn_categoria_cima.setText("▲")
        btn_categoria_cima.setCursor(Qt.PointingHandCursor)
        btn_categoria_cima.setToolTip("Categoria anterior")
        btn_categoria_cima.setFixedSize(22, 16)
        btn_categoria_cima.setStyleSheet(estilo_seta)
        btn_categoria_cima.clicked.connect(
            lambda: self._alternar_categoria_temporadas(-1)
        )
        setas_layout.addWidget(btn_categoria_cima)

        btn_categoria_baixo = QToolButton()
        btn_categoria_baixo.setText("▼")
        btn_categoria_baixo.setCursor(Qt.PointingHandCursor)
        btn_categoria_baixo.setToolTip("Proxima categoria")
        btn_categoria_baixo.setFixedSize(22, 16)
        btn_categoria_baixo.setStyleSheet(estilo_seta)
        btn_categoria_baixo.clicked.connect(
            lambda: self._alternar_categoria_temporadas(1)
        )
        setas_layout.addWidget(btn_categoria_baixo)

        categoria_controles_layout.addLayout(setas_layout)
        filtros_layout.addWidget(categoria_controles)

        filtros_layout.addStretch()

        layout.addWidget(filtros_widget, 0)

        self.tabela_temporadas = QTableWidget()
        self._header_bandeiras_temporadas = BandeiraHeaderView(
            Qt.Horizontal,
            self.tabela_temporadas,
        )
        self.tabela_temporadas.setHorizontalHeader(self._header_bandeiras_temporadas)
        self.tabela_temporadas.setStyleSheet(self._estilo_tabela_historia())
        self.tabela_temporadas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_temporadas.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_temporadas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_temporadas.verticalHeader().setVisible(False)
        self.tabela_temporadas.setShowGrid(False)
        self.tabela_temporadas.setFocusPolicy(Qt.NoFocus)
        self.tabela_temporadas.cellClicked.connect(self._ao_clicar_linha_temporadas)
        self.tabela_temporadas.cellDoubleClicked.connect(
            self._ao_duplo_clique_linha_temporadas
        )
        self._delegate_resultados_temporadas = BadgeResultadoDelegate(self.tabela_temporadas)
        self.tabela_temporadas.setItemDelegate(self._delegate_resultados_temporadas)
        self.tabela_temporadas.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        area_tabelas = QWidget()
        area_tabelas_layout = QHBoxLayout(area_tabelas)
        area_tabelas_layout.setContentsMargins(0, 0, 0, 0)
        area_tabelas_layout.setSpacing(12)

        painel_pilotos = QWidget()
        painel_pilotos_layout = QVBoxLayout(painel_pilotos)
        painel_pilotos_layout.setContentsMargins(0, 0, 0, 0)
        painel_pilotos_layout.setSpacing(6)
        painel_pilotos_layout.addWidget(self.tabela_temporadas, 1)

        legenda = QLabel(
            "Grid de resultados: 1º ouro • 2º prata • 3º bronze • DNF vermelho"
        )
        legenda.setFont(Fontes.texto_pequeno())
        legenda.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        painel_pilotos_layout.addWidget(legenda)
        area_tabelas_layout.addWidget(painel_pilotos, 3)

        separador_vertical = QFrame()
        separador_vertical.setFixedWidth(1)
        separador_vertical.setStyleSheet(f"background-color: {HIST_BORDER};")
        area_tabelas_layout.addWidget(separador_vertical)

        painel_equipes = QWidget()
        painel_equipes_layout = QVBoxLayout(painel_equipes)
        painel_equipes_layout.setContentsMargins(0, 0, 0, 0)
        painel_equipes_layout.setSpacing(6)

        titulo_equipes = QLabel("CLASSIFICAÇÃO DE CONSTRUTORES")
        titulo_equipes.setFont(Fontes.titulo_medio())
        titulo_equipes.setStyleSheet(f"color: {HIST_ACCENT};")
        painel_equipes_layout.addWidget(titulo_equipes)

        self.tabela_equipes_temporadas = QTableWidget()
        self.tabela_equipes_temporadas.setColumnCount(4)
        self.tabela_equipes_temporadas.setHorizontalHeaderLabels(
            ["POS", "EQUIPE", "PTS", "TAÇAS"]
        )
        self.tabela_equipes_temporadas.setStyleSheet(self._estilo_tabela_historia())
        self.tabela_equipes_temporadas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_equipes_temporadas.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_equipes_temporadas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_equipes_temporadas.verticalHeader().setVisible(False)
        self.tabela_equipes_temporadas.setShowGrid(False)
        self.tabela_equipes_temporadas.setFocusPolicy(Qt.NoFocus)
        self.tabela_equipes_temporadas.cellClicked.connect(
            self._ao_clicar_linha_equipes_temporadas
        )
        self.tabela_equipes_temporadas.cellDoubleClicked.connect(
            self._ao_duplo_clique_linha_equipes_temporadas
        )
        self._delegate_equipes_temporadas = BadgeResultadoDelegate(
            self.tabela_equipes_temporadas
        )
        self.tabela_equipes_temporadas.setItemDelegate(self._delegate_equipes_temporadas)
        header_equipes = self.tabela_equipes_temporadas.horizontalHeader()
        header_equipes.setSectionResizeMode(0, QHeaderView.Fixed)
        header_equipes.setSectionResizeMode(1, QHeaderView.Stretch)
        header_equipes.setSectionResizeMode(2, QHeaderView.Fixed)
        header_equipes.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabela_equipes_temporadas.setColumnWidth(0, 58)
        self.tabela_equipes_temporadas.setColumnWidth(2, 80)
        self.tabela_equipes_temporadas.setColumnWidth(3, 230)
        self.tabela_equipes_temporadas.setMinimumWidth(420)
        self.tabela_equipes_temporadas.setMaximumWidth(620)
        painel_equipes_layout.addWidget(self.tabela_equipes_temporadas, 1)

        legenda_equipes = QLabel("🏆 Equipes agregadas: pontos + taças por temporada")
        legenda_equipes.setFont(Fontes.texto_pequeno())
        legenda_equipes.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        painel_equipes_layout.addWidget(legenda_equipes)

        area_tabelas_layout.addWidget(painel_equipes, 2)
        layout.addWidget(area_tabelas, 1)

        if anos_disponiveis:
            self._atualizar_tabela_temporadas()

        return widget

    def _build_tab_arquivo(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        titulo = QLabel("HISTÓRICO E ARQUIVO")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {HIST_ACCENT};")
        layout.addWidget(titulo)

        layout.addWidget(Separador())
        self.lbl_stat_titulos = None
        self.lbl_stat_vices = None
        self.lbl_stat_terceiros = None
        self.lbl_stat_temporadas = None
        self.lbl_timeline_arquivo = None
        self.card_comparativo_arquivo = None
        self.lbl_comparativo_arquivo = None

        filtros_layout = QHBoxLayout()
        filtros_layout.setSpacing(8)

        self.combo_filtro_arquivo = CampoCombo(
            "Filtrar por",
            ["Todas", "Apenas Títulos", "Apenas Minhas"],
        )
        self.combo_filtro_arquivo.currentTextChanged.connect(self._ao_mudar_filtros_arquivo)
        filtros_layout.addWidget(self.combo_filtro_arquivo)

        categorias_nomes = ["Todas"] + [categoria["nome"] for categoria in CATEGORIAS]
        self.combo_filtro_categoria_arquivo = CampoCombo("Por Categoria", categorias_nomes)
        self.combo_filtro_categoria_arquivo.currentTextChanged.connect(
            self._ao_mudar_filtros_arquivo
        )
        filtros_layout.addWidget(self.combo_filtro_categoria_arquivo)

        self.combo_ordem_arquivo = CampoCombo("Ordenar", ["Mais Recente", "Mais Antigo"])
        self.combo_ordem_arquivo.currentTextChanged.connect(self._ao_mudar_filtros_arquivo)
        filtros_layout.addWidget(self.combo_ordem_arquivo)

        self.input_busca_arquivo = CampoTexto("Busca", "Ano ou categoria...")
        self.input_busca_arquivo.textChanged.connect(self._ao_mudar_filtros_arquivo)
        filtros_layout.addWidget(self.input_busca_arquivo)

        layout.addLayout(filtros_layout)

        self.scroll_arquivo = QScrollArea()
        self.scroll_arquivo.setWidgetResizable(True)
        self.scroll_arquivo.setStyleSheet(self._estilo_scroll_historia())

        self._content_arquivo = QWidget()
        self._layout_cards_arquivo = QVBoxLayout(self._content_arquivo)
        self._layout_cards_arquivo.setContentsMargins(8, 8, 8, 8)
        self._layout_cards_arquivo.setSpacing(8)

        self.scroll_arquivo.setWidget(self._content_arquivo)
        layout.addWidget(self.scroll_arquivo, stretch=1)

        self._atualizar_arquivo_temporadas()

        return widget

    def _criar_bloco_resumo_arquivo(self, icone: str, titulo: str):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        lbl_valor = QLabel(f"{icone} 0")
        lbl_valor.setAlignment(Qt.AlignCenter)
        lbl_valor.setFont(Fontes.titulo_medio())
        lbl_valor.setStyleSheet(f"color: {HIST_TEXT_PRIMARY}; border: none;")
        layout.addWidget(lbl_valor)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setAlignment(Qt.AlignCenter)
        lbl_titulo.setFont(Fontes.texto_pequeno())
        lbl_titulo.setStyleSheet(f"color: {HIST_TEXT_SECONDARY}; border: none;")
        layout.addWidget(lbl_titulo)

        container.setStyleSheet(
            f"""
            QWidget {{
                background-color: {HIST_BG_SURFACE};
                border: 1px solid {HIST_BORDER};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
        """
        )

        return container, lbl_valor

    def _safe_int(self, valor, default=0):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return default

    def _normalizar_id(self, valor: Any) -> str:
        if valor is None or isinstance(valor, bool):
            return ""
        texto = str(valor).strip()
        if not texto:
            return ""
        try:
            return str(int(texto))
        except (TypeError, ValueError):
            return texto.casefold()

    def _ids_equivalentes(self, a: Any, b: Any) -> bool:
        na = self._normalizar_id(a)
        nb = self._normalizar_id(b)
        return bool(na and nb and na == nb)

    def _coletar_temporadas_historico(self) -> list[dict[str, Any]]:
        return [
            item
            for item in self.banco.get("historico_temporadas_completas", [])
            if isinstance(item, dict)
        ]

    def _categoria_id_por_nome(self, nome_categoria: str) -> str | None:
        for categoria in CATEGORIAS:
            if str(categoria.get("nome", "")) == str(nome_categoria):
                return str(categoria.get("id", ""))
        return None

    def _obter_entrada_jogador_temporada(
        self,
        temporada: dict[str, Any],
    ) -> dict[str, Any] | None:
        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return None

        jogador = self._obter_jogador_atual()
        if not jogador:
            return None

        jogador_id = jogador.get("id")
        if jogador_id is not None:
            entrada_por_id = next(
                (
                    item
                    for item in classificacao
                    if self._ids_equivalentes(item.get("piloto_id"), jogador_id)
                ),
                None,
            )
            if entrada_por_id is not None:
                return entrada_por_id

        nome_jogador = self._normalizar_nome(
            jogador.get("nome") or self.banco.get("nome_jogador", "")
        )
        if not nome_jogador:
            return None

        return next(
            (
                item
                for item in classificacao
                if self._normalizar_nome(item.get("piloto", "")) == nome_jogador
            ),
            None,
        )

    def _ao_mudar_filtros_arquivo(self, *_):
        self._atualizar_arquivo_temporadas()

    def _aplicar_filtros_arquivo(
        self,
        temporadas: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        modo = (
            self.combo_filtro_arquivo.currentText()
            if hasattr(self, "combo_filtro_arquivo")
            else self._arquivo_modo_filtro
        )
        categoria_nome = (
            self.combo_filtro_categoria_arquivo.currentText()
            if hasattr(self, "combo_filtro_categoria_arquivo")
            else self._arquivo_categoria_filtro
        )
        ordem = (
            self.combo_ordem_arquivo.currentText()
            if hasattr(self, "combo_ordem_arquivo")
            else self._arquivo_ordem_filtro
        )
        busca = (
            self.input_busca_arquivo.text().strip()
            if hasattr(self, "input_busca_arquivo")
            else ""
        )
        busca_norm = busca.casefold()

        self._arquivo_modo_filtro = modo
        self._arquivo_categoria_filtro = categoria_nome
        self._arquivo_ordem_filtro = ordem

        categoria_id_filtro = (
            self._categoria_id_por_nome(categoria_nome)
            if categoria_nome and categoria_nome != "Todas"
            else None
        )

        filtradas: list[dict[str, Any]] = []
        for temporada in temporadas:
            entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
            participou = entrada_jogador is not None
            posicao_jogador = (
                self._safe_int(entrada_jogador.get("posicao"), default=999)
                if entrada_jogador
                else 999
            )

            categoria_id = str(temporada.get("categoria_id", ""))
            categoria_nome_resolvida = (
                str(temporada.get("categoria_nome", "")).strip()
                or self._nome_categoria_por_id(categoria_id)
            )
            ano = self._safe_int(temporada.get("ano"), default=0)

            if categoria_id_filtro and categoria_id != categoria_id_filtro:
                continue

            if modo == "Apenas Minhas" and not participou:
                continue
            if modo == "Apenas Títulos" and posicao_jogador != 1:
                continue

            if busca_norm:
                alvo = f"{ano} {categoria_nome_resolvida} {categoria_id}".casefold()
                if busca_norm not in alvo:
                    continue

            filtradas.append(temporada)

        if ordem == "Mais Antigo":
            return sorted(
                filtradas,
                key=lambda item: (
                    self._safe_int(item.get("ano"), default=0),
                    self._ordem_categoria(item.get("categoria_id", "")),
                    self._nome_categoria_por_id(item.get("categoria_id", "")).casefold(),
                ),
            )

        return sorted(
            filtradas,
            key=lambda item: (
                -self._safe_int(item.get("ano"), default=0),
                self._ordem_categoria(item.get("categoria_id", "")),
                self._nome_categoria_por_id(item.get("categoria_id", "")).casefold(),
            ),
        )

    def _atualizar_resumo_geral_arquivo(self, temporadas: list[dict[str, Any]]):
        titulos = 0
        vices = 0
        terceiros = 0
        total = 0

        for temporada in temporadas:
            entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
            if not entrada_jogador:
                continue
            total += 1
            pos = self._safe_int(entrada_jogador.get("posicao"), default=0)
            if pos == 1:
                titulos += 1
            elif pos == 2:
                vices += 1
            elif pos == 3:
                terceiros += 1

        if hasattr(self, "lbl_stat_titulos") and self.lbl_stat_titulos is not None:
            self.lbl_stat_titulos.setText(f"🏆 {titulos}")
        if hasattr(self, "lbl_stat_vices") and self.lbl_stat_vices is not None:
            self.lbl_stat_vices.setText(f"🥈 {vices}")
        if hasattr(self, "lbl_stat_terceiros") and self.lbl_stat_terceiros is not None:
            self.lbl_stat_terceiros.setText(f"🥉 {terceiros}")
        if hasattr(self, "lbl_stat_temporadas") and self.lbl_stat_temporadas is not None:
            self.lbl_stat_temporadas.setText(f"📅 {total}")

    def _resumo_ano_jogador(self, temporadas_ano: list[dict[str, Any]]) -> str:
        participacoes = 0
        titulos = 0
        vices = 0
        terceiros = 0
        melhor_categoria = ""
        melhor_pos = 999

        for temporada in temporadas_ano:
            entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
            if not entrada_jogador:
                continue
            participacoes += 1
            posicao = self._safe_int(entrada_jogador.get("posicao"), default=999)
            if posicao == 1:
                titulos += 1
            elif posicao == 2:
                vices += 1
            elif posicao == 3:
                terceiros += 1

            if posicao < melhor_pos:
                melhor_pos = posicao
                categoria_id = temporada.get("categoria_id", "")
                melhor_categoria = (
                    str(temporada.get("categoria_nome", "")).strip()
                    or self._nome_categoria_por_id(categoria_id)
                )

        if participacoes == 0:
            return "Você não participou deste ano."

        if titulos > 0:
            melhor_momento = f'Campeão do {melhor_categoria}!'
        elif melhor_pos <= 3:
            melhor_momento = f"P{melhor_pos} no {melhor_categoria}."
        else:
            melhor_momento = f"Melhor resultado: P{melhor_pos} no {melhor_categoria}."

        return (
            f"Você participou de: {participacoes} categoria(s)\n"
            f"Resultados: 🏆 {titulos} | 🥈 {vices} | 🥉 {terceiros}\n"
            f"Melhor momento: {melhor_momento}"
        )

    def _atualizar_timeline_arquivo(self, temporadas: list[dict[str, Any]]):
        if (
            not hasattr(self, "lbl_timeline_arquivo")
            or self.lbl_timeline_arquivo is None
        ):
            return

        anos = sorted(
            {
                self._safe_int(item.get("ano"), default=0)
                for item in temporadas
                if self._safe_int(item.get("ano"), default=0) > 0
            }
        )
        ano_atual = self._safe_int(self.banco.get("ano_atual"), default=0)
        if ano_atual > 0 and ano_atual not in anos:
            anos.append(ano_atual)

        if not anos:
            self.lbl_timeline_arquivo.setText("Sem dados de linha do tempo.")
            return

        if len(anos) > 8:
            anos = anos[-8:]

        status_por_ano: dict[int, str] = {}
        anos_com_dados = {
            self._safe_int(item.get("ano"), default=0)
            for item in temporadas
            if self._safe_int(item.get("ano"), default=0) > 0
        }
        for ano in anos:
            temporadas_ano = [
                item
                for item in temporadas
                if self._safe_int(item.get("ano"), default=0) == ano
            ]
            resumo = self._resumo_ano_jogador(temporadas_ano)
            if "🏆" in resumo:
                status_por_ano[ano] = "Títulos"
            elif "P2" in resumo or "🥈" in resumo:
                status_por_ano[ano] = "Vice"
            elif ano == ano_atual and ano not in anos_com_dados:
                status_por_ano[ano] = "Em andamento"
            elif "não participou" in resumo:
                status_por_ano[ano] = "Sem participação"
            else:
                status_por_ano[ano] = "Competiu"

        marcos = []
        for ano in anos:
            status = status_por_ano.get(ano, "")
            if ano not in anos_com_dados and ano != ano_atual:
                continue
            marcos.append(f"{ano}: {status}")

        texto = " • ".join(marcos) if marcos else "Sem dados de linha do tempo."
        self.lbl_timeline_arquivo.setText(texto)
        self.lbl_timeline_arquivo.setToolTip(
            "Linha do tempo do arquivo\n" + texto
        )

    def _atualizar_comparativo_arquivo(self, temporadas: list[dict[str, Any]]):
        if (
            not hasattr(self, "lbl_comparativo_arquivo")
            or self.lbl_comparativo_arquivo is None
        ):
            return

        categorias_jogador: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
        for temporada in temporadas:
            entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
            if not entrada_jogador:
                continue
            categoria_id = str(temporada.get("categoria_id", ""))
            ano = self._safe_int(temporada.get("ano"), default=0)
            categorias_jogador[categoria_id].append((ano, entrada_jogador))

        if not categorias_jogador:
            self.lbl_comparativo_arquivo.setText("Sem histórico do jogador para comparar.")
            return

        categoria_filtro_nome = (
            self.combo_filtro_categoria_arquivo.currentText()
            if hasattr(self, "combo_filtro_categoria_arquivo")
            else "Todas"
        )
        categoria_id_base = (
            self._categoria_id_por_nome(categoria_filtro_nome)
            if categoria_filtro_nome and categoria_filtro_nome != "Todas"
            else None
        )
        if not categoria_id_base or categoria_id_base not in categorias_jogador:
            categoria_id_base = max(
                categorias_jogador.keys(),
                key=lambda item: len(categorias_jogador[item]),
            )

        dados = sorted(categorias_jogador.get(categoria_id_base, []), key=lambda item: item[0])
        if not dados:
            self.lbl_comparativo_arquivo.setText("Sem dados para o comparativo selecionado.")
            return

        dados_visiveis = dados[-3:]
        categoria_nome = self._nome_categoria_por_id(categoria_id_base)
        linha_anos = []
        for ano, entrada in dados_visiveis:
            pos = self._safe_int(entrada.get("posicao"), default=0)
            linha_anos.append(f"{ano}: P{pos}")
        linhas = [f"{categoria_nome}: " + " • ".join(linha_anos)]

        if len(dados_visiveis) >= 2:
            pos_ini = self._safe_int(dados_visiveis[0][1].get("posicao"), default=0)
            pos_fim = self._safe_int(dados_visiveis[-1][1].get("posicao"), default=0)
            if pos_ini > 0 and pos_fim > 0:
                ganho = pos_ini - pos_fim
                if ganho > 0:
                    linhas.append(f"📈 Tendência: +{ganho} posição(ões).")
                elif ganho < 0:
                    linhas.append(f"📉 Tendência: -{abs(ganho)} posição(ões).")
                else:
                    linhas.append("➖ Tendência estável.")

        self.lbl_comparativo_arquivo.setText("\n".join(linhas))

    def _nome_categoria_por_id(self, categoria_id: Any) -> str:
        categoria_id_str = str(categoria_id or "")
        categoria = next(
            (
                item
                for item in CATEGORIAS
                if str(item.get("id", "")) == categoria_id_str
            ),
            None,
        )
        if categoria:
            return str(categoria.get("nome", categoria_id_str))
        return categoria_id_str.upper() if categoria_id_str else "Categoria"

    def _ordem_categoria(self, categoria_id: Any) -> int:
        categoria_id_str = str(categoria_id or "")
        for indice, categoria in enumerate(CATEGORIAS):
            if str(categoria.get("id", "")) == categoria_id_str:
                return indice
        return len(CATEGORIAS) + 1

    def _obter_podio_temporada(self, temporada: dict[str, Any]) -> list[dict[str, Any]]:
        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return []

        classificacao_ordenada = sorted(
            classificacao,
            key=lambda item: self._safe_int(item.get("posicao"), default=999),
        )
        return classificacao_ordenada[:3]

    def _linhas_podio_temporada(self, temporada: dict[str, Any]) -> list[str]:
        podio = self._obter_podio_temporada(temporada)
        medalhas = {1: "🥇", 2: "🥈", 3: "🥉"}
        linhas: list[str] = []

        entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
        jogador_id = entrada_jogador.get("piloto_id") if entrada_jogador else None

        for posicao, entrada in enumerate(podio, start=1):
            nome = str(entrada.get("piloto", "-")).strip() or "-"
            if jogador_id is not None and entrada.get("piloto_id") == jogador_id:
                nome = "Você"
            pontos = self._safe_int(entrada.get("pontos"), default=0)
            vitorias = self._safe_int(entrada.get("vitorias"), default=0)
            podios = self._safe_int(entrada.get("podios"), default=0)
            linhas.append(
                f"{medalhas[posicao]} {posicao}º {nome} — {pontos} pts | {vitorias} vitórias | {podios} pódios"
            )

        for posicao in range(len(podio) + 1, 4):
            linhas.append(f"{medalhas[posicao]} {posicao}º —")

        return linhas

    def _calcular_streak_vitorias(self, resultados: list[Any]) -> int:
        maior = 0
        atual = 0
        for resultado in resultados:
            if self._safe_int(resultado, default=0) == 1:
                atual += 1
                maior = max(maior, atual)
            else:
                atual = 0
        return maior

    def _conquistas_temporada_jogador(self, temporada: dict[str, Any]) -> list[str]:
        entrada = self._obter_entrada_jogador_temporada(temporada)
        if not entrada:
            return []

        conquistas: list[str] = []
        posicao = self._safe_int(entrada.get("posicao"), default=999)
        vitorias = self._safe_int(entrada.get("vitorias"), default=0)
        podios = self._safe_int(entrada.get("podios"), default=0)
        resultados = list(entrada.get("resultados", []))

        if posicao == 1:
            conquistas.append("🏆 Campeão")
        if vitorias > 0:
            conquistas.append(f"🔥 {vitorias} vitória(s)")
        if podios >= 3:
            conquistas.append("🎯 Pódio constante")
        if resultados and "DNF" not in [str(r).upper() for r in resultados]:
            conquistas.append("✅ Sem DNF")

        streak = self._calcular_streak_vitorias(resultados)
        if streak >= 2:
            conquistas.append(f"🚀 {streak} vitórias seguidas")

        return conquistas

    def _texto_grafico_temporada(self, temporada: dict[str, Any]) -> tuple[str, str]:
        entrada = self._obter_entrada_jogador_temporada(temporada)
        if not entrada:
            return ("Sem dados do jogador para evolução.", "")

        resultados = list(entrada.get("resultados", []))
        if not resultados:
            return ("Sem corridas registradas nesta temporada.", "")

        pontos = []
        for resultado in resultados:
            if str(resultado).upper() == "DNF":
                pontos.append("DNF")
            else:
                pos = self._safe_int(resultado, default=0)
                pontos.append(f"P{pos}" if pos > 0 else "-")

        linha = " ─ ".join(pontos)

        primeira_pos = self._safe_int(resultados[0], default=99)
        ultima_pos = self._safe_int(resultados[-1], default=99)
        if primeira_pos != 99 and ultima_pos != 99:
            if ultima_pos < primeira_pos:
                insight = f"Você melhorou de P{primeira_pos} para P{ultima_pos} ao longo da temporada."
            elif ultima_pos > primeira_pos:
                insight = f"Você caiu de P{primeira_pos} para P{ultima_pos} ao longo da temporada."
            else:
                insight = f"Você manteve o nível entre P{primeira_pos} e P{ultima_pos}."
        else:
            insight = "A evolução inclui abandonos, então o ritmo foi irregular."

        return (linha, insight)

    def _cor_temporada_arquivo(self, temporada: dict[str, Any]) -> str:
        podio = self._obter_podio_temporada(temporada)
        if podio:
            return Cores.OURO
        return HIST_ACCENT

    def _jogador_participou_temporada(self, temporada: dict[str, Any]) -> bool:
        return self._obter_entrada_jogador_temporada(temporada) is not None

    def _criar_card_arquivo_temporada(
        self,
        temporada: dict[str, Any],
        *,
        destaque: bool = False,
    ) -> Card:
        ano = self._safe_int(temporada.get("ano"), default=0)
        categoria_id = str(temporada.get("categoria_id", ""))
        categoria_nome = (
            str(temporada.get("categoria_nome", "")).strip()
            or self._nome_categoria_por_id(categoria_id)
        )
        linhas_podio = self._linhas_podio_temporada(temporada)
        entrada_jogador = self._obter_entrada_jogador_temporada(temporada)
        cor = HIST_ACCENT if destaque else self._cor_temporada_arquivo(temporada)
        cor_fundo = HIST_BG_CARD_HOVER if destaque else HIST_BG_CARD

        card = Card()
        card.setMinimumWidth(320)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {cor_fundo};
                border: 1px solid {cor if destaque else HIST_BORDER};
                border-left: 4px solid {cor};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
            QFrame:hover {{
                border-color: {cor};
            }}
        """
        )

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        btn_categoria = QToolButton()
        btn_categoria.setText(categoria_nome)
        btn_categoria.setFont(Fontes.titulo_pequeno())
        btn_categoria.setCursor(Qt.PointingHandCursor)
        btn_categoria.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn_categoria.setAutoRaise(True)
        btn_categoria.setStyleSheet(
            f"""
            QToolButton {{
                color: {HIST_ACCENT if destaque else HIST_TEXT_PRIMARY};
                border: none;
                background: transparent;
                padding: 0;
                text-align: left;
            }}
            QToolButton:hover {{
                color: {HIST_ACCENT};
            }}
        """
        )
        btn_categoria.clicked.connect(
            lambda _, ano_ref=ano, categoria_ref=categoria_id: self._abrir_detalhes_temporada(
                ano_ref,
                categoria_ref,
            )
        )
        header_layout.addWidget(btn_categoria)
        header_layout.addStretch()

        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        card.add(header_widget)

        if destaque:
            posicao_jogador = (
                self._safe_int(entrada_jogador.get("posicao"), default=999)
                if entrada_jogador
                else 999
            )
            if posicao_jogador == 1:
                selo = "🏆 TÍTULO"
            elif posicao_jogador == 2:
                selo = "🥈 VICE"
            elif posicao_jogador == 3:
                selo = "🥉 TOP 3"
            else:
                selo = f"🏁 P{posicao_jogador}" if posicao_jogador < 999 else "🏁 Temporada"

            lbl_selo = QLabel(selo)
            lbl_selo.setFont(Fontes.texto_pequeno())
            lbl_selo.setStyleSheet(
                f"color: {HIST_TEXT_PRIMARY}; border: 1px solid {HIST_ACCENT}; border-radius: {Espacos.RAIO_BADGE}px; padding: 3px 6px;"
            )
            card.add(lbl_selo)

            lbl_destaque = QLabel("⭐ Categoria que você disputou")
            lbl_destaque.setFont(Fontes.texto_pequeno())
            lbl_destaque.setStyleSheet(
                f"color: {HIST_ACCENT}; border: none; background: transparent; font-weight: bold;"
            )
            card.add(lbl_destaque)

        lbl_temporada = QLabel(f"Temporada {ano}")
        lbl_temporada.setFont(Fontes.texto_pequeno())
        lbl_temporada.setStyleSheet(
            f"color: {HIST_TEXT_MUTED}; border: none; background: transparent;"
        )
        card.add(lbl_temporada)

        lbl_podio = QLabel("\n".join(linhas_podio))
        lbl_podio.setFont(Fontes.texto_pequeno())
        lbl_podio.setStyleSheet(
            f"color: {HIST_TEXT_SECONDARY}; border: none; background: transparent;"
        )
        lbl_podio.setWordWrap(True)
        card.add(Separador())
        lbl_resultado = QLabel("🏁 Resultado Final")
        lbl_resultado.setFont(Fontes.texto_pequeno())
        lbl_resultado.setStyleSheet(
            f"color: {HIST_TEXT_PRIMARY}; border: none; background: transparent; font-weight: bold;"
        )
        card.add(lbl_resultado)
        card.add(lbl_podio)

        if destaque and entrada_jogador:
            card.add(Separador())
            lbl_stats = QLabel("📊 Suas Estatísticas")
            lbl_stats.setFont(Fontes.texto_pequeno())
            lbl_stats.setStyleSheet(
                f"color: {HIST_TEXT_PRIMARY}; border: none; background: transparent; font-weight: bold;"
            )
            card.add(lbl_stats)

            corridas = len(list(entrada_jogador.get("resultados", [])))
            vitorias = self._safe_int(entrada_jogador.get("vitorias"), default=0)
            podios = self._safe_int(entrada_jogador.get("podios"), default=0)
            pontos = self._safe_int(entrada_jogador.get("pontos"), default=0)

            stats_layout = QGridLayout()
            stats_layout.setContentsMargins(0, 0, 0, 0)
            stats_layout.setHorizontalSpacing(6)
            stats_layout.setVerticalSpacing(6)
            stats = [
                f"{corridas} Corridas",
                f"{vitorias} Vitórias",
                f"{podios} Pódios",
                f"{pontos} Pontos",
            ]
            for indice, texto_stat in enumerate(stats):
                lbl_stat = QLabel(texto_stat)
                lbl_stat.setAlignment(Qt.AlignCenter)
                lbl_stat.setFont(Fontes.texto_pequeno())
                lbl_stat.setStyleSheet(
                    f"""
                    QLabel {{
                        color: {HIST_TEXT_PRIMARY};
                        background-color: {HIST_BG_APP};
                        border: 1px solid {HIST_BORDER};
                        border-radius: {Espacos.RAIO_BADGE}px;
                        padding: 4px 6px;
                    }}
                """
                )
                stats_layout.addWidget(lbl_stat, 0, indice)

            stats_widget = QWidget()
            stats_widget.setLayout(stats_layout)
            card.add(stats_widget)

            card.add(Separador())
            lbl_grafico_titulo = QLabel("📈 Evolução na Temporada")
            lbl_grafico_titulo.setFont(Fontes.texto_pequeno())
            lbl_grafico_titulo.setStyleSheet(
                f"color: {HIST_TEXT_PRIMARY}; border: none; background: transparent; font-weight: bold;"
            )
            card.add(lbl_grafico_titulo)

            grafico_texto, insight = self._texto_grafico_temporada(temporada)
            lbl_grafico = QLabel(grafico_texto)
            lbl_grafico.setFont(QFont(Fontes.FAMILIA_MONO, 9))
            lbl_grafico.setStyleSheet(
                f"color: {HIST_TEXT_SECONDARY}; border: none; background: transparent;"
            )
            lbl_grafico.setWordWrap(True)
            card.add(lbl_grafico)

            lbl_insight = QLabel(f"\"{insight}\"")
            lbl_insight.setFont(Fontes.texto_pequeno())
            lbl_insight.setStyleSheet(
                f"color: {HIST_ACCENT}; border: none; background: transparent;"
            )
            lbl_insight.setWordWrap(True)
            card.add(lbl_insight)

            conquistas = self._conquistas_temporada_jogador(temporada)
            if conquistas:
                card.add(Separador())
                lbl_conquistas = QLabel("🎖️ Conquistas da Temporada")
                lbl_conquistas.setFont(Fontes.texto_pequeno())
                lbl_conquistas.setStyleSheet(
                    f"color: {HIST_TEXT_PRIMARY}; border: none; background: transparent; font-weight: bold;"
                )
                card.add(lbl_conquistas)

                lbl_lista_conquistas = QLabel("  |  ".join(conquistas))
                lbl_lista_conquistas.setFont(Fontes.texto_pequeno())
                lbl_lista_conquistas.setStyleSheet(
                    f"color: {HIST_TEXT_SECONDARY}; border: none; background: transparent;"
                )
                lbl_lista_conquistas.setWordWrap(True)
                card.add(lbl_lista_conquistas)

            lbl_hint = QLabel("Clique no nome da categoria para abrir a temporada completa.")
            lbl_hint.setFont(Fontes.texto_pequeno())
            lbl_hint.setStyleSheet(
                f"color: {HIST_ACCENT}; border: none; background: transparent;"
            )
            card.add(lbl_hint)

        return card

    def _atualizar_arquivo_temporadas(self):
        while self._layout_cards_arquivo.count():
            item = self._layout_cards_arquivo.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        historico_base = self._coletar_temporadas_historico()
        historico_filtrado = self._aplicar_filtros_arquivo(historico_base)

        self._atualizar_resumo_geral_arquivo(historico_base)
        self._atualizar_timeline_arquivo(historico_base)
        self._atualizar_comparativo_arquivo(historico_base)
        if hasattr(self, "_atualizar_sala_trofeus"):
            self._atualizar_sala_trofeus()
        self._atualizar_header_historia()

        if not historico_filtrado:
            lbl_vazio = QLabel("Nenhuma temporada anterior encontrada.")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            lbl_vazio.setFont(Fontes.texto_normal())
            lbl_vazio.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
            self._layout_cards_arquivo.addWidget(lbl_vazio)
            self._layout_cards_arquivo.addStretch()
            return

        temporadas_por_ano: dict[int, list[dict[str, Any]]] = {}
        for temporada in historico_filtrado:
            ano = self._safe_int(temporada.get("ano"), default=0)
            temporadas_por_ano.setdefault(ano, []).append(temporada)

        if self._arquivo_ordem_filtro == "Mais Antigo":
            anos_ordenados = sorted(temporadas_por_ano.keys())
        else:
            anos_ordenados = sorted(temporadas_por_ano.keys(), reverse=True)

        for indice_ano, ano in enumerate(anos_ordenados):
            texto_ano = f"Ano {ano}" if ano > 0 else "Ano não informado"
            expandido = self._arquivo_anos_expandidos.get(ano, indice_ano == 0)

            btn_ano = QToolButton()
            btn_ano.setCheckable(True)
            btn_ano.setChecked(expandido)
            btn_ano.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn_ano.setAutoRaise(True)
            btn_ano.setCursor(Qt.PointingHandCursor)
            btn_ano.setFont(Fontes.titulo_medio())
            btn_ano.setStyleSheet(
                f"""
                QToolButton {{
                    color: {HIST_ACCENT};
                    border: 1px solid {HIST_BORDER};
                    background: {HIST_BG_SURFACE};
                    border-radius: {Espacos.RAIO_BADGE}px;
                    padding: 6px 10px;
                    text-align: left;
                }}
                QToolButton:hover {{
                    color: {HIST_ACCENT_HOVER};
                    border-color: {HIST_ACCENT};
                }}
            """
            )

            temporadas_ano_ordenadas = sorted(
                temporadas_por_ano[ano],
                key=lambda item: (
                    self._ordem_categoria(item.get("categoria_id", "")),
                    self._nome_categoria_por_id(item.get("categoria_id", "")).casefold(),
                ),
            )

            resumo_ano = self._resumo_ano_jogador(temporadas_ano_ordenadas)

            grupo_ano = QWidget()
            layout_grupo_ano = QVBoxLayout(grupo_ano)
            layout_grupo_ano.setContentsMargins(12, 4, 0, 8)
            layout_grupo_ano.setSpacing(8)

            temporada_destaque = next(
                (
                    temporada
                    for temporada in temporadas_ano_ordenadas
                    if self._jogador_participou_temporada(temporada)
                ),
                None,
            )
            temporadas_restantes = [
                temporada
                for temporada in temporadas_ano_ordenadas
                if temporada is not temporada_destaque
            ]

            if temporada_destaque is not None:
                linha_destaque = QWidget()
                layout_linha_destaque = QHBoxLayout(linha_destaque)
                layout_linha_destaque.setContentsMargins(0, 0, 0, 0)
                layout_linha_destaque.setSpacing(8)
                layout_linha_destaque.addStretch()
                layout_linha_destaque.addWidget(
                    self._criar_card_arquivo_temporada(temporada_destaque, destaque=True),
                    1,
                )
                layout_linha_destaque.addStretch()
                layout_grupo_ano.addWidget(linha_destaque)

            for indice in range(0, len(temporadas_restantes), 2):
                linha_widget = QWidget()
                layout_linha = QHBoxLayout(linha_widget)
                layout_linha.setContentsMargins(0, 0, 0, 0)
                layout_linha.setSpacing(8)

                card_esquerda = self._criar_card_arquivo_temporada(
                    temporadas_restantes[indice]
                )
                layout_linha.addWidget(card_esquerda, 1)

                if indice + 1 < len(temporadas_restantes):
                    card_direita = self._criar_card_arquivo_temporada(
                        temporadas_restantes[indice + 1]
                    )
                    layout_linha.addWidget(card_direita, 1)
                else:
                    espaco_vazio = QWidget()
                    espaco_vazio.setStyleSheet("background: transparent; border: none;")
                    layout_linha.addWidget(espaco_vazio, 1)

                layout_grupo_ano.addWidget(linha_widget)

            grupo_ano.setVisible(expandido)
            seta = "▼" if expandido else "▶"
            btn_ano.setText(f"{seta} {texto_ano}")
            btn_ano.toggled.connect(
                lambda checked, ano_ref=ano, botao_ref=btn_ano, grupo_ref=grupo_ano, texto_ref=texto_ano: self._alternar_secao_ano(
                    ano_ref,
                    checked,
                    botao_ref,
                    grupo_ref,
                    texto_ref,
                )
            )

            header_ano = QWidget()
            layout_header_ano = QVBoxLayout(header_ano)
            layout_header_ano.setContentsMargins(0, 0, 0, 0)
            layout_header_ano.setSpacing(3)
            layout_header_ano.addWidget(btn_ano)

            lbl_resumo_ano = QLabel(resumo_ano)
            lbl_resumo_ano.setFont(Fontes.texto_pequeno())
            lbl_resumo_ano.setStyleSheet(
                f"color: {HIST_TEXT_SECONDARY}; border: none; background: transparent;"
            )
            lbl_resumo_ano.setWordWrap(True)
            layout_header_ano.addWidget(lbl_resumo_ano)

            self._layout_cards_arquivo.addWidget(header_ano)
            self._layout_cards_arquivo.addWidget(grupo_ano)

            if indice_ano < len(anos_ordenados) - 1:
                self._layout_cards_arquivo.addWidget(Separador())

        self._layout_cards_arquivo.addStretch()

    def _alternar_secao_ano(
        self,
        ano: int,
        expandido: bool,
        botao: QToolButton,
        grupo: QWidget,
        texto_ano: str,
    ):
        self._arquivo_anos_expandidos[ano] = expandido
        grupo.setVisible(expandido)
        seta = "▼" if expandido else "▶"
        botao.setText(f"{seta} {texto_ano}")

    def _abrir_detalhes_temporada(self, ano: int, categoria_id: str):
        self._mostrar_aba_historia(0)
        self.combo_ano.setCurrentText(str(ano))

        categoria_nome = self._nome_categoria_por_id(categoria_id)
        if categoria_nome:
            self.combo_categoria.setCurrentText(categoria_nome)

        self._atualizar_tabela_temporadas()

    def _build_tab_trofeus(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        titulo = QLabel("🏆 SALA DE TROFÉUS")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {HIST_ACCENT};")
        layout.addWidget(titulo)

        layout.addWidget(Separador())

        self.scroll_trofeus = QScrollArea()
        self.scroll_trofeus.setWidgetResizable(True)
        self.scroll_trofeus.setStyleSheet(self._estilo_scroll_historia())

        self._content_trofeus = QWidget()
        self._layout_trofeus = QVBoxLayout(self._content_trofeus)
        self._layout_trofeus.setContentsMargins(12, 12, 12, 12)
        self._layout_trofeus.setSpacing(10)
        self.scroll_trofeus.setWidget(self._content_trofeus)

        layout.addWidget(self.scroll_trofeus)

        self._atualizar_sala_trofeus()

        return widget

    def _atualizar_sala_trofeus(self):
        if not hasattr(self, "_layout_trofeus"):
            return

        while self._layout_trofeus.count():
            item = self._layout_trofeus.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        temporadas = self._coletar_temporadas_historico()
        temporadas_jogador: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for temporada in temporadas:
            entrada = self._obter_entrada_jogador_temporada(temporada)
            if entrada:
                temporadas_jogador.append((temporada, entrada))

        milestones_hist = obter_historico_milestones(self.banco)
        jogador_atual = self._obter_jogador_atual() or {}

        if milestones_hist:
            card_milestones = CardTitulo("MARCOS DE CARREIRA")
            ordenados = sorted(
                milestones_hist,
                key=lambda item: (
                    self._safe_int(item.get("temporada"), default=0),
                    self._safe_int(item.get("rodada"), default=0),
                ),
            )
            for item in ordenados:
                if not isinstance(item, dict):
                    continue
                icone = str(item.get("icone", "🏆") or "🏆")
                titulo = str(item.get("titulo", "Marco") or "Marco")
                temporada_txt = self._safe_int(item.get("temporada"), default=0)
                rodada_txt = self._safe_int(item.get("rodada"), default=0)
                detalhe = f"Temporada {temporada_txt}" if temporada_txt > 0 else "Temporada -"
                if rodada_txt > 0:
                    detalhe = f"{detalhe} | Rodada {rodada_txt}"

                lbl = QLabel(f"{icone}  {titulo}  —  {detalhe}")
                lbl.setFont(Fontes.texto_normal())
                lbl.setStyleSheet(f"color: {HIST_TEXT_SECONDARY}; border: none;")
                lbl.setWordWrap(True)
                card_milestones.add(lbl)

            proximo = obter_proximo_milestone(jogador_atual) if isinstance(jogador_atual, dict) else None
            if isinstance(proximo, dict):
                atual = self._safe_int(proximo.get("atual"), default=0)
                alvo = self._safe_int(proximo.get("alvo"), default=1)
                icone = str(proximo.get("icone", "🏁") or "🏁")
                titulo = str(proximo.get("titulo", "Proximo marco") or "Proximo marco")
                lbl_proximo = QLabel(f"Proximo marco: {icone} {titulo} (atual: {atual}/{alvo})")
                lbl_proximo.setFont(Fontes.texto_normal())
                lbl_proximo.setStyleSheet(f"color: {HIST_ACCENT}; border: none; font-weight: 700;")
                lbl_proximo.setWordWrap(True)
                card_milestones.add(Separador())
                card_milestones.add(lbl_proximo)

            self._layout_trofeus.addWidget(card_milestones)

        if not temporadas_jogador and not milestones_hist:
            vazio = QLabel("Nenhum troféu registrado ainda para o jogador.")
            vazio.setAlignment(Qt.AlignCenter)
            vazio.setFont(Fontes.texto_normal())
            vazio.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
            self._layout_trofeus.addWidget(vazio)
            self._layout_trofeus.addStretch()
            return

        temporadas_jogador.sort(
            key=lambda item: (
                -self._safe_int(item[0].get("ano"), default=0),
                self._ordem_categoria(item[0].get("categoria_id", "")),
            )
        )

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setVerticalSpacing(10)

        total_ouro = 0
        total_prata = 0
        total_bronze = 0

        colunas = 3
        for indice, (temporada, entrada) in enumerate(temporadas_jogador):
            posicao = self._safe_int(entrada.get("posicao"), default=999)
            categoria_id = str(temporada.get("categoria_id", ""))
            categoria_nome = (
                str(temporada.get("categoria_nome", "")).strip()
                or self._nome_categoria_por_id(categoria_id)
            )
            ano = self._safe_int(temporada.get("ano"), default=0)

            if posicao == 1:
                emoji = "🏆"
                cor = Cores.OURO
                total_ouro += 1
            elif posicao == 2:
                emoji = "🥈"
                cor = Cores.PRATA
                total_prata += 1
            elif posicao == 3:
                emoji = "🥉"
                cor = Cores.BRONZE
                total_bronze += 1
            else:
                emoji = "🏁"
                cor = HIST_ACCENT

            card = Card()
            card.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {HIST_BG_CARD};
                    border: 1px solid {cor};
                    border-left: 3px solid {cor};
                    border-radius: {Espacos.RAIO_CARD}px;
                }}
            """
            )

            lbl_emoji = QLabel(emoji)
            lbl_emoji.setAlignment(Qt.AlignCenter)
            lbl_emoji.setFont(Fontes.numero_medio())
            lbl_emoji.setStyleSheet(f"color: {cor}; border: none; background: transparent;")
            card.add(lbl_emoji)

            btn_nome = QToolButton()
            btn_nome.setText(f"{categoria_nome} {ano}")
            btn_nome.setCursor(Qt.PointingHandCursor)
            btn_nome.setAutoRaise(True)
            btn_nome.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn_nome.setFont(Fontes.texto_pequeno())
            btn_nome.setStyleSheet(
                f"""
                QToolButton {{
                    color: {HIST_TEXT_PRIMARY};
                    border: none;
                    background: transparent;
                }}
                QToolButton:hover {{
                    color: {HIST_ACCENT};
                }}
            """
            )
            btn_nome.clicked.connect(
                lambda _, ano_ref=ano, categoria_ref=categoria_id: self._abrir_detalhes_temporada(
                    ano_ref,
                    categoria_ref,
                )
            )
            card.add(btn_nome)

            row = indice // colunas
            col = indice % colunas
            grid_layout.addWidget(card, row, col)

        self._layout_trofeus.addWidget(grid_widget)

        lbl_total = QLabel(
            f"Total: {total_ouro} 🏆  |  {total_prata} 🥈  |  {total_bronze} 🥉"
        )
        lbl_total.setFont(Fontes.titulo_pequeno())
        lbl_total.setStyleSheet(f"color: {HIST_TEXT_PRIMARY}; border: none;")
        self._layout_trofeus.addWidget(lbl_total)
        self._layout_trofeus.addStretch()

    def _build_tab_rivalidades_ia(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        titulo = QLabel("🔥 RIVAIS")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {HIST_ACCENT};")
        layout.addWidget(titulo)

        layout.addWidget(Separador())

        filtros_widget = QWidget()
        filtros_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filtros_layout = QHBoxLayout(filtros_widget)
        filtros_layout.setContentsMargins(0, 0, 0, 0)
        filtros_layout.setSpacing(6)

        estilo_seta = f"""
            QToolButton {{
                background-color: {HIST_BG_SURFACE_ALT};
                color: {HIST_TEXT_SECONDARY};
                border: 1px solid {HIST_BORDER};
                border-radius: 4px;
                font-weight: 700;
            }}
            QToolButton:hover {{
                background-color: {HIST_BG_CARD_HOVER};
                color: {HIST_TEXT_PRIMARY};
                border-color: {HIST_BORDER_HOVER};
            }}
            QToolButton:pressed {{
                background-color: {HIST_BG_SURFACE};
            }}
        """

        anos_disponiveis = self._obter_anos_rivalidade()
        self._anos_rivalidades_disponiveis = [str(ano) for ano in anos_disponiveis]
        self.combo_ano_rival = CampoCombo("Ano", [str(ano) for ano in anos_disponiveis])
        self.combo_ano_rival.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        if anos_disponiveis:
            self.combo_ano_rival.setCurrentIndex(0)
        self.combo_ano_rival.currentTextChanged.connect(self._atualizar_rivalidades_ia)

        ano_controles = QWidget()
        ano_controles.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        ano_controles_layout = QHBoxLayout(ano_controles)
        ano_controles_layout.setContentsMargins(0, 0, 0, 0)
        ano_controles_layout.setSpacing(4)
        ano_controles_layout.addWidget(self.combo_ano_rival)

        setas_ano_layout = QVBoxLayout()
        setas_ano_layout.setContentsMargins(0, 20, 0, 0)
        setas_ano_layout.setSpacing(2)

        btn_ano_cima = QToolButton()
        btn_ano_cima.setText("▲")
        btn_ano_cima.setCursor(Qt.PointingHandCursor)
        btn_ano_cima.setToolTip("Ano anterior")
        btn_ano_cima.setFixedSize(22, 16)
        btn_ano_cima.setStyleSheet(estilo_seta)
        btn_ano_cima.clicked.connect(lambda: self._alternar_ano_rivalidades(-1))
        setas_ano_layout.addWidget(btn_ano_cima)

        btn_ano_baixo = QToolButton()
        btn_ano_baixo.setText("▼")
        btn_ano_baixo.setCursor(Qt.PointingHandCursor)
        btn_ano_baixo.setToolTip("Proximo ano")
        btn_ano_baixo.setFixedSize(22, 16)
        btn_ano_baixo.setStyleSheet(estilo_seta)
        btn_ano_baixo.clicked.connect(lambda: self._alternar_ano_rivalidades(1))
        setas_ano_layout.addWidget(btn_ano_baixo)

        ano_controles_layout.addLayout(setas_ano_layout)
        filtros_layout.addWidget(ano_controles)

        categorias_nomes = [categoria["nome"] for categoria in CATEGORIAS]
        self._categorias_rivalidades_nomes = list(categorias_nomes)
        self.combo_categoria_rival = CampoCombo("Categoria", categorias_nomes)
        self.combo_categoria_rival.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        jogador = self._obter_jogador_atual()
        if jogador:
            categoria_jogador = next(
                (
                    categoria["nome"]
                    for categoria in CATEGORIAS
                    if categoria.get("id") == jogador.get("categoria_atual")
                ),
                None,
            )
            if categoria_jogador:
                self.combo_categoria_rival.setCurrentText(categoria_jogador)
        self.combo_categoria_rival.currentTextChanged.connect(self._atualizar_rivalidades_ia)

        categoria_controles = QWidget()
        categoria_controles.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        categoria_controles_layout = QHBoxLayout(categoria_controles)
        categoria_controles_layout.setContentsMargins(0, 0, 0, 0)
        categoria_controles_layout.setSpacing(4)
        categoria_controles_layout.addWidget(self.combo_categoria_rival)

        setas_categoria_layout = QVBoxLayout()
        setas_categoria_layout.setContentsMargins(0, 20, 0, 0)
        setas_categoria_layout.setSpacing(2)

        btn_categoria_cima = QToolButton()
        btn_categoria_cima.setText("▲")
        btn_categoria_cima.setCursor(Qt.PointingHandCursor)
        btn_categoria_cima.setToolTip("Categoria anterior")
        btn_categoria_cima.setFixedSize(22, 16)
        btn_categoria_cima.setStyleSheet(estilo_seta)
        btn_categoria_cima.clicked.connect(
            lambda: self._alternar_categoria_rivalidades(-1)
        )
        setas_categoria_layout.addWidget(btn_categoria_cima)

        btn_categoria_baixo = QToolButton()
        btn_categoria_baixo.setText("▼")
        btn_categoria_baixo.setCursor(Qt.PointingHandCursor)
        btn_categoria_baixo.setToolTip("Proxima categoria")
        btn_categoria_baixo.setFixedSize(22, 16)
        btn_categoria_baixo.setStyleSheet(estilo_seta)
        btn_categoria_baixo.clicked.connect(
            lambda: self._alternar_categoria_rivalidades(1)
        )
        setas_categoria_layout.addWidget(btn_categoria_baixo)

        categoria_controles_layout.addLayout(setas_categoria_layout)
        filtros_layout.addWidget(categoria_controles)

        filtros_layout.addStretch()
        layout.addWidget(filtros_widget, 0)

        self.lbl_rivais_vazio = QLabel("")
        self.lbl_rivais_vazio.setFont(Fontes.texto_normal())
        self.lbl_rivais_vazio.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
        self.lbl_rivais_vazio.setAlignment(Qt.AlignCenter)
        self.lbl_rivais_vazio.setVisible(False)
        layout.addWidget(self.lbl_rivais_vazio)

        self.card_rival_principal = Card()
        self.card_rival_principal.setStyleSheet(
            f"""
            QFrame {{
                background-color: {HIST_BG_CARD};
                border: 1px solid {HIST_BORDER};
                border-left: 4px solid {HIST_ACCENT};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
        """
        )

        lbl_rival_principal = QLabel("RIVAL PRINCIPAL")
        lbl_rival_principal.setFont(Fontes.titulo_pequeno())
        lbl_rival_principal.setStyleSheet(f"color: {HIST_TEXT_PRIMARY};")
        self.card_rival_principal.add(lbl_rival_principal)
        self.card_rival_principal.add(Separador())

        linha_info = QWidget()
        linha_info_layout = QHBoxLayout(linha_info)
        linha_info_layout.setContentsMargins(0, 0, 0, 0)
        linha_info_layout.setSpacing(12)

        foto = QFrame()
        foto.setFixedSize(68, 68)
        foto.setStyleSheet(
            f"""
            QFrame {{
                background-color: {HIST_BG_APP};
                border: 1px dashed {HIST_BORDER_HOVER};
                border-radius: 8px;
            }}
        """
        )
        foto_layout = QVBoxLayout(foto)
        foto_layout.setContentsMargins(0, 0, 0, 0)
        lbl_foto = QLabel("FOTO\nIA")
        lbl_foto.setAlignment(Qt.AlignCenter)
        lbl_foto.setFont(Fontes.texto_pequeno())
        lbl_foto.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
        foto_layout.addWidget(lbl_foto)
        linha_info_layout.addWidget(foto)

        coluna_info = QWidget()
        coluna_info_layout = QVBoxLayout(coluna_info)
        coluna_info_layout.setContentsMargins(0, 0, 0, 0)
        coluna_info_layout.setSpacing(2)

        self.lbl_nome_rival_principal = QLabel("-")
        self.lbl_nome_rival_principal.setFont(Fontes.titulo_medio())
        self.lbl_nome_rival_principal.setStyleSheet(f"color: {HIST_ACCENT};")
        coluna_info_layout.addWidget(self.lbl_nome_rival_principal)

        self.lbl_desde_rival_principal = QLabel("-")
        self.lbl_desde_rival_principal.setFont(Fontes.texto_pequeno())
        self.lbl_desde_rival_principal.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        coluna_info_layout.addWidget(self.lbl_desde_rival_principal)

        self.lbl_frase_rival_principal = QLabel("-")
        self.lbl_frase_rival_principal.setFont(Fontes.texto_pequeno())
        self.lbl_frase_rival_principal.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
        coluna_info_layout.addWidget(self.lbl_frase_rival_principal)

        linha_info_layout.addWidget(coluna_info, 1)
        self.card_rival_principal.add(linha_info)

        self.lbl_barra_voce = QLabel("-")
        self.lbl_barra_voce.setFont(QFont(Fontes.FAMILIA_MONO, 10))
        self.lbl_barra_voce.setStyleSheet(f"color: {Cores.VERDE};")
        self.card_rival_principal.add(self.lbl_barra_voce)

        self.lbl_barra_ele = QLabel("-")
        self.lbl_barra_ele.setFont(QFont(Fontes.FAMILIA_MONO, 10))
        self.lbl_barra_ele.setStyleSheet(f"color: {Cores.AMARELO};")
        self.card_rival_principal.add(self.lbl_barra_ele)

        self.btn_ver_perfil_rival = BotaoSecondary("Ver Perfil Completo")
        self.btn_ver_perfil_rival.clicked.connect(self._abrir_perfil_rival_principal)
        self.card_rival_principal.add(self.btn_ver_perfil_rival)
        layout.addWidget(self.card_rival_principal)

        self.card_intensidade = CardTitulo("NÍVEL DA RIVALIDADE")
        self.lbl_intensidade_rival = QLabel("-")
        self.lbl_intensidade_rival.setFont(Fontes.titulo_pequeno())
        self.lbl_intensidade_rival.setStyleSheet(f"color: {HIST_TEXT_PRIMARY};")
        self.card_intensidade.add(self.lbl_intensidade_rival)

        self.lbl_intensidade_barra = QLabel("-")
        self.lbl_intensidade_barra.setFont(QFont(Fontes.FAMILIA_MONO, 10))
        self.lbl_intensidade_barra.setStyleSheet(f"color: {Cores.VERMELHO};")
        self.card_intensidade.add(self.lbl_intensidade_barra)

        self.lbl_intensidade_fatores = QLabel("-")
        self.lbl_intensidade_fatores.setWordWrap(True)
        self.lbl_intensidade_fatores.setFont(Fontes.texto_pequeno())
        self.lbl_intensidade_fatores.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        self.card_intensidade.add(self.lbl_intensidade_fatores)
        layout.addWidget(self.card_intensidade)

        lbl_outros = QLabel("OUTROS RIVAIS")
        lbl_outros.setFont(Fontes.titulo_pequeno())
        lbl_outros.setStyleSheet(f"color: {HIST_TEXT_PRIMARY};")
        layout.addWidget(lbl_outros)

        self.layout_outros_rivais = QHBoxLayout()
        self.layout_outros_rivais.setContentsMargins(0, 0, 0, 0)
        self.layout_outros_rivais.setSpacing(10)
        self._cards_outros_rivais: list[dict[str, Any]] = []
        for indice in range(3):
            refs = self._criar_card_outro_rival(indice)
            self._cards_outros_rivais.append(refs)
            self.layout_outros_rivais.addWidget(refs["widget"], 1)
        layout.addLayout(self.layout_outros_rivais)

        layout.addStretch()
        self._rival_principal_data = None
        self._outros_rivais_dados: list[dict[str, Any]] = []
        self._atualizar_rivalidades_ia()

        return widget

    def _criar_card_outro_rival(self, indice: int) -> dict[str, Any]:
        card = Card(clickable=True)
        card.setVisible(False)
        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {HIST_BG_CARD};
                border: 1px solid {HIST_BORDER};
                border-radius: {Espacos.RAIO_CARD}px;
            }}
            QFrame:hover {{
                border-color: {HIST_ACCENT};
            }}
        """
        )

        lbl_nome = QLabel("-")
        lbl_nome.setFont(Fontes.titulo_pequeno())
        lbl_nome.setStyleSheet(f"color: {HIST_TEXT_PRIMARY};")
        card.add(lbl_nome)

        lbl_confrontos = QLabel("-")
        lbl_confrontos.setFont(Fontes.texto_pequeno())
        lbl_confrontos.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        card.add(lbl_confrontos)

        lbl_placar = QLabel("-")
        lbl_placar.setFont(Fontes.texto_pequeno())
        lbl_placar.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
        card.add(lbl_placar)

        lbl_barra = QLabel("-")
        lbl_barra.setFont(QFont(Fontes.FAMILIA_MONO, 9))
        lbl_barra.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
        card.add(lbl_barra)

        card.clicked.connect(lambda idx=indice: self._abrir_perfil_outro_rival(idx))

        return {
            "widget": card,
            "nome": lbl_nome,
            "confrontos": lbl_confrontos,
            "placar": lbl_placar,
            "barra": lbl_barra,
        }

    def _abrir_perfil_rival_principal(self):
        if self._rival_principal_data:
            self._abrir_perfil_rival(self._rival_principal_data)

    def _abrir_perfil_outro_rival(self, indice: int):
        if 0 <= indice < len(self._outros_rivais_dados):
            self._abrir_perfil_rival(self._outros_rivais_dados[indice])

    def _barra_vitorias_texto(self, vitorias: int, total: int) -> str:
        if total <= 0:
            return "-" * 20
        preenchido = int(round((vitorias / total) * 20))
        preenchido = max(0, min(preenchido, 20))
        return f"{'#' * preenchido}{'-' * (20 - preenchido)}"

    def _calcular_intensidade_curta(self, total_duelos: int, duelos_acirrados: int) -> tuple[str, int]:
        score = min(100, total_duelos * 12 + duelos_acirrados * 8)
        if score >= 80:
            nivel = "ALTA"
        elif score >= 50:
            nivel = "MÉDIA"
        else:
            nivel = "BAIXA"
        return nivel, score

    def _atualizar_card_rival_principal(self, rival_data: dict[str, Any]):
        rival = rival_data["rival"]
        analise = rival_data["analise"]
        nome_rival = str(rival.get("piloto", "Rival IA"))
        total = len(analise["duelos"])
        vj = int(analise["vitorias_jogador"])
        vr = int(analise["vitorias_rival"])

        self.lbl_nome_rival_principal.setText(f"{nome_rival} 🔥")
        self.lbl_desde_rival_principal.setText(
            f"Rival desde: {self.combo_categoria_rival.currentText()} {self.combo_ano_rival.currentText()}"
        )
        self.lbl_frase_rival_principal.setText(f"\"Vocês já se enfrentaram {total} vezes\"")

        self.lbl_barra_voce.setText(
            f"VOCÊ  {self._barra_vitorias_texto(vj, max(total, 1))}  {vj} vitórias"
        )
        self.lbl_barra_ele.setText(
            f"ELE   {self._barra_vitorias_texto(vr, max(total, 1))}  {vr} vitórias"
        )

        duelos_acirrados = sum(
            1 for _, pj, pr in analise["duelos"] if abs(pj - pr) <= 2
        )
        nivel, score = self._calcular_intensidade_curta(total, duelos_acirrados)
        self.lbl_intensidade_rival.setText(f"🔥 Intensidade: {nivel} ({score}%)")
        self.lbl_intensidade_barra.setText(self._barra_vitorias_texto(score, 100))

        fatores = []
        if total >= 3:
            fatores.append("✓ Muitos confrontos diretos")
        if duelos_acirrados >= 2:
            fatores.append("✓ Disputas acirradas")
        if abs(int(rival_data["diff_pontos"])) <= 15:
            fatores.append("✓ Disputa de campeonato")
        if not fatores:
            fatores.append("✓ Rivalidade em construção")
        self.lbl_intensidade_fatores.setText("\n".join(fatores))

    def _atualizar_cards_outros_rivais(self, ranking: list[dict[str, Any]]):
        self._outros_rivais_dados = ranking
        for indice, refs in enumerate(self._cards_outros_rivais):
            card = refs["widget"]
            if indice >= len(ranking):
                card.setVisible(False)
                continue

            dados = ranking[indice]
            analise = dados["analise"]
            total = len(analise["duelos"])
            vj = int(analise["vitorias_jogador"])
            vr = int(analise["vitorias_rival"])
            nome_rival = str(dados["rival"].get("piloto", "Rival IA"))

            refs["nome"].setText(f"{nome_rival} 🔥")
            refs["confrontos"].setText(f"{total} confrontos")
            refs["placar"].setText(f"Você: {vj} | Ele: {vr}")
            refs["barra"].setText(
                f"{self._barra_vitorias_texto(vj, max(total, 1))} vs {self._barra_vitorias_texto(vr, max(total, 1))}"
            )
            card.setVisible(True)

    def _abrir_perfil_rival(self, rival_data: dict[str, Any]):
        rival = rival_data["rival"]
        analise = rival_data["analise"]
        nome_rival = str(rival.get("piloto", "Rival IA"))
        duelos = analise["duelos"]

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Perfil do Rival - {nome_rival}")
        dialog.setMinimumSize(850, 650)
        dialog.resize(920, 720)
        dialog.setStyleSheet(f"background-color: {HIST_BG_APP};")

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        topo = QHBoxLayout()
        btn_voltar = BotaoSecondary("← Voltar")
        btn_voltar.clicked.connect(dialog.close)
        topo.addWidget(btn_voltar)
        topo.addStretch()
        lbl_titulo = QLabel("PERFIL DO RIVAL")
        lbl_titulo.setFont(Fontes.titulo_medio())
        lbl_titulo.setStyleSheet(f"color: {HIST_ACCENT};")
        topo.addWidget(lbl_titulo)
        layout.addLayout(topo)
        layout.addWidget(Separador())

        card_info = CardTitulo(f"{nome_rival} 🔥")
        card_info.add(
            LinhaInfo(
                "🏁 Rival desde",
                f"{self.combo_categoria_rival.currentText()} {self.combo_ano_rival.currentText()}",
            )
        )
        card_info.add(LinhaInfo("📊 Confrontos totais", str(len(duelos))))
        card_info.add(
            LinhaInfo(
                "🏆 Você lidera",
                f"{analise['vitorias_jogador']} x {analise['vitorias_rival']}",
                HIST_ACCENT,
            )
        )
        layout.addWidget(card_info)

        card_hist = CardTitulo("HISTÓRICO DE CONFRONTOS")
        if duelos:
            tabela = QTableWidget()
            tabela.setColumnCount(3)
            tabela.setRowCount(len(duelos))
            tabela.setHorizontalHeaderLabels(["VOCÊ", "ELE", "ETAPA"])
            tabela.setStyleSheet(self._estilo_tabela_historia())
            tabela.setSelectionMode(QAbstractItemView.NoSelection)
            tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
            tabela.verticalHeader().setVisible(False)
            tabela.setShowGrid(False)

            header = tabela.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.Stretch)

            for row, (rodada, pj, pr) in enumerate(reversed(duelos)):
                tabela.setRowHeight(row, 30)
                item_j = QTableWidgetItem(f"P{pj}")
                item_r = QTableWidgetItem(f"P{pr}")
                item_e = QTableWidgetItem(f"R{rodada}")
                item_j.setTextAlignment(Qt.AlignCenter)
                item_r.setTextAlignment(Qt.AlignCenter)

                if pj < pr:
                    item_j.setForeground(QBrush(QColor(Cores.VERDE)))
                    item_r.setForeground(QBrush(QColor(Cores.VERMELHO)))
                elif pr < pj:
                    item_j.setForeground(QBrush(QColor(Cores.VERMELHO)))
                    item_r.setForeground(QBrush(QColor(Cores.VERDE)))

                tabela.setItem(row, 0, item_j)
                tabela.setItem(row, 1, item_r)
                tabela.setItem(row, 2, item_e)
            card_hist.add(tabela)
        else:
            lbl_sem = QLabel("Sem histórico de confrontos diretos neste contexto.")
            lbl_sem.setFont(Fontes.texto_pequeno())
            lbl_sem.setStyleSheet(f"color: {HIST_TEXT_MUTED};")
            card_hist.add(lbl_sem)
        layout.addWidget(card_hist)

        card_stats = CardTitulo("ESTATÍSTICAS DO CONFRONTO")
        total = len(duelos)
        vj = int(analise["vitorias_jogador"])
        vr = int(analise["vitorias_rival"])
        media_j = (sum(pj for _, pj, _ in duelos) / total) if total else None
        media_r = (sum(pr for _, _, pr in duelos) / total) if total else None
        card_stats.add(LinhaInfo("Vitórias", f"{vj} x {vr}"))
        card_stats.add(
            LinhaInfo(
                "Posição média",
                f"{media_j:.2f} x {media_r:.2f}" if media_j is not None and media_r is not None else "-",
            )
        )
        if media_j is not None and media_r is not None:
            diff = media_r - media_j
            texto_diff = f"+{diff:.2f} a seu favor" if diff >= 0 else f"{diff:.2f} contra você"
        else:
            texto_diff = "-"
        card_stats.add(LinhaInfo("Diferença", texto_diff, HIST_ACCENT))
        layout.addWidget(card_stats)

        card_badges = CardTitulo("🎖️ BADGES")
        badges = []
        if total >= 10:
            badges.append("⚔️ Guerreiro — 10+ confrontos")
        if total >= 5 and vj >= vr + 2:
            badges.append("🏆 Dominante — vantagem consistente")
        if total >= 4 and (vj / max(total, 1)) >= 0.75:
            badges.append("👑 Rei dos Duelos — 75%+ de vitórias")
        if not badges:
            badges.append("🎯 Caçador — rivalidade em progresso")
        for badge in badges:
            lbl_badge = QLabel(badge)
            lbl_badge.setFont(Fontes.texto_pequeno())
            lbl_badge.setStyleSheet(f"color: {HIST_TEXT_SECONDARY};")
            card_badges.add(lbl_badge)
        layout.addWidget(card_badges)

        dialog.exec()

    def _obter_jogador_atual(self) -> dict[str, Any] | None:
        return next(
            (
                piloto
                for piloto in self.banco.get("pilotos", [])
                if piloto.get("is_jogador", False)
            ),
            None,
        )

    def _obter_anos_rivalidade(self) -> list[int]:
        anos = {
            int(item.get("ano"))
            for item in self.banco.get("historico_temporadas_completas", [])
            if isinstance(item, dict) and isinstance(item.get("ano"), int)
        }
        anos.add(int(self.banco.get("ano_atual", 2024)))
        return sorted(anos, reverse=True)

    def _normalizar_nome(self, nome: Any) -> str:
        texto = " ".join(str(nome or "").strip().casefold().split())
        if not texto:
            return ""
        decomposicao = unicodedata.normalize("NFD", texto)
        return "".join(
            caractere
            for caractere in decomposicao
            if unicodedata.category(caractere) != "Mn"
        )

    def _resultado_para_posicao(self, resultado: Any) -> int | str | None:
        if isinstance(resultado, bool):
            return None

        if isinstance(resultado, int):
            return resultado if resultado > 0 else None

        texto = str(resultado or "").strip()
        if not texto:
            return None

        if texto.upper() == "DNF":
            return "DNF"

        # Aceita formatos como "P1", "1º", "P2 (+18)".
        texto_norm = (
            texto.upper()
            .replace("º", "")
            .replace("°", "")
            .replace("ª", "")
            .strip()
        )
        if texto_norm.startswith("P"):
            texto_norm = texto_norm[1:].strip()

        try:
            posicao = int(texto_norm)
        except (TypeError, ValueError):
            match = re.search(r"\d+", texto_norm)
            if not match:
                return None
            posicao = int(match.group(0))

        return posicao if posicao > 0 else None

    def _chave_desempate_resultados_temporada(
        self,
        resultados: list[Any],
        limite_rodadas: int | None = None,
        tamanho_chave: int = 0,
    ) -> tuple[int, ...]:
        if not isinstance(resultados, list):
            resultados = []

        if limite_rodadas is None:
            amostra = resultados
        else:
            amostra = resultados[: max(0, limite_rodadas)]

        posicoes: list[int] = []
        for resultado in amostra:
            posicao = self._resultado_para_posicao(resultado)
            if isinstance(posicao, int) and posicao > 0:
                posicoes.append(posicao)
            elif posicao == "DNF":
                posicoes.append(998)
            else:
                posicoes.append(999)

        posicoes.sort()
        if tamanho_chave > 0 and len(posicoes) < tamanho_chave:
            posicoes.extend([999] * (tamanho_chave - len(posicoes)))
        return tuple(posicoes)

    def _ordenar_classificacao_por_desempenho_temporada(
        self,
        classificacao: list[dict[str, Any]],
        limite_rodadas: int | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(classificacao, list):
            return []

        tamanho_chave = 0
        for entrada in classificacao:
            resultados = entrada.get("resultados", [])
            if not isinstance(resultados, list):
                resultados = []
            tamanho = len(resultados if limite_rodadas is None else resultados[: max(0, limite_rodadas)])
            if tamanho > tamanho_chave:
                tamanho_chave = tamanho

        return sorted(
            classificacao,
            key=lambda e: (
                -self._safe_int(e.get("pontos"), default=0),
                self._chave_desempate_resultados_temporada(
                    e.get("resultados", []),
                    limite_rodadas=limite_rodadas,
                    tamanho_chave=tamanho_chave,
                ),
                self._normalizar_nome(e.get("piloto", "")),
            ),
        )

    def _calcular_pontos_ate_rodada_temporada(
        self,
        resultados: list[Any],
        limite_rodadas: int,
    ) -> int:
        if not isinstance(resultados, list):
            return 0

        pontos = 0
        for resultado in resultados[: max(0, limite_rodadas)]:
            posicao = self._resultado_para_posicao(resultado)
            if isinstance(posicao, int) and posicao > 0:
                pontos += int(PONTOS_POR_POSICAO.get(posicao, 0))
        return pontos

    def _contar_rodadas_com_resultado_temporada(
        self,
        classificacao: list[dict[str, Any]],
    ) -> int:
        max_rodada = 0
        for entrada in classificacao:
            resultados = entrada.get("resultados", [])
            if not isinstance(resultados, list):
                continue
            for indice, resultado in enumerate(resultados, start=1):
                if self._resultado_para_posicao(resultado) is not None:
                    max_rodada = max(max_rodada, indice)
        return max_rodada

    def _mapa_tendencia_real_temporadas(
        self,
        classificacao: list[dict[str, Any]],
    ) -> dict[str, str]:
        if not isinstance(classificacao, list) or not classificacao:
            return {}

        rodadas_completadas = self._contar_rodadas_com_resultado_temporada(classificacao)
        if rodadas_completadas < 2:
            return {}

        def _chave_entrada(entrada: dict[str, Any]) -> str:
            return self._chave_entrada_piloto_temporada(entrada)

        atual_lista: list[dict[str, Any]] = []
        anterior_lista: list[dict[str, Any]] = []
        for entrada in classificacao:
            base = dict(entrada)
            resultados = entrada.get("resultados", [])
            if not isinstance(resultados, list):
                resultados = []

            atual = dict(base)
            atual["pontos"] = self._calcular_pontos_ate_rodada_temporada(resultados, rodadas_completadas)
            atual["resultados"] = list(resultados[:rodadas_completadas])
            atual_lista.append(atual)

            anterior = dict(base)
            anterior["pontos"] = self._calcular_pontos_ate_rodada_temporada(resultados, rodadas_completadas - 1)
            anterior["resultados"] = list(resultados[: max(0, rodadas_completadas - 1)])
            anterior_lista.append(anterior)

        ordenado_atual = self._ordenar_classificacao_por_desempenho_temporada(
            atual_lista,
            limite_rodadas=rodadas_completadas,
        )
        ordenado_anterior = self._ordenar_classificacao_por_desempenho_temporada(
            anterior_lista,
            limite_rodadas=max(0, rodadas_completadas - 1),
        )

        pos_atual = {
            _chave_entrada(entrada): indice
            for indice, entrada in enumerate(ordenado_atual, start=1)
            if _chave_entrada(entrada)
        }
        pos_anterior = {
            _chave_entrada(entrada): indice
            for indice, entrada in enumerate(ordenado_anterior, start=1)
            if _chave_entrada(entrada)
        }

        tendencia: dict[str, str] = {}
        for chave, posicao_atual in pos_atual.items():
            posicao_anterior = pos_anterior.get(chave)
            if posicao_anterior is None:
                continue
            delta = posicao_anterior - posicao_atual
            if delta >= 3:
                tendencia[chave] = "up2"
            elif delta > 0:
                tendencia[chave] = "up"
            elif delta <= -3:
                tendencia[chave] = "down2"
            elif delta < 0:
                tendencia[chave] = "down"
            else:
                tendencia[chave] = "flat"

        return tendencia

    def _obter_classificacao_rivalidade(
        self,
        ano: int,
        categoria_id: str,
    ) -> list[dict[str, Any]]:
        ano_atual = int(self.banco.get("ano_atual", 2024))

        if ano == ano_atual:
            pilotos_categoria = [
                piloto
                for piloto in self.banco.get("pilotos", [])
                if piloto.get("categoria_atual") == categoria_id
                and not piloto.get("aposentado", False)
            ]

            classificacao_base = [
                {
                    "piloto": piloto.get("nome", ""),
                    "piloto_id": piloto.get("id"),
                    "pontos": int(piloto.get("pontos_temporada", 0)),
                    "resultados": list(piloto.get("resultados_temporada", [])),
                }
                for piloto in pilotos_categoria
            ]
            ordenada = self._ordenar_classificacao_por_desempenho_temporada(classificacao_base)
            for posicao, entrada in enumerate(ordenada, start=1):
                entrada["posicao"] = posicao
            return ordenada

        temporada_historica = next(
            (
                item
                for item in self.banco.get("historico_temporadas_completas", [])
                if item.get("ano") == ano and item.get("categoria_id") == categoria_id
            ),
            None,
        )
        if not temporada_historica:
            return []

        classificacao_historica = list(temporada_historica.get("classificacao", []))
        ordenada_historica = self._ordenar_classificacao_por_desempenho_temporada(classificacao_historica)
        for posicao, entrada in enumerate(ordenada_historica, start=1):
            entrada["posicao"] = posicao
        return ordenada_historica

    def _obter_jogador_na_classificacao(
        self,
        classificacao: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        if not classificacao:
            return None

        jogador_atual = self._obter_jogador_atual()
        jogador_id = jogador_atual.get("id") if jogador_atual else None
        jogador_nome = (
            jogador_atual.get("nome")
            if jogador_atual
            else self.banco.get("nome_jogador", "")
        )

        if jogador_id is not None:
            for item in classificacao:
                if item.get("piloto_id") == jogador_id:
                    return item

        nome_normalizado = self._normalizar_nome(jogador_nome)
        if not nome_normalizado:
            return None

        for item in classificacao:
            if self._normalizar_nome(item.get("piloto", "")) == nome_normalizado:
                return item

        return None

    def _coletar_duelos(
        self,
        resultados_jogador: list[Any],
        resultados_rival: list[Any],
    ) -> dict[str, Any]:
        duelos_proximos: list[tuple[int, int, int]] = []
        duelos_gerais: list[tuple[int, int, int]] = []
        ultima_corrida: tuple[int, int | str, int | str] | None = None

        max_corridas = max(len(resultados_jogador), len(resultados_rival))
        for indice in range(max_corridas):
            resultado_jogador = (
                self._resultado_para_posicao(resultados_jogador[indice])
                if indice < len(resultados_jogador)
                else None
            )
            resultado_rival = (
                self._resultado_para_posicao(resultados_rival[indice])
                if indice < len(resultados_rival)
                else None
            )

            if resultado_jogador is None or resultado_rival is None:
                continue

            ultima_corrida = (indice + 1, resultado_jogador, resultado_rival)

            if isinstance(resultado_jogador, int) and isinstance(resultado_rival, int):
                duelos_gerais.append((indice + 1, resultado_jogador, resultado_rival))
                if abs(resultado_jogador - resultado_rival) <= 3:
                    duelos_proximos.append((indice + 1, resultado_jogador, resultado_rival))

        duelos_base = duelos_proximos if duelos_proximos else duelos_gerais

        vitorias_jogador = sum(1 for _, pj, pr in duelos_base if pj < pr)
        vitorias_rival = sum(1 for _, pj, pr in duelos_base if pr < pj)

        return {
            "duelos": duelos_base,
            "vitorias_jogador": vitorias_jogador,
            "vitorias_rival": vitorias_rival,
            "ultima_corrida": ultima_corrida,
        }

    def _selecionar_rival_principal(
        self,
        jogador: dict[str, Any],
        rivais: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        melhor_rival = None
        melhor_analise = None
        melhor_ordem: tuple[int, int, int] | None = None

        for rival in rivais:
            analise = self._coletar_duelos(
                list(jogador.get("resultados", [])),
                list(rival.get("resultados", [])),
            )

            diff_pontos = int(jogador.get("pontos", 0)) - int(rival.get("pontos", 0))
            ordem = (
                len(analise["duelos"]),
                -abs(diff_pontos),
                -int(rival.get("pontos", 0)),
            )

            if melhor_ordem is None or ordem > melhor_ordem:
                melhor_ordem = ordem
                melhor_rival = rival
                melhor_analise = analise

        if melhor_rival is None or melhor_analise is None:
            return None

        return {
            "rival": melhor_rival,
            "analise": melhor_analise,
            "diff_pontos": int(jogador.get("pontos", 0)) - int(melhor_rival.get("pontos", 0)),
        }

    def _formatar_linha_box(self, texto: str, largura: int = 61) -> str:
        conteudo = str(texto)
        if len(conteudo) > largura:
            conteudo = f"{conteudo[: max(0, largura - 3)]}..."
        return f"│{conteudo.ljust(largura)}│"

    def _montar_box_sem_dados(self, mensagem: str) -> str:
        largura = 61
        linhas = [
            f"┌{'─' * largura}┐",
            self._formatar_linha_box("  SEUS RIVAIS", largura),
            f"├{'─' * largura}┤",
            self._formatar_linha_box("", largura),
            self._formatar_linha_box(f"  {mensagem}", largura),
            self._formatar_linha_box("", largura),
            f"└{'─' * largura}┘",
        ]
        return "\n".join(linhas)

    def _montar_linhas_ultima_corrida(
        self,
        nome_rival: str,
        ultima_corrida: tuple[int, int | str, int | str] | None,
    ) -> tuple[str, str]:
        if not ultima_corrida:
            return (
                "• Nenhum confronto registrado na temporada",
                "• Simule ou importe corridas para gerar rivalidade",
            )

        rodada, resultado_jogador, resultado_rival = ultima_corrida
        prefixo = f"• Rodada {rodada}: "

        if isinstance(resultado_jogador, int) and isinstance(resultado_rival, int):
            linha_1 = (
                f"{prefixo}você P{resultado_jogador}, {nome_rival} P{resultado_rival}"
            )
            if resultado_jogador < resultado_rival:
                linha_2 = (
                    f"• Você terminou {resultado_rival - resultado_jogador} posição(ões) à frente"
                )
            elif resultado_rival < resultado_jogador:
                linha_2 = (
                    f"• {nome_rival} terminou {resultado_jogador - resultado_rival} posição(ões) à frente"
                )
            else:
                linha_2 = "• Vocês terminaram empatados na posição final"
            return linha_1, linha_2

        if resultado_jogador == "DNF" and isinstance(resultado_rival, int):
            return (
                f"{prefixo}você DNF, {nome_rival} P{resultado_rival}",
                "• O abandono comprometeu o duelo direto",
            )

        if isinstance(resultado_jogador, int) and resultado_rival == "DNF":
            return (
                f"{prefixo}você P{resultado_jogador}, {nome_rival} DNF",
                "• Você capitalizou o abandono do rival",
            )

        return (
            f"{prefixo}você DNF, {nome_rival} DNF",
            "• Duelo sem resultado por abandono de ambos",
        )

    def _montar_box_rivalidade(
        self,
        rival_data: dict[str, Any],
    ) -> str:
        largura = 61
        rival = rival_data["rival"]
        analise = rival_data["analise"]
        diff_pontos = int(rival_data["diff_pontos"])

        nome_rival = str(rival.get("piloto", "Rival IA"))
        disputas = len(analise["duelos"])
        vitorias_jogador = int(analise["vitorias_jogador"])
        vitorias_rival = int(analise["vitorias_rival"])

        if diff_pontos > 0:
            texto_diff = f"+{diff_pontos} pts (você lidera)"
        elif diff_pontos < 0:
            texto_diff = f"-{abs(diff_pontos)} pts (rival lidera)"
        else:
            texto_diff = "0 pts (empatados)"

        linha_ultima_1, linha_ultima_2 = self._montar_linhas_ultima_corrida(
            nome_rival,
            analise["ultima_corrida"],
        )

        linhas = [
            f"┌{'─' * largura}┐",
            self._formatar_linha_box("  SEUS RIVAIS", largura),
            f"├{'─' * largura}┤",
            self._formatar_linha_box("", largura),
            self._formatar_linha_box(f"  🔥 Rival Principal: {nome_rival} (IA)", largura),
            self._formatar_linha_box(f"  • {disputas} disputas diretas", largura),
            self._formatar_linha_box(
                f"  • Você venceu {vitorias_jogador}x, ele venceu {vitorias_rival}x",
                largura,
            ),
            self._formatar_linha_box(
                f"  • Diferença no campeonato: {texto_diff}",
                largura,
            ),
            self._formatar_linha_box("", largura),
            self._formatar_linha_box("  ⚔️ Confrontos na última corrida:", largura),
            self._formatar_linha_box(f"  {linha_ultima_1}", largura),
            self._formatar_linha_box(f"  {linha_ultima_2}", largura),
            self._formatar_linha_box("", largura),
            f"└{'─' * largura}┘",
        ]

        return "\n".join(linhas)

    def _atualizar_rivalidades_ia(self):
        ano_texto = self.combo_ano_rival.currentText()
        categoria_nome = self.combo_categoria_rival.currentText()

        if not ano_texto or not categoria_nome:
            self.lbl_rivais_vazio.setText("Selecione ano e categoria para analisar rivais.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        categoria = next(
            (item for item in CATEGORIAS if item.get("nome") == categoria_nome),
            None,
        )
        if not categoria:
            self.lbl_rivais_vazio.setText("Categoria inválida para análise.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        classificacao = self._obter_classificacao_rivalidade(
            int(ano_texto),
            categoria["id"],
        )
        if not classificacao:
            self.lbl_rivais_vazio.setText("Sem resultados registrados para esse ano/categoria.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        jogador = self._obter_jogador_na_classificacao(classificacao)
        if not jogador:
            self.lbl_rivais_vazio.setText("Seu piloto não aparece nessa temporada/categoria.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        jogador_id = jogador.get("piloto_id")
        nome_jogador_normalizado = self._normalizar_nome(jogador.get("piloto", ""))
        rivais = [
            item
            for item in classificacao
            if item is not jogador
            and (jogador_id is None or item.get("piloto_id") != jogador_id)
            and self._normalizar_nome(item.get("piloto", "")) != nome_jogador_normalizado
        ]
        if not rivais:
            self.lbl_rivais_vazio.setText("Não há rivais suficientes nessa categoria.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        ranking: list[dict[str, Any]] = []
        for rival in rivais:
            analise = self._coletar_duelos(
                list(jogador.get("resultados", [])),
                list(rival.get("resultados", [])),
            )
            ranking.append(
                {
                    "rival": rival,
                    "analise": analise,
                    "diff_pontos": int(jogador.get("pontos", 0)) - int(rival.get("pontos", 0)),
                }
            )

        ranking.sort(
            key=lambda item: (
                len(item["analise"]["duelos"]),
                -abs(int(item["diff_pontos"])),
                -int(item["rival"].get("pontos", 0)),
            ),
            reverse=True,
        )

        if not ranking:
            self.lbl_rivais_vazio.setText("Não foi possível determinar rivais para esse contexto.")
            self.lbl_rivais_vazio.setVisible(True)
            self.card_rival_principal.setVisible(False)
            self.card_intensidade.setVisible(False)
            self._atualizar_cards_outros_rivais([])
            self._rival_principal_data = None
            return

        self.lbl_rivais_vazio.setVisible(False)
        self.card_rival_principal.setVisible(True)
        self.card_intensidade.setVisible(True)

        self._rival_principal_data = ranking[0]
        self._atualizar_card_rival_principal(self._rival_principal_data)
        self._atualizar_cards_outros_rivais(ranking[1:4])

    def _criar_item(
        self,
        texto,
        *,
        cor_texto=None,
        cor_fundo=None,
        alinhamento=None,
        negrito=False,
    ):
        item = QTableWidgetItem(str(texto))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

        if alinhamento is not None:
            item.setTextAlignment(alinhamento)

        if cor_texto:
            item.setForeground(QBrush(QColor(cor_texto)))

        if cor_fundo:
            item.setBackground(QBrush(QColor(cor_fundo)))

        if negrito:
            fonte = item.font()
            fonte.setBold(True)
            item.setFont(fonte)

        return item

    def _cor_borda_badge_resultado_temporada(self, texto: str, cor_fundo: str) -> str:
        texto_upper = str(texto).strip().upper()
        if texto_upper == "DNF":
            return "#8b3a3a"
        if cor_fundo in {Cores.OURO, Cores.PRATA, Cores.BRONZE}:
            return HIST_BG_SURFACE
        return HIST_BORDER_HOVER

    def _normalizar_texto_busca_temporada(self, texto: Any) -> str:
        bruto = str(texto or "").strip().casefold()
        if not bruto:
            return ""
        decomposicao = unicodedata.normalize("NFD", bruto)
        return "".join(
            caractere
            for caractere in decomposicao
            if unicodedata.category(caractere) != "Mn"
        )

    def _obter_codigo_bandeira_corrida_temporada(self, circuito: Any, indice: int) -> str:
        return obter_codigo_bandeira_circuito(
            str(circuito or ""),
            indice_fallback=indice,
        )

    def _obter_piloto_referencia_temporada(self, entrada: dict[str, Any]) -> dict[str, Any] | None:
        piloto_id = entrada.get("piloto_id")
        if piloto_id is not None:
            por_id = next(
                (
                    piloto
                    for piloto in self.banco.get("pilotos", [])
                    if self._ids_equivalentes(piloto.get("id"), piloto_id)
                ),
                None,
            )
            if isinstance(por_id, dict):
                return por_id

        nome_alvo = self._normalizar_nome(entrada.get("piloto", ""))
        if not nome_alvo:
            return None

        return next(
            (
                piloto
                for piloto in self.banco.get("pilotos", [])
                if self._normalizar_nome(piloto.get("nome", "")) == nome_alvo
            ),
            None,
        )

    def _criar_piloto_snapshot_temporada(self, entrada: dict[str, Any]) -> dict[str, Any] | None:
        from UI.fichas import preparar_payload_ficha_piloto

        categoria_nome = self.combo_categoria.currentText().strip() if hasattr(self, "combo_categoria") else ""
        return preparar_payload_ficha_piloto(
            None,
            self.banco,
            entrada_temporada=entrada if isinstance(entrada, dict) else None,
            categoria_nome=categoria_nome,
        )

    def _enriquecer_piloto_ficha_temporada(
        self,
        piloto_ref: dict[str, Any],
        entrada: dict[str, Any],
        row: int,
    ) -> dict[str, Any]:
        from UI.fichas import preparar_payload_ficha_piloto

        categoria_nome = self.combo_categoria.currentText().strip() if hasattr(self, "combo_categoria") else ""
        cor_equipe = ""
        item_piloto = self.tabela_temporadas.item(row, 3) if hasattr(self, "tabela_temporadas") else None
        if item_piloto is not None:
            cor_equipe = str(item_piloto.data(BadgeResultadoDelegate.ROLE_EQUIPE_COR) or "").strip()

        payload = preparar_payload_ficha_piloto(
            piloto_ref if isinstance(piloto_ref, dict) else None,
            self.banco,
            entrada_temporada=entrada if isinstance(entrada, dict) else None,
            categoria_nome=categoria_nome,
            cor_equipe_hint=cor_equipe,
        )
        return payload if isinstance(payload, dict) else dict(piloto_ref or {})

    def _obter_codigo_bandeira_nacionalidade_temporada(
        self,
        entrada: dict[str, Any],
        piloto_ref: dict[str, Any] | None,
    ) -> str:
        def _fallback_por_nome() -> str:
            nome = str(entrada.get("piloto", "") or "").strip()
            if not nome:
                return "un"
            seed = sum((indice + 1) * ord(ch) for indice, ch in enumerate(nome.casefold()))
            return CODIGOS_BANDEIRAS_SUPORTADOS[seed % len(CODIGOS_BANDEIRAS_SUPORTADOS)]

        nacionalidade = ""
        for chave in ("nacionalidade", "nac", "country", "country_code", "pais", "pais_codigo"):
            valor_entrada = entrada.get(chave)
            if valor_entrada not in (None, ""):
                nacionalidade = str(valor_entrada).strip()
                break

        if isinstance(piloto_ref, dict):
            nacionalidade_ref = str(piloto_ref.get("nacionalidade", "") or "").strip()
            if nacionalidade_ref:
                nacionalidade = nacionalidade_ref

        if not nacionalidade:
            return _fallback_por_nome()

        codigo = obter_codigo_bandeira(nacionalidade, fallback="")
        if codigo:
            return codigo

        return _fallback_por_nome()

    def _obter_idade_exibicao_temporada(self, piloto_ref: dict[str, Any] | None, ano: int) -> str:
        if not isinstance(piloto_ref, dict):
            return "-"

        idade_atual = self._safe_int(piloto_ref.get("idade"), default=-1)
        if idade_atual <= 0:
            return "-"

        ano_atual = self._safe_int(self.banco.get("ano_atual"), default=ano)
        delta = max(0, ano_atual - ano)
        idade_temporada = max(16, idade_atual - delta)
        return str(idade_temporada)

    def _montar_medalhas_resultados_temporada(self, resultados: list[Any]) -> str:
        ouro = 0
        prata = 0
        bronze = 0

        for resultado in resultados:
            posicao = self._resultado_para_posicao(resultado)
            if posicao == 1:
                ouro += 1
            elif posicao == 2:
                prata += 1
            elif posicao == 3:
                bronze += 1

        partes = []
        if ouro > 0:
            partes.append("🥇" * ouro)
        if prata > 0:
            partes.append("🥈" * prata)
        if bronze > 0:
            partes.append("🥉" * bronze)
        return "".join(partes) or "—"

    def _formatar_resultado_heatmap_temporada(
        self,
        resultado: Any,
    ) -> tuple[str, str, str, str, bool]:
        resultado_normalizado = self._resultado_para_posicao(resultado)

        if resultado_normalizado == "DNF":
            return "DNF", Cores.VERMELHO, "#2a171a", "#8b3a3a", True

        if isinstance(resultado_normalizado, int):
            if resultado_normalizado == 1:
                return "1", Cores.TEXTO_INVERSE, Cores.OURO, HIST_BG_SURFACE, True
            if resultado_normalizado == 2:
                return "2", Cores.TEXTO_INVERSE, Cores.PRATA, HIST_BG_SURFACE, True
            if resultado_normalizado == 3:
                return "3", Cores.TEXTO_INVERSE, Cores.BRONZE, HIST_BG_SURFACE, True
            return str(resultado_normalizado), HIST_TEXT_PRIMARY, HIST_BG_SURFACE_ALT, HIST_BORDER_HOVER, False

        # Corridas futuras/sem dado: bloco discreto e sem texto.
        return "", HIST_TEXT_MUTED, HIST_BG_SURFACE, HIST_BORDER, False

    def _chave_entrada_piloto_temporada(self, entrada: dict[str, Any]) -> str:
        piloto_id_norm = self._normalizar_id(entrada.get("piloto_id"))
        if piloto_id_norm:
            return f"id:{piloto_id_norm}"

        nome_norm = self._normalizar_nome(entrada.get("piloto", ""))
        if nome_norm:
            return f"nome:{nome_norm}"
        return ""

    def _obter_marcadores_evento_mock_temporada(
        self,
        entrada: dict[str, Any],
        indice_corrida: int,
        ano: int,
        categoria_id: str,
        resultado: Any,
    ) -> bool:
        posicao = self._resultado_para_posicao(resultado)
        if not isinstance(posicao, int):
            return False

        chave_entrada = self._chave_entrada_piloto_temporada(entrada)
        if not chave_entrada:
            return False

        mapa_vmr = getattr(self, "_mapa_vmr_rodada_temporadas", {})
        if not isinstance(mapa_vmr, dict):
            return False
        return mapa_vmr.get(indice_corrida) == chave_entrada

    def _mapear_vmr_por_rodada_temporada(
        self,
        classificacao: list[dict[str, Any]],
        temporada: dict[str, Any],
        ano: int,
        categoria_id: str,
        num_corridas: int,
    ) -> dict[int, str]:
        mapa_vmr: dict[int, str] = {}
        total_corridas = max(0, int(num_corridas))
        if total_corridas <= 0 or not classificacao:
            return mapa_vmr

        chaves_por_id: dict[str, str] = {}
        chaves_por_nome: dict[str, str] = {}
        for entrada in classificacao:
            if not isinstance(entrada, dict):
                continue
            chave = self._chave_entrada_piloto_temporada(entrada)
            if not chave:
                continue
            piloto_id_norm = self._normalizar_id(entrada.get("piloto_id"))
            if piloto_id_norm:
                chaves_por_id[piloto_id_norm] = chave
            nome_norm = self._normalizar_nome(entrada.get("piloto", ""))
            if nome_norm and nome_norm not in chaves_por_nome:
                chaves_por_nome[nome_norm] = chave

        mapas_registrados: list[dict[str, Any]] = []
        mapa_temporada = temporada.get("volta_rapida_por_rodada")
        if isinstance(mapa_temporada, dict):
            mapas_registrados.append(mapa_temporada)

        ano_atual = self._safe_int(self.banco.get("ano_atual"), default=ano)
        banco_vmr = self.banco.get("volta_rapida_por_rodada", {})
        if ano == ano_atual and isinstance(banco_vmr, dict):
            mapa_atual_categoria = banco_vmr.get(str(categoria_id), {})
            if isinstance(mapa_atual_categoria, dict):
                mapas_registrados.append(mapa_atual_categoria)

        for mapa_registrado in mapas_registrados:
            for rodada_raw, registro in mapa_registrado.items():
                try:
                    rodada = int(rodada_raw)
                except (TypeError, ValueError):
                    continue
                if rodada <= 0:
                    continue
                indice_corrida = rodada - 1
                if indice_corrida >= total_corridas:
                    continue

                chave_piloto = ""
                if isinstance(registro, dict):
                    piloto_id_norm = self._normalizar_id(registro.get("piloto_id"))
                    if piloto_id_norm:
                        chave_piloto = chaves_por_id.get(piloto_id_norm, "")

                    if not chave_piloto:
                        nome_norm = self._normalizar_nome(registro.get("piloto_nome", ""))
                        if nome_norm:
                            chave_piloto = chaves_por_nome.get(nome_norm, "")
                elif isinstance(registro, str):
                    nome_norm = self._normalizar_nome(registro)
                    if nome_norm:
                        chave_piloto = chaves_por_nome.get(nome_norm, "")

                if chave_piloto:
                    mapa_vmr[indice_corrida] = chave_piloto

        # Fallback para temporadas antigas sem metadado: garante 1 marcador por corrida.
        for indice_corrida in range(total_corridas):
            if indice_corrida in mapa_vmr:
                continue

            melhor_chave = ""
            melhor_score = float("-inf")
            for entrada in classificacao:
                if not isinstance(entrada, dict):
                    continue
                resultados = entrada.get("resultados", [])
                if not isinstance(resultados, list):
                    continue
                resultado = resultados[indice_corrida] if indice_corrida < len(resultados) else None
                posicao = self._resultado_para_posicao(resultado)
                if not isinstance(posicao, int):
                    continue

                chave = self._chave_entrada_piloto_temporada(entrada)
                if not chave:
                    continue

                chave_seed = f"{chave}|{indice_corrida}|{ano}|{categoria_id}"
                seed = sum((indice + 1) * ord(ch) for indice, ch in enumerate(chave_seed))
                variacao = ((seed % 1000) / 1000.0 - 0.5) * 2.0
                score = max(0.0, 22.0 - float(posicao)) * 1.8 + variacao

                if score > melhor_score or (
                    score == melhor_score
                    and (not melhor_chave or chave < melhor_chave)
                ):
                    melhor_score = score
                    melhor_chave = chave

            if melhor_chave:
                mapa_vmr[indice_corrida] = melhor_chave

        return mapa_vmr

    def _obter_chaves_rivais_mock_temporadas(
        self,
        classificacao: list[dict[str, Any]],
    ) -> set[str]:
        if not classificacao:
            return set()

        chaves_rivais: set[str] = set()
        indice_jogador = next(
            (
                i
                for i, entrada in enumerate(classificacao)
                if self._entrada_eh_jogador_temporada(entrada)
            ),
            -1,
        )

        if indice_jogador >= 0:
            for deslocamento in (1, -1, 2, -2, 3, -3):
                indice = indice_jogador + deslocamento
                if indice < 0 or indice >= len(classificacao):
                    continue
                entrada = classificacao[indice]
                if self._entrada_eh_jogador_temporada(entrada):
                    continue
                chave = self._chave_entrada_piloto_temporada(entrada)
                if chave:
                    chaves_rivais.add(chave)
                if len(chaves_rivais) >= 2:
                    return chaves_rivais

        for entrada in classificacao:
            if self._entrada_eh_jogador_temporada(entrada):
                continue
            chave = self._chave_entrada_piloto_temporada(entrada)
            if chave:
                chaves_rivais.add(chave)
            if len(chaves_rivais) >= 2:
                break

        return chaves_rivais

    def _obter_trofeus_equipes_temporadas(
        self,
        categoria_id: str,
        ano_limite: int | None = None,
    ) -> dict[str, dict[str, int]]:
        trofeus: dict[str, dict[str, int]] = {}
        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return trofeus

        for temporada in historico:
            if not isinstance(temporada, dict):
                continue
            if str(temporada.get("categoria_id", "")) != str(categoria_id):
                continue

            ano_temporada = self._safe_int(temporada.get("ano"), default=0)
            if ano_limite is not None and ano_temporada > int(ano_limite):
                continue

            classificacao = temporada.get("classificacao", [])
            if not isinstance(classificacao, list) or not classificacao:
                continue

            pontos_por_equipe: dict[str, int] = {}
            for entrada in classificacao:
                if not isinstance(entrada, dict):
                    continue
                equipe_nome = str(entrada.get("equipe", "") or "").strip()
                if not equipe_nome:
                    continue
                pontos = self._safe_int(entrada.get("pontos"), default=0)
                pontos_por_equipe[equipe_nome] = pontos_por_equipe.get(equipe_nome, 0) + pontos

            ranking = sorted(
                pontos_por_equipe.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
            if not ranking:
                continue

            for indice, tipo in enumerate(("ouro", "prata", "bronze")):
                if indice >= len(ranking):
                    break
                equipe_nome = ranking[indice][0].casefold()
                if equipe_nome not in trofeus:
                    trofeus[equipe_nome] = {"ouro": 0, "prata": 0, "bronze": 0}
                trofeus[equipe_nome][tipo] += 1

        return trofeus

    def _contar_titulos_historicos_piloto_temporadas(
        self,
        entrada_ref: dict[str, Any],
        categoria_id: str,
        ano_limite: int | None = None,
    ) -> int:
        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return 0

        piloto_id_ref = entrada_ref.get("piloto_id")
        nome_ref_norm = self._normalizar_nome(entrada_ref.get("piloto", ""))
        if piloto_id_ref is None and not nome_ref_norm:
            return 0

        total_titulos = 0
        for temporada in historico:
            if not isinstance(temporada, dict):
                continue
            if str(temporada.get("categoria_id", "")) != str(categoria_id):
                continue

            ano_temporada = self._safe_int(temporada.get("ano"), default=0)
            if ano_limite is not None and ano_temporada > int(ano_limite):
                continue

            classificacao = temporada.get("classificacao", [])
            if not isinstance(classificacao, list) or not classificacao:
                continue

            campeao = next(
                (
                    entrada
                    for entrada in classificacao
                    if self._safe_int(entrada.get("posicao"), default=0) == 1
                ),
                None,
            )
            if not isinstance(campeao, dict):
                continue

            match_por_id = (
                piloto_id_ref is not None
                and campeao.get("piloto_id") is not None
                and self._ids_equivalentes(campeao.get("piloto_id"), piloto_id_ref)
            )
            match_por_nome = bool(
                nome_ref_norm
                and self._normalizar_nome(campeao.get("piloto", "")) == nome_ref_norm
            )
            if match_por_id or match_por_nome:
                total_titulos += 1

        return total_titulos

    def _chave_piloto_historico_temporadas(self, piloto_id: Any, nome: Any) -> str:
        piloto_id_norm = self._normalizar_id(piloto_id)
        if piloto_id_norm:
            return f"id:{piloto_id_norm}"

        nome_norm = self._normalizar_nome(nome)
        if nome_norm:
            return f"nome:{nome_norm}"
        return ""

    def _obter_chave_campeao_pilotos_ano_temporadas(
        self,
        categoria_id: str,
        ano_referencia: int | None,
    ) -> str:
        if ano_referencia is None:
            return ""

        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return ""

        temporada = next(
            (
                item
                for item in historico
                if isinstance(item, dict)
                and str(item.get("categoria_id", "")) == str(categoria_id)
                and self._safe_int(item.get("ano"), default=0) == int(ano_referencia)
            ),
            None,
        )
        if not isinstance(temporada, dict):
            return ""

        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return ""

        campeao = next(
            (
                entrada
                for entrada in classificacao
                if self._safe_int(entrada.get("posicao"), default=0) == 1
            ),
            None,
        )
        if not isinstance(campeao, dict):
            return ""

        return self._chave_piloto_historico_temporadas(
            campeao.get("piloto_id"),
            campeao.get("piloto", ""),
        )

    def _obter_podio_construtores_ano_temporadas(
        self,
        categoria_id: str,
        ano_referencia: int | None,
    ) -> dict[str, str]:
        if ano_referencia is None:
            return {}

        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return {}

        temporada = next(
            (
                item
                for item in historico
                if isinstance(item, dict)
                and str(item.get("categoria_id", "")) == str(categoria_id)
                and self._safe_int(item.get("ano"), default=0) == int(ano_referencia)
            ),
            None,
        )
        if not isinstance(temporada, dict):
            return {}

        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return {}

        pontos_por_equipe: dict[str, int] = {}
        for entrada in classificacao:
            if not isinstance(entrada, dict):
                continue
            equipe_nome = str(entrada.get("equipe", "") or "").strip()
            if not equipe_nome:
                continue
            pontos = self._safe_int(entrada.get("pontos"), default=0)
            pontos_por_equipe[equipe_nome] = pontos_por_equipe.get(equipe_nome, 0) + pontos

        if not pontos_por_equipe:
            return {}

        ranking = sorted(
            pontos_por_equipe.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
        tipos = ("ouro", "prata", "bronze")
        podio: dict[str, str] = {}
        for indice, tipo in enumerate(tipos):
            if indice >= len(ranking):
                break
            podio[tipo] = self._normalizar_chave_equipe_temporadas(ranking[indice][0])
        return podio

    def _obter_pontos_equipes_temporadas(
        self,
        classificacao: list[dict[str, Any]],
    ) -> dict[str, int]:
        pontos_por_equipe: dict[str, int] = {}
        for entrada in classificacao:
            equipe_nome = str(entrada.get("equipe", "") or "").strip()
            if not equipe_nome:
                continue
            pontos = self._safe_int(entrada.get("pontos"), default=0)
            pontos_por_equipe[equipe_nome] = pontos_por_equipe.get(equipe_nome, 0) + pontos
        return pontos_por_equipe

    def _entrada_eh_jogador_temporada(self, entrada: dict[str, Any]) -> bool:
        jogador_atual = self._obter_jogador_atual()
        if not isinstance(jogador_atual, dict):
            return False

        jogador_id = jogador_atual.get("id")
        if jogador_id is not None and self._ids_equivalentes(entrada.get("piloto_id"), jogador_id):
            return True

        nome_jogador_norm = self._normalizar_nome(jogador_atual.get("nome", ""))
        return bool(
            nome_jogador_norm
            and self._normalizar_nome(entrada.get("piloto", "")) == nome_jogador_norm
        )

    def _obter_destaques_linhas_temporadas(
        self,
        classificacao: list[dict[str, Any]],
    ) -> tuple[set[str], set[str]]:
        ids_destaque: set[str] = set()
        nomes_destaque: set[str] = set()

        if not classificacao:
            return ids_destaque, nomes_destaque

        entrada_sel = None
        if self._piloto_id_destacado_temporadas is not None:
            entrada_sel = next(
                (
                    entrada
                    for entrada in classificacao
                    if self._ids_equivalentes(
                        entrada.get("piloto_id"),
                        self._piloto_id_destacado_temporadas,
                    )
                ),
                None,
            )

        if entrada_sel is None and self._piloto_nome_destacado_temporadas:
            entrada_sel = next(
                (
                    entrada
                    for entrada in classificacao
                    if self._normalizar_nome(entrada.get("piloto", ""))
                    == self._piloto_nome_destacado_temporadas
                ),
                None,
            )

        if not isinstance(entrada_sel, dict):
            return ids_destaque, nomes_destaque

        equipe_sel = str(entrada_sel.get("equipe", "") or "").strip().casefold()
        for entrada in classificacao:
            entrada_id_norm = self._normalizar_id(entrada.get("piloto_id"))
            entrada_nome_norm = self._normalizar_nome(entrada.get("piloto", ""))
            mesma_equipe = (
                equipe_sel
                and str(entrada.get("equipe", "") or "").strip().casefold() == equipe_sel
            )

            if mesma_equipe or (
                entrada_nome_norm
                and entrada_nome_norm == self._normalizar_nome(entrada_sel.get("piloto", ""))
            ):
                if entrada_id_norm:
                    ids_destaque.add(entrada_id_norm)
                if entrada_nome_norm:
                    nomes_destaque.add(entrada_nome_norm)

        return ids_destaque, nomes_destaque

    def _normalizar_chave_equipe_temporadas(self, nome_equipe: Any) -> str:
        return str(nome_equipe or "").strip().casefold()

    def _cor_destaque_por_equipe_temporadas(
        self,
        cor_base: str,
        cor_equipe: str,
        alpha: int = 64,
    ) -> str:
        base = QColor(str(cor_base or HIST_BG_CARD))
        equipe = QColor(str(cor_equipe or HIST_ACCENT))
        if not equipe.isValid():
            equipe = QColor(HIST_ACCENT)

        fator = max(0, min(255, int(alpha))) / 255.0
        r = int((1.0 - fator) * base.red() + fator * equipe.red())
        g = int((1.0 - fator) * base.green() + fator * equipe.green())
        b = int((1.0 - fator) * base.blue() + fator * equipe.blue())
        return QColor(r, g, b).name()

    def _obter_contexto_destaque_equipes_temporadas(
        self,
        classificacao: list[dict[str, Any]],
    ) -> tuple[set[str], set[str], str]:
        ids_destaque: set[str] = set()
        nomes_destaque: set[str] = set()
        equipe_chave_sel = self._normalizar_chave_equipe_temporadas(
            self._equipe_chave_destacada_temporadas
        )

        if not classificacao:
            return ids_destaque, nomes_destaque, equipe_chave_sel

        entrada_sel = None
        if self._piloto_id_destacado_temporadas is not None:
            entrada_sel = next(
                (
                    entrada
                    for entrada in classificacao
                    if self._ids_equivalentes(
                        entrada.get("piloto_id"),
                        self._piloto_id_destacado_temporadas,
                    )
                ),
                None,
            )
        if entrada_sel is None and self._piloto_nome_destacado_temporadas:
            entrada_sel = next(
                (
                    entrada
                    for entrada in classificacao
                    if self._normalizar_nome(entrada.get("piloto", ""))
                    == self._piloto_nome_destacado_temporadas
                ),
                None,
            )

        if not equipe_chave_sel and isinstance(entrada_sel, dict):
            equipe_chave_sel = self._normalizar_chave_equipe_temporadas(
                entrada_sel.get("equipe", "")
            )

        if isinstance(entrada_sel, dict):
            id_norm = self._normalizar_id(entrada_sel.get("piloto_id"))
            nome_norm = self._normalizar_nome(entrada_sel.get("piloto", ""))
            if id_norm:
                ids_destaque.add(id_norm)
            if nome_norm:
                nomes_destaque.add(nome_norm)

            if self._destacar_somente_piloto_temporadas:
                return ids_destaque, nomes_destaque, ""

        for entrada in classificacao:
            entrada_id_norm = self._normalizar_id(entrada.get("piloto_id"))
            entrada_nome_norm = self._normalizar_nome(entrada.get("piloto", ""))
            entrada_equipe_chave = self._normalizar_chave_equipe_temporadas(
                entrada.get("equipe", "")
            )
            if not entrada_equipe_chave:
                continue
            if equipe_chave_sel and entrada_equipe_chave == equipe_chave_sel:
                if entrada_id_norm:
                    ids_destaque.add(entrada_id_norm)
                if entrada_nome_norm:
                    nomes_destaque.add(entrada_nome_norm)

        return ids_destaque, nomes_destaque, equipe_chave_sel

    def _ao_clicar_linha_temporadas(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._classificacao_temporadas_atual):
            return

        self._destacar_somente_piloto_temporadas = False
        entrada = self._classificacao_temporadas_atual[row]
        self._piloto_id_destacado_temporadas = entrada.get("piloto_id")
        self._piloto_nome_destacado_temporadas = self._normalizar_nome(
            entrada.get("piloto", "")
        )
        item_piloto = self.tabela_temporadas.item(row, 3)
        if item_piloto is not None:
            self._equipe_chave_destacada_temporadas = self._normalizar_chave_equipe_temporadas(
                item_piloto.data(BadgeResultadoDelegate.ROLE_EQUIPE_CHAVE)
            )
            self._cor_equipe_destacada_temporadas = str(
                item_piloto.data(BadgeResultadoDelegate.ROLE_EQUIPE_COR)
                or self._cor_equipe_destacada_temporadas
                or ""
            )
        self._atualizar_tabela_temporadas()

        # Fallback de "duplo clique" quando a repintura da tabela interrompe o evento nativo.
        agora = monotonic()
        if row == self._ultimo_clique_linha_temporadas and (agora - self._ultimo_clique_ts_temporadas) <= 0.34:
            self._ultimo_clique_linha_temporadas = -1
            self._ultimo_clique_ts_temporadas = 0.0
            self._abrir_ficha_piloto_linha_temporadas(row, _col)
        else:
            self._ultimo_clique_linha_temporadas = row
            self._ultimo_clique_ts_temporadas = agora

    def _ao_clicar_linha_equipes_temporadas(self, row: int, _col: int) -> None:
        if not hasattr(self, "tabela_equipes_temporadas"):
            return
        if row < 0 or row >= self.tabela_equipes_temporadas.rowCount():
            return

        self._destacar_somente_piloto_temporadas = False
        item_equipe = self.tabela_equipes_temporadas.item(row, 1)
        if item_equipe is None:
            return

        self._piloto_id_destacado_temporadas = None
        self._piloto_nome_destacado_temporadas = ""
        self._equipe_chave_destacada_temporadas = self._normalizar_chave_equipe_temporadas(
            item_equipe.data(BadgeResultadoDelegate.ROLE_EQUIPE_CHAVE)
        )
        self._cor_equipe_destacada_temporadas = str(
            item_equipe.data(BadgeResultadoDelegate.ROLE_EQUIPE_COR)
            or self._cor_equipe_destacada_temporadas
            or ""
        )
        self._atualizar_tabela_temporadas()

    def _destacar_piloto_na_tela(self, piloto: dict[str, Any]) -> None:
        if not isinstance(piloto, dict):
            return
        if not hasattr(self, "tabela_temporadas"):
            return
        if not isinstance(getattr(self, "_classificacao_temporadas_atual", None), list):
            return

        classificacao = self._classificacao_temporadas_atual
        if not classificacao:
            return

        piloto_id_norm = self._normalizar_id(piloto.get("id"))
        nome_norm = self._normalizar_nome(piloto.get("nome", ""))
        row = -1

        if piloto_id_norm:
            row = next(
                (
                    indice
                    for indice, entrada in enumerate(classificacao)
                    if self._normalizar_id(entrada.get("piloto_id")) == piloto_id_norm
                ),
                -1,
            )

        if row < 0 and nome_norm:
            row = next(
                (
                    indice
                    for indice, entrada in enumerate(classificacao)
                    if self._normalizar_nome(entrada.get("piloto", "")) == nome_norm
                ),
                -1,
            )

        if row < 0:
            return

        entrada = classificacao[row]
        self._destacar_somente_piloto_temporadas = True
        self._piloto_id_destacado_temporadas = entrada.get("piloto_id")
        self._piloto_nome_destacado_temporadas = self._normalizar_nome(entrada.get("piloto", ""))
        self._equipe_chave_destacada_temporadas = ""
        item_piloto = self.tabela_temporadas.item(row, 3)
        if item_piloto is not None:
            self._cor_equipe_destacada_temporadas = str(
                item_piloto.data(BadgeResultadoDelegate.ROLE_EQUIPE_COR)
                or self._cor_equipe_destacada_temporadas
                or HIST_ACCENT
            )
        self._atualizar_tabela_temporadas()

        item_ref = self.tabela_temporadas.item(row, 3) or self.tabela_temporadas.item(row, 0)
        if item_ref is not None:
            self.tabela_temporadas.scrollToItem(item_ref, QAbstractItemView.PositionAtCenter)
            self.tabela_temporadas.setCurrentCell(row, 3)
            self.tabela_temporadas.viewport().update()

    def _ao_duplo_clique_linha_equipes_temporadas(self, row: int, _col: int) -> None:
        if not hasattr(self, "tabela_equipes_temporadas"):
            return
        if row < 0 or row >= self.tabela_equipes_temporadas.rowCount():
            return

        self._ao_clicar_linha_equipes_temporadas(row, _col)

        item_equipe = self.tabela_equipes_temporadas.item(row, 1)
        if item_equipe is None:
            return

        nome_equipe = str(item_equipe.text() or "").strip()
        chave_equipe = self._normalizar_chave_equipe_temporadas(
            item_equipe.data(BadgeResultadoDelegate.ROLE_EQUIPE_CHAVE) or nome_equipe
        )
        equipe_ref = next(
            (
                equipe
                for equipe in self.banco.get("equipes", [])
                if isinstance(equipe, dict)
                and self._normalizar_chave_equipe_temporadas(equipe.get("nome", "")) == chave_equipe
            ),
            None,
        )
        if not isinstance(equipe_ref, dict):
            QMessageBox.information(
                self,
                "Ficha indisponível",
                "Não foi possível localizar a equipe no banco atual.",
            )
            return

        try:
            from UI.fichas import FichaEquipe

            ficha = FichaEquipe(equipe_ref, self.banco, self)
            ficha.exec()
        except Exception as exc:
            print("[Historia] Falha ao abrir ficha da equipe:", exc)
            print(traceback.format_exc())
            QMessageBox.warning(
                self,
                "Ficha indisponível",
                "Não foi possível abrir a ficha da equipe.",
            )

    def _ao_duplo_clique_linha_temporadas(self, row: int, _col: int) -> None:
        self._ultimo_clique_linha_temporadas = -1
        self._ultimo_clique_ts_temporadas = 0.0
        self._abrir_ficha_piloto_linha_temporadas(row, _col)

    def _abrir_ficha_piloto_linha_temporadas(self, row: int, _col: int) -> None:
        agora = monotonic()
        if (agora - self._ultimo_open_ficha_piloto_ts) <= 0.25:
            return
        self._ultimo_open_ficha_piloto_ts = agora

        if row < 0 or row >= len(self._classificacao_temporadas_atual):
            return

        entrada = self._classificacao_temporadas_atual[row]
        self._ao_clicar_linha_temporadas(row, _col)
        piloto_ref = self._obter_piloto_referencia_temporada(entrada)
        if not isinstance(piloto_ref, dict):
            piloto_ref = self._criar_piloto_snapshot_temporada(entrada)
        if not isinstance(piloto_ref, dict):
            QMessageBox.information(
                self,
                "Ficha indisponível",
                "Não foi possível localizar o piloto no banco atual.",
            )
            return
        piloto_ref = self._enriquecer_piloto_ficha_temporada(piloto_ref, entrada, row)

        try:
            from UI.fichas import FichaPiloto

            try:
                ficha = FichaPiloto(piloto_ref, self.banco, self, tema="historia")
            except TypeError:
                ficha = FichaPiloto(piloto_ref, self.banco, self)
            ficha.exec()
        except Exception as exc:
            print("[Historia] Falha ao abrir ficha do piloto:", exc)
            print(traceback.format_exc())
            QMessageBox.warning(
                self,
                "Ficha indisponível",
                f"Não foi possível abrir a ficha do piloto.\n\nDetalhe: {exc}",
            )

    def _atualizar_tabela_temporadas(self):
        ano_texto = self.combo_ano.currentText()
        if not ano_texto:
            self.tabela_temporadas.clear()
            self.tabela_temporadas.setRowCount(0)
            self.tabela_temporadas.setColumnCount(0)
            if hasattr(self, "tabela_equipes_temporadas"):
                self.tabela_equipes_temporadas.clear()
                self.tabela_equipes_temporadas.setRowCount(0)
            self._classificacao_temporadas_atual = []
            return

        ano = int(ano_texto)
        categoria_nome = self.combo_categoria.currentText()

        categoria = next(
            (item for item in CATEGORIAS if item["nome"] == categoria_nome),
            None,
        )
        if not categoria:
            self.tabela_temporadas.clear()
            self.tabela_temporadas.setRowCount(0)
            self.tabela_temporadas.setColumnCount(0)
            if hasattr(self, "tabela_equipes_temporadas"):
                self.tabela_equipes_temporadas.clear()
                self.tabela_equipes_temporadas.setRowCount(0)
            self._classificacao_temporadas_atual = []
            return

        categoria_id = categoria["id"]
        historico = self.banco.get("historico_temporadas_completas", [])
        temporada = next(
            (
                item
                for item in historico
                if item.get("ano") == ano and item.get("categoria_id") == categoria_id
            ),
            None,
        )

        if not temporada:
            self.tabela_temporadas.clear()
            self.tabela_temporadas.setRowCount(0)
            self.tabela_temporadas.setColumnCount(0)
            if hasattr(self, "tabela_equipes_temporadas"):
                self.tabela_equipes_temporadas.clear()
                self.tabela_equipes_temporadas.setRowCount(0)
            self._classificacao_temporadas_atual = []
            return

        classificacao_bruta = temporada.get("classificacao", [])
        classificacao = self._ordenar_classificacao_por_desempenho_temporada(
            list(classificacao_bruta) if isinstance(classificacao_bruta, list) else []
        )
        self._classificacao_temporadas_atual = list(classificacao)
        num_corridas = max(
            [len(piloto.get("resultados", [])) for piloto in classificacao],
            default=12,
        )
        inicio_corridas = 4
        total_colunas = 4 + num_corridas + 2
        self.tabela_temporadas.clear()
        self.tabela_temporadas.setColumnCount(total_colunas)
        self.tabela_temporadas.setRowCount(len(classificacao))
        self.tabela_temporadas.setUpdatesEnabled(False)

        calendario_base = self.banco.get("calendario", [])
        if not isinstance(calendario_base, list):
            calendario_base = []

        headers = ["POS", "NAC", "IDADE", "PILOTO"]
        for indice_corrida in range(num_corridas):
            corrida = calendario_base[indice_corrida] if indice_corrida < len(calendario_base) else {}
            if not isinstance(corrida, dict):
                corrida = {}
            headers.append("")
        headers.extend(["PTS", "MEDALHAS"])
        self.tabela_temporadas.setHorizontalHeaderLabels(headers)

        header = self.tabela_temporadas.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)

        for indice_corrida in range(num_corridas):
            coluna = inicio_corridas + indice_corrida
            header.setSectionResizeMode(coluna, QHeaderView.Fixed)
            self.tabela_temporadas.setColumnWidth(coluna, 50)

        coluna_pts = inicio_corridas + num_corridas
        coluna_medalhas = coluna_pts + 1
        header.setSectionResizeMode(coluna_pts, QHeaderView.Fixed)
        header.setSectionResizeMode(coluna_medalhas, QHeaderView.Stretch)

        self.tabela_temporadas.setColumnWidth(0, 58)
        self.tabela_temporadas.setColumnWidth(1, 48)
        self.tabela_temporadas.setColumnWidth(2, 58)
        self.tabela_temporadas.setColumnWidth(3, 180)
        self.tabela_temporadas.setColumnWidth(coluna_pts, 60)
        self.tabela_temporadas.setColumnWidth(coluna_medalhas, 130)
        if isinstance(header, BandeiraHeaderView):
            header.limpar_bandeiras()

        for coluna, texto_header in enumerate(headers):
            item_header = QTableWidgetItem(texto_header)
            alinhamento_header = Qt.AlignCenter
            if coluna == 3:
                alinhamento_header = Qt.AlignVCenter | Qt.AlignLeft
            if coluna in {coluna_pts, coluna_medalhas}:
                alinhamento_header = Qt.AlignCenter
            item_header.setTextAlignment(alinhamento_header)
            if inicio_corridas <= coluna < inicio_corridas + num_corridas:
                rodada = coluna - inicio_corridas
                corrida = calendario_base[rodada] if rodada < len(calendario_base) else {}
                if not isinstance(corrida, dict):
                    corrida = {}
                circuito = str(corrida.get("circuito", "") or "").strip()
                codigo_bandeira = self._obter_codigo_bandeira_corrida_temporada(circuito, rodada)
                item_header.setText("")
                if isinstance(header, BandeiraHeaderView):
                    header.definir_bandeira_coluna(coluna, codigo_bandeira)
                else:
                    item_header.setText(obter_emoji_bandeira(codigo_bandeira, fallback="🏳️"))
                item_header.setToolTip(
                    f"Rodada {rodada + 1}: {circuito or 'Circuito indefinido'}"
                )
            self.tabela_temporadas.setHorizontalHeaderItem(coluna, item_header)

        jogador_atual = self._obter_jogador_atual()
        jogador_id = jogador_atual.get("id") if isinstance(jogador_atual, dict) else None
        nome_jogador_norm = (
            self._normalizar_nome(jogador_atual.get("nome", ""))
            if isinstance(jogador_atual, dict)
            else ""
        )
        ids_destaque, nomes_destaque, equipe_chave_destacada = (
            self._obter_contexto_destaque_equipes_temporadas(
                self._classificacao_temporadas_atual
            )
        )
        cor_equipe_destacada = str(self._cor_equipe_destacada_temporadas or HIST_ACCENT)
        if not cor_equipe_destacada or not QColor(cor_equipe_destacada).isValid():
            cor_equipe_destacada = HIST_ACCENT
        cor_linha_jogador = "#3a2c2a"
        chaves_rivais = self._obter_chaves_rivais_mock_temporadas(
            self._classificacao_temporadas_atual
        )
        trofeus_equipes = self._obter_trofeus_equipes_temporadas(
            categoria_id,
            ano_limite=ano,
        )
        trofeus_equipes_ano_anterior = self._obter_trofeus_equipes_temporadas(
            categoria_id,
            ano_limite=ano - 1,
        )
        ano_anterior = ano - 1 if ano > 0 else None
        chave_campeao_pilotos_anterior = self._obter_chave_campeao_pilotos_ano_temporadas(
            categoria_id,
            ano_anterior,
        )
        podio_construtores_anterior = self._obter_podio_construtores_ano_temporadas(
            categoria_id,
            ano_anterior,
        )
        pontos_equipes = self._obter_pontos_equipes_temporadas(classificacao)
        self._mapa_vmr_rodada_temporadas = self._mapear_vmr_por_rodada_temporada(
            classificacao,
            temporada,
            ano,
            categoria_id,
            num_corridas,
        )

        equipes_por_nome = {
            str(equipe.get("nome", "")).strip().casefold(): equipe
            for equipe in self.banco.get("equipes", [])
            if isinstance(equipe, dict)
        }

        try:
            for row, piloto in enumerate(classificacao):
                self.tabela_temporadas.setRowHeight(row, 30)

                posicao = row + 1
                piloto_id = piloto.get("piloto_id")
                piloto_id_norm = self._normalizar_id(piloto_id)
                nome_piloto = str(piloto.get("piloto", ""))
                nome_piloto_norm = self._normalizar_nome(nome_piloto)
                is_jogador = (
                    (jogador_id is not None and self._ids_equivalentes(piloto_id, jogador_id))
                    or self._normalizar_nome(nome_piloto) == nome_jogador_norm
                )
                is_piloto_origem = (
                    (self._piloto_id_destacado_temporadas is not None and self._ids_equivalentes(piloto_id, self._piloto_id_destacado_temporadas))
                    or (
                        self._piloto_id_destacado_temporadas is None
                        and self._piloto_nome_destacado_temporadas
                        and nome_piloto_norm == self._piloto_nome_destacado_temporadas
                    )
                )

                equipe_nome = str(piloto.get("equipe", "-"))
                equipe_chave = self._normalizar_chave_equipe_temporadas(equipe_nome)
                equipe_ref = equipes_por_nome.get(equipe_chave)
                cor_equipe = (
                    str(equipe_ref.get("cor_primaria", HIST_TEXT_SECONDARY))
                    if isinstance(equipe_ref, dict)
                    else HIST_TEXT_SECONDARY
                )

                linha_equipe_destacada = bool(
                    equipe_chave_destacada and equipe_chave == equipe_chave_destacada
                )
                em_destaque = (
                    (piloto_id_norm and piloto_id_norm in ids_destaque)
                    or (nome_piloto_norm and nome_piloto_norm in nomes_destaque)
                )

                if linha_equipe_destacada:
                    cor_base = (
                        cor_linha_jogador
                        if is_jogador
                        else (HIST_BG_CARD if row % 2 == 0 else HIST_BG_APP)
                    )
                    cor_fundo = self._cor_destaque_por_equipe_temporadas(
                        cor_base,
                        cor_equipe_destacada,
                        alpha=76,
                    )
                elif em_destaque:
                    cor_fundo = self._cor_destaque_por_equipe_temporadas(
                        "#3f2a24",
                        cor_equipe_destacada,
                        alpha=76,
                    )
                elif is_jogador:
                    cor_fundo = cor_linha_jogador
                elif row % 2 == 0:
                    cor_fundo = HIST_BG_CARD
                else:
                    cor_fundo = HIST_BG_APP

                linha_destacada = linha_equipe_destacada or em_destaque

                if posicao == 1:
                    cor_posicao = Cores.OURO
                elif posicao == 2:
                    cor_posicao = Cores.PRATA
                elif posicao == 3:
                    cor_posicao = Cores.BRONZE
                else:
                    cor_posicao = HIST_TEXT_PRIMARY

                item_posicao = self._criar_item(
                    str(posicao),
                    cor_texto="#ffffff" if linha_destacada else cor_posicao,
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignCenter,
                    negrito=True,
                )
                self.tabela_temporadas.setItem(row, 0, item_posicao)

                piloto_ref = self._obter_piloto_referencia_temporada(piloto)
                codigo_bandeira_nac = self._obter_codigo_bandeira_nacionalidade_temporada(
                    piloto,
                    piloto_ref,
                )
                idade = self._obter_idade_exibicao_temporada(piloto_ref, ano)
                emoji_nacionalidade = obter_emoji_bandeira(codigo_bandeira_nac, fallback="🏳️")

                item_nac = self._criar_item(
                    emoji_nacionalidade,
                    cor_texto="#ffffff" if linha_destacada else HIST_TEXT_PRIMARY,
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignCenter,
                )
                fonte_nac = item_nac.font()
                fonte_nac.setFamily("Segoe UI Emoji")
                item_nac.setFont(fonte_nac)
                item_nac.setData(
                    BadgeResultadoDelegate.ROLE_BANDEIRA_CODIGO,
                    codigo_bandeira_nac,
                )
                self.tabela_temporadas.setItem(row, 1, item_nac)

                item_idade = self._criar_item(
                    idade,
                    cor_texto="#ffffff" if linha_destacada else HIST_TEXT_SECONDARY,
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignCenter,
                )
                self.tabela_temporadas.setItem(row, 2, item_idade)

                titulos_historicos = self._contar_titulos_historicos_piloto_temporadas(
                    piloto,
                    categoria_id,
                    ano_limite=ano - 1,
                )
                chave_hist_piloto = self._chave_piloto_historico_temporadas(
                    piloto.get("piloto_id"),
                    nome_piloto,
                )
                foi_campeao_anterior = bool(
                    chave_campeao_pilotos_anterior
                    and chave_hist_piloto
                    and chave_hist_piloto == chave_campeao_pilotos_anterior
                )
                nome_exibicao = f"⭐ {nome_piloto}" if is_jogador else nome_piloto
                if titulos_historicos > 0:
                    nome_exibicao = f"{nome_exibicao}   x{titulos_historicos}"
                negrito_piloto = bool(posicao <= 3 or is_jogador)
                if linha_destacada:
                    negrito_piloto = is_piloto_origem
                item_piloto = self._criar_item(
                    nome_exibicao,
                    cor_texto="#ffffff" if linha_destacada else cor_posicao,
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignVCenter | Qt.AlignLeft,
                    negrito=negrito_piloto,
                )
                item_piloto.setData(
                    BadgeResultadoDelegate.ROLE_INLINE_PREFIX,
                    {
                        "cor_fundo": cor_equipe,
                        "cor_borda": "#333333",
                        "tamanho": 9,
                        "gap": 6,
                    },
                )
                item_piloto.setData(BadgeResultadoDelegate.ROLE_EQUIPE_CHAVE, equipe_chave)
                item_piloto.setData(BadgeResultadoDelegate.ROLE_EQUIPE_COR, cor_equipe)
                if is_piloto_origem and linha_destacada:
                    fonte_origem = item_piloto.font()
                    fonte_origem.setBold(True)
                    tamanho_origem = (
                        fonte_origem.pointSizeF()
                        if fonte_origem.pointSizeF() > 0
                        else float(fonte_origem.pointSize())
                    )
                    fonte_origem.setPointSizeF(max(8.7, tamanho_origem + 0.5))
                    item_piloto.setFont(fonte_origem)
                chave_entrada = self._chave_entrada_piloto_temporada(piloto)
                sufixos: list[dict[str, Any]] = []
                if (not is_jogador) and chave_entrada and chave_entrada in chaves_rivais:
                    sufixos.append({"texto": "🔥", "cor_texto": "#f97316", "gap": 6})
                payload_sufixo: dict[str, Any] = {}
                if sufixos:
                    payload_sufixo["itens"] = sufixos
                if foi_campeao_anterior:
                    payload_sufixo["seta_sobre_trofeu"] = True
                    payload_sufixo["cor_seta_sobre_trofeu"] = "#22c55e"
                    item_piloto.setToolTip("Campeão da temporada anterior")
                if payload_sufixo:
                    item_piloto.setData(
                        BadgeResultadoDelegate.ROLE_INLINE_SUFFIX,
                        payload_sufixo,
                    )
                self.tabela_temporadas.setItem(row, 3, item_piloto)

                resultados = piloto.get("resultados", [])
                for indice_corrida in range(num_corridas):
                    coluna = inicio_corridas + indice_corrida

                    resultado = resultados[indice_corrida] if indice_corrida < len(resultados) else None
                    (
                        texto_resultado,
                        cor_resultado,
                        cor_badge_resultado,
                        cor_borda_resultado,
                        negrito_resultado,
                    ) = self._formatar_resultado_heatmap_temporada(resultado)
                    marcador_vmr = self._obter_marcadores_evento_mock_temporada(
                        piloto,
                        indice_corrida,
                        ano,
                        categoria_id,
                        resultado,
                    )

                    item_resultado = self._criar_item(
                        texto_resultado,
                        cor_texto=cor_resultado,
                        cor_fundo=cor_fundo,
                        alinhamento=Qt.AlignCenter,
                        negrito=negrito_resultado,
                    )
                    item_resultado.setData(
                        BadgeResultadoDelegate.ROLE_BADGE,
                        {
                            "texto": texto_resultado,
                            "cor_texto": cor_resultado,
                            "cor_fundo": cor_badge_resultado,
                            "cor_borda": cor_borda_resultado,
                            "negrito": negrito_resultado,
                            "marcador_vmr": marcador_vmr,
                        },
                    )
                    self.tabela_temporadas.setItem(row, coluna, item_resultado)

                pontos_piloto = self._safe_int(piloto.get("pontos"), default=0)
                cor_pts = (
                    "#ffffff" if linha_destacada or pontos_piloto > 0 else "#555555"
                )
                item_pontos = self._criar_item(
                    pontos_piloto,
                    cor_texto=cor_pts,
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignCenter,
                    negrito=linha_destacada or pontos_piloto > 0,
                )
                fonte_pontos = item_pontos.font()
                tamanho_base = fonte_pontos.pointSizeF() if fonte_pontos.pointSizeF() > 0 else float(fonte_pontos.pointSize())
                incremento = 0.4
                if posicao == 1:
                    incremento = 1.6
                elif posicao == 2:
                    incremento = 1.2
                elif posicao == 3:
                    incremento = 0.8
                fonte_pontos.setPointSizeF(max(8.5, tamanho_base + incremento))
                item_pontos.setFont(fonte_pontos)
                self.tabela_temporadas.setItem(row, coluna_pts, item_pontos)

                medalhas = self._montar_medalhas_resultados_temporada(resultados)
                item_medalhas = self._criar_item(
                    medalhas,
                    cor_texto=(
                        "#ffffff"
                        if linha_destacada
                        else (HIST_TEXT_PRIMARY if medalhas != "—" else "#555555")
                    ),
                    cor_fundo=cor_fundo,
                    alinhamento=Qt.AlignCenter,
                )
                self.tabela_temporadas.setItem(row, coluna_medalhas, item_medalhas)
        finally:
            self.tabela_temporadas.setUpdatesEnabled(True)

        if hasattr(self, "tabela_equipes_temporadas"):
            max_ouro = 0
            for info_trofeus in trofeus_equipes.values():
                if not isinstance(info_trofeus, dict):
                    continue
                max_ouro = max(max_ouro, int(info_trofeus.get("ouro", 0) or 0))

            equipes_ordenadas = sorted(
                (
                    {
                        "nome": nome,
                        "pontos": pontos,
                    }
                    for nome, pontos in pontos_equipes.items()
                ),
                key=lambda item: (-int(item.get("pontos", 0)), str(item.get("nome", "")).casefold()),
            )

            self.tabela_equipes_temporadas.setUpdatesEnabled(False)
            try:
                self.tabela_equipes_temporadas.setRowCount(len(equipes_ordenadas))
                for row, equipe in enumerate(equipes_ordenadas):
                    pos = row + 1
                    self.tabela_equipes_temporadas.setRowHeight(row, 32)

                    nome_equipe = str(equipe.get("nome", "") or "")
                    nome_equipe_chave = self._normalizar_chave_equipe_temporadas(nome_equipe)
                    pontos_equipe = self._safe_int(equipe.get("pontos"), default=0)
                    equipe_ref = equipes_por_nome.get(nome_equipe_chave)
                    cor_equipe = (
                        str(equipe_ref.get("cor_primaria", HIST_TEXT_PRIMARY))
                        if isinstance(equipe_ref, dict)
                        else HIST_TEXT_PRIMARY
                    )

                    if pos <= 3:
                        cor_base = "#1a3a2a"
                    elif pos % 2 == 0:
                        cor_base = HIST_BG_CARD
                    else:
                        cor_base = HIST_BG_APP

                    linha_destacada = bool(
                        equipe_chave_destacada
                        and nome_equipe_chave == equipe_chave_destacada
                    )
                    if linha_destacada:
                        cor_fundo = self._cor_destaque_por_equipe_temporadas(
                            cor_base,
                            cor_equipe_destacada,
                            alpha=48,
                        )
                    else:
                        cor_fundo = cor_base

                    if pos == 1:
                        cor_pos = Cores.OURO
                    elif pos == 2:
                        cor_pos = Cores.PRATA
                    elif pos == 3:
                        cor_pos = Cores.BRONZE
                    else:
                        cor_pos = HIST_TEXT_PRIMARY
                    if linha_destacada:
                        cor_pos = "#ffffff"

                    self.tabela_equipes_temporadas.setItem(
                        row,
                        0,
                        self._criar_item(
                            str(pos),
                            cor_texto=cor_pos,
                            cor_fundo=cor_fundo,
                            alinhamento=Qt.AlignCenter,
                            negrito=True,
                        ),
                    )
                    self.tabela_equipes_temporadas.setItem(
                        row,
                        1,
                        self._criar_item(
                            nome_equipe or "?",
                            cor_texto="#ffffff" if linha_destacada else cor_equipe,
                            cor_fundo=cor_fundo,
                            alinhamento=Qt.AlignVCenter | Qt.AlignLeft,
                            negrito=linha_destacada,
                        ),
                    )
                    item_equipe = self.tabela_equipes_temporadas.item(row, 1)
                    if item_equipe is not None:
                        item_equipe.setData(BadgeResultadoDelegate.ROLE_EQUIPE_CHAVE, nome_equipe_chave)
                        item_equipe.setData(BadgeResultadoDelegate.ROLE_EQUIPE_COR, cor_equipe)

                    cor_pts_equipe = "#ffffff" if linha_destacada else (cor_pos if pontos_equipe > 0 else "#555555")
                    self.tabela_equipes_temporadas.setItem(
                        row,
                        2,
                        self._criar_item(
                            str(pontos_equipe),
                            cor_texto=cor_pts_equipe,
                            cor_fundo=cor_fundo,
                            alinhamento=Qt.AlignCenter,
                            negrito=linha_destacada or pontos_equipe > 0,
                        ),
                    )
                    item_pts = self.tabela_equipes_temporadas.item(row, 2)
                    if item_pts is not None:
                        fonte_pts = item_pts.font()
                        tamanho_base = fonte_pts.pointSizeF() if fonte_pts.pointSizeF() > 0 else float(fonte_pts.pointSize())
                        incremento = 0.5
                        if pos == 1:
                            incremento = 1.3
                        elif pos == 2:
                            incremento = 1.0
                        elif pos == 3:
                            incremento = 0.8
                        fonte_pts.setPointSizeF(max(8.5, tamanho_base + incremento))
                        item_pts.setFont(fonte_pts)

                    trofeus_base = trofeus_equipes.get(
                        nome_equipe_chave,
                        {"ouro": 0, "prata": 0, "bronze": 0},
                    )
                    trofeus_prev = trofeus_equipes_ano_anterior.get(
                        nome_equipe_chave,
                        {"ouro": 0, "prata": 0, "bronze": 0},
                    )
                    ganhos = {
                        "ouro": max(
                            0,
                            int(trofeus_base.get("ouro", 0) or 0)
                            - int(trofeus_prev.get("ouro", 0) or 0),
                        ),
                        "prata": max(
                            0,
                            int(trofeus_base.get("prata", 0) or 0)
                            - int(trofeus_prev.get("prata", 0) or 0),
                        ),
                        "bronze": max(
                            0,
                            int(trofeus_base.get("bronze", 0) or 0)
                            - int(trofeus_prev.get("bronze", 0) or 0),
                        ),
                    }
                    trofeus_info = {
                        "ouro": int(trofeus_base.get("ouro", 0) or 0),
                        "prata": int(trofeus_base.get("prata", 0) or 0),
                        "bronze": int(trofeus_base.get("bronze", 0) or 0),
                        "ganhos": ganhos,
                        "setas_tipos": {
                            "ouro": bool(
                                podio_construtores_anterior.get("ouro")
                                and nome_equipe_chave == podio_construtores_anterior.get("ouro")
                            ),
                            "prata": bool(
                                podio_construtores_anterior.get("prata")
                                and nome_equipe_chave == podio_construtores_anterior.get("prata")
                            ),
                            "bronze": bool(
                                podio_construtores_anterior.get("bronze")
                                and nome_equipe_chave == podio_construtores_anterior.get("bronze")
                            ),
                        },
                        "lider_ouro": (
                            max_ouro > 0
                            and int(trofeus_base.get("ouro", 0) or 0) == max_ouro
                        ),
                    }
                    item_trofeus = self._criar_item(
                        "",
                        cor_texto="#ffffff" if linha_destacada else HIST_TEXT_PRIMARY,
                        cor_fundo=cor_fundo,
                        alinhamento=Qt.AlignCenter,
                    )
                    partes_ganho = []
                    if ganhos["ouro"] > 0:
                        partes_ganho.append(f"Ouro +{ganhos['ouro']}")
                    if ganhos["prata"] > 0:
                        partes_ganho.append(f"Prata +{ganhos['prata']}")
                    if ganhos["bronze"] > 0:
                        partes_ganho.append(f"Bronze +{ganhos['bronze']}")
                    if partes_ganho:
                        item_trofeus.setToolTip(
                            "Troféus ganhos vs ano anterior: " + " | ".join(partes_ganho)
                        )
                    partes_podio_anterior = []
                    setas_tipos_info = trofeus_info["setas_tipos"]
                    if setas_tipos_info.get("ouro"):
                        partes_podio_anterior.append("ouro (campeã)")
                    if setas_tipos_info.get("prata"):
                        partes_podio_anterior.append("prata (vice)")
                    if setas_tipos_info.get("bronze"):
                        partes_podio_anterior.append("bronze (3ª)")
                    if partes_podio_anterior:
                        texto_podio = "Pódio de construtores no ano anterior: " + ", ".join(partes_podio_anterior)
                        if partes_ganho:
                            texto_atual = str(item_trofeus.toolTip() or "").strip()
                            item_trofeus.setToolTip(texto_atual + "\n" + texto_podio)
                        else:
                            item_trofeus.setToolTip(texto_podio)
                    item_trofeus.setData(BadgeResultadoDelegate.ROLE_TROFEUS_INFO, trofeus_info)
                    self.tabela_equipes_temporadas.setItem(row, 3, item_trofeus)
            finally:
                self.tabela_equipes_temporadas.setUpdatesEnabled(True)


