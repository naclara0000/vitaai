
import random
import re
import unicodedata
from datetime import datetime, timedelta

from informacoes import academia
from base_dados import (
    ALUNOS, AULAS, LIMITE_RESERVAS, CANCELAR_ATE_HORAS,
    SERIES, EXPRESSO, AQUECIMENTO, TREINOS,
)
from api_exercicios import buscar_exercicios

try:
    from ia import conversar_ia
except Exception:  # IA é opcional
    conversar_ia = None

# ---------------------------------------------------------------- constantes
MENU_OPCOES = [
    "Montar meu treino",
    "Agendar aula",
    "Minhas reservas",
    "Horário de funcionamento",
    "Falar com a recepção",
]

NOMES_NIVEL = {"iniciante": "Iniciante", "intermediario": "Intermediário", "avancado": "Avançado"}

CATEGORIAS = {
    "superior": [11, 12, 13, 8], "inferior": [9, 14],
    "perna": [9], "coxa": [9], "gluteo": [9], "quadriceps": [9],
    "panturrilha": [14],
    "braco": [8], "biceps": [8], "triceps": [8],
    "abdomen": [10], "abdominal": [10],
    "peito": [11], "costas": [12], "ombro": [13], "cardio": [15],
}

# Perguntas do fluxo de nível: (rótulo do botão, palavras-chave aceitas)
TEMPO = [
    ("Nunca pratiquei", ["nunca", "nao pratico", "zero", "comecando", "iniciando"]),
    ("Menos de 6 meses", ["menos de 6", "poucos meses", "alguns meses"]),
    ("De 6 meses a 2 anos", ["6 meses", "1 ano", "um ano", "2 anos", "dois anos"]),
    ("Mais de 2 anos", ["mais de 2", "anos", "bastante"]),
]
FREQ = [
    ("1 a 2 vezes", ["1", "2", "uma", "duas"]),
    ("3 a 4 vezes", ["3", "4", "tres", "quatro"]),
    ("5 ou mais vezes", ["5", "6", "7", "cinco", "todo dia"]),
]
OBJETIVO = [
    ("Emagrecer", ["emagrec", "perder peso", "secar"]),
    ("Ganhar massa", ["massa", "hipertrofia", "ganhar", "crescer"]),
    ("Condicionamento", ["condicion", "resistencia", "folego"]),
    ("Saúde e bem-estar", ["saude", "bem", "qualidade"]),
]
LESAO = [
    ("Não tenho", ["nao", "nenhum", "nada"]),
    ("Tenho lesão ou restrição", ["sim", "tenho", "lesao", "dor", "restri"]),
]
FOCO = [
    ("Superiores", ["superior", "parte de cima", "peito", "costas", "ombro", "braco"]),
    ("Inferiores", ["inferior", "perna", "gluteo", "coxa", "panturrilha"]),
    ("Corpo todo", ["corpo todo", "full body", "geral"]),
]
FOCO_ID = ["superiores", "inferiores", "corpo_todo"]
DURACAO = [
    ("Treino completo", ["completo", "normal", "tenho tempo"]),
    ("Expresso (20 min)", ["expresso", "rapido", "20", "pouco tempo", "curto"]),
]


# ---------------------------------------------------------------- utilitários
def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def tem(texto, palavras):
    return any(p in texto for p in palavras)


def variar(*opcoes):
    return random.choice(opcoes)


def rotulos(opcoes):
    return [o[0] for o in opcoes]


def mascarar(texto):
    """RNF08/09: esconde números longos (CPF, matrícula) no histórico exibido."""
    return re.sub(r"\d[\d.\-/]{2,}\d", "•••", texto)


def escolher(texto, opcoes, numerico=True):
    """Devolve o índice da opção que combina com o texto (ou None)."""
    t = texto.strip()
    if numerico and t.isdigit() and 1 <= int(t) <= len(opcoes):
        return int(t) - 1
    for i, (rotulo, _) in enumerate(opcoes):
        if normalizar(rotulo) == t:
            return i
    for i, (_, chaves) in enumerate(opcoes):
        if any(c in t for c in chaves):
            return i
    return None


