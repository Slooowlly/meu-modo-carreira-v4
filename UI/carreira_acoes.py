"""
Módulo contendo utilidades base para gerenciar e calcular estatísticas da carreira.
"""
from __future__ import annotations

from typing import Any, Iterable

from Dados.constantes import CATEGORIAS_CONFIG, PONTOS_POR_POSICAO  # type: ignore
from Dados.banco import salvar_banco
from Logica.milestones import verificar_milestones
from Logica.noticias import GeradorNoticias
from Utils.iracing_conteudo import (
    categoria_para_conteudo,
    jogador_possui_categoria,
    jogador_possui_pista,
    nome_carro_categoria,
    nome_carro_equipe,
    normalizar_conteudo_iracing,
    pista_cobranca_slug,
)
from Utils.helpers import obter_nome_categoria


class CarreiraAcoesBaseMixin:
    """
    Base compartilhada entre os mixins da carreira.

    Não depende de __init__ e assume que a classe final possui:
        - self.banco
        - self.categoria_atual
        - self._obter_jogador()
    """

    banco: dict[str, Any]
    categoria_atual: str | None

    # ============================================================
    # CONTEUDO IRACING
    # ============================================================

    def _obter_conteudo_iracing(self) -> dict[str, list[str]]:
        conteudo = normalizar_conteudo_iracing(self.banco.get("conteudo_iracing"))
        if self.banco.get("conteudo_iracing") != conteudo:
            self.banco["conteudo_iracing"] = conteudo
        return conteudo

    def _categoria_conteudo_proposta(
        self,
        categoria_id: Any,
        equipe: dict[str, Any] | None = None,
    ) -> str:
        return categoria_para_conteudo(categoria_id, equipe)

    def _descricao_carro_proposta(
        self,
        categoria_id: Any,
        equipe: dict[str, Any] | None = None,
    ) -> str:
        categoria_conteudo = self._categoria_conteudo_proposta(categoria_id, equipe)
        if isinstance(equipe, dict):
            return nome_carro_equipe(equipe, categoria_id)
        return nome_carro_categoria(categoria_conteudo)

    def _proposta_requer_conteudo_nao_possuido(
        self,
        categoria_id: Any,
        equipe: dict[str, Any] | None = None,
    ) -> bool:
        categoria_conteudo = self._categoria_conteudo_proposta(categoria_id, equipe)
        conteudo = self._obter_conteudo_iracing()
        return not jogador_possui_categoria(conteudo, categoria_conteudo)

    def _corrida_requer_pista_nao_possuida(self, corrida: dict[str, Any] | None) -> bool:
        if not isinstance(corrida, dict):
            return False
        conteudo = self._obter_conteudo_iracing()
        circuito = corrida.get("circuito", "")
        return not jogador_possui_pista(conteudo, circuito)

    def _id_pista_cobranca_corrida(self, corrida: dict[str, Any] | None) -> str:
        if not isinstance(corrida, dict):
            return ""
        return pista_cobranca_slug(corrida.get("circuito", ""))

    # ============================================================
    # ESTADO DA TEMPORADA
    # ============================================================

    def _temporada_concluida(self) -> bool:
        """Indica se a temporada atual já foi encerrada."""
        return bool(self.banco.get("temporada_concluida", False))

    def _obter_total_rodadas_temporada(self) -> int:
        """
        Retorna o total de rodadas efetivo da categoria atual.
        """
        categoria_id = str(getattr(self, "categoria_atual", "") or "").strip()

        try:
            from Logica.aiseason import obter_total_etapas_predefinido  # type: ignore

            total_preset = obter_total_etapas_predefinido(categoria_id)
        except Exception:
            total_preset = None

        if isinstance(total_preset, int) and total_preset > 0:
            return total_preset

        calendario = self.banco.get("calendario", [])
        if isinstance(calendario, list) and calendario:
            return len(calendario)

        try:
            total_banco = int(self.banco.get("total_rodadas", 0))
        except (TypeError, ValueError):
            total_banco = 0

        return total_banco if total_banco > 0 else 24

    def _corridas_disputadas(self) -> int:
        """Retorna quantas corridas da temporada ja foram processadas."""
        total = self._obter_total_rodadas_temporada()
        try:
            rodada_atual = int(self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada_atual = 1

        if self._temporada_concluida():
            return total

        return min(max(rodada_atual - 1, 0), total)

    def _corridas_restantes(self) -> int:
        """Retorna quantas corridas ainda faltam na temporada."""
        total = self._obter_total_rodadas_temporada()
        return max(total - self._corridas_disputadas(), 0)

    def _obter_gerador_noticias(self) -> GeradorNoticias:
        return GeradorNoticias(self.banco)

    def _registrar_resultado_categoria_ui(
        self,
        *,
        categoria_id: str | None,
        rodada: int | None,
        corrida: dict[str, Any] | None,
        classificacao: list[dict[str, Any]] | None,
    ) -> None:
        """Persiste ultimo resultado detalhado por categoria para exibicao na UI."""
        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return
        if not isinstance(classificacao, list) or not classificacao:
            return

        try:
            rodada_int = int(rodada if rodada is not None else self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada_int = int(self.banco.get("rodada_atual", 1) or 1)
        rodada_int = max(1, rodada_int)

        circuito = ""
        if isinstance(corrida, dict):
            circuito = str(corrida.get("circuito", corrida.get("nome", "")) or "").strip()

        linhas: list[dict[str, Any]] = []
        for indice, item in enumerate(classificacao, start=1):
            if not isinstance(item, dict):
                continue
            nome = str(
                item.get("piloto_nome", item.get("piloto", item.get("nome", "Piloto")))
                or "Piloto"
            ).strip() or "Piloto"
            equipe = str(item.get("equipe_nome", item.get("equipe", "")) or "").strip()
            dnf = bool(item.get("dnf", False))
            try:
                pos = int(
                    item.get(
                        "posicao_campeonato",
                        item.get("posicao_classe", item.get("posicao", indice)),
                    )
                    or indice
                )
            except (TypeError, ValueError):
                pos = indice
            linhas.append(
                {
                    "piloto_nome": nome,
                    "equipe_nome": equipe,
                    "posicao": pos,
                    "dnf": dnf,
                    "motivo_dnf": str(item.get("motivo_dnf", "") or "").strip(),
                    "pontos": int(item.get("pontos", 0) or 0),
                    "is_jogador": bool(item.get("is_jogador", False)),
                }
            )

        if not linhas:
            return

        raiz = self.banco.get("ultimos_resultados_por_categoria")
        if not isinstance(raiz, dict):
            raiz = {}
            self.banco["ultimos_resultados_por_categoria"] = raiz

        raiz[categoria] = {
            "categoria_id": categoria,
            "categoria_nome": obter_nome_categoria(categoria),
            "rodada": rodada_int,
            "circuito": circuito,
            "classificacao": linhas[:50],
            "timestamp": int(self.banco.get("rodada_atual", rodada_int) or rodada_int),
        }

    def _registrar_noticias_pos_corrida(
        self,
        *,
        categoria_id: str | None,
        rodada: int | None,
        corrida: dict[str, Any] | None,
        classificacao: list[dict[str, Any]],
        lesoes: list[dict[str, Any]] | None = None,
        ordens: list[str] | None = None,
        outras_categorias: list[dict[str, Any]] | None = None,
    ) -> None:
        """Gera noticias de corrida/incidentes para alimentar o feed."""
        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return
        categoria_nome = obter_nome_categoria(categoria)
        ano_atual = int(self.banco.get("ano_atual", 2024) or 2024)
        try:
            rodada_int = int(rodada if rodada is not None else self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada_int = int(self.banco.get("rodada_atual", 1) or 1)
        rodada_int = max(1, rodada_int)

        circuito = ""
        if isinstance(corrida, dict):
            circuito = str(corrida.get("circuito", corrida.get("nome", "")) or "").strip()

        gerador = self._obter_gerador_noticias()
        gerador.gerar_noticia_corrida(
            resultado=classificacao,
            categoria_nome=categoria_nome,
            rodada=rodada_int,
            temporada=ano_atual,
            circuito=circuito,
            categoria_id=categoria,
        )

        dnfs = [
            item
            for item in classificacao
            if isinstance(item, dict) and bool(item.get("dnf", False))
        ]
        if len(dnfs) >= 2:
            nomes = ", ".join(
                str(item.get("piloto_nome", "Piloto") or "Piloto")
                for item in dnfs[:3]
                if isinstance(item, dict)
            )
            if nomes:
                gerador.gerar_noticia_incidente(
                    incidente=f"DNFs notaveis na largada: {nomes}.",
                    categoria_nome=categoria_nome,
                    rodada=rodada_int,
                    temporada=ano_atual,
                    categoria_id=categoria,
                )

        for lesao in (lesoes or []):
            if not isinstance(lesao, dict):
                continue
            gerador.gerar_noticia_lesao(
                piloto_nome=str(lesao.get("piloto_nome", "Piloto") or "Piloto"),
                lesao=lesao,
                temporada=ano_atual,
                rodada=rodada_int,
                tipo_evento="lesao",
            )

        for ordem in (ordens or []):
            texto = str(ordem or "").strip()
            if not texto:
                continue
            equipe_nome = "Equipe"
            if ":" in texto:
                equipe_nome = str(texto.split(":", 1)[0]).strip() or "Equipe"
            gerador.gerar_noticia_hierarquia(
                equipe_nome=equipe_nome,
                evento=texto,
                temporada=ano_atual,
                rodada=rodada_int,
            )

        for item in (outras_categorias or []):
            if not isinstance(item, dict):
                continue
            categoria_aux = str(item.get("categoria_id", "") or "").strip()
            if not categoria_aux:
                continue
            rodada_aux = int(item.get("rodada", 0) or 0)
            vencedor = str(item.get("vencedor", "Piloto") or "Piloto")
            gerador.gerar_noticia_corrida(
                resultado=[{"piloto_nome": vencedor, "dnf": False}],
                categoria_nome=str(
                    item.get("categoria_nome", obter_nome_categoria(categoria_aux))
                    or obter_nome_categoria(categoria_aux)
                ),
                rodada=rodada_aux,
                temporada=ano_atual,
                circuito="",
                categoria_id=categoria_aux,
            )

    def _obter_mapa_volta_rapida_por_rodada(
        self,
        categoria_id: str | None = None,
    ) -> dict[str, dict[str, Any]]:
        """Retorna o mapa persistente de volta rapida por rodada da categoria."""
        raiz = self.banco.get("volta_rapida_por_rodada")
        if not isinstance(raiz, dict):
            raiz = {}
            self.banco["volta_rapida_por_rodada"] = raiz

        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return {}

        mapa_categoria = raiz.get(categoria)
        if not isinstance(mapa_categoria, dict):
            mapa_categoria = {}
            raiz[categoria] = mapa_categoria

        return mapa_categoria

    def _registrar_volta_rapida_da_rodada(
        self,
        classificacao: list[dict[str, Any]],
        categoria_id: str | None = None,
        rodada: int | None = None,
    ) -> None:
        """
        Persiste quem fez volta rapida da rodada atual para uso no dashboard.
        """
        if not isinstance(classificacao, list) or not classificacao:
            return

        if rodada is None:
            try:
                rodada = int(self.banco.get("rodada_atual", 1))
            except (TypeError, ValueError):
                rodada = 1
        rodada = max(1, int(rodada))
        chave_rodada = str(rodada)

        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return

        mapa_categoria = self._obter_mapa_volta_rapida_por_rodada(categoria)

        entrada_vmr = next(
            (
                entrada
                for entrada in classificacao
                if isinstance(entrada, dict)
                and bool(entrada.get("volta_rapida", False))
                and not bool(entrada.get("dnf", False))
            ),
            None,
        )

        if not isinstance(entrada_vmr, dict):
            mapa_categoria.pop(chave_rodada, None)
            return

        piloto_id = entrada_vmr.get("piloto_id", entrada_vmr.get("id"))
        if piloto_id in (None, "") or isinstance(piloto_id, bool):
            nome_raw = entrada_vmr.get("piloto", entrada_vmr.get("nome", ""))
            piloto_ref = self._obter_piloto_por_nome(str(nome_raw), categoria)
            if isinstance(piloto_ref, dict):
                piloto_id = piloto_ref.get("id")
            else:
                piloto_id = None

        nome_piloto = str(
            entrada_vmr.get("piloto", entrada_vmr.get("nome", ""))
            or ""
        ).strip()
        if not nome_piloto and piloto_id not in (None, "") and not isinstance(piloto_id, bool):
            piloto_ref = self._obter_piloto_por_id(piloto_id, categoria)
            if isinstance(piloto_ref, dict):
                nome_piloto = str(piloto_ref.get("nome", "") or "").strip()

        registro: dict[str, Any] = {}
        if piloto_id not in (None, "") and not isinstance(piloto_id, bool):
            registro["piloto_id"] = piloto_id
        if nome_piloto:
            registro["piloto_nome"] = nome_piloto

        if registro:
            mapa_categoria[chave_rodada] = registro
        else:
            mapa_categoria.pop(chave_rodada, None)

    # ============================================================
    # ORDENACAO
    # ============================================================

    def _ordenar_pilotos_campeonato(
        self,
        pilotos: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ordena pilotos por pontos, vitórias, pódios e nome."""
        return sorted(
            pilotos,
            key=lambda p: (
                -int(p.get("pontos_temporada", 0)),
                -int(p.get("vitorias_temporada", 0)),
                -int(p.get("podios_temporada", 0)),
                str(p.get("nome", "")).casefold(),
            ),
        )

    def _ordenar_equipes_campeonato(
        self,
        equipes: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Ordena equipes por pontos, vitórias, pódios e nome."""
        return sorted(
            equipes,
            key=lambda e: (
                -int(e.get("pontos_temporada", 0)),
                -int(e.get("vitorias_temporada", 0)),
                -int(e.get("podios_temporada", 0)),
                str(e.get("nome", "")).casefold(),
            ),
        )

    # ============================================================
    # SNAPSHOTS / POS-CORRIDA
    # ============================================================

    def _snapshot_pontos_categoria(self, categoria_id: str | None = None) -> dict[str, int]:
        """Registra pontos atuais por piloto (id) para calculo de delta no pos-corrida."""
        mapa: dict[str, int] = {}
        for piloto in self._obter_pilotos_da_categoria(categoria_id):
            piloto_id = self._normalizar_id_hierarquia(piloto.get("id"))
            if not piloto_id:
                continue
            try:
                mapa[piloto_id] = int(piloto.get("pontos_temporada", 0) or 0)
            except (TypeError, ValueError):
                mapa[piloto_id] = 0
        return mapa

    def _snapshot_lesoes_categoria(self, categoria_id: str | None = None) -> dict[str, int]:
        """Registra corridas restantes de lesao ativa por piloto."""
        mapa: dict[str, int] = {}
        for piloto in self._obter_pilotos_da_categoria(categoria_id):
            piloto_id = self._normalizar_id_hierarquia(piloto.get("id"))
            if not piloto_id:
                continue
            lesao = piloto.get("lesao")
            corridas = 0
            if isinstance(lesao, dict):
                try:
                    corridas = int(lesao.get("corridas_restantes", 0) or 0)
                except (TypeError, ValueError):
                    corridas = 0
            mapa[piloto_id] = max(0, corridas)
        return mapa

    def _snapshot_ordens_hierarquia_categoria(
        self,
        categoria_id: str | None = None,
    ) -> dict[str, dict[str, int]]:
        """Registra contadores de ordens obedecidas/desobedecidas por equipe."""
        categoria = str(categoria_id or self.categoria_atual or "").strip()
        mapa: dict[str, dict[str, int]] = {}
        if not categoria:
            return mapa

        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if not bool(equipe.get("ativa", True)):
                continue
            categoria_eq = str(equipe.get("categoria", equipe.get("categoria_id", "")) or "").strip()
            if categoria_eq != categoria:
                continue

            equipe_id = self._normalizar_id_hierarquia(equipe.get("id"))
            if not equipe_id:
                continue

            hierarquia = equipe.get("hierarquia")
            if not isinstance(hierarquia, dict):
                hierarquia = {}

            try:
                obed = int(hierarquia.get("ordens_obedecidas", 0) or 0)
            except (TypeError, ValueError):
                obed = 0
            try:
                desob = int(hierarquia.get("ordens_desobedecidas", 0) or 0)
            except (TypeError, ValueError):
                desob = 0

            mapa[equipe_id] = {
                "obedecidas": max(0, obed),
                "desobedecidas": max(0, desob),
            }
        return mapa

    def _coletar_ordens_equipe_disparadas(
        self,
        categoria_id: str | None,
        snapshot_antes: dict[str, dict[str, int]] | None = None,
    ) -> list[str]:
        """Gera resumo textual de ordens de equipe ocorridas na rodada."""
        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return []

        antes = snapshot_antes if isinstance(snapshot_antes, dict) else {}
        depois = self._snapshot_ordens_hierarquia_categoria(categoria)
        linhas: list[str] = []

        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if str(equipe.get("categoria", equipe.get("categoria_id", "")) or "").strip() != categoria:
                continue
            equipe_id = self._normalizar_id_hierarquia(equipe.get("id"))
            if not equipe_id:
                continue
            reg_antes = antes.get(equipe_id, {})
            reg_depois = depois.get(equipe_id, {})

            obed_antes = int(reg_antes.get("obedecidas", 0) or 0)
            obed_depois = int(reg_depois.get("obedecidas", 0) or 0)
            desob_antes = int(reg_antes.get("desobedecidas", 0) or 0)
            desob_depois = int(reg_depois.get("desobedecidas", 0) or 0)

            delta_obed = max(0, obed_depois - obed_antes)
            delta_desob = max(0, desob_depois - desob_antes)
            if delta_obed <= 0 and delta_desob <= 0:
                continue

            nome_equipe = str(equipe.get("nome", "Equipe") or "Equipe")
            if delta_obed > 0:
                linhas.append(f"{nome_equipe}: ordem de equipe obedecida ({delta_obed}x)")
            if delta_desob > 0:
                linhas.append(f"{nome_equipe}: ordem de equipe ignorada ({delta_desob}x)")

        return linhas[:10]

    def _coletar_lesoes_novas_categoria(
        self,
        categoria_id: str | None,
        snapshot_antes: dict[str, int] | None = None,
    ) -> list[dict[str, Any]]:
        """Lista lesoes novas detectadas apos a corrida."""
        antes = snapshot_antes if isinstance(snapshot_antes, dict) else {}
        saida: list[dict[str, Any]] = []
        for piloto in self._obter_pilotos_da_categoria(categoria_id):
            piloto_id = self._normalizar_id_hierarquia(piloto.get("id"))
            if not piloto_id:
                continue
            lesao = piloto.get("lesao")
            if not isinstance(lesao, dict):
                continue
            try:
                corridas = int(lesao.get("corridas_restantes", 0) or 0)
            except (TypeError, ValueError):
                corridas = 0
            if corridas <= 0:
                continue
            corridas_antes = int(antes.get(piloto_id, 0) or 0)
            if corridas_antes > 0:
                continue
            saida.append(
                {
                    "piloto_nome": str(piloto.get("nome", "Piloto") or "Piloto"),
                    "tipo": str(lesao.get("tipo", "desconhecida") or "desconhecida"),
                    "corridas_restantes": corridas,
                }
            )
        return saida

    def _montar_campeonato_pos_corrida(
        self,
        categoria_id: str | None,
        pontos_antes: dict[str, int] | None = None,
        limite: int = 20,
    ) -> list[dict[str, Any]]:
        """Monta classificacao do campeonato com delta de pontos da rodada."""
        pilotos = self._ordenar_pilotos_campeonato(self._obter_pilotos_da_categoria(categoria_id))
        mapa_antes = pontos_antes if isinstance(pontos_antes, dict) else {}
        saida: list[dict[str, Any]] = []
        for posicao, piloto in enumerate(pilotos[: max(1, limite)], start=1):
            piloto_id = self._normalizar_id_hierarquia(piloto.get("id"))
            try:
                pontos = int(piloto.get("pontos_temporada", 0) or 0)
            except (TypeError, ValueError):
                pontos = 0
            pontos_prev = int(mapa_antes.get(piloto_id, pontos) or pontos)
            saida.append(
                {
                    "posicao": posicao,
                    "nome": str(piloto.get("nome", "Piloto") or "Piloto"),
                    "pontos": pontos,
                    "delta": pontos - pontos_prev,
                    "is_jogador": bool(piloto.get("is_jogador", False)),
                }
            )
        return saida

    def _enriquecer_classificacao_para_dialogo(
        self,
        classificacao: list[dict[str, Any]],
        categoria_id: str | None,
    ) -> list[dict[str, Any]]:
        """Normaliza classificacao para exibir no dialogo detalhado."""
        pilotos_por_id = {
            self._normalizar_id_hierarquia(p.get("id")): p
            for p in self._obter_pilotos_da_categoria(categoria_id)
            if isinstance(p, dict)
        }
        saida: list[dict[str, Any]] = []
        for indice, entrada in enumerate(classificacao, start=1):
            if not isinstance(entrada, dict):
                continue
            piloto_id = self._normalizar_id_hierarquia(entrada.get("piloto_id", entrada.get("id")))
            piloto_ref = pilotos_por_id.get(piloto_id, {})

            nome = str(
                entrada.get("piloto_nome", entrada.get("piloto", entrada.get("nome", "")))
                or piloto_ref.get("nome", "Piloto")
            ).strip() or "Piloto"
            equipe = str(entrada.get("equipe_nome", piloto_ref.get("equipe_nome", "")) or "").strip()
            dnf = bool(entrada.get("dnf", False))
            volta_rapida = bool(entrada.get("volta_rapida", False))
            try:
                posicao = int(
                    entrada.get(
                        "posicao_campeonato",
                        entrada.get("posicao_classe", entrada.get("posicao", indice)),
                    )
                )
            except (TypeError, ValueError):
                posicao = indice

            pontos = entrada.get("pontos")
            if isinstance(pontos, bool):
                pontos = None
            if pontos is None:
                pontos_calc = self._calcular_pontos_da_posicao(posicao=posicao, volta_rapida=volta_rapida, dnf=dnf)
            else:
                try:
                    pontos_calc = int(pontos)
                except (TypeError, ValueError):
                    pontos_calc = self._calcular_pontos_da_posicao(
                        posicao=posicao,
                        volta_rapida=volta_rapida,
                        dnf=dnf,
                    )

            saida.append(
                {
                    "piloto_id": piloto_id,
                    "piloto_nome": nome,
                    "equipe_nome": equipe,
                    "dnf": dnf,
                    "motivo_dnf": str(entrada.get("motivo_dnf", "") or "").strip(),
                    "volta_rapida": volta_rapida,
                    "pontos": pontos_calc,
                    "posicao_campeonato": posicao,
                    "incidentes": int(entrada.get("incidentes", 0) or 0),
                    "is_jogador": bool(
                        entrada.get("is_jogador", piloto_ref.get("is_jogador", False))
                    ),
                }
            )
        return saida

    def _consumir_notificacoes_hierarquia_pendentes(self) -> list[dict[str, Any]]:
        """Retorna notificacoes de hierarquia acumuladas e limpa fila."""
        pendentes = getattr(self, "_notificacoes_hierarquia_pendentes", [])
        if not isinstance(pendentes, list):
            pendentes = []
        self._notificacoes_hierarquia_pendentes = []
        return [item for item in pendentes if isinstance(item, dict)]

    def _mostrar_notificacoes_hierarquia(self, notificacoes: list[dict[str, Any]]) -> None:
        """Exibe notificacoes de mudanca de hierarquia da equipe do jogador."""
        if not isinstance(notificacoes, list) or not notificacoes:
            return

        try:
            from PySide6.QtWidgets import QMessageBox
        except Exception:
            return

        for item in notificacoes:
            if not isinstance(item, dict):
                continue
            texto = str(item.get("notificacao", "") or "").strip()
            if not texto:
                continue
            destaque = bool(item.get("destaque", False))
            titulo = "Hierarquia interna"
            if destaque:
                titulo = "Mudanca importante de hierarquia"
                QMessageBox.warning(self, titulo, texto)
            else:
                QMessageBox.information(self, titulo, texto)

    def _abrir_resultado_corrida_detalhado(
        self,
        *,
        classificacao: list[dict[str, Any]],
        corrida: dict[str, Any] | None,
        categoria_id: str | None,
        rodada: int | None = None,
        pontos_antes: dict[str, int] | None = None,
        lesoes_antes: dict[str, int] | None = None,
        ordens_antes: dict[str, dict[str, int]] | None = None,
        outras_categorias: list[dict[str, Any]] | None = None,
    ) -> None:
        """Abre dialogo detalhado de pos-corrida e, ao final, mostra notificacoes de hierarquia."""
        classificacao_ok = self._enriquecer_classificacao_para_dialogo(classificacao, categoria_id)
        campeonato = self._montar_campeonato_pos_corrida(categoria_id, pontos_antes=pontos_antes, limite=20)
        lesoes = self._coletar_lesoes_novas_categoria(categoria_id, snapshot_antes=lesoes_antes)
        ordens = self._coletar_ordens_equipe_disparadas(categoria_id, snapshot_antes=ordens_antes)

        destaques: list[str] = []
        volta_rapida = next(
            (
                item
                for item in classificacao_ok
                if isinstance(item, dict) and bool(item.get("volta_rapida", False))
            ),
            None,
        )
        if isinstance(volta_rapida, dict):
            destaques.append(f"Volta mais rapida: {volta_rapida.get('piloto_nome', 'Piloto')}")
        dnfs = [item for item in classificacao_ok if isinstance(item, dict) and bool(item.get("dnf", False))]
        if dnfs:
            destaques.append(f"DNFs na corrida: {len(dnfs)}")

        jogador_res = next(
            (
                item
                for item in classificacao_ok
                if isinstance(item, dict) and bool(item.get("is_jogador", False))
            ),
            None,
        )
        if isinstance(jogador_res, dict):
            if bool(jogador_res.get("dnf", False)):
                destaques.append("Seu resultado: DNF")
            else:
                pos_jog = int(jogador_res.get("posicao_campeonato", 0) or 0)
                destaques.append(f"Seu resultado: P{pos_jog}")

        nome_evento = "Corrida"
        if isinstance(corrida, dict):
            nome_evento = str(corrida.get("circuito", corrida.get("nome", "Corrida")) or "Corrida")
        categoria_txt = obter_nome_categoria(str(categoria_id or self.categoria_atual or "").strip())
        rodada_txt = str(rodada if rodada is not None else "-")
        try:
            rodada_int = int(rodada if rodada is not None else self.banco.get("rodada_atual", 1) or 1)
        except (TypeError, ValueError):
            rodada_int = int(self.banco.get("rodada_atual", 1) or 1)
        titulo = f"Resultado - Rodada {rodada_txt} - {nome_evento}"
        if categoria_txt:
            titulo = f"{titulo} ({categoria_txt})"

        dados_dialogo = {
            "titulo": titulo,
            "classificacao": classificacao_ok,
            "destaques": destaques,
            "lesoes_rodada": lesoes,
            "ordens_equipe": ordens,
            "campeonato_atualizado": campeonato,
            "outras_categorias": outras_categorias if isinstance(outras_categorias, list) else [],
        }

        self._registrar_resultado_categoria_ui(
            categoria_id=categoria_id,
            rodada=rodada,
            corrida=corrida if isinstance(corrida, dict) else {},
            classificacao=classificacao_ok,
        )
        self._registrar_noticias_pos_corrida(
            categoria_id=categoria_id,
            rodada=rodada,
            corrida=corrida if isinstance(corrida, dict) else {},
            classificacao=classificacao_ok,
            lesoes=lesoes,
            ordens=ordens,
            outras_categorias=outras_categorias if isinstance(outras_categorias, list) else [],
        )

        avaliacao = None
        obter_avaliacao = getattr(self, "_obter_expectativa_e_avaliacao", None)
        if callable(obter_avaliacao):
            try:
                _exp, avaliacao = obter_avaliacao(
                    persistir_historico=True,
                    rodada_ref=rodada_int,
                )
            except Exception:
                avaliacao = None

        processar_alerta = getattr(self, "_processar_alerta_contratual_pos_corrida", None)
        if callable(processar_alerta):
            try:
                processar_alerta(rodada_int, avaliacao)
            except Exception:
                pass

        novos_milestones: list[dict[str, Any]] = []
        jogador = self._obter_jogador() if hasattr(self, "_obter_jogador") else None
        if isinstance(jogador, dict):
            try:
                total_incidentes = int(
                    jogador_res.get("incidentes", 0) if isinstance(jogador_res, dict) else 0
                )
            except (TypeError, ValueError):
                total_incidentes = 0
            novos_milestones = verificar_milestones(
                jogador,
                self.banco,
                contexto={
                    "tipo": "pos_corrida",
                    "rodada": rodada_int,
                    "resultado": jogador_res if isinstance(jogador_res, dict) else {},
                    "total_incidentes": total_incidentes,
                },
            )
            if novos_milestones:
                gerador = self._obter_gerador_noticias()
                temporada = int(self.banco.get("ano_atual", 2024) or 2024)
                categoria_chave = str(categoria_id or self.categoria_atual or "").strip()
                categoria_nome = obter_nome_categoria(categoria_chave)
                for milestone in novos_milestones:
                    try:
                        gerador.gerar_noticia_milestone(
                            jogador=jogador,
                            milestone=milestone,
                            temporada=temporada,
                            rodada=rodada_int,
                            categoria_id=categoria_chave,
                            categoria_nome=categoria_nome,
                        )
                    except Exception:
                        pass
        salvar_banco(self.banco)

        aberto = False
        usar_embutido = False
        consumir_embutido = getattr(self, "_rw_receber_resultado_dialogo", None)
        if callable(consumir_embutido):
            try:
                usar_embutido = bool(
                    consumir_embutido(
                        dados_dialogo,
                        rodada_resultado=rodada_int,
                    )
                )
                aberto = usar_embutido
            except Exception:
                usar_embutido = False
                aberto = False

        if not usar_embutido:
            try:
                from UI.dialogs import ResultadoCorridaDialog

                dialogo = ResultadoCorridaDialog(dados_dialogo, parent=self)
                dialogo.exec()
                aberto = True
            except Exception:
                aberto = False

        if not aberto:
            try:
                from PySide6.QtWidgets import QMessageBox

                linhas = [titulo, ""]
                for item in classificacao_ok[:12]:
                    if not isinstance(item, dict):
                        continue
                    nome = str(item.get("piloto_nome", "Piloto") or "Piloto")
                    if bool(item.get("dnf", False)):
                        motivo = str(item.get("motivo_dnf", "") or "").strip() or "abandono"
                        linhas.append(f"DNF {nome} - {motivo}")
                    else:
                        pos = int(item.get("posicao_campeonato", 0) or 0)
                        pts = int(item.get("pontos", 0) or 0)
                        linhas.append(f"P{pos:02d} {nome} (+{pts} pts)")
                QMessageBox.information(self, "Resultado detalhado", "\n".join(linhas))
            except Exception:
                pass

        if novos_milestones:
            try:
                from UI.dialogs import MilestoneDialog

                for milestone in novos_milestones:
                    if not isinstance(milestone, dict):
                        continue
                    dialogo_m = MilestoneDialog(milestone, parent=self)
                    dialogo_m.exec()
            except Exception:
                pass

        pendentes = [
            item
            for item in self._consumir_notificacoes_hierarquia_pendentes()
            if bool(item.get("envolve_jogador", False)) and str(item.get("notificacao", "")).strip()
        ]
        self._mostrar_notificacoes_hierarquia(pendentes)
    # BUSCA DE PILOTOS
    # ============================================================

    def _normalizar_nome_piloto(self, nome: str) -> str:
        """Normaliza nome para comparação segura."""
        return " ".join(str(nome or "").strip().casefold().split())

    def _obter_pilotos_da_categoria(
        self,
        categoria_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retorna pilotos ativos da categoria informada."""
        categoria = categoria_id or self.categoria_atual
        return [
            piloto
            for piloto in self.banco.get("pilotos", [])
            if piloto.get("categoria_atual") == categoria
            and not piloto.get("aposentado", False)
        ]

    def _obter_piloto_por_id(
        self,
        piloto_id: Any,
        categoria_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Busca piloto por id dentro da categoria."""
        if piloto_id is None:
            return None

        categoria = categoria_id or self.categoria_atual
        for piloto in self.banco.get("pilotos", []):
            if (
                self._ids_equivalentes_resultado(piloto.get("id"), piloto_id)
                and piloto.get("categoria_atual") == categoria
                and not piloto.get("aposentado", False)
            ):
                return piloto
        return None

    def _ids_equivalentes_resultado(self, left: Any, right: Any) -> bool:
        """Compara ids int/str com tolerancia a tipo."""
        if left == right:
            return True
        if left in (None, "") or right in (None, ""):
            return False
        if isinstance(left, bool) or isinstance(right, bool):
            return False
        try:
            return int(left) == int(right)
        except (TypeError, ValueError):
            return str(left) == str(right)

    @staticmethod
    def _normalizar_id_hierarquia(valor: Any) -> str:
        if valor in (None, "") or isinstance(valor, bool):
            return ""
        try:
            return str(int(valor))
        except (TypeError, ValueError):
            return str(valor).strip()

    @staticmethod
    def _normalizar_papel_hierarquia(valor: Any) -> str:
        papel = str(valor or "").strip().lower()
        if papel in {"n1", "numero_1"}:
            return "numero_1"
        if papel in {"n2", "numero_2"}:
            return "numero_2"
        return papel

    @staticmethod
    def _obter_experiencia_hierarquia(piloto: dict[str, Any]) -> float:
        try:
            return float(
                piloto.get(
                    "experience",
                    piloto.get("experiencia", 0),
                )
                or 0
            )
        except (TypeError, ValueError):
            return 0.0

    def _obter_total_rodadas_categoria(self, categoria_id: str | None) -> int:
        categoria = str(categoria_id or "").strip()
        if not categoria:
            return self._obter_total_rodadas_temporada()
        cfg = CATEGORIAS_CONFIG.get(categoria, {})
        try:
            total_cfg = int(cfg.get("num_corridas", 0) or 0)
        except (TypeError, ValueError):
            total_cfg = 0
        if total_cfg > 0:
            return total_cfg
        return self._obter_total_rodadas_temporada()

    def _obter_equipe_por_id_hierarquia(self, equipe_id: Any) -> dict[str, Any] | None:
        for equipe in self.banco.get("equipes", []):
            if not isinstance(equipe, dict):
                continue
            if self._ids_equivalentes_resultado(equipe.get("id"), equipe_id):
                return equipe
        return None

    def _obter_piloto_global_por_id_hierarquia(self, piloto_id: Any) -> dict[str, Any] | None:
        for piloto in self.banco.get("pilotos", []):
            if not isinstance(piloto, dict):
                continue
            if bool(piloto.get("aposentado", False)):
                continue
            if self._ids_equivalentes_resultado(piloto.get("id"), piloto_id):
                return piloto
        return None

    def _resolver_hierarquia_inicial_equipe(
        self,
        equipe: dict[str, Any],
        piloto_1: dict[str, Any],
        piloto_2: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        from Logica.hierarquia.avaliacao import definir_hierarquia_inicial

        contrato_1 = {"duracao_anos": int(piloto_1.get("contrato_anos", 0) or 0)}
        contrato_2 = {"duracao_anos": int(piloto_2.get("contrato_anos", 0) or 0)}
        n1_id, n2_id, _motivo = definir_hierarquia_inicial(
            piloto_1,
            piloto_2,
            contrato_1=contrato_1,
            contrato_2=contrato_2,
        )

        if self._ids_equivalentes_resultado(n1_id, piloto_1.get("id")):
            n1 = piloto_1
            n2 = piloto_2
        else:
            n1 = piloto_2
            n2 = piloto_1

        n1["papel"] = "numero_1"
        n2["papel"] = "numero_2"
        n1["duelos_internos_total"] = 0
        n1["duelos_internos_vencidos"] = 0
        n1["n2_superou_n1_temporada"] = False
        n2["duelos_internos_total"] = 0
        n2["duelos_internos_vencidos"] = 0
        n2["n2_superou_n1_temporada"] = False
        equipe["piloto_numero_1"] = n1.get("id")
        equipe["piloto_numero_2"] = n2.get("id")
        equipe["piloto_1"] = n1.get("nome")
        equipe["piloto_2"] = n2.get("nome")
        return n1, n2

    def _inicializar_hierarquia_equipe(
        self,
        equipe: dict[str, Any],
        piloto_1: dict[str, Any],
        piloto_2: dict[str, Any],
    ) -> dict[str, Any]:
        n1, n2 = self._resolver_hierarquia_inicial_equipe(equipe, piloto_1, piloto_2)
        hierarquia = {
            "n1_id": n1.get("id"),
            "n2_id": n2.get("id"),
            "status": "estavel",
            "corridas_n2_a_frente": 0,
            "ultima_reavaliacao": 0,
            "inversoes_temporada": 0,
        }
        equipe["hierarquia"] = hierarquia
        return hierarquia

    def _registrar_duelo_hierarquia(
        self,
        piloto_n1: dict[str, Any],
        piloto_n2: dict[str, Any],
        n2_a_frente: bool,
    ) -> None:
        for piloto in (piloto_n1, piloto_n2):
            piloto["duelos_internos_total"] = int(piloto.get("duelos_internos_total", 0) or 0) + 1

        if n2_a_frente:
            piloto_n2["duelos_internos_vencidos"] = int(piloto_n2.get("duelos_internos_vencidos", 0) or 0) + 1
            piloto_n1["duelos_internos_vencidos"] = int(piloto_n1.get("duelos_internos_vencidos", 0) or 0)
            piloto_n2["n2_superou_n1_temporada"] = (
                int(piloto_n2.get("duelos_internos_vencidos", 0) or 0) >= 3
            )
        else:
            piloto_n1["duelos_internos_vencidos"] = int(piloto_n1.get("duelos_internos_vencidos", 0) or 0) + 1
            piloto_n2["duelos_internos_vencidos"] = int(piloto_n2.get("duelos_internos_vencidos", 0) or 0)
            piloto_n2["n2_superou_n1_temporada"] = bool(piloto_n2.get("n2_superou_n1_temporada", False))

    def _atualizar_hierarquia_pos_corrida(
        self,
        resultado_corrida: list[dict[str, Any]],
        categoria_id: str | None,
        rodada: int | None = None,
        foi_corrida_jogador: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Atualiza dinamica N1/N2 para todas as equipes da categoria apos uma corrida.

        Regras integradas do M9:
        - N2 a frente por 3 corridas: tensao
        - N2 a frente por 4 corridas: reavaliacao
        - N2 a frente por 5 corridas, ou metade da temporada + 3: inversao
        """
        if not isinstance(resultado_corrida, list) or not resultado_corrida:
            return []

        categoria = str(categoria_id or self.categoria_atual or "").strip()
        if not categoria:
            return []

        try:
            rodada_atual = int(rodada if rodada is not None else self.banco.get("rodada_atual", 1))
        except (TypeError, ValueError):
            rodada_atual = int(self.banco.get("rodada_atual", 1) or 1)
        rodada_atual = max(1, rodada_atual)
        total_corridas = max(1, self._obter_total_rodadas_categoria(categoria))
        jogador = self._obter_jogador() if hasattr(self, "_obter_jogador") else None
        jogador_id = self._normalizar_id_hierarquia(jogador.get("id")) if isinstance(jogador, dict) else ""

        pilotos_por_id = {
            self._normalizar_id_hierarquia(p.get("id")): p
            for p in self.banco.get("pilotos", [])
            if isinstance(p, dict)
        }

        resultados_por_equipe: dict[str, list[dict[str, Any]]] = {}
        for posicao_lista, entrada in enumerate(resultado_corrida, start=1):
            if not isinstance(entrada, dict):
                continue

            piloto_id = entrada.get("piloto_id", entrada.get("id"))
            piloto = None
            if piloto_id not in (None, ""):
                piloto = pilotos_por_id.get(self._normalizar_id_hierarquia(piloto_id))
            if not isinstance(piloto, dict):
                nome = str(entrada.get("piloto_nome", entrada.get("piloto", entrada.get("nome", ""))) or "").strip()
                if nome:
                    piloto = next(
                        (
                            p for p in self.banco.get("pilotos", [])
                            if isinstance(p, dict)
                            and not bool(p.get("aposentado", False))
                            and str(p.get("categoria_atual", "")).strip() == categoria
                            and str(p.get("nome", "")).strip() == nome
                        ),
                        None,
                    )
            if not isinstance(piloto, dict):
                continue

            equipe_id = piloto.get("equipe_id")
            if equipe_id in (None, ""):
                continue
            if str(piloto.get("categoria_atual", "")).strip() != categoria:
                continue

            try:
                posicao = int(
                    entrada.get(
                        "posicao_campeonato",
                        entrada.get("posicao_classe", entrada.get("posicao_geral", entrada.get("posicao", posicao_lista))),
                    )
                )
            except (TypeError, ValueError):
                posicao = posicao_lista
            if bool(entrada.get("dnf", False)):
                posicao = max(posicao, len(resultado_corrida) + 1)

            chave = self._normalizar_id_hierarquia(equipe_id)
            resultados_por_equipe.setdefault(chave, []).append(
                {
                    "piloto_id": piloto.get("id"),
                    "posicao": posicao,
                    "dnf": bool(entrada.get("dnf", False)),
                }
            )

        atualizacoes: list[dict[str, Any]] = []
        for equipe_id, resultados in resultados_por_equipe.items():
            if len(resultados) < 2:
                continue

            equipe = self._obter_equipe_por_id_hierarquia(equipe_id)
            if not isinstance(equipe, dict) or not bool(equipe.get("ativa", True)):
                continue
            if str(equipe.get("categoria", equipe.get("categoria_id", "")) or "").strip() != categoria:
                continue

            hierarquia = equipe.get("hierarquia")
            if not isinstance(hierarquia, dict):
                hierarquia = {}
            status_anterior = str(hierarquia.get("status", "estavel") or "estavel").strip().lower()

            n1_id = hierarquia.get("n1_id") or equipe.get("piloto_numero_1")
            n2_id = hierarquia.get("n2_id") or equipe.get("piloto_numero_2")
            jogador_era_n1 = bool(jogador_id and self._ids_equivalentes_resultado(n1_id, jogador_id))

            res_n1 = next((r for r in resultados if self._ids_equivalentes_resultado(r.get("piloto_id"), n1_id)), None)
            res_n2 = next((r for r in resultados if self._ids_equivalentes_resultado(r.get("piloto_id"), n2_id)), None)

            if not isinstance(res_n1, dict) or not isinstance(res_n2, dict):
                pilotos_ids = [r.get("piloto_id") for r in resultados if r.get("piloto_id") not in (None, "")]
                if len(pilotos_ids) < 2:
                    continue
                p1 = self._obter_piloto_global_por_id_hierarquia(pilotos_ids[0])
                p2 = self._obter_piloto_global_por_id_hierarquia(pilotos_ids[1])
                if not isinstance(p1, dict) or not isinstance(p2, dict):
                    continue
                hierarquia = self._inicializar_hierarquia_equipe(equipe, p1, p2)
                n1_id = hierarquia.get("n1_id")
                n2_id = hierarquia.get("n2_id")
                res_n1 = next((r for r in resultados if self._ids_equivalentes_resultado(r.get("piloto_id"), n1_id)), None)
                res_n2 = next((r for r in resultados if self._ids_equivalentes_resultado(r.get("piloto_id"), n2_id)), None)
                if not isinstance(res_n1, dict) or not isinstance(res_n2, dict):
                    continue

            pos_n1 = int(res_n1.get("posicao", 999) or 999)
            pos_n2 = int(res_n2.get("posicao", 999) or 999)
            n2_a_frente = pos_n2 < pos_n1

            corridas_n2_a_frente = int(hierarquia.get("corridas_n2_a_frente", 0) or 0)
            if n2_a_frente:
                corridas_n2_a_frente += 1
            else:
                corridas_n2_a_frente = max(0, corridas_n2_a_frente - 1)
            hierarquia["corridas_n2_a_frente"] = corridas_n2_a_frente

            piloto_n1 = self._obter_piloto_global_por_id_hierarquia(n1_id)
            piloto_n2 = self._obter_piloto_global_por_id_hierarquia(n2_id)
            if isinstance(piloto_n1, dict) and isinstance(piloto_n2, dict):
                self._registrar_duelo_hierarquia(piloto_n1, piloto_n2, n2_a_frente=n2_a_frente)

            inversao = False
            metade_temporada = max(1, total_corridas // 2)
            if corridas_n2_a_frente >= 5 or (rodada_atual >= metade_temporada and corridas_n2_a_frente >= 3):
                hierarquia["status"] = "invertido"
                hierarquia["ultima_reavaliacao"] = rodada_atual
                inversao = True
                antigo_n1 = n1_id
                antigo_n2 = n2_id
                hierarquia["n1_id"] = antigo_n2
                hierarquia["n2_id"] = antigo_n1
                hierarquia["corridas_n2_a_frente"] = 0
                hierarquia["inversoes_temporada"] = int(hierarquia.get("inversoes_temporada", 0) or 0) + 1

                novo_n1 = self._obter_piloto_global_por_id_hierarquia(hierarquia["n1_id"])
                novo_n2 = self._obter_piloto_global_por_id_hierarquia(hierarquia["n2_id"])
                if isinstance(novo_n1, dict):
                    novo_n1["papel"] = "numero_1"
                if isinstance(novo_n2, dict):
                    novo_n2["papel"] = "numero_2"
            elif corridas_n2_a_frente >= 4:
                hierarquia["status"] = "reavaliacao"
                hierarquia["ultima_reavaliacao"] = rodada_atual
            elif corridas_n2_a_frente >= 3:
                hierarquia["status"] = "tensao"
            else:
                hierarquia["status"] = "estavel"

            n1_atual = self._obter_piloto_global_por_id_hierarquia(hierarquia.get("n1_id"))
            n2_atual = self._obter_piloto_global_por_id_hierarquia(hierarquia.get("n2_id"))
            if isinstance(n1_atual, dict):
                equipe["piloto_numero_1"] = n1_atual.get("id")
                equipe["piloto_1"] = n1_atual.get("nome")
                n1_atual["papel"] = "numero_1"
            if isinstance(n2_atual, dict):
                equipe["piloto_numero_2"] = n2_atual.get("id")
                equipe["piloto_2"] = n2_atual.get("nome")
                n2_atual["papel"] = "numero_2"
            equipe["hierarquia"] = hierarquia

            status_novo = str(hierarquia.get("status", "estavel") or "estavel").strip().lower()
            status_mudou = status_novo != status_anterior
            jogador_env = bool(
                jogador_id
                and (
                    self._ids_equivalentes_resultado(hierarquia.get("n1_id"), jogador_id)
                    or self._ids_equivalentes_resultado(hierarquia.get("n2_id"), jogador_id)
                )
            )
            jogador_agora_n1 = bool(jogador_id and self._ids_equivalentes_resultado(hierarquia.get("n1_id"), jogador_id))
            jogador_virou_n1 = bool(jogador_env and (not jogador_era_n1) and jogador_agora_n1)
            jogador_perdeu_n1 = bool(jogador_env and jogador_era_n1 and (not jogador_agora_n1))

            notificacao = ""
            destaque = False
            if status_mudou and jogador_env:
                if status_novo == "tensao":
                    notificacao = (
                        "Tensao interna: voce esta superando seu companheiro de equipe "
                        "com frequencia nas ultimas corridas."
                    )
                elif status_novo == "invertido":
                    if jogador_virou_n1:
                        notificacao = "Promocao: voce foi promovido a piloto N1 da equipe."
                        destaque = True
                    elif jogador_perdeu_n1:
                        notificacao = "Rebaixamento: voce perdeu a posicao de piloto N1."
                        destaque = True
                    else:
                        notificacao = "A hierarquia interna da equipe foi invertida."
                elif status_novo == "estavel" and status_anterior == "tensao":
                    notificacao = "A situacao interna da equipe estabilizou."

            if status_mudou:
                evento_noticia = ""
                if status_novo == "tensao":
                    evento_noticia = "Tensao entre os pilotos por resultados recentes."
                elif status_novo == "invertido":
                    evento_noticia = "Hierarquia invertida apos sequencia de desempenho do N2."
                elif status_novo == "reavaliacao":
                    evento_noticia = "Equipe iniciou reavaliacao de hierarquia."
                elif status_novo == "estavel" and status_anterior == "tensao":
                    evento_noticia = "Situacao interna estabilizada."
                if evento_noticia:
                    self._obter_gerador_noticias().gerar_noticia_hierarquia(
                        equipe_nome=str(equipe.get("nome", "Equipe") or "Equipe"),
                        evento=evento_noticia,
                        temporada=int(self.banco.get("ano_atual", 2024) or 2024),
                        rodada=rodada_atual,
                    )

            atualizacoes.append(
                {
                    "equipe_id": equipe_id,
                    "status": status_novo,
                    "status_anterior": status_anterior,
                    "status_novo": status_novo,
                    "status_mudou": status_mudou,
                    "corridas_n2_a_frente": int(hierarquia.get("corridas_n2_a_frente", 0) or 0),
                    "inversao": inversao,
                    "rodada": rodada_atual,
                    "foi_corrida_jogador": bool(foi_corrida_jogador),
                    "envolve_jogador": jogador_env,
                    "jogador_virou_n1": jogador_virou_n1,
                    "jogador_perdeu_n1": jogador_perdeu_n1,
                    "notificacao": notificacao,
                    "destaque": destaque,
                }
            )

        return atualizacoes

    def _obter_piloto_por_nome(
        self,
        nome: str,
        categoria_id: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Busca piloto por nome normalizado.
        Retorna None se não encontrar ou se houver ambiguidade.
        """
        categoria = categoria_id or self.categoria_atual
        nome_normalizado = self._normalizar_nome_piloto(nome)

        encontrados = [
            piloto
            for piloto in self._obter_pilotos_da_categoria(categoria)
            if self._normalizar_nome_piloto(piloto.get("nome", "")) == nome_normalizado
        ]

        if len(encontrados) == 1:
            return encontrados[0]

        return None

    # ============================================================
    # RESULTADOS
    # ============================================================

    def _calcular_pontos_da_posicao(
        self,
        posicao: int | None,
        volta_rapida: bool = False,
        dnf: bool = False,
    ) -> int:
        """Calcula os pontos da posição, incluindo volta mais rápida."""
        if dnf or posicao is None:
            return 0

        pontos = int(PONTOS_POR_POSICAO.get(posicao, 0))
        if volta_rapida and posicao is not None and posicao <= 10:
            pontos += 1
        return pontos

    def _resolver_track_id_corrida(
        self,
        rodada: int | None = None,
    ) -> str | None:
        """Resolve o track_id da rodada atual para atualizar historico de circuitos."""
        if rodada is None:
            try:
                rodada = int(self.banco.get("rodada_atual", 1))
            except (TypeError, ValueError):
                rodada = 1
        rodada = max(1, int(rodada))

        calendario = self.banco.get("calendario", [])
        if not isinstance(calendario, list) or not calendario:
            return None
        if rodada > len(calendario):
            rodada = len(calendario)

        corrida = calendario[rodada - 1]
        if not isinstance(corrida, dict):
            return None

        track_raw = corrida.get("trackId", corrida.get("id"))
        if track_raw in (None, ""):
            return None

        try:
            return str(int(track_raw))
        except (TypeError, ValueError):
            return str(track_raw).strip() or None

    def _processar_pos_corrida_evolucao(
        self,
        participantes: list[dict[str, Any]],
        categoria_id: str | None = None,
        rodada: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Executa atualizacoes M6 de pos-corrida para todos os pilotos da classificacao.
        """
        if not participantes:
            return []

        from Logica.evolucao.evolucao_manager import EvolucaoManager
        from Logica.pilotos import atualizar_historico_circuito

        manager = EvolucaoManager()
        grid_size = max(1, len(participantes))
        track_id = self._resolver_track_id_corrida(rodada=rodada)
        total_incidentes = sum(
            int(item.get("incidentes", 0) or 0)
            for item in participantes
            if isinstance(item, dict)
        )

        categoria_alvo = str(categoria_id or self.categoria_atual or "").strip()
        relatorio: list[dict[str, Any]] = []

        for item in participantes:
            piloto = item.get("piloto")
            if not isinstance(piloto, dict):
                continue
            if bool(piloto.get("aposentado", False)):
                continue

            posicao = int(item.get("posicao", grid_size) or grid_size)
            esperado = manager.calcular_posicao_esperada(piloto, grid_size=grid_size)
            foi_dnf = bool(item.get("dnf", False))
            foi_pole = bool(item.get("pole", False))
            dnf_erro_proprio = bool(item.get("erro_piloto", False))
            piloto_teve_incidente = bool(item.get("teve_incidente", False))

            atualizacao = manager.processar_resultado_corrida(
                piloto,
                posicao=posicao,
                expectativa=esperado,
                foi_pole=foi_pole,
                foi_dnf=foi_dnf,
                dnf_erro_proprio=dnf_erro_proprio,
                tipo_incidente="colisao" if (foi_dnf and piloto_teve_incidente) else None,
                total_incidentes_corrida=total_incidentes,
                piloto_teve_incidente=piloto_teve_incidente,
            )

            piloto["corridas_na_categoria"] = int(piloto.get("corridas_na_categoria", 0) or 0) + 1
            if categoria_alvo:
                piloto["categoria_atual"] = categoria_alvo

            if track_id:
                atualizar_historico_circuito(
                    piloto,
                    circuito_id=track_id,
                    posicao=posicao,
                    pole=foi_pole,
                    dnf=foi_dnf,
                )

            ajustes_intermediarios: list[dict[str, float]] = []
            corridas_temporada = int(piloto.get("corridas_temporada", 0) or 0)
            if corridas_temporada > 0 and corridas_temporada % 5 == 0:
                ajustes_intermediarios = manager.evolucao_intermediaria(piloto)

            relatorio.append(
                {
                    "piloto_id": piloto.get("id"),
                    "motivacao": atualizacao.get("motivacao"),
                    "experiencia": atualizacao.get("experiencia"),
                    "ajustes_intermediarios": ajustes_intermediarios,
                }
            )

        return relatorio

    def _garantir_campos_piloto(self, piloto: dict[str, Any]) -> None:
        """Garante que os campos principais existam e tenham tipo consistente."""
        campos_int = (
            "corridas_temporada",
            "corridas_carreira",
            "dnfs_temporada",
            "dnfs_carreira",
            "melhor_resultado_temporada",
            "pontos_temporada",
            "pontos_carreira",
            "vitorias_temporada",
            "vitorias_carreira",
            "podios_temporada",
            "podios_carreira",
            "poles_temporada",
            "poles_carreira",
            "voltas_rapidas_temporada",
            "voltas_rapidas_carreira",
        )

        for campo in campos_int:
            try:
                piloto[campo] = int(piloto.get(campo, 0) or 0)
            except (TypeError, ValueError):
                piloto[campo] = 0

        if piloto["melhor_resultado_temporada"] <= 0:
            piloto["melhor_resultado_temporada"] = 99

        if not isinstance(piloto.get("resultados_temporada"), list):
            piloto["resultados_temporada"] = []

    def _registrar_resultado_piloto(
        self,
        piloto: dict[str, Any],
        posicao: int | None,
        dnf: bool = False,
        volta_rapida: bool = False,
        pole: bool = False,
        pontos_override: int | None = None,
    ) -> int:
        """
        Aplica um resultado a um piloto.
        Retorna os pontos somados na corrida.
        """
        self._garantir_campos_piloto(piloto)

        piloto["corridas_temporada"] += 1
        piloto["corridas_carreira"] += 1

        resultados = piloto["resultados_temporada"]

        if pole:
            piloto["poles_temporada"] += 1
            piloto["poles_carreira"] += 1

        if dnf:
            piloto["dnfs_temporada"] += 1
            piloto["dnfs_carreira"] += 1
            resultados.append("DNF")
            return 0

        pontos: int
        if pontos_override is not None and pontos_override >= 0:
            pontos = int(pontos_override)
        else:
            pontos = self._calcular_pontos_da_posicao(
                posicao=posicao,
                volta_rapida=volta_rapida,
                dnf=False,
            )

        piloto["pontos_temporada"] += pontos
        piloto["pontos_carreira"] += pontos

        if posicao is not None:
            resultados.append(posicao)
            piloto["melhor_resultado_temporada"] = min(
                int(piloto.get("melhor_resultado_temporada", 99)),
                int(posicao),
            )

        if posicao == 1:
            piloto["vitorias_temporada"] += 1
            piloto["vitorias_carreira"] += 1

        if posicao is not None and posicao <= 3:
            piloto["podios_temporada"] += 1
            piloto["podios_carreira"] += 1

        if volta_rapida:
            piloto["voltas_rapidas_temporada"] += 1
            piloto["voltas_rapidas_carreira"] += 1

        return pontos

    def _aplicar_classificacao_por_nome(
        self,
        classificacao: list[dict[str, Any]],
        rodada: int | None = None,
        foi_corrida_jogador: bool = False,
    ) -> int:
        """
        Aplica uma classificação baseada em nome de piloto.
        """
        aplicados: int = 0
        participantes_evolucao: list[dict[str, Any]] = []

        for posicao, entrada in enumerate(classificacao, start=1):
            nome_piloto = entrada.get("piloto") or entrada.get("nome") or ""
            piloto = self._obter_piloto_por_nome(nome_piloto, self.categoria_atual)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))
            try:
                posicao_campeonato = int(
                    entrada.get(
                        "posicao_campeonato",
                        entrada.get("posicao_classe", entrada.get("posicao", posicao)),
                    )
                )
            except (TypeError, ValueError):
                posicao_campeonato = posicao

            pontos_override = entrada.get("pontos")
            if isinstance(pontos_override, bool):
                pontos_override = None
            elif pontos_override is not None:
                try:
                    pontos_override = int(pontos_override)
                except (TypeError, ValueError):
                    pontos_override = None

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao_campeonato,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
                pontos_override=pontos_override,
            )
            try:
                incidentes = int(entrada.get("incidentes", 0) or 0)
            except (TypeError, ValueError):
                incidentes = 0
            participantes_evolucao.append(
                {
                    "piloto": piloto,
                    "piloto_id": piloto.get("id"),
                    "posicao": posicao_campeonato,
                    "dnf": bool(entrada.get("dnf", False)),
                    "pole": pole,
                    "incidentes": incidentes,
                    "teve_incidente": bool(incidentes > 0 or entrada.get("incidente", False)),
                    "erro_piloto": bool(
                        entrada.get(
                            "erro_piloto",
                            entrada.get("dnf_erro_proprio", False),
                        )
                    ),
                }
            )
            aplicados += 1  # type: ignore

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
            )
            self._processar_pos_corrida_evolucao(
                participantes=participantes_evolucao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
            )
            atualizacoes_hierarquia = self._atualizar_hierarquia_pos_corrida(
                resultado_corrida=classificacao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
                foi_corrida_jogador=foi_corrida_jogador,
            )
            if isinstance(atualizacoes_hierarquia, list):
                pendentes = getattr(self, "_notificacoes_hierarquia_pendentes", [])
                if not isinstance(pendentes, list):
                    pendentes = []
                pendentes.extend(
                    item
                    for item in atualizacoes_hierarquia
                    if isinstance(item, dict)
                    and bool(item.get("status_mudou", False))
                )
                self._notificacoes_hierarquia_pendentes = pendentes

        return aplicados

    def _aplicar_classificacao_por_id(
        self,
        classificacao: list[dict[str, Any]],
        rodada: int | None = None,
        foi_corrida_jogador: bool = False,
    ) -> int:
        """
        Aplica uma classificação baseada em id do piloto.
        """
        aplicados: int = 0
        participantes_evolucao: list[dict[str, Any]] = []

        for posicao, entrada in enumerate(classificacao, start=1):
            piloto_id = entrada.get("piloto_id", entrada.get("id"))
            piloto = self._obter_piloto_por_id(piloto_id, self.categoria_atual)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))
            try:
                posicao_campeonato = int(
                    entrada.get(
                        "posicao_campeonato",
                        entrada.get("posicao_classe", entrada.get("posicao", posicao)),
                    )
                )
            except (TypeError, ValueError):
                posicao_campeonato = posicao

            pontos_override = entrada.get("pontos")
            if isinstance(pontos_override, bool):
                pontos_override = None
            elif pontos_override is not None:
                try:
                    pontos_override = int(pontos_override)
                except (TypeError, ValueError):
                    pontos_override = None

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao_campeonato,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
                pontos_override=pontos_override,
            )
            try:
                incidentes = int(entrada.get("incidentes", 0) or 0)
            except (TypeError, ValueError):
                incidentes = 0
            participantes_evolucao.append(
                {
                    "piloto": piloto,
                    "piloto_id": piloto.get("id"),
                    "posicao": posicao_campeonato,
                    "dnf": bool(entrada.get("dnf", False)),
                    "pole": pole,
                    "incidentes": incidentes,
                    "teve_incidente": bool(incidentes > 0 or entrada.get("incidente", False)),
                    "erro_piloto": bool(
                        entrada.get(
                            "erro_piloto",
                            entrada.get("dnf_erro_proprio", False),
                        )
                    ),
                }
            )
            aplicados += 1  # type: ignore

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
            )
            self._processar_pos_corrida_evolucao(
                participantes=participantes_evolucao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
            )
            atualizacoes_hierarquia = self._atualizar_hierarquia_pos_corrida(
                resultado_corrida=classificacao,
                categoria_id=self.categoria_atual,
                rodada=rodada,
                foi_corrida_jogador=foi_corrida_jogador,
            )
            if isinstance(atualizacoes_hierarquia, list):
                pendentes = getattr(self, "_notificacoes_hierarquia_pendentes", [])
                if not isinstance(pendentes, list):
                    pendentes = []
                pendentes.extend(
                    item
                    for item in atualizacoes_hierarquia
                    if isinstance(item, dict)
                    and bool(item.get("status_mudou", False))
                )
                self._notificacoes_hierarquia_pendentes = pendentes

        return aplicados
