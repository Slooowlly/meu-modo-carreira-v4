from __future__ import annotations

import copy
import json
import os
import random
import re
import uuid
from datetime import datetime

from Dados.config import definir_season_atual, obter_pasta_aiseasons
from Dados.constantes import CAR_INFO, NOMES_CAMPEONATO, PISTAS_IRACING
from Utils.helpers import obter_nome_categoria, normalizar_int_positivo as _normalizar_int_positivo

_SUBSESSOES_PADRAO = [6]
_TRACK_STATE_PADRAO = {
    "leave_marbles": True,
    "practice_rubber": -1,
    "qualify_rubber": -1,
    "race_rubber": -1,
    "warmup_rubber": -1,
}
_OVAL_TRACK_IDS = {556}
_UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

_CATEGORY_PRESETS = {
    "mx5": {
        "nome": "Mazda MX-5 Cup - {ANO}",
        "car_id": 67,
        "aiCarClassId": 74,
        "category_id": 2,
        "race_length": 15,
        "max_drivers": 20,
        "etapas": 3,
        "pontuacao": "mx5cup",
        "calendario": [
            {"etapa": 1, "trackId": 47, "nome": "Laguna Seca"},
            {"etapa": 2, "trackId": 465, "nome": "VIR Full Course"},
            {"etapa": 3, "trackId": 353, "nome": "Lime Rock Park GP"},
        ],
    },
    "toyotagr86": {
        "nome": "Toyota GR86 Cup - {ANO}",
        "car_id": 160,
        "aiCarClassId": 4012,
        "category_id": 2,
        "race_length": 20,
        "max_drivers": 20,
        "etapas": 6,
        "pontuacao": "fia",
        "calendario": [
            {"etapa": 1, "trackId": 324, "nome": "Tsukuba"},
            {"etapa": 2, "trackId": 166, "nome": "Okayama"},
            {"etapa": 3, "trackId": 180, "nome": "Oulton Park"},
            {"etapa": 4, "trackId": 297, "nome": "Snetterton"},
            {"etapa": 5, "trackId": 439, "nome": "Winton"},
            {"etapa": 6, "trackId": 202, "nome": "Oran Park"},
        ],
    },
    "bmwm2cs": {
        "nome": "BMW M2 CS Racing Cup - {ANO}",
        "car_id": 195,
        "aiCarClassId": 4005,
        "category_id": 2,
        "race_length": 20,
        "max_drivers": 20,
        "etapas": 6,
        "pontuacao": "fia",
        "calendario": [
            {"etapa": 1, "trackId": 449, "nome": "Oschersleben"},
            {"etapa": 2, "trackId": 489, "nome": "Ledenon"},
            {"etapa": 3, "trackId": 515, "nome": "Navarra"},
            {"etapa": 4, "trackId": 180, "nome": "Oulton Park"},
            {"etapa": 5, "trackId": 297, "nome": "Snetterton"},
            {"etapa": 6, "trackId": 451, "nome": "Rudskogen"},
        ],
    },
}

_CATEGORY_PRESET_ALIASES = {
    "mazda_rookie": "mx5",
    "mazda_amador": "mx5",
    "toyota_rookie": "toyotagr86",
    "toyota_amador": "toyotagr86",
    "bmw_m2": "bmwm2cs",
    "production_challenger": "bmwm2cs",
}

for alias_id, base_id in _CATEGORY_PRESET_ALIASES.items():
    if alias_id in _CATEGORY_PRESETS:
        continue
    base_preset = _CATEGORY_PRESETS.get(base_id)
    if isinstance(base_preset, dict):
        _CATEGORY_PRESETS[alias_id] = copy.deepcopy(base_preset)

_POINTS_TABLES = {
    "mx5cup": {
        1: 35,
        2: 32,
        3: 30,
        4: 28,
        5: 26,
        6: 25,
        7: 24,
        8: 23,
        9: 22,
        10: 21,
        11: 20,
        12: 19,
        13: 18,
        14: 17,
        15: 16,
        16: 15,
        17: 14,
        18: 13,
        19: 12,
        20: 11,
    },
    "fia": {
        1: 25,
        2: 18,
        3: 15,
        4: 12,
        5: 10,
        6: 8,
        7: 6,
        8: 4,
        9: 2,
        10: 1,
    },
}

