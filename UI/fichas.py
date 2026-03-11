"""
Fichas detalhadas de pilotos e equipes
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtGui import QColor, QPixmap, QPainter, QPen, QFont, QImage
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QWidget, QScrollArea, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QGridLayout, QProgressBar, QPushButton,
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QGraphicsBlurEffect, QStackedLayout
)
from PySide6.QtCore import Qt, QPoint, QRect, QEasingCurve, QPropertyAnimation, QEvent, QTimer

from Dados.constantes import CATEGORIAS
from UI.temas import Cores, Fontes, Espacos
from UI.componentes import (
    CardTitulo, BotaoSecondary,
    LinhaInfo, BarraProgresso
)
from Utils.helpers import obter_nome_categoria
from Utils.bandeiras import (
    obter_codigo_bandeira,
    obter_emoji_bandeira,
    obter_pasta_bandeiras_absoluta,
)


def _tema_ficha(nome_tema: str | None) -> dict[str, str]:
    tema = str(nome_tema or "").strip().casefold()
    if tema == "historia":
        return {
            "backdrop": "rgba(8, 6, 6, 78)",
            "card_bg": "#0f0d0d",
            "card_border": "rgba(245, 247, 251, 24)",
            "header_bg": "#181312",
            "panel_bg": "#221a19",
            "chip_bg": "#2a211f",
            "plot_bg": "#1c1514",
            "timeline": "#4a3632",
            "text_primary": "#f5f7fb",
            "text_secondary": "#b3bccb",
            "text_muted": "#7f8a9b",
            "border": "#4a3632",
            "border_hover": "#6b4b44",
            "tab_active": "#ff6a3d",
            "drawer_hover_bg": "rgba(76, 44, 38, 230)",
            "nav_hover_bg": "rgba(88, 50, 40, 165)",
        }

    return {
        "backdrop": "rgba(8, 12, 18, 70)",
        "card_bg": "#0d131a",
        "card_border": "rgba(230, 237, 243, 26)",
        "header_bg": "#0c141f",
        "panel_bg": "#161e29",
        "chip_bg": "#101824",
        "plot_bg": "#0f1825",
        "timeline": "#2b3647",
        "text_primary": Cores.TEXTO_PRIMARY,
        "text_secondary": Cores.TEXTO_SECONDARY,
        "text_muted": Cores.TEXTO_MUTED,
        "border": Cores.BORDA,
        "border_hover": Cores.BORDA_HOVER,
        "tab_active": "#38d4ff",
        "drawer_hover_bg": "rgba(28, 44, 67, 230)",
        "nav_hover_bg": "rgba(35, 54, 82, 165)",
    }


def _estilo_tabs_ficha(
    *,
    cor_destaque: str = "#38d4ff",
    cor_inativa: str = "#d6e0ea",
    cor_hover: str = "#ffffff",
) -> str:
    return f"""
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar {{
            background: transparent;
            left: 0px;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {cor_inativa};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 10px 14px 8px 14px;
            margin-right: 14px;
            min-height: 28px;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            color: {cor_destaque};
            border-bottom-color: {cor_destaque};
            font-weight: 800;
        }}
        QTabBar::tab:hover:!selected {{
            color: {cor_hover};
        }}
    """


def _estilo_scroll_ficha(cor_handle: str | None = None) -> str:
    cor = str(cor_handle or "").strip() or Cores.BORDA_HOVER
    return f"""
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollBar:vertical {{
            width: 8px;
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {cor};
            border-radius: 4px;
            min-height: 28px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    """


def _estilo_tabela_ficha(
    *,
    cor_fundo: str = "#0f1622",
    cor_header: str = "#111c2a",
    cor_texto: str | None = None,
    cor_texto_secundario: str | None = None,
    cor_borda: str | None = None,
) -> str:
    texto = cor_texto or Cores.TEXTO_PRIMARY
    texto_sec = cor_texto_secundario or Cores.TEXTO_SECONDARY
    borda = cor_borda or Cores.BORDA
    return f"""
        QTableWidget {{
            background-color: {cor_fundo};
            color: {texto};
            border: none;
            gridline-color: {borda};
            outline: none;
        }}
        QTableWidget::item {{
            padding: 5px 9px;
            border-bottom: 1px solid {borda};
        }}
        QHeaderView::section {{
            background-color: {cor_header};
            color: {texto_sec};
            border: none;
            border-bottom: 1px solid {borda};
            padding: 7px 8px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        QTableWidget QTableCornerButton::section {{
            background-color: {cor_header};
            border: none;
        }}
    """


def _normalizar_texto_base(texto: Any) -> str:
    return " ".join(str(texto or "").strip().casefold().split())


def _categoria_id_por_nome(categoria_nome: Any, fallback: str = "mazda_rookie") -> str:
    nome = str(categoria_nome or "").strip()
    if not nome:
        return str(fallback or "mazda_rookie")
    for categoria in CATEGORIAS:
        if str(categoria.get("nome", "")).strip() == nome:
            return str(categoria.get("id", fallback or "mazda_rookie"))
    return str(fallback or "mazda_rookie")


def _resolver_cor_equipe_payload(
    piloto: dict[str, Any],
    banco: dict[str, Any],
    categoria_id: str,
    cor_equipe_hint: str = "",
) -> str:
    cor_hint = str(cor_equipe_hint or "").strip()
    if cor_hint and QColor(cor_hint).isValid():
        return cor_hint

    cor_direta = str(piloto.get("cor_equipe") or piloto.get("cor_primaria") or "").strip()
    if cor_direta and QColor(cor_direta).isValid():
        return cor_direta

    equipe_id = piloto.get("equipe_id")
    equipe_nome = _normalizar_texto_base(piloto.get("equipe_nome", ""))
    categoria_norm = _normalizar_texto_base(categoria_id)
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        cor_eq = str(equipe.get("cor_primaria", "") or "").strip()
        if not cor_eq or not QColor(cor_eq).isValid():
            continue

        if equipe_id not in (None, "") and equipe.get("id") == equipe_id:
            return cor_eq

        nome_eq = _normalizar_texto_base(equipe.get("nome", ""))
        categoria_eq = _normalizar_texto_base(equipe.get("categoria", ""))
        if equipe_nome and nome_eq == equipe_nome:
            if not categoria_norm or not categoria_eq or categoria_norm == categoria_eq:
                return cor_eq

    return Cores.ACCENT_PRIMARY


def preparar_payload_ficha_piloto(
    piloto_base: dict[str, Any] | None,
    banco: dict[str, Any],
    *,
    entrada_temporada: dict[str, Any] | None = None,
    categoria_nome: str | None = None,
    cor_equipe_hint: str = "",
) -> dict[str, Any] | None:
    def _safe_int(valor: Any, default: int = 0) -> int:
        try:
            return int(round(float(valor)))
        except (TypeError, ValueError):
            return int(default)

    piloto = dict(piloto_base or {})
    entrada = entrada_temporada if isinstance(entrada_temporada, dict) else {}

    nome_entrada = str(entrada.get("piloto", "") or "").strip()
    nome_base = str(piloto.get("nome", "") or "").strip()
    nome_final = nome_entrada or nome_base
    if not nome_final:
        return None

    categoria_padrao = str(piloto.get("categoria_atual", "") or "").strip() or "mazda_rookie"
    categoria_id = _categoria_id_por_nome(categoria_nome, fallback=categoria_padrao)

    equipe_entrada = str(entrada.get("equipe", "") or "").strip()
    equipe_base = str(piloto.get("equipe_nome", "") or "").strip()
    equipe_final = equipe_entrada or equipe_base or "Sem equipe"

    nacionalidade_base = str(piloto.get("nacionalidade", "") or "").strip()
    nacionalidade_entrada = str(
        entrada.get("nacionalidade")
        or entrada.get("nac")
        or entrada.get("country")
        or ""
    ).strip()
    nacionalidade_final = nacionalidade_base or nacionalidade_entrada

    piloto["id"] = piloto.get("id", entrada.get("piloto_id"))
    piloto["nome"] = nome_final
    piloto["equipe_nome"] = equipe_final
    piloto["categoria_atual"] = categoria_id
    piloto["nacionalidade"] = nacionalidade_final
    piloto["idade"] = piloto.get("idade", entrada.get("idade", "-"))

    if entrada:
        piloto["pontos_temporada"] = _safe_int(
            entrada.get("pontos", piloto.get("pontos_temporada", 0)),
            default=_safe_int(piloto.get("pontos_temporada", 0), 0),
        )
        resultados = entrada.get("resultados")
        if isinstance(resultados, list):
            piloto["resultados_temporada"] = list(resultados)

    defaults = {
        "titulos": 0,
        "vitorias_carreira": 0,
        "podios_carreira": 0,
        "poles_carreira": 0,
        "corridas_carreira": 0,
        "dnfs_carreira": 0,
        "incidentes_carreira": 0,
    }
    for chave, valor_default in defaults.items():
        piloto[chave] = piloto.get(chave, valor_default)

    piloto["cor_equipe"] = _resolver_cor_equipe_payload(
        piloto,
        banco if isinstance(banco, dict) else {},
        categoria_id,
        cor_equipe_hint=cor_equipe_hint,
    )
    return piloto


class FichaPiloto(QDialog):
    """Ficha detalhada de um piloto"""
    
    def __init__(self, piloto, banco, parent=None, tema: str | None = None):
        super().__init__(parent)
        
        self.piloto = piloto
        self.banco = banco
        tema_inferido = str(tema or "").strip().casefold()
        if not tema_inferido:
            parent_nome = str(parent.objectName() if isinstance(parent, QWidget) else "").strip()
            tema_inferido = "historia" if parent_nome == "tela_historia" else "carreira"
        self._tema_nome = tema_inferido
        self._tema = _tema_ficha(self._tema_nome)
        self._tema_texto_primario = self._tema.get("text_primary", Cores.TEXTO_PRIMARY)
        self._tema_texto_secundario = self._tema.get("text_secondary", Cores.TEXTO_SECONDARY)
        self._tema_texto_muted = self._tema.get("text_muted", Cores.TEXTO_MUTED)
        self._tema_borda = self._tema.get("border", Cores.BORDA)
        self._tema_borda_hover = self._tema.get("border_hover", Cores.BORDA_HOVER)
        self._cor_equipe = self._obter_cor_equipe_piloto()
        self._overlay_backdrop = None
        self._backdrop_blur_label = None
        self._backdrop_base_pixmap = QPixmap()
        self._atualizando_blur = False
        self._blur_effect = None
        self._blur_anim = None
        self._overlay_card = None
        self._btn_fechar_drawer = None
        self._drawer_anim = None
        self._fechamento_animando = False
        self._entrada_animando = False
        self._aceita_clique_fora = False
        self._header_conteudo = None
        self._header_lbl_nome = None
        self._header_lbl_equipe = None
        self._header_lbl_bandeira = None
        self._btn_nav_piloto_up = None
        self._btn_nav_piloto_down = None
        self._pilotos_navegacao = []
        self._indice_piloto_navegacao = 0
        self._inicializar_navegacao_pilotos()
        
        self.setWindowTitle(f"Ficha do Piloto - {piloto['nome']}")
        self.setObjectName("ficha_piloto_dialog")
        self.setMinimumSize(760, 700)
        self.resize(980, 840)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Dialog, True)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(self._estilo_dialogo())
        
        self._build_ui()

    def _ajustar_geometria_overlay(self) -> None:
        parent = self.parentWidget()
        if parent and parent.isVisible():
            topo_esq = parent.mapToGlobal(QPoint(0, 0))
            self.setGeometry(topo_esq.x(), topo_esq.y(), parent.width(), parent.height())
            return

        # Fallback sem parent: mantem tamanho padrao do dialogo.
        if self.width() < 940 or self.height() < 760:
            self.resize(980, 840)

    def _calcular_geometria_card(self) -> QRect:
        margem_x = 24
        margem_y = 18
        largura_disp = max(320, self.width() - margem_x * 2)
        altura_disp = max(260, self.height() - margem_y * 2)

        # Metade exata de tela 1920x1080 = 960px de largura
        largura_pref = min(960, int(self.width() * 0.82))
        altura_pref = min(920, int(self.height() * 0.92))

        largura = min(largura_disp, max(760, largura_pref))
        altura = min(altura_disp, max(700, altura_pref))

        x = max(margem_x, self.width() - margem_x - largura)
        y = max(margem_y, (self.height() - altura) // 2)
        return QRect(x, y, largura, altura)

    def _posicionar_controles_overlay(self) -> None:
        if not isinstance(self._overlay_backdrop, QWidget):
            return
        if not isinstance(self._overlay_card, QFrame):
            return

        self._overlay_backdrop.setGeometry(0, 0, self.width(), self.height())
        self._atualizar_blur_backdrop()
        rect = self._calcular_geometria_card()
        self._overlay_card.setGeometry(rect)
        self._posicionar_elementos_gaveta()

    def _atualizar_blur_backdrop(self, recapturar: bool = False) -> None:
        if not isinstance(self._backdrop_blur_label, QLabel):
            return

        self._backdrop_blur_label.setGeometry(0, 0, self.width(), self.height())

        if recapturar and not self._atualizando_blur:
            parent = self.parentWidget()
            if parent and parent.isVisible():
                self._atualizando_blur = True
                try:
                    captura = parent.grab()
                    if not captura.isNull():
                        self._backdrop_base_pixmap = captura
                finally:
                    self._atualizando_blur = False

        if self._backdrop_base_pixmap.isNull():
            self._backdrop_blur_label.clear()
            return

        pixmap = self._backdrop_base_pixmap.scaled(
            max(2, self.width()),
            max(2, self.height()),
            Qt.IgnoreAspectRatio,
            Qt.SmoothTransformation,
        )
        self._backdrop_blur_label.setPixmap(pixmap)
        self._backdrop_blur_label.lower()

    def _animar_blur_entrada(self) -> None:
        if not isinstance(self._blur_effect, QGraphicsBlurEffect):
            return
        if self._backdrop_base_pixmap.isNull():
            QTimer.singleShot(0, self._capturar_e_animar_blur)
            return

        self._iniciar_animacao_blur()

    def _capturar_e_animar_blur(self) -> None:
        if not self.isVisible() or self._fechamento_animando:
            return
        self._atualizar_blur_backdrop(recapturar=True)
        if self._backdrop_base_pixmap.isNull():
            return
        self._iniciar_animacao_blur()

    def _iniciar_animacao_blur(self) -> None:
        if not isinstance(self._blur_effect, QGraphicsBlurEffect):
            return

        if isinstance(self._blur_anim, QPropertyAnimation):
            self._blur_anim.stop()

        self._blur_effect.setBlurRadius(0.4)
        self._blur_anim = QPropertyAnimation(self._blur_effect, b"blurRadius", self)
        self._blur_anim.setDuration(320)
        self._blur_anim.setStartValue(0.4)
        self._blur_anim.setEndValue(6.0)
        self._blur_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._blur_anim.start()

    def _atualizar_header_info(self) -> None:
        if not isinstance(self._header_lbl_nome, QLabel):
            return
        if not isinstance(self._header_lbl_equipe, QLabel):
            return
        if isinstance(self._header_conteudo, QWidget):
            self._header_conteudo.raise_()

        nome = str(self.piloto.get("nome", "?") or "?").strip() or "?"
        equipe = str(self.piloto.get("equipe_nome", "Sem equipe") or "Sem equipe").strip()
        categoria = obter_nome_categoria(self.piloto.get("categoria_atual", "mazda_rookie"))
        self._header_lbl_nome.setText(nome)
        self._header_lbl_equipe.setText(f"{equipe} | {categoria}")
        self._atualizar_widget_bandeira(self._header_lbl_bandeira)
        self._atualizar_estado_navegacao()

    def _posicionar_botao_drawer(self) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        if not isinstance(self._btn_fechar_drawer, QPushButton):
            return

        rect = self._overlay_card.geometry()
        largura_btn = 28
        altura_btn = max(220, rect.height())
        self._btn_fechar_drawer.setFixedSize(largura_btn, altura_btn)
        x_btn = max(0, rect.x() - largura_btn + 2)
        y_btn = rect.y()
        self._btn_fechar_drawer.move(x_btn, y_btn)
        self._btn_fechar_drawer.raise_()

    def _posicionar_elementos_gaveta(self) -> None:
        self._posicionar_botao_drawer()

    def _animar_entrada_gaveta(self) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        self._entrada_animando = True
        self._aceita_clique_fora = False
        self._animar_blur_entrada()

        rect_final = self._calcular_geometria_card()
        rect_inicio = QRect(
            self.width() + 20,
            rect_final.y(),
            rect_final.width(),
            rect_final.height(),
        )
        self._overlay_card.setGeometry(rect_inicio)
        self._posicionar_botao_drawer()

        if self._drawer_anim is not None:
            self._drawer_anim.stop()

        self._drawer_anim = QPropertyAnimation(self._overlay_card, b"geometry", self)
        self._drawer_anim.setDuration(220)
        self._drawer_anim.setStartValue(rect_inicio)
        self._drawer_anim.setEndValue(rect_final)
        self._drawer_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._drawer_anim.valueChanged.connect(lambda _value: self._posicionar_elementos_gaveta())
        self._drawer_anim.finished.connect(self._finalizar_animacao_entrada)
        self._drawer_anim.start()

    def _finalizar_animacao_entrada(self) -> None:
        self._entrada_animando = False
        self._posicionar_controles_overlay()
        QTimer.singleShot(180, self._habilitar_clique_fora)

    def _habilitar_clique_fora(self) -> None:
        if self.isVisible() and not self._fechamento_animando and not self._entrada_animando:
            self._aceita_clique_fora = True

    def _animar_saida_gaveta(self) -> None:
        if self._fechamento_animando:
            return
        if not isinstance(self._overlay_card, QFrame):
            self.close()
            return

        self._fechamento_animando = True
        self._aceita_clique_fora = False
        rect_atual = self._overlay_card.geometry()
        rect_fim = QRect(
            self.width() + 24,
            rect_atual.y(),
            rect_atual.width(),
            rect_atual.height(),
        )

        if self._drawer_anim is not None:
            self._drawer_anim.stop()

        if isinstance(self._btn_fechar_drawer, QPushButton):
            self._btn_fechar_drawer.setEnabled(False)
        self._atualizar_estado_navegacao()

        self._drawer_anim = QPropertyAnimation(self._overlay_card, b"geometry", self)
        self._drawer_anim.setDuration(180)
        self._drawer_anim.setStartValue(rect_atual)
        self._drawer_anim.setEndValue(rect_fim)
        self._drawer_anim.setEasingCurve(QEasingCurve.InCubic)
        self._drawer_anim.valueChanged.connect(lambda _value: self._posicionar_elementos_gaveta())
        self._drawer_anim.finished.connect(self.accept)
        self._drawer_anim.start()

    def reject(self) -> None:
        self._animar_saida_gaveta()

    def eventFilter(self, obj, event):
        if obj is self._overlay_backdrop and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            if event.button() == Qt.LeftButton and isinstance(self._overlay_card, QFrame):
                clicou_dentro = self._overlay_card.geometry().contains(event.pos())
                if not clicou_dentro:
                    if self._entrada_animando or self._fechamento_animando or not self._aceita_clique_fora:
                        return True
                    self._animar_saida_gaveta()
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._posicionar_controles_overlay()

    def showEvent(self, event) -> None:
        self._ajustar_geometria_overlay()
        super().showEvent(event)
        self._fechamento_animando = False
        self._entrada_animando = True
        self._aceita_clique_fora = False
        if isinstance(self._btn_fechar_drawer, QPushButton):
            self._btn_fechar_drawer.setEnabled(True)
        if isinstance(self._blur_effect, QGraphicsBlurEffect):
            self._blur_effect.setBlurRadius(0.0)
        self._posicionar_controles_overlay()
        self._atualizar_header_info()
        self._notificar_piloto_em_evidencia()
        self._animar_entrada_gaveta()

    def _estilo_dialogo(self) -> str:
        return f"""
            QDialog#ficha_piloto_dialog {{
                background: transparent;
            }}
            QWidget#overlay_backdrop {{
                background-color: {self._tema.get("backdrop", "rgba(8, 12, 18, 70)")};
            }}
            QLabel#overlay_blur_label {{
                background: transparent;
                border: none;
            }}
            QFrame#overlay_card {{
                background-color: {self._tema.get("card_bg", "#0d131a")};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 26)")};
            }}
            QFrame#header_ficha_piloto {{
                background-color: {self._tema.get("header_bg", "#0c141f")};
                border: none;
            }}
            QLabel#header_textura {{
                background: transparent;
                border: none;
            }}
            QLabel#lbl_nome_piloto {{
                color: {self._tema_texto_primario};
                font-weight: 800;
            }}
            QLabel#lbl_equipe_nome {{
                color: {self._tema_texto_secundario};
            }}
            QFrame#header_avatar_placeholder {{
                background-color: {self._tema.get("chip_bg", "#111a24")};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 45)")};
                border-radius: 8px;
            }}
            QFrame#barra_equipe_ficha {{
                background-color: {self._cor_equipe};
                border: none;
            }}
            QFrame#ficha_panel {{
                background-color: {self._tema.get("panel_bg", "#161e29")};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 18)")};
            }}
            QLabel#titulo_secao {{
                color: {self._tema_texto_primario};
                font-size: 11pt;
                font-weight: 700;
                letter-spacing: 0.3px;
            }}
            QLabel#subtitulo_secao {{
                color: {self._tema_texto_secundario};
            }}
            QFrame#bloco_stat {{
                background-color: {self._tema.get("chip_bg", "#101824")};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 20)")};
            }}
            QLabel#lbl_stat_titulo {{
                color: {self._tema_texto_secundario};
            }}
            QLabel#lbl_stat_valor {{
                color: {self._tema_texto_primario};
                font-weight: 900;
            }}
            QLabel#lbl_stat_icone {{
                color: rgba(238, 245, 255, 220);
            }}
            QFrame#timeline_linha_horizontal {{
                background-color: {self._tema.get("timeline", "#2b3647")};
                border: none;
            }}
            QFrame#timeline_linha_vertical {{
                background-color: {self._tema.get("timeline", "#2b3647")};
                border: none;
            }}
            QPushButton#btn_fechar_ficha {{
                background-color: transparent;
                color: {self._tema_texto_primario};
                border: 1px solid {self._tema_borda_hover};
                padding: 6px 16px;
                min-height: 34px;
                font-weight: 600;
            }}
            QPushButton#btn_fechar_ficha:hover {{
                border-color: {self._tema.get("tab_active", Cores.ACCENT_PRIMARY)};
                color: #f5f9ff;
                background-color: {self._tema.get("chip_bg", "#121c29")};
            }}
            QPushButton#btn_fechar_drawer {{
                background-color: {self._tema.get("header_bg", "rgba(9, 15, 22, 214)")};
                color: {self._tema_texto_primario};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 45)")};
                border-right: 1px solid {self._tema_borda_hover};
                border-radius: 0px;
                min-width: 28px;
                max-width: 28px;
                font-size: 12pt;
                font-weight: 900;
                padding: 0px;
            }}
            QPushButton#btn_fechar_drawer:hover {{
                border-color: {self._tema.get("tab_active", Cores.ACCENT_PRIMARY)};
                color: #ffffff;
                background-color: {self._tema.get("drawer_hover_bg", "rgba(28, 44, 67, 230)")};
            }}
            QPushButton#btn_nav_piloto {{
                background-color: transparent;
                color: {self._tema_texto_primario};
                border: 1px solid {self._tema.get("card_border", "rgba(230, 237, 243, 40)")};
                min-width: 22px;
                max-width: 22px;
                min-height: 16px;
                max-height: 16px;
                font-size: 8pt;
                font-weight: 800;
                padding: 0px;
            }}
            QPushButton#btn_nav_piloto:hover {{
                border-color: {self._tema.get("tab_active", Cores.ACCENT_PRIMARY)};
                color: #ffffff;
                background-color: {self._tema.get("nav_hover_bg", "rgba(35, 54, 82, 165)")};
            }}
            QPushButton#btn_nav_piloto:disabled {{
                color: {self._tema_texto_muted};
                border-color: {self._tema_borda};
            }}
        """

    def _obter_cor_equipe_piloto(self) -> str:
        cor_direta = str(
            self.piloto.get("cor_equipe")
            or self.piloto.get("cor_primaria")
            or ""
        ).strip()
        if cor_direta and QColor(cor_direta).isValid():
            return cor_direta

        equipe_id = self.piloto.get("equipe_id")
        equipe_nome = str(self.piloto.get("equipe_nome", "") or "").strip().casefold()
        categoria_piloto = str(self.piloto.get("categoria_atual", "") or "").strip().casefold()

        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue

            cor_eq = str(equipe.get("cor_primaria", "") or "").strip()
            if not cor_eq or not QColor(cor_eq).isValid():
                continue

            if equipe_id and equipe.get("id") == equipe_id:
                return cor_eq

            nome_eq = str(equipe.get("nome", "") or "").strip().casefold()
            categoria_eq = str(equipe.get("categoria", "") or "").strip().casefold()
            if equipe_nome and nome_eq == equipe_nome:
                if not categoria_piloto or not categoria_eq or categoria_piloto == categoria_eq:
                    return cor_eq

        return str(self._tema.get("tab_active", Cores.ACCENT_PRIMARY))

    @staticmethod
    def _chave_piloto_navegacao(piloto: dict) -> tuple[str, str]:
        pid = piloto.get("id")
        if pid not in (None, ""):
            return ("id", str(pid))
        nome = " ".join(str(piloto.get("nome", "") or "").split()).casefold()
        return ("nome", nome)

    def _inicializar_navegacao_pilotos(self) -> None:
        candidatos = self._coletar_pilotos_contexto_parent()
        if not candidatos:
            candidatos = [
                p for p in self.banco.get("pilotos", [])
                if isinstance(p, dict)
            ]
        if not candidatos:
            self._pilotos_navegacao = [self.piloto]
            self._indice_piloto_navegacao = 0
            return

        self._pilotos_navegacao = candidatos
        chave_atual = self._chave_piloto_navegacao(self.piloto)
        indice = next(
            (
                i for i, piloto_ref in enumerate(self._pilotos_navegacao)
                if self._chave_piloto_navegacao(piloto_ref) == chave_atual
            ),
            -1,
        )
        if indice < 0:
            self._pilotos_navegacao.insert(0, self.piloto)
            indice = 0
        self._indice_piloto_navegacao = indice

    def _coletar_pilotos_contexto_parent(self) -> list[dict]:
        parent = self.parentWidget()
        if parent is None:
            return []

        # TelaCarreira: usa a mesma ordem/recorte da tabela principal de pilotos.
        pilotos_tabela = getattr(parent, "pilotos_ordenados", None)
        if isinstance(pilotos_tabela, list):
            candidatos = [p for p in pilotos_tabela if isinstance(p, dict)]
            if candidatos:
                return candidatos

        # TelaHistoria: converte a classificacao exibida em referencias de piloto.
        classificacao = getattr(parent, "_classificacao_temporadas_atual", None)
        resolver = getattr(parent, "_obter_piloto_referencia_temporada", None)
        if isinstance(classificacao, list) and callable(resolver):
            vistos: set[tuple[str, str]] = set()
            candidatos_historia: list[dict] = []
            categoria_nome = ""
            combo_categoria = getattr(parent, "combo_categoria", None)
            if combo_categoria is not None and hasattr(combo_categoria, "currentText"):
                try:
                    categoria_nome = str(combo_categoria.currentText() or "").strip()
                except Exception:
                    categoria_nome = ""
            for entrada in classificacao:
                if not isinstance(entrada, dict):
                    continue
                try:
                    piloto_ref = resolver(entrada)
                except Exception:
                    piloto_ref = None
                payload = preparar_payload_ficha_piloto(
                    piloto_ref if isinstance(piloto_ref, dict) else None,
                    self.banco,
                    entrada_temporada=entrada,
                    categoria_nome=categoria_nome,
                )
                if not isinstance(payload, dict):
                    continue
                chave = self._chave_piloto_navegacao(payload)
                if chave in vistos:
                    continue
                vistos.add(chave)
                candidatos_historia.append(payload)
            if candidatos_historia:
                return candidatos_historia

        return []

    def _atualizar_estado_navegacao(self) -> None:
        habilitado = len(self._pilotos_navegacao) > 1 and not self._fechamento_animando
        if isinstance(self._btn_nav_piloto_up, QPushButton):
            self._btn_nav_piloto_up.setEnabled(habilitado)
        if isinstance(self._btn_nav_piloto_down, QPushButton):
            self._btn_nav_piloto_down.setEnabled(habilitado)

    def _navegar_piloto(self, delta: int) -> None:
        if len(self._pilotos_navegacao) <= 1:
            return
        total = len(self._pilotos_navegacao)
        novo_indice = (self._indice_piloto_navegacao + int(delta)) % total
        if novo_indice == self._indice_piloto_navegacao:
            return

        indice_tab = self.tabs.currentIndex() if isinstance(getattr(self, "tabs", None), QTabWidget) else 0
        self._indice_piloto_navegacao = novo_indice
        self.piloto = self._pilotos_navegacao[novo_indice]
        self._cor_equipe = self._obter_cor_equipe_piloto()
        self.setWindowTitle(f"Ficha do Piloto - {self.piloto.get('nome', '?')}")
        self.setStyleSheet(self._estilo_dialogo())
        self._montar_conteudo_card(indice_tab=indice_tab)
        self._atualizar_header_info()
        self._atualizar_estado_navegacao()
        self._notificar_piloto_em_evidencia()
        self._posicionar_controles_overlay()

    def keyPressEvent(self, event) -> None:
        """Setas do teclado navegam entre pilotos; Escape fecha a ficha."""
        key = event.key()
        if key in (Qt.Key_Right, Qt.Key_Down):
            self._navegar_piloto(+1)
            event.accept()
        elif key in (Qt.Key_Left, Qt.Key_Up):
            self._navegar_piloto(-1)
            event.accept()
        elif key == Qt.Key_Escape:
            self._iniciar_fechamento()
            event.accept()
        else:
            super().keyPressEvent(event)


    def _notificar_piloto_em_evidencia(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return

        atualizado_parent = False
        callback = getattr(parent, "_destacar_piloto_na_tela", None)
        if callable(callback):
            try:
                callback(self.piloto)
                atualizado_parent = True
            except Exception:
                atualizado_parent = False

        if not atualizado_parent:
            atualizado_parent = self._destacar_piloto_parent_fallback(parent)

        if atualizado_parent and hasattr(parent, "repaint"):
            try:
                parent.repaint()
            except Exception:
                pass

        # O fundo do overlay e um snapshot blur da tela pai.
        # Re-captura apos trocar o piloto para refletir a nova linha destacada.
        QTimer.singleShot(0, lambda: self._atualizar_blur_backdrop(recapturar=True))
        QTimer.singleShot(28, lambda: self._atualizar_blur_backdrop(recapturar=True))
        QTimer.singleShot(80, lambda: self._atualizar_blur_backdrop(recapturar=True))

    def _destacar_piloto_parent_fallback(self, parent: QWidget) -> bool:
        return (
            self._destacar_piloto_parent_fallback_carreira(parent)
            or self._destacar_piloto_parent_fallback_historia(parent)
        )

    def _destacar_piloto_parent_fallback_carreira(self, parent: QWidget) -> bool:
        tabela = getattr(parent, "tabela_pilotos", None)
        pilotos = getattr(parent, "pilotos_ordenados", None)
        if tabela is None or not isinstance(pilotos, list):
            return False

        piloto_id = self.piloto.get("id")
        nome = str(self.piloto.get("nome", "") or "").strip().casefold()
        ids_eq = getattr(parent, "_ids_equivalentes", None)

        row = -1
        for i, piloto_ref in enumerate(pilotos):
            if not isinstance(piloto_ref, dict):
                continue
            mesmo_id = False
            if callable(ids_eq):
                try:
                    mesmo_id = bool(ids_eq(piloto_ref.get("id"), piloto_id))
                except Exception:
                    mesmo_id = False
            if not mesmo_id and piloto_id is not None:
                mesmo_id = str(piloto_ref.get("id")) == str(piloto_id)
            mesmo_nome = (
                nome
                and str(piloto_ref.get("nome", "") or "").strip().casefold() == nome
            )
            if mesmo_id or mesmo_nome:
                row = i
                break

        if row < 0:
            return False

        try:
            setattr(parent, "_piloto_id_destacado_tabela", pilotos[row].get("id"))
            if hasattr(parent, "_destacar_somente_piloto_tabela"):
                setattr(parent, "_destacar_somente_piloto_tabela", True)
            setattr(parent, "_equipe_chave_destacada_tabela", "")
            atualizar = getattr(parent, "_atualizar_tabela_pilotos", None)
            if callable(atualizar):
                atualizar()
            item_ref = tabela.item(row, 3) or tabela.item(row, 0)
            if item_ref is not None:
                tabela.scrollToItem(item_ref, QAbstractItemView.PositionAtCenter)
                tabela.setCurrentCell(row, 3)
                tabela.viewport().update()
            return True
        except Exception:
            return False

    def _destacar_piloto_parent_fallback_historia(self, parent: QWidget) -> bool:
        tabela = getattr(parent, "tabela_temporadas", None)
        classificacao = getattr(parent, "_classificacao_temporadas_atual", None)
        if tabela is None or not isinstance(classificacao, list):
            return False

        normalizar_id = getattr(parent, "_normalizar_id", None)
        normalizar_nome = getattr(parent, "_normalizar_nome", None)

        def _norm_id(v):
            if callable(normalizar_id):
                try:
                    return normalizar_id(v)
                except Exception:
                    return str(v or "").strip()
            return str(v or "").strip()

        def _norm_nome(v):
            if callable(normalizar_nome):
                try:
                    return normalizar_nome(v)
                except Exception:
                    return str(v or "").strip().casefold()
            return str(v or "").strip().casefold()

        piloto_id_norm = _norm_id(self.piloto.get("id"))
        nome_norm = _norm_nome(self.piloto.get("nome", ""))
        row = -1
        for i, entrada in enumerate(classificacao):
            if not isinstance(entrada, dict):
                continue
            if (
                piloto_id_norm
                and _norm_id(entrada.get("piloto_id")) == piloto_id_norm
            ) or (
                nome_norm
                and _norm_nome(entrada.get("piloto", "")) == nome_norm
            ):
                row = i
                break

        if row < 0:
            return False

        try:
            entrada = classificacao[row]
            setattr(parent, "_piloto_id_destacado_temporadas", entrada.get("piloto_id"))
            setattr(parent, "_piloto_nome_destacado_temporadas", _norm_nome(entrada.get("piloto", "")))
            if hasattr(parent, "_destacar_somente_piloto_temporadas"):
                setattr(parent, "_destacar_somente_piloto_temporadas", True)
            setattr(parent, "_equipe_chave_destacada_temporadas", "")
            atualizar = getattr(parent, "_atualizar_tabela_temporadas", None)
            if callable(atualizar):
                atualizar()
            item_ref = tabela.item(row, 3) or tabela.item(row, 0)
            if item_ref is not None:
                tabela.scrollToItem(item_ref, QAbstractItemView.PositionAtCenter)
                tabela.setCurrentCell(row, 3)
                tabela.viewport().update()
            return True
        except Exception:
            return False

    def _aplicar_sombra_suave(
        self,
        widget: QWidget,
        blur: int = 18,
        offset_y: int = 2,
        alpha: int = 70,
    ) -> None:
        efeito = QGraphicsDropShadowEffect(widget)
        efeito.setBlurRadius(max(6, int(blur)))
        efeito.setOffset(0, int(offset_y))
        efeito.setColor(QColor(0, 0, 0, max(0, min(255, int(alpha)))))
        widget.setGraphicsEffect(efeito)

    def _icone_por_titulo(self, titulo: str) -> tuple[str, str | None]:
        chave = str(titulo or "").strip().casefold()
        mapa = {
            "titulos": ("taca_ouro_img", Cores.OURO),
            "campeonatos": ("taca_ouro_img", Cores.OURO),
            "vitorias": ("🥇", "#fbbf24"),
            "voltas rapidas": ("⏱", "#c084fc"),
            "voltas rápidas": ("⏱", "#c084fc"),
            "poles": ("◎", "#fbbf24"),
            "podios": ("◆", "#d5d8e0"),
            "pódios": ("◆", "#d5d8e0"),
            "pontos": ("✦", Cores.ACCENT_PRIMARY),
            "corridas": ("🏎️", "#7dd3fc"),
            "incidentes": ("⚠", "#ff6b61"),
            "dnfs": ("✖", "#ff4d4f"),
            "top 10": ("✅", "#22c55e"),
            "media final": ("📉", "#93c5fd"),
            "taxa dnf": ("✖", "#ff4d4f"),
            "inc/corrida": ("⚠", "#ff6b61"),
        }
        return mapa.get(chave, ("•", None))

    def _gerar_pixmap_textura_header(self, largura: int, altura: int) -> QPixmap:
        pixmap = QPixmap(max(2, largura), max(2, altura))
        pixmap.fill(QColor(self._tema.get("header_bg", "#0e1622")))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # Faixas diagonais sutis para simular textura de fibra.
        pen_textura = QPen(QColor(255, 255, 255, 10), 1)
        painter.setPen(pen_textura)
        passo = 14
        for x in range(-altura, largura + altura, passo):
            painter.drawLine(x, 0, x + altura, altura)

        pen_textura_2 = QPen(QColor(0, 0, 0, 26), 1)
        painter.setPen(pen_textura_2)
        for x in range(-altura + 6, largura + altura, passo):
            painter.drawLine(x, 0, x + altura, altura)

        painter.end()
        return pixmap

    def _gerar_pixmap_avatar(self, largura: int = 78, altura: int = 96) -> QPixmap:
        pixmap = QPixmap(max(2, largura), max(2, altura))
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._tema.get("chip_bg", "#111a27")))
        painter.drawRoundedRect(0, 0, largura, altura, 8, 8)

        painter.setBrush(QColor(self._cor_equipe))
        painter.drawRect(0, 0, largura, 4)

        # Silhueta generica (cabeca e ombros).
        painter.setBrush(QColor(self._tema.get("border_hover", "#4f637e")))
        raio_cabeca = max(12, largura // 6)
        centro_x = largura // 2
        centro_y = altura // 3
        painter.drawEllipse(
            QPoint(centro_x, centro_y),
            raio_cabeca,
            raio_cabeca,
        )
        painter.drawRoundedRect(
            max(8, largura // 7),
            int(altura * 0.48),
            largura - max(16, largura // 3),
            int(altura * 0.38),
            10,
            10,
        )

        painter.end()
        return pixmap

    def _gerar_pixmap_logo_equipe(self, tamanho: int = 28) -> QPixmap:
        tamanho_int = max(20, int(tamanho))
        pixmap = QPixmap(tamanho_int, tamanho_int)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(Qt.NoPen)

        cor_principal = QColor(self._cor_equipe)
        cor_secundaria = QColor(self._cor_equipe).lighter(145)
        contorno = QColor(255, 255, 255, 46)

        pontos = [
            QPoint(tamanho_int // 2, 2),
            QPoint(tamanho_int - 3, tamanho_int // 4),
            QPoint(tamanho_int - 6, tamanho_int - 6),
            QPoint(tamanho_int // 2, tamanho_int - 2),
            QPoint(6, tamanho_int - 6),
            QPoint(3, tamanho_int // 4),
        ]

        painter.setBrush(cor_principal)
        painter.drawPolygon(pontos)
        painter.setPen(QPen(contorno, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(pontos)

        painter.setPen(Qt.NoPen)
        painter.setBrush(cor_secundaria)
        painter.drawEllipse(
            tamanho_int // 2 - 5,
            tamanho_int // 2 - 5,
            10,
            10,
        )
        painter.end()
        return pixmap

    def _obter_pixmap_bandeira_quadriculada_branca(
        self,
        largura: int = 20,
        altura: int = 20,
    ) -> QPixmap:
        pixmap = QPixmap(max(12, int(largura)), max(12, int(altura)))
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pole_color = QColor("#f1f5f9")
        painter.setPen(QPen(pole_color, 2))
        painter.drawLine(4, pixmap.height() - 3, 4, 4)

        flag_x = 6
        flag_y = 4
        flag_w = max(8, pixmap.width() - 9)
        flag_h = max(8, int(pixmap.height() * 0.62))
        cols = 3
        rows = 3
        cell_w = max(2, flag_w // cols)
        cell_h = max(2, flag_h // rows)

        for r in range(rows):
            for c in range(cols):
                branco = (r + c) % 2 == 0
                cor = QColor("#f8fbff") if branco else QColor("#cfd8e3")
                painter.fillRect(
                    flag_x + c * cell_w,
                    flag_y + r * cell_h,
                    cell_w + (1 if c == cols - 1 else 0),
                    cell_h + (1 if r == rows - 1 else 0),
                    cor,
                )

        painter.setPen(QPen(QColor(248, 251, 255, 200), 1))
        painter.drawRect(flag_x, flag_y, flag_w, flag_h)
        painter.end()
        return pixmap

    def _obter_pixmap_taca_ouro(self, largura: int = 22, altura: int = 22) -> QPixmap:
        caminho = Path(__file__).resolve().parent / "widgets" / "ouro.png"
        cache = getattr(self, "_pixmap_taca_ouro_base", None)
        if isinstance(cache, QPixmap) and not cache.isNull():
            base = cache
        else:
            imagem = QImage(str(caminho))
            if imagem.isNull():
                return QPixmap()

            min_x = imagem.width()
            min_y = imagem.height()
            max_x = -1
            max_y = -1

            for y in range(imagem.height()):
                for x in range(imagem.width()):
                    if imagem.pixelColor(x, y).alpha() > 0:
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)
                        max_x = max(max_x, x)
                        max_y = max(max_y, y)

            if max_x < 0 or max_y < 0:
                return QPixmap()

            imagem_recortada = imagem.copy(
                min_x,
                min_y,
                max_x - min_x + 1,
                max_y - min_y + 1,
            )
            margem = 2
            imagem_expandida = QImage(
                imagem_recortada.width() + margem * 2,
                imagem_recortada.height() + margem * 2,
                QImage.Format_ARGB32,
            )
            imagem_expandida.fill(Qt.transparent)
            painter = QPainter(imagem_expandida)
            painter.drawImage(margem, margem, imagem_recortada)
            painter.end()

            base = QPixmap.fromImage(imagem_expandida)
            setattr(self, "_pixmap_taca_ouro_base", base)

        if base.isNull():
            return QPixmap()
        return base.scaled(
            max(14, int(largura)),
            max(14, int(altura)),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    def _atualizar_widget_bandeira(self, lbl: QLabel | None) -> None:
        if not isinstance(lbl, QLabel):
            return

        nacionalidade = str(self.piloto.get("nacionalidade", "") or "")
        codigo = obter_codigo_bandeira(nacionalidade, fallback="")
        lbl.clear()
        lbl.setFixedSize(30, 20)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background: transparent; border: none;")
        lbl.setToolTip(nacionalidade.strip() or "Nacionalidade")

        if codigo:
            caminho = obter_pasta_bandeiras_absoluta() / f"{codigo}.png"
            pixmap = QPixmap(str(caminho))
            if not pixmap.isNull():
                lbl.setPixmap(
                    pixmap.scaled(28, 18, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                return

        lbl.setFont(QFont("Segoe UI Emoji", 12))
        lbl.setText(obter_emoji_bandeira(nacionalidade, fallback="\U0001F3F3\ufe0f"))
        lbl.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
    
    def _criar_widget_bandeira(self) -> QLabel:
        lbl = QLabel()
        lbl.setFixedSize(30, 20)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("background: transparent; border: none;")
        self._atualizar_widget_bandeira(lbl)
        return lbl

    def _criar_painel_secao(self, titulo: str, subtitulo: str | None = None):
        painel = QFrame()
        painel.setObjectName("ficha_panel")

        layout = QVBoxLayout(painel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        lbl_titulo = QLabel(str(titulo))
        lbl_titulo.setObjectName("titulo_secao")
        lbl_titulo.setFont(Fontes.titulo_pequeno())
        layout.addWidget(lbl_titulo)

        if subtitulo:
            lbl_subtitulo = QLabel(str(subtitulo))
            lbl_subtitulo.setObjectName("subtitulo_secao")
            lbl_subtitulo.setFont(Fontes.texto_pequeno())
            layout.addWidget(lbl_subtitulo)

        separador = QFrame()
        separador.setFixedHeight(1)
        separador.setStyleSheet(f"background-color: {Cores.BORDA}; border: none;")
        layout.addWidget(separador)

        self._aplicar_sombra_suave(painel, blur=16, offset_y=1, alpha=65)
        return painel, layout

    def _criar_linha_atributo(
        self,
        titulo: str,
        valor: int,
        cor: str,
        maximo: int = 100,
    ) -> QWidget:
        linha = QWidget()
        layout = QHBoxLayout(linha)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(Fontes.texto_pequeno())
        lbl_titulo.setStyleSheet(f"color: {self._tema_texto_secundario};")
        lbl_titulo.setFixedWidth(88)
        layout.addWidget(lbl_titulo)

        barra = QProgressBar()
        max_int = max(1, int(maximo))
        valor_int = max(0, min(max_int, int(valor)))
        barra.setRange(0, max_int)
        barra.setValue(valor_int)
        barra.setTextVisible(False)
        barra.setFixedHeight(11)
        barra.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {self._tema.get("plot_bg", "#0f1825")};
                border: none;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background-color: {cor};
                border-radius: 5px;
            }}
            """
        )
        layout.addWidget(barra, 1)

        lbl_valor = QLabel(f"{valor_int} / {max_int}")
        lbl_valor.setFont(Fontes.texto_pequeno())
        lbl_valor.setStyleSheet(f"color: {self._tema_texto_primario};")
        lbl_valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_valor.setFixedWidth(68)
        layout.addWidget(lbl_valor)

        return linha

    def _criar_bloco_stat(
        self,
        titulo: str,
        valor: Any,
        cor_valor: str | None = None,
        icone: str | None = None,
        cor_icone: str | None = None,
    ) -> QWidget:
        bloco = QFrame()
        bloco.setObjectName("bloco_stat")

        layout = QVBoxLayout(bloco)
        layout.setContentsMargins(10, 7, 10, 8)
        layout.setSpacing(3)

        icone_texto, icone_cor_padrao = self._icone_por_titulo(titulo)
        icone_final = str(icone or icone_texto)
        cor_icone_final = cor_icone or icone_cor_padrao

        lbl_icone = QLabel()
        lbl_icone.setObjectName("lbl_stat_icone")
        usa_emoji_font = any(ord(ch) >= 0x1F000 for ch in icone_final)
        if usa_emoji_font:
            tamanho_emoji = 16 if icone_final in {"🥇", "🥈", "🥉"} else 14
            fonte_icone = QFont("Segoe UI Emoji", tamanho_emoji)
            fonte_icone.setBold(False)
        else:
            fonte_icone = QFont(Fontes.FAMILIA, 12)
            fonte_icone.setBold(True)
        lbl_icone.setFont(fonte_icone)
        lbl_icone.setAlignment(Qt.AlignCenter)
        lbl_icone.setMinimumHeight(30)
        if icone_final == "taca_ouro_img":
            pixmap_taca = self._obter_pixmap_taca_ouro(26, 26)
            if not pixmap_taca.isNull():
                lbl_icone.setPixmap(pixmap_taca)
            else:
                lbl_icone.setText("🏆")
                if cor_icone_final:
                    lbl_icone.setStyleSheet(f"color: {cor_icone_final};")
        elif icone_final == "flag_quadriculada_branca_img":
            pixmap_bandeira = self._obter_pixmap_bandeira_quadriculada_branca()
            if not pixmap_bandeira.isNull():
                lbl_icone.setPixmap(pixmap_bandeira)
            else:
                lbl_icone.setText("⚑")
                lbl_icone.setStyleSheet("color: #f8fbff;")
        else:
            lbl_icone.setText(icone_final)
            if cor_icone_final:
                lbl_icone.setStyleSheet(f"color: {cor_icone_final};")
        opacidade_icone = QGraphicsOpacityEffect(lbl_icone)
        opacidade_icone.setOpacity(
            0.95 if icone_final in {"taca_ouro_img", "flag_quadriculada_branca_img"} else 0.90
        )
        lbl_icone.setGraphicsEffect(opacidade_icone)
        layout.addWidget(lbl_icone)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setObjectName("lbl_stat_valor")
        fonte_valor = QFont(Fontes.numero_medio())
        fonte_valor.setBold(True)
        fonte_valor.setWeight(QFont.Weight.Black)
        lbl_valor.setFont(fonte_valor)
        lbl_valor.setAlignment(Qt.AlignCenter)
        if cor_valor:
            lbl_valor.setStyleSheet(f"color: {cor_valor};")
        layout.addWidget(lbl_valor)

        lbl_titulo = QLabel(str(titulo))
        lbl_titulo.setObjectName("lbl_stat_titulo")
        lbl_titulo.setFont(Fontes.texto_pequeno())
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_titulo)

        self._aplicar_sombra_suave(bloco, blur=12, offset_y=1, alpha=55)
        return bloco

    def _criar_grade_stats(
        self,
        stats: list[tuple[str, Any, str | None] | dict[str, Any]],
        colunas: int = 4,
    ) -> QWidget:
        grade_widget = QWidget()
        grade = QGridLayout(grade_widget)
        grade.setContentsMargins(0, 0, 0, 0)
        grade.setHorizontalSpacing(8)
        grade.setVerticalSpacing(8)

        for indice, stat in enumerate(stats):
            if isinstance(stat, dict):
                titulo = stat.get("titulo", "-")
                valor = stat.get("valor", "-")
                cor = stat.get("cor")
                icone = stat.get("icone")
                cor_icone = stat.get("cor_icone")
            else:
                titulo, valor, cor = stat
                icone = None
                cor_icone = None

            linha = indice // colunas
            coluna = indice % colunas
            grade.addWidget(
                self._criar_bloco_stat(titulo, valor, cor, icone=icone, cor_icone=cor_icone),
                linha,
                coluna,
            )

        for coluna in range(colunas):
            grade.setColumnStretch(coluna, 1)

        return grade_widget

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._overlay_backdrop = QWidget(self)
        self._overlay_backdrop.setObjectName("overlay_backdrop")
        self._overlay_backdrop.installEventFilter(self)
        root_layout.addWidget(self._overlay_backdrop)

        self._backdrop_blur_label = QLabel(self._overlay_backdrop)
        self._backdrop_blur_label.setObjectName("overlay_blur_label")
        self._backdrop_blur_label.setScaledContents(True)
        self._backdrop_blur_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._blur_effect = QGraphicsBlurEffect(self._backdrop_blur_label)
        self._blur_effect.setBlurRadius(0.0)
        self._backdrop_blur_label.setGraphicsEffect(self._blur_effect)
        self._backdrop_blur_label.lower()

        self._overlay_card = QFrame(self._overlay_backdrop)
        self._overlay_card.setObjectName("overlay_card")
        self._overlay_card.setMinimumWidth(760)
        self._overlay_card.setMinimumHeight(700)

        card_layout = QVBoxLayout(self._overlay_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        self._montar_conteudo_card()

        self._btn_fechar_drawer = QPushButton("➜", self._overlay_backdrop)
        self._btn_fechar_drawer.setObjectName("btn_fechar_drawer")
        self._btn_fechar_drawer.setCursor(Qt.PointingHandCursor)
        self._btn_fechar_drawer.clicked.connect(self._animar_saida_gaveta)
        self._btn_fechar_drawer.raise_()
        self._posicionar_controles_overlay()

    def _montar_conteudo_card(self, indice_tab: int = 0) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        layout = self._overlay_card.layout()
        if not isinstance(layout, QVBoxLayout):
            return

        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        header = self._build_header()
        layout.addWidget(header)

        barra_equipe = QFrame()
        barra_equipe.setObjectName("barra_equipe_ficha")
        barra_equipe.setFixedHeight(3)
        layout.addWidget(barra_equipe)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            _estilo_tabs_ficha(
                cor_destaque=self._tema.get("tab_active", "#38d4ff"),
                cor_inativa=self._tema_texto_secundario,
                cor_hover=self._tema_texto_primario,
            )
        )
        self.tabs.addTab(self._build_tab_info(), "Informações")
        self.tabs.addTab(self._build_tab_temporadas(), "Temporadas")
        self.tabs.addTab(self._build_tab_estatisticas(), "Estatísticas")
        self.tabs.setCurrentIndex(max(0, min(indice_tab, self.tabs.count() - 1)))
        layout.addWidget(self.tabs, 1)
    
    def _build_header(self):
        """Header com textura e dados do piloto."""
        header = QFrame()
        header.setObjectName("header_ficha_piloto")
        header.setFixedHeight(164)

        layout_stack = QStackedLayout(header)
        layout_stack.setStackingMode(QStackedLayout.StackAll)
        layout_stack.setContentsMargins(0, 0, 0, 0)

        textura = QLabel()
        textura.setObjectName("header_textura")
        textura.setPixmap(self._gerar_pixmap_textura_header(1500, 230))
        textura.setScaledContents(True)
        layout_stack.addWidget(textura)

        nome = self.piloto.get("nome", "?")
        equipe = self.piloto.get("equipe_nome", "Sem equipe") or "Sem equipe"
        categoria = obter_nome_categoria(self.piloto.get("categoria_atual", "mazda_rookie"))

        conteudo = QWidget()
        self._header_conteudo = conteudo
        conteudo.setStyleSheet("background: transparent; border: none;")
        conteudo_layout = QHBoxLayout(conteudo)
        conteudo_layout.setContentsMargins(20, 20, 20, 20)
        conteudo_layout.setSpacing(16)
        conteudo_layout.setAlignment(Qt.AlignVCenter)

        avatar_placeholder = QFrame()
        avatar_placeholder.setObjectName("header_avatar_placeholder")
        avatar_placeholder.setFixedSize(80, 80)
        conteudo_layout.addWidget(avatar_placeholder, 0, Qt.AlignVCenter)

        texto_layout = QVBoxLayout()
        texto_layout.setContentsMargins(0, 0, 0, 0)
        texto_layout.setSpacing(4)
        texto_layout.setAlignment(Qt.AlignVCenter)

        linha_nome = QHBoxLayout()
        linha_nome.setContentsMargins(0, 0, 0, 0)
        linha_nome.setSpacing(10)

        nav_container = QWidget()
        nav_container.setFixedWidth(24)
        flag_container = QWidget()
        flag_container.setFixedWidth(32)
        self._header_lbl_bandeira = self._criar_widget_bandeira()
        flag_layout = QHBoxLayout(flag_container)
        flag_layout.setContentsMargins(0, 0, 0, 0)
        flag_layout.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        flag_layout.addWidget(self._header_lbl_bandeira)

        lbl_nome = QLabel(str(nome))
        lbl_nome.setObjectName("lbl_nome_piloto")
        fonte_nome = QFont(Fontes.FAMILIA, 24)
        fonte_nome.setBold(True)
        lbl_nome.setFont(fonte_nome)
        lbl_nome.setStyleSheet(f"color: {self._tema_texto_primario};")
        self._header_lbl_nome = lbl_nome

        nav_layout = QVBoxLayout()
        nav_layout.setAlignment(Qt.AlignVCenter)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(2)
        self._btn_nav_piloto_up = QPushButton("▲")
        self._btn_nav_piloto_up.setObjectName("btn_nav_piloto")
        self._btn_nav_piloto_up.setCursor(Qt.PointingHandCursor)
        self._btn_nav_piloto_up.clicked.connect(lambda: self._navegar_piloto(-1))
        nav_layout.addWidget(self._btn_nav_piloto_up)

        self._btn_nav_piloto_down = QPushButton("▼")
        self._btn_nav_piloto_down.setObjectName("btn_nav_piloto")
        self._btn_nav_piloto_down.setCursor(Qt.PointingHandCursor)
        self._btn_nav_piloto_down.clicked.connect(lambda: self._navegar_piloto(1))
        nav_layout.addWidget(self._btn_nav_piloto_down)
        nav_container.setLayout(nav_layout)
        linha_nome.addWidget(nav_container, 0, Qt.AlignVCenter)
        linha_nome.addWidget(flag_container, 0, Qt.AlignVCenter)
        linha_nome.addWidget(lbl_nome, 0, Qt.AlignVCenter)
        linha_nome.addStretch(1)
        texto_layout.addLayout(linha_nome)

        linha_info = QHBoxLayout()
        linha_info.setContentsMargins(0, 0, 0, 0)
        linha_info.setSpacing(6)

        lbl_equipe = QLabel(f"{equipe} | {categoria}")
        lbl_equipe.setObjectName("lbl_equipe_nome")
        lbl_equipe.setFont(Fontes.texto_normal())
        lbl_equipe.setStyleSheet(f"color: {self._tema_texto_secundario};")
        self._header_lbl_equipe = lbl_equipe
        linha_info.addWidget(lbl_equipe, 0, Qt.AlignVCenter)
        linha_info.addStretch(1)
        texto_layout.addLayout(linha_info)

        conteudo_layout.addLayout(texto_layout, 1)
        layout_stack.addWidget(conteudo)
        layout_stack.setCurrentWidget(conteudo)
        conteudo.raise_()
        self._atualizar_header_info()

        return header
    
    def _build_tab_info(self):
        """Tab com informações pessoais e atributos qualitativos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # --- Atributos (sem números, só rótulos qualitativos) ---
        painel_attr, painel_attr_layout = self._criar_painel_secao("Atributos")

        skill = self._as_int(self.piloto.get("skill"), 50)
        aggression = self._as_int(float(self.piloto.get("aggression", 0.5)) * 100, 50)
        potencial = self._as_int(self.piloto.get("potencial"), 50)
        corridas = self._as_int(self.piloto.get("corridas_carreira"), 0)
        dnfs = self._as_int(self.piloto.get("dnfs_carreira"), 0)
        taxa_dnf = dnfs / corridas if corridas > 0 else 0.0

        rot_skill, cor_skill = self._rotulo_skill(skill)
        rot_agg, cor_agg = self._rotulo_agressividade(aggression)
        rot_teto, cor_teto, valor_teto = self._rotulo_teto_estimado(potencial)
        rot_consist, cor_consist = self._rotulo_consistencia(taxa_dnf)

        painel_attr_layout.addWidget(
            self._criar_linha_atributo_qualitativo("Habilidade", skill, rot_skill, cor_skill, cor_skill)
        )
        painel_attr_layout.addWidget(
            self._criar_linha_atributo_qualitativo("Agressividade", aggression, rot_agg, cor_agg, cor_agg)
        )
        painel_attr_layout.addWidget(
            self._criar_linha_atributo_qualitativo(
                "Teto estimado",
                valor_teto,
                rot_teto,
                cor_teto,
                cor_teto,
            )
        )
        painel_attr_layout.addWidget(
            self._criar_linha_atributo_qualitativo(
                "Consistência",
                max(0, int((1.0 - taxa_dnf) * 100)),
                rot_consist,
                cor_consist,
                cor_consist,
            )
        )
        layout.addWidget(painel_attr)

        # --- Carreira completa (com ranking histórico global) ---
        painel_carreira, painel_carreira_layout = self._criar_painel_secao("Carreira completa")
        titulos = self._as_int(self.piloto.get("titulos"), 0)
        vitorias = self._as_int(self.piloto.get("vitorias_carreira"), 0)
        podios = self._as_int(self.piloto.get("podios_carreira"), 0)
        poles = self._as_int(self.piloto.get("poles_carreira"), 0)
        voltas_rap = self._as_int(
            self.piloto.get("voltas_rapidas_carreira", self.piloto.get("poles_carreira", 0)), 0
        )
        corridas_car = self._as_int(self.piloto.get("corridas_carreira"), 0)
        pontos_car = self._as_int(self.piloto.get("pontos_carreira"), 0)
        incidentes_car = self._as_int(self.piloto.get("incidentes_carreira"), 0)

        painel_carreira_layout.addWidget(self._criar_piramide_carreira(corridas_base=corridas_car))
        layout.addWidget(painel_carreira)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll
    
    def _calcular_recordes_pessoais(self) -> dict[str, dict[str, int]]:
        """
        Retorna {campo: {"max": valor, "min": valor}} para cada métrica,
        calculado sobre todas as temporadas do piloto (histórico + atual).
        Apenas temporadas com pelo menos uma corrida são incluídas no mínimo.
        """
        campos = ["pontos", "vitorias", "podios", "poles", "voltas_rapidas", "dnfs"]
        maximos: dict[str, int] = {c: 0 for c in campos}
        # Para mínimos ignoramos 0 (temporada sem dados)
        minimos: dict[str, int | None] = {c: None for c in campos}
        n_temporadas = 0

        def _atualizar(temp_dict: dict, mapa_campos: dict[str, str] | None = None):
            nonlocal n_temporadas
            n_temporadas += 1
            for campo in campos:
                chave = mapa_campos[campo] if mapa_campos else campo
                v = self._as_int(temp_dict.get(chave), 0)
                if v > maximos[campo]:
                    maximos[campo] = v
                if v >= 0:  # inclui 0 para mínimos só se houver mais de 1 temporada depois
                    if minimos[campo] is None or v < minimos[campo]:  # type: ignore[operator]
                        minimos[campo] = v

        for temp in self.piloto.get("historico_temporadas", []):
            if isinstance(temp, dict):
                _atualizar(temp)

        mapa_atual = {
            "pontos": "pontos_temporada",
            "vitorias": "vitorias_temporada",
            "podios": "podios_temporada",
            "poles": "poles_temporada",
            "voltas_rapidas": "voltas_rapidas_temporada",
            "dnfs": "dnfs_temporada",
        }
        _atualizar(self.piloto, mapa_atual)

        resultado: dict[str, dict[str, int]] = {}
        for campo in campos:
            mn = minimos[campo] if minimos[campo] is not None else 0
            mx = maximos[campo]
            resultado[campo] = {"max": mx, "min": int(mn)}
        return resultado

    def _build_tab_temporadas(self):
        """Aba Temporadas — temporada atual + histórico com recordes pessoais."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        recordes = self._calcular_recordes_pessoais()
        historico = self.piloto.get("historico_temporadas", [])
        n_temp_total = len(historico) + 1  # +1 temporada atual
        ano_atual = self._as_int(self.banco.get("ano_atual"), 2024)

        # --- Temporada atual ---
        painel_atual, painel_atual_layout = self._criar_painel_secao(
            f"Temporada {ano_atual}  (Em andamento)"
        )
        stats_atual = [
            ("pontos", "Pontos", self._as_int(self.piloto.get("pontos_temporada"), 0), Cores.ACCENT_PRIMARY, "✦"),
            ("vitorias", "Vitórias", self._as_int(self.piloto.get("vitorias_temporada"), 0), Cores.OURO, "🥇"),
            ("podios", "Pódios", self._as_int(self.piloto.get("podios_temporada"), 0), Cores.PRATA, "🥈"),
            ("poles", "Poles", self._as_int(self.piloto.get("poles_temporada"), 0), None, "◎"),
            ("voltas_rapidas", "V. Rápidas", self._as_int(self.piloto.get("voltas_rapidas_temporada"), 0), None, "⧗"),
            ("dnfs", "DNFs", self._as_int(self.piloto.get("dnfs_temporada"), 0), Cores.VERMELHO, "🛑"),
        ]
        grade_atual = QWidget()
        grade_layout = QGridLayout(grade_atual)
        grade_layout.setContentsMargins(0, 0, 0, 0)
        grade_layout.setHorizontalSpacing(8)
        grade_layout.setVerticalSpacing(8)
        for idx, (campo, titulo, valor, cor, icone) in enumerate(stats_atual):
            bloco = self._criar_bloco_stat(titulo, valor, cor, icone=icone)
            grade_layout.addWidget(bloco, idx // 3, idx % 3)
        for c in range(3):
            grade_layout.setColumnStretch(c, 1)
        painel_atual_layout.addWidget(grade_atual)

        resultados_atuais = self.piloto.get("resultados_temporada", [])
        painel_atual_layout.addWidget(self._criar_timeline_resultados_horizontal(list(resultados_atuais)))
        layout.addWidget(painel_atual)

        # --- Histórico de temporadas ---
        if historico:
            historico_ord = sorted(historico, key=lambda x: x.get("ano", 0), reverse=True)
            titulo_hist = "Histórico de Temporadas"
            painel_hist, painel_hist_layout = self._criar_painel_secao(titulo_hist)

            for temp in historico_ord:
                ano = self._as_int(temp.get("ano"), 0)
                cat_raw = temp.get("categoria", "?")
                cat_nome = self._nome_categoria(cat_raw)
                equipe_nome = str(temp.get("equipe_nome", "-") or "-").strip()
                posicao = temp.get("posicao_final", "?")
                pontos = self._as_int(temp.get("pontos"), 0)
                vitorias = self._as_int(temp.get("vitorias"), 0)
                podios = self._as_int(temp.get("podios"), 0)
                poles = self._as_int(temp.get("poles"), 0)
                vr = self._as_int(temp.get("voltas_rapidas"), 0)
                dnfs_t = self._as_int(temp.get("dnfs"), 0)
                cor_pos = self._cor_por_posicao_historico(posicao)

                card_temp = QFrame()
                card_temp.setObjectName("ficha_panel")
                card_temp_layout = QVBoxLayout(card_temp)
                card_temp_layout.setContentsMargins(12, 10, 12, 10)
                card_temp_layout.setSpacing(6)

                # ---------- Linha topo (clicável para expandir) ----------
                topo_widget = QWidget()
                topo_widget.setCursor(Qt.PointingHandCursor)
                topo = QHBoxLayout(topo_widget)
                topo.setContentsMargins(0, 0, 0, 0)
                topo.setSpacing(8)

                lbl_ano = QLabel(str(ano))
                fonte_ano = QFont(Fontes.FAMILIA, 11)
                fonte_ano.setBold(True)
                lbl_ano.setFont(fonte_ano)
                lbl_ano.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
                topo.addWidget(lbl_ano)

                sep = QLabel("·")
                sep.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
                topo.addWidget(sep)

                lbl_cat = QLabel(cat_nome)
                lbl_cat.setFont(Fontes.texto_pequeno())
                lbl_cat.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
                topo.addWidget(lbl_cat)

                sep2 = QLabel("·")
                sep2.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
                topo.addWidget(sep2)

                lbl_equipe = QLabel(equipe_nome)
                lbl_equipe.setFont(Fontes.texto_pequeno())
                lbl_equipe.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
                topo.addWidget(lbl_equipe)
                topo.addStretch(1)

                # Seta de expansão
                lbl_seta = QLabel("▼")
                lbl_seta.setFont(QFont(Fontes.FAMILIA, 7))
                lbl_seta.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
                topo.addWidget(lbl_seta)

                pos_int = self._as_int(posicao, 999)
                badge_pos = QLabel(f"P{pos_int}" if pos_int < 999 else "?")
                badge_pos.setAlignment(Qt.AlignCenter)
                badge_pos.setFixedSize(40, 40)
                badge_pos.setStyleSheet(
                    f"""
                    QLabel {{
                        background-color: {self._tema.get("chip_bg", "#101824")};
                        color: {cor_pos};
                        border: 1px solid rgba(230,237,243,38);
                        border-radius: 20px;
                        font-weight: 800;
                    }}
                    """
                )
                topo.addWidget(badge_pos)
                card_temp_layout.addWidget(topo_widget)

                # ---------- Stats compactos (sempre visíveis) ----------
                stats_linha = QHBoxLayout()
                stats_linha.setSpacing(12)

                def _stat_item(titulo_s, valor_s, campo_r, icone_s=""):
                    """Mini widget stat com badges de melhor (⭐) e pior (📉) temporada."""
                    w = QWidget()
                    wl = QVBoxLayout(w)
                    wl.setContentsMargins(0, 0, 0, 0)
                    wl.setSpacing(1)
                    rec = recordes.get(campo_r, {"max": 0, "min": 0})
                    rec_max = rec.get("max", 0) if isinstance(rec, dict) else 0
                    rec_min = rec.get("min", 0) if isinstance(rec, dict) else 0
                    is_melhor = bool(campo_r and valor_s > 0 and valor_s >= rec_max and rec_max > 0 and n_temp_total > 1)
                    # Pior: menor valor; para DNFs pior = maior valor
                    if campo_r == "dnfs":
                        is_pior = bool(campo_r and valor_s > 0 and valor_s >= rec_max and n_temp_total > 1)
                        is_melhor = False  # DNFs: não há badge de melhor
                    else:
                        is_pior = bool(campo_r and rec_min is not None and rec_min >= 0
                                       and valor_s == rec_min and rec_max > rec_min and n_temp_total > 1)

                    linha_h = QHBoxLayout()
                    linha_h.setSpacing(3)

                    if icone_s:
                        lbl_ico = QLabel(icone_s)
                        lbl_ico.setFont(QFont("Segoe UI Emoji", 8))
                        linha_h.addWidget(lbl_ico)

                    lbl_v = QLabel(str(valor_s))
                    fonte_v = QFont(Fontes.FAMILIA, 11)
                    fonte_v.setBold(True)
                    lbl_v.setFont(fonte_v)
                    cor_v = Cores.OURO if is_melhor else (Cores.VERMELHO if is_pior and campo_r != "dnfs" else Cores.TEXTO_PRIMARY)
                    lbl_v.setStyleSheet(f"color: {cor_v};")
                    linha_h.addWidget(lbl_v)

                    if is_melhor:
                        lbl_rec = QLabel("⭐")
                        lbl_rec.setFont(QFont("Segoe UI Emoji", 8))
                        lbl_rec.setToolTip("Melhor temporada pessoal")
                        linha_h.addWidget(lbl_rec)
                    elif is_pior and campo_r not in ("", "dnfs"):
                        lbl_rec = QLabel("📉")
                        lbl_rec.setFont(QFont("Segoe UI Emoji", 8))
                        lbl_rec.setToolTip("Pior temporada pessoal")
                        linha_h.addWidget(lbl_rec)

                    wl.addLayout(linha_h)
                    lbl_t = QLabel(titulo_s)
                    lbl_t.setFont(Fontes.texto_pequeno())
                    lbl_t.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
                    wl.addWidget(lbl_t)
                    return w

                _sep = lambda: self._criar_sep_vertical()

                stats_linha.addWidget(_stat_item("Pontos", pontos, "pontos", "✦"))
                stats_linha.addWidget(_sep())
                stats_linha.addWidget(_stat_item("Vitórias", vitorias, "vitorias", "🥇"))
                stats_linha.addWidget(_sep())
                stats_linha.addWidget(_stat_item("Pódios", podios, "podios", "🥈"))
                stats_linha.addWidget(_sep())
                stats_linha.addWidget(_stat_item("Poles", poles, "poles", "◎"))
                stats_linha.addWidget(_sep())
                stats_linha.addWidget(_stat_item("VR", vr, "voltas_rapidas", "⧗"))
                stats_linha.addWidget(_sep())
                stats_linha.addWidget(_stat_item("DNFs", dnfs_t, "dnfs", "🛑"))
                stats_linha.addStretch(1)
                card_temp_layout.addLayout(stats_linha)

                # ---------- Detalhes expandidos (ocultos por padrão) ----------
                detalhes_widget = QWidget()
                detalhes_widget.setVisible(False)
                detalhes_layout = QVBoxLayout(detalhes_widget)
                detalhes_layout.setContentsMargins(0, 8, 0, 0)
                detalhes_layout.setSpacing(6)

                # Grade de stats ampliada (mesma estrutura da temporada atual)
                stats_exp = [
                    ("Pontos", pontos, Cores.ACCENT_PRIMARY, "✦"),
                    ("Vitórias", vitorias, Cores.OURO if vitorias > 0 else None, "🥇"),
                    ("Pódios", podios, Cores.PRATA if podios > 0 else None, "🥈"),
                    ("Poles", poles, None, "◎"),
                    ("V. Rápidas", vr, None, "⧗"),
                    ("DNFs", dnfs_t, Cores.VERMELHO if dnfs_t > 0 else None, "🛑"),
                ]
                grade_exp = QWidget()
                gl_exp = QGridLayout(grade_exp)
                gl_exp.setContentsMargins(0, 0, 0, 0)
                gl_exp.setHorizontalSpacing(8)
                gl_exp.setVerticalSpacing(8)
                for idx_e, (tit_e, val_e, cor_e, ico_e) in enumerate(stats_exp):
                    bloco_e = self._criar_bloco_stat(tit_e, val_e, cor_e, icone=ico_e)
                    gl_exp.addWidget(bloco_e, idx_e // 3, idx_e % 3)
                for c_e in range(3):
                    gl_exp.setColumnStretch(c_e, 1)
                detalhes_layout.addWidget(grade_exp)

                # Timeline de corridas desta temporada (se disponível)
                resultados_hist = temp.get("resultados", [])
                if resultados_hist:
                    detalhes_layout.addWidget(
                        self._criar_timeline_resultados_horizontal(list(resultados_hist))
                    )

                card_temp_layout.addWidget(detalhes_widget)

                # ---------- Toggle ao clicar no topo ----------
                def _make_toggle(dw, sl):
                    def _on_click(_evt=None):
                        aberto = dw.isVisible()
                        dw.setVisible(not aberto)
                        sl.setText("▲" if not aberto else "▼")
                    return _on_click

                topo_widget.mousePressEvent = _make_toggle(detalhes_widget, lbl_seta)

                self._aplicar_sombra_suave(card_temp, blur=12, offset_y=1, alpha=55)
                painel_hist_layout.addWidget(card_temp)

            layout.addWidget(painel_hist)
        else:
            lbl_sem = QLabel("Este piloto ainda não tem histórico de temporadas anteriores.")
            lbl_sem.setFont(Fontes.texto_normal())
            lbl_sem.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl_sem.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl_sem)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll
    

    
    def _as_int(self, valor, padrao=0):
        try:
            return int(valor)
        except (TypeError, ValueError):
            return padrao

    # ------------------------------------------------------------------
    # Rótulos qualitativos
    # ------------------------------------------------------------------

    @staticmethod
    def _rotulo_skill(valor: int) -> tuple[str, str]:
        """Retorna (rótulo, cor) para o skill."""
        if valor >= 85:
            return "Excepcional", "#34d399"
        if valor >= 70:
            return "Habilidoso", "#6ee7b7"
        if valor >= 55:
            return "Competente", "#fbbf24"
        if valor >= 40:
            return "Mediano", "#f59e0b"
        if valor >= 25:
            return "Iniciante", "#fb923c"
        return "Fraco", "#f87171"

    def _criar_sep_vertical(self) -> QFrame:
        """Retorna um separador vertical fino para usar em linhas de stats."""
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {Cores.BORDA};")
        return sep

    @staticmethod
    def _rotulo_agressividade(valor: int) -> tuple[str, str]:
        """Retorna (rótulo, cor) para a agressividade (0–100)."""
        if valor >= 80:
            return "Muito Agressivo", "#f87171"
        if valor >= 60:
            return "Agressivo", "#fb923c"
        if valor >= 40:
            return "Moderado", "#fbbf24"
        if valor >= 20:
            return "Calmo", "#6ee7b7"
        return "Muito Calmo", "#34d399"

    @staticmethod
    def _rotulo_potencial(valor: int) -> tuple[str, str]:
        """Retorna (rótulo, cor) para o potencial (0–100)."""
        if valor >= 85:
            return "Prodígio", "#c084fc"
        if valor >= 70:
            return "Alto Potencial", "#818cf8"
        if valor >= 50:
            return "Promissor", "#38bdf8"
        if valor >= 30:
            return "Limitado", "#94a3b8"
        return "Baixo", "#64748b"

    @staticmethod
    def _rotulo_teto_estimado(valor: int) -> tuple[str, str, int]:
        """Retorna (rotulo, cor, valor_visual) para ocultar potencial exato."""
        if valor >= 80:
            return "⭐⭐⭐ Alto", "#a78bfa", 95
        if valor >= 60:
            return "⭐⭐ Medio", "#38bdf8", 70
        return "⭐ Baixo", "#94a3b8", 40

    @staticmethod
    def _rotulo_consistencia(taxa_dnf: float) -> tuple[str, str]:
        """Retorna (rótulo, cor) com base na taxa de abandono (0.0–1.0)."""
        pct = taxa_dnf * 100.0
        if pct <= 5:
            return "Muito Consistente", "#34d399"
        if pct <= 15:
            return "Consistente", "#fbbf24"
        if pct <= 25:
            return "Irregular", "#fb923c"
        return "Problemático", "#f87171"

    # ------------------------------------------------------------------
    # Ranking histórico global
    # ------------------------------------------------------------------

    def _calcular_ranking_global(
        self,
        campo: str,
        *,
        reverso: bool = True,
        pilotos_extras: list[dict] | None = None,
    ) -> tuple[int, int]:
        """
        Calcula a posição deste piloto entre todos os pilotos do banco
        (ativos + aposentados) para o campo indicado.

        Retorna (posicao_1indexed, total).
        """
        piloto_id = self.piloto.get("id")
        valor_self = float(self._as_int(self.piloto.get(campo), 0))

        todos: list[dict] = []
        for p in self.banco.get("pilotos", []):
            if isinstance(p, dict):
                todos.append(p)
        for a in self.banco.get("aposentados", []):
            if isinstance(a, dict):
                todos.append(a)
        if pilotos_extras:
            todos.extend(pilotos_extras)

        valores: list[float] = []
        valor_proprio: float | None = None
        for p in todos:
            v = float(self._as_int(p.get(campo), 0))
            valores.append(v)
            eid = p.get("id")
            if eid is not None and eid == piloto_id:
                valor_proprio = v

        if valor_proprio is None:
            valor_proprio = valor_self

        total = len(valores)
        if total == 0:
            return 1, 1

        valores_ord = sorted(valores, reverse=reverso)
        posicao = 1
        for v in valores_ord:
            if (reverso and v > valor_proprio) or (not reverso and v < valor_proprio):
                posicao += 1
            else:
                break

        return posicao, total

    def _criar_linha_atributo_qualitativo(
        self,
        titulo: str,
        valor: int,
        rotulo: str,
        cor_rotulo: str,
        cor_barra: str,
        maximo: int = 100,
    ) -> QWidget:
        """Linha de atributo com barra (sem número) e rótulo qualitativo."""
        linha = QWidget()
        layout = QHBoxLayout(linha)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(Fontes.texto_pequeno())
        lbl_titulo.setStyleSheet(f"color: {self._tema_texto_secundario};")
        lbl_titulo.setFixedWidth(100)
        layout.addWidget(lbl_titulo)

        barra = QProgressBar()
        max_int = max(1, int(maximo))
        valor_int = max(0, min(max_int, int(valor)))
        barra.setRange(0, max_int)
        barra.setValue(valor_int)
        barra.setTextVisible(False)
        barra.setFixedHeight(8)
        barra.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {self._tema.get("plot_bg", "#0f1825")};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {cor_barra};
                border-radius: 4px;
            }}
            """
        )
        layout.addWidget(barra, 1)

        lbl_rotulo = QLabel(rotulo)
        lbl_rotulo.setFont(Fontes.texto_pequeno())
        lbl_rotulo.setStyleSheet(
            f"color: {cor_rotulo}; font-weight: 700; min-width: 120px; max-width: 140px;"
        )
        lbl_rotulo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(lbl_rotulo)

        return linha

    def _criar_bloco_stat_com_ranking(
        self,
        titulo: str,
        valor: Any,
        posicao: int,
        total: int,
        cor_valor: str | None = None,
        icone: str | None = None,
        cor_icone: str | None = None,
        taxa_texto: str | None = None,
        premium: bool = False,
    ) -> QWidget:
        """
        Bloco de stat com badge de ranking global.
        - icone fica à esquerda do número (layout horizontal compacto)
        - taxa_texto: linha adicional de porcentagem (ex: '12.5% win rate')
        - premium: borda dourada e card levemente maior (para Títulos)
        """
        bloco = QFrame()
        bloco.setObjectName("bloco_stat")

        borda_premium = f"border: 1.5px solid {Cores.OURO}; border-radius: 8px;" if premium else ""
        if premium:
            bloco.setStyleSheet(
                f"""
                QFrame#bloco_stat {{
                    background-color: {self._tema.get("chip_bg", "#101824")};
                    border: 1.5px solid {Cores.OURO};
                    border-radius: 8px;
                }}
                """
            )

        layout = QVBoxLayout(bloco)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(3)

        icone_texto, icone_cor_padrao = self._icone_por_titulo(titulo)
        icone_final = str(icone or icone_texto)
        cor_icone_final = cor_icone or icone_cor_padrao

        # Linha horizontal: [icone] [número grande]
        linha_valor = QHBoxLayout()
        linha_valor.setContentsMargins(0, 0, 0, 0)
        linha_valor.setSpacing(6)
        linha_valor.setAlignment(Qt.AlignCenter)

        lbl_icone = QLabel()
        lbl_icone.setObjectName("lbl_stat_icone")
        usa_emoji_font = any(ord(ch) >= 0x1F000 for ch in icone_final)
        tamanho_icone = 18 if premium else 14
        if usa_emoji_font:
            fonte_icone = QFont("Segoe UI Emoji", tamanho_icone)
            fonte_icone.setBold(False)
        else:
            fonte_icone = QFont(Fontes.FAMILIA, tamanho_icone)
            fonte_icone.setBold(True)
        lbl_icone.setFont(fonte_icone)
        lbl_icone.setAlignment(Qt.AlignVCenter | Qt.AlignRight)

        if icone_final == "taca_ouro_img":
            sz = 28 if premium else 20
            pixmap_taca = self._obter_pixmap_taca_ouro(sz, sz)
            if not pixmap_taca.isNull():
                lbl_icone.setPixmap(pixmap_taca)
            else:
                lbl_icone.setText("🏆")
        else:
            lbl_icone.setText(icone_final)
            if cor_icone_final:
                lbl_icone.setStyleSheet(f"color: {cor_icone_final};")
        opacidade_icone = QGraphicsOpacityEffect(lbl_icone)
        opacidade_icone.setOpacity(0.92)
        lbl_icone.setGraphicsEffect(opacidade_icone)
        linha_valor.addWidget(lbl_icone)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setObjectName("lbl_stat_valor")
        tamanho_num = 22 if premium else 18
        fonte_valor = QFont(Fontes.FAMILIA, tamanho_num)
        fonte_valor.setBold(True)
        fonte_valor.setWeight(QFont.Weight.Black)
        lbl_valor.setFont(fonte_valor)
        lbl_valor.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        cor_v = cor_valor or (Cores.OURO if premium else None)
        if cor_v:
            lbl_valor.setStyleSheet(f"color: {cor_v};")
        linha_valor.addWidget(lbl_valor)
        layout.addLayout(linha_valor)

        lbl_titulo = QLabel(str(titulo))
        lbl_titulo.setObjectName("lbl_stat_titulo")
        fonte_tit = QFont(Fontes.FAMILIA, 8 if premium else 7)
        fonte_tit.setBold(premium)
        lbl_titulo.setFont(fonte_tit)
        lbl_titulo.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_titulo)

        # Taxa opcional (ex: '12.5% win rate')
        if taxa_texto:
            lbl_taxa = QLabel(taxa_texto)
            fonte_taxa = QFont(Fontes.FAMILIA, 7)
            lbl_taxa.setFont(fonte_taxa)
            lbl_taxa.setAlignment(Qt.AlignCenter)
            lbl_taxa.setStyleSheet(f"color: {self._tema_texto_muted};")
            layout.addWidget(lbl_taxa)

        # Badge de ranking
        if total > 1:
            if posicao == 1:
                badge_texto = "🥇 #1 histórico"
                badge_cor = Cores.OURO
            elif posicao <= 3:
                badge_texto = f"🥈 #{posicao} histórico"
                badge_cor = Cores.PRATA
            elif posicao <= int(total * 0.10) + 1:
                badge_texto = f"Top 10%  #{posicao}"
                badge_cor = "#38d4ff"
            else:
                badge_texto = f"#{posicao} de {total}"
                badge_cor = self._tema_texto_muted

            lbl_ranking = QLabel(badge_texto)
            fonte_badge = QFont(Fontes.FAMILIA, 7)
            fonte_badge.setBold(True)
            lbl_ranking.setFont(fonte_badge)
            lbl_ranking.setAlignment(Qt.AlignCenter)
            lbl_ranking.setStyleSheet(
                f"color: {badge_cor}; "
                "border: 1px solid rgba(230,237,243,20); "
                "border-radius: 8px; "
                "padding: 1px 4px;"
            )
            layout.addWidget(lbl_ranking)

        self._aplicar_sombra_suave(bloco, blur=14 if premium else 12, offset_y=1, alpha=65 if premium else 55)
        return bloco

    def _criar_piramide_carreira(self, corridas_base: int = 0) -> QWidget:
        """
        Monta o layout 'pirâmide' para a seção Carreira Completa:
          Linha 1: Títulos (card premium, full-width)
          Linha 2: Vitórias | Pódios | Top 10  (3 cols)
          Linha 3:    Poles | Voltas Rápidas    (2 cols centralizados)
          Linha 4: Corridas | Pontos | Incidentes (3 cols)
        """
        # ---- Coleta valores ----
        titulos     = self._as_int(self.piloto.get("titulos"), 0)
        vitorias    = self._as_int(self.piloto.get("vitorias_carreira"), 0)
        podios      = self._as_int(self.piloto.get("podios_carreira"), 0)
        corridas    = self._as_int(self.piloto.get("corridas_carreira"), 0) or corridas_base

        # ---- Top-10 calculado ----
        resultados_carreira = self._coletar_resultados_carreira()
        top10 = sum(
            1 for item in resultados_carreira
            if not item.get("dnf", False)
            and isinstance(item.get("posicao"), int)
            and item["posicao"] <= 10
        )

        def _pct(num, base, suffix=""):
            if base <= 0:
                return ""
            return f"{num / base * 100:.1f}%{' ' + suffix if suffix else ''}"

        # ---- Rankings ----
        r_titulos   = self._calcular_ranking_global("titulos")
        r_vitorias  = self._calcular_ranking_global("vitorias_carreira")
        r_podios    = self._calcular_ranking_global("podios_carreira")
        r_corridas  = self._calcular_ranking_global("corridas_carreira")

        def _bloco(titulo, valor, posicao, total, cor=None,
                   icone=None, taxa_texto=None, premium=False):
            return self._criar_bloco_stat_com_ranking(
                titulo=titulo, valor=valor,
                posicao=posicao, total=total,
                cor_valor=cor, icone=icone,
                taxa_texto=taxa_texto,
                premium=premium,
            )

        piramide = QWidget()
        vbox = QVBoxLayout(piramide)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(8)

        # ---- Linha 1: Títulos (full-width, premium) ----
        bloco_titulos = _bloco(
            "Títulos de Campeão", titulos, r_titulos[0], r_titulos[1],
            cor=Cores.OURO if titulos > 0 else None,
            icone="taca_ouro_img", premium=True,
        )
        bloco_titulos.setMinimumHeight(68)
        vbox.addWidget(bloco_titulos)

        # ---- Linha 2: Vitórias | Pódios | Top 10 ----
        linha2 = QHBoxLayout()
        linha2.setSpacing(8)
        linha2.addWidget(_bloco(
            "Vitórias", vitorias, r_vitorias[0], r_vitorias[1],
            cor="#fbbf24" if vitorias > 0 else None,
            icone="🥇",
            taxa_texto=_pct(vitorias, corridas, "win rate"),
        ))
        linha2.addWidget(_bloco(
            "Pódios", podios, r_podios[0], r_podios[1],
            cor=Cores.PRATA if podios > 0 else None,
            icone="🥈",
            taxa_texto=_pct(podios, corridas, "pódio rate"),
        ))
        top10_txt = str(top10) if resultados_carreira else ("-" if corridas == 0 else str(top10))
        linha2.addWidget(_bloco(
            "Top 10", top10_txt, r_podios[0], r_podios[1],
            cor=Cores.VERDE if top10 > 0 else None,
            icone="✅",
            taxa_texto=_pct(top10, corridas, "top10 rate") if isinstance(top10, int) else "",
        ))
        vbox.addLayout(linha2)

        # ---- Linha 3: Corridas (centralizado) ----
        linha3 = QHBoxLayout()
        linha3.setSpacing(8)
        linha3.addStretch(1)
        linha3.addWidget(_bloco(
            "Corridas", corridas, r_corridas[0], r_corridas[1],
            icone="🏎️",
        ), 3)
        linha3.addStretch(1)
        vbox.addLayout(linha3)

        return piramide

    def _criar_grade_stats_com_ranking(
        self,
        stats: list[dict],
        colunas: int = 4,
    ) -> QWidget:
        """Grade genérica de blocos de stat com badge de ranking global."""
        grade_widget = QWidget()
        grade = QGridLayout(grade_widget)
        grade.setContentsMargins(0, 0, 0, 0)
        grade.setHorizontalSpacing(8)
        grade.setVerticalSpacing(8)

        for indice, stat in enumerate(stats):
            campo_ranking = stat.get("campo_ranking")
            reverso = stat.get("ranking_reverso", True)
            if campo_ranking:
                posicao, total = self._calcular_ranking_global(campo_ranking, reverso=reverso)
            else:
                posicao, total = 1, 0

            linha = indice // colunas
            coluna = indice % colunas
            grade.addWidget(
                self._criar_bloco_stat_com_ranking(
                    titulo=stat.get("titulo", "-"),
                    valor=stat.get("valor", "-"),
                    posicao=posicao,
                    total=total,
                    cor_valor=stat.get("cor"),
                    icone=stat.get("icone"),
                    cor_icone=stat.get("cor_icone"),
                    taxa_texto=stat.get("taxa_texto"),
                ),
                linha,
                coluna,
            )

        for coluna in range(colunas):
            grade.setColumnStretch(coluna, 1)

        return grade_widget

    def _normalizar_categoria_id(self, categoria):
        texto = str(categoria or "").strip()
        if not texto:
            return ""

        texto_fold = texto.casefold()
        for item in CATEGORIAS:
            cat_id = str(item.get("id", "")).strip()
            cat_nome = str(item.get("nome", "")).strip()
            if texto_fold in {cat_id.casefold(), cat_nome.casefold()}:
                return cat_id

        return texto

    def _nome_categoria(self, categoria):
        categoria_id = self._normalizar_categoria_id(categoria)
        return obter_nome_categoria(categoria_id) if categoria_id else "-"

    def _obter_mapa_historico_completo(self):
        mapa = {}
        piloto_id = self.piloto.get("id")
        nome_piloto = str(self.piloto.get("nome", "")).strip().casefold()

        for temporada in self.banco.get("historico_temporadas_completas", []):
            if not isinstance(temporada, dict):
                continue

            ano = self._as_int(temporada.get("ano"), 0)
            categoria_id = self._normalizar_categoria_id(
                temporada.get("categoria_id")
                or temporada.get("categoria_nome")
                or temporada.get("categoria")
            )
            classificacao = temporada.get("classificacao", [])

            if ano <= 0 or not isinstance(classificacao, list):
                continue

            entrada_piloto = None
            for entrada in classificacao:
                if not isinstance(entrada, dict):
                    continue

                if piloto_id is not None and entrada.get("piloto_id") == piloto_id:
                    entrada_piloto = entrada
                    break

                nome_entrada = str(entrada.get("piloto", "")).strip().casefold()
                if nome_piloto and nome_entrada == nome_piloto:
                    entrada_piloto = entrada

            if entrada_piloto is None:
                continue

            mapa[(ano, categoria_id)] = entrada_piloto

        return mapa

    def _coletar_resultados_carreira(self):
        resultados = []
        mapa_historico = self._obter_mapa_historico_completo()

        temporadas = sorted(mapa_historico.items(), key=lambda item: (item[0][0], item[0][1]))
        for _, entrada in temporadas:
            for resultado in entrada.get("resultados", []):
                dnf = str(resultado).strip().casefold() == "dnf"
                posicao = None if dnf else self._as_int(resultado, None)
                if posicao is not None and posicao <= 0:
                    posicao = None
                resultados.append({"posicao": posicao, "dnf": dnf})

        for resultado in self.piloto.get("resultados_temporada", []):
            dnf = str(resultado).strip().casefold() == "dnf"
            posicao = None if dnf else self._as_int(resultado, None)
            if posicao is not None and posicao <= 0:
                posicao = None
            resultados.append({"posicao": posicao, "dnf": dnf})

        return resultados

    def _obter_posicao_atual_piloto(self):
        categoria_id = self._normalizar_categoria_id(self.piloto.get("categoria_atual", ""))
        piloto_id = self.piloto.get("id")
        if not categoria_id or piloto_id is None:
            return "-"

        pilotos_categoria = [
            piloto
            for piloto in self.banco.get("pilotos", [])
            if piloto.get("categoria_atual") == categoria_id
            and not piloto.get("aposentado", False)
        ]
        if not pilotos_categoria:
            return "-"

        pilotos_ordenados = sorted(
            pilotos_categoria,
            key=lambda piloto: (
                -self._as_int(piloto.get("pontos_temporada"), 0),
                -self._as_int(piloto.get("vitorias_temporada"), 0),
                -self._as_int(piloto.get("podios_temporada"), 0),
                str(piloto.get("nome", "")).casefold(),
            ),
        )

        for indice, piloto in enumerate(pilotos_ordenados, start=1):
            if piloto.get("id") == piloto_id:
                return indice

        return "-"

    def _coletar_resumo_temporadas(self):
        resumos = []
        mapa_historico = self._obter_mapa_historico_completo()

        for temporada in self.piloto.get("historico_temporadas", []):
            if not isinstance(temporada, dict):
                continue

            ano = self._as_int(temporada.get("ano"), 0)
            categoria_id = self._normalizar_categoria_id(temporada.get("categoria"))
            entrada_completa = mapa_historico.get((ano, categoria_id), {})

            resumos.append(
                {
                    "ano": ano,
                    "categoria_id": categoria_id,
                    "posicao": self._as_int(temporada.get("posicao_final"), "-"),
                    "pontos": self._as_int(temporada.get("pontos"), 0),
                    "vitorias": self._as_int(temporada.get("vitorias"), 0),
                    "podios": self._as_int(temporada.get("podios"), 0),
                    "dnfs": self._as_int(temporada.get("dnfs"), 0),
                    "poles": self._as_int(
                        temporada.get("poles"),
                        self._as_int(entrada_completa.get("poles"), 0),
                    ),
                    "voltas_rapidas": self._as_int(
                        temporada.get("voltas_rapidas"),
                        self._as_int(entrada_completa.get("voltas_rapidas"), 0),
                    ),
                    "atual": False,
                }
            )

        ano_atual = self._as_int(self.banco.get("ano_atual"), 2024)
        categoria_atual = self._normalizar_categoria_id(self.piloto.get("categoria_atual"))
        resumos.append(
            {
                "ano": ano_atual,
                "categoria_id": categoria_atual,
                "posicao": self._obter_posicao_atual_piloto(),
                "pontos": self._as_int(self.piloto.get("pontos_temporada"), 0),
                "vitorias": self._as_int(self.piloto.get("vitorias_temporada"), 0),
                "podios": self._as_int(self.piloto.get("podios_temporada"), 0),
                "dnfs": self._as_int(self.piloto.get("dnfs_temporada"), 0),
                "poles": self._as_int(self.piloto.get("poles_temporada"), 0),
                "voltas_rapidas": self._as_int(self.piloto.get("voltas_rapidas_temporada"), 0),
                "atual": True,
            }
        )

        resumos.sort(
            key=lambda item: (
                self._as_int(item.get("ano"), 0),
                1 if item.get("atual", False) else 0,
            ),
            reverse=True,
        )
        return resumos

    def _cor_por_posicao_corrida(self, posicao, dnf=False):
        if dnf:
            return "#ff4d4f"
        if posicao == 1:
            return Cores.OURO
        if posicao == 2:
            return Cores.PRATA
        if posicao == 3:
            return Cores.BRONZE
        if isinstance(posicao, int) and posicao <= 10:
            return Cores.VERDE
        return Cores.TEXTO_MUTED

    def _normalizar_posicao_corrida(self, resultado: Any, total_grid: int) -> tuple[int, bool]:
        dnf = str(resultado).strip().casefold() == "dnf"
        posicao = self._as_int(resultado, 0)
        if dnf or posicao <= 0:
            return total_grid, True
        return min(total_grid, posicao), False

    def _criar_timeline_resultados_horizontal(self, resultados: list[Any]) -> QWidget:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(6)

        if not resultados:
            lbl_vazio = QLabel("Nenhuma corrida disputada ainda.")
            lbl_vazio.setFont(Fontes.texto_normal())
            lbl_vazio.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(lbl_vazio)
            return wrapper

        categoria_id = self._normalizar_categoria_id(self.piloto.get("categoria_atual"))
        total_grid = sum(
            1
            for piloto in self.banco.get("pilotos", [])
            if piloto.get("categoria_atual") == categoria_id and not piloto.get("aposentado", False)
        )
        total_grid = max(20, total_grid)

        linha_widget = QWidget()
        linha_layout = QHBoxLayout(linha_widget)
        linha_layout.setContentsMargins(6, 10, 6, 10)
        linha_layout.setSpacing(0)

        for indice, resultado in enumerate(resultados, start=1):
            posicao, dnf = self._normalizar_posicao_corrida(resultado, total_grid)
            cor = self._cor_por_posicao_corrida(posicao, dnf)
            texto_resultado = "DNF" if dnf else f"P{posicao}"

            if indice > 1:
                conector = QFrame()
                conector.setObjectName("timeline_linha_horizontal")
                conector.setFixedHeight(2)
                conector.setFixedWidth(30)
                linha_layout.addWidget(conector, 0, Qt.AlignVCenter)

            no = QWidget()
            no_layout = QVBoxLayout(no)
            no_layout.setContentsMargins(2, 0, 2, 0)
            no_layout.setSpacing(4)

            bolha = QLabel(texto_resultado)
            bolha.setAlignment(Qt.AlignCenter)
            bolha.setFixedSize(52, 30)
            bolha.setStyleSheet(
                f"""
                QLabel {{
                    background-color: {self._tema.get("chip_bg", "#101824")};
                    color: {cor};
                    border: 1px solid rgba(230, 237, 243, 28);
                    border-radius: 15px;
                    font-weight: 700;
                }}
                """
            )
            no_layout.addWidget(bolha, 0, Qt.AlignHCenter)

            lbl_rodada = QLabel(f"R{indice}")
            lbl_rodada.setAlignment(Qt.AlignCenter)
            lbl_rodada.setFont(Fontes.texto_pequeno())
            lbl_rodada.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            no_layout.addWidget(lbl_rodada)

            linha_layout.addWidget(no, 0, Qt.AlignTop)

        linha_widget.setMinimumWidth(max(520, len(resultados) * 84))
        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))
        scroll.setFixedHeight(92)
        scroll.setWidget(linha_widget)

        wrapper_layout.addWidget(scroll)
        return wrapper

    def _cor_por_posicao_historico(self, posicao: Any) -> str:
        pos = self._as_int(posicao, 999)
        if pos <= 0:
            return Cores.TEXTO_MUTED
        if pos == 1:
            return Cores.OURO
        if pos == 2:
            return Cores.PRATA
        if pos == 3:
            return Cores.BRONZE
        if pos <= 10:
            return Cores.VERDE
        return Cores.TEXTO_MUTED

    def _criar_grafico_posicoes_temporada(self, resultados):
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(6)

        if not resultados:
            lbl_vazio = QLabel("Nenhuma corrida na temporada atual.")
            lbl_vazio.setFont(Fontes.texto_pequeno())
            lbl_vazio.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(lbl_vazio)
            return wrapper

        lbl_hint = QLabel("Evolucao de posicao por rodada (P1 no topo)")
        lbl_hint.setFont(Fontes.texto_pequeno())
        lbl_hint.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        wrapper_layout.addWidget(lbl_hint)

        categoria_id = self._normalizar_categoria_id(self.piloto.get("categoria_atual"))
        total_grid = sum(
            1
            for piloto in self.banco.get("pilotos", [])
            if piloto.get("categoria_atual") == categoria_id
            and not piloto.get("aposentado", False)
        )
        total_grid = max(20, total_grid)

        largura = max(380, len(resultados) * 64)
        altura = 220
        pixmap = QPixmap(largura, altura)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._tema.get("plot_bg", "#0f1825")))
        painter.drawRoundedRect(0, 0, largura, altura, 8, 8)

        margem_esq = 42
        margem_dir = 18
        margem_top = 18
        margem_base = 30
        area_largura = max(1, largura - margem_esq - margem_dir)
        area_altura = max(1, altura - margem_top - margem_base)

        # Fundo da zona de pódio (P1 a P3)
        y_p1 = margem_top
        y_p3 = margem_top + (2 / max(1, total_grid - 1)) * area_altura
        h_podio = y_p3 - y_p1
        painter.setBrush(QColor(255, 215, 0, 12))  # Dourado bem transparente
        painter.setPen(Qt.NoPen)
        painter.drawRect(margem_esq, int(y_p1), int(area_largura), int(h_podio))

        # Grade horizontal.
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = int(margem_top + frac * area_altura)
            painter.setPen(QPen(QColor(self._tema_borda), 1))
            painter.drawLine(margem_esq, y, largura - margem_dir, y)

            pos_lbl = 1 + int(round(frac * (total_grid - 1)))
            painter.setPen(QPen(QColor(self._tema_texto_muted), 1))
            painter.setFont(Fontes.texto_pequeno())
            painter.drawText(6, y + 4, f"P{pos_lbl}")

        total_pontos = len(resultados)
        passo_x = area_largura / max(1, total_pontos - 1)
        pontos: list[tuple[float, float, str, bool, int]] = []

        for indice, resultado in enumerate(resultados):
            posicao, dnf = self._normalizar_posicao_corrida(resultado, total_grid)
            x = margem_esq + indice * passo_x
            y = margem_top + ((max(1, posicao) - 1) / max(1, total_grid - 1)) * area_altura
            cor = self._cor_por_posicao_corrida(posicao, dnf)
            pontos.append((x, y, cor, dnf, posicao))

        if len(pontos) >= 2:
            painter.setPen(QPen(QColor(self._cor_equipe), 2))
            for indice in range(1, len(pontos)):
                x0, y0, _, _, _ = pontos[indice - 1]
                x1, y1, _, _, _ = pontos[indice]
                painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        for indice, (x, y, cor, dnf, posicao) in enumerate(pontos, start=1):
            painter.setPen(QPen(QColor(self._tema.get("card_bg", "#0d131a")), 1))
            painter.setBrush(QColor(cor))
            painter.drawEllipse(QPoint(int(x), int(y)), 4, 4)

            painter.setPen(QPen(QColor(self._tema_texto_muted), 1))
            painter.setFont(Fontes.texto_pequeno())
            painter.drawText(int(x - 9), altura - 10, f"R{indice}")

            if dnf:
                painter.setPen(QPen(QColor("#ff6b61"), 1))
                painter.drawText(int(x - 10), int(y - 8), "DNF")
            elif posicao <= 3:
                painter.setPen(QPen(QColor(cor), 1))
                painter.drawText(int(x - 8), int(y - 8), f"P{posicao}")

        painter.end()

        grafico_lbl = QLabel()
        grafico_lbl.setPixmap(pixmap)
        grafico_lbl.setFixedSize(largura, altura)
        grafico_lbl.setScaledContents(False)
        self._aplicar_sombra_suave(grafico_lbl, blur=10, offset_y=1, alpha=45)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))
        scroll.setFixedHeight(altura + 16)
        scroll.setWidget(grafico_lbl)

        wrapper_layout.addWidget(scroll)
        return wrapper

    def _criar_grafico_historico_categoria(self) -> QWidget:
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(6)

        mapa_historico = self._obter_mapa_historico_completo()
        if not mapa_historico:
            lbl_vazio = QLabel("Nenhum histórico disponível.")
            lbl_vazio.setFont(Fontes.texto_pequeno())
            lbl_vazio.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(lbl_vazio)
            return wrapper

        lbl_hint = QLabel("Histórico na categoria (Posição x Ano)")
        lbl_hint.setFont(Fontes.texto_pequeno())
        lbl_hint.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        wrapper_layout.addWidget(lbl_hint)

        categoria_id = self._normalizar_categoria_id(self.piloto.get("categoria_atual"))

        # Coletar pontos: (Ano, Posicao)
        dados = []
        for (ano, cat_id), entrada in mapa_historico.items():
            if categoria_id and cat_id != categoria_id:
                continue
            pos = self._as_int(entrada.get("posicao"), 0)
            if pos > 0:
                dados.append((ano, pos))
        
        dados.sort(key=lambda x: x[0])  # Ordenar por ano crescente

        if not dados:
            lbl_vazio = QLabel("Piloto não possui histórico completo nesta categoria.")
            lbl_vazio.setFont(Fontes.texto_pequeno())
            lbl_vazio.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl_vazio.setAlignment(Qt.AlignCenter)
            wrapper_layout.addWidget(lbl_vazio)
            return wrapper

        largura = max(380, len(dados) * 64)
        altura = 220
        pixmap = QPixmap(largura, altura)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self._tema.get("plot_bg", "#0f1825")))
        painter.drawRoundedRect(0, 0, largura, altura, 8, 8)

        margem_esq = 42
        margem_dir = 18
        margem_top = 18
        margem_base = 30
        area_largura = max(1, largura - margem_esq - margem_dir)
        area_altura = max(1, altura - margem_top - margem_base)

        pos_max = max(d[1] for d in dados)
        pos_max = max(pos_max, 5)  # Eixo até pelo menos 5

        # Grade horizontal
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            y = int(margem_top + frac * area_altura)
            painter.setPen(QPen(QColor(self._tema_borda), 1))
            painter.drawLine(margem_esq, y, largura - margem_dir, y)

            pos_lbl = 1 + int(round(frac * (pos_max - 1)))
            painter.setPen(QPen(QColor(self._tema_texto_muted), 1))
            painter.setFont(Fontes.texto_pequeno())
            painter.drawText(6, y + 4, f"{pos_lbl}º")

        passo_x = area_largura / max(1, len(dados) - 1)
        pontos: list[tuple[float, float, str, int, int]] = []

        cor_linha = "#8b5cf6"  # Roxo suave distinto da cor da equipe atual

        for indice, (ano, pos) in enumerate(dados):
            x = margem_esq + indice * passo_x
            y = margem_top + ((pos - 1) / max(1, pos_max - 1)) * area_altura
            pontos.append((x, y, cor_linha, ano, pos))

        if len(pontos) >= 2:
            painter.setPen(QPen(QColor(cor_linha), 2))
            for indice in range(1, len(pontos)):
                x0, y0, _, _, _ = pontos[indice - 1]
                x1, y1, _, _, _ = pontos[indice]
                painter.drawLine(int(x0), int(y0), int(x1), int(y1))

        for x, y, cor, ano, pos in pontos:
            painter.setPen(QPen(QColor(self._tema.get("card_bg", "#0d131a")), 1))
            painter.setBrush(QColor(cor))
            painter.drawEllipse(QPoint(int(x), int(y)), 4, 4)

            painter.setPen(QPen(QColor(self._tema_texto_muted), 1))
            painter.setFont(Fontes.texto_pequeno())
            painter.drawText(int(x - 12), altura - 10, str(ano))

            if pos <= 3:
                c_lbl = Cores.OURO if pos == 1 else (Cores.PRATA if pos == 2 else Cores.BRONZE)
                painter.setPen(QPen(QColor(c_lbl), 1))
            else:
                painter.setPen(QPen(QColor(self._tema_texto_secundario), 1))
            painter.drawText(int(x - 6), int(y - 8), f"P{pos}")

        painter.end()

        grafico_lbl = QLabel()
        grafico_lbl.setPixmap(pixmap)
        grafico_lbl.setFixedSize(largura, altura)
        grafico_lbl.setScaledContents(False)
        self._aplicar_sombra_suave(grafico_lbl, blur=10, offset_y=1, alpha=45)

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))
        scroll.setFixedHeight(altura + 16)
        scroll.setWidget(grafico_lbl)

        wrapper_layout.addWidget(scroll)
        return wrapper

    def _criar_tabela_comparativo_temporadas(self, resumos):
        if not resumos:
            lbl = QLabel("Nenhum dado de temporada disponivel.")
            lbl.setFont(Fontes.texto_pequeno())
            lbl.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
            lbl.setAlignment(Qt.AlignCenter)
            return lbl

        tabela = QTableWidget()
        tabela.setColumnCount(9)
        tabela.setRowCount(len(resumos))
        tabela.setHorizontalHeaderLabels(
            ["Ano", "Categoria", "Pos", "Pts", "Vit", "Pod", "DNF", "Pol", "VR"]
        )
        tabela.setStyleSheet(
            _estilo_tabela_ficha(
                cor_fundo=self._tema.get("panel_bg", "#161e29"),
                cor_header=self._tema.get("chip_bg", "#101824"),
                cor_texto=self._tema_texto_primario,
                cor_texto_secundario=self._tema_texto_secundario,
                cor_borda=self._tema_borda,
            )
        )
        tabela.setSelectionMode(QAbstractItemView.NoSelection)
        tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabela.verticalHeader().setVisible(False)
        tabela.setShowGrid(False)

        header = tabela.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for coluna in range(2, 9):
            header.setSectionResizeMode(coluna, QHeaderView.ResizeToContents)

        for row, resumo in enumerate(resumos):
            tabela.setRowHeight(row, 30)

            ano = self._as_int(resumo.get("ano"), "-")
            if resumo.get("atual", False):
                ano = f"{ano} (Atual)"

            valores = [
                ano,
                self._nome_categoria(resumo.get("categoria_id")),
                resumo.get("posicao", "-"),
                self._as_int(resumo.get("pontos"), 0),
                self._as_int(resumo.get("vitorias"), 0),
                self._as_int(resumo.get("podios"), 0),
                self._as_int(resumo.get("dnfs"), 0),
                self._as_int(resumo.get("poles"), 0),
                self._as_int(resumo.get("voltas_rapidas"), 0),
            ]

            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if coluna == 1:
                    item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                else:
                    item.setTextAlignment(Qt.AlignCenter)
                tabela.setItem(row, coluna, item)

        return tabela

    def _criar_barra_distribuicao_resultados(
        self,
        total_corridas: int,
        vitorias: int,
        podios: int,
        top10: int,
    ) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        if total_corridas <= 0:
            lbl_vazio = QLabel("Sem corridas para calcular distribuicao.")
            lbl_vazio.setFont(Fontes.texto_pequeno())
            lbl_vazio.setStyleSheet(f"color: {self._tema_texto_muted};")
            layout.addWidget(lbl_vazio)
            return wrapper

        vitorias = max(0, min(total_corridas, int(vitorias)))
        podios = max(0, min(total_corridas, int(podios)))
        top10 = max(0, min(total_corridas, int(top10)))

        podios_sem_v = max(0, podios - vitorias)
        top10_sem_p = max(0, top10 - podios)
        fora_top10 = max(0, total_corridas - top10)

        barra = QFrame()
        barra.setFixedHeight(12)
        barra.setStyleSheet(
            f"""
            QFrame {{
                background-color: {self._tema.get("plot_bg", "#0f1825")};
                border: 1px solid rgba(230, 237, 243, 24);
                border-radius: 6px;
            }}
            """
        )

        barra_layout = QHBoxLayout(barra)
        barra_layout.setContentsMargins(1, 1, 1, 1)
        barra_layout.setSpacing(0)

        segmentos = [
            ("Vitorias", vitorias, Cores.OURO),
            ("Podios", podios_sem_v, Cores.PRATA),
            ("Top 10", top10_sem_p, Cores.VERDE),
            ("Resto", fora_top10, self._tema_borda),
        ]
        for _nome, qtd, cor in segmentos:
            if qtd <= 0:
                continue
            seg = QFrame()
            seg.setStyleSheet(f"background-color: {cor}; border: none;")
            barra_layout.addWidget(seg, max(1, int(qtd)))

        legenda = QLabel(
            f"Vitorias {vitorias} | Podios {podios} | Top 10 {top10} | Total {total_corridas}"
        )
        legenda.setFont(Fontes.texto_pequeno())
        legenda.setStyleSheet(f"color: {self._tema_texto_secundario};")

        layout.addWidget(barra)
        layout.addWidget(legenda)
        return wrapper

    def _calcular_maior_sequencia_podios(self, resultados):
        max_seq, seq_atual = 0, 0
        for r in resultados:
            pos = self._as_int(r.get("posicao"), 999) if not r.get("dnf") else 999
            if pos <= 3:
                seq_atual += 1
                max_seq = max(max_seq, seq_atual)
            else:
                seq_atual = 0
        return max_seq

    def _calcular_maior_sequencia_vitorias(self, resultados):
        max_seq, seq_atual = 0, 0
        for r in resultados:
            pos = self._as_int(r.get("posicao"), 999) if not r.get("dnf") else 999
            if pos == 1:
                seq_atual += 1
                max_seq = max(max_seq, seq_atual)
            else:
                seq_atual = 0
        return max_seq

    def _calcular_maior_ganho_posicao(self, resultados):
        max_ganho = 0
        corrida_ref = ""
        for r in resultados:
            if r.get("dnf"): continue
            grid = self._as_int(r.get("grid"), 0)
            pos = self._as_int(r.get("posicao"), 0)
            if grid > 0 and pos > 0 and grid > pos:
                ganho = grid - pos
                if ganho > max_ganho:
                    max_ganho = ganho
                    corrida_ref = r.get("circuito", "")
        return max_ganho, corrida_ref

    def _calcular_hat_tricks(self, resultados):
        count = 0
        for r in resultados:
            if r.get("dnf"): continue
            grid = self._as_int(r.get("grid"), 0)
            pos = self._as_int(r.get("posicao"), 0)
            vr = bool(r.get("volta_rapida", False))
            if grid == 1 and pos == 1 and vr:
                count += 1
        return count

    def _calcular_grand_slams(self, resultados):
        count = 0
        for r in resultados:
            if r.get("dnf"): continue
            grid = self._as_int(r.get("grid"), 0)
            pos = self._as_int(r.get("posicao"), 0)
            vr = bool(r.get("volta_rapida", False))
            led_all = bool(r.get("liderou_todas_voltas", False) or r.get("liderou_todas", False))
            if grid == 1 and pos == 1 and vr and led_all:
                count += 1
        return count

    def _criar_painel_graficos_lado_a_lado(self, res_temp: list) -> QWidget:
        wrapper = QWidget()
        lay = QHBoxLayout(wrapper)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        p_esq, lay_esq = self._criar_painel_secao("Histórico da Carreira")
        lay_esq.addWidget(self._criar_grafico_historico_categoria())
        lay.addWidget(p_esq, 1)

        p_dir, lay_dir = self._criar_painel_secao("Evolução — Temporada Atual")
        lay_dir.addWidget(self._criar_grafico_posicoes_temporada(res_temp))
        lay.addWidget(p_dir, 1)

        return wrapper

    def _build_tab_estatisticas(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema_borda_hover))

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        resultados_carreira = self._coletar_resultados_carreira()
        resultados_validos = [
            item["posicao"]
            for item in resultados_carreira
            if isinstance(item.get("posicao"), int) and not item.get("dnf", False)
        ]

        total_corridas = self._as_int(self.piloto.get("corridas_carreira"), 0)
        if total_corridas <= 0:
            total_corridas = len(resultados_carreira)

        vitorias = self._as_int(self.piloto.get("vitorias_carreira"), 0)
        podios = self._as_int(self.piloto.get("podios_carreira"), 0)
        dnfs = self._as_int(self.piloto.get("dnfs_carreira"), 0)
        incidentes = self._as_int(self.piloto.get("incidentes_carreira"), 0)
        top10 = sum(
            1
            for item in resultados_carreira
            if not item.get("dnf", False)
            and isinstance(item.get("posicao"), int)
            and item["posicao"] <= 10
        )
        poles = self._as_int(self.piloto.get("poles_carreira"), 0)
        voltas_rap = self._as_int(self.piloto.get("voltas_rapidas_carreira", self.piloto.get("poles_carreira", 0)), 0)
        pontos = self._as_int(self.piloto.get("pontos_carreira"), 0)

        taxa_abandono = (dnfs / total_corridas * 100.0) if total_corridas else 0.0
        media_posicao = (sum(resultados_validos) / len(resultados_validos) if resultados_validos else None)
        incidentes_por_corrida = (incidentes / total_corridas) if total_corridas else 0.0
        
        top10_texto = str(top10) if resultados_carreira else ("0" if total_corridas == 0 else "-")
        media_texto = f"P{media_posicao:.2f}" if media_posicao is not None else "-"

        def _pct_e(num, base, suffix=""):
            if base <= 0:
                return ""
            return f"{num / base * 100:.1f}%{' ' + suffix if suffix else ''}"

        # ─── PERFIL GERAL (Agrupado) ──────────────────────────────────────────
        painel_geral, painel_geral_layout = self._criar_painel_secao("Perfil Geral")

        # 1. Volume & Eficiência
        lbl_vol = QLabel("Volume & Eficiência")
        lbl_vol.setFont(QFont(Fontes.FAMILIA, 11, QFont.Bold))
        lbl_vol.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; margin-top: 4px;")
        painel_geral_layout.addWidget(lbl_vol)

        s_vol = [
            {"titulo": "Corridas", "valor": total_corridas, "icone": "🏎️", "campo_ranking": "corridas_carreira"},
            {"titulo": "Pontos", "valor": pontos, "cor": Cores.ACCENT_PRIMARY, "icone": "✦", "campo_ranking": "pontos_carreira", "taxa_texto": f"{pontos/total_corridas:.1f} pts/corr" if total_corridas else ""},
            {"titulo": "Média Final", "valor": media_texto, "icone": "📉"},
        ]
        painel_geral_layout.addWidget(self._criar_grade_stats_com_ranking(s_vol, colunas=3))
        painel_geral_layout.addWidget(self._criar_sep_vertical())

        # 2. Sucesso & Ritmo
        lbl_suc = QLabel("Sucesso & Ritmo")
        lbl_suc.setFont(QFont(Fontes.FAMILIA, 11, QFont.Bold))
        lbl_suc.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; margin-top: 8px;")
        painel_geral_layout.addWidget(lbl_suc)

        s_suc = [
            {"titulo": "Vitórias", "valor": vitorias, "cor": Cores.OURO if vitorias > 0 else "", "icone": "🥇", "campo_ranking": "vitorias_carreira", "taxa_texto": _pct_e(vitorias, total_corridas, "win")},
            {"titulo": "Pódios", "valor": podios, "cor": Cores.PRATA if podios > 0 else "", "icone": "🥈", "campo_ranking": "podios_carreira", "taxa_texto": _pct_e(podios, total_corridas, "pod")},
            {"titulo": "Top 10", "valor": top10_texto, "cor": Cores.VERDE if str(top10_texto).isdigit() else "", "icone": "✅", "taxa_texto": _pct_e(top10, total_corridas, "t10")},
            {"titulo": "Poles", "valor": poles, "icone": "◎", "campo_ranking": "poles_carreira", "taxa_texto": _pct_e(poles, total_corridas, "pole")},
            {"titulo": "V. Rápidas", "valor": voltas_rap, "icone": "⧗", "campo_ranking": "voltas_rapidas_carreira", "taxa_texto": _pct_e(voltas_rap, total_corridas, "vr")},
        ]
        painel_geral_layout.addWidget(self._criar_grade_stats_com_ranking(s_suc, colunas=5))
        painel_geral_layout.addWidget(self._criar_sep_vertical())

        # 3. Disciplina
        lbl_dis = QLabel("Disciplina")
        lbl_dis.setFont(QFont(Fontes.FAMILIA, 11, QFont.Bold))
        lbl_dis.setStyleSheet(f"color: {Cores.VERMELHO}; margin-top: 8px;")
        painel_geral_layout.addWidget(lbl_dis)

        s_dis = [
            {"titulo": "Incidentes", "valor": incidentes, "cor": Cores.VERMELHO if incidentes > 0 else "", "icone": "🛡", "campo_ranking": "incidentes_carreira", "ranking_reverso": False, "taxa_texto": f"{incidentes_por_corrida:.2f} inc/corr"},
            {"titulo": "DNFs", "valor": dnfs, "cor": Cores.VERMELHO if dnfs > 0 else "", "icone": "🛑", "taxa_texto": f"{taxa_abandono:.1f}% abandono"},
        ]
        painel_geral_layout.addWidget(self._criar_grade_stats_com_ranking(s_dis, colunas=2))

        # Dist Barra
        painel_geral_layout.addSpacing(8)
        painel_geral_layout.addWidget(self._criar_barra_distribuicao_resultados(total_corridas, vitorias, podios, top10))
        layout.addWidget(painel_geral)

        # ─── CONQUISTAS ───────────────────────────────────────────────────────
        campeonatos = self._as_int(self.piloto.get("titulos"), 0)
        streak_podio = self._calcular_maior_sequencia_podios(resultados_carreira)
        streak_vit = self._calcular_maior_sequencia_vitorias(resultados_carreira)
        ganho, corrida_ganho = self._calcular_maior_ganho_posicao(resultados_carreira)
        str_ganho = f"+{ganho} pos" if ganho > 0 else "-"
        hat_tricks = self._calcular_hat_tricks(resultados_carreira)
        grand_slams = self._calcular_grand_slams(resultados_carreira)

        painel_conquistas, painel_conquistas_layout = self._criar_painel_secao("Recordes & Conquistas")
        s_conq = [
            {"titulo": "Campeonatos", "valor": campeonatos, "cor": Cores.OURO if campeonatos > 0 else "", "icone": "🏆"},
            {"titulo": "Streak Pódio", "valor": f"{streak_podio} seg" if streak_podio > 0 else "-", "icone": "📈"},
            {"titulo": "Streak Vitória", "valor": f"{streak_vit} seg" if streak_vit > 0 else "-", "icone": "🔥"},
            {"titulo": "Maior Escalada", "valor": str_ganho, "cor": Cores.VERDE if ganho > 0 else "", "icone": "🚀", "taxa_texto": corrida_ganho},
            {"titulo": "Hat-Tricks", "valor": hat_tricks, "cor": Cores.ROXO if hat_tricks > 0 else "", "icone": "🎩", "taxa_texto": "Pole+Vit+VR"},
            {"titulo": "Grand Slams", "valor": grand_slams, "cor": Cores.OURO if grand_slams > 0 else "", "icone": "👑", "taxa_texto": "Perfeito"},
        ]
        painel_conquistas_layout.addWidget(self._criar_grade_stats(s_conq, colunas=6))
        layout.addWidget(painel_conquistas)

        # ─── GRÁFICOS (Lado a Lado) ───────────────────────────────────────────
        res_temp = self.piloto.get("resultados_temporada", [])
        layout.addWidget(self._criar_painel_graficos_lado_a_lado(res_temp))

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

class FichaEquipe(QDialog):
    """Ficha detalhada de uma equipe — gaveta esquerda."""

    def __init__(self, equipe, banco, parent=None):
        super().__init__(parent)
        self.equipe = equipe
        self.banco = banco
        self._tema = _tema_ficha(None)
        self._cor_equipe = str(equipe.get("cor_primaria", "") or "").strip() or Cores.ACCENT_PRIMARY
        self._overlay_backdrop = None
        self._backdrop_blur_label = None
        self._backdrop_base_pixmap = QPixmap()
        self._atualizando_blur = False
        self._blur_effect = None
        self._blur_anim = None
        self._overlay_card = None
        self._btn_fechar_drawer = None
        self._drawer_anim = None
        self._fechamento_animando = False
        self._entrada_animando = False
        self._aceita_clique_fora = False
        self._header_lbl_nome = None
        self._header_lbl_sub = None
        self._btn_nav_up = None
        self._btn_nav_down = None
        self._equipes_navegacao: list = []
        self._indice_equipe_navegacao = 0
        self._inicializar_navegacao_equipes()
        self.setWindowTitle(f"Ficha da Equipe - {equipe.get('nome','?')}")
        self.setObjectName("ficha_equipe_dialog")
        self.setMinimumSize(720, 640)
        self.resize(900, 800)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setWindowFlag(Qt.Dialog, True)
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(self._estilo_dialogo())
        self._build_ui()

    # ── Navegação ────────────────────────────────────────────────────────────

    def _inicializar_navegacao_equipes(self) -> None:
        parent = self.parentWidget()
        candidatos = []
        if parent is not None:
            candidatos = [e for e in getattr(parent, "equipes_ordenadas", []) if isinstance(e, dict)]
        if not candidatos:
            candidatos = [e for e in self.banco.get("equipes", []) if isinstance(e, dict)]
        if not candidatos:
            self._equipes_navegacao = [self.equipe]
            self._indice_equipe_navegacao = 0
            return
        self._equipes_navegacao = candidatos
        nome_atual = str(self.equipe.get("nome", "") or "").strip().casefold()
        idx = next(
            (i for i, e in enumerate(candidatos)
             if str(e.get("nome", "") or "").strip().casefold() == nome_atual), -1
        )
        if idx < 0:
            self._equipes_navegacao.insert(0, self.equipe)
            idx = 0
        self._indice_equipe_navegacao = idx

    def _navegar_equipe(self, delta: int) -> None:
        total = len(self._equipes_navegacao)
        if total <= 1:
            return
        novo = (self._indice_equipe_navegacao + delta) % total
        if novo == self._indice_equipe_navegacao:
            return
        self._indice_equipe_navegacao = novo
        self.equipe = self._equipes_navegacao[novo]
        self._cor_equipe = str(self.equipe.get("cor_primaria", "") or "").strip() or Cores.ACCENT_PRIMARY
        self.setStyleSheet(self._estilo_dialogo())
        tab_idx = 0
        if hasattr(self, "_tabs_equipe") and isinstance(self._tabs_equipe, QTabWidget):
            tab_idx = self._tabs_equipe.currentIndex()
        self._montar_conteudo_card(indice_tab=tab_idx)
        self._atualizar_header_info()
        self._atualizar_estado_navegacao()
        self._notificar_equipe_em_evidencia()
        self._posicionar_controles_overlay()

    def _atualizar_estado_navegacao(self) -> None:
        hab = len(self._equipes_navegacao) > 1 and not self._fechamento_animando
        if isinstance(self._btn_nav_up, QPushButton):
            self._btn_nav_up.setEnabled(hab)
        if isinstance(self._btn_nav_down, QPushButton):
            self._btn_nav_down.setEnabled(hab)

    # ── Geometria ────────────────────────────────────────────────────────────

    def _ajustar_geometria_overlay(self) -> None:
        parent = self.parentWidget()
        if parent and parent.isVisible():
            topo = parent.mapToGlobal(QPoint(0, 0))
            self.setGeometry(topo.x(), topo.y(), parent.width(), parent.height())
            return
        if self.width() < 880 or self.height() < 700:
            self.resize(900, 800)

    def _calcular_geometria_card(self) -> QRect:
        mx, my = 24, 18
        largura = min(1000, max(680, int(self.width() * 0.78)))
        altura = min(900, max(640, int(self.height() * 0.92)))
        largura = min(largura, self.width() - mx * 2)
        altura = min(altura, self.height() - my * 2)
        x = mx
        y = max(my, (self.height() - altura) // 2)
        return QRect(x, y, largura, altura)

    def _posicionar_botao_drawer(self) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        if not isinstance(self._btn_fechar_drawer, QPushButton):
            return
        rect = self._overlay_card.geometry()
        btn_w, btn_h = 28, max(220, rect.height())
        self._btn_fechar_drawer.setFixedSize(btn_w, btn_h)
        self._btn_fechar_drawer.move(rect.right() - 2, rect.y())
        self._btn_fechar_drawer.raise_()

    def _posicionar_controles_overlay(self) -> None:
        if not isinstance(self._overlay_backdrop, QWidget):
            return
        self._overlay_backdrop.setGeometry(0, 0, self.width(), self.height())
        self._atualizar_blur_backdrop()
        if isinstance(self._overlay_card, QFrame):
            self._overlay_card.setGeometry(self._calcular_geometria_card())
        self._posicionar_botao_drawer()

    # ── Blur ─────────────────────────────────────────────────────────────────

    def _atualizar_blur_backdrop(self, recapturar: bool = False) -> None:
        if not isinstance(self._backdrop_blur_label, QLabel):
            return
        self._backdrop_blur_label.setGeometry(0, 0, self.width(), self.height())
        if recapturar and not self._atualizando_blur:
            parent = self.parentWidget()
            if parent and parent.isVisible():
                self._atualizando_blur = True
                try:
                    cap = parent.grab()
                    if not cap.isNull():
                        self._backdrop_base_pixmap = cap
                finally:
                    self._atualizando_blur = False
        if self._backdrop_base_pixmap.isNull():
            self._backdrop_blur_label.clear()
            return
        px = self._backdrop_base_pixmap.scaled(
            max(2, self.width()), max(2, self.height()),
            Qt.IgnoreAspectRatio, Qt.SmoothTransformation,
        )
        self._backdrop_blur_label.setPixmap(px)
        self._backdrop_blur_label.lower()

    def _animar_blur_entrada(self) -> None:
        if not isinstance(self._blur_effect, QGraphicsBlurEffect):
            return
        if self._backdrop_base_pixmap.isNull():
            QTimer.singleShot(0, self._capturar_e_animar_blur)
            return
        self._iniciar_animacao_blur()

    def _capturar_e_animar_blur(self) -> None:
        if not self.isVisible() or self._fechamento_animando:
            return
        self._atualizar_blur_backdrop(recapturar=True)
        if not self._backdrop_base_pixmap.isNull():
            self._iniciar_animacao_blur()

    def _iniciar_animacao_blur(self) -> None:
        if not isinstance(self._blur_effect, QGraphicsBlurEffect):
            return
        if isinstance(self._blur_anim, QPropertyAnimation):
            self._blur_anim.stop()
        self._blur_effect.setBlurRadius(0.4)
        self._blur_anim = QPropertyAnimation(self._blur_effect, b"blurRadius", self)
        self._blur_anim.setDuration(320)
        self._blur_anim.setStartValue(0.4)
        self._blur_anim.setEndValue(6.0)
        self._blur_anim.setEasingCurve(QEasingCurve.OutQuad)
        self._blur_anim.start()

    # ── Animações ────────────────────────────────────────────────────────────

    def _animar_entrada_gaveta(self) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        self._entrada_animando = True
        self._aceita_clique_fora = False
        self._animar_blur_entrada()
        rect_final = self._calcular_geometria_card()
        rect_inicio = QRect(-rect_final.width() - 20, rect_final.y(),
                            rect_final.width(), rect_final.height())
        self._overlay_card.setGeometry(rect_inicio)
        self._posicionar_botao_drawer()
        if self._drawer_anim is not None:
            self._drawer_anim.stop()
        self._drawer_anim = QPropertyAnimation(self._overlay_card, b"geometry", self)
        self._drawer_anim.setDuration(220)
        self._drawer_anim.setStartValue(rect_inicio)
        self._drawer_anim.setEndValue(rect_final)
        self._drawer_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._drawer_anim.valueChanged.connect(lambda _v: self._posicionar_botao_drawer())
        self._drawer_anim.finished.connect(self._finalizar_animacao_entrada)
        self._drawer_anim.start()

    def _finalizar_animacao_entrada(self) -> None:
        self._entrada_animando = False
        self._posicionar_controles_overlay()
        QTimer.singleShot(180, self._habilitar_clique_fora)

    def _habilitar_clique_fora(self) -> None:
        if self.isVisible() and not self._fechamento_animando and not self._entrada_animando:
            self._aceita_clique_fora = True

    def _animar_saida_gaveta(self) -> None:
        if self._fechamento_animando:
            return
        if not isinstance(self._overlay_card, QFrame):
            self.close()
            return
        self._fechamento_animando = True
        self._aceita_clique_fora = False
        rect_atual = self._overlay_card.geometry()
        rect_fim = QRect(-rect_atual.width() - 24, rect_atual.y(),
                         rect_atual.width(), rect_atual.height())
        if self._drawer_anim is not None:
            self._drawer_anim.stop()
        if isinstance(self._btn_fechar_drawer, QPushButton):
            self._btn_fechar_drawer.setEnabled(False)
        self._atualizar_estado_navegacao()
        self._drawer_anim = QPropertyAnimation(self._overlay_card, b"geometry", self)
        self._drawer_anim.setDuration(180)
        self._drawer_anim.setStartValue(rect_atual)
        self._drawer_anim.setEndValue(rect_fim)
        self._drawer_anim.setEasingCurve(QEasingCurve.InCubic)
        self._drawer_anim.valueChanged.connect(lambda _v: self._posicionar_botao_drawer())
        self._drawer_anim.finished.connect(self.accept)
        self._drawer_anim.start()

    def reject(self) -> None:
        self._animar_saida_gaveta()

    # ── Eventos ──────────────────────────────────────────────────────────────

    def eventFilter(self, obj, event):
        if obj is self._overlay_backdrop and event.type() in (
            QEvent.MouseButtonPress, QEvent.MouseButtonDblClick
        ):
            if event.button() == Qt.LeftButton and isinstance(self._overlay_card, QFrame):
                if not self._overlay_card.geometry().contains(event.pos()):
                    if self._entrada_animando or self._fechamento_animando or not self._aceita_clique_fora:
                        return True
                    self._animar_saida_gaveta()
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._posicionar_controles_overlay()


    def keyPressEvent(self, event) -> None:  # noqa: N802
        key = event.key()
        if key == Qt.Key_Up:
            self._navegar_equipe(-1)
        elif key == Qt.Key_Down:
            self._navegar_equipe(1)
        elif key in (Qt.Key_Escape, Qt.Key_Left):
            self._animar_saida_gaveta()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event) -> None:
        self._ajustar_geometria_overlay()
        super().showEvent(event)
        self._fechamento_animando = False
        self._entrada_animando = True
        self._aceita_clique_fora = False
        if isinstance(self._btn_fechar_drawer, QPushButton):
            self._btn_fechar_drawer.setEnabled(True)
        if isinstance(self._blur_effect, QGraphicsBlurEffect):
            self._blur_effect.setBlurRadius(0.0)
        self._posicionar_controles_overlay()
        self._atualizar_header_info()
        self._notificar_equipe_em_evidencia()
        self._animar_entrada_gaveta()

    # ── Notificação parent ────────────────────────────────────────────────────

    def _notificar_equipe_em_evidencia(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        callback = getattr(parent, "_destacar_equipe_na_tela", None)
        if callable(callback):
            try:
                callback(self.equipe)
            except Exception:
                pass
        QTimer.singleShot(0, lambda: self._atualizar_blur_backdrop(recapturar=True))
        QTimer.singleShot(40, lambda: self._atualizar_blur_backdrop(recapturar=True))
        QTimer.singleShot(100, lambda: self._atualizar_blur_backdrop(recapturar=True))

    # ── Estilos ───────────────────────────────────────────────────────────────

    def _estilo_dialogo(self) -> str:
        t = self._tema
        cor = self._cor_equipe
        tp = t.get("text_primary", Cores.TEXTO_PRIMARY)
        ts = t.get("text_secondary", Cores.TEXTO_SECONDARY)
        tm = t.get("text_muted", Cores.TEXTO_MUTED)
        bd = t.get("border", Cores.BORDA)
        bh = t.get("border_hover", Cores.BORDA_HOVER)
        return f"""
            QDialog#ficha_equipe_dialog {{ background: transparent; }}
            QWidget#overlay_backdrop_eq {{ background-color: {t.get("backdrop", "rgba(8,12,18,70)")}; }}
            QLabel#overlay_blur_label_eq {{ background: transparent; border: none; }}
            QFrame#overlay_card_eq {{
                background-color: {t.get("card_bg", "#0d131a")};
                border: 1px solid {t.get("card_border", "rgba(230,237,243,26)")};
            }}
            QFrame#header_ficha_equipe {{
                background-color: {t.get("header_bg", "#0c141f")};
                border: none;
            }}
            QLabel#lbl_nome_equipe {{ color: {tp}; font-weight: 800; }}
            QLabel#lbl_sub_equipe  {{ color: {ts}; }}
            QFrame#barra_cor_equipe {{ background-color: {cor}; border: none; }}
            QFrame#ficha_panel {{
                background-color: {t.get("panel_bg", "#161e29")};
                border: 1px solid {t.get("card_border", "rgba(230,237,243,18)")};
            }}
            QLabel#titulo_secao {{ color: {tp}; font-size: 11pt; font-weight: 700; }}
            QFrame#bloco_stat {{
                background-color: {t.get("chip_bg", "#101824")};
                border: 1px solid {t.get("card_border", "rgba(230,237,243,20)")};
            }}
            QLabel#lbl_stat_titulo {{ color: {ts}; }}
            QLabel#lbl_stat_valor  {{ color: {tp}; font-weight: 900; }}
            QPushButton#btn_fechar_drawer_eq {{
                background-color: {t.get("header_bg", "rgba(9,15,22,214)")};
                color: {tp};
                border: 1px solid {t.get("card_border", "rgba(230,237,243,45)")};
                border-left: 1px solid {bh};
                border-radius: 0px;
                min-width: 28px; max-width: 28px;
                font-size: 12pt; font-weight: 900; padding: 0px;
            }}
            QPushButton#btn_fechar_drawer_eq:hover {{
                border-color: {cor}; color: #ffffff;
                background-color: {t.get("drawer_hover_bg", "rgba(28,44,67,230)")};
            }}
            QPushButton#btn_nav_equipe {{
                background-color: transparent; color: {tp};
                border: 1px solid {t.get("card_border", "rgba(230,237,243,40)")};
                min-width: 22px; max-width: 22px;
                min-height: 16px; max-height: 16px;
                font-size: 8pt; font-weight: 800; padding: 0px;
            }}
            QPushButton#btn_nav_equipe:hover {{
                border-color: {cor}; color: #ffffff;
                background-color: {t.get("nav_hover_bg", "rgba(35,54,82,165)")};
            }}
            QPushButton#btn_nav_equipe:disabled {{
                color: {tm}; border-color: {bd};
            }}
        """

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._overlay_backdrop = QWidget(self)
        self._overlay_backdrop.setObjectName("overlay_backdrop_eq")
        self._overlay_backdrop.installEventFilter(self)
        root.addWidget(self._overlay_backdrop)

        self._backdrop_blur_label = QLabel(self._overlay_backdrop)
        self._backdrop_blur_label.setObjectName("overlay_blur_label_eq")
        self._backdrop_blur_label.setScaledContents(True)
        self._backdrop_blur_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._blur_effect = QGraphicsBlurEffect(self._backdrop_blur_label)
        self._blur_effect.setBlurRadius(0.0)
        self._backdrop_blur_label.setGraphicsEffect(self._blur_effect)
        self._backdrop_blur_label.lower()

        self._overlay_card = QFrame(self._overlay_backdrop)
        self._overlay_card.setObjectName("overlay_card_eq")
        self._overlay_card.setMinimumWidth(680)
        self._overlay_card.setMinimumHeight(640)
        card_layout = QVBoxLayout(self._overlay_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        self._montar_conteudo_card()

        self._btn_fechar_drawer = QPushButton("\u276f", self._overlay_backdrop)
        self._btn_fechar_drawer.setObjectName("btn_fechar_drawer_eq")
        self._btn_fechar_drawer.setCursor(Qt.PointingHandCursor)
        self._btn_fechar_drawer.clicked.connect(self._animar_saida_gaveta)
        self._btn_fechar_drawer.raise_()
        self._posicionar_controles_overlay()

    def _montar_conteudo_card(self, indice_tab: int = 0) -> None:
        if not isinstance(self._overlay_card, QFrame):
            return
        layout = self._overlay_card.layout()
        if not isinstance(layout, QVBoxLayout):
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        layout.addWidget(self._build_header())

        barra = QFrame()
        barra.setObjectName("barra_cor_equipe")
        barra.setFixedHeight(3)
        layout.addWidget(barra)

        self._tabs_equipe = QTabWidget()
        self._tabs_equipe.setStyleSheet(_estilo_tabs_ficha(
            cor_destaque=self._tema.get("tab_active", "#38d4ff"),
            cor_inativa=self._tema.get("text_secondary", Cores.TEXTO_SECONDARY),
            cor_hover=self._tema.get("text_primary", Cores.TEXTO_PRIMARY),
        ))
        self._tabs_equipe.addTab(self._build_tab_info(), "Informações")
        self._tabs_equipe.addTab(self._build_tab_temporada(), "Temporada")
        self._tabs_equipe.addTab(self._build_tab_historico(), "Histórico")
        self._tabs_equipe.setCurrentIndex(max(0, min(indice_tab, self._tabs_equipe.count() - 1)))
        layout.addWidget(self._tabs_equipe, 1)

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("header_ficha_equipe")
        header.setFixedHeight(148)

        stack = QStackedLayout(header)
        stack.setStackingMode(QStackedLayout.StackAll)
        stack.setContentsMargins(0, 0, 0, 0)

        textura = QLabel()
        textura.setPixmap(self._gerar_textura_header(1400, 200))
        textura.setScaledContents(True)
        stack.addWidget(textura)

        conteudo = QWidget()
        conteudo.setStyleSheet("background: transparent; border: none;")
        cl = QHBoxLayout(conteudo)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(16)
        cl.setAlignment(Qt.AlignVCenter)

        swatch = QFrame()
        swatch.setFixedSize(72, 72)
        swatch.setStyleSheet(f"""
            QFrame {{
                background-color: {self._tema.get("chip_bg", "#111a24")};
                border: 1px solid {self._tema.get("card_border", "rgba(230,237,243,45)")};
                border-radius: 8px;
                border-left: 4px solid {self._cor_equipe};
            }}
        """)
        cl.addWidget(swatch, 0, Qt.AlignVCenter)

        texto_layout = QVBoxLayout()
        texto_layout.setContentsMargins(0, 0, 0, 0)
        texto_layout.setSpacing(4)
        texto_layout.setAlignment(Qt.AlignVCenter)

        linha_nome = QHBoxLayout()
        linha_nome.setContentsMargins(0, 0, 0, 0)
        linha_nome.setSpacing(10)

        nav = QWidget()
        nav.setFixedWidth(24)
        nav_lay = QVBoxLayout(nav)
        nav_lay.setContentsMargins(0, 0, 0, 0)
        nav_lay.setSpacing(2)
        nav_lay.setAlignment(Qt.AlignVCenter)

        self._btn_nav_up = QPushButton("\u25b2")
        self._btn_nav_up.setObjectName("btn_nav_equipe")
        self._btn_nav_up.setCursor(Qt.PointingHandCursor)
        self._btn_nav_up.clicked.connect(lambda: self._navegar_equipe(-1))
        nav_lay.addWidget(self._btn_nav_up)

        self._btn_nav_down = QPushButton("\u25bc")
        self._btn_nav_down.setObjectName("btn_nav_equipe")
        self._btn_nav_down.setCursor(Qt.PointingHandCursor)
        self._btn_nav_down.clicked.connect(lambda: self._navegar_equipe(1))
        nav_lay.addWidget(self._btn_nav_down)

        linha_nome.addWidget(nav, 0, Qt.AlignVCenter)

        lbl_nome = QLabel(str(self.equipe.get("nome", "?") or "?"))
        lbl_nome.setObjectName("lbl_nome_equipe")
        fonte_nome = QFont(Fontes.FAMILIA, 22)
        fonte_nome.setBold(True)
        lbl_nome.setFont(fonte_nome)
        self._header_lbl_nome = lbl_nome
        linha_nome.addWidget(lbl_nome, 0, Qt.AlignVCenter)
        linha_nome.addStretch(1)
        texto_layout.addLayout(linha_nome)

        lbl_sub = QLabel(self._montar_sub_texto())
        lbl_sub.setObjectName("lbl_sub_equipe")
        lbl_sub.setFont(Fontes.texto_normal())
        self._header_lbl_sub = lbl_sub
        texto_layout.addWidget(lbl_sub)

        cl.addLayout(texto_layout, 1)
        stack.addWidget(conteudo)
        stack.setCurrentWidget(conteudo)
        conteudo.raise_()
        self._atualizar_estado_navegacao()
        return header

    def _montar_sub_texto(self) -> str:
        tier_map = {1: "\U0001f947 Top Team", 2: "\U0001f948 Competitiva",
                    3: "\U0001f949 Midfield", 4: "\U0001f4c9 Backmarker"}
        try:
            tier = int(self.equipe.get("tier", 3))
        except (TypeError, ValueError):
            tier = 3
        tier_txt = tier_map.get(tier, "—")
        cat = str(self.equipe.get("categoria", "") or "").strip()
        cat_txt = obter_nome_categoria(cat) if cat else ""
        partes = [tier_txt]
        if cat_txt:
            partes.append(cat_txt)
        return "  |  ".join(partes)

    def _atualizar_header_info(self) -> None:
        if isinstance(self._header_lbl_nome, QLabel):
            self._header_lbl_nome.setText(str(self.equipe.get("nome", "?") or "?"))
        if isinstance(self._header_lbl_sub, QLabel):
            self._header_lbl_sub.setText(self._montar_sub_texto())
        self._atualizar_estado_navegacao()

    def _gerar_textura_header(self, w: int, h: int) -> QPixmap:
        px = QPixmap(max(2, w), max(2, h))
        px.fill(QColor(self._tema.get("header_bg", "#0e1622")))
        painter = QPainter(px)
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        for x in range(-h, w + h, 14):
            painter.drawLine(x, 0, x + h, h)
        painter.setPen(QPen(QColor(0, 0, 0, 26), 1))
        for x in range(-h + 6, w + h, 14):
            painter.drawLine(x, 0, x + h, h)
        painter.end()
        return px

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _as_int(v, pad=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return pad

    def _aplicar_sombra(self, widget: QWidget) -> None:
        ef = QGraphicsDropShadowEffect(widget)
        ef.setBlurRadius(14)
        ef.setOffset(0, 1)
        ef.setColor(QColor(0, 0, 0, 60))
        widget.setGraphicsEffect(ef)

    def _criar_painel(self, titulo: str):
        painel = QFrame()
        painel.setObjectName("ficha_panel")
        lay = QVBoxLayout(painel)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)
        lbl = QLabel(titulo)
        lbl.setObjectName("titulo_secao")
        lbl.setFont(Fontes.titulo_pequeno())
        lay.addWidget(lbl)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {Cores.BORDA}; border: none;")
        lay.addWidget(sep)
        self._aplicar_sombra(painel)
        return painel, lay

    def _criar_bloco_stat(self, titulo: str, valor, cor=None, icone: str = "•") -> QWidget:
        bloco = QFrame()
        bloco.setObjectName("bloco_stat")
        lay = QVBoxLayout(bloco)
        lay.setContentsMargins(10, 7, 10, 8)
        lay.setSpacing(3)
        lbl_ic = QLabel(icone)
        lbl_ic.setObjectName("lbl_stat_icone")
        usa_emoji = any(ord(ch) >= 0x1F000 for ch in icone)
        if usa_emoji:
            lbl_ic.setFont(QFont("Segoe UI Emoji", 14))
        else:
            lbl_ic.setFont(QFont(Fontes.FAMILIA, 13, QFont.Bold))
        lbl_ic.setAlignment(Qt.AlignCenter)
        lbl_ic.setMinimumHeight(28)
        if cor:
            lbl_ic.setStyleSheet(f"color: {cor};")
        lay.addWidget(lbl_ic)
        lbl_val = QLabel(str(valor))
        lbl_val.setObjectName("lbl_stat_valor")
        fonte_v = QFont(Fontes.numero_medio())
        fonte_v.setBold(True)
        lbl_val.setFont(fonte_v)
        lbl_val.setAlignment(Qt.AlignCenter)
        if cor:
            lbl_val.setStyleSheet(f"color: {cor};")
        lay.addWidget(lbl_val)
        lbl_tit = QLabel(titulo)
        lbl_tit.setObjectName("lbl_stat_titulo")
        lbl_tit.setFont(Fontes.texto_pequeno())
        lbl_tit.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl_tit)
        self._aplicar_sombra(bloco)
        return bloco

    def _criar_grade_stats(self, stats: list, colunas: int = 3) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(8)
        for i, s in enumerate(stats):
            g.addWidget(
                self._criar_bloco_stat(s["titulo"], s["valor"], s.get("cor"), s.get("icone", "•")),
                i // colunas, i % colunas,
            )
        for c in range(colunas):
            g.setColumnStretch(c, 1)
        return w

    def _criar_barra_progresso(self, titulo: str, valor: int) -> QWidget:
        linha = QWidget()
        lay = QHBoxLayout(linha)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)
        lbl_t = QLabel(titulo)
        lbl_t.setFont(Fontes.texto_pequeno())
        lbl_t.setStyleSheet(f"color: {self._tema.get('text_secondary', Cores.TEXTO_SECONDARY)};")
        lbl_t.setFixedWidth(120)
        lay.addWidget(lbl_t)
        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(max(0, min(100, valor)))
        barra.setTextVisible(False)
        barra.setFixedHeight(11)
        barra.setStyleSheet(f"""
            QProgressBar {{ background-color: {self._tema.get("plot_bg", "#0f1825")};
                border: none; border-radius: 5px; }}
            QProgressBar::chunk {{ background-color: {self._cor_equipe}; border-radius: 5px; }}
        """)
        lay.addWidget(barra, 1)
        lbl_v = QLabel(str(valor))
        lbl_v.setFont(Fontes.texto_pequeno())
        lbl_v.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")
        lbl_v.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_v.setFixedWidth(36)
        lay.addWidget(lbl_v)
        return linha

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _build_tab_info(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema.get("border_hover", Cores.BORDA_HOVER)))
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        def _clamp_pct(valor: Any, padrao: int = 0) -> int:
            try:
                numero = int(round(float(valor)))
            except (TypeError, ValueError):
                numero = int(padrao)
            return max(0, min(100, numero))

        def _linha_info(chave: str, valor: str) -> QWidget:
            linha = QWidget()
            ll = QHBoxLayout(linha)
            ll.setContentsMargins(0, 2, 0, 2)
            ll.setSpacing(8)

            lbl_k = QLabel(chave)
            lbl_k.setFont(Fontes.texto_pequeno())
            lbl_k.setStyleSheet(f"color: {self._tema.get('text_secondary', Cores.TEXTO_SECONDARY)};")
            lbl_k.setFixedWidth(180)

            lbl_v = QLabel(valor)
            lbl_v.setWordWrap(True)
            lbl_v.setFont(Fontes.texto_normal())
            lbl_v.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")

            ll.addWidget(lbl_k)
            ll.addWidget(lbl_v, 1)
            return linha

        pan_perf, lay_perf = self._criar_painel("Performance")
        car_perf = _clamp_pct(self.equipe.get("car_performance", self.equipe.get("aero", 50)), 50)
        budget = _clamp_pct(self.equipe.get("budget", self.equipe.get("orcamento", 50)), 50)
        facilities = _clamp_pct(self.equipe.get("facilities", self.equipe.get("infraestrutura", 50)), 50)
        engineering = _clamp_pct(self.equipe.get("engineering_quality", self.equipe.get("pitcrew_skill", 50)), 50)
        reputacao = _clamp_pct(self.equipe.get("reputacao", 50), 50)

        lay_perf.addWidget(self._criar_barra_progresso("Car Performance", car_perf))
        lay_perf.addWidget(self._criar_barra_progresso("Budget", budget))
        lay_perf.addWidget(self._criar_barra_progresso("Facilities", facilities))
        lay_perf.addWidget(self._criar_barra_progresso("Engineering", engineering))
        lay_perf.addWidget(self._criar_barra_progresso("Reputacao", reputacao))

        try:
            morale_raw = float(self.equipe.get("morale", 1.0) or 1.0)
        except (TypeError, ValueError):
            morale_raw = 1.0
        morale_norm = morale_raw / 100.0 if morale_raw > 2.0 else morale_raw
        if morale_norm < 0.9:
            morale_txt = "Baixo"
        elif morale_norm > 1.1:
            morale_txt = "Alto"
        else:
            morale_txt = "Normal"
        lay_perf.addWidget(_linha_info("Morale", f"{morale_txt} ({morale_norm:.2f})"))
        lay.addWidget(pan_perf)

        pan_p, lay_p = self._criar_painel("Pilotos")
        pilotos_por_id = {
            str(p.get("id")): p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict)
        }
        hierarquia = self.equipe.get("hierarquia")
        if not isinstance(hierarquia, dict):
            hierarquia = {}

        n1_id = str(hierarquia.get("n1_id", self.equipe.get("piloto_numero_1")) or "")
        n2_id = str(hierarquia.get("n2_id", self.equipe.get("piloto_numero_2")) or "")
        p1_ref = pilotos_por_id.get(n1_id, {})
        p2_ref = pilotos_por_id.get(n2_id, {})

        nome_n1 = str(
            p1_ref.get("nome", self.equipe.get("piloto_1", "Sem piloto"))
            or "Sem piloto"
        ).strip()
        nome_n2 = str(
            p2_ref.get("nome", self.equipe.get("piloto_2", "Sem piloto"))
            or "Sem piloto"
        ).strip()
        skill_n1 = _clamp_pct(p1_ref.get("skill", 0), 0)
        skill_n2 = _clamp_pct(p2_ref.get("skill", 0), 0)

        status_hierarquia = str(hierarquia.get("status", "estavel") or "estavel").strip().lower()
        mapa_status = {
            "estavel": "Estavel",
            "tensao": "Tensao",
            "reavaliacao": "Reavaliacao",
            "invertido": "Invertido",
        }
        status_txt = mapa_status.get(status_hierarquia, "Estavel")

        lay_p.addWidget(_linha_info("N1", f"{nome_n1} (skill {skill_n1})"))
        lay_p.addWidget(_linha_info("N2", f"{nome_n2} (skill {skill_n2})"))
        lay_p.addWidget(_linha_info("Status hierarquia", status_txt))
        lay.addWidget(pan_p)

        pan_i, lay_i = self._criar_painel("Informacoes")
        categoria_id = str(self.equipe.get("categoria", self.equipe.get("categoria_id", "")) or "").strip()
        categoria_txt = obter_nome_categoria(categoria_id) if categoria_id else "-"
        marca = str(
            self.equipe.get("marca", self.equipe.get("carro_marca", self.equipe.get("carro", "-")))
            or "-"
        ).strip() or "-"
        temporadas_categoria = self._as_int(self.equipe.get("temporadas_na_categoria"), 0)

        equipes_cat = [
            equipe_ref
            for equipe_ref in self.banco.get("equipes", [])
            if isinstance(equipe_ref, dict)
            and bool(equipe_ref.get("ativa", True))
            and str(equipe_ref.get("categoria", equipe_ref.get("categoria_id", "")) or "").strip() == categoria_id
        ]
        total_equipes = max(1, len(equipes_cat))
        posicao_construtores = self._calcular_posicao_equipe()
        posicao_txt = f"{posicao_construtores}º / {total_equipes}" if posicao_construtores > 0 else "-"

        lay_i.addWidget(_linha_info("Categoria", categoria_txt))
        lay_i.addWidget(_linha_info("Carro/Marca", marca))
        lay_i.addWidget(_linha_info("Temporadas na categoria", str(temporadas_categoria)))
        lay_i.addWidget(_linha_info("Posicao construtores", posicao_txt))
        lay.addWidget(pan_i)

        pan_h, lay_h = self._criar_painel("Historico")
        historico = self._historico_equipe()
        if historico:
            for item in historico[:4]:
                ano = self._as_int(item.get("ano"), 0)
                pos = self._as_int(item.get("posicao"), 0)
                pts = self._as_int(item.get("pontos"), 0)
                if ano <= 0:
                    continue
                pos_txt = f"{pos}º construtores" if pos > 0 else "sem posicao"
                lbl = QLabel(f"{ano}: {categoria_txt} - {pos_txt} ({pts} pts)")
                lbl.setWordWrap(True)
                lbl.setFont(Fontes.texto_pequeno())
                lbl.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")
                lay_h.addWidget(lbl)
        else:
            texto_historico = self.equipe.get("historico", [])
            if isinstance(texto_historico, list) and texto_historico:
                for entrada in texto_historico[:4]:
                    lbl = QLabel(str(entrada))
                    lbl.setWordWrap(True)
                    lbl.setFont(Fontes.texto_pequeno())
                    lbl.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")
                    lay_h.addWidget(lbl)
            else:
                lay_h.addWidget(_linha_info("Registros", "Sem historico de construtores."))
        lay.addWidget(pan_h)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll
    # ── Helpers de dados históricos ─────────────────────────────────────────

    def _historico_equipe(self) -> list:
        """Retorna lista de dicts {ano, posicao, pontos, vitorias, podios} da equipe."""
        nome_eq = str(self.equipe.get("nome", "") or "").strip().casefold()
        cat_id  = str(self.equipe.get("categoria", "") or "").strip().casefold()
        hist_all = self.banco.get("historico_temporadas_completas", [])
        resultado = []
        for temp in hist_all:
            if not isinstance(temp, dict):
                continue
            if cat_id and str(temp.get("categoria_id", "") or "").strip().casefold() != cat_id:
                continue
            ano = self._as_int(temp.get("ano"), 0)
            for entrada in temp.get("classificacao", []):
                if not isinstance(entrada, dict):
                    continue
                eq_nome = str(entrada.get("equipe", "") or "").strip().casefold()
                if eq_nome == nome_eq:
                    resultado.append({
                        "ano"     : ano,
                        "posicao" : self._as_int(entrada.get("posicao"), 0),
                        "pontos"  : self._as_int(entrada.get("pontos"), 0),
                        "vitorias": self._as_int(entrada.get("vitorias"), 0),
                        "podios"  : self._as_int(entrada.get("podios"), 0),
                    })
                    break
        resultado.sort(key=lambda x: x["ano"], reverse=True)
        return resultado

    def _calcular_posicao_equipe(self) -> int:
        """Calcula a posição atual da equipe no campeonato de construtores."""
        nome_eq = str(self.equipe.get("nome", "") or "").strip().casefold()
        cat_id  = str(self.equipe.get("categoria", "") or "").strip().casefold()
        # Agrupa pontos por equipe na categoria
        pontos_por_equipe: dict[str, int] = {}
        for p in self.banco.get("pilotos", []):
            if p.get("aposentado"):
                continue
            if cat_id and str(p.get("categoria_atual", "") or "").strip().casefold() != cat_id:
                continue
            eq = str(p.get("equipe_nome", "") or "").strip().casefold()
            pts = self._as_int(p.get("pontos_temporada"), 0)
            pontos_por_equipe[eq] = pontos_por_equipe.get(eq, 0) + pts
        if not pontos_por_equipe:
            return 0
        minha_pts = pontos_por_equipe.get(nome_eq, self._as_int(self.equipe.get("pontos_temporada"), 0))
        acima = sum(1 for pts in pontos_por_equipe.values() if pts > minha_pts)
        return acima + 1

    def _pilotos_da_equipe(self) -> list:
        """Retorna os pilotos ativos que pertencem a esta equipe."""
        nome_eq = str(self.equipe.get("nome", "") or "").strip().casefold()
        cat_id  = str(self.equipe.get("categoria", "") or "").strip().casefold()
        resultado = []
        for p in self.banco.get("pilotos", []):
            if p.get("aposentado"):
                continue
            if cat_id and str(p.get("categoria_atual", "") or "").strip().casefold() != cat_id:
                continue
            if str(p.get("equipe_nome", "") or "").strip().casefold() == nome_eq:
                resultado.append(p)
        return resultado

    # ── Aba Temporada ─────────────────────────────────────────────────────────

    def _build_tab_temporada(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema.get("border_hover", Cores.BORDA_HOVER)))
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        ano = self.banco.get("ano_atual", 2024)
        rodada    = self._as_int(self.banco.get("rodada_atual"), 1)
        tot_rod   = self._as_int(self.banco.get("total_rodadas"), rodada)
        pts       = self._as_int(self.equipe.get("pontos_temporada"), 0)
        vit       = self._as_int(self.equipe.get("vitorias_temporada"), 0)
        pod       = self._as_int(self.equipe.get("podios_temporada"), 0)
        posicao   = self._calcular_posicao_equipe()

        # ── Cabeçalho: grade 4 cards ────────────────────────────────────────
        pan_topo, lay_topo = self._criar_painel(f"📅 Temporada {ano}  (Em andamento)")

        cor_pos = Cores.OURO if posicao == 1 else (Cores.PRATA if posicao == 2 else
                  Cores.BRONZE if posicao == 3 else None)
        pos_txt = f"{posicao}º" if posicao > 0 else "—"

        stats_topo = [
            {"titulo": "Posição",   "valor": pos_txt, "cor": cor_pos,            "icone": "🏆"},
            {"titulo": "Pontos",    "valor": pts,      "cor": Cores.ACCENT_PRIMARY, "icone": "✦"},
            {"titulo": "Vitórias",  "valor": vit,      "cor": Cores.OURO if vit > 0 else None, "icone": "🥇"},
            {"titulo": "Progresso", "valor": f"{rodada}/{tot_rod}", "cor": None,  "icone": "◎"},
        ]
        lay_topo.addWidget(self._criar_grade_stats(stats_topo, colunas=4))

        # sub-linha pódios
        lbl_pod = QLabel(f"Pódios nesta temporada:  {pod}")
        lbl_pod.setFont(Fontes.texto_pequeno())
        lbl_pod.setStyleSheet(f"color: {self._tema.get('text_secondary', Cores.TEXTO_SECONDARY)};")
        lay_topo.addWidget(lbl_pod)
        lay.addWidget(pan_topo)

        # ── Line-up de pilotos ───────────────────────────────────────────────
        pilotos = self._pilotos_da_equipe()
        if pilotos:
            pan_p, lay_p = self._criar_painel("👥 Line-up de Pilotos")
            grade_p = QWidget()
            g_lay   = QGridLayout(grade_p)
            g_lay.setContentsMargins(0, 0, 0, 0)
            g_lay.setHorizontalSpacing(10)
            g_lay.setVerticalSpacing(4)
            for col, p in enumerate(pilotos[:4]):
                nome_p = str(p.get("nome", "?") or "?").strip()
                pts_p  = self._as_int(p.get("pontos_temporada"), 0)
                vit_p  = self._as_int(p.get("vitorias_temporada"), 0)
                card_p = QFrame()
                card_p.setObjectName("bloco_stat")
                cl_p   = QVBoxLayout(card_p)
                cl_p.setContentsMargins(10, 8, 10, 8)
                cl_p.setSpacing(3)
                lbl_n = QLabel(nome_p)
                lbl_n.setFont(Fontes.texto_normal())
                lbl_n.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)}; font-weight: 700;")
                lbl_n.setAlignment(Qt.AlignCenter)
                cl_p.addWidget(lbl_n)
                lbl_pts_p = QLabel(f"{pts_p} pts  ·  {vit_p} vit")
                lbl_pts_p.setFont(Fontes.texto_pequeno())
                lbl_pts_p.setStyleSheet(f"color: {self._tema.get('text_secondary', Cores.TEXTO_SECONDARY)};")
                lbl_pts_p.setAlignment(Qt.AlignCenter)
                cl_p.addWidget(lbl_pts_p)
                self._aplicar_sombra(card_p)
                g_lay.addWidget(card_p, 0, col)
                g_lay.setColumnStretch(col, 1)
            lay_p.addWidget(grade_p)
            lay.addWidget(pan_p)

        # ── Forma recente (últimas corridas, via historico completo) ─────────
        # Pega resultados dos pilotos da equipe na temporada atual
        resultados_equipe: list = []
        for p in pilotos[:2]:
            res = list(p.get("resultados_temporada", []) or [])
            if res:
                resultados_equipe = res
                break
        if resultados_equipe:
            pan_r, lay_r = self._criar_painel("🏁 Forma Recente")
            ultimos = resultados_equipe[-8:]  # últimas 8 corridas
            linha_r = QHBoxLayout()
            linha_r.setSpacing(6)
            for res in ultimos:
                dnf = str(res).strip().casefold() == "dnf"
                pos_r = 0 if dnf else self._as_int(res, 99)
                if dnf:
                    cor_r, txt_r = "#ff4d4f", "DNF"
                elif pos_r == 1:
                    cor_r, txt_r = Cores.OURO, "P1"
                elif pos_r <= 3:
                    cor_r, txt_r = Cores.PRATA, f"P{pos_r}"
                elif pos_r <= 10:
                    cor_r, txt_r = Cores.VERDE, f"P{pos_r}"
                else:
                    cor_r, txt_r = Cores.TEXTO_MUTED, f"P{pos_r}"
                chip = QLabel(txt_r)
                chip.setFixedSize(42, 28)
                chip.setAlignment(Qt.AlignCenter)
                chip.setFont(QFont(Fontes.FAMILIA, 9, QFont.Bold))
                chip.setStyleSheet(f"""
                    QLabel {{
                        background-color: {self._tema.get('chip_bg','#101824')};
                        border: 1px solid {cor_r};
                        color: {cor_r};
                        border-radius: 4px;
                    }}
                """)
                linha_r.addWidget(chip)
            linha_r.addStretch(1)
            lay_r.addLayout(linha_r)
            lay.addWidget(pan_r)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Aba Histórico ─────────────────────────────────────────────────────────

    def _build_tab_historico(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_estilo_scroll_ficha(self._tema.get("border_hover", Cores.BORDA_HOVER)))
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(14)

        fund = str(self.equipe.get("ano_fundacao", "") or "").strip()
        titulo_hist = f"🏆 Histórico da Equipe{f'  (Desde {fund})' if fund else ''}"

        # ── Grade 4 cards ────────────────────────────────────────────────────
        pan_topo, lay_h = self._criar_painel(titulo_hist)
        titulos  = self._as_int(self.equipe.get("titulos_equipe"), 0)
        vit_eq   = self._as_int(self.equipe.get("vitorias_equipe"), 0)
        pod_eq   = self._as_int(self.equipe.get("podios_equipe"), 0)
        hist_eq  = self._historico_equipe()
        corridas  = len(hist_eq)  # 1 entrada por temporada; melhor que 0

        stats_hist = [
            {"titulo": "Títulos",  "valor": titulos,  "cor": Cores.OURO if titulos > 0 else None, "icone": "🏆"},
            {"titulo": "Vitórias", "valor": vit_eq,   "cor": None, "icone": "🥇"},
            {"titulo": "Pódios",   "valor": pod_eq,   "cor": None, "icone": "◆"},
            {"titulo": "Temporadas","valor": corridas, "cor": None, "icone": "📅"},
        ]
        lay_h.addWidget(self._criar_grade_stats(stats_hist, colunas=4))
        lay.addWidget(pan_topo)

        # ── Gráfico de posição histórica ──────────────────────────────────────
        if len(hist_eq) >= 2:
            pan_g, lay_g = self._criar_painel("📈 Posição no Campeonato ao Longo dos Anos")
            grafico = self._desenhar_grafico_posicao_equipe(hist_eq)
            lay_g.addWidget(grafico)
            lay.addWidget(pan_g)

        # ── Temporadas passadas (cards expansíveis) ────────────────────────
        if hist_eq:
            pan_s, lay_s = self._criar_painel("📋 Temporadas Passadas")
            for temp_h in hist_eq:
                lay_s.addWidget(self._criar_card_temporada_equipe(temp_h))
            lay.addWidget(pan_s)

        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    def _desenhar_grafico_posicao_equipe(self, hist: list) -> QWidget:
        """Mini gráfico de linha: posição no campeonato por ano."""
        from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont as QGFont
        from PySide6.QtWidgets import QSizePolicy

        dados = sorted(hist, key=lambda x: x["ano"])

        anos  = [d["ano"] for d in dados]
        posicoes = [d["posicao"] for d in dados]
        posicoes_validas = [p for p in posicoes if p > 0]
        pos_max = max(posicoes_validas) if posicoes_validas else 1
        pos_max = max(pos_max, 5)  # no mínimo 5 posições no eixo

        class GraficoWidget(QWidget):
            def __init__(self_, parent=None):
                super().__init__(parent)
                self_.setMinimumHeight(160)
                self_.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                self_._cor_linha = self._cor_equipe
                self_._cor_bg    = self._tema.get("plot_bg", "#0f1825")
                self_._cor_grade = self._tema.get("border", Cores.BORDA)
                self_._cor_txt   = self._tema.get("text_secondary", Cores.TEXTO_SECONDARY)

            def paintEvent(self_, event):
                painter = QPainter(self_)
                painter.setRenderHint(QPainter.Antialiasing)
                W, H = self_.width(), self_.height()
                mg_l, mg_r, mg_t, mg_b = 42, 14, 14, 28
                aw = max(1, W - mg_l - mg_r)
                ah = max(1, H - mg_t - mg_b)
                # Fundo
                painter.fillRect(0, 0, W, H, QColor(self_._cor_bg))
                # Grade
                painter.setPen(QPen(QColor(self_._cor_grade), 1))
                for i in range(5):
                    y = mg_t + int(i * ah / 4)
                    painter.drawLine(mg_l, y, W - mg_r, y)
                    pos_lbl = max(1, round(1 + i * (pos_max - 1) / 4))
                    painter.setPen(QPen(QColor(self_._cor_txt), 1))
                    painter.setFont(QGFont("Segoe UI", 7))
                    painter.drawText(2, y + 4, f"{pos_lbl}º")
                    painter.setPen(QPen(QColor(self_._cor_grade), 1))
                # Linha
                if len(dados) >= 2:
                    path = QPainterPath()
                    for i, (ano_p, pos_p) in enumerate(zip(anos, posicoes)):
                        if pos_p <= 0:
                            continue
                        x = mg_l + int(i * aw / max(1, len(anos) - 1))
                        y = mg_t + int((pos_p - 1) / max(1, pos_max - 1) * ah)
                        if path.elementCount() == 0:
                            path.moveTo(x, y)
                        else:
                            path.lineTo(x, y)
                    pen_ln = QPen(QColor(self_._cor_linha), 2)
                    painter.setPen(pen_ln)
                    painter.drawPath(path)
                # Pontos + labels
                for i, (ano_p, pos_p) in enumerate(zip(anos, posicoes)):
                    if pos_p <= 0:
                        continue
                    x = mg_l + int(i * aw / max(1, len(anos) - 1))
                    y = mg_t + int((pos_p - 1) / max(1, pos_max - 1) * ah)
                    painter.setBrush(QColor(self_._cor_linha))
                    painter.setPen(QPen(QColor(self_._cor_bg), 2))
                    painter.drawEllipse(x - 4, y - 4, 8, 8)
                    # label ano
                    painter.setPen(QPen(QColor(self_._cor_txt), 1))
                    painter.setFont(QGFont("Segoe UI", 7))
                    painter.drawText(x - 12, H - mg_b + 14, str(ano_p))
                painter.end()
        return GraficoWidget()

    def _criar_card_temporada_equipe(self, temp_h: dict) -> QWidget:
        """Card expansível de uma temporada passada (similar à ficha do piloto)."""
        ano    = self._as_int(temp_h.get("ano"), 0)
        pos    = self._as_int(temp_h.get("posicao"), 0)
        pts    = self._as_int(temp_h.get("pontos"), 0)
        vit    = self._as_int(temp_h.get("vitorias"), 0)
        pod    = self._as_int(temp_h.get("podios"), 0)

        card = QFrame()
        card.setObjectName("bloco_stat")
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(12, 10, 12, 10)
        card_lay.setSpacing(6)

        # ── Topo clicável ────
        topo_w = QWidget()
        topo_w.setCursor(Qt.PointingHandCursor)
        topo_l = QHBoxLayout(topo_w)
        topo_l.setContentsMargins(0, 0, 0, 0)
        topo_l.setSpacing(10)

        lbl_ano = QLabel(str(ano) if ano > 0 else "—")
        lbl_ano.setFont(QFont(Fontes.FAMILIA, 13, QFont.Bold))
        lbl_ano.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")
        topo_l.addWidget(lbl_ano)

        cor_pos = Cores.OURO if pos == 1 else (Cores.PRATA if pos == 2 else
                  Cores.BRONZE if pos == 3 else self._tema.get("text_secondary", Cores.TEXTO_SECONDARY))
        badge_pos = QLabel(f"P{pos}" if pos > 0 else "?")
        badge_pos.setAlignment(Qt.AlignCenter)
        badge_pos.setFixedSize(40, 24)
        badge_pos.setFont(QFont(Fontes.FAMILIA, 9, QFont.Bold))
        badge_pos.setStyleSheet(f"""
            QLabel {{
                background-color: {self._tema.get('chip_bg','#101824')};
                color: {cor_pos};
                border: 1px solid {cor_pos};
                border-radius: 4px;
            }}
        """)
        topo_l.addWidget(badge_pos)
        topo_l.addStretch(1)

        lbl_seta = QLabel("▼")
        lbl_seta.setFont(QFont(Fontes.FAMILIA, 7))
        lbl_seta.setStyleSheet(f"color: {Cores.TEXTO_MUTED};")
        topo_l.addWidget(lbl_seta)
        card_lay.addWidget(topo_w)

        # ── Stats rápidos (sempre visíveis) ─────
        linha_stats = QHBoxLayout()
        linha_stats.setSpacing(16)
        for lbl_txt, val in (("Pontos", pts), ("Vitórias", vit), ("Pódios", pod)):
            w_s = QWidget()
            wl  = QVBoxLayout(w_s)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(1)
            lbl_v = QLabel(str(val))
            lbl_v.setFont(QFont(Fontes.FAMILIA, 11, QFont.Bold))
            lbl_v.setStyleSheet(f"color: {self._tema.get('text_primary', Cores.TEXTO_PRIMARY)};")
            lbl_v.setAlignment(Qt.AlignCenter)
            lbl_t = QLabel(lbl_txt)
            lbl_t.setFont(Fontes.texto_pequeno())
            lbl_t.setStyleSheet(f"color: {self._tema.get('text_secondary', Cores.TEXTO_SECONDARY)};")
            lbl_t.setAlignment(Qt.AlignCenter)
            wl.addWidget(lbl_v)
            wl.addWidget(lbl_t)
            linha_stats.addWidget(w_s)
        linha_stats.addStretch(1)
        card_lay.addLayout(linha_stats)

        # ── Detalhes expandidos ─────────────────
        detalhe_w = QWidget()
        detalhe_w.setVisible(False)
        detalhe_l = QVBoxLayout(detalhe_w)
        detalhe_l.setContentsMargins(0, 6, 0, 0)
        detalhe_l.setSpacing(6)
        stats_exp = [
            {"titulo": "Pontos",   "valor": pts, "cor": Cores.ACCENT_PRIMARY, "icone": "✦"},
            {"titulo": "Vitórias", "valor": vit, "cor": Cores.OURO if vit > 0 else None, "icone": "🥇"},
            {"titulo": "Pódios",   "valor": pod, "cor": None, "icone": "◆"},
        ]
        detalhe_l.addWidget(self._criar_grade_stats(stats_exp, colunas=3))
        card_lay.addWidget(detalhe_w)

        def _toggle(_evt=None):
            aberto = detalhe_w.isVisible()
            detalhe_w.setVisible(not aberto)
            lbl_seta.setText("▲" if not aberto else "▼")
        topo_w.mousePressEvent = _toggle

        self._aplicar_sombra(card)
        return card