def novo_estado():
    return {
        "fluxo": None, "etapa": None, "dados": {},
        "nivel": None, "perfil": {}, "aluno": None,
        "reservas": {a["id"]: list(a["inscritos"]) for a in AULAS},
        "ultimo_treino": None, "ajuste": 0, "falhas": 0,
    }


def _limpar_fluxo(estado):
    estado["fluxo"] = None
    estado["etapa"] = None
    estado["dados"] = {}


def _recepcao():
    tel = academia["recepcao_telefone"]
    return variar(
        f"Claro! Você pode falar com a recepção pelo {tel} 😊",
        f"Sem problemas! O contato da recepção é {tel}.",
        f"Pode deixar! Liga pra recepção no {tel} que eles te ajudam.",
    ), []


def _menu():
    return ("Posso te ajudar com:\n\n"
            "- Montar seu treino (com aquecimento e séries)\n"
            "- Agendar ou cancelar aulas coletivas\n"
            "- Horários, planos, modalidades e endereço\n"
            "- Sugestões de exercícios\n\n"
            "É só escrever ou tocar numa opção 💜"), MENU_OPCOES


# ---------------------------------------------------------------- aulas
def _aula(aula_id):
    return next(a for a in AULAS if a["id"] == aula_id)


def _rotulo_aula(a):
    return f"{a['modalidade']} {a['dia']} {a['hora']}"


def _vagas(estado, a):
    return a["vagas"] - len(estado["reservas"][a["id"]])


def _reservas_do_aluno(estado):
    mat = estado["aluno"]
    return [a for a in AULAS if mat in estado["reservas"][a["id"]]]


def _achar_aula(texto, aulas):
    if texto.strip().isdigit():
        i = int(texto.strip())
        if 1 <= i <= len(aulas):
            return aulas[i - 1]
    nums = {int(n) for n in re.findall(r"\d+", texto)}
    cands = [a for a in aulas if normalizar(a["dia"]) in texto and int(a["hora"][:2]) in nums]
    if len(cands) > 1:
        cands = [a for a in cands if normalizar(a["modalidade"]) in texto] or cands
    return cands[0] if cands else None


def _proxima_ocorrencia(aula, agora):
    h, m = map(int, aula["hora"].split(":"))
    dias = (aula["dia_semana"] - agora.weekday()) % 7
    dt = agora.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(days=dias)
    if dt <= agora:
        dt += timedelta(days=7)
    return dt


def _validar_regras(estado, aula):
    """RN05, RN08 e RN09. Devolve mensagem de erro ou None."""
    mat = estado["aluno"]
    if _vagas(estado, aula) <= 0:
        return f"A aula **{_rotulo_aula(aula)}** está lotada 😕"
    if mat in estado["reservas"][aula["id"]]:
        return f"Você já tem reserva em **{_rotulo_aula(aula)}**."
    for outra in _reservas_do_aluno(estado):
        if outra["dia_semana"] == aula["dia_semana"] and outra["hora"] == aula["hora"]:
            return (f"Esse horário conflita com sua reserva em "
                    f"**{_rotulo_aula(outra)}**.")
    plano = ALUNOS[mat]["plano"]
    limite = LIMITE_RESERVAS[plano]
    if len(_reservas_do_aluno(estado)) >= limite:
        return (f"Seu plano {plano} permite até **{limite}** reservas ao mesmo tempo, "
                "e você já atingiu o limite. Cancele uma reserva para agendar outra.")
    return None


def _buscar_aluno(digitos):
    if not digitos:
        return None
    for mat, a in ALUNOS.items():
        if digitos == mat or digitos == a["cpf"]:
            return mat
    return None


def _validar_id(texto, estado):
    """RN01. Devolve (ok, resposta_se_falhou)."""
    mat = _buscar_aluno(re.sub(r"\D", "", texto))
    if mat is None:
        d = estado["dados"]
        d["tentativas"] = d.get("tentativas", 0) + 1
        if d["tentativas"] >= 3:
            _limpar_fluxo(estado)
            tel = academia["recepcao_telefone"]
            return False, (f"Não consegui validar seu cadastro. Fale com a recepção pelo {tel} 😊", [])
        return False, ("Não encontrei esse número no cadastro. Confira e envie de novo "
                       "(matrícula ou CPF, só números).", ["Falar com a recepção"])
    if not ALUNOS[mat]["ativo"]:
        _limpar_fluxo(estado)
        tel = academia["recepcao_telefone"]
        return False, (f"Seu cadastro consta como **inativo**. A recepção resolve isso pra você: {tel}.", [])
    estado["aluno"] = mat
    return True, None


