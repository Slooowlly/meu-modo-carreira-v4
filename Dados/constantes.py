"""
Constantes do projeto - Modo Carreira iRacing
Todos os valores fixos ficam aqui para fácil manutenção
"""

from pathlib import Path

# ============================================================
# ARQUIVOS
# ============================================================
PASTA_PROJETO = Path(__file__).resolve().parent.parent / 'Projeto'
ARQUIVO_CONFIG = str(PASTA_PROJETO / "config.json")
ARQUIVO_BANCO = str(PASTA_PROJETO / "banco_de_dados_pilotos.json")

# ============================================================
# NOMES E SOBRENOMES PARA GERAÇÃO DE PILOTOS
# ============================================================
POOL_NOMES_NACIONALIDADES = [
    {
        "id": "britanica",
        "rotulo": "🇬🇧 Britânica",
        "peso": 12,
        "nomes_masculinos": [
            "Oliver", "James", "George", "William",
            "Edward", "Henry", "Thomas", "Alexander",
            "Charles", "Benjamin", "Sebastian", "Theodore",
            "Arthur", "Frederick", "Edmund", "Nathaniel",
            "Harrison", "Maxwell", "Callum", "Dominic",
        ],
        "nomes_femininos": [
            "Charlotte", "Victoria", "Eleanor", "Arabella", "Penelope",
        ],
        "sobrenomes": [
            "Crawford", "Bennett", "Harrison", "Mitchell",
            "Ashford", "Whitmore", "Pemberton", "Thornton",
            "Harrington", "Spencer", "Weston", "Holloway",
            "Barrington", "Mercer", "Langley", "Sinclair",
            "Kingsley", "Norwood", "Caldwell", "Palmer",
        ],
    },
    {
        "id": "alema",
        "rotulo": "🇩🇪 Alemã",
        "peso": 10,
        "nomes_masculinos": [
            "Lukas", "Maximilian", "Felix", "Jonas",
            "Niklas", "Florian", "Moritz", "Leon",
            "Tobias", "Julian", "Sebastian", "Matthias",
            "Fabian", "Dominik", "Benedikt", "Lennart",
            "Henrik", "Konstantin", "Valentin", "Philipp",
        ],
        "nomes_femininos": [
            "Lena", "Clara", "Emilia", "Katharina", "Marlene",
        ],
        "sobrenomes": [
            "Hoffmann", "Richter", "Vogel", "Braun",
            "Lehmann", "Krause", "Hartmann", "Bergmann",
            "Kessler", "Roth", "Zimmermann", "Adler",
            "Stein", "Falk", "Werner", "König",
            "Lange", "Sommer", "Engel", "Brandt",
        ],
    },
    {
        "id": "francesa",
        "rotulo": "🇫🇷 Francesa",
        "peso": 8,
        "nomes_masculinos": [
            "Antoine", "Mathieu", "Lucas", "Hugo",
            "Théo", "Maxime", "Alexandre", "Julien",
            "Romain", "Adrien", "Étienne", "Baptiste",
            "Clément", "Raphaël", "Damien", "Aurélien",
            "Tristan", "Quentin", "Sébastien", "Florent",
        ],
        "nomes_femininos": [
            "Camille", "Juliette", "Margaux", "Élodie", "Océane",
        ],
        "sobrenomes": [
            "Beaumont", "Fontaine", "Moreau", "Dubois",
            "Lefèvre", "Girard", "Rousseau", "Blanc",
            "Delacroix", "Renard", "Marchand", "Chevalier",
            "Deschamps", "Boucher", "Mercier", "Garnier",
            "Leroy", "Fournier", "Perrin", "Laurent",
        ],
    },
    {
        "id": "italiana",
        "rotulo": "🇮🇹 Italiana",
        "peso": 8,
        "nomes_masculinos": [
            "Marco", "Alessandro", "Matteo", "Lorenzo",
            "Andrea", "Luca", "Davide", "Riccardo",
            "Filippo", "Simone", "Niccolò", "Gabriele",
            "Federico", "Edoardo", "Tommaso", "Leonardo",
            "Stefano", "Giacomo", "Emanuele", "Vincenzo",
        ],
        "nomes_femininos": [
            "Giulia", "Valentina", "Francesca", "Chiara", "Beatrice",
        ],
        "sobrenomes": [
            "Colombo", "Ferretti", "Rinaldi", "Marchetti",
            "Moretti", "Benedetti", "Fabbri", "Caruso",
            "Rizzi", "Sartori", "Lombardi", "De Luca",
            "Martini", "Bellini", "Romano", "Ricci",
            "Santoro", "Fontana", "Conti", "Gallo",
        ],
    },
    {
        "id": "espanhola",
        "rotulo": "🇪🇸 Espanhola",
        "peso": 6,
        "nomes_masculinos": [
            "Alejandro", "Pablo", "Diego", "Adrián",
            "Javier", "Miguel", "Daniel", "Sergio",
            "Álvaro", "Marcos", "Gonzalo", "Raúl",
            "Iñigo", "Andrés", "Enrique", "Rodrigo",
            "Martín", "Nicolás", "Rubén", "Óscar",
        ],
        "nomes_femininos": [
            "Lucía", "Carmen", "Valentina", "Elena", "Sofía",
        ],
        "sobrenomes": [
            "Delgado", "Vega", "Navarro", "Molina",
            "Serrano", "Mendoza", "Campos", "Aguilar",
            "Castillo", "Romero", "Moreno", "Cortés",
            "Medina", "Ramos", "Fuentes", "Cabrera",
            "León", "Ortega", "Reyes", "Herrera",
        ],
    },
    {
        "id": "brasileira",
        "rotulo": "🇧🇷 Brasileira",
        "peso": 6,
        "nomes_masculinos": [
            "Lucas", "Gustavo", "Rafael", "Henrique",
            "Pedro", "Bruno", "Felipe", "Thiago",
            "Matheus", "Caio", "Gabriel", "Leonardo",
            "Vinicius", "Arthur", "Eduardo", "Bernardo",
            "Guilherme", "André", "Daniel", "Ricardo",
        ],
        "nomes_femininos": [
            "Mariana", "Beatriz", "Gabriela", "Carolina", "Letícia",
        ],
        "sobrenomes": [
            "Monteiro", "Carvalho", "Rezende", "Teixeira",
            "Almeida", "Ribeiro", "Andrade", "Correia",
            "Figueiredo", "Moraes", "Pinheiro", "Mendes",
            "Ferreira", "Azevedo", "Cardoso", "Barbosa",
            "Campos", "Duarte", "Machado", "Lopes",
        ],
    },
    {
        "id": "holandesa",
        "rotulo": "🇳🇱 Holandesa",
        "peso": 5,
        "nomes_masculinos": [
            "Lars", "Daan", "Bram", "Sven",
            "Ruben", "Joris", "Niels", "Thijs",
            "Bas", "Stijn", "Floris", "Wouter",
            "Jasper", "Luuk", "Mees", "Gijs",
            "Timo", "Casper", "Sem", "Koen",
        ],
        "nomes_femininos": [
            "Sophie", "Fleur", "Lotte", "Emma", "Noa",
        ],
        "sobrenomes": [
            "Bakker", "Visser", "Jansen", "De Wit",
            "Mulder", "De Vries", "Bos", "Smit",
            "Van Berg", "Hendriks", "Dekker", "Kramer",
            "De Jong", "Vermeer", "Brouwer", "Peters",
            "Van Dijk", "Kuiper", "Willems", "Van Leeuwen",
        ],
    },
    {
        "id": "australiana",
        "rotulo": "🇦🇺 Australiana",
        "peso": 4,
        "nomes_masculinos": [
            "Lachlan", "Jack", "Cooper", "Ethan",
            "Riley", "Noah", "Oscar", "Flynn",
            "Archer", "Mason", "Harrison", "Liam",
            "Blake", "Callum", "Declan", "Mitchell",
            "Angus", "Hudson", "Xavier", "Finn",
        ],
        "nomes_femininos": [
            "Sienna", "Isla", "Harper", "Chloe", "Ava",
        ],
        "sobrenomes": [
            "Mitchell", "Thompson", "Reynolds", "O'Brien",
            "Campbell", "Henderson", "Fitzgerald", "Murray",
            "Morrison", "Patterson", "MacLeod", "Brennan",
            "Dawson", "Fletcher", "Cameron", "Walsh",
            "Barrett", "Sullivan", "Gallagher", "Hawkins",
        ],
    },
    {
        "id": "japonesa",
        "rotulo": "🇯🇵 Japonesa",
        "peso": 4,
        "nomes_masculinos": [
            "Haruki", "Kenji", "Takeshi", "Ryo",
            "Shinji", "Hiroshi", "Daiki", "Yuto",
            "Kaito", "Ren", "Sota", "Hayato",
            "Kenta", "Takumi", "Naoki", "Shota",
            "Ryota", "Yuki", "Akira", "Kazuki",
        ],
        "nomes_femininos": [
            "Sakura", "Aiko", "Hana", "Rin", "Akari",
        ],
        "sobrenomes": [
            "Nakamura", "Yamamoto", "Ishikawa", "Matsuda",
            "Tanaka", "Watanabe", "Kimura", "Hayashi",
            "Takahashi", "Inoue", "Shimizu", "Kobayashi",
            "Saito", "Endo", "Yoshida", "Kato",
            "Sasaki", "Fujita", "Mori", "Okada",
        ],
    },
    {
        "id": "americana",
        "rotulo": "🇺🇸 Americana",
        "peso": 4,
        "nomes_masculinos": [
            "Tyler", "Brandon", "Ryan", "Kyle",
            "Austin", "Chase", "Blake", "Colton",
            "Dylan", "Logan", "Carter", "Hunter",
            "Garrett", "Mason", "Preston", "Bryce",
            "Tanner", "Grant", "Trevor", "Wyatt",
        ],
        "nomes_femininos": [
            "Madison", "Kennedy", "Skylar", "Morgan", "Taylor",
        ],
        "sobrenomes": [
            "Anderson", "Parker", "Morgan", "Brooks",
            "Mitchell", "Foster", "Griffin", "Hayes",
            "Sullivan", "Crawford", "Fleming", "Hawkins",
            "Turner", "Ellis", "Carson", "Douglas",
            "Warren", "Cooper", "Preston", "Reynolds",
        ],
    },
    {
        "id": "mexicana",
        "rotulo": "🇲🇽 Mexicana",
        "peso": 3,
        "nomes_masculinos": [
            "Santiago", "Rodrigo", "Emiliano", "Sebastián",
            "Mateo", "Leonardo", "Diego", "Andrés",
            "Nicolás", "Alejandro", "Maximiliano", "Ángel",
            "Patricio", "Eduardo", "Adrián", "Héctor",
            "Francisco", "Iván", "Omar", "Raúl",
        ],
        "nomes_femininos": [
            "Valentina", "Ximena", "Camila", "Regina", "Fernanda",
        ],
        "sobrenomes": [
            "Salazar", "Vargas", "Mendoza", "Guerrero",
            "Aguilar", "Delgado", "Espinoza", "Cervantes",
            "Vázquez", "Sandoval", "Rojas", "Ibarra",
            "Paredes", "Orozco", "Morales", "Fuentes",
            "Herrera", "Luna", "Ríos", "Estrada",
        ],
    },
    {
        "id": "argentina",
        "rotulo": "🇦🇷 Argentina",
        "peso": 3,
        "nomes_masculinos": [
            "Facundo", "Tomás", "Agustín", "Ignacio",
            "Joaquín", "Nicolás", "Matías", "Lautaro",
            "Franco", "Ramiro", "Gonzalo", "Santiago",
            "Luciano", "Maximiliano", "Sebastián", "Valentín",
            "Bautista", "Federico", "Martín", "Thiago",
        ],
        "nomes_femininos": [
            "Martina", "Valentina", "Catalina", "Florencia", "Luciana",
        ],
        "sobrenomes": [
            "Fernández", "Rossi", "Bianchi", "Pereyra",
            "Romano", "Gómez", "Sosa", "Álvarez",
            "Lombardi", "Ferreyra", "Giménez", "Ortiz",
            "Bruno", "Peralta", "Ledesma", "Ruiz",
            "Paz", "Acosta", "Aguirre", "Méndez",
        ],
    },
    {
        "id": "finlandesa",
        "rotulo": "🇫🇮 Finlandesa",
        "peso": 3,
        "nomes_masculinos": [
            "Aleksi", "Eero", "Mikko", "Ville",
            "Jari", "Antti", "Juha", "Sami",
            "Kalle", "Olli", "Lauri", "Teemu",
            "Toni", "Mika", "Petteri", "Joni",
            "Niko", "Valtteri", "Riku", "Eetu",
        ],
        "nomes_femininos": [
            "Emilia", "Siiri", "Aino", "Veera", "Iida",
        ],
        "sobrenomes": [
            "Virtanen", "Korhonen", "Heikkinen", "Järvinen",
            "Mäkinen", "Laine", "Koskinen", "Hämäläinen",
            "Salonen", "Lindqvist", "Lahtinen", "Saarinen",
            "Rantanen", "Kallio", "Ketola", "Nurmi",
            "Hakala", "Lehtonen", "Nieminen", "Mattila",
        ],
    },
    {
        "id": "belga",
        "rotulo": "🇧🇪 Belga",
        "peso": 3,
        "nomes_masculinos": [
            "Wout", "Mathias", "Pieter", "Jens",
            "Thibault", "Arnaud", "Jasper", "Maxim",
            "Robbe", "Loïc", "Arthur", "Simon",
            "Emile", "Victor", "Julien", "Thomas",
            "Axel", "Romain", "Florian", "Nicolas",
        ],
        "nomes_femininos": [
            "Charlotte", "Camille", "Julie", "Elise", "Noor",
        ],
        "sobrenomes": [
            "Claessens", "Janssens", "Willems", "Martens",
            "Dubois", "Lambert", "Jacobs", "Mertens",
            "Wouters", "De Smet", "Maes", "Leemans",
            "Renard", "Vandenberghe", "Leclercq", "De Graef",
            "Hermans", "Peeters", "Goossens", "Claes",
        ],
    },
    {
        "id": "portuguesa",
        "rotulo": "🇵🇹 Portuguesa",
        "peso": 3,
        "nomes_masculinos": [
            "Diogo", "Gonçalo", "Tiago", "Rodrigo",
            "Miguel", "João", "Pedro", "Afonso",
            "Tomás", "Bernardo", "Francisco", "Martim",
            "Duarte", "Lourenço", "Henrique", "Gustavo",
            "Simão", "Rafael", "André", "Nuno",
        ],
        "nomes_femininos": [
            "Leonor", "Beatriz", "Matilde", "Carolina", "Inês",
        ],
        "sobrenomes": [
            "Ferreira", "Santos", "Oliveira", "Pereira",
            "Costa", "Rodrigues", "Martins", "Sousa",
            "Fernandes", "Gonçalves", "Gomes", "Lopes",
            "Marques", "Alves", "Almeida", "Ribeiro",
            "Pinto", "Carvalho", "Teixeira", "Moreira",
        ],
    },
    {
        "id": "canadense",
        "rotulo": "🇨🇦 Canadense",
        "peso": 3,
        "nomes_masculinos": [
            "Liam", "Ethan", "Owen", "Nathan",
            "Connor", "Gavin", "Tyler", "Brayden",
            "Caleb", "Evan", "Derek", "Jordan",
            "Trevor", "Kyle", "Brett", "Colin",
            "Shane", "Reid", "Cameron", "Dustin",
        ],
        "nomes_femininos": [
            "Olivia", "Emma", "Sophia", "Chloe", "Megan",
        ],
        "sobrenomes": [
            "MacDonald", "Campbell", "Stewart", "Fraser",
            "Morrison", "Johnston", "Robertson", "Thomson",
            "Anderson", "Wilson", "Graham", "Henderson",
            "Mackenzie", "Cameron", "Murray", "Sinclair",
            "Douglas", "Crawford", "Wallace", "Fleming",
        ],
    },
    {
        "id": "austriaca",
        "rotulo": "🇦🇹 Austríaca",
        "peso": 2,
        "nomes_masculinos": [
            "Lukas", "Florian", "Tobias", "Maximilian",
            "Felix", "Sebastian", "Moritz", "Julian",
            "Dominik", "Fabian", "Matthias", "Philipp",
            "Stefan", "Thomas", "Michael", "Andreas",
            "Bernhard", "Markus", "Patrick", "Alexander",
        ],
        "nomes_femininos": [
            "Anna", "Lena", "Laura", "Sophie", "Katharina",
        ],
        "sobrenomes": [
            "Gruber", "Huber", "Bauer", "Wagner",
            "Müller", "Pichler", "Steiner", "Moser",
            "Mayer", "Hofer", "Leitner", "Berger",
            "Fuchs", "Eder", "Fischer", "Schmid",
            "Winkler", "Weber", "Schwarz", "Maier",
        ],
    },
    {
        "id": "suica",
        "rotulo": "🇨🇭 Suíça",
        "peso": 2,
        "nomes_masculinos": [
            "Luca", "Noah", "Leon", "David",
            "Samuel", "Elias", "Lukas", "Jonas",
            "Julian", "Nico", "Fabian", "Marco",
            "Raphael", "Sven", "Adrian", "Patrick",
            "Yannick", "Kevin", "Simon", "Nils",
        ],
        "nomes_femininos": [
            "Mia", "Elena", "Laura", "Lena", "Nina",
        ],
        "sobrenomes": [
            "Müller", "Meier", "Schmid", "Keller",
            "Weber", "Huber", "Schneider", "Meyer",
            "Steiner", "Fischer", "Gerber", "Brunner",
            "Baumann", "Frei", "Zimmermann", "Moser",
            "Widmer", "Wyss", "Graf", "Roth",
        ],
    },
    {
        "id": "dinamarquesa",
        "rotulo": "🇩🇰 Dinamarquesa",
        "peso": 2,
        "nomes_masculinos": [
            "Magnus", "Frederik", "Oliver", "Emil",
            "Kasper", "Nikolaj", "Mikkel", "Rasmus",
            "Mads", "Anders", "Søren", "Christian",
            "Jonas", "Viktor", "Tobias", "Simon",
            "Jakob", "Lars", "Henrik", "Kristian",
        ],
        "nomes_femininos": [
            "Freja", "Emma", "Ida", "Sofia", "Clara",
        ],
        "sobrenomes": [
            "Nielsen", "Jensen", "Hansen", "Pedersen",
            "Andersen", "Christensen", "Larsen", "Sørensen",
            "Rasmussen", "Jørgensen", "Madsen", "Kristensen",
            "Olsen", "Thomsen", "Møller", "Poulsen",
            "Johansen", "Knudsen", "Mortensen", "Eriksen",
        ],
    },
    {
        "id": "sueca",
        "rotulo": "🇸🇪 Sueca",
        "peso": 2,
        "nomes_masculinos": [
            "Erik", "Oscar", "Viktor", "Alexander",
            "Filip", "Lucas", "Emil", "Hugo",
            "Axel", "Gustav", "Elias", "William",
            "Oliver", "Liam", "Adam", "Sebastian",
            "Nils", "Anton", "Leo", "Theodor",
        ],
        "nomes_femininos": [
            "Astrid", "Elsa", "Freya", "Maja", "Linnea",
        ],
        "sobrenomes": [
            "Andersson", "Johansson", "Karlsson", "Nilsson",
            "Eriksson", "Larsson", "Olsson", "Persson",
            "Svensson", "Gustafsson", "Pettersson", "Jonsson",
            "Lindberg", "Lindström", "Lindqvist", "Magnusson",
            "Lindgren", "Axelsson", "Berg", "Bergström",
        ],
    },
    {
        "id": "norueguesa",
        "rotulo": "🇳🇴 Norueguesa",
        "peso": 2,
        "nomes_masculinos": [
            "Magnus", "Henrik", "Kristian", "Jonas",
            "Sander", "Tobias", "Mathias", "Emil",
            "Oliver", "Oskar", "Erik", "Aleksander",
            "Mikkel", "Adrian", "Sindre", "Eirik",
            "Lars", "Håkon", "Kjetil", "Trond",
        ],
        "nomes_femininos": [
            "Ingrid", "Astrid", "Nora", "Emma", "Frida",
        ],
        "sobrenomes": [
            "Hansen", "Johansen", "Olsen", "Larsen",
            "Andersen", "Pedersen", "Nilsen", "Kristiansen",
            "Jensen", "Karlsen", "Berg", "Haugen",
            "Hagen", "Eriksen", "Solberg", "Bakken",
            "Moen", "Dahl", "Lund", "Strøm",
        ],
    },
    {
        "id": "polonesa",
        "rotulo": "🇵🇱 Polonesa",
        "peso": 2,
        "nomes_masculinos": [
            "Jakub", "Mateusz", "Szymon", "Kacper",
            "Filip", "Michał", "Bartosz", "Piotr",
            "Tomasz", "Maciej", "Krzysztof", "Paweł",
            "Kamil", "Dawid", "Wojciech", "Marcin",
            "Adam", "Łukasz", "Stanisław", "Rafał",
        ],
        "nomes_femininos": [
            "Zofia", "Aleksandra", "Natalia", "Wiktoria", "Maja",
        ],
        "sobrenomes": [
            "Kowalski", "Wiśniewski", "Wójcik", "Kowalczyk",
            "Kamiński", "Lewandowski", "Zieliński", "Szymański",
            "Woźniak", "Dąbrowski", "Kozłowski", "Jankowski",
            "Mazur", "Kwiatkowski", "Krawczyk", "Piotrowski",
            "Grabowski", "Nowakowski", "Pawłowski", "Michalski",
        ],
    },
    {
        "id": "russa",
        "rotulo": "🇷🇺 Russa",
        "peso": 2,
        "nomes_masculinos": [
            "Aleksandr", "Dmitri", "Mikhail", "Sergei",
            "Andrei", "Alexei", "Nikolai", "Ivan",
            "Maxim", "Pavel", "Viktor", "Anton",
            "Kirill", "Artem", "Vladimir", "Evgeny",
            "Roman", "Oleg", "Stanislav", "Daniil",
        ],
        "nomes_femininos": [
            "Anastasia", "Ekaterina", "Natalia", "Alina", "Viktoria",
        ],
        "sobrenomes": [
            "Petrov", "Ivanov", "Volkov", "Sokolov",
            "Kuznetsov", "Fedorov", "Morozov", "Vasiliev",
            "Popov", "Smirnov", "Kozlov", "Novikov",
            "Lebedev", "Sorokin", "Orlov", "Baranov",
            "Zaitsev", "Kovalev", "Belov", "Medvedev",
        ],
    },
    {
        "id": "chinesa",
        "rotulo": "🇨🇳 Chinesa",
        "peso": 2,
        "nomes_masculinos": [
            "Wei", "Chen", "Hao", "Jun",
            "Ming", "Lei", "Feng", "Yang",
            "Long", "Jian", "Tao", "Xing",
            "Bo", "Kun", "Rui", "Cheng",
            "Peng", "Zhi", "Qiang", "Xiang",
        ],
        "nomes_femininos": [
            "Mei", "Lin", "Xiu", "Yan", "Hua",
        ],
        "sobrenomes": [
            "Wang", "Li", "Zhang", "Liu",
            "Chen", "Yang", "Huang", "Zhao",
            "Zhou", "Wu", "Xu", "Sun",
            "Ma", "Zhu", "Hu", "Guo",
            "Lin", "He", "Gao", "Luo",
        ],
    },
]

