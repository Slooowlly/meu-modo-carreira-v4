"""Acoes de simulacao da carreira."""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox

from Dados.constantes import CATEGORIAS, CATEGORIAS_CONFIG
from Dados.banco import salvar_banco
from Logica.equipes import calcular_pontos_equipes
from Logica.pilotos import obter_pilotos_categoria


class SimularMixin:
    """
    Mixin de simulacao de corridas.
    Assume helpers da base em UI.carreira_acoes.
    """

    def _obter_total_corridas_categoria(self, categoria_id: str) -> int:
        cfg = CATEGORIAS_CONFIG.get(str(categoria_id or "").strip(), {})
        try:
            total_cfg = int(cfg.get("num_corridas", 0) or 0)
        except (TypeError, ValueError):
            total_cfg = 0
        if total_cfg > 0:
            return total_cfg

        try:
            total_geral = int(self.banco.get("total_rodadas", 24))
        except (TypeError, ValueError):
            total_geral = 24
        return max(1, total_geral)

    def _obter_rodada_categoria(self, categoria_id: str) -> int:
        pilotos = [
            piloto
            for piloto in obter_pilotos_categoria(self.banco, categoria_id)
            if isinstance(piloto, dict) and not bool(piloto.get("aposentado", False))
        ]
        if not pilotos:
            return 0
        corridas = [int(p.get("corridas_temporada", 0) or 0) for p in pilotos]
        if not corridas:
            return 0
        return max(0, min(corridas))

    def _simular_rodada_todas_categorias(
        self,
        rodada_referencia: int | None = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Avanca categorias nao ativas ate a rodada de referencia.

        Nota: neste momento todas usam simulacao completa do M4.
        """
        from Logica.simulacao import simular_corrida_categoria_detalhada

        categoria_jogador = str(self.categoria_atual or "").strip()
        try:
            alvo = int(rodada_referencia if rodada_referencia is not None else self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            alvo = 1
        alvo = max(1, alvo)

        simuladas_por_categoria: dict[str, dict[str, Any]] = {}

        for categoria in CATEGORIAS:
            categoria_id = str(categoria.get("id", "") or "").strip()
            if not categoria_id or categoria_id == categoria_jogador:
                continue

            total_corridas = self._obter_total_corridas_categoria(categoria_id)
            rodada_atual_categoria = self._obter_rodada_categoria(categoria_id)
            if rodada_atual_categoria >= total_corridas:
                continue

            simuladas = 0
            ultimo_vencedor = ""
            ultima_rodada = 0
            while rodada_atual_categoria < alvo and rodada_atual_categoria < total_corridas:
                try:
                    resultado_payload = simular_corrida_categoria_detalhada(self.banco, categoria_id)
                except Exception:
                    break
                resultado = resultado_payload.get("classificacao", []) if isinstance(resultado_payload, dict) else []
                if not isinstance(resultado, list) or not resultado:
                    break

                rodada_aplicacao = rodada_atual_categoria + 1
                ultima_rodada = rodada_aplicacao
                vencedor = next(
                    (
                        str(item.get("piloto_nome", item.get("piloto", "Piloto")) or "Piloto")
                        for item in resultado
                        if isinstance(item, dict) and not bool(item.get("dnf", False))
                    ),
                    "",
                )
                if vencedor:
                    ultimo_vencedor = vencedor
                aplicar_categoria = getattr(self, "_aplicar_classificacao_categoria", None)
                if callable(aplicar_categoria):
                    aplicados = aplicar_categoria(
                        categoria_id=categoria_id,
                        classificacao=resultado,
                        rodada=rodada_aplicacao,
                    )
                else:
                    categoria_backup = str(self.categoria_atual or "")
                    try:
                        self.categoria_atual = categoria_id
                        aplicados = self._aplicar_classificacao_por_id(
                            resultado,
                            rodada=rodada_aplicacao,
                            foi_corrida_jogador=False,
                        )
                    finally:
                        self.categoria_atual = categoria_backup

                if int(aplicados or 0) <= 0:
                    break

                corrida_ref: dict[str, Any] = {}
                calendario = self.banco.get("calendario", [])
                if (
                    isinstance(calendario, list)
                    and rodada_aplicacao > 0
                    and rodada_aplicacao <= len(calendario)
                    and isinstance(calendario[rodada_aplicacao - 1], dict)
                ):
                    corrida_ref = dict(calendario[rodada_aplicacao - 1])

                registrar_resultado = getattr(self, "_registrar_resultado_categoria_ui", None)
                if callable(registrar_resultado):
                    registrar_resultado(
                        categoria_id=categoria_id,
                        rodada=rodada_aplicacao,
                        corrida=corrida_ref,
                        classificacao=resultado,
                    )

                registrar_noticias = getattr(self, "_registrar_noticias_pos_corrida", None)
                if callable(registrar_noticias):
                    registrar_noticias(
                        categoria_id=categoria_id,
                        rodada=rodada_aplicacao,
                        corrida=corrida_ref,
                        classificacao=resultado,
                        lesoes=[],
                        ordens=[],
                        outras_categorias=[],
                    )

                calcular_pontos_equipes(self.banco, categoria_id)
                rodada_atual_categoria += 1
                simuladas += 1

            if simuladas > 0:
                simuladas_por_categoria[categoria_id] = {
                    "simuladas": simuladas,
                    "rodada": ultima_rodada,
                    "vencedor": ultimo_vencedor,
                }

        return simuladas_por_categoria

    def _simular_classificacao(self, *, retornar_resultado: bool = False) -> list[dict[str, Any]] | None:
        corrida = self._get_corrida_atual()
        if not corrida:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nao ha corrida disponivel para classificar.",
            )
            return None

        try:
            from Logica.simulacao import simular_classificacao_categoria

            grid = simular_classificacao_categoria(self.banco, self.categoria_atual)
            if not isinstance(grid, list) or not grid:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "A classificacao nao retornou resultados validos.",
                )
                return None

            if retornar_resultado:
                return grid

            linhas = [f"Classificacao: {corrida.get('nome', 'Sessao')}", ""]
            for entrada in grid[:20]:
                if not isinstance(entrada, dict):
                    continue
                posicao = int(entrada.get("posicao", len(linhas)))
                piloto = str(entrada.get("piloto_nome", "Piloto sem nome"))
                equipe = str(entrada.get("equipe_nome", "Equipe"))
                classe = str(entrada.get("classe", "") or "").strip()
                score = float(entrada.get("quali_score", 0.0) or 0.0)
                extra_classe = f" [{classe.upper()}]" if classe else ""
                linhas.append(
                    f"P{posicao:02d}  {piloto}{extra_classe} - {equipe} (score {score:.2f})"
                )

            QMessageBox.information(
                self,
                "Grid de Largada",
                "\n".join(linhas),
            )
            return None
        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao simular classificacao:\n{erro}",
            )
            return None

    def _simular_corrida(self) -> None:
        evento = self._get_proximo_evento_exibicao()
        evento_pcc = bool(evento and evento.get("tipo_evento") == "pcc")

        if self._temporada_concluida() and not evento_pcc:
            QMessageBox.information(
                self,
                "Temporada concluida",
                "A ultima corrida ja foi processada. Finalize a temporada para continuar.",
            )
            return

        corrida = evento if evento_pcc else self._get_corrida_atual()
        if not corrida:
            QMessageBox.warning(
                self,
                "Aviso",
                "Nao ha corrida disponivel para simular.",
            )
            return

        if not evento_pcc and self._corrida_requer_pista_nao_possuida(corrida):
            circuito = str(corrida.get("circuito", "Pista desconhecida") or "Pista desconhecida")
            pista_slug = self._id_pista_cobranca_corrida(corrida)

            dialogo = QMessageBox(self)
            dialogo.setIcon(QMessageBox.Warning)
            dialogo.setWindowTitle("Conteudo de Pista")
            dialogo.setText(
                "⚠️ Esta corrida usa uma pista nao marcada como possuida.\n\n"
                f"Pista: {circuito}\n"
                "Voce pode simular normalmente ou confirmar que possui a pista."
            )

            dialogo.addButton("Simular esta corrida", QMessageBox.AcceptRole)
            btn_confirmar = dialogo.addButton("Tenho esta pista, correr", QMessageBox.YesRole)
            btn_cancelar = dialogo.addButton("Cancelar", QMessageBox.RejectRole)
            dialogo.exec()

            clicado = dialogo.clickedButton()
            if clicado == btn_cancelar:
                return

            if clicado == btn_confirmar and pista_slug:
                conteudo = self._obter_conteudo_iracing()
                pistas = list(conteudo.get("pistas_pagas", []))
                if pista_slug not in pistas:
                    pistas.append(pista_slug)
                    conteudo["pistas_pagas"] = pistas
                    self.banco["conteudo_iracing"] = conteudo
                    salvar_banco(self.banco)

        pontos_antes = self._snapshot_pontos_categoria(self.categoria_atual)
        lesoes_antes = self._snapshot_lesoes_categoria(self.categoria_atual)
        ordens_antes = self._snapshot_ordens_hierarquia_categoria(self.categoria_atual)
        try:
            rodada_processada = int(self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_processada = 1

        try:
            resultado_simulacao = None
            resumo_outras_categorias: dict[str, dict[str, Any]] = {}
            
            def _calcular():
                nonlocal resultado_simulacao
                if evento_pcc:
                    from Logica.series_especiais import simular_proximo_evento_pcc
                    resultado_simulacao = simular_proximo_evento_pcc(self.banco)
                else:
                    from Logica.simulacao import simular_corrida_categoria_detalhada

                    resultado_detalhado = simular_corrida_categoria_detalhada(
                        self.banco,
                        self.categoria_atual,
                    )
                    if isinstance(resultado_detalhado, dict):
                        resultado_simulacao = resultado_detalhado.get("classificacao", [])
                    else:
                        resultado_simulacao = []
            
            def _aplicar():
                nonlocal resumo_outras_categorias
                if evento_pcc:
                    from Logica.series_especiais import aplicar_resultado_pcc
                    aplicados = aplicar_resultado_pcc(
                        self.banco,
                        resultado_simulacao,
                        origem="simulada",
                    )
                else:
                    aplicados = self._aplicar_resultado_simulado(resultado_simulacao)

                if aplicados <= 0:
                    raise Exception("A simulacao foi executada, mas nenhum resultado pode ser aplicado.")

                if not evento_pcc:
                    resumo_outras_categorias = self._simular_rodada_todas_categorias(
                        rodada_referencia=int(self.banco.get("rodada_atual", 1)),
                    )
                    self._avancar_rodada()
                else:
                    salvar_banco(self.banco)

                self._atualizar_tudo()

            def _finalizar():
                if resultado_simulacao:
                    outras_categorias = []
                    for categoria_id, info in (resumo_outras_categorias or {}).items():
                        if not isinstance(info, dict):
                            continue
                        outras_categorias.append(
                            {
                                "categoria_id": categoria_id,
                                "categoria_nome": next(
                                    (
                                        str(cat.get("nome", categoria_id))
                                        for cat in CATEGORIAS
                                        if str(cat.get("id", "")) == str(categoria_id)
                                    ),
                                    str(categoria_id),
                                ),
                                "rodada": int(info.get("rodada", 0) or 0),
                                "vencedor": str(info.get("vencedor", "Sem vencedor") or "Sem vencedor"),
                            }
                        )

                    self._abrir_resultado_corrida_detalhado(
                        classificacao=resultado_simulacao,
                        corrida=corrida if isinstance(corrida, dict) else {},
                        categoria_id=self.categoria_atual,
                        rodada=rodada_processada,
                        pontos_antes=pontos_antes,
                        lesoes_antes=lesoes_antes,
                        ordens_antes=ordens_antes,
                        outras_categorias=outras_categorias,
                    )
                    
                    # Mostrar sucesso
                    if hasattr(self, 'mostrar_sucesso_animado'):
                        self.mostrar_sucesso_animado()

            self.simular_com_progresso([
                ("Preparando grid de largada...", lambda: None, 20),
                ("Calculando condições climáticas...", lambda: None, 10),
                ("Simulando desempenho...", _calcular, 50),
                ("Processando bandeiradas finais...", _aplicar, 20)
            ], on_complete=_finalizar)

        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro na simulacao:\n{erro}",
            )

    def _simular_temporada_completa(self) -> None:
        evento_atual = self._get_proximo_evento_exibicao()
        if self._temporada_concluida() and not (
            evento_atual and evento_atual.get("tipo_evento") == "pcc"
        ):
            QMessageBox.information(
                self,
                "Info",
                "A temporada ja foi concluida.",
            )
            return

        if not evento_atual and self._corridas_restantes() <= 0:
            QMessageBox.information(
                self,
                "Info",
                "Nao ha eventos restantes para simular.",
            )
            return

        resposta = QMessageBox.question(
            self,
            "Confirmar",
            "Simular todos os eventos restantes?\nIsso pode demorar alguns segundos.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return

        try:
            from Logica.series_especiais import (
                aplicar_resultado_pcc,
                simular_proximo_evento_pcc,
            )
            from Logica.simulacao import simular_corrida_categoria
        except ImportError:
            QMessageBox.warning(
                self,
                "Aviso",
                "Modulo de simulacao nao encontrado.",
            )
            return

        processadas_principais = 0
        processadas_pcc = 0

        try:
            while True:
                evento = self._get_proximo_evento_exibicao()

                if evento and evento.get("tipo_evento") == "pcc":
                    resultado = simular_proximo_evento_pcc(self.banco)
                    aplicados = aplicar_resultado_pcc(
                        self.banco,
                        resultado,
                        origem="simulada",
                    )
                    if aplicados <= 0:
                        break
                    processadas_pcc += 1
                    salvar_banco(self.banco)
                    continue

                if self._temporada_concluida():
                    break

                corrida = self._get_corrida_atual()
                if not corrida:
                    break

                resultado = simular_corrida_categoria(self.banco, self.categoria_atual)
                aplicados = self._aplicar_resultado_simulado(resultado)
                if aplicados <= 0:
                    break

                self._simular_rodada_todas_categorias(
                    rodada_referencia=int(self.banco.get("rodada_atual", 1)),
                )
                self._avancar_rodada()
                processadas_principais += 1

            self._atualizar_tudo()

            QMessageBox.information(
                self,
                "Concluido",
                "Eventos simulados.\n"
                f"Campeonato principal: {processadas_principais}\n"
                f"Production Car Challenge: {processadas_pcc}",
            )

        except Exception as erro:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro na simulacao:\n{erro}",
            )

    def _aplicar_resultado_simulado(self, resultado: list[dict]) -> int:
        aplicados = self._aplicar_classificacao_por_id(
            resultado,
            rodada=int(self.banco.get("rodada_atual", 1) or 1),
            foi_corrida_jogador=False,
        )
        calcular_pontos_equipes(self.banco, self.categoria_atual)
        return aplicados