PEDIR_ID = ("Para isso preciso validar seu cadastro. Me envie seu **número de matrícula "
            "ou CPF** (só números). Eu não deixo esse dado visível na conversa 🔒")


# ---------------------------------------------------------------- fluxo: agendar
def _iniciar_agendar(texto, estado):
    estado["fluxo"] = "agendar"
    estado["dados"] = {}
    for m in {a["modalidade"] for a in AULAS}:
        if normalizar(m) in texto:
            estado["dados"]["filtro"] = m
    if estado["aluno"]:
        return _mostrar_aulas(estado)
    estado["etapa"] = "id"
    return PEDIR_ID, []


def _mostrar_aulas(estado):
    d = estado["dados"]
    aulas = [a for a in AULAS if not d.get("filtro") or a["modalidade"] == d["filtro"]]
    linhas, botoes = [], []
    for i, a in enumerate(aulas, 1):
        v = _vagas(estado, a)
        linhas.append(f"{i}. {_rotulo_aula(a)} — {f'{v} vaga(s)' if v > 0 else 'lotada'}")
        if v > 0:
            botoes.append(_rotulo_aula(a))
    d["lista"] = [a["id"] for a in aulas]
    d["botoes"] = botoes
    estado["etapa"] = "aula"
    nome = ALUNOS[estado["aluno"]]["nome"].split()[0]
    return (f"Cadastro validado, {nome}! ✅ Estas são as aulas coletivas:\n\n" + "\n".join(linhas)
            + "\n\nQual você quer reservar?"), botoes


def _fluxo_agendar(texto, estado, agora):
    d = estado["dados"]
    etapa = estado["etapa"]
    if etapa == "id":
        ok, resp = _validar_id(texto, estado)
        return _mostrar_aulas(estado) if ok else resp
    if etapa == "aula":
        aula = _achar_aula(texto, [_aula(i) for i in d["lista"]])
        if aula is None:
            return "Não identifiquei a aula 😅 Toque numa opção ou diga o dia e a hora.", d["botoes"]
        erro = _validar_regras(estado, aula)
        if erro:
            return erro + "\n\nEscolha outro horário:", d["botoes"]
        d["aula"] = aula["id"]
        estado["etapa"] = "confirma"
        return f"Posso confirmar a reserva em **{_rotulo_aula(aula)}**?", ["Sim, confirmar", "Não"]
    if etapa == "confirma":
        palavras = set(re.findall(r"\w+", texto))
        if palavras & {"nao", "cancela", "desisto"}:
            _limpar_fluxo(estado)
            return "Tudo bem, não reservei nada.", ["Agendar aula", "Menu"]
        if palavras & {"sim", "confirmo", "confirmar", "pode", "ok", "isso"}:
            aula = _aula(d["aula"])
            erro = _validar_regras(estado, aula)  # revalida (vaga pode ter acabado)
            if erro:
                _limpar_fluxo(estado)
                return erro, ["Agendar aula", "Menu"]
            estado["reservas"][aula["id"]].append(estado["aluno"])
            # RN07: só confirma quando o registro aparece no sistema
            if estado["aluno"] in estado["reservas"][aula["id"]]:
                _limpar_fluxo(estado)
                protocolo = f"VIT-{aula['id'].upper()}-{estado['aluno']}"
                return (f"Reserva confirmada! 🎉 **{_rotulo_aula(aula)}**\n\n"
                        f"Protocolo: `{protocolo}`\n\nChegue 10 minutos antes. "
                        f"Cancelamentos até {CANCELAR_ATE_HORAS} h antes da aula."), \
                    ["Minhas reservas", "Montar meu treino", "Menu"]
            _limpar_fluxo(estado)
            return "Não consegui registrar a reserva no sistema. Tente de novo ou fale com a recepção.", []
        return "Responda **sim** para confirmar ou **não** para desistir.", ["Sim, confirmar", "Não"]


