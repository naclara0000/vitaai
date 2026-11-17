"""Dados simulados da academia (no projeto final viriam do ERP / banco de dados)."""

ALUNOS = {
    "1001": {"nome": "Maria Souza", "cpf": "11111111111", "plano": "Básico", "ativo": True},
    "1002": {"nome": "João Lima", "cpf": "22222222222", "plano": "Premium", "ativo": True},
    "1003": {"nome": "Ana Costa", "cpf": "33333333333", "plano": "Básico", "ativo": False},
}

LIMITE_RESERVAS = {"Básico": 2, "Premium": 4}

CANCELAR_ATE_HORAS = 2



AULAS = [
    {"id": "spin-seg-07", "modalidade": "Spin", "dia": "Segunda", "dia_semana": 0, "hora": "07:00", "vagas": 10, "inscritos": ["9001", "9002"]},
    {"id": "spin-seg-19", "modalidade": "Spin", "dia": "Segunda", "dia_semana": 0, "hora": "19:00", "vagas": 10, "inscritos": []},
    {"id": "func-ter-18", "modalidade": "Funcional", "dia": "Terça", "dia_semana": 1, "hora": "18:00", "vagas": 12, "inscritos": []},
    {"id": "spin-qua-19", "modalidade": "Spin", "dia": "Quarta", "dia_semana": 2, "hora": "19:00", "vagas": 3, "inscritos": ["9001", "9002", "9003"]},  # lotada
    {"id": "func-qui-18", "modalidade": "Funcional", "dia": "Quinta", "dia_semana": 3, "hora": "18:00", "vagas": 12, "inscritos": []},
    {"id": "spin-sex-18", "modalidade": "Spin", "dia": "Sexta", "dia_semana": 4, "hora": "18:00", "vagas": 10, "inscritos": ["9001"]},
    {"id": "spin-sab-09", "modalidade": "Spin", "dia": "Sábado", "dia_semana": 5, "hora": "09:00", "vagas": 10, "inscritos": []},
]


SERIES = {
    "iniciante":     {"series": 2, "min": 2, "max": 3, "reps": "12 a 15", "descanso": "60 s"},
    "intermediario": {"series": 3, "min": 2, "max": 4, "reps": "10 a 12", "descanso": "60 a 90 s"},
    "avancado":      {"series": 4, "min": 3, "max": 5, "reps": "8 a 12", "descanso": "90 s"},
}


EXPRESSO = {
    "iniciante": (30, 30),
    "intermediario": (40, 20),
    "avancado": (45, 15),
}


AQUECIMENTO = {
    "iniciante": [
        "Caminhada leve na esteira (5 min)",
        "Bicicleta ergométrica em ritmo leve (5 min)",
        "Mobilidade de ombros, quadril e tornozelos (2 min)",
    ],
    "intermediario": [
        "Esteira ou elíptico em ritmo moderado (5 a 8 min)",
        "Bicicleta ergométrica com cadência progressiva (5 min)",
        "Mobilidade articular dinâmica (3 min)",
    ],
    "avancado": [
        "Esteira ou bicicleta em ritmo moderado (8 min)",
        "Corda ou polichinelos (3 min)",
        "Mobilidade dinâmica + séries de aproximação com carga leve",
    ],
}


TREINOS = {
    "superiores": {
        "nome": "Superiores",
        "principal": ["Supino reto com halteres", "Remada baixa", "Desenvolvimento com halteres"],
        "secundario": ["Rosca direta", "Tríceps na polia", "Elevação lateral"],
        "aquecimento": "Mobilidade de ombros e escápulas + 1 série leve do primeiro exercício",
    },
    "inferiores": {
        "nome": "Inferiores",
        "principal": ["Agachamento", "Leg press 45°", "Cadeira extensora"],
        "secundario": ["Mesa flexora", "Elevação pélvica", "Panturrilha em pé"],
        "aquecimento": "Mobilidade de quadril e tornozelos + agachamento livre sem carga",
    },
    "corpo_todo": {
        "nome": "Corpo todo",
        "principal": ["Agachamento", "Supino reto com halteres", "Remada baixa"],
        "secundario": ["Elevação pélvica", "Desenvolvimento com halteres", "Prancha"],
        "aquecimento": "Mobilidade geral + 1 série leve do primeiro exercício",
    },
}
