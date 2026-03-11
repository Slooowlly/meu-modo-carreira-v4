from __future__ import annotations

import json
import os
import random
import string
import uuid
from typing import Any

from PySide6.QtWidgets import (
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QWidget,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import (
    Qt,
    QPoint,
    QEvent,
    QTimer,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
)
from shiboken6 import isValid

from Dados.banco import salvar_banco
from Dados.constantes import (
    CAR_INFO,
    GT3_CARROS,
    GT4_CARROS,
    NOMES_CAMPEONATO,
    PISTAS_IRACING,
    PRODUCTION_CAR_CARROS,
)
from Logica.equipes import calcular_pontos_equipes
from Logica.pilotos import obter_pilotos_categoria
from Utils.helpers import obter_nome_categoria


class ToastNotification(QDialog):
    def __init__(
        self,
        parent,
        message,
        duration=4200,
        title="🏁 TUDO PRONTO!",
        details="",
    ):
        super().__init__(parent)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setWindowOpacity(0.0)

        self._duration = max(0, int(duration or 0))
        self._closing = False
        self._usar_blur_parent = True
        self._camadas_ocultas = False
        self._encerrar_rapido = False
        self._duracao_curta_ms = 700
        self._owner_id = uuid.uuid4().hex
        self._backdrop: QWidget | None = None
        self._blur_parent: QGraphicsBlurEffect | None = None
        self._blur_parent_aplicado = False
        self._criar_backdrop()

        layout_raiz = QVBoxLayout(self)
        layout_raiz.setContentsMargins(0, 0, 0, 0)
        layout_raiz.setSpacing(0)

        card = QFrame(self)
        card.setObjectName("toastCard")
        layout_raiz.addWidget(card)
        self._card = card

        layout_card = QHBoxLayout(card)
        layout_card.setContentsMargins(0, 0, 0, 0)
        layout_card.setSpacing(0)

        barra_status = QFrame(card)
        barra_status.setObjectName("toastAccent")
        barra_status.setFixedWidth(6)
        layout_card.addWidget(barra_status)

        conteudo = QFrame(card)
        conteudo.setObjectName("toastContent")
        layout_card.addWidget(conteudo)

        layout_conteudo = QVBoxLayout(conteudo)
        layout_conteudo.setContentsMargins(16, 14, 18, 14)
        layout_conteudo.setSpacing(4)

        largura_texto = 360

        self.label_titulo = QLabel(title, conteudo)
        self.label_titulo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_titulo.setFixedWidth(largura_texto)

        self.label_corpo = QLabel(message, conteudo)
        self.label_corpo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_corpo.setWordWrap(True)
        self.label_corpo.setFixedWidth(largura_texto)

        self.label_detalhes = QLabel(details, conteudo)
        self.label_detalhes.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.label_detalhes.setWordWrap(True)
        self.label_detalhes.setFixedWidth(largura_texto)
        self.label_detalhes.setVisible(bool(str(details).strip()))

        self.setCursor(Qt.PointingHandCursor)
        for widget in (card, barra_status, conteudo, self.label_titulo, self.label_corpo, self.label_detalhes):
            widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        layout_conteudo.addWidget(self.label_titulo)
        layout_conteudo.addWidget(self.label_corpo)
        layout_conteudo.addWidget(self.label_detalhes)

        self.setStyleSheet("""
            QFrame#toastCard {
                background-color: #1B1F26;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 10px;
            }
            QFrame#toastAccent {
                background-color: #4CAF50;
                border: none;
                border-top-left-radius: 10px;
                border-bottom-left-radius: 10px;
            }
            QFrame#toastContent {
                background: transparent;
                border: none;
            }
            QLabel {
                font-family: "Segoe UI", "Segoe UI Emoji", Arial;
                background: transparent;
                border: none;
            }
        """)

        self._shadow_card = QGraphicsDropShadowEffect(self)
        self._shadow_card.setBlurRadius(34.0)
        self._shadow_card.setOffset(0, 10)
        self._shadow_card.setColor(QColor(0, 0, 0, 155))
        self._card.setGraphicsEffect(self._shadow_card)

        self.label_titulo.setStyleSheet(
            "color: #FFFFFF; font-size: 15px; font-weight: 700;"
        )
        self.label_corpo.setStyleSheet(
            "color: #CCCCCC; font-size: 13px; font-weight: 400;"
        )
        self.label_detalhes.setStyleSheet(
            "color: #888888; font-size: 11px; font-weight: 400;"
        )

        self.adjustSize()

        self._margin = 20
        self._entry_offset_y = -18
        self._exit_offset_y = -12
        self._final_pos = QPoint(0, 0)
        self._entry_pos = QPoint(0, 0)
        self._exit_pos = QPoint(0, 0)
        self._atualizar_posicoes()
        self.move(self._entry_pos)

        self._display_timer = QTimer(self)
        self._display_timer.setSingleShot(True)
        self._display_timer.timeout.connect(self._iniciar_animacao_saida)

        # Entrada: slide para cima + fade in
        self._anim_in_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_in_pos.setDuration(280)
        self._anim_in_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_in_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_in_opacity.setDuration(280)
        self._anim_in_opacity.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_in_group = QParallelAnimationGroup(self)
        self._anim_in_group.addAnimation(self._anim_in_pos)
        self._anim_in_group.addAnimation(self._anim_in_opacity)
        self._anim_in_group.finished.connect(self._agendar_animacao_saida)

        # Saida: slide para baixo + fade out
        self._anim_out_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_out_pos.setDuration(220)
        self._anim_out_pos.setEasingCurve(QEasingCurve.InCubic)

        self._anim_out_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_out_opacity.setDuration(220)
        self._anim_out_opacity.setEasingCurve(QEasingCurve.InCubic)

        self._anim_out_group = QParallelAnimationGroup(self)
        self._anim_out_group.addAnimation(self._anim_out_pos)
        self._anim_out_group.addAnimation(self._anim_out_opacity)
        self._anim_out_group.finished.connect(self._finalizar_fechamento)

    def _atualizar_posicoes(self):
        parent = self.parentWidget()
        if parent:
            parent_rect = parent.geometry()
            x = parent_rect.right() - self.width() - self._margin
            y = parent_rect.top() + self._margin
            self._final_pos = QPoint(x, y)
        else:
            self._final_pos = QPoint(self.pos().x(), self.pos().y())

        self._entry_pos = self._final_pos + QPoint(0, self._entry_offset_y)
        self._exit_pos = self._final_pos + QPoint(0, self._exit_offset_y)

    def _criar_backdrop(self):
        parent = self.parentWidget()
        if not parent:
            return

        self._camadas_ocultas = False
        self._backdrop = QWidget(parent)
        self._backdrop.setObjectName("_toast_backdrop_layer")
        self._backdrop.setProperty("_toast_backdrop", True)
        self._backdrop.setProperty("_toast_owner", self._owner_id)
        self._backdrop.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._backdrop.setStyleSheet("background-color: rgba(6, 10, 16, 66);")
        self._backdrop.installEventFilter(self)
        self._backdrop.hide()

    @staticmethod
    def _objeto_qt_valido(obj) -> bool:
        try:
            return obj is not None and isValid(obj)
        except RuntimeError:
            return False

    def _aplicar_blur_parent(self):
        parent = self.parentWidget()
        if not self._objeto_qt_valido(parent) or self._blur_parent_aplicado:
            return
        if not self._usar_blur_parent:
            return

        efeito_parent = parent.graphicsEffect()
        if isinstance(efeito_parent, QGraphicsBlurEffect):
            eh_blur_toast = (
                efeito_parent.objectName() == "_toast_blur_effect"
                or bool(efeito_parent.property("_toast_blur"))
            )
            if eh_blur_toast:
                efeito_parent.setObjectName("_toast_blur_effect")
                efeito_parent.setProperty("_toast_blur", True)
                efeito_parent.setProperty("_toast_owner", self._owner_id)
                self._blur_parent = efeito_parent
                self._blur_parent_aplicado = True
                return
        if efeito_parent is not None:
            return

        self._blur_parent = QGraphicsBlurEffect(parent)
        self._blur_parent.setObjectName("_toast_blur_effect")
        self._blur_parent.setProperty("_toast_blur", True)
        self._blur_parent.setProperty("_toast_owner", self._owner_id)
        self._blur_parent.setBlurRadius(3.8)
        parent.setGraphicsEffect(self._blur_parent)
        self._blur_parent_aplicado = True

    def _remover_blur_parent(self):
        parent = self.parentWidget()
        efeito_parent_ativo = parent.graphicsEffect() if self._objeto_qt_valido(parent) else None

        if self._objeto_qt_valido(parent):
            if isinstance(efeito_parent_ativo, QGraphicsBlurEffect):
                eh_blur_toast = (
                    efeito_parent_ativo.objectName() == "_toast_blur_effect"
                    or bool(efeito_parent_ativo.property("_toast_blur"))
                )
                dono_blur = str(efeito_parent_ativo.property("_toast_owner") or "")
                if eh_blur_toast and dono_blur == self._owner_id:
                    parent.setGraphicsEffect(None)
                    try:
                        efeito_parent_ativo.deleteLater()
                    except RuntimeError:
                        pass

        if (
            self._objeto_qt_valido(self._blur_parent)
            and self._blur_parent is not efeito_parent_ativo
            and str(self._blur_parent.property("_toast_owner") or "") == self._owner_id
        ):
            try:
                self._blur_parent.deleteLater()
            except RuntimeError:
                pass

        self._blur_parent = None
        self._blur_parent_aplicado = False
        if self._objeto_qt_valido(parent):
            parent.update()
            parent.repaint()
            QTimer.singleShot(0, parent.update)

    def _mostrar_backdrop(self):
        parent = self.parentWidget()
        if not self._objeto_qt_valido(parent):
            return

        if not self._objeto_qt_valido(self._backdrop):
            self._backdrop = None
            self._criar_backdrop()
        if not self._objeto_qt_valido(self._backdrop):
            return

        if self._objeto_qt_valido(parent):
            self._backdrop.setGeometry(parent.rect())
        self._aplicar_blur_parent()
        self._backdrop.show()
        self._backdrop.raise_()

    def _ocultar_backdrop(self):
        if self._camadas_ocultas:
            return
        self._camadas_ocultas = True

        parent = self.parentWidget()
        self._remover_blur_parent()
        if self._objeto_qt_valido(self._backdrop):
            try:
                self._backdrop.hide()
                self._backdrop.setParent(None)
                self._backdrop.deleteLater()
            except RuntimeError:
                pass
        self._backdrop = None
        if self._objeto_qt_valido(parent):
            parent.update()
            parent.repaint()
            QTimer.singleShot(0, parent.update)

    def _agendar_animacao_saida(self):
        if self._closing:
            return
        duracao = self._duracao_curta_ms if self._encerrar_rapido else self._duration
        self._display_timer.start(max(0, int(duracao)))

    def _acelerar_fechamento(self):
        if self._closing:
            return
        self._encerrar_rapido = True
        if self._display_timer.isActive():
            restante = self._display_timer.remainingTime()
            if restante < 0 or restante > self._duracao_curta_ms:
                self._display_timer.start(self._duracao_curta_ms)

    def _iniciar_animacao_saida(self):
        if self._closing:
            return
        self._closing = True
        self._display_timer.stop()
        self._anim_in_group.stop()
        self._anim_out_group.stop()

        self._anim_out_pos.setStartValue(self.pos())
        self._anim_out_pos.setEndValue(self._exit_pos)
        self._anim_out_opacity.setStartValue(float(self.windowOpacity()))
        self._anim_out_opacity.setEndValue(0.0)
        self._anim_out_group.start()

    def _finalizar_fechamento(self):
        self._ocultar_backdrop()
        super().close()
        self.deleteLater()

    def showEvent(self, event):
        super().showEvent(event)
        if self._closing:
            return
        self._camadas_ocultas = False

        self._display_timer.stop()
        self._anim_in_group.stop()
        self._anim_out_group.stop()
        self._atualizar_posicoes()
        self._mostrar_backdrop()
        self.raise_()

        self.setWindowOpacity(0.0)
        self.move(self._entry_pos)

        self._anim_in_pos.setStartValue(self._entry_pos)
        self._anim_in_pos.setEndValue(self._final_pos)
        self._anim_in_opacity.setStartValue(0.0)
        self._anim_in_opacity.setEndValue(1.0)
        self._anim_in_group.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self._closing:
            self._iniciar_animacao_saida()
            event.accept()
            return
        super().mousePressEvent(event)

    def eventFilter(self, watched, event):
        if (
            self._objeto_qt_valido(self._backdrop)
            and watched is self._backdrop
            and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick)
        ):
            if not self._closing:
                # Clique fora do card: remove foco visual (blur + escurecimento).
                self._ocultar_backdrop()
                # Encurta bastante o tempo de vida do toast após perder foco.
                self._acelerar_fechamento()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def closeEvent(self, event):
        self._ocultar_backdrop()
        self._backdrop = None
        super().closeEvent(event)