# ---------------------------------------------------------------- fluxo: cancelar / ver reservas
def _iniciar_cancelar(estado, so_ver=False):
    estado["fluxo"] = "cancelar"
    estado["dados"] = {"so_ver": so_ver}
    if estado["aluno"]:
        return _mostrar_reservas(estado, datetime.now())
    estado["etapa"] = "id"
    return PEDIR_ID, []


def _mostrar_reservas(estado, agora):
    d = estado["dados"]
    reservas = _reservas_do_aluno(estado)
    if not reservas:
        _limpar_fluxo(estado)
        return "Você não tem nenhuma reserva no momento.", ["Agendar aula", "Menu"]
    linhas = [f"{i}. {_rotulo_aula(a)}" for i, a in enumerate(reservas, 1)]
    if d.get("so_ver"):
        _limpar_fluxo(estado)
        return "Suas reservas:\n\n" + "\n".join(linhas), ["Agendar aula", "Cancelar uma reserva", "Menu"]
    d["lista"] = [a["id"] for a in reservas]
    d["botoes"] = [_rotulo_aula(a) for a in reservas]
    estado["etapa"] = "escolha"
    return "Suas reservas:\n\n" + "\n".join(linhas) + "\n\nQual você quer cancelar?", d["botoes"]


def _fluxo_cancelar(texto, estado, agora):
    d = estado["dados"]
    etapa = estado["etapa"]
    if etapa == "id":
        ok, resp = _validar_id(texto, estado)
        return _mostrar_reservas(estado, agora) if ok else resp
    if etapa == "escolha":
        aula = _achar_aula(texto, [_aula(i) for i in d["lista"]])
        if aula is None:
            return "Não identifiquei a reserva 😅 Toque numa opção.", d["botoes"]
        faltam = _proxima_ocorrencia(aula, agora) - agora
        if faltam < timedelta(hours=CANCELAR_ATE_HORAS):
            _limpar_fluxo(estado)
            return (f"A aula **{_rotulo_aula(aula)}** começa em menos de {CANCELAR_ATE_HORAS} h, "
                    f"então já não dá para cancelar por aqui. Fale com a recepção: "
                    f"{academia['recepcao_telefone']}."), []
        d["aula"] = aula["id"]
        estado["etapa"] = "confirma"
        return f"Confirma o cancelamento de **{_rotulo_aula(aula)}**?", ["Sim, cancelar", "Não"]
    if etapa == "confirma":
        palavras = set(re.findall(r"\w+", texto))
        if palavras & {"nao", "desisto", "manter"}:
            _limpar_fluxo(estado)
            return "Ok, mantive sua reserva 👍", ["Menu"]
        if palavras & {"sim", "confirmo", "cancelar", "pode", "ok"}:
            aula = _aula(d["aula"])
            estado["reservas"][aula["id"]].remove(estado["aluno"])
            if estado["aluno"] not in estado["reservas"][aula["id"]]:
                _limpar_fluxo(estado)
                return (f"Reserva em **{_rotulo_aula(aula)}** cancelada e vaga liberada ✅"), \
                    ["Agendar aula", "Menu"]
            _limpar_fluxo(estado)
            return "Não consegui cancelar no sistema. Fale com a recepção.", []
        return "Responda **sim** para cancelar ou **não** para manter.", ["Sim, cancelar", "Não"]


# ---------------------------------------------------------------- fluxo: nível
def _iniciar_nivel(estado, depois=None, pre=None):
    estado["fluxo"] = "nivel"
    estado["etapa"] = "tempo"
    estado["dados"] = {"depois": depois, "pre": pre or {}}
    estado["perfil"] = {}
    return "Há quanto tempo você pratica musculação?", rotulos(TEMPO)