_DATAS_POR_PISTA = {
    47: {"mes": 9, "hora": 10, "minuto": 0},
    465: {"mes": 8, "hora": 9, "minuto": 0},
    353: {"mes": 7, "hora": 9, "minuto": 30},
    324: {"mes": 5, "hora": 10, "minuto": 0},
    166: {"mes": 4, "hora": 10, "minuto": 0},
    180: {"mes": 6, "hora": 11, "minuto": 0},
    297: {"mes": 7, "hora": 10, "minuto": 30},
    439: {"mes": 3, "hora": 10, "minuto": 0},
    202: {"mes": 2, "hora": 9, "minuto": 0},
    449: {"mes": 6, "hora": 10, "minuto": 0},
    489: {"mes": 7, "hora": 10, "minuto": 0},
    515: {"mes": 8, "hora": 9, "minuto": 30},
    451: {"mes": 6, "hora": 11, "minuto": 0},
}

_CATEGORY_ID_POR_CATEGORIA = {
    "mx5": 2,
    "toyotagr86": 2,
    "bmwm2cs": 2,
    "mazda_rookie": 2,
    "mazda_amador": 2,
    "toyota_rookie": 2,
    "toyota_amador": 2,
    "bmw_m2": 2,
    "production_challenger": 2,
    "gt4": 5,
    "gt3": 5,
    "endurance": 5,
}

_TRACK_IDS_COMPATIVEIS: list[int] = []
for pista in PISTAS_IRACING:
    try:
        track_id = int(pista.get("trackId"))
    except (TypeError, ValueError, AttributeError):
        continue
    if track_id not in _TRACK_IDS_COMPATIVEIS:
        _TRACK_IDS_COMPATIVEIS.append(track_id)


def categoria_tem_calendario_predefinido(categoria_id: str) -> bool:
    return str(categoria_id or "").strip() in _CATEGORY_PRESETS


def obter_calendario_predefinido(categoria_id: str) -> list[dict]:
    """
    Retorna o calendario predefinido da categoria em formato amigavel para UI.
    """
    categoria = str(categoria_id or "").strip()
    preset = _CATEGORY_PRESETS.get(categoria, {})
    calendario = preset.get("calendario", [])

    saida = []
    for indice, item in enumerate(calendario, start=1):
        if not isinstance(item, dict):
            continue

        track_id = _normalizar_int_positivo(item.get("trackId"))
        if track_id is None:
            continue

        nome_pista = str(item.get("nome", f"Track ID {track_id}") or "").strip()
        if not nome_pista:
            nome_pista = f"Track ID {track_id}"

        saida.append(
            {
                "etapa": indice,
                "trackId": track_id,
                "nome": nome_pista,
            }
        )

    return saida


def obter_total_etapas_predefinido(categoria_id: str) -> int | None:
    """Retorna o total de etapas do preset da categoria, quando existir."""
    calendario = obter_calendario_predefinido(categoria_id)
    return len(calendario) if calendario else None





def _resolver_nome_visivel_categoria(categoria_id: str) -> str:
    nome = NOMES_CAMPEONATO.get(categoria_id)
    if nome:
        return str(nome)

    nome = obter_nome_categoria(categoria_id)
    if nome:
        return str(nome)

    return str(categoria_id).upper()


def _resolver_max_drivers(banco: dict, categoria_id: str, preset: dict | None) -> int:
    if preset:
        return max(1, min(int(preset.get("max_drivers", 20)), 63))

    maximos = banco.get("max_drivers_por_categoria", {})
    if isinstance(maximos, dict):
        max_categoria = _normalizar_int_positivo(maximos.get(categoria_id))
        if max_categoria is not None:
            return max(1, min(max_categoria, 63))

    total = _normalizar_int_positivo(banco.get("pilotos_por_categoria"))
    if total is not None:
        return max(1, min(total, 63))

    return 20


def _resolver_race_length(preset: dict | None) -> int:
    if preset:
        return max(1, int(preset.get("race_length", 20)))
    return 20


def _resolver_faixa_skill() -> tuple[int, int]:
    return 50, 70


