"""Cérebro da VitaAI: intenções, fluxos guiados e regras de negócio.

responder(pergunta, estado) -> (texto, opcoes)
  - texto: resposta em markdown
  - opcoes: botões de resposta rápida (RNF07)
"""
import random
import re
import unicodedata
from datetime import datetime, timedelta

from informacoes import academia
from base_dados import (
    ALUNOS, GRADE, LIMITE_RESERVAS, CANCELAR_ATE_HORAS, SERIES, AQUECIMENTO,
    TREINOS, EXECUCAO, CHAVES_EXERCICIO, EXPRESSO,
)
from api_exercicios import buscar_exercicios

try:
    from ia import conversar_ia
except Exception: 
    conversar_ia = None

MENU_OPCOES = [
    "Montar meu treino",
    "Agendar aula",
    "Minhas reservas",
    "Horário de funcionamento",
    "Falar com a recepção",
]

NOMES_NIVEL = {"iniciante": "Iniciante", "intermediario": "Intermediário", "avancado": "Avançado"}
NIVEL_MIN = {"iniciante": "iniciante", "intermediario": "intermediário", "avancado": "avançado"}

CATEGORIAS = {
    "superior": [11, 12, 13, 8], "inferior": [9, 14],
    "perna": [9], "coxa": [9], "gluteo": [9], "quadriceps": [9],
    "panturrilha": [14],
    "braco": [8], "biceps": [8], "triceps": [8],
    "abdomen": [10], "abdominal": [10],
    "peito": [11], "costas": [12], "ombro": [13], "cardio": [15],
}

FOCO = [
    ("Superiores", ["superior", "parte de cima", "peito", "costas", "ombro", "braco"]),
    ("Inferiores", ["inferior", "perna", "gluteo", "coxa", "panturrilha"]),
    ("Corpo todo", ["corpo todo", "full body", "geral"]),
]
FOCO_ID = ["superiores", "inferiores", "corpo_todo"]
FOCO_PADRAO = 1

TEMPO_OPCOES = ["Nunca treinei", "Mais de 6 meses parado", "Menos de 6 meses parado", "Treino regularmente"]
OBJETIVO_OPCOES = ["Ganhar massa", "Emagrecer", "Melhorar o fôlego", "Saúde e bem-estar"]

DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
NOMES_DIA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
             "sexta-feira", "sábado", "domingo"]

NUMEROS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
           "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12}
UNIDADES = {"semana": 0.25, "semanas": 0.25, "mes": 1, "meses": 1, "ano": 12, "anos": 12}

EXPRESSO_PALAVRAS = ["20 min", "corrido", "pouco tempo", "expresso", "rapid", "so tenho"]


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def tem(texto, palavras):
    return any(p in texto for p in palavras)


def variar(*opcoes):
    return random.choice(opcoes)


def mascarar(texto):
    """RNF08/09: esconde números longos (CPF, matrícula) no histórico exibido."""
    return re.sub(r"\d[\d.\-/]{2,}\d", "•••", texto)


def escolher(texto, opcoes, numerico=True):
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


def _frase_lista(itens):
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def novo_estado():
    return {
        "fluxo": None, "etapa": None, "dados": {},
        "nivel": None, "perfil": {}, "aluno": None,
        "reservas": {}, "slots": {},
        "ultimo_treino": None, "ajuste": 0, "aquecido": False,
        "foco_pref": None, "aguardando": None, "falhas": 0,
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
            "- Descobrir seu nível e montar seu treino\n"
            "- Indicar o aquecimento e uma série expressa\n"
            "- Agendar ou cancelar aulas coletivas\n"
            "- Horários, planos, modalidades e endereço\n\n"
            "É só escrever ou tocar numa opção 💜"), MENU_OPCOES


def _parse_data(texto, agora):
    hoje = agora.date()
    if "depois de amanha" in texto:
        return hoje + timedelta(days=2)
    if "amanha" in texto:
        return hoje + timedelta(days=1)
    if "hoje" in texto:
        return hoje
    for i, d in enumerate(DIAS):
        if d in texto:
            return hoje + timedelta(days=(i - agora.weekday()) % 7)
    m = re.search(r"(\d{1,2})/(\d{1,2})", texto)
    if m:
        try:
            return hoje.replace(month=int(m.group(2)), day=int(m.group(1)))
        except ValueError:
            return None
    return None


def _parse_hora(texto):
    m = re.search(r"(\d{1,2})\s*[:h]\s*(\d{2})", texto)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"\b(\d{1,2})\s*(?:h|horas?)?\b", texto)
    if m:
        return int(m.group(1)), None
    return None


def _dia_rel(data, agora):
    delta = (data - agora.date()).days
    if delta == 0:
        return "hoje"
    if delta == 1:
        return "amanhã"
    return f"{NOMES_DIA[data.weekday()]} ({data:%d/%m})"


