"""Dados simulados da academia (no projeto final viriam do ERP / banco de dados)."""


ALUNOS = {
    "48592": {"nome": "Maria Souza", "cpf": "11111111111", "plano": "Básico", "ativo": True},
    "48593": {"nome": "João Lima", "cpf": "22222222222", "plano": "Premium", "ativo": True},
    "48594": {"nome": "Ana Costa", "cpf": "33333333333", "plano": "Básico", "ativo": False},
}


LIMITE_RESERVAS = {"Básico": 2, "Premium": 4}


CANCELAR_ATE_HORAS = 2


GRADE = [
    {"modalidade": "Spin", "dias": [0, 1, 2, 3, 4, 5],
     "horas": ["07:00", "08:30", "18:30", "19:30"], "vagas": 10,
     "ocupadas": {"07:00": 2, "08:30": 3, "18:30": 5, "19:30": 4}},
    
    {"modalidade": "Funcional", "dias": [1, 3],
     "horas": ["18:00"], "vagas": 2, "ocupadas": {"18:00": 2}},
]


SERIES = {
    "iniciante":     {"series": 3, "min": 2, "max": 4, "reps": "12 a 15", "descanso": "entre 60 e 90 segundos"},
    "intermediario": {"series": 4, "min": 3, "max": 5, "reps": "8 a 12", "descanso": "entre 60 e 90 segundos"},
    "avancado":      {"series": 4, "min": 3, "max": 6, "reps": "6 a 10", "descanso": "cerca de 90 segundos"},
}


AQUECIMENTO = {
    "iniciante": [
        {"nome": "Esteira", "keys": ["esteira"],
         "descricao": "8 a 10 minutos de caminhada moderada (velocidade 4.5 a 5.5 km/h).",
         "escolha": "Faça 8 a 10 minutos de caminhada na esteira."},
        {"nome": "Bicicleta Ergométrica", "keys": ["bicicleta", "bike", "ergometrica"],
         "descricao": "10 minutos com carga leve.",
         "escolha": "Faça 10 minutos de bicicleta com carga leve."},
    ],
    "intermediario": [
        {"nome": "Esteira", "keys": ["esteira"],
         "descricao": "8 a 10 minutos de caminhada rápida ou trote leve (velocidade 5.5 a 7 km/h).",
         "escolha": "Faça 8 a 10 minutos na esteira, em caminhada rápida ou trote leve."},
        {"nome": "Bicicleta Ergométrica", "keys": ["bicicleta", "bike", "ergometrica"],
         "descricao": "10 minutos com carga leve a moderada.",
         "escolha": "Faça 10 minutos de bicicleta com carga leve a moderada."},
    ],
    "avancado": [
        {"nome": "Esteira", "keys": ["esteira"],
         "descricao": "10 minutos de trote leve a moderado (velocidade 6 a 8 km/h).",
         "escolha": "Faça 10 minutos de trote na esteira, de leve a moderado."},
        {"nome": "Bicicleta Ergométrica", "keys": ["bicicleta", "bike", "ergometrica"],
         "descricao": "10 minutos com carga moderada e cadência progressiva.",
         "escolha": "Faça 10 minutos de bicicleta com carga moderada, aumentando a cadência aos poucos."},
    ],
}


TREINOS = {
    "inferiores": {
        "principal_frase": "nos Membros Inferiores (Quadríceps e Glúteos)",
        "sec_frase": "o Core (Abdômen)",
        "principal": [
            {"nome": "Leg Press 45°", "reps_inic": "12"},
            {"nome": "Cadeira Extensora", "reps_inic": "10 a 12"},
        ],
        "secundario": [{"nome": "Abdominal Infra no solo", "reps_inic": "15"}],
    },
    "superiores": {
        "principal_frase": "nos Membros Superiores (Peito e Costas)",
        "sec_frase": "os Ombros e Braços",
        "principal": [
            {"nome": "Supino reto com halteres", "reps_inic": "12"},
            {"nome": "Remada baixa", "reps_inic": "10 a 12"},
        ],
        "secundario": [
            {"nome": "Elevação lateral", "reps_inic": "12"},
            {"nome": "Rosca direta", "reps_inic": "12"},
        ],
    },
    "corpo_todo": {
        "principal_frase": "no Corpo Todo (Pernas, Peito e Costas)",
        "sec_frase": "o Core (Abdômen)",
        "principal": [
            {"nome": "Leg Press 45°", "reps_inic": "12"},
            {"nome": "Supino reto com halteres", "reps_inic": "12"},
            {"nome": "Remada baixa", "reps_inic": "10 a 12"},
        ],
        "secundario": [{"nome": "Abdominal Infra no solo", "reps_inic": "15"}],
    },
}


EXECUCAO = {
    "Leg Press 45°": "Sente-se com as costas e o quadril apoiados e os pés na largura dos ombros. Empurre a plataforma sem esticar totalmente os joelhos e volte devagar, sem tirar o quadril do banco.",
    "Cadeira Extensora": "Ajuste o encosto para o joelho ficar alinhado ao eixo do aparelho. Estenda as pernas de forma controlada e desça devagar, sem balançar o corpo.",
    "Abdominal Infra no solo": "Deite de costas com a lombar apoiada no chão. Eleve o quadril e as pernas de forma controlada, sem tirar a lombar do chão, e volte devagar.",
    "Supino reto com halteres": "Deitado no banco, com os pés no chão. Desça os halteres até a altura do peito com controle e empurre para cima sem bater um no outro.",
    "Remada baixa": "Sentado, com o peito aberto e as costas retas. Puxe o puxador em direção ao abdômen, juntando as escápulas, e volte devagar.",
    "Elevação lateral": "Em pé, com halteres leves ao lado do corpo. Eleve os braços até a altura dos ombros, com os cotovelos levemente flexionados, e desça devagar.",
    "Rosca direta": "Em pé, com os cotovelos junto ao corpo. Flexione os cotovelos levando a carga até os ombros e desça controlando o movimento.",
}

CHAVES_EXERCICIO = {
    "leg press": "Leg Press 45°", "extensora": "Cadeira Extensora",
    "abdominal": "Abdominal Infra no solo", "supino": "Supino reto com halteres",
    "remada": "Remada baixa", "elevacao": "Elevação lateral", "rosca": "Rosca direta",
}

EXPRESSO = {
    "iniciante": {"descanso": "30 segundos", "exercicios": [
        ("Agachamento livre com peso corporal", "3 séries de 15 repetições"),
        ("Flexão de braços com joelhos apoiados", "3 séries de 10 repetições"),
        ("Prancha isométrica", "3 séries de 30 segundos")]},
    "intermediario": {"descanso": "30 segundos", "exercicios": [
        ("Agachamento livre com peso corporal", "3 séries de 20 repetições"),
        ("Flexão de braços", "3 séries de 10 repetições"),
        ("Prancha isométrica", "3 séries de 45 segundos")]},
    "avancado": {"descanso": "20 segundos", "exercicios": [
        ("Agachamento com salto", "4 séries de 15 repetições"),
        ("Flexão de braços", "4 séries de 12 repetições"),
        ("Prancha isométrica", "4 séries de 60 segundos")]},
}
