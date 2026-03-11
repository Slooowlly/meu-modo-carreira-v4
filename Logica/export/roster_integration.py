# Logica/export/roster_integration.py
"""
Integration helpers between existing roster export flow and Module 5 logic.
"""

from __future__ import annotations

from typing import Any

from .models import PilotContext, RaceContext
from .exporter import export_pilot_data
from .car_ids import get_car_id_for_category, get_car_name


def _get(obj: Any, key: str, default=None):
    """Read key from dict or attribute from object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_rival_ids(rivalidades: Any) -> list[str]:
    """Normalize rivalries into a list of rival pilot IDs as strings."""
    if not isinstance(rivalidades, list):
        return []

    rival_ids: list[str] = []
    for rivalidade in rivalidades:
        if isinstance(rivalidade, dict):
            rival_id = rivalidade.get("rival_id", rivalidade.get("piloto_id"))
        else:
            rival_id = rivalidade
        if rival_id in (None, ""):
            continue
        rival_ids.append(str(rival_id))

    return rival_ids


def _normalizar_clima(weather_data: Any) -> str | None:
    """
    Convert weather input to one of:
    - None (dry)
    - DAMP
    - WET
    - HEAVY_RAIN
    """
    if weather_data in (None, "", "-", "Seco", "Dry"):
        return None

    if isinstance(weather_data, dict):
        if weather_data.get("chuva") is not True:
            return None
        intensidade = str(weather_data.get("intensidade", "")).strip().lower()
        if intensidade in {"leve", "light", "damp"}:
            return "DAMP"
        if intensidade in {"moderada", "moderat", "wet"}:
            return "WET"
        if intensidade in {"forte", "heavy", "heavy_rain", "tempestade", "storm"}:
            return "HEAVY_RAIN"
        return "WET"

    if hasattr(weather_data, "name"):
        weather_data = getattr(weather_data, "name")

    text = str(weather_data or "").strip().casefold()
    clima_map = {
        "damp": "DAMP",
        "wet": "WET",
        "heavy_rain": "HEAVY_RAIN",
        "heavy rain": "HEAVY_RAIN",
        "seco": None,
        "nublado": None,
        "chuva leve": "DAMP",
        "chuva": "WET",
        "chuva moderada": "WET",
        "chuva forte": "HEAVY_RAIN",
        "tempestade": "HEAVY_RAIN",
    }
    if text in clima_map:
        return clima_map[text]

    text_up = str(weather_data or "").strip().upper()
    if text_up in {"DAMP", "WET", "HEAVY_RAIN"}:
        return text_up
    return None


def calculate_pilot_for_export(
    pilot: Any,
    pilot_ctx: PilotContext,
    race_ctx: RaceContext,
    car_number: str = "0",
    livery: dict | None = None,
    races_this_season: int = 0,
) -> dict:
    """Calculate final values for one pilot and return iRacing attribute payload."""
    data = export_pilot_data(
        pilot=pilot,
        pilot_ctx=pilot_ctx,
        race_ctx=race_ctx,
        car_number=car_number,
        livery=livery,
        races_this_season=races_this_season,
    )
    return data.to_iracing_format()


def build_pilot_context(
    pilot: Any,
    season_data: Any = None,
    track_id: int = 0,
) -> PilotContext:
    """
    Build PilotContext from canonical M1 pilot fields.

    Canonical source fields:
    - corridas_na_categoria
    - temporadas_na_categoria
    - historico_circuitos
    - resultados_temporada
    - contrato_anos
    - lesao
    - rivalidades
    - corridas_temporada
    """
    pilot_id = str(_get(pilot, "id", str(id(pilot))))

    standings_by_id = {}
    expected_position_by_id = {}
    rivals_in_race_by_id = {}
    home_race_pilots = set()

    if isinstance(season_data, dict):
        standings_by_id = season_data.get("standings_by_id", {}) or {}
        expected_position_by_id = season_data.get("expected_position_by_id", {}) or {}
        rivals_in_race_by_id = season_data.get("rivals_in_race_by_id", {}) or {}
        home_race_pilots = set(str(pid) for pid in season_data.get("home_race_pilots", []) or [])

    corridas_na_categoria = _to_int(_get(pilot, "corridas_na_categoria", 0), 0)
    temporadas_na_categoria = _to_int(
        _get(pilot, "temporadas_na_categoria", max(0, corridas_na_categoria // 12)),
        max(0, corridas_na_categoria // 12),
    )

    historico_circuitos = _get(pilot, "historico_circuitos", {})
    times_at_track = 0
    best_result_at_track = 99
    if isinstance(historico_circuitos, dict):
        key_candidates = [track_id, str(track_id)]
        track_data = None
        for key in key_candidates:
            if key in historico_circuitos:
                track_data = historico_circuitos[key]
                break
        if isinstance(track_data, dict):
            times_at_track = _to_int(track_data.get("corridas", track_data.get("times", 0)), 0)
            best_result_at_track = _to_int(
                track_data.get("melhor_resultado", track_data.get("best", 99)),
                99,
            )

    resultados = _get(pilot, "resultados_temporada", [])
    if not isinstance(resultados, list):
        resultados = []
    last_5_results = [r for r in resultados[-5:] if isinstance(r, int)]

    expected_position = _to_int(expected_position_by_id.get(pilot_id), 0)
    if expected_position > 0:
        last_5_expected = [expected_position] * len(last_5_results)
    else:
        historico_expectativas = _get(pilot, "historico_expectativas", [])
        if isinstance(historico_expectativas, list) and historico_expectativas:
            last_5_expected = [
                _to_int(valor, 10) for valor in historico_expectativas[-5:] if isinstance(valor, (int, float))
            ]
            if len(last_5_expected) < len(last_5_results):
                last_5_expected += [10] * (len(last_5_results) - len(last_5_expected))
        else:
            fallback_pos = _to_int(_get(pilot, "posicao_campeonato", 10), 10)
            if fallback_pos <= 0:
                fallback_pos = 10
            last_5_expected = [fallback_pos] * len(last_5_results)

    dnf_in_last_race = bool(resultados) and str(resultados[-1]).upper() == "DNF"
    dnf_was_collision = bool(_get(pilot, "dnf_colisao", False))

    standing_entry = standings_by_id.get(pilot_id, {}) if isinstance(standings_by_id, dict) else {}
    championship_position = _to_int(
        standing_entry.get("position", _get(pilot, "posicao_campeonato", 0)),
        0,
    )
    points_to_leader = _to_int(
        standing_entry.get(
            "gap_to_leader",
            _get(pilot, "pontos_para_lider", _get(pilot, "diferenca_para_lider", 999)),
        ),
        999,
    )
    is_eliminated = bool(
        standing_entry.get("is_eliminated", _get(pilot, "eliminado", _get(pilot, "is_eliminated", False)))
    )

    contract_years_left = _to_int(_get(pilot, "contrato_anos", 2), 2)
    is_in_contract_year = contract_years_left <= 1

    has_injury = bool(_get(pilot, "lesionado", False))
    injury_severity = _to_float(_get(pilot, "severidade_lesao", 0.0), 0.0)
    injury_races_left = _to_int(_get(pilot, "corridas_lesao", 0), 0)

    lesao = _get(pilot, "lesao", None)
    if isinstance(lesao, dict):
        corridas_lesao = _to_int(lesao.get("corridas_restantes", 0), 0)
        modifier = _to_float(lesao.get("modifier", 0.0), 0.0)
        if corridas_lesao > 0:
            has_injury = True
            injury_races_left = max(injury_races_left, corridas_lesao)
            if modifier < 0:
                injury_severity = max(injury_severity, -modifier)
            elif 0 < modifier <= 1:
                # Legacy format where 0.88 means -12%
                injury_severity = max(injury_severity, 1.0 - modifier)

    rivalidades = _get(pilot, "rivalidades", [])
    rival_ids = _extract_rival_ids(rivalidades)
    rivals_in_race = [
        str(rid) for rid in (rivals_in_race_by_id.get(pilot_id, []) if isinstance(rivals_in_race_by_id, dict) else [])
    ]

    is_home_race = bool(_get(pilot, "is_home_race", False)) or pilot_id in home_race_pilots
    is_rookie = corridas_na_categoria < 10 or temporadas_na_categoria <= 0
    is_veteran = corridas_na_categoria >= 50 or temporadas_na_categoria >= 5

    team_performance_vs_expectations = _to_float(
        standing_entry.get("team_performance_vs_expectations", _get(pilot, "team_performance_vs_expectations", 1.0)),
        1.0,
    )
    if team_performance_vs_expectations == 1.0 and last_5_results and last_5_expected:
        ratios = []
        for result, expected in zip(last_5_results, last_5_expected):
            if result <= 0 or expected <= 0:
                continue
            ratios.append(expected / result)
        if ratios:
            team_performance_vs_expectations = sum(ratios) / len(ratios)
            team_performance_vs_expectations = max(0.4, min(1.6, team_performance_vs_expectations))

    return PilotContext(
        pilot_id=pilot_id,
        races_in_category=corridas_na_categoria,
        seasons_in_category=temporadas_na_categoria,
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
        team_performance_vs_expectations=team_performance_vs_expectations,
        has_injury=has_injury,
        injury_severity=injury_severity,
        injury_races_left=injury_races_left,
        rival_ids=rival_ids,
        rivals_in_race=rivals_in_race,
        is_home_race=is_home_race,
        is_rookie=is_rookie,
        is_veteran=is_veteran,
    )


def build_race_context(
    category_id: str,
    track_id: int,
    track_name: str,
    round_number: int,
    total_rounds: int,
    championship_data: Any = None,
    weather_data: Any = None,
) -> RaceContext:
    """Build RaceContext from race payload."""
    car_id = get_car_id_for_category(category_id)

    weather_tag = _normalizar_clima(weather_data)
    is_wet = weather_tag is not None
    if weather_tag == "DAMP":
        rain_intensity = 0.3
    elif weather_tag == "WET":
        rain_intensity = 0.6
    elif weather_tag == "HEAVY_RAIN":
        rain_intensity = 1.0
    else:
        rain_intensity = 0.0

    championship_standings = {}
    points_gap_to_leader = {}
    active_rivalries: list[tuple[str, str, int]] = []
    home_race_pilots: list[str] = []

    if isinstance(championship_data, dict):
        championship_standings = championship_data.get("standings", championship_data.get("championship_standings", {})) or {}
        points_gap_to_leader = championship_data.get("gaps", championship_data.get("points_gap_to_leader", {})) or {}
        active_rivalries = championship_data.get("rivalries", championship_data.get("active_rivalries", [])) or []
        home_race_pilots = [str(pid) for pid in championship_data.get("home_race_pilots", []) or []]
    elif championship_data is not None:
        championship_standings = getattr(championship_data, "standings", {})
        points_gap_to_leader = getattr(championship_data, "gaps", {})
        active_rivalries = getattr(championship_data, "rivalries", [])
        home_race_pilots = [str(pid) for pid in getattr(championship_data, "home_race_pilots", [])]

    return RaceContext(
        category_id=category_id,
        category_name=category_id.upper(),
        category_tier=1,
        track_id=track_id,
        track_name=track_name,
        round_number=round_number,
        total_rounds=total_rounds,
        car_id=car_id,
        is_wet=is_wet,
        rain_intensity=rain_intensity,
        is_championship_deciding=(round_number == total_rounds),
        championship_standings=championship_standings,
        points_gap_to_leader=points_gap_to_leader,
        active_rivalries=active_rivalries,
        home_race_pilots=home_race_pilots,
    )


def prepare_roster_data(
    pilots: list,
    category_id: str,
    track_id: int,
    track_name: str,
    round_number: int,
    total_rounds: int,
    car_numbers: dict | None = None,
    liveries: dict | None = None,
    championship_data: Any = None,
    weather_data: Any = None,
    season_data: Any = None,
) -> dict:
    """
    Prepare all export data for roster generation.
    """
    race_ctx = build_race_context(
        category_id=category_id,
        track_id=track_id,
        track_name=track_name,
        round_number=round_number,
        total_rounds=total_rounds,
        championship_data=championship_data,
        weather_data=weather_data,
    )

    pilots_data = []
    modifier_reports = []

    for pilot in pilots:
        pilot_id = str(_get(pilot, "id"))
        pilot_ctx = build_pilot_context(
            pilot=pilot,
            season_data=season_data,
            track_id=track_id,
        )

        car_number = (
            (car_numbers or {}).get(pilot_id, _get(pilot, "numero", "0"))
            if isinstance(car_numbers, dict)
            else _get(pilot, "numero", "0")
        )
        livery = (liveries or {}).get(pilot_id, {}) if isinstance(liveries, dict) else {}
        races_this_season = _to_int(_get(pilot, "corridas_temporada", 0), 0)

        export_data = export_pilot_data(
            pilot=pilot,
            pilot_ctx=pilot_ctx,
            race_ctx=race_ctx,
            car_number=str(car_number),
            livery=livery,
            races_this_season=races_this_season,
        )

        pilots_data.append(export_data.to_iracing_format())
        if export_data.modifier_report:
            modifier_reports.append(export_data.modifier_report)

    skills = [p["skill"] for p in pilots_data]
    min_skill = min(skills) if skills else 40
    max_skill = max(skills) if skills else 100
    car_name = get_car_name(race_ctx.car_id)

    return {
        "roster_name": f"{category_id.upper()} - Round {round_number}",
        "car_id": race_ctx.car_id,
        "car_name": car_name,
        "min_skill": min_skill,
        "max_skill": max_skill,
        "max_drivers": len(pilots_data),
        "track_id": track_id,
        "track_name": track_name,
        "round_number": round_number,
        "is_wet": race_ctx.is_wet,
        "pilots": pilots_data,
        "modifier_reports": modifier_reports,
    }


def get_iracing_roster_path() -> str:
    """Return default iRacing airosters path."""
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