def _concluir_nivel(estado, agora):
    p = estado["perfil"]
    score = p["tempo"] + p["freq"]
    if p["tempo"] == 0 or score <= 1:
        nivel = "iniciante"
    elif score <= 3:
        nivel = "intermediario"
    else:
        nivel = "avancado"
    estado["nivel"] = nivel
    estado["ultimo_treino"] = None
    msg = f"Pronto! Classifiquei você como **{NOMES_NIVEL[nivel]}** 💪"
    if p.get("lesao"):
        msg += ("\n\nComo você tem lesão ou restrição, converse com o professor antes de treinar. "
                f"Recepção: {academia['recepcao_telefone']}.")
    depois, pre = estado["dados"].get("depois"), estado["dados"].get("pre", {})
    _limpar_fluxo(estado)
    if depois == "treino":
        resp, ops = _iniciar_treino(estado, pre)
        return msg + "\n\n" + resp, ops
    return msg, ["Montar meu treino", "Aquecimento", "Agendar aula"]


def _fluxo_nivel(texto, estado, agora):
    p, etapa = estado["perfil"], estado["etapa"]
    perguntas = {
        "tempo": (TEMPO, "freq", "Quantas vezes por semana você consegue treinar?", FREQ, True),
        "freq": (FREQ, "obj", "Qual é o seu objetivo principal?", OBJETIVO, False),
        "obj": (OBJETIVO, "lesao", "Você tem alguma lesão ou restrição médica?", LESAO, True),
    }
    if etapa in perguntas:
        atual, proxima, pergunta, prox_opcoes, _ = perguntas[etapa]
        i = escolher(texto, atual, numerico=(etapa != "freq"))
        if i is None:
            return "Não entendi 😅 Escolha uma das opções:", rotulos(atual)
        p[etapa] = i
        estado["etapa"] = proxima
        return pergunta, rotulos(prox_opcoes)
    if etapa == "lesao":
        i = escolher(texto, LESAO)
        if i is None:
            return "Não entendi 😅 Escolha uma das opções:", rotulos(LESAO)
        p["lesao"] = i == 1
        return _concluir_nivel(estado, agora)


# ---------------------------------------------------------------- fluxo: treino
def _iniciar_treino(estado, pre):
    if estado["nivel"] is None:
        resp, ops = _iniciar_nivel(estado, depois="treino", pre=pre)
        return ("Para montar um treino seguro, preciso saber seu nível. "
                "São 4 perguntinhas rápidas.\n\n" + resp), ops
    estado["fluxo"] = "treino"
    estado["dados"] = dict(pre)
    return _treino_proximo(estado)


def _treino_proximo(estado):
    d = estado["dados"]
    if d.get("foco") is None:
        estado["etapa"] = "foco"
        return "Qual região você quer treinar hoje?", rotulos(FOCO)
    if d.get("express") is None:
        estado["etapa"] = "duracao"
        return "Quanto tempo você tem?", rotulos(DURACAO)
    estado["ultimo_treino"] = (d["foco"], d["express"])
    estado["ajuste"] = 0
    _limpar_fluxo(estado)
    return _texto_treino(estado)


def _fluxo_treino(texto, estado, agora):
    d, etapa = estado["dados"], estado["etapa"]
    if etapa == "foco":
        i = escolher(texto, FOCO)
        if i is None:
            return "Não entendi 😅 Escolha uma das opções:", rotulos(FOCO)
        d["foco"] = i
    elif etapa == "duracao":
        i = escolher(texto, DURACAO)
        if i is None:
            return "Não entendi 😅 Escolha uma das opções:", rotulos(DURACAO)
        d["express"] = i == 1
    return _treino_proximo(estado)


