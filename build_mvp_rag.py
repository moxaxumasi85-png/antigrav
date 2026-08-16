import json
import os
import re
from pathlib import Path

try:
    import chromadb
    from chromadb.utils import embedding_functions
except ImportError:
    print("Установите: pip install chromadb")
    exit(1)

MAX_FILE = r"d:\AI\projects\чатбот и другие чаты по моторам\max_dialogues_with_files.json"
TG_FILE = r"d:\AI\projects\чатбот и другие чаты по моторам\tg_dialogues_manual_backup.json"
TRANSCRIPTS_LOG = r"D:\AI\Projects_Active\transcripts\transcriptions_log.txt"
CHROMA_PATH = r"D:\AI\chroma_db_mvp"

def extract_audio_transcripts():
    # Простая логика из merge_conversations.py
    conversations = {}
    current_file = None
    current_text = None
    
    if not os.path.exists(TRANSCRIPTS_LOG):
        return []

    try:
        with open(TRANSCRIPTS_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(TRANSCRIPTS_LOG, "r", encoding="cp1251", errors="replace") as f:
            lines = f.readlines()
            
    pattern = re.compile(r"external-\d+-(\d+)-(\d{8})-(\d{6})-(\d+)\.(\d+)\.wav")
    
    for line in lines:
        line = line.rstrip("\n\r")
        if line.startswith("FILE: "):
            current_file = line[6:].strip()
            current_text = None
        elif line.startswith("TEXT: "):
            current_text = line[6:].strip()
            if current_file and current_text:
                m = pattern.match(os.path.basename(current_file))
                if m:
                    phone, date, time_, base_id, order = m.groups()
                    key = f"audio-{phone}-{date}-{time_}"
                    if key not in conversations:
                        conversations[key] = []
                    conversations[key].append((int(order), current_text))
                    
    docs = []
    for key, fragments in conversations.items():
        fragments.sort(key=lambda x: x[0])
        full_text = " ".join(t for _, t in fragments if t.strip())
        if len(full_text.strip()) > 20:
            docs.append({
                "id": key,
                "text": full_text.strip(),
                "source": "phone"
            })
    return docs

def extract_labeled():
    LABELED_FILE = r"d:\AI\projects\чатбот и другие чаты по моторам\labeled_dialogues.json"
    if not os.path.exists(LABELED_FILE): return []
    with open(LABELED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    docs = []
    for chat in data:
        # Avoid phone source as extract_audio_transcripts will pull the absolutely latest directly from the log
        if chat.get("source") == "phone":
            continue
            
        text_lines = []
        for m in chat.get("messages", []):
            txt = m.get("text", "").strip()
            if txt:
                speaker = "Менеджер" if m.get("type") in ["manager", "out", "admin"] or m.get("out") else "Клиент"
                text_lines.append(f"{speaker}: {txt}")
                
        if text_lines:
            docs.append({
                "id": chat.get("id"),
                "text": "\n".join(text_lines),
                "source": chat.get("source")
            })
    return docs

def main():
    print("Собираем данные...")
    audio_docs = extract_audio_transcripts()
    labeled_docs = extract_labeled()
    
    all_docs = audio_docs + labeled_docs
    print(f"Собрано: {len(audio_docs)} звонков, {len(labeled_docs)} чатов TG и Max. Всего: {len(all_docs)}")
    
    print("\nИнициализация ChromaDB MVP...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    try:
        client.delete_collection("conversations")
    except ValueError:
        pass # Коллекции еще нет
    
    col = client.create_collection(
        name="conversations",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    
    to_add = all_docs
    
    if not to_add:
        print("Новых документов для векторизации нет.")
        return
        
    print(f"Векторизация {len(to_add)} документов (может занять время)...")
    BATCH = 50
    for i in range(0, len(to_add), BATCH):
        batch = to_add[i:i+BATCH]
        try:
            col.add(
                ids=[d["id"] for d in batch],
                documents=[d["text"] for d in batch], # Полный текст без ограничений
                metadatas=[{"source": d["source"]} for d in batch]
            )
            print(f"  Векторизовано: {min(i+BATCH, len(to_add))} / {len(to_add)}")
        except Exception as e:
            print(f"  Ошибка в батче {i}: {e}")
            
    print(f"\nГотово! Всего в MVP базе: {col.count()} документов.")

if __name__ == "__main__":
    main()
