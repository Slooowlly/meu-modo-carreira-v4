# Logica/export/car_ids.py
"""
IDs oficiais dos carros do iRacing.
Usados para gerar rosters compatíveis com o jogo.

IMPORTANTE: Estes IDs são fixos e definidos pelo iRacing.
Não alterar sem verificar a documentação oficial.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class CarInfo:
    """Informações de um carro do iRacing"""
    car_id: int
    car_path: str
    car_name: str
    car_class: str


IRACING_CARS = {
    67: CarInfo(67, "mx5/mx52016", "Mazda MX-5 Cup (2016)", "MX5"),
    160: CarInfo(160, "toyotagr86", "Toyota GR86", "GR86"),
    162: CarInfo(162, "renaultcliocup", "Renault Clio Cup", "Touring"),
    195: CarInfo(195, "bmwm2csr", "BMW M2 CS Racing", "Touring"),
    189: CarInfo(189, "bmwm4evogt4", "BMW M4 GT4", "GT4"),
    132: CarInfo(132, "bmwm4gt3", "BMW M4 GT3", "GT3"),
    119: CarInfo(119, "porsche718gt4", "Porsche 718 Cayman GT4 Clubsport MR", "GT4"),
    169: CarInfo(169, "porsche992rgt3", "Porsche 911 GT3 R (992)", "GT3"),
    157: CarInfo(157, "mercedesamggt4", "Mercedes-AMG GT4", "GT4"),
    156: CarInfo(156, "mercedesamgevogt3", "Mercedes-AMG GT3 EVO", "GT3"),
    150: CarInfo(150, "amvantagegt4", "Aston Martin Vantage GT4", "GT4"),
    206: CarInfo(206, "amvantageevogt3", "Aston Martin Vantage GT3 EVO", "GT3"),
    135: CarInfo(135, "mclaren570sgt4", "McLaren 570S GT4", "GT4"),
    188: CarInfo(188, "mclaren720sgt3", "McLaren 720S GT3", "GT3"),
    133: CarInfo(133, "lamborghinievogt3", "Lamborghini Huracán GT3 EVO", "GT3"),
    144: CarInfo(144, "ferrarievogt3", "Ferrari 296 GT3", "GT3"),
    204: CarInfo(204, "fordmustanggt4", "Ford Mustang GT4", "GT4"),
    185: CarInfo(185, "fordmustanggt3", "Ford Mustang GT3", "GT3"),
    184: CarInfo(184, "chevyvettez06rgt3", "Chevrolet Corvette Z06 GT3.R", "GT3"),
    176: CarInfo(176, "audir8lmsevo2gt3", "Audi R8 LMS EVO II GT3", "GT3"),
    194: CarInfo(194, "acuransxevo22gt3", "Acura NSX GT3 EVO 22", "GT3"),
}

CATEGORY_TO_CAR_ID = {
    "mazda_rookie": 67,
    "mazda_amador": 67,
    "mazda_mx5_rookie": 67,
    "mazda_championship": 67,
    "mazda_mx5_championship": 67,
    "toyota_rookie": 160,
    "toyota_amador": 160,
    "toyota_gr86": 160,
    "toyota_gr86_cup": 160,
    "production_challenger": 67,
    "production_challenge": 67,
    "touring_challenger": 162,
    "bmw_m2": 195,
    "renault_clio": 162,
    "touring_pro": 195,
    "gt4": 189,
    "gt4_challenge": 189,
    "gt4_pro": 189,
    "porsche_gt4": 119,
    "bmw_gt4": 189,
    "mercedes_gt4": 157,
    "aston_gt4": 150,
    "mclaren_gt4": 135,
    "ford_gt4": 204,
    "gt3": 132,
    "endurance": 132,
    "porsche_cup": 169,
    "porsche_carrera_cup": 169,
    "gt3_challenger": 132,
    "gt3_pro": 132,
    "bmw_gt3": 132,
    "mercedes_gt3": 156,
    "porsche_gt3": 169,
    "ferrari_gt3": 144,
    "lamborghini_gt3": 133,
    "aston_gt3": 206,
    "mclaren_gt3": 188,
    "audi_gt3": 176,
    "ford_gt3": 185,
    "corvette_gt3": 184,
    "acura_gt3": 194,
}


def get_car_info(car_id: int) -> Optional[CarInfo]:
    return IRACING_CARS.get(car_id)


def get_car_id_for_category(category_id: str) -> int:
    return CATEGORY_TO_CAR_ID.get(category_id.lower(), 67)


def get_car_name(car_id: int) -> str:
    car_info = IRACING_CARS.get(car_id)
    return car_info.car_name if car_info else "Unknown Car"


def get_cars_by_class(car_class: str) -> list[CarInfo]:
    return [
        car for car in IRACING_CARS.values()
        if car.car_class.upper() == car_class.upper()
    ]


def get_all_gt3_cars() -> list[CarInfo]:
    return get_cars_by_class("GT3")


def get_all_gt4_cars() -> list[CarInfo]:
    return get_cars_by_class("GT4")


def is_valid_car_id(car_id: int) -> bool:
    return car_id in IRACING_CARS


def validate_car_for_category(car_id: int, category_id: str) -> bool:
    car_info = IRACING_CARS.get(car_id)
    if not car_info:
        return False

    category_lower = category_id.lower()

    if "gt3" in category_lower:
        return car_info.car_class == "GT3"
    elif "gt4" in category_lower:
        return car_info.car_class == "GT4"
    elif "mazda" in category_lower or "mx5" in category_lower:
        return car_id == 67
    elif "toyota" in category_lower or "gr86" in category_lower:
        return car_id == 160
    elif "porsche_cup" in category_lower:
        return car_id == 169

    return True
