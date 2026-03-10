"""
Orquestrador principal de simulação de corridas.
"""

import random
from typing import Optional
from dataclasses import dataclass

from .models import (
    RaceResult,
    SimulationContext,
    WeatherCondition,
    RaceDriverResult,
    QualifyingResult,
    calculate_points,
)
from .qualifying import simulate_qualifying
from .race import simulate_race
from .weather import determine_weather
from .safety_car import should_deploy_safety_car, create_safety_car_period


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

        for result in race_results:
            if result.has_fastest_lap:
                fastest_lap_id   = result.pilot_id
                fastest_lap_time = result.best_lap_time_ms

            result.points_earned = calculate_points(
                position=result.finish_position,
                got_pole=(result.pilot_id == pole_id),
                got_fastest_lap=result.has_fastest_lap,
                points_system=config.points_system,
            )

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

        def _id(p):
            return getattr(p, "id", None) or (p.get("id") if isinstance(p, dict) else str(id(p)))

        pilot_map = {_id(p): p for p in pilots}
        race_rows = []

        for quali in quali_results:
            pilot = pilot_map.get(quali.pilot_id)
            team  = teams.get(quali.pilot_id)
            if not pilot or not team:
                continue

            skill       = getattr(pilot, "skill", pilot.get("skill", 60) if isinstance(pilot, dict) else 60)
            consistency = getattr(pilot, "consistencia", pilot.get("consistencia", 60) if isinstance(pilot, dict) else 60)
            car_perf    = getattr(team, "car_performance", team.get("car_performance", 60) if isinstance(team, dict) else 60)

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
