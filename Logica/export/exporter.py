# Logica/export/exporter.py
"""
Main orchestrator for Module 5 export modifiers.

This module calculates final pilot attributes. It does not write the final
roster JSON file.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import PilotExportData, ModifierReport, PilotContext, RaceContext
from .skill_modifiers import get_all_skill_modifiers
from .aggression_modifiers import get_all_aggression_modifiers
from .optimism_modifiers import get_all_optimism_modifiers
from .smoothness_modifiers import get_all_smoothness_modifiers


@runtime_checkable
class PilotProtocol(Protocol):
    """Expected pilot interface for export logic."""

    id: str
    nome: str
    skill: float
    aggression: float
    optimism: float
    smoothness: float
    idade: int
    fator_clutch: float
    fator_chuva: float
    experiencia: float


SKILL_MODIFIER_CAP = 25.0
AGGRESSION_MODIFIER_CAP = 25.0
OPTIMISM_MODIFIER_CAP = 20.0
SMOOTHNESS_MODIFIER_CAP = 20.0


def _get(obj, key: str, default=None):
    """Read value from dict or object using one canonical key."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _get_one_of(obj, keys: tuple[str, ...], default=None):
    """Read first existing key/attribute from dict or object."""
    for key in keys:
        value = _get(obj, key, None)
        if value is not None:
            return value
    return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def calculate_all_modifiers(
    pilot,  # PilotProtocol
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    races_this_season: int = 0,
) -> ModifierReport:
    """Calculate all modifiers for one pilot."""
    report = ModifierReport(
        pilot_id=str(_get(pilot, "id", str(id(pilot)))),
        pilot_name=str(_get_one_of(pilot, ("nome", "name"), "Pilot")),
    )

    fator_clutch = float(_get(pilot, "fator_clutch", 50.0))
    fator_chuva = float(_get(pilot, "fator_chuva", 50.0))
    experiencia = float(_get(pilot, "experiencia", 50.0))

    report.skill_modifiers = get_all_skill_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        fator_clutch=fator_clutch,
        fator_chuva=fator_chuva,
    )

    report.aggression_modifiers = get_all_aggression_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
    )

    report.optimism_modifiers = get_all_optimism_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
    )

    report.smoothness_modifiers = get_all_smoothness_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        experiencia=experiencia,
        fator_chuva=fator_chuva,
        races_this_season=races_this_season,
    )

    report.calculate_totals()
    return report


def apply_skill_modifier(base_skill: float, modifier_total: float) -> float:
    """Apply percentage modifier to base skill with cap."""
    capped = clamp(modifier_total, -SKILL_MODIFIER_CAP, SKILL_MODIFIER_CAP)
    return base_skill * (1 + capped / 100)


def apply_absolute_modifier(base_value: float, modifier_total: float, cap: float) -> float:
    """Apply absolute point modifier with cap."""
    capped = clamp(modifier_total, -cap, cap)
    return base_value + capped


def export_pilot_data(
    pilot,  # PilotProtocol / dict
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    car_number: str = "0",
    livery: dict | None = None,
    races_this_season: int = 0,
) -> PilotExportData:
    """Calculate final export values for one pilot."""
    report = calculate_all_modifiers(
        pilot=pilot,
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        races_this_season=races_this_season,
    )

    base_skill = float(_get(pilot, "skill", 60.0))
    base_aggression = float(_get_one_of(pilot, ("aggression", "agressividade"), 50.0))
    base_optimism = float(_get_one_of(pilot, ("optimism", "otimismo"), 50.0))
    base_smoothness = float(_get_one_of(pilot, ("smoothness", "suavidade"), 50.0))
    age = int(_get(pilot, "idade", _get(pilot, "age", 25)))
    pilot_id = str(_get(pilot, "id", "0"))
    display_name = str(_get_one_of(pilot, ("nome", "name"), "Pilot"))

    final_skill = apply_skill_modifier(base_skill, report.skill_total)
    final_aggression = apply_absolute_modifier(
        base_aggression,
        report.aggression_total,
        AGGRESSION_MODIFIER_CAP,
    )
    final_optimism = apply_absolute_modifier(
        base_optimism,
        report.optimism_total,
        OPTIMISM_MODIFIER_CAP,
    )
    final_smoothness = apply_absolute_modifier(
        base_smoothness,
        report.smoothness_total,
        SMOOTHNESS_MODIFIER_CAP,
    )

    return PilotExportData(
        pilot_id=pilot_id,
        display_name=display_name,
        car_number=car_number,
        skill=int(clamp(final_skill, 0, 100)),
        aggression=int(clamp(final_aggression, 0, 100)),
        optimism=int(clamp(final_optimism, 0, 100)),
        smoothness=int(clamp(final_smoothness, 0, 100)),
        age=age,
        livery=livery or {},
        original_skill=base_skill,
        modifier_report=report,
    )


def export_all_pilots(
    pilots: list,  # list[PilotProtocol / dict]
    pilot_contexts: dict,  # dict[pilot_id, PilotContext]
    race_ctx: RaceContext,
    car_numbers: dict | None = None,
    liveries: dict | None = None,
    races_this_season: int = 0,
) -> list[PilotExportData]:
    """Export all pilots from one race."""
    exported: list[PilotExportData] = []

    for pilot in pilots:
        pilot_id = _get(pilot, "id", str(id(pilot)))
        pilot_ctx = pilot_contexts.get(pilot_id, PilotContext(pilot_id=str(pilot_id)))
        car_number = car_numbers.get(pilot_id, "0") if car_numbers else "0"
        livery = liveries.get(pilot_id, {}) if liveries else {}

        data = export_pilot_data(
            pilot=pilot,
            pilot_ctx=pilot_ctx,
            race_ctx=race_ctx,
            car_number=car_number,
            livery=livery,
            races_this_season=races_this_season,
        )
        exported.append(data)

    return exported


def generate_modifier_report_text(pilots_data: list[PilotExportData]) -> str:
    """Generate textual report with all modifiers."""
    lines = [
        "=" * 60,
        "RELATORIO DE MODIFICADORES",
        "=" * 60,
        "",
    ]

    for pilot in pilots_data:
        if pilot.modifier_report:
            lines.append(pilot.modifier_report.get_summary())
            lines.append("")
            lines.append(">>> VALORES FINAIS:")
            lines.append(f"    Skill: {pilot.original_skill:.0f} -> {pilot.skill}")
            lines.append(f"    Agressividade: {pilot.aggression}")
            lines.append(f"    Otimismo: {pilot.optimism}")
            lines.append(f"    Suavidade: {pilot.smoothness}")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

    return "\n".join(lines)