class ExportarImportarMixin:
    """
    Mixin com exportação/importação.
    Assume que a classe final possui:
        - self.banco
        - self.categoria_atual
        - helpers da base em UI.carreira_acoes
    """

    CARROS_IRACING = {**CAR_INFO}

    NOMES_CATEGORIAS = {
        **NOMES_CAMPEONATO,
        "mazda_rookie": "Mazda MX-5 Rookie Cup",
        "mazda_amador": "Mazda MX-5 Championship",
        "toyota_rookie": "Toyota GR86 Rookie Cup",
        "toyota_amador": "Toyota GR86 Cup",
        "bmw_m2": "BMW M2 CS Racing",
        "production_challenger": "Production Car Challenger",
        "gt3": "GT3 Challenge",
        "gt4": "GT4 Series",
    }

    GT3_CARROS = GT3_CARROS
    GT4_CARROS = GT4_CARROS
    PRODUCTION_CAR_CARROS = PRODUCTION_CAR_CARROS
    CATEGORIAS_PRODUCTION_CAR = (
        "mazda_rookie",
        "mazda_amador",
        "toyota_rookie",
        "toyota_amador",
        "bmw_m2",
        "renault_clio",
    )
    NOMES_CARROS_IRACING = {
        "acuransxevo22gt3": "Acura NSX Evo 22 GT3",
        "amvantageevogt3": "Aston Martin Vantage GT3",
        "audir8lmsevo2gt3": "Audi R8 LMS Evo II GT3",
        "bmwm4gt3": "BMW M4 GT3",
        "chevyvettez06rgt3": "Chevrolet Corvette Z06 GT3.R",
        "ferrarievogt3": "Ferrari 296 GT3",
        "fordmustanggt3": "Ford Mustang GT3",
        "lamborghinievogt3": "Lamborghini Huracan GT3 EVO",
        "mclaren720sgt3": "McLaren 720S GT3 EVO",
        "mercedesamgevogt3": "Mercedes-AMG GT3 EVO",
        "porsche992rgt3": "Porsche 911 GT3 R (992)",
        "amvantagegt4": "Aston Martin Vantage GT4",
        "bmwm4evogt4": "BMW M4 GT4 Evo",
        "fordmustanggt4": "Ford Mustang GT4",
        "mclaren570sgt4": "McLaren 570S GT4",
        "mercedesamggt4": "Mercedes-AMG GT4",
        "porsche718gt4": "Porsche 718 Cayman GT4",
    }
    CLIMA_MAP_M5 = {
        "seco": None,
        "nublado": None,
        "chuva leve": "DAMP",
        "chuva": "WET",
        "chuva moderada": "WET",
        "chuva forte": "HEAVY_RAIN",
        "tempestade": "HEAVY_RAIN",
        "dry": None,
        "damp": "DAMP",
        "wet": "WET",
        "heavy rain": "HEAVY_RAIN",
        "heavy_rain": "HEAVY_RAIN",
    }
    # Mapeamento inicial de pais por circuito para ativar "corrida em casa".
    # TODO: expandir conforme novos circuitos forem usados.
    PAIS_POR_TRACK_ID = {
        8: "eua",
        24: "eua",
        53: "inglaterra",
        101: "franca",
        110: "alemanha",
        129: "italia",
    }

    @staticmethod
    def _to_int(valor: Any, padrao: int = 0) -> int:
        try:
            return int(valor)
        except (TypeError, ValueError):
            return int(padrao)

    @staticmethod
    def _normalizar_valor_iracing(valor: Any, padrao: int = 50) -> int:
        try:
            numero = int(round(float(valor)))
        except (TypeError, ValueError):
            numero = int(padrao)
        return max(0, min(100, numero))

    def _normalizar_clima_para_m5(self, clima_raw: Any) -> str | None:
        if clima_raw in (None, "", "-", "None"):
            return None
        chave = str(clima_raw).strip().casefold()
        if chave in {"damp", "wet", "heavy_rain"}:
            return chave.upper()
        return self.CLIMA_MAP_M5.get(chave, None)

    def _resolver_dados_corrida_export(self) -> dict:
        rodada_atual = self._to_int(self.banco.get("rodada_atual", 1), 1)
        calendario = self.banco.get("calendario", [])
        total_corridas = len(calendario) if isinstance(calendario, list) and calendario else 10

        corrida = {}
        indice = rodada_atual - 1
        if isinstance(calendario, list) and 0 <= indice < len(calendario):
            corrida = calendario[indice] or {}
        if not isinstance(corrida, dict):
            corrida = {}

        track_id = (
            corrida.get("trackId")
            or corrida.get("id")
            or corrida.get("track_id")
            or 0
        )
        track_name = (
            corrida.get("circuito")
            or corrida.get("nome")
            or corrida.get("track_name")
            or "Unknown Track"
        )
        clima_exibicao = str(corrida.get("clima", "Seco") or "Seco").strip()
        clima_m5 = self._normalizar_clima_para_m5(clima_exibicao)

        return {
            "rodada_atual": rodada_atual,
            "total_corridas": total_corridas,
            "corrida": corrida,
            "track_id": track_id,
            "track_name": str(track_name),
            "clima_exibicao": clima_exibicao,
            "clima_m5": clima_m5,
        }

    def _resolver_ids_rivais(self, piloto: dict) -> list[str]:
        rivalidades = piloto.get("rivalidades", [])
        if not isinstance(rivalidades, list):
            return []

        rival_ids: list[str] = []
        for rivalidade in rivalidades:
            if isinstance(rivalidade, dict):
                rival_id = rivalidade.get("rival_id", rivalidade.get("piloto_id"))
            else:
                rival_id = rivalidade
            if rival_id in (None, ""):
                continue
            rival_ids.append(str(rival_id))
        return rival_ids

    def _obter_pais_circuito(self, track_id: Any, track_name: str) -> str | None:
        track_id_int = self._to_int(track_id, 0)
        pais = self.PAIS_POR_TRACK_ID.get(track_id_int)
        if pais:
            return pais

        nome = str(track_name or "").casefold()
        if any(token in nome for token in ("summit", "daytona", "road america", "sebring", "indianapolis")):
            return "eua"
        if "brands hatch" in nome or "donington" in nome or "silverstone" in nome:
            return "inglaterra"
        if "spa" in nome:
            return "belgica"
        if "nurburgring" in nome or "hockenheim" in nome:
            return "alemanha"
        if "imola" in nome or "monza" in nome:
            return "italia"
        return None

    def _calcular_max_pontos_por_corrida_categoria(self) -> int:
        try:
            from Logica.categorias import calcular_pontos_corrida

            return int(
                calcular_pontos_corrida(
                    posicao=1,
                    categoria_id=self.categoria_atual,
                    eh_pole=True,
                    volta_rapida=True,
                    posicao_geral=1,
                )
            )
        except Exception:
            return 25

    def _preparar_contexto_export_completo(self, pilotos_exportacao: list[dict]) -> dict:
        from Logica.export import build_pilot_context, build_race_context

        dados_corrida = self._resolver_dados_corrida_export()
        rodada_atual = dados_corrida["rodada_atual"]
        total_corridas = dados_corrida["total_corridas"]
        track_id = dados_corrida["track_id"]
        track_name = dados_corrida["track_name"]
        clima_exibicao = dados_corrida["clima_exibicao"]
        clima_m5 = dados_corrida["clima_m5"]

        pilotos_categoria = obter_pilotos_categoria(self.banco, self.categoria_atual)
        pilotos_ordenados = sorted(
            pilotos_categoria,
            key=lambda piloto: (
                -int(piloto.get("pontos_temporada", 0) or 0),
                -int(piloto.get("vitorias_temporada", 0) or 0),
                -int(piloto.get("podios_temporada", 0) or 0),
                -float(piloto.get("skill", 0) or 0),
                str(piloto.get("nome", "")).casefold(),
            ),
        )

        standings_by_id: dict[str, dict] = {}
        points_by_id: dict[str, int] = {}
        gaps_by_id: dict[str, int] = {}

        pontos_lider = int(pilotos_ordenados[0].get("pontos_temporada", 0) or 0) if pilotos_ordenados else 0
        rodadas_restantes = max(0, total_corridas - rodada_atual)
        pontos_maximos_restantes = rodadas_restantes * self._calcular_max_pontos_por_corrida_categoria()

        for posicao, piloto in enumerate(pilotos_ordenados, start=1):
            piloto_id = str(piloto.get("id"))
            pontos = int(piloto.get("pontos_temporada", 0) or 0)
            gap = max(0, pontos_lider - pontos)
            eliminado = gap > pontos_maximos_restantes
            standings_by_id[piloto_id] = {
                "position": posicao,
                "points": pontos,
                "gap_to_leader": gap,
                "is_eliminated": eliminado,
            }
            points_by_id[piloto_id] = pontos
            gaps_by_id[piloto_id] = gap

        equipes_por_id = {
            str(equipe.get("id")): equipe
            for equipe in self.banco.get("equipes", [])
            if isinstance(equipe, dict)
        }

        def _score_esperado(piloto: dict) -> float:
            equipe = equipes_por_id.get(str(piloto.get("equipe_id")), {})
            car_perf = float(equipe.get("car_performance", 50) or 50)
            skill = float(piloto.get("skill", 50) or 50)
            return (skill * 0.75) + (car_perf * 0.25)

        pilotos_esperados = sorted(
            pilotos_categoria,
            key=lambda piloto: (
                -_score_esperado(piloto),
                -float(piloto.get("skill", 0) or 0),
                str(piloto.get("nome", "")).casefold(),
            ),
        )
        expected_position_by_id = {
            str(piloto.get("id")): idx
            for idx, piloto in enumerate(pilotos_esperados, start=1)
        }

        for piloto_id, info in standings_by_id.items():
            esperado = expected_position_by_id.get(piloto_id, info["position"])
            atual = max(1, info["position"])
            ratio = float(esperado) / float(atual)
            info["team_performance_vs_expectations"] = max(0.4, min(1.6, ratio))

        ids_grid = {str(piloto.get("id")) for piloto in pilotos_categoria if piloto.get("id") is not None}
        rivals_in_race_by_id: dict[str, list[str]] = {}
        rivalries_map: dict[tuple[str, str], int] = {}

        for piloto in pilotos_categoria:
            piloto_id = str(piloto.get("id"))
            rival_ids = self._resolver_ids_rivais(piloto)
            rival_ids_grid = [rid for rid in rival_ids if rid in ids_grid]
            rivals_in_race_by_id[piloto_id] = rival_ids_grid

            rivalidades = piloto.get("rivalidades", [])
            if not isinstance(rivalidades, list):
                continue
            for rivalidade in rivalidades:
                if isinstance(rivalidade, dict):
                    rival_id = rivalidade.get("rival_id", rivalidade.get("piloto_id"))
                    intensidade = self._to_int(rivalidade.get("intensidade", 5), 5) * 10
                else:
                    rival_id = rivalidade
                    intensidade = 50
                if rival_id in (None, ""):
                    continue
                rival_id_str = str(rival_id)
                if rival_id_str not in ids_grid or rival_id_str == piloto_id:
                    continue
                par = tuple(sorted((piloto_id, rival_id_str)))
                rivalries_map[par] = max(rivalries_map.get(par, 0), max(0, min(100, intensidade)))

        active_rivalries = [
            (par[0], par[1], intensidade)
            for par, intensidade in rivalries_map.items()
        ]

        pais_circuito = self._obter_pais_circuito(track_id, track_name)
        home_race_pilots: list[str] = []
        if pais_circuito:
            for piloto in pilotos_categoria:
                piloto_id = str(piloto.get("id"))
                nacionalidade = str(piloto.get("nacionalidade", "")).casefold()
                if pais_circuito in nacionalidade:
                    home_race_pilots.append(piloto_id)

        season_data = {
            "standings_by_id": standings_by_id,
            "expected_position_by_id": expected_position_by_id,
            "rivals_in_race_by_id": rivals_in_race_by_id,
            "home_race_pilots": home_race_pilots,
        }

        championship_payload = {
            "standings": points_by_id,
            "gaps": gaps_by_id,
            "rivalries": active_rivalries,
            "home_race_pilots": home_race_pilots,
        }

        race_ctx = build_race_context(
            category_id=self.categoria_atual,
            track_id=track_id,
            track_name=track_name,
            round_number=rodada_atual,
            total_rounds=total_corridas,
            championship_data=championship_payload,
            weather_data=clima_m5,
        )

        pilot_ctx_by_id: dict[str, Any] = {}
        races_this_season_by_id: dict[str, int] = {}
        for piloto in pilotos_exportacao:
            piloto_id = str(piloto.get("id"))
            pilot_ctx_by_id[piloto_id] = build_pilot_context(
                pilot=piloto,
                season_data=season_data,
                track_id=self._to_int(track_id, 0),
            )
            races_this_season_by_id[piloto_id] = self._to_int(piloto.get("corridas_temporada", 0), 0)

        return {
            "race_ctx": race_ctx,
            "pilot_ctx_by_id": pilot_ctx_by_id,
            "races_this_season_by_id": races_this_season_by_id,
            "track_name": track_name,
            "track_id": track_id,
            "clima_exibicao": clima_exibicao,
            "rodada_atual": rodada_atual,
            "total_corridas": total_corridas,
        }

    def _salvar_relatorio_modificadores(
        self,
        pasta_season: str,
        pilotos_export_data: list,
        contexto_corrida: dict,
    ) -> None:
        if not pilotos_export_data:
            return
        try:
            from Logica.export import generate_modifier_report_text

            cabecalho = [
                "=== MODIFICADORES DA CORRIDA ===",
                (
                    f"Circuito: {contexto_corrida.get('track_name', 'Desconhecido')} | "
                    f"Clima: {contexto_corrida.get('clima_exibicao', 'Seco')} | "
                    f"Rodada {contexto_corrida.get('rodada_atual', '?')}/"
                    f"{contexto_corrida.get('total_corridas', '?')}"
                ),
                "",
            ]
            conteudo = generate_modifier_report_text(pilotos_export_data)
            caminho_relatorio = os.path.join(pasta_season, "modifier_report.txt")
            with open(caminho_relatorio, "w", encoding="utf-8") as arquivo_relatorio:
                arquivo_relatorio.write("\n".join(cabecalho) + conteudo)
            self._persistir_preview_modificadores(
                pilotos_export_data=pilotos_export_data,
                contexto_corrida=contexto_corrida,
            )
        except Exception as erro:
            print(f"Falha ao gerar modifier_report.txt: {erro}")

    @staticmethod
    def _clamp_export_modifier(valor: float, limite: float) -> float:
        return max(-float(limite), min(float(limite), float(valor)))

    def _persistir_preview_modificadores(
        self,
        *,
        pilotos_export_data: list,
        contexto_corrida: dict,
    ) -> None:
        """Persistencia estruturada dos modificadores para exibicao no dialogo da UI."""
        pilotos_por_id = {
            str(p.get("id")): p for p in self.banco.get("pilotos", []) if isinstance(p, dict)
        }
        linhas: list[dict[str, Any]] = []
        for item in pilotos_export_data:
            relatorio = getattr(item, "modifier_report", None)
            piloto_id = str(getattr(item, "pilot_id", "") or "")
            piloto_ref = pilotos_por_id.get(piloto_id, {})
            nome = str(
                getattr(item, "display_name", piloto_ref.get("nome", "Piloto")) or "Piloto"
            )
            equipe_nome = str(piloto_ref.get("equipe_nome", "Equipe") or "Equipe")

            skill_base = float(getattr(item, "original_skill", 0.0) or 0.0)
            skill_final = int(getattr(item, "skill", round(skill_base)) or round(skill_base))

            agg_final = int(getattr(item, "aggression", 50) or 50)
            opt_final = int(getattr(item, "optimism", 50) or 50)
            smo_final = int(getattr(item, "smoothness", 50) or 50)

            agg_total = float(getattr(relatorio, "aggression_total", 0.0) or 0.0) if relatorio else 0.0
            opt_total = float(getattr(relatorio, "optimism_total", 0.0) or 0.0) if relatorio else 0.0
            smo_total = float(getattr(relatorio, "smoothness_total", 0.0) or 0.0) if relatorio else 0.0

            agg_base = int(round(agg_final - self._clamp_export_modifier(agg_total, 25.0)))
            opt_base = int(round(opt_final - self._clamp_export_modifier(opt_total, 20.0)))
            smo_base = int(round(smo_final - self._clamp_export_modifier(smo_total, 20.0)))

            def _serializar_mods(lista_mods) -> list[dict[str, Any]]:
                saida: list[dict[str, Any]] = []
                for mod in (lista_mods or []):
                    valor = float(getattr(mod, "value", 0.0) or 0.0)
                    saida.append(
                        {
                            "fonte": str(getattr(getattr(mod, "source", None), "value", "") or ""),
                            "valor": valor,
                            "descricao": str(getattr(mod, "description", "") or ""),
                        }
                    )
                return saida

            skill_mods = _serializar_mods(getattr(relatorio, "skill_modifiers", []) if relatorio else [])
            agg_mods = _serializar_mods(getattr(relatorio, "aggression_modifiers", []) if relatorio else [])
            opt_mods = _serializar_mods(getattr(relatorio, "optimism_modifiers", []) if relatorio else [])
            smo_mods = _serializar_mods(getattr(relatorio, "smoothness_modifiers", []) if relatorio else [])
            ativo = any(abs(float(mod.get("valor", 0.0) or 0.0)) > 0.01 for mod in (skill_mods + agg_mods + opt_mods + smo_mods))

            linhas.append(
                {
                    "piloto_id": piloto_id,
                    "nome": nome,
                    "equipe_nome": equipe_nome,
                    "skill_base": int(round(skill_base)),
                    "skill_final": int(skill_final),
                    "aggression_base": int(agg_base),
                    "aggression_final": int(agg_final),
                    "optimism_base": int(opt_base),
                    "optimism_final": int(opt_final),
                    "smoothness_base": int(smo_base),
                    "smoothness_final": int(smo_final),
                    "skill_modifiers": skill_mods,
                    "aggression_modifiers": agg_mods,
                    "optimism_modifiers": opt_mods,
                    "smoothness_modifiers": smo_mods,
                    "ativo": bool(ativo),
                }
            )

        linhas.sort(
            key=lambda item: (
                not bool(item.get("ativo", False)),
                -int(item.get("skill_final", 0) or 0),
                str(item.get("nome", "")).casefold(),
            )
        )

        self.banco["modifier_preview"] = {
            "categoria_id": str(getattr(self, "categoria_atual", "") or ""),
            "track_name": str(contexto_corrida.get("track_name", "Pista desconhecida") or "Pista desconhecida"),
            "clima": str(contexto_corrida.get("clima_exibicao", "Seco") or "Seco"),
            "rodada_atual": int(contexto_corrida.get("rodada_atual", self.banco.get("rodada_atual", 1)) or 1),
            "total_corridas": int(contexto_corrida.get("total_corridas", len(self.banco.get("calendario", []))) or len(self.banco.get("calendario", []))),
            "pilotos": linhas,
        }

    def _limpar_toast_atual(self, toast_id=None, *_):
        toast_atual = getattr(self, "_toast_atual", None)
        if toast_atual is None:
            return

        if toast_id is not None and id(toast_atual) != int(toast_id):
            return

        emissor = self.sender()
        if emissor is not None and emissor is not toast_atual:
            return

        self._toast_atual = None

    def _fechar_toasts_ativos(self):
        toasts_ativos = []
        ids_toasts = set()

        for toast in self.findChildren(ToastNotification):
            toast_id = id(toast)
            if toast_id in ids_toasts:
                continue
            ids_toasts.add(toast_id)
            toasts_ativos.append(toast)

        for widget in QApplication.topLevelWidgets():
            if not isinstance(widget, ToastNotification):
                continue
            if widget.parentWidget() is not self:
                continue
            toast_id = id(widget)
            if toast_id in ids_toasts:
                continue
            ids_toasts.add(toast_id)
            toasts_ativos.append(widget)

        toast_atual = getattr(self, "_toast_atual", None)
        if isinstance(toast_atual, ToastNotification):
            toast_id = id(toast_atual)
            if toast_id not in ids_toasts:
                toasts_ativos.append(toast_atual)

        for toast in toasts_ativos:
            try:
                if hasattr(toast, "_display_timer"):
                    toast._display_timer.stop()
                toast.close()
            except RuntimeError:
                pass

        self._resetar_camadas_toast()
        self._toast_atual = None

    def _resetar_camadas_toast(self):
        for backdrop in self.findChildren(QWidget, "_toast_backdrop_layer"):
            try:
                backdrop.hide()
                backdrop.setParent(None)
                backdrop.deleteLater()
            except RuntimeError:
                pass

        for widget in self.findChildren(QWidget):
            if not bool(widget.property("_toast_backdrop")):
                continue
            try:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            except RuntimeError:
                pass

        efeito_parent = self.graphicsEffect()
        if isinstance(efeito_parent, QGraphicsBlurEffect):
            eh_blur_toast = (
                efeito_parent.objectName() == "_toast_blur_effect"
                or bool(efeito_parent.property("_toast_blur"))
            )
            if eh_blur_toast:
                self.setGraphicsEffect(None)
                try:
                    efeito_parent.deleteLater()
                except RuntimeError:
                    pass
        self.update()
        self.repaint()
        QTimer.singleShot(0, self.update)

    def _resetar_camadas_toast_se_pertencer(self, toast_id=None, *_):
        toast_atual = getattr(self, "_toast_atual", None)
        if toast_id is not None and isinstance(toast_atual, ToastNotification):
            if id(toast_atual) != int(toast_id):
                return
        self._resetar_camadas_toast()

    def _agendar_failsafe_camadas_toast(self, toast_id: int, atraso_ms: int = 6500):
        atraso = max(0, int(atraso_ms or 0))

        def _failsafe():
            toast_atual = getattr(self, "_toast_atual", None)
            if isinstance(toast_atual, ToastNotification):
                return
            for widget in QApplication.topLevelWidgets():
                if (
                    isinstance(widget, ToastNotification)
                    and widget.parentWidget() is self
                    and widget.isVisible()
                ):
                    return
            self._resetar_camadas_toast()

        QTimer.singleShot(atraso, _failsafe)

    def _obter_carros_categoria_multimarca(self, categoria_id: str) -> list[dict]:
        if categoria_id == "gt3":
            return [carro.copy() for carro in self.GT3_CARROS]
        if categoria_id == "gt4":
            return [carro.copy() for carro in self.GT4_CARROS]
        return []

    def _formatar_rotulo_carro(self, carro_config: dict) -> str:
        car_path = str(carro_config.get("carPath", "")).strip()
        car_id = int(carro_config.get("carId", 0) or 0)
        nome = self.NOMES_CARROS_IRACING.get(car_path, car_path or "Carro desconhecido")
        return f"{nome} (carId {car_id})"

    def _obter_carro_jogador_salvo(
        self,
        categoria_id: str,
        opcoes_carro: list[dict],
    ) -> dict | None:
        configs = self.banco.get("carro_jogador_por_categoria", {})
        if not isinstance(configs, dict):
            return None

        salvo = configs.get(categoria_id)
        if not isinstance(salvo, dict):
            return None

        car_path = str(salvo.get("carPath", "")).strip()
        try:
            car_id = int(salvo.get("carId", 0) or 0)
            car_class_id = int(salvo.get("carClassId", 0) or 0)
        except (TypeError, ValueError):
            return None

        for opcao in opcoes_carro:
            try:
                opcao_car_id = int(opcao.get("carId", 0) or 0)
                opcao_class_id = int(opcao.get("carClassId", 0) or 0)
            except (TypeError, ValueError):
                continue

            if (
                str(opcao.get("carPath", "")).strip() == car_path
                and opcao_car_id == car_id
                and opcao_class_id == car_class_id
            ):
                return opcao.copy()

        return None

    def _salvar_carro_jogador_categoria(self, categoria_id: str, carro_config: dict) -> None:
        self.banco.setdefault("carro_jogador_por_categoria", {})
        self.banco["carro_jogador_por_categoria"][categoria_id] = {
            "carPath": str(carro_config.get("carPath", "")).strip(),
            "carId": int(carro_config.get("carId", 0) or 0),
            "carClassId": int(carro_config.get("carClassId", 0) or 0),
        }
        salvar_banco(self.banco)

    def _selecionar_carro_jogador_multimarca(self, categoria_id: str) -> bool:
        opcoes_carro = self._obter_carros_categoria_multimarca(categoria_id)
        if not opcoes_carro:
            return True

        carro_salvo = self._obter_carro_jogador_salvo(categoria_id, opcoes_carro)
        if carro_salvo is None:
            carro_salvo = opcoes_carro[0]

        rotulos = [self._formatar_rotulo_carro(carro) for carro in opcoes_carro]
        indice_padrao = 0
        for indice, carro in enumerate(opcoes_carro):
            if (
                str(carro.get("carPath", "")).strip()
                == str(carro_salvo.get("carPath", "")).strip()
            ):
                indice_padrao = indice
                break

        nome_categoria = self.NOMES_CATEGORIAS.get(categoria_id, categoria_id.upper())
        escolha, confirmado = QInputDialog.getItem(
            self,
            "Carro do jogador",
            (
                f"Escolha o carro do jogador para {nome_categoria}.\n"
                "A IA continua multimarca por equipe."
            ),
            rotulos,
            indice_padrao,
            False,
        )
        if not confirmado:
            return False

        try:
            indice_escolhido = rotulos.index(str(escolha))
        except ValueError:
            return False

        self._salvar_carro_jogador_categoria(
            categoria_id,
            opcoes_carro[indice_escolhido],
        )
        return True

    def _obter_pasta_airosters_salva(self) -> str:
        try:
            from Dados.config import obter_pasta_airosters

            pasta = obter_pasta_airosters()
            if pasta:
                return pasta
        except Exception:
            pass

        return str(self.banco.get("pasta_iracing_airosters", "")).strip()

    def _salvar_pasta_airosters(self, pasta: str) -> None:
        pasta = str(pasta or "").strip()
        self.banco["pasta_iracing_airosters"] = pasta
        salvar_banco(self.banco)

        try:
            from Dados.config import definir_pasta_airosters

            definir_pasta_airosters(pasta)
        except Exception:
            pass

    def _obter_pasta_aiseasons_salva(self) -> str:
        try:
            from Dados.config import obter_pasta_aiseasons

            pasta = obter_pasta_aiseasons()
            if pasta:
                return self._resolver_pasta_aiseasons_valida(pasta)
        except Exception:
            pass

        return ""

    def _eh_pasta_aiseasons_temporaria(self, pasta: str) -> bool:
        caminho = str(pasta or "").strip()
        if not caminho:
            return False

        caminho_normpath = os.path.normpath(caminho)
        nome_pasta = os.path.basename(caminho_normpath).casefold()
        nome_pasta_pai = os.path.basename(os.path.dirname(caminho_normpath)).casefold()
        eh_tmp_legado = nome_pasta.startswith(".tmp_aiseasons")
        eh_tmp_organizado = nome_pasta_pai == "tmp" and nome_pasta in {"aiseasons", "aiseasonssync"}
        if not (eh_tmp_legado or eh_tmp_organizado):
            return False

        try:
            raiz_projeto = os.path.normcase(os.path.abspath(os.getcwd()))
            caminho_norm = os.path.normcase(os.path.abspath(caminho))
        except Exception:
            return False

        return caminho_norm.startswith(raiz_projeto)

    def _resolver_pasta_aiseasons_valida(self, pasta: str) -> str:
        caminho = str(pasta or "").strip()
        if not caminho:
            return ""
        if self._eh_pasta_aiseasons_temporaria(caminho):
            return ""
        return caminho

    def _salvar_pasta_aiseasons(self, pasta: str) -> None:
        pasta = self._resolver_pasta_aiseasons_valida(pasta)
        if not pasta:
            return

        try:
            from Dados.config import definir_pasta_aiseasons

            definir_pasta_aiseasons(pasta)
        except Exception:
            pass

        reiniciar_monitor = getattr(self, "_reiniciar_monitor_resultados", None)
        if callable(reiniciar_monitor):
            reiniciar_monitor()

    def _obter_arquivo_season_salvo(self) -> str:
        def _eh_roster_json(caminho: str) -> bool:
            nome_arquivo = os.path.basename(os.path.normpath(str(caminho or "").strip())).casefold()
            return nome_arquivo == "roster.json"

        try:
            from Dados.config import obter_season_atual

            arquivo = obter_season_atual(self.categoria_atual)
            if arquivo:
                caminho = str(arquivo).strip()
                if caminho and not _eh_roster_json(caminho):
                    return caminho
        except Exception:
            pass

        arquivos_por_categoria = self.banco.get("arquivo_season_por_categoria", {})
        if isinstance(arquivos_por_categoria, dict):
            arquivo = arquivos_por_categoria.get(self.categoria_atual, "")
            if arquivo:
                caminho = str(arquivo).strip()
                if caminho and not _eh_roster_json(caminho):
                    return caminho

        caminho = str(self.banco.get("arquivo_season", "")).strip()
        if caminho and not _eh_roster_json(caminho):
            return caminho
        return ""

    def _salvar_arquivo_season_atual(self, arquivo: str) -> None:
        caminho = str(arquivo or "").strip()
        if not caminho:
            return
        if os.path.basename(os.path.normpath(caminho)).casefold() == "roster.json":
            return

        self.banco.setdefault("arquivo_season_por_categoria", {})
        self.banco["arquivo_season_por_categoria"][self.categoria_atual] = caminho
        salvar_banco(self.banco)

        try:
            from Dados.config import definir_season_atual

            definir_season_atual(self.categoria_atual, caminho)
        except Exception:
            pass

    def _salvar_arquivo_roster_atual(self, arquivo: str) -> None:
        caminho = str(arquivo or "").strip()
        if not caminho:
            return

        self.banco.setdefault("arquivo_roster_por_categoria", {})
        self.banco["arquivo_roster_por_categoria"][self.categoria_atual] = caminho
        salvar_banco(self.banco)

    def _obter_evento_jogavel_atual(self) -> dict | None:
        metodo = getattr(self, "_get_proximo_evento_exibicao", None)
        if callable(metodo):
            return metodo()
        return None

    def _evento_pcc_ativo(self) -> bool:
        evento = self._obter_evento_jogavel_atual()
        return bool(evento and evento.get("tipo_evento") == "pcc")

    def _obter_arquivo_season_evento_atual(self) -> str:
        if self._evento_pcc_ativo():
            try:
                from Logica.series_especiais import obter_arquivo_season_pcc

                return obter_arquivo_season_pcc(self.banco)
            except Exception:
                return ""

        return self._obter_arquivo_season_salvo()

    def _obter_limite_ai_exportacao(self, tem_jogador_na_categoria: bool) -> int | None:
        maximos = self.banco.get("max_drivers_por_categoria", {})
        if isinstance(maximos, dict):
            max_drivers = maximos.get(self.categoria_atual)
            try:
                max_drivers_int = int(max_drivers)
            except (TypeError, ValueError):
                max_drivers_int = 0
            if max_drivers_int > 0:
                desconto_jogador = 1 if tem_jogador_na_categoria else 0
                return max(1, max_drivers_int - desconto_jogador)

        try:
            grid_total = int(self.banco.get("pilotos_por_categoria", 20))
        except (TypeError, ValueError):
            grid_total = 20

        if grid_total <= 0:
            return None

        desconto_jogador = 1 if tem_jogador_na_categoria else 0
        return max(1, grid_total - desconto_jogador)

    def _encontrar_pasta_airosters_padrao(self) -> str:
        candidatos = [
            os.path.expanduser("~/OneDrive/Documentos/iRacing/airosters"),
            os.path.expanduser("~/OneDrive/Documents/iRacing/airosters"),
            os.path.expanduser("~/Documents/iRacing/airosters"),
            os.path.expanduser("~/Documentos/iRacing/airosters"),
        ]

        for caminho in candidatos:
            if os.path.isdir(caminho):
                return caminho

        return ""

    def _encontrar_pasta_aiseasons_padrao(self) -> str:
        candidatos = [
            os.path.expanduser("~/OneDrive/Documentos/iRacing/aiseasons"),
            os.path.expanduser("~/OneDrive/Documents/iRacing/aiseasons"),
            os.path.expanduser("~/Documents/iRacing/aiseasons"),
            os.path.expanduser("~/Documentos/iRacing/aiseasons"),
        ]

        for caminho in candidatos:
            if os.path.isdir(caminho):
                return caminho

        return ""

    def _obter_nome_roster_categoria(self, ano: int | None = None) -> str:
        ano_final = int(ano if ano is not None else self.banco.get("ano_atual", 2024))
        nome_categoria = self.NOMES_CATEGORIAS.get(
            self.categoria_atual,
            obter_nome_categoria(self.categoria_atual) or str(self.categoria_atual).upper(),
        )
        return f"{nome_categoria} - {ano_final}"

    def _obter_arquivo_roster_categoria(self, nome_roster: str | None = None) -> str:
        pasta_iracing = self._obter_pasta_airosters_salva()
        if not pasta_iracing:
            return ""

        nome_pasta = str(nome_roster or self._obter_nome_roster_categoria()).strip()
        if not nome_pasta:
            return ""

        return os.path.join(pasta_iracing, nome_pasta, "roster.json")

    def _normalizar_cor_hex(self, cor: str | None, padrao: str = "ffffff") -> str:
        texto = str(cor or "").strip().lstrip("#")

        if len(texto) == 3:
            texto = "".join(ch * 2 for ch in texto)

        if len(texto) != 6:
            return padrao

        if any(ch not in string.hexdigits for ch in texto):
            return padrao

        return texto.lower()

    def _obter_config_carro_padrao(self) -> dict:
        return self.CARROS_IRACING.get(
            self.categoria_atual,
            self.CARROS_IRACING["mazda_rookie"],
        )

    def _mapear_carros_por_equipe(self, pilotos: list[dict], categoria_id: str) -> dict | None:
        if categoria_id == "gt3":
            carros_base = self.GT3_CARROS
        elif categoria_id == "gt4":
            carros_base = self.GT4_CARROS
        else:
            return None

        equipes_unicas: list[tuple[str, str]] = []
        vistos: set[tuple[str, str]] = set()

        for piloto in pilotos:
            equipe_id = str(piloto.get("equipe_id") or "")
            equipe_nome = str(piloto.get("equipe_nome") or "")
            chave = (equipe_id, equipe_nome)
            if chave in vistos:
                continue
            vistos.add(chave)
            equipes_unicas.append(chave)

        equipes_unicas.sort(key=lambda item: (item[1].casefold(), item[0]))

        ano = int(self.banco.get("ano_atual", 2024))
        seed = f"{categoria_id}|{ano}|{len(equipes_unicas)}"
        rng = random.Random(seed)
        carros_disponiveis = [carro.copy() for carro in carros_base]
        rng.shuffle(carros_disponiveis)

        carros_por_equipe: dict[tuple[str, str], dict] = {}
        for indice, chave in enumerate(equipes_unicas):
            carros_por_equipe[chave] = carros_disponiveis[indice % len(carros_disponiveis)]

        return carros_por_equipe

    def _obter_config_carro_piloto(self, piloto: dict, carros_por_equipe: dict | None) -> dict:
        if self.categoria_atual not in {"gt3", "gt4"} or not carros_por_equipe:
            return self._obter_config_carro_padrao()

        chave = (
            str(piloto.get("equipe_id") or ""),
            str(piloto.get("equipe_nome") or ""),
        )
        return carros_por_equipe.get(chave, self._obter_config_carro_padrao())

    def _resumir_carros_multimarca(self, drivers: list[dict], categoria_id: str) -> str:
        carros_usados = sorted({driver["carPath"] for driver in drivers})
        if categoria_id == "gt3":
            return f"Multimarca GT3 ({len(carros_usados)} modelos)"
        if categoria_id == "gt4":
            return f"Multimarca GT4 ({len(carros_usados)} modelos)"
        return f"Multimarca ({len(carros_usados)} modelos)"

    def _obter_cores_equipes(self) -> dict[str, str]:
        cores = {}
        for equipe in self.banco.get("equipes", []):
            equipe_id = str(equipe.get("id", ""))
            if equipe_id:
                cores[equipe_id] = self._normalizar_cor_hex(equipe.get("cor_primaria", "ffffff"))
        return cores

    def _distribuir_carros_equipes(self, pilotos: list[dict]) -> dict | None:
        return self._mapear_carros_por_equipe(pilotos, self.categoria_atual)

    def _exportar_production_car_challenger(
        self,
        pasta_iracing: str,
        ano: int,
        cores_equipes: dict[str, str],
        silencioso: bool = False,
    ) -> tuple[str, int] | None:
        pilotos_multiclasse: list[dict] = []

        if not hasattr(self, "CATEGORIAS_PRODUCTION_CAR"):
            return None

        for categoria_id in self.CATEGORIAS_PRODUCTION_CAR:
            pilotos_categoria = [
                piloto
                for piloto in obter_pilotos_categoria(self.banco, categoria_id)
                if not piloto.get("is_jogador", False)
            ]
            if not pilotos_categoria:
                continue

            limite_categoria = self._obter_limite_ai_exportacao(False)
            if limite_categoria is not None and len(pilotos_categoria) > limite_categoria:
                pilotos_categoria = sorted(
                    pilotos_categoria,
                    key=lambda piloto: (
                        -int(piloto.get("pontos_temporada", 0)),
                        -int(piloto.get("vitorias_temporada", 0)),
                        -int(piloto.get("podios_temporada", 0)),
                        -float(piloto.get("skill", 0)),
                        str(piloto.get("nome", "")).casefold(),
                    ),
                )[:limite_categoria]

            pilotos_multiclasse.extend(pilotos_categoria)

        if not pilotos_multiclasse:
            return None

        nome_season = f"Production Car Challenge - {ano}"
        pasta_season = os.path.join(pasta_iracing, nome_season)
        arquivo = os.path.join(pasta_season, "roster.json")
        os.makedirs(pasta_season, exist_ok=True)

        pilotos_multiclasse.sort(
            key=lambda piloto: (
                self.CATEGORIAS_PRODUCTION_CAR.index(piloto.get("categoria_atual"))
                if piloto.get("categoria_atual") in self.CATEGORIAS_PRODUCTION_CAR
                else len(self.CATEGORIAS_PRODUCTION_CAR),
                -float(piloto.get("skill", 0)),
                str(piloto.get("nome", "")).casefold(),
            )
        )

        try:
            from Logica.export import build_race_context
            race_ctx = build_race_context(
                category_id="production_challenger",
                track_id=0,
                track_name="PCC Event",
                round_number=1,
                total_rounds=8,
                championship_data=None,
                weather_data=None
            )
        except Exception:
            race_ctx = None

        drivers = []
        pilotos_export_data = []
        for indice, piloto in enumerate(pilotos_multiclasse):
            categoria_id = piloto.get("categoria_atual", "mazda_rookie")
            carro_config = self.PRODUCTION_CAR_CARROS.get(
                categoria_id,
                self.PRODUCTION_CAR_CARROS["mazda_rookie"],
            )
            drivers.append(
                self._criar_driver_iracing(
                    piloto,
                    indice,
                    carro_config,
                    cores_equipes,
                    race_ctx,
                    races_this_season=self._to_int(piloto.get("corridas_temporada", 0), 0),
                    pilotos_export_data=pilotos_export_data,
                )
            )

        with open(arquivo, "w", encoding="utf-8") as arquivo_saida:
            json.dump({"drivers": drivers}, arquivo_saida, indent=4, ensure_ascii=True)
        self._salvar_relatorio_modificadores(
            pasta_season=pasta_season,
            pilotos_export_data=pilotos_export_data,
            contexto_corrida={
                "track_name": "PCC Event",
                "clima_exibicao": "Seco",
                "rodada_atual": 1,
                "total_corridas": 8,
            },
        )

        return arquivo, len(drivers)

    def _exportar_roster(self, silencioso: bool = False) -> None:
        tem_jogador_na_categoria = any(
            piloto.get("is_jogador", False)
            and piloto.get("categoria_atual") == self.categoria_atual
            for piloto in self.banco.get("pilotos", [])
        )

        pilotos = [
            piloto
            for piloto in obter_pilotos_categoria(self.banco, self.categoria_atual)
            if not piloto.get("is_jogador", False)
        ]

        limite_ai = self._obter_limite_ai_exportacao(tem_jogador_na_categoria)
        if limite_ai is not None and len(pilotos) > limite_ai:
            pilotos = sorted(
                pilotos,
                key=lambda piloto: (
                    -int(piloto.get("pontos_temporada", 0)),
                    -int(piloto.get("vitorias_temporada", 0)),
                    -int(piloto.get("podios_temporada", 0)),
                    -float(piloto.get("skill", 0)),
                    str(piloto.get("nome", "")).casefold(),
                ),
            )[:limite_ai]

        if not pilotos:
            if not silencioso:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    f"Nenhum piloto de IA encontrado na categoria '{self.categoria_atual}'.",
                )
            return

        pasta_iracing = self._obter_pasta_airosters_salva()
        if not pasta_iracing or not os.path.isdir(pasta_iracing):
            pasta_iracing = self._encontrar_pasta_airosters_padrao()

        if not pasta_iracing:
            QMessageBox.information(
                self,
                "Selecionar Pasta",
                "Selecione a pasta 'airosters' do iRacing.",
            )
            pasta_iracing = QFileDialog.getExistingDirectory(
                self,
                "Selecionar pasta 'airosters' do iRacing",
            )

        if not pasta_iracing:
            return

        self._salvar_pasta_airosters(pasta_iracing)

        ano = int(self.banco.get("ano_atual", 2024))
        nome_categoria = self.NOMES_CATEGORIAS.get(
            self.categoria_atual,
            obter_nome_categoria(self.categoria_atual) or str(self.categoria_atual).upper(),
        )
        nome_season = self._obter_nome_roster_categoria(ano)

        pasta_season = os.path.join(pasta_iracing, nome_season)
        arquivo = os.path.join(pasta_season, "roster.json")

        try:
            os.makedirs(pasta_season, exist_ok=True)
        except OSError as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Não foi possível criar a pasta da season:\n{erro}",
            )
            return

        cores_equipes = self._obter_cores_equipes()
        carros_equipes = self._distribuir_carros_equipes(pilotos) if self.categoria_atual in {"gt3", "gt4"} else None

        # --- MODULE 5 INTEGRATION ---
        try:
            contexto_export = self._preparar_contexto_export_completo(pilotos)
            race_ctx = contexto_export.get("race_ctx")
            pilot_ctx_by_id = contexto_export.get("pilot_ctx_by_id", {})
            races_this_season_by_id = contexto_export.get("races_this_season_by_id", {})
        except Exception as e:
            print(f"Erro ao preparar contexto de exportacao M5: {e}")
            contexto_export = {
                "track_name": "Unknown Track",
                "clima_exibicao": "Seco",
                "rodada_atual": self._to_int(self.banco.get("rodada_atual", 1), 1),
                "total_corridas": len(self.banco.get("calendario", [])),
            }
            race_ctx = None
            pilot_ctx_by_id = {}
            races_this_season_by_id = {}
        # ---------------------------

        drivers = []
        pilotos_export_data = []
        for indice, piloto in enumerate(pilotos):
            carro_config = self._obter_config_carro_piloto(piloto, carros_equipes)
            piloto_id = str(piloto.get("id"))
            drivers.append(
                self._criar_driver_iracing(
                    piloto,
                    indice,
                    carro_config,
                    cores_equipes,
                    race_ctx,
                    pilot_ctx=pilot_ctx_by_id.get(piloto_id),
                    races_this_season=races_this_season_by_id.get(piloto_id),
                    pilotos_export_data=pilotos_export_data,
                )
            )

        try:
            with open(arquivo, "w", encoding="utf-8") as arquivo_saida:
                json.dump({"drivers": drivers}, arquivo_saida, indent=4, ensure_ascii=True)
            self._salvar_relatorio_modificadores(
                pasta_season=pasta_season,
                pilotos_export_data=pilotos_export_data,
                contexto_corrida=contexto_export,
            )
        except OSError as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao salvar roster.json:\n{erro}",
            )
            return

        # Export PCC after the main category if PCC exists
        if hasattr(self, "CATEGORIAS_PRODUCTION_CAR") and self.categoria_atual in self.CATEGORIAS_PRODUCTION_CAR:
            resultado_pcc = self._exportar_production_car_challenger(
                pasta_iracing,
                ano,
                cores_equipes,
                silencioso=silencioso,
            )
            if resultado_pcc:
                arquivo_pcc, qtd_pcc = resultado_pcc
                mensagem = (
                    f"Roster da categoria '{nome_categoria}' exportado com sucesso!\n"
                    f"({len(drivers)} pilotos)\n"
                    f"Salvo em:\n{arquivo}\n\n"
                    f"Roster do Production Car Challenge exportado com sucesso!\n"
                    f"({qtd_pcc} pilotos)\n"
                    f"Salvo em:\n{arquivo_pcc}"
                )
            else:
                mensagem = (
                    f"Roster da categoria '{nome_categoria}' exportado com sucesso!\n"
                    f"({len(drivers)} pilotos)\n"
                    f"Salvo em:\n{arquivo}\n\n"
                    f"(Nenhum piloto encontrado para o Production Car Challenge)"
                )
            self._salvar_arquivo_roster_atual(arquivo)
            if not silencioso:
                QMessageBox.information(
                    self,
                    "Exportação Concluída",
                    mensagem,
                )
        else:
            self._salvar_arquivo_roster_atual(arquivo)
            resumo = self._resumir_carros_multimarca(drivers, self.categoria_atual)
            if not silencioso:
                QMessageBox.information(
                    self,
                    "Exportação Concluída",
                    f"Roster da categoria '{nome_categoria}' exportado com sucesso!\n"
                    f"Veículos: {resumo}\n"
                    f"({len(drivers)} pilotos)\n"
                    f"Salvo em:\n{arquivo}",
                )

    def _criar_driver_iracing(
        self,
        piloto: dict,
        indice: int,
        carro_config: dict,
        cores_equipes: dict[str, str],
        race_ctx=None,
        pilot_ctx=None,
        races_this_season: int | None = None,
        pilotos_export_data: list | None = None,
    ) -> dict:
        nome_completo = str(piloto.get("nome", ""))
        idade = int(piloto.get("idade", 25))

        # --- MODULE 5 INTEGRATION ---
        try:
            from Logica.export import build_pilot_context, export_pilot_data

            if pilot_ctx is None:
                pilot_ctx = build_pilot_context(piloto)
            if races_this_season is None:
                races_this_season = self._to_int(piloto.get("corridas_temporada", 0), 0)

            export_data = export_pilot_data(
                pilot=piloto,
                pilot_ctx=pilot_ctx,
                race_ctx=race_ctx,
                car_number=str(piloto.get("numero", indice + 1)),
                livery={},
                races_this_season=self._to_int(races_this_season, 0),
            )

            skill = int(export_data.skill)
            aggression = int(export_data.aggression)
            optimism = int(export_data.optimism)
            smoothness = int(export_data.smoothness)

            if isinstance(pilotos_export_data, list):
                pilotos_export_data.append(export_data)

            pit_crew = int(piloto.get("pit_crew", 50))
            strategy = int(piloto.get("strategy_risk", 50))

        except Exception as e:
            print(f"Fallback esport_data: {e}")
            skill = self._normalizar_valor_iracing(piloto.get("skill", 50), 50)
            aggression = self._normalizar_valor_iracing(piloto.get("aggression", 50), 50)
            optimism = self._normalizar_valor_iracing(piloto.get("optimism", 50), 50)
            smoothness = self._normalizar_valor_iracing(piloto.get("smoothness", 50), 50)
            pit_crew = int(piloto.get("pit_crew", 50))
            strategy = int(piloto.get("strategy_risk", 50))
        # ---------------------------

        equipe_id = str(piloto.get("equipe_id", ""))
        cor_hex = cores_equipes.get(equipe_id, "FFFFFF")
        seed_base = f"{nome_completo}_{idade}_{piloto.get('nacionalidade', '')}"
        cust_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, seed_base))
        pilot_id = str(piloto.get("id", ""))

        return {
            "driverName": nome_completo,
            "carNumber": str(piloto.get("numero", indice + 1)),
            "carDesign": f"0,{cor_hex},FFFFFF,FFFFFF",
            "suitDesign": f"0,{cor_hex},FFFFFF,FFFFFF",
            "helmetDesign": f"0,{cor_hex},FFFFFF,FFFFFF",
            "carPath": carro_config["carPath"],
            "carId": carro_config["carId"],
            "carClassId": carro_config.get("carClassId") or 74,
            "numberDesign": f"0,0,FFFFFF,{cor_hex},000000",
            "driverSkill": skill,
            "driverAggression": aggression,
            "driverOptimism": optimism,
            "driverSmoothness": smoothness,
            "pitCrewSkill": pit_crew,
            "strategyRiskiness": strategy,
            "driverAge": idade,
            "id": cust_id,
            "custId": cust_id,
            "pilot_id": pilot_id,
            "rowIndex": indice,
        }
    def _validar_calendario_para_exportacao(self) -> tuple[bool, str]:
        try:
            from Logica.aiseason import categoria_tem_calendario_predefinido

            if categoria_tem_calendario_predefinido(self.categoria_atual):
                return True, ""
        except Exception:
            pass

        calendario = self.banco.get("calendario", [])
        if not isinstance(calendario, list) or not calendario:
            return (
                False,
                "Calendario vazio: adicione corridas antes de exportar a AI Season.",
            )

        for indice, corrida in enumerate(calendario, start=1):
            if not isinstance(corrida, dict):
                return (
                    False,
                    f"Calendario invalido: a corrida {indice} nao possui dados validos.",
                )

            if corrida.get("trackId") in (None, "", "-"):
                return (
                    False,
                    f"Calendario invalido: a corrida {indice} nao possui trackId.",
                )

            if corrida.get("voltas") in (None, "", "-"):
                return (
                    False,
                    f"Calendario invalido: a corrida {indice} nao possui voltas.",
                )

        return True, ""

    def _nome_pista_por_track_id(self, track_id: int | str | None) -> str:
        try:
            track_int = int(track_id)
        except (TypeError, ValueError):
            return f"Track ID {track_id if track_id not in (None, '') else 'N/D'}"

        for pista in PISTAS_IRACING:
            if int(pista.get("trackId", -1)) == track_int:
                return str(pista.get("nome", f"Track ID {track_int}"))

        return f"Track ID {track_int}"

    def _extrair_voltas_corrida_importada(self, corrida: dict) -> int | str:
        voltas_validas: list[int] = []
        for resultado in corrida.get("resultados", []):
            try:
                voltas = int(resultado.get("voltas", 0))
            except (TypeError, ValueError):
                continue
            if voltas > 0:
                voltas_validas.append(voltas)

        return max(voltas_validas) if voltas_validas else "-"

    def _exportar_aiseason(self, silencioso: bool = False) -> None:
        categoria_id = str(getattr(self, "categoria_atual", "") or "").strip()
        if not categoria_id:
            QMessageBox.warning(
                self,
                "Aviso",
                "Categoria atual invalida para exportacao da Season.",
            )
            return

        calendario_ok, erro_calendario = self._validar_calendario_para_exportacao()
        if not calendario_ok:
            QMessageBox.warning(self, "Calendario invalido", erro_calendario)
            return

        pasta_aiseasons = self._obter_pasta_aiseasons_salva()
        if not pasta_aiseasons or not os.path.isdir(pasta_aiseasons):
            pasta_aiseasons = self._encontrar_pasta_aiseasons_padrao()

        if not pasta_aiseasons:
            QMessageBox.information(
                self,
                "Selecionar Pasta",
                "Selecione a pasta 'aiseasons' do iRacing.",
            )
            pasta_aiseasons = QFileDialog.getExistingDirectory(
                self,
                "Selecionar pasta 'aiseasons' do iRacing",
            )

        if not pasta_aiseasons:
            return

        try:
            os.makedirs(pasta_aiseasons, exist_ok=True)
        except OSError as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Nao foi possivel acessar a pasta aiseasons:\n{pasta_aiseasons}\n\nErro: {erro}",
            )
            return

        self._salvar_pasta_aiseasons(pasta_aiseasons)

        if categoria_id in {"gt3", "gt4"}:
            if not self._selecionar_carro_jogador_multimarca(categoria_id):
                return

        nome_roster = self._obter_nome_roster_categoria()
        
        self._exportar_roster(silencioso=True)
        arquivo_roster = self._obter_arquivo_roster_categoria(nome_roster)

        if not arquivo_roster or not os.path.isfile(arquivo_roster):
            QMessageBox.warning(
                self,
                "Aviso",
                "Nao foi possivel gerar/encontrar o roster.json antes da AI Season.",
            )
            return

        try:
            from Logica.aiseason import gerar_aiseason
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Modulo de exportacao de Season nao encontrado.",
            )
            return

        resultado = gerar_aiseason(self.banco, categoria_id, nome_roster)
        if not resultado.get("sucesso", False):
            QMessageBox.critical(
                self,
                "Erro",
                str(resultado.get("erro", "Falha desconhecida ao exportar AI Season.")),
            )
            return

        arquivo = str(resultado.get("arquivo", "")).strip()
        if not arquivo:
            QMessageBox.critical(
                self,
                "Erro",
                "Exportacao concluida sem caminho de arquivo retornado.",
            )
            return

        self.banco["arquivo_season"] = arquivo
        self.banco.setdefault("arquivo_season_por_categoria", {})
        self.banco["arquivo_season_por_categoria"][categoria_id] = arquivo
        salvar_banco(self.banco)

        self._salvar_pasta_aiseasons(os.path.dirname(arquivo))

        resumo_carro_jogador = ""
        if categoria_id in {"gt3", "gt4"}:
            opcoes_carro = self._obter_carros_categoria_multimarca(categoria_id)
            carro_escolhido = self._obter_carro_jogador_salvo(categoria_id, opcoes_carro)
            if carro_escolhido:
                resumo_carro_jogador = (
                    f"Carro do jogador: {self._formatar_rotulo_carro(carro_escolhido)}\n"
                )

        if not silencioso:
            QMessageBox.information(
                self,
                "Exportado",
                "Season exportada e selecionada com sucesso.\n\n"
                f"Roster: {nome_roster}\n"
                f"{resumo_carro_jogador}"
                f"Arquivo: {arquivo}",
            )
        else:
            try:
                rodada_atual = int(self.banco.get("rodada_atual", 1))
                nome_pista = "Pista desconhecida"
                detalhes_toast = ""
                
                calendario = self.banco.get("calendario", [])
                if calendario and len(calendario) >= rodada_atual:
                    etapa = calendario[rodada_atual - 1]
                    
                    pista_id = etapa.get("id")
                    nome_pista = etapa.get("nome") or etapa.get("circuito")
                    if not nome_pista and pista_id not in (None, "", "-"):
                        nome_pista = self._nome_pista_por_track_id(pista_id)
                            
                    if not nome_pista:
                         nome_pista = str(pista_id)
                        
                    voltas = etapa.get("voltas", "-")
                    clima = str(etapa.get("clima", "-") or "-").strip()
                    temperatura = str(etapa.get("temperatura", "-") or "-").strip()

                    detalhes = []
                    if str(voltas).strip() not in {"", "-"}:
                        detalhes.append(f"⏱ {voltas} Voltas")

                    if clima not in {"", "-"}:
                        clima_norm = clima.casefold()
                        if "chuva" in clima_norm or "rain" in clima_norm or "molhado" in clima_norm:
                            icone_clima = "☔"
                        elif "nublado" in clima_norm or "cloud" in clima_norm:
                            icone_clima = "☁"
                        else:
                            icone_clima = "☀"
                        detalhes.append(f"{icone_clima} {clima}")

                    if temperatura not in {"", "-"}:
                        temp_formatada = temperatura.replace("º", "").replace("°", "").replace("C", "").strip()
                        if temp_formatada:
                            detalhes.append(f"🌡 {temp_formatada}°C")

                    detalhes_toast = "   •   ".join(detalhes)

                corpo_toast = f"A corrida em {nome_pista} foi configurada no iRacing."
                titulo_toast = "🏁 TUDO PRONTO!"
                    
                self._fechar_toasts_ativos()
                    
                self._toast_atual = ToastNotification(
                    self,
                    corpo_toast,
                    4200,
                    title=titulo_toast,
                    details=detalhes_toast,
                )
                toast_id = id(self._toast_atual)
                self._toast_atual.destroyed.connect(
                    lambda *_args, tid=toast_id: self._resetar_camadas_toast_se_pertencer(tid)
                )
                self._toast_atual.destroyed.connect(
                    lambda *_args, tid=toast_id: self._limpar_toast_atual(tid)
                )
                self._toast_atual.show()
                self._agendar_failsafe_camadas_toast(toast_id, atraso_ms=7000)
                
            except Exception as e:
                print(f"Erro ao mostrar popup: {e}")
                QMessageBox.information(self, "Tudo pronto", "A próxima corrida está configurada no iRacing!")

    def _importar_resultado(self) -> None:
        pasta_inicial = self._obter_pasta_aiseasons_salva()

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de resultado",
            pasta_inicial,
            "JSON Files (*.json);;All Files (*)",
        )

        if not arquivo:
            return

        try:
            from Logica.importador import carregar_arquivo_iracing, extrair_corridas
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Modulo de importacao nao encontrado.",
            )
            return

        dados = carregar_arquivo_iracing(arquivo)
        if not dados:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nao foi possivel ler o arquivo de season selecionado.",
            )
            return

        corridas = extrair_corridas(dados)
        if not corridas:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nenhuma corrida valida foi encontrada no arquivo selecionado.",
            )
            return

        if self._evento_pcc_ativo():
            try:
                from Logica.series_especiais import definir_arquivo_season_pcc
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "Modulo do PCC nao encontrado.",
                )
                return

            definir_arquivo_season_pcc(self.banco, arquivo, corridas)
            salvar_banco(self.banco)

            try:
                from Dados.config import definir_pasta_aiseasons

                definir_pasta_aiseasons(os.path.dirname(arquivo))
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Selecionado",
                "Arquivo selecionado para o Production Car Challenge:\n"
                f"{arquivo}\n\nCorridas detectadas: {len(corridas)}",
            )
            return

        self.banco["arquivo_season"] = arquivo
        self.banco.setdefault("arquivo_season_por_categoria", {})
        self.banco["arquivo_season_por_categoria"][self.categoria_atual] = arquivo
        self.banco.setdefault("max_drivers_por_categoria", {})
        self.banco["max_drivers_por_categoria"][self.categoria_atual] = int(
            dados.get("max_drivers", 0) or 0
        )
        self.banco["total_rodadas"] = len(corridas)
        calendario = []
        for indice, corrida in enumerate(corridas, start=1):
            track_id_raw = corrida.get("track_id", "N/D")
            try:
                track_id = int(track_id_raw)
            except (TypeError, ValueError):
                track_id = track_id_raw
            calendario.append(
                {
                    "nome": f"Rodada {indice}",
                    "circuito": self._nome_pista_por_track_id(track_id),
                    "trackId": track_id,
                    "voltas": self._extrair_voltas_corrida_importada(corrida),
                    "clima": "-",
                    "temperatura": "-",
                }
            )
        self.banco["calendario"] = calendario
        salvar_banco(self.banco)

        try:
            from Dados.config import definir_season_atual

            definir_season_atual(self.categoria_atual, arquivo)
        except Exception:
            pass

        try:
            from Dados.config import definir_pasta_aiseasons

            definir_pasta_aiseasons(os.path.dirname(arquivo))
        except Exception:
            pass

        QMessageBox.information(
            self,
            "Selecionado",
            f"Arquivo selecionado:\n{arquivo}\n\nCorridas detectadas: {len(corridas)}",
        )

    def _sincronizar_resultado_iracing(self) -> None:
        categoria_id = str(getattr(self, "categoria_atual", "") or "").strip()
        if not categoria_id:
            QMessageBox.warning(
                self,
                "Aviso",
                "Categoria atual invalida para sincronizacao de resultado.",
            )
            return

        if self._temporada_concluida():
            QMessageBox.information(
                self,
                "Temporada concluida",
                "A temporada ja foi concluida. Finalize a temporada para continuar.",
            )
            return

        try:
            from Logica.importador import ler_resultado_aiseason
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Modulo de sincronizacao de AI Season nao encontrado.",
            )
            return

        resultado = ler_resultado_aiseason(self.banco, categoria_id)
        if not resultado.get("sucesso", False):
            aviso = str(resultado.get("aviso", "")).strip()
            erro = str(resultado.get("erro", "")).strip()
            if aviso:
                QMessageBox.information(self, "Aguardando resultado", aviso)
                return

            QMessageBox.warning(
                self,
                "Aviso",
                erro or "Nao foi possivel sincronizar o resultado da rodada atual.",
            )
            return

        classificacao = resultado.get("classificacao", [])
        if not isinstance(classificacao, list) or not classificacao:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nao foi encontrada classificacao valida para aplicar.",
            )
            return

        try:
            rodada_resultado = int(resultado.get("rodada", self.banco.get("rodada_atual", 1)))
        except (TypeError, ValueError):
            rodada_resultado = int(self.banco.get("rodada_atual", 1) or 1)

        pontos_antes = self._snapshot_pontos_categoria(self.categoria_atual)
        lesoes_antes = self._snapshot_lesoes_categoria(self.categoria_atual)
        ordens_antes = self._snapshot_ordens_hierarquia_categoria(self.categoria_atual)

        corrida_ref: dict[str, Any] = {}
        calendario = self.banco.get("calendario", [])
        if isinstance(calendario, list):
            indice_rodada = rodada_resultado - 1
            if 0 <= indice_rodada < len(calendario):
                corrida_item = calendario[indice_rodada]
                if isinstance(corrida_item, dict):
                    corrida_ref = dict(corrida_item)

        aplicados = self._aplicar_classificacao_por_nome(
            classificacao,
            rodada=rodada_resultado,
            foi_corrida_jogador=True,
        )
        if aplicados <= 0:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nenhum resultado pode ser aplicado.\n"
                "Verifique nomes de pilotos e categoria atual.",
            )
            return

        calcular_pontos_equipes(self.banco, self.categoria_atual)
        simular_paralelo = getattr(self, "_simular_rodada_todas_categorias", None)
        resumo_outras_raw: dict[str, Any] = {}
        if callable(simular_paralelo):
            retorno = simular_paralelo(rodada_referencia=int(self.banco.get("rodada_atual", 1)))
            if isinstance(retorno, dict):
                resumo_outras_raw = retorno
        self._avancar_rodada()
        self._atualizar_tudo()

        outras_categorias: list[dict[str, Any]] = []
        for categoria_aux, info in resumo_outras_raw.items():
            if not isinstance(info, dict):
                continue
            outras_categorias.append(
                {
                    "categoria_id": categoria_aux,
                    "categoria_nome": obter_nome_categoria(str(categoria_aux)),
                    "rodada": int(info.get("rodada", 0) or 0),
                    "vencedor": str(info.get("vencedor", "Sem vencedor") or "Sem vencedor"),
                }
            )

        self._abrir_resultado_corrida_detalhado(
            classificacao=classificacao,
            corrida=corrida_ref,
            categoria_id=self.categoria_atual,
            rodada=rodada_resultado,
            pontos_antes=pontos_antes,
            lesoes_antes=lesoes_antes,
            ordens_antes=ordens_antes,
            outras_categorias=outras_categorias,
        )

    def _aplicar_resultado_importado(
        self,
        resultado: dict,
        retornar_classificacao: bool = False,
    ) -> int | tuple[int, list[dict[str, Any]]]:
        resultados = resultado.get("resultados", [])
        melhor_nome = None
        melhor_tempo = None
        for entrada in resultados:
            if bool(entrada.get("dnf", False)):
                continue
            try:
                tempo = float(entrada.get("melhor_volta", -1))
            except (TypeError, ValueError):
                continue
            if tempo <= 0:
                continue
            if melhor_tempo is None or tempo < melhor_tempo:
                melhor_tempo = tempo
                melhor_nome = entrada.get("nome", "")

        classificacao = []
        for entrada in resultados:
            nome = entrada.get("nome", "")
            classificacao.append(
                {
                    "piloto": nome,
                    "dnf": bool(entrada.get("dnf", False)),
                    "volta_rapida": bool(nome and nome == melhor_nome),
                }
            )
        aplicados = self._aplicar_classificacao_por_nome(
            classificacao,
            rodada=int(self.banco.get("rodada_atual", 1) or 1),
            foi_corrida_jogador=True,
        )
        calcular_pontos_equipes(self.banco, self.categoria_atual)
        if retornar_classificacao:
            return aplicados, classificacao
        return aplicados

    def _proximo_resultado(self) -> None:
        evento = self._obter_evento_jogavel_atual()
        evento_pcc = bool(evento and evento.get("tipo_evento") == "pcc")

        if self._temporada_concluida() and not evento_pcc:
            QMessageBox.information(
                self,
                "Temporada concluida",
                "A ultima corrida ja foi processada. Finalize a temporada para continuar.",
            )
            return

        arquivo = self._obter_arquivo_season_evento_atual()
        if not arquivo or not os.path.isfile(arquivo):
            mensagem = (
                "Nenhum arquivo de season configurado para esta categoria.\n"
                "Exporte a Season primeiro."
            )
            if evento_pcc:
                mensagem = (
                    "Nenhum arquivo de season do PCC selecionado.\n"
                    "Defina o arquivo da season do PCC antes de continuar."
                )
            QMessageBox.warning(self, "Aviso", mensagem)
            return

        try:
            from Logica.importador import carregar_arquivo_iracing, extrair_corridas
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Modulo de importacao nao encontrado.",
            )
            return

        dados = carregar_arquivo_iracing(arquivo)
        if not dados:
            QMessageBox.critical(
                self,
                "Erro",
                "Erro ao ler o arquivo de season selecionado.",
            )
            return

        corridas = extrair_corridas(dados)
        rodada = int(evento.get("rodada", 1)) if evento_pcc else int(self.banco.get("rodada_atual", 1))
        indice_corrida = rodada - 1
        resultado = corridas[indice_corrida] if 0 <= indice_corrida < len(corridas) else None

        if resultado is None:
            QMessageBox.warning(
                self,
                "Aviso",
                f"Resultado da rodada {rodada} nao encontrado no arquivo.",
            )
            return

        pontos_antes = self._snapshot_pontos_categoria(self.categoria_atual)
        lesoes_antes = self._snapshot_lesoes_categoria(self.categoria_atual)
        ordens_antes = self._snapshot_ordens_hierarquia_categoria(self.categoria_atual)

        if evento_pcc:
            try:
                from Logica.series_especiais import aplicar_resultado_pcc
            except ImportError:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "Modulo do PCC nao encontrado.",
                )
                return

            classificacao = []
            for entrada in resultado.get("resultados", []):
                classificacao.append(
                    {
                        "piloto": entrada.get("nome", ""),
                        "dnf": bool(entrada.get("dnf", False)),
                    }
                )

            aplicados = aplicar_resultado_pcc(
                self.banco,
                classificacao,
                origem="importada",
            )
        else:
            retorno_importado = self._aplicar_resultado_importado(
                resultado,
                retornar_classificacao=True,
            )
            if (
                isinstance(retorno_importado, tuple)
                and len(retorno_importado) == 2
            ):
                aplicados = int(retorno_importado[0] or 0)
                classificacao = (
                    retorno_importado[1]
                    if isinstance(retorno_importado[1], list)
                    else []
                )
            else:
                aplicados = int(retorno_importado or 0)
                classificacao = []

        if aplicados <= 0:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nenhum resultado pode ser aplicado.\n"
                "Verifique nomes de pilotos e categoria atual.",
            )
            return

        resumo_outras_raw: dict[str, Any] = {}
        if not evento_pcc:
            simular_paralelo = getattr(self, "_simular_rodada_todas_categorias", None)
            if callable(simular_paralelo):
                retorno = simular_paralelo(rodada_referencia=int(self.banco.get("rodada_atual", 1)))
                if isinstance(retorno, dict):
                    resumo_outras_raw = retorno
            self._avancar_rodada()
        else:
            salvar_banco(self.banco)
        self._atualizar_tudo()

        outras_categorias: list[dict[str, Any]] = []
        for categoria_aux, info in resumo_outras_raw.items():
            if not isinstance(info, dict):
                continue
            outras_categorias.append(
                {
                    "categoria_id": categoria_aux,
                    "categoria_nome": obter_nome_categoria(str(categoria_aux)),
                    "rodada": int(info.get("rodada", 0) or 0),
                    "vencedor": str(info.get("vencedor", "Sem vencedor") or "Sem vencedor"),
                }
            )

        corrida_ref = {}
        if isinstance(self.banco.get("calendario", []), list):
            indice = rodada - 1
            calendario = self.banco.get("calendario", [])
            if isinstance(calendario, list) and 0 <= indice < len(calendario):
                item_corrida = calendario[indice]
                if isinstance(item_corrida, dict):
                    corrida_ref = dict(item_corrida)

        self._abrir_resultado_corrida_detalhado(
            classificacao=classificacao if isinstance(classificacao, list) else [],
            corrida=corrida_ref,
            categoria_id=self.categoria_atual,
            rodada=rodada,
            pontos_antes=pontos_antes,
            lesoes_antes=lesoes_antes,
            ordens_antes=ordens_antes,
            outras_categorias=outras_categorias,
        )

