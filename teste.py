# teste_langchain.py
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

print("--- Iniciando teste direto da biblioteca LangChain ---")
load_dotenv()

# Verifica se a chave está sendo carregada
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ ERRO: A chave GOOGLE_API_KEY não foi encontrada no arquivo .env.")
else:
    print(f"🔑 Chave de API encontrada com sucesso (termina com: ...{api_key[-4:]})")
    
    try:
        # Tenta inicializar o LLM diretamente
        print("⏳ Inicializando o modelo ChatGoogleGenerativeAI...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash-latest",
            google_api_key=api_key
        )
        print("✅ Modelo inicializado com sucesso!")
        
        # Tenta fazer uma chamada simples
        print("🗣️  Enviando uma mensagem de teste para a API...")
        resposta = llm.invoke("Olá, Gemini! Responda 'ok' se estiver funcionando.")
        
        print("\n🎉 SUCESSO! A API respondeu:")
        print(resposta.content)
        
    except Exception as e:
        print("\n❌ FALHA NO TESTE DIRETO! Ocorreu um erro na comunicação com a API do Google:")
        print("--------------------------------------------------")
        print(e)
        print("--------------------------------------------------")
        print("Isso confirma que o problema NÃO é no CrewAI, mas sim na sua chave ou projeto Google Cloud.")