"""
iRacerApp - Efeitos Visuais
Hover effects, ripple, glow e outros efeitos interativos
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QLabel
)
from PySide6.QtCore import (
    Qt, QPropertyAnimation, QPoint, QTimer, QRect,
    QEasingCurve, Property, QObject, Signal, QEvent
)
from PySide6.QtGui import (
    QColor, QPainter, QBrush, QPen, QLinearGradient,
    QRadialGradient, QPainterPath, QEnterEvent
)
from typing import Optional


class HoverEffect(QObject):
    """
    Aplica efeito de hover em qualquer widget.
    
    Uso:
        HoverEffect.apply(my_button, scale=1.02, shadow=True)
    """
    
    @staticmethod
    def apply(
        widget: QWidget,
        scale: float = 1.0,
        shadow: bool = True,
        color_shift: bool = False,
        lift: int = 0
    ):
        """
        Aplica efeitos de hover no widget.
        
        Args:
            widget: Widget alvo
            scale: Fator de escala no hover (1.02 = 2% maior)
            shadow: Adicionar/aumentar sombra no hover
            color_shift: Mudar levemente a cor no hover
            lift: Pixels para "levantar" o widget no hover
        """
        # Guardar estado original
        widget._original_geometry = None
        widget._original_shadow = None
        widget._hover_effect_applied = True
        
        # Sombra base
        if shadow:
            base_shadow = QGraphicsDropShadowEffect(widget)
            base_shadow.setBlurRadius(10)
            base_shadow.setColor(QColor(0, 0, 0, 40))
            base_shadow.setOffset(0, 2)
            widget.setGraphicsEffect(base_shadow)
            widget._base_shadow = base_shadow
        
        # Override enterEvent e leaveEvent
        original_enter = widget.enterEvent
        original_leave = widget.leaveEvent
        
        def on_enter(event):
            widget._original_geometry = widget.geometry()
            
            # Scale effect
            if scale != 1.0:
                new_width = int(widget.width() * scale)
                new_height = int(widget.height() * scale)
                dx = (new_width - widget.width()) // 2
                dy = (new_height - widget.height()) // 2
                widget.setGeometry(
                    widget.x() - dx,
                    widget.y() - dy - lift,
                    new_width,
                    new_height
                )
            elif lift > 0:
                widget.move(widget.x(), widget.y() - lift)
            
            # Shadow increase
            if shadow and hasattr(widget, '_base_shadow'):
                widget._base_shadow.setBlurRadius(20)
                widget._base_shadow.setColor(QColor(0, 0, 0, 60))
                widget._base_shadow.setOffset(0, 4 + lift)
            
            original_enter(event)
        
        def on_leave(event):
            if widget._original_geometry:
                widget.setGeometry(widget._original_geometry)
            
            if shadow and hasattr(widget, '_base_shadow'):
                widget._base_shadow.setBlurRadius(10)
                widget._base_shadow.setColor(QColor(0, 0, 0, 40))
                widget._base_shadow.setOffset(0, 2)
            
            original_leave(event)
        
        widget.enterEvent = on_enter
        widget.leaveEvent = on_leave


class RippleEffect(QWidget):
    """
    Efeito de ripple (Material Design) para botões.
    
    Uso:
        # Herdar ou aplicar em botão existente
        ripple_btn = RippleButton("Clique aqui")
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.ripples = []  # Lista de ripples ativos
        self.ripple_color = QColor(255, 255, 255, 80)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_ripples)
    
    def add_ripple(self, center: QPoint):
        """Adiciona um novo ripple na posição especificada."""
        ripple = {
            'center': center,
            'radius': 0,
            'max_radius': max(self.width(), self.height()) * 1.5,
            'opacity': 1.0
        }
        self.ripples.append(ripple)
        
        if not self.timer.isActive():
            self.timer.start(16)
    
    def _update_ripples(self):
        """Atualiza todos os ripples ativos."""
        to_remove = []
        
        for ripple in self.ripples:
            ripple['radius'] += 8
            ripple['opacity'] -= 0.03
            
            if ripple['opacity'] <= 0:
                to_remove.append(ripple)
        
        for ripple in to_remove:
            self.ripples.remove(ripple)
        
        if not self.ripples:
            self.timer.stop()
        
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.ripples:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for ripple in self.ripples:
            color = QColor(self.ripple_color)
            color.setAlphaF(ripple['opacity'] * 0.3)
            
            gradient = QRadialGradient(
                ripple['center'].x(),
                ripple['center'].y(),
                ripple['radius']
            )
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                ripple['center'],
                int(ripple['radius']),
                int(ripple['radius'])
            )


