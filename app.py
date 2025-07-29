import sys
import os
import threading
import traceback
import datetime
import requests
from urllib.parse import urlparse

from flask import Flask, request
from werkzeug.wrappers import Response
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Adiciona o diretório raiz para que o Python encontre os módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importa tudo do bot/db.py unificado
from bot.db import (
    salvar_mensagem, inicializar_db, buscar_historico_conversa,
    get_conversation_status, set_conversation_status
)

# Importa funções de crew_config
from bot.crew_config import (
    classificar_mensagem,
    encaminhar_para_atendente,
    responder_duvida
)

load_dotenv(os.path.join(project_root, '.env'))
app = Flask(__name__)

# Inicializar o banco de dados unificado
inicializar_db()

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')
NGROK_PLATFORM_URL = os.getenv('NGROK_PLATFORM_URL')

if not all([account_sid, auth_token, twilio_number, NGROK_PLATFORM_URL]):
    raise ValueError("Variáveis de ambiente (Twilio, NGROK_PLATFORM_URL) não foram definidas. Verifique seu .env")

twilio_client = Client(account_sid, auth_token)

# Define o caminho para a pasta de uploads da plataforma
UPLOADS_DIR = os.path.join(project_root, 'plataforma', 'uploads')
os.makedirs(UPLOADS_DIR, exist_ok=True)

def processar_em_background(numero_cliente_com_prefixo, texto_mensagem):
    """
    Função principal que processa a mensagem do usuário em segundo plano.
    """
    print(f"⚙️ [BG] Iniciando processamento para {numero_cliente_com_prefixo}...")
    try:
        print("⚙️ [BG] Salvando mensagem do usuário...")
        salvar_mensagem(numero_cliente_com_prefixo, 'user', texto_mensagem)
        
        print("⚙️ [BG] Buscando histórico...")
        historico = buscar_historico_conversa(numero_cliente_com_prefixo)
        
        print("⚙️ [BG] Classificando mensagem...")
        classificacao = classificar_mensagem(texto_mensagem, historico)
        print(f"🔍 [BG] Classificação: {classificacao}")

        resposta_final = ""
        atendente_destino = "Agente de IA"

        if classificacao == "SAUDACAO":
            resposta_final = "Olá! Sou a assistente virtual da Casa de Madeira. 😊 Em que posso te ajudar hoje?"
        
        elif classificacao == "DESPEDIDA":
            resposta_final = "Por nada! Se precisar de mais alguma coisa, é só chamar. A Casa de Madeira agradece seu contato! 👋"

        elif classificacao == "DUVIDA_GERAL":
            print("⚙️ [BG] Gerando resposta para dúvida geral...")
            resposta_final = responder_duvida(texto_mensagem, historico)
            
        else: # Encaminha para um humano
            print("⚙️ [BG] Encaminhando para atendente humano...")
            atendente_destino = encaminhar_para_atendente(classificacao)
            mapa_setor = {
                "Atendente do Financeiro": "nosso setor Financeiro",
                "Atendente Geral": "nossa equipe de Atendimento Geral"
            }
            setor_nome_amigavel = mapa_setor.get(atendente_destino, "nossa equipe")
            resposta_final = f"Ok! Para te ajudar com sua solicitação, já estou te encaminhando para {setor_nome_amigavel}. Em breve um de nossos atendentes continuará a conversa por aqui. 😊"
            
            print(f"👤 [BG] Encaminhando para: {atendente_destino}")
            set_conversation_status(numero_cliente_com_prefixo, 'HUMAN', atendente_destino)

        print("⚙️ [BG] Salvando resposta do bot...")
        salvar_mensagem(numero_cliente_com_prefixo, 'bot', resposta_final, classificacao, atendente_destino)
        
        print(f"⚙️ [BG] Enviando mensagem via Twilio: '{resposta_final[:30]}...'")
        twilio_client.messages.create(
            from_=twilio_number,
            body=resposta_final,
            to=numero_cliente_com_prefixo
        )
        print(f"✅ [BG] Resposta final enviada para {numero_cliente_com_prefixo}")

    except Exception as e:
        print("❌ ERRO NO BACKGROUND:")
        traceback.print_exc()

