"""
iRacerApp - Sistema de Transições
Transições suaves entre páginas e estados
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QStackedWidget, QGraphicsOpacityEffect,
    QVBoxLayout, QFrame
)
from PySide6.QtCore import (
    QPropertyAnimation, QParallelAnimationGroup,
    QSequentialAnimationGroup, QEasingCurve, QPoint,
    QTimer, Signal, QObject
)
from PySide6.QtGui import QColor
from enum import Enum
from typing import Optional, Callable


class TransitionType(Enum):
    """Tipos de transição disponíveis."""
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    FLIP = "flip"


class AnimatedStackedWidget(QStackedWidget):
    """
    QStackedWidget com transições animadas entre páginas.
    
    Uso:
        stack = AnimatedStackedWidget()
        stack.addWidget(page1)
        stack.addWidget(page2)
        stack.set_transition(TransitionType.SLIDE_LEFT)
        stack.slide_to_index(1)  # Transição animada para página 2
    """
    
    transition_started = Signal()
    transition_finished = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.transition_type = TransitionType.FADE
        self.duration = 300
        self.easing = QEasingCurve.Type.OutCubic
        
        self._is_transitioning = False
        self._animation_group = None
    
    def set_transition(
        self,
        transition_type: TransitionType,
        duration: int = 300,
        easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    ):
        """Configura o tipo de transição."""
        self.transition_type = transition_type
        self.duration = duration
        self.easing = easing
    
    def slide_to_index(self, index: int):
        """Transiciona para o índice especificado com animação."""
        if self._is_transitioning:
            return
        
        if index == self.currentIndex():
            return
        
        if index < 0 or index >= self.count():
            return
        
        self._is_transitioning = True
        self.transition_started.emit()
        
        current_widget = self.currentWidget()
        next_widget = self.widget(index)
        
        # Preparar widgets
        next_widget.setGeometry(self.geometry())
        
        if self.transition_type == TransitionType.FADE:
            self._fade_transition(current_widget, next_widget, index)
        elif self.transition_type in [TransitionType.SLIDE_LEFT, TransitionType.SLIDE_RIGHT]:
            self._slide_horizontal(current_widget, next_widget, index)
        elif self.transition_type in [TransitionType.SLIDE_UP, TransitionType.SLIDE_DOWN]:
            self._slide_vertical(current_widget, next_widget, index)
        else:
            self._fade_transition(current_widget, next_widget, index)
    
    def _fade_transition(self, current: QWidget, next_widget: QWidget, index: int):
        """Transição de fade."""
        # Efeitos de opacidade
        current_effect = QGraphicsOpacityEffect(current)
        current.setGraphicsEffect(current_effect)
        
        next_effect = QGraphicsOpacityEffect(next_widget)
        next_widget.setGraphicsEffect(next_effect)
        next_effect.setOpacity(0)
        
        # Mostrar próximo widget
        next_widget.show()
        next_widget.raise_()
        
        # Grupo de animações
        self._animation_group = QParallelAnimationGroup()
        
        # Fade out current
        fade_out = QPropertyAnimation(current_effect, b"opacity")
        fade_out.setDuration(self.duration)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(self.easing)
        self._animation_group.addAnimation(fade_out)
        
        # Fade in next
        fade_in = QPropertyAnimation(next_effect, b"opacity")
        fade_in.setDuration(self.duration)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(self.easing)
        self._animation_group.addAnimation(fade_in)
        
        self._animation_group.finished.connect(
            lambda: self._on_transition_finished(index, current, next_widget)
        )
        self._animation_group.start()
    
    def _slide_horizontal(self, current: QWidget, next_widget: QWidget, index: int):
        """Transição de slide horizontal."""
        width = self.width()
        
        # Direção baseada no índice ou tipo de transição
        if self.transition_type == TransitionType.SLIDE_LEFT:
            direction = -1
        else:
            direction = 1
        
        # Posições
        current_start = current.pos()
        current_end = QPoint(current_start.x() + (width * direction), current_start.y())
        
        next_start = QPoint(current_start.x() - (width * direction), current_start.y())
        next_end = current_start
        
        next_widget.move(next_start)
        next_widget.show()
        next_widget.raise_()
        
        # Animações
        self._animation_group = QParallelAnimationGroup()
        
        anim_current = QPropertyAnimation(current, b"pos")
        anim_current.setDuration(self.duration)
        anim_current.setStartValue(current_start)
        anim_current.setEndValue(current_end)
        anim_current.setEasingCurve(self.easing)
        self._animation_group.addAnimation(anim_current)
        
        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(self.duration)
        anim_next.setStartValue(next_start)
        anim_next.setEndValue(next_end)
        anim_next.setEasingCurve(self.easing)
        self._animation_group.addAnimation(anim_next)
        
        self._animation_group.finished.connect(
            lambda: self._on_transition_finished(index, current, next_widget)
        )
        self._animation_group.start()
    
    def _slide_vertical(self, current: QWidget, next_widget: QWidget, index: int):
        """Transição de slide vertical."""
        height = self.height()
        
        if self.transition_type == TransitionType.SLIDE_UP:
            direction = -1
        else:
            direction = 1
        
        current_start = current.pos()
        current_end = QPoint(current_start.x(), current_start.y() + (height * direction))
        
        next_start = QPoint(current_start.x(), current_start.y() - (height * direction))
        next_end = current_start
        
        next_widget.move(next_start)
        next_widget.show()
        next_widget.raise_()
        
        self._animation_group = QParallelAnimationGroup()
        
        anim_current = QPropertyAnimation(current, b"pos")
        anim_current.setDuration(self.duration)
        anim_current.setStartValue(current_start)
        anim_current.setEndValue(current_end)
        anim_current.setEasingCurve(self.easing)
        self._animation_group.addAnimation(anim_current)
        
        anim_next = QPropertyAnimation(next_widget, b"pos")
        anim_next.setDuration(self.duration)
        anim_next.setStartValue(next_start)
        anim_next.setEndValue(next_end)
        anim_next.setEasingCurve(self.easing)
        self._animation_group.addAnimation(anim_next)
        
        self._animation_group.finished.connect(
            lambda: self._on_transition_finished(index, current, next_widget)
        )
        self._animation_group.start()
    
    def _on_transition_finished(self, index: int, old_widget: QWidget, new_widget: QWidget):
        """Callback ao finalizar transição."""
        # Limpar efeitos
        old_widget.setGraphicsEffect(None)
        new_widget.setGraphicsEffect(None)
        
        # Definir índice atual
        self.setCurrentIndex(index)
        
        # Reset posições
        old_widget.move(0, 0)
        new_widget.move(0, 0)
        
        self._is_transitioning = False
        self.transition_finished.emit()
    
    def slide_to_next(self):
        """Vai para a próxima página."""
        next_index = (self.currentIndex() + 1) % self.count()
        self.slide_to_index(next_index)
    
    def slide_to_previous(self):
        """Vai para a página anterior."""
        prev_index = (self.currentIndex() - 1) % self.count()
        self.slide_to_index(prev_index)


class PageTransitionManager:
    """
    Gerenciador de transições para uso geral.
    
    Uso:
        manager = PageTransitionManager(stacked_widget)
        manager.go_to("dashboard", TransitionType.SLIDE_LEFT)
    """
    
    def __init__(self, stacked_widget: QStackedWidget):
        self.stack = stacked_widget
        self.pages = {}
        self.default_transition = TransitionType.FADE
        self.duration = 300
    
    def register_page(self, name: str, widget: QWidget):
        """Registra uma página com um nome."""
        index = self.stack.addWidget(widget)
        self.pages[name] = index
    
    def go_to(
        self,
        page_name: str,
        transition: TransitionType = None,
        on_finished: Callable = None
    ):
        """Navega para uma página registrada."""
        if page_name not in self.pages:
            return False
        
        transition = transition or self.default_transition
        index = self.pages[page_name]
        
        if isinstance(self.stack, AnimatedStackedWidget):
            self.stack.set_transition(transition, self.duration)
            if on_finished:
                self.stack.transition_finished.connect(on_finished)
            self.stack.slide_to_index(index)
        else:
            self.stack.setCurrentIndex(index)
            if on_finished:
                on_finished()
        
        return True
    
    def set_default_transition(self, transition: TransitionType, duration: int = 300):
        """Define a transição padrão."""
        self.default_transition = transition
        self.duration = duration


class ContentTransition:
    """
    Transição de conteúdo dentro de um mesmo container.
    Útil para atualizar dados com animação.
    
    Uso:
        ContentTransition.refresh(my_widget, lambda: update_data())
    """
    
    @staticmethod
    def refresh(
        widget: QWidget,
        update_callback: Callable,
        duration: int = 200
    ):
        """
        Faz fade out, executa callback, faz fade in.
        
        Args:
            widget: Widget a ser atualizado
            update_callback: Função que atualiza o conteúdo
            duration: Duração de cada fase da animação
        """
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        # Fade out
        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(duration)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        def on_fade_out_finished():
            # Executar atualização
            update_callback()
            
            # Fade in
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(duration)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InQuad)
            fade_in.finished.connect(lambda: widget.setGraphicsEffect(None))
            fade_in.start()
            
            # Manter referência
            widget._fade_in_anim = fade_in
        
        fade_out.finished.connect(on_fade_out_finished)
        fade_out.start()
        
        # Manter referência
        widget._fade_out_anim = fade_out
    
    @staticmethod
    def swap(
        old_widget: QWidget,
        new_widget: QWidget,
        parent_layout,
        duration: int = 250
    ):
        """
        Troca um widget por outro com animação.
        
        Args:
            old_widget: Widget atual a ser removido
            new_widget: Novo widget a ser inserido
            parent_layout: Layout pai onde fazer a troca
            duration: Duração da animação
        """
        # Setup novo widget invisível
        new_effect = QGraphicsOpacityEffect(new_widget)
        new_widget.setGraphicsEffect(new_effect)
        new_effect.setOpacity(0.0)
        
        # Efeito no widget antigo
        old_effect = QGraphicsOpacityEffect(old_widget)
        old_widget.setGraphicsEffect(old_effect)
        
        # Encontrar índice do widget antigo
        index = parent_layout.indexOf(old_widget)
        
        # Inserir novo widget na mesma posição
        parent_layout.insertWidget(index, new_widget)
        new_widget.show()
        
        # Animações paralelas
        group = QParallelAnimationGroup()
        
        # Fade out old
        fade_out = QPropertyAnimation(old_effect, b"opacity")
        fade_out.setDuration(duration)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutQuad)
        group.addAnimation(fade_out)
        
        # Fade in new
        fade_in = QPropertyAnimation(new_effect, b"opacity")
        fade_in.setDuration(duration)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InQuad)
        group.addAnimation(fade_in)
        
        def cleanup():
            old_widget.hide()
            old_widget.setGraphicsEffect(None)
            new_widget.setGraphicsEffect(None)
            parent_layout.removeWidget(old_widget)
        
        group.finished.connect(cleanup)
        group.start()
        
        # Manter referência
        new_widget._swap_animation = group


class StateTransition:
    """
    Transições visuais para mudanças de estado.
    Ex: loading → loaded, error → success
    
    Uso:
        StateTransition.to_loading(widget)
        # ... carrega dados ...
        StateTransition.to_loaded(widget)
    """
    
    @staticmethod
    def to_loading(widget: QWidget, opacity: float = 0.5):
        """Transiciona widget para estado de carregamento."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(1.0)
        anim.setEndValue(opacity)
        anim.start()
        
        widget._loading_anim = anim
        widget._loading_effect = effect
        widget.setEnabled(False)
    
    @staticmethod
    def to_loaded(widget: QWidget):
        """Transiciona widget de volta ao estado normal."""
        if hasattr(widget, '_loading_effect'):
            anim = QPropertyAnimation(widget._loading_effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(widget._loading_effect.opacity())
            anim.setEndValue(1.0)
            anim.finished.connect(lambda: widget.setGraphicsEffect(None))
            anim.start()
            
            widget._loaded_anim = anim
        
        widget.setEnabled(True)
    
    @staticmethod
    def flash_success(widget: QWidget, color: str = "#2ecc71"):
        """Flash verde indicando sucesso."""
        original_style = widget.styleSheet()
        
        widget.setStyleSheet(f"{original_style} border: 2px solid {color};")
        
        QTimer.singleShot(150, lambda: widget.setStyleSheet(original_style))
        QTimer.singleShot(300, lambda: widget.setStyleSheet(f"{original_style} border: 2px solid {color};"))
        QTimer.singleShot(450, lambda: widget.setStyleSheet(original_style))
    
    @staticmethod
    def flash_error(widget: QWidget, color: str = "#e74c3c"):
        """Flash vermelho indicando erro."""
        original_style = widget.styleSheet()
        
        widget.setStyleSheet(f"{original_style} border: 2px solid {color};")
        
        QTimer.singleShot(100, lambda: widget.setStyleSheet(original_style))
        QTimer.singleShot(200, lambda: widget.setStyleSheet(f"{original_style} border: 2px solid {color};"))
        QTimer.singleShot(300, lambda: widget.setStyleSheet(original_style))
        QTimer.singleShot(400, lambda: widget.setStyleSheet(f"{original_style} border: 2px solid {color};"))
        QTimer.singleShot(500, lambda: widget.setStyleSheet(original_style))


class CollapseTransition:
    """
    Transição de colapso/expansão para painéis.
    
    Uso:
        CollapseTransition.collapse(panel)
        CollapseTransition.expand(panel, target_height=200)
    """
    
    @staticmethod
    def collapse(
        widget: QWidget,
        duration: int = 300,
        on_finished: Callable = None
    ):
        """Colapsa o widget (altura → 0)."""
        original_height = widget.height()
        widget._original_height = original_height
        
        anim = QPropertyAnimation(widget, b"maximumHeight")
        anim.setDuration(duration)
        anim.setStartValue(original_height)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        if on_finished:
            anim.finished.connect(on_finished)
        
        anim.finished.connect(widget.hide)
        anim.start()
        
        widget._collapse_anim = anim
    
    @staticmethod
    def expand(
        widget: QWidget,
        target_height: int = None,
        duration: int = 300,
        on_finished: Callable = None
    ):
        """Expande o widget."""
        if target_height is None:
            target_height = getattr(widget, '_original_height', 100)
        
        widget.setMaximumHeight(0)
        widget.show()
        
        anim = QPropertyAnimation(widget, b"maximumHeight")
        anim.setDuration(duration)
        anim.setStartValue(0)
        anim.setEndValue(target_height)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        def reset_max():
            widget.setMaximumHeight(16777215)  # Qt default max
            if on_finished:
                on_finished()
        
        anim.finished.connect(reset_max)
        anim.start()
        
        widget._expand_anim = anim
    
    @staticmethod
    def toggle(widget: QWidget, duration: int = 300):
        """Alterna entre colapsado e expandido."""
        if widget.isVisible() and widget.height() > 0:
            CollapseTransition.collapse(widget, duration)
        else:
            CollapseTransition.expand(widget, duration=duration)
