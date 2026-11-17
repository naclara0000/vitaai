import re
from functools import lru_cache

import requests
from deep_translator import GoogleTranslator

URL = "https://wger.de/api/v2/exerciseinfo/"
IDIOMA_INGLES = 2


def traduzir(texto):
    if not texto:
        return ""
    try:
        return GoogleTranslator(source="en", target="pt").translate(texto)
    except Exception as erro:
        print("Erro na tradução:", erro)  # aparece no terminal
        return texto


def limpar_html(texto):
    """A descrição vem com tags HTML (<p>, <li>); aqui removemos."""
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto[:400]  # limita o tamanho


@lru_cache(maxsize=32)
def buscar_exercicios(categoria=None, quantidade=5):
    params = {"limit": 30, "language": IDIOMA_INGLES}
    if categoria:
        params["category"] = categoria

    try:
        resposta = requests.get(URL, params=params, timeout=15)
        resposta.raise_for_status()
        dados = resposta.json()
    except (requests.RequestException, ValueError):
        return []

    exercicios = []
    for item in dados.get("results", []):
        for t in item.get("translations", []):
            nome = t.get("name")
            descricao = limpar_html(t.get("description"))
            if nome and descricao and t.get("language") == IDIOMA_INGLES:
                exercicios.append({
                    "nome": traduzir(nome),
                    "descricao": traduzir(descricao),
                })
                break
        if len(exercicios) >= quantidade:
            break
    return exercicios