"""
Orquestrador principal de simulação de corridas.
"""

import random
from typing import Any, Optional
from dataclasses import dataclass

from Dados.constantes import CATEGORIAS_CONFIG, PONTUACAO_ENDURANCE, PONTUACAO_PADRAO

from .models import (
    RaceResult,
    SimulationContext,
    WeatherCondition,
    RaceDriverResult,
    calculate_points,
)
from .qualifying import simulate_qualifying
from .race import simulate_race
from .weather import determine_weather
from .safety_car import should_deploy_safety_car, create_safety_car_period


def _get(obj: Any, key: str, default=None):
    """Le atributo de dict/objeto sem perder compatibilidade legada."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_float(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _norm_id(value: Any) -> str:
    if value in (None, "") or isinstance(value, bool):
        return ""
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return str(value).strip()


def _normalize_points_system(raw_points: Any) -> dict[int, int]:
    """Normaliza sistema de pontos para dict[int, int]."""
    if isinstance(raw_points, dict):
        points: dict[int, int] = {}
        for key, value in raw_points.items():
            try:
                points[int(key)] = int(value)
            except (TypeError, ValueError):
                continue
        if points:
            return points

    if isinstance(raw_points, list):
        points = {}
        for index, value in enumerate(raw_points, start=1):
            try:
                points[index] = int(value)
            except (TypeError, ValueError):
                continue
        if points:
            return points

    return dict(PONTUACAO_PADRAO)


def _resolve_scoring_rules(category_id: str, explicit_points_system: Any = None) -> dict[str, Any]:
    """Resolve tabela e regras de pontuacao da categoria (M3)."""
    categoria_cfg = CATEGORIAS_CONFIG.get(str(category_id or "").strip(), {})
    sistema = str(categoria_cfg.get("sistema_pontuacao", "padrao")).strip().lower()

    if explicit_points_system is not None:
        pontos = _normalize_points_system(explicit_points_system)
    elif sistema == "endurance":
        pontos = dict(PONTUACAO_ENDURANCE)
    else:
        pontos = dict(PONTUACAO_PADRAO)

    return {
        "points_system": pontos,
        "bonus_pole": bool(categoria_cfg.get("bonus_pole", True)),
        "bonus_fastest_lap": bool(categoria_cfg.get("bonus_volta_rapida", True)),
        "points_by_class": bool(
            categoria_cfg.get("multiclasse", False)
            and categoria_cfg.get("pontuacao_por_classe", False)
        ),
    }


def _assign_class_positions(race_results: list[RaceDriverResult]) -> dict[str, list[RaceDriverResult]]:
    """
    Calcula posicoes por classe sem alterar o ranking geral.
    """
    grouped: dict[str, list[RaceDriverResult]] = {}
    for result in sorted(race_results, key=lambda item: item.finish_position):
        class_id = str(result.class_id or "").strip().lower()
        if not class_id:
            result.class_position = result.finish_position
            continue
        grouped.setdefault(class_id, []).append(result)

    for class_results in grouped.values():
        class_results.sort(key=lambda item: item.finish_position)
        for pos, result in enumerate(class_results, start=1):
            result.class_position = pos

    return grouped


@dataclass
class SimulationConfig:
    """Configuração de uma simulação"""
    category_id: str
    category_name: str
    category_tier: int
    track_id: int
    track_name: str
    total_laps: int
    race_duration_minutes: int
    base_lap_time_ms: float = 90000
    force_weather: Optional[WeatherCondition] = None
    is_championship_deciding: bool = False
    enable_safety_car: bool = True
    points_system: Optional[dict] = None


class RaceSimulator:
    """
    Simulador principal de corridas.

    Uso básico::

        simulator = RaceSimulator()
        result = simulator.simulate_full_event(config, pilots, teams)
    """

    def __init__(self):
        self.last_result: Optional[RaceResult] = None

    def _aplicar_ordens_equipe_simuladas(
        self,
        race_results: list[RaceDriverResult],
        teams: dict[Any, Any],
    ) -> int:
        """
        M9: aplica ordens de equipe apenas em corridas simuladas.

        Regra:
        - Se N2 estiver a frente do N1 no fim e diferenca <= 2
        - 40% chance de ordem
        - 30% de desobediencia
        - obedecer: troca posicoes e morale +0.02
        - desobedecer: morale -0.05
        """
        if not race_results or not teams:
            return 0

        equipes_por_id: dict[str, dict[str, Any]] = {}
        for equipe in teams.values():
            if not isinstance(equipe, dict):
                continue
            eid = _norm_id(equipe.get("id"))
            if not eid:
                continue
            equipes_por_id[eid] = equipe

        if not equipes_por_id:
            return 0

        resultados_por_equipe: dict[str, list[RaceDriverResult]] = {}
        for resultado in race_results:
            equipe_id = _norm_id(resultado.team_id)
            if not equipe_id:
                continue
            resultados_por_equipe.setdefault(equipe_id, []).append(resultado)

        ordens_aplicadas = 0
        for equipe_id, resultados in resultados_por_equipe.items():
            if len(resultados) != 2:
                continue
            equipe = equipes_por_id.get(equipe_id)
            if not isinstance(equipe, dict):
                continue

            hierarquia = equipe.get("hierarquia")
            if not isinstance(hierarquia, dict):
                continue

            n1_id = _norm_id(hierarquia.get("n1_id", equipe.get("piloto_numero_1")))
            n2_id = _norm_id(hierarquia.get("n2_id", equipe.get("piloto_numero_2")))
            if not n1_id or not n2_id or n1_id == n2_id:
                continue

            res_n1 = next((r for r in resultados if _norm_id(r.pilot_id) == n1_id), None)
            res_n2 = next((r for r in resultados if _norm_id(r.pilot_id) == n2_id), None)
            if res_n1 is None or res_n2 is None:
                continue
            if res_n1.is_dnf or res_n2.is_dnf:
                continue
            if int(res_n2.finish_position) >= int(res_n1.finish_position):
                continue

            diferenca = int(res_n1.finish_position) - int(res_n2.finish_position)
            if diferenca > 2:
                continue
            if random.random() >= 0.40:
                continue

            obedeceu = random.random() >= 0.30
            if obedeceu:
                pos_n1 = int(res_n1.finish_position)
                pos_n2 = int(res_n2.finish_position)
                res_n1.finish_position = pos_n2
                res_n2.finish_position = pos_n1
                equipe["morale"] = round(min(1.5, _to_float(equipe.get("morale", 1.0), 1.0) + 0.02), 3)
                hierarquia["ordens_obedecidas"] = int(hierarquia.get("ordens_obedecidas", 0) or 0) + 1
                ordens_aplicadas += 1
            else:
                equipe["morale"] = round(max(0.5, _to_float(equipe.get("morale", 1.0), 1.0) - 0.05), 3)
                hierarquia["ordens_desobedecidas"] = int(hierarquia.get("ordens_desobedecidas", 0) or 0) + 1

            equipe["hierarquia"] = hierarquia

        if ordens_aplicadas > 0:
            race_results.sort(key=lambda item: int(item.finish_position))
            for posicao, resultado in enumerate(race_results, start=1):
                resultado.finish_position = posicao
                resultado.positions_gained = int(resultado.grid_position) - posicao

        return ordens_aplicadas

    def create_context(self, config: SimulationConfig) -> SimulationContext:
        weather = determine_weather(
            config.track_id,
            config.force_weather,
            config.track_name,
        )
        return SimulationContext(
            category_id=config.category_id,
            category_tier=config.category_tier,
            track_id=config.track_id,
            track_name=config.track_name,
            weather=weather,
            temperature=25.0,
            humidity=50.0,
            total_laps=config.total_laps,
            race_duration_minutes=config.race_duration_minutes,
            is_championship_deciding=config.is_championship_deciding,
            has_safety_car_enabled=config.enable_safety_car,
            base_lap_time_ms=config.base_lap_time_ms,
        )

    def simulate_qualifying_session(self, pilots, teams, context) -> list:
        return simulate_qualifying(pilots, teams, context)

    def simulate_race_session(self, qualifying_results, pilots, teams, context) -> list:
        return simulate_race(qualifying_results, pilots, teams, context)

    def simulate_full_event(
        self,
        config: SimulationConfig,
        pilots: list,
        teams: dict,
    ) -> RaceResult:
        """
        Simula evento completo (classificação + corrida).

        Args:
            config: Configuração da simulação
            pilots: Lista de objetos piloto
            teams: dict {pilot_id → equipe}

        Returns:
            RaceResult completo
        """
        context = self.create_context(config)

        quali_results = self.simulate_qualifying_session(pilots, teams, context)
        race_results  = self.simulate_race_session(quali_results, pilots, teams, context)
        self._aplicar_ordens_equipe_simuladas(race_results, teams)

        # Safety car
        safety_car_periods = []
        if context.has_safety_car_enabled:
            for result in race_results:
                for incident in result.incidents:
                    if should_deploy_safety_car([incident]):
                        sc = create_safety_car_period(
                            incident.dnf_segment or incident.segment if hasattr(incident, "dnf_segment") else incident.segment,
                            incident,
                            context.total_laps,
                        )
                        safety_car_periods.append(sc)
                        break

        # Pontos
        pole_id = quali_results[0].pilot_id if quali_results else ""
        fastest_lap_id   = ""
        fastest_lap_time = float("inf")
        scoring_rules = _resolve_scoring_rules(config.category_id, config.points_system)

        for result in race_results:
            if result.has_fastest_lap:
                fastest_lap_id   = result.pilot_id
                fastest_lap_time = result.best_lap_time_ms

        _assign_class_positions(race_results)

        for result in race_results:
            if result.is_dnf:
                result.points_earned = 0
                result.points_in_class = 0
                continue

            scoring_position = result.finish_position
            if scoring_rules["points_by_class"] and result.class_position > 0:
                scoring_position = result.class_position

            result.points_earned = calculate_points(
                position=scoring_position,
                got_pole=(scoring_rules["bonus_pole"] and result.pilot_id == pole_id),
                got_fastest_lap=(
                    scoring_rules["bonus_fastest_lap"] and result.has_fastest_lap
                ),
                points_system=scoring_rules["points_system"],
            )
            result.points_in_class = result.points_earned if result.class_position > 0 else 0

        total_incidents = sum(r.incidents_count for r in race_results)
        total_dnfs      = sum(1 for r in race_results if r.is_dnf)
        lead_changes    = sum(
            1 for r in race_results
            if r.grid_position > 1 and r.finish_position == 1
        )

        highlights = self._generate_highlights(quali_results, race_results, context)

        result = RaceResult(
            category_id=config.category_id,
            category_name=config.category_name,
            track_id=config.track_id,
            track_name=config.track_name,
            weather=context.weather,
            temperature=context.temperature,
            total_laps=context.total_laps,
            race_duration_minutes=config.race_duration_minutes,
            qualifying_results=quali_results,
            race_results=race_results,
            total_incidents=total_incidents,
            total_dnfs=total_dnfs,
            lead_changes=lead_changes,
            safety_car_periods=safety_car_periods,
            pole_sitter_id=pole_id,
            winner_id=race_results[0].pilot_id if race_results else "",
            fastest_lap_id=fastest_lap_id,
            fastest_lap_time_ms=fastest_lap_time if fastest_lap_time != float("inf") else 0,
            highlights=highlights,
        )
        self.last_result = result
        return result

    def _generate_highlights(self, quali, race, context) -> list:
        highlights = []
        if not race:
            return highlights

        winner = race[0]
        highlights.append(
            f"{winner.pilot_name} ({winner.team_name}) wins at {context.track_name}!"
        )

        if quali and quali[0].pilot_id == winner.pilot_id:
            highlights.append(f"{winner.pilot_name} converts pole to victory")
        elif quali:
            highlights.append(f"{winner.pilot_name} beats pole-sitter {quali[0].pilot_name}")

        biggest_gainer = max(race, key=lambda x: x.positions_gained)
        if biggest_gainer.positions_gained > 3:
            highlights.append(
                f"{biggest_gainer.pilot_name} gains {biggest_gainer.positions_gained} positions "
                f"(P{biggest_gainer.grid_position} → P{biggest_gainer.finish_position})"
            )

        biggest_loser = min(race, key=lambda x: x.positions_gained)
        if biggest_loser.positions_gained < -5:
            highlights.append(
                f"Tough race for {biggest_loser.pilot_name}: "
                f"drops {abs(biggest_loser.positions_gained)} positions"
            )

        dnfs = [r for r in race if r.is_dnf]
        if dnfs:
            names = [d.pilot_name for d in dnfs[:3]]
            prefix = f"{len(dnfs)} retirements including " if len(dnfs) > 3 else "Retirements: "
            highlights.append(prefix + ", ".join(names))

        fastest = next((r for r in race if r.has_fastest_lap), None)
        if fastest:
            highlights.append(f"Fastest lap: {fastest.pilot_name}")

        if context.weather != WeatherCondition.DRY:
            highlights.append(f"Race held in {context.weather.value} conditions")

        return highlights

    def simulate_simple(
        self,
        config: SimulationConfig,
        pilots: list,
        teams: dict,
    ) -> RaceResult:
        """Simulação simplificada (corridas distantes, sem segmentos)."""
        context      = self.create_context(config)
        quali_results = self.simulate_qualifying_session(pilots, teams, context)
        scoring_rules = _resolve_scoring_rules(config.category_id, config.points_system)

        def _id(p):
            return _get(p, "id", str(id(p)))

        pilot_map = {_id(p): p for p in pilots}
        race_rows = []

        for quali in quali_results:
            pilot = pilot_map.get(quali.pilot_id)
            team  = teams.get(quali.pilot_id)
            if not pilot or not team:
                continue

            skill = _to_float(_get(pilot, "skill", 60), 60)
            consistency = _to_float(_get(pilot, "consistencia", _get(pilot, "consistency", 60)), 60)
            car_perf = _to_float(_get(team, "car_performance", 60), 60)

            score    = skill * 0.4 + consistency * 0.2 + car_perf * 0.4 + random.uniform(-8, 8)
            is_dnf   = random.random() < 0.03

            race_rows.append({
                "pilot_id":   quali.pilot_id,
                "pilot_name": quali.pilot_name,
                "team_id":    quali.team_id,
                "team_name":  quali.team_name,
                "grid":       quali.position,
                "score":      -1000 if is_dnf else score,
                "is_dnf":     is_dnf,
            })

        race_rows.sort(key=lambda x: x["score"], reverse=True)

        final_results = []
        for pos, entry in enumerate(race_rows, 1):
            final_results.append(RaceDriverResult(
                pilot_id=entry["pilot_id"],
                pilot_name=entry["pilot_name"],
                team_id=entry["team_id"],
                team_name=entry["team_name"],
                grid_position=entry["grid"],
                finish_position=pos,
                is_dnf=entry["is_dnf"],
                laps_completed=(config.total_laps if not entry["is_dnf"]
                                else random.randint(1, config.total_laps - 1)),
            ))

        pole_id = quali_results[0].pilot_id if quali_results else ""
        _assign_class_positions(final_results)
        for result in final_results:
            if result.is_dnf:
                result.points_earned = 0
                result.points_in_class = 0
                continue
            scoring_position = (
                result.class_position
                if scoring_rules["points_by_class"] and result.class_position > 0
                else result.finish_position
            )
            result.points_earned = calculate_points(
                position=scoring_position,
                got_pole=(scoring_rules["bonus_pole"] and result.pilot_id == pole_id),
                got_fastest_lap=(
                    scoring_rules["bonus_fastest_lap"] and result.has_fastest_lap
                ),
                points_system=scoring_rules["points_system"],
            )
            result.points_in_class = result.points_earned if result.class_position > 0 else 0

        return RaceResult(
            category_id=config.category_id,
            category_name=config.category_name,
            track_id=config.track_id,
            track_name=config.track_name,
            weather=context.weather,
            total_laps=config.total_laps,
            qualifying_results=quali_results,
            race_results=final_results,
            winner_id=final_results[0].pilot_id if final_results else "",
            pole_sitter_id=quali_results[0].pilot_id if quali_results else "",
            highlights=self._generate_highlights(quali_results, final_results, context),
        )


_simulator_instance: Optional[RaceSimulator] = None


def get_simulator() -> RaceSimulator:
    """Retorna instância global do simulador."""
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = RaceSimulator()
    return _simulator_instance