NACIONALIDADES = [item["rotulo"] for item in POOL_NOMES_NACIONALIDADES]

NOMES = [
    nome
    for item in POOL_NOMES_NACIONALIDADES
    for nome in (item["nomes_masculinos"] + item["nomes_femininos"])
]

SOBRENOMES = [
    sobrenome
    for item in POOL_NOMES_NACIONALIDADES
    for sobrenome in item["sobrenomes"]
]


# ============================================================
# CATEGORIAS (iRacing)
# ============================================================
CATEGORIAS = [
    {"id": "mazda_rookie", "nome": "Mazda MX-5 Rookie Cup", "nivel": 1},
    {"id": "toyota_rookie", "nome": "Toyota GR86 Rookie Cup", "nivel": 1},
    {"id": "mazda_amador", "nome": "Mazda MX-5 Championship", "nivel": 2},
    {"id": "toyota_amador", "nome": "Toyota GR86 Cup", "nivel": 2},
    {"id": "bmw_m2", "nome": "BMW M2 CS Racing", "nivel": 3},
    {"id": "production_challenger", "nome": "Production Car Challenger", "nivel": 3},
    {"id": "gt4", "nome": "GT4 Series", "nivel": 4},
    {"id": "gt3", "nome": "GT3 Championship", "nivel": 5},
    {"id": "endurance", "nome": "Endurance Championship", "nivel": 6},
]

