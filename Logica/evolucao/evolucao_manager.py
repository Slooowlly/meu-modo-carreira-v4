"""
Orquestrador principal do sistema de evolucao.
Coordena os subsistemas e aplica evolucao aos pilotos.
"""

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
    ) -> dict:
        """
        Processa resultado de uma corrida.
        """
        pid = _pilot_id(pilot)
        estado = self._get_estado(pid)
        resultado: dict[str, Any] = {}

        estado.resultados.append(int(posicao))
        estado.expectativas.append(int(expectativa))

        if posicao == 1:
            estado.vitorias += 1
        if posicao <= 3:
            estado.podios += 1
        if foi_pole:
            estado.poles += 1
        if foi_dnf:
            estado.dnfs += 1

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

        if estado.lesao is None:
            estado.lesao = _extrair_lesao_do_piloto(pilot)

        ctx.resultados = list(estado.resultados)
        ctx.expectativas = list(estado.expectativas)
        ctx.vitorias = estado.vitorias
        ctx.podios = estado.podios
        ctx.poles = estado.poles
        ctx.dnfs = estado.dnfs
        ctx.corridas_disputadas = len(estado.resultados)

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

        relatorio.motivacao_media = calcular_motivacao_media_temporada(
            estado.historico_motivacao
        )

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

        idade_atual = int(_get_valor(pilot, "idade", idade))
        _set_valor(pilot, "idade", idade_atual + 1)

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