@app.route('/webhook', methods=['POST'])
def receber():
    try:
        numero_cliente_com_prefixo = request.form.get('From')
        texto_mensagem = request.form.get('Body')
        num_media = int(request.form.get('NumMedia', 0))

        mensagem_a_salvar = texto_mensagem
        if num_media > 0:
            twilio_media_url = request.form.get('MediaUrl0')
            mime_type = request.form.get('MediaContentType0', '')
            
            try:
                response = requests.get(twilio_media_url, auth=(account_sid, auth_token))
                response.raise_for_status()
                parsed_url = urlparse(twilio_media_url)
                filename = os.path.basename(parsed_url.path)
                save_path = os.path.join(UPLOADS_DIR, filename)
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                public_media_url = f"{NGROK_PLATFORM_URL}/uploads/{filename}"

                if 'image' in mime_type: tipo = "Imagem"
                elif 'video' in mime_type: tipo = "Vídeo"
                elif 'audio' in mime_type: tipo = "Áudio"
                else: tipo = "Arquivo"

                mensagem_a_salvar = f"[{tipo} recebido do cliente]({public_media_url})"
                if texto_mensagem:
                     mensagem_a_salvar += f"\nLegenda: {texto_mensagem}"
            
            except requests.exceptions.RequestException as e:
                print(f"❌ Falha ao descarregar mídia do Twilio: {e}")
                mensagem_a_salvar = "[Falha ao receber mídia do cliente]"

        conversation_state = get_conversation_status(numero_cliente_com_prefixo)
        
        if conversation_state and conversation_state['status'] == 'HUMAN':
            last_interaction_str = conversation_state.get('last_human_interaction')
            last_interaction = datetime.datetime.fromisoformat(last_interaction_str) if last_interaction_str else datetime.datetime.now(datetime.timezone.utc)
            
            if (datetime.datetime.now(datetime.timezone.utc) - last_interaction) < datetime.timedelta(hours=12):
                print(f"🤫 Atendimento com humano. Bot em silêncio para {numero_cliente_com_prefixo}.")
                salvar_mensagem(numero_cliente_com_prefixo, 'user', mensagem_a_salvar)
                return Response(str(MessagingResponse()), mimetype='text/xml')
            else:
                print(f"⏳ Timeout expirado. Bot reassumindo para {numero_cliente_com_prefixo}.")
                set_conversation_status(numero_cliente_com_prefixo, 'BOT')

        if num_media > 0:
             salvar_mensagem(numero_cliente_com_prefixo, 'user', mensagem_a_salvar)
             atendente_destino = encaminhar_para_atendente("GERAL")
             set_conversation_status(numero_cliente_com_prefixo, 'HUMAN', atendente_destino)
             resposta_encaminhamento = "Recebi sua mídia! Já estou encaminhando para nossa equipe. 👍"
             salvar_mensagem(numero_cliente_com_prefixo, 'bot', resposta_encaminhamento, "GERAL", atendente_destino)
             twilio_client.messages.create(from_=twilio_number, body=resposta_encaminhamento, to=numero_cliente_com_prefixo)
             return Response(str(MessagingResponse()), mimetype='text/xml')

        thread = threading.Thread(
            target=processar_em_background,
            args=(numero_cliente_com_prefixo, texto_mensagem)
        )
        thread.start()
        
        return Response(str(MessagingResponse()), mimetype='text/xml')

    except Exception as e:
        print("❌ ERRO GRAVE NO WEBHOOK:")
        traceback.print_exc()
        return Response(str(MessagingResponse()), mimetype='text/xml')

if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