# ============================================================
# CATEGORIAS (Fórmula - Progressão)
# ============================================================
CATEGORIAS_FORMULA = [
    {"id": "f1", "nome": "Fórmula 1", "nivel": 1},
    {"id": "f2", "nome": "Fórmula 2", "nivel": 2},
    {"id": "f3", "nome": "Fórmula 3", "nivel": 3},
]

# ============================================================
# PISTAS (iRacing)
# ============================================================
PISTAS_IRACING = [
    {"nome": "Summit Point Raceway - Jefferson Circuit", "trackId": 8},
    {"nome": "Summit Point Raceway - Summit Point Raceway", "trackId": 9},
    {"nome": "Summit Point Raceway - Short", "trackId": 24},
    {"nome": "WeatherTech Raceway at Laguna Seca - Full Course", "trackId": 47},
    {"nome": "Summit Point Raceway - Jefferson Reverse", "trackId": 142},
    {"nome": "Okayama International Circuit - Full Course", "trackId": 166},
    {"nome": "Okayama International Circuit - Short", "trackId": 167},
    {"nome": "Oulton Park Circuit - International", "trackId": 180},
    {"nome": "Oulton Park Circuit - Fosters", "trackId": 181},
    {"nome": "Oulton Park Circuit - Island", "trackId": 182},
    {"nome": "Oulton Park Circuit - Intl w/out Hislop", "trackId": 183},
    {"nome": "Oulton Park Circuit - Intl w/no Chicanes", "trackId": 185},
    {"nome": "Oulton Park Circuit - Fosters w/Hislop", "trackId": 186},
    {"nome": "Oulton Park Circuit - Island Historic", "trackId": 187},
    {"nome": "Oran Park Raceway - Grand Prix", "trackId": 202},
    {"nome": "Oran Park Raceway - North", "trackId": 207},
    {"nome": "Oran Park Raceway - South", "trackId": 208},
    {"nome": "Oran Park Raceway - North A", "trackId": 209},
    {"nome": "Oran Park Raceway - Moto", "trackId": 211},
    {"nome": "Snetterton Circuit - 300", "trackId": 297},
    {"nome": "Snetterton Circuit - 200", "trackId": 298},
    {"nome": "Tsukuba Circuit - 2000 Full", "trackId": 324},
    {"nome": "Tsukuba Circuit - 2000 Short", "trackId": 326},
    {"nome": "Tsukuba Circuit - 1000 Full", "trackId": 327},
    {"nome": "Lime Rock Park - Classic", "trackId": 352},
    {"nome": "Lime Rock Park - Grand Prix", "trackId": 353},
    {"nome": "Lime Rock Park - Chicanes", "trackId": 354},
    {"nome": "Winton Motor Raceway - National Circuit", "trackId": 439},
    {"nome": "Winton Motor Raceway - Club Circuit", "trackId": 440},
    {"nome": "Motorsport Arena Oschersleben - Grand Prix", "trackId": 449},
    {"nome": "Rudskogen Motorsenter", "trackId": 451},
    {"nome": "Motorsport Arena Oschersleben - Alternate", "trackId": 454},
    {"nome": "Motorsport Arena Oschersleben - B Course", "trackId": 455},
    {"nome": "Motorsport Arena Oschersleben - C Course", "trackId": 456},
    {"nome": "Virginia International Raceway - Full Course", "trackId": 465},
    {"nome": "Virginia International Raceway - Grand Course", "trackId": 466},
    {"nome": "Virginia International Raceway - North Course", "trackId": 467},
    {"nome": "Virginia International Raceway - South Course", "trackId": 468},
    {"nome": "Virginia International Raceway - Patriot Course", "trackId": 469},
    {"nome": "Circuit de Ledenon", "trackId": 489},
    {"nome": "Circuito de Navarra - Speed Circuit", "trackId": 515},
    {"nome": "Circuito de Navarra - Speed Circuit - Medium", "trackId": 516},
    {"nome": "Circuito de Navarra - Speed Circuit - Short", "trackId": 517},
    {"nome": "Charlotte Motor Speedway - Roval 2019", "trackId": 553},
    {"nome": "Charlotte Motor Speedway - Roval 2025", "trackId": 554},
    {"nome": "Charlotte Motor Speedway - Roval No Chicanes", "trackId": 555},
    {"nome": "Charlotte Motor Speedway - Oval", "trackId": 556},
]

# ============================================================
# SISTEMA DE PONTUAÇÃO (Por posição - chave = posição real)
# ============================================================
PONTOS_POR_POSICAO = {
    1: 25, 2: 18, 3: 15, 4: 12, 5: 10,
    6: 8, 7: 6, 8: 4, 9: 2, 10: 1
}

# ============================================================
# DIFICULDADES
# ============================================================
DIFICULDADES = {
    "Fácil": {"skill_min": 20, "skill_max": 60},
    "Médio": {"skill_min": 30, "skill_max": 75},
    "Difícil": {"skill_min": 50, "skill_max": 90},
    "Lendário": {"skill_min": 70, "skill_max": 100}
}

# ============================================================
# INFORMAÇÕES DOS CARROS (iRacing)
# ============================================================
CAR_INFO = {
    # Canonical expanded IDs
    "mazda_rookie": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "mazda_amador": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "toyota_rookie": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "toyota_amador": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "bmw_m2": {"carPath": "bmwm2csr", "carId": 195, "carClassId": 4005},
    "production_challenger": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "gt4": {"carPath": "mercedesamggt4", "carId": 157, "carClassId": 3905},
    "gt3": {"carPath": "ferrarievogt3", "carId": 144, "carClassId": 4036},
    "endurance": {"carPath": "ferrarievogt3", "carId": 144, "carClassId": 4036},
    # Legacy aliases
    "mx5": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "toyotagr86": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "bmwm2cs": {"carPath": "bmwm2csr", "carId": 195, "carClassId": 4005},
}

GT3_CARROS = [
    {"carPath": "acuransxevo22gt3", "carId": 194, "carClassId": 4036},
    {"carPath": "amvantageevogt3", "carId": 206, "carClassId": 4036},
    {"carPath": "audir8lmsevo2gt3", "carId": 176, "carClassId": 4036},
    {"carPath": "bmwm4gt3", "carId": 132, "carClassId": 4036},
    {"carPath": "chevyvettez06rgt3", "carId": 184, "carClassId": 4036},
    {"carPath": "ferrarievogt3", "carId": 144, "carClassId": 4036},
    {"carPath": "fordmustanggt3", "carId": 185, "carClassId": 4036},
    {"carPath": "lamborghinievogt3", "carId": 133, "carClassId": 4036},
    {"carPath": "mclaren720sgt3", "carId": 188, "carClassId": 4036},
    {"carPath": "mercedesamgevogt3", "carId": 156, "carClassId": 4036},
    {"carPath": "porsche992rgt3", "carId": 169, "carClassId": 4036},
]

