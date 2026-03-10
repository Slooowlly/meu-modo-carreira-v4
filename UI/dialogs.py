"""
Diálogos e janelas auxiliares
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from UI.temas import Cores, Fontes, Espacos, Estilos
from UI.componentes import (
    BotaoPrimary, BotaoSecondary, Separador
)


class DialogConfigurarPastas(QDialog):
    """Diálogo para configurar pastas do iRacing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        from Dados.config import obter_pasta_airosters, obter_pasta_aiseasons
        
        self.setWindowTitle("⚙️ Configurar Pastas")
        self.setMinimumSize(550, 280)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Título
        titulo = QLabel("Configure as pastas do iRacing")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)
        
        layout.addWidget(Separador())
        
        # Pasta airosters
        lbl_rosters = QLabel("📁 PASTA AIROSTERS (para exportar grids)")
        lbl_rosters.setFont(Fontes.label_campo())
        lbl_rosters.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        layout.addWidget(lbl_rosters)
        
        row_rosters = QHBoxLayout()
        self.input_rosters = QLineEdit()
        self.input_rosters.setStyleSheet(Estilos.input_field())
        self.input_rosters.setFont(Fontes.texto_normal())
        self.input_rosters.setText(obter_pasta_airosters())
        self.input_rosters.setPlaceholderText("Ex: C:\\Users\\...\\iRacing\\airosters")
        row_rosters.addWidget(self.input_rosters)
        
        btn_browse_rosters = BotaoSecondary("...")
        btn_browse_rosters.setFixedWidth(40)
        btn_browse_rosters.clicked.connect(lambda: self._escolher_pasta(self.input_rosters))
        row_rosters.addWidget(btn_browse_rosters)
        layout.addLayout(row_rosters)
        
        # Pasta aiseasons
        lbl_seasons = QLabel("📁 PASTA AISEASONS (para importar resultados)")
        lbl_seasons.setFont(Fontes.label_campo())
        lbl_seasons.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        layout.addWidget(lbl_seasons)
        
        row_seasons = QHBoxLayout()
        self.input_seasons = QLineEdit()
        self.input_seasons.setStyleSheet(Estilos.input_field())
        self.input_seasons.setFont(Fontes.texto_normal())
        self.input_seasons.setText(obter_pasta_aiseasons())
        self.input_seasons.setPlaceholderText("Ex: C:\\Users\\...\\iRacing\\aiseasons")
        row_seasons.addWidget(self.input_seasons)
        
        btn_browse_seasons = BotaoSecondary("...")
        btn_browse_seasons.setFixedWidth(40)
        btn_browse_seasons.clicked.connect(lambda: self._escolher_pasta(self.input_seasons))
        row_seasons.addWidget(btn_browse_seasons)
        layout.addLayout(row_seasons)
        
        layout.addStretch()
        
        # Botões
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancelar = BotaoSecondary("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)
        
        btn_salvar = BotaoPrimary("💾 Salvar")
        btn_salvar.clicked.connect(self._salvar)
        btn_layout.addWidget(btn_salvar)
        
        layout.addLayout(btn_layout)
    
    def _escolher_pasta(self, input_widget):
        """Abre diálogo para escolher pasta"""
        pasta = QFileDialog.getExistingDirectory(
            self, "Selecionar Pasta",
            input_widget.text()
        )
        if pasta:
            input_widget.setText(pasta)
    
    def _salvar(self):
        """Salva configuração das pastas"""
        from Dados.config import definir_pasta_airosters, definir_pasta_aiseasons
        
        definir_pasta_airosters(self.input_rosters.text())
        definir_pasta_aiseasons(self.input_seasons.text())
        
        QMessageBox.information(self, "Salvo!", "Configurações salvas com sucesso!")
        self.accept()