def _texto_treino(estado):
    foco_i, express = estado["ultimo_treino"]
    nivel = estado["nivel"]
    t = TREINOS[FOCO_ID[foco_i]]
    s = SERIES[nivel]
    n = max(s["min"], min(s["max"], s["series"] + estado["ajuste"]))  # RN03
    n2 = max(2, n - 1)

    if express:
        trabalho, descanso = EXPRESSO[nivel]
        lista = "\n".join(f"- {e}" for e in t["principal"] + t["secundario"])
        texto = (f"**Treino expresso — {t['nome']}** (nível {NOMES_NIVEL[nivel]})\n\n"
                 "**1) Aquecimento (4 min)**\n\n"
                 f"- Esteira ou bicicleta em ritmo leve (3 min)\n- {t['aquecimento']}\n\n"
                 f"**2) Circuito (12 min)** — 2 voltas, {trabalho} s de trabalho e {descanso} s de descanso em cada exercício:\n\n"
                 f"{lista}\n\n"
                 "**3) Alongamento (4 min)**")
    else:
        aq = "\n".join(f"- {a}" for a in AQUECIMENTO[nivel])
        pri = "\n".join(f"- {e}" for e in t["principal"])
        sec = "\n".join(f"- {e}" for e in t["secundario"])
        texto = (f"**Seu treino — {t['nome']}** (nível {NOMES_NIVEL[nivel]})\n\n"
                 f"**1) Aquecimento** (escolha uma opção + o específico)\n\n{aq}\n- Específico: {t['aquecimento']}\n\n"
                 f"**2) Treino principal** — {n} séries de {s['reps']} repetições, descanso {s['descanso']}\n\n{pri}\n\n"
                 f"**3) Treino secundário** — {n2} séries de 12 a 15 repetições, descanso 45 a 60 s\n\n{sec}")
    texto += ("\n\n⚠️ É uma sugestão geral. Peça a um instrutor da academia para ajustar cargas e técnica.")
    if estado["perfil"].get("lesao"):
        texto += "\n\nLembre de avisar o professor sobre sua lesão ou restrição."
    ops = ["Mais séries", "Menos séries",
           "Treino completo" if express else "Treino expresso (20 min)", "Agendar aula"]
    if express:
        ops = ops[2:3] + ops[3:]
    return texto, ops


def _ajustar_treino(texto, estado):
    if estado["ultimo_treino"] is None:
        return None
    foco_i, express = estado["ultimo_treino"]
    nivel = estado["nivel"]
    s = SERIES[nivel]
    if tem(texto, ["mais serie", "aumentar serie", "mais volume", "aumentar volume"]):
        if s["series"] + estado["ajuste"] >= s["max"]:
            r, o = _texto_treino(estado)
            return (f"Esse já é o máximo recomendado para o nível {NOMES_NIVEL[nivel]} "
                    f"({s['max']} séries) 😉\n\n" + r), o
        estado["ajuste"] += 1
        return _texto_treino(estado)
    if tem(texto, ["menos serie", "diminuir serie", "reduzir serie", "menos volume"]):
        if s["series"] + estado["ajuste"] <= s["min"]:
            r, o = _texto_treino(estado)
            return (f"Esse já é o mínimo recomendado para o nível {NOMES_NIVEL[nivel]} "
                    f"({s['min']} séries).\n\n" + r), o
        estado["ajuste"] -= 1
        return _texto_treino(estado)
    if escolher(texto, FOCO, numerico=False) is None:
        if tem(texto, ["expresso", "rapido"]) and not express:
            estado["ultimo_treino"] = (foco_i, True)
            return _texto_treino(estado)
        if "treino completo" in texto and express:
            estado["ultimo_treino"] = (foco_i, False)
            return _texto_treino(estado)
    return None


def _texto_aquecimento(estado):
    nivel = estado["nivel"]
    if nivel:
        itens = "\n".join(f"- {a}" for a in AQUECIMENTO[nivel])
        return (f"Aquecimento recomendado para o nível **{NOMES_NIVEL[nivel]}**:\n\n{itens}\n\n"
                "Ele prepara músculos e articulações e ajuda a prevenir lesões 💪"), ["Montar meu treino"]
    itens = "\n".join(f"- {a}" for a in AQUECIMENTO["iniciante"])
    return ("Algumas opções de aquecimento:\n\n" + itens +
            "\n\nSe me disser seu nível, eu adapto a recomendação."), ["Descobrir meu nível", "Montar meu treino"]


# ---------------------------------------------------------------- informações (UC01)
def _lista_modalidades():
    mods = list(academia["modalidades"])
    for a in AULAS:
        if a["modalidade"] not in mods:
            mods.append(a["modalidade"])
    return mods