GT4_CARROS = [
    {"carPath": "amvantagegt4", "carId": 150, "carClassId": 3905},
    {"carPath": "bmwm4evogt4", "carId": 189, "carClassId": 3905},
    {"carPath": "fordmustanggt4", "carId": 204, "carClassId": 3905},
    {"carPath": "mclaren570sgt4", "carId": 135, "carClassId": 3905},
    {"carPath": "mercedesamggt4", "carId": 157, "carClassId": 3905},
    {"carPath": "porsche718gt4", "carId": 119, "carClassId": 3905},
]

PRODUCTION_CAR_CARROS = {
    "mazda_rookie": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "mazda_amador": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "toyota_rookie": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "toyota_amador": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "bmw_m2": {"carPath": "bmwm2csr", "carId": 195, "carClassId": 4005},
    "renault_clio": {"carPath": "renaultcliocup", "carId": 162, "carClassId": 4031},
    # Legacy aliases
    "mx5": {"carPath": "mx5\\mx52016", "carId": 67, "carClassId": 74},
    "toyotagr86": {"carPath": "toyotagr86", "carId": 160, "carClassId": 4012},
    "bmwm2cs": {"carPath": "bmwm2csr", "carId": 195, "carClassId": 4005},
}

# ============================================================
# NOMES DOS CAMPEONATOS
# ============================================================
NOMES_CAMPEONATO = {
    "mazda_rookie": "Mazda MX-5 Rookie Cup",
    "toyota_rookie": "Toyota GR86 Rookie Cup",
    "mazda_amador": "Mazda MX-5 Championship",
    "toyota_amador": "Toyota GR86 Cup",
    "bmw_m2": "BMW M2 CS Racing",
    "production_challenger": "Production Car Challenger",
    "gt4": "GT4 Series",
    "gt3": "GT3 Championship",
    "endurance": "Endurance Championship",
    # Legacy aliases
    "mx5": "Mazda MX-5 Rookie Cup",
    "toyotagr86": "Toyota GR86 Cup",
    "bmwm2cs": "BMW M2 CS Racing",
}

# ============================================================
# CORES (Hexadecimal sem #)
# ============================================================
CORES = [
    "ff0000", "00ff00", "0000ff", "ffff00", "ff00ff", "00ffff",
    "ff8000", "ff0080", "80ff00", "0080ff", "8000ff", "00ff80",
    "ffffff", "ffd700", "ff4500", "1e90ff", "32cd32", "ff1493",
    "00ced1", "9400d3", "ff6347", "4169e1", "228b22", "dc143c",
    "20b2aa", "da70d6", "cd853f", "708090", "2e8b57", "b22222"
]

# ============================================================
# NOMES DE EQUIPES
# ============================================================
NOMES_EQUIPES = [
    # Tier 1 - Equipes de elite
    {"nome": "Apex Racing", "tier": 1},
    {"nome": "Velocity Motorsport", "tier": 1},
    {"nome": "Thunder Racing", "tier": 1},
    {"nome": "Zenith Performance", "tier": 1},
    # Tier 2 - Equipes competitivas
    {"nome": "Eclipse Performance", "tier": 2},
    {"nome": "Nitro Dynamics", "tier": 2},
    {"nome": "Storm Racing Team", "tier": 2},
    {"nome": "Phoenix Motorsport", "tier": 2},
    {"nome": "Blaze Competition", "tier": 2},
    {"nome": "Nova Racing", "tier": 2},
    # Tier 3 - Equipes de meio de grid
    {"nome": "Cobra Racing", "tier": 3},
    {"nome": "Wolf Pack Racing", "tier": 3},
    {"nome": "Titan Motorsport", "tier": 3},
    {"nome": "Falcon Speed", "tier": 3},
    {"nome": "Viper Racing Team", "tier": 3},
    {"nome": "Hawk Motorsport", "tier": 3},
    {"nome": "Panther Racing", "tier": 3},
    {"nome": "Iron Force Racing", "tier": 3},
    # Tier 4 - Equipes menores
    {"nome": "Shadow Motorsport", "tier": 4},
    {"nome": "Rookie Racing", "tier": 4},
    {"nome": "Underdog Motorsport", "tier": 4},
    {"nome": "Rising Stars Racing", "tier": 4},
    {"nome": "Maverick Racing", "tier": 4},
    {"nome": "Horizon Motorsport", "tier": 4},
    {"nome": "Drift Kings Racing", "tier": 4},
    {"nome": "Last Lap Motorsport", "tier": 4},
]

PREFIXOS_EXTRA = [
    "Alpha", "Beta", "Delta", "Omega", "Sigma", "Turbo", "Hyper",
    "Ultra", "Mega", "Prime", "Elite", "Pro", "Max", "Rapid",
    "Swift", "Steel", "Chrome", "Platinum", "Diamond", "Gold"
]

SUFIXOS_EXTRA = [
    "Racing", "Motorsport", "Performance", "Competition", "Speed",
    "Dynamics", "Racing Team", "Autosport", "Racing Co.", "Works"
]

CORES_EQUIPES = [
    "#ff0000", "#00ff00", "#0000ff", "#ffff00", "#ff00ff", "#00ffff",
    "#ff8000", "#ff0080", "#80ff00", "#0080ff", "#8000ff", "#00ff80",
    "#ffd700", "#ff4500", "#1e90ff", "#32cd32", "#ff1493", "#00ced1",
    "#dc143c", "#9400d3", "#ff6347", "#20b2aa", "#da70d6", "#cd853f",
    "#708090", "#2e8b57", "#b22222", "#4682b4", "#d2691e", "#6b8e23"
]

# ============================================================
# CONFIGURAÇÕES DE IDADE
# ============================================================
IDADE_MINIMA_PILOTO = 16
IDADE_MAXIMA_INICIO = 35
IDADE_APOSENTADORIA_PADRAO = 42



# ============================================================
# MÓDULO 2 — EQUIPES
# ============================================================

NIVEIS_CATEGORIA = {
    "rookie":      1,
    "amador":      2,
    "pro":         3,
    "super_pro":   4,
    "elite":       5,
    "super_elite": 6,
}

MAPA_PROGRESSAO = {
    "trilha_pro": {
        "caminhos": {
            "mazda": ["mazda_rookie", "mazda_amador", "production_challenger"],
            "toyota": ["toyota_rookie", "toyota_amador", "production_challenger"],
            "bmw": ["bmw_m2", "production_challenger"],
        },
        "promocao_rebaixamento": {
            ("mazda_rookie", "mazda_amador"): {"sobem": 1, "descem": 1},
            ("toyota_rookie", "toyota_amador"): {"sobem": 1, "descem": 1},
            ("mazda_amador", "production_challenger"): {"sobem": 3, "descem": 3, "marca": "mazda"},
            ("toyota_amador", "production_challenger"): {"sobem": 3, "descem": 3, "marca": "toyota"},
            ("bmw_m2", "production_challenger"): {"sobem": 3, "descem": 3, "marca": "bmw"},
        },
        "topo": "production_challenger",
    },
    "trilha_elite": {
        "caminhos": {
            "gt4": ["gt4", "endurance"],
            "gt3": ["gt3", "endurance"],
            "lmp2": ["endurance"],  # fixo, sem movimento
        },
        "promocao_rebaixamento": {
            ("gt4", "endurance"): {"sobem": 3, "descem": 3, "classe": "gt4"},
            ("gt3", "endurance"): {"sobem": 3, "descem": 3, "classe": "gt3"},
        },
        "topo": "endurance",
        "fixos": ["lmp2"],  # classes que nunca sobem/descem
    },
}

REGRAS_PROMOCAO = {
    "mazda_rookie": {
        "sobem": 1, "ssobem": 1,
        "destino_subida": "mazda_amador",
        "descem": 0,
        "destino_descida": None,
    },
    "toyota_rookie": {
        "sobem": 1, "ssobem": 1,
        "destino_subida": "toyota_amador",
        "descem": 0,
        "destino_descida": None,
    },
    "mazda_amador": {
        "sobem": 3, "ssobem": 3,
        "destino_subida": "production_challenger",
        "descem": 1,
        "destino_descida": "mazda_rookie",
    },
    "toyota_amador": {
        "sobem": 3, "ssobem": 3,
        "destino_subida": "production_challenger",
        "descem": 1,
        "destino_descida": "toyota_rookie",
    },
    "bmw_m2": {
        "sobem": 3, "ssobem": 3,
        "destino_subida": "production_challenger",
        "descem": 0,
        "destino_descida": None,
    },
    "production_challenger": {
        "sobem": 0, "ssobem": 0,
        "destino_subida": None,
        "descem": 9,
        "destino_descida": {
            "mazda": "mazda_amador",
            "toyota": "toyota_amador",
            "bmw_m2": "bmw_m2",
        },
    },
    # GT4/GT3 não rebaixam para baixo nesta regra.
    "gt4": {
        "sobem": 3, "ssobem": 3,
        "destino_subida": "endurance",
        "descem": 0,
        "destino_descida": None,
    },
    "gt3": {
        "sobem": 3, "ssobem": 3,
        "destino_subida": "endurance",
        "descem": 0,
        "destino_descida": None,
    },
    # Endurance aplica regras por classe no módulo de promoção.
    "endurance": {
        "sobem": 0, "ssobem": 0,
        "destino_subida": None,
        "descem": 6,
        "destino_descida": {
            "gt3": "gt3",
            "gt4": "gt4",
        },
    },
}

MARCAS_POR_CATEGORIA = {
    "gt3": ["Ferrari", "BMW", "Mercedes-AMG", "Porsche", "Lamborghini", "Aston Martin", "McLaren", "Audi"],
    "gt4": ["BMW", "Porsche", "Mercedes-AMG", "Aston Martin", "McLaren", "Toyota", "Chevrolet"],
}


# ============================================================
# MÓDULO 3 — CATEGORIAS E CALENDÁRIOS
# ============================================================

