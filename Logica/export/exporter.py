# Logica/export/exporter.py
"""
Orquestrador principal do sistema de exportação.
Calcula todos os modificadores e prepara dados para exportação.

IMPORTANTE: Este arquivo NÃO gera o JSON final.
O JSON deve ser gerado pelo EXPORTADOR EXISTENTE no projeto.
Este módulo apenas calcula os valores finais dos atributos.
"""

from typing import Protocol, runtime_checkable, Optional

from .models import (
    PilotExportData,
    ModifierReport,
    PilotContext,
    RaceContext
)
from .skill_modifiers import get_all_skill_modifiers
from .aggression_modifiers import get_all_aggression_modifiers
from .optimism_modifiers import get_all_optimism_modifiers
from .smoothness_modifiers import get_all_smoothness_modifiers
from .car_ids import get_car_id_for_category, get_car_name


@runtime_checkable
class PilotProtocol(Protocol):
    """
    Interface esperada do modelo Pilot do Módulo 1.
    
    O Pilot DEVE ter estes atributos para funcionar com o exportador.
    """
    id: str
    name: str
    skill: float           # 0-100
    agressividade: float   # 0-100
    otimismo: float        # 0-100
    suavidade: float       # 0-100
    idade: int
    clutch_factor: float   # 0-100
    rain_factor: float     # 0-100
    experience: float      # 0-100


# ==================== CAPS DE MODIFICADORES ====================

