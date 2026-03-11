"""
iRacerApp - Sistema de Feedback Visual
Toasts, loading indicators, progress, notificações
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame,
    QGraphicsOpacityEffect, QProgressBar, QApplication,
    QPushButton, QSizePolicy
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QPoint, QEasingCurve,
    Signal, QSize, QThread, QObject
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QMovie
from enum import Enum
from typing import Optional, Callable
import math


class ToastType(Enum):
    """Tipos de toast/notificação."""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Toast(QFrame):
    """
    Notificação toast que aparece e desaparece automaticamente.
    
    Uso:
        Toast.show_message(parent, "Arquivo salvo!", ToastType.SUCCESS)
    """
    
    # Cores por tipo
    COLORS = {
        ToastType.SUCCESS: {"bg": "#2ecc71", "icon": "✓"},
        ToastType.ERROR: {"bg": "#e74c3c", "icon": "✕"},
        ToastType.WARNING: {"bg": "#f39c12", "icon": "⚠"},
        ToastType.INFO: {"bg": "#3498db", "icon": "ℹ"},
    }
    
    # Posição padrão
    POSITION_TOP_RIGHT = "top_right"
    POSITION_TOP_CENTER = "top_center"
    POSITION_BOTTOM_RIGHT = "bottom_right"
    POSITION_BOTTOM_CENTER = "bottom_center"
    
    # Stack de toasts ativos (para empilhar)
    _active_toasts: list = []
    
    def __init__(
        self,
        parent: QWidget,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000,
        position: str = POSITION_TOP_RIGHT
    ):
        super().__init__(parent)
        
        self.duration = duration
        self.position = position
        self.toast_type = toast_type
        
        self._setup_ui(message)
        self._setup_style()
        self._position_toast()
        
        # Adicionar ao stack
        Toast._active_toasts.append(self)
        self._reposition_all()
    
    def _setup_ui(self, message: str):
        """Monta o layout do toast."""
        self.setFixedHeight(50)
        self.setMinimumWidth(250)
        self.setMaximumWidth(400)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Ícone
        icon_label = QLabel(self.COLORS[self.toast_type]["icon"])
        icon_label.setFont(QFont("Segoe UI", 14))
        icon_label.setStyleSheet("color: white;")
        layout.addWidget(icon_label)
        
        # Mensagem
        self.message_label = QLabel(message)
        self.message_label.setFont(QFont("Segoe UI", 11))
        self.message_label.setStyleSheet("color: white;")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label, 1)
        
        # Botão fechar
        close_btn = QPushButton("×")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255,255,255,0.7);
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: white;
            }
        """)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._dismiss)
        layout.addWidget(close_btn)
    
    def _setup_style(self):
        """Aplica estilo visual."""
        bg_color = self.COLORS[self.toast_type]["bg"]
        self.setStyleSheet(f"""
            Toast {{
                background-color: {bg_color};
                border-radius: 8px;
                border: none;
            }}
        """)
        
        # Sombra
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
    
    def _position_toast(self):
        """Posiciona o toast na tela."""
        parent = self.parent()
        if not parent:
            return
        
        margin = 20
        
        if "right" in self.position:
            x = parent.width() - self.width() - margin
        else:
            x = (parent.width() - self.width()) // 2
        
        if "top" in self.position:
            y = margin
        else:
            y = parent.height() - self.height() - margin
        
        self.target_pos = QPoint(x, y)
    
    def _reposition_all(self):
        """Reposiciona todos os toasts ativos para empilhar."""
        margin = 20
        spacing = 10
        
        for i, toast in enumerate(Toast._active_toasts):
            if "top" in toast.position:
                y_offset = margin + i * (toast.height() + spacing)
            else:
                y_offset = toast.parent().height() - margin - (i + 1) * (toast.height() + spacing)
            
            if "right" in toast.position:
                x = toast.parent().width() - toast.width() - margin
            else:
                x = (toast.parent().width() - toast.width()) // 2
            
            toast.move(x, y_offset)
    
    def show_animated(self):
        """Mostra o toast com animação."""
        # Posição inicial (fora da tela)
        if "right" in self.position:
            start_x = self.parent().width() + 50
        else:
            start_x = self.target_pos.x()
        
        self.move(start_x, self.target_pos.y())
        self.show()
        
        # Opacity effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Slide in animation
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setStartValue(QPoint(start_x, self.target_pos.y()))
        self.slide_anim.setEndValue(self.target_pos)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_anim.start()
        
        # Auto dismiss
        if self.duration > 0:
            QTimer.singleShot(self.duration, self._dismiss)
    
    def _dismiss(self):
        """Remove o toast com animação."""
        # Fade out
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self._cleanup)
        self.fade_anim.start()
    
    def _cleanup(self):
        """Limpa o toast após animação."""
        if self in Toast._active_toasts:
            Toast._active_toasts.remove(self)
        self._reposition_all()
        self.deleteLater()
    
    @classmethod
    def show_message(
        cls,
        parent: QWidget,
        message: str,
        toast_type: ToastType = ToastType.INFO,
        duration: int = 3000,
        position: str = POSITION_TOP_RIGHT
    ):
        """
        Método estático para mostrar um toast.
        
        Exemplo:
            Toast.show_message(self, "Salvo com sucesso!", ToastType.SUCCESS)
        """
        toast = cls(parent, message, toast_type, duration, position)
        toast.show_animated()
        return toast
    
    @classmethod
    def success(cls, parent: QWidget, message: str, **kwargs):
        """Atalho para toast de sucesso."""
        return cls.show_message(parent, message, ToastType.SUCCESS, **kwargs)
    
    @classmethod
    def error(cls, parent: QWidget, message: str, **kwargs):
        """Atalho para toast de erro."""
        return cls.show_message(parent, message, ToastType.ERROR, **kwargs)
    
    @classmethod
    def warning(cls, parent: QWidget, message: str, **kwargs):
        """Atalho para toast de aviso."""
        return cls.show_message(parent, message, ToastType.WARNING, **kwargs)
    
    @classmethod
    def info(cls, parent: QWidget, message: str, **kwargs):
        """Atalho para toast de informação."""
        return cls.show_message(parent, message, ToastType.INFO, **kwargs)