def _contexto_ia():
    h = "; ".join(f"{d}: {v}" for d, v in academia["horarios"].items())
    return (f"Academia {academia['nome']}. Horários: {h}. Planos: {academia['planos']}. "
            f"Modalidades: {', '.join(_lista_modalidades())}. Endereço: {academia['endereco']}. "
            f"Recepção: {academia['recepcao_telefone']}.")


def _info(texto, palavras, estado):
    """Intents de consulta. Devolve (texto, opcoes) ou None."""
    if tem(texto, ["vaga", "grade", "aulas coletivas", "horario das aulas", "quais aulas"]):
        linhas = []
        for a in AULAS:
            v = _vagas(estado, a)
            linhas.append(f"- {_rotulo_aula(a)} — {f'{v} vaga(s)' if v > 0 else 'lotada'}")
        return "Grade de aulas coletivas:\n\n" + "\n".join(linhas), ["Agendar aula", "Menu"]
    if palavras & {"abre", "fecha", "abrem", "fecham", "aberto"} or tem(texto, ["horario", "funcionamento", "que horas"]):
        linhas = [f"- {dia}: {h}" for dia, h in academia["horarios"].items()]
        intro = variar("Nosso horário é este:", "Funcionamos assim:", "Olha só nossos horários:")
        return intro + "\n\n" + "\n".join(linhas) + "\n\nA VitaAI atende você 24 h por dia 💜", ["Agendar aula", "Menu"]
    if tem(texto, ["mensalidade", "plano", "valor", "preco"]):
        extra = "\n\nLimite de reservas de aula: " + ", ".join(
            f"{p}: {n}" for p, n in LIMITE_RESERVAS.items())
        return f"{academia['planos']}{extra}", ["Falar com a recepção", "Menu"]
    if tem(texto, ["modalidade", "aula", "servico", "spin", "funcional"]):
        intro = variar("Por aqui temos:", "Estas são nossas modalidades:")
        return intro + "\n\n" + "\n".join(f"- {m}" for m in _lista_modalidades()), ["Agendar aula", "Menu"]
    if tem(texto, ["endereco", "onde fica", "localizacao", "como chegar"]):
        return f"Nosso endereço é {academia['endereco']}. Te esperamos por lá! 💜", ["Menu"]
    if tem(texto, ["regra", "politica", "limite"]):
        return ("Regras das aulas coletivas:\n\n"
                "- Reserva só com matrícula ou CPF válidos\n"
                "- Sem reservas duplicadas ou em horários conflitantes\n"
                f"- Limite de reservas por plano ({', '.join(f'{p}: {n}' for p, n in LIMITE_RESERVAS.items())})\n"
                f"- Cancelamento até {CANCELAR_ATE_HORAS} h antes da aula"), ["Agendar aula", "Menu"]
    return None


# ---------------------------------------------------------------- exercícios (API)
def _exercicios_api(texto):
    categorias = []
    for palavra, ids in CATEGORIAS.items():
        if palavra in texto:
            categorias += [i for i in ids if i not in categorias]
    categorias = categorias or [None]
    por_cat = 2 if len(categorias) > 1 else 5
    itens = []
    for c in categorias:
        itens += buscar_exercicios(c, por_cat)
    if not itens:
        return (f"Não consegui buscar os exercícios agora 😕 Fale com a recepção: "
                f"{academia['recepcao_telefone']}."), ["Montar meu treino", "Falar com a recepção"]
    linhas = [f"**{e['nome']}**\n\n{e['descricao']}" for e in itens]
    abertura = variar("Separei estes exercícios pra você:", "Olha só algumas opções:")
    return (abertura + "\n\n" + "\n\n---\n\n".join(linhas) +
            "\n\nPeça a um instrutor para ajustar séries e cargas 💪"), ["Montar meu treino", "Menu"]


# ---------------------------------------------------------------- roteador principal
FLUXOS = {
    "agendar": _fluxo_agendar,
    "cancelar": _fluxo_cancelar,
    "nivel": _fluxo_nivel,
    "treino": _fluxo_treino,
}


