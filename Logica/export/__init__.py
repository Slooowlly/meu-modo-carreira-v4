# Logica/export/__init__.py
"""
Módulo 5: Sistema de Exportação para iRacing
"""

from .car_ids import (
    CarInfo,
    IRACING_CARS,
    CATEGORY_TO_CAR_ID,
    get_car_info,
    get_car_id_for_category,
    get_car_name,
    get_cars_by_class,
    get_all_gt3_cars,
    get_all_gt4_cars,
    is_valid_car_id,
    validate_car_for_category
)

from .models import (
    ModifierSource,
    Modifier,
    ModifierReport,
    PilotExportData,
    PilotContext,
    RaceContext
)

from .skill_modifiers import (
    get_all_skill_modifiers,
    calculate_category_familiarity,
    calculate_track_knowledge,
    calculate_injury_modifier,
    calculate_pressure_clutch,
    calculate_momentum,
    calculate_rain_skill_modifier
)

from .aggression_modifiers import (
    get_all_aggression_modifiers,
    calculate_frustration,
    calculate_rivalry,
    calculate_nothing_to_lose,
    calculate_contract_desperation,
    calculate_home_race,
    calculate_chasing_leader
)

from .optimism_modifiers import (
    get_all_optimism_modifiers,
    calculate_positive_momentum,
    calculate_negative_momentum,
    calculate_rookie_modifier,
    calculate_post_dnf,
    calculate_championship_leader,
    calculate_championship_chaser,
    calculate_veteran_modifier
)

from .smoothness_modifiers import (
    get_all_smoothness_modifiers,
    calculate_experience_modifier,
    calculate_frustration_smoothness,
    calculate_fatigue_modifier,
    calculate_confidence_modifier,
    calculate_rain_insecurity
)

from .exporter import (
    calculate_all_modifiers,
    export_pilot_data,
    export_all_pilots,
    generate_modifier_report_text,
    apply_skill_modifier,
    apply_absolute_modifier,
    SKILL_MODIFIER_CAP,
    AGGRESSION_MODIFIER_CAP,
    OPTIMISM_MODIFIER_CAP,
    SMOOTHNESS_MODIFIER_CAP
)

from .roster_integration import (
    calculate_pilot_for_export,
    build_pilot_context,
    build_race_context,
    prepare_roster_data,
    get_iracing_roster_path
)


__all__ = [
    'CarInfo', 'IRACING_CARS', 'CATEGORY_TO_CAR_ID', 'get_car_info',
    'get_car_id_for_category', 'get_car_name', 'get_cars_by_class',
    'get_all_gt3_cars', 'get_all_gt4_cars', 'is_valid_car_id',
    'validate_car_for_category',

    'ModifierSource', 'Modifier', 'ModifierReport', 'PilotExportData',
    'PilotContext', 'RaceContext',

    'get_all_skill_modifiers', 'calculate_category_familiarity',
    'calculate_track_knowledge', 'calculate_injury_modifier',
    'calculate_pressure_clutch', 'calculate_momentum',
    'calculate_rain_skill_modifier',

    'get_all_aggression_modifiers', 'calculate_frustration',
    'calculate_rivalry', 'calculate_nothing_to_lose',
    'calculate_contract_desperation', 'calculate_home_race',
    'calculate_chasing_leader',

    'get_all_optimism_modifiers', 'calculate_positive_momentum',
    'calculate_negative_momentum', 'calculate_rookie_modifier',
    'calculate_post_dnf', 'calculate_championship_leader',
    'calculate_championship_chaser', 'calculate_veteran_modifier',

    'get_all_smoothness_modifiers', 'calculate_experience_modifier',
    'calculate_frustration_smoothness', 'calculate_fatigue_modifier',
    'calculate_confidence_modifier', 'calculate_rain_insecurity',

    'calculate_all_modifiers', 'export_pilot_data', 'export_all_pilots',
    'generate_modifier_report_text', 'apply_skill_modifier',
    'apply_absolute_modifier', 'SKILL_MODIFIER_CAP',
    'AGGRESSION_MODIFIER_CAP', 'OPTIMISM_MODIFIER_CAP',
    'SMOOTHNESS_MODIFIER_CAP',

    'calculate_pilot_for_export', 'build_pilot_context',
    'build_race_context', 'prepare_roster_data', 'get_iracing_roster_path'
]
