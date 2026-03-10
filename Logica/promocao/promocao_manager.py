"""Main orchestrator for team promotion/relegation."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional, Tuple

from Logica.equipes import promover_equipe, rebaixar_equipe

from .avaliacao import AvaliacaoEquipe, criar_resultado_temporada, avaliar_equipe
from .clausulas import liberar_pilotos_por_rebaixamento
from .consequencias import (
    aplicar_consequencias,
    calcular_consequencias_promocao,
    calcular_consequencias_rebaixamento,
    simular_impacto,
)
from .convites import gerar_convites_categoria, processar_convites
from .historico import HistoricoGlobal, criar_movimentacao
from .models import (
    ConsequenciasMovimentacao,
    Convite,
    MotivoMovimentacao,
    Movimentacao,
    RelatorioPromocao,
    ResultadoTemporada,
    TipoMovimentacao,
)
from .regras import (
    canonicalizar_categoria_id,
    get_regra_categoria,
    get_todas_categorias,
    resolver_destino_rebaixamento_production,
)


class PromocaoManager:
    def __init__(self, historico: Optional[HistoricoGlobal] = None):
        self.historico = historico or HistoricoGlobal()
        self._resultados_temporada: Dict[str, ResultadoTemporada] = {}
        self._convites_pendentes: List[Convite] = []

    @staticmethod
    def _get(entidade: Any, campo: str, default=None):
        if isinstance(entidade, dict):
            return entidade.get(campo, default)
        return getattr(entidade, campo, default)

    @staticmethod
    def _set(entidade: Any, campo: str, valor):
        if isinstance(entidade, dict):
            entidade[campo] = valor
        else:
            setattr(entidade, campo, valor)

    def registrar_resultado(
        self,
        equipe: Any,
        posicao: int,
        pontos: int,
        total_equipes: int,
        temporada: int,
        vitorias: int = 0,
        podios: int = 0,
        poles: int = 0,
    ):
        resultado = criar_resultado_temporada(
            equipe=equipe,
            posicao=posicao,
            pontos=pontos,
            total_equipes=total_equipes,
            temporada=temporada,
            vitorias=vitorias,
            podios=podios,
            poles=poles,
        )
        self._resultados_temporada[str(resultado.equipe_id)] = resultado
        self.historico.adicionar_resultado_equipe(resultado)

    def avaliar_equipes_categoria(
        self,
        equipes: List[Any],
        categoria_id: str,
        vagas_promocao_override: Optional[int] = None,
    ) -> List[AvaliacaoEquipe]:
        avaliacoes: List[AvaliacaoEquipe] = []
        for equipe in equipes:
            equipe_id = str(self._get(equipe, "id", str(id(equipe))))
            resultado = self._resultados_temporada.get(equipe_id)
            if not resultado:
                continue
            historico = self.historico.get_historico_equipe(equipe_id)
            avaliacoes.append(
                avaliar_equipe(
                    equipe=equipe,
                    resultado=resultado,
                    historico=historico,
                    vagas_promocao_override=vagas_promocao_override,
                )
            )
        return avaliacoes

    def _detectar_rebaixamentos_endurance(self, equipes_endurance: List[Any]) -> List[Tuple[Any, str]]:
        por_classe: Dict[str, List[Tuple[Any, ResultadoTemporada]]] = {"gt3": [], "gt4": []}

        for equipe in equipes_endurance:
            equipe_id = str(self._get(equipe, "id", str(id(equipe))))
            resultado = self._resultados_temporada.get(equipe_id)
            if not resultado:
                continue

            classe = str(self._get(equipe, "classe_endurance", resultado.classe_endurance or "")).strip().lower()
            if classe not in por_classe:
                continue
            por_classe[classe].append((equipe, resultado))

        rebaixar: List[Tuple[Any, str]] = []
        for classe, items in por_classe.items():
            if not items:
                continue
            piores = sorted(
                items,
                key=lambda par: (
                    int(par[1].pontos_construtores),
                    -int(par[1].posicao_construtores),
                    str(self._get(par[0], "nome", "")).casefold(),
                ),
            )[:3]
            destino = "gt3" if classe == "gt3" else "gt4"
            for equipe, _resultado in piores:
                rebaixar.append((equipe, destino))

        return rebaixar

    def _detectar_rebaixamentos_production(self, equipes_production: List[Any]) -> List[Tuple[Any, str]]:
        por_classe: Dict[str, List[Tuple[Any, ResultadoTemporada]]] = {
            "mazda": [],
            "toyota": [],
            "bmw_m2": [],
        }
        destino_por_classe = {
            "mazda": "mazda_amador",
            "toyota": "toyota_amador",
            "bmw_m2": "bmw_m2",
        }

        for equipe in equipes_production:
            equipe_id = str(self._get(equipe, "id", str(id(equipe))))
            resultado = self._resultados_temporada.get(equipe_id)
            if not resultado:
                continue

            classe = str(self._get(equipe, "carro_classe", "")).strip().lower()
            if classe not in por_classe:
                continue
            por_classe[classe].append((equipe, resultado))

        rebaixar: List[Tuple[Any, str]] = []
        for classe, items in por_classe.items():
            if not items:
                continue
            piores = sorted(
                items,
                key=lambda par: (
                    int(par[1].pontos_construtores),
                    -int(par[1].posicao_construtores),
                    str(self._get(par[0], "nome", "")).casefold(),
                ),
            )[:3]

            destino = destino_por_classe.get(classe)
            if not destino:
                continue
            for equipe, _resultado in piores:
                rebaixar.append((equipe, destino))

        return rebaixar

    def _aplicar_movimentacao_categoria(self, equipe: Any, tipo: TipoMovimentacao, categoria_destino: str):
        categoria_destino = canonicalizar_categoria_id(categoria_destino)
        categoria_origem = canonicalizar_categoria_id(
            str(self._get(equipe, "categoria", self._get(equipe, "categoria_id", "")) or "")
        )

        if tipo == TipoMovimentacao.PROMOCAO:
            promover_equipe(equipe, categoria_destino)
            if categoria_destino == "endurance":
                classe = str(self._get(equipe, "classe_endurance", "")).strip().lower()
                if classe not in {"gt3", "gt4", "lmp2"}:
                    if categoria_origem == "gt4":
                        classe = "gt4"
                    elif categoria_origem == "gt3":
                        classe = "gt3"
                    else:
                        classe = "gt3"
                self._set(equipe, "classe_endurance", classe)
        elif tipo == TipoMovimentacao.REBAIXAMENTO:
            rebaixar_equipe(equipe, categoria_destino)
            # Out of endurance; clear class tag.
            if categoria_destino in {"gt3", "gt4", "production_challenger", "bmw_m2", "mazda_amador", "toyota_amador"}:
                if self._get(equipe, "categoria", "") != "endurance":
                    self._set(equipe, "classe_endurance", None)

    def _processar_promocao(
        self,
        relatorio: RelatorioPromocao,
        equipe: Any,
        avaliacao: AvaliacaoEquipe,
        temporada: int,
        aplicar_automaticamente: bool,
    ):
        regra_destino = get_regra_categoria(avaliacao.categoria_destino or "")
        tier_destino = int(regra_destino.tier if regra_destino else 1)

        consequencias = calcular_consequencias_promocao(equipe, tier_destino)
        mov = criar_movimentacao(
            equipe=equipe,
            tipo=TipoMovimentacao.PROMOCAO,
            motivo=avaliacao.motivo,
            temporada=temporada,
            categoria_origem=avaliacao.categoria_id,
            categoria_destino=str(avaliacao.categoria_destino or ""),
            posicao=avaliacao.posicao,
            pontos=avaliacao.pontos,
            consequencias=consequencias,
        )

        relatorio.promocoes.append(mov)
        self.historico.adicionar_movimentacao(mov)

        if aplicar_automaticamente:
            self._aplicar_movimentacao_categoria(equipe, TipoMovimentacao.PROMOCAO, str(avaliacao.categoria_destino or ""))
            aplicar_consequencias(equipe, consequencias)

        relatorio.adicionar_destaque(
            f"{avaliacao.equipe_nome} promovida para {avaliacao.categoria_destino}."
        )

    def _processar_rebaixamento(
        self,
        relatorio: RelatorioPromocao,
        equipe: Any,
        motivo: MotivoMovimentacao,
        categoria_origem: str,
        categoria_destino: str,
        temporada: int,
        posicao: int,
        pontos: int,
        aplicar_automaticamente: bool,
    ):
        regra_destino = get_regra_categoria(categoria_destino)
        tier_destino = int(regra_destino.tier if regra_destino else 1)

        consequencias = calcular_consequencias_rebaixamento(equipe, tier_destino)
        mov = criar_movimentacao(
            equipe=equipe,
            tipo=TipoMovimentacao.REBAIXAMENTO,
            motivo=motivo,
            temporada=temporada,
            categoria_origem=categoria_origem,
            categoria_destino=categoria_destino,
            posicao=posicao,
            pontos=pontos,
            consequencias=consequencias,
        )

        relatorio.rebaixamentos.append(mov)
        self.historico.adicionar_movimentacao(mov)

        if aplicar_automaticamente:
            self._aplicar_movimentacao_categoria(equipe, TipoMovimentacao.REBAIXAMENTO, categoria_destino)
            aplicar_consequencias(equipe, consequencias)

        relatorio.adicionar_destaque(
            f"{self._get(equipe, 'nome', 'Equipe')} rebaixada para {categoria_destino}."
        )

    def processar_fim_temporada(
        self,
        equipes_por_categoria: Dict[str, List[Any]],
        temporada: int,
        banco: Optional[dict] = None,
        aplicar_automaticamente: bool = False,
    ) -> RelatorioPromocao:
        relatorio = RelatorioPromocao(temporada=int(temporada))

        equipes_dict: Dict[str, Any] = {}
        for equipes in equipes_por_categoria.values():
            for equipe in equipes:
                equipes_dict[str(self._get(equipe, "id", str(id(equipe))))] = equipe

        # Endurance relegation opens class slots.
        endurance_equipes = equipes_por_categoria.get("endurance", [])
        rebaixamentos_endurance = self._detectar_rebaixamentos_endurance(endurance_equipes)
        vagas_endurance_por_classe = {
            "gt3": sum(1 for _, destino in rebaixamentos_endurance if destino == "gt3"),
            "gt4": sum(1 for _, destino in rebaixamentos_endurance if destino == "gt4"),
        }

        # Production relegation is class-based (3 por classe).
        production_equipes = equipes_por_categoria.get("production_challenger", [])
        rebaixamentos_production = self._detectar_rebaixamentos_production(production_equipes)

        todas_avaliacoes: List[AvaliacaoEquipe] = []
        for categoria_id, equipes in equipes_por_categoria.items():
            categoria_norm = canonicalizar_categoria_id(categoria_id)
            if categoria_norm == "endurance":
                continue

            vagas_override = None
            if categoria_norm == "gt3":
                vagas_override = vagas_endurance_por_classe.get("gt3", 0)
            elif categoria_norm == "gt4":
                vagas_override = vagas_endurance_por_classe.get("gt4", 0)

            avaliacoes = self.avaliar_equipes_categoria(
                equipes=equipes,
                categoria_id=categoria_norm,
                vagas_promocao_override=vagas_override,
            )
            todas_avaliacoes.extend(avaliacoes)

        # Automatic promotions.
        for avaliacao in todas_avaliacoes:
            if avaliacao.tipo_movimentacao != TipoMovimentacao.PROMOCAO:
                continue
            equipe = equipes_dict.get(avaliacao.equipe_id)
            if not equipe:
                continue
            self._processar_promocao(
                relatorio=relatorio,
                equipe=equipe,
                avaliacao=avaliacao,
                temporada=int(temporada),
                aplicar_automaticamente=aplicar_automaticamente,
            )

        # Optional invitations for non-gt3/gt4 categories.
        convites: List[Convite] = []
        for categoria_id, equipes in equipes_por_categoria.items():
            categoria_norm = canonicalizar_categoria_id(categoria_id)
            if categoria_norm in {"gt3", "gt4", "endurance"}:
                continue
            historicos = {
                str(self._get(equipe, "id", str(id(equipe)))): self.historico.get_historico_equipe(
                    str(self._get(equipe, "id", str(id(equipe))))
                )
                for equipe in equipes
            }
            resultados = {
                str(self._get(equipe, "id", str(id(equipe)))): self._resultados_temporada.get(
                    str(self._get(equipe, "id", str(id(equipe))))
                )
                for equipe in equipes
            }
            convites.extend(
                gerar_convites_categoria(
                    equipes=equipes,
                    resultados={k: v for k, v in resultados.items() if v is not None},
                    historicos=historicos,
                    categoria_id=categoria_norm,
                    temporada=int(temporada),
                )
            )

        relatorio.convites_enviados = list(convites)
        aceitos, recusados = processar_convites(convites, equipes_dict)
        relatorio.convites_aceitos = list(aceitos)
        relatorio.convites_recusados = list(recusados)

        for convite in aceitos:
            equipe = equipes_dict.get(convite.equipe_id)
            if not equipe:
                continue

            consequencias = calcular_consequencias_promocao(equipe, convite.categoria_destino_tier)
            mov = criar_movimentacao(
                equipe=equipe,
                tipo=TipoMovimentacao.PROMOCAO,
                motivo=MotivoMovimentacao.CONVITE_ACEITO,
                temporada=int(temporada),
                categoria_origem=convite.categoria_origem_id,
                categoria_destino=convite.categoria_destino_id,
                consequencias=consequencias,
            )
            relatorio.promocoes.append(mov)
            self.historico.adicionar_movimentacao(mov)
            if aplicar_automaticamente:
                self._aplicar_movimentacao_categoria(equipe, TipoMovimentacao.PROMOCAO, convite.categoria_destino_id)
                aplicar_consequencias(equipe, consequencias)
            relatorio.adicionar_destaque(
                f"{convite.equipe_nome} aceitou convite para {convite.categoria_destino_id}."
            )

        # Local relegations (except endurance handled below).
        for avaliacao in todas_avaliacoes:
            if avaliacao.tipo_movimentacao != TipoMovimentacao.REBAIXAMENTO:
                continue
            if avaliacao.categoria_id == "production_challenger":
                continue
            equipe = equipes_dict.get(avaliacao.equipe_id)
            if not equipe:
                continue

            destino = str(avaliacao.categoria_destino or "")
            if avaliacao.categoria_id == "production_challenger" and not destino:
                destino = resolver_destino_rebaixamento_production(equipe)
            if not destino:
                continue

            self._processar_rebaixamento(
                relatorio=relatorio,
                equipe=equipe,
                motivo=avaliacao.motivo,
                categoria_origem=avaliacao.categoria_id,
                categoria_destino=destino,
                temporada=int(temporada),
                posicao=avaliacao.posicao,
                pontos=avaliacao.pontos,
                aplicar_automaticamente=aplicar_automaticamente,
            )

        # Production class-based relegations.
        for equipe, destino in rebaixamentos_production:
            equipe_id = str(self._get(equipe, "id", str(id(equipe))))
            resultado = self._resultados_temporada.get(equipe_id)
            self._processar_rebaixamento(
                relatorio=relatorio,
                equipe=equipe,
                motivo=MotivoMovimentacao.ULTIMO_LUGAR,
                categoria_origem="production_challenger",
                categoria_destino=destino,
                temporada=int(temporada),
                posicao=int(resultado.posicao_construtores if resultado else 0),
                pontos=int(resultado.pontos_construtores if resultado else 0),
                aplicar_automaticamente=aplicar_automaticamente,
            )

        # Endurance class-based relegations.
        for equipe, destino in rebaixamentos_endurance:
            equipe_id = str(self._get(equipe, "id", str(id(equipe))))
            resultado = self._resultados_temporada.get(equipe_id)
            self._processar_rebaixamento(
                relatorio=relatorio,
                equipe=equipe,
                motivo=MotivoMovimentacao.ULTIMO_LUGAR,
                categoria_origem="endurance",
                categoria_destino=destino,
                temporada=int(temporada),
                posicao=int(resultado.posicao_construtores if resultado else 0),
                pontos=int(resultado.pontos_construtores if resultado else 0),
                aplicar_automaticamente=aplicar_automaticamente,
            )

        # Trigger market clause releases for relegated teams.
        if banco is not None:
            equipes_rebaixadas = {mov.equipe_id for mov in relatorio.rebaixamentos}
            pilotos_liberados = liberar_pilotos_por_rebaixamento(banco, equipes_rebaixadas)
            relatorio.total_pilotos_liberados = len(pilotos_liberados)
            if pilotos_liberados:
                relatorio.adicionar_destaque(
                    f"{len(pilotos_liberados)} pilotos ativaram clausula de saida por rebaixamento."
                )
                pilotos_por_equipe: Dict[str, List[str]] = {}
                for pid in pilotos_liberados:
                    for mov in relatorio.rebaixamentos:
                        if pid not in mov.pilotos_que_sairam:
                            mov.pilotos_que_sairam.append(pid)
                        pilotos_por_equipe.setdefault(mov.equipe_id, []).append(pid)

        relatorio.total_equipes_promovidas = len(relatorio.promocoes)
        relatorio.total_equipes_rebaixadas = len(relatorio.rebaixamentos)
        return relatorio

    def simular_movimentacao(self, equipe: Any, tipo: TipoMovimentacao, categoria_destino: str) -> ConsequenciasMovimentacao:
        regra = get_regra_categoria(categoria_destino)
        tier_destino = int(regra.tier if regra else 1)
        return simular_impacto(equipe, tipo, tier_destino)

    def get_historico_equipe(self, equipe_id: str):
        return self.historico.get_historico_equipe(equipe_id)

    def get_movimentacoes_temporada(self, temporada: int) -> List[Movimentacao]:
        return self.historico.get_movimentacoes_temporada(temporada)

    def limpar_cache_temporada(self):
        self._resultados_temporada.clear()
        self._convites_pendentes.clear()

    def get_estatisticas_globais(self) -> dict:
        total_promocoes = sum(1 for mov in self.historico.movimentacoes if mov.tipo == TipoMovimentacao.PROMOCAO)
        total_rebaixamentos = sum(1 for mov in self.historico.movimentacoes if mov.tipo == TipoMovimentacao.REBAIXAMENTO)

        promocoes_por_equipe: Dict[str, int] = {}
        rebaixamentos_por_equipe: Dict[str, int] = {}

        for mov in self.historico.movimentacoes:
            if mov.tipo == TipoMovimentacao.PROMOCAO:
                promocoes_por_equipe[mov.equipe_nome] = promocoes_por_equipe.get(mov.equipe_nome, 0) + 1
            elif mov.tipo == TipoMovimentacao.REBAIXAMENTO:
                rebaixamentos_por_equipe[mov.equipe_nome] = rebaixamentos_por_equipe.get(mov.equipe_nome, 0) + 1

        return {
            "total_promocoes": total_promocoes,
            "total_rebaixamentos": total_rebaixamentos,
            "temporadas_registradas": len({mov.temporada for mov in self.historico.movimentacoes}),
            "equipes_registradas": len(self.historico.historicos_equipes),
            "top_promocoes": sorted(promocoes_por_equipe.items(), key=lambda item: item[1], reverse=True)[:5],
            "top_rebaixamentos": sorted(rebaixamentos_por_equipe.items(), key=lambda item: item[1], reverse=True)[:5],
        }


# Utility functions

def processar_promocoes_simples(
    equipes: List[Any],
    resultados: Dict[str, dict],
    temporada: int,
    categoria_id: str,
) -> Tuple[List[Any], List[Any]]:
    _ = temporada
    from .regras import get_vagas_promocao, get_vagas_rebaixamento

    vagas_promo = get_vagas_promocao(categoria_id)
    vagas_rebaixa = get_vagas_rebaixamento(categoria_id)
    categoria_norm = canonicalizar_categoria_id(categoria_id)

    equipes_ordenadas = sorted(
        equipes,
        key=lambda equipe: int(
            resultados.get(str(PromocaoManager._get(equipe, "id", "")), {}).get("posicao", 999)
        ),
    )

    if categoria_norm == "production_challenger":
        rebaixadas: List[Any] = []
        for classe in ("mazda", "toyota", "bmw_m2"):
            equipes_classe = [
                equipe for equipe in equipes_ordenadas
                if str(PromocaoManager._get(equipe, "carro_classe", "")).strip().lower() == classe
            ]
            if not equipes_classe:
                continue
            rebaixadas.extend(equipes_classe[-3:])
        return [], rebaixadas

    if categoria_norm == "endurance":
        rebaixadas = []
        for classe in ("gt3", "gt4"):
            equipes_classe = [
                equipe for equipe in equipes_ordenadas
                if str(PromocaoManager._get(equipe, "classe_endurance", "")).strip().lower() == classe
            ]
            if not equipes_classe:
                continue
            rebaixadas.extend(equipes_classe[-3:])
        return [], rebaixadas

    promovidas = equipes_ordenadas[:vagas_promo]
    rebaixadas = equipes_ordenadas[-vagas_rebaixa:] if vagas_rebaixa > 0 else []
    return promovidas, rebaixadas


def aplicar_promocao_simples(equipe: Any, categoria_destino: str):
    from random import randint

    promover_equipe(equipe, canonicalizar_categoria_id(categoria_destino))

    if isinstance(equipe, dict):
        if "car_performance" in equipe:
            equipe["car_performance"] = min(100, float(equipe.get("car_performance", 50)) + randint(5, 10))
        if "budget" in equipe:
            equipe["budget"] = min(100, float(equipe.get("budget", 50)) + randint(5, 15))
            if "orcamento" in equipe:
                equipe["orcamento"] = equipe["budget"]
        if "morale" in equipe:
            equipe["morale"] = 1.15
        if "reputacao" in equipe:
            equipe["reputacao"] = min(100, float(equipe.get("reputacao", 50)) + randint(3, 8))


def aplicar_rebaixamento_simples(equipe: Any, categoria_destino: str):
    from random import randint

    rebaixar_equipe(equipe, canonicalizar_categoria_id(categoria_destino))

    if isinstance(equipe, dict):
        if "car_performance" in equipe:
            equipe["car_performance"] = max(30, float(equipe.get("car_performance", 50)) + randint(-8, -3))
        if "budget" in equipe:
            equipe["budget"] = max(10, float(equipe.get("budget", 50)) + randint(-15, -5))
            if "orcamento" in equipe:
                equipe["orcamento"] = equipe["budget"]
        if "morale" in equipe:
            equipe["morale"] = 0.75
        if "reputacao" in equipe:
            equipe["reputacao"] = max(0, float(equipe.get("reputacao", 50)) + randint(-10, -5))


def relatorio_to_dict(relatorio: RelatorioPromocao) -> dict:
    return asdict(relatorio)
