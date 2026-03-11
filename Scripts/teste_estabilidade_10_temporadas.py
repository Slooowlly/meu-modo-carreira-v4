"""Teste de estabilidade headless para 10 temporadas completas."""

from __future__ import annotations

import os
import sys
import traceback
from dataclasses import dataclass
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from Dados.banco import criar_banco_vazio
from Dados.constantes import CATEGORIAS, CATEGORIAS_CONFIG, _EQUIPES_POR_CATEGORIA
from Logica.equipes import (
    atribuir_pilotos_equipes,
    calcular_pontos_equipes,
    criar_todas_equipes,
    evolucionar_equipes,
)
from Logica.pilotos import popular_categoria
from Logica.promocao import relatorio_to_dict
from Logica.series_especiais import inicializar_production_car_challenge
from Logica.simulacao import simular_corrida_categoria_detalhada
from UI.carreira_acoes_simular import SimularMixin
from UI.carreira_acoes_temporada import TemporadaMixin


@dataclass
class ResultadoTemporada:
    sucesso: bool
    aposentadorias: int = 0
    promocoes: int = 0
    rebaixamentos: int = 0
    transferencias: int = 0
    rookies: int = 0
    validacao_pos_mercado: bool = False
    validacao_final: bool = False


class HeadlessCarreira(SimularMixin, TemporadaMixin):
    """Harness sem UI para reutilizar os mesmos metodos da carreira."""

    def __init__(self, banco: dict[str, Any], categoria_atual: str = "mazda_rookie") -> None:
        self.banco = banco
        self.categoria_atual = categoria_atual
        self._notificacoes_hierarquia_pendentes: list[dict[str, Any]] = []

    def _obter_jogador(self) -> dict[str, Any] | None:
        return next(
            (
                p
                for p in self.banco.get("pilotos", [])
                if isinstance(p, dict) and bool(p.get("is_jogador", False))
            ),
            None,
        )

    def _atualizar_tudo(self, animar: bool = False) -> None:
        _ = animar

    def _mostrar_aba_mercado(self) -> None:
        return

    def _exibir_resumo_temporada(self, *args, **kwargs) -> None:
        _ = args
        _ = kwargs


def _capacidade_categoria(categoria_id: str) -> int:
    equipes = _EQUIPES_POR_CATEGORIA.get(categoria_id, [])
    if equipes:
        return max(2, len(equipes) * 2)
    cfg = CATEGORIAS_CONFIG.get(categoria_id, {})
    return max(2, int(cfg.get("tamanho_grid", 20) or 20))


def criar_banco_novo() -> dict[str, Any]:
    banco = criar_banco_vazio()
    banco["ano_atual"] = 2024
    banco["temporada_atual"] = 1
    banco["rodada_atual"] = 1
    banco["temporada_concluida"] = False
    banco["pilotos"] = []
    banco["equipes"] = []
    banco["max_drivers_por_categoria"] = {}

    for categoria in CATEGORIAS:
        categoria_id = str(categoria.get("id", "")).strip()
        if not categoria_id:
            continue
        capacidade = _capacidade_categoria(categoria_id)
        banco["max_drivers_por_categoria"][categoria_id] = capacidade
        popular_categoria(
            banco,
            categoria_id,
            capacidade,
            banco.get("ano_atual", 2024),
        )

    criar_todas_equipes(banco, banco.get("ano_atual", 2024))
    for categoria in CATEGORIAS:
        categoria_id = str(categoria.get("id", "")).strip()
        if not categoria_id:
            continue
        atribuir_pilotos_equipes(banco, categoria_id)

    inicializar_production_car_challenge(banco, banco.get("ano_atual", 2024))
    return banco