PISTAS_GRATUITAS = [
    {"nome": "Charlotte Motor Speedway - Road Course", "tipo": "road", "pais": "🇺🇸 EUA", "comprimento_km": 3.7},
    {"nome": "Lime Rock Park",                         "tipo": "road", "pais": "🇺🇸 EUA", "comprimento_km": 2.4},
    {"nome": "Okayama International Circuit",           "tipo": "road", "pais": "🇯🇵 Japão", "comprimento_km": 3.7},
    {"nome": "Oran Park Raceway",                      "tipo": "road", "pais": "🇦🇺 Austrália", "comprimento_km": 2.6},
    {"nome": "Oulton Park Circuit",                    "tipo": "road", "pais": "🇬🇧 Reino Unido", "comprimento_km": 4.3},
    {"nome": "Rudskogen Motorsenter",                  "tipo": "road", "pais": "🇳🇴 Noruega", "comprimento_km": 3.3},
    {"nome": "Summit Point Motorsports Park",           "tipo": "road", "pais": "🇺🇸 EUA", "comprimento_km": 3.2},
    {"nome": "Tsukuba Circuit",                        "tipo": "road", "pais": "🇯🇵 Japão", "comprimento_km": 2.0},
    {"nome": "Virginia International Raceway",          "tipo": "road", "pais": "🇺🇸 EUA", "comprimento_km": 5.3},
    {"nome": "WeatherTech Raceway Laguna Seca",         "tipo": "road", "pais": "🇺🇸 EUA", "comprimento_km": 3.6},
]

