"""
Tela de criação de carreira
Integrado com o backend do Modo Carreira
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QScrollArea, QMessageBox, QPushButton, QFrame, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QEvent,
    QEasingCurve,
    QPoint,
    QRect,
    QSize,
    QPropertyAnimation,
    QTimer,
)
from PySide6.QtGui import QCursor

from UI.temas import Cores, Fontes, Espacos, Estilos
from UI.componentes import (
    Card, CardTitulo, CampoTexto, CampoCombo,
    CampoSlider, CampoCheck, BotaoPrimary, BotaoSecondary,
    BotaoDanger, LabelTitulo, LabelSubtitulo, Separador,
    Espacador, LinhaInfo
)

# Importa nosso backend
from Dados.constantes import CATEGORIAS, DIFICULDADES, PISTAS_IRACING, _EQUIPES_POR_CATEGORIA
from Dados.banco import carregar_banco, salvar_banco, banco_existe, deletar_banco
from Logica.pilotos import popular_categoria, obter_pilotos_categoria
from Logica.equipes import criar_todas_equipes, atribuir_pilotos_equipes
from Logica.series_especiais import inicializar_production_car_challenge


class TelaInicialConfig(QMainWindow):
    """Janela de criação de nova carreira"""
    
    carreira_criada = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🏁 Modo Carreira — Nova Carreira")
        self.setMinimumSize(650, 750)
        self.resize(750, 850)
        self.setStyleSheet(Estilos.janela_principal() + Estilos.tooltip())
        self._fixar_tela_cheia = True
        
        # Verifica se já existe carreira
        if banco_existe():
            self._build_tela_existente()
        else:
            self._build_ui()

        self._configurar_controles_fullscreen()

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
        self._fonte_versao_base = 10.0
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
                max(int(area.width() * 0.72), self.minimumWidth()),
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

    def resizeEvent(self, event):
        self._posicionar_controles_fullscreen()
        super().resizeEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if (
                self._fixar_tela_cheia
                and self.isVisible()
                and not self.isMinimized()
                and not self.isFullScreen()
            ):
                QTimer.singleShot(0, self.showFullScreen)
        super().changeEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "_timer_controles_fullscreen"):
            self._timer_controles_fullscreen.stop()
        super().closeEvent(event)
    
    def _build_tela_existente(self):
        """Tela quando já existe uma carreira salva"""
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(
            Espacos.PADDING_JANELA, Espacos.PADDING_JANELA,
            Espacos.PADDING_JANELA, Espacos.PADDING_JANELA
        )
        layout.setSpacing(Espacos.MARGIN_SECTION)
        
        layout.addStretch()
        
        # Aviso
        card = Card()
        card_layout = QVBoxLayout()
        card_layout.setAlignment(Qt.AlignCenter)
        card_layout.setSpacing(15)
        
        icone = QLabel("⚠️")
        icone.setFont(Fontes.numero_destaque())
        icone.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(icone)
        
        titulo = QLabel("Já existe uma carreira salva!")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        titulo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(titulo)
        
        subtitulo = QLabel("O que deseja fazer?")
        subtitulo.setFont(Fontes.texto_normal())
        subtitulo.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        subtitulo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitulo)
        
        card_widget = QWidget()
        card_widget.setLayout(card_layout)
        card.add(card_widget)
        
        layout.addWidget(card)
        layout.addWidget(Espacador(20))
        
        # Botões
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        btn_continuar = BotaoPrimary("▶️  Continuar Carreira Existente")
        btn_continuar.clicked.connect(self._continuar_carreira)
        btn_layout.addWidget(btn_continuar)
        
        btn_nova = BotaoDanger("🗑️  Deletar e Criar Nova Carreira")
        btn_nova.clicked.connect(self._resetar_e_criar)
        btn_layout.addWidget(btn_nova)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
    
    def _continuar_carreira(self):
        """Continua com a carreira existente"""
        banco = carregar_banco()
        self.carreira_criada.emit(banco)
        self.close()
    
    def _resetar_e_criar(self):
        """Deleta carreira e mostra tela de criação"""
        resposta = QMessageBox.warning(
            self, "Confirmar",
            "Tem certeza? Isso vai APAGAR todos os dados da carreira atual!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if resposta == QMessageBox.Yes:
            deletar_banco()
            # Reconstrói a interface
            self._build_ui()
    
    def _build_ui(self):
        """Constrói a tela de criação de carreira"""
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        
        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        conteudo = QWidget()
        main_layout = QVBoxLayout(conteudo)
        main_layout.setContentsMargins(
            Espacos.PADDING_JANELA, Espacos.PADDING_JANELA,
            Espacos.PADDING_JANELA, Espacos.PADDING_JANELA
        )
        main_layout.setSpacing(Espacos.MARGIN_SECTION)
        
        # ── HEADER ──
        header = QVBoxLayout()
        header.setSpacing(4)
        
        titulo = LabelTitulo("🏁  Modo Carreira")
        header.addWidget(titulo)
        
        subtitulo = LabelSubtitulo("Configure sua jornada no automobilismo")
        header.addWidget(subtitulo)
        
        main_layout.addLayout(header)
        main_layout.addWidget(Separador())
        
        # ── DADOS DO JOGADOR ──
        card_jogador = CardTitulo("👤 Perfil do Jogador")
        
        self.campo_nome = CampoTexto("Nome", "Digite seu nome...")
        card_jogador.add(self.campo_nome)
        
        self.slider_idade = CampoSlider("Idade Inicial", 16, 35, 18, " anos")
        card_jogador.add(self.slider_idade)
        
        main_layout.addWidget(card_jogador)
        
        # ── CATEGORIA INICIAL ──
        card_categoria = CardTitulo("🏎️ Categoria Inicial", "Onde você vai começar sua carreira")
        
        categorias_nomes = [c["nome"] for c in CATEGORIAS]
        self.combo_categoria = CampoCombo("Categoria", categorias_nomes)
        card_categoria.add(self.combo_categoria)
        
        # Info das categorias
        info_cat = QLabel("💡 Comece de baixo e suba nas categorias! Top 5 = Promoção")
        info_cat.setFont(Fontes.texto_pequeno())
        info_cat.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        card_categoria.add(info_cat)
        
        main_layout.addWidget(card_categoria)
        
        # ── CONFIGURAÇÕES DO MUNDO ──
        card_config = CardTitulo("🌍 Configurações do Mundo")
        
        self.slider_ano = CampoSlider("Ano de Início", 2020, 2035, 2024)
        card_config.add(self.slider_ano)
        
        self.slider_pre_sim = CampoSlider("Anos Pré-Simulados", 0, 15, 5, " anos")
        card_config.add(self.slider_pre_sim)
        
        info_pre = QLabel("💡 Anos pré-simulados criam história: campeões, recordes, rivalidades")
        info_pre.setFont(Fontes.texto_pequeno())
        info_pre.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        card_config.add(info_pre)
        
        main_layout.addWidget(card_config)
        
        # ── DIFICULDADE ──
        card_dif = CardTitulo("🏁 Dificuldade")
        
        dificuldades_nomes = list(DIFICULDADES.keys())
        self.combo_dificuldade = CampoCombo("Skill dos Rivais", dificuldades_nomes)
        self.combo_dificuldade.setCurrentIndex(1)  # Médio
        card_dif.add(self.combo_dificuldade)
        
        self.slider_pilotos = CampoSlider("Pilotos por Categoria", 16, 30, 20)
        card_dif.add(self.slider_pilotos)
        
        self.slider_aposentadoria = CampoSlider("Idade de Aposentadoria", 38, 50, 42, " anos")
        card_dif.add(self.slider_aposentadoria)
        
        main_layout.addWidget(card_dif)
        
        # ── OPÇÕES EXTRAS ──
        card_extras = CardTitulo("⚙️ Opções Extras")
        
        self.check_lendas = CampoCheck("Gerar pilotos lendários nas categorias superiores", checked=True)
        card_extras.add(self.check_lendas)
        
        main_layout.addWidget(card_extras)
        
        # ── BOTÕES ──
        main_layout.addWidget(Espacador(15))
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(Espacos.MARGIN_ITEM)
        
        btn_cancelar = BotaoSecondary("Cancelar")
        btn_cancelar.clicked.connect(self.close)
        btn_layout.addWidget(btn_cancelar)
        
        btn_layout.addStretch()
        
        self.btn_criar = BotaoPrimary("🚀  Iniciar Carreira")
        self.btn_criar.setMinimumWidth(200)
        self.btn_criar.clicked.connect(self._criar_carreira)
        btn_layout.addWidget(self.btn_criar)
        
        main_layout.addLayout(btn_layout)
        main_layout.addWidget(Espacador(20))
        
        # Montar scroll
        scroll.setWidget(conteudo)
        
        scroll_layout = QVBoxLayout(central)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.addWidget(scroll)

    def _registrar_historico_pre_simulado(self, banco, categoria, ano_corrente):
        pilotos_categoria = obter_pilotos_categoria(banco, categoria["id"])
        pilotos_ordenados = sorted(
            pilotos_categoria,
            key=lambda piloto: (
                -int(piloto.get("pontos_temporada", 0)),
                -int(piloto.get("vitorias_temporada", 0)),
                -int(piloto.get("podios_temporada", 0)),
                str(piloto.get("nome", "")).casefold(),
            ),
        )

        classificacao = []
        for posicao, piloto in enumerate(pilotos_ordenados, start=1):
            piloto.setdefault("historico_temporadas", [])
            piloto["historico_temporadas"].append(
                {
                    "ano": ano_corrente,
                    "categoria": categoria["id"],
                    "equipe_nome": piloto.get("equipe_nome", ""),
                    "posicao_final": posicao,
                    "pontos": int(piloto.get("pontos_temporada", 0)),
                    "vitorias": int(piloto.get("vitorias_temporada", 0)),
                    "podios": int(piloto.get("podios_temporada", 0)),
                    "poles": int(piloto.get("poles_temporada", 0)),
                    "voltas_rapidas": int(piloto.get("voltas_rapidas_temporada", 0)),
                    "dnfs": int(piloto.get("dnfs_temporada", 0)),
                }
            )

            classificacao.append(
                {
                    "posicao": posicao,
                    "piloto": piloto.get("nome", ""),
                    "piloto_id": piloto.get("id"),
                    "equipe": piloto.get("equipe_nome", ""),
                    "pontos": int(piloto.get("pontos_temporada", 0)),
                    "vitorias": int(piloto.get("vitorias_temporada", 0)),
                    "podios": int(piloto.get("podios_temporada", 0)),
                    "poles": int(piloto.get("poles_temporada", 0)),
                    "voltas_rapidas": int(piloto.get("voltas_rapidas_temporada", 0)),
                    "resultados": piloto.get("resultados_temporada", []).copy(),
                }
            )

        banco.setdefault("historico_temporadas_completas", [])
        banco["historico_temporadas_completas"].append(
            {
                "ano": ano_corrente,
                "categoria_id": categoria["id"],
                "categoria_nome": categoria["nome"],
                "classificacao": classificacao,
            }
        )

    def _capacidade_categoria_por_equipes_fixas(self, categoria_id, fallback_pilotos):
        total_equipes = len(_EQUIPES_POR_CATEGORIA.get(categoria_id, []))
        if total_equipes > 0:
            return total_equipes * 2
        return max(2, int(fallback_pilotos))

    def _garantir_equipe_jogador(self, banco, categoria_id):
        jogador = next(
            (piloto for piloto in banco["pilotos"] if piloto.get("is_jogador")),
            None,
        )
        if not jogador or jogador.get("equipe_id"):
            return

        atribuir_pilotos_equipes(banco, categoria_id)
        if jogador.get("equipe_id"):
            return

        equipes_categoria = [
            equipe for equipe in banco.get("equipes", [])
            if equipe.get("categoria") == categoria_id
        ]
        if not equipes_categoria:
            return

        equipe_alvo = next(
            (equipe for equipe in equipes_categoria if len(equipe.get("pilotos", [])) < 2),
            None,
        )
        if equipe_alvo is None:
            equipe_alvo = equipes_categoria[0]

            # Se todas estiverem cheias, libera o 2º piloto para manter grade fixa.
            pilotos_equipe = list(equipe_alvo.get("pilotos", []))
            if len(pilotos_equipe) >= 2:
                piloto_saida_id = pilotos_equipe[-1]
                piloto_saida = next(
                    (piloto for piloto in banco.get("pilotos", []) if piloto.get("id") == piloto_saida_id),
                    None,
                )
                if piloto_saida and not piloto_saida.get("is_jogador", False):
                    piloto_saida["equipe_id"] = None
                    piloto_saida["equipe_nome"] = None
                    piloto_saida["papel"] = "reserva"
                    equipe_alvo["pilotos"] = [pid for pid in pilotos_equipe if pid != piloto_saida_id]
                    if equipe_alvo.get("piloto_numero_1") == piloto_saida_id:
                        equipe_alvo["piloto_numero_1"] = None
                        equipe_alvo["piloto_1"] = None
                    if equipe_alvo.get("piloto_numero_2") == piloto_saida_id:
                        equipe_alvo["piloto_numero_2"] = None
                        equipe_alvo["piloto_2"] = None

        if jogador.get("id") not in equipe_alvo.get("pilotos", []):
            equipe_alvo.setdefault("pilotos", []).append(jogador.get("id"))
        jogador["equipe_id"] = equipe_alvo.get("id")
        jogador["equipe_nome"] = equipe_alvo.get("nome")

        if equipe_alvo.get("piloto_numero_1") is None:
            equipe_alvo["piloto_numero_1"] = jogador.get("id")
            equipe_alvo["piloto_1"] = jogador.get("nome")
            jogador["papel"] = "numero_1"
        elif equipe_alvo.get("piloto_numero_2") is None:
            equipe_alvo["piloto_numero_2"] = jogador.get("id")
            equipe_alvo["piloto_2"] = jogador.get("nome")
            jogador["papel"] = "numero_2"

    def _normalizar_categoria_inicial(self, banco, categoria_id, total_pilotos):
        capacidade_categoria = self._capacidade_categoria_por_equipes_fixas(
            categoria_id,
            total_pilotos,
        )
        total_desejado = min(max(1, int(total_pilotos)), int(capacidade_categoria))

        pilotos_categoria = [
            piloto
            for piloto in banco["pilotos"]
            if piloto.get("categoria_atual") == categoria_id
            and not piloto.get("aposentado", False)
        ]

        jogador = next(
            (piloto for piloto in pilotos_categoria if piloto.get("is_jogador", False)),
            None,
        )
        vagas_ai = max(total_desejado - (1 if jogador else 0), 0)

        pilotos_ai = [
            piloto for piloto in pilotos_categoria if not piloto.get("is_jogador", False)
        ]

        if len(pilotos_ai) > vagas_ai:
            pilotos_ai_ordenados = sorted(
                pilotos_ai,
                key=lambda piloto: (
                    -float(piloto.get("skill", 0)),
                    -int(piloto.get("potencial", 0)),
                    str(piloto.get("nome", "")).casefold(),
                ),
            )
            pilotos_mantidos = {
                piloto["id"] for piloto in pilotos_ai_ordenados[:vagas_ai]
            }
            banco["pilotos"] = [
                piloto
                for piloto in banco["pilotos"]
                if piloto.get("categoria_atual") != categoria_id
                or piloto.get("is_jogador", False)
                or piloto.get("id") in pilotos_mantidos
            ]

        pilotos_categoria = [
            piloto
            for piloto in banco["pilotos"]
            if piloto.get("categoria_atual") == categoria_id
            and not piloto.get("aposentado", False)
        ]
        pilotos_ai = [
            piloto for piloto in pilotos_categoria if not piloto.get("is_jogador", False)
        ]

        faltantes = vagas_ai - len(pilotos_ai)
        if faltantes > 0:
            popular_categoria(
                banco,
                categoria_id,
                faltantes,
                banco.get("ano_inicio_historico", banco.get("ano_atual", 2024)),
            )

        equipes_categoria = [
            equipe
            for equipe in banco.get("equipes", [])
            if equipe.get("categoria") == categoria_id
        ]
        for equipe in equipes_categoria:
            equipe["pilotos"] = []
            equipe["piloto_numero_1"] = None
            equipe["piloto_numero_2"] = None
            equipe["piloto_1"] = None
            equipe["piloto_2"] = None

        pilotos_categoria = [
            piloto
            for piloto in banco["pilotos"]
            if piloto.get("categoria_atual") == categoria_id
            and not piloto.get("aposentado", False)
        ]
        for piloto in pilotos_categoria:
            piloto["equipe_id"] = None
            piloto["equipe_nome"] = None
            if not piloto.get("is_jogador", False):
                piloto["papel"] = "reserva"

        atribuir_pilotos_equipes(banco, categoria_id)

    def _gerar_calendario_inicial(self, total_rodadas):
        """Gera um calendario base com trackId para a temporada principal."""
        pistas_validas = [
            pista
            for pista in PISTAS_IRACING
            if isinstance(pista, dict) and pista.get("trackId") not in (None, "")
        ]
        if not pistas_validas:
            return []

        total = max(int(total_rodadas), 1)
        calendario = []
        for indice in range(total):
            pista = pistas_validas[indice % len(pistas_validas)]
            track_id = int(pista.get("trackId"))
            circuito = str(pista.get("nome", f"Track ID {track_id}")).strip() or f"Track ID {track_id}"
            calendario.append(
                {
                    "nome": f"Rodada {indice + 1}",
                    "circuito": circuito,
                    "trackId": track_id,
                    "voltas": 10,
                    "clima": "Seco",
                    "temperatura": 26,
                }
            )
        return calendario
    
    def _criar_carreira(self):
        """Cria a carreira com todos os dados"""
        # Validação
        nome = self.campo_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Campo obrigatório", "Digite seu nome!")
            return
        
        # Coleta dados
        idade_jogador = self.slider_idade.value()
        ano_inicio = self.slider_ano.value()
        anos_pre_sim = self.slider_pre_sim.value()
        dificuldade = self.combo_dificuldade.currentText()
        qtd_pilotos = self.slider_pilotos.value()
        idade_aposentadoria = self.slider_aposentadoria.value()
        gerar_lendas = self.check_lendas.isChecked()
        
        categoria_nome = self.combo_categoria.currentText()
        categoria_id = next((c["id"] for c in CATEGORIAS if c["nome"] == categoria_nome), "mazda_rookie")
        
        ano_simulacao_inicio = ano_inicio - anos_pre_sim
        
        # Desabilita botão enquanto processa
        self.btn_criar.setEnabled(False)
        self.btn_criar.setText("⏳ Criando...")
        
        carreira_criada = False
        try:
            # Cria banco
            from Dados.banco import criar_banco_vazio
            from Logica.pilotos import resetar_stats_temporada
            banco = criar_banco_vazio()
            
            banco["nome_jogador"] = nome
            banco["ano_atual"] = ano_inicio
            banco["ano_inicio_historico"] = ano_simulacao_inicio
            banco["idade_aposentadoria"] = idade_aposentadoria
            banco["dificuldade"] = dificuldade
            banco["pilotos_por_categoria"] = qtd_pilotos
            banco["total_rodadas"] = 24
            banco["rodada_atual"] = 1
            banco["temporada_concluida"] = False
            banco["calendario"] = self._gerar_calendario_inicial(banco["total_rodadas"])
            
            # Popular todas as categorias
            banco.setdefault("max_drivers_por_categoria", {})
            for categoria in CATEGORIAS:
                cat_id = categoria["id"]
                capacidade_categoria = self._capacidade_categoria_por_equipes_fixas(
                    cat_id,
                    qtd_pilotos,
                )
                banco["max_drivers_por_categoria"][cat_id] = int(capacidade_categoria)

                quantidade_categoria = int(capacidade_categoria)
                if cat_id == categoria_id:
                    quantidade_categoria = max(int(capacidade_categoria) - 1, 1)
    
                popular_categoria(
                    banco,
                    cat_id,
                    quantidade_categoria,
                    ano_simulacao_inicio,
                )
            
            # Gerar lendas
            if gerar_lendas:
                from Logica.pilotos import criar_piloto_lenda
                for cat_id in ["gt3", "gt4"]:
                    for _ in range(3):
                        lenda = criar_piloto_lenda(banco, cat_id, ano_simulacao_inicio)
                        banco["pilotos"].append(lenda)
            
            # Criar equipes fixas oficiais e distribuir pilotos.
            criar_todas_equipes(banco, banco["ano_atual"])
            for categoria in CATEGORIAS:
                atribuir_pilotos_equipes(banco, categoria["id"])
            
            # Pré-simulação
            if anos_pre_sim > 0:
                from Logica.simulacao import simular_temporada_completa
                from Logica.pilotos import envelhecer_piloto
                from Logica.equipes import resetar_equipes_temporada
                
                for ano_idx in range(anos_pre_sim):
                    ano_corrente = ano_simulacao_inicio + ano_idx
                    
                    for categoria in CATEGORIAS:
                        resultado = simular_temporada_completa(banco, categoria["id"], ano_corrente)
                        
                        if resultado:
                            banco["campeoes"].append({
                                "ano": ano_corrente,
                                "categoria": categoria["nome"],
                                "categoria_id": categoria["id"],
                                "piloto": resultado["campeao"],
                                "pontos": resultado["pontos_campeao"],
                                "vice": resultado["vice"]
                            })
                            self._registrar_historico_pre_simulado(
                                banco,
                                categoria,
                                ano_corrente,
                            )
                    
                    # Envelhecer pilotos
                    for piloto in banco["pilotos"]:
                        envelhecer_piloto(piloto)
                        resetar_stats_temporada(piloto)
                    
                    resetar_equipes_temporada(banco)
            
            # Reset final para a primeira temporada real
            for piloto in banco["pilotos"]:
                resetar_stats_temporada(piloto)
            
            # Adiciona o jogador
            from Dados.banco import obter_proximo_id
            jogador = {
                "id": obter_proximo_id(banco, "piloto"),
                "nome": nome,
                "idade": idade_jogador,
                "categoria_atual": categoria_id,
                "skill": 50,
                "aggression": 0.5,
                "titulos": 0,
                "vitorias_carreira": 0,
                "podios_carreira": 0,
                "poles_carreira": 0,
                "voltas_rapidas_carreira": 0,
                "corridas_carreira": 0,
                "pontos_carreira": 0,
                "dnfs_carreira": 0,
                "pontos_temporada": 0,
                "vitorias_temporada": 0,
                "podios_temporada": 0,
                "poles_temporada": 0,
                "voltas_rapidas_temporada": 0,
                "corridas_temporada": 0,
                "dnfs_temporada": 0,
                "incidentes_carreira": 0,
                "incidentes_temporada": 0,
                "melhor_resultado_temporada": 99,
                "temporadas_na_categoria": 0,
                "ano_inicio_carreira": ano_inicio,
                "resultados_temporada": [],
                "equipe_id": None,
                "equipe_nome": None,
                "historico_temporadas": [],
                "is_jogador": True
            }
            banco["pilotos"].append(jogador)
            
            # Garante o tamanho correto do grid e recompõe as equipes da categoria inicial.
            self._normalizar_categoria_inicial(banco, categoria_id, qtd_pilotos)
            self._garantir_equipe_jogador(banco, categoria_id)
            inicializar_production_car_challenge(banco, banco["ano_atual"])
            
            # Salva
            salvar_banco(banco)
            carreira_criada = True
    
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Erro ao criar carreira",
                f"Ocorreu um erro ao criar a carreira:\n{exc}",
            )
            return
        finally:
            if not carreira_criada:
                self.btn_criar.setEnabled(True)
                self.btn_criar.setText("🚀  Iniciar Carreira")
        
        # Mostra resumo
        total_pilotos = len(banco["pilotos"])
        total_equipes = len(banco["equipes"])
        
        jogador_atualizado = next((p for p in banco["pilotos"] if p.get("is_jogador")), jogador)
        equipe_jogador = jogador_atualizado.get("equipe_nome", "Sem equipe")
        
        QMessageBox.information(
            self, "🏁 Carreira Criada!",
            f"Sua carreira foi criada com sucesso!\n\n"
            f"👤 Piloto: {nome}, {idade_jogador} anos\n"
            f"📅 Ano: {ano_inicio}\n"
            f"🏎️ Categoria: {categoria_nome}\n"
            f"🏢 Equipe: {equipe_jogador}\n"
            f"👥 Pilotos: {total_pilotos}\n"
            f"🏢 Equipes: {total_equipes}\n"
            f"📜 Anos de história: {anos_pre_sim}"
        )
        
        # Emite sinal e fecha
        self.carreira_criada.emit(banco)
        self.close()