def simular_temporada_completa(engine: HeadlessCarreira, temporada_num: int) -> ResultadoTemporada:
    print(f"\n{'=' * 60}")
    print(
        f"TEMPORADA {temporada_num} "
        f"(Ano {int(engine.banco.get('ano_atual', 2024) or 2024)})"
    )
    print(f"{'=' * 60}")

    for categoria in CATEGORIAS:
        categoria_id = str(categoria.get("id", "")).strip()
        if not categoria_id:
            continue

        engine.categoria_atual = categoria_id
        cfg = CATEGORIAS_CONFIG.get(categoria_id, {})
        total_corridas = int(cfg.get("num_corridas", 8) or 8)

        for rodada in range(1, total_corridas + 1):
            engine.banco["rodada_atual"] = rodada
            try:
                payload = simular_corrida_categoria_detalhada(engine.banco, categoria_id)
                classificacao = payload.get("classificacao", []) if isinstance(payload, dict) else []
                if not isinstance(classificacao, list) or not classificacao:
                    print(f"  [ERRO] {categoria_id} rodada {rodada}: classificacao vazia")
                    return ResultadoTemporada(sucesso=False)

                aplicados = engine._aplicar_classificacao_categoria(
                    categoria_id=categoria_id,
                    classificacao=classificacao,
                    rodada=rodada,
                )
                if int(aplicados or 0) <= 0:
                    print(f"  [ERRO] {categoria_id} rodada {rodada}: nenhum resultado aplicado")
                    return ResultadoTemporada(sucesso=False)

                calcular_pontos_equipes(engine.banco, categoria_id)
            except Exception as erro:
                print(f"  [ERRO] {categoria_id} rodada {rodada}: {erro}")
                traceback.print_exc()
                return ResultadoTemporada(sucesso=False)

        print(f"  [OK] {categoria_id}: {total_corridas} corridas")

    print("  [OK] Corridas simuladas")

    try:
        ano = int(engine.banco.get("ano_atual", 2024) or 2024)
        fechamento = engine._estado_fechamento_temporada()
        fechamento["em_andamento"] = True
        fechamento["ano_base"] = ano
        fechamento["simulacao_ai_concluida"] = True

        aposentados, _relatorios_evolucao = engine._processar_evolucao_fim_temporada(ano)
        fechamento["aposentados"] = list(aposentados)
        fechamento["total_aposentadorias"] = len(aposentados)
        print(f"  [OK] M6 Evolucao | Aposentadorias: {len(aposentados)}")

        engine._sincronizar_rosters()

        relatorio_promocao = engine._processar_promocao_fim_temporada(ano)
        relatorio_promocao_dict = relatorio_to_dict(relatorio_promocao)
        promocoes = len(relatorio_promocao_dict.get("promocoes", []))
        rebaixamentos = len(relatorio_promocao_dict.get("rebaixamentos", []))
        print(f"  [OK] M8 Promocao | Subidas: {promocoes} | Descidas: {rebaixamentos}")

        engine._sincronizar_rosters()

        resultado_mercado = engine._processar_mercado_fim_temporada(
            aposentadorias_temporada=len(aposentados)
        )
        if resultado_mercado is None:
            print("  [ERRO] Mercado: pendencia de jogador em modo headless")
            return ResultadoTemporada(sucesso=False)

        mercado_dict = resultado_mercado.to_dict() if hasattr(resultado_mercado, "to_dict") else {}
        transferencias = len(mercado_dict.get("contratos_novos", []))
        rookies = len(mercado_dict.get("rookies_gerados", []))
        print(f"  [OK] M7 Mercado | Transferencias: {transferencias} | Rookies: {rookies}")

        engine._sincronizar_rosters()
        saneamento = engine._sanear_integridade_banco()
        print(f"  [OK] Saneamento | Alterado: {bool(saneamento.get('alterado', False))}")
        validacao_pos_mercado = engine._validar_ecossistema_pos_mercado()
        validacao_pos_ok = bool(validacao_pos_mercado.get("valido", False))
        print(f"  [OK] Pos-mercado | Valido: {validacao_pos_ok}")

        evolucionar_equipes(engine.banco)
        engine._resetar_stats_temporada()

        engine.banco["ano_atual"] = ano + 1
        engine.banco["temporada_atual"] = int(engine.banco.get("temporada_atual", 1) or 1) + 1
        engine.banco["rodada_atual"] = 1
        engine.banco["temporada_concluida"] = False
        inicializar_production_car_challenge(engine.banco, engine.banco["ano_atual"])

        engine._sincronizar_rosters()
        saneamento_final = engine._sanear_integridade_banco()
        print(f"  [OK] Saneamento final | Alterado: {bool(saneamento_final.get('alterado', False))}")
        engine._inicializar_hierarquias(engine.banco)
        validacao_final_ok = engine._validar_ecossistema_final(engine.banco)
        print("  [OK] M9 Hierarquias definidas")

        engine._limpar_estado_fechamento_temporada()
        return ResultadoTemporada(
            sucesso=True,
            aposentadorias=len(aposentados),
            promocoes=promocoes,
            rebaixamentos=rebaixamentos,
            transferencias=transferencias,
            rookies=rookies,
            validacao_pos_mercado=validacao_pos_ok,
            validacao_final=bool(validacao_final_ok),
        )
    except Exception as erro:
        print(f"  [ERRO] Fim de temporada: {erro}")
        traceback.print_exc()
        return ResultadoTemporada(sucesso=False)


