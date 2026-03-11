"""Dialogos e janelas auxiliares."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from UI.componentes import BotaoPrimary, BotaoSecondary, CampoCheck, Separador
from UI.temas import Cores, Fontes, Estilos
from Utils.helpers import obter_nome_categoria
from Utils.iracing_conteudo import (
    CATEGORIAS_CONTEUDO_SIMPLIFICADO,
    PISTAS_PAGAS_OPCOES,
    normalizar_conteudo_iracing,
)


def _safe_int(valor: Any, padrao: int = 0) -> int:
    try:
        return int(round(float(valor)))
    except (TypeError, ValueError):
        return int(padrao)


def _safe_float(valor: Any, padrao: float = 0.0) -> float:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return float(padrao)


def _normalizar_papel(papel: Any) -> str:
    valor = str(papel or "").strip().lower()
    if valor in {"numero_1", "n1"}:
        return "N1 (principal)"
    if valor in {"numero_2", "n2"}:
        return "N2"
    if valor == "reserva":
        return "Reserva"
    return "Nao definido"


def _classificar_morale(morale: Any) -> str:
    fator = _safe_float(morale, 1.0)
    if fator < 0.9:
        return f"Baixo ({fator:.2f})"
    if fator > 1.1:
        return f"Alto ({fator:.2f})"
    return f"Normal ({fator:.2f})"


def _classificar_potencial(potencial: Any) -> str:
    valor = _safe_int(potencial, 0)
    if valor >= 80:
        return "Alto"
    if valor >= 60:
        return "Medio"
    return "Baixo"


def montar_texto_resultado_corrida(dados: dict[str, Any]) -> str:
    """Monta o corpo textual do resultado detalhado de corrida."""
    payload = dados if isinstance(dados, dict) else {}
    linhas: list[str] = []

    classificacao = payload.get("classificacao", [])
    if isinstance(classificacao, list) and classificacao:
        linhas.append("=== CLASSIFICACAO FINAL ===")
        for indice, item in enumerate(classificacao, start=1):
            if not isinstance(item, dict):
                continue
            nome = str(item.get("piloto_nome", "Piloto") or "Piloto")
            equipe = str(item.get("equipe_nome", "") or "").strip()
            equipe_txt = f" ({equipe})" if equipe else ""
            is_jogador = bool(item.get("is_jogador", False))
            pontos = _safe_int(item.get("pontos"), 0)
            if bool(item.get("dnf", False)):
                motivo = str(item.get("motivo_dnf", "") or "").strip() or "abandono"
                prefixo = "VOCE - " if is_jogador else ""
                linhas.append(f"DNF  {prefixo}{nome}{equipe_txt} - {motivo}")
                continue
            posicao = _safe_int(item.get("posicao_campeonato", item.get("posicao", indice)), indice)
            prefixo = "VOCE - " if is_jogador else ""
            linhas.append(f"P{posicao:02d}  {prefixo}{nome}{equipe_txt}  +{pontos} pts")
        linhas.append("")

    destaques = payload.get("destaques", [])
    if isinstance(destaques, list) and destaques:
        linhas.append("=== DESTAQUES ===")
        for item in destaques:
            texto = str(item or "").strip()
            if texto:
                linhas.append(f"- {texto}")
        linhas.append("")

    lesoes = payload.get("lesoes_rodada", [])
    if isinstance(lesoes, list) and lesoes:
        linhas.append("=== LESOES DA RODADA ===")
        for item in lesoes:
            if not isinstance(item, dict):
                continue
            nome = str(item.get("piloto_nome", "Piloto") or "Piloto")
            tipo = str(item.get("tipo", "desconhecida") or "desconhecida")
            corridas = _safe_int(item.get("corridas_restantes"), 0)
            linhas.append(f"- {nome}: {tipo} ({corridas} corrida(s))")
        linhas.append("")

    ordens = payload.get("ordens_equipe", [])
    if isinstance(ordens, list) and ordens:
        linhas.append("=== ORDENS DE EQUIPE ===")
        for item in ordens:
            texto = str(item or "").strip()
            if texto:
                linhas.append(f"- {texto}")
        linhas.append("")

    campeonato = payload.get("campeonato_atualizado", [])
    if isinstance(campeonato, list) and campeonato:
        linhas.append("=== CAMPEONATO ATUALIZADO ===")
        for item in campeonato[:20]:
            if not isinstance(item, dict):
                continue
            pos = _safe_int(item.get("posicao"), 0)
            nome = str(item.get("nome", "Piloto") or "Piloto")
            pontos = _safe_int(item.get("pontos"), 0)
            delta = _safe_int(item.get("delta"), 0)
            delta_txt = f" ({delta:+d})" if delta else ""
            linhas.append(f"{pos:02d} - {nome}: {pontos} pts{delta_txt}")
        linhas.append("")

    outras = payload.get("outras_categorias", [])
    if isinstance(outras, list) and outras:
        linhas.append("=== OUTRAS CATEGORIAS ===")
        for item in outras:
            if not isinstance(item, dict):
                continue
            categoria = str(item.get("categoria_nome", item.get("categoria_id", "Categoria")) or "Categoria")
            rodada = item.get("rodada")
            vencedor = str(item.get("vencedor", "Sem vencedor") or "Sem vencedor")
            rodada_txt = f"Rodada {rodada}" if rodada not in (None, "", 0) else "Rodada"
            linhas.append(f"- {categoria} {rodada_txt}: vencedor {vencedor}")

    return "\n".join(linhas) if linhas else "Sem dados detalhados para exibir."


class DialogConfigurarPastas(QDialog):
    """Dialogo para configurar pastas do iRacing."""

    def __init__(self, parent=None):
        super().__init__(parent)

        from Dados.config import obter_pasta_airosters, obter_pasta_aiseasons

        self.setWindowTitle("Configurar Pastas")
        self.setMinimumSize(550, 280)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        titulo = QLabel("Configure as pastas do iRacing")
        titulo.setFont(Fontes.titulo_medio())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)

        layout.addWidget(Separador())

        lbl_rosters = QLabel("PASTA AIROSTERS (exportar grids)")
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

        lbl_seasons = QLabel("PASTA AISEASONS (importar resultados)")
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

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = BotaoSecondary("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancelar)

        btn_salvar = BotaoPrimary("Salvar")
        btn_salvar.clicked.connect(self._salvar)
        btn_layout.addWidget(btn_salvar)

        layout.addLayout(btn_layout)

    def _escolher_pasta(self, input_widget):
        pasta = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta",
            input_widget.text(),
        )
        if pasta:
            input_widget.setText(pasta)

    def _salvar(self):
        from Dados.config import definir_pasta_airosters, definir_pasta_aiseasons

        definir_pasta_airosters(self.input_rosters.text())
        definir_pasta_aiseasons(self.input_seasons.text())

        QMessageBox.information(self, "Salvo", "Configuracoes salvas com sucesso.")
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

class PerfilJogadorDialog(QDialog):
    """Tela dedicada de perfil completo do jogador."""

    _atributos = [
        ("Skill", "skill"),
        ("Consistencia", "consistencia"),
        ("Racecraft", "racecraft"),
        ("Ritmo Quali", "ritmo_classificacao"),
        ("Gestao Pneus", "gestao_pneus"),
        ("Hab. Largada", "habilidade_largada"),
        ("Resist. Mental", "resistencia_mental"),
        ("Fitness", "fitness"),
        ("Fator Chuva", "fator_chuva"),
        ("Fator Clutch", "fator_clutch"),
        ("Experiencia", "experiencia"),
        ("Motivacao", "motivacao"),
    ]

    def __init__(
        self,
        banco: dict[str, Any],
        jogador: dict[str, Any],
        contexto: dict[str, Any] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.banco = banco if isinstance(banco, dict) else {}
        self.jogador = jogador if isinstance(jogador, dict) else {}
        self.contexto = contexto if isinstance(contexto, dict) else {}

        nome = str(self.jogador.get("nome", "Jogador") or "Jogador")
        self.setWindowTitle(f"Meu Perfil - {nome}")
        self.setMinimumSize(900, 760)
        self.resize(980, 820)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        titulo = QLabel(f"MEU PERFIL - {nome}")
        titulo.setFont(Fontes.titulo_grande())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)
        layout.addWidget(Separador())

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        layout.addWidget(scroll, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(6, 6, 6, 6)
        content_layout.setSpacing(12)
        scroll.setWidget(content)

        content_layout.addWidget(self._build_secao_info_pessoal())
        content_layout.addWidget(self._build_secao_contrato())
        content_layout.addWidget(self._build_secao_atributos())
        content_layout.addWidget(self._build_secao_stats())
        content_layout.addWidget(self._build_secao_lesao())
        content_layout.addWidget(self._build_secao_historico())
        content_layout.addWidget(self._build_secao_evolucao_skill())
        content_layout.addStretch(1)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        btn_fechar = BotaoPrimary("Fechar")
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

    def _novo_painel(self, titulo: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setStyleSheet(
            f"""
            QFrame {{
                background: {Cores.FUNDO_CARD};
                border: 1px solid {Cores.BORDA};
                border-radius: 8px;
            }}
            """
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(Fontes.titulo_pequeno())
        lbl_titulo.setStyleSheet(f"color: {Cores.ACCENT_PRIMARY}; border: none;")
        layout.addWidget(lbl_titulo)

        separador = QFrame()
        separador.setFixedHeight(1)
        separador.setStyleSheet(f"background: {Cores.BORDA}; border: none;")
        layout.addWidget(separador)
        return frame, layout

    def _linha_info(self, chave: str, valor: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lbl_chave = QLabel(chave)
        lbl_chave.setFont(Fontes.texto_pequeno())
        lbl_chave.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        lbl_chave.setFixedWidth(180)

        lbl_valor = QLabel(valor)
        lbl_valor.setFont(Fontes.texto_normal())
        lbl_valor.setWordWrap(True)
        lbl_valor.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")

        layout.addWidget(lbl_chave)
        layout.addWidget(lbl_valor, 1)
        return widget

    def _build_secao_info_pessoal(self) -> QWidget:
        frame, layout = self._novo_painel("INFORMACOES PESSOAIS")
        layout.addWidget(self._linha_info("Nome", str(self.jogador.get("nome", "-") or "-")))
        idade = _safe_int(self.jogador.get("idade"), 0)
        layout.addWidget(self._linha_info("Idade", f"{idade} anos"))
        nacionalidade = str(self.jogador.get("nacionalidade", "-") or "-")
        layout.addWidget(self._linha_info("Nacionalidade", nacionalidade))
        return frame

    def _build_secao_contrato(self) -> QWidget:
        frame, layout = self._novo_painel("CONTRATO ATUAL")
        equipe = str(self.jogador.get("equipe_nome", "Sem equipe") or "Sem equipe")
        categoria_id = str(self.jogador.get("categoria_atual", "") or "").strip()
        categoria = obter_nome_categoria(categoria_id) if categoria_id else "-"
        papel = _normalizar_papel(self.jogador.get("papel"))
        contrato = max(0, _safe_int(self.jogador.get("contrato_anos"), 0))
        contrato_txt = f"{contrato} ano(s) restante(s)" if contrato else "Encerrando nesta temporada"

        layout.addWidget(self._linha_info("Equipe", equipe))
        layout.addWidget(self._linha_info("Categoria", categoria))
        layout.addWidget(self._linha_info("Papel", papel))
        layout.addWidget(self._linha_info("Contrato", contrato_txt))
        return frame

    def _criar_linha_atributo(self, rotulo: str, valor: int) -> QWidget:
        linha = QWidget()
        layout = QHBoxLayout(linha)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        lbl = QLabel(rotulo)
        lbl.setFont(Fontes.texto_pequeno())
        lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
        lbl.setFixedWidth(150)
        layout.addWidget(lbl)

        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(max(0, min(100, valor)))
        barra.setTextVisible(False)
        barra.setFixedHeight(12)
        barra.setStyleSheet(
            f"""
            QProgressBar {{
                background: #0f1825;
                border: 1px solid {Cores.BORDA};
                border-radius: 6px;
            }}
            QProgressBar::chunk {{
                background: {Cores.ACCENT_PRIMARY};
                border-radius: 6px;
            }}
            """
        )
        layout.addWidget(barra, 1)

        lbl_valor = QLabel(str(valor))
        lbl_valor.setFont(Fontes.texto_pequeno())
        lbl_valor.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        lbl_valor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_valor.setFixedWidth(32)
        layout.addWidget(lbl_valor)
        return linha

    def _build_secao_atributos(self) -> QWidget:
        frame, layout = self._novo_painel("ATRIBUTOS")
        for rotulo, campo in self._atributos:
            valor = _safe_int(self.jogador.get(campo), 0)
            layout.addWidget(self._criar_linha_atributo(rotulo, valor))

        potencial = _safe_int(
            self.jogador.get("potencial", self.jogador.get("potencial_base", 0)),
            0,
        )
        teto = _classificar_potencial(potencial)
        layout.addWidget(self._linha_info("Teto estimado", f"{teto} ({potencial}/100)"))
        return frame

    def _build_secao_stats(self) -> QWidget:
        frame, layout = self._novo_painel("STATS TEMPORADA E CARREIRA")
        corridas_temp = _safe_int(self.jogador.get("corridas_temporada"), 0)
        vitorias_temp = _safe_int(self.jogador.get("vitorias_temporada"), 0)
        podios_temp = _safe_int(self.jogador.get("podios_temporada"), 0)
        poles_temp = _safe_int(self.jogador.get("poles_temporada"), 0)
        dnfs_temp = _safe_int(self.jogador.get("dnfs_temporada"), 0)
        pontos_temp = _safe_int(self.jogador.get("pontos_temporada"), 0)

        pos = self.contexto.get("posicao_campeonato", "-")
        total = self.contexto.get("total_pilotos", "-")
        pos_txt = f"{pos}/{total}" if pos != "-" and total != "-" else "-"

        layout.addWidget(
            self._linha_info(
                "Temporada",
                (
                    f"Corridas: {corridas_temp} | Vitorias: {vitorias_temp} | Podios: {podios_temp} | "
                    f"Poles: {poles_temp} | DNFs: {dnfs_temp} | Pontos: {pontos_temp}"
                ),
            )
        )
        layout.addWidget(self._linha_info("Posicao no campeonato", pos_txt))

        corridas_carr = _safe_int(self.jogador.get("corridas_carreira"), 0)
        vitorias_carr = _safe_int(self.jogador.get("vitorias_carreira"), 0)
        podios_carr = _safe_int(self.jogador.get("podios_carreira"), 0)
        poles_carr = _safe_int(self.jogador.get("poles_carreira"), 0)
        dnfs_carr = _safe_int(self.jogador.get("dnfs_carreira"), 0)
        titulos = _safe_int(self.jogador.get("titulos"), 0)
        layout.addWidget(
            self._linha_info(
                "Carreira",
                (
                    f"Corridas: {corridas_carr} | Vitorias: {vitorias_carr} | Podios: {podios_carr} | "
                    f"Poles: {poles_carr} | DNFs: {dnfs_carr} | Titulos: {titulos}"
                ),
            )
        )
        return frame

    def _build_secao_lesao(self) -> QWidget:
        frame, layout = self._novo_painel("LESAO")
        lesao = self.jogador.get("lesao")
        if isinstance(lesao, dict) and _safe_int(lesao.get("corridas_restantes"), 0) > 0:
            tipo = str(lesao.get("tipo", "desconhecida") or "desconhecida")
            restantes = _safe_int(lesao.get("corridas_restantes"), 0)
            texto = f"Lesao {tipo} - {restantes} corrida(s) restante(s)"
        else:
            texto = "Sem lesao ativa"
        layout.addWidget(self._linha_info("Status", texto))
        return frame

    def _build_secao_historico(self) -> QWidget:
        frame, layout = self._novo_painel("HISTORICO DE CARREIRA")
        historico = self.jogador.get("historico_temporadas", [])
        linhas: list[str] = []
        if isinstance(historico, list):
            for item in historico[-12:]:
                if not isinstance(item, dict):
                    continue
                ano = _safe_int(item.get("ano"), 0)
                categoria = str(item.get("categoria") or item.get("categoria_id") or "").strip()
                categoria_txt = obter_nome_categoria(categoria) if categoria else "-"
                equipe = str(item.get("equipe_nome", "-") or "-")
                posicao = _safe_int(item.get("posicao_final"), 0)
                pos_txt = f"P{posicao}" if posicao > 0 else "sem posicao"
                if ano > 0:
                    linhas.append(f"{ano}: {categoria_txt} - {equipe} - {pos_txt}")

        if not linhas:
            hist_equipes = self.jogador.get("historico_equipes", [])
            if isinstance(hist_equipes, list):
                for item in hist_equipes[-12:]:
                    if not isinstance(item, dict):
                        continue
                    inicio = _safe_int(item.get("ano_inicio"), 0)
                    fim = item.get("ano_fim")
                    fim_txt = str(fim) if fim not in (None, "", 0) else "atual"
                    equipe = str(item.get("equipe_nome", "-") or "-")
                    categoria = str(item.get("categoria", "") or "").strip()
                    categoria_txt = obter_nome_categoria(categoria) if categoria else "-"
                    if inicio > 0:
                        linhas.append(f"{inicio}-{fim_txt}: {categoria_txt} - {equipe}")

        if not linhas:
            linhas = ["Sem historico de temporadas registrado."]

        for linha in linhas[-8:]:
            lbl = QLabel(linha)
            lbl.setWordWrap(True)
            lbl.setFont(Fontes.texto_pequeno())
            lbl.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
            layout.addWidget(lbl)
        return frame

    def _build_secao_evolucao_skill(self) -> QWidget:
        frame, layout = self._novo_painel("EVOLUCAO DE SKILLS")
        historico = self.jogador.get("historico_temporadas", [])
        pontos: list[tuple[str, int]] = []
        if isinstance(historico, list):
            for item in historico:
                if not isinstance(item, dict):
                    continue
                ano = _safe_int(item.get("ano"), 0)
                skill = None
                for chave in ("skill", "skill_final", "overall", "rating"):
                    if chave in item:
                        skill = _safe_int(item.get(chave), -1)
                        break
                if ano > 0 and isinstance(skill, int) and skill >= 0:
                    pontos.append((str(ano), skill))

        skill_atual = _safe_int(self.jogador.get("skill"), 0)
        if not pontos:
            pontos.append(("Atual", skill_atual))
        elif pontos[-1][1] != skill_atual:
            pontos.append(("Atual", skill_atual))

        texto_linha = " -> ".join(f"{rotulo}: {valor}" for rotulo, valor in pontos)
        layout.addWidget(self._linha_info("Linha do tempo", texto_linha))

        grade = QGridLayout()
        grade.setContentsMargins(0, 0, 0, 0)
        grade.setHorizontalSpacing(8)
        grade.setVerticalSpacing(6)
        for indice, (rotulo, valor) in enumerate(pontos[-6:]):
            lbl_rotulo = QLabel(rotulo)
            lbl_rotulo.setFont(Fontes.texto_pequeno())
            lbl_rotulo.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
            grade.addWidget(lbl_rotulo, indice, 0)
            grade.addWidget(self._criar_linha_atributo("Skill", valor), indice, 1)
        layout.addLayout(grade)
        return frame

class ResultadoCorridaDialog(QDialog):
    """Dialogo com resultado detalhado de corrida."""

    def __init__(self, dados: dict[str, Any], parent=None):
        super().__init__(parent)
        self.dados = dados if isinstance(dados, dict) else {}

        titulo = str(self.dados.get("titulo", "Resultado da Corrida") or "Resultado da Corrida")
        self.setWindowTitle(titulo)
        self.setMinimumSize(920, 680)
        self.resize(980, 760)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        lbl_titulo = QLabel(titulo)
        lbl_titulo.setFont(Fontes.titulo_grande())
        lbl_titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(lbl_titulo)
        layout.addWidget(Separador())

        corpo = QTextEdit()
        corpo.setReadOnly(True)
        corpo.setText(self._montar_texto())
        corpo.setStyleSheet(
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
        layout.addWidget(corpo, 1)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        btn_fechar = BotaoPrimary("Fechar")
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

    def _montar_texto(self) -> str:
        return montar_texto_resultado_corrida(self.dados)


class MilestoneDialog(QDialog):
    """Dialogo de celebracao para marcos de carreira."""

    def __init__(self, milestone: dict[str, Any], parent=None):
        super().__init__(parent)
        self.milestone = milestone if isinstance(milestone, dict) else {}
        self.setWindowTitle("Marco de Carreira")
        self.setMinimumSize(420, 260)
        self.resize(460, 300)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        icone = QLabel(str(self.milestone.get("icone", "🏆") or "🏆"))
        icone.setAlignment(Qt.AlignCenter)
        icone.setStyleSheet("font-size: 56px; border: none; background: transparent;")
        layout.addWidget(icone)

        titulo = QLabel(str(self.milestone.get("titulo", "Novo marco") or "Novo marco"))
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setFont(Fontes.titulo_grande())
        titulo.setStyleSheet("color: #FFD54F; border: none; background: transparent;")
        layout.addWidget(titulo)

        descricao = QLabel(str(self.milestone.get("descricao", "") or ""))
        descricao.setAlignment(Qt.AlignCenter)
        descricao.setWordWrap(True)
        descricao.setFont(Fontes.texto_normal())
        descricao.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none; background: transparent;")
        layout.addWidget(descricao)

        layout.addStretch(1)
        btn = BotaoPrimary("Continuar")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, 0, Qt.AlignCenter)


class ModificadoresDialog(QDialog):
    """Dialogo para exibicao de modificadores ativos da rodada."""

    def __init__(self, dados: dict[str, Any], parent=None):
        super().__init__(parent)
        self.dados = dados if isinstance(dados, dict) else {}
        self.setWindowTitle("Modificadores Ativos")
        self.setMinimumSize(940, 700)
        self.resize(980, 760)
        self.setStyleSheet(f"background-color: {Cores.FUNDO_APP};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        rodada = _safe_int(self.dados.get("rodada_atual"), 0)
        total = _safe_int(self.dados.get("total_corridas"), 0)
        pista = str(self.dados.get("track_name", "Pista desconhecida") or "Pista desconhecida")
        clima = str(self.dados.get("clima", "Seco") or "Seco")

        titulo = QLabel(f"MODIFICADORES ATIVOS - Rodada {rodada}/{max(1, total)}")
        titulo.setFont(Fontes.titulo_grande())
        titulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(titulo)

        subtitulo = QLabel(f"Circuito: {pista} | Clima: {clima}")
        subtitulo.setFont(Fontes.texto_normal())
        subtitulo.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY};")
        layout.addWidget(subtitulo)
        layout.addWidget(Separador())

        self.chk_apenas_ativos = QCheckBox("Mostrar apenas pilotos com modificadores ativos")
        self.chk_apenas_ativos.setChecked(False)
        self.chk_apenas_ativos.stateChanged.connect(self._atualizar_texto)
        self.chk_apenas_ativos.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY};")
        layout.addWidget(self.chk_apenas_ativos)

        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setStyleSheet(
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
        layout.addWidget(self.editor, 1)

        botoes = QHBoxLayout()
        botoes.addStretch(1)
        btn_fechar = BotaoPrimary("Fechar")
        btn_fechar.clicked.connect(self.accept)
        botoes.addWidget(btn_fechar)
        layout.addLayout(botoes)

        self._atualizar_texto()

    def _linha_mods(self, mods: list[dict[str, Any]]) -> str:
        if not isinstance(mods, list) or not mods:
            return "sem mudanca"
        partes = []
        for mod in mods:
            if not isinstance(mod, dict):
                continue
            valor = float(mod.get("valor", 0.0) or 0.0)
            if abs(valor) <= 0.01:
                continue
            desc = str(mod.get("descricao", mod.get("fonte", "modificador")) or "modificador")
            partes.append(f"{valor:+.1f} ({desc})")
        return " | ".join(partes) if partes else "sem mudanca"

    def _atualizar_texto(self) -> None:
        pilotos = self.dados.get("pilotos", [])
        if not isinstance(pilotos, list):
            pilotos = []
        apenas_ativos = bool(self.chk_apenas_ativos.isChecked())

        linhas: list[str] = []
        for item in pilotos:
            if not isinstance(item, dict):
                continue
            ativo = bool(item.get("ativo", False))
            if apenas_ativos and not ativo:
                continue

            nome = str(item.get("nome", "Piloto") or "Piloto")
            equipe = str(item.get("equipe_nome", "Equipe") or "Equipe")
            skill_base = _safe_int(item.get("skill_base"), 0)
            skill_final = _safe_int(item.get("skill_final"), skill_base)
            agg_base = _safe_int(item.get("aggression_base"), 0)
            agg_final = _safe_int(item.get("aggression_final"), agg_base)
            opt_base = _safe_int(item.get("optimism_base"), 0)
            opt_final = _safe_int(item.get("optimism_final"), opt_base)
            smo_base = _safe_int(item.get("smoothness_base"), 0)
            smo_final = _safe_int(item.get("smoothness_final"), smo_base)

            linhas.append(f"{nome} ({equipe})")
            linhas.append(
                f"  Skill: {skill_base} -> {skill_final} ({skill_final - skill_base:+d})"
            )
            linhas.append(f"    {self._linha_mods(item.get('skill_modifiers', []))}")
            linhas.append(
                f"  Aggression: {agg_base} -> {agg_final} ({agg_final - agg_base:+d})"
            )
            linhas.append(f"    {self._linha_mods(item.get('aggression_modifiers', []))}")
            linhas.append(
                f"  Optimism: {opt_base} -> {opt_final} ({opt_final - opt_base:+d})"
            )
            linhas.append(f"    {self._linha_mods(item.get('optimism_modifiers', []))}")
            linhas.append(
                f"  Smoothness: {smo_base} -> {smo_final} ({smo_final - smo_base:+d})"
            )
            linhas.append(f"    {self._linha_mods(item.get('smoothness_modifiers', []))}")
            linhas.append("-" * 56)

        if not linhas:
            linhas = ["Nenhum modificador disponivel para a rodada atual."]
        self.editor.setText("\n".join(linhas))


class DialogFimTemporada(QDialog):
    """Resumo completo de fim de temporada em abas."""

    def __init__(self, ano: int, dados: dict, parent=None):
        super().__init__(parent)
        self.dados = dados if isinstance(dados, dict) else {}

        self.setWindowTitle(f"Fim de Temporada {ano}")
        self.setMinimumSize(900, 650)
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
        tabs.addTab(self._build_tab_texto(self.dados.get("resumo", "")), "Resumo")
        tabs.addTab(self._build_tab_evolucao(), "Evolucao")
        tabs.addTab(self._build_tab_mercado(), "Mercado")
        tabs.addTab(self._build_tab_promocoes(), "Promocoes")
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

    def _build_tab_evolucao(self) -> QWidget:
        evolucao = self.dados.get("evolucao_detalhada", [])
        if not isinstance(evolucao, list) or not evolucao:
            return self._build_tab_texto(str(self.dados.get("evolucao", "") or "Sem dados de evolucao."))

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        painel = QFrame()
        painel.setStyleSheet(
            f"""
            QFrame {{
                background: {Cores.FUNDO_CARD};
                border: 1px solid {Cores.BORDA};
                border-radius: 8px;
            }}
            """
        )
        painel_layout = QVBoxLayout(painel)
        painel_layout.setContentsMargins(10, 10, 10, 10)
        painel_layout.setSpacing(8)

        cabecalho = QGridLayout()
        cabecalho.setHorizontalSpacing(8)
        cabecalho.addWidget(self._label_coluna("Atributo"), 0, 0)
        cabecalho.addWidget(self._label_coluna("Antes"), 0, 1)
        cabecalho.addWidget(self._label_coluna("Depois"), 0, 2)
        cabecalho.addWidget(self._label_coluna("Delta"), 0, 3)
        painel_layout.addLayout(cabecalho)

        for item in evolucao:
            if not isinstance(item, dict):
                continue
            rotulo = str(item.get("rotulo", item.get("campo", "Atributo")) or "Atributo")
            antes = _safe_int(item.get("antes"), 0)
            depois = _safe_int(item.get("depois"), antes)
            delta = _safe_int(item.get("delta"), depois - antes)

            cor_delta = Cores.TEXTO_SECONDARY
            seta = "="
            if delta > 0:
                cor_delta = Cores.VERDE
                seta = "up"
            elif delta < 0:
                cor_delta = Cores.VERMELHO
                seta = "down"

            linha = QGridLayout()
            linha.setHorizontalSpacing(8)
            lbl_rotulo = QLabel(rotulo)
            lbl_rotulo.setFont(Fontes.texto_pequeno())
            lbl_rotulo.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
            linha.addWidget(lbl_rotulo, 0, 0)
            linha.addWidget(self._barra_valor(antes, cor="#3b82f6"), 0, 1)
            linha.addWidget(self._barra_valor(depois, cor=Cores.ACCENT_PRIMARY), 0, 2)
            lbl_delta = QLabel(f"{delta:+d} ({seta})")
            lbl_delta.setFont(Fontes.texto_pequeno())
            lbl_delta.setStyleSheet(f"color: {cor_delta}; border: none; font-weight: 700;")
            linha.addWidget(lbl_delta, 0, 3)
            linha.setColumnStretch(1, 1)
            linha.setColumnStretch(2, 1)
            painel_layout.addLayout(linha)

        resumo = str(self.dados.get("evolucao_resumo", "") or "").strip()
        if resumo:
            lbl_resumo = QLabel(resumo)
            lbl_resumo.setWordWrap(True)
            lbl_resumo.setFont(Fontes.texto_pequeno())
            lbl_resumo.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none;")
            painel_layout.addWidget(lbl_resumo)

        contexto = str(self.dados.get("evolucao_contexto", "") or "").strip()
        if contexto:
            lbl_contexto = QLabel(f'"{contexto}"')
            lbl_contexto.setWordWrap(True)
            lbl_contexto.setFont(Fontes.texto_pequeno())
            lbl_contexto.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
            painel_layout.addWidget(lbl_contexto)

        layout.addWidget(painel, 1)
        return widget

    def _build_tab_mercado(self) -> QWidget:
        narrativo = self.dados.get("mercado_narrativo", {})
        if not isinstance(narrativo, dict) or not narrativo:
            return self._build_tab_texto(self.dados.get("mercado", "Sem dados de mercado."))

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        editor = QTextEdit()
        editor.setReadOnly(True)
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

        linhas: list[str] = []
        transferencias = narrativo.get("transferencias", [])
        aposentadorias = narrativo.get("aposentadorias", [])
        rookies = narrativo.get("rookies", [])

        linhas.append("TRANSFERENCIAS PRINCIPAIS:")
        if isinstance(transferencias, list) and transferencias:
            for item in transferencias[:25]:
                if not isinstance(item, dict):
                    continue
                linhas.append(
                    f"- {item.get('piloto', 'Piloto')}: {item.get('origem', '-')} -> {item.get('destino', '-')}"
                    f" ({item.get('categoria', '-')}) - {item.get('papel', '-')}, {item.get('duracao', 1)} ano(s)"
                )
        else:
            linhas.append("- Sem transferencias relevantes.")

        linhas.append("")
        linhas.append("APOSENTADORIAS:")
        if isinstance(aposentadorias, list) and aposentadorias:
            for item in aposentadorias[:20]:
                if not isinstance(item, dict):
                    continue
                linhas.append(
                    f"- {item.get('piloto', 'Piloto')} ({item.get('idade', 0)}) - "
                    f"{item.get('temporadas', 0)} temporada(s), {item.get('titulos', 0)} titulo(s), "
                    f"{item.get('vitorias', 0)} vitoria(s)"
                )
        else:
            linhas.append("- Nenhuma aposentadoria.")

        linhas.append("")
        linhas.append("ROOKIES:")
        if isinstance(rookies, list) and rookies:
            for item in rookies[:20]:
                if not isinstance(item, dict):
                    continue
                linhas.append(
                    f"- {item.get('piloto', 'Rookie')} ({item.get('idade', 0)}) -> "
                    f"{item.get('equipe', 'Sem equipe')} ({item.get('categoria', '-')})"
                )
        else:
            linhas.append("- Nenhum rookie.")

        linhas.append("")
        linhas.append("SUA EQUIPE:")
        linhas.append(f"Antes: {str(narrativo.get('sua_equipe_antes', '-'))}")
        linhas.append(f"Depois: {str(narrativo.get('sua_equipe_depois', '-'))}")

        editor.setText("\n".join(linhas))
        layout.addWidget(editor, 1)
        return widget

    def _build_tab_promocoes(self) -> QWidget:
        mapa = self.dados.get("promocoes_mapa", {})
        if not isinstance(mapa, dict) or not mapa:
            return self._build_tab_texto(self.dados.get("promocoes", "Sem dados de promocoes."))

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        editor = QTextEdit()
        editor.setReadOnly(True)
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

        linhas: list[str] = []
        for trilha, titulo in (("pro", "TRILHA PRO"), ("elite", "TRILHA ELITE")):
            bloco = mapa.get(trilha, {})
            if not isinstance(bloco, dict):
                continue
            promovidas = bloco.get("promovidas", [])
            rebaixadas = bloco.get("rebaixadas", [])
            linhas.append(titulo)
            linhas.append("PROMOVIDAS:")
            if isinstance(promovidas, list) and promovidas:
                for item in promovidas[:20]:
                    if not isinstance(item, dict):
                        continue
                    destaque = " <SUA EQUIPE>" if bool(item.get("destaque_jogador", False)) else ""
                    linhas.append(
                        f"- {item.get('equipe', 'Equipe')} -> {item.get('destino', '-')}{destaque}"
                    )
            else:
                linhas.append("- Nenhuma")

            linhas.append("REBAIXADAS:")
            if isinstance(rebaixadas, list) and rebaixadas:
                for item in rebaixadas[:20]:
                    if not isinstance(item, dict):
                        continue
                    destaque = " <SUA EQUIPE>" if bool(item.get("destaque_jogador", False)) else ""
                    linhas.append(
                        f"- {item.get('equipe', 'Equipe')} -> {item.get('destino', '-')}{destaque}"
                    )
            else:
                linhas.append("- Nenhuma")
            linhas.append("")

        editor.setText("\n".join(linhas) if linhas else "Sem movimentacoes de promocoes/rebaixamentos.")
        layout.addWidget(editor, 1)
        return widget

    def _label_coluna(self, texto: str) -> QLabel:
        lbl = QLabel(texto)
        lbl.setFont(Fontes.texto_pequeno())
        lbl.setStyleSheet(f"color: {Cores.TEXTO_SECONDARY}; border: none; font-weight: 700;")
        return lbl

    def _barra_valor(self, valor: int, cor: str) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        barra = QProgressBar()
        barra.setRange(0, 100)
        barra.setValue(max(0, min(100, valor)))
        barra.setTextVisible(False)
        barra.setFixedHeight(10)
        barra.setStyleSheet(
            f"""
            QProgressBar {{
                background: #0f1825;
                border: 1px solid {Cores.BORDA};
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: {cor};
                border-radius: 5px;
            }}
            """
        )

        lbl = QLabel(str(valor))
        lbl.setFont(Fontes.texto_pequeno())
        lbl.setStyleSheet(f"color: {Cores.TEXTO_PRIMARY}; border: none;")
        lbl.setFixedWidth(28)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout.addWidget(barra, 1)
        layout.addWidget(lbl)
        return container
