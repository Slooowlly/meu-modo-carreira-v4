"""
Diálogos e janelas auxiliares
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QFileDialog, QMessageBox, QScrollArea, QWidget, QTabWidget, QTextEdit
)
from PySide6.QtCore import Qt

from UI.temas import Cores, Fontes, Espacos, Estilos
from UI.componentes import (
    BotaoPrimary, BotaoSecondary, CampoCheck, Separador
)
from Utils.iracing_conteudo import (
    CATEGORIAS_CONTEUDO_SIMPLIFICADO,
    PISTAS_PAGAS_OPCOES,
    normalizar_conteudo_iracing,
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


class DialogConteudoIRacing(QDialog):
    """Dialogo para configurar o conteudo possuido no iRacing."""

    def __init__(self, conteudo_atual=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Conteudo iRacing")
        self.setMinimumSize(560, 620)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        self._checks_categoria: dict[str, CampoCheck] = {}
        self._checks_pistas: dict[str, CampoCheck] = {}
        self._resultado = normalizar_conteudo_iracing(conteudo_atual)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        titulo = QLabel("Atualize o conteudo que voce possui")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)
        layout.addWidget(Separador())

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        content_layout.setSpacing(10)
        scroll.setWidget(content)

        lbl_cat = QLabel("Categorias de carro:")
        lbl_cat.setFont(Fontes.label_campo())
        lbl_cat.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        content_layout.addWidget(lbl_cat)

        categorias_ativas = set(self._resultado.get("categorias", []))
        for opcao in CATEGORIAS_CONTEUDO_SIMPLIFICADO:
            opcao_id = str(opcao.get("id", "") or "").strip()
            if not opcao_id:
                continue
            label = str(opcao.get("label", opcao_id) or opcao_id)
            checked = opcao_id in categorias_ativas or bool(opcao.get("free", False))
            check = CampoCheck(label, checked=checked)
            self._checks_categoria[opcao_id] = check
            content_layout.addWidget(check)

        content_layout.addWidget(Separador())

        lbl_pistas = QLabel("Pistas pagas:")
        lbl_pistas.setFont(Fontes.label_campo())
        lbl_pistas.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        content_layout.addWidget(lbl_pistas)

        pistas_ativas = set(self._resultado.get("pistas_pagas", []))
        for opcao in PISTAS_PAGAS_OPCOES:
            opcao_id = str(opcao.get("id", "") or "").strip()
            if not opcao_id:
                continue
            label = str(opcao.get("label", opcao_id) or opcao_id)
            check = CampoCheck(label, checked=opcao_id in pistas_ativas)
            self._checks_pistas[opcao_id] = check
            content_layout.addWidget(check)

        info = QLabel(
            "Essas informacoes servem para avisos de proposta e corrida. "
            "Nao bloqueiam a jogabilidade."
        )
        info.setWordWrap(True)
        info.setFont(Fontes.texto_pequeno())
        info.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        content_layout.addWidget(info)
        content_layout.addStretch(1)

        botoes = QHBoxLayout()
        botoes.addStretch(1)

        btn_cancelar = BotaoSecondary("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        botoes.addWidget(btn_cancelar)

        btn_salvar = BotaoPrimary("Salvar")
        btn_salvar.clicked.connect(self._salvar)
        botoes.addWidget(btn_salvar)

        layout.addLayout(botoes)

    def _salvar(self):
        categorias = [
            categoria_id
            for categoria_id, check in self._checks_categoria.items()
            if check.isChecked()
        ]
        pistas = [
            pista_id
            for pista_id, check in self._checks_pistas.items()
            if check.isChecked()
        ]
        self._resultado = normalizar_conteudo_iracing(
            {
                "carros": list(categorias),
                "categorias": list(categorias),
                "pistas_pagas": list(pistas),
            }
        )
        self.accept()

    def resultado(self) -> dict:
        return dict(self._resultado)


class DialogFimTemporada(QDialog):
    """Resumo completo de fim de temporada em abas."""

    def __init__(self, ano: int, dados: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Fim de Temporada {ano}")
        self.setMinimumSize(880, 620)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        titulo = QLabel(f"FIM DE TEMPORADA {ano}")
        titulo.setFont(Fontes.titulo_grande())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)
        layout.addWidget(Separador())

        tabs = QTabWidget(self)
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(
            f"""
            QTabBar::tab {{
                color: {Cores.TEXTO_SECONDARY};
                background: transparent;
                border: 1px solid {Cores.BORDA};
                padding: 8px 12px;
                margin-right: 4px;
                border-radius: 6px;
            }}
            QTabBar::tab:selected {{
                color: {Cores.TEXTO_PRIMARY};
                border-color: {Cores.ACCENT_PRIMARY};
                background: {Cores.FUNDO_CARD};
            }}
            """
        )
        tabs.addTab(self._build_tab_texto(dados.get("resumo", "")), "Resumo")
        tabs.addTab(self._build_tab_texto(dados.get("evolucao", "")), "Evolucao")
        tabs.addTab(self._build_tab_texto(dados.get("mercado", "")), "Mercado")
        tabs.addTab(self._build_tab_texto(dados.get("promocoes", "")), "Promocoes")
        layout.addWidget(tabs, 1)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        btn_ok = BotaoPrimary("Continuar")
        btn_ok.clicked.connect(self.accept)
        botoes.addWidget(btn_ok)
        layout.addLayout(botoes)

    def _build_tab_texto(self, texto: str) -> QWidget:
        widget = QWidget()
        tab_layout = QVBoxLayout(widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.setSpacing(0)

        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setText(str(texto or "Sem dados."))
        editor.setStyleSheet(
            f"""
            QTextEdit {{
                background: {Cores.FUNDO_CARD};
                color: {Cores.TEXTO_PRIMARY};
                border: 1px solid {Cores.BORDA};
                border-radius: 8px;
                padding: 10px;
            }}
            """
        )
        tab_layout.addWidget(editor)
        return widget