def _resolver_category_id(categoria_id: str, preset: dict | None) -> int:
    if preset:
        return int(preset.get("category_id", 2))
    return int(_CATEGORY_ID_POR_CATEGORIA.get(categoria_id, 2))


def _resolver_carro(categoria_id: str, preset: dict | None, banco: dict) -> tuple[int, int]:
    info = CAR_INFO.get(categoria_id, {})
    car_id_info = int(info.get("carId", 0) or 0)
    ai_class_info = int(info.get("carClassId", 0) or 0)

    if preset:
        car_id = int(preset.get("car_id", car_id_info))
        ai_class = int(preset.get("aiCarClassId", ai_class_info))
        return car_id, ai_class

    if categoria_id in {"gt3", "gt4"} and isinstance(banco, dict):
        configs = banco.get("carro_jogador_por_categoria", {})
        if isinstance(configs, dict):
            config_categoria = configs.get(categoria_id)
            if isinstance(config_categoria, dict):
                try:
                    car_id = int(config_categoria.get("carId", 0) or 0)
                    ai_class = int(config_categoria.get("carClassId", 0) or 0)
                except (TypeError, ValueError):
                    car_id = 0
                    ai_class = 0
                if car_id > 0 and ai_class > 0:
                    return car_id, ai_class

    return car_id_info, ai_class_info


def _resolver_pontuacao_nome(preset: dict | None) -> str:
    if not preset:
        return "fia"
    nome = str(preset.get("pontuacao", "fia")).strip().casefold()
    return nome if nome in _POINTS_TABLES else "fia"


def _sanitizar_nome_arquivo(nome: str) -> str:
    texto = str(nome or "").strip()
    texto = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip().rstrip(". ")
    return texto or "AI Season"


def _resolver_pace_car(track_id: int) -> dict:
    is_oval = track_id in _OVAL_TRACK_IDS
    return {
        "category_id": 1 if is_oval else 2,
        "car_id": 90,
        "is_oval": is_oval,
        "is_dirt": False,
        "car_name": "Pace Car - Truck",
        "car_class_id": 11,
        "order": 3 if is_oval else 5,
    }


def _gerar_custom_points(tabela_nome: str) -> list[dict]:
    tabela = _POINTS_TABLES.get(tabela_nome, _POINTS_TABLES["fia"])
    pontos = []
    for posicao in range(1, 61):
        pontos.append(
            {
                "position": posicao,
                "points": int(tabela.get(posicao, 0)),
            }
        )
    return pontos


def _gerar_data_hora_por_pista(track_id: int, ano: int, rng: random.Random) -> str:
    dados = _DATAS_POR_PISTA.get(track_id, {"mes": 6, "hora": 10, "minuto": 0})
    dia = rng.randint(1, 28)
    minuto = int(dados["minuto"]) + int(rng.choice([0, 15, -15]))
    minuto = max(0, min(59, minuto))

    return (
        f"{ano:04d}-{int(dados['mes']):02d}-{dia:02d}"
        f"T{int(dados['hora']):02d}:{minuto:02d}:00"
    )


def _gerar_weather_realista(track_id: int, ano: int, rng: random.Random) -> dict:
    return {
        "type": 0,
        "temp_units": 1,
        "temp_value": 22,
        "rel_humidity": 55,
        "fog": 0,
        "wind_dir": 180,
        "wind_units": 1,
        "wind_value": 8,
        "skies": 1,
        "simulated_start_time": _gerar_data_hora_por_pista(track_id, ano, rng),
        "simulated_time_multiplier": 1,
        "simulated_time_offsets": [15],
        "version": 2,
        "weather_var_initial": 0,
        "weather_var_ongoing": 0,
        "time_of_day": 4,
        "track_water": 0,
    }


def _extrair_calendario_predefinido(categoria_id: str) -> list[dict]:
    return [
        {"trackId": item["trackId"]}
        for item in obter_calendario_predefinido(categoria_id)
    ]


