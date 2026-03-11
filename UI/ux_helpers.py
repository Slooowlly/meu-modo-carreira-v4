"""iRacerApp - UX helpers.

Integrates animations and visual feedback with TelaCarreira.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QTabWidget, QWidget

from UI.animacoes import AnimationManager, StaggeredAnimation
from UI.efeitos import AnimatedCounter, HoverEffect
from UI.feedback import LoadingOverlay, ProgressIndicator, SuccessCheckmark, Toast
from UI.transicoes import AnimatedStackedWidget, ContentTransition, TransitionType


class UXMixin:
    """Adds reusable UX helpers to TelaCarreira."""

    def _setup_ux(self):
        """Initialize UX components after UI widgets exist."""
        central = None
        getter = getattr(self, "centralWidget", None)
        if callable(getter):
            central = getter()
            if central is None and hasattr(self, "setCentralWidget"):
                central = QWidget(self)
                self.setCentralWidget(central)
        elif isinstance(self, QWidget):
            central = self

        if central is None:
            central = QWidget()

        self._loading_overlay = LoadingOverlay(central)
        self._ux_initialized = True
        self.cards_estatisticas = []

        if hasattr(self, "stacked_widget"):
            self._setup_animated_navigation()

    def _is_ux_ready(self) -> bool:
        """Whether UX components were initialized."""
        return bool(getattr(self, "_ux_initialized", False))

    def _setup_animated_navigation(self):
        """Hook for future stacked-widget navigation setup."""

    # ================================================================== #
    #                         TOASTS / NOTIFICATIONS                     #
    # ================================================================== #

    def mostrar_toast_sucesso(self, mensagem: str, duracao: int = 3000):
        """Show success toast."""
        if not self._is_ux_ready():
            print(f"[Sucesso] {mensagem}")
            return
        Toast.success(self, mensagem, duration=duracao)

    def mostrar_toast_erro(self, mensagem: str, duracao: int = 4000):
        """Show error toast."""
        if not self._is_ux_ready():
            print(f"[Erro] {mensagem}")
            return
        Toast.error(self, mensagem, duration=duracao)

    def mostrar_toast_aviso(self, mensagem: str, duracao: int = 3500):
        """Show warning toast."""
        if not self._is_ux_ready():
            print(f"[Aviso] {mensagem}")
            return
        Toast.warning(self, mensagem, duration=duracao)

    def mostrar_toast_info(self, mensagem: str, duracao: int = 3000):
        """Show info toast."""
        if not self._is_ux_ready():
            print(f"[Info] {mensagem}")
            return
        Toast.info(self, mensagem, duration=duracao)

    # ================================================================== #
    #                         LOADING STATES                             #
    # ================================================================== #

    def mostrar_loading(self, mensagem: str = "Carregando..."):
        """Show global loading overlay."""
        if not self._is_ux_ready():
            return
        overlay = getattr(self, "_loading_overlay", None)
        if overlay is not None:
            overlay.show_loading(mensagem)

    def esconder_loading(self):
        """Hide global loading overlay."""
        if not self._is_ux_ready():
            return
        overlay = getattr(self, "_loading_overlay", None)
        if overlay is not None:
            overlay.hide_loading()

    def executar_com_loading(
        self,
        operacao: Callable,
        mensagem: str = "Processando...",
        callback_sucesso: Callable | None = None,
        callback_erro: Callable | None = None,
    ):
        """Run an operation wrapped by loading feedback."""
        self.mostrar_loading(mensagem)

        def executar():
            try:
                resultado = operacao()
                self.esconder_loading()
                if callback_sucesso:
                    if resultado is None:
                        callback_sucesso()
                    else:
                        callback_sucesso(resultado)
            except Exception as erro:  # noqa: BLE001 - bubble to UX callback
                self.esconder_loading()
                if callback_erro:
                    callback_erro(erro)
                else:
                    self.mostrar_toast_erro(f"Erro: {erro}")

        QTimer.singleShot(50, executar)

    # ================================================================== #
    #                         ENTRY ANIMATIONS                           #
    # ================================================================== #

    def animar_entrada_cards(self, cards: List[QWidget], delay: int = 50):
        """Animate a list of cards in sequence."""
        if not cards:
            return
        StaggeredAnimation.slide_in_sequence(cards, direction="up", delay=delay)

    def animar_entrada_pagina(self, pagina: QWidget):
        """Animate page fade-in."""
        if pagina:
            AnimationManager.fade_in(pagina, duration=250)

    def animar_atualizacao(self, widget: QWidget, callback: Callable):
        """Animate content refresh (fade out -> update -> fade in)."""
        if widget:
            ContentTransition.refresh(widget, callback)

    # ================================================================== #
    #                         ACTION FEEDBACK                            #
    # ================================================================== #

    def mostrar_sucesso_animado(self):
        """Show animated success checkmark."""
        if self._is_ux_ready():
            SuccessCheckmark.show_success(self)

    def destacar_widget(self, widget: QWidget, cor: str = "#3498db"):
        """Highlight a widget with glow."""
        if not widget:
            return
        from PySide6.QtGui import QColor

        AnimationManager.highlight_glow(widget, QColor(cor), duration=1500, loops=2)

    def shake_erro(self, widget: QWidget):
        """Shake a widget to indicate error."""
        if widget:
            AnimationManager.shake(widget, duration=400, intensity=8)

    def pulsar_widget(self, widget: QWidget):
        """Pulse a widget for emphasis."""
        if widget:
            AnimationManager.pulse(widget, duration=400, loops=2)

    # ================================================================== #
    #                         TAB/PAGE TRANSITIONS                       #
    # ================================================================== #

    def transicao_para_aba(self, indice: int, tipo: str = "fade"):
        """Switch page/tab without fade animation."""
        if hasattr(self, "stacked_widget") and isinstance(self.stacked_widget, AnimatedStackedWidget):
            transition_map = {
                "fade": TransitionType.FADE,
                "slide_left": TransitionType.SLIDE_LEFT,
                "slide_right": TransitionType.SLIDE_RIGHT,
                "slide_up": TransitionType.SLIDE_UP,
                "slide_down": TransitionType.SLIDE_DOWN,
            }
            transition = transition_map.get(tipo, TransitionType.FADE)
            self.stacked_widget.set_transition(transition)
            self.stacked_widget.slide_to_index(indice)
            return

        tab_widget = self._encontrar_tab_widget()
        if tab_widget is None or indice < 0 or indice >= tab_widget.count():
            return

        if tab_widget.currentIndex() == indice:
            return

        tab_widget.setCurrentIndex(indice)

    def _encontrar_tab_widget(self) -> Optional[QTabWidget]:
        """Locate the main tab widget."""
        for attr in ("tabs", "tab_widget", "tab_principal", "abas"):
            if hasattr(self, attr):
                widget = getattr(self, attr)
                if isinstance(widget, QTabWidget):
                    return widget

        central = None
        getter = getattr(self, "centralWidget", None)
        if callable(getter):
            central = getter()
        elif isinstance(self, QWidget):
            central = self

        if central is None:
            return None

        encontrados = central.findChildren(QTabWidget)
        return encontrados[0] if encontrados else None

    # ================================================================== #
    #                         HOVER EFFECTS                              #
    # ================================================================== #

    def aplicar_hover_cards(self, cards: List[QWidget]):
        """Apply hover effect to cards."""
        for card in cards:
            if card:
                HoverEffect.apply(card, scale=1.02, shadow=True, lift=3)

    def aplicar_hover_botoes(self, botoes: List[QWidget]):
        """Apply hover effect to buttons."""
        for botao in botoes:
            if botao:
                HoverEffect.apply(botao, scale=1.0, shadow=True, lift=2)

    def registrar_cards_dashboard(self, cards: List[QWidget]):
        """Register cards used by dashboard entry animation."""
        self.cards_estatisticas = cards or []


class SimulacaoUXMixin:
    """UX helpers specific to race simulation."""

    def _criar_progresso_simulacao(self) -> ProgressIndicator:
        """Create centered progress indicator for race simulation."""
        progress = ProgressIndicator(
            self,
            message="Preparando simulacao...",
            show_percentage=True,
        )
        progress.setFixedWidth(350)

        x = (self.width() - progress.width()) // 2
        y = (self.height() - progress.height()) // 2
        progress.move(x, y)
        return progress

    def simular_com_progresso(
        self,
        etapas: List[tuple],
        on_complete: Callable | None = None,
    ):
        """Run simulation stages with visible progress."""
        progress = self._criar_progresso_simulacao()
        progress.show()
        progress.raise_()

        total_peso = max(1, sum(etapa[2] for etapa in etapas))
        progresso_atual = [0]

        def executar_etapa(indice: int):
            if indice >= len(etapas):
                progress.hide()
                progress.deleteLater()
                if on_complete:
                    on_complete()
                return

            mensagem, callback, peso = etapas[indice]
            progress.set_message(mensagem)

            def processar():
                try:
                    callback()
                except Exception as erro:  # noqa: BLE001
                    print(f"Erro na etapa {indice}: {erro}")

                progresso_atual[0] += peso
                percentual = int((progresso_atual[0] / total_peso) * 100)
                progress.set_progress(percentual)
                QTimer.singleShot(100, lambda: executar_etapa(indice + 1))

            QTimer.singleShot(50, processar)

        executar_etapa(0)

    def mostrar_resultado_corrida_animado(self, resultado: dict):
        """Show animated race result feedback."""
        if hasattr(self, "mostrar_sucesso_animado"):
            self.mostrar_sucesso_animado()

        posicao_raw = resultado.get("posicao", 99)
        try:
            posicao = int(posicao_raw)
        except (TypeError, ValueError):
            posicao = 99

        piloto = str(resultado.get("piloto", "Piloto"))
        if posicao <= 3:
            self.mostrar_toast_sucesso(f"{piloto} terminou em P{posicao}!")
        elif posicao <= 10:
            self.mostrar_toast_info(f"{piloto} terminou em P{posicao}")
        else:
            self.mostrar_toast_aviso(f"{piloto} terminou em P{posicao}")

        if hasattr(self, "_atualizar_tudo"):
            QTimer.singleShot(800, lambda: self._atualizar_tudo(animar=True))


class DashboardUXMixin:
    """UX helpers specific to dashboard presentation."""

    def _animar_entrada_dashboard(self):
        """Animate dashboard cards when explicitly registered."""
        if not getattr(self, "_ux_initialized", False):
            return

        cards = list(getattr(self, "cards_estatisticas", []) or [])
        if not cards:
            return

        ativos = [card for card in cards if card and card.isVisible()]
        if not ativos:
            return
        QTimer.singleShot(
            60,
            lambda: StaggeredAnimation.fade_in_sequence(ativos, delay=40, duration=140),
        )

    def _coletar_cards_dashboard(self) -> List[QWidget]:
        """Try to discover dashboard cards using simple heuristics."""
        base_widget = None
        tabs = getattr(self, "tabs", None)
        if isinstance(tabs, QTabWidget):
            base_widget = tabs.currentWidget()

        if base_widget is None:
            base_widget = self.centralWidget()

        if base_widget is None:
            return []

        cards: list[QWidget] = []
        for widget in base_widget.findChildren(QWidget):
            if not widget.isVisible():
                continue
            cls = widget.__class__.__name__.lower()
            obj = widget.objectName().lower()
            if "card" in cls or "card" in obj:
                cards.append(widget)
            elif obj and any(token in obj for token in ("stat", "resumo", "painel")):
                cards.append(widget)

        return cards[:12]

    def _animar_cards_sequencia(self, cards: List[QWidget]):
        """Animate cards one by one with small staggering."""
        for indice, card in enumerate(cards):
            if card:
                QTimer.singleShot(indice * 80, lambda c=card: self._pop_in_card(c))

    def _pop_in_card(self, card: QWidget):
        """Pop-in animation for a single card."""
        card.show()
        AnimationManager.pop_in(card, duration=300)

    def atualizar_estatistica_animada(
        self,
        label: QWidget,
        novo_valor: int,
        prefixo: str = "",
        sufixo: str = "",
    ):
        """Update stat value with smooth feedback."""
        if isinstance(label, AnimatedCounter):
            label.animate_to(novo_valor)
            return

        if hasattr(label, "setText"):
            def atualizar():
                texto = f"{prefixo}{novo_valor:,}{sufixo}".replace(",", ".")
                label.setText(texto)

            ContentTransition.refresh(label, atualizar, duration=150)

    def mostrar_notificacao_mercado(self, mensagem: str, tipo: str = "info"):
        """Show market-related notification with icon prefix."""
        icones = {
            "contratacao": "[OK]",
            "renovacao": "[RNV]",
            "saida": "[OUT]",
            "rumor": "[RMR]",
            "transferencia": "[TRF]",
        }
        prefixo = icones.get(tipo, "[INF]")
        self.mostrar_toast_info(f"{prefixo} {mensagem}", duracao=4000)
