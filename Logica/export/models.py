# Logica/export/models.py
"""
Modelos de dados para o sistema de exportação ao iRacing.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ModifierSource(Enum):
    """Fonte/razão do modificador"""
    # Skill
    CATEGORY_FAMILIARITY = "category_familiarity"
    TRACK_KNOWLEDGE = "track_knowledge"
    INJURY = "injury"
    PRESSURE_CLUTCH = "pressure_clutch"
    MOMENTUM = "momentum"
    RAIN = "rain"

    # Aggression
    FRUSTRATION = "frustration"
    RIVALRY = "rivalry"
    NOTHING_TO_LOSE = "nothing_to_lose"
    CONTRACT_DESPERATION = "contract_desperation"
    HOME_RACE = "home_race"
    CHASING_LEADER = "chasing_leader"

    # Optimism
    POSITIVE_MOMENTUM = "positive_momentum"
    NEGATIVE_MOMENTUM = "negative_momentum"
    ROOKIE_IN_CATEGORY = "rookie_in_category"
    POST_DNF = "post_dnf"
    CHAMPIONSHIP_LEADER = "championship_leader"
    CHAMPIONSHIP_CHASER = "championship_chaser"
    VETERAN = "veteran"

    # Smoothness
    EXPERIENCE = "experience"
    FATIGUE = "fatigue"
    CONFIDENCE = "confidence"
    RAIN_INSECURITY = "rain_insecurity"


@dataclass
class Modifier:
    """Um modificador individual"""
    source: ModifierSource
    value: float  # Valor do modificador (pode ser + ou -)
    description: str

    def __str__(self):
        sign = "+" if self.value >= 0 else ""
        return f"{self.source.value}: {sign}{self.value:.1f} ({self.description})"


@dataclass
class ModifierReport:
    """Relatório completo de modificadores de um piloto"""
    pilot_id: str
    pilot_name: str

    # Modificadores por categoria
    skill_modifiers: list[Modifier] = field(default_factory=list)
    aggression_modifiers: list[Modifier] = field(default_factory=list)
    optimism_modifiers: list[Modifier] = field(default_factory=list)
    smoothness_modifiers: list[Modifier] = field(default_factory=list)

    # Totais calculados
    skill_total: float = 0.0
    aggression_total: float = 0.0
    optimism_total: float = 0.0
    smoothness_total: float = 0.0

    def calculate_totals(self):
        """Calcula totais de cada categoria"""
        self.skill_total = sum(m.value for m in self.skill_modifiers)
        self.aggression_total = sum(m.value for m in self.aggression_modifiers)
        self.optimism_total = sum(m.value for m in self.optimism_modifiers)
        self.smoothness_total = sum(m.value for m in self.smoothness_modifiers)

    def get_summary(self) -> str:
        """Retorna resumo textual"""
        self.calculate_totals()
        lines = [
            f"=== Modificadores: {self.pilot_name} ===",
            "",
            "SKILL:",
        ]
        for m in self.skill_modifiers:
            lines.append(f"  {m}")
        lines.append(f"  TOTAL: {self.skill_total:+.1f}%")

        lines.append("\nAGRESSIVIDADE:")
        for m in self.aggression_modifiers:
            lines.append(f"  {m}")
        lines.append(f"  TOTAL: {self.aggression_total:+.1f}")

        lines.append("\nOTIMISMO:")
        for m in self.optimism_modifiers:
            lines.append(f"  {m}")
        lines.append(f"  TOTAL: {self.optimism_total:+.1f}")

        lines.append("\nSUAVIDADE:")
        for m in self.smoothness_modifiers:
            lines.append(f"  {m}")
        lines.append(f"  TOTAL: {self.smoothness_total:+.1f}")

        return "\n".join(lines)


@dataclass
class PilotExportData:
    """
    Dados de um piloto prontos para exportar ao iRacing.
    """
    pilot_id: str
    display_name: str
    car_number: str

    # Atributos do iRacing (0-100)
    skill: int
    aggression: int
    optimism: int
    smoothness: int
    age: int

    livery: dict = field(default_factory=dict)

    original_skill: float = 0.0
    modifier_report: Optional[ModifierReport] = None

    def to_iracing_format(self) -> dict:
        """
        Converte para formato esperado pelo iRacing.
        """
        return {
            "display_name": self.display_name,
            "carNumber": self.car_number,
            "skill": self.skill,
            "aggression": self.aggression,
            "optimism": self.optimism,
            "smoothness": self.smoothness,
            "age": self.age,
            "livery": self.livery
        }


@dataclass
class RaceContext:
    """Contexto da corrida para cálculo de modificadores"""
    category_id: str
    category_name: str
    category_tier: int  # 1-6
    track_id: int
    track_name: str
    round_number: int
    total_rounds: int

    car_id: int = 67

    is_wet: bool = False
    rain_intensity: float = 0.0

    is_championship_deciding: bool = False
    championship_standings: dict = field(default_factory=dict)
    points_gap_to_leader: dict = field(default_factory=dict)

    active_rivalries: list[tuple[str, str, int]] = field(default_factory=list)

    home_race_pilots: list[str] = field(default_factory=list)


@dataclass
class PilotContext:
    """Contexto específico do piloto para cálculo de modificadores"""
    pilot_id: str

    races_in_category: int = 0
    seasons_in_category: int = 0

    times_at_track: int = 0
    best_result_at_track: int = 99

    last_5_results: list[int] = field(default_factory=list)
    last_5_expected: list[int] = field(default_factory=list)
    dnf_in_last_race: bool = False
    dnf_was_collision: bool = False

    championship_position: int = 0
    points_to_leader: int = 0
    is_eliminated: bool = False

    contract_years_left: int = 2
    is_in_contract_year: bool = False
    team_performance_vs_expectations: float = 1.0

    has_injury: bool = False
    injury_severity: float = 0.0
    injury_races_left: int = 0

    rival_ids: list[str] = field(default_factory=list)
    rivals_in_race: list[str] = field(default_factory=list)

    is_home_race: bool = False
    is_rookie: bool = False
    is_veteran: bool = False