class RippleButton(QPushButton):
    """Botão com efeito de ripple integrado."""
    
    def __init__(self, text: str = "", parent: QWidget = None):
        super().__init__(text, parent)
        self.ripples = []
        self.ripple_color = QColor(255, 255, 255, 80)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_ripples)
    
    def mousePressEvent(self, event):
        self.add_ripple(event.pos())
        super().mousePressEvent(event)

    def add_ripple(self, center: QPoint):
        """Adiciona um novo ripple na posição especificada."""
        ripple = {
            'center': center,
            'radius': 0,
            'max_radius': max(self.width(), self.height()) * 1.5,
            'opacity': 1.0
        }
        self.ripples.append(ripple)
        
        if not self.timer.isActive():
            self.timer.start(16)

    def _update_ripples(self):
        """Atualiza todos os ripples ativos."""
        to_remove = []
        
        for ripple in self.ripples:
            ripple['radius'] += 8
            ripple['opacity'] -= 0.03
            
            if ripple['opacity'] <= 0:
                to_remove.append(ripple)
        
        for ripple in to_remove:
            self.ripples.remove(ripple)
        
        if not self.ripples:
            self.timer.stop()
        
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.ripples:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for ripple in self.ripples:
            color = QColor(self.ripple_color)
            color.setAlphaF(ripple['opacity'] * 0.3)
            
            gradient = QRadialGradient(
                ripple['center'].x(),
                ripple['center'].y(),
                ripple['radius']
            )
            gradient.setColorAt(0, color)
            gradient.setColorAt(1, QColor(255, 255, 255, 0))
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(
                ripple['center'],
                int(ripple['radius']),
                int(ripple['radius'])
            )


class GlowingBorder(QFrame):
    """
    Frame com borda que brilha/pulsa.
    Útil para destacar elementos importantes.
    
    Uso:
        frame = GlowingBorder()
        frame.set_glow_color("#3498db")
        frame.start_glow()
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.glow_color = QColor("#3498db")
        self.glow_intensity = 0
        self.max_intensity = 20
        self.direction = 1
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate_glow)
        
        self._update_style()
    
    def set_glow_color(self, color: str):
        """Define a cor do glow."""
        self.glow_color = QColor(color)
        self._update_style()
    
    def _update_style(self):
        """Atualiza o estilo com o glow atual."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(self.glow_intensity)
        shadow.setColor(self.glow_color)
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
    
    def _animate_glow(self):
        """Anima a intensidade do glow."""
        self.glow_intensity += self.direction
        
        if self.glow_intensity >= self.max_intensity:
            self.direction = -1
        elif self.glow_intensity <= 5:
            self.direction = 1
        
        self._update_style()
    
    def start_glow(self):
        """Inicia a animação de glow."""
        self.timer.start(50)
    
    def stop_glow(self):
        """Para a animação de glow."""
        self.timer.stop()
        self.glow_intensity = 0
        self._update_style()