PISTAS_PAGAS = [
    {"nome": "Circuit de Spa-Francorchamps",                      "tipo": "road", "pais": "🇧🇪 Bélgica",    "comprimento_km": 7.0},
    {"nome": "Circuit des 24 Heures du Mans",                     "tipo": "road", "pais": "🇫🇷 França",     "comprimento_km": 13.6},
    {"nome": "Autodromo Nazionale Monza",                         "tipo": "road", "pais": "🇮🇹 Itália",     "comprimento_km": 5.8},
    {"nome": "Nürburgring Grand-Prix-Strecke",                    "tipo": "road", "pais": "🇩🇪 Alemanha",   "comprimento_km": 5.1},
    {"nome": "Nürburgring Nordschleife",                          "tipo": "road", "pais": "🇩🇪 Alemanha",   "comprimento_km": 20.8},
    {"nome": "Silverstone Circuit",                               "tipo": "road", "pais": "🇬🇧 Reino Unido","comprimento_km": 5.9},
    {"nome": "Mount Panorama Motor Racing Circuit",                "tipo": "road", "pais": "🇦🇺 Austrália",  "comprimento_km": 6.2},
    {"nome": "Sebring International Raceway",                     "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 6.0},
    {"nome": "Road America",                                      "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 6.5},
    {"nome": "Watkins Glen International",                        "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 5.4},
    {"nome": "Michelin Raceway Road Atlanta",                     "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 4.1},
    {"nome": "Mid-Ohio Sports Car Course",                        "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 3.6},
    {"nome": "Circuit of the Americas",                           "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 5.5},
    {"nome": "Daytona International Speedway - Road Course",      "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 5.7},
    {"nome": "Indianapolis Motor Speedway - Road Course",         "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 4.0},
    {"nome": "Sonoma Raceway",                                    "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 4.0},
    {"nome": "Acura Grand Prix of Long Beach",                    "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 3.2},
    {"nome": "Brands Hatch Circuit",                              "tipo": "road", "pais": "🇬🇧 Reino Unido","comprimento_km": 3.9},
    {"nome": "Donington Park Circuit",                            "tipo": "road", "pais": "🇬🇧 Reino Unido","comprimento_km": 4.0},
    {"nome": "Snetterton Circuit",                                "tipo": "road", "pais": "🇬🇧 Reino Unido","comprimento_km": 4.8},
    {"nome": "Knockhill Racing Circuit",                          "tipo": "road", "pais": "🇬🇧 Reino Unido","comprimento_km": 2.0},
    {"nome": "Circuit de Barcelona-Catalunya",                    "tipo": "road", "pais": "🇪🇸 Espanha",    "comprimento_km": 4.7},
    {"nome": "Circuito de Jerez – Ángel Nieto",                  "tipo": "road", "pais": "🇪🇸 Espanha",    "comprimento_km": 4.4},
    {"nome": "Hungaroring",                                       "tipo": "road", "pais": "🇭🇺 Hungria",    "comprimento_km": 4.4},
    {"nome": "Red Bull Ring",                                     "tipo": "road", "pais": "🇦🇹 Áustria",    "comprimento_km": 4.3},
    {"nome": "Hockenheimring Baden-Württemberg",                  "tipo": "road", "pais": "🇩🇪 Alemanha",   "comprimento_km": 4.6},
    {"nome": "Motorsport Arena Oschersleben",                     "tipo": "road", "pais": "🇩🇪 Alemanha",   "comprimento_km": 3.7},
    {"nome": "Circuit Zolder",                                    "tipo": "road", "pais": "🇧🇪 Bélgica",    "comprimento_km": 4.0},
    {"nome": "CM.com Circuit Zandvoort",                          "tipo": "road", "pais": "🇳🇱 Holanda",    "comprimento_km": 4.3},
    {"nome": "Circuit de Nevers Magny-Cours",                     "tipo": "road", "pais": "🇫🇷 França",     "comprimento_km": 4.4},
    {"nome": "Autodromo Internazionale Enzo e Dino Ferrari",      "tipo": "road", "pais": "🇮🇹 Itália",     "comprimento_km": 4.9},
    {"nome": "Suzuka International Racing Course",                 "tipo": "road", "pais": "🇯🇵 Japão",     "comprimento_km": 5.8},
    {"nome": "Fuji International Speedway",                       "tipo": "road", "pais": "🇯🇵 Japão",     "comprimento_km": 4.6},
    {"nome": "Mobility Resort Motegi",                            "tipo": "road", "pais": "🇯🇵 Japão",     "comprimento_km": 4.8},
    {"nome": "Autodromo Jose Carlos Pace",                        "tipo": "road", "pais": "🇧🇷 Brasil",    "comprimento_km": 4.3},
    {"nome": "Canadian Tire Motorsport Park",                     "tipo": "road", "pais": "🇨🇦 Canadá",    "comprimento_km": 3.9},
    {"nome": "Circuit Gilles-Villeneuve",                         "tipo": "road", "pais": "🇨🇦 Canadá",    "comprimento_km": 4.4},
    {"nome": "Phillip Island Circuit",                            "tipo": "road", "pais": "🇦🇺 Austrália",  "comprimento_km": 4.4},
    {"nome": "Sandown International Motor Raceway",               "tipo": "road", "pais": "🇦🇺 Austrália",  "comprimento_km": 3.1},
    {"nome": "Winton Motor Raceway",                              "tipo": "road", "pais": "🇦🇺 Austrália",  "comprimento_km": 3.0},
    {"nome": "Barber Motorsports Park",                           "tipo": "road", "pais": "🇺🇸 EUA",        "comprimento_km": 3.7},
]

# Duração da classificação (minutos) por pista
DURACAO_CLASSIFICACAO = {
    "Nürburgring Nordschleife":              20,
    "Circuit des 24 Heures du Mans":         20,
    "Circuit de Spa-Francorchamps":          18,
    "Road America":                          18,
    "Mount Panorama Motor Racing Circuit":   18,
    "Sebring International Raceway":         18,
    "Virginia International Raceway":        18,
    "Silverstone Circuit":                   18,
    "Suzuka International Racing Course":    18,
    "_default":                              15,
}

# Chance de chuva base por pista (0.0–1.0)
CHANCE_CHUVA_BASE = {
    "Oulton Park Circuit":                       0.25,
    "Brands Hatch Circuit":                      0.25,
    "Silverstone Circuit":                       0.25,
    "Donington Park Circuit":                    0.25,
    "Snetterton Circuit":                        0.20,
    "Knockhill Racing Circuit":                  0.30,
    "Circuit de Spa-Francorchamps":              0.35,
    "Circuit Zolder":                            0.20,
    "Nürburgring Grand-Prix-Strecke":            0.25,
    "Nürburgring Nordschleife":                  0.30,
    "Hockenheimring Baden-Württemberg":          0.15,
    "Suzuka International Racing Course":        0.20,
    "Fuji International Speedway":               0.25,
    "Okayama International Circuit":             0.15,
    "Tsukuba Circuit":                           0.15,
    "WeatherTech Raceway Laguna Seca":           0.05,
    "Virginia International Raceway":            0.10,
    "Road America":                              0.10,
    "Sebring International Raceway":             0.15,
    "Daytona International Speedway - Road Course": 0.20,
    "Summit Point Motorsports Park":             0.10,
    "Lime Rock Park":                            0.10,
    "Charlotte Motor Speedway - Road Course":    0.15,
    "Mount Panorama Motor Racing Circuit":       0.10,
    "Phillip Island Circuit":                    0.15,
    "Oran Park Raceway":                         0.10,
    "Rudskogen Motorsenter":                     0.20,
    "_default":                                  0.10,
}

# ── Calendários ────────────────────────────────────────────────────────────────

CALENDARIO_MAZDA_ROOKIE = {
    "num_corridas": 5,
    "duracao_corrida_minutos": 15,
    "pistas_fixas": [
        "Summit Point Motorsports Park",
        "Lime Rock Park",
        "Okayama International Circuit",
    ],
    "pistas_variaveis": [
        "Oulton Park Circuit",
        "Tsukuba Circuit",
        "Charlotte Motor Speedway - Road Course",
        "Virginia International Raceway",
    ],
    "num_variaveis": 2,
    "ordem_varia": True,
}

CALENDARIO_TOYOTA_ROOKIE = {
    "num_corridas": 5,
    "duracao_corrida_minutos": 15,
    "pistas_fixas": [
        "Tsukuba Circuit",
        "Okayama International Circuit",
        "Oran Park Raceway",
    ],
    "pistas_variaveis": [
        "Lime Rock Park",
        "Oulton Park Circuit",
        "Summit Point Motorsports Park",
        "Rudskogen Motorsenter",
        "WeatherTech Raceway Laguna Seca",
    ],
    "num_variaveis": 2,
    "ordem_varia": True,
}

CALENDARIO_MAZDA_AMADOR = {
    "num_corridas": 8,
    "duracao_corrida_minutos": 25,
    "pistas_fixas": [
        "Summit Point Motorsports Park",
        "Lime Rock Park",
        "Virginia International Raceway",
        "Okayama International Circuit",
        "Oulton Park Circuit",
        "WeatherTech Raceway Laguna Seca",
    ],
    "pistas_variaveis": [
        "Tsukuba Circuit",
        "Oran Park Raceway",
        "Rudskogen Motorsenter",
        "Charlotte Motor Speedway - Road Course",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_TOYOTA_AMADOR = {
    "num_corridas": 8,
    "duracao_corrida_minutos": 25,
    "pistas_fixas": [
        "Tsukuba Circuit",
        "Okayama International Circuit",
        "Oran Park Raceway",
        "Lime Rock Park",
        "Oulton Park Circuit",
        "Virginia International Raceway",
    ],
    "pistas_variaveis": [
        "Summit Point Motorsports Park",
        "WeatherTech Raceway Laguna Seca",
        "Rudskogen Motorsenter",
        "Charlotte Motor Speedway - Road Course",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_BMW_M2 = {
    "num_corridas": 8,
    "duracao_corrida_minutos": 25,
    "pistas_fixas": [
        "Oulton Park Circuit",
        "Lime Rock Park",
        "Virginia International Raceway",
        "Okayama International Circuit",
        "WeatherTech Raceway Laguna Seca",
        "Summit Point Motorsports Park",
    ],
    "pistas_variaveis": [
        "Tsukuba Circuit",
        "Oran Park Raceway",
        "Rudskogen Motorsenter",
        "Charlotte Motor Speedway - Road Course",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_PRODUCTION_CHALLENGER = {
    "num_corridas": 10,
    "duracao_corrida_minutos": 30,
    "multiclasse": True,
    "classes": ["mazda", "toyota", "bmw_m2"],
    "pistas_fixas": [
        "Virginia International Raceway",
        "WeatherTech Raceway Laguna Seca",
        "Lime Rock Park",
        "Okayama International Circuit",
        "Oulton Park Circuit",
        "Summit Point Motorsports Park",
        "Tsukuba Circuit",
        "Oran Park Raceway",
    ],
    "pistas_variaveis": [
        "Rudskogen Motorsenter",
        "Charlotte Motor Speedway - Road Course",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_GT4 = {
    "num_corridas": 10,
    "duracao_corrida_minutos": 30,
    "pistas_fixas": [
        "Circuit de Spa-Francorchamps",
        "Brands Hatch Circuit",
        "Silverstone Circuit",
        "Nürburgring Grand-Prix-Strecke",
        "Red Bull Ring",
        "Hungaroring",
        "Circuit de Barcelona-Catalunya",
        "Autodromo Nazionale Monza",
    ],
    "pistas_variaveis": [
        "Donington Park Circuit",
        "Circuit Zolder",
        "Hockenheimring Baden-Württemberg",
        "Snetterton Circuit",
        "Motorsport Arena Oschersleben",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_GT3 = {
    "num_corridas": 14,
    "duracao_corrida_minutos": 50,
    "pistas_fixas": [
        "Circuit de Spa-Francorchamps",
        "Autodromo Nazionale Monza",
        "Brands Hatch Circuit",
        "Silverstone Circuit",
        "Nürburgring Grand-Prix-Strecke",
        "Circuit de Barcelona-Catalunya",
        "Hungaroring",
        "Red Bull Ring",
        "Circuit Zolder",
        "Autodromo Internazionale Enzo e Dino Ferrari",
        "Circuito de Jerez – Ángel Nieto",
        "CM.com Circuit Zandvoort",
    ],
    "pistas_variaveis": [
        "Donington Park Circuit",
        "Hockenheimring Baden-Württemberg",
        "Circuit de Nevers Magny-Cours",
        "Snetterton Circuit",
    ],
    "num_variaveis": 2,
    "ordem_varia": False,
}

CALENDARIO_ENDURANCE = {
    "num_corridas": 6,
    "duracao_corrida_minutos": None,
    "multiclasse": True,
    "classes": ["gt3", "gt4", "lmp2"],
    "pistas_fixas": [
        {"nome": "Daytona International Speedway - Road Course", "duracao_corrida": 90,  "nome_evento": "3 Horas de Daytona"},
        {"nome": "Sebring International Raceway",                "duracao_corrida": 60,  "nome_evento": "2 Horas de Sebring"},
        {"nome": "Circuit de Spa-Francorchamps",                 "duracao_corrida": 120, "nome_evento": "4 Horas de Spa"},
        {"nome": "Circuit des 24 Heures du Mans",                "duracao_corrida": 60,  "nome_evento": "2 Horas de Le Mans"},
        {"nome": "Nürburgring Nordschleife",                     "duracao_corrida": 90,  "nome_evento": "3 Horas de Nürburgring"},
        {"nome": "Mount Panorama Motor Racing Circuit",           "duracao_corrida": 120, "nome_evento": "4 Horas de Bathurst"},
    ],
    "pistas_variaveis": [],
    "num_variaveis": 0,
    "ordem_varia": False,
}

# ── Pontuação ──────────────────────────────────────────────────────────────────

PONTUACAO_PADRAO = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10, 6: 8, 7: 6, 8: 4, 9: 2, 10: 1}
PONTUACAO_ENDURANCE = {1: 35, 2: 28, 3: 23, 4: 19, 5: 16, 6: 13, 7: 10, 8: 7, 9: 4, 10: 2}

BONUS_POLE = 1
BONUS_VOLTA_RAPIDA = 1
BONUS_POSICAO_GERAL_MULTICLASSE = {1: 5, 2: 3, 3: 1}

PONTUACAO_POR_CATEGORIA = {
    "mazda_rookie":          "padrao",
    "toyota_rookie":         "padrao",
    "mazda_amador":          "padrao",
    "toyota_amador":         "padrao",
    "bmw_m2":                "padrao",
    "production_challenger": "padrao",
    "gt4":                   "padrao",
    "gt3":                   "padrao",
    "endurance":             "endurance",
}

CATEGORIAS_CONFIG = {
    "mazda_rookie": {
        "nivel": "rookie",
        "nome": "Mazda MX-5 Rookie Cup",
        "carro": "Mazda MX-5",
        "monomarca": True,
        "multiclasse": False,
        "num_equipes": 6,
        "proxima_categoria": "mazda_amador",
        "num_corridas": 5,
        "duracao_corrida_minutos": 15,
        "calendario": CALENDARIO_MAZDA_ROOKIE,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 12,
    },
    "toyota_rookie": {
        "nivel": "rookie",
        "nome": "Toyota GR86 Rookie Cup",
        "carro": "Toyota GR86",
        "monomarca": True,
        "multiclasse": False,
        "num_equipes": 6,
        "proxima_categoria": "toyota_amador",
        "num_corridas": 5,
        "duracao_corrida_minutos": 15,
        "calendario": CALENDARIO_TOYOTA_ROOKIE,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 12,
    },
    "mazda_amador": {
        "nivel": "amador",
        "nome": "Mazda MX-5 Championship",
        "carro": "Mazda MX-5",
        "monomarca": True,
        "multiclasse": False,
        "num_equipes": 10,
        "proxima_categoria": "production_challenger",
        "num_corridas": 8,
        "duracao_corrida_minutos": 25,
        "calendario": CALENDARIO_MAZDA_AMADOR,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 20,
    },
    "toyota_amador": {
        "nivel": "amador",
        "nome": "Toyota GR86 Cup",
        "carro": "Toyota GR86",
        "monomarca": True,
        "multiclasse": False,
        "num_equipes": 10,
        "proxima_categoria": "production_challenger",
        "num_corridas": 8,
        "duracao_corrida_minutos": 25,
        "calendario": CALENDARIO_TOYOTA_AMADOR,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 20,
    },
    "bmw_m2": {
        "nivel": "amador",
        "nome": "BMW M2 CS Racing",
        "carro": "BMW M2 CS",
        "monomarca": True,
        "multiclasse": False,
        "num_equipes": 10,
        "proxima_categoria": "production_challenger",
        "num_corridas": 8,
        "duracao_corrida_minutos": 25,
        "calendario": CALENDARIO_BMW_M2,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 20,
    },
    "production_challenger": {
        "nivel": "pro",
        "nome": "Production Car Challenger",
        "carro": None,
        "monomarca": False,
        "multiclasse": True,
        "classes": ["mazda", "toyota", "bmw_m2"],
        "num_equipes": 15,
        # Topo da trilha PRO (nao conecta automaticamente com trilha ELITE).
        "proxima_categoria": None,
        "num_corridas": 10,
        "duracao_corrida_minutos": 30,
        "calendario": CALENDARIO_PRODUCTION_CHALLENGER,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "pontuacao_por_classe": True,
        "campeonato_geral": True,
        "bonus_posicao_geral": True,
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 30,
    },
    "gt4": {
        "nivel": "super_pro",
        "nome": "GT4 Series",
        "carro": None,
        "monomarca": False,
        "multiclasse": False,
        "usa_marca": True,
        "num_equipes": 10,
        "proxima_categoria": "endurance",
        "num_corridas": 10,
        "duracao_corrida_minutos": 30,
        "calendario": CALENDARIO_GT4,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 20,
    },
    "gt3": {
        "nivel": "elite",
        "nome": "GT3 Pro Championship",
        "carro": None,
        "monomarca": False,
        "multiclasse": False,
        "usa_marca": True,
        "num_equipes": 14,
        "proxima_categoria": "endurance",
        "num_corridas": 14,
        "duracao_corrida_minutos": 50,
        "calendario": CALENDARIO_GT3,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "padrao",
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 28,
    },
    "endurance": {
        "nivel": "super_elite",
        "nome": "Endurance Championship",
        "carro": None,
        "monomarca": False,
        "multiclasse": True,
        "classes": ["gt3", "gt4", "lmp2"],
        "num_equipes": 21,
        "proxima_categoria": None,
        "num_corridas": 6,
        "duracao_corrida_minutos": None,
        "calendario": CALENDARIO_ENDURANCE,
        "tem_classificacao": True,
        "classificacao_por_tempo": True,
        "sistema_pontuacao": "endurance",
        "pontuacao_por_classe": True,
        "campeonato_geral": True,
        "bonus_posicao_geral": True,
        "bonus_pole": True,
        "bonus_volta_rapida": True,
        "tamanho_grid": 42,
    },
}

CONFLITOS_CALENDARIO = [
    ("mazda_rookie", "toyota_rookie"),   # alternam
    ("mazda_amador", "toyota_amador"),   # alternam
]


# ── Listas fixas de equipes (102 no total) ─────────────────────────────────────

EQUIPES_MAZDA_ROOKIE = [
    {"nome": "Rookie Racing Academy", "nome_curto": "RRA",        "pais": "🇺🇸 EUA",         "cores": ("#4169E1", "#FFFFFF")},
    {"nome": "First Step Motorsport", "nome_curto": "First Step", "pais": "🇺🇸 EUA",         "cores": ("#00FF7F", "#000000")},
    {"nome": "Rising Stars Racing",   "nome_curto": "Rising",     "pais": "🇺🇸 EUA",         "cores": ("#FF69B4", "#FFFFFF")},
    {"nome": "Grid Start Academy",    "nome_curto": "Grid Start", "pais": "🇺🇸 EUA",         "cores": ("#8B4513", "#FFD700")},
    {"nome": "Apex Juniors",          "nome_curto": "Apex Jr",    "pais": "🇺🇸 EUA",         "cores": ("#00CED1", "#000000")},
    {"nome": "New Talent Racing",     "nome_curto": "New Talent", "pais": "🇺🇸 EUA",         "cores": ("#9932CC", "#FFFFFF")},
]

EQUIPES_MAZDA_AMADOR = [
    {"nome": "Mazda Motorsports",       "nome_curto": "Mazda MS",   "pais": "🇯🇵 Japão",       "cores": ("#9B0000", "#FFFFFF")},
    {"nome": "Copeland Motorsports",    "nome_curto": "Copeland",   "pais": "🇺🇸 EUA",         "cores": ("#1E90FF", "#FFFFFF")},
    {"nome": "Atlanta Speedwerks",      "nome_curto": "ATL Speed",  "pais": "🇺🇸 EUA",         "cores": ("#FF6347", "#000000")},
    {"nome": "McCumbee McAleer Racing", "nome_curto": "MM Racing",  "pais": "🇺🇸 EUA",         "cores": ("#32CD32", "#FFFFFF")},
    {"nome": "Sick Sideways",           "nome_curto": "Sideways",   "pais": "🇺🇸 EUA",         "cores": ("#FFD700", "#000000")},
    {"nome": "Velocity Motorsport MX5", "nome_curto": "Velocity",   "pais": "🇺🇸 EUA",         "cores": ("#FF4500", "#FFFFFF")},
    {"nome": "Trackside Development",   "nome_curto": "Trackside",  "pais": "🇺🇸 EUA",         "cores": ("#2E8B57", "#FFFFFF")},
    {"nome": "Grassroots Motorsport",   "nome_curto": "Grassroots", "pais": "🇺🇸 EUA",         "cores": ("#228B22", "#FFFFFF")},
    {"nome": "Slipstream Racing MX5",   "nome_curto": "Slipstream", "pais": "🇬🇧 Reino Unido", "cores": ("#4682B4", "#FFFFFF")},
    {"nome": "Roadster Cup Racing",     "nome_curto": "Roadster",   "pais": "🇺🇸 EUA",         "cores": ("#8B008B", "#FFD700")},
]

EQUIPES_MAZDA_PRODUCTION = [
    {"nome": "Mazda Factory Team",  "nome_curto": "Mazda FT",   "pais": "🇯🇵 Japão", "cores": ("#9B0000", "#FFFFFF"), "carro_classe": "mazda"},
    {"nome": "MX5 Pro Racing",      "nome_curto": "MX5 Pro",    "pais": "🇺🇸 EUA",   "cores": ("#1E90FF", "#000000"), "carro_classe": "mazda"},
    {"nome": "Miata Masters",       "nome_curto": "Miata M",    "pais": "🇺🇸 EUA",   "cores": ("#FF6347", "#FFFFFF"), "carro_classe": "mazda"},
    {"nome": "Zoom Zoom Racing",    "nome_curto": "Zoom Zoom",  "pais": "🇯🇵 Japão", "cores": ("#32CD32", "#000000"), "carro_classe": "mazda"},
    {"nome": "Rotary Spirit Racing","nome_curto": "Rotary",     "pais": "🇯🇵 Japão", "cores": ("#FFD700", "#9B0000"), "carro_classe": "mazda"},
]

EQUIPES_TOYOTA_ROOKIE = [
    {"nome": "GR Academy",            "nome_curto": "GR Academy",     "pais": "🇯🇵 Japão",       "cores": ("#EB0A1E", "#FFFFFF")},
    {"nome": "86 Cup Rookies",        "nome_curto": "86 Rookies",     "pais": "🇺🇸 EUA",         "cores": ("#4169E1", "#FFFFFF")},
    {"nome": "Next Gen Racing GR",    "nome_curto": "Next Gen",       "pais": "🇺🇸 EUA",         "cores": ("#32CD32", "#000000")},
    {"nome": "Rising Sun Motorsport", "nome_curto": "Rising Sun",     "pais": "🇯🇵 Japão",       "cores": ("#FF4500", "#FFFFFF")},
    {"nome": "Fuji Speedway Academy", "nome_curto": "Fuji",           "pais": "🇯🇵 Japão",       "cores": ("#000000", "#EB0A1E")},
    {"nome": "Track Warriors Toyota", "nome_curto": "Track Warriors", "pais": "🇬🇧 Reino Unido", "cores": ("#8B008B", "#FFFFFF")},
]

EQUIPES_TOYOTA_AMADOR = [
    {"nome": "Toyota Gazoo Racing",      "nome_curto": "TGR",       "pais": "🇯🇵 Japão",       "cores": ("#EB0A1E", "#FFFFFF")},
    {"nome": "TRD Sports",               "nome_curto": "TRD",       "pais": "🇺🇸 EUA",         "cores": ("#EB0A1E", "#000000")},
    {"nome": "GR Cup Development",       "nome_curto": "GR Dev",    "pais": "🇯🇵 Japão",       "cores": ("#000000", "#EB0A1E")},
    {"nome": "Riley Motorsports GR",     "nome_curto": "Riley GR",  "pais": "🇺🇸 EUA",         "cores": ("#8B0000", "#FFD700")},
    {"nome": "Bryan Herta Autosport GR", "nome_curto": "BHA GR",    "pais": "🇺🇸 EUA",         "cores": ("#FF8C00", "#000000")},
    {"nome": "Hattori Racing GR",        "nome_curto": "Hattori",   "pais": "🇯🇵 Japão",       "cores": ("#FFD700", "#000000")},
    {"nome": "Passport Toyota Racing",   "nome_curto": "Passport",  "pais": "🇺🇸 EUA",         "cores": ("#1E90FF", "#FFFFFF")},
    {"nome": "Pacific Coast Racing GR",  "nome_curto": "Pacific",   "pais": "🇺🇸 EUA",         "cores": ("#00CED1", "#000000")},
    {"nome": "Red Line Racing Toyota",   "nome_curto": "Red Line",  "pais": "🇬🇧 Reino Unido", "cores": ("#DC143C", "#FFFFFF")},
    {"nome": "Spirit of 86 Racing",      "nome_curto": "Spirit 86", "pais": "🇯🇵 Japão",       "cores": ("#2F4F4F", "#EB0A1E")},
]

EQUIPES_TOYOTA_PRODUCTION = [
    {"nome": "Gazoo Racing Pro",   "nome_curto": "GR Pro",     "pais": "🇯🇵 Japão", "cores": ("#EB0A1E", "#FFFFFF"), "carro_classe": "toyota"},
    {"nome": "86 Masters Racing",  "nome_curto": "86 Masters", "pais": "🇺🇸 EUA",   "cores": ("#000000", "#EB0A1E"), "carro_classe": "toyota"},
    {"nome": "TRD Pro Series",     "nome_curto": "TRD Pro",    "pais": "🇺🇸 EUA",   "cores": ("#EB0A1E", "#FFD700"), "carro_classe": "toyota"},
    {"nome": "Twin Cam Racing",    "nome_curto": "Twin Cam",   "pais": "🇯🇵 Japão", "cores": ("#4169E1", "#FFFFFF"), "carro_classe": "toyota"},
    {"nome": "AE86 Legacy Racing", "nome_curto": "AE86",       "pais": "🇯🇵 Japão", "cores": ("#FFFFFF", "#000000"), "carro_classe": "toyota"},
]

EQUIPES_BMW_M2_AMADOR = [
    {"nome": "BMW M Performance",          "nome_curto": "M Perf",      "pais": "🇩🇪 Alemanha", "cores": ("#1C69D4", "#FFFFFF")},
    {"nome": "Walkenhorst Motorsport M2",  "nome_curto": "Walkenhorst", "pais": "🇩🇪 Alemanha", "cores": ("#003366", "#FFD700")},
    {"nome": "Schnitzer Motorsport",       "nome_curto": "Schnitzer",   "pais": "🇩🇪 Alemanha", "cores": ("#1C69D4", "#FF0000")},
    {"nome": "RMG Racing",                 "nome_curto": "RMG",         "pais": "🇩🇪 Alemanha", "cores": ("#000000", "#1C69D4")},
    {"nome": "Nürburgring Racing Academy", "nome_curto": "N-Academy",   "pais": "🇩🇪 Alemanha", "cores": ("#2F4F4F", "#FFFFFF")},
    {"nome": "Bavarian Motorsport",        "nome_curto": "Bavarian",    "pais": "🇩🇪 Alemanha", "cores": ("#87CEEB", "#000000")},
    {"nome": "Munich Racing Team",         "nome_curto": "Munich RT",   "pais": "🇩🇪 Alemanha", "cores": ("#FFD700", "#1C69D4")},
    {"nome": "Motorsport Arena",           "nome_curto": "Arena",       "pais": "🇦🇹 Áustria",  "cores": ("#DC143C", "#FFFFFF")},
    {"nome": "Clubsport Champions",        "nome_curto": "Clubsport",   "pais": "🇳🇱 Holanda",  "cores": ("#FF8C00", "#000000")},
    {"nome": "M Power Racing",             "nome_curto": "M Power",     "pais": "🇩🇪 Alemanha", "cores": ("#1C69D4", "#EB0A1E")},
]

EQUIPES_BMW_M2_PRODUCTION = [
    {"nome": "BMW M Factory Racing",    "nome_curto": "M Factory",    "pais": "🇩🇪 Alemanha", "cores": ("#1C69D4", "#FFFFFF"), "carro_classe": "bmw_m2"},
    {"nome": "M2 Pro Series",           "nome_curto": "M2 Pro",       "pais": "🇩🇪 Alemanha", "cores": ("#000000", "#1C69D4"), "carro_classe": "bmw_m2"},
    {"nome": "Nordschleife Masters",    "nome_curto": "Nordschleife", "pais": "🇩🇪 Alemanha", "cores": ("#228B22", "#FFFFFF"), "carro_classe": "bmw_m2"},
    {"nome": "Alpina Racing Team",      "nome_curto": "Alpina",       "pais": "🇩🇪 Alemanha", "cores": ("#003366", "#87CEEB"), "carro_classe": "bmw_m2"},
    {"nome": "Ultimate Driving Racing", "nome_curto": "Ultimate",     "pais": "🇺🇸 EUA",      "cores": ("#1C69D4", "#FFD700"), "carro_classe": "bmw_m2"},
]

EQUIPES_GT4 = [
    {"nome": "BMW Junior Team GT4",    "nome_curto": "BMW Jr",      "pais": "🇩🇪 Alemanha",    "marca": "BMW",          "cores": ("#1C69D4", "#FFFFFF")},
    {"nome": "Allied Racing",          "nome_curto": "Allied",      "pais": "🇩🇪 Alemanha",    "marca": "Porsche",      "cores": ("#000000", "#FFD700")},
    {"nome": "Selleslagh Racing Team", "nome_curto": "SRT",         "pais": "🇧🇪 Bélgica",     "marca": "Mercedes-AMG", "cores": ("#C0C0C0", "#000000")},
    {"nome": "Academy Motorsport",     "nome_curto": "Academy",     "pais": "🇬🇧 Reino Unido", "marca": "Aston Martin", "cores": ("#228B22", "#FFFFFF")},
    {"nome": "Autorama Motorsport",    "nome_curto": "Autorama",    "pais": "🇩🇪 Alemanha",    "marca": "BMW",          "cores": ("#FF4500", "#000000")},
    {"nome": "Speed Lover",            "nome_curto": "Speed Lover", "pais": "🇧🇪 Bélgica",     "marca": "Porsche",      "cores": ("#00CED1", "#FFFFFF")},
    {"nome": "Newbridge Motorsport",   "nome_curto": "Newbridge",   "pais": "🇬🇧 Reino Unido", "marca": "Aston Martin", "cores": ("#4B0082", "#FFD700")},
    {"nome": "Racing Spirit of Léman", "nome_curto": "RS Léman",    "pais": "🇨🇭 Suíça",       "marca": "Toyota",       "cores": ("#DC143C", "#FFFFFF")},
    {"nome": "MDM Motorsport",         "nome_curto": "MDM",         "pais": "🇳🇱 Holanda",     "marca": "McLaren",      "cores": ("#0000CD", "#FFD700")},
    {"nome": "Street Art Racing GT4",  "nome_curto": "Street Art",  "pais": "🇫🇷 França",      "marca": "Chevrolet",    "cores": ("#9400D3", "#00FF00")},
]

EQUIPES_GT3 = [
    {"nome": "Ferrari Competizioni GT",   "nome_curto": "Ferrari",     "pais": "🇮🇹 Itália",     "marca": "Ferrari",      "cores": ("#DC0000", "#FFCC00")},
    {"nome": "BMW M Motorsport",          "nome_curto": "BMW M",       "pais": "🇩🇪 Alemanha",   "marca": "BMW",          "cores": ("#1C69D4", "#FFFFFF")},
    {"nome": "Mercedes-AMG Team",         "nome_curto": "AMG",         "pais": "🇩🇪 Alemanha",   "marca": "Mercedes-AMG", "cores": ("#00D2BE", "#000000")},
    {"nome": "Porsche Motorsport",        "nome_curto": "Porsche",     "pais": "🇩🇪 Alemanha",   "marca": "Porsche",      "cores": ("#C41E3A", "#FFFFFF")},
    {"nome": "Lamborghini Squadra Corse", "nome_curto": "Lambo SC",    "pais": "🇮🇹 Itália",     "marca": "Lamborghini",  "cores": ("#5B8C2A", "#000000")},
    {"nome": "Aston Martin Racing",       "nome_curto": "AMR",         "pais": "🇬🇧 Reino Unido","marca": "Aston Martin", "cores": ("#006847", "#FFFFFF")},
    {"nome": "McLaren Factory GT",        "nome_curto": "McLaren",     "pais": "🇬🇧 Reino Unido","marca": "McLaren",      "cores": ("#FF8700", "#000000")},
    {"nome": "Iron Lynx",                 "nome_curto": "Iron Lynx",   "pais": "🇮🇹 Itália",     "marca": "Ferrari",      "cores": ("#FF6B00", "#000000")},
    {"nome": "Walkenhorst Motorsport",    "nome_curto": "Walkenhorst", "pais": "🇩🇪 Alemanha",   "marca": "BMW",          "cores": ("#003366", "#FFD700")},
    {"nome": "AKKA ASP Team",             "nome_curto": "AKKA ASP",    "pais": "🇫🇷 França",     "marca": "Mercedes-AMG", "cores": ("#1E90FF", "#FFFFFF")},
    {"nome": "Dinamic Motorsport",        "nome_curto": "Dinamic",     "pais": "🇮🇹 Itália",     "marca": "Porsche",      "cores": ("#00205B", "#FF0000")},
    {"nome": "Barwell Motorsport",        "nome_curto": "Barwell",     "pais": "🇬🇧 Reino Unido","marca": "Lamborghini",  "cores": ("#FFD700", "#000000")},
    {"nome": "Garage 59",                 "nome_curto": "Garage 59",   "pais": "🇬🇧 Reino Unido","marca": "McLaren",      "cores": ("#FF8700", "#FFFFFF")},
    {"nome": "Audi Sport Team WRT",       "nome_curto": "WRT Audi",    "pais": "🇧🇪 Bélgica",    "marca": "Audi",         "cores": ("#CC0000", "#FFFFFF")},
]

EQUIPES_ENDURANCE_GT3 = [
    {"nome": "AF Corse",                 "nome_curto": "AF Corse",       "pais": "🇮🇹 Itália",     "marca": "Ferrari",      "cores": ("#DC0000", "#FFFFFF"), "classe_endurance": "gt3"},
    {"nome": "ROWE Racing",              "nome_curto": "ROWE",           "pais": "🇩🇪 Alemanha",   "marca": "BMW",          "cores": ("#FFD700", "#1C69D4"), "classe_endurance": "gt3"},
    {"nome": "GruppeM Racing",           "nome_curto": "GruppeM",        "pais": "🇭🇰 Hong Kong",  "marca": "Mercedes-AMG", "cores": ("#000000", "#00D2BE"), "classe_endurance": "gt3"},
    {"nome": "Manthey Racing",           "nome_curto": "Manthey",        "pais": "🇩🇪 Alemanha",   "marca": "Porsche",      "cores": ("#00FF00", "#000000"), "classe_endurance": "gt3"},
    {"nome": "Orange1 FFF Racing",       "nome_curto": "FFF",            "pais": "🇨🇳 China",      "marca": "Lamborghini",  "cores": ("#FF8C00", "#000000"), "classe_endurance": "gt3"},
    {"nome": "TF Sport",                 "nome_curto": "TF Sport",       "pais": "🇬🇧 Reino Unido","marca": "Aston Martin", "cores": ("#006847", "#FFD700"), "classe_endurance": "gt3"},
    {"nome": "Inception Racing",         "nome_curto": "Inception",      "pais": "🇬🇧 Reino Unido","marca": "McLaren",      "cores": ("#FF1493", "#000000"), "classe_endurance": "gt3"},
    {"nome": "Car Collection Motorsport","nome_curto": "Car Collection", "pais": "🇩🇪 Alemanha",   "marca": "Audi",         "cores": ("#CC0000", "#FFFFFF"), "classe_endurance": "gt3"},
]

EQUIPES_ENDURANCE_GT4 = [
    {"nome": "PROsport Racing",    "nome_curto": "PROsport", "pais": "🇩🇪 Alemanha", "marca": "Aston Martin", "cores": ("#FFD700", "#006400"), "classe_endurance": "gt4"},
    {"nome": "ST Racing",          "nome_curto": "ST Racing","pais": "🇺🇸 EUA",      "marca": "BMW",          "cores": ("#000000", "#1C69D4"), "classe_endurance": "gt4"},
    {"nome": "Winward Racing GT4", "nome_curto": "Winward",  "pais": "🇺🇸 EUA",      "marca": "Mercedes-AMG", "cores": ("#C0C0C0", "#DC143C"), "classe_endurance": "gt4"},
    {"nome": "GMG Racing",         "nome_curto": "GMG",      "pais": "🇺🇸 EUA",      "marca": "Porsche",      "cores": ("#FF4500", "#FFFFFF"), "classe_endurance": "gt4"},
    {"nome": "Murillo Racing",     "nome_curto": "Murillo",  "pais": "🇺🇸 EUA",      "marca": "McLaren",      "cores": ("#FF8C00", "#000000"), "classe_endurance": "gt4"},
]

EQUIPES_ENDURANCE_LMP2 = [
    {"nome": "United Autosports",         "nome_curto": "United",        "pais": "🇬🇧 Reino Unido","cores": ("#1E3A5F", "#FFFFFF"), "classe_endurance": "lmp2"},
    {"nome": "Jota Sport",                "nome_curto": "Jota",          "pais": "🇬🇧 Reino Unido","cores": ("#FFD700", "#000000"), "classe_endurance": "lmp2"},
    {"nome": "WRT",                       "nome_curto": "WRT",           "pais": "🇧🇪 Bélgica",    "cores": ("#00BFFF", "#FFFFFF"), "classe_endurance": "lmp2"},
    {"nome": "Prema Racing",              "nome_curto": "Prema",         "pais": "🇮🇹 Itália",     "cores": ("#DC0000", "#000000"), "classe_endurance": "lmp2"},
    {"nome": "Cool Racing",               "nome_curto": "Cool",          "pais": "🇨🇭 Suíça",      "cores": ("#00CED1", "#000000"), "classe_endurance": "lmp2"},
    {"nome": "Inter Europol Competition", "nome_curto": "Inter Europol", "pais": "🇵🇱 Polônia",    "cores": ("#FF4500", "#FFFFFF"), "classe_endurance": "lmp2"},
    {"nome": "Nielsen Racing",            "nome_curto": "Nielsen",       "pais": "🇩🇰 Dinamarca",  "cores": ("#228B22", "#FFFFFF"), "classe_endurance": "lmp2"},
    {"nome": "Algarve Pro Racing",        "nome_curto": "Algarve",       "pais": "🇵🇹 Portugal",   "cores": ("#006400", "#FFD700"), "classe_endurance": "lmp2"},
]

_EQUIPES_POR_CATEGORIA = {
    "mazda_rookie":          EQUIPES_MAZDA_ROOKIE,
    "mazda_amador":          EQUIPES_MAZDA_AMADOR,
    "toyota_rookie":         EQUIPES_TOYOTA_ROOKIE,
    "toyota_amador":         EQUIPES_TOYOTA_AMADOR,
    "bmw_m2":                EQUIPES_BMW_M2_AMADOR,
    "production_challenger": EQUIPES_MAZDA_PRODUCTION + EQUIPES_TOYOTA_PRODUCTION + EQUIPES_BMW_M2_PRODUCTION,
    "gt4":                   EQUIPES_GT4,
    "gt3":                   EQUIPES_GT3,
    "endurance":             EQUIPES_ENDURANCE_GT3 + EQUIPES_ENDURANCE_GT4 + EQUIPES_ENDURANCE_LMP2,
}
