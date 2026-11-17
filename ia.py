
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

INSTRUCOES = """Você é a VitaAI, assistente virtual de uma academia.
Responda em português do Brasil, de forma simpática, motivadora e curta (até 4 frases).
Use SOMENTE as informações do contexto. Nunca invente horários, preços ou regras.
Não dê orientação médica. Se não souber, diga que não tem a informação e
sugira falar com a recepção."""


def conversar_ia(pergunta, contexto):
    chave = os.getenv("OPENAI_API_KEY")
    if not chave:
        return None
    try:
        from openai import OpenAI
        cliente = OpenAI(api_key=chave)
        r = cliente.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": INSTRUCOES},
                {"role": "user", "content": f"Contexto:\n{contexto}\n\nPergunta: {pergunta}"},
            ],
            temperature=0.5,
            max_tokens=300,
        )
        return r.choices[0].message.content
    except Exception:
        return None