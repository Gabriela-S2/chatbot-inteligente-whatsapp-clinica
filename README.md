# Chatbot de Atendimento Inteligente para Clínicas via WhatsApp

## 📖 Sobre o Projeto

Este é um chatbot para WhatsApp desenvolvido para automatizar o atendimento de clínicas de saúde. Ele utiliza a API da Twilio para a comunicação e um modelo de linguagem do Google (Gemini) para interpretar as mensagens dos usuários e fornecer respostas precisas com base em uma base de conhecimento personalizável.

O bot foi projetado para ser facilmente adaptável a diferentes empresas, bastando editar o arquivo de base de conhecimento (`knowledge_base.txt`).

---

## ✨ Funcionalidades Principais

* **Integração com WhatsApp:** Recebe e envia mensagens através da API da Twilio.
* **Processamento de Linguagem Natural:** Usa o Google Gemini para entender as intenções dos usuários.
* **Base de Conhecimento Editável:** Responde a perguntas sobre horários, preços, serviços e convênios com base no arquivo `knowledge_base.txt`.
* **Classificação de Intenção:** Categoriza as mensagens em `SAUDACAO`, `DESPEDIDA`, `FINANCEIRO`, `DUVIDA_GERAL`, etc.
* **Tratamento de Mídia:** Salva imagens, vídeos e áudios enviados pelos usuários e encaminha para o atendimento humano.
* **Transbordo para Atendimento Humano:** Quando o bot não sabe a resposta ou a intenção é complexa, ele encaminha a conversa para um setor específico (ex: Financeiro, Atendimento Geral).
* **Histórico de Conversas:** Salva todas as interações em um banco de dados SQLite para consulta.

---

## 🛠️ Tecnologias Utilizadas

* Python
* Flask
* Twilio API
* Langchain com Google Generative AI (Gemini)
* SQLite
* Uvicorn & Gunicorn/Waitress

---

## 🚀 Como Executar o Projeto

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/SEU-USUARIO/NOME-DO-SEU-REPOSITORIO.git](https://github.com/SEU-USUARIO/NOME-DO-SEU-REPOSITORIO.git)
    cd NOME-DO-SEU-REPOSITORIO
    ```

2.  **Crie um ambiente virtual e instale as dependências:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # No Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configure as variáveis de ambiente:**
    * Renomeie o arquivo `.env.example` para `.env`.
    * Preencha as variáveis com suas chaves da API do Google, Twilio e a URL do ngrok.
        ```
        GOOGLE_API_KEY="SUA_CHAVE_GOOGLE"
        TWILIO_ACCOUNT_SID="SEU_SID_TWILIO"
        TWILIO_AUTH_TOKEN="SEU_TOKEN_TWILIO"
        TWILIO_PHONE_NUMBER="whatsapp:+SEU_NUMERO_TWILIO"
        NGROK_PLATFORM_URL="SUA_URL_NGROK"
        FLASK_SECRET_KEY="SUA_CHAVE_SECRETA"
        ```

4.  **Personalize a Base de Conhecimento:**
    * Edite o arquivo `knowledge_base.txt` com as informações da sua clínica/empresa.

5.  **Execute a aplicação:**
    * Para desenvolvimento:
      ```bash
      flask run
      ```
    * Para produção (usando Waitress, como no seu `app.py`):
      ```bash
      python app.py
      ```

6.  **Configure o Webhook no Twilio:**
    * Instale o ngrok neste diretório e inicie para expor sua porta local (ex: 5000) na internet: `ngrok http 5000`.
    * Pegue a URL HTTPS gerada pelo `ngrok` e configure no painel do seu número do Twilio, na seção "Messaging", adicionando `/webhook` ao final (ex: `https://sua-url.ngrok-free.app/webhook`).