def _reconstruir_resultados_evento(banco: dict, categoria_id: str, indice_rodada: int) -> dict | None:
    """
    Reconstrói um bloco de 'results' do iRacing para uma corrida que já aconteceu,
    baseando-se no array de 'resultados_temporada' de cada piloto no banco local.
    """
    pilotos = banco.get("pilotos", [])
    resultados_simulados = []

    for p in pilotos:
        if p.get("categoria_atual") != categoria_id:
            continue
        
        hist = p.get("resultados_temporada", [])
        if indice_rodada >= len(hist):
            continue  # Piloto não correu nesta rodada
            
        pos = hist[indice_rodada]
        is_dnf = False
        finish_pos = 999
        
        if isinstance(pos, int):
            finish_pos = pos - 1  # iRacing é 0-indexed
        elif isinstance(pos, str) and pos.upper() == "DNF":
            is_dnf = True
            finish_pos = 999
        else:
            continue
            
        cust_id = int(str(p.get("id", "0")).replace("-", "")[:8], 16) % 100000 if "id" in p else 0
        
        resultados_simulados.append({
            "cust_id": cust_id,
            "display_name": p.get("nome", "Piloto Desconhecido"),
            "finish_position_in_class": finish_pos,
            "incidents": 4 if is_dnf else 0,
            "reason_out": "Accident" if is_dnf else "Running"
        })

    if not resultados_simulados:
        return None

    resultados_simulados.sort(key=lambda x: int(str(x["finish_position_in_class"])))
    
    # Corrigir posições dos DNFs para o fim do grid
    dnf_start = len([r for r in resultados_simulados if int(str(r["finish_position_in_class"])) < 999])
    for i, r in enumerate(resultados_simulados):
        if int(str(r["finish_position_in_class"])) == 999:
            r["finish_position_in_class"] = dnf_start
            dnf_start += 1

    return {
        "session_results": [
            {
                "simsession_type_name": "Race",
                "results": resultados_simulados
            }
        ]
    }


def _validar_e_montar_eventos(calendario: list, banco: dict | None = None, categoria_id: str | None = None) -> tuple[list[dict] | None, str | None]:
    eventos: list[dict] = []

    for indice, corrida in enumerate(calendario, start=1):
        if not isinstance(corrida, dict):
            return None, f"Calendario invalido: a corrida {indice} nao possui dados validos."

        track_id = _normalizar_int_positivo(corrida.get("trackId"))
        if track_id is None:
            return None, f"Calendario invalido: a corrida {indice} nao possui trackId."

        if track_id not in _TRACK_IDS_COMPATIVEIS:
            return (
                None,
                f"Calendario invalido: trackId {track_id} da corrida {indice} nao esta na lista de pistas gratuitas.",
            )

        event_id = str(uuid.uuid4())
        if not _UUID_REGEX.fullmatch(event_id):
            return None, f"Falha ao gerar UUID valido para a corrida {indice}."
            
        evento_obj = {
            "trackId": track_id,
            "num_opt_laps": 0,
            "paceCar": _resolver_pace_car(track_id),
            "short_parade_lap": False,
            "must_use_diff_tire_types_in_race": False,
            "subsessions": list(_SUBSESSOES_PADRAO),
            "eventId": event_id,
        }
        
        # Injetar resultados simulados se disponíveis
        if banco and categoria_id:
            try:
                rodada_atual = int(str(banco.get("rodada_atual", 1)))
            except (ValueError, TypeError):
                rodada_atual = 1
                
            indice_rodada = indice - 1  # 0-indexed
            if indice_rodada < rodada_atual - 1:
                # Esta corrida já está no passado
                results_block = _reconstruir_resultados_evento(banco, categoria_id, indice_rodada)
                if results_block:
                    evento_obj["results"] = results_block

        eventos.append(evento_obj)

    return eventos, None


