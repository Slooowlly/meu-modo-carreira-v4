"""
iRacerApp - Sistema de Animações
Animações reutilizáveis para widgets PySide6
"""

from __future__ import annotations

from PySide6.QtCore import (
    QPropertyAnimation, QSequentialAnimationGroup, QParallelAnimationGroup,
    QEasingCurve, Property, QObject, Signal, QPoint, QRect, QSize,
    QAbstractAnimation, QTimer, QPointF
)
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor
from typing import Optional, Callable
from enum import Enum


class AnimationType(Enum):
    """Tipos de animação disponíveis."""
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    BOUNCE = "bounce"
    SHAKE = "shake"
    PULSE = "pulse"
    GLOW = "glow"


class AnimationManager(QObject):
    """
    Gerenciador central de animações do iRacerApp.
    Uso: AnimationManager.fade_in(widget, duration=300)
    """
    
    # Duração padrão das animações (ms)
    DURATION_FAST = 150
    DURATION_NORMAL = 300
    DURATION_SLOW = 500
    
    # Curvas de easing padrão
    EASE_DEFAULT = QEasingCurve.Type.OutCubic
    EASE_BOUNCE = QEasingCurve.Type.OutBounce
    EASE_ELASTIC = QEasingCurve.Type.OutElastic
    EASE_SMOOTH = QEasingCurve.Type.InOutQuad
    
    # Cache de animações ativas (evita garbage collection)
    _active_animations: dict = {}
    
    @classmethod
    def _store_animation(cls, widget: QWidget, animation: QAbstractAnimation):
        """Armazena animação para evitar garbage collection."""
        widget_id = id(widget)
        cls._active_animations[widget_id] = animation
        animation.finished.connect(lambda: cls._cleanup_animation(widget_id))
    
    @classmethod
    def _cleanup_animation(cls, widget_id: int):
        """Remove animação finalizada do cache."""
        cls._active_animations.pop(widget_id, None)
    
    # ================================================================== #
    #                          FADE ANIMATIONS                            #
    # ================================================================== #
    
    @classmethod
    def fade_in(
        cls,
        widget: QWidget,
        duration: int = None,
        start_opacity: float = 0.0,
        end_opacity: float = 1.0,
        on_finished: Callable = None
    ) -> QPropertyAnimation:
        """
        Anima o widget de transparente para visível.
        
        Args:
            widget: Widget alvo
            duration: Duração em ms
            start_opacity: Opacidade inicial (0.0 a 1.0)
            end_opacity: Opacidade final (0.0 a 1.0)
            on_finished: Callback ao finalizar
        """
        duration = duration or cls.DURATION_NORMAL
        
        # Criar efeito de opacidade se não existir
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        effect.setOpacity(start_opacity)
        widget.show()
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(start_opacity)
        animation.setEndValue(end_opacity)
        animation.setEasingCurve(cls.EASE_DEFAULT)
        
        if on_finished:
            animation.finished.connect(on_finished)
        
        cls._store_animation(widget, animation)
        animation.start()
        
        return animation
    
    @classmethod
    def fade_out(
        cls,
        widget: QWidget,
        duration: int = None,
        hide_after: bool = True,
        on_finished: Callable = None
    ) -> QPropertyAnimation:
        """
        Anima o widget de visível para transparente.
        
        Args:
            widget: Widget alvo
            duration: Duração em ms
            hide_after: Esconde o widget após animação
            on_finished: Callback ao finalizar
        """
        duration = duration or cls.DURATION_NORMAL
        
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        
        effect.setOpacity(1.0)
        
        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(duration)
        animation.setStartValue(1.0)
        animation.setEndValue(0.0)
        animation.setEasingCurve(cls.EASE_DEFAULT)
        
        def _on_finished():
            if hide_after:
                widget.hide()
            if on_finished:
                on_finished()
        
        animation.finished.connect(_on_finished)
        cls._store_animation(widget, animation)
        animation.start()
        
        return animation
    
    @classmethod
    def crossfade(
        cls,
        widget_out: QWidget,
        widget_in: QWidget,
        duration: int = None
    ):
        """Fade out de um widget enquanto fade in de outro."""
        duration = duration or cls.DURATION_NORMAL
        
        group = QParallelAnimationGroup()
        
        # Fade out
        effect_out = QGraphicsOpacityEffect(widget_out)
        widget_out.setGraphicsEffect(effect_out)
        anim_out = QPropertyAnimation(effect_out, b"opacity")
        anim_out.setDuration(duration)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)
        group.addAnimation(anim_out)
        
        # Fade in
        effect_in = QGraphicsOpacityEffect(widget_in)
        widget_in.setGraphicsEffect(effect_in)
        effect_in.setOpacity(0.0)
        widget_in.show()
        
        anim_in = QPropertyAnimation(effect_in, b"opacity")
        anim_in.setDuration(duration)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)
        group.addAnimation(anim_in)
        
        group.finished.connect(widget_out.hide)
        cls._store_animation(widget_out, group)
        group.start()
    
    # ================================================================== #
    #                         SLIDE ANIMATIONS                            #
    # ================================================================== #
    
    @classmethod
    def slide_in(
        cls,
        widget: QWidget,
        direction: str = "left",
        duration: int = None,
        distance: int = None,
        on_finished: Callable = None
    ) -> QPropertyAnimation:
        """
        Desliza o widget para dentro da tela.
        
        Args:
            widget: Widget alvo
            direction: "left", "right", "up", "down"
            duration: Duração em ms
            distance: Distância do slide (default: largura/altura do widget)
        """
        duration = duration or cls.DURATION_NORMAL
        
        widget.show()
        end_pos = widget.pos()
        
        if distance is None:
            distance = widget.width() if direction in ["left", "right"] else widget.height()
        
        # Calcular posição inicial baseado na direção
        if direction == "left":
            start_pos = QPoint(end_pos.x() + distance, end_pos.y())
        elif direction == "right":
            start_pos = QPoint(end_pos.x() - distance, end_pos.y())
        elif direction == "up":
            start_pos = QPoint(end_pos.x(), end_pos.y() + distance)
        elif direction == "down":
            start_pos = QPoint(end_pos.x(), end_pos.y() - distance)
        else:
            start_pos = end_pos
        
        widget.move(start_pos)
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(cls.EASE_DEFAULT)
        
        if on_finished:
            animation.finished.connect(on_finished)
        
        cls._store_animation(widget, animation)
        animation.start()
        
        return animation
    
    @classmethod
    def slide_out(
        cls,
        widget: QWidget,
        direction: str = "left",
        duration: int = None,
        distance: int = None,
        hide_after: bool = True,
        on_finished: Callable = None
    ) -> QPropertyAnimation:
        """Desliza o widget para fora da tela."""
        duration = duration or cls.DURATION_NORMAL
        
        start_pos = widget.pos()
        
        if distance is None:
            distance = widget.width() if direction in ["left", "right"] else widget.height()
        
        if direction == "left":
            end_pos = QPoint(start_pos.x() - distance, start_pos.y())
        elif direction == "right":
            end_pos = QPoint(start_pos.x() + distance, start_pos.y())
        elif direction == "up":
            end_pos = QPoint(start_pos.x(), start_pos.y() - distance)
        elif direction == "down":
            end_pos = QPoint(start_pos.x(), start_pos.y() + distance)
        else:
            end_pos = start_pos
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.setEasingCurve(cls.EASE_DEFAULT)
        
        def _on_finished():
            if hide_after:
                widget.hide()
                widget.move(start_pos)  # Reset position
            if on_finished:
                on_finished()
        
        animation.finished.connect(_on_finished)
        cls._store_animation(widget, animation)
        animation.start()
        
        return animation
    
    @classmethod
    def slide_fade_in(
        cls,
        widget: QWidget,
        direction: str = "up",
        duration: int = None,
        distance: int = 30
    ):
        """Combinação de slide + fade in (muito usado em cards)."""
        duration = duration or cls.DURATION_NORMAL
        
        # Setup
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        
        end_pos = widget.pos()
        if direction == "up":
            start_pos = QPoint(end_pos.x(), end_pos.y() + distance)
        elif direction == "down":
            start_pos = QPoint(end_pos.x(), end_pos.y() - distance)
        elif direction == "left":
            start_pos = QPoint(end_pos.x() + distance, end_pos.y())
        else:
            start_pos = QPoint(end_pos.x() - distance, end_pos.y())
        
        widget.move(start_pos)
        widget.show()
        
        # Animações paralelas
        group = QParallelAnimationGroup()
        
        # Fade
        fade_anim = QPropertyAnimation(effect, b"opacity")
        fade_anim.setDuration(duration)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.setEasingCurve(cls.EASE_DEFAULT)
        group.addAnimation(fade_anim)
        
        # Slide
        slide_anim = QPropertyAnimation(widget, b"pos")
        slide_anim.setDuration(duration)
        slide_anim.setStartValue(start_pos)
        slide_anim.setEndValue(end_pos)
        slide_anim.setEasingCurve(cls.EASE_DEFAULT)
        group.addAnimation(slide_anim)
        
        cls._store_animation(widget, group)
        group.start()
    
    # ================================================================== #
    #                         SCALE ANIMATIONS                            #
    # ================================================================== #
    
    @classmethod
    def scale_up(
        cls,
        widget: QWidget,
        duration: int = None,
        start_scale: float = 0.8,
        end_scale: float = 1.0,
        on_finished: Callable = None
    ) -> QPropertyAnimation:
        """Anima o widget crescendo."""
        duration = duration or cls.DURATION_FAST
        
        original_size = widget.size()
        start_size = QSize(
            int(original_size.width() * start_scale),
            int(original_size.height() * start_scale)
        )
        
        widget.show()
        
        animation = QPropertyAnimation(widget, b"size")
        animation.setDuration(duration)
        animation.setStartValue(start_size)
        animation.setEndValue(original_size)
        animation.setEasingCurve(cls.EASE_DEFAULT)
        
        if on_finished:
            animation.finished.connect(on_finished)
        
        cls._store_animation(widget, animation)
        animation.start()
        
        return animation
    
    @classmethod
    def pop_in(
        cls,
        widget: QWidget,
        duration: int = None
    ):
        """Efeito de 'pop' - scale + fade com bounce."""
        duration = duration or cls.DURATION_NORMAL
        
        # Opacity effect
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        
        original_size = widget.size()
        start_size = QSize(
            int(original_size.width() * 0.5),
            int(original_size.height() * 0.5)
        )
        
        widget.resize(start_size)
        widget.show()
        
        group = QParallelAnimationGroup()
        
        # Fade
        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(duration)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        group.addAnimation(fade)
        
        # Scale with bounce
        scale = QPropertyAnimation(widget, b"size")
        scale.setDuration(duration)
        scale.setStartValue(start_size)
        scale.setEndValue(original_size)
        scale.setEasingCurve(QEasingCurve.Type.OutBack)
        group.addAnimation(scale)
        
        cls._store_animation(widget, group)
        group.start()
    
    # ================================================================== #
    #                       ATTENTION ANIMATIONS                          #
    # ================================================================== #
    
    @classmethod
    def shake(
        cls,
        widget: QWidget,
        duration: int = 500,
        intensity: int = 10,
        on_finished: Callable = None
    ):
        """Agita o widget horizontalmente (erro/atenção)."""
        original_pos = widget.pos()
        
        group = QSequentialAnimationGroup()
        
        # Criar sequência de movimentos
        positions = [
            QPoint(original_pos.x() - intensity, original_pos.y()),
            QPoint(original_pos.x() + intensity, original_pos.y()),
            QPoint(original_pos.x() - intensity // 2, original_pos.y()),
            QPoint(original_pos.x() + intensity // 2, original_pos.y()),
            original_pos
        ]
        
        step_duration = duration // len(positions)
        current_pos = original_pos
        
        for pos in positions:
            anim = QPropertyAnimation(widget, b"pos")
            anim.setDuration(step_duration)
            anim.setStartValue(current_pos)
            anim.setEndValue(pos)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            group.addAnimation(anim)
            current_pos = pos
        
        if on_finished:
            group.finished.connect(on_finished)
        
        cls._store_animation(widget, group)
        group.start()
    
    @classmethod
    def pulse(
        cls,
        widget: QWidget,
        duration: int = 300,
        scale: float = 1.05,
        loops: int = 2
    ):
        """Efeito de pulsação (atenção suave)."""
        original_size = widget.size()
        enlarged_size = QSize(
            int(original_size.width() * scale),
            int(original_size.height() * scale)
        )
        
        group = QSequentialAnimationGroup()
        group.setLoopCount(loops)
        
        # Expand
        expand = QPropertyAnimation(widget, b"size")
        expand.setDuration(duration // 2)
        expand.setStartValue(original_size)
        expand.setEndValue(enlarged_size)
        expand.setEasingCurve(QEasingCurve.Type.OutQuad)
        group.addAnimation(expand)
        
        # Contract
        contract = QPropertyAnimation(widget, b"size")
        contract.setDuration(duration // 2)
        contract.setStartValue(enlarged_size)
        contract.setEndValue(original_size)
        contract.setEasingCurve(QEasingCurve.Type.InQuad)
        group.addAnimation(contract)
        
        cls._store_animation(widget, group)
        group.start()
    
    @classmethod
    def bounce(
        cls,
        widget: QWidget,
        duration: int = 500,
        height: int = 20
    ):
        """Efeito de bounce vertical."""
        original_pos = widget.pos()
        
        animation = QPropertyAnimation(widget, b"pos")
        animation.setDuration(duration)
        animation.setStartValue(QPoint(original_pos.x(), original_pos.y() - height))
        animation.setEndValue(original_pos)
        animation.setEasingCurve(QEasingCurve.Type.OutBounce)
        
        # Primeiro move para cima instantaneamente
        widget.move(original_pos.x(), original_pos.y() - height)
        
        cls._store_animation(widget, animation)
        animation.start()
    
    # ================================================================== #
    #                        HIGHLIGHT ANIMATIONS                         #
    # ================================================================== #
    
    @classmethod
    def highlight_glow(
        cls,
        widget: QWidget,
        color: QColor = None,
        duration: int = 1000,
        loops: int = 2
    ):
        """Adiciona efeito de glow pulsante."""
        if color is None:
            color = QColor("#3498db")
        
        effect = QGraphicsDropShadowEffect(widget)
        effect.setColor(color)
        effect.setOffset(0, 0)
        effect.setBlurRadius(0)
        widget.setGraphicsEffect(effect)
        
        group = QSequentialAnimationGroup()
        group.setLoopCount(loops)
        
        # Glow in
        glow_in = QPropertyAnimation(effect, b"blurRadius")
        glow_in.setDuration(duration // 2)
        glow_in.setStartValue(0)
        glow_in.setEndValue(25)
        glow_in.setEasingCurve(QEasingCurve.Type.OutQuad)
        group.addAnimation(glow_in)
        
        # Glow out
        glow_out = QPropertyAnimation(effect, b"blurRadius")
        glow_out.setDuration(duration // 2)
        glow_out.setStartValue(25)
        glow_out.setEndValue(0)
        glow_out.setEasingCurve(QEasingCurve.Type.InQuad)
        group.addAnimation(glow_out)
        
        def cleanup():
            widget.setGraphicsEffect(None)
        
        group.finished.connect(cleanup)
        cls._store_animation(widget, group)
        group.start()
    
    @classmethod
    def flash(
        cls,
        widget: QWidget,
        color: str = "#ffffff",
        duration: int = 200,
        loops: int = 2
    ):
        """Flash de cor (sucesso, erro, etc)."""
        original_style = widget.styleSheet()
        
        def toggle_on():
            widget.setStyleSheet(f"{original_style} background-color: {color};")
        
        def toggle_off():
            widget.setStyleSheet(original_style)
        
        def animate_step(step):
            if step >= loops * 2:
                toggle_off()
                return
            if step % 2 == 0:
                toggle_on()
            else:
                toggle_off()
            QTimer.singleShot(duration // 2, lambda: animate_step(step + 1))
        
        animate_step(0)


class StaggeredAnimation:
    """
    Animação escalonada para múltiplos widgets.
    Útil para animar listas de cards, itens de menu, etc.
    """
    
    @staticmethod
    def fade_in_sequence(
        widgets: list,
        delay: int = 50,
        duration: int = 300
    ):
        """Fade in sequencial com delay entre widgets."""
        for i, widget in enumerate(widgets):
            QTimer.singleShot(
                i * delay,
                lambda w=widget: AnimationManager.fade_in(w, duration=duration)
            )
    
    @staticmethod
    def slide_in_sequence(
        widgets: list,
        direction: str = "up",
        delay: int = 50,
        duration: int = 300
    ):
        """Slide in sequencial."""
        for i, widget in enumerate(widgets):
            QTimer.singleShot(
                i * delay,
                lambda w=widget, d=direction: AnimationManager.slide_fade_in(w, direction=d, duration=duration)
            )
    
    @staticmethod
    def pop_in_sequence(
        widgets: list,
        delay: int = 80,
        duration: int = 300
    ):
        """Pop in sequencial (ótimo para cards de dashboard)."""
        for i, widget in enumerate(widgets):
            QTimer.singleShot(
                i * delay,
                lambda w=widget: AnimationManager.pop_in(w, duration=duration)
            )
