"""
Modelos de dados para resultados de corridas e simulação.
Integra com os modelos de Pilot e Team dos Módulos 1 e 2.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import uuid


# ==================== ENUMS ====================

class SessionType(Enum):
    QUALIFYING = "qualifying"
    RACE = "race"


class IncidentType(Enum):
    NONE = "none"
    MECHANICAL = "mechanical"
    DRIVER_ERROR = "driver_error"
    COLLISION = "collision"


class IncidentSeverity(Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


class WeatherCondition(Enum):
    DRY = "dry"
    DAMP = "damp"
    WET = "wet"
    HEAVY_RAIN = "heavy_rain"


class RaceSegment(Enum):
    START = "start"
    EARLY = "early"
    MID = "mid"
    LATE = "late"
    FINISH = "finish"


# ==================== MODELOS DE DADOS ====================

@dataclass
class SegmentResult:
    """Resultado de um piloto em um segmento específico"""
    segment: RaceSegment
    position: int
    segment_score: float
    cumulative_score: float
    tire_wear: float
    physical_condition: float
    incident: Optional["IncidentResult"] = None
    positions_changed: int = 0


@dataclass
class IncidentResult:
    """Resultado de um incidente"""
    incident_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    incident_type: IncidentType = IncidentType.NONE
    severity: IncidentSeverity = IncidentSeverity.MINOR
    segment: RaceSegment = RaceSegment.START
    is_dnf: bool = False
    positions_lost: int = 0
    involved_pilots: list = field(default_factory=list)
    description: str = ""
    causes_injury: bool = False

    def __post_init__(self):
        if self.severity in (IncidentSeverity.MAJOR, IncidentSeverity.CRITICAL):
            self.is_dnf = True


@dataclass
class QualifyingResult:
    """Resultado da classificação de um piloto"""
    pilot_id: str
    pilot_name: str
    team_id: str
    team_name: str
    position: int
    quali_score: float
    best_lap_time_ms: float
    gap_to_pole_ms: float
    is_pole: bool = False

    @property
    def best_lap_formatted(self) -> str:
        total_seconds = self.best_lap_time_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:06.3f}"


@dataclass
class RaceDriverResult:
    """Resultado completo de um piloto na corrida"""
    pilot_id: str
    pilot_name: str
    team_id: str
    team_name: str

    grid_position: int
    finish_position: int
    class_id: str = ""
    class_position: int = 0
    points_in_class: int = 0
    positions_gained: int = 0

    best_lap_time_ms: float = 0
    total_race_time_ms: float = 0
    gap_to_winner_ms: float = 0

    is_dnf: bool = False
    dnf_reason: str = ""
    dnf_segment: Optional[RaceSegment] = None
    laps_completed: int = 0

    laps_led: int = 0
    incidents_count: int = 0
    incidents: list = field(default_factory=list)

    has_fastest_lap: bool = False
    segment_history: list = field(default_factory=list)
    points_earned: int = 0

    def __post_init__(self):
        self.positions_gained = self.grid_position - self.finish_position


@dataclass
class SafetyCarPeriod:
    """Período de safety car"""
    start_segment: RaceSegment
    laps_under_sc: int
    reason: str
    incident_id: str


@dataclass
class RaceResult:
    """Resultado completo de uma corrida"""
    race_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category_id: str = ""
    category_name: str = ""
    track_id: int = 0
    track_name: str = ""

    weather: WeatherCondition = WeatherCondition.DRY
    temperature: float = 25.0

    total_laps: int = 0
    race_duration_minutes: int = 0

    qualifying_results: list = field(default_factory=list)
    race_results: list = field(default_factory=list)

    total_incidents: int = 0
    total_dnfs: int = 0
    lead_changes: int = 0
    safety_car_periods: list = field(default_factory=list)

    pole_sitter_id: str = ""
    winner_id: str = ""
    fastest_lap_id: str = ""
    fastest_lap_time_ms: float = 0

    highlights: list = field(default_factory=list)

    @property
    def had_safety_car(self) -> bool:
        return len(self.safety_car_periods) > 0

    @property
    def is_wet_race(self) -> bool:
        return self.weather in (WeatherCondition.WET, WeatherCondition.HEAVY_RAIN)

    def get_podium(self) -> list:
        sorted_results = sorted(
            [r for r in self.race_results if not r.is_dnf],
            key=lambda x: x.finish_position
        )
        return sorted_results[:3]

    def get_dnf_list(self) -> list:
        return [r for r in self.race_results if r.is_dnf]

    def get_driver_result(self, pilot_id: str) -> Optional[RaceDriverResult]:
        for result in self.race_results:
            if result.pilot_id == pilot_id:
                return result
        return None


@dataclass
class SimulationContext:
    """Contexto da simulação"""
    category_id: str
    category_tier: int
    track_id: int
    track_name: str
    weather: WeatherCondition
    temperature: float
    humidity: float
    total_laps: int
    race_duration_minutes: int
    is_championship_deciding: bool = False
    has_safety_car_enabled: bool = True
    base_lap_time_ms: float = 90000
    tire_degradation_rate: float = 0.02
    physical_degradation_rate: float = 0.01


# ==================== PONTUAÇÃO ====================

DEFAULT_POINTS_SYSTEM = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8,  7: 6,  8: 4,  9: 2,  10: 1
}

POLE_BONUS_POINTS = 1
FASTEST_LAP_BONUS_POINTS = 1


def calculate_points(
    position: int,
    got_pole: bool = False,
    got_fastest_lap: bool = False,
    points_system: dict = None
) -> int:
    """Calcula pontos baseado na posição e bônus"""
    if points_system is None:
        points_system = DEFAULT_POINTS_SYSTEM

    points = points_system.get(position, 0)

    if got_pole:
        points += POLE_BONUS_POINTS

    if got_fastest_lap and position <= 10:
        points += FASTEST_LAP_BONUS_POINTS

    return points