class AnimatedCounter(QLabel):
    """
    Label numérico que anima a contagem.
    
    Uso:
        counter = AnimatedCounter()
        counter.animate_to(1000)  # Conta de 0 até 1000
    """
    
    value_changed = Signal(int)
    
    def __init__(
        self,
        parent: QWidget = None,
        prefix: str = "",
        suffix: str = "",
        decimals: int = 0
    ):
        super().__init__(parent)
        
        self.prefix = prefix
        self.suffix = suffix
        self.decimals = decimals
        self._current_value = 0
        self._target_value = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._step)
        
        self._update_display()
    
    def _update_display(self):
        """Atualiza o texto exibido."""
        if self.decimals > 0:
            text = f"{self.prefix}{self._current_value:.{self.decimals}f}{self.suffix}"
        else:
            text = f"{self.prefix}{int(self._current_value):,}{self.suffix}".replace(",", ".")
        self.setText(text)
    
    def _step(self):
        """Um passo da animação."""
        diff = self._target_value - self._current_value
        
        if abs(diff) < 1:
            self._current_value = self._target_value
            self.timer.stop()
        else:
            # Ease out
            step = diff * 0.1
            if abs(step) < 1:
                step = 1 if diff > 0 else -1
            self._current_value += step
        
        self._update_display()
        self.value_changed.emit(int(self._current_value))
    
    def animate_to(self, value: float, duration: int = 1000):
        """
        Anima até o valor especificado.
        
        Args:
            value: Valor final
            duration: Duração aproximada em ms
        """
        self._target_value = value
        self.timer.start(16)  # ~60 FPS
    
    def set_value(self, value: float, animate: bool = True):
        """Define o valor, opcionalmente com animação."""
        if animate:
            self.animate_to(value)
        else:
            self._current_value = value
            self._target_value = value
            self._update_display()


class ProgressRing(QWidget):
    """
    Indicador de progresso circular estilizado.
    
    Uso:
        ring = ProgressRing(size=100)
        ring.set_progress(75)  # 75%
    """
    
    def __init__(
        self,
        parent: QWidget = None,
        size: int = 100,
        line_width: int = 8,
        bg_color: QColor = None,
        progress_color: QColor = None
    ):
        super().__init__(parent)
        
        self.ring_size = size
        self.line_width = line_width
        self.bg_color = bg_color or QColor("#2b2b3d")
        self.progress_color = progress_color or QColor("#3498db")
        self._progress = 0
        self._target_progress = 0
        
        self.setFixedSize(size, size)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(
            self.line_width, self.line_width,
            -self.line_width, -self.line_width
        )
        
        # Background circle
        pen = QPen(self.bg_color)
        pen.setWidth(self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)
        
        # Progress arc
        if self._progress > 0:
            pen = QPen(self.progress_color)
            pen.setWidth(self.line_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            span = int(360 * self._progress / 100)
            painter.drawArc(rect, 90 * 16, -span * 16)
        
        # Center text
        painter.setPen(QPen(QColor("#ffffff")))
        painter.setFont(self.font())
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(self._progress)}%")
    
    def _animate(self):
        diff = self._target_progress - self._progress
        if abs(diff) < 0.5:
            self._progress = self._target_progress
            self.timer.stop()
        else:
            self._progress += diff * 0.1
        self.update()
    
    def set_progress(self, value: int, animate: bool = True):
        """Define o progresso (0-100)."""
        self._target_progress = max(0, min(100, value))
        
        if animate:
            if not self.timer.isActive():
                self.timer.start(16)
        else:
            self._progress = self._target_progress
            self.update()
    
    def set_colors(self, bg: str, progress: str):
        """Define as cores do ring."""
        self.bg_color = QColor(bg)
        self.progress_color = QColor(progress)
        self.update()


class ShimmerEffect(QWidget):
    """
    Efeito shimmer/skeleton loading.
    Mostra enquanto conteúdo está carregando.
    
    Uso:
        shimmer = ShimmerEffect(parent, width=200, height=20)
        shimmer.start()
    """
    
    def __init__(
        self,
        parent: QWidget = None,
        width: int = 200,
        height: int = 20,
        radius: int = 4
    ):
        super().__init__(parent)
        
        self.setFixedSize(width, height)
        self.radius = radius
        self.shimmer_pos = -width
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        painter.fillPath(path, QColor("#2b2b3d"))
        
        # Shimmer gradient
        gradient = QLinearGradient(self.shimmer_pos, 0, self.shimmer_pos + self.width(), 0)
        gradient.setColorAt(0, QColor(255, 255, 255, 0))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 30))
        gradient.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setClipPath(path)
        painter.fillRect(self.rect(), gradient)
    
    def _animate(self):
        self.shimmer_pos += 5
        if self.shimmer_pos > self.width() * 2:
            self.shimmer_pos = -self.width()
        self.update()
    
    def start(self):
        """Inicia a animação."""
        self.show()
        self.timer.start(16)
    
    def stop(self):
        """Para a animação."""
        self.timer.stop()
        self.hide()