def _dt(slot):
    h, m = map(int, slot["hora"].split(":"))
    d = slot["data"]
    return datetime(d.year, d.month, d.day, h, m)


def _slot(estado, g, data, hora):
    key = f"{g['modalidade']}|{data.isoformat()}|{hora}"
    if key not in estado["reservas"]:
        n = g["ocupadas"].get(hora, 0)
        estado["reservas"][key] = [f"9{i:04d}" for i in range(n)]  # outros alunos
    estado["slots"][key] = {"key": key, "modalidade": g["modalidade"], "data": data,
                            "hora": hora, "vagas": g["vagas"]}
    return estado["slots"][key]


def _slots_do_dia(estado, data, modalidade, agora):
    out = []
    for g in GRADE:
        if modalidade and g["modalidade"] != modalidade:
            continue
        if data.weekday() not in g["dias"]:
            continue
        for hora in g["horas"]:
            s = _slot(estado, g, data, hora)
            if _dt(s) > agora:
                out.append(s)
    return out


def _vagas(estado, slot):
    return slot["vagas"] - len(estado["reservas"][slot["key"]])


def _reservas_do_aluno(estado, agora):
    mat = estado["aluno"]
    res = [s for k, s in estado["slots"].items()
           if mat in estado["reservas"].get(k, []) and _dt(s) > agora]
    return sorted(res, key=_dt)


def _rotulo(slot, agora):
    return f"{slot['modalidade']} {_dia_rel(slot['data'], agora)} às {slot['hora']}"


def _rotulo_curto(slot):
    return f"{slot['modalidade']} {slot['data']:%d/%m} {slot['hora']}"


def _periodo(hora):
    h = int(hora[:2])
    return "Manhã" if h < 12 else ("Tarde" if h < 18 else "Noite")


def _linhas_periodos(slots):
    grupos = {}
    for s in slots:
        grupos.setdefault(_periodo(s["hora"]), []).append(s["hora"])
    return [f"- {p}: {_frase_lista(grupos[p])}" for p in ("Manhã", "Tarde", "Noite") if p in grupos]


def _achar_slot(texto, slots, agora, exigir_hora=False):
    if texto.strip().isdigit() and 1 <= int(texto.strip()) <= len(slots):
        return slots[int(texto.strip()) - 1]
    hr = _parse_hora(texto)
    data = _parse_data(texto, agora)
    if hr is None and (exigir_hora or data is None):
        return None
    cands = list(slots)
    if hr:
        cands = [s for s in cands if int(s["hora"][:2]) == hr[0]
                 and (hr[1] is None or int(s["hora"][3:]) == hr[1])]
    if data:
        cands = [s for s in cands if s["data"] == data]
    por_mod = [s for s in cands if normalizar(s["modalidade"]) in texto]
    cands = por_mod or cands
    return cands[0] if cands else None