def responder(pergunta, estado, agora=None):
    agora = agora or datetime.now()
    texto = normalizar(pergunta)
    palavras = set(re.findall(r"\w+", texto))

    # Dentro de um fluxo guiado
    if estado["fluxo"]:
        if tem(texto, ["recepcao", "atendente", "humano"]):
            _limpar_fluxo(estado)
            return _recepcao()
        if palavras & {"sair", "voltar", "menu", "parar"} or tem(texto, ["desisti", "deixa pra la"]):
            _limpar_fluxo(estado)
            return _menu()
        estado["falhas"] = 0
        return FLUXOS[estado["fluxo"]](texto, estado, agora)

    resp = _rotear(pergunta, texto, palavras, estado, agora)
    if resp is not None:
        estado["falhas"] = 0
        return resp

    # Não entendeu: IA opcional, depois redirecionamento (RF09)
    estado["falhas"] += 1
    if conversar_ia:
        r = conversar_ia(pergunta, _contexto_ia())
        if r:
            return r, ["Menu"]
    tel = academia["recepcao_telefone"]
    if estado["falhas"] >= 2:
        return (f"Ainda não consegui entender 😕 Para não te deixar na mão, fale com a "
                f"recepção ou com um professor: {tel}."), ["Menu", "Falar com a recepção"]
    return variar(
        f"Hmm, essa eu não sei responder. Mas a recepção pode te ajudar: {tel} 😊",
        f"Ainda não consigo ajudar com isso. Fala com a recepção pelo {tel}, tá?",
    ), ["Menu"]


def _rotear(pergunta, texto, palavras, estado, agora):
    # 0. Conversa social (mensagens curtas)
    if len(palavras) <= 4:
        if palavras & {"oi", "ola", "opa", "eae", "hey"} or tem(texto, ["bom dia", "boa tarde", "boa noite"]):
            return variar(
                "Oi! 💜 Tudo bem? Como posso te ajudar hoje?",
                "Olá! Que bom ter você aqui! Sobre o que quer saber?",
            ), MENU_OPCOES
        if tem(texto, ["obrigad", "valeu", "brigad"]):
            return variar("Por nada! 💜", "Sempre que precisar, é só chamar!", "Disponha! Bons treinos 💪"), []
        if palavras & {"menu", "ajuda"} or tem(texto, ["o que voce faz", "o que voce pode"]):
            return _menu()

    # 1. Atendimento humano (RF09)
    if tem(texto, ["recepcao", "atendente", "humano", "falar com", "professor", "telefone"]):
        return _recepcao()

    # 2. Ajustes no último treino
    r = _ajustar_treino(texto, estado)
    if r:
        return r

    # 3. Reservas
    if tem(texto, ["minhas reserva", "minha reserva", "meus agendamentos", "ver reserva"]):
        return _iniciar_cancelar(estado, so_ver=True)
    if tem(texto, ["cancel", "desmarcar"]):
        return _iniciar_cancelar(estado)
    if tem(texto, ["agend", "marcar", "reservar", "inscrever"]):
        return _iniciar_agendar(texto, estado)

    # 4. Nível (RF03)
    if tem(texto, ["nivel", "condicionamento", "classific", "avaliacao", "avaliar"]):
        if estado["nivel"] and not tem(texto, ["refaz", "novamente", "reclass", "de novo", "avaliacao"]):
            return (f"Seu nível atual é **{NOMES_NIVEL[estado['nivel']]}**.",
                    ["Refazer avaliação", "Montar meu treino"])
        return _iniciar_nivel(estado)
    if tem(texto, ["descobrir meu nivel"]):
        return _iniciar_nivel(estado)

    # 5. Aquecimento (RF04) e treino (RF05, RF06)
    if tem(texto, ["aquecimento", "aquecer"]):
        return _texto_aquecimento(estado)
    if tem(texto, ["treino", "ficha", "malhar", "treinar"]):
        pre = {}
        i = escolher(texto, FOCO, numerico=False)
        pre["foco"] = i
        pre["express"] = (True if tem(texto, ["expresso", "rapido", "20 min", "pouco tempo"]) else None)
        return _iniciar_treino(estado, pre)

    # 6. Informações da academia (RF07)
    r = _info(texto, palavras, estado)
    if r:
        return r

    # 7. Exercícios pela API
    if "exercicio" in texto or any(p in texto for p in CATEGORIAS):
        return _exercicios_api(texto)

    return None
