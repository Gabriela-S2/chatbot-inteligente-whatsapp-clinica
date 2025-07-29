import sqlite3
import datetime
import os
import hashlib

# O único banco de dados agora é o mensagens.db, localizado dentro da pasta 'bot'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mensagens.db')

def get_db_connection(check_same_thread=False):
    """Função auxiliar para obter uma conexão com o banco de dados principal."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    """
    Inicializa TODAS as tabelas necessárias para o bot e a plataforma.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de mensagens com a nova coluna 'is_read'
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_cliente TEXT NOT NULL,
        remetente TEXT NOT NULL, -- 'user', 'bot', 'human' ou 'system'
        texto_mensagem TEXT NOT NULL,
        classificacao TEXT,
        atendente_destino TEXT,
        data_recebimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_read INTEGER DEFAULT 0 -- 0 para não lida, 1 para lida
    )
    ''')
    
    # Adiciona a coluna 'is_read' se ela não existir (para compatibilidade com bancos antigos)
    try:
        cursor.execute("SELECT is_read FROM mensagens LIMIT 1")
    except sqlite3.OperationalError:
        print("Adicionando coluna 'is_read' à tabela de mensagens...")
        cursor.execute("ALTER TABLE mensagens ADD COLUMN is_read INTEGER DEFAULT 0")

    # O restante das tabelas
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS atendentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, setor TEXT NOT NULL, 
        email TEXT UNIQUE NOT NULL, senha TEXT NOT NULL
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS contatos_salvos (
        numero_cliente TEXT PRIMARY KEY, nome_contato TEXT NOT NULL
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mensagens_prontas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, conteudo TEXT NOT NULL UNIQUE
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, token TEXT UNIQUE NOT NULL,
        expiration_time TIMESTAMP NOT NULL, is_used INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES atendentes (id)
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversation_status (
        contact_number TEXT PRIMARY KEY, status TEXT NOT NULL, assigned_sector TEXT,
        last_human_interaction TIMESTAMP
    )''')
    
    conn.commit()
    conn.close()
    print(f"🗄️ Banco de dados '{DB_PATH}' inicializado/verificado com sucesso!")

# --- Funções de Controle de Status da Conversa ---

def set_conversation_status(contact_number, status, sector=None):
    conn = get_db_connection(check_same_thread=False)
    clean_number = contact_number.replace('whatsapp:', '')
    if status == 'BOT':
        conn.execute('UPDATE conversation_status SET status=?, last_human_interaction=NULL, assigned_sector=NULL WHERE contact_number=?', (status, clean_number))
    else:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        conn.execute('INSERT INTO conversation_status (contact_number, status, last_human_interaction, assigned_sector) VALUES (?, ?, ?, ?) ON CONFLICT(contact_number) DO UPDATE SET status=excluded.status, last_human_interaction=excluded.last_human_interaction, assigned_sector=excluded.assigned_sector', (clean_number, status, now_utc, sector))
    conn.commit()
    conn.close()

def get_conversation_status(contact_number):
    conn = get_db_connection(check_same_thread=False)
    clean_number = contact_number.replace('whatsapp:', '')
    conversation = conn.execute("SELECT * FROM conversation_status WHERE contact_number = ?", (clean_number,)).fetchone()
    conn.close()
    return dict(conversation) if conversation else None

# --- Funções de Mensagens e Histórico ---

def salvar_mensagem(numero, remetente, texto, classificacao=None, atendente=None):
    conn = get_db_connection(check_same_thread=False)
    is_read_status = 0 if remetente == 'user' else 1
    conn.execute('INSERT INTO mensagens (numero_cliente, remetente, texto_mensagem, classificacao, atendente_destino, is_read) VALUES (?, ?, ?, ?, ?, ?)',
                 (numero, remetente, texto, classificacao, atendente, is_read_status))
    conn.commit()
    conn.close()

def buscar_historico_conversa(numero_cliente, limite=6):
    conn = get_db_connection(check_same_thread=False)
    historico_raw = conn.execute('SELECT remetente, texto_mensagem FROM mensagens WHERE numero_cliente = ? ORDER BY data_recebimento DESC LIMIT ?', (numero_cliente, limite)).fetchall()
    conn.close()
    if not historico_raw: return ""
    historico_formatado = "\n--- Histórico da Conversa Recente ---\n"
    for row in reversed(historico_raw):
        historico_formatado += f"{row['remetente'].capitalize()}: {row['texto_mensagem']}\n"
    return historico_formatado + "--- Fim do Histórico ---\n"

# --- Funções da Plataforma ---

def salvar_nome_contato(numero_cliente, nome_contato):
    conn = get_db_connection(check_same_thread=False)
    clean_number = numero_cliente.replace('whatsapp:', '')
    conn.execute('INSERT INTO contatos_salvos (numero_cliente, nome_contato) VALUES (?, ?) ON CONFLICT(numero_cliente) DO UPDATE SET nome_contato=excluded.nome_contato', (clean_number, nome_contato))
    conn.commit()
    conn.close()

def get_nome_contato(numero_cliente):
    """
    Obtém o nome amigável de um contato. Esta é a função que estava faltando.
    """
    conn = get_db_connection(check_same_thread=False)
    clean_number = numero_cliente.replace('whatsapp:', '')
    result = conn.execute("SELECT nome_contato FROM contatos_salvos WHERE numero_cliente = ?", (clean_number,)).fetchone()
    conn.close()
    return result['nome_contato'] if result else None

def get_mensagens_prontas(conn):
    mensagens = conn.execute("SELECT id, nome, conteudo FROM mensagens_prontas ORDER BY nome").fetchall()
    return [dict(row) for row in mensagens]

def add_mensagem_pronta(conn, nome, conteudo):
    try:
        conn.execute("INSERT INTO mensagens_prontas (nome, conteudo) VALUES (?, ?)", (nome, conteudo))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

# --- Funções de Reset de Senha ---

def create_password_reset_token(user_id):
    conn = get_db_connection(check_same_thread=False)
    token = hashlib.sha256(os.urandom(32)).hexdigest()
    expiration_time = datetime.datetime.now() + datetime.timedelta(hours=1)
    try:
        conn.execute('INSERT INTO password_reset_tokens (user_id, token, expiration_time) VALUES (?, ?, ?)',
                     (user_id, token, expiration_time))
        conn.commit()
        return token
    finally:
        conn.close()

def validate_password_reset_token(token):
    conn = get_db_connection(check_same_thread=False)
    result = conn.execute('SELECT user_id, expiration_time, is_used FROM password_reset_tokens WHERE token = ?', (token,)).fetchone()
    conn.close()
    if result:
        expiration_time = datetime.datetime.fromisoformat(result['expiration_time'])
        if not result['is_used'] and expiration_time > datetime.datetime.now():
            return result['user_id']
    return None

def invalidate_password_reset_token(token):
    conn = get_db_connection(check_same_thread=False)
    conn.execute('UPDATE password_reset_tokens SET is_used = 1 WHERE token = ?', (token,))
    conn.commit()
    conn.close()

def update_user_password(user_id, hashed_password):
    conn = get_db_connection(check_same_thread=False)
    conn.execute('UPDATE atendentes SET senha = ? WHERE id = ?', (hashed_password, user_id))
    conn.commit()
    conn.close()
