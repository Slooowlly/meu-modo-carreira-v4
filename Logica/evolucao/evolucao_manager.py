"""
Orquestrador principal do sistema de evolucao.
Coordena os subsistemas e aplica evolucao aos pilotos.
"""

import random
from dataclasses import dataclass, field
from typing import Any, Optional

from .aposentadoria import verificar_aposentadoria
from .crescimento import processar_crescimento
from .declinio import processar_declinio
from .experiencia import atualizar_experiencia
from .lesoes import processar_lesao_pos_corrida, verificar_lesao
from .models import (
    AposentadoriaCausa,
    ContextoTemporada,
    EvolucaoAtributo,
    Lesao,
    LesaoTipo,
    RelatorioEvolucao,
)
from .motivacao import (
    atualizar_motivacao_corrida,
    atualizar_motivacao_fim_temporada,
    calcular_motivacao_media_temporada,
)


def _get_valor(pilot: Any, campo: str, default=None, aliases: tuple[str, ...] = ()):
    nomes = (campo, *aliases)
    if isinstance(pilot, dict):
        for nome in nomes:
            if nome in pilot:
                return pilot.get(nome, default)
        return default
    for nome in nomes:
        if hasattr(pilot, nome):
            return getattr(pilot, nome)
    return default


def _set_valor(pilot: Any, campo: str, valor, aliases: tuple[str, ...] = ()):
    nomes = (campo, *aliases)
    if isinstance(pilot, dict):
        for nome in nomes:
            if nome in pilot:
                pilot[nome] = valor
                return
        pilot[campo] = valor
        return

    for nome in nomes:
        if hasattr(pilot, nome):
            setattr(pilot, nome, valor)
            return
    setattr(pilot, campo, valor)


def _pilot_id(pilot: Any) -> str:
    return str(_get_valor(pilot, "id", str(id(pilot))))


def _pilot_name(pilot: Any) -> str:
    return str(_get_valor(pilot, "name", _get_valor(pilot, "nome", "Unknown")))


def _normalizar_lesao_tipo(valor) -> LesaoTipo:
    if isinstance(valor, LesaoTipo):
        return valor
    if isinstance(valor, str):
        chave = valor.strip().lower()
        for item in LesaoTipo:
            if item.value == chave:
                return item
    return LesaoTipo.NENHUMA


def _extrair_lesao_do_piloto(pilot: Any) -> Optional[Lesao]:
    lesao_raw = _get_valor(pilot, "lesao", None)
    if not lesao_raw:
        return None

    if isinstance(lesao_raw, Lesao):
        return lesao_raw if lesao_raw.esta_ativa else None

    if isinstance(lesao_raw, dict):
        tipo = _normalizar_lesao_tipo(lesao_raw.get("tipo"))
        corridas = int(lesao_raw.get("corridas_restantes", 0) or 0)
        penalidade = float(lesao_raw.get("penalidade_skill", 0.0) or 0.0)
        if penalidade <= 0:
            modifier = float(lesao_raw.get("modifier", 1.0) or 1.0)
            penalidade = max(0.0, min(1.0, 1.0 - modifier))

        lesao = Lesao(
            tipo=tipo,
            corridas_restantes=corridas,
            penalidade_skill=penalidade,
            causa=str(lesao_raw.get("causa", "acidente")),
        )
        return lesao if lesao.esta_ativa else None

    return None


def _sincronizar_lesao_no_piloto(pilot: Any, lesao: Optional[Lesao]):
    ativa = bool(lesao and lesao.esta_ativa)

    if ativa and lesao is not None:
        lesao_dict = {
            "tipo": lesao.tipo.value,
            "corridas_restantes": lesao.corridas_restantes,
            "modifier": round(1.0 - lesao.penalidade_skill, 3),
            "penalidade_skill": lesao.penalidade_skill,
            "causa": lesao.causa,
        }
        _set_valor(pilot, "lesao", lesao_dict)
        _set_valor(pilot, "lesionado", True)
        _set_valor(pilot, "severidade_lesao", lesao.penalidade_skill)
        _set_valor(pilot, "corridas_lesao", lesao.corridas_restantes)
        return

    _set_valor(pilot, "lesao", None)
    _set_valor(pilot, "lesionado", False)
    _set_valor(pilot, "severidade_lesao", 0.0)
    _set_valor(pilot, "corridas_lesao", 0)