def _validar_season_gerada(season: dict) -> str | None:
    obrigatorios = [
        "name",
        "carId",
        "aiCarClassId",
        "category_id",
        "race_length_type",
        "race_length",
        "subsessions",
        "events",
        "carSettings",
        "weather",
        "track_state",
    ]

    for campo in obrigatorios:
        if campo not in season:
            return f"Campo obrigatorio ausente: {campo}."

    car_settings = season.get("carSettings", [])
    if not isinstance(car_settings, list) or not car_settings:
        return "carSettings invalido: deve conter pelo menos uma entrada."

    if car_settings[0].get("car_id") != season.get("carId"):
        return "Inconsistencia: carSettings[0].car_id deve ser igual ao carId da raiz."

    min_skill = int(season.get("minSkill", 0))
    max_skill = int(season.get("maxSkill", 0))
    if min_skill < 0 or max_skill > 100 or max_skill < min_skill:
        return "Faixa de skill invalida."

    max_drivers = int(season.get("max_drivers", 0))
    if max_drivers < 1 or max_drivers > 63:
        return "max_drivers fora da faixa valida (1-63)."

    race_length_type = int(season.get("race_length_type", 0))
    race_length = int(season.get("race_length", 0))
    race_laps = int(season.get("race_laps", 0))

    if race_length_type == 2 and race_laps != 0:
        return "race_laps deve ser 0 quando race_length_type for 2."

    if race_length_type == 3 and race_laps != race_length:
        return "race_laps deve ser igual a race_length quando race_length_type for 3."

    if int(season.get("num_fast_tows", 0)) != 0:
        return "num_fast_tows deve ser 0 (reparos rapidos desabilitados)."

    subs_raiz = list(season.get("subsessions", []))
    event_ids: set[str] = set()

    eventos = season.get("events", [])
    if not isinstance(eventos, list) or not eventos:
        return "events invalido: deve conter ao menos um evento."

    for evento in eventos:
        if int(evento.get("trackId", -1)) not in _TRACK_IDS_COMPATIVEIS:
            return "Evento com trackId fora da lista de pistas conhecidas."

        if list(evento.get("subsessions", [])) != subs_raiz:
            return "subsessions do evento deve ser igual ao subsessions da raiz."

        event_id = str(evento.get("eventId", "")).strip()
        if not _UUID_REGEX.fullmatch(event_id):
            return "eventId invalido: formato UUID hexadecimal 8-4-4-4-12 obrigatorio."
        if event_id in event_ids:
            return "eventId duplicado encontrado."
        event_ids.add(event_id)

        pace = evento.get("paceCar", {})
        track_id = int(evento.get("trackId"))
        is_oval = track_id in _OVAL_TRACK_IDS
        esperado_category = 1 if is_oval else 2
        esperado_order = 3 if is_oval else 5

        if int(pace.get("category_id", -1)) != esperado_category:
            return "paceCar.category_id inconsistente com o tipo de pista."
        if bool(pace.get("is_oval", False)) != is_oval:
            return "paceCar.is_oval inconsistente com o tipo de pista."
        if int(pace.get("order", -1)) != esperado_order:
            return "paceCar.order inconsistente com o tipo de pista."

    if int(season.get("points_system_id", 0)) == 2:
        custom_points = season.get("custom_points", [])
        if not isinstance(custom_points, list) or len(custom_points) != 60:
            return "custom_points deve conter exatamente 60 posicoes quando points_system_id = 2."

    weather = season.get("weather", {})
    if int(weather.get("type", -1)) != 0:
        return "weather.type deve ser 0 para clima realista simplificado."

    return None


