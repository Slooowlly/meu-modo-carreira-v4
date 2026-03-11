"""
Tela principal da carreira - Dashboard
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import unicodedata
from queue import Empty, Queue
from math import ceil
from typing import Any

from PySide6.QtCore import (
    QObject,
    Qt,
    Signal,
    QEvent,
    QEasingCurve,
    QPoint,
    QRect,
    QSize,
    QPropertyAnimation,
    QVariantAnimation,
    QTimer,
)
from PySide6.QtGui import QColor, QBrush, QCloseEvent, QCursor, QFont, QPainter, QPixmap, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QGraphicsOpacityEffect,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QStyledItemDelegate,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from UI.temas import Cores, Fontes, Espacos, Estilos
from UI.componentes import (
    BarraProgresso,
    BotaoDanger,
    BotaoPrimary,
    BotaoSecondary,
    BotaoSuccess,
    Card,
    CardStat,
    CardTitulo,
    LinhaInfo,
    Separador,
)

from UI.carreira_acoes_exportar import ExportarImportarMixin
from UI.carreira_acoes_simular import SimularMixin
from UI.carreira_acoes_temporada import TemporadaMixin
from UI.carreira_acoes_config import ConfigMixin
from UI.carreira_acoes_mercado import MercadoMixin

from UI.ux_helpers import UXMixin, SimulacaoUXMixin, DashboardUXMixin

from Dados.constantes import CATEGORIAS, NOMES_CAMPEONATO, PONTOS_POR_POSICAO
from Dados.banco import carregar_banco, salvar_banco
from Logica.pilotos import (
    obter_pilotos_categoria,
    sanear_distribuicao_pilotos_categoria,
)
from Logica.equipes import (
    calcular_pontos_equipes,
    obter_classificacao_equipes,
    obter_equipe_piloto,
    obter_equipes_categoria,
)
from Logica.noticias import listar_noticias_ordenadas
from Logica.expectativas import (
    avaliar_desempenho_vs_expectativa,
    calcular_expectativa_equipe,
    obter_classificacao_categoria,
    registrar_avaliacao_historico,
)
from Logica.contrato_alertas import (
    gerar_alerta_contratual,
    registrar_alerta_contratual,
)
from Utils.helpers import obter_nome_categoria
from Utils.bandeiras import (
    CODIGOS_BANDEIRAS_SUPORTADOS,
    obter_emoji_bandeira,
    obter_codigo_bandeira,
    obter_codigo_bandeira_circuito,
    obter_pasta_bandeiras_absoluta,
)
from UI.widgets.bandeira_widget import BandeiraLabel
from UI.widgets.bandeira_header import BandeiraHeaderView
from Logica.series_especiais import (
    inicializar_production_car_challenge,
    obter_proximo_evento_exibicao,
    sincronizar_production_car_challenge,
)


BRIEFINGS_CIRCUITO = {
    "Summit Point Raceway": (
        "Circuito curto e tecnico. Poucas oportunidades de ultrapassagem. "
        "Consistencia e tracao em saida valem muito."
    ),
    "Lime Rock Park": (
        "Circuito rapido e fluido, com pouca margem para erro. "
        "Gestao de pneus e coragem em curva de alta fazem diferenca."
    ),
    "Spa-Francorchamps": (
        "Um dos circuitos mais exigentes do calendario. "
        "Setores de alta e clima imprevisivel cobram adaptacao constante."
    ),
    "Watkins Glen": (
        "Trecho misto, alternando curvas lentas e sequencias rapidas. "
        "Bom compromisso de acerto costuma decidir as disputas."
    ),
    "_default": "Circuito desafiador. Prepare-se para uma corrida competitiva.",
}


class BadgeHeatmapDelegate(QStyledItemDelegate):
    ROLE_BADGE = Qt.UserRole + 31
    ROLE_POS_TENDENCIA = Qt.UserRole + 32
    ROLE_INLINE_SUFFIX = Qt.UserRole + 33
    ROLE_SEPARADOR_ESQ = Qt.UserRole + 34
    ROLE_EQUIPE_INFO = Qt.UserRole + 35
    ROLE_INLINE_PREFIX = Qt.UserRole + 36
    ROLE_TROFEUS_INFO = Qt.UserRole + 37
    ROLE_EQUIPE_CHAVE = Qt.UserRole + 38
    ROLE_EQUIPE_COR = Qt.UserRole + 39
    ROLE_BANDEIRA_CODIGO = Qt.UserRole + 40
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

    def paint(self, painter: QPainter, option, index):
        payload = index.data(self.ROLE_BADGE)

        painter.save()
        fundo_item = index.data(Qt.BackgroundRole)
        if isinstance(fundo_item, QBrush):
            painter.fillRect(option.rect, fundo_item)
        elif isinstance(fundo_item, QColor):
            painter.fillRect(option.rect, fundo_item)
        else:
            painter.fillRect(option.rect, QColor(Cores.FUNDO_CARD))

        if bool(index.data(self.ROLE_SEPARADOR_ESQ)):
            painter.fillRect(
                QRect(option.rect.left(), option.rect.top() + 1, 2, max(1, option.rect.height() - 2)),
                QColor("#334155"),
            )

        if not isinstance(payload, dict):
            texto = str(index.data(Qt.DisplayRole) or "")
            alinhamento = index.data(Qt.TextAlignmentRole)
            if not isinstance(alinhamento, int):
                alinhamento = int(Qt.AlignVCenter | Qt.AlignLeft)

            cor_texto = QColor(Cores.TEXTO_PRIMARY)
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
                trofeus_raw = payload_equipe.get("trofeus", {})
                trofeus = trofeus_raw if isinstance(trofeus_raw, dict) else {}

                area = option.rect.adjusted(6, 0, -6, 0)
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
                gap_icone = 3
                gap_grupo = 10
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
                setas_tipos_raw = trofeus.get("setas_tipos", {})
                if isinstance(setas_tipos_raw, dict):
                    setas_tipos = {
                        "ouro": bool(setas_tipos_raw.get("ouro", False)),
                        "prata": bool(setas_tipos_raw.get("prata", False)),
                        "bronze": bool(setas_tipos_raw.get("bronze", False)),
                    }
                else:
                    campeao_anterior = bool(trofeus.get("campeao_anterior", False))
                    setas_tipos = {
                        "ouro": campeao_anterior,
                        "prata": False,
                        "bronze": False,
                    }
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

                # Slots fixos por categoria para manter alinhamento entre linhas.
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

                    if setas_tipos.get(tipo, False):
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
                        painter.drawText(rect_seta, Qt.AlignCenter, "\u25B2")
                    cursor_x += largura_grupo + gap_grupo

                painter.restore()
                return

            payload_tendencia = index.data(self.ROLE_POS_TENDENCIA)
            if isinstance(payload_tendencia, dict):
                estado = str(payload_tendencia.get("estado", "flat")).strip().lower()
                if estado == "up":
                    indicador = "\u25B2"
                    cor_indicador = QColor("#22c55e")
                elif estado == "up2":
                    indicador = "▲▲"
                    cor_indicador = QColor("#22c55e")
                elif estado == "down":
                    indicador = "\u25BC"
                    cor_indicador = QColor("#ef4444")
                elif estado == "down2":
                    indicador = "▼▼"
                    cor_indicador = QColor("#ef4444")
                else:
                    indicador = "–"
                    cor_indicador = QColor("#64748b")

                area = option.rect.adjusted(6, 0, -6, 0)
                largura_indicador = 16
                rect_indicador = QRect(
                    area.right() - largura_indicador + 1,
                    area.top(),
                    largura_indicador,
                    area.height(),
                )
                rect_numero = QRect(
                    area.left(),
                    area.top(),
                    max(8, area.width() - largura_indicador - 2),
                    area.height(),
                )

                painter.setFont(fonte)
                painter.setPen(cor_texto)
                painter.drawText(rect_numero, Qt.AlignVCenter | Qt.AlignHCenter, texto)

                fonte_indicador = QFont(fonte)
                fonte_indicador.setBold(True)
                painter.setFont(fonte_indicador)
                painter.setPen(cor_indicador)
                painter.drawText(rect_indicador, Qt.AlignCenter, indicador)
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
                        texto_sufixo = str(payload_suffix.get("texto", "") or "").strip()
                        if texto_sufixo:
                            sufixos.append(
                                (
                                    texto_sufixo,
                                    QColor(str(payload_suffix.get("cor_texto", "#f97316"))),
                                    int(payload_suffix.get("gap", 6)),
                                )
                            )

                prefix_tamanho = 0
                gap_prefix = 6
                cor_prefix = QColor("#64748b")
                cor_prefix_borda = QColor("#0f172a")
                if isinstance(payload_prefix, dict):
                    prefix_tamanho = int(payload_prefix.get("tamanho", 9))
                    prefix_tamanho = max(6, min(12, prefix_tamanho))
                    gap_prefix = int(payload_prefix.get("gap", 6))
                    cor_prefix = QColor(str(payload_prefix.get("cor_fundo", "#64748b")))
                    cor_prefix_borda = QColor(str(payload_prefix.get("cor_borda", "#0f172a")))

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
                        tamanho_trofeu = max(14, min(rect_base.height() - 2, largura_trofeu + 6))
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
                    else:
                        x_trofeu_draw = None

                if seta_sobre_trofeu:
                    if x_trofeu >= 0 and largura_trofeu > 0:
                        fonte_seta = QFont(fonte)
                        tamanho_seta = fonte_seta.pointSizeF()
                        if tamanho_seta <= 0:
                            tamanho_seta = float(fonte_seta.pointSize())
                        fonte_seta.setPointSizeF(max(6.6, tamanho_seta - 1.5))
                        fonte_seta.setBold(True)
                        painter.setFont(fonte_seta)
                        painter.setPen(cor_seta_sobre_trofeu)
                        
                        if 'pixmap_trofeu_escalado' in locals() and x_trofeu_draw is not None:
                            x_seta = x_trofeu_draw + max(0, tamanho_trofeu - 8)
                            y_seta = rect_base.top() + 1
                        else:
                            x_seta = x_trofeu + max(0, largura_trofeu - 8)
                            y_seta = rect_base.top() + 1

                        rect_seta_trofeu = QRect(
                            x_seta,
                            y_seta,
                            10,
                            10,
                        )
                        painter.drawText(rect_seta_trofeu, Qt.AlignCenter, "\u25B2")
                    else:
                        fonte_seta = QFont(fonte)
                        tamanho_seta = fonte_seta.pointSizeF()
                        if tamanho_seta <= 0:
                            tamanho_seta = float(fonte_seta.pointSize())
                        fonte_seta.setPointSizeF(max(6.6, tamanho_seta - 1.5))
                        fonte_seta.setBold(True)
                        painter.setFont(fonte_seta)
                        painter.setPen(cor_seta_sobre_trofeu)
                        
                        x_seta = rect_base.left() + metricas.horizontalAdvance(texto_base) + 2
                        rect_seta = QRect(
                            x_seta,
                            rect_base.top() + (rect_base.height() - 9) // 2,
                            9,
                            9,
                        )
                        painter.drawText(rect_seta, Qt.AlignCenter, "\u25B2")
                        
                        if sufixos:
                            # Adjust suffixes if we added the arrow after the name
                            x_sufixo += 11

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

        texto = str(payload.get("texto", ""))
        cor_texto = str(payload.get("cor_texto", Cores.TEXTO_PRIMARY))
        cor_fundo = str(payload.get("cor_fundo", "#1e293b"))
        cor_borda = str(payload.get("cor_borda", "#2d3a4f"))
        negrito = bool(payload.get("negrito", False))
        texto_reduzido = bool(payload.get("texto_reduzido", False))
        marcador_vmr = bool(payload.get("marcador_vmr", False))

        fonte = option.font
        fonte.setBold(negrito)
        if texto_reduzido:
            tamanho = fonte.pointSizeF() if fonte.pointSizeF() > 0 else float(fonte.pointSize())
            fonte.setPointSizeF(max(7.0, tamanho - 1.0))
        painter.setFont(fonte)

        # Mesmo molde da tabela de temporadas: bloco retangular, quase sem arredondamento.
        badge_rect = option.rect.adjusted(1, 4, -1, -4)
        painter.setPen(QColor(cor_borda))
        painter.setBrush(QColor(cor_fundo))
        painter.drawRect(badge_rect.adjusted(0, 0, -1, -1))
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


class _MonitorResultadosSignals(QObject):
    """Sinais para encaminhar eventos do watchdog para a thread da UI."""

    resultado_detectado = Signal(str)
    resultado_detectado_sync = Signal(str, object)


class TelaCarreira(
    QMainWindow,
    ExportarImportarMixin,
    SimularMixin,
    TemporadaMixin,
    MercadoMixin,
    ConfigMixin,
    UXMixin,
    SimulacaoUXMixin,
    DashboardUXMixin,
):
    """Dashboard principal da carreira."""

    def __init__(self, banco=None):
        super().__init__()

        self.banco = banco if banco is not None else carregar_banco()
        self.categoria_atual = "mazda_rookie"

        ano_atual = int(self.banco.get("ano_atual", 2024))
        temporadas_pcc = (
            self.banco.get("series_especiais", {})
            .get("production_car_challenge", {})
            .get("temporadas", {})
        )
        if str(ano_atual) not in temporadas_pcc:
            inicializar_production_car_challenge(self.banco, ano_atual)
            salvar_banco(self.banco)
        elif sincronizar_production_car_challenge(self.banco):
            salvar_banco(self.banco)

        self.pilotos_ordenados: list[dict[str, Any]] = []
        self.equipes_ordenadas: list[dict[str, Any]] = []
        self._piloto_id_destacado_tabela: Any = None
        self._destacar_somente_piloto_tabela: bool = False
        self._equipe_chave_destacada_tabela: str = ""
        self._cor_equipe_destacada_tabela: str = ""
        self._rw_etapa_atual: int = 0
        self._rw_quali_resultado: list[dict[str, Any]] = []
        self._rw_roster_exportado: bool = False
        self._rw_resultado_dialogo: dict[str, Any] = {}
        self._monitor_iracing = None
        self._monitor_signals = _MonitorResultadosSignals(self)
        self._monitor_signals.resultado_detectado_sync.connect(
            self._ao_resultado_detectado_monitor_sync,
            Qt.QueuedConnection,
        )

        jogador = self._obter_jogador()
        if jogador:
            self.categoria_atual = jogador.get("categoria_atual", "mazda_rookie")

        ajustes_grid = sanear_distribuicao_pilotos_categoria(
            self.banco,
            self.categoria_atual,
        )

        precisa_hierarquia_inicial = any(
            isinstance(equipe, dict)
            and bool(equipe.get("ativa", True))
            and isinstance(equipe.get("pilotos"), list)
            and len(equipe.get("pilotos", [])) == 2
            and not isinstance(equipe.get("hierarquia"), dict)
            for equipe in self.banco.get("equipes", [])
        )
        if precisa_hierarquia_inicial:
            self._inicializar_hierarquias(self.banco)

        if ajustes_grid or precisa_hierarquia_inicial:
            salvar_banco(self.banco)

        self.setWindowTitle("🏁 Modo Carreira")
        self.setMinimumSize(1100, 750)
        self.resize(1250, 900)
        self.setStyleSheet(Estilos.janela_principal() + Estilos.tooltip())
        self._fixar_tela_cheia = True

        self._build_ui()
        self._configurar_controles_fullscreen()
        self._configurar_atalhos()
        self._setup_ux()
        self._atualizar_tudo(animar=True)
        self._iniciar_monitor_resultados()

    # ============================================================
    # FALLBACKS / BASE
    # ============================================================

    def _delegar_mixin(self, mixin_cls, nome_metodo: str, *args, **kwargs):
        metodo = getattr(mixin_cls, nome_metodo, None)
        if callable(metodo):
            return metodo(self, *args, **kwargs)

        QMessageBox.warning(
            self,
            "Aviso",
            f"A ação '{nome_metodo}' não está disponível no momento.",
        )
        return None

    def _configurar_controles_fullscreen(self):
        self._barra_controles_fullscreen = QFrame(self)
        self._barra_controles_fullscreen.setObjectName("barra_controles_fullscreen")
        self._barra_controles_fullscreen.setFixedSize(132, 34)
        self._barra_controles_fullscreen.setStyleSheet(
            """
            QFrame#barra_controles_fullscreen {
                background-color: rgba(12, 18, 29, 0.92);
                border: 1px solid #34445a;
                border-radius: 9px;
            }
            """
        )

        barra_layout = QHBoxLayout(self._barra_controles_fullscreen)
        barra_layout.setContentsMargins(5, 4, 5, 4)
        barra_layout.setSpacing(4)

        self._btn_janela_modo = QPushButton("🗗", self._barra_controles_fullscreen)
        self._btn_janela_modo.setObjectName("btn_janela_modo")
        self._btn_janela_modo.setCursor(Qt.PointingHandCursor)
        self._btn_janela_modo.setFixedSize(38, 24)
        self._btn_janela_modo.clicked.connect(self._alternar_modo_janela)

        self._btn_minimizar_fullscreen = QPushButton("—", self._barra_controles_fullscreen)
        self._btn_minimizar_fullscreen.setObjectName("btn_minimizar_fullscreen")
        self._btn_minimizar_fullscreen.setCursor(Qt.PointingHandCursor)
        self._btn_minimizar_fullscreen.setFixedSize(38, 24)
        self._btn_minimizar_fullscreen.clicked.connect(self.showMinimized)

        self._btn_fechar_fullscreen = QPushButton("✕", self._barra_controles_fullscreen)
        self._btn_fechar_fullscreen.setObjectName("btn_fechar_fullscreen")
        self._btn_fechar_fullscreen.setCursor(Qt.PointingHandCursor)
        self._btn_fechar_fullscreen.setFixedSize(38, 24)
        self._btn_fechar_fullscreen.clicked.connect(self.close)

        for botao in (
            self._btn_janela_modo,
            self._btn_minimizar_fullscreen,
            self._btn_fechar_fullscreen,
        ):
            botao.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: transparent;
                    color: {Cores.TEXTO_PRIMARY};
                    border: 1px solid transparent;
                    border-radius: 6px;
                    font-size: 10pt;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #1f2c40;
                    border-color: #3f5472;
                }}
                """
            )
        self._btn_fechar_fullscreen.setStyleSheet(
            self._btn_fechar_fullscreen.styleSheet()
            + f"""
            QPushButton:hover {{
                background-color: {Cores.VERMELHO};
                border-color: {Cores.VERMELHO};
            }}
            """
        )

        barra_layout.addWidget(self._btn_minimizar_fullscreen)
        barra_layout.addWidget(self._btn_janela_modo)
        barra_layout.addWidget(self._btn_fechar_fullscreen)

        self._lbl_versao_controles = QLabel(self)
        self._lbl_versao_controles.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none;"
        )
        self._fonte_versao_base = 9.2
        self._fonte_versao_secundaria = max(7.0, self._fonte_versao_base - 1.6)
        self._lbl_versao_controles.setTextFormat(Qt.RichText)
        self._lbl_versao_controles.setText(
            (
                "<div style='text-align:center; line-height:1.0;'>"
                f"<span style='font-size:{self._fonte_versao_base:.1f}pt; font-weight:700;'>"
                "iRacerApp"
                "</span><br>"
                f"<span style='font-size:{self._fonte_versao_secundaria:.1f}pt; font-weight:600;'>"
                "v0.20"
                "</span>"
                "</div>"
            )
        )
        self._lbl_versao_controles.setAlignment(Qt.AlignCenter)
        self._lbl_versao_controles.adjustSize()
        hint = self._lbl_versao_controles.sizeHint()
        self._tamanho_rotulo_versao = QSize(hint.width() + 8, hint.height() + 2)
        self._lbl_versao_controles.resize(self._tamanho_rotulo_versao)
        self._lbl_versao_controles.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._lbl_versao_controles.hide()
        self._offset_vertical_rotulo_versao = 6
        self._efeito_opacidade_versao = QGraphicsOpacityEffect(self._lbl_versao_controles)
        self._efeito_opacidade_versao.setOpacity(0.0)
        self._lbl_versao_controles.setGraphicsEffect(self._efeito_opacidade_versao)

        self._anim_opacidade_versao = QPropertyAnimation(
            self._efeito_opacidade_versao, b"opacity", self
        )
        self._anim_opacidade_versao.setDuration(280)
        self._anim_opacidade_versao.setStartValue(0.0)
        self._anim_opacidade_versao.setEndValue(1.0)
        self._anim_opacidade_versao.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_controles_fullscreen = QPropertyAnimation(
            self._barra_controles_fullscreen, b"pos", self
        )
        self._anim_controles_fullscreen.setDuration(95)
        self._anim_controles_fullscreen.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_controles_fullscreen.valueChanged.connect(
            self._sincronizar_rotulo_versao_controles
        )
        self._anim_controles_fullscreen.finished.connect(
            self._ao_animacao_controles_fullscreen_finalizada
        )

        self._anim_recuo_controles_topo = QVariantAnimation(self)
        self._anim_recuo_controles_topo.setDuration(95)
        self._anim_recuo_controles_topo.setEasingCurve(QEasingCurve.OutCubic)
        self._anim_recuo_controles_topo.valueChanged.connect(
            self._aplicar_recuo_controles_topo
        )

        self._controles_fullscreen_visiveis = False
        self._posicionar_controles_fullscreen()
        self._barra_controles_fullscreen.hide()
        self._atualizar_botao_modo_janela()

        self._timer_controles_fullscreen = QTimer(self)
        self._timer_controles_fullscreen.setInterval(80)
        self._timer_controles_fullscreen.timeout.connect(
            self._atualizar_controles_fullscreen
        )
        self._timer_controles_fullscreen.start()

    def _alternar_modo_janela(self):
        self._fixar_tela_cheia = not self._fixar_tela_cheia
        self._atualizar_botao_modo_janela()

        if self._fixar_tela_cheia:
            self.showFullScreen()
            return

        self.showNormal()
        tela = self.screen()
        if tela:
            area = tela.availableGeometry()
            largura = min(
                max(int(area.width() * 0.82), self.minimumWidth()),
                area.width(),
            )
            altura = min(
                max(int(area.height() * 0.82), self.minimumHeight()),
                area.height(),
            )
            pos_x = area.x() + (area.width() - largura) // 2
            pos_y = area.y() + (area.height() - altura) // 2
            self.setGeometry(pos_x, pos_y, largura, altura)

    def _atualizar_botao_modo_janela(self):
        if not hasattr(self, "_btn_janela_modo"):
            return
        if self._fixar_tela_cheia:
            self._btn_janela_modo.setText("🗗")
        else:
            self._btn_janela_modo.setText("🗖")

    def _posicao_rotulo_versao_controles(self) -> QPoint:
        if not hasattr(self, "_lbl_versao_controles") or not hasattr(
            self, "_barra_controles_fullscreen"
        ):
            return QPoint(0, 0)
        largura_base = int(getattr(self, "_tamanho_rotulo_versao", QSize(0, 0)).width())
        x = (
            self._barra_controles_fullscreen.x()
            + (self._barra_controles_fullscreen.width() - largura_base) // 2
        )
        y = (
            self._barra_controles_fullscreen.y()
            + self._barra_controles_fullscreen.height()
            + int(getattr(self, "_offset_vertical_rotulo_versao", 6))
        )
        return QPoint(max(x, 0), y)

    def _retangulo_rotulo_versao_controles(self, escala: float = 1.0) -> QRect:
        if not hasattr(self, "_tamanho_rotulo_versao"):
            return QRect()
        ponto_base = self._posicao_rotulo_versao_controles()
        largura_base = int(self._tamanho_rotulo_versao.width())
        altura_base = int(self._tamanho_rotulo_versao.height())
        largura = max(1, int(round(largura_base * float(escala))))
        altura = max(1, int(round(altura_base * float(escala))))
        x = int(round(ponto_base.x() + (largura_base - largura) / 2.0))
        y = int(round(ponto_base.y() + (altura_base - altura) / 2.0))
        return QRect(x, y, largura, altura)

    def _posicionar_rotulo_versao_controles(self):
        if not hasattr(self, "_lbl_versao_controles"):
            return
        largura_base = max(1, int(getattr(self, "_tamanho_rotulo_versao", QSize(1, 1)).width()))
        escala_atual = self._lbl_versao_controles.width() / largura_base
        escala_atual = max(0.7, min(1.3, escala_atual))
        self._lbl_versao_controles.setGeometry(
            self._retangulo_rotulo_versao_controles(escala_atual)
        )

    def _sincronizar_rotulo_versao_controles(self, _valor):
        if hasattr(self, "_lbl_versao_controles") and self._lbl_versao_controles.isVisible():
            self._posicionar_rotulo_versao_controles()

    def _animar_entrada_rotulo_versao(self):
        if not hasattr(self, "_lbl_versao_controles"):
            return
        self._anim_opacidade_versao.stop()
        self._efeito_opacidade_versao.setOpacity(0.0)
        self._lbl_versao_controles.setGeometry(
            self._retangulo_rotulo_versao_controles(1.0)
        )
        self._anim_opacidade_versao.start()

    def _posicao_controles_fullscreen(self, visiveis: bool) -> QPoint:
        if not hasattr(self, "_barra_controles_fullscreen"):
            return QPoint(0, 0)
        margem = 12
        x = max(
            self.width() - self._barra_controles_fullscreen.width() - margem,
            margem,
        )
        y_visivel = 8
        y_oculto = -self._barra_controles_fullscreen.height() - 2
        return QPoint(x, y_visivel if visiveis else y_oculto)

    def _posicionar_controles_fullscreen(self):
        if not hasattr(self, "_barra_controles_fullscreen"):
            return
        self._barra_controles_fullscreen.move(
            self._posicao_controles_fullscreen(self._controles_fullscreen_visiveis)
        )
        self._posicionar_rotulo_versao_controles()

    def _set_controles_fullscreen_visiveis(self, visiveis: bool, instantaneo: bool = False):
        if not hasattr(self, "_barra_controles_fullscreen"):
            return
        if self._controles_fullscreen_visiveis == visiveis and not instantaneo:
            return

        self._controles_fullscreen_visiveis = visiveis
        self._animar_recuo_controles_topo(visiveis, instantaneo=instantaneo)
        destino = self._posicao_controles_fullscreen(visiveis)

        self._anim_controles_fullscreen.stop()
        if instantaneo:
            self._barra_controles_fullscreen.move(destino)
            self._barra_controles_fullscreen.setVisible(visiveis)
            if hasattr(self, "_lbl_versao_controles"):
                self._lbl_versao_controles.setVisible(visiveis)
                if visiveis:
                    self._lbl_versao_controles.setGeometry(
                        self._retangulo_rotulo_versao_controles(1.0)
                    )
                    self._efeito_opacidade_versao.setOpacity(1.0)
            return

        if visiveis:
            self._barra_controles_fullscreen.show()
            self._barra_controles_fullscreen.raise_()
            if hasattr(self, "_lbl_versao_controles"):
                self._lbl_versao_controles.hide()
                self._anim_opacidade_versao.stop()
                self._efeito_opacidade_versao.setOpacity(0.0)

        self._anim_controles_fullscreen.setStartValue(self._barra_controles_fullscreen.pos())
        self._anim_controles_fullscreen.setEndValue(destino)
        self._anim_controles_fullscreen.start()

    def _ao_animacao_controles_fullscreen_finalizada(self):
        if self._controles_fullscreen_visiveis:
            if hasattr(self, "_lbl_versao_controles"):
                self._lbl_versao_controles.show()
                self._lbl_versao_controles.raise_()
                self._posicionar_rotulo_versao_controles()
                self._animar_entrada_rotulo_versao()
            return

        if not self._controles_fullscreen_visiveis and hasattr(
            self, "_barra_controles_fullscreen"
        ):
            self._barra_controles_fullscreen.hide()
            if hasattr(self, "_lbl_versao_controles"):
                self._lbl_versao_controles.hide()
                self._anim_opacidade_versao.stop()
                self._efeito_opacidade_versao.setOpacity(0.0)
                self._lbl_versao_controles.setGeometry(
                    self._retangulo_rotulo_versao_controles(1.0)
                )

    def _aplicar_recuo_controles_topo(self, valor):
        self._recuo_controles_topo_atual = int(valor)
        if not hasattr(self, "_top_right_widget") or not hasattr(
            self, "_grupo_categoria_top"
        ):
            return

        recuo_max = int(getattr(self, "_top_right_recuo_max", 0))
        recuo = max(0, min(self._recuo_controles_topo_atual, recuo_max))

        controles_w = self._grupo_categoria_top.width()
        x_base = self._top_right_widget.width() - controles_w
        x = max(0, x_base - recuo)
        y = max((self._top_right_widget.height() - self._grupo_categoria_top.height()) // 2, 0)
        self._grupo_categoria_top.move(x, y)

    def _animar_recuo_controles_topo(self, visiveis: bool, instantaneo: bool = False):
        if not hasattr(self, "_top_right_widget"):
            return
        if not hasattr(self, "_barra_controles_fullscreen"):
            return

        destino = self._barra_controles_fullscreen.width() + 12 if visiveis else 0
        if instantaneo:
            self._aplicar_recuo_controles_topo(destino)
            return

        atual = int(getattr(self, "_recuo_controles_topo_atual", 0))
        if atual == destino:
            return

        self._anim_recuo_controles_topo.stop()
        self._anim_recuo_controles_topo.setStartValue(atual)
        self._anim_recuo_controles_topo.setEndValue(destino)
        self._anim_recuo_controles_topo.start()

    def _atualizar_controles_fullscreen(self):
        if not hasattr(self, "_barra_controles_fullscreen"):
            return

        if not self.isVisible() or self.isMinimized():
            self._set_controles_fullscreen_visiveis(False, instantaneo=True)
            return

        if self._fixar_tela_cheia and not self.isFullScreen():
            QTimer.singleShot(0, self.showFullScreen)
            return

        pos_local = self.mapFromGlobal(QCursor.pos())
        dentro_janela = (
            0 <= pos_local.x() <= self.width() and 0 <= pos_local.y() <= self.height()
        )
        if not dentro_janela:
            self._set_controles_fullscreen_visiveis(False)
            return

        faixa_ativacao = pos_local.y() <= 22
        area_barra_expandida = self._barra_controles_fullscreen.geometry().adjusted(
            -20, -16, 20, 18
        )
        manter_visivel = self._barra_controles_fullscreen.isVisible() and area_barra_expandida.contains(pos_local)
        self._set_controles_fullscreen_visiveis(faixa_ativacao or manter_visivel)

    def _temporada_concluida(self) -> bool:
        return bool(self.banco.get("temporada_concluida", False))

    def _obter_calendario_temporada(self) -> list[dict[str, Any]]:
        """
        Retorna o calendario efetivo da categoria atual.
        Prioriza o preset do backend (AI Season) quando existir.
        """
        categoria_id = str(self.categoria_atual or "").strip()

        try:
            from Logica.aiseason import obter_calendario_predefinido

            calendario_preset = obter_calendario_predefinido(categoria_id)
        except Exception:
            calendario_preset = []

        if calendario_preset:
            calendario_ui: list[dict[str, Any]] = []
            for indice, etapa in enumerate(calendario_preset, start=1):
                track_id = etapa.get("trackId", "N/D")
                circuito = str(etapa.get("nome", f"Track ID {track_id}") or "").strip()
                if not circuito:
                    circuito = f"Track ID {track_id}"

                calendario_ui.append(
                    {
                        "nome": f"Rodada {indice}",
                        "circuito": circuito,
                        "trackId": track_id,
                        "voltas": "-",
                        "clima": "-",
                        "temperatura": "-",
                    }
                )
            return calendario_ui

        calendario_raw = self.banco.get("calendario", [])
        if not isinstance(calendario_raw, list):
            return []

        return [corrida for corrida in calendario_raw if isinstance(corrida, dict)]

    def _obter_total_rodadas_temporada(self) -> int:
        """
        Retorna o total de rodadas efetivo da categoria atual.
        """
        categoria_id = str(self.categoria_atual or "").strip()

        try:
            from Logica.aiseason import obter_total_etapas_predefinido

            total_preset = obter_total_etapas_predefinido(categoria_id)
        except Exception:
            total_preset = None

        if isinstance(total_preset, int) and total_preset > 0:
            return total_preset

        calendario = self._obter_calendario_temporada()
        if calendario:
            return len(calendario)

        try:
            total_banco = int(self.banco.get("total_rodadas", 0))
        except (TypeError, ValueError):
            total_banco = 0

        return total_banco if total_banco > 0 else 24

    def _corridas_disputadas(self) -> int:
        total = self._obter_total_rodadas_temporada()
        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada_atual = 1

        if self._temporada_concluida():
            return total

        return min(max(rodada_atual - 1, 0), total)

    def _corridas_restantes(self) -> int:
        total = self._obter_total_rodadas_temporada()
        return max(total - self._corridas_disputadas(), 0)

    def _ordenar_pilotos_campeonato(
        self,
        pilotos: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return self._ordenar_pilotos_por_desempenho_dashboard(pilotos)

    def _ordenar_equipes_campeonato(
        self,
        equipes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        trofeus_historicos = self._obter_trofeus_equipes_historico_tabela()
        ano_atual = self.banco.get("ano_atual", 0)
        try:
            ano_anterior = int(ano_atual) - 1
        except (TypeError, ValueError):
            ano_anterior = None
        if isinstance(ano_anterior, int) and ano_anterior < 0:
            ano_anterior = None

        podio_anterior = self._obter_podio_construtores_historico_dashboard(
            self.categoria_atual,
            ano_anterior,
        )
        prioridade_podio: dict[str, int] = {}
        for indice, tipo in enumerate(("ouro", "prata", "bronze")):
            chave_equipe = podio_anterior.get(tipo, "")
            if chave_equipe and chave_equipe not in prioridade_podio:
                prioridade_podio[chave_equipe] = indice

        def _chave_ordenacao(equipe: dict[str, Any]) -> tuple[Any, ...]:
            nome_equipe = str(equipe.get("nome", "") or "")
            chave_equipe = self._normalizar_chave_equipe_tabela(nome_equipe)
            trofeus = trofeus_historicos.get(
                chave_equipe,
                {"ouro": 0, "prata": 0, "bronze": 0},
            )

            return (
                -int(equipe.get("pontos_temporada", 0) or 0),
                -int(equipe.get("vitorias_temporada", 0) or 0),
                -int(equipe.get("podios_temporada", 0) or 0),
                prioridade_podio.get(chave_equipe, 99),
                -int(trofeus.get("ouro", 0) or 0),
                -int(trofeus.get("prata", 0) or 0),
                -int(trofeus.get("bronze", 0) or 0),
                nome_equipe.casefold(),
            )

        return sorted(
            equipes,
            key=_chave_ordenacao,
        )

    def _obter_jogador(self):
        return next(
            (p for p in self.banco.get("pilotos", []) if p.get("is_jogador")),
            None,
        )

    # ============================================================
    # WRAPPERS DOS MIXINS
    # ============================================================

    def _abrir_historia(self):
        return self._delegar_mixin(ConfigMixin, "_abrir_historia")

    def _abrir_perfil_jogador(self):
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            QMessageBox.warning(self, "Aviso", "Jogador nao encontrado.")
            return

        categoria_jogador = str(jogador.get("categoria_atual", self.categoria_atual) or self.categoria_atual)
        pilotos_categoria = obter_pilotos_categoria(self.banco, categoria_jogador)
        pilotos_ordenados = self._ordenar_pilotos_por_desempenho_dashboard(pilotos_categoria)
        posicao_campeonato = next(
            (
                indice + 1
                for indice, piloto in enumerate(pilotos_ordenados)
                if isinstance(piloto, dict) and bool(piloto.get("is_jogador", False))
            ),
            "-",
        )

        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_atual = 1

        contexto = {
            "posicao_campeonato": posicao_campeonato,
            "total_pilotos": len(pilotos_ordenados),
            "rodada_atual": rodada_atual,
            "total_rodadas": int(self._obter_total_rodadas_temporada()),
        }

        try:
            from UI.dialogs import PerfilJogadorDialog

            dialogo = PerfilJogadorDialog(
                banco=self.banco,
                jogador=jogador,
                contexto=contexto,
                parent=self,
            )
            dialogo.exec()
        except Exception as erro:
            QMessageBox.warning(self, "Aviso", f"Tela de perfil indisponivel.\nErro: {erro}")

    def _configurar_pastas(self):
        return self._delegar_mixin(ConfigMixin, "_configurar_pastas")

    def _configurar_conteudo_iracing(self):
        return self._delegar_mixin(ConfigMixin, "_configurar_conteudo_iracing")

    def _exportar_roster(self, silencioso: bool = False):
        return self._delegar_mixin(ExportarImportarMixin, "_exportar_roster", silencioso=silencioso)

    def _exportar_aiseason(self, silencioso: bool = False):
        return self._delegar_mixin(ExportarImportarMixin, "_exportar_aiseason", silencioso=silencioso)

    def _preparar_proxima_corrida(self):
        if hasattr(self, "tabs"):
            self._mostrar_aba(1)
        if hasattr(self, "_rw_stack"):
            self._rw_ir_para_etapa(0)
            return None
        return self._exportar_aiseason(silencioso=True)

    def _importar_resultado(self):
        return self._delegar_mixin(ExportarImportarMixin, "_importar_resultado")

    def _proximo_resultado(self):
        return self._delegar_mixin(ExportarImportarMixin, "_proximo_resultado")

    def _sincronizar_resultado_iracing(self):
        return self._delegar_mixin(ExportarImportarMixin, "_sincronizar_resultado_iracing")

    def _simular_corrida(self):
        return self._delegar_mixin(SimularMixin, "_simular_corrida")

    def _simular_temporada_completa(self):
        return self._delegar_mixin(SimularMixin, "_simular_temporada_completa")

    def _finalizar_temporada(self):
        return self._delegar_mixin(TemporadaMixin, "_finalizar_temporada")

    def _configurar_atalhos(self):
        from PySide6.QtGui import QKeySequence, QShortcut

        atalhos_map = {
            "Ctrl+1": lambda: self._mostrar_aba(0),
            "Ctrl+2": lambda: self._mostrar_aba(1),
            "Ctrl+3": lambda: self._mostrar_aba(2),
            "Ctrl+4": lambda: self._mostrar_aba(3),
            "Ctrl+5": lambda: self._mostrar_aba(4),
            "Ctrl+6": lambda: self._mostrar_aba(5),
            "Ctrl+7": lambda: self._mostrar_aba(6),
            "Ctrl+Page Up": lambda: self._navegar_categoria(-1),
            "Ctrl+Page Down": lambda: self._navegar_categoria(1),
        }
        self._atalhos_salvos = []
        for seq, callback in atalhos_map.items():
            atalho = QShortcut(QKeySequence(seq), self)
            atalho.activated.connect(callback)
            self._atalhos_salvos.append(atalho)

    # ============================================================
    # MONITOR DE RESULTADOS
    # ============================================================

    @staticmethod
    def _normalizar_caminho_monitor(caminho: str) -> str:
        caminho_limpo = str(caminho or "").strip()
        if not caminho_limpo:
            return ""
        try:
            return os.path.normcase(os.path.abspath(os.path.normpath(caminho_limpo)))
        except Exception:
            return os.path.normcase(os.path.normpath(caminho_limpo))

    def _resolver_pasta_monitor_resultados(self) -> str:
        pasta_aiseasons = self._obter_pasta_aiseasons_salva()
        if not pasta_aiseasons or not os.path.isdir(pasta_aiseasons):
            pasta_aiseasons = self._encontrar_pasta_aiseasons_padrao()

        if not pasta_aiseasons:
            return ""

        return os.path.normpath(pasta_aiseasons)

    def _arquivo_estah_em_results_monitor(self, caminho_norm: str) -> bool:
        pasta_base = str(getattr(self, "_pasta_aiseasons_monitor_norm", "") or "").strip()
        if not pasta_base:
            return False

        pasta_results = self._normalizar_caminho_monitor(os.path.join(pasta_base, "results"))
        if not pasta_results:
            return False

        return (
            caminho_norm == pasta_results
            or caminho_norm.startswith(f"{pasta_results}{os.sep}")
        )

    def _resolver_categoria_por_arquivo_monitor(self, caminho_norm: str) -> str:
        caminhos_categoria: dict[str, str] = {}

        try:
            from Dados.config import obter_todas_seasons

            seasons_config = obter_todas_seasons()
            if isinstance(seasons_config, dict):
                for categoria_id, arquivo in seasons_config.items():
                    if categoria_id and arquivo:
                        caminhos_categoria[str(categoria_id)] = str(arquivo)
        except Exception:
            pass

        arquivos_banco = self.banco.get("arquivo_season_por_categoria", {})
        if isinstance(arquivos_banco, dict):
            for categoria_id, arquivo in arquivos_banco.items():
                categoria_key = str(categoria_id or "").strip()
                if not categoria_key or not arquivo:
                    continue
                caminhos_categoria.setdefault(categoria_key, str(arquivo))

        for categoria_id, caminho in caminhos_categoria.items():
            if self._normalizar_caminho_monitor(caminho) == caminho_norm:
                return categoria_id

        return ""

    def _iniciar_monitor_resultados(self) -> None:
        monitor_atual = getattr(self, "_monitor_iracing", None)
        if monitor_atual and monitor_atual.esta_rodando():
            return

        pasta_monitor = self._resolver_pasta_monitor_resultados()
        if not pasta_monitor:
            print("Monitor de resultados: pasta aiseasons nao configurada.")
            return

        try:
            from Logica.monitor_resultados import MonitorIRacing
        except ImportError:
            print("Monitor de resultados indisponivel: modulo nao encontrado.")
            return

        monitor = MonitorIRacing(
            pasta_monitorada=pasta_monitor,
            callback=self._callback_monitor_resultados,
            recursive=True,
        )
        if monitor.iniciar():
            self._monitor_iracing = monitor
            self._pasta_aiseasons_monitor_norm = self._normalizar_caminho_monitor(pasta_monitor)
        else:
            self._monitor_iracing = None
            self._pasta_aiseasons_monitor_norm = ""

    def _callback_monitor_resultados(self, caminho_arquivo: str) -> bool:
        """
        Encaminha o evento do watchdog para a thread da UI e aguarda retorno.
        """
        fila_resultado: Queue[bool] = Queue(maxsize=1)
        self._monitor_signals.resultado_detectado_sync.emit(
            str(caminho_arquivo or ""),
            fila_resultado,
        )

        try:
            return bool(fila_resultado.get(timeout=300.0))
        except Empty:
            return False

    def _ao_resultado_detectado_monitor_sync(
        self,
        caminho_arquivo: str,
        fila_resultado: object,
    ) -> None:
        resultado = False
        try:
            resultado = bool(self._ao_resultado_detectado_monitor(caminho_arquivo))
        finally:
            if isinstance(fila_resultado, Queue):
                try:
                    fila_resultado.put_nowait(resultado)
                except Exception:
                    pass

    def _parar_monitor_resultados(self) -> None:
        monitor = getattr(self, "_monitor_iracing", None)
        if monitor:
            monitor.parar()
        self._monitor_iracing = None
        self._pasta_aiseasons_monitor_norm = ""

    def _reiniciar_monitor_resultados(self) -> None:
        self._parar_monitor_resultados()
        self._iniciar_monitor_resultados()

    def _atualizar_standings_automatico(self, categoria_id: str, dados_corrida: dict) -> int:
        classificacao = dados_corrida.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return 0

        categoria_original = str(self.categoria_atual or "").strip()
        categoria_alvo = str(categoria_id or categoria_original).strip() or categoria_original

        try:
            self.categoria_atual = categoria_alvo
            aplicados = self._aplicar_classificacao_por_nome(classificacao)
            if aplicados <= 0:
                return 0

            calcular_pontos_equipes(self.banco, self.categoria_atual)
            simular_paralelo = getattr(self, "_simular_rodada_todas_categorias", None)
            if callable(simular_paralelo):
                simular_paralelo(rodada_referencia=int(self.banco.get("rodada_atual", 1)))
            self._avancar_rodada()
        finally:
            self.categoria_atual = categoria_original

        self._atualizar_tudo()
        return aplicados

    def _sincronizar_resultado_automatico_season(self, categoria_id: str) -> dict:
        try:
            from Logica.importador import ler_resultado_aiseason
        except ImportError:
            return {
                "sucesso": False,
                "erro": "Modulo de sincronizacao de AI Season nao encontrado.",
            }

        resultado = ler_resultado_aiseason(self.banco, categoria_id)
        if not resultado.get("sucesso", False):
            return {
                "sucesso": False,
                "erro": str(resultado.get("erro", "")).strip(),
                "aviso": str(resultado.get("aviso", "")).strip(),
            }

        classificacao = resultado.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return {
                "sucesso": False,
                "erro": "Classificacao invalida retornada pela season.",
            }

        dados_corrida = {"classificacao": classificacao}
        aplicados = self._atualizar_standings_automatico(categoria_id, dados_corrida)
        if aplicados <= 0:
            return {
                "sucesso": False,
                "erro": "Nenhum resultado foi aplicado aos standings.",
            }

        total_resultados = len(classificacao)
        return {
            "sucesso": True,
            "categoria_id": categoria_id,
            "vencedor": str(resultado.get("vencedor", "")).strip(),
            "aplicados": aplicados,
            "total_resultados": total_resultados,
        }

    def _ao_resultado_detectado_monitor(self, caminho_arquivo: str) -> bool:
        caminho = str(caminho_arquivo or "").strip()
        if not caminho:
            return False
        caminho_norm = self._normalizar_caminho_monitor(caminho)
        if not caminho_norm:
            return False

        if self._temporada_concluida():
            print("Monitor: temporada concluida, ignorando novo resultado.")
            return False

        if self._evento_pcc_ativo():
            print("Monitor: resultado ignorado durante evento PCC ativo.")
            return False

        categoria_por_arquivo = self._resolver_categoria_por_arquivo_monitor(caminho_norm)
        if categoria_por_arquivo:
            categoria_id = categoria_por_arquivo
            resultado = self._sincronizar_resultado_automatico_season(categoria_id)
        elif self._arquivo_estah_em_results_monitor(caminho_norm):
            categoria_id = str(getattr(self, "categoria_atual", "") or "").strip()
            if not categoria_id:
                print("Monitor: categoria ativa invalida, resultado ignorado.")
                return False

            try:
                from Logica.processar_resultado import processar_resultado_corrida
            except ImportError:
                print("Monitor: modulo Logica.processar_resultado nao encontrado.")
                return False

            resultado = processar_resultado_corrida(
                caminho_arquivo=caminho,
                categoria_id=categoria_id,
                atualizar_standings_callback=self._atualizar_standings_automatico,
            )
        else:
            return True

        if not resultado.get("sucesso", False):
            erro = str(resultado.get("erro", "Falha desconhecida.")).strip()
            aviso = str(resultado.get("aviso", "")).strip()
            if aviso:
                print(f"Monitor: aguardando resultado em {caminho}: {aviso}")
                return False
            print(f"Monitor: falha ao processar resultado ({caminho}): {erro}")
            return False

        aplicados = int(resultado.get("aplicados", 0) or 0)
        total = int(resultado.get("total_resultados", aplicados) or aplicados)
        vencedor = str(resultado.get("vencedor", "")).strip() or "Nao identificado"

        mensagem = (
            "Novo resultado detectado e sincronizado automaticamente.\n\n"
            f"Categoria: {categoria_id}\n"
            f"Vencedor: {vencedor}\n"
            f"Resultados aplicados: {aplicados}/{total}"
        )
        QMessageBox.information(self, "Resultado sincronizado", mensagem)

        try:
            pendentes = [
                item
                for item in self._consumir_notificacoes_hierarquia_pendentes()
                if bool(item.get("envolve_jogador", False))
                and str(item.get("notificacao", "")).strip()
            ]
            self._mostrar_notificacoes_hierarquia(pendentes)
        except Exception:
            pass
        return True

    # ============================================================
    # BUILD UI
    # ============================================================

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_top_navigation())

        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(14, 12, 14, 12)
        content_layout.setSpacing(12)
        content_layout.addWidget(self._build_header_stats())
        content_layout.addWidget(self._build_conteudo(), stretch=1)

        root_layout.addWidget(content_container, stretch=1)

        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet(
            f"background-color: {Cores.FUNDO_APP}; color: {Cores.TEXTO_SECONDARY}; "
            f"border-top: 1px solid {Cores.BORDA};"
        )
        self.status_bar.showMessage("Pronto")

    def _build_top_navigation(self):
        header = QFrame()
        header.setObjectName("header_top")
        header.setFixedHeight(92)
        header.setStyleSheet(
            f"""
            QFrame#header_top {{
                background-color: #0a111d;
                border-bottom: 1px solid {Cores.BORDA};
            }}
            QPushButton#btn_tab_nav {{
                background-color: transparent;
                color: {Cores.TEXTO_SECONDARY};
                border: none;
                border-radius: 16px;
                padding: 6px 14px;
                font-size: 10pt;
                font-weight: 600;
            }}
            QPushButton#btn_tab_nav:hover {{
                color: {Cores.TEXTO_PRIMARY};
                background-color: #121c2b;
            }}
            QPushButton#btn_tab_nav:checked {{
                color: #d7e9ff;
                background-color: #18293f;
            }}
            QComboBox#combo_categoria_top {{
                background-color: #0f1a2a;
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid #2a3547;
                border-radius: 8px;
                padding: 6px 28px 6px 10px;
                min-height: 34px;
            }}
            QComboBox#combo_categoria_top:hover {{
                border-color: {Cores.ACCENT_PRIMARY};
            }}
            QComboBox#combo_categoria_top::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox#combo_categoria_top::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {Cores.TEXTO_SECONDARY};
                margin-right: 8px;
            }}
            QComboBox#combo_categoria_top QAbstractItemView {{
                background-color: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                selection-background-color: {Cores.ACCENT_PRIMARY};
                selection-color: {Cores.TEXTO_INVERSE};
            }}
            QPushButton#btn_config_pastas {{
                background-color: #0f1a2a;
                color: {Cores.TEXTO_SECONDARY};
                border: 1px solid #2a3547;
                border-radius: 8px;
                min-width: 36px;
                min-height: 34px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton#btn_config_pastas:hover {{
                color: {Cores.TEXTO_PRIMARY};
                border-color: {Cores.ACCENT_PRIMARY};
            }}
            QPushButton#btn_cat_nav {{
                background-color: #0f1a2a;
                color: {Cores.TEXTO_SECONDARY};
                border: 1px solid #2a3547;
                border-radius: 5px;
                min-width: 24px;
                max-width: 24px;
                min-height: 16px;
                max-height: 16px;
                font-size: 9pt;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton#btn_cat_nav:hover {{
                color: {Cores.TEXTO_PRIMARY};
                border-color: {Cores.ACCENT_PRIMARY};
                background-color: #162235;
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

        lbl_brand = QLabel("MODO CARREIRA")
        fonte_brand = QFont("Bahnschrift SemiBold", 16)
        fonte_brand.setBold(True)
        fonte_brand.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        lbl_brand.setFont(fonte_brand)
        lbl_brand.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        branding_layout.addWidget(lbl_brand)

        self.lbl_info_temporada = QLabel("Temporada 1 • 2024 | Rodada 3/3")
        self.lbl_info_temporada.setFont(Fontes.texto_pequeno())
        self.lbl_info_temporada.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none;"
        )
        branding_layout.addWidget(self.lbl_info_temporada)

        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)

        self.nav_tab_buttons: list[QPushButton] = []
        tabs_topo = [
            ("Pilotos", 0),
            ("Próxima Corrida", 1),
            ("Minha Equipe", 2),
            ("Previsão", 3),
            ("Mercado", 4),
            ("Notícias", 5),
            ("Outras Categorias", 6),
        ]
        for titulo, indice in tabs_topo:
            botao = self._criar_botao_navegacao(titulo, indice)
            self.nav_tab_buttons.append(botao)
            nav_layout.addWidget(botao)

        self.btn_nav_historia = QPushButton("Historia")
        self.btn_nav_historia.setObjectName("btn_tab_nav")
        self.btn_nav_historia.setCursor(Qt.PointingHandCursor)
        self.btn_nav_historia.clicked.connect(self._abrir_historia)
        nav_layout.addWidget(self.btn_nav_historia)

        self.btn_nav_perfil = QPushButton("Meu Perfil")
        self.btn_nav_perfil.setObjectName("btn_tab_nav")
        self.btn_nav_perfil.setCursor(Qt.PointingHandCursor)
        self.btn_nav_perfil.clicked.connect(self._abrir_perfil_jogador)
        nav_layout.addWidget(self.btn_nav_perfil)

        categorias_nomes = [c["nome"] for c in CATEGORIAS]
        self.combo_categoria = QComboBox()
        self.combo_categoria.setObjectName("combo_categoria_top")
        self.combo_categoria.setFont(Fontes.texto_normal())
        self.combo_categoria.addItems(categorias_nomes)
        cat_nome = obter_nome_categoria(self.categoria_atual)
        idx = categorias_nomes.index(cat_nome) if cat_nome in categorias_nomes else 0
        self.combo_categoria.setCurrentIndex(idx)
        self.combo_categoria.currentTextChanged.connect(self._ao_trocar_categoria)
        self.combo_categoria.setFixedWidth(230)

        btn_config = QPushButton("\u2699")
        btn_config.setObjectName("btn_config_pastas")
        btn_config.setCursor(Qt.PointingHandCursor)
        btn_config.setToolTip("Config. Pastas")
        btn_config.clicked.connect(self._configurar_pastas)
        btn_config.setFixedSize(36, 34)

        btn_conteudo = QPushButton("\U0001F4E6")
        btn_conteudo.setObjectName("btn_config_pastas")
        btn_conteudo.setCursor(Qt.PointingHandCursor)
        btn_conteudo.setToolTip("Conteudo iRacing")
        btn_conteudo.clicked.connect(self._configurar_conteudo_iracing)
        btn_conteudo.setFixedSize(36, 34)

        self._top_right_widget = QWidget()
        self._top_right_recuo_max = 154
        self._recuo_controles_topo_atual = int(getattr(self, "_recuo_controles_topo_atual", 0))

        self._grupo_categoria_top = QWidget(self._top_right_widget)
        grupo_layout = QHBoxLayout(self._grupo_categoria_top)
        grupo_layout.setContentsMargins(0, 0, 0, 0)
        grupo_layout.setSpacing(4)

        nav_categoria = QWidget(self._grupo_categoria_top)
        nav_categoria_layout = QVBoxLayout(nav_categoria)
        nav_categoria_layout.setContentsMargins(0, 0, 0, 0)
        nav_categoria_layout.setSpacing(2)
        nav_categoria.setFixedWidth(24)

        btn_cat_up = QPushButton("\u25B2")
        btn_cat_up.setObjectName("btn_cat_nav")
        btn_cat_up.setCursor(Qt.PointingHandCursor)
        btn_cat_up.clicked.connect(lambda: self._navegar_categoria(-1))

        btn_cat_down = QPushButton("\u25BC")
        btn_cat_down.setObjectName("btn_cat_nav")
        btn_cat_down.setCursor(Qt.PointingHandCursor)
        btn_cat_down.clicked.connect(lambda: self._navegar_categoria(1))

        nav_categoria_layout.addWidget(btn_cat_up)
        nav_categoria_layout.addWidget(btn_cat_down)

        self._btn_config_top = btn_config
        self._btn_conteudo_top = btn_conteudo
        grupo_layout.addWidget(self.combo_categoria)
        grupo_layout.addWidget(nav_categoria)
        grupo_layout.addWidget(self._btn_conteudo_top)
        grupo_layout.addWidget(self._btn_config_top)

        self._grupo_categoria_top.adjustSize()
        controles_largura = self._grupo_categoria_top.sizeHint().width()
        controles_altura = max(
            self.combo_categoria.sizeHint().height(),
            nav_categoria.sizeHint().height(),
            self._btn_conteudo_top.sizeHint().height(),
            self._btn_config_top.sizeHint().height(),
        )
        self._grupo_categoria_top.setFixedSize(controles_largura, controles_altura)
        self._top_right_widget.setFixedSize(
            controles_largura + self._top_right_recuo_max,
            controles_altura,
        )
        self._aplicar_recuo_controles_topo(self._recuo_controles_topo_atual)

        layout.addWidget(branding, 0, Qt.AlignVCenter)
        layout.addStretch(1)
        layout.addWidget(nav_widget, 0, Qt.AlignCenter)
        layout.addStretch(1)
        layout.addWidget(self._top_right_widget, 0, Qt.AlignRight | Qt.AlignVCenter)
        QTimer.singleShot(
            0,
            lambda: self._aplicar_recuo_controles_topo(
                self._recuo_controles_topo_atual
            ),
        )

        return header

    def _criar_botao_navegacao(self, texto: str, indice: int) -> QPushButton:
        botao = QPushButton(texto)
        botao.setObjectName("btn_tab_nav")
        botao.setCheckable(True)
        botao.setCursor(Qt.PointingHandCursor)
        botao.clicked.connect(lambda _checked=False, idx=indice: self._mostrar_aba(idx))
        return botao

    def _build_conteudo(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
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

        self.tab_pilotos = self._build_tab_pilotos()
        self.tabs.addTab(self.tab_pilotos, "👤 Pilotos")

        self.tab_corrida = self._build_tab_proxima_corrida()
        self.tabs.addTab(self.tab_corrida, "🏎️ Próxima Corrida")

        self.tab_minha_equipe = self._build_tab_minha_equipe()
        self.tabs.addTab(self.tab_minha_equipe, "🔧 Minha Equipe")

        self.tab_previsao = self._build_tab_previsao_campeonato()
        self.tabs.addTab(self.tab_previsao, "📈 Previsão")

        self.tab_mercado = self._build_tab_mercado()
        self.tabs.addTab(self.tab_mercado, "💼 Mercado")
        self._indice_aba_mercado = self.tabs.count() - 1

        self.tab_noticias = self._build_tab_noticias()
        self.tabs.addTab(self.tab_noticias, "📰 Notícias")
        self._indice_aba_noticias = self.tabs.count() - 1

        self.tab_outras_categorias = self._build_tab_outras_categorias()
        self.tabs.addTab(self.tab_outras_categorias, "🏁 Outras Categorias")
        self._indice_aba_outras_categorias = self.tabs.count() - 1

        self.tabs.currentChanged.connect(self._atualizar_navegacao_ativa)
        layout.addWidget(self.tabs)
        self._atualizar_navegacao_ativa()
        return container

    def _build_header_stats(self):
        painel = QFrame()
        painel.setObjectName("painel_acoes_dashboard")
        painel.setStyleSheet(
            f"""
            QFrame#painel_acoes_dashboard {{
                background-color: transparent;
                border: none;
            }}
            QFrame#painel_resumo_jogador {{
                background-color: #111b2a;
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
            }}
            QToolButton#btn_menu_acao {{
                background-color: transparent;
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA_HOVER};
                border-radius: {Espacos.RAIO_BOTAO}px;
                padding: 6px 14px;
                min-height: {Espacos.ALTURA_BOTAO}px;
                font-weight: 600;
            }}
            QToolButton#btn_menu_acao:hover {{
                background-color: #1c283b;
                border-color: {Cores.ACCENT_PRIMARY};
            }}
            QMenu {{
                background-color: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                padding: 6px;
            }}
            QMenu::item {{
                padding: 6px 18px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {Cores.ACCENT_PRIMARY};
                color: {Cores.TEXTO_INVERSE};
            }}
        """
        )

        layout = QHBoxLayout(painel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.painel_resumo_jogador = QFrame()
        self.painel_resumo_jogador.setObjectName("painel_resumo_jogador")
        resumo_layout = QVBoxLayout(self.painel_resumo_jogador)
        resumo_layout.setContentsMargins(12, 10, 12, 10)
        resumo_layout.setSpacing(4)

        self.lbl_resumo_jogador_titulo = QLabel("Jogador - Categoria")
        self.lbl_resumo_jogador_titulo.setFont(Fontes.texto_normal())
        self.lbl_resumo_jogador_titulo.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARY}; border: none; font-weight: 700;"
        )
        resumo_layout.addWidget(self.lbl_resumo_jogador_titulo)

        self.lbl_resumo_jogador_l1 = QLabel("Equipe: - | Papel: -")
        self.lbl_resumo_jogador_l1.setFont(Fontes.texto_pequeno())
        self.lbl_resumo_jogador_l1.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        resumo_layout.addWidget(self.lbl_resumo_jogador_l1)

        self.lbl_resumo_jogador_l2 = QLabel("Contrato: -")
        self.lbl_resumo_jogador_l2.setFont(Fontes.texto_pequeno())
        self.lbl_resumo_jogador_l2.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        resumo_layout.addWidget(self.lbl_resumo_jogador_l2)

        self.lbl_resumo_jogador_l3 = QLabel("Posicao: - | Pontos: -")
        self.lbl_resumo_jogador_l3.setFont(Fontes.texto_pequeno())
        self.lbl_resumo_jogador_l3.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        resumo_layout.addWidget(self.lbl_resumo_jogador_l3)

        self.lbl_resumo_jogador_l4 = QLabel("Proxima corrida: -")
        self.lbl_resumo_jogador_l4.setFont(Fontes.texto_pequeno())
        self.lbl_resumo_jogador_l4.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        resumo_layout.addWidget(self.lbl_resumo_jogador_l4)

        self.lbl_contrato_alerta = QLabel("Contrato: sem alertas")
        self.lbl_contrato_alerta.setFont(Fontes.texto_pequeno())
        self.lbl_contrato_alerta.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
        self.lbl_contrato_alerta.setWordWrap(True)
        resumo_layout.addWidget(self.lbl_contrato_alerta)

        self.btn_meu_perfil_dashboard = BotaoSecondary("Meu Perfil")
        self.btn_meu_perfil_dashboard.setMinimumWidth(124)
        self.btn_meu_perfil_dashboard.clicked.connect(self._abrir_perfil_jogador)
        resumo_layout.addWidget(self.btn_meu_perfil_dashboard, 0, Qt.AlignRight)

        layout.addWidget(self.painel_resumo_jogador, 1)
        layout.addStretch(1)

        acoes = QWidget()
        acoes_layout = QHBoxLayout(acoes)
        acoes_layout.setContentsMargins(0, 0, 0, 0)
        acoes_layout.setSpacing(8)

        btn_sincronizar = BotaoSuccess("🔄 Sincronizar")
        btn_sincronizar.setMinimumWidth(146)
        btn_sincronizar.clicked.connect(self._sincronizar_resultado_iracing)
        acoes_layout.addWidget(btn_sincronizar)

        btn_simulacao = self._criar_botao_menu_acao(
            "🎮 Simular",
            [
                ("Simular Corrida", self._simular_corrida),
                ("Simular Temporada", self._simular_temporada_completa),
            ],
        )
        btn_simulacao.setMinimumWidth(126)
        acoes_layout.addWidget(btn_simulacao)

        btn_proxima = BotaoPrimary("🏁 Próxima Corrida")
        btn_proxima.setMinimumWidth(150)
        btn_proxima.clicked.connect(self._preparar_proxima_corrida)
        acoes_layout.addWidget(btn_proxima)

        btn_finalizar = BotaoDanger("🏁 Finalizar")
        btn_finalizar.setMinimumWidth(136)
        btn_finalizar.clicked.connect(self._finalizar_temporada)
        acoes_layout.addWidget(btn_finalizar)

        layout.addWidget(acoes, 0, Qt.AlignRight | Qt.AlignVCenter)

        return painel

    def _criar_botao_menu_acao(self, texto: str, itens: list[tuple[str, Any]]) -> QToolButton:
        botao = QToolButton()
        botao.setObjectName("btn_menu_acao")
        botao.setText(f"{texto} \u25BE")
        botao.setToolButtonStyle(Qt.ToolButtonTextOnly)
        botao.setPopupMode(QToolButton.InstantPopup)
        botao.setCursor(Qt.PointingHandCursor)

        menu = QMenu(botao)
        for titulo, callback in itens:
            acao = menu.addAction(titulo)
            acao.triggered.connect(callback)
        botao.setMenu(menu)

        return botao

    def _build_tab_pilotos(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.tabela_pilotos = QTableWidget()
        self._header_bandeiras_pilotos = BandeiraHeaderView(
            Qt.Horizontal,
            self.tabela_pilotos,
        )
        self.tabela_pilotos.setHorizontalHeader(self._header_bandeiras_pilotos)
        self._qtd_colunas_corridas_tabela_pilotos = 4
        total_colunas_iniciais = 4 + self._qtd_colunas_corridas_tabela_pilotos + 2
        self.tabela_pilotos.setColumnCount(total_colunas_iniciais)
        self.tabela_pilotos.setHorizontalHeaderLabels(
            ["POS", "NAC", "IDADE", "PILOTO", "🏁", "🏁", "🏁", "🏁", "PTS", "MEDALHAS"]
        )
        self.tabela_pilotos.setStyleSheet(
            f"""
            QTableWidget {{
                background-color: #0f1622;
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: 10px;
                gridline-color: {Cores.BORDA};
                outline: none;
            }}
            QHeaderView::section {{
                background-color: #111c2a;
                color: {Cores.TEXTO_SECONDARY};
                border: none;
                border-bottom: 1px solid {Cores.BORDA};
                padding: 7px 8px;
                font-weight: 700;
                text-transform: uppercase;
            }}
            QTableWidget QTableCornerButton::section {{
                background-color: #111c2a;
                border: none;
            }}
        """
        )
        self.tabela_pilotos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_pilotos.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_pilotos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_pilotos.verticalHeader().setVisible(False)
        self.tabela_pilotos.setShowGrid(False)
        self.tabela_pilotos.cellDoubleClicked.connect(self._abrir_ficha_piloto_tabela)
        self.tabela_pilotos.cellClicked.connect(self._ao_clicar_linha_piloto)
        self.tabela_pilotos.cellPressed.connect(self._ao_clicar_linha_piloto)

        self._delegate_heatmap_pilotos = BadgeHeatmapDelegate(self.tabela_pilotos)
        self._configurar_colunas_tabela_pilotos(self._qtd_colunas_corridas_tabela_pilotos)

        titulo_pilotos = QLabel("CLASSIFICAÇÃO DE PILOTOS")
        titulo_pilotos.setFont(Fontes.titulo_medio())
        titulo_pilotos.setStyleSheet(f"color: {Cores.ACCENT_PRIMARY};")
        layout.addWidget(titulo_pilotos)

        area_tabelas = QWidget()
        area_tabelas_layout = QHBoxLayout(area_tabelas)
        area_tabelas_layout.setContentsMargins(0, 0, 0, 0)
        area_tabelas_layout.setSpacing(12)

        painel_pilotos = QWidget()
        painel_pilotos_layout = QVBoxLayout(painel_pilotos)
        painel_pilotos_layout.setContentsMargins(0, 0, 0, 0)
        painel_pilotos_layout.setSpacing(6)
        painel_pilotos_layout.addWidget(self.tabela_pilotos, 1)

        legenda = QLabel(
            "Grid de resultados: 1º ouro • 2º prata • 3º bronze • DNF vermelho • Duplo clique para ficha"
        )
        legenda.setFont(Fontes.texto_pequeno())
        legenda.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
        painel_pilotos_layout.addWidget(legenda)

        area_tabelas_layout.addWidget(painel_pilotos, 3)
        separador_vertical = QFrame()
        separador_vertical.setFixedWidth(1)
        separador_vertical.setStyleSheet(f"background-color: {Cores.BORDA};")
        area_tabelas_layout.addWidget(separador_vertical)

        painel_equipes = QWidget()
        painel_equipes_layout = QVBoxLayout(painel_equipes)
        painel_equipes_layout.setContentsMargins(0, 0, 0, 0)
        painel_equipes_layout.setSpacing(6)

        titulo_equipes = QLabel("CLASSIFICAÇÃO DE CONSTRUTORES")
        titulo_equipes.setFont(Fontes.titulo_medio())
        titulo_equipes.setStyleSheet(f"color: {Cores.ACCENT_PRIMARY};")
        painel_equipes_layout.addWidget(titulo_equipes)

        self.tabela_equipes = QTableWidget()
        self.tabela_equipes.setColumnCount(4)
        self.tabela_equipes.setHorizontalHeaderLabels(
            ["POS", "EQUIPE", "PTS", "TAÇAS"]
        )
        self.tabela_equipes.setStyleSheet(Estilos.tabela())
        self.tabela_equipes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_equipes.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_equipes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_equipes.verticalHeader().setVisible(False)
        self.tabela_equipes.setShowGrid(False)
        self.tabela_equipes.cellDoubleClicked.connect(self._abrir_ficha_equipe_tabela)
        self.tabela_equipes.cellClicked.connect(self._ao_clicar_linha_equipe_tabela)
        self.tabela_equipes.cellPressed.connect(self._ao_clicar_linha_equipe_tabela)
        self._delegate_tabela_equipes = BadgeHeatmapDelegate(self.tabela_equipes)
        self.tabela_equipes.setItemDelegate(self._delegate_tabela_equipes)

        header_equipes = self.tabela_equipes.horizontalHeader()
        header_equipes.setSectionResizeMode(0, QHeaderView.Fixed)
        header_equipes.setSectionResizeMode(1, QHeaderView.Stretch)
        header_equipes.setSectionResizeMode(2, QHeaderView.Fixed)
        header_equipes.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabela_equipes.setColumnWidth(0, 58)
        self.tabela_equipes.setColumnWidth(2, 80)
        self.tabela_equipes.setColumnWidth(3, 230)
        self.tabela_equipes.setMinimumWidth(420)
        self.tabela_equipes.setMaximumWidth(620)
        painel_equipes_layout.addWidget(self.tabela_equipes, 1)

        legenda_equipes = QLabel("🏆 Equipes agregadas: pontos + taças por temporada")
        legenda_equipes.setFont(Fontes.texto_pequeno())
        legenda_equipes.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
        painel_equipes_layout.addWidget(legenda_equipes)

        self._grafico_equipes_widget = self._criar_grafico_equipes_dashboard()
        painel_equipes_layout.addWidget(self._grafico_equipes_widget)
        area_tabelas_layout.addWidget(painel_equipes, 2)
        layout.addWidget(area_tabelas, 1)

        return widget

    def _configurar_colunas_tabela_pilotos(self, qtd_colunas_corrida: int) -> None:
        if not hasattr(self, "tabela_pilotos"):
            return

        qtd_corridas = max(1, int(qtd_colunas_corrida))
        total_colunas = 4 + qtd_corridas + 2
        self.tabela_pilotos.setColumnCount(total_colunas)

        header = self.tabela_pilotos.horizontalHeader()
        for coluna in range(total_colunas):
            header.setSectionResizeMode(coluna, QHeaderView.Fixed)

        header.setSectionResizeMode(3, QHeaderView.Fixed)

        self.tabela_pilotos.setColumnWidth(0, 64)   # POS + tendência
        self.tabela_pilotos.setColumnWidth(1, 48)   # NAC
        self.tabela_pilotos.setColumnWidth(2, 58)   # IDADE
        self.tabela_pilotos.setColumnWidth(3, 180)  # PILOTO

        inicio_corridas = 4
        for indice in range(qtd_corridas):
            self.tabela_pilotos.setColumnWidth(inicio_corridas + indice, 50)

        coluna_pts = inicio_corridas + qtd_corridas
        coluna_medalhas = coluna_pts + 1
        self.tabela_pilotos.setColumnWidth(coluna_pts, 60)
        header.setSectionResizeMode(coluna_medalhas, QHeaderView.Stretch)
        self.tabela_pilotos.setColumnWidth(coluna_medalhas, 130)

        if hasattr(self, "_delegate_heatmap_pilotos"):
            self.tabela_pilotos.setItemDelegate(self._delegate_heatmap_pilotos)

    def _obter_codigo_bandeira_nacionalidade_piloto(self, piloto: dict[str, Any]) -> str:
        nacionalidade = str(piloto.get("nacionalidade", "") or "").strip()
        codigo = obter_codigo_bandeira(nacionalidade, fallback="")
        if codigo:
            return codigo

        nome = str(piloto.get("nome", "") or "").strip()
        if not nome:
            return "un"

        seed = sum((indice + 1) * ord(ch) for indice, ch in enumerate(nome.casefold()))
        return CODIGOS_BANDEIRAS_SUPORTADOS[seed % len(CODIGOS_BANDEIRAS_SUPORTADOS)]

    def _formatar_resultado_heatmap_tabela(
        self, resultado: Any
    ) -> tuple[str, str, str, str, bool, bool]:
        posicao = self._resultado_para_posicao_dashboard(resultado)

        if posicao == "DNF":
            # Igual ao molde da aba Historia.
            return "DNF", Cores.VERMELHO, "#2a171a", "#8b3a3a", True, True

        if isinstance(posicao, int):
            if posicao == 1:
                return "1", Cores.TEXTO_INVERSE, Cores.OURO, "#0f1622", True, False
            if posicao == 2:
                return "2", Cores.TEXTO_INVERSE, Cores.PRATA, "#0f1622", True, False
            if posicao == 3:
                return "3", Cores.TEXTO_INVERSE, Cores.BRONZE, "#0f1622", True, False
            return str(posicao), "#ffffff", "#1e293b", "#2d3a4f", False, False

        # Corridas futuras/sem dado: bloco discreto e sem texto para reduzir ruído visual.
        return "", "#475569", "#111827", "#1f2937", False, False

    def _obter_rodada_proxima_mock_tabela(self, qtd_corridas: int) -> int:
        if qtd_corridas <= 0:
            return 1
        # Mock visual solicitado: considerar a rodada 4 como próxima corrida.
        return max(1, min(4, qtd_corridas))

    def _obter_marcadores_evento_mock_tabela(
        self,
        piloto: dict[str, Any],
        indice_corrida: int,
        resultado: Any,
    ) -> bool:
        posicao = self._resultado_para_posicao_dashboard(resultado)
        if not isinstance(posicao, int):
            return False

        chave_piloto = self._chave_piloto_mock_tabela(piloto)
        if not chave_piloto:
            return False

        mapa_vmr = getattr(self, "_mapa_vmr_rodada_tabela", {})
        if not isinstance(mapa_vmr, dict):
            return False
        return mapa_vmr.get(indice_corrida) == chave_piloto

    def _obter_mapa_vmr_por_rodada_tabela(
        self,
        pilotos: list[dict[str, Any]],
        qtd_corridas: int,
    ) -> dict[int, str]:
        mapa_vmr: dict[int, str] = {}
        total_corridas = max(0, int(qtd_corridas))
        if total_corridas <= 0 or not pilotos:
            return mapa_vmr

        banco_vmr = self.banco.get("volta_rapida_por_rodada", {})
        if not isinstance(banco_vmr, dict):
            return mapa_vmr

        categoria_id = str(self.categoria_atual or "").strip()
        mapa_categoria = banco_vmr.get(categoria_id, {})
        if not isinstance(mapa_categoria, dict):
            return mapa_vmr

        pilotos_por_id: dict[Any, str] = {}
        pilotos_por_id_texto: dict[str, str] = {}
        pilotos_por_nome_norm: dict[str, str] = {}
        for piloto in pilotos:
            chave = self._chave_piloto_mock_tabela(piloto)
            if not chave:
                continue
            piloto_id = piloto.get("id")
            if piloto_id not in (None, ""):
                pilotos_por_id[piloto_id] = chave
                pilotos_por_id_texto[str(piloto_id).strip()] = chave
            nome_norm = self._normalizar_texto_busca_dashboard(piloto.get("nome", ""))
            if nome_norm and nome_norm not in pilotos_por_nome_norm:
                pilotos_por_nome_norm[nome_norm] = chave

        for rodada_raw, registro in mapa_categoria.items():
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
                piloto_id = registro.get("piloto_id")
                if piloto_id in pilotos_por_id:
                    chave_piloto = pilotos_por_id[piloto_id]
                elif piloto_id not in (None, ""):
                    chave_piloto = pilotos_por_id_texto.get(str(piloto_id).strip(), "")

                if not chave_piloto:
                    nome_norm = self._normalizar_texto_busca_dashboard(
                        registro.get("piloto_nome", "")
                    )
                    if nome_norm:
                        chave_piloto = pilotos_por_nome_norm.get(nome_norm, "")
            elif isinstance(registro, str):
                nome_norm = self._normalizar_texto_busca_dashboard(registro)
                if nome_norm:
                    chave_piloto = pilotos_por_nome_norm.get(nome_norm, "")

            if chave_piloto:
                mapa_vmr[indice_corrida] = chave_piloto

        # Fallback: para corridas jogadas no iRacing antes da gravacao local do metadado.
        if len(mapa_vmr) < total_corridas and pilotos_por_nome_norm:
            mapa_vmr_season = self._obter_mapa_vmr_aiseason_tabela(
                pilotos_por_nome_norm,
                total_corridas,
            )
            for indice_corrida, chave_piloto in mapa_vmr_season.items():
                if indice_corrida not in mapa_vmr:
                    mapa_vmr[indice_corrida] = chave_piloto

        return mapa_vmr

    def _obter_mapa_vmr_aiseason_tabela(
        self,
        pilotos_por_nome_norm: dict[str, str],
        qtd_corridas: int,
    ) -> dict[int, str]:
        mapa_vmr: dict[int, str] = {}
        total_corridas = max(0, int(qtd_corridas))
        if total_corridas <= 0:
            return mapa_vmr

        obter_arquivo = getattr(self, "_obter_arquivo_season_evento_atual", None)
        if not callable(obter_arquivo):
            return mapa_vmr

        try:
            caminho_arquivo = str(obter_arquivo() or "").strip()
        except Exception:
            caminho_arquivo = ""
        if not caminho_arquivo or not os.path.isfile(caminho_arquivo):
            return mapa_vmr

        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except (OSError, json.JSONDecodeError):
            return mapa_vmr

        eventos = dados.get("events", [])
        if not isinstance(eventos, list) or not eventos:
            return mapa_vmr

        limite_eventos = min(len(eventos), total_corridas)
        status_finalizado = {"running", "finished", "complete", "completed", "checkered", "finish"}

        for indice_evento in range(limite_eventos):
            evento = eventos[indice_evento]
            if not isinstance(evento, dict):
                continue
            bloco_resultados = evento.get("results")
            if not isinstance(bloco_resultados, dict):
                continue
            sessoes = bloco_resultados.get("session_results", [])
            if not isinstance(sessoes, list):
                continue

            sessao_race = None
            for sessao in sessoes:
                if not isinstance(sessao, dict):
                    continue
                tipo_nome = str(sessao.get("simsession_type_name", "")).strip().casefold()
                if tipo_nome == "race":
                    sessao_race = sessao
                    break
                try:
                    tipo_num = int(sessao.get("simsession_type", -1) or -1)
                except (TypeError, ValueError):
                    tipo_num = -1
                if tipo_num == 6:
                    sessao_race = sessao
                    break
            if not isinstance(sessao_race, dict):
                continue

            resultados = sessao_race.get("results", [])
            if not isinstance(resultados, list) or not resultados:
                continue

            melhor_nome_norm = ""
            melhor_tempo = None

            for entrada in resultados:
                if not isinstance(entrada, dict):
                    continue

                reason_out = str(entrada.get("reason_out", "Running") or "").strip()
                dnf = bool(entrada.get("dnf", False))
                if not dnf and reason_out:
                    dnf = reason_out.casefold() not in status_finalizado
                if dnf:
                    continue

                try:
                    tempo = float(entrada.get("best_lap_time", -1))
                except (TypeError, ValueError):
                    continue
                if tempo <= 0:
                    continue

                nome_norm = self._normalizar_texto_busca_dashboard(
                    entrada.get("display_name", "")
                )
                if not nome_norm:
                    continue

                if melhor_tempo is None or tempo < melhor_tempo:
                    melhor_tempo = tempo
                    melhor_nome_norm = nome_norm

            if not melhor_nome_norm:
                continue

            chave_piloto = pilotos_por_nome_norm.get(melhor_nome_norm, "")
            if chave_piloto:
                mapa_vmr[indice_evento] = chave_piloto

        return mapa_vmr

    def _chave_piloto_mock_tabela(self, piloto: dict[str, Any]) -> str:
        piloto_id = piloto.get("id")
        if piloto_id not in (None, ""):
            return f"id:{piloto_id}"

        nome = self._normalizar_texto_busca_dashboard(piloto.get("nome", ""))
        if nome:
            return f"nome:{nome}"
        return ""

    def _obter_chaves_rivais_mock_tabela(self) -> set[str]:
        if not self.pilotos_ordenados:
            return set()

        chaves_rivais: set[str] = set()
        indice_jogador = next(
            (i for i, piloto in enumerate(self.pilotos_ordenados) if piloto.get("is_jogador")),
            -1,
        )

        if indice_jogador >= 0:
            for deslocamento in (1, -1, 2, -2, 3, -3):
                indice = indice_jogador + deslocamento
                if indice < 0 or indice >= len(self.pilotos_ordenados):
                    continue
                piloto = self.pilotos_ordenados[indice]
                if piloto.get("is_jogador"):
                    continue
                chave = self._chave_piloto_mock_tabela(piloto)
                if chave:
                    chaves_rivais.add(chave)
                if len(chaves_rivais) >= 2:
                    return chaves_rivais

        for piloto in self.pilotos_ordenados:
            if piloto.get("is_jogador"):
                continue
            chave = self._chave_piloto_mock_tabela(piloto)
            if chave:
                chaves_rivais.add(chave)
            if len(chaves_rivais) >= 2:
                break

        return chaves_rivais

    def _obter_trofeus_equipes_historico_tabela(self) -> dict[str, dict[str, int]]:
        trofeus: dict[str, dict[str, int]] = {}
        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return trofeus

        for temporada in historico:
            if not isinstance(temporada, dict):
                continue
            if str(temporada.get("categoria_id", "")) != str(self.categoria_atual):
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
                pontos = int(entrada.get("pontos", 0) or 0)
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

    def _contar_titulos_historicos_piloto_dashboard(
        self,
        piloto_ref: dict[str, Any],
        categoria_id: str,
        ano_limite: int | None = None,
    ) -> int:
        historico = self.banco.get("historico_temporadas_completas", [])
        if not isinstance(historico, list):
            return 0

        def _normalizar_id(valor: Any) -> str:
            if valor in (None, "") or isinstance(valor, bool):
                return ""
            texto = str(valor).strip()
            if not texto:
                return ""
            try:
                return str(int(texto))
            except (TypeError, ValueError):
                return texto.casefold()

        def _posicao_num(valor: Any) -> int:
            texto = str(valor or "").strip()
            if not texto:
                return 0
            texto = texto.replace("º", "").replace("°", "").replace("ª", "").strip()
            if texto.upper().startswith("P"):
                texto = texto[1:].strip()
            try:
                return int(texto)
            except (TypeError, ValueError):
                return 0

        piloto_id_ref = _normalizar_id(piloto_ref.get("id"))
        nome_ref_norm = self._normalizar_texto_busca_dashboard(
            piloto_ref.get("nome", "")
        )
        if not piloto_id_ref and not nome_ref_norm:
            return 0

        total_titulos = 0
        for temporada in historico:
            if not isinstance(temporada, dict):
                continue
            if str(temporada.get("categoria_id", "")) != str(categoria_id):
                continue

            ano_temporada_raw = temporada.get("ano")
            try:
                ano_temporada = int(ano_temporada_raw)
            except (TypeError, ValueError):
                ano_temporada = 0
            if ano_limite is not None and ano_temporada > int(ano_limite):
                continue

            classificacao = temporada.get("classificacao", [])
            if not isinstance(classificacao, list) or not classificacao:
                continue

            campeao = next(
                (
                    entrada
                    for entrada in classificacao
                    if _posicao_num(entrada.get("posicao")) == 1
                ),
                None,
            )
            if not isinstance(campeao, dict):
                continue

            campeao_id = _normalizar_id(campeao.get("piloto_id"))
            campeao_nome = self._normalizar_texto_busca_dashboard(
                campeao.get("piloto", "")
            )
            match_por_id = bool(piloto_id_ref and campeao_id and piloto_id_ref == campeao_id)
            match_por_nome = bool(nome_ref_norm and campeao_nome and nome_ref_norm == campeao_nome)
            if match_por_id or match_por_nome:
                total_titulos += 1

        return total_titulos

    def _chave_piloto_historico_dashboard(self, piloto_id: Any, nome: Any) -> str:
        if piloto_id not in (None, "") and not isinstance(piloto_id, bool):
            texto_id = str(piloto_id).strip()
            if texto_id:
                try:
                    return f"id:{int(texto_id)}"
                except (TypeError, ValueError):
                    return f"id:{texto_id.casefold()}"

        nome_norm = self._normalizar_texto_busca_dashboard(nome)
        if nome_norm:
            return f"nome:{nome_norm}"
        return ""

    def _obter_chave_campeao_pilotos_historico_dashboard(
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
                and int(item.get("ano", 0) or 0) == int(ano_referencia)
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
                if self._resultado_para_posicao_dashboard(entrada.get("posicao")) == 1
            ),
            None,
        )
        if not isinstance(campeao, dict):
            return ""

        return self._chave_piloto_historico_dashboard(
            campeao.get("piloto_id"),
            campeao.get("piloto", ""),
        )

    def _obter_chave_campeao_construtores_historico_dashboard(
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
                and int(item.get("ano", 0) or 0) == int(ano_referencia)
            ),
            None,
        )
        if not isinstance(temporada, dict):
            return ""

        classificacao = temporada.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            return ""

        pontos_por_equipe: dict[str, int] = {}
        for entrada in classificacao:
            if not isinstance(entrada, dict):
                continue
            equipe_nome = str(entrada.get("equipe", "") or "").strip()
            if not equipe_nome:
                continue
            try:
                pontos = int(entrada.get("pontos", 0) or 0)
            except (TypeError, ValueError):
                pontos = 0
            pontos_por_equipe[equipe_nome] = pontos_por_equipe.get(equipe_nome, 0) + pontos

        if not pontos_por_equipe:
            return ""

        ranking = sorted(
            pontos_por_equipe.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
        campea_nome = ranking[0][0]
        return self._normalizar_chave_equipe_tabela(campea_nome)

    def _obter_podio_construtores_historico_dashboard(
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
                and int(item.get("ano", 0) or 0) == int(ano_referencia)
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
            try:
                pontos = int(entrada.get("pontos", 0) or 0)
            except (TypeError, ValueError):
                pontos = 0
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
            podio[tipo] = self._normalizar_chave_equipe_tabela(ranking[indice][0])
        return podio

    def _normalizar_chave_equipe_tabela(self, nome_equipe: Any) -> str:
        return str(nome_equipe or "").strip().casefold()

    def _obter_contexto_destaque_equipes_tabela(self) -> tuple[set[Any], str]:
        ids_destaque: set[Any] = set()
        equipe_chave_sel = self._normalizar_chave_equipe_tabela(
            self._equipe_chave_destacada_tabela
        )

        piloto_sel = None
        if self._piloto_id_destacado_tabela is not None:
            piloto_sel = next(
                (
                    piloto
                    for piloto in self.pilotos_ordenados
                    if piloto.get("id") == self._piloto_id_destacado_tabela
                ),
                None,
            )

        if not equipe_chave_sel and isinstance(piloto_sel, dict):
            equipe_chave_sel = self._normalizar_chave_equipe_tabela(
                piloto_sel.get("equipe_nome", "")
            )

        if isinstance(piloto_sel, dict):
            piloto_id = piloto_sel.get("id")
            if piloto_id is not None:
                ids_destaque.add(piloto_id)

            if self._destacar_somente_piloto_tabela:
                return ids_destaque, ""

            equipe_id_sel = piloto_sel.get("equipe_id")
            for piloto in self.pilotos_ordenados:
                mesmo_id = (
                    equipe_id_sel not in (None, "")
                    and piloto.get("equipe_id") == equipe_id_sel
                )
                mesma_equipe_nome = (
                    equipe_chave_sel
                    and self._normalizar_chave_equipe_tabela(
                        piloto.get("equipe_nome", "")
                    )
                    == equipe_chave_sel
                )
                if mesmo_id or mesma_equipe_nome:
                    pid = piloto.get("id")
                    if pid is not None:
                        ids_destaque.add(pid)
        elif equipe_chave_sel:
            for piloto in self.pilotos_ordenados:
                if (
                    self._normalizar_chave_equipe_tabela(
                        piloto.get("equipe_nome", "")
                    )
                    == equipe_chave_sel
                ):
                    pid = piloto.get("id")
                    if pid is not None:
                        ids_destaque.add(pid)

        return ids_destaque, equipe_chave_sel

    def _cor_destaque_por_equipe(
        self,
        cor_base: str,
        cor_equipe: str,
        alpha: int = 64,
    ) -> str:
        base = QColor(str(cor_base or Cores.FUNDO_CARD))
        equipe = QColor(str(cor_equipe or "#3b82f6"))
        if not equipe.isValid():
            equipe = QColor("#3b82f6")

        alpha_clamp = max(0, min(255, int(alpha)))
        fator = alpha_clamp / 255.0
        r = int((1.0 - fator) * base.red() + fator * equipe.red())
        g = int((1.0 - fator) * base.green() + fator * equipe.green())
        b = int((1.0 - fator) * base.blue() + fator * equipe.blue())
        return QColor(r, g, b).name()

    def _ao_clicar_linha_piloto(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self.pilotos_ordenados):
            return

        self._destacar_somente_piloto_tabela = False
        self._piloto_id_destacado_tabela = self.pilotos_ordenados[row].get("id")
        item_ref = self.tabela_pilotos.item(row, 3)
        if item_ref is not None:
            equipe_chave = self._normalizar_chave_equipe_tabela(
                item_ref.data(BadgeHeatmapDelegate.ROLE_EQUIPE_CHAVE)
            )
            cor_equipe = str(
                item_ref.data(BadgeHeatmapDelegate.ROLE_EQUIPE_COR)
                or self._cor_equipe_destacada_tabela
                or ""
            )
            self._equipe_chave_destacada_tabela = equipe_chave
            self._cor_equipe_destacada_tabela = cor_equipe
        self._atualizar_tabela_pilotos()
        self._atualizar_tabela_equipes()

    def _ao_clicar_linha_equipe_tabela(self, row: int, _col: int) -> None:
        if not hasattr(self, "tabela_equipes"):
            return
        if row < 0 or row >= self.tabela_equipes.rowCount():
            return

        self._destacar_somente_piloto_tabela = False
        item_equipe = self.tabela_equipes.item(row, 1)
        if item_equipe is None:
            return

        self._piloto_id_destacado_tabela = None
        self._equipe_chave_destacada_tabela = self._normalizar_chave_equipe_tabela(
            item_equipe.data(BadgeHeatmapDelegate.ROLE_EQUIPE_CHAVE)
        )
        self._cor_equipe_destacada_tabela = str(
            item_equipe.data(BadgeHeatmapDelegate.ROLE_EQUIPE_COR)
            or self._cor_equipe_destacada_tabela
            or ""
        )
        self._atualizar_tabela_pilotos()
        self._atualizar_tabela_equipes()

    def _aplicar_destaque_linhas_pilotos(self) -> None:
        if not hasattr(self, "tabela_pilotos"):
            return

        ids_destaque, _equipe_chave_sel = self._obter_contexto_destaque_equipes_tabela()
        cor_linha_destaque = "#1f4e66"
        cor_linha_jogador = "#2c3e56"

        total_colunas = self.tabela_pilotos.columnCount()
        total_linhas = min(self.tabela_pilotos.rowCount(), len(self.pilotos_ordenados))

        for row in range(total_linhas):
            piloto = self.pilotos_ordenados[row]
            piloto_id = piloto.get("id")
            is_jogador = bool(piloto.get("is_jogador", False))

            if piloto_id in ids_destaque:
                cor_fundo = cor_linha_destaque
            elif is_jogador:
                cor_fundo = cor_linha_jogador
            elif row % 2 == 0:
                cor_fundo = Cores.FUNDO_CARD
            else:
                cor_fundo = Cores.FUNDO_APP

            for coluna in range(total_colunas):
                item = self.tabela_pilotos.item(row, coluna)
                if item is not None:
                    item.setBackground(QBrush(QColor(cor_fundo)))

    def _build_tab_equipes(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)

        self.tabela_equipes = QTableWidget()
        self.tabela_equipes.setColumnCount(4)
        self.tabela_equipes.setHorizontalHeaderLabels(
            ["POS", "EQUIPE", "PTS", "TAÇAS"]
        )
        self.tabela_equipes.setStyleSheet(Estilos.tabela())
        self.tabela_equipes.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_equipes.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela_equipes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_equipes.verticalHeader().setVisible(False)
        self.tabela_equipes.setShowGrid(False)
        self.tabela_equipes.cellDoubleClicked.connect(self._abrir_ficha_equipe_tabela)
        self._delegate_tabela_equipes = BadgeHeatmapDelegate(self.tabela_equipes)
        self.tabela_equipes.setItemDelegate(self._delegate_tabela_equipes)

        header = self.tabela_equipes.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)

        self.tabela_equipes.setColumnWidth(0, 58)
        self.tabela_equipes.setColumnWidth(2, 80)
        self.tabela_equipes.setColumnWidth(3, 230)

        layout.addWidget(self.tabela_equipes)

        legenda = QLabel("🏆 Classificação de construtores agregada • Duplo clique para ver ficha")
        legenda.setFont(Fontes.texto_pequeno())
        legenda.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
        layout.addWidget(legenda)

        return widget

    def _build_tab_proxima_corrida(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        self._rw_construir_layout_weekend(layout)
        self._rw_carregar_estado_persistido()
        self._rw_atualizar_tela_weekend()
        return widget


    def _rw_construir_layout_weekend(self, layout: QVBoxLayout) -> None:
        topo = QFrame()
        topo.setStyleSheet(
            f"background-color: {Cores.FUNDO_CARD}; border: 1px solid {Cores.BORDA}; border-radius: 8px;"
        )
        topo_layout = QVBoxLayout(topo)
        topo_layout.setContentsMargins(10, 8, 10, 8)
        topo_layout.setSpacing(6)

        nomes = ["Pre-Corrida", "Classificacao", "Corrida", "Resultado"]
        linha = QHBoxLayout()
        linha.setSpacing(6)
        self._rw_etapas_labels = []
        for indice, nome in enumerate(nomes):
            lbl = QLabel(nome)
            lbl.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
            self._rw_etapas_labels.append(lbl)
            linha.addWidget(lbl)
            if indice < len(nomes) - 1:
                seta = QLabel("->")
                seta.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
                linha.addWidget(seta)
        linha.addStretch(1)
        topo_layout.addLayout(linha)

        self._rw_progress = QProgressBar()
        self._rw_progress.setRange(0, 100)
        self._rw_progress.setValue(25)
        self._rw_progress.setTextVisible(True)
        self._rw_progress.setFormat("%p%")
        topo_layout.addWidget(self._rw_progress)
        layout.addWidget(topo)

        self._rw_stack = QStackedWidget()
        layout.addWidget(self._rw_stack, 1)

        pagina_pre = QWidget()
        pre_layout = QVBoxLayout(pagina_pre)
        pre_layout.setContentsMargins(0, 0, 0, 0)
        pre_layout.setSpacing(8)
        self.lbl_rw_pre_titulo = QLabel("RACE WEEKEND")
        self.lbl_rw_pre_titulo.setFont(Fontes.titulo_medio())
        self.lbl_rw_pre_subtitulo = QLabel("-")
        self.txt_rw_pre_briefing = QTextEdit()
        self.txt_rw_pre_briefing.setReadOnly(True)
        self.btn_ver_modificadores = BotaoSecondary("Ver Modificadores dos IAs")
        self.btn_ver_modificadores.clicked.connect(self._abrir_dialog_modificadores)
        self.btn_rw_pre_para_quali = BotaoPrimary("Prosseguir -> Quali")
        self.btn_rw_pre_para_quali.clicked.connect(lambda: self._rw_ir_para_etapa(1))
        botoes_pre = QHBoxLayout()
        botoes_pre.addStretch(1)
        botoes_pre.addWidget(self.btn_ver_modificadores)
        botoes_pre.addWidget(self.btn_rw_pre_para_quali)
        pre_layout.addWidget(self.lbl_rw_pre_titulo)
        pre_layout.addWidget(self.lbl_rw_pre_subtitulo)
        pre_layout.addWidget(self.txt_rw_pre_briefing, 1)
        pre_layout.addLayout(botoes_pre)
        self._rw_stack.addWidget(pagina_pre)

        pagina_quali = QWidget()
        quali_layout = QVBoxLayout(pagina_quali)
        quali_layout.setContentsMargins(0, 0, 0, 0)
        quali_layout.setSpacing(8)
        self.lbl_rw_quali_titulo = QLabel("CLASSIFICACAO")
        self.lbl_rw_quali_titulo.setFont(Fontes.titulo_medio())
        self.btn_rw_simular_quali = BotaoSuccess("Simular Classificacao")
        self.btn_rw_simular_quali.clicked.connect(self._rw_simular_quali)
        self.tbl_rw_quali = QTableWidget()
        self.tbl_rw_quali.setColumnCount(4)
        self.tbl_rw_quali.setHorizontalHeaderLabels(["Pos", "Piloto", "Equipe", "Score"])
        self.tbl_rw_quali.setStyleSheet(Estilos.tabela())
        self.tbl_rw_quali.setSelectionMode(QAbstractItemView.NoSelection)
        self.tbl_rw_quali.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_rw_quali.verticalHeader().setVisible(False)
        self.tbl_rw_quali.setShowGrid(False)
        head = self.tbl_rw_quali.horizontalHeader()
        head.setSectionResizeMode(0, QHeaderView.Fixed)
        head.setSectionResizeMode(1, QHeaderView.Stretch)
        head.setSectionResizeMode(2, QHeaderView.Stretch)
        head.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tbl_rw_quali.setColumnWidth(0, 68)
        self.tbl_rw_quali.setColumnWidth(3, 98)
        self.lbl_rw_quali_contexto = QLabel("Simule a classificacao para montar o grid.")
        botoes_quali = QHBoxLayout()
        self.btn_rw_quali_voltar = BotaoSecondary("<- Voltar")
        self.btn_rw_quali_voltar.clicked.connect(lambda: self._rw_ir_para_etapa(0))
        self.btn_rw_quali_para_corrida = BotaoPrimary("Prosseguir -> Corrida")
        self.btn_rw_quali_para_corrida.clicked.connect(lambda: self._rw_ir_para_etapa(2))
        self.btn_rw_quali_para_corrida.setVisible(False)
        botoes_quali.addWidget(self.btn_rw_quali_voltar)
        botoes_quali.addStretch(1)
        botoes_quali.addWidget(self.btn_rw_quali_para_corrida)
        quali_layout.addWidget(self.lbl_rw_quali_titulo)
        quali_layout.addWidget(self.btn_rw_simular_quali, 0, Qt.AlignLeft)
        quali_layout.addWidget(self.tbl_rw_quali, 1)
        quali_layout.addWidget(self.lbl_rw_quali_contexto)
        quali_layout.addLayout(botoes_quali)
        self._rw_stack.addWidget(pagina_quali)

        pagina_corrida = QWidget()
        corrida_layout = QVBoxLayout(pagina_corrida)
        corrida_layout.setContentsMargins(0, 0, 0, 0)
        corrida_layout.setSpacing(8)
        self.lbl_rw_corrida_titulo = QLabel("CORRIDA")
        self.lbl_rw_corrida_titulo.setFont(Fontes.titulo_medio())
        self.lbl_rw_corrida_contexto = QLabel("-")
        self.btn_rw_exportar_roster = BotaoSecondary("Exportar AI Season")
        self.btn_rw_exportar_roster.clicked.connect(self._rw_exportar_roster)
        self.lbl_rw_export_status = QLabel("AI Season + Roster ainda nao exportados.")
        self.input_rw_posicao = QLineEdit()
        self.input_rw_posicao.setPlaceholderText("Posicao final")
        self.btn_rw_registrar_posicao = BotaoSuccess("Registrar Resultado")
        self.btn_rw_registrar_posicao.clicked.connect(self._rw_registrar_resultado_manual)
        self.btn_rw_simular_corrida = BotaoPrimary("Simular Corrida")
        self.btn_rw_simular_corrida.clicked.connect(self._simular_corrida)
        self.btn_rw_corrida_voltar = BotaoSecondary("<- Voltar")
        self.btn_rw_corrida_voltar.clicked.connect(lambda: self._rw_ir_para_etapa(1))
        corrida_layout.addWidget(self.lbl_rw_corrida_titulo)
        corrida_layout.addWidget(self.lbl_rw_corrida_contexto)
        corrida_layout.addWidget(self.btn_rw_exportar_roster, 0, Qt.AlignLeft)
        corrida_layout.addWidget(self.lbl_rw_export_status)
        corrida_layout.addWidget(self.input_rw_posicao, 0, Qt.AlignLeft)
        corrida_layout.addWidget(self.btn_rw_registrar_posicao, 0, Qt.AlignLeft)
        corrida_layout.addWidget(QLabel("OU"), 0, Qt.AlignCenter)
        corrida_layout.addWidget(self.btn_rw_simular_corrida, 0, Qt.AlignLeft)
        corrida_layout.addStretch(1)
        corrida_layout.addWidget(self.btn_rw_corrida_voltar, 0, Qt.AlignLeft)
        self._rw_stack.addWidget(pagina_corrida)

        pagina_pos = QWidget()
        pos_layout = QVBoxLayout(pagina_pos)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_layout.setSpacing(8)
        self.lbl_rw_pos_titulo = QLabel("RESULTADO")
        self.lbl_rw_pos_titulo.setFont(Fontes.titulo_medio())
        self.txt_rw_pos = QTextEdit()
        self.txt_rw_pos.setReadOnly(True)
        self.btn_rw_proxima_rodada = BotaoPrimary("Proxima Rodada ->")
        self.btn_rw_proxima_rodada.clicked.connect(self._rw_proxima_rodada)
        pos_layout.addWidget(self.lbl_rw_pos_titulo)
        pos_layout.addWidget(self.txt_rw_pos, 1)
        pos_layout.addWidget(self.btn_rw_proxima_rodada, 0, Qt.AlignRight)
        self._rw_stack.addWidget(pagina_pos)

    def _rw_carregar_estado_persistido(self) -> None:
        self._rw_etapa_atual = 0
        self._rw_quali_resultado = []
        self._rw_roster_exportado = False
        self._rw_resultado_dialogo = {}

        estado = self.banco.get("race_weekend")
        if not isinstance(estado, dict):
            return

        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_atual = 1
        try:
            rodada_salva = int(estado.get("rodada", rodada_atual) or rodada_atual)
        except (TypeError, ValueError):
            rodada_salva = rodada_atual
        try:
            rodada_resultado = int(estado.get("rodada_resultado", rodada_salva) or rodada_salva)
        except (TypeError, ValueError):
            rodada_resultado = rodada_salva
        try:
            etapa = int(estado.get("etapa", 0) or 0)
        except (TypeError, ValueError):
            etapa = 0
        etapa = max(0, min(3, etapa))

        categoria_salva = str(estado.get("categoria_id", self.categoria_atual) or self.categoria_atual).strip()
        mesma_categoria = categoria_salva == str(self.categoria_atual or "").strip()
        mesmo_weekend = rodada_salva == rodada_atual
        restaurar_pos = etapa == 3 and rodada_resultado == max(1, rodada_atual - 1)

        if not mesma_categoria or (not mesmo_weekend and not restaurar_pos):
            return

        quali = estado.get("quali_resultado")
        if isinstance(quali, list):
            self._rw_quali_resultado = [item for item in quali if isinstance(item, dict)]
        self._rw_roster_exportado = bool(estado.get("roster_exportado", False))
        resultado_dialogo = estado.get("resultado_dialogo")
        if isinstance(resultado_dialogo, dict):
            self._rw_resultado_dialogo = dict(resultado_dialogo)
        self._rw_etapa_atual = etapa

    def _rw_salvar_estado_persistido(self) -> None:
        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_atual = 1

        rodada_resultado = rodada_atual
        if isinstance(self._rw_resultado_dialogo, dict):
            try:
                rodada_resultado = int(
                    self._rw_resultado_dialogo.get(
                        "rodada_resultado",
                        self._rw_resultado_dialogo.get("rodada", rodada_resultado),
                    )
                    or rodada_resultado
                )
            except (TypeError, ValueError):
                rodada_resultado = rodada_atual

        self.banco["race_weekend"] = {
            "categoria_id": str(self.categoria_atual or ""),
            "rodada": rodada_resultado if self._rw_etapa_atual == 3 else rodada_atual,
            "rodada_resultado": rodada_resultado,
            "etapa": int(max(0, min(3, self._rw_etapa_atual))),
            "quali_resultado": [item for item in self._rw_quali_resultado if isinstance(item, dict)],
            "roster_exportado": bool(self._rw_roster_exportado),
            "resultado_dialogo": dict(self._rw_resultado_dialogo) if isinstance(self._rw_resultado_dialogo, dict) else {},
        }
        salvar_banco(self.banco)

    def _rw_ir_para_etapa(self, etapa: int) -> None:
        self._rw_etapa_atual = max(0, min(3, int(etapa)))
        self._rw_salvar_estado_persistido()
        self._rw_atualizar_tela_weekend()

    def _rw_atualizar_barra_progresso(self) -> None:
        labels = getattr(self, "_rw_etapas_labels", [])
        for indice, lbl in enumerate(labels):
            if indice < self._rw_etapa_atual:
                lbl.setStyleSheet(f"color: {Cores.VERDE}; border: none; font-weight: 700;")
            elif indice == self._rw_etapa_atual:
                lbl.setStyleSheet(f"color: {Cores.ACCENT_PRIMARY}; border: none; font-weight: 700;")
            else:
                lbl.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")

        if hasattr(self, "_rw_progress"):
            porcentagem = int(((self._rw_etapa_atual + 1) / 4.0) * 100.0)
            self._rw_progress.setValue(max(0, min(100, porcentagem)))

    def _rw_obter_equipe_por_id(self, equipe_id: Any) -> dict[str, Any] | None:
        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if self._ids_equivalentes_resultado(equipe.get("id"), equipe_id):
                return equipe
        return None

    def _obter_expectativa_e_avaliacao(
        self,
        *,
        persistir_historico: bool = False,
        rodada_ref: int | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]] | tuple[None, None]:
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return None, None

        equipe = obter_equipe_piloto(self.banco, jogador) or self._rw_obter_equipe_por_id(jogador.get("equipe_id"))
        expectativa = calcular_expectativa_equipe(jogador, equipe, self.banco)
        avaliacao = avaliar_desempenho_vs_expectativa(jogador, expectativa, self.banco)

        if persistir_historico:
            try:
                rodada = int(rodada_ref if rodada_ref is not None else self.banco.get("rodada_atual", 1) or 1)
            except (TypeError, ValueError):
                rodada = 1
            registrar_avaliacao_historico(
                self.banco,
                rodada=max(1, rodada),
                categoria_id=str(jogador.get("categoria_atual", self.categoria_atual) or self.categoria_atual),
                avaliacao=avaliacao,
            )
        return expectativa, avaliacao

    def _rw_obter_alerta_contratual_visual(self, avaliacao: dict[str, Any] | None = None) -> dict[str, Any] | None:
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return None
        try:
            rodada = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada = 1
        total = max(1, self._obter_total_rodadas_temporada())
        return gerar_alerta_contratual(
            jogador,
            self.banco,
            rodada,
            total,
            avaliacao=avaliacao,
            ignorar_cadencia=True,
        )

    def _processar_alerta_contratual_pos_corrida(
        self,
        rodada_processada: int,
        avaliacao: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return None

        total = max(1, self._obter_total_rodadas_temporada())
        alerta = gerar_alerta_contratual(
            jogador,
            self.banco,
            max(1, int(rodada_processada)),
            total,
            avaliacao=avaliacao,
            ignorar_cadencia=False,
        )
        if not isinstance(alerta, dict):
            return None

        registrar_alerta_contratual(
            self.banco,
            rodada_atual=max(1, int(rodada_processada)),
            categoria_id=str(self.categoria_atual or ""),
            alerta=alerta,
        )

        try:
            gerador = self._obter_gerador_noticias()
            temporada = int(self.banco.get("ano_atual", 2024) or 2024)
            categoria_id = str(self.categoria_atual or "")
            categoria_nome = obter_nome_categoria(categoria_id)
            titulo = str(alerta.get("titulo", "Contrato") or "Contrato")
            texto = str(alerta.get("texto", "") or "").strip()
            detalhe = str(alerta.get("detalhe", "") or "").strip()
            mensagem = texto if not detalhe else f"{texto} {detalhe}"
            chave = f"contrato:{temporada}:{categoria_id}:{rodada_processada}:{titulo.casefold()}"
            gerador.adicionar(
                tipo="mercado",
                icone=str(alerta.get("icone", "")),
                titulo=f"Contrato - {titulo}",
                texto=mensagem or "Atualizacao contratual.",
                rodada=max(1, int(rodada_processada)),
                temporada=temporada,
                categoria_id=categoria_id,
                categoria_nome=categoria_nome,
                chave=chave,
            )
        except Exception:
            pass

        return alerta

    def _rw_montar_briefing_pre_corrida(
        self,
        corrida: dict[str, Any] | None,
    ) -> str:
        if not isinstance(corrida, dict):
            return "Temporada concluida. Finalize a temporada para iniciar o proximo ciclo."

        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            return "Jogador nao encontrado."

        categoria = str(jogador.get("categoria_atual", self.categoria_atual) or self.categoria_atual)
        pilotos_categoria = [
            p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict)
            and str(p.get("categoria_atual", "") or "").strip() == categoria
            and not bool(p.get("aposentado", False))
            and str(p.get("status", "ativo") or "ativo").strip().lower() not in {"aposentado", "livre", "reserva"}
        ]

        nome_circuito = str(corrida.get("circuito", corrida.get("nome", "Circuito")) or "Circuito")
        briefing = BRIEFINGS_CIRCUITO.get(nome_circuito, BRIEFINGS_CIRCUITO.get("_default", "Circuito desafiador."))
        clima = str(corrida.get("clima", "Seco") or "Seco")

        fator_chuva = int(jogador.get("fator_chuva", 50) or 50)
        historico_circuitos = jogador.get("historico_circuitos", {})
        if not isinstance(historico_circuitos, dict):
            historico_circuitos = {}
        track_id_raw = corrida.get("trackId", corrida.get("id", ""))
        track_id = str(track_id_raw or "")

        entrada_historico = None
        if track_id:
            chaves_busca: list[Any] = [track_id]
            try:
                track_id_int = int(float(track_id_raw))
            except (TypeError, ValueError):
                track_id_int = None
            if track_id_int is not None:
                chaves_busca.extend([track_id_int, str(track_id_int)])

            for chave in chaves_busca:
                if chave in historico_circuitos:
                    entrada_historico = historico_circuitos.get(chave)
                    break

        def _int_seguro_local(valor: Any, padrao: int = 0) -> int:
            try:
                return int(float(valor))
            except (TypeError, ValueError):
                return padrao

        if isinstance(entrada_historico, dict):
            vezes_no_circuito = _int_seguro_local(
                entrada_historico.get(
                    "corridas",
                    entrada_historico.get(
                        "vezes",
                        entrada_historico.get("participacoes", entrada_historico.get("times", 0)),
                    ),
                ),
                0,
            )
        else:
            vezes_no_circuito = _int_seguro_local(entrada_historico, 0)
        vezes_no_circuito = max(0, vezes_no_circuito)
        corridas_na_cat = int(jogador.get("corridas_na_categoria", 0) or 0)

        def _score_favorito(piloto: dict[str, Any]) -> int:
            equipe = self._rw_obter_equipe_por_id(piloto.get("equipe_id")) or {}
            try:
                skill = int(float(piloto.get("skill", 0) or 0))
            except (TypeError, ValueError):
                skill = 0
            try:
                car_perf = int(float(equipe.get("car_performance", 50) or 50))
            except (TypeError, ValueError):
                car_perf = 50
            return skill + car_perf

        favorito = max(pilotos_categoria, key=_score_favorito) if pilotos_categoria else None

        rival = None
        rivalidades = jogador.get("rivalidades", [])
        rival_ids: list[Any] = []
        if isinstance(rivalidades, list):
            for item in rivalidades:
                rival_id = item.get("piloto_id", item.get("id")) if isinstance(item, dict) else item
                if rival_id not in (None, ""):
                    rival_ids.append(rival_id)
        if rival_ids:
            for piloto in pilotos_categoria:
                if any(self._ids_equivalentes_resultado(piloto.get("id"), rid) for rid in rival_ids):
                    rival = piloto
                    break

        equipe_id_jogador = jogador.get("equipe_id")
        companheiro = next(
            (
                piloto
                for piloto in pilotos_categoria
                if not self._ids_equivalentes_resultado(piloto.get("id"), jogador.get("id"))
                and self._ids_equivalentes_resultado(piloto.get("equipe_id"), equipe_id_jogador)
            ),
            None,
        )

        classificacao = obter_classificacao_categoria(self.banco, categoria)
        posicao_jogador = next(
            (
                int(item.get("posicao", 0) or 0)
                for item in classificacao
                if isinstance(item, dict) and self._ids_equivalentes_resultado(item.get("piloto_id"), jogador.get("id"))
            ),
            0,
        )
        pontos_jogador = int(jogador.get("pontos_temporada", 0) or 0)
        pontos_lider = int(classificacao[0].get("pontos", 0) or 0) if classificacao else 0
        diferenca = max(0, pontos_lider - pontos_jogador)
        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_atual = 1
        total_rodadas = max(1, self._obter_total_rodadas_temporada())
        corridas_restantes = max(0, total_rodadas - rodada_atual)
        pontos_maximos_restantes = corridas_restantes * 25
        if diferenca <= 0:
            situacao_titulo = "Lider no campeonato."
        elif diferenca <= pontos_maximos_restantes * 0.3:
            situacao_titulo = "Titulo ao alcance."
        elif diferenca <= pontos_maximos_restantes * 0.6:
            situacao_titulo = "Titulo dificil, mas possivel."
        elif diferenca <= pontos_maximos_restantes:
            situacao_titulo = "Titulo muito dificil."
        else:
            situacao_titulo = "Matematicamente eliminado."

        expectativa, avaliacao = self._obter_expectativa_e_avaliacao()
        alerta_contrato = self._rw_obter_alerta_contratual_visual(avaliacao=avaliacao)

        linhas = [
            "-- BRIEFING DO CIRCUITO --",
            briefing,
            f"Clima previsto: {clima}",
            "",
            "-- ALERTAS DO JOGADOR --",
            f"Fator de chuva: {fator_chuva}/100",
            (
                "Primeira vez neste circuito: atencao a penalidade de adaptacao."
                if vezes_no_circuito <= 0
                else f"Experiencia no circuito: {vezes_no_circuito} corrida(s)."
            ),
            (
                f"Categoria ainda em adaptacao ({corridas_na_cat} corrida(s))."
                if corridas_na_cat < 5
                else f"Experiencia na categoria: {corridas_na_cat} corrida(s)."
            ),
            "",
            "-- DESTAQUES DO GRID --",
        ]
        if isinstance(favorito, dict):
            equipe_fav = self._rw_obter_equipe_por_id(favorito.get("equipe_id")) or {}
            linhas.append(
                f"Favorito: {favorito.get('nome', 'Piloto')} (skill {int(favorito.get('skill', 0) or 0)}, carro {int(equipe_fav.get('car_performance', 50) or 50)})"
            )
        if isinstance(rival, dict):
            linhas.append(f"Rival no grid: {rival.get('nome', 'Rival')}.")
        if isinstance(companheiro, dict):
            linhas.append(f"Companheiro no grid: {companheiro.get('nome', 'Companheiro')}.")
        linhas.extend(
            [
                "",
                "-- CONTEXTO DO CAMPEONATO --",
                (f"Sua posicao: {posicao_jogador}o ({pontos_jogador} pts)" if posicao_jogador > 0 else "Sua posicao: sem dados"),
                f"Lider: {pontos_lider} pts | Diferenca: -{diferenca} pts",
                f"Restam {corridas_restantes} corrida(s) | Maximo possivel: {pontos_maximos_restantes} pts",
                f"Situacao do titulo: {situacao_titulo}",
            ]
        )
        if isinstance(expectativa, dict) and isinstance(avaliacao, dict):
            linhas.extend(
                [
                    "",
                    "-- EXPECTATIVAS DA EQUIPE --",
                    f"Equipe espera: {expectativa.get('texto_faixa', 'Top')}.",
                    f"Atual: {int(avaliacao.get('posicao_real', 0) or 0)}o - {avaliacao.get('emoji', '')} {avaliacao.get('texto', '')}",
                    f"Impacto: {avaliacao.get('impacto', '')}",
                ]
            )
        if isinstance(alerta_contrato, dict):
            linhas.extend(
                [
                    "",
                    "-- TENSAO CONTRATUAL --",
                    str(alerta_contrato.get("titulo", "Contrato")),
                    str(alerta_contrato.get("texto", "")),
                    str(alerta_contrato.get("detalhe", "")),
                ]
            )
        return "\n".join(item for item in linhas if item is not None)

    def _rw_atualizar_pre_corrida(self, corrida: dict[str, Any] | None) -> None:
        if not hasattr(self, "lbl_rw_pre_titulo"):
            return
        if not isinstance(corrida, dict):
            self.lbl_rw_pre_titulo.setText("RACE WEEKEND")
            self.lbl_rw_pre_subtitulo.setText("Temporada concluida")
            self.txt_rw_pre_briefing.setText("Nao ha corrida pendente.")
            self.btn_rw_pre_para_quali.setEnabled(False)
            return

        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_atual = 1
        total = max(1, self._obter_total_rodadas_temporada())
        circuito = str(corrida.get("circuito", corrida.get("nome", "Circuito")) or "Circuito")
        clima = str(corrida.get("clima", "Seco") or "Seco")
        self.lbl_rw_pre_titulo.setText(f"RACE WEEKEND - Rodada {min(max(rodada_atual, 1), total)}/{total}")
        self.lbl_rw_pre_subtitulo.setText(f"{circuito} | {clima}")
        self.txt_rw_pre_briefing.setText(self._rw_montar_briefing_pre_corrida(corrida))
        self.btn_rw_pre_para_quali.setEnabled(True)

    def _rw_atualizar_quali(self) -> None:
        if not hasattr(self, "tbl_rw_quali"):
            return
        tabela = self.tbl_rw_quali
        tabela.clearContents()
        grid = [item for item in self._rw_quali_resultado if isinstance(item, dict)]
        tabela.setRowCount(len(grid) if grid else 1)

        if not grid:
            for col in range(4):
                texto = "Simule a classificacao para gerar o grid." if col == 1 else "-"
                item = self._criar_item_tabela(texto, Cores.TEXTO_MUTED, Cores.FUNDO_CARD)
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter if col == 1 else Qt.AlignCenter)
                tabela.setItem(0, col, item)
            self.btn_rw_quali_para_corrida.setVisible(False)
            self.lbl_rw_quali_contexto.setText("Seu companheiro e rival aparecerao apos a simulacao.")
            return

        jogador = self._obter_jogador()
        jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
        equipe_id_jogador = jogador.get("equipe_id") if isinstance(jogador, dict) else None
        rival_ids = []
        rivalidades = jogador.get("rivalidades", []) if isinstance(jogador, dict) else []
        if isinstance(rivalidades, list):
            for item in rivalidades:
                rival_id = item.get("piloto_id", item.get("id")) if isinstance(item, dict) else item
                if rival_id not in (None, ""):
                    rival_ids.append(rival_id)

        pos_companheiro = "-"
        pos_rival = "-"
        for indice, entrada in enumerate(grid):
            posicao = int(entrada.get("posicao_campeonato", entrada.get("posicao", indice + 1)) or (indice + 1))
            piloto_id = entrada.get("piloto_id")
            nome = str(entrada.get("piloto_nome", "Piloto") or "Piloto")
            equipe = str(entrada.get("equipe_nome", "Equipe") or "Equipe")
            score = float(entrada.get("quali_score", 0.0) or 0.0)

            is_jogador = self._ids_equivalentes_resultado(piloto_id, jogador_id)
            is_companheiro = (
                not is_jogador
                and equipe_id_jogador not in (None, "")
                and self._ids_equivalentes_resultado(entrada.get("equipe_id"), equipe_id_jogador)
            )
            is_rival = any(self._ids_equivalentes_resultado(piloto_id, rid) for rid in rival_ids)
            cor_fundo = Cores.FUNDO_CARD if indice % 2 == 0 else Cores.FUNDO_APP
            if is_jogador:
                cor_fundo = "#173b5f"
                nome = f"[VOCE] {nome}"
            elif is_companheiro:
                cor_fundo = "#2a2f4f"
                pos_companheiro = f"P{posicao}"
            elif is_rival:
                cor_fundo = "#4a2b2b"
                pos_rival = f"P{posicao}"

            tabela.setRowHeight(indice, 30)
            tabela.setItem(indice, 0, self._criar_item_tabela(f"P{posicao}", Cores.TEXTO_PRIMARY, cor_fundo, Qt.AlignCenter))
            tabela.setItem(indice, 1, self._criar_item_tabela(nome, Cores.TEXTO_PRIMARY, cor_fundo))
            tabela.setItem(indice, 2, self._criar_item_tabela(equipe, Cores.TEXTO_SECONDARY, cor_fundo))
            tabela.setItem(indice, 3, self._criar_item_tabela(f"{score:.2f}", Cores.ACCENT_PRIMARY, cor_fundo, Qt.AlignCenter))

        partes = []
        if pos_companheiro != "-":
            partes.append(f"Companheiro: {pos_companheiro}")
        if pos_rival != "-":
            partes.append(f"Rival: {pos_rival}")
        self.lbl_rw_quali_contexto.setText(" | ".join(partes) if partes else "Grid pronto para a largada.")
        self.btn_rw_quali_para_corrida.setVisible(True)

    def _rw_atualizar_corrida(self, corrida: dict[str, Any] | None) -> None:
        if not hasattr(self, "lbl_rw_corrida_titulo"):
            return
        if not isinstance(corrida, dict):
            self.lbl_rw_corrida_titulo.setText("CORRIDA")
            self.lbl_rw_corrida_contexto.setText("Sem corrida pendente.")
            return

        circuito = str(corrida.get("circuito", corrida.get("nome", "Circuito")) or "Circuito")
        clima = str(corrida.get("clima", "Seco") or "Seco")
        grid = [item for item in self._rw_quali_resultado if isinstance(item, dict)]
        jogador = self._obter_jogador()
        jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
        pos_jogador_grid = next(
            (
                int(item.get("posicao_campeonato", item.get("posicao", 0)) or 0)
                for item in grid
                if self._ids_equivalentes_resultado(item.get("piloto_id"), jogador_id)
            ),
            0,
        )
        texto_largada = f"Voce larga de P{pos_jogador_grid}" if pos_jogador_grid > 0 else "Grid ainda nao definido"
        self.lbl_rw_corrida_titulo.setText(f"CORRIDA - {circuito}")
        self.lbl_rw_corrida_contexto.setText(
            f"{texto_largada} | Grid: {len(grid) if grid else '-'} pilotos | Clima: {clima}"
        )

        if self._rw_roster_exportado:
            self.lbl_rw_export_status.setStyleSheet(f"color: {Cores.VERDE}; border: none;")
            self.lbl_rw_export_status.setText("AI Season + Roster exportados com sucesso.")
        else:
            self.lbl_rw_export_status.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
            self.lbl_rw_export_status.setText("AI Season + Roster ainda nao exportados.")

    def _rw_atualizar_pos_corrida(self) -> None:
        if not hasattr(self, "txt_rw_pos"):
            return
        if not isinstance(self._rw_resultado_dialogo, dict) or not self._rw_resultado_dialogo:
            self.lbl_rw_pos_titulo.setText("RESULTADO")
            self.txt_rw_pos.setText("Resultado sera exibido aqui apos concluir a corrida.")
            self.btn_rw_proxima_rodada.setText("Proxima Rodada ->")
            return

        from UI.dialogs import montar_texto_resultado_corrida

        titulo = str(self._rw_resultado_dialogo.get("titulo", "Resultado") or "Resultado")
        self.lbl_rw_pos_titulo.setText(titulo)
        self.txt_rw_pos.setText(montar_texto_resultado_corrida(self._rw_resultado_dialogo))
        self.btn_rw_proxima_rodada.setText("Fim de Temporada ->" if self._temporada_concluida() else "Proxima Rodada ->")

    def _rw_atualizar_tela_weekend(self) -> None:
        if not hasattr(self, "_rw_stack"):
            return
        evento = self._get_proximo_evento_exibicao()
        corrida = evento if isinstance(evento, dict) else self._get_corrida_atual()
        self._rw_atualizar_barra_progresso()
        self._rw_atualizar_pre_corrida(corrida)
        self._rw_atualizar_quali()
        self._rw_atualizar_corrida(corrida)
        self._rw_atualizar_pos_corrida()
        self._rw_stack.setCurrentIndex(max(0, min(3, self._rw_etapa_atual)))

    def _rw_simular_quali(self) -> None:
        grid = self._simular_classificacao(retornar_resultado=True)
        if not isinstance(grid, list) or not grid:
            return
        self._rw_quali_resultado = [item for item in grid if isinstance(item, dict)]
        self._rw_etapa_atual = max(1, self._rw_etapa_atual)
        self._rw_salvar_estado_persistido()
        self._rw_atualizar_tela_weekend()

    def _rw_exportar_roster(self) -> None:
        self._exportar_aiseason(silencioso=True)
        self._rw_roster_exportado = False
        obter_nome = getattr(self, "_obter_nome_roster_categoria", None)
        obter_arquivo = getattr(self, "_obter_arquivo_roster_categoria", None)
        obter_arquivo_season = getattr(self, "_obter_arquivo_season_evento_atual", None)
        if callable(obter_nome) and callable(obter_arquivo):
            try:
                arquivo_roster = str(obter_arquivo(obter_nome()) or "").strip()
                arquivo_season = (
                    str(obter_arquivo_season() or "").strip()
                    if callable(obter_arquivo_season)
                    else ""
                )
                self._rw_roster_exportado = bool(
                    arquivo_roster
                    and os.path.isfile(arquivo_roster)
                    and arquivo_season
                    and os.path.isfile(arquivo_season)
                )
            except Exception:
                self._rw_roster_exportado = False
        self._rw_salvar_estado_persistido()
        self._rw_atualizar_tela_weekend()

    def _rw_ajustar_resultado_para_posicao_jogador(
        self,
        classificacao: list[dict[str, Any]],
        posicao_alvo: int,
    ) -> list[dict[str, Any]]:
        resultado = [dict(item) for item in classificacao if isinstance(item, dict)]
        if not resultado:
            return []

        jogador = self._obter_jogador()
        jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
        indice_jogador = next(
            (
                indice
                for indice, item in enumerate(resultado)
                if self._ids_equivalentes_resultado(item.get("piloto_id"), jogador_id)
                or bool(item.get("is_jogador", False))
            ),
            -1,
        )
        if indice_jogador < 0:
            return resultado

        entrada_jogador = resultado.pop(indice_jogador)
        posicao_real = max(1, min(int(posicao_alvo), len(resultado) + 1))
        resultado.insert(posicao_real - 1, entrada_jogador)

        for indice, item in enumerate(resultado, start=1):
            dnf = bool(item.get("dnf", False))
            volta_rapida = bool(item.get("volta_rapida", False))
            item["posicao"] = indice
            item["posicao_geral"] = indice
            item["posicao_classe"] = indice
            item["posicao_campeonato"] = indice
            item["pontos"] = self._calcular_pontos_da_posicao(
                posicao=indice,
                volta_rapida=volta_rapida,
                dnf=dnf,
            )
        return resultado

    def _rw_registrar_resultado_manual(self) -> None:
        texto_pos = str(self.input_rw_posicao.text() if hasattr(self, "input_rw_posicao") else "").strip()
        if not texto_pos:
            QMessageBox.warning(self, "Aviso", "Informe sua posicao final para registrar o resultado.")
            return
        try:
            posicao_final = int(texto_pos)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Aviso", "Posicao invalida. Use um numero inteiro.")
            return
        if posicao_final <= 0:
            QMessageBox.warning(self, "Aviso", "A posicao deve ser maior que zero.")
            return

        corrida = self._get_corrida_atual()
        if not isinstance(corrida, dict):
            QMessageBox.warning(self, "Aviso", "Nao ha corrida disponivel para registrar resultado.")
            return

        try:
            from Logica.simulacao import simular_corrida_categoria_detalhada

            resultado_detalhado = simular_corrida_categoria_detalhada(self.banco, self.categoria_atual)
            classificacao_base = resultado_detalhado.get("classificacao", []) if isinstance(resultado_detalhado, dict) else []
            classificacao_base = [item for item in classificacao_base if isinstance(item, dict)]
            if not classificacao_base:
                QMessageBox.warning(self, "Aviso", "Nao foi possivel gerar classificacao base para registro manual.")
                return

            classificacao = self._rw_ajustar_resultado_para_posicao_jogador(classificacao_base, posicao_final)
            pontos_antes = self._snapshot_pontos_categoria(self.categoria_atual)
            lesoes_antes = self._snapshot_lesoes_categoria(self.categoria_atual)
            ordens_antes = self._snapshot_ordens_hierarquia_categoria(self.categoria_atual)
            rodada_processada = int(self.banco.get("rodada_atual", 1) or 1)

            aplicados = self._aplicar_classificacao_por_id(
                classificacao,
                rodada=rodada_processada,
                foi_corrida_jogador=True,
            )
            if aplicados <= 0:
                QMessageBox.warning(self, "Aviso", "Nenhum resultado pode ser aplicado para o registro manual.")
                return

            calcular_pontos_equipes(self.banco, self.categoria_atual)
            resumo_outras_categorias = self._simular_rodada_todas_categorias(
                rodada_referencia=int(self.banco.get("rodada_atual", 1) or 1),
            )
            self._avancar_rodada()
            self._atualizar_tudo()

            outras_categorias = []
            for categoria_id, info in (resumo_outras_categorias or {}).items():
                if not isinstance(info, dict):
                    continue
                outras_categorias.append(
                    {
                        "categoria_id": categoria_id,
                        "categoria_nome": obter_nome_categoria(str(categoria_id)),
                        "rodada": int(info.get("rodada", 0) or 0),
                        "vencedor": str(info.get("vencedor", "Sem vencedor") or "Sem vencedor"),
                    }
                )

            self._abrir_resultado_corrida_detalhado(
                classificacao=classificacao,
                corrida=corrida,
                categoria_id=self.categoria_atual,
                rodada=rodada_processada,
                pontos_antes=pontos_antes,
                lesoes_antes=lesoes_antes,
                ordens_antes=ordens_antes,
                outras_categorias=outras_categorias,
            )
        except Exception as erro:
            QMessageBox.critical(self, "Erro", f"Erro ao registrar resultado manual:\n{erro}")

    def _rw_receber_resultado_dialogo(
        self,
        dados_dialogo: dict[str, Any],
        *,
        rodada_resultado: int | None = None,
    ) -> bool:
        if not isinstance(dados_dialogo, dict):
            return False
        payload = dict(dados_dialogo)
        if rodada_resultado is not None:
            payload["rodada_resultado"] = int(rodada_resultado)
        self._rw_resultado_dialogo = payload
        self._rw_etapa_atual = 3
        self._rw_salvar_estado_persistido()
        self._rw_atualizar_tela_weekend()
        return True

    def _rw_proxima_rodada(self) -> None:
        if self._temporada_concluida():
            self._finalizar_temporada()
            return
        self._rw_etapa_atual = 0
        self._rw_quali_resultado = []
        self._rw_roster_exportado = False
        self._rw_resultado_dialogo = {}
        if hasattr(self, "input_rw_posicao"):
            self.input_rw_posicao.clear()
        self._rw_salvar_estado_persistido()
        self._rw_atualizar_tela_weekend()

    def _criar_grafico_equipes_dashboard(self) -> QWidget:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 10, 0, 0)
        wrapper_layout.setSpacing(8)

        # Título do gráfico
        lbl_titulo = QLabel("EVOLUÇÃO DAS EQUIPES (HISTÓRICO)")
        lbl_titulo.setFont(Fontes.texto_pequeno())
        lbl_titulo.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; font-weight: bold; letter-spacing: 0.5px;")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        wrapper_layout.addWidget(lbl_titulo)

        self._lbl_grafico_equipes = QLabel()
        self._lbl_grafico_equipes.setAlignment(Qt.AlignCenter)
        self._lbl_grafico_equipes.setMinimumHeight(140)
        self._lbl_grafico_equipes.setStyleSheet(f"background-color: {Cores.FUNDO_CARD}; border-radius: 6px; border: 1px solid {Cores.BORDA};")
        wrapper_layout.addWidget(self._lbl_grafico_equipes)

        return wrapper

    def _atualizar_grafico_equipes_dashboard(self) -> None:
        if not hasattr(self, "_lbl_grafico_equipes"):
            return

        # Coletar histórico de todas as equipes
        hist_all = self.banco.get("historico_temporadas_completas", [])
        if not hist_all:
            self._lbl_grafico_equipes.setText("Nenhum histórico disponível para gráfico.")
            self._lbl_grafico_equipes.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            return

        cat_id = self.categoria_atual
        
        # Estrutura: dados[nome_equipe] = list of tuples (ano, posicao, cor)
        dados_por_equipe = {}
        for temp in hist_all:
            if not isinstance(temp, dict):
                continue
            cat_t = str(temp.get("categoria_id", "") or "").strip().casefold()
            if cat_id and cat_t != cat_id:
                continue
            ano = 0
            try:
                ano = int(temp.get("ano", 0))
            except (TypeError, ValueError):
                pass
            
            for entrada in temp.get("classificacao", []):
                if not isinstance(entrada, dict):
                    continue
                eq_nome = str(entrada.get("equipe", "") or "").strip()
                eq_key = self._normalizar_chave_equipe_tabela(eq_nome)
                pos = 0
                try:
                    pos = int(entrada.get("posicao", 0))
                except (TypeError, ValueError):
                    pass
                cor = str(entrada.get("cor_primaria", "") or "").strip()
                if eq_key and pos > 0:
                    if eq_key not in dados_por_equipe:
                        dados_por_equipe[eq_key] = []
                    dados_por_equipe[eq_key].append((ano, pos, cor))

        # Adicionar posições atuais se a temporada ainda estiver rolando (ou usar da atual)
        ano_atual = int(self.banco.get("ano_atual", 2024))
        for eq in self.equipes_ordenadas:
            eq_nome = str(eq.get("nome", "") or "").strip()
            eq_key = self._normalizar_chave_equipe_tabela(eq_nome)
            cor = str(eq.get("cor_primaria", "") or "").strip()
            # A posicao atual é o indice na lista (que ja está ordenada) + 1
            pos_atual = self.equipes_ordenadas.index(eq) + 1
            if eq_key:
                if eq_key not in dados_por_equipe:
                    dados_por_equipe[eq_key] = []
                # Evitar duplicar o ano atual se já estiver no histórico
                ja_tem_ano = any(a == ano_atual for a, p, c in dados_por_equipe[eq_key])
                if not ja_tem_ano:
                    dados_por_equipe[eq_key].append((ano_atual, pos_atual, cor))

        if not dados_por_equipe:
            self._lbl_grafico_equipes.setText("Dados insuficientes.")
            return

        anos_all = set()
        pos_max = max(5, len(self.equipes_ordenadas))
        for eq_key, lista in dados_por_equipe.items():
            lista.sort(key=lambda x: x[0])  # Ordenar por ano crescente
            for ano, pos, cor in lista:
                anos_all.add(ano)
                
        anos_ordenados = sorted(list(anos_all))
        if not anos_ordenados:
            return

        largura = 580
        altura = 130
        pixmap = QPixmap(largura, altura)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        margem_esq = 30
        margem_dir = 15
        margem_top = 10
        margem_base = 20
        area_largura = max(1, largura - margem_esq - margem_dir)
        area_altura = max(1, altura - margem_top - margem_base)

        # Grade horizontal
        painter.setPen(QPen(QColor(Cores.BORDA), 1))
        for frac in (0.25, 0.5, 0.75, 1.0):
            y = int(margem_top + frac * area_altura)
            painter.drawLine(margem_esq, y, largura - margem_dir, y)
            
            pos_lbl = 1 + int(round(frac * (pos_max - 1)))
            painter.setPen(QPen(QColor(Cores.TEXTO_MUTED), 1))
            painter.setFont(Fontes.texto_pequeno())
            painter.drawText(2, y + 4, f"{pos_lbl}º")
            painter.setPen(QPen(QColor(Cores.BORDA), 1))

        # Eixo Y superior (1º lugar)
        painter.drawLine(margem_esq, margem_top, largura - margem_dir, margem_top)
        painter.setPen(QPen(QColor(Cores.OURO), 1))
        painter.drawText(2, margem_top + 4, "1º")

        # Desenhar as linhas de cada equipe
        passo_x = area_largura / max(1, len(anos_ordenados) - 1) if len(anos_ordenados) > 1 else area_largura
        
        eq_destaque = getattr(self, "_equipe_chave_destacada_tabela", "")
        
        for eq_key, lista in dados_por_equipe.items():
            is_destaque = (eq_key == eq_destaque) or not eq_destaque
            cor_base = lista[-1][2] if lista and lista[-1][2] else Cores.TEXTO_SECONDARY
            
            espessura = 3 if is_destaque else 1
            opacidade = 255 if is_destaque else 40
            
            cor = QColor(cor_base)
            cor.setAlpha(opacidade)
            
            painter.setPen(QPen(cor, espessura))
            
            pontos = []
            for ano, pos, _ in lista:
                if ano in anos_ordenados:
                    idx_ano = anos_ordenados.index(ano)
                    x = margem_esq + idx_ano * passo_x
                    pos_calc = min(pos, pos_max)
                    y = margem_top + ((pos_calc - 1) / max(1, pos_max - 1)) * area_altura
                    pontos.append((x, y, pos))
            
            if len(pontos) >= 2:
                for indice in range(1, len(pontos)):
                    x0, y0, _ = pontos[indice - 1]
                    x1, y1, _ = pontos[indice]
                    painter.drawLine(int(x0), int(y0), int(x1), int(y1))
            
            if is_destaque:
                for x, y, pos in pontos:
                    painter.setPen(QPen(QColor(Cores.FUNDO_CARD), 1))
                    painter.setBrush(cor)
                    painter.drawEllipse(QPoint(int(x), int(y)), 3, 3)

        # Desenhar os rótulos de ano no eixo X no final para ficar por cima
        painter.setPen(QPen(QColor(Cores.TEXTO_MUTED), 1))
        painter.setFont(Fontes.texto_pequeno())
        for idx_ano, ano in enumerate(anos_ordenados):
            x = margem_esq + idx_ano * passo_x
            painter.drawText(int(x - 10), altura - 4, str(ano))

        painter.end()
        self._lbl_grafico_equipes.setPixmap(pixmap)

    def _build_tab_minha_equipe(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        card_equipe = CardTitulo("Minha Equipe")

        self.frame_barra_equipe = QFrame()
        self.frame_barra_equipe.setFixedHeight(3)
        self.frame_barra_equipe.setStyleSheet(
            f"background-color: {Cores.ACCENT_PRIMARY}; border: none; border-radius: 1px;"
        )
        card_equipe.add(self.frame_barra_equipe)

        self.lbl_minha_equipe_nome = QLabel("Sem equipe")
        self.lbl_minha_equipe_nome.setFont(Fontes.titulo_medio())
        self.lbl_minha_equipe_nome.setStyleSheet(
            f"color: {Cores.ACCENT_PRIMARY}; border: none; background: transparent;"
        )
        card_equipe.add(self.lbl_minha_equipe_nome)

        card_equipe.add(Separador())

        self.bar_aero = BarraProgresso("Aero", 0, cor=Cores.ACCENT_PRIMARY)
        self.bar_motor = BarraProgresso("Motor", 0, cor=Cores.ACCENT_PRIMARY)
        self.bar_chassi = BarraProgresso("Chassi", 0, cor=Cores.ACCENT_PRIMARY)
        self.bar_confiab = BarraProgresso("Confiab.", 0, cor=Cores.AMARELO)

        card_equipe.add(self.bar_aero)
        card_equipe.add(self.bar_motor)
        card_equipe.add(self.bar_chassi)
        card_equipe.add(self.bar_confiab)

        card_equipe.add(Separador())

        lbl_pilotos = QLabel("PILOTOS")
        lbl_pilotos.setFont(Fontes.label_campo())
        lbl_pilotos.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        card_equipe.add(lbl_pilotos)

        self.info_piloto_1 = LinhaInfo("Piloto 1", "-")
        self.info_piloto_2 = LinhaInfo("Piloto 2", "-")
        card_equipe.add(self.info_piloto_1)
        card_equipe.add(self.info_piloto_2)

        card_equipe.add(Separador())

        lbl_dinamica = QLabel("DINAMICA INTERNA")
        lbl_dinamica.setFont(Fontes.label_campo())
        lbl_dinamica.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        card_equipe.add(lbl_dinamica)

        self.info_dinamica_n1 = LinhaInfo("Piloto N1", "-")
        self.info_dinamica_n2 = LinhaInfo("Piloto N2", "-")
        self.info_dinamica_status = LinhaInfo("Status", "-")
        self.info_dinamica_detalhe = LinhaInfo("Detalhe", "-")
        card_equipe.add(self.info_dinamica_n1)
        card_equipe.add(self.info_dinamica_n2)
        card_equipe.add(self.info_dinamica_status)
        card_equipe.add(self.info_dinamica_detalhe)

        card_equipe.add(Separador())

        self.info_pts_equipe = LinhaInfo("Pontos", "0")
        self.info_vit_equipe = LinhaInfo("Vitórias", "0")
        card_equipe.add(self.info_pts_equipe)
        card_equipe.add(self.info_vit_equipe)

        card_equipe.add(Separador())

        lbl_comp = QLabel("COMPARACAO JOGADOR VS COMPANHEIRO")
        lbl_comp.setFont(Fontes.label_campo())
        lbl_comp.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        card_equipe.add(lbl_comp)

        self.tabela_comparacao_dupla = QTableWidget()
        self.tabela_comparacao_dupla.setColumnCount(3)
        self.tabela_comparacao_dupla.setHorizontalHeaderLabels(["Stat", "Voce", "Companheiro"])
        self.tabela_comparacao_dupla.setStyleSheet(Estilos.tabela())
        self.tabela_comparacao_dupla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_comparacao_dupla.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_comparacao_dupla.verticalHeader().setVisible(False)
        self.tabela_comparacao_dupla.setShowGrid(False)
        head_comp = self.tabela_comparacao_dupla.horizontalHeader()
        head_comp.setSectionResizeMode(0, QHeaderView.Stretch)
        head_comp.setSectionResizeMode(1, QHeaderView.Stretch)
        head_comp.setSectionResizeMode(2, QHeaderView.Stretch)
        card_equipe.add(self.tabela_comparacao_dupla)

        self.lbl_comparacao_status = QLabel("Comparacao indisponivel.")
        self.lbl_comparacao_status.setWordWrap(True)
        self.lbl_comparacao_status.setFont(Fontes.texto_pequeno())
        self.lbl_comparacao_status.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        card_equipe.add(self.lbl_comparacao_status)

        card_equipe.add(Separador())
        lbl_expect = QLabel("EXPECTATIVAS DA EQUIPE")
        lbl_expect.setFont(Fontes.label_campo())
        lbl_expect.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        card_equipe.add(lbl_expect)
        self.lbl_expectativa_faixa = QLabel("Expectativa: -")
        self.lbl_expectativa_faixa.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        self.lbl_expectativa_status = QLabel("Avaliacao: -")
        self.lbl_expectativa_status.setWordWrap(True)
        self.lbl_expectativa_status.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        self.lbl_expectativa_impacto = QLabel("Impacto: -")
        self.lbl_expectativa_impacto.setWordWrap(True)
        self.lbl_expectativa_impacto.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        card_equipe.add(self.lbl_expectativa_faixa)
        card_equipe.add(self.lbl_expectativa_status)
        card_equipe.add(self.lbl_expectativa_impacto)

        self.txt_historico_avaliacao = QTextEdit()
        self.txt_historico_avaliacao.setReadOnly(True)
        self.txt_historico_avaliacao.setMinimumHeight(100)
        self.txt_historico_avaliacao.setStyleSheet(
            f"""
            QTextEdit {{
                background: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_SECONDARY};
                border: 1px solid {Cores.BORDA};
                border-radius: 6px;
                padding: 6px;
            }}
            """
        )
        card_equipe.add(self.txt_historico_avaliacao)

        layout.addWidget(card_equipe)
        layout.addStretch()

        return widget

    def _build_tab_noticias(self):
        widget = QWidget()
        root_layout = QVBoxLayout(widget)
        root_layout.setContentsMargins(15, 15, 15, 15)
        root_layout.setSpacing(10)

        topo = QHBoxLayout()
        lbl_titulo = QLabel("FEED DE NOTICIAS")
        lbl_titulo.setFont(Fontes.titulo_medio())
        lbl_titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        topo.addWidget(lbl_titulo)
        topo.addStretch(1)

        self.combo_noticias_filtro = QComboBox()
        self.combo_noticias_filtro.setObjectName("combo_categoria_top")
        self.combo_noticias_filtro.setMinimumWidth(170)
        self.combo_noticias_filtro.addItems(
            [
                "Todos",
                "Corrida",
                "Incidente",
                "Mercado",
                "Promocao",
                "Rebaixamento",
                "Aposentadoria",
                "Rookies",
                "Hierarquia",
                "Milestone",
            ]
        )
        self.combo_noticias_filtro.currentIndexChanged.connect(self._atualizar_feed_noticias)
        topo.addWidget(self.combo_noticias_filtro)
        root_layout.addLayout(topo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        root_layout.addWidget(scroll, 1)

        self._widget_noticias_scroll = QWidget()
        self._layout_noticias_cards = QVBoxLayout(self._widget_noticias_scroll)
        self._layout_noticias_cards.setContentsMargins(0, 0, 0, 0)
        self._layout_noticias_cards.setSpacing(10)
        scroll.setWidget(self._widget_noticias_scroll)
        return widget

    def _build_tab_outras_categorias(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        topo = QHBoxLayout()
        lbl_titulo = QLabel("OUTRAS CATEGORIAS")
        lbl_titulo.setFont(Fontes.titulo_medio())
        lbl_titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        topo.addWidget(lbl_titulo)
        topo.addStretch(1)

        self.combo_outras_categorias = QComboBox()
        self.combo_outras_categorias.setObjectName("combo_categoria_top")
        self.combo_outras_categorias.setMinimumWidth(260)
        self.combo_outras_categorias.currentIndexChanged.connect(self._atualizar_aba_outras_categorias)
        topo.addWidget(self.combo_outras_categorias)
        layout.addLayout(topo)

        self.lbl_outras_contexto = QLabel("Selecione uma categoria para ver o resumo.")
        self.lbl_outras_contexto.setWordWrap(True)
        self.lbl_outras_contexto.setFont(Fontes.texto_normal())
        self.lbl_outras_contexto.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        layout.addWidget(self.lbl_outras_contexto)

        self.tabela_outras_pilotos = QTableWidget()
        self.tabela_outras_pilotos.setColumnCount(4)
        self.tabela_outras_pilotos.setHorizontalHeaderLabels(["POS", "PILOTO", "EQUIPE", "PTS"])
        self.tabela_outras_pilotos.setStyleSheet(Estilos.tabela())
        self.tabela_outras_pilotos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_outras_pilotos.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_outras_pilotos.verticalHeader().setVisible(False)
        self.tabela_outras_pilotos.setShowGrid(False)
        head_pil = self.tabela_outras_pilotos.horizontalHeader()
        head_pil.setSectionResizeMode(0, QHeaderView.Fixed)
        head_pil.setSectionResizeMode(1, QHeaderView.Stretch)
        head_pil.setSectionResizeMode(2, QHeaderView.Stretch)
        head_pil.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabela_outras_pilotos.setColumnWidth(0, 58)
        self.tabela_outras_pilotos.setColumnWidth(3, 90)
        layout.addWidget(self.tabela_outras_pilotos, 1)

        self.tabela_outras_equipes = QTableWidget()
        self.tabela_outras_equipes.setColumnCount(3)
        self.tabela_outras_equipes.setHorizontalHeaderLabels(["POS", "CONSTRUTOR", "PTS"])
        self.tabela_outras_equipes.setStyleSheet(Estilos.tabela())
        self.tabela_outras_equipes.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela_outras_equipes.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela_outras_equipes.verticalHeader().setVisible(False)
        self.tabela_outras_equipes.setShowGrid(False)
        head_eq = self.tabela_outras_equipes.horizontalHeader()
        head_eq.setSectionResizeMode(0, QHeaderView.Fixed)
        head_eq.setSectionResizeMode(1, QHeaderView.Stretch)
        head_eq.setSectionResizeMode(2, QHeaderView.Fixed)
        self.tabela_outras_equipes.setColumnWidth(0, 58)
        self.tabela_outras_equipes.setColumnWidth(2, 90)
        layout.addWidget(self.tabela_outras_equipes, 1)

        self.lbl_outras_ultimo_resultado = QLabel("Ultimo resultado: sem dados.")
        self.lbl_outras_ultimo_resultado.setWordWrap(True)
        self.lbl_outras_ultimo_resultado.setFont(Fontes.texto_pequeno())
        self.lbl_outras_ultimo_resultado.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
        layout.addWidget(self.lbl_outras_ultimo_resultado)
        return widget

    def _estilo_barra_previsao(self, cor: str) -> str:
        return f"""
            QProgressBar {{
                background-color: {Cores.BORDA};
                border: none;
                border-radius: 4px;
                min-height: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {cor};
                border-radius: 4px;
            }}
        """

    def _criar_card_cenario_previsao(
        self,
        titulo: str,
        cor_destaque: str,
    ) -> tuple[Card, dict[str, Any]]:
        card = Card()

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(Fontes.titulo_pequeno())
        lbl_titulo.setStyleSheet(
            f"color: {cor_destaque}; border: none; background: transparent;"
        )
        card.add(lbl_titulo)

        card.add(Separador())

        lbl_status = QLabel("—")
        lbl_status.setFont(Fontes.titulo_medio())
        lbl_status.setAlignment(Qt.AlignCenter)
        lbl_status.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARY}; border: none; background: transparent; font-weight: bold;"
        )
        card.add(lbl_status)

        lbl_delta = QLabel("0 pts")
        lbl_delta.setFont(Fontes.numero_medio())
        lbl_delta.setAlignment(Qt.AlignCenter)
        lbl_delta.setStyleSheet(
            f"color: {cor_destaque}; border: none; background: transparent;"
        )
        card.add(lbl_delta)

        lbl_condicao_1 = QLabel("• —")
        lbl_condicao_1.setFont(Fontes.texto_pequeno())
        lbl_condicao_1.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        lbl_condicao_1.setWordWrap(True)
        card.add(lbl_condicao_1)

        lbl_condicao_2 = QLabel("• —")
        lbl_condicao_2.setFont(Fontes.texto_pequeno())
        lbl_condicao_2.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        lbl_condicao_2.setWordWrap(True)
        card.add(lbl_condicao_2)

        lbl_probabilidade = QLabel("Probabilidade: --%")
        lbl_probabilidade.setFont(Fontes.texto_pequeno())
        lbl_probabilidade.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARY}; border: none; background: transparent;"
        )
        card.add(lbl_probabilidade)

        barra_probabilidade = QProgressBar()
        barra_probabilidade.setRange(0, 100)
        barra_probabilidade.setValue(0)
        barra_probabilidade.setTextVisible(False)
        barra_probabilidade.setStyleSheet(self._estilo_barra_previsao(cor_destaque))
        card.add(barra_probabilidade)

        return card, {
            "status": lbl_status,
            "delta": lbl_delta,
            "condicao_1": lbl_condicao_1,
            "condicao_2": lbl_condicao_2,
            "probabilidade": lbl_probabilidade,
            "barra": barra_probabilidade,
        }

    def _criar_item_checklist_previsao(self) -> QLabel:
        lbl = QLabel("⬜ —")
        lbl.setFont(Fontes.texto_normal())
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"""
            QLabel {{
                border: 1px solid {Cores.BORDA};
                border-radius: 6px;
                padding: 10px 12px;
                color: {Cores.TEXTO_PRIMARY};
                background: transparent;
            }}
        """
        )
        return lbl

    def _build_tab_previsao_campeonato(self):
        widget = QWidget()
        root_layout = QVBoxLayout(widget)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            """
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """
        )

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(14)

        card_header = CardTitulo("📈 PREVISÃO DE CAMPEONATO")

        self.lbl_previsao_temporada = QLabel("—")
        self.lbl_previsao_temporada.setFont(Fontes.titulo_medio())
        self.lbl_previsao_temporada.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARY}; border: none; background: transparent;"
        )
        card_header.add(self.lbl_previsao_temporada)

        kpis_layout = QHBoxLayout()
        kpis_layout.setSpacing(10)
        self.stat_prev_posicao = CardStat("-", "POSIÇÃO", Cores.ACCENT_PRIMARY)
        self.stat_prev_diferenca = CardStat("-", "DO LÍDER", Cores.VERMELHO)
        self.stat_prev_restantes = CardStat("0", "RESTANTES", Cores.AMARELO)
        kpis_layout.addWidget(self.stat_prev_posicao)
        kpis_layout.addWidget(self.stat_prev_diferenca)
        kpis_layout.addWidget(self.stat_prev_restantes)
        kpis_widget = QWidget()
        kpis_widget.setLayout(kpis_layout)
        card_header.add(kpis_widget)

        self.lbl_previsao_status = QLabel("")
        self.lbl_previsao_status.setFont(Fontes.texto_pequeno())
        self.lbl_previsao_status.setWordWrap(True)
        self.lbl_previsao_status.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        card_header.add(self.lbl_previsao_status)

        layout.addWidget(card_header)

        card_disputa = CardTitulo("DISPUTA PELO TÍTULO")
        self.previsao_disputa_rows: list[dict[str, Any]] = []
        cores_disputa = [Cores.AMARELO, Cores.ACCENT_PRIMARY, Cores.VERDE]

        for cor in cores_disputa:
            linha = QWidget()
            linha_layout = QVBoxLayout(linha)
            linha_layout.setContentsMargins(0, 0, 0, 0)
            linha_layout.setSpacing(3)

            cabecalho = QHBoxLayout()
            cabecalho.setContentsMargins(0, 0, 0, 0)
            cabecalho.setSpacing(8)

            lbl_nome = QLabel("—")
            lbl_nome.setFont(Fontes.texto_normal())
            lbl_nome.setStyleSheet(
                f"color: {Cores.TEXTO_PRIMARY}; border: none; background: transparent;"
            )
            cabecalho.addWidget(lbl_nome)

            cabecalho.addStretch()

            lbl_pontos = QLabel("0 pts")
            lbl_pontos.setFont(Fontes.texto_normal())
            lbl_pontos.setStyleSheet(
                f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
            )
            cabecalho.addWidget(lbl_pontos)

            linha_layout.addLayout(cabecalho)

            barra_layout = QHBoxLayout()
            barra_layout.setContentsMargins(0, 0, 0, 0)
            barra_layout.setSpacing(8)

            barra = QProgressBar()
            barra.setRange(0, 100)
            barra.setValue(0)
            barra.setTextVisible(False)
            barra.setStyleSheet(self._estilo_barra_previsao(cor))
            barra_layout.addWidget(barra, stretch=1)

            lbl_percentual = QLabel("0%")
            lbl_percentual.setFont(Fontes.texto_pequeno())
            lbl_percentual.setStyleSheet(
                f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
            )
            lbl_percentual.setFixedWidth(36)
            lbl_percentual.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            barra_layout.addWidget(lbl_percentual)

            linha_layout.addLayout(barra_layout)
            card_disputa.add(linha)

            self.previsao_disputa_rows.append(
                {
                    "nome": lbl_nome,
                    "pontos": lbl_pontos,
                    "barra": barra,
                    "percentual": lbl_percentual,
                }
            )

        self.lbl_previsao_gap_titulo = QLabel("—")
        self.lbl_previsao_gap_titulo.setFont(Fontes.titulo_pequeno())
        self.lbl_previsao_gap_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_previsao_gap_titulo.setStyleSheet(
            f"color: {Cores.AMARELO}; border: none; background: transparent;"
        )
        card_disputa.add(self.lbl_previsao_gap_titulo)

        layout.addWidget(card_disputa)

        self.card_previsao_cenarios = CardTitulo("SE VOCÊ VENCER AS PRÓXIMAS CORRIDAS")
        cenarios_layout = QHBoxLayout()
        cenarios_layout.setSpacing(12)

        card_melhor, self.previsao_melhor_widgets = self._criar_card_cenario_previsao(
            "🏆 MELHOR CASO",
            Cores.VERDE,
        )
        card_pior, self.previsao_pior_widgets = self._criar_card_cenario_previsao(
            "😰 PIOR CASO",
            Cores.VERMELHO,
        )

        cenarios_layout.addWidget(card_melhor)
        cenarios_layout.addWidget(card_pior)
        cenarios_widget = QWidget()
        cenarios_widget.setLayout(cenarios_layout)
        self.card_previsao_cenarios.add(cenarios_widget)
        layout.addWidget(self.card_previsao_cenarios)

        card_requisitos = CardTitulo("✅ REQUISITOS PARA SER CAMPEÃO")

        self.lbl_previsao_requisitos_intro = QLabel("Para garantir o título, você precisa:")
        self.lbl_previsao_requisitos_intro.setFont(Fontes.texto_normal())
        self.lbl_previsao_requisitos_intro.setStyleSheet(
            f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;"
        )
        card_requisitos.add(self.lbl_previsao_requisitos_intro)

        self.lbl_req_plano_a_1 = self._criar_item_checklist_previsao()
        self.lbl_req_plano_a_2 = self._criar_item_checklist_previsao()
        self.lbl_req_ou = QLabel("OU")
        self.lbl_req_ou.setAlignment(Qt.AlignCenter)
        self.lbl_req_ou.setFont(Fontes.titulo_pequeno())
        self.lbl_req_ou.setStyleSheet(
            f"color: {Cores.TEXTO_MUTED}; border: none; background: transparent;"
        )
        self.lbl_req_plano_b_1 = self._criar_item_checklist_previsao()
        self.lbl_req_plano_b_2 = self._criar_item_checklist_previsao()

        card_requisitos.add(self.lbl_req_plano_a_1)
        card_requisitos.add(self.lbl_req_plano_a_2)
        card_requisitos.add(self.lbl_req_ou)
        card_requisitos.add(self.lbl_req_plano_b_1)
        card_requisitos.add(self.lbl_req_plano_b_2)
        layout.addWidget(card_requisitos)

        card_evolucao = CardTitulo("📊 EVOLUÇÃO DO CAMPEONATO")
        self.lbl_previsao_grafico = QLabel("")
        self.lbl_previsao_grafico.setFont(QFont(Fontes.FAMILIA_MONO, 9))
        self.lbl_previsao_grafico.setStyleSheet(
            f"color: {Cores.TEXTO_PRIMARY}; border: none; background: transparent;"
        )
        self.lbl_previsao_grafico.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_evolucao.add(self.lbl_previsao_grafico)
        layout.addWidget(card_evolucao)

        self.card_previsao_decisiva = CardTitulo("⚠️ CORRIDA DECISIVA!")
        self.lbl_previsao_decisiva = QLabel("")
        self.lbl_previsao_decisiva.setFont(Fontes.texto_normal())
        self.lbl_previsao_decisiva.setWordWrap(True)
        self.lbl_previsao_decisiva.setStyleSheet(
            f"color: {Cores.AMARELO}; border: none; background: transparent; font-weight: bold;"
        )
        self.card_previsao_decisiva.add(self.lbl_previsao_decisiva)
        layout.addWidget(self.card_previsao_decisiva)

        layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

        return widget

    # ============================================================
    # HELPERS
    # ============================================================

    def _get_corrida_atual(self):
        if self._temporada_concluida():
            return None

        calendario = self._obter_calendario_temporada()
        try:
            rodada = int(self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada = 1
        total = self._obter_total_rodadas_temporada()

        if calendario and 1 <= rodada <= len(calendario):
            return calendario[rodada - 1]

        if 1 <= rodada <= total:
            return {
                "nome": f"Rodada {rodada}",
                "circuito": "Circuito aleatorio",
                "clima": "-",
                "temperatura": "-",
                "voltas": "-",
            }

        return None

    def _get_proximo_evento_exibicao(self):
        return obter_proximo_evento_exibicao(self.banco)

    def _formatar_clima(self, clima: Any) -> str:
        texto = str(clima or "—")
        return f"{'☀️' if texto == 'Seco' else '🌧️' if texto != '—' else '•'} {texto}"

    def _formatar_temperatura(self, temperatura: Any) -> str:
        if isinstance(temperatura, (int, float)):
            return f"{temperatura}°C"
        return str(temperatura or "—")

    def _normalizar_texto_busca_dashboard(self, texto: Any) -> str:
        bruto = str(texto or "").strip().casefold()
        if not bruto:
            return ""
        decomposicao = unicodedata.normalize("NFD", bruto)
        return "".join(
            caractere
            for caractere in decomposicao
            if unicodedata.category(caractere) != "Mn"
        )

    def _resultado_para_posicao_dashboard(self, resultado: Any) -> int | str | None:
        if isinstance(resultado, bool):
            return None

        if isinstance(resultado, int):
            return resultado if resultado > 0 else None

        texto = str(resultado or "").strip()
        if not texto or texto in {"—", "-"}:
            return None
        if texto.upper() == "DNF":
            return "DNF"

        try:
            posicao = int(float(texto.replace(",", ".")))
            return posicao if posicao > 0 else None
        except (TypeError, ValueError):
            return None

    def _chave_desempate_resultados_dashboard(
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
            posicao = self._resultado_para_posicao_dashboard(resultado)
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

    def _ordenar_pilotos_por_desempenho_dashboard(
        self,
        pilotos: list[dict[str, Any]],
        limite_rodadas: int | None = None,
    ) -> list[dict[str, Any]]:
        if not isinstance(pilotos, list):
            return []

        tamanho_chave = 0
        for piloto in pilotos:
            resultados = piloto.get("resultados_temporada", [])
            if not isinstance(resultados, list):
                resultados = []
            tamanho = len(resultados if limite_rodadas is None else resultados[: max(0, limite_rodadas)])
            if tamanho > tamanho_chave:
                tamanho_chave = tamanho

        return sorted(
            pilotos,
            key=lambda p: (
                -int(p.get("pontos_temporada", 0)),
                self._chave_desempate_resultados_dashboard(
                    p.get("resultados_temporada", []),
                    limite_rodadas=limite_rodadas,
                    tamanho_chave=tamanho_chave,
                ),
                str(p.get("nome", "")).casefold(),
            ),
        )

    def _calcular_pontos_ate_rodada_dashboard(
        self,
        resultados: list[Any],
        limite_rodadas: int,
    ) -> int:
        if not isinstance(resultados, list):
            return 0

        pontos = 0
        for resultado in resultados[: max(0, limite_rodadas)]:
            posicao = self._resultado_para_posicao_dashboard(resultado)
            if isinstance(posicao, int) and posicao > 0:
                pontos += int(PONTOS_POR_POSICAO.get(posicao, 0))
        return pontos

    def _contar_rodadas_com_resultado_dashboard(self, pilotos: list[dict[str, Any]]) -> int:
        max_rodada = 0
        for piloto in pilotos:
            resultados = piloto.get("resultados_temporada", [])
            if not isinstance(resultados, list):
                continue
            for indice, resultado in enumerate(resultados, start=1):
                if self._resultado_para_posicao_dashboard(resultado) is not None:
                    max_rodada = max(max_rodada, indice)
        return max_rodada

    def _mapa_tendencia_real_tabela(self, pilotos: list[dict[str, Any]]) -> dict[str, str]:
        if not isinstance(pilotos, list) or not pilotos:
            return {}

        rodadas_completadas = self._contar_rodadas_com_resultado_dashboard(pilotos)
        if rodadas_completadas < 2:
            return {}

        def _chave_piloto(p: dict[str, Any]) -> str:
            return self._chave_piloto_mock_tabela(p)

        pilotos_atual: list[dict[str, Any]] = []
        pilotos_anterior: list[dict[str, Any]] = []
        for piloto in pilotos:
            base = dict(piloto)
            resultados = piloto.get("resultados_temporada", [])
            if not isinstance(resultados, list):
                resultados = []

            atual = dict(base)
            atual["pontos_temporada"] = self._calcular_pontos_ate_rodada_dashboard(
                resultados,
                rodadas_completadas,
            )
            atual["resultados_temporada"] = list(resultados[:rodadas_completadas])
            pilotos_atual.append(atual)

            anterior = dict(base)
            anterior["pontos_temporada"] = self._calcular_pontos_ate_rodada_dashboard(
                resultados,
                rodadas_completadas - 1,
            )
            anterior["resultados_temporada"] = list(resultados[: max(0, rodadas_completadas - 1)])
            pilotos_anterior.append(anterior)

        ordenado_atual = self._ordenar_pilotos_por_desempenho_dashboard(
            pilotos_atual,
            limite_rodadas=rodadas_completadas,
        )
        ordenado_anterior = self._ordenar_pilotos_por_desempenho_dashboard(
            pilotos_anterior,
            limite_rodadas=max(0, rodadas_completadas - 1),
        )

        pos_atual = {
            _chave_piloto(piloto): indice
            for indice, piloto in enumerate(ordenado_atual, start=1)
            if _chave_piloto(piloto)
        }
        pos_anterior = {
            _chave_piloto(piloto): indice
            for indice, piloto in enumerate(ordenado_anterior, start=1)
            if _chave_piloto(piloto)
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

    def _obter_codigo_bandeira_corrida_dashboard(
        self, circuito: Any, indice_fallback: int | None = None
    ) -> str:
        return obter_codigo_bandeira_circuito(
            str(circuito or ""),
            indice_fallback=indice_fallback,
        )

    def _limpar_layout_dashboard(self, layout: QHBoxLayout | QVBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _montar_medalhas_resultados_dashboard(self, resultados: list[Any]) -> str:
        ouro = 0
        prata = 0
        bronze = 0

        for resultado in resultados:
            posicao = self._resultado_para_posicao_dashboard(resultado)
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
        return "".join(partes)

    def _criar_badge_resultado_dashboard(self, resultado: Any, rodada: int) -> QLabel:
        texto = "-"
        cor_fundo = "#121c2b"
        cor_texto = Cores.TEXTO_MUTED
        cor_borda = "#27384f"

        posicao = self._resultado_para_posicao_dashboard(resultado)
        if posicao == "DNF":
            texto = "DNF"
            cor_fundo = "#7a1f1b"
            cor_texto = Cores.TEXTO_PRIMARY
            cor_borda = "#c44f47"
        elif isinstance(posicao, int):
            texto = str(posicao)
            if posicao == 1:
                cor_fundo = Cores.OURO
                cor_texto = Cores.TEXTO_INVERSE
                cor_borda = "#ffea7a"
            elif posicao == 2:
                cor_fundo = Cores.PRATA
                cor_texto = Cores.TEXTO_INVERSE
                cor_borda = "#d4d4d4"
            elif posicao == 3:
                cor_fundo = Cores.BRONZE
                cor_texto = Cores.TEXTO_INVERSE
                cor_borda = "#e4a86f"
            else:
                cor_texto = Cores.TEXTO_PRIMARY

        label = QLabel(texto)
        label.setObjectName("badge_resultado_corrida")
        label.setAlignment(Qt.AlignCenter)
        label.setFixedSize(42, 23)
        label.setToolTip(f"Rodada {rodada}: {texto}")
        label.setStyleSheet(
            f"""
            QLabel#badge_resultado_corrida {{
                background-color: {cor_fundo};
                color: {cor_texto};
                border: 1px solid {cor_borda};
                border-radius: 6px;
                font-weight: 700;
            }}
            """
        )
        return label

    def _atualizar_tira_corridas_dashboard(
        self,
        calendario: list[dict[str, Any]],
        resultados_jogador: list[Any],
    ) -> None:
        if (
            not hasattr(self, "layout_bandeiras_corridas")
            or not hasattr(self, "layout_resultados_corridas")
        ):
            return

        self._limpar_layout_dashboard(self.layout_bandeiras_corridas)
        self._limpar_layout_dashboard(self.layout_resultados_corridas)

        total_rodadas = self._obter_total_rodadas_temporada()
        total_itens = max(total_rodadas, len(calendario), len(resultados_jogador))

        if total_itens <= 0:
            total_itens = 1

        for indice in range(total_itens):
            corrida = calendario[indice] if indice < len(calendario) else {}
            if not isinstance(corrida, dict):
                corrida = {}

            circuito = str(corrida.get("circuito", "") or "").strip()
            codigo_bandeira = self._obter_codigo_bandeira_corrida_dashboard(
                circuito,
                indice_fallback=indice,
            )

            badge_bandeira = BandeiraLabel(codigo_bandeira, largura=42, altura=23)
            badge_bandeira.setObjectName("badge_flag_corrida")
            badge_bandeira.setAlignment(Qt.AlignCenter)
            badge_bandeira.setFixedSize(42, 23)
            badge_bandeira.setToolTip(
                f"Rodada {indice + 1}: {circuito or 'Circuito indefinido'}"
            )
            self.layout_bandeiras_corridas.addWidget(badge_bandeira)

            resultado = resultados_jogador[indice] if indice < len(resultados_jogador) else None
            self.layout_resultados_corridas.addWidget(
                self._criar_badge_resultado_dashboard(resultado, indice + 1)
            )

        self.layout_bandeiras_corridas.addStretch(1)
        self.layout_resultados_corridas.addStretch(1)
    def _simular_previsao_com_vitorias(
        self,
        pilotos_base: list[dict[str, Any]],
        corridas_restantes: int,
        favorecer_adversarios: bool,
    ) -> list[dict[str, Any]]:
        simulacao = [
            {
                "id": piloto.get("id"),
                "nome": str(piloto.get("nome", "")),
                "is_jogador": bool(piloto.get("is_jogador", False)),
                "pontos_temporada": int(piloto.get("pontos_temporada", 0)),
                "vitorias_temporada": int(piloto.get("vitorias_temporada", 0)),
                "podios_temporada": int(piloto.get("podios_temporada", 0)),
            }
            for piloto in pilotos_base
        ]

        jogador = next(
            (piloto for piloto in simulacao if piloto.get("is_jogador", False)),
            None,
        )
        if jogador is None:
            return self._ordenar_pilotos_campeonato(simulacao)

        pontos_vitoria = int(PONTOS_POR_POSICAO.get(1, 25))

        for _ in range(max(corridas_restantes, 0)):
            jogador["pontos_temporada"] += pontos_vitoria
            jogador["vitorias_temporada"] += 1
            jogador["podios_temporada"] += 1

            adversarios = [
                piloto
                for piloto in simulacao
                if not piloto.get("is_jogador", False)
            ]

            if favorecer_adversarios:
                adversarios.sort(
                    key=lambda piloto: (
                        -int(piloto.get("pontos_temporada", 0)),
                        -int(piloto.get("vitorias_temporada", 0)),
                        -int(piloto.get("podios_temporada", 0)),
                        str(piloto.get("nome", "")).casefold(),
                    )
                )
            else:
                adversarios.sort(
                    key=lambda piloto: (
                        int(piloto.get("pontos_temporada", 0)),
                        int(piloto.get("vitorias_temporada", 0)),
                        int(piloto.get("podios_temporada", 0)),
                        str(piloto.get("nome", "")).casefold(),
                    )
                )

            for posicao, adversario in enumerate(adversarios, start=2):
                pontos = int(PONTOS_POR_POSICAO.get(posicao, 0))
                adversario["pontos_temporada"] += pontos
                if posicao <= 3:
                    adversario["podios_temporada"] += 1

        return self._ordenar_pilotos_campeonato(simulacao)

    def _resumo_classificacao_previsao(
        self,
        classificacao: list[dict[str, Any]],
    ) -> dict[str, int] | None:
        indice_jogador = next(
            (
                indice
                for indice, piloto in enumerate(classificacao)
                if piloto.get("is_jogador", False)
            ),
            -1,
        )
        if indice_jogador < 0:
            return None

        jogador = classificacao[indice_jogador]
        posicao_jogador = indice_jogador + 1
        pontos_jogador = int(jogador.get("pontos_temporada", 0))

        if posicao_jogador == 1 and len(classificacao) > 1:
            referencia = classificacao[1]
        else:
            referencia = classificacao[0]

        pontos_referencia = int(referencia.get("pontos_temporada", 0))
        return {
            "posicao": posicao_jogador,
            "delta": pontos_jogador - pontos_referencia,
        }

    def _descricao_posicao_previsao(self, posicao: int) -> str:
        if posicao == 1:
            return "CAMPEÃO"
        return f"{posicao}º lugar"

    def _formatar_diferenca_pontos(self, diferenca: int) -> str:
        sufixo = "pt" if abs(diferenca) == 1 else "pts"
        if diferenca > 0:
            return f"+{diferenca} {sufixo}"
        return f"{diferenca} {sufixo}"

    def _requisitos_titulo_previsao(
        self,
        delta_atual: int,
        corridas_restantes: int,
    ) -> list[str]:
        if corridas_restantes <= 0:
            if delta_atual >= 0:
                return [
                    "A temporada já foi concluída na liderança",
                    "Finalize para iniciar a próxima disputa",
                ]
            return [
                "Não há corridas restantes para tirar a diferença",
                "Você precisará buscar o título na próxima temporada",
            ]

        if delta_atual >= 0:
            vantagem = delta_atual
            sufixo = "pt" if abs(vantagem) == 1 else "pts"
            return [
                "Manter o ritmo nas corridas finais",
                f"Defender pelo menos {vantagem} {sufixo} para o vice-líder",
            ]

        deficit = abs(delta_atual)
        swing_necessario = deficit + 1

        pontos_vitoria = int(PONTOS_POR_POSICAO.get(1, 25))
        ganho_vs_top3 = max(1, pontos_vitoria - int(PONTOS_POR_POSICAO.get(3, 15)))
        ganho_vs_fora_top3 = max(1, pontos_vitoria - int(PONTOS_POR_POSICAO.get(4, 12)))
        ganho_maximo_total = corridas_restantes * pontos_vitoria

        if swing_necessario > ganho_maximo_total:
            return [
                f"Vencer as {corridas_restantes} corridas restantes",
                "E torcer para o líder ficar sem pontuar em todas elas",
            ]

        vitorias_min = min(corridas_restantes, ceil(swing_necessario / ganho_vs_top3))
        corridas_fora_top3 = min(
            corridas_restantes,
            max(1, ceil(swing_necessario / ganho_vs_fora_top3)),
        )

        return [
            f"Vencer pelo menos {vitorias_min} corrida(s)",
            f"E o líder terminar fora do top 3 em {corridas_fora_top3} corrida(s)",
        ]

    def _calcular_probabilidade_titulo_previsao(
        self,
        delta_atual: int,
        corridas_restantes: int,
        posicao_atual: int,
    ) -> int:
        base = 55 + (delta_atual * 3)
        base += max(0, 4 - posicao_atual) * 4
        base += corridas_restantes * 3
        return max(5, min(95, int(base)))

    def _pontos_resultado_previsao(self, resultado: Any) -> int:
        if isinstance(resultado, int):
            return self._calcular_pontos_da_posicao(posicao=resultado)

        texto = str(resultado or "").strip().upper()
        if not texto or texto in {"DNF", "-", "—"}:
            return 0

        try:
            posicao = int(texto)
        except (TypeError, ValueError):
            return 0

        return self._calcular_pontos_da_posicao(posicao=posicao)

    def _serie_cumulativa_previsao(
        self,
        resultados: list[Any],
        corridas_disputadas: int,
    ) -> list[int]:
        acumulado = 0
        serie: list[int] = []

        for indice in range(max(corridas_disputadas, 0)):
            resultado = resultados[indice] if indice < len(resultados) else None
            acumulado += self._pontos_resultado_previsao(resultado)
            serie.append(acumulado)

        if not serie:
            serie.append(0)
        return serie

    def _sparkline_previsao(self, valores: list[int]) -> str:
        blocos = "▁▂▃▄▅▆▇█"
        if not valores:
            return ""

        minimo = min(valores)
        maximo = max(valores)
        if minimo == maximo:
            return blocos[0] * len(valores)

        escala = len(blocos) - 1
        return "".join(
            blocos[int(round((valor - minimo) / (maximo - minimo) * escala))]
            for valor in valores
        )

    def _obter_posicao_jogador(self):
        jogador = self._obter_jogador()
        if not jogador:
            return "-"

        pilotos_cat = obter_pilotos_categoria(self.banco, self.categoria_atual)
        pilotos_ord = self._ordenar_pilotos_campeonato(pilotos_cat)

        return next(
            (i + 1 for i, p in enumerate(pilotos_ord) if p.get("is_jogador")),
            "-",
        )

    def _criar_item_tabela(
        self,
        texto: Any,
        cor_texto: QColor | str,
        cor_fundo: QColor | str,
        alinhamento: Qt.AlignmentFlag | None = None,
        negrito: bool = False,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(str(texto))
        item.setForeground(QBrush(QColor(cor_texto)))
        item.setBackground(QBrush(QColor(cor_fundo)))
        if alinhamento is not None:
            item.setTextAlignment(alinhamento)
        if negrito:
            fonte = item.font()
            fonte.setBold(True)
            item.setFont(fonte)
        return item

    def _simular_classificacao(self, *, retornar_resultado: bool = False):
        return self._delegar_mixin(
            SimularMixin,
            "_simular_classificacao",
            retornar_resultado=retornar_resultado,
        )

    def _abrir_dialog_modificadores(self) -> None:
        dados = self.banco.get("modifier_preview")
        if not isinstance(dados, dict):
            QMessageBox.information(
                self,
                "Modificadores",
                "Nenhum preview de modificadores disponivel ainda. Exporte o roster da proxima corrida primeiro.",
            )
            return

        pilotos = dados.get("pilotos", [])
        if not isinstance(pilotos, list) or not pilotos:
            QMessageBox.information(
                self,
                "Modificadores",
                "Nenhum modificador registrado para a rodada atual.",
            )
            return

        try:
            from UI.dialogs import ModificadoresDialog

            dialogo = ModificadoresDialog(dados=dados, parent=self)
            dialogo.exec()
        except Exception as erro:
            QMessageBox.warning(self, "Aviso", f"Tela de modificadores indisponivel.\nErro: {erro}")

    # ============================================================
    # ATUALIZAÇÕES
    # ============================================================

    def _atualizar_tudo(self, animar: bool = False):
        if sincronizar_production_car_challenge(self.banco):
            salvar_banco(self.banco)
        self._atualizar_info_temporada()
        self._atualizar_tabela_pilotos()
        self._atualizar_tabela_equipes()
        self._atualizar_stats_jogador()
        self._atualizar_proxima_corrida()
        self._atualizar_minha_equipe()
        self._atualizar_previsao_campeonato()
        self._atualizar_aba_mercado()
        self._atualizar_feed_noticias()
        self._atualizar_aba_outras_categorias()

        if animar and getattr(self, "_ux_initialized", False):
            QTimer.singleShot(100, self._animar_entrada_dashboard)

    def _atualizar_feed_noticias(self, *_args) -> None:
        if not hasattr(self, "_layout_noticias_cards"):
            return

        while self._layout_noticias_cards.count():
            item = self._layout_noticias_cards.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        filtro_tipo = ""
        if hasattr(self, "combo_noticias_filtro"):
            filtro_texto = str(self.combo_noticias_filtro.currentText() or "").strip().lower()
            mapa_tipos = {
                "corrida": "corrida",
                "incidente": "incidente",
                "mercado": "mercado",
                "promocao": "promocao",
                "rebaixamento": "rebaixamento",
                "aposentadoria": "aposentadoria",
                "rookies": "rookies",
                "hierarquia": "hierarquia",
                "milestone": "milestone",
            }
            filtro_tipo = mapa_tipos.get(filtro_texto, "")

        noticias = listar_noticias_ordenadas(self.banco, tipo=filtro_tipo, limite=120)
        if not noticias:
            vazio = QLabel("Nenhuma noticia disponivel para o filtro atual.")
            vazio.setWordWrap(True)
            vazio.setFont(Fontes.texto_normal())
            vazio.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
            self._layout_noticias_cards.addWidget(vazio)
            self._layout_noticias_cards.addStretch(1)
            return

        for noticia in noticias:
            if not isinstance(noticia, dict):
                continue

            card = QFrame()
            card.setStyleSheet(
                f"""
                QFrame {{
                    background-color: {Cores.FUNDO_CARD};
                    border: 1px solid {Cores.BORDA};
                    border-radius: 8px;
                }}
                """
            )
            layout_card = QVBoxLayout(card)
            layout_card.setContentsMargins(12, 10, 12, 10)
            layout_card.setSpacing(6)

            topo = QHBoxLayout()
            topo.setSpacing(6)

            icone = QLabel(str(noticia.get("icone", "*") or "*"))
            icone.setFont(Fontes.titulo_pequeno())
            icone.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
            topo.addWidget(icone)

            titulo = QLabel(str(noticia.get("titulo", "Noticia") or "Noticia"))
            titulo.setFont(Fontes.texto_normal())
            titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none; font-weight: 700;")
            titulo.setWordWrap(True)
            topo.addWidget(titulo, 1)

            rodada = noticia.get("rodada")
            temporada = noticia.get("temporada")
            meta_partes = []
            if isinstance(temporada, int) and temporada > 0:
                meta_partes.append(str(temporada))
            if isinstance(rodada, int) and rodada > 0:
                meta_partes.append(f"R{rodada}")
            categoria_nome = str(noticia.get("categoria_nome", "") or "").strip()
            if categoria_nome:
                meta_partes.append(categoria_nome)
            meta = QLabel(" | ".join(meta_partes))
            meta.setFont(Fontes.texto_pequeno())
            meta.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
            topo.addWidget(meta, 0, Qt.AlignRight)

            layout_card.addLayout(topo)

            texto_noticia = QLabel(str(noticia.get("texto", "") or ""))
            texto_noticia.setWordWrap(True)
            texto_noticia.setFont(Fontes.texto_pequeno())
            texto_noticia.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
            layout_card.addWidget(texto_noticia)

            self._layout_noticias_cards.addWidget(card)

        self._layout_noticias_cards.addStretch(1)

    def _popular_combo_outras_categorias(self) -> None:
        if not hasattr(self, "combo_outras_categorias"):
            return

        jogador = self._obter_jogador()
        categoria_jogador = str(
            jogador.get("categoria_atual", self.categoria_atual) if isinstance(jogador, dict) else self.categoria_atual
        ).strip()
        categorias_externas = [
            categoria
            for categoria in CATEGORIAS
            if str(categoria.get("id", "") or "").strip()
            and str(categoria.get("id", "") or "").strip() != categoria_jogador
        ]

        atual = str(self.combo_outras_categorias.currentData() or "").strip()

        self.combo_outras_categorias.blockSignals(True)
        self.combo_outras_categorias.clear()
        for categoria in categorias_externas:
            categoria_id = str(categoria.get("id", "") or "").strip()
            nome = str(categoria.get("nome", categoria_id) or categoria_id)
            self.combo_outras_categorias.addItem(nome, categoria_id)

        if self.combo_outras_categorias.count() > 0:
            indice = self.combo_outras_categorias.findData(atual)
            if indice < 0:
                indice = 0
            self.combo_outras_categorias.setCurrentIndex(indice)
        self.combo_outras_categorias.blockSignals(False)

    def _atualizar_aba_outras_categorias(self, *_args) -> None:
        if not hasattr(self, "combo_outras_categorias"):
            return

        self._popular_combo_outras_categorias()

        categoria_id = str(self.combo_outras_categorias.currentData() or "").strip()
        if not categoria_id:
            if hasattr(self, "lbl_outras_contexto"):
                self.lbl_outras_contexto.setText("Sem categorias externas dispon?veis no momento.")
            if hasattr(self, "tabela_outras_pilotos"):
                self.tabela_outras_pilotos.setRowCount(0)
            if hasattr(self, "tabela_outras_equipes"):
                self.tabela_outras_equipes.setRowCount(0)
            if hasattr(self, "lbl_outras_ultimo_resultado"):
                self.lbl_outras_ultimo_resultado.setText("Ultimo resultado: sem dados.")
            return

        categoria_nome = obter_nome_categoria(categoria_id)
        ano = int(self.banco.get("ano_atual", 2024) or 2024)

        rodada_categoria = 0
        obter_rodada = getattr(self, "_obter_rodada_categoria", None)
        if callable(obter_rodada):
            try:
                rodada_categoria = int(obter_rodada(categoria_id) or 0)
            except (TypeError, ValueError):
                rodada_categoria = 0

        total_corridas = 0
        obter_total = getattr(self, "_obter_total_corridas_categoria", None)
        if callable(obter_total):
            try:
                total_corridas = int(obter_total(categoria_id) or 0)
            except (TypeError, ValueError):
                total_corridas = 0

        ultimos = self.banco.get("ultimos_resultados_por_categoria", {})
        if isinstance(ultimos, dict):
            ultimo = ultimos.get(categoria_id, {})
        else:
            ultimo = {}
        if not isinstance(ultimo, dict):
            ultimo = {}

        rodada_ultima = int(ultimo.get("rodada", rodada_categoria) or rodada_categoria)
        circuito_ultimo = str(ultimo.get("circuito", "") or "").strip()
        if circuito_ultimo:
            contexto = (
                f"{categoria_nome} - Temporada {ano} | Rodada {rodada_ultima}/{max(1, total_corridas)}"
                f" | ?ltima: {circuito_ultimo}"
            )
        else:
            contexto = f"{categoria_nome} - Temporada {ano} | Rodada {rodada_categoria}/{max(1, total_corridas)}"

        self.lbl_outras_contexto.setText(contexto)

        pilotos = obter_pilotos_categoria(self.banco, categoria_id)
        pilotos_ordenados = self._ordenar_pilotos_campeonato(pilotos)
        self.tabela_outras_pilotos.setRowCount(len(pilotos_ordenados))
        for row, piloto in enumerate(pilotos_ordenados):
            self.tabela_outras_pilotos.setRowHeight(row, 28)
            nome = str(piloto.get("nome", "Piloto") or "Piloto")
            equipe = str(piloto.get("equipe_nome", "Sem equipe") or "Sem equipe")
            pontos = int(piloto.get("pontos_temporada", 0) or 0)
            self.tabela_outras_pilotos.setItem(
                row,
                0,
                self._criar_item_tabela(row + 1, Cores.TEXTO_PRIMARY, Cores.FUNDO_CARD, Qt.AlignCenter),
            )
            self.tabela_outras_pilotos.setItem(
                row,
                1,
                self._criar_item_tabela(nome, Cores.TEXTO_PRIMARY, Cores.FUNDO_CARD),
            )
            self.tabela_outras_pilotos.setItem(
                row,
                2,
                self._criar_item_tabela(equipe, Cores.TEXTO_SECONDARY, Cores.FUNDO_CARD),
            )
            self.tabela_outras_pilotos.setItem(
                row,
                3,
                self._criar_item_tabela(pontos, Cores.AMARELO, Cores.FUNDO_CARD, Qt.AlignCenter, negrito=True),
            )

        classificacao_equipes = obter_classificacao_equipes(self.banco, categoria_id)
        self.tabela_outras_equipes.setRowCount(len(classificacao_equipes))
        for row, equipe in enumerate(classificacao_equipes):
            self.tabela_outras_equipes.setRowHeight(row, 28)
            nome_equipe = str(equipe.get("nome", "Equipe") or "Equipe")
            pontos_eq = int(equipe.get("pontos_temporada", 0) or 0)
            self.tabela_outras_equipes.setItem(
                row,
                0,
                self._criar_item_tabela(row + 1, Cores.TEXTO_PRIMARY, Cores.FUNDO_CARD, Qt.AlignCenter),
            )
            self.tabela_outras_equipes.setItem(
                row,
                1,
                self._criar_item_tabela(nome_equipe, Cores.TEXTO_PRIMARY, Cores.FUNDO_CARD),
            )
            self.tabela_outras_equipes.setItem(
                row,
                2,
                self._criar_item_tabela(pontos_eq, Cores.AMARELO, Cores.FUNDO_CARD, Qt.AlignCenter, negrito=True),
            )

        classificacao_ultima = ultimo.get("classificacao", []) if isinstance(ultimo, dict) else []
        if isinstance(classificacao_ultima, list) and classificacao_ultima:
            top = [
                item
                for item in classificacao_ultima
                if isinstance(item, dict) and not bool(item.get("dnf", False))
            ]
            top1 = str(top[0].get("piloto_nome", "-") or "-") if len(top) > 0 else "-"
            top2 = str(top[1].get("piloto_nome", "-") or "-") if len(top) > 1 else "-"

            dnf = [
                item
                for item in classificacao_ultima
                if isinstance(item, dict) and bool(item.get("dnf", False))
            ]
            if dnf:
                nome_dnf = str(dnf[0].get("piloto_nome", "Piloto") or "Piloto")
                motivo_dnf = str(dnf[0].get("motivo_dnf", "abandono") or "abandono")
                txt_dnf = f" | DNF: {nome_dnf} ({motivo_dnf})"
            else:
                txt_dnf = ""

            self.lbl_outras_ultimo_resultado.setText(
                f"Ultimo resultado (Rodada {max(1, rodada_ultima)}): P1 {top1} | P2 {top2}{txt_dnf}"
            )
        else:
            self.lbl_outras_ultimo_resultado.setText("Ultimo resultado: sem dados para esta categoria.")

    def _atualizar_info_temporada(self):
        ano = int(self.banco.get("ano_atual", 2024))
        temporada = int(self.banco.get("temporada_atual", 1))
        try:
            rodada = int(self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada = 1
        total = self._obter_total_rodadas_temporada()
        proximo_evento = self._get_proximo_evento_exibicao()
        rodada_exibicao = min(max(rodada, 1), total)

        if self._temporada_concluida():
            texto = f"Temporada {temporada} • {ano} | Temporada concluída"
        else:
            texto = f"Temporada {temporada} • {ano} | Rodada {rodada_exibicao}/{total}"

        if proximo_evento and proximo_evento.get("tipo_evento") == "pcc":
            mes_nome = proximo_evento.get("mes_nome", "-")
            texto += f" | Convite especial: {mes_nome} (PCC)"

        if hasattr(self, "lbl_info_temporada"):
            self.lbl_info_temporada.setText(texto)

    def _atualizar_proxima_corrida(self):
        if hasattr(self, "_rw_stack"):
            self._rw_atualizar_tela_weekend()

    def _atualizar_previsao_campeonato(self):
        if not hasattr(self, "lbl_previsao_temporada"):
            return

        def _resetar_visual(mensagem: str):
            self.stat_prev_posicao.set_valor("-")
            self.stat_prev_diferenca.set_valor("-")
            self.stat_prev_restantes.set_valor("0")
            self.lbl_previsao_status.setText(mensagem)
            self.lbl_previsao_gap_titulo.setText("—")
            self.card_previsao_cenarios.set_titulo("SE VOCÊ VENCER AS PRÓXIMAS CORRIDAS")
            for row in self.previsao_disputa_rows:
                row["nome"].setText("—")
                row["pontos"].setText("0 pts")
                row["barra"].setValue(0)
                row["percentual"].setText("0%")
            for bloco in (self.previsao_melhor_widgets, self.previsao_pior_widgets):
                bloco["status"].setText("—")
                bloco["delta"].setText("0 pts")
                bloco["condicao_1"].setText("• —")
                bloco["condicao_2"].setText("• —")
                bloco["probabilidade"].setText("Probabilidade: --%")
                bloco["barra"].setValue(0)
            self.lbl_req_plano_a_1.setText("⬜ —")
            self.lbl_req_plano_a_2.setText("⬜ —")
            self.lbl_req_plano_b_1.setText("⬜ —")
            self.lbl_req_plano_b_2.setText("⬜ —")
            self.lbl_previsao_grafico.setText("Sem dados suficientes para projeção.")
            self.card_previsao_decisiva.setVisible(False)

        ano_atual = int(self.banco.get("ano_atual", 2024))
        nome_campeonato = NOMES_CAMPEONATO.get(
            self.categoria_atual,
            obter_nome_categoria(self.categoria_atual),
        )
        self.lbl_previsao_temporada.setText(f"{str(nome_campeonato).upper()} — {ano_atual}")

        pilotos_categoria = obter_pilotos_categoria(self.banco, self.categoria_atual)
        classificacao_atual = self._ordenar_pilotos_campeonato(pilotos_categoria)
        if not classificacao_atual:
            _resetar_visual("Sem dados de pilotos na categoria para calcular os cenários.")
            return

        indice_jogador = next(
            (
                indice
                for indice, piloto in enumerate(classificacao_atual)
                if piloto.get("is_jogador", False)
            ),
            -1,
        )
        if indice_jogador < 0:
            _resetar_visual("Previsão indisponível: o jogador não está na categoria selecionada.")
            return

        corridas_restantes = self._corridas_restantes()
        jogador = classificacao_atual[indice_jogador]
        posicao_atual = indice_jogador + 1
        pontos_jogador = int(jogador.get("pontos_temporada", 0))
        lider = classificacao_atual[0]
        pontos_lider = int(lider.get("pontos_temporada", 0))
        nome_lider = str(lider.get("nome", "Líder"))

        if posicao_atual == 1 and len(classificacao_atual) > 1:
            referencia_gap = classificacao_atual[1]
            delta_atual = pontos_jogador - int(referencia_gap.get("pontos_temporada", 0))
            self.stat_prev_diferenca.lbl_desc.setText("PARA O 2º")
        else:
            referencia_gap = lider
            delta_atual = pontos_jogador - int(referencia_gap.get("pontos_temporada", 0))
            self.stat_prev_diferenca.lbl_desc.setText("DO LÍDER")

        cor_pos = Cores.AMARELO if posicao_atual == 1 else Cores.ACCENT_PRIMARY
        if posicao_atual > 3:
            cor_pos = Cores.TEXTO_PRIMARY
        cor_gap = Cores.VERDE if delta_atual >= 0 else Cores.VERMELHO

        self.stat_prev_posicao.set_valor(f"{posicao_atual}º", cor_pos)
        self.stat_prev_diferenca.set_valor(self._formatar_diferenca_pontos(delta_atual), cor_gap)
        self.stat_prev_restantes.set_valor(str(corridas_restantes), Cores.AMARELO)
        self.stat_prev_restantes.lbl_desc.setText("CORRIDAS")

        if posicao_atual == 1:
            self.lbl_previsao_status.setText(
                f"Você lidera o campeonato com {self._formatar_diferenca_pontos(delta_atual)} para o vice."
            )
        else:
            self.lbl_previsao_status.setText(
                f"Faltam {corridas_restantes} corridas e você está em {posicao_atual}º, "
                f"{self._formatar_diferenca_pontos(delta_atual)} do líder."
            )

        pilotos_disputa: list[dict[str, Any]] = [lider]
        ids_usados = {lider.get("id")}
        if jogador.get("id") not in ids_usados:
            pilotos_disputa.append(jogador)
            ids_usados.add(jogador.get("id"))

        for piloto in classificacao_atual:
            piloto_id = piloto.get("id")
            if piloto_id in ids_usados:
                continue
            pilotos_disputa.append(piloto)
            ids_usados.add(piloto_id)
            if len(pilotos_disputa) >= 3:
                break

        while pilotos_disputa and len(pilotos_disputa) < 3:
            pilotos_disputa.append(pilotos_disputa[-1])

        posicoes_por_id = {
            piloto.get("id"): indice + 1
            for indice, piloto in enumerate(classificacao_atual)
        }

        for indice, row in enumerate(self.previsao_disputa_rows):
            if indice >= len(pilotos_disputa):
                row["nome"].setText("—")
                row["pontos"].setText("0 pts")
                row["barra"].setValue(0)
                row["percentual"].setText("0%")
                continue

            piloto = pilotos_disputa[indice]
            piloto_id = piloto.get("id")
            posicao = int(posicoes_por_id.get(piloto_id, indice + 1))
            pontos = int(piloto.get("pontos_temporada", 0))
            is_jogador = bool(piloto.get("is_jogador", False))

            nome_exibicao = "Você" if is_jogador else str(piloto.get("nome", "—"))
            if posicao == 1 and not is_jogador:
                nome_exibicao = f"{nome_exibicao} (Líder)"
            else:
                nome_exibicao = f"{nome_exibicao} ({posicao}º)"

            percentual = 100 if pontos_lider <= 0 else int(round((pontos / pontos_lider) * 100))
            percentual_visual = max(0, min(100, percentual))

            cor_barra = Cores.AMARELO if posicao == 1 else Cores.VERDE
            if is_jogador:
                cor_barra = Cores.ACCENT_PRIMARY
            row["barra"].setStyleSheet(self._estilo_barra_previsao(cor_barra))

            row["nome"].setText(nome_exibicao)
            row["pontos"].setText(f"{pontos} pts")
            row["barra"].setValue(percentual_visual)
            row["percentual"].setText(f"{percentual}%")

        if posicao_atual == 1:
            self.lbl_previsao_gap_titulo.setText(
                f"↑ {self._formatar_diferenca_pontos(delta_atual)} para o vice-líder"
            )
            self.lbl_previsao_gap_titulo.setStyleSheet(
                f"color: {Cores.VERDE}; border: none; background: transparent;"
            )
        else:
            self.lbl_previsao_gap_titulo.setText(
                f"↑ {self._formatar_diferenca_pontos(delta_atual)} para o título"
            )
            self.lbl_previsao_gap_titulo.setStyleSheet(
                f"color: {Cores.AMARELO}; border: none; background: transparent;"
            )

        melhor_classificacao = self._simular_previsao_com_vitorias(
            classificacao_atual,
            corridas_restantes,
            favorecer_adversarios=False,
        )
        pior_classificacao = self._simular_previsao_com_vitorias(
            classificacao_atual,
            corridas_restantes,
            favorecer_adversarios=True,
        )
        resumo_melhor = self._resumo_classificacao_previsao(melhor_classificacao)
        resumo_pior = self._resumo_classificacao_previsao(pior_classificacao)
        if resumo_melhor is None or resumo_pior is None:
            _resetar_visual("Não foi possível calcular a previsão de campeonato.")
            return

        if corridas_restantes == 1:
            self.card_previsao_cenarios.set_titulo("SE VOCÊ VENCER A PRÓXIMA CORRIDA")
        else:
            self.card_previsao_cenarios.set_titulo(
                f"SE VOCÊ VENCER AS {corridas_restantes} PRÓXIMAS CORRIDAS"
            )

        pos_melhor = int(resumo_melhor["posicao"])
        pos_pior = int(resumo_pior["posicao"])
        delta_melhor = int(resumo_melhor["delta"])
        delta_pior = int(resumo_pior["delta"])

        self.previsao_melhor_widgets["status"].setText(
            self._descricao_posicao_previsao(pos_melhor)
        )
        self.previsao_melhor_widgets["delta"].setText(
            self._formatar_diferenca_pontos(delta_melhor)
        )
        self.previsao_pior_widgets["status"].setText(
            self._descricao_posicao_previsao(pos_pior)
        )
        self.previsao_pior_widgets["delta"].setText(
            self._formatar_diferenca_pontos(delta_pior)
        )

        if pos_melhor == 1:
            self.previsao_melhor_widgets["condicao_1"].setText(f"• {nome_lider} fora do top 5")
            self.previsao_melhor_widgets["condicao_2"].setText("• Você manter sequência de vitórias")
        else:
            self.previsao_melhor_widgets["condicao_1"].setText("• Líder seguir pontuando forte")
            self.previsao_melhor_widgets["condicao_2"].setText("• Rivais diretos manterem ritmo")

        self.previsao_pior_widgets["condicao_1"].setText(f"• {nome_lider} manter pódios")
        self.previsao_pior_widgets["condicao_2"].setText("• Concorrência direta pontuar alto")

        prob_base = self._calcular_probabilidade_titulo_previsao(
            delta_atual,
            corridas_restantes,
            posicao_atual,
        )
        prob_melhor = max(5, min(95, prob_base + 15))
        prob_pior = max(5, min(95, 100 - prob_base))

        self.previsao_melhor_widgets["probabilidade"].setText(
            f"Probabilidade: {prob_melhor}%"
        )
        self.previsao_melhor_widgets["barra"].setValue(prob_melhor)
        self.previsao_pior_widgets["probabilidade"].setText(
            f"Probabilidade: {prob_pior}%"
        )
        self.previsao_pior_widgets["barra"].setValue(prob_pior)

        if corridas_restantes <= 0:
            self.lbl_req_plano_a_1.setText("⬜ Temporada encerrada")
            self.lbl_req_plano_a_2.setText("⬜ Resultado final já definido")
            self.lbl_req_plano_b_1.setText("⬜ Preparar estratégia para a próxima temporada")
            self.lbl_req_plano_b_2.setText("⬜ Revisar evolução da equipe e dos rivais")
        else:
            vitorias_min = 1
            if delta_atual < 0:
                swing_necessario = abs(delta_atual) + 1
                ganho_vs_top3 = max(
                    1,
                    int(PONTOS_POR_POSICAO.get(1, 25)) - int(PONTOS_POR_POSICAO.get(3, 15)),
                )
                vitorias_min = min(
                    corridas_restantes,
                    max(1, ceil(swing_necessario / ganho_vs_top3)),
                )

            pontos_potenciais_plano_a = (
                vitorias_min * int(PONTOS_POR_POSICAO.get(1, 25))
            ) + (
                max(corridas_restantes - vitorias_min, 0) * int(PONTOS_POR_POSICAO.get(5, 10))
            )
            max_lider_sem_vitoria = corridas_restantes * int(PONTOS_POR_POSICAO.get(2, 18))

            self.lbl_req_plano_a_1.setText(
                (
                    f"⬜ Vencer pelo menos {vitorias_min} das {corridas_restantes} corridas restantes"
                    f"<br><span style='color:{Cores.TEXTO_SECONDARY};'>"
                    f"Pontos potenciais: +{pontos_potenciais_plano_a} pts</span>"
                )
            )
            self.lbl_req_plano_a_2.setText(
                (
                    f"⬜ Líder ({nome_lider}) terminar fora do top 3 em pelo menos 1"
                    f"<br><span style='color:{Cores.TEXTO_SECONDARY};'>"
                    f"Isso limita o ganho dele por corrida</span>"
                )
            )
            self.lbl_req_plano_b_1.setText(
                (
                    f"⬜ Vencer TODAS as {corridas_restantes} corridas restantes"
                    f"<br><span style='color:{Cores.TEXTO_SECONDARY};'>"
                    f"+{corridas_restantes * int(PONTOS_POR_POSICAO.get(1, 25))} pts garantidos</span>"
                )
            )
            self.lbl_req_plano_b_2.setText(
                (
                    "⬜ Líder não pode vencer nenhuma"
                    f"<br><span style='color:{Cores.TEXTO_SECONDARY};'>"
                    f"Máximo dele seria +{max_lider_sem_vitoria} pts</span>"
                )
            )

        referencia_evolucao = lider
        if referencia_evolucao.get("id") == jogador.get("id") and len(classificacao_atual) > 1:
            referencia_evolucao = classificacao_atual[1]

        resultados_jogador = jogador.get("resultados_temporada", [])
        if not isinstance(resultados_jogador, list):
            resultados_jogador = []

        resultados_referencia = referencia_evolucao.get("resultados_temporada", [])
        if not isinstance(resultados_referencia, list):
            resultados_referencia = []

        corridas_disputadas = self._corridas_disputadas()
        serie_jogador = self._serie_cumulativa_previsao(resultados_jogador, corridas_disputadas)
        serie_referencia = self._serie_cumulativa_previsao(resultados_referencia, corridas_disputadas)
        serie_jogador[-1] = pontos_jogador
        serie_referencia[-1] = int(referencia_evolucao.get("pontos_temporada", 0))

        janela = min(6, len(serie_jogador), len(serie_referencia))
        hist_jogador = serie_jogador[-janela:]
        hist_referencia = serie_referencia[-janela:]

        proj_jogador = pontos_jogador + (corridas_restantes * int(PONTOS_POR_POSICAO.get(1, 25)))
        proj_referencia = int(referencia_evolucao.get("pontos_temporada", 0)) + (
            corridas_restantes * int(PONTOS_POR_POSICAO.get(2, 18))
        )

        spark_jogador = f"{self._sparkline_previsao(hist_jogador)}\u25CB"
        spark_referencia = f"{self._sparkline_previsao(hist_referencia)}\u25CB"

        inicio_eixo = max(corridas_disputadas - janela + 1, 1)
        eixo_labels = [f"E{inicio_eixo + i}" for i in range(janela)] + ["Proj"]
        eixo_texto = " ".join(label.rjust(4) for label in eixo_labels)

        nome_ref = "Líder" if referencia_evolucao.get("id") == lider.get("id") else "Vice-líder"
        self.lbl_previsao_grafico.setText(
            "\n".join(
                [
                    "Pontos",
                    f"Você      {spark_jogador}  ({pontos_jogador} -> {proj_jogador})",
                    (
                        f"{nome_ref:<10}{spark_referencia}  "
                        f"({int(referencia_evolucao.get('pontos_temporada', 0))} -> {proj_referencia})"
                    ),
                    f"Eixo      {eixo_texto}",
                    "Legenda: Histórico (▁..█) | Projeção (○)",
                ]
            )
        )

        corrida_atual = self._get_corrida_atual() or {}
        nome_corrida = str(corrida_atual.get("circuito", "")).strip() or str(
            corrida_atual.get("nome", "próxima etapa")
        )

        swing_proxima = int(PONTOS_POR_POSICAO.get(1, 25)) - int(PONTOS_POR_POSICAO.get(4, 12))
        delta_apos_corrida = delta_atual + swing_proxima
        max_recuperacao_restante = max(0, corridas_restantes - 1) * int(PONTOS_POR_POSICAO.get(1, 25))
        corrida_decisiva = corridas_restantes > 0 and delta_apos_corrida > max_recuperacao_restante

        if corrida_decisiva:
            self.card_previsao_decisiva.setVisible(True)
            self.lbl_previsao_decisiva.setText(
                (
                    "A próxima corrida pode definir o campeonato!\n\n"
                    "Se você vencer e o líder ficar fora do pódio,\n"
                    "você pode garantir o título matematicamente.\n\n"
                    f"Etapa decisiva: {nome_corrida}"
                )
            )
        else:
            self.card_previsao_decisiva.setVisible(False)

    def _atualizar_tabela_pilotos(self):
        pilotos = obter_pilotos_categoria(self.banco, self.categoria_atual)
        self.pilotos_ordenados = self._ordenar_pilotos_campeonato(pilotos)
        equipes_por_id = {
            equipe.get("id"): equipe
            for equipe in self.banco.get("equipes", [])
            if equipe.get("categoria") == self.categoria_atual
        }
        equipes_por_nome = {
            str(equipe.get("nome", "")).strip().casefold(): equipe
            for equipe in self.banco.get("equipes", [])
            if equipe.get("categoria") == self.categoria_atual
        }
        calendario = self._obter_calendario_temporada()
        qtd_corridas = max(1, int(getattr(self, "_qtd_colunas_corridas_tabela_pilotos", 4)))
        self._configurar_colunas_tabela_pilotos(qtd_corridas)

        inicio_corridas = 4
        coluna_pts = inicio_corridas + qtd_corridas
        coluna_medalhas = coluna_pts + 1

        headers = ["POS", "NAC", "IDADE", "PILOTO"]
        for indice in range(qtd_corridas):
            corrida = calendario[indice] if indice < len(calendario) else {}
            if not isinstance(corrida, dict):
                corrida = {}
            headers.append("")
        headers.extend(["PTS", "MEDALHAS"])
        self.tabela_pilotos.setHorizontalHeaderLabels(headers)
        header_widget = self.tabela_pilotos.horizontalHeader()
        rodada_proxima = self._obter_rodada_proxima_mock_tabela(qtd_corridas)
        if isinstance(header_widget, BandeiraHeaderView):
            header_widget.limpar_bandeiras()

        for coluna, texto_header in enumerate(headers):
            item_header = QTableWidgetItem(texto_header)
            alinhamento_header = Qt.AlignCenter
            if coluna == 3:
                alinhamento_header = Qt.AlignVCenter | Qt.AlignLeft
            if coluna in {coluna_pts, coluna_medalhas}:
                alinhamento_header = Qt.AlignCenter
            item_header.setTextAlignment(alinhamento_header)

            if inicio_corridas <= coluna < inicio_corridas + qtd_corridas:
                rodada = coluna - inicio_corridas + 1
                corrida = calendario[rodada - 1] if rodada - 1 < len(calendario) else {}
                if not isinstance(corrida, dict):
                    corrida = {}
                circuito = str(corrida.get("circuito", "") or "").strip()
                codigo_bandeira = self._obter_codigo_bandeira_corrida_dashboard(
                    circuito,
                    indice_fallback=rodada - 1,
                )
                item_header.setText("")
                if isinstance(header_widget, BandeiraHeaderView):
                    header_widget.definir_bandeira_coluna(coluna, codigo_bandeira)
                    estado_coluna = "past" if rodada < rodada_proxima else (
                        "next" if rodada == rodada_proxima else "future"
                    )
                    header_widget.definir_estado_coluna(coluna, estado_coluna)
                else:
                    item_header.setText(obter_emoji_bandeira(codigo_bandeira, fallback="🏳️"))
                item_header.setToolTip(
                    f"Rodada {rodada}: {circuito or 'Circuito indefinido'}"
                )
            self.tabela_pilotos.setHorizontalHeaderItem(coluna, item_header)

        self.tabela_pilotos.setRowCount(len(self.pilotos_ordenados))
        ids_destaque, equipe_chave_destacada = self._obter_contexto_destaque_equipes_tabela()
        cor_equipe_destacada = str(self._cor_equipe_destacada_tabela or "#3b82f6")
        if not cor_equipe_destacada or not QColor(cor_equipe_destacada).isValid():
            cor_equipe_destacada = "#3b82f6"
        mapa_tendencia = self._mapa_tendencia_real_tabela(self.pilotos_ordenados)
        chaves_rivais = self._obter_chaves_rivais_mock_tabela()
        cor_linha_destaque = "#1f4e66"
        cor_linha_jogador = "#2c3e56"
        ano_atual = self.banco.get("ano_atual", 0)
        try:
            ano_limite_titulos = int(ano_atual) - 1
        except (TypeError, ValueError):
            ano_limite_titulos = None
        if isinstance(ano_limite_titulos, int) and ano_limite_titulos < 0:
            ano_limite_titulos = None
        chave_campeao_anterior = self._obter_chave_campeao_pilotos_historico_dashboard(
            self.categoria_atual,
            ano_limite_titulos,
        )
        self._mapa_vmr_rodada_tabela = self._obter_mapa_vmr_por_rodada_tabela(
            self.pilotos_ordenados,
            qtd_corridas,
        )

        for row, piloto in enumerate(self.pilotos_ordenados):
            pos = row + 1
            is_jogador = bool(piloto.get("is_jogador", False))
            piloto_id = piloto.get("id")
            is_piloto_origem = (
                self._piloto_id_destacado_tabela is not None
                and piloto_id == self._piloto_id_destacado_tabela
            )

            self.tabela_pilotos.setRowHeight(row, 30)

            equipe_chave_piloto = self._normalizar_chave_equipe_tabela(
                piloto.get("equipe_nome", "")
            )
            if not equipe_chave_piloto:
                equipe_ref_inicial = equipes_por_id.get(piloto.get("equipe_id"))
                if isinstance(equipe_ref_inicial, dict):
                    equipe_chave_piloto = self._normalizar_chave_equipe_tabela(
                        equipe_ref_inicial.get("nome", "")
                    )
            linha_equipe_destacada = bool(
                equipe_chave_destacada and equipe_chave_piloto == equipe_chave_destacada
            )
            if equipe_chave_destacada and equipe_chave_piloto == equipe_chave_destacada:
                cor_base = cor_linha_jogador if is_jogador else (
                    Cores.FUNDO_CARD if row % 2 == 0 else Cores.FUNDO_APP
                )
                cor_fundo = self._cor_destaque_por_equipe(
                    cor_base,
                    cor_equipe_destacada,
                    alpha=76,
                )
            elif piloto_id in ids_destaque:
                cor_fundo = self._cor_destaque_por_equipe(
                    cor_linha_destaque,
                    cor_equipe_destacada,
                    alpha=76,
                )
            elif is_jogador:
                cor_fundo = cor_linha_jogador
            elif row % 2 == 0:
                cor_fundo = Cores.FUNDO_CARD
            else:
                cor_fundo = Cores.FUNDO_APP

            linha_destacada = linha_equipe_destacada or (piloto_id in ids_destaque)

            if pos == 1:
                cor_texto = Cores.OURO
            elif pos == 2:
                cor_texto = Cores.PRATA
            elif pos == 3:
                cor_texto = Cores.BRONZE
            else:
                cor_texto = Cores.TEXTO_PRIMARY

            nome = piloto.get("nome", "?")
            if is_jogador:
                nome = f"⭐ {nome}"
            titulos_historicos = self._contar_titulos_historicos_piloto_dashboard(
                piloto,
                self.categoria_atual,
                ano_limite=ano_limite_titulos,
            )
            if titulos_historicos > 0:
                nome = f"{nome}      x{titulos_historicos}"
            chave_hist_piloto = self._chave_piloto_historico_dashboard(
                piloto.get("id"),
                piloto.get("nome", ""),
            )
            foi_campeao_anterior = bool(
                chave_campeao_anterior
                and chave_hist_piloto
                and chave_hist_piloto == chave_campeao_anterior
            )

            resultados = piloto.get("resultados_temporada", [])
            if not isinstance(resultados, list):
                resultados = []

            equipe = equipes_por_id.get(piloto.get("equipe_id"))
            if not isinstance(equipe, dict):
                equipe_nome = str(piloto.get("equipe_nome", "") or "").strip().casefold()
                equipe = equipes_por_nome.get(equipe_nome)
            cor_equipe = equipe.get("cor_primaria", Cores.TEXTO_SECONDARY) if equipe else Cores.TEXTO_SECONDARY
            if not equipe_chave_piloto and isinstance(equipe, dict):
                equipe_chave_piloto = self._normalizar_chave_equipe_tabela(
                    equipe.get("nome", "")
                )

            medalhas = self._montar_medalhas_resultados_dashboard(resultados)
            if not medalhas:
                medalhas = "—"

            codigo_bandeira_nac = self._obter_codigo_bandeira_nacionalidade_piloto(piloto)
            emoji_nacionalidade = obter_emoji_bandeira(codigo_bandeira_nac, fallback="🏳️")
            idade = piloto.get("idade", "?")
            chave_piloto = self._chave_piloto_mock_tabela(piloto)
            is_rival = (not is_jogador) and bool(chave_piloto) and chave_piloto in chaves_rivais
            estado_tendencia = mapa_tendencia.get(chave_piloto, "flat")

            item_posicao = self._criar_item_tabela(
                pos,
                "#ffffff" if linha_destacada else cor_texto,
                cor_fundo,
                Qt.AlignCenter,
                negrito=True,
            )
            item_posicao.setData(
                BadgeHeatmapDelegate.ROLE_POS_TENDENCIA,
                {"estado": estado_tendencia},
            )
            self.tabela_pilotos.setItem(
                row,
                0,
                item_posicao,
            )
            item_nac = self._criar_item_tabela(
                emoji_nacionalidade,
                "#ffffff" if linha_destacada else Cores.TEXTO_PRIMARY,
                cor_fundo,
                Qt.AlignCenter,
            )
            item_nac.setData(BadgeHeatmapDelegate.ROLE_BANDEIRA_CODIGO, codigo_bandeira_nac)
            if item_nac is not None:
                fonte_nac = item_nac.font()
                fonte_nac.setFamily("Segoe UI Emoji")
                item_nac.setFont(fonte_nac)
            self.tabela_pilotos.setItem(row, 1, item_nac)
            self.tabela_pilotos.setItem(
                row,
                2,
                self._criar_item_tabela(
                    idade,
                    "#ffffff" if linha_destacada else Cores.TEXTO_SECONDARY,
                    cor_fundo,
                    Qt.AlignCenter,
                ),
            )
            negrito_piloto = bool(is_jogador or pos <= 3)
            if linha_destacada:
                negrito_piloto = is_piloto_origem
            item_piloto = self._criar_item_tabela(
                nome,
                "#ffffff" if linha_destacada else cor_texto,
                cor_fundo,
                negrito=negrito_piloto,
            )
            item_piloto.setData(
                BadgeHeatmapDelegate.ROLE_INLINE_PREFIX,
                {
                    "cor_fundo": cor_equipe,
                    "cor_borda": "#333333",
                    "tamanho": 9,
                    "gap": 6,
                },
            )
            item_piloto.setData(BadgeHeatmapDelegate.ROLE_EQUIPE_CHAVE, equipe_chave_piloto)
            item_piloto.setData(BadgeHeatmapDelegate.ROLE_EQUIPE_COR, cor_equipe)
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
            sufixos: list[dict[str, Any]] = []
            if is_rival:
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
                    BadgeHeatmapDelegate.ROLE_INLINE_SUFFIX,
                    payload_sufixo,
                )
            self.tabela_pilotos.setItem(
                row,
                3,
                item_piloto,
            )

            for indice_corrida in range(qtd_corridas):
                coluna = inicio_corridas + indice_corrida
                resultado_raw = resultados[indice_corrida] if indice_corrida < len(resultados) else None
                (
                    texto_resultado,
                    cor_resultado,
                    cor_fundo_badge,
                    cor_borda,
                    negrito,
                    texto_reduzido,
                ) = self._formatar_resultado_heatmap_tabela(resultado_raw)
                marcador_vmr = self._obter_marcadores_evento_mock_tabela(
                    piloto,
                    indice_corrida,
                    resultado_raw,
                )

                item_resultado = self._criar_item_tabela(
                    texto_resultado,
                    cor_resultado,
                    cor_fundo,
                    Qt.AlignCenter,
                )
                if negrito:
                    fonte = item_resultado.font()
                    fonte.setBold(True)
                    item_resultado.setFont(fonte)
                item_resultado.setData(
                    BadgeHeatmapDelegate.ROLE_BADGE,
                    {
                        "texto": texto_resultado,
                        "cor_texto": cor_resultado,
                        "cor_fundo": cor_fundo_badge,
                        "cor_borda": cor_borda,
                        "negrito": negrito,
                        "texto_reduzido": texto_reduzido,
                        "marcador_vmr": marcador_vmr,
                    },
                )
                self.tabela_pilotos.setItem(row, coluna, item_resultado)

            pontos_piloto = int(piloto.get("pontos_temporada", 0) or 0)
            cor_pts_piloto = (
                "#ffffff"
                if linha_destacada or pontos_piloto > 0
                else "#555555"
            )
            item_pontos = self._criar_item_tabela(
                pontos_piloto,
                cor_pts_piloto,
                cor_fundo,
                Qt.AlignCenter,
                negrito=linha_destacada or pontos_piloto > 0,
            )
            fonte_pontos = item_pontos.font()
            tamanho_base = fonte_pontos.pointSizeF() if fonte_pontos.pointSizeF() > 0 else float(fonte_pontos.pointSize())
            incremento = 0.4
            if pos == 1:
                incremento = 1.6
            elif pos == 2:
                incremento = 1.2
            elif pos == 3:
                incremento = 0.8
            fonte_pontos.setPointSizeF(max(8.5, tamanho_base + incremento))
            item_pontos.setFont(fonte_pontos)
            self.tabela_pilotos.setItem(row, coluna_pts, item_pontos)
            self.tabela_pilotos.setItem(
                row,
                coluna_medalhas,
                self._criar_item_tabela(
                    medalhas,
                    "#ffffff"
                    if linha_destacada
                    else (Cores.TEXTO_PRIMARY if medalhas != "—" else "#555555"),
                    cor_fundo,
                    Qt.AlignCenter,
                ),
            )

        self.tabela_pilotos.viewport().update()

    def _atualizar_tabela_equipes(self):
        calcular_pontos_equipes(self.banco, self.categoria_atual)
        equipes = obter_equipes_categoria(self.banco, self.categoria_atual)
        self.equipes_ordenadas = self._ordenar_equipes_campeonato(equipes)
        trofeus_equipes = self._obter_trofeus_equipes_historico_tabela()
        ano_atual = self.banco.get("ano_atual", 0)
        try:
            ano_anterior = int(ano_atual) - 1
        except (TypeError, ValueError):
            ano_anterior = None
        if isinstance(ano_anterior, int) and ano_anterior < 0:
            ano_anterior = None
        podio_construtores_anterior = self._obter_podio_construtores_historico_dashboard(
            self.categoria_atual,
            ano_anterior,
        )
        max_ouro = 0
        for info_trofeus in trofeus_equipes.values():
            if not isinstance(info_trofeus, dict):
                continue
            max_ouro = max(max_ouro, int(info_trofeus.get("ouro", 0) or 0))
        equipe_chave_destacada = self._normalizar_chave_equipe_tabela(
            self._equipe_chave_destacada_tabela
        )
        cor_equipe_destacada = str(self._cor_equipe_destacada_tabela or "#3b82f6")
        if not cor_equipe_destacada or not QColor(cor_equipe_destacada).isValid():
            cor_equipe_destacada = "#3b82f6"

        self.tabela_equipes.setRowCount(len(self.equipes_ordenadas))

        for row, equipe in enumerate(self.equipes_ordenadas):
            pos = row + 1
            self.tabela_equipes.setRowHeight(row, 32)

            cor_equipe = equipe.get("cor_primaria", Cores.TEXTO_PRIMARY)
            nome_equipe = str(equipe.get("nome", "") or "")
            nome_equipe_chave = self._normalizar_chave_equipe_tabela(nome_equipe)

            if pos <= 3:
                cor_base = "#1a3a2a"
            elif pos % 2 == 0:
                cor_base = Cores.FUNDO_CARD
            else:
                cor_base = Cores.FUNDO_APP

            if equipe_chave_destacada and nome_equipe_chave == equipe_chave_destacada:
                cor_fundo = self._cor_destaque_por_equipe(
                    cor_base,
                    cor_equipe_destacada,
                    alpha=48,
                )
                linha_destacada = True
            else:
                cor_fundo = cor_base
                linha_destacada = False

            if pos == 1:
                cor_pos = Cores.AMARELO
            elif pos == 2:
                cor_pos = "#C0C0C0"
            elif pos == 3:
                cor_pos = "#CD7F32"
            else:
                cor_pos = Cores.TEXTO_PRIMARY
            if linha_destacada:
                cor_pos = "#ffffff"

            self.tabela_equipes.setItem(
                row,
                0,
                self._criar_item_tabela(pos, cor_pos, cor_fundo, Qt.AlignCenter),
            )
            self.tabela_equipes.setItem(
                row,
                1,
                self._criar_item_tabela(
                    nome_equipe or "?",
                    "#ffffff" if linha_destacada else cor_equipe,
                    cor_fundo,
                    negrito=linha_destacada,
                ),
            )
            item_equipe = self.tabela_equipes.item(row, 1)
            if item_equipe is not None:
                item_equipe.setData(BadgeHeatmapDelegate.ROLE_EQUIPE_CHAVE, nome_equipe_chave)
                item_equipe.setData(BadgeHeatmapDelegate.ROLE_EQUIPE_COR, cor_equipe)
            self.tabela_equipes.setItem(
                row,
                2,
                self._criar_item_tabela(
                    equipe.get("pontos_temporada", 0),
                    "#ffffff" if linha_destacada else cor_pos,
                    cor_fundo,
                    Qt.AlignCenter,
                    negrito=True,
                ),
            )
            item_pts_equipe = self.tabela_equipes.item(row, 2)
            if item_pts_equipe is not None:
                fonte_pts = item_pts_equipe.font()
                tamanho_base = fonte_pts.pointSizeF() if fonte_pts.pointSizeF() > 0 else float(fonte_pts.pointSize())
                incremento = 0.5
                if pos == 1:
                    incremento = 1.3
                elif pos == 2:
                    incremento = 1.0
                elif pos == 3:
                    incremento = 0.8
                fonte_pts.setPointSizeF(max(8.5, tamanho_base + incremento))
                item_pts_equipe.setFont(fonte_pts)
            item_trofeus = self._criar_item_tabela(
                "",
                "#ffffff" if linha_destacada else Cores.TEXTO_PRIMARY,
                cor_fundo,
                Qt.AlignCenter,
            )
            trofeus_info_base = trofeus_equipes.get(
                nome_equipe_chave,
                {"ouro": 0, "prata": 0, "bronze": 0},
            )
            trofeus_info = {
                "ouro": int(trofeus_info_base.get("ouro", 0) or 0),
                "prata": int(trofeus_info_base.get("prata", 0) or 0),
                "bronze": int(trofeus_info_base.get("bronze", 0) or 0),
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
                    and int(trofeus_info_base.get("ouro", 0) or 0) == max_ouro
                ),
            }
            setas_tipos_info = trofeus_info["setas_tipos"]
            destaques = []
            if setas_tipos_info.get("ouro"):
                destaques.append("ouro (campeã)")
            if setas_tipos_info.get("prata"):
                destaques.append("prata (vice)")
            if setas_tipos_info.get("bronze"):
                destaques.append("bronze (3ª)")
            if destaques:
                item_trofeus.setToolTip(
                    "Pódio de construtores no ano anterior: " + ", ".join(destaques)
                )
            item_trofeus.setData(
                BadgeHeatmapDelegate.ROLE_TROFEUS_INFO,
                trofeus_info,
            )
            self.tabela_equipes.setItem(row, 3, item_trofeus)

        self.tabela_equipes.viewport().update()
        self._atualizar_grafico_equipes_dashboard()

    @staticmethod
    def _formatar_papel_resumo_jogador(papel_raw: Any) -> str:
        papel = str(papel_raw or "").strip().lower()
        if papel in {"numero_1", "n1"}:
            return "Nº1"
        if papel in {"numero_2", "n2"}:
            return "Nº2"
        if papel == "reserva":
            return "Reserva"
        return "-"

    def _atualizar_stats_jogador(self):
        if not hasattr(self, "lbl_resumo_jogador_titulo"):
            return

        jogador = self._obter_jogador()
        if not isinstance(jogador, dict):
            self.lbl_resumo_jogador_titulo.setText("Sem jogador ativo")
            self.lbl_resumo_jogador_l1.setText("Equipe: - | Papel: -")
            self.lbl_resumo_jogador_l2.setText("Contrato: -")
            self.lbl_resumo_jogador_l3.setText("Posicao: - | Pontos: -")
            self.lbl_resumo_jogador_l4.setText("Proxima corrida: -")
            if hasattr(self, "lbl_contrato_alerta"):
                self.lbl_contrato_alerta.setText("Contrato: sem alertas")
                self.lbl_contrato_alerta.setToolTip("")
                self.lbl_contrato_alerta.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
            if hasattr(self, "btn_meu_perfil_dashboard"):
                self.btn_meu_perfil_dashboard.setEnabled(False)
            return

        categoria_jogador = str(jogador.get("categoria_atual", self.categoria_atual) or self.categoria_atual).strip()
        categoria_nome = obter_nome_categoria(categoria_jogador) if categoria_jogador else "-"
        nome_jogador = str(jogador.get("nome", "Jogador") or "Jogador")
        equipe_nome = str(jogador.get("equipe_nome", "Sem equipe") or "Sem equipe")
        papel = self._formatar_papel_resumo_jogador(jogador.get("papel"))

        contrato_anos = max(0, int(jogador.get("contrato_anos", 0) or 0))
        contrato_txt = (
            f"{contrato_anos} ano(s) restante(s)"
            if contrato_anos > 0
            else "Contrato encerrando nesta temporada"
        )

        pilotos_categoria = obter_pilotos_categoria(self.banco, categoria_jogador)
        pilotos_ordenados = self._ordenar_pilotos_por_desempenho_dashboard(pilotos_categoria)
        total_pilotos = len(pilotos_ordenados)
        posicao = next(
            (
                indice + 1
                for indice, piloto in enumerate(pilotos_ordenados)
                if isinstance(piloto, dict) and bool(piloto.get("is_jogador", False))
            ),
            "-",
        )
        pontos = int(jogador.get("pontos_temporada", 0) or 0)
        if isinstance(posicao, int):
            posicao_txt = f"{posicao}º / {max(1, total_pilotos)}"
        else:
            posicao_txt = "-"

        evento = self._get_proximo_evento_exibicao()
        corrida = evento or self._get_corrida_atual()
        if corrida and not self._temporada_concluida():
            try:
                rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
            except (TypeError, ValueError):
                rodada_atual = 1
            total_rodadas = self._obter_total_rodadas_temporada()
            nome_corrida = str(corrida.get("circuito", corrida.get("nome", "Proxima corrida")) or "Proxima corrida")
            rodada_exibicao = min(max(rodada_atual, 1), max(1, total_rodadas))
            proxima_txt = f"Proxima corrida: {nome_corrida} (Rodada {rodada_exibicao}/{max(1, total_rodadas)})"
        elif self._temporada_concluida():
            proxima_txt = "Proxima corrida: temporada concluida"
        else:
            proxima_txt = "Proxima corrida: calendario indisponivel"

        self.lbl_resumo_jogador_titulo.setText(f"{nome_jogador} - {categoria_nome}")
        self.lbl_resumo_jogador_l1.setText(f"Equipe: {equipe_nome} | Papel: {papel}")
        self.lbl_resumo_jogador_l2.setText(f"Contrato: {contrato_txt}")
        self.lbl_resumo_jogador_l3.setText(f"Posicao: {posicao_txt} | Pontos: {pontos}")
        self.lbl_resumo_jogador_l4.setText(proxima_txt)
        if hasattr(self, "lbl_contrato_alerta"):
            _exp, avaliacao = self._obter_expectativa_e_avaliacao()
            alerta_contrato = self._rw_obter_alerta_contratual_visual(avaliacao=avaliacao)
            if isinstance(alerta_contrato, dict):
                tipo = str(alerta_contrato.get("tipo", "") or "").strip().lower()
                if tipo == "perigo":
                    cor = Cores.VERMELHO
                elif tipo == "positivo":
                    cor = Cores.VERDE
                else:
                    cor = Cores.AMARELO
                icone = str(alerta_contrato.get("icone", "") or "").strip()
                titulo = str(alerta_contrato.get("titulo", "Contrato") or "Contrato")
                texto = str(alerta_contrato.get("texto", "") or "").strip()
                detalhe = str(alerta_contrato.get("detalhe", "") or "").strip()
                tooltip = f"{texto}\n{detalhe}".strip()
                self.lbl_contrato_alerta.setStyleSheet(f"color: {cor}; border: none; font-weight: 700;")
                self.lbl_contrato_alerta.setText(f"{icone} {titulo}".strip())
                self.lbl_contrato_alerta.setToolTip(tooltip)
            else:
                self.lbl_contrato_alerta.setText("Contrato: sem alertas")
                self.lbl_contrato_alerta.setToolTip("")
                self.lbl_contrato_alerta.setStyleSheet(f"color: {Cores.TEXTO_MUTED}; border: none;")
        if hasattr(self, "btn_meu_perfil_dashboard"):
            self.btn_meu_perfil_dashboard.setEnabled(True)

    def _atualizar_minha_equipe(self):
        jogador = self._obter_jogador()
        equipe_data = obter_equipe_piloto(self.banco, jogador) if jogador else None

        if not equipe_data:
            self.frame_barra_equipe.setStyleSheet(
                f"background-color: {Cores.ACCENT_PRIMARY}; border: none; border-radius: 1px;"
            )
            self.lbl_minha_equipe_nome.setText("Sem equipe")
            self.lbl_minha_equipe_nome.setStyleSheet(
                f"color: {Cores.ACCENT_PRIMARY}; border: none; background: transparent;"
            )
            self.bar_aero.set_valor(0)
            self.bar_motor.set_valor(0)
            self.bar_chassi.set_valor(0)
            self.bar_confiab.set_valor(0)
            self.info_piloto_1.set_valor("-")
            self.info_piloto_2.set_valor("-")
            self.info_dinamica_n1.set_valor("-")
            self.info_dinamica_n2.set_valor("-")
            self.info_dinamica_status.set_valor("-")
            self.info_dinamica_detalhe.set_valor("-")
            self.info_pts_equipe.set_valor("0")
            self.info_vit_equipe.set_valor("0")
            self._atualizar_comparacao_jogador_companheiro(None, None, {})
            if hasattr(self, "lbl_expectativa_faixa"):
                self.lbl_expectativa_faixa.setText("Expectativa: -")
                self.lbl_expectativa_status.setText("Avaliacao: -")
                self.lbl_expectativa_impacto.setText("Impacto: -")
                self.txt_historico_avaliacao.setText("Sem dados de avaliacao.")
            return

        cor_equipe = equipe_data.get("cor_primaria", Cores.ACCENT_PRIMARY)
        self.frame_barra_equipe.setStyleSheet(
            f"background-color: {cor_equipe}; border: none; border-radius: 1px;"
        )
        self.lbl_minha_equipe_nome.setText(equipe_data.get("nome", "Minha Equipe"))
        self.lbl_minha_equipe_nome.setStyleSheet(
            f"color: {cor_equipe}; border: none; background: transparent;"
        )

        stats_equipe = equipe_data.get("stats", {})
        if not isinstance(stats_equipe, dict):
            stats_equipe = {}

        def _int_seguro(valor, padrao):
            try:
                return int(round(float(valor)))
            except (TypeError, ValueError):
                return padrao

        self.bar_aero.set_valor(
            _int_seguro(
                stats_equipe.get("aerodinamica", equipe_data.get("aero", 50)),
                50,
            )
        )
        self.bar_motor.set_valor(
            _int_seguro(
                stats_equipe.get("motor", equipe_data.get("motor", 50)),
                50,
            )
        )
        self.bar_chassi.set_valor(
            _int_seguro(
                stats_equipe.get("chassi", equipe_data.get("chassi", 50)),
                50,
            )
        )
        self.bar_confiab.set_valor(
            _int_seguro(
                stats_equipe.get("confiabilidade", equipe_data.get("confiabilidade", 50)),
                50,
            )
        )

        self.info_piloto_1.set_valor(equipe_data.get("piloto_1", "-") or "-")
        self.info_piloto_2.set_valor(equipe_data.get("piloto_2", "-") or "-")

        pilotos_por_id = {
            str(piloto.get("id")): piloto
            for piloto in self.banco.get("pilotos", [])
            if isinstance(piloto, dict)
        }
        hierarquia = equipe_data.get("hierarquia")
        if not isinstance(hierarquia, dict):
            hierarquia = {}

        n1_id = str(hierarquia.get("n1_id", equipe_data.get("piloto_numero_1")) or "")
        n2_id = str(hierarquia.get("n2_id", equipe_data.get("piloto_numero_2")) or "")
        piloto_n1 = pilotos_por_id.get(n1_id, {})
        piloto_n2 = pilotos_por_id.get(n2_id, {})

        nome_n1 = str(piloto_n1.get("nome", equipe_data.get("piloto_1", "-")) or "-")
        nome_n2 = str(piloto_n2.get("nome", equipe_data.get("piloto_2", "-")) or "-")
        try:
            skill_n1 = int(float(piloto_n1.get("skill", 0) or 0))
        except (TypeError, ValueError):
            skill_n1 = 0
        try:
            skill_n2 = int(float(piloto_n2.get("skill", 0) or 0))
        except (TypeError, ValueError):
            skill_n2 = 0

        self.info_dinamica_n1.set_valor(f"{nome_n1} (skill {skill_n1})")
        self.info_dinamica_n2.set_valor(f"{nome_n2} (skill {skill_n2})")

        status_hierarquia = str(hierarquia.get("status", "estavel") or "estavel").strip().lower()
        corridas_n2 = int(hierarquia.get("corridas_n2_a_frente", 0) or 0)
        rodada_evento = hierarquia.get("ultima_reavaliacao", "-")

        mapa_status = {
            "estavel": "Estavel",
            "tensao": "⚡ Tensao",
            "reavaliacao": "🔎 Reavaliacao",
            "invertido": "🔄 Invertido",
        }
        status_legivel = mapa_status.get(status_hierarquia, status_hierarquia or "-")
        if status_hierarquia == "tensao":
            detalhe = f"N2 esta a frente por {corridas_n2} corrida(s) consecutiva(s)."
        elif status_hierarquia == "invertido":
            detalhe = f"Hierarquia invertida na rodada {rodada_evento}."
        elif status_hierarquia == "reavaliacao":
            detalhe = f"Reavaliacao em curso ({corridas_n2} corridas com N2 a frente)."
        else:
            detalhe = "Sem tensao interna no momento."

        self.info_dinamica_status.set_valor(status_legivel)
        self.info_dinamica_detalhe.set_valor(detalhe)
        self.info_pts_equipe.set_valor(str(equipe_data.get("pontos_temporada", 0)))
        self.info_vit_equipe.set_valor(str(equipe_data.get("vitorias_temporada", 0)))

        companheiro = None
        jogador_id = jogador.get("id") if isinstance(jogador, dict) else None
        if isinstance(jogador, dict) and isinstance(piloto_n1, dict) and not self._ids_equivalentes_resultado(piloto_n1.get("id"), jogador_id):
            companheiro = piloto_n1
        if isinstance(jogador, dict) and isinstance(piloto_n2, dict) and not self._ids_equivalentes_resultado(piloto_n2.get("id"), jogador_id):
            companheiro = piloto_n2
        if not isinstance(companheiro, dict):
            equipe_nome = str(equipe_data.get("nome", "") or "").strip().casefold()
            for piloto in self.banco.get("pilotos", []):
                if not isinstance(piloto, dict):
                    continue
                if bool(piloto.get("aposentado", False)):
                    continue
                if str(piloto.get("equipe_nome", "") or "").strip().casefold() != equipe_nome:
                    continue
                if self._ids_equivalentes_resultado(piloto.get("id"), jogador_id):
                    continue
                companheiro = piloto
                break

        self._atualizar_comparacao_jogador_companheiro(jogador, companheiro, hierarquia)

        if hasattr(self, "lbl_expectativa_faixa"):
            expectativa, avaliacao = self._obter_expectativa_e_avaliacao(
                persistir_historico=True,
            )
            if isinstance(expectativa, dict) and isinstance(avaliacao, dict):
                faixa = str(expectativa.get("texto_faixa", "Top") or "Top")
                pos_real = int(avaliacao.get("posicao_real", 0) or 0)
                self.lbl_expectativa_faixa.setText(f"Expectativa: {faixa}")
                self.lbl_expectativa_status.setText(
                    f"Desempenho atual: {pos_real}o | {avaliacao.get('emoji', '')} {avaliacao.get('texto', '')}"
                )
                self.lbl_expectativa_impacto.setText(f"Impacto: {avaliacao.get('impacto', '-')}")

                historico_raw = self.banco.get("historico_avaliacoes", [])
                historico = [
                    item
                    for item in historico_raw
                    if isinstance(item, dict)
                    and str(item.get("categoria_id", "") or "") == str(self.categoria_atual or "")
                ]
                historico.sort(key=lambda item: int(item.get("rodada", 0) or 0))
                linhas_hist = []
                for item in historico[-8:]:
                    rodada = int(item.get("rodada", 0) or 0)
                    nivel = str(item.get("nivel", "neutro") or "neutro")
                    pos = int(item.get("posicao", 0) or 0)
                    emoji = {
                        "impressionada": "😍",
                        "satisfeita": "😊",
                        "neutra": "😐",
                        "preocupada": "😟",
                        "insatisfeita": "😠",
                    }.get(nivel, "😐")
                    linhas_hist.append(f"Rodada {rodada}: {emoji} {nivel} (posicao {pos}o)")
                self.txt_historico_avaliacao.setText(
                    "\n".join(linhas_hist) if linhas_hist else "Sem historico de avaliacao."
                )
            else:
                self.lbl_expectativa_faixa.setText("Expectativa: -")
                self.lbl_expectativa_status.setText("Avaliacao: sem dados")
                self.lbl_expectativa_impacto.setText("Impacto: -")
                self.txt_historico_avaliacao.setText("Sem historico de avaliacao.")

    def _valor_int_comparacao(self, piloto: dict[str, Any] | None, campo: str, padrao: int = 0) -> int:
        if not isinstance(piloto, dict):
            return int(padrao)
        try:
            return int(round(float(piloto.get(campo, padrao) or padrao)))
        except (TypeError, ValueError):
            return int(padrao)

    def _atualizar_comparacao_jogador_companheiro(
        self,
        jogador: dict[str, Any] | None,
        companheiro: dict[str, Any] | None,
        hierarquia: dict[str, Any] | None,
    ) -> None:
        if not hasattr(self, "tabela_comparacao_dupla"):
            return

        tabela = self.tabela_comparacao_dupla
        tabela.clearContents()

        if not isinstance(jogador, dict):
            tabela.setRowCount(0)
            if hasattr(self, "lbl_comparacao_status"):
                self.lbl_comparacao_status.setText("Comparacao indisponivel sem jogador ativo.")
            return

        papel_jogador = self._formatar_papel_resumo_jogador(jogador.get("papel"))
        nome_jogador = str(jogador.get("nome", "Voce") or "Voce")

        if isinstance(companheiro, dict):
            nome_comp = str(companheiro.get("nome", "Companheiro") or "Companheiro")
            papel_comp = self._formatar_papel_resumo_jogador(companheiro.get("papel"))
        else:
            nome_comp = "Sem companheiro"
            papel_comp = "-"

        melhor_j = self._valor_int_comparacao(jogador, "melhor_resultado_temporada", 99)
        melhor_c = self._valor_int_comparacao(companheiro, "melhor_resultado_temporada", 99)
        melhor_j_txt = "-" if melhor_j <= 0 or melhor_j >= 99 else f"P{melhor_j}"
        melhor_c_txt = "-" if melhor_c <= 0 or melhor_c >= 99 else f"P{melhor_c}"

        linhas = [
            ("Nome", nome_jogador, nome_comp, "texto"),
            ("Status", papel_jogador, papel_comp, "texto"),
            ("Skill", self._valor_int_comparacao(jogador, "skill", 0), self._valor_int_comparacao(companheiro, "skill", 0), "maior"),
            ("Corridas", self._valor_int_comparacao(jogador, "corridas_temporada", 0), self._valor_int_comparacao(companheiro, "corridas_temporada", 0), "maior"),
            ("Vit?rias", self._valor_int_comparacao(jogador, "vitorias_temporada", 0), self._valor_int_comparacao(companheiro, "vitorias_temporada", 0), "maior"),
            ("P?dios", self._valor_int_comparacao(jogador, "podios_temporada", 0), self._valor_int_comparacao(companheiro, "podios_temporada", 0), "maior"),
            ("Pontos", self._valor_int_comparacao(jogador, "pontos_temporada", 0), self._valor_int_comparacao(companheiro, "pontos_temporada", 0), "maior"),
            ("Melhor", melhor_j_txt, melhor_c_txt, "menor"),
        ]

        tabela.setRowCount(len(linhas))
        fundo_primario = Cores.FUNDO_CARD
        fundo_secundario = "#101929"
        cor_destaque = "#163528"

        for row, (rotulo, valor_j, valor_c, regra) in enumerate(linhas):
            fundo = fundo_secundario if row % 2 else fundo_primario
            tabela.setRowHeight(row, 28)

            item_rotulo = self._criar_item_tabela(rotulo, Cores.TEXTO_SECONDARY, fundo)
            tabela.setItem(row, 0, item_rotulo)

            item_j = self._criar_item_tabela(str(valor_j), Cores.TEXTO_PRIMARY, fundo, Qt.AlignCenter)
            item_c = self._criar_item_tabela(str(valor_c), Cores.TEXTO_PRIMARY, fundo, Qt.AlignCenter)

            if regra in {"maior", "menor"}:
                comp_j = valor_j
                comp_c = valor_c
                if regra == "menor":
                    try:
                        comp_j = int(str(valor_j).replace("P", "")) if str(valor_j).startswith("P") else 999
                    except ValueError:
                        comp_j = 999
                    try:
                        comp_c = int(str(valor_c).replace("P", "")) if str(valor_c).startswith("P") else 999
                    except ValueError:
                        comp_c = 999

                if comp_j != comp_c:
                    if (regra == "maior" and comp_j > comp_c) or (regra == "menor" and comp_j < comp_c):
                        item_j.setBackground(QBrush(QColor(cor_destaque)))
                    else:
                        item_c.setBackground(QBrush(QColor(cor_destaque)))

            tabela.setItem(row, 1, item_j)
            tabela.setItem(row, 2, item_c)

        if hasattr(self, "lbl_comparacao_status"):
            status = str((hierarquia or {}).get("status", "estavel") or "estavel")
            corridas_n2 = int((hierarquia or {}).get("corridas_n2_a_frente", 0) or 0)
            jogador_n2 = str(jogador.get("papel", "") or "").strip().lower() in {"numero_2", "n2"}
            if jogador_n2 and corridas_n2 > 0:
                self.lbl_comparacao_status.setText(
                    f"Status interno: {status}. Voce esta a frente ha {corridas_n2} corrida(s)."
                )
            elif corridas_n2 > 0:
                self.lbl_comparacao_status.setText(
                    f"Status interno: {status}. Companheiro esta a frente ha {corridas_n2} corrida(s)."
                )
            else:
                self.lbl_comparacao_status.setText(
                    f"Status interno: {status}. Sem vantagem recente entre os dois pilotos."
                )

    # ============================================================
    # FICHAS
    # ============================================================

    def _destacar_piloto_na_tela(self, piloto: dict[str, Any]) -> None:
        if not isinstance(piloto, dict):
            return
        if not hasattr(self, "tabela_pilotos"):
            return
        if not isinstance(getattr(self, "pilotos_ordenados", None), list):
            return

        piloto_id = piloto.get("id")
        nome_alvo = self._normalizar_texto_busca_dashboard(piloto.get("nome", ""))
        row = -1

        if piloto_id is not None:
            row = next(
                (
                    indice
                    for indice, piloto_ref in enumerate(self.pilotos_ordenados)
                    if self._ids_equivalentes(piloto_ref.get("id"), piloto_id)
                ),
                -1,
            )

        if row < 0 and nome_alvo:
            row = next(
                (
                    indice
                    for indice, piloto_ref in enumerate(self.pilotos_ordenados)
                    if self._normalizar_texto_busca_dashboard(piloto_ref.get("nome", "")) == nome_alvo
                ),
                -1,
            )

        if row < 0:
            return

        item_piloto = self.tabela_pilotos.item(row, 3)
        self._piloto_id_destacado_tabela = self.pilotos_ordenados[row].get("id")
        self._destacar_somente_piloto_tabela = True
        self._equipe_chave_destacada_tabela = ""
        if item_piloto is not None:
            self._cor_equipe_destacada_tabela = str(
                item_piloto.data(BadgeHeatmapDelegate.ROLE_EQUIPE_COR)
                or self._cor_equipe_destacada_tabela
                or "#3b82f6"
            )

        self._atualizar_tabela_pilotos()

        item_ref = self.tabela_pilotos.item(row, 3) or self.tabela_pilotos.item(row, 0)
        if item_ref is not None:
            self.tabela_pilotos.scrollToItem(item_ref, QAbstractItemView.PositionAtCenter)
            self.tabela_pilotos.setCurrentCell(row, 3)
            self.tabela_pilotos.viewport().update()

    def _destacar_equipe_na_tela(self, equipe: dict) -> None:
        """Destaca a equipe na tabela de construtores (e pilotos por equipe) ao abrir/navegar a FichaEquipe."""
        if not isinstance(equipe, dict):
            return
        nome_equipe = str(equipe.get("nome", "") or "").strip()
        chave = self._normalizar_chave_equipe_tabela(nome_equipe)
        cor = str(equipe.get("cor_primaria", "") or "").strip() or str(self._cor_equipe_destacada_tabela or "#3b82f6")
        if not chave:
            return
        self._equipe_chave_destacada_tabela = chave
        self._cor_equipe_destacada_tabela = cor
        self._piloto_id_destacado_tabela = None
        self._destacar_somente_piloto_tabela = False
        self._atualizar_tabela_pilotos()
        self._atualizar_tabela_equipes()
        # Scroll para a linha da equipe na tabela de construtores
        if hasattr(self, "tabela_equipes") and isinstance(getattr(self, "equipes_ordenadas", None), list):
            for row_eq, eq in enumerate(self.equipes_ordenadas):
                if self._normalizar_chave_equipe_tabela(str(eq.get("nome", "") or "")) == chave:
                    item_ref = self.tabela_equipes.item(row_eq, 1) or self.tabela_equipes.item(row_eq, 0)
                    if item_ref is not None:
                        self.tabela_equipes.scrollToItem(item_ref, QAbstractItemView.PositionAtCenter)
                        self.tabela_equipes.setCurrentCell(row_eq, 1)
                        self.tabela_equipes.viewport().update()
                    break
        self._atualizar_grafico_equipes_dashboard()

    def _abrir_ficha_piloto_tabela(self, row, col):
        if 0 <= row < len(self.pilotos_ordenados):
            self._abrir_ficha_piloto(self.pilotos_ordenados[row])


    def _abrir_ficha_piloto(self, piloto):
        try:
            from UI.fichas import FichaPiloto, preparar_payload_ficha_piloto

            categoria_nome = ""
            if hasattr(self, "combo_categoria"):
                categoria_nome = str(self.combo_categoria.currentText() or "").strip()
            payload = preparar_payload_ficha_piloto(
                piloto if isinstance(piloto, dict) else None,
                self.banco,
                categoria_nome=categoria_nome,
            )
            ficha = FichaPiloto(payload, self.banco, self)
            ficha.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Aviso", f"Ficha de piloto indisponível.\nErro: {e}")

    def _abrir_ficha_equipe_tabela(self, row, col):
        if 0 <= row < len(self.equipes_ordenadas):
            self._abrir_ficha_equipe(self.equipes_ordenadas[row])

    def _abrir_ficha_equipe(self, equipe):
        try:
            from UI.fichas import FichaEquipe

            ficha = FichaEquipe(equipe, self.banco, self)
            ficha.exec()
        except ImportError:
            QMessageBox.warning(self, "Aviso", "Ficha de equipe indisponível.")

    # ============================================================
    # EVENTOS
    # ============================================================

    def resizeEvent(self, event) -> None:
        self._posicionar_controles_fullscreen()
        self._aplicar_recuo_controles_topo(self._recuo_controles_topo_atual)
        super().resizeEvent(event)

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.WindowStateChange:
            if (
                self._fixar_tela_cheia
                and self.isVisible()
                and not self.isMinimized()
                and not self.isFullScreen()
            ):
                QTimer.singleShot(0, self.showFullScreen)
        super().changeEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        if hasattr(self, "_timer_controles_fullscreen"):
            self._timer_controles_fullscreen.stop()
        self._parar_monitor_resultados()
        super().closeEvent(event)

    def _ao_trocar_categoria(self, nome_categoria):
        categoria = next((c for c in CATEGORIAS if c["nome"] == nome_categoria), None)
        if categoria:
            self.categoria_atual = categoria["id"]
            self._piloto_id_destacado_tabela = None
            self._equipe_chave_destacada_tabela = ""
            self._cor_equipe_destacada_tabela = ""
            self._atualizar_tudo()

    def _navegar_categoria(self, direcao: int):
        if not hasattr(self, "combo_categoria"):
            return
        total = self.combo_categoria.count()
        if total <= 0:
            return
        atual = self.combo_categoria.currentIndex()
        novo = (atual + int(direcao)) % total
        self.combo_categoria.setCurrentIndex(novo)

    def _mostrar_aba(self, indice):
        if hasattr(self, "tabs") and 0 <= indice < self.tabs.count():
            if getattr(self, "_ux_initialized", False) and hasattr(self, "transicao_para_aba"):
                self.transicao_para_aba(indice)
                self._atualizar_navegacao_ativa()
            else:
                self.tabs.setCurrentIndex(indice)
                self._atualizar_navegacao_ativa()
            return
        self._atualizar_navegacao_ativa()

    def _atualizar_navegacao_ativa(self, *_):
        botoes = getattr(self, "nav_tab_buttons", [])
        if not botoes or not hasattr(self, "tabs"):
            return

        indice_ativo = self.tabs.currentIndex()
        for indice, botao in enumerate(botoes):
            botao.setChecked(indice == indice_ativo)