SKILL_MODIFIER_CAP = 25.0       # ±25% máximo
AGGRESSION_MODIFIER_CAP = 25.0  # ±25 pontos máximo
OPTIMISM_MODIFIER_CAP = 20.0    # ±20 pontos máximo
SMOOTHNESS_MODIFIER_CAP = 20.0  # ±20 pontos máximo


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limita valor entre min e max"""
    return max(min_val, min(max_val, value))


def calculate_all_modifiers(
    pilot,  # PilotProtocol
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    races_this_season: int = 0
) -> ModifierReport:
    """
    Calcula todos os modificadores para um piloto.
    """
    report = ModifierReport(
        pilot_id=pilot.id if hasattr(pilot, 'id') else pilot.get('id', str(id(pilot))),
        pilot_name=pilot.name if hasattr(pilot, 'name') else pilot.get('nome', 'Pilot')
    )

    # Extrair atributos dependendo se é dict ou object
    clutch_factor = getattr(pilot, 'clutch_factor', pilot.get('clutch_factor', 50.0)) if isinstance(pilot, dict) else getattr(pilot, 'clutch_factor', 50.0)
    rain_factor = getattr(pilot, 'rain_factor', pilot.get('fator_chuva', 50.0)) if isinstance(pilot, dict) else getattr(pilot, 'rain_factor', 50.0)
    experience = getattr(pilot, 'experience', pilot.get('experiencia', 50.0)) if isinstance(pilot, dict) else getattr(pilot, 'experience', 50.0)

    # Skill modifiers
    report.skill_modifiers = get_all_skill_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        clutch_factor=clutch_factor,
        rain_factor=rain_factor
    )

    # Aggression modifiers
    report.aggression_modifiers = get_all_aggression_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx
    )

    # Optimism modifiers
    report.optimism_modifiers = get_all_optimism_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx
    )

    # Smoothness modifiers
    report.smoothness_modifiers = get_all_smoothness_modifiers(
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        experience=experience,
        rain_factor=rain_factor,
        races_this_season=races_this_season
    )

    report.calculate_totals()

    return report


def apply_skill_modifier(base_skill: float, modifier_total: float) -> float:
    """
    Aplica modificador de skill (porcentagem).
    """
    capped = clamp(modifier_total, -SKILL_MODIFIER_CAP, SKILL_MODIFIER_CAP)
    return base_skill * (1 + capped / 100)


def apply_absolute_modifier(base_value: float, modifier_total: float, cap: float) -> float:
    """
    Aplica modificador absoluto (pontos).
    """
    capped = clamp(modifier_total, -cap, cap)
    return base_value + capped


def export_pilot_data(
    pilot,  # PilotProtocol / dict
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    car_number: str = "0",
    livery: dict = None,
    races_this_season: int = 0
) -> PilotExportData:
    """
    Calcula valores finais de um piloto para exportação.
    """
    import logging
    # Calcular modificadores
    report = calculate_all_modifiers(
        pilot=pilot,
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        races_this_season=races_this_season
    )

    is_dict = isinstance(pilot, dict)

    # Extrair valores base
    base_skill = float(pilot.get('skill', 60.0)) if is_dict else float(getattr(pilot, 'skill', 60.0))
    base_aggression = float(pilot.get('agressividade', pilot.get('aggression', 50.0))) if is_dict else float(getattr(pilot, 'agressividade', 50.0))
    base_optimism = float(pilot.get('otimismo', pilot.get('optimism', 50.0))) if is_dict else float(getattr(pilot, 'otimismo', 50.0))
    base_smoothness = float(pilot.get('suavidade', pilot.get('smoothness', 50.0))) if is_dict else float(getattr(pilot, 'suavidade', 50.0))
    age = int(pilot.get('idade', 25)) if is_dict else int(getattr(pilot, 'idade', 25))
    pilot_id = str(pilot.get('id', '0')) if is_dict else str(getattr(pilot, 'id', '0'))
    display_name = str(pilot.get('nome', 'Pilot')) if is_dict else str(getattr(pilot, 'name', 'Pilot'))

    # Aplicar modificadores
    final_skill = apply_skill_modifier(base_skill, report.skill_total)
    final_aggression = apply_absolute_modifier(
        base_aggression, report.aggression_total, AGGRESSION_MODIFIER_CAP
    )
    final_optimism = apply_absolute_modifier(
        base_optimism, report.optimism_total, OPTIMISM_MODIFIER_CAP
    )
    final_smoothness = apply_absolute_modifier(
        base_smoothness, report.smoothness_total, SMOOTHNESS_MODIFIER_CAP
    )

    # Clampar para range do iRacing (0-100)
    final_skill_int = int(clamp(final_skill, 0, 100))
    final_aggression_int = int(clamp(final_aggression, 0, 100))
    final_optimism_int = int(clamp(final_optimism, 0, 100))
    final_smoothness_int = int(clamp(final_smoothness, 0, 100))

    return PilotExportData(
        pilot_id=pilot_id,
        display_name=display_name,
        car_number=car_number,
        skill=final_skill_int,
        aggression=final_aggression_int,
        optimism=final_optimism_int,
        smoothness=final_smoothness_int,
        age=age,
        livery=livery or {},
        original_skill=base_skill,
        modifier_report=report
    )


def export_all_pilots(
    pilots: list,  # list[PilotProtocol / dict]
    pilot_contexts: dict,  # dict[pilot_id, PilotContext]
    race_ctx: RaceContext,
    car_numbers: dict = None,
    liveries: dict = None,
    races_this_season: int = 0
) -> list[PilotExportData]:
    """
    Exporta todos os pilotos de uma corrida.
    """
    exported = []

    for pilot in pilots:
        pilot_id = pilot.get('id', str(id(pilot))) if isinstance(pilot, dict) else getattr(pilot, 'id', str(id(pilot)))
        pilot_ctx = pilot_contexts.get(pilot_id, PilotContext(pilot_id=pilot_id))
        car_number = car_numbers.get(pilot_id, "0") if car_numbers else "0"
        livery = liveries.get(pilot_id, {}) if liveries else {}

        data = export_pilot_data(
            pilot=pilot,
            pilot_ctx=pilot_ctx,
            race_ctx=race_ctx,
            car_number=car_number,
            livery=livery,
            races_this_season=races_this_season
        )
        exported.append(data)

    return exported


def generate_modifier_report_text(pilots_data: list[PilotExportData]) -> str:
    """
    Gera relatório textual de modificadores para debug/visualização.
    """
    lines = [
        "=" * 60,
        "RELATÓRIO DE MODIFICADORES",
        "=" * 60,
        ""
    ]

    for pilot in pilots_data:
        if pilot.modifier_report:
            lines.append(pilot.modifier_report.get_summary())
            lines.append("")
            lines.append(f">>> VALORES FINAIS:")
            lines.append(f"    Skill: {pilot.original_skill:.0f} → {pilot.skill}")
            lines.append(f"    Agressividade: {pilot.aggression}")
            lines.append(f"    Otimismo: {pilot.optimism}")
            lines.append(f"    Suavidade: {pilot.smoothness}")
            lines.append("")
            lines.append("-" * 40)
            lines.append("")

    return "\n".join(lines)
