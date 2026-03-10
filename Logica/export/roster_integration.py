# Logica/export/roster_integration.py
"""
Integração com o EXPORTADOR JSON EXISTENTE no projeto.
"""

from typing import Optional, Any
from .models import PilotContext, RaceContext, PilotExportData
from .exporter import export_pilot_data, export_all_pilots
from .car_ids import (
    get_car_id_for_category,
    get_car_name,
    get_car_info,
    IRACING_CARS,
    CATEGORY_TO_CAR_ID
)


def calculate_pilot_for_export(
    pilot: Any,
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    car_number: str = "0",
    livery: dict = None,
    races_this_season: int = 0
) -> dict:
    """
    Calcula os valores de um piloto para exportação.
    """
    data = export_pilot_data(
        pilot=pilot,
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        car_number=car_number,
        livery=livery,
        races_this_season=races_this_season
    )
    return data.to_iracing_format()


def build_pilot_context(
    pilot: Any,
    season_data: Any = None,
    track_id: int = 0
) -> PilotContext:
    """
    Constrói PilotContext a partir dos dados do seu piloto (Dict).
    """
    is_dict = isinstance(pilot, dict)
    pilot_id = str(pilot.get('id', str(id(pilot))) if is_dict else getattr(pilot, 'id', str(id(pilot))))

    # Dados da temporada atual armazenados no piloto
    races_in_category = int(pilot.get('corridas_carreira', 0) if is_dict else getattr(pilot, 'corridas_carreira', 0))
    seasons_in_category = int(pilot.get('temporadas_categoria', max(1, races_in_category // 12)) if is_dict else getattr(pilot, 'temporadas_categoria', max(1, races_in_category // 12)))

    # Experiencia no circuito (mock fallback caso nao via DB)
    times_at_track = 0
    best_result_at_track = 99
    track_history = pilot.get('track_history', {}) if is_dict else getattr(pilot, 'track_history', {})
    if track_history and track_id in track_history:
        track_data = track_history[track_id]
        times_at_track = track_data.get('times', 0)
        best_result_at_track = track_data.get('best', 99)

    # Resultados Recentes (no banco é salvo em resultados_temporada)
    resultados = pilot.get('resultados_temporada', []) if is_dict else getattr(pilot, 'resultados_temporada', [])
    if not isinstance(resultados, list): resultados = []
    
    # Filtrar apenas inteiros para as posicoes calculadas
    last_5_results = [r for r in resultados[-5:] if isinstance(r, int)]
    
    last_5_expected = pilot.get('historico_expectativas', [])[-5:] if is_dict else getattr(pilot, 'historico_expectativas', [])[-5:]
    if not isinstance(last_5_expected, list) or not last_5_expected:
        last_5_expected = [10] * len(last_5_results) # Mock fallback para desencadear o Momentum

    # DNF Flag
    dnf_in_last_race = len(resultados) > 0 and (resultados[-1] == "DNF" or str(resultados[-1]).upper() == "DNF")
    dnf_was_collision = bool(pilot.get('dnf_colisao', False) if is_dict else getattr(pilot, 'dnf_colisao', False))

    # Campeonato
    championship_position = int(pilot.get('posicao_campeonato', 0) if is_dict else getattr(pilot, 'posicao_campeonato', 0))
    points_to_leader = int(pilot.get('pontos_para_lider', 999) if is_dict else getattr(pilot, 'pontos_para_lider', 999))
    is_eliminated = bool(pilot.get('eliminado', False) if is_dict else getattr(pilot, 'eliminado', False))

    contract_years_left = int(pilot.get('anos_contrato', 2) if is_dict else getattr(pilot, 'anos_contrato', 2))
    is_in_contract_year = contract_years_left <= 1

    # Lesão
    has_injury = bool(pilot.get('lesionado', False) if is_dict else getattr(pilot, 'lesionado', False))
    injury_severity = float(pilot.get('severidade_lesao', 0.0) if is_dict else getattr(pilot, 'severidade_lesao', 0.0))
    injury_races_left = int(pilot.get('corridas_lesao', 0) if is_dict else getattr(pilot, 'corridas_lesao', 0))

    rival_ids = pilot.get('rivais', []) if is_dict else getattr(pilot, 'rivais', [])

    is_rookie = races_in_category < 5 or seasons_in_category == 0
    is_veteran = seasons_in_category >= 5

    return PilotContext(
        pilot_id=pilot_id,
        races_in_category=races_in_category,
        seasons_in_category=seasons_in_category,
        times_at_track=times_at_track,
        best_result_at_track=best_result_at_track,
        last_5_results=last_5_results,
        last_5_expected=last_5_expected,
        dnf_in_last_race=dnf_in_last_race,
        dnf_was_collision=dnf_was_collision,
        championship_position=championship_position,
        points_to_leader=points_to_leader,
        is_eliminated=is_eliminated,
        contract_years_left=contract_years_left,
        is_in_contract_year=is_in_contract_year,
        has_injury=has_injury,
        injury_severity=injury_severity,
        injury_races_left=injury_races_left,
        rival_ids=rival_ids,
        is_rookie=is_rookie,
        is_veteran=is_veteran
    )


def build_race_context(
    category_id: str,
    track_id: int,
    track_name: str,
    round_number: int,
    total_rounds: int,
    championship_data: Any = None,
    weather_data: Any = None
) -> RaceContext:
    """
    Constrói RaceContext a partir dos dados da corrida.
    """
    # Car ID
    car_id = get_car_id_for_category(category_id)

    # Clima (fallback mock)
    is_wet = False
    rain_intensity = 0.0
    if weather_data:
        # Se for string (ex: 'WET', 'HEAVY_RAIN')
        if isinstance(weather_data, str):
            is_wet = weather_data in ["DAMP", "WET", "HEAVY_RAIN"]
            if weather_data == "DAMP": rain_intensity = 0.3
            elif weather_data == "WET": rain_intensity = 0.6
            elif weather_data == "HEAVY_RAIN": rain_intensity = 1.0
        # Se for o objeto interno WeatherCondition do modulo 4
        else:
            is_wet = getattr(weather_data, 'name', '') in ("WET", "DAMP", "HEAVY_RAIN")
            if getattr(weather_data, 'name', '') == "HEAVY_RAIN": rain_intensity = 1.0
            elif is_wet: rain_intensity = 0.6

    is_championship_deciding = (round_number == total_rounds)
    championship_standings = {}
    points_gap_to_leader = {}

    if championship_data:
        championship_standings = getattr(championship_data, 'standings', {})
        points_gap_to_leader = getattr(championship_data, 'gaps', {})

    active_rivalries = []
    if championship_data and hasattr(championship_data, 'rivalries'):
        active_rivalries = championship_data.rivalries

    home_race_pilots = []

    return RaceContext(
        category_id=category_id,
        category_name=category_id.upper(), # Apenas pra log
        category_tier=1,
        track_id=track_id,
        track_name=track_name,
        round_number=round_number,
        total_rounds=total_rounds,
        car_id=car_id,
        is_wet=is_wet,
        rain_intensity=rain_intensity,
        is_championship_deciding=is_championship_deciding,
        championship_standings=championship_standings,
        points_gap_to_leader=points_gap_to_leader,
        active_rivalries=active_rivalries,
        home_race_pilots=home_race_pilots
    )


def prepare_roster_data(
    pilots: list,
    category_id: str,
    track_id: int,
    track_name: str,
    round_number: int,
    total_rounds: int,
    car_numbers: dict = None,
    liveries: dict = None,
    championship_data: Any = None,
    weather_data: Any = None,
    season_data: Any = None
) -> dict:
    """
    Prepara todos os dados necessários para o roster.
    Retorna o dicionário usado pelo exportador existente.
    """
    race_ctx = build_race_context(
        category_id=category_id,
        track_id=track_id,
        track_name=track_name,
        round_number=round_number,
        total_rounds=total_rounds,
        championship_data=championship_data,
        weather_data=weather_data
    )

    pilots_data = []
    modifier_reports = []

    # Map pilots
    pilot_ids_in_race = [str(p.get('id')) if isinstance(p, dict) else str(getattr(p, 'id')) for p in pilots]

    for pilot in pilots:
        pilot_id = str(pilot.get('id') if isinstance(pilot, dict) else getattr(pilot, 'id'))
        pilot_ctx = build_pilot_context(
            pilot=pilot,
            season_data=season_data,
            track_id=track_id
        )

        # Atualiza rivais na grid e flags de casa
        pilot_ctx.rivals_in_race = [r for r in pilot_ctx.rival_ids if r in pilot_ids_in_race]
        pilot_ctx.is_home_race = pilot_id in race_ctx.home_race_pilots

        car_number = (car_numbers or {}).get(pilot_id, getattr(pilot, "numero", pilot.get("numero", "0") if isinstance(pilot, dict) else "0"))
        livery = (liveries or {}).get(pilot_id, {})

        # Default a 0
        races_this_season = int(pilot.get('corridas_temporada', round_number - 1)) if isinstance(pilot, dict) else getattr(pilot, 'corridas_temporada', round_number - 1)

        export_data = export_pilot_data(
            pilot=pilot,
            pilot_ctx=pilot_ctx,
            race_ctx=race_ctx,
            car_number=str(car_number),
            livery=livery,
            races_this_season=races_this_season
        )

        pilots_data.append(export_data.to_iracing_format())

        if export_data.modifier_report:
            modifier_reports.append(export_data.modifier_report)

    skills = [p["skill"] for p in pilots_data]
    min_skill = min(skills) if skills else 40
    max_skill = max(skills) if skills else 100

    roster_name = f"{category_id.upper()} - Round {round_number}"

    car_id = race_ctx.car_id
    car_name = get_car_name(car_id)

    return {
        "roster_name": roster_name,
        "car_id": car_id,
        "car_name": car_name,
        "min_skill": min_skill,
        "max_skill": max_skill,
        "max_drivers": len(pilots_data),
        "track_id": track_id,
        "track_name": track_name,
        "round_number": round_number,
        "is_wet": race_ctx.is_wet,
        "pilots": pilots_data,
        "modifier_reports": modifier_reports
    }


def get_iracing_roster_path() -> str:
    """
    Retorna o caminho padrão da pasta de AI Seasons do iRacing.
    """
    import os

    documents = os.path.expanduser("~/Documents")
    iracing_path = os.path.join(documents, "iRacing", "airosters")

    if os.path.exists(iracing_path):
        return iracing_path

    alt_path = os.path.join(os.path.expanduser("~"), "Documents", "iRacing", "airosters")
    if os.path.exists(alt_path):
        return alt_path

    alt_path_pt = os.path.join(os.path.expanduser("~"), "Documentos", "iRacing", "airosters")
    if os.path.exists(alt_path_pt):
        return alt_path_pt

    return ""
