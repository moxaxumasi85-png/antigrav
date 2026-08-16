import sqlite3
import os
import pymysql
import pymysql.cursors

DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")

import json
def search_catalog(query: str):
    """
    Ищет товары в motors_db.json по всем категориям двигателей.
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'motors_db.json')
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # We will just return the entire mini-database to the LLM because it's only 11 items.
        # This way the LLM has complete context of motor.regiontehsnab.ru
        result_lines = []
        for item in data:
            base_info = f"Категория: {item['name']}, Ссылка: {item['url']}"
            if "configurations" in item:
                conf = item["configurations"]
                conf_str = f"Блок в сборе: {conf.get('Блок в сборе')} руб, Агрегат: {conf.get('Агрегат (без навесного)')} руб, С навесным: {conf.get('Двигатель в сборе с навесным')} руб."
                result_lines.append(f"{base_info}, Цены: {conf_str}")
            else:
                result_lines.append(f"{base_info}, Цена: {item.get('price')}")
            
        return "\n".join(result_lines)
    except Exception as e:
        print(f"Error reading JSON db: {e}")
        return ""

def search_gpu_vector_db(query: str, n_results: int = 3):
    """
    Поиск релевантного контекста и Q&A пар в векторной базе ChromaDB GPU.
    """
    try:
        import chromadb
        from sentence_transformers import SentenceTransformer
        import torch
        
        gpu_path = r"D:\AI\chroma_db_unified_gpu"
        if not os.path.exists(gpu_path):
            return ""
            
        client = chromadb.PersistentClient(path=gpu_path)
        try:
            collection = client.get_collection("unified_knowledge_gpu")
        except Exception:
            return ""
            
        device = "cuda" if torch.cuda.is_available() else "cpu"
        embedder = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2", device=device)
        query_vec = embedder.encode([query], convert_to_numpy=True).tolist()
        
        results = collection.query(
            query_embeddings=query_vec,
            n_results=n_results
        )
        
        documents = results.get("documents", [[]])[0]
        if documents:
            return "\n\n".join(documents)
    except Exception as e:
        print(f"Error in search_gpu_vector_db: {e}")
    return ""


import urllib.request
_city_cache = {}

def get_city_by_ip(ip: str) -> str:
    if not ip or ip in ('127.0.0.1', 'localhost', '::1') or ip.startswith('192.168.') or ip.startswith('10.'):
        return ""
    if ip in _city_cache:
        return _city_cache[ip]
    try:
        url = f"http://ip-api.com/json/{ip}?lang=ru"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=3)
        data = json.loads(res.read().decode('utf-8'))
        if data.get('status') == 'success':
            city = data.get('city') or data.get('regionName') or ""
            _city_cache[ip] = city
            return city
    except Exception as e:
        print(f"GeoIP error for {ip}: {e}")
    return ""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_manual_mode BOOLEAN DEFAULT 0,
            last_manager_msg_time TIMESTAMP,
            lead_score INTEGER DEFAULT 0,
            ip_address TEXT,
            city TEXT,
            phone TEXT,
            user_agent TEXT,
            status TEXT DEFAULT 'active',
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            sender TEXT, -- 'client', 'bot', 'manager'
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    ''')
    
    # Check and add columns if upgrading existing db
    cursor.execute("PRAGMA table_info(sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    for col_name, col_type in [
        ("ip_address", "TEXT"), 
        ("city", "TEXT"), 
        ("phone", "TEXT"), 
        ("user_agent", "TEXT"), 
        ("status", "TEXT DEFAULT 'active'"), 
        ("last_activity", "TIMESTAMP"),
        ("client_name", "TEXT"),
        ("passport", "TEXT"),
        ("inn", "TEXT"),
        ("order_details", "TEXT")
    ]:
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()

def update_session_requisites(session_id: str, phone: str = None, city: str = None, client_name: str = None, passport: str = None, inn: str = None, order_details: str = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE sessions 
        SET phone = COALESCE(?, phone),
            city = COALESCE(?, city),
            client_name = COALESCE(?, client_name),
            passport = COALESCE(?, passport),
            inn = COALESCE(?, inn),
            order_details = COALESCE(?, order_details),
            last_activity = CURRENT_TIMESTAMP
        WHERE session_id = ?
    ''', (phone, city, client_name, passport, inn, order_details, session_id))
    conn.commit()
    conn.close()

def get_or_create_session(session_id, ip_address=None, user_agent=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    city = get_city_by_ip(ip_address) if ip_address else ""
    cursor.execute('SELECT is_manual_mode, last_manager_msg_time, city FROM sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute('INSERT INTO sessions (session_id, is_manual_mode, ip_address, city, user_agent, status) VALUES (?, 0, ?, ?, ?, "active")', (session_id, ip_address, city, user_agent))
        conn.commit()
        is_manual = False
        last_time = None
    else:
        is_manual = bool(row[0])
        last_time = row[1]
        existing_city = row[2]
        if not existing_city and city:
            cursor.execute('UPDATE sessions SET city = ? WHERE session_id = ?', (city, session_id))
            conn.commit()
        if ip_address or user_agent:
            cursor.execute('UPDATE sessions SET ip_address = COALESCE(?, ip_address), user_agent = COALESCE(?, user_agent), last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (ip_address, user_agent, session_id))
            conn.commit()
    conn.close()
    return is_manual, last_time

def set_manual_mode(session_id, is_manual=True):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if is_manual:
        cursor.execute('UPDATE sessions SET is_manual_mode = 1, last_manager_msg_time = CURRENT_TIMESTAMP, last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (session_id,))
    else:
        cursor.execute('UPDATE sessions SET is_manual_mode = 0, last_manager_msg_time = NULL, last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (session_id,))
    conn.commit()
    conn.close()

import re
def save_message(session_id, sender, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (session_id, sender, content) VALUES (?, ?, ?)', (session_id, sender, content))
    
    # Try extracting phone number from client message
    if sender == 'client' and content:
        phone_match = re.search(r'\+?[78]\s*\(?\d{3}\)?\s*\d{3}[\s-]?\d{2}[\s-]?\d{2}', content)
        if phone_match:
            cursor.execute('UPDATE sessions SET phone = ? WHERE session_id = ?', (phone_match.group(0), session_id))

    if sender == 'manager':
        cursor.execute('UPDATE sessions SET is_manual_mode = 1, last_manager_msg_time = CURRENT_TIMESTAMP, last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (session_id,))
    else:
        cursor.execute('UPDATE sessions SET last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (session_id,))
    
    conn.commit()
    conn.close()

def update_session_status(session_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE sessions SET status = ? WHERE session_id = ?', (status, session_id))
    conn.commit()
    conn.close()

def update_session_score(session_id, score):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE sessions SET lead_score = ?, last_activity = CURRENT_TIMESTAMP WHERE session_id = ?', (score, session_id))
    conn.commit()
    conn.close()

def get_all_sessions():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT s.*, 
            (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.session_id) as msg_count,
            (SELECT content FROM messages m WHERE m.session_id = s.session_id ORDER BY timestamp DESC LIMIT 1) as last_msg,
            (SELECT timestamp FROM messages m WHERE m.session_id = s.session_id ORDER BY timestamp DESC LIMIT 1) as last_msg_time
        FROM sessions s 
        ORDER BY COALESCE((SELECT MAX(timestamp) FROM messages m WHERE m.session_id = s.session_id), s.last_activity) DESC
    ''')
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

def get_session_messages(session_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT sender, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp ASC', (session_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return messages

init_db()
