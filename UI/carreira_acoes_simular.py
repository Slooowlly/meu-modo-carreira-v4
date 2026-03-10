from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from Dados.banco import salvar_banco
from Logica.equipes import calcular_pontos_equipes


class SimularMixin:
    """
    Mixin de simulacao de corridas.
    Assume helpers da base em UI.carreira_acoes.
    """

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

        try:
            if evento_pcc:
                from Logica.series_especiais import (
                    aplicar_resultado_pcc,
                    simular_proximo_evento_pcc,
                )

                resultado = simular_proximo_evento_pcc(self.banco)
                aplicados = aplicar_resultado_pcc(
                    self.banco,
                    resultado,
                    origem="simulada",
                )
            else:
                from Logica.simulacao import simular_corrida_categoria

                resultado = simular_corrida_categoria(self.banco, self.categoria_atual)
                aplicados = self._aplicar_resultado_simulado(resultado)

            if aplicados <= 0:
                QMessageBox.warning(
                    self,
                    "Aviso",
                    "A simulacao foi executada, mas nenhum resultado pode ser aplicado.",
                )
                return

            if not evento_pcc:
                self._avancar_rodada()
            else:
                salvar_banco(self.banco)

            self._atualizar_tudo()
            self._mostrar_resultado_corrida(resultado, corrida)

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
        aplicados = self._aplicar_classificacao_por_id(resultado)
        calcular_pontos_equipes(self.banco, self.categoria_atual)
        return aplicados

    def _mostrar_resultado_corrida(self, resultado: list[dict], corrida: dict) -> None:
        linhas = [f"Corrida: {corrida.get('nome', 'Corrida')}", ""]

        for posicao, entrada in enumerate(resultado[:10], start=1):
            entry_name = entrada.get("piloto_nome", "Piloto sem nome")
            dnf = bool(entrada.get("dnf", False))
            volta_rapida = bool(entrada.get("volta_rapida", False))
            pontos = self._calcular_pontos_da_posicao(
                posicao=posicao,
                volta_rapida=volta_rapida,
                dnf=dnf,
            )

            sufixos: list[str] = []
            if volta_rapida and not dnf and posicao <= 10:
                sufixos.append("VR")
            if dnf:
                sufixos.append("DNF")

            sufixo = f" ({', '.join(sufixos)})" if sufixos else ""
            linhas.append(f"P{posicao:02d}  {entry_name}  +{pontos} pts{sufixo}")

        QMessageBox.information(
            self,
            "Resultado",
            "\n".join(linhas),
        )