def validar_ecossistema(banco: dict[str, Any], temporada_num: int) -> bool:
    erros: list[str] = []

    contagens_esperadas = {
        "mazda_rookie": 6,
        "toyota_rookie": 6,
        "mazda_amador": 10,
        "toyota_amador": 10,
        "bmw_m2": 10,
        "production_challenger": 15,
        "gt4": 10,
        "gt3": 14,
        "endurance": 21,
    }
    for categoria_id, esperado in contagens_esperadas.items():
        equipes = [
            e
            for e in banco.get("equipes", [])
            if isinstance(e, dict)
            and bool(e.get("ativa", True))
            and str(e.get("categoria", "")) == categoria_id
        ]
        if len(equipes) != esperado:
            erros.append(f"  {categoria_id}: {len(equipes)} equipes (esperado {esperado})")

    equipes_problema: dict[int, int] = {}
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        if not bool(equipe.get("ativa", True)):
            continue
        qtd = len(equipe.get("pilotos", [])) if isinstance(equipe.get("pilotos"), list) else 0
        equipes_problema[qtd] = equipes_problema.get(qtd, 0) + 1
    if equipes_problema.get(0, 0) > 0 or equipes_problema.get(1, 0) > 0:
        erros.append(f"  Distribuicao pilotos/equipe: {equipes_problema}")

    ativos = [
        p
        for p in banco.get("pilotos", [])
        if isinstance(p, dict)
        and str(p.get("status", "")).strip().lower() == "ativo"
        and not bool(p.get("aposentado", False))
    ]
    if not (195 <= len(ativos) <= 215):
        erros.append(f"  Pilotos ativos: {len(ativos)} (esperado ~204)")

    atributos_check = [
        "skill",
        "consistencia",
        "racecraft",
        "ritmo_classificacao",
        "gestao_pneus",
        "habilidade_largada",
        "resistencia_mental",
        "fitness",
        "fator_chuva",
        "fator_clutch",
    ]
    violacoes = 0
    for piloto in ativos:
        potencial = int(piloto.get("potencial", 100) or 100)
        for atributo in atributos_check:
            if int(piloto.get(atributo, 0) or 0) > potencial:
                violacoes += 1
    if violacoes > 0:
        erros.append(f"  Violacoes skill>potencial: {violacoes}")

    fora_range = 0
    for piloto in ativos:
        for atributo in atributos_check:
            valor = int(piloto.get(atributo, 50) or 50)
            if valor < 20 or valor > 100:
                fora_range += 1
    if fora_range > 0:
        erros.append(f"  Atributos fora de range (20-100): {fora_range}")

    pilotos_por_id = {
        str(p.get("id")): p
        for p in banco.get("pilotos", [])
        if isinstance(p, dict)
    }
    ghosts = 0
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict) or not bool(equipe.get("ativa", True)):
            continue
        for pid in equipe.get("pilotos", []):
            piloto = pilotos_por_id.get(str(pid))
            if (
                not isinstance(piloto, dict)
                or str(piloto.get("status", "")).strip().lower() != "ativo"
                or bool(piloto.get("aposentado", False))
            ):
                ghosts += 1
    if ghosts > 0:
        erros.append(f"  Ghost IDs em equipes: {ghosts}")

    sem_equipe = [p for p in ativos if p.get("equipe_id") in (None, "")]
    if sem_equipe:
        erros.append(f"  Pilotos ativos sem equipe: {len(sem_equipe)}")

    sem_hierarquia = 0
    for equipe in banco.get("equipes", []):
        if not isinstance(equipe, dict):
            continue
        if not bool(equipe.get("ativa", True)):
            continue
        if len(equipe.get("pilotos", [])) == 2 and not isinstance(equipe.get("hierarquia"), dict):
            sem_hierarquia += 1
    if sem_hierarquia > 0:
        erros.append(f"  Equipes sem hierarquia: {sem_hierarquia}")

    if erros:
        print(f"\n  [ERRO] VALIDACAO TEMPORADA {temporada_num}: {len(erros)} PROBLEMAS")
        for erro in erros:
            print(erro)
        return False

    print(f"\n  [OK] VALIDACAO TEMPORADA {temporada_num}: TUDO OK")
    print(f"     Ativos: {len(ativos)} | Equipes: {equipes_problema}")
    return True