def _validar_regras(estado, slot, agora):
    """RN05, RN08 e RN09. Devolve (tipo, mensagem) ou None."""
    mat = estado["aluno"]
    if _vagas(estado, slot) <= 0:
        return "vagas", f"A aula **{_rotulo(slot, agora)}** está lotada 😕"
    if mat in estado["reservas"][slot["key"]]:
        return "dup", f"Você já tem reserva em **{_rotulo(slot, agora)}**."
    ativas = _reservas_do_aluno(estado, agora)
    for o in ativas:
        if o["data"] == slot["data"] and o["hora"] == slot["hora"]:
            return "conflito", f"Esse horário conflita com sua reserva em **{_rotulo(o, agora)}**."
    plano = ALUNOS[mat]["plano"]
    limite = LIMITE_RESERVAS[plano]
    if len(ativas) >= limite:
        return "limite", (f"Seu plano {plano} permite até **{limite}** reservas ao mesmo tempo, "
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
            return False, (f"Não consegui validar seu cadastro. Fale com a recepção pelo "
                           f"{academia['recepcao_telefone']} 😊", [])
        return False, ("Não encontrei esse número no cadastro. Confira e envie de novo "
                       "(matrícula ou CPF, só números).", ["Falar com a recepção"])
    if not ALUNOS[mat]["ativo"]:
        _limpar_fluxo(estado)
        return False, (f"Seu cadastro consta como **inativo**. A recepção resolve isso pra você: "
                       f"{academia['recepcao_telefone']}.", [])
    estado["aluno"] = mat
    return True, None


PEDIR_ID = ("Para isso preciso validar seu cadastro. Me envie seu **número de matrícula "
            "ou CPF** (só números). Eu não deixo esse dado visível na conversa 🔒")


def _iniciar_agendar(texto, estado, agora):
    d = {"filtro": None, "data": _parse_data(texto, agora)}
    for g in GRADE:
        if normalizar(g["modalidade"]) in texto:
            d["filtro"] = g["modalidade"]
    estado["fluxo"] = "agendar"
    estado["dados"] = d
    if d["data"] is None:
        estado["etapa"] = "dia"
        return ("Para qual dia você quer agendar? Posso ver hoje, amanhã ou um dia da semana.",
                ["Hoje", "Amanhã"])
    return _mostrar_slots(estado, agora)


def _mostrar_slots(estado, agora, prefixo=""):
    d = estado["dados"]
    pedido = d["data"]
    slots, dia = [], pedido
    for i in range(8):
        dia = pedido + timedelta(days=i)
        slots = [s for s in _slots_do_dia(estado, dia, d["filtro"], agora) if _vagas(estado, s) > 0]
        if slots:
            break
    if not slots:
        filtro = d["filtro"]
        _limpar_fluxo(estado)
        quais = f"As aulas de {filtro} estão lotadas" if filtro else "Não há horários vagos"
        return (f"{quais} nos próximos dias 😕 Fale com a recepção para entrar na lista de "
                f"espera: {academia['recepcao_telefone']}."), []
    d["data"] = dia
    aviso = ""
    if dia != pedido:
        aviso = (f"Não encontrei horários vagos para {_dia_rel(pedido, agora)}. "
                 f"Os próximos são para {_dia_rel(dia, agora)}.\n\n")
    rel = _dia_rel(dia, agora)
    intro = "" if prefixo else "Posso realizar o agendamento para você agora mesmo! "
    mods = list(dict.fromkeys(s["modalidade"] for s in slots))
    if len(mods) == 1:
        corpo = (f"{intro}Para {rel}, temos os seguintes horários vagos na aula de {mods[0]}:\n\n"
                 + "\n".join(_linhas_periodos(slots)))
        botoes = [s["hora"] for s in slots]
    else:
        partes = []
        for m in mods:
            sm = [s for s in slots if s["modalidade"] == m]
            partes.append(f"**{m}**\n" + "\n".join(_linhas_periodos(sm)))
        corpo = f"{intro}Para {rel}, temos os seguintes horários vagos:\n\n" + "\n\n".join(partes)
        botoes = [f"{s['modalidade']} {s['hora']}" for s in slots]
    d["slots"] = [s["key"] for s in slots]
    d["botoes"] = botoes
    estado["etapa"] = "hora"
    return prefixo + aviso + corpo + "\n\nQual horário prefere reservar?", botoes


def _confirmar_reserva(estado, agora, validou_agora):
    d = estado["dados"]
    slot = estado["slots"][d["escolhido"]]
    erro = _validar_regras(estado, slot, agora)
    if erro:
        tipo, msg = erro
        if tipo == "limite":
            _limpar_fluxo(estado)
            return msg, ["Cancelar uma reserva", "Menu"]
        return _mostrar_slots(estado, agora, prefixo=msg + "\n\nEscolha outro horário.\n\n")
    estado["reservas"][slot["key"]].append(estado["aluno"])
    # RN07: só confirma quando o registro aparece no sistema
    if estado["aluno"] in estado["reservas"][slot["key"]]:
        _limpar_fluxo(estado)
        protocolo = (f"VIT-{slot['modalidade'][:3].upper()}-{slot['data']:%d%m}-"
                     f"{slot['hora'].replace(':', '')}-{estado['aluno']}")
        prefixo = "Matrícula validada! " if validou_agora else ""
        return (f"{prefixo}Sua vaga na aula de {slot['modalidade']} de "
                f"{_dia_rel(slot['data'], agora)} às {slot['hora']} está confirmada. 🎉\n\n"
                f"Comprovante da reserva: `{protocolo}`\n\nPosso te ajudar em algo mais?"), \
            ["Minhas reservas", "Montar meu treino", "Não, obrigado"]
    _limpar_fluxo(estado)
    return "Não consegui registrar a reserva no sistema. Tente de novo ou fale com a recepção.", []


def _fluxo_agendar(texto, estado, agora):
    d, etapa = estado["dados"], estado["etapa"]
    if etapa == "dia":
        data = _parse_data(texto, agora)
        if data is None:
            return "Não entendi o dia 😅 Escolha uma opção ou diga, por exemplo, \"sexta\".", ["Hoje", "Amanhã"]
        d["data"] = data
        return _mostrar_slots(estado, agora)
    if etapa == "hora":
        slot = _achar_slot(texto, [estado["slots"][k] for k in d["slots"]], agora, exigir_hora=True)
        if slot is None:
            return "Não identifiquei o horário 😅 Toque numa opção ou diga a hora.", d["botoes"]
        d["escolhido"] = slot["key"]
        if estado["aluno"]:
            return _confirmar_reserva(estado, agora, validou_agora=False)
        estado["etapa"] = "id"
        return "Para confirmar a reserva, por favor me informe o seu número de matrícula ou CPF.", []
    if etapa == "id":
        ok, resp = _validar_id(texto, estado)
        return _confirmar_reserva(estado, agora, validou_agora=True) if ok else resp


def _iniciar_cancelar(estado, agora, so_ver=False):
    estado["fluxo"] = "cancelar"
    estado["dados"] = {"so_ver": so_ver}
    if estado["aluno"]:
        return _mostrar_reservas(estado, agora)
    estado["etapa"] = "id"
    return PEDIR_ID, []


def _mostrar_reservas(estado, agora):
    d = estado["dados"]
    res = _reservas_do_aluno(estado, agora)
    if not res:
        _limpar_fluxo(estado)
        return "Você não tem nenhuma reserva no momento.", ["Agendar aula", "Menu"]
    linhas = [f"{i}. {_rotulo(s, agora)}" for i, s in enumerate(res, 1)]
    if d.get("so_ver"):
        _limpar_fluxo(estado)
        return "Suas reservas:\n\n" + "\n".join(linhas), ["Agendar aula", "Cancelar uma reserva", "Menu"]
    d["lista"] = [s["key"] for s in res]
    d["botoes"] = [_rotulo_curto(s) for s in res]
    estado["etapa"] = "escolha"
    return "Suas reservas:\n\n" + "\n".join(linhas) + "\n\nQual você quer cancelar?", d["botoes"]


def _fluxo_cancelar(texto, estado, agora):
    d, etapa = estado["dados"], estado["etapa"]
    if etapa == "id":
        ok, resp = _validar_id(texto, estado)
        return _mostrar_reservas(estado, agora) if ok else resp
    if etapa == "escolha":
        slot = _achar_slot(texto, [estado["slots"][k] for k in d["lista"]], agora)
        if slot is None:
            return "Não identifiquei a reserva 😅 Toque numa opção.", d["botoes"]
        if _dt(slot) - agora < timedelta(hours=CANCELAR_ATE_HORAS):
            _limpar_fluxo(estado)
            return (f"A aula **{_rotulo(slot, agora)}** começa em menos de {CANCELAR_ATE_HORAS} h, "
                    f"então já não dá para cancelar por aqui. Fale com a recepção: "
                    f"{academia['recepcao_telefone']}."), []
        d["escolhido"] = slot["key"]
        estado["etapa"] = "confirma"
        return f"Confirma o cancelamento de **{_rotulo(slot, agora)}**?", ["Sim, cancelar", "Não"]
    if etapa == "confirma":
        palavras = set(re.findall(r"\w+", texto))
        if palavras & {"nao", "desisto", "manter"}:
            _limpar_fluxo(estado)
            return "Ok, mantive sua reserva 👍", ["Menu"]
        if palavras & {"sim", "confirmo", "cancelar", "pode", "ok"}:
            slot = estado["slots"][d["escolhido"]]
            estado["reservas"][slot["key"]].remove(estado["aluno"])
            _limpar_fluxo(estado)
            return (f"Reserva em **{_rotulo(slot, agora)}** cancelada e vaga liberada ✅"), \
                ["Agendar aula", "Menu"]
        return "Responda **sim** para cancelar ou **não** para manter.", ["Sim, cancelar", "Não"]


def _duracao_meses(texto):
    if "meio ano" in texto:
        return 6
    m = re.search(r"(\d+|" + "|".join(NUMEROS) + r")\s*(semanas?|meses|mes|anos?)\b", texto)
    if not m:
        return None
    n = int(m.group(1)) if m.group(1).isdigit() else NUMEROS[m.group(1)]
    meses = n * UNIDADES[m.group(2)]
    if "menos de" in texto:
        meses -= 0.5
    return meses


def _classificar(texto):
    """Regra: parado há 6 meses ou mais (ou nunca treinou) = iniciante;
    parado há menos de 6 meses = intermediário; treina regularmente =
    intermediário (avançado se treina há 2 anos ou mais)."""
    meses = _duracao_meses(texto)
    parou = tem(texto, ["nao treino", "nao treinei", "nao pratico", "nao praticava", "parado", "parei"])
    regular = (not parou) and tem(texto, ["regularmente", "nao parei", "sem parar", "continuo",
                                          "ainda treino", "treino todo", "treino ha",
                                          "treinando ha", "ja treino"])
    if regular:
        return "avancado" if meses is not None and meses >= 24 else "intermediario"
    if meses is not None:
        return "iniciante" if meses >= 6 else "intermediario"
    if tem(texto, ["nunca", "jamais", "primeira vez", "nao treino", "nao pratico", "sedentar"]):
        return "iniciante"
    return None


def _iniciar_nivel(estado, depois=None, pre=None, boas_vindas=False):
    estado["fluxo"] = "nivel"
    estado["etapa"] = "tempo"
    estado["dados"] = {"depois": depois, "pre": pre or {}}
    estado["perfil"] = {}
    if boas_vindas:
        intro = (f"Olá! Seja muito bem-vindo à {academia['nome']}! Meu nome é VitaAI e vou te "
                 "acompanhar. Para eu montar a melhor rotina para você, me conta: ")
    else:
        intro = "Para montar o melhor treino para você, me conta: "
    return intro + "há quanto tempo você não pratica atividades físicas regulares?", TEMPO_OPCOES


FRASE_NIVEL = {
    "iniciante": "Isso garante uma intensidade adequada para evitar lesões e promover adaptação gradual.",
    "intermediario": "Isso garante um treino com intensidade adequada ao seu momento.",
    "avancado": "Isso permite um treino com mais volume e intensidade, dentro do limite seguro.",
}


def _fluxo_nivel(texto, estado, agora):
    etapa = estado["etapa"]
    if etapa == "tempo":
        nivel = _classificar(texto)
        if nivel is None:
            return ("Não entendi 😅 Me conta há quanto tempo você não treina (por exemplo, "
                    "\"8 meses\") ou escolha uma opção:"), TEMPO_OPCOES
        estado["nivel"] = nivel  # RN02
        estado["aquecido"] = False
        estado["ultimo_treino"] = None
        estado["etapa"] = "objetivo"
        return (f"Perfeito! Com base na sua resposta, vamos te classificar como "
                f"{NIVEL_MIN[nivel]} neste momento. {FRASE_NIVEL[nivel]} "
                "Qual é o seu principal objetivo?"), OBJETIVO_OPCOES
    if etapa == "objetivo":
        estado["perfil"]["objetivo"] = texto
        return _concluir_nivel(estado, agora)


def _concluir_nivel(estado, agora):
    nivel = estado["nivel"]
    depois, pre = estado["dados"].get("depois"), estado["dados"].get("pre", {})
    msg = (f"Excelente! Seu nível {NIVEL_MIN[nivel]} e seus objetivos foram registrados no "
           "sistema. Vamos passar para a escolha do seu treino!")
    _limpar_fluxo(estado)
    if depois == "treino":
        r, o = _treino_visao(estado, pre)
        return msg + "\n\n" + r, o
    if depois == "aquecimento":
        r, o = _iniciar_aquecimento(estado)
        return msg + "\n\n" + r, o
    if depois == "express":
        r, o = _texto_expresso(estado, pre.get("foco"))
        return msg + "\n\n" + r, o
    return msg, ["Aquecimento", "Ver minha ficha de treino"]


def _iniciar_aquecimento(estado):
    if estado["nivel"] is None:
        resp, ops = _iniciar_nivel(estado, depois="aquecimento")
        return "Para indicar o aquecimento certo, preciso conhecer seu nível. " + resp, ops
    nivel = estado["nivel"]
    opcoes = AQUECIMENTO[nivel]
    linhas = "\n".join(f"- **{o['nome']}:** {o['descricao']}" for o in opcoes)
    estado["fluxo"] = "aquecimento"
    estado["etapa"] = "escolha"
    estado["dados"] = {}
    return (f"O aquecimento é fundamental para preparar suas articulações e músculos! "
            f"Para o seu nível {NIVEL_MIN[nivel]}, recomendo duas opções:\n\n{linhas}\n\n"
            "Qual dessas modalidades você prefere fazer agora?"), [o["nome"] for o in opcoes]


def _fluxo_aquecimento(texto, estado, agora):
    opcoes = AQUECIMENTO[estado["nivel"]]
    for o in opcoes:
        if any(k in texto for k in o["keys"]):
            estado["aquecido"] = True
            _limpar_fluxo(estado)
            return (f"Ótima escolha! {o['escolha']} Assim que terminar, me avise por aqui para "
                    "passarmos ao treino principal!"), ["Terminei o aquecimento"]
    return "Não entendi 😅 Qual você prefere?", [o["nome"] for o in opcoes]


def _iniciar_treino(estado, pre):
    if estado["nivel"] is None:
        r, o = _iniciar_nivel(estado, depois="treino", pre=pre)
        return "Antes de montar sua ficha, preciso conhecer seu nível. " + r, o
    return _treino_visao(estado, pre)


def _treino_visao(estado, pre):
    foco = pre.get("foco")
    foco = FOCO_PADRAO if foco is None else foco
    t = TREINOS[FOCO_ID[foco]]
    estado["ultimo_treino"] = (foco, False)
    estado["ajuste"] = 0
    estado["aguardando"] = "exercicios"
    msg = (f"Muito bem! Hoje seu treino principal será focado {t['principal_frase']} e seu "
           f"treino secundário trabalhará {t['sec_frase']}.")
    outro = "Treino de superiores" if foco != 0 else "Treino de inferiores"
    ops = ["Quais são os exercícios?", "Treino expresso (20 min)", outro]
    if not estado["aquecido"]:
        msg += ("\n\n💡 Antes de começar, não esqueça do aquecimento: ele ajuda a prevenir "
                "lesões. Quer ver as opções?")
        ops = ["Aquecimento"] + ops
    return msg, ops


def _series_atual(estado):
    s = SERIES[estado["nivel"]]
    return max(s["min"], min(s["max"], s["series"] + estado["ajuste"]))


def _texto_lista_exercicios(estado):
    foco, _ = estado["ultimo_treino"]
    t = TREINOS[FOCO_ID[foco]]
    nivel = estado["nivel"]
    n = _series_atual(estado)

    def fmt(ex, principal):
        if nivel == "iniciante":
            reps = ex["reps_inic"]
        else:
            reps = SERIES[nivel]["reps"] if principal else "12 a 15"
        return f"{ex['nome']} ({n} séries de {reps} repetições)"

    pri = _frase_lista([fmt(e, True) for e in t["principal"]])
    sec = _frase_lista([fmt(e, False) for e in t["secundario"]])
    nomes = _nomes_treino(estado)
    return (f"**Treino Principal:** {pri}.\n\n**Treino Secundário:** {sec}.\n\n"
            "Quer conferir a carga inicial sugerida ou a instrução de execução de algum deles?"), \
        nomes + ["Não precisa"]


def _nomes_treino(estado):
    t = TREINOS[FOCO_ID[estado["ultimo_treino"][0]]]
    return [e["nome"] for e in t["principal"] + t["secundario"]]


def _detalhe_exercicio(estado, nome):
    return (f"**{nome}**\n\n**Execução:** {EXECUCAO[nome]}\n\n"
            "**Carga inicial sugerida:** comece leve, com um peso que permita completar todas as "
            f"repetições com boa técnica. O instrutor da {academia['nome']} define o valor ideal "
            "para você.\n\nQuer ver outro exercício?"), _nomes_treino(estado) + ["Não precisa"]


def _ajustar_treino(texto, estado):
    ut = estado["ultimo_treino"]
    if ut is None:
        return None
    if ut[1]:
        if "treino completo" in texto:
            return _treino_visao(estado, {"foco": ut[0]})
        return None
    s = SERIES[estado["nivel"]]
    mais = tem(texto, ["mais serie", "aumentar serie", "mais volume", "aumentar volume"])
    menos = tem(texto, ["menos serie", "diminuir serie", "reduzir serie", "menos volume"])
    if not (mais or menos):
        return None
    aviso = ""
    if mais:
        if s["series"] + estado["ajuste"] >= s["max"]:
            aviso = (f"Esse já é o máximo recomendado para o nível {NOMES_NIVEL[estado['nivel']]} "
                     f"({s['max']} séries) 😉\n\n")
        else:
            estado["ajuste"] += 1
    else:
        if s["series"] + estado["ajuste"] <= s["min"]:
            aviso = (f"Esse já é o mínimo recomendado para o nível {NOMES_NIVEL[estado['nivel']]} "
                     f"({s['min']} séries).\n\n")
        else:
            estado["ajuste"] -= 1
    estado["aguardando"] = "detalhe"
    r, o = _texto_lista_exercicios(estado)
    return aviso + r, o


def _soft(texto, palavras, estado):
    """Respostas que dependem da última pergunta, sem travar o usuário num fluxo."""
    ag = estado["aguardando"]
    if not ag:
        return None
    if ag == "exercicios":
        if (tem(texto, ["exercicio", "quais", "sim", "mostra", "lista", "pode"])
                and "expresso" not in texto and not any(p in texto for p in CATEGORIAS)):
            estado["aguardando"] = "detalhe"
            return _texto_lista_exercicios(estado)
        estado["aguardando"] = None
        return None
    if ag == "detalhe":
        if tem(texto, ["mais serie", "menos serie", "expresso", "aquecimento"]):
            return None
        nomes = _nomes_treino(estado)
        achou = [n for k, n in CHAVES_EXERCICIO.items() if k in texto and n in nomes]
        if achou:
            return _detalhe_exercicio(estado, achou[0])
        if palavras & {"nao", "dispenso", "vou"} or tem(texto, ["ja sei", "nao precisa"]):
            estado["aguardando"] = None
            desc = SERIES[estado["nivel"]]["descanso"]
            return (f"Perfeito! Lembre-se de descansar {desc} entre as séries. Bom treino!"), \
                ["Agendar aula", "Menu"]
        if tem(texto, ["carga", "instrucao", "execucao", "sim", "como"]):
            return "De qual exercício você quer ver a carga e a execução?", nomes + ["Não precisa"]
        estado["aguardando"] = None
        return None
    if ag == "expresso_ok":
        estado["aguardando"] = None
        if tem(texto, ["show", "exatamente", "otimo", "perfeito", "legal", "gostei", "top", "bora"]):
            return ("Excelente! Esse treino em circuito vai manter seu metabolismo acelerado no "
                    "tempo que você tem. Bom treino rápido!"), ["Agendar aula", "Menu"]
        return None
    return None


def _texto_expresso(estado, foco=None):
    if estado["nivel"] is None:
        r, o = _iniciar_nivel(estado, depois="express", pre={"foco": foco})
        return "Para adaptar a série ao seu nível, preciso te conhecer um pouco. " + r, o
    nivel = estado["nivel"]
    ex = EXPRESSO[nivel]
    if foco is None:
        foco = estado["ultimo_treino"][0] if estado["ultimo_treino"] else FOCO_PADRAO
    estado["ultimo_treino"] = (foco, True)
    estado["aguardando"] = "expresso_ok"
    linhas = "\n".join(f"- Exercício {i}: {nome} ({series})."
                       for i, (nome, series) in enumerate(ex["exercicios"], 1))
    return ("Dá sim! Vou adaptar uma série expressa de alta eficiência para caber no seu tempo "
            "disponível. Faremos um circuito contínuo:\n\n" + linhas +
            f"\n\nO descanso entre os exercícios será de apenas {ex['descanso']}.\n\n"
            "💡 Antes de começar, faça uns 3 minutos de aquecimento leve (esteira ou bicicleta) "
            "para prevenir lesões."), ["Treino completo", "Agendar aula"]



def _iniciar_serie(texto, estado):
    foco = escolher(texto, FOCO, numerico=False)
    estado["fluxo"] = "serie"
    estado["etapa"] = "aquecimento"
    estado["dados"] = {"pre": {"foco": 2 if foco is None else foco}}
    return "Posso ajudar! Você deseja começar com aquecimento?", ["Sim", "Não"]


def _seguir_serie(estado, prefixo):
    d = estado["dados"]
    pre, aquecer = d["pre"], d["aquecer"]
    estado["foco_pref"] = pre["foco"]
    nome = ALUNOS[estado["aluno"]]["nome"].split()[0]
    if estado["nivel"] is None:
        resp, ops = _iniciar_nivel(estado, depois="aquecimento" if aquecer else "treino", pre=pre)
    elif aquecer:
        resp, ops = _iniciar_aquecimento(estado)
    else:
        resp, ops = _treino_visao(estado, pre)
    return f"{prefixo}Cadastro validado, {nome}! ✅\n\n" + resp, ops


def _fluxo_serie(texto, estado, agora):
    palavras = set(re.findall(r"\w+", texto))
    d = estado["dados"]
    if estado["etapa"] == "aquecimento":
        if palavras & {"sim", "quero", "claro", "pode", "vamos", "ok"}:
            d["aquecer"], prefixo = True, ""
        elif palavras & {"nao", "dispenso"}:
            d["aquecer"] = False
            prefixo = ("Tudo bem! Mesmo assim vou deixar a sugestão de aquecimento no seu treino, "
                       "porque ele previne lesões. ")
        else:
            return "Responda **sim** ou **não**: você deseja começar com aquecimento?", ["Sim", "Não"]
        if estado["aluno"]:
            return _seguir_serie(estado, prefixo)
        estado["etapa"] = "id"
        d["prefixo"] = prefixo
        return prefixo + "Informe seu número de matrícula para prosseguir.", []
    if estado["etapa"] == "id":
        ok, resp = _validar_id(texto, estado)
        return _seguir_serie(estado, "") if ok else resp


def _faixa_dias(dias):
    nomes = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    dias = sorted(dias)
    if len(dias) > 2 and dias == list(range(dias[0], dias[-1] + 1)):
        return f"{nomes[dias[0]]} a {nomes[dias[-1]]}"
    return _frase_lista([nomes[d] for d in dias])


def _lista_modalidades():
    mods = list(academia["modalidades"])
    for g in GRADE:
        if g["modalidade"] not in mods:
            mods.append(g["modalidade"])
    return mods


def _contexto_ia():
    h = "; ".join(f"{d}: {v}" for d, v in academia["horarios"].items())
    return (f"Academia {academia['nome']}. Horários: {h}. Planos: {academia['planos']}. "
            f"Modalidades: {', '.join(_lista_modalidades())}. Endereço: {academia['endereco']}. "
            f"Recepção: {academia['recepcao_telefone']}.")


def _info(texto, palavras, estado, agora):
    if tem(texto, ["vaga", "grade", "aulas coletivas", "horario das aulas", "quais aulas"]):
        data = _parse_data(texto, agora)
        if data:
            slots = _slots_do_dia(estado, data, None, agora)
            if not slots:
                return f"Não temos aulas coletivas {_dia_rel(data, agora)}.", ["Agendar aula", "Menu"]
            linhas = [f"- {s['modalidade']} às {s['hora']}: "
                      f"{f'{_vagas(estado, s)} vaga(s)' if _vagas(estado, s) > 0 else 'lotada'}"
                      for s in slots]
            return f"Aulas {_dia_rel(data, agora)}:\n\n" + "\n".join(linhas), ["Agendar aula", "Menu"]
        linhas = [f"- {g['modalidade']}: {_faixa_dias(g['dias'])}, às {_frase_lista(g['horas'])}"
                  for g in GRADE]
        return "Grade de aulas coletivas:\n\n" + "\n".join(linhas), ["Agendar aula", "Menu"]
    if palavras & {"abre", "fecha", "abrem", "fecham", "aberto"} or tem(texto, ["horario", "funcionamento", "que horas"]):
        linhas = [f"- {dia}: {h}" for dia, h in academia["horarios"].items()]
        intro = variar("Nosso horário é este:", "Funcionamos assim:", "Olha só nossos horários:")
        return intro + "\n\n" + "\n".join(linhas) + "\n\nA VitaAI atende você 24 h por dia 💜", ["Agendar aula", "Menu"]
    if tem(texto, ["mensalidade", "plano", "valor", "preco"]):
        extra = "\n\nLimite de reservas de aula: " + ", ".join(f"{p}: {n}" for p, n in LIMITE_RESERVAS.items())
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



FLUXOS = {
    "agendar": _fluxo_agendar,
    "cancelar": _fluxo_cancelar,
    "nivel": _fluxo_nivel,
    "aquecimento": _fluxo_aquecimento,
    "serie": _fluxo_serie,
}


def responder(pergunta, estado, agora=None):
    agora = agora or datetime.now()
    texto = normalizar(pergunta)
    palavras = set(re.findall(r"\w+", texto))

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
    
    r = _soft(texto, palavras, estado)
    if r:
        return r

   
    if len(palavras) <= 4:
        if palavras & {"oi", "ola", "opa", "eae", "hey"} or tem(texto, ["bom dia", "boa tarde", "boa noite"]):
            return variar(
                "Oi! 💜 Tudo bem? Como posso te ajudar hoje?",
                "Olá! Que bom ter você aqui! Sobre o que quer saber?",
            ), MENU_OPCOES
        if tem(texto, ["obrigad", "valeu", "brigad"]):
            return f"Por nada! Tenha um ótimo dia e nos vemos na {academia['nome']}!", []
        if palavras & {"menu", "ajuda"} or tem(texto, ["o que voce faz", "o que voce pode"]):
            return _menu()

   
    if tem(texto, ["recepcao", "atendente", "humano", "falar com", "professor", "telefone"]):
        return _recepcao()

 
    r = _ajustar_treino(texto, estado)
    if r:
        return r

   
    if tem(texto, EXPRESSO_PALAVRAS):
        i = escolher(texto, FOCO, numerico=False)
        return _texto_expresso(estado, i)

    
    if tem(texto, ["minhas reserva", "minha reserva", "meus agendamentos", "ver reserva"]):
        return _iniciar_cancelar(estado, agora, so_ver=True)
    if tem(texto, ["cancel", "desmarcar"]):
        return _iniciar_cancelar(estado, agora)
    if tem(texto, ["agend", "marcar", "reservar", "inscrever"]):
        return _iniciar_agendar(texto, estado, agora)

   
    if "serie" in texto and not palavras & {"mais", "menos", "aumentar", "diminuir", "reduzir"}:
        return _iniciar_serie(texto, estado)

    
    if tem(texto, ["nivel", "classific", "avaliacao", "avaliar", "comecar a treinar",
                   "por fora", "primeira vez", "nunca treinei"]):
        if estado["nivel"] and tem(texto, ["nivel"]) and not tem(texto, ["refaz", "novamente", "reclass", "de novo"]):
            return (f"Seu nível atual é **{NOMES_NIVEL[estado['nivel']]}**.",
                    ["Refazer avaliação", "Montar meu treino"])
        return _iniciar_nivel(estado, boas_vindas=True)

  
    if tem(texto, ["aquecimento", "aquecer"]):
        return _iniciar_aquecimento(estado)

   
    if tem(texto, ["treino", "ficha", "malhar", "treinar", "terminei"]):
        if "terminei" in texto:
            estado["aquecido"] = True
        i = escolher(texto, FOCO, numerico=False)
        if i is not None:
            estado["foco_pref"] = i
        return _iniciar_treino(estado, {"foco": estado["foco_pref"]})

   
    r = _info(texto, palavras, estado, agora)
    if r:
        return r

   
    if "exercicio" in texto or any(p in texto for p in CATEGORIAS):
        return _exercicios_api(texto)

    return None
