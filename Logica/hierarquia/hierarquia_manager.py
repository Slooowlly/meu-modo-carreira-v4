"""
Orquestrador principal do sistema de hierarquia numero 1/2.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .avaliacao import (
    avaliar_desempenho_temporada,
    definir_hierarquia_inicial,
)
from .impactos import (
    ImpactoHierarquia,
    aplicar_modificador_visibilidade,
    calcular_impactos,
)
from .models import (
    ComparacaoResultado,
    EstadoHierarquia,
    HistoricoHierarquia,
    MotivoHierarquia,
    OrdemEquipe,
    Papel,
    RelatorioHierarquiaTemporada,
    RespostaOrdem,
    StatusTensao,
)
from .ordens_equipe import simular_ordens_corrida as simular_ordens_corrida_engine
from .reavaliacao import (
    aplicar_impacto_inversao,
    deve_inverter_hierarquia,
    deve_reavaliar_hierarquia,
    executar_inversao,
)
from .tensao import atualizar_tensao_pos_corrida, tensao_afeta_moral_equipe


class HierarquiaManager:
    """
    Gerenciador principal de hierarquia de pilotos.
    """

    def __init__(self):
        self._estados: Dict[str, EstadoHierarquia] = {}
        self._pilotos: Dict[str, Any] = {}
        self._equipes: Dict[str, Any] = {}
        self._ordens_temporada: List[OrdemEquipe] = []

    @staticmethod
    def _get(entidade: Any, campo: str, default=None):
        if isinstance(entidade, dict):
            return entidade.get(campo, default)
        return getattr(entidade, campo, default)

    @staticmethod
    def _get_any(entidade: Any, campos: tuple[str, ...], default=None):
        for campo in campos:
            valor = HierarquiaManager._get(entidade, campo, None)
            if valor is not None:
                return valor
        return default

    @staticmethod
    def _set(entidade: Any, campo: str, valor):
        if isinstance(entidade, dict):
            entidade[campo] = valor
        else:
            setattr(entidade, campo, valor)

    @staticmethod
    def _extrair_id(entidade: Any) -> str:
        valor = HierarquiaManager._get(entidade, "id", None)
        if valor is not None:
            return str(valor)
        return str(id(entidade))

    def _atualizar_equipe_com_hierarquia(self, equipe_id: str, estado: EstadoHierarquia):
        equipe = self._equipes.get(equipe_id)
        if not equipe:
            return

        self._set(equipe, "piloto_numero_1", estado.piloto_1_id)
        self._set(equipe, "piloto_numero_2", estado.piloto_2_id)
        self._set(equipe, "piloto_1", estado.piloto_1_nome)
        self._set(equipe, "piloto_2", estado.piloto_2_nome)

    def _atualizar_papel_pilotos(self, estado: EstadoHierarquia):
        piloto_n1 = self._pilotos.get(str(estado.piloto_1_id))
        piloto_n2 = self._pilotos.get(str(estado.piloto_2_id))
        if piloto_n1 is not None:
            self._set(piloto_n1, "papel", "numero_1")
        if piloto_n2 is not None:
            self._set(piloto_n2, "papel", "numero_2")

    def definir_hierarquia_equipe(
        self,
        equipe: Any,
        piloto_1: Any,
        piloto_2: Any,
        temporada: int,
        contrato_1: Optional[Any] = None,
        contrato_2: Optional[Any] = None,
    ) -> EstadoHierarquia:
        """
        Define hierarquia inicial de uma equipe para a temporada.
        """
        equipe_id = self._extrair_id(equipe)
        equipe_nome = str(self._get(equipe, "nome", "Unknown"))

        p1_id, p2_id, motivo = definir_hierarquia_inicial(piloto_1, piloto_2, contrato_1, contrato_2)
        piloto_1_id_real = self._extrair_id(piloto_1)

        if piloto_1_id_real == p1_id:
            numero_1, numero_2 = piloto_1, piloto_2
        else:
            numero_1, numero_2 = piloto_2, piloto_1

        historico = HistoricoHierarquia(
            equipe_id=equipe_id,
            temporada=int(temporada),
            piloto_numero_1_id=str(p1_id),
            piloto_numero_2_id=str(p2_id),
        )

        estado = EstadoHierarquia(
            equipe_id=equipe_id,
            equipe_nome=equipe_nome,
            temporada=int(temporada),
            piloto_1_id=str(p1_id),
            piloto_1_nome=str(self._get_any(numero_1, ("nome", "name"), "P1")),
            piloto_2_id=str(p2_id),
            piloto_2_nome=str(self._get_any(numero_2, ("nome", "name"), "P2")),
            motivo=motivo if isinstance(motivo, MotivoHierarquia) else MotivoHierarquia.SKILL,
            status_tensao=StatusTensao.ESTAVEL,
            nivel_tensao=0.0,
            historico=historico,
            hierarquia_definida=True,
        )

        self._estados[equipe_id] = estado
        self._equipes[equipe_id] = equipe
        self._pilotos[str(p1_id)] = numero_1
        self._pilotos[str(p2_id)] = numero_2

        self._atualizar_equipe_com_hierarquia(equipe_id, estado)
        self._atualizar_papel_pilotos(estado)
        return estado

    def processar_resultado_corrida(
        self,
        equipe_id: str,
        posicao_p1: int,
        posicao_p2: int,
        corrida_numero: int,
        foi_corrida_jogador: bool = False,
    ) -> Dict[str, Any]:
        """
        Processa resultado de corrida para atualizar hierarquia.
        """
        del foi_corrida_jogador

        estado = self._estados.get(str(equipe_id))
        if not estado or not estado.historico:
            return {"erro": "Equipe nao encontrada"}

        comparacao = ComparacaoResultado(
            corrida_numero=int(corrida_numero),
            piloto_1_id=str(estado.piloto_1_id),
            piloto_2_id=str(estado.piloto_2_id),
            posicao_piloto_1=int(posicao_p1),
            posicao_piloto_2=int(posicao_p2),
        )
        estado.historico.adicionar_resultado(comparacao)

        p1_venceu = comparacao.piloto_1_venceu_duelo
        novo_nivel = atualizar_tensao_pos_corrida(estado=estado, p1_venceu_duelo=p1_venceu)

        resultado: Dict[str, Any] = {
            "corrida": int(corrida_numero),
            "p1_venceu_duelo": bool(p1_venceu),
            "nivel_tensao": float(novo_nivel),
            "status_tensao": estado.status_tensao.value,
            "sequencia_p2": int(estado.historico.sequencia_atual_p2),
        }
        if estado.historico.sequencia_atual_p2 >= 3:
            resultado["aviso"] = f"N2 a frente por {estado.historico.sequencia_atual_p2} corridas"
        return resultado

    def verificar_reavaliacao(self, equipe_id: str, corrida_atual: int, total_corridas: int) -> Tuple[bool, str]:
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return False, "Equipe nao encontrada"
        return deve_reavaliar_hierarquia(estado, corrida_atual, total_corridas)

    def verificar_inversao(self, equipe_id: str, corrida_atual: int, total_corridas: int) -> Tuple[bool, str]:
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return False, "Equipe nao encontrada"
        return deve_inverter_hierarquia(estado, corrida_atual, total_corridas)

    def executar_inversao_hierarquia(self, equipe_id: str, corrida_numero: int) -> Optional[EstadoHierarquia]:
        """
        Executa inversao de hierarquia e aplica impactos.
        """
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return None

        antigo_n1_id = str(estado.piloto_1_id)
        antigo_n2_id = str(estado.piloto_2_id)

        piloto_rebaixado = self._pilotos.get(antigo_n1_id)
        piloto_promovido = self._pilotos.get(antigo_n2_id)

        if piloto_rebaixado is not None:
            aplicar_impacto_inversao(piloto_rebaixado, foi_promovido=False)
        if piloto_promovido is not None:
            aplicar_impacto_inversao(piloto_promovido, foi_promovido=True)

        estado = executar_inversao(estado, int(corrida_numero))

        # Mantem caches sincronizados apos inversao.
        if piloto_promovido is not None:
            self._pilotos[str(estado.piloto_1_id)] = piloto_promovido
        if piloto_rebaixado is not None:
            self._pilotos[str(estado.piloto_2_id)] = piloto_rebaixado

        self._atualizar_equipe_com_hierarquia(str(equipe_id), estado)
        self._atualizar_papel_pilotos(estado)
        return estado

    def get_estado_equipe(self, equipe_id: str) -> Optional[EstadoHierarquia]:
        return self._estados.get(str(equipe_id))

    def get_papel_piloto(self, equipe_id: str, piloto_id: str) -> Papel:
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return Papel.INDEFINIDO
        if str(piloto_id) == str(estado.piloto_1_id):
            return Papel.NUMERO_1
        if str(piloto_id) == str(estado.piloto_2_id):
            return Papel.NUMERO_2
        return Papel.INDEFINIDO

    def get_impactos_piloto(self, equipe_id: str, piloto_id: str) -> ImpactoHierarquia:
        papel = self.get_papel_piloto(equipe_id, piloto_id)
        return calcular_impactos(papel)

    def aplicar_modificador_visibilidade_piloto(self, equipe_id: str, piloto_id: str, visibilidade_base: float) -> float:
        papel = self.get_papel_piloto(equipe_id, piloto_id)
        return aplicar_modificador_visibilidade(visibilidade_base, papel)

    def simular_ordens_corrida(
        self,
        equipe_id: str,
        resultado_p1: int,
        resultado_p2: int,
        corrida_numero: int,
        diferenca_campeonato: int,
    ) -> Tuple[List[OrdemEquipe], int, int]:
        """
        Simula ordens de equipe em corrida simulada.
        """
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return [], resultado_p1, resultado_p2

        piloto_2 = self._pilotos.get(str(estado.piloto_2_id))
        if not piloto_2:
            return [], resultado_p1, resultado_p2

        ordens, r1, r2 = simular_ordens_corrida_engine(
            estado=estado,
            resultado_p1=int(resultado_p1),
            resultado_p2=int(resultado_p2),
            piloto_2=piloto_2,
            corrida_numero=int(corrida_numero),
            diferenca_campeonato=int(diferenca_campeonato),
        )
        self._ordens_temporada.extend(ordens)

        for ordem in ordens:
            obedeceu = ordem.resposta != RespostaOrdem.IGNOROU if ordem.resposta else True
            atualizar_tensao_pos_corrida(
                estado=estado,
                p1_venceu_duelo=(r1 < r2),
                ordem_emitida=True,
                ordem_obedecida=obedeceu,
            )

        return ordens, r1, r2

    def get_moral_equipe_modificada(self, equipe_id: str) -> float:
        estado = self._estados.get(str(equipe_id))
        if not estado:
            return 1.0
        return tensao_afeta_moral_equipe(estado)

    def gerar_relatorio_temporada(self, temporada: int) -> RelatorioHierarquiaTemporada:
        """
        Gera relatorio completo da temporada.
        """
        relatorio = RelatorioHierarquiaTemporada(temporada=int(temporada))

        for equipe_id, estado in self._estados.items():
            if int(estado.temporada) != int(temporada):
                continue

            relatorio.estados[equipe_id] = estado
            if estado.inversao_ocorreu:
                corrida_inv = int(estado.historico.corrida_inversao) if estado.historico and estado.historico.corrida_inversao else 0
                relatorio.inversoes.append((equipe_id, corrida_inv))
            if estado.status_tensao == StatusTensao.CRISE:
                relatorio.crises.append(equipe_id)

        ordens_temp = list(self._ordens_temporada)
        relatorio.total_ordens = len(ordens_temp)
        relatorio.ordens_obedecidas = sum(1 for ordem in ordens_temp if ordem.resposta == RespostaOrdem.OBEDECEU)
        relatorio.ordens_ignoradas = sum(1 for ordem in ordens_temp if ordem.resposta == RespostaOrdem.IGNOROU)

        for estado in relatorio.estados.values():
            if estado.inversao_ocorreu:
                relatorio.adicionar_destaque(
                    f"{estado.equipe_nome}: {estado.piloto_1_nome} promovido a N1 apos superar {estado.piloto_2_nome}"
                )
            if estado.status_tensao == StatusTensao.CRISE:
                relatorio.adicionar_destaque(f"{estado.equipe_nome}: Crise interna entre pilotos")
            if estado.historico and estado.historico.percentual_p2 >= 70.0:
                relatorio.adicionar_destaque(
                    f"{estado.equipe_nome}: {estado.piloto_2_nome} dominou duelos internos ({estado.historico.percentual_p2:.0f}%)"
                )

        return relatorio

    def limpar_temporada(self):
        """
        Limpa dados da temporada para a proxima.
        """
        self._estados.clear()
        self._ordens_temporada.clear()
        self._equipes.clear()
        # Mantem cache de pilotos.

    def processar_fim_temporada(self, equipes: List[Any], temporada: int) -> RelatorioHierarquiaTemporada:
        """
        Processa fim de temporada para todas as equipes.
        """
        relatorio = self.gerar_relatorio_temporada(temporada)

        for equipe in equipes:
            equipe_id = self._extrair_id(equipe)
            estado = self._estados.get(equipe_id)
            if not estado or not estado.historico:
                continue

            avaliacao = avaliar_desempenho_temporada(estado.historico)
            if float(avaliacao.get("p2_percentual", 0.0)) < 35.0:
                relatorio.adicionar_destaque(
                    f"{estado.equipe_nome}: {estado.piloto_2_nome} em risco de substituicao (apenas {avaliacao['p2_percentual']:.0f}% dos duelos)"
                )

        return relatorio


def criar_manager_para_temporada(
    equipes: List[Any],
    pilotos_por_equipe: Dict[str, Tuple[Any, Any]],
    contratos: Dict[str, Any],
    temporada: int,
) -> HierarquiaManager:
    """
    Cria e configura manager para uma temporada.
    """
    manager = HierarquiaManager()

    for equipe in equipes:
        equipe_id = manager._extrair_id(equipe)
        pilotos = pilotos_por_equipe.get(equipe_id)
        if not pilotos or len(pilotos) < 2:
            continue

        piloto_1, piloto_2 = pilotos
        p1_id = manager._extrair_id(piloto_1)
        p2_id = manager._extrair_id(piloto_2)

        contrato_1 = contratos.get(p1_id)
        contrato_2 = contratos.get(p2_id)

        manager.definir_hierarquia_equipe(
            equipe=equipe,
            piloto_1=piloto_1,
            piloto_2=piloto_2,
            temporada=int(temporada),
            contrato_1=contrato_1,
            contrato_2=contrato_2,
        )

    return manager


def processar_corrida_todas_equipes(
    manager: HierarquiaManager,
    resultados: Dict[str, Dict[str, int]],
    corrida_numero: int,
    total_corridas: int,
) -> Dict[str, Dict[str, Any]]:
    """
    Processa resultado de corrida para todas as equipes.
    """
    atualizacoes: Dict[str, Dict[str, Any]] = {}

    for equipe_id, resultado in resultados.items():
        pos_p1 = int(resultado.get("p1", 99))
        pos_p2 = int(resultado.get("p2", 99))

        att = manager.processar_resultado_corrida(
            equipe_id=equipe_id,
            posicao_p1=pos_p1,
            posicao_p2=pos_p2,
            corrida_numero=int(corrida_numero),
        )

        deve, motivo = manager.verificar_inversao(
            equipe_id=str(equipe_id),
            corrida_atual=int(corrida_numero),
            total_corridas=int(total_corridas),
        )
        if deve:
            manager.executar_inversao_hierarquia(str(equipe_id), int(corrida_numero))
            att["inversao"] = True
            att["motivo_inversao"] = motivo

        atualizacoes[str(equipe_id)] = att

    return atualizacoes


def integrar_com_mercado(
    manager: HierarquiaManager,
    equipe_id: str,
    piloto_id: str,
    visibilidade_base: float,
) -> float:
    """
    Integra hierarquia com sistema de mercado (modulo 7).
    """
    return manager.aplicar_modificador_visibilidade_piloto(equipe_id, piloto_id, visibilidade_base)


def integrar_com_simulacao(
    manager: HierarquiaManager,
    equipe_id: str,
    resultado_simulado_p1: int,
    resultado_simulado_p2: int,
    corrida_numero: int,
    diferenca_campeonato: int,
) -> Tuple[int, int, List[OrdemEquipe]]:
    """
    Integra hierarquia com sistema de simulacao (modulo 4).
    """
    ordens, r1, r2 = manager.simular_ordens_corrida(
        equipe_id=equipe_id,
        resultado_p1=resultado_simulado_p1,
        resultado_p2=resultado_simulado_p2,
        corrida_numero=corrida_numero,
        diferenca_campeonato=diferenca_campeonato,
    )
    return r1, r2, ordens