@dataclass
class EstadoPilotoTemporada:
    """Estado do piloto durante a temporada."""

    pilot_id: str

    historico_motivacao: list[float] = field(default_factory=list)

    resultados: list[int] = field(default_factory=list)
    expectativas: list[int] = field(default_factory=list)

    vitorias: int = 0
    podios: int = 0
    poles: int = 0
    dnfs: int = 0

    lesao: Optional[Lesao] = None

    temporadas_motivacao_baixa: int = 0
    temporadas_na_categoria: int = 1


class EvolucaoManager:
    """
    Gerenciador principal de evolucao de pilotos.
    """

    _ALIASES_ATRIBUTOS: dict[str, tuple[str, ...]] = {
        "clutch_factor": ("fator_clutch",),
        "experience": ("experiencia",),
    }
    _ATRIBUTOS_INTERMEDIARIOS = (
        "consistencia",
        "racecraft",
        "gestao_pneus",
        "habilidade_largada",
        "fator_chuva",
    )
    _CAMPOS_ESTADO_TEMPORADA = (
        "historico_motivacao_temporada",
        "evolucao_resultados_temporada",
        "evolucao_expectativas_temporada",
    )

    def __init__(self):
        self._estados: dict[str, EstadoPilotoTemporada] = {}

    def _get_estado(self, pilot_id: str) -> EstadoPilotoTemporada:
        if pilot_id not in self._estados:
            self._estados[pilot_id] = EstadoPilotoTemporada(pilot_id=pilot_id)
        return self._estados[pilot_id]

    def iniciar_temporada(self, pilot_id: str, temporadas_na_categoria: int = 1):
        """
        Inicializa estado do piloto para nova temporada.
        """
        self._estados[pilot_id] = EstadoPilotoTemporada(
            pilot_id=pilot_id,
            temporadas_na_categoria=temporadas_na_categoria,
        )

    def _coletar_ints(self, valores: Any) -> list[int]:
        if not isinstance(valores, list):
            return []
        saida: list[int] = []
        for valor in valores:
            if isinstance(valor, bool):
                continue
            if isinstance(valor, (int, float)):
                saida.append(int(valor))
        return saida

    def _hidratar_estado_do_piloto(self, pilot: Any, estado: EstadoPilotoTemporada) -> None:
        if not isinstance(pilot, dict):
            return

        if not estado.historico_motivacao:
            motivacoes = pilot.get("historico_motivacao_temporada", [])
            if isinstance(motivacoes, list):
                estado.historico_motivacao = [
                    float(valor)
                    for valor in motivacoes
                    if isinstance(valor, (int, float)) and not isinstance(valor, bool)
                ]

        if not estado.resultados:
            estado.resultados = self._coletar_ints(pilot.get("evolucao_resultados_temporada", []))
        if not estado.expectativas:
            estado.expectativas = self._coletar_ints(pilot.get("evolucao_expectativas_temporada", []))

        if not estado.resultados:
            resultados_temporada = pilot.get("resultados_temporada", [])
            if isinstance(resultados_temporada, list):
                for item in resultados_temporada:
                    if isinstance(item, bool):
                        continue
                    if isinstance(item, (int, float)):
                        estado.resultados.append(int(item))

        if len(estado.expectativas) < len(estado.resultados):
            grid = max(1, int(_get_valor(pilot, "corridas_temporada", 1) or 1))
            esperado_padrao = self.calcular_posicao_esperada(pilot, grid_size=max(10, grid))
            faltantes = len(estado.resultados) - len(estado.expectativas)
            estado.expectativas.extend([esperado_padrao] * faltantes)

        estado.vitorias = int(_get_valor(pilot, "vitorias_temporada", estado.vitorias) or 0)
        estado.podios = int(_get_valor(pilot, "podios_temporada", estado.podios) or 0)
        estado.poles = int(_get_valor(pilot, "poles_temporada", estado.poles) or 0)
        estado.dnfs = int(_get_valor(pilot, "dnfs_temporada", estado.dnfs) or 0)
        estado.temporadas_motivacao_baixa = int(
            _get_valor(pilot, "temporadas_motivacao_baixa", estado.temporadas_motivacao_baixa) or 0
        )
        estado.temporadas_na_categoria = max(
            1,
            int(_get_valor(pilot, "temporadas_na_categoria", estado.temporadas_na_categoria) or 1),
        )

    def _sincronizar_estado_no_piloto(self, pilot: Any, estado: EstadoPilotoTemporada) -> None:
        if not isinstance(pilot, dict):
            return
        pilot["historico_motivacao_temporada"] = [round(float(v), 2) for v in estado.historico_motivacao]
        pilot["evolucao_resultados_temporada"] = [int(v) for v in estado.resultados]
        pilot["evolucao_expectativas_temporada"] = [int(v) for v in estado.expectativas]
        pilot["temporadas_motivacao_baixa"] = int(estado.temporadas_motivacao_baixa)

    def _limpar_dados_temporada_evolucao(self, pilot: Any) -> None:
        if not isinstance(pilot, dict):
            return
        for campo in self._CAMPOS_ESTADO_TEMPORADA:
            pilot[campo] = []

    def calcular_posicao_esperada(self, pilot: Any, grid_size: int) -> int:
        grid = max(1, int(grid_size))
        skill = float(_get_valor(pilot, "skill", 50.0) or 50.0)
        skill_ratio = max(0.0, min(1.0, skill / 100.0))
        posicao = int(grid * (1.0 - skill_ratio))
        return max(1, min(grid, posicao))

    def evolucao_intermediaria(self, pilot: Any) -> list[dict[str, float]]:
        """
        Aplica ajustes pequenos (a cada 5 corridas) em 1-2 atributos.
        """
        potencial = float(_get_valor(pilot, "potencial", _get_valor(pilot, "potencial_base", 100.0)) or 100.0)
        motivacao = float(_get_valor(pilot, "motivacao", 50.0) or 50.0)
        fator_motivacao = max(0.0, min(1.0, motivacao / 100.0))

        quantidade = random.randint(1, 2)
        atributos = random.sample(self._ATRIBUTOS_INTERMEDIARIOS, k=quantidade)
        ajustes: list[dict[str, float]] = []

        for atributo in atributos:
            valor_atual = float(_get_valor(pilot, atributo, 50.0) or 50.0)
            delta = random.uniform(-0.5, 1.0) * fator_motivacao
            valor_novo = max(20.0, min(potencial, valor_atual + delta))
            valor_novo = round(valor_novo, 2)
            aliases = self._ALIASES_ATRIBUTOS.get(atributo, ())
            _set_valor(pilot, atributo, valor_novo, aliases=aliases)
            ajustes.append(
                {
                    "atributo": atributo,
                    "anterior": round(valor_atual, 2),
                    "novo": valor_novo,
                    "delta": round(valor_novo - valor_atual, 2),
                }
            )

        return ajustes

    def processar_resultado_corrida(
        self,
        pilot: Any,
        posicao: int,
        expectativa: int,
        foi_pole: bool = False,
        foi_dnf: bool = False,
        dnf_erro_proprio: bool = False,
        tipo_incidente: Optional[str] = None,
        total_incidentes_corrida: int = 0,
        piloto_teve_incidente: Optional[bool] = None,
    ) -> dict:
        """
        Processa resultado de uma corrida.
        """
        pid = _pilot_id(pilot)
        estado = self._get_estado(pid)
        self._hidratar_estado_do_piloto(pilot, estado)
        resultado: dict[str, Any] = {}

        estado.resultados.append(int(posicao))
        estado.expectativas.append(int(expectativa))

        estado.vitorias = int(_get_valor(pilot, "vitorias_temporada", estado.vitorias) or 0)
        estado.podios = int(_get_valor(pilot, "podios_temporada", estado.podios) or 0)
        estado.poles = int(_get_valor(pilot, "poles_temporada", estado.poles) or 0)
        estado.dnfs = int(_get_valor(pilot, "dnfs_temporada", estado.dnfs) or 0)

        motivacao_atual = float(_get_valor(pilot, "motivacao", 50.0))
        nova_motivacao, ajustes_mot = atualizar_motivacao_corrida(
            motivacao_atual=motivacao_atual,
            posicao=posicao,
            expectativa=expectativa,
            foi_vitoria=(posicao == 1),
            foi_podio=(posicao <= 3),
            foi_pole=foi_pole,
            foi_dnf=foi_dnf,
            dnf_erro_proprio=dnf_erro_proprio,
        )
        _set_valor(pilot, "motivacao", nova_motivacao)
        estado.historico_motivacao.append(nova_motivacao)
        resultado["motivacao"] = {
            "anterior": motivacao_atual,
            "nova": nova_motivacao,
            "ajustes": [str(a) for a in ajustes_mot],
        }

        experiencia_atual = float(
            _get_valor(pilot, "experience", _get_valor(pilot, "experiencia", 0.0))
        )
        if isinstance(piloto_teve_incidente, bool):
            teve_incidente = piloto_teve_incidente
        else:
            teve_incidente = tipo_incidente is not None
        nova_exp, ganhos_exp = atualizar_experiencia(
            experiencia_atual=experiencia_atual,
            posicao=posicao,
            total_incidentes_corrida=total_incidentes_corrida,
            piloto_teve_incidente=teve_incidente,
        )
        _set_valor(pilot, "experience", nova_exp, aliases=("experiencia",))
        resultado["experiencia"] = {
            "anterior": experiencia_atual,
            "nova": nova_exp,
            "ganhos": [str(g) for g in ganhos_exp],
        }

        if tipo_incidente and foi_dnf:
            nova_lesao = verificar_lesao(tipo_incidente)
            if nova_lesao:
                estado.lesao = nova_lesao
                _sincronizar_lesao_no_piloto(pilot, estado.lesao)
                resultado["lesao"] = {
                    "tipo": nova_lesao.tipo.value,
                    "corridas": nova_lesao.corridas_restantes,
                    "penalidade": nova_lesao.penalidade_skill,
                }
        elif estado.lesao:
            estado.lesao = processar_lesao_pos_corrida(estado.lesao)
            _sincronizar_lesao_no_piloto(pilot, estado.lesao)
            if estado.lesao:
                resultado["lesao_atual"] = {
                    "tipo": estado.lesao.tipo.value,
                    "corridas_restantes": estado.lesao.corridas_restantes,
                }
            else:
                resultado["lesao_curada"] = True

        self._sincronizar_estado_no_piloto(pilot, estado)
        return resultado

    def processar_fim_temporada(
        self,
        pilot: Any,
        ctx: ContextoTemporada,
    ) -> RelatorioEvolucao:
        """
        Processa evolucao de fim de temporada.
        """
        pid = _pilot_id(pilot)
        estado = self._get_estado(pid)
        self._hidratar_estado_do_piloto(pilot, estado)

        if estado.lesao is None:
            estado.lesao = _extrair_lesao_do_piloto(pilot)

        if estado.resultados:
            ctx.resultados = list(estado.resultados)
        elif not ctx.resultados and isinstance(pilot, dict):
            ctx.resultados = self._coletar_ints(pilot.get("resultados_temporada", []))

        if estado.expectativas:
            ctx.expectativas = list(estado.expectativas)
        elif not ctx.expectativas:
            esperado_padrao = self.calcular_posicao_esperada(
                pilot,
                grid_size=max(10, len(ctx.resultados) or 10),
            )
            ctx.expectativas = [esperado_padrao] * len(ctx.resultados)

        ctx.vitorias = int(_get_valor(pilot, "vitorias_temporada", estado.vitorias) or 0)
        ctx.podios = int(_get_valor(pilot, "podios_temporada", estado.podios) or 0)
        ctx.poles = int(_get_valor(pilot, "poles_temporada", estado.poles) or 0)
        ctx.dnfs = int(_get_valor(pilot, "dnfs_temporada", estado.dnfs) or 0)
        ctx.corridas_disputadas = int(
            _get_valor(pilot, "corridas_temporada", len(ctx.resultados))
            or len(ctx.resultados)
        )

        skill_anterior = float(_get_valor(pilot, "skill", 60.0))
        potencial = float(_get_valor(pilot, "potencial", _get_valor(pilot, "potencial_base", 85.0)))
        idade = int(_get_valor(pilot, "idade", 25))

        relatorio = RelatorioEvolucao(
            pilot_id=pid,
            pilot_name=_pilot_name(pilot),
            idade=idade,
            temporada=ctx.temporada,
            skill_anterior=skill_anterior,
            potencial=potencial,
        )

        motivacao_atual = float(_get_valor(pilot, "motivacao", 50.0))
        nova_motivacao, _ajustes = atualizar_motivacao_fim_temporada(
            motivacao_atual=motivacao_atual,
            ctx=ctx,
            temporadas_na_categoria=estado.temporadas_na_categoria,
        )
        _set_valor(pilot, "motivacao", nova_motivacao)

        relatorio.motivacao_media = calcular_motivacao_media_temporada(estado.historico_motivacao)
        ctx.motivacao_media_temporada = relatorio.motivacao_media

        if nova_motivacao < 20.0:
            estado.temporadas_motivacao_baixa += 1
        else:
            estado.temporadas_motivacao_baixa = 0

        evolucoes_crescimento = processar_crescimento(pilot, ctx)
        evolucoes_declinio = processar_declinio(pilot)

        declinio_por_atributo = {d.atributo: d for d in evolucoes_declinio}
        evolucoes_finais: list[EvolucaoAtributo] = []
        atributos_processados: set[str] = set()

        for evo in evolucoes_crescimento:
            atributos_processados.add(evo.atributo)
            dec = declinio_por_atributo.get(evo.atributo)

            if dec and dec.variacao < 0:
                variacao_total = evo.variacao + dec.variacao
                valor_novo = evo.valor_anterior + variacao_total
                valor_novo = max(20.0, min(valor_novo, potencial))
                evolucoes_finais.append(
                    EvolucaoAtributo(
                        atributo=evo.atributo,
                        valor_anterior=evo.valor_anterior,
                        valor_novo=valor_novo,
                        variacao=valor_novo - evo.valor_anterior,
                        motivo=f"{evo.motivo}; {dec.motivo}",
                    )
                )
            else:
                evolucoes_finais.append(evo)

        for dec in evolucoes_declinio:
            if dec.atributo not in atributos_processados:
                evolucoes_finais.append(dec)

        for evo in evolucoes_finais:
            aliases = self._ALIASES_ATRIBUTOS.get(evo.atributo, ())
            _set_valor(pilot, evo.atributo, evo.valor_novo, aliases=aliases)

        relatorio.evolucoes = evolucoes_finais
        relatorio.skill_novo = float(_get_valor(pilot, "skill", skill_anterior))

        if estado.lesao and estado.lesao.esta_ativa:
            relatorio.lesao_ativa = True
            relatorio.lesao_tipo = estado.lesao.tipo

        lesao_tipo = LesaoTipo.NENHUMA
        if estado.lesao and estado.lesao.esta_ativa:
            lesao_tipo = estado.lesao.tipo

        aposentou, causa = verificar_aposentadoria(
            idade=int(_get_valor(pilot, "idade", idade)),
            motivacao=nova_motivacao,
            temporadas_motivacao_baixa=estado.temporadas_motivacao_baixa,
            lesao_tipo=lesao_tipo,
        )
        relatorio.aposentou = aposentou
        relatorio.causa_aposentadoria = causa

        if aposentou:
            _set_valor(pilot, "aposentado", True)
            _set_valor(pilot, "status", "aposentado")
            _set_valor(pilot, "contrato_anos", 0)
        else:
            temporadas_na_categoria = max(
                1,
                int(_get_valor(pilot, "temporadas_na_categoria", estado.temporadas_na_categoria) or 1),
            )
            _set_valor(pilot, "temporadas_na_categoria", temporadas_na_categoria + 1)

        idade_atual = int(_get_valor(pilot, "idade", idade))
        _set_valor(pilot, "idade", idade_atual + 1)
        _set_valor(pilot, "temporadas_motivacao_baixa", estado.temporadas_motivacao_baixa)
        self._limpar_dados_temporada_evolucao(pilot)

        if pid in self._estados:
            del self._estados[pid]

        return relatorio

    def processar_todos_pilotos(
        self,
        pilotos: list,
        contextos: dict,
    ) -> list[RelatorioEvolucao]:
        """
        Processa evolucao de todos os pilotos.
        """
        relatorios: list[RelatorioEvolucao] = []

        for pilot in pilotos:
            pid = _pilot_id(pilot)
            ctx = contextos.get(pid)
            if ctx is None:
                raw_id = _get_valor(pilot, "id", None)
                if raw_id is not None:
                    ctx = contextos.get(raw_id)
            if ctx is None:
                continue
            relatorios.append(self.processar_fim_temporada(pilot, ctx))

        return relatorios

    def construir_contexto_temporada(
        self,
        pilot: Any,
        banco: Optional[dict[str, Any]],
        temporada: Optional[int] = None,
    ) -> ContextoTemporada:
        categoria_id = str(_get_valor(pilot, "categoria_atual", "mazda_rookie") or "mazda_rookie")
        categoria_tier = 1

        try:
            from Dados.constantes import CATEGORIAS

            mapa_tier = {
                str(c.get("id", "")).strip(): int(c.get("nivel", 1))
                for c in CATEGORIAS
                if isinstance(c, dict)
            }
            categoria_tier = int(mapa_tier.get(categoria_id, 1))
        except Exception:
            categoria_tier = 1

        resultados = self._coletar_ints(_get_valor(pilot, "evolucao_resultados_temporada", []))
        if not resultados and isinstance(pilot, dict):
            resultados = self._coletar_ints(pilot.get("resultados_temporada", []))

        expectativas = self._coletar_ints(_get_valor(pilot, "evolucao_expectativas_temporada", []))
        if len(expectativas) < len(resultados):
            esperado_padrao = self.calcular_posicao_esperada(
                pilot,
                grid_size=max(10, len(resultados) or 10),
            )
            expectativas.extend([esperado_padrao] * (len(resultados) - len(expectativas)))

        corridas_temporada = int(_get_valor(pilot, "corridas_temporada", len(resultados)) or len(resultados))
        if corridas_temporada <= 0:
            corridas_temporada = len(resultados)

        posicao_campeonato = 0
        if isinstance(banco, dict):
            pilotos_categoria = [
                item
                for item in banco.get("pilotos", [])
                if isinstance(item, dict)
                and not bool(item.get("aposentado", False))
                and str(item.get("categoria_atual", "") or "").strip() == categoria_id
            ]
            pilotos_categoria.sort(
                key=lambda item: (
                    -int(item.get("pontos_temporada", 0) or 0),
                    -int(item.get("vitorias_temporada", 0) or 0),
                    -int(item.get("podios_temporada", 0) or 0),
                    str(item.get("nome", "")).casefold(),
                )
            )
            pid = str(_get_valor(pilot, "id", ""))
            for indice, item in enumerate(pilotos_categoria, start=1):
                if str(item.get("id", "")) == pid:
                    posicao_campeonato = indice
                    break

        if posicao_campeonato <= 0:
            posicao_campeonato = max(
                1,
                self.calcular_posicao_esperada(
                    pilot,
                    grid_size=max(10, len(resultados) or 10),
                ),
            )

        motivacoes = _get_valor(pilot, "historico_motivacao_temporada", [])
        motivacao_media = 50.0
        if isinstance(motivacoes, list) and motivacoes:
            motivacao_media = calcular_motivacao_media_temporada(
                [
                    float(valor)
                    for valor in motivacoes
                    if isinstance(valor, (int, float)) and not isinstance(valor, bool)
                ]
            )
        else:
            motivacao_media = float(_get_valor(pilot, "motivacao", 50.0) or 50.0)

        if temporada is not None:
            temporada_atual = int(temporada)
        elif isinstance(banco, dict):
            temporada_atual = int(banco.get("temporada_atual", 1) or 1)
        else:
            temporada_atual = 1
        return ContextoTemporada(
            temporada=temporada_atual,
            categoria_id=categoria_id,
            categoria_tier=categoria_tier,
            corridas_disputadas=corridas_temporada,
            vitorias=int(_get_valor(pilot, "vitorias_temporada", 0) or 0),
            podios=int(_get_valor(pilot, "podios_temporada", 0) or 0),
            poles=int(_get_valor(pilot, "poles_temporada", 0) or 0),
            dnfs=int(_get_valor(pilot, "dnfs_temporada", 0) or 0),
            posicao_campeonato=posicao_campeonato,
            resultados=resultados,
            expectativas=expectativas,
            motivacao_media_temporada=motivacao_media,
            foi_promovido=bool(_get_valor(pilot, "foi_promovido_temporada", False)),
            foi_rebaixado=bool(_get_valor(pilot, "foi_rebaixado_temporada", False)),
            renovou_contrato=bool(int(_get_valor(pilot, "contrato_anos", 0) or 0) > 0),
            time_bom=bool(_get_valor(pilot, "time_bom_temporada", False)),
            perdeu_vaga_para_jovem=bool(_get_valor(pilot, "perdeu_vaga_para_jovem_temporada", False)),
        )

    def aposentar_piloto_no_banco(self, pilot: Any, banco: Optional[dict[str, Any]] = None) -> None:
        _set_valor(pilot, "status", "aposentado")
        _set_valor(pilot, "aposentado", True)
        _set_valor(pilot, "contrato_anos", 0)

        equipe_id = _get_valor(pilot, "equipe_id", None)
        pilot_id = str(_get_valor(pilot, "id", ""))
        pilot_name = _pilot_name(pilot)

        if isinstance(banco, dict) and equipe_id not in (None, ""):
            equipe_alvo = None
            for equipe in banco.get("equipes", []):
                if not isinstance(equipe, dict):
                    continue
                if str(equipe.get("id", "")) == str(equipe_id):
                    equipe_alvo = equipe
                    break

            if isinstance(equipe_alvo, dict):
                pilotos_equipes = equipe_alvo.get("pilotos", [])
                if isinstance(pilotos_equipes, list):
                    equipe_alvo["pilotos"] = [
                        item
                        for item in pilotos_equipes
                        if str(item) != pilot_id
                    ]

                if str(equipe_alvo.get("piloto_numero_1", "")) == pilot_id:
                    equipe_alvo["piloto_numero_1"] = None
                    equipe_alvo["piloto_1"] = None
                if str(equipe_alvo.get("piloto_numero_2", "")) == pilot_id:
                    equipe_alvo["piloto_numero_2"] = None
                    equipe_alvo["piloto_2"] = None

                if str(equipe_alvo.get("piloto_1", "") or "").strip() == pilot_name:
                    equipe_alvo["piloto_1"] = None
                if str(equipe_alvo.get("piloto_2", "") or "").strip() == pilot_name:
                    equipe_alvo["piloto_2"] = None

        _set_valor(pilot, "equipe_id", None)
        _set_valor(pilot, "equipe_nome", None)
        _set_valor(pilot, "papel", None)

    def get_pilotos_aposentados(
        self,
        relatorios: list[RelatorioEvolucao],
    ) -> list[RelatorioEvolucao]:
        """Filtra relatorios de pilotos aposentados."""
        return [r for r in relatorios if r.aposentou]

    def get_resumo_evolucao(self, relatorios: list[RelatorioEvolucao]) -> dict:
        """
        Gera resumo estatistico da evolucao.
        """
        if not relatorios:
            return {}

        cresceram = sum(1 for r in relatorios if r.skill_novo > r.skill_anterior)
        declinaram = sum(1 for r in relatorios if r.skill_novo < r.skill_anterior)
        aposentaram = sum(1 for r in relatorios if r.aposentou)
        lesionados = sum(1 for r in relatorios if r.lesao_ativa)

        media_skill_antes = sum(r.skill_anterior for r in relatorios) / len(relatorios)
        media_skill_depois = sum(r.skill_novo for r in relatorios) / len(relatorios)

        return {
            "total_pilotos": len(relatorios),
            "cresceram": cresceram,
            "declinaram": declinaram,
            "estagnaram": len(relatorios) - cresceram - declinaram,
            "aposentaram": aposentaram,
            "lesionados": lesionados,
            "media_skill_antes": round(media_skill_antes, 2),
            "media_skill_depois": round(media_skill_depois, 2),
            "delta_medio_skill": round(media_skill_depois - media_skill_antes, 2),
        }