def gerar_aiseason(banco: dict, categoria_id: str, nome_roster: str) -> dict:
    """Gera arquivo .json de AI Season com presets por categoria e weather simplificado (type=0)."""
    try:
        categoria_id = str(categoria_id or "").strip()
        preset = _CATEGORY_PRESETS.get(categoria_id)

        ano_atual = _normalizar_int_positivo(banco.get("ano_atual")) or datetime.now().year

        if preset:
            calendario = _extrair_calendario_predefinido(categoria_id)
            nome_temporada = str(preset.get("nome", "")).format(ANO=ano_atual)
        else:
            calendario = banco.get("calendario", [])
            nome_temporada = f"{_resolver_nome_visivel_categoria(categoria_id)} - {ano_atual}"

        if not isinstance(calendario, list) or not calendario:
            return {
                "sucesso": False,
                "erro": "Calendario vazio: adicione corridas antes de exportar a AI Season.",
            }

        car_id, ai_car_class_id = _resolver_carro(categoria_id, preset, banco)
        if car_id <= 0 or ai_car_class_id <= 0:
            return {
                "sucesso": False,
                "erro": f"CAR_INFO invalido para a categoria {categoria_id}.",
            }

        pasta_aiseasons = str(obter_pasta_aiseasons() or "").strip()
        if not pasta_aiseasons:
            return {
                "sucesso": False,
                "erro": "Pasta aiseasons nao configurada.",
            }

        os.makedirs(pasta_aiseasons, exist_ok=True)

        eventos, erro_eventos = _validar_e_montar_eventos(calendario, banco=banco, categoria_id=categoria_id)

        if erro_eventos:
            return {"sucesso": False, "erro": erro_eventos}
        if eventos is None:
            return {
                "sucesso": False,
                "erro": "Nao foi possivel montar os eventos do calendario.",
            }

        nome_roster_final = str(nome_roster or "").strip()
        if not nome_roster_final:
            nome_roster_final = nome_temporada

        max_drivers = _resolver_max_drivers(banco, categoria_id, preset)
        min_skill, max_skill = _resolver_faixa_skill()
        race_length = _resolver_race_length(preset)
        tabela_pontos = _resolver_pontuacao_nome(preset)

        primeiro_track_id = int(eventos[0]["trackId"])
        seed_clima = f"{nome_temporada}|{ano_atual}|{categoria_id}|{primeiro_track_id}"
        rng_clima = random.Random(seed_clima)
        weather_raiz = _gerar_weather_realista(primeiro_track_id, ano_atual, rng_clima)

        season = {
            "name": nome_temporada,
            "rosterName": nome_roster_final,
            "car_name": _resolver_nome_visivel_categoria(categoria_id),
            "adaptiveAIEnabled": False,
            "adaptiveAIDifficulty": 0,
            "carId": car_id,
            "aiCarClassId": ai_car_class_id,
            "avoidUser": False,
            "category_id": _resolver_category_id(categoria_id, preset),
            "damage_model": 0,
            "multiclassType": 0,
            "max_drivers": max_drivers,
            "minSkill": min_skill,
            "maxSkill": max_skill,
            "gridPosition": 0,
            "startZone": 0,
            "rolling_starts": False,
            "short_parade_lap": False,
            "restarts": 2,
            "race_length_type": 2,
            "race_length": race_length,
            "race_laps": 0,
            "practice_length": 0,
            "qualify_laps": 0,
            "qualify_length": 10,
            "subsessions": list(_SUBSESSOES_PADRAO),
            "full_course_cautions": True,
            "lucky_dog": True,
            "do_not_count_caution_laps": True,
            "no_lapper_wave_arounds": False,
            "incident_limit": 0,
            "incident_warn_mode": 0,
            "incident_warn_param1": 0,
            "incident_warn_param2": 0,
            "unsport_conduct_rule_mode": 0,
            "max_visor_tearoffs": -1,
            "num_fast_tows": 0,
            "start_on_qual_tire": False,
            "must_use_diff_tire_types_in_race": False,
            "time_of_day": 0,
            "points_system_id": 2,
            "carSettings": [
                {
                    "car_id": car_id,
                    "max_pct_fuel_fill": 100,
                    "max_dry_tire_sets": 0,
                }
            ],
            "track_state": copy.deepcopy(_TRACK_STATE_PADRAO),
            "weather": weather_raiz,
            "events": eventos,
            "event_count": len(eventos),
            "custom_points": _gerar_custom_points(tabela_pontos),
            "official": False,
            "starred": False,
        }

        erro_validacao = _validar_season_gerada(season)
        if erro_validacao:
            return {
                "sucesso": False,
                "erro": f"Falha de validacao da season gerada: {erro_validacao}",
            }

        nome_arquivo = f"{_sanitizar_nome_arquivo(nome_temporada)}.json"
        caminho_arquivo = os.path.normpath(os.path.join(pasta_aiseasons, nome_arquivo))

        with open(caminho_arquivo, "w", encoding="utf-8") as arquivo_saida:
            json.dump(season, arquivo_saida, indent=4, ensure_ascii=False)

        definir_season_atual(categoria_id, caminho_arquivo)

        return {
            "sucesso": True,
            "arquivo": caminho_arquivo,
        }
    except Exception as erro:
        return {
            "sucesso": False,
            "erro": f"Erro ao gerar AI Season: {erro}",
        }
