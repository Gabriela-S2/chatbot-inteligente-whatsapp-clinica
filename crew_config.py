import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI, HarmCategory, HarmBlockThreshold

# Carrega as variáveis de ambiente
load_dotenv()

# --- Bloco de configuração do LLM ---
llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash-latest",
    temperature=0.1,
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    safety_settings={
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    },
)

# --- Base de Conhecimento ---
def carregar_base_conhecimento():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, 'knowledge_base.txt')
        with open(file_path, "r", encoding="utf-8") as f:
            print(f"✅ Base de conhecimento carregada com sucesso de: {file_path}")
            return f.read()
    except FileNotFoundError:
        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.txt')
        print(f"AVISO: Arquivo 'knowledge_base.txt' não encontrado em {file_path}")
        return ""

base_de_conhecimento = carregar_base_conhecimento()


# --- Funções do Cérebro do Bot ---

def classificar_mensagem(texto_do_usuario: str, historico_conversa: str) -> str:
    prompt_de_classificacao = f"""
    Analise a ÚLTIMA mensagem do usuário para definir a intenção.
    Categorias: SAUDACAO, DESPEDIDA, FINANCEIRO, GERAL, DUVIDA_GERAL.

    REGRAS:
    1. SAUDACAO: Apenas cumprimentos (Olá, Bom dia, Oi).
    2. DESPEDIDA: Apenas despedidas ou agradecimentos (Obrigado, Tchau).
    3. FINANCEIRO: Sobre boletos, notas fiscais, pagamentos, cancelamentos. ALTA PRIORIDADE.
    4. DUVIDA_GERAL: Perguntas sobre preços, horários, serviços, convênios.
    5. GERAL: Pedidos de agendamento, vagas, e outras dúvidas que precisam de um humano.
    6. PRIORIDADE: Se a mensagem tiver um cumprimento E uma pergunta (ex: "Oi, qual o preço?"), a intenção é a da pergunta (DUVIDA_GERAL).

    Histórico para contexto:
    {historico_conversa}
    
    ÚLTIMA MENSAGEM DO USUÁRIO: '{texto_do_usuario}'

    Retorne APENAS uma das seguintes palavras: SAUDACAO, DESPEDIDA, FINANCEIRO, GERAL, DUVIDA_GERAL.
    """
    try:
        resposta = llm.invoke(prompt_de_classificacao)
        resultado = resposta.content.strip().upper()
        if resultado in ["SAUDACAO", "DESPEDIDA", "FINANCEIRO", "GERAL", "DUVIDA_GERAL"]:
            return resultado
        return "GERAL" 
    except Exception as e:
        print(f"❌ Erro na chamada ao LLM para classificação: {e}")
        return "GERAL"

def responder_duvida(texto_do_usuario: str, historico_conversa: str) -> str:
    prompt_de_resposta = f"""
    Você é um assistente virtual da 'Casa de Madeira'. Sua única fonte de informação é a "Base de Conhecimento".

    ***REGRAS DE COMPORTAMENTO***
    1.  **RESTRITO À BASE:** Você SÓ PODE usar as informações da "Base de Conhecimento". NÃO invente informações.
    2.  **SE NÃO SOUBER, ENCAMINHE:** Se a resposta não estiver na base ou se as regras de lógica não se aplicarem, sua única resposta deve ser: "Hmm, não encontrei essa informação específica. Já estou passando para nossa equipe que poderá te ajudar com isso! 😊"
    3.  **SEJA DIRETO:** Responda de forma clara e objetiva.

    ***LÓGICA DE RACIOCÍNIO (MUITO IMPORTANTE!)***
    1.  **LÓGICA DE CONVÊNIOS:** A base de conhecimento lista os serviços que CADA convênio cobre. Se um usuário perguntar se um serviço (ex: Pilates) é coberto por um convênio, e esse serviço NÃO ESTÁ LISTADO sob aquele convênio, você deve concluir que NÃO é coberto. Sua resposta deve ser clara, por exemplo: "Para o convênio X, cobrimos apenas os seguintes procedimentos: [lista]. O Pilates é um atendimento particular. O valor é R$ 238,00 mensais."
    2.  **LÓGICA DE NATAÇÃO (FLUXO OBRIGATÓRIO):**
        -   Se o usuário perguntar sobre natação, sua PRIMEIRA ação é SEMPRE fazer as 3 perguntas que estão na base de conhecimento (idade, experiência, período).
        -   Analise o histórico da conversa. Se o usuário já respondeu a uma ou mais perguntas, NÃO as repita. Faça apenas as que faltam.
        -   SOMENTE APÓS ter as respostas para as 3 perguntas, você deve consultar a base de conhecimento e fornecer o orçamento correto para a idade informada.
        -   NUNCA encaminhe para um humano durante o fluxo de perguntas da natação, a menos que o usuário peça explicitamente.

    === Base de Conhecimento ===
    ---
    {base_de_conhecimento}
    ---
    
    === Histórico da Conversa ===
    {historico_conversa}
    ---

    TAREFA: Com base na ÚLTIMA mensagem do usuário ('{texto_do_usuario}'), no histórico e nas REGRAS DE LÓGICA, formule a resposta correta.
    """
    try:
        resposta = llm.invoke(prompt_de_resposta)
        return resposta.content
    except Exception as e:
        print(f"❌ Erro na chamada ao LLM para responder dúvida: {e}")
        return "Obrigado por sua mensagem. Em breve um de nossos atendentes entrará em contato para te ajudar."

def encaminhar_para_atendente(classificacao: str) -> str:
    """Retorna o nome do setor baseado na classificação."""
    return "Atendente do Financeiro" if classificacao == "FINANCEIRO" else "Atendente Geral"