def main() -> int:
    print("============================================================")
    print("TESTE DE ESTABILIDADE - 10 TEMPORADAS")
    print("============================================================")

    banco = criar_banco_novo()
    engine = HeadlessCarreira(banco=banco, categoria_atual="mazda_rookie")
    engine._sincronizar_rosters()
    engine._inicializar_hierarquias(banco)

    stats_gerais: dict[str, Any] = {
        "temporadas": 0,
        "total_aposentadorias": 0,
        "total_rookies": 0,
        "total_transferencias": 0,
        "erros": 0,
        "skill_medio_por_temporada": [],
        "pilotos_ativos_por_temporada": [],
    }

    for temporada in range(1, 11):
        resultado = simular_temporada_completa(engine, temporada)
        if not resultado.sucesso:
            print(f"\n[FALHA CRITICA] Temporada {temporada}. Abortando.")
            stats_gerais["erros"] += 1
            break

        valido = validar_ecossistema(engine.banco, temporada)
        if not valido:
            stats_gerais["erros"] += 1

        stats_gerais["temporadas"] = temporada
        stats_gerais["total_aposentadorias"] += int(resultado.aposentadorias)
        stats_gerais["total_rookies"] += int(resultado.rookies)
        stats_gerais["total_transferencias"] += int(resultado.transferencias)

        ativos = [
            p
            for p in engine.banco.get("pilotos", [])
            if isinstance(p, dict)
            and str(p.get("status", "")).strip().lower() == "ativo"
            and not bool(p.get("aposentado", False))
        ]
        skill_medio = (
            sum(float(p.get("skill", 50) or 50) for p in ativos) / len(ativos)
            if ativos
            else 0.0
        )
        stats_gerais["skill_medio_por_temporada"].append(round(skill_medio, 1))
        stats_gerais["pilotos_ativos_por_temporada"].append(len(ativos))

    print("\n" + "=" * 60)
    print("RELATORIO FINAL")
    print("=" * 60)
    print(f"Temporadas completadas: {stats_gerais['temporadas']}/10")
    print(f"Erros de validacao: {stats_gerais['erros']}")
    print(f"Aposentadorias (total): {stats_gerais['total_aposentadorias']}")
    print(f"Rookies gerados (total): {stats_gerais['total_rookies']}")
    print(f"Transferencias (total): {stats_gerais['total_transferencias']}")
    print(f"Skill medio por temporada: {stats_gerais['skill_medio_por_temporada']}")
    print(f"Pilotos ativos por temporada: {stats_gerais['pilotos_ativos_por_temporada']}")

    aprovado = stats_gerais["erros"] == 0 and stats_gerais["temporadas"] == 10
    if aprovado:
        print("\nTESTE DE ESTABILIDADE: APROVADO")
        return 0

    print("\nTESTE DE ESTABILIDADE: REPROVADO")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