class LoadingSpinner(QWidget):
    """
    Spinner de carregamento animado.
    
    Uso:
        spinner = LoadingSpinner(self)
        spinner.start()
        # ... operação ...
        spinner.stop()
    """
    
    def __init__(
        self,
        parent: QWidget = None,
        size: int = 40,
        color: QColor = None,
        line_width: int = 4
    ):
        super().__init__(parent)
        
        self.size = size
        self.color = color or QColor("#3498db")
        self.line_width = line_width
        self.angle = 0
        
        self.setFixedSize(size, size)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
    
    def paintEvent(self, event):
        """Desenha o spinner."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calcular área de desenho
        rect_size = self.size - self.line_width * 2
        rect = self.rect().adjusted(
            self.line_width, self.line_width,
            -self.line_width, -self.line_width
        )
        
        # Desenhar arco
        pen = QPen(self.color)
        pen.setWidth(self.line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        # Arco de 270 graus, rotacionado pelo ângulo atual
        start_angle = self.angle * 16  # Qt usa 1/16 de grau
        span_angle = 270 * 16
        
        painter.drawArc(rect, start_angle, span_angle)
    
    def _rotate(self):
        """Rotaciona o spinner."""
        self.angle = (self.angle + 10) % 360
        self.update()
    
    def start(self):
        """Inicia a animação."""
        self.show()
        self.timer.start(16)  # ~60 FPS
    
    def stop(self):
        """Para a animação."""
        self.timer.stop()
        self.hide()


class LoadingOverlay(QWidget):
    """
    Overlay de carregamento que cobre um widget.
    
    Uso:
        overlay = LoadingOverlay(self.content_widget)
        overlay.show_loading("Carregando dados...")
        # ... operação ...
        overlay.hide_loading()
    """
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0.7);")
        self.hide()
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Spinner
        self.spinner = LoadingSpinner(self, size=50, color=QColor("#ffffff"))
        layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Mensagem
        self.message_label = QLabel()
        self.message_label.setFont(QFont("Segoe UI", 12))
        self.message_label.setStyleSheet("color: white;")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.message_label)

        self.opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity)
        self.opacity.setOpacity(1.0)
        self.fade_anim = None
    
    def show_loading(self, message: str = "Carregando..."):
        """Mostra o overlay com mensagem."""
        self.message_label.setText(message)
        parent = self.parent()
        if parent is not None:
            self.resize(parent.size())
        elif self.width() <= 0 or self.height() <= 0:
            self.resize(400, 300)
        self.raise_()
        self.show()
        self.spinner.start()
        
        # Fade in
        self.fade_anim = QPropertyAnimation(self.opacity, b"opacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
    
    def hide_loading(self):
        """Esconde o overlay."""
        if self.isHidden():
            return

        self.fade_anim = QPropertyAnimation(self.opacity, b"opacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(self.opacity.opacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self._on_hidden)
        self.fade_anim.start()
    
    def _on_hidden(self):
        self.spinner.stop()
        self.hide()
    
    def resizeEvent(self, event):
        """Redimensiona junto com o parent."""
        super().resizeEvent(event)
        parent = self.parent()
        if parent is not None:
            self.resize(parent.size())


class ProgressIndicator(QFrame):
    """
    Indicador de progresso com estilo.
    
    Uso:
        progress = ProgressIndicator(self, "Simulando corrida...")
        progress.set_progress(50)
        progress.set_progress(100)
        progress.hide()
    """
    
    def __init__(
        self,
        parent: QWidget,
        message: str = "Processando...",
        show_percentage: bool = True
    ):
        super().__init__(parent)
        
        self.show_percentage = show_percentage
        
        self._setup_ui(message)
        self._setup_style()
    
    def _setup_ui(self, message: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Header com mensagem e porcentagem
        header = QHBoxLayout()
        
        self.message_label = QLabel(message)
        self.message_label.setFont(QFont("Segoe UI", 11))
        header.addWidget(self.message_label)
        
        self.percent_label = QLabel("0%")
        self.percent_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.addWidget(self.percent_label)
        
        layout.addLayout(header)
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)
    
    def _setup_style(self):
        self.setStyleSheet("""
            ProgressIndicator {
                background-color: #2b2b3d;
                border-radius: 10px;
                border: 1px solid #3e3e55;
            }
            QLabel {
                color: #e0e0e0;
            }
            QProgressBar {
                background-color: #1e1e2e;
                border-radius: 4px;
                border: none;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 4px;
            }
        """)
    
    def set_progress(self, value: int, message: str = None):
        """Atualiza o progresso."""
        self.progress_bar.setValue(value)
        self.percent_label.setText(f"{value}%")
        
        if message:
            self.message_label.setText(message)
    
    def set_message(self, message: str):
        """Atualiza apenas a mensagem."""
        self.message_label.setText(message)


class SuccessCheckmark(QWidget):
    """
    Animação de checkmark de sucesso.
    Aparece após uma operação bem-sucedida.
    """
    
    finished = Signal()
    
    def __init__(self, parent: QWidget, size: int = 80):
        super().__init__(parent)
        
        self.check_size = size
        self.progress = 0.0
        self.circle_progress = 0.0
        
        self.setFixedSize(size, size)
        
        # Timer para animação
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = self.check_size // 2 - 5
        
        # Desenhar círculo
        if self.circle_progress > 0:
            pen = QPen(QColor("#2ecc71"))
            pen.setWidth(4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            
            span = int(360 * self.circle_progress)
            painter.drawArc(
                center.x() - radius, center.y() - radius,
                radius * 2, radius * 2,
                90 * 16, -span * 16
            )
        
        # Desenhar checkmark
        if self.progress > 0:
            pen = QPen(QColor("#2ecc71"))
            pen.setWidth(4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            
            # Pontos do checkmark
            p1 = QPoint(center.x() - radius // 2, center.y())
            p2 = QPoint(center.x() - radius // 6, center.y() + radius // 3)
            p3 = QPoint(center.x() + radius // 2, center.y() - radius // 3)
            
            # Primeira linha (p1 -> p2)
            if self.progress <= 0.5:
                t = self.progress / 0.5
                end_x = p1.x() + (p2.x() - p1.x()) * t
                end_y = p1.y() + (p2.y() - p1.y()) * t
                painter.drawLine(p1, QPoint(int(end_x), int(end_y)))
            else:
                # Linha completa + segunda linha
                painter.drawLine(p1, p2)
                t = (self.progress - 0.5) / 0.5
                end_x = p2.x() + (p3.x() - p2.x()) * t
                end_y = p2.y() + (p3.y() - p2.y()) * t
                painter.drawLine(p2, QPoint(int(end_x), int(end_y)))
    
    def _animate(self):
        # Fase 1: círculo
        if self.circle_progress < 1.0:
            self.circle_progress += 0.05
        # Fase 2: checkmark
        elif self.progress < 1.0:
            self.progress += 0.08
        else:
            self.timer.stop()
            QTimer.singleShot(500, self._finish)
        
        self.update()
    
    def _finish(self):
        self.finished.emit()
        self.hide()
    
    def play(self):
        """Inicia a animação."""
        self.progress = 0.0
        self.circle_progress = 0.0
        self.show()
        self.raise_()
        self.timer.start(20)
    
    @classmethod
    def show_success(cls, parent: QWidget, size: int = 80):
        """Mostra animação de sucesso centralizada no parent."""
        check = cls(parent, size)
        check.move(
            (parent.width() - size) // 2,
            (parent.height() - size) // 2
        )
        check.play()
        return check
