import os

import streamlit as st

from informacoes import academia
from fluxos import responder, novo_estado, mascarar, MENU_OPCOES
from base_dados import ALUNOS

PASTA = os.path.dirname(os.path.abspath(__file__))
# RNF05: coloque a imagem da persona (gerada por IA) em AssAcad/vitaai.png
IMG_PERSONA = os.path.join(PASTA, "vitaai.png")        
IMG_CORPO = os.path.join(PASTA, "vitaai_corpo.png")  
AVATARES = {
    "user": "🧑",
    "assistant": IMG_PERSONA if os.path.exists(IMG_PERSONA) else "💚",
}

BOAS_VINDAS = ("Oi! Eu sou a **VitaAI** 💜, assistente virtual da "
               f"{academia['nome']}. Estou aqui 24 h por dia para te ajudar. O que você precisa?")

st.set_page_config(
    page_title="VitaAI",
    page_icon=IMG_PERSONA if os.path.exists(IMG_PERSONA) else "💚",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
    html, body, [class*="css"], [data-testid="stAppViewContainer"], button, input, textarea {
        font-family: 'Poppins', sans-serif !important;
    }
    h1 { color: #3DDC5A; }
    [data-testid="stChatMessage"] { border-radius: 16px; padding: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("VitaAI")
st.caption(f"Assistente virtual da {academia['nome']} · atendimento 24 h")


def reiniciar():
    st.session_state.estado = novo_estado()
    st.session_state.historico = [
        {"role": "assistant", "content": BOAS_VINDAS, "opcoes": MENU_OPCOES}
    ]


if "estado" not in st.session_state:
    reiniciar()

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    if os.path.exists(IMG_CORPO):
        st.image(IMG_CORPO, use_container_width=True)
    st.header(academia["nome"])
    st.write("**VitaAI**: sua parceira de treino, simpática e motivadora 💪")
    st.write(f"📞 Recepção: {academia['recepcao_telefone']}")
    st.write(f"📍 {academia['endereco']}")
    st.divider()
    st.caption("🔒 Uso sua matrícula ou CPF só para validar agendamentos. "
               "Eles não ficam visíveis na conversa.")
    with st.expander("Dados de teste (demonstração)"):
        for mat, a in ALUNOS.items():
            situacao = "ativo" if a["ativo"] else "inativo"
            st.write(f"Matrícula **{mat}** · CPF {a['cpf']} · {a['plano']} · {situacao}")
    if st.button("🗑️ Reiniciar conversa"):
        reiniciar()
        st.rerun()

# ---------------------------------------------------------------- processamento
clique = st.session_state.pop("clique", None)
entrada = st.chat_input("Como posso ajudar você?")
pergunta = clique or entrada

if pergunta:
    st.session_state.historico.append({"role": "user", "content": mascarar(pergunta)})
    with st.spinner("VitaAI está pensando..."):
        texto, opcoes = responder(pergunta, st.session_state.estado)
    st.session_state.historico.append(
        {"role": "assistant", "content": texto, "opcoes": opcoes}
    )

# ---------------------------------------------------------------- exibição
for msg in st.session_state.historico:
    with st.chat_message(msg["role"], avatar=AVATARES[msg["role"]]):
        st.write(msg["content"])

ultima = st.session_state.historico[-1]
if ultima["role"] == "assistant" and ultima.get("opcoes"):
    for i, op in enumerate(ultima["opcoes"]):
        if st.button(op, key=f"op_{len(st.session_state.historico)}_{i}"):
            st.session_state.clique = op
            st.rerun()
