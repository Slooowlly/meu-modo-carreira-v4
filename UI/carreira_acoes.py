from __future__ import annotations

from typing import Any, Iterable

from Dados.constantes import PONTOS_POR_POSICAO


class CarreiraAcoesBaseMixin:
    """
    Base compartilhada entre os mixins da carreira.

    Não depende de __init__ e assume que a classe final possui:
        - self.banco
        - self.categoria_atual
        - self._obter_jogador()
    """

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
            from Logica.aiseason import obter_total_etapas_predefinido

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
    # ORDENAÇÃO
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
                piloto.get("id") == piloto_id
                and piloto.get("categoria_atual") == categoria
                and not piloto.get("aposentado", False)
            ):
                return piloto
        return None

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
        if volta_rapida and posicao <= 10:
            pontos += 1
        return pontos

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
            piloto[campo] = int(piloto.get(campo, 0))

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
    ) -> int:
        """
        Aplica uma classificação baseada em nome de piloto.
        """
        aplicados = 0

        for posicao, entrada in enumerate(classificacao, start=1):
            nome_piloto = entrada.get("piloto") or entrada.get("nome") or ""
            piloto = self._obter_piloto_por_nome(nome_piloto, self.categoria_atual)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
            )
            aplicados += 1

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=self.categoria_atual,
            )

        return aplicados

    def _aplicar_classificacao_por_id(
        self,
        classificacao: list[dict[str, Any]],
    ) -> int:
        """
        Aplica uma classificação baseada em id do piloto.
        """
        aplicados = 0

        for posicao, entrada in enumerate(classificacao, start=1):
            piloto_id = entrada.get("piloto_id", entrada.get("id"))
            piloto = self._obter_piloto_por_id(piloto_id, self.categoria_atual)
            if piloto is None:
                continue

            volta_rapida = bool(entrada.get("volta_rapida", False))
            pole = bool(entrada.get("pole", volta_rapida))

            self._registrar_resultado_piloto(
                piloto=piloto,
                posicao=posicao,
                dnf=bool(entrada.get("dnf", False)),
                volta_rapida=volta_rapida,
                pole=pole,
            )
            aplicados += 1

        if aplicados > 0:
            self._registrar_volta_rapida_da_rodada(
                classificacao,
                categoria_id=self.categoria_atual,
            )

        return aplicados
