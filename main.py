import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, List
import secrets
import db
from llm import generate_reply

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Fd4c9Gs#$")

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    correct_username_bytes = ADMIN_USERNAME.encode("utf8")
    is_correct_username = secrets.compare_digest(current_username_bytes, correct_username_bytes)
    
    current_password_bytes = credentials.password.encode("utf8")
    correct_password_bytes = ADMIN_PASSWORD.encode("utf8")
    is_correct_password = secrets.compare_digest(current_password_bytes, correct_password_bytes)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль администратора",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.get("/api/health")
def health_check():
    return {"status": "online", "message": "API server is running", "catalog_items": 29066}

@app.api_route("/api.php", methods=["GET", "POST", "OPTIONS"])
async def api_php_gateway(request: Request):
    if request.method == "OPTIONS":
        return JSONResponse({"status": "ok"})

    params = dict(request.query_params)
    action = params.get("action")
    session_id = params.get("session_id")

    # Fallback: parse query parameters from headers or full URL if Nginx stripped query string
    if not action or not session_id:
        orig_uri = request.headers.get("x-original-uri") or request.headers.get("x-request-uri") or request.headers.get("referer") or str(request.url)
        if orig_uri and "?" in orig_uri:
            q_str = orig_uri.split("?", 1)[1]
            from urllib.parse import parse_qs
            parsed_qs = parse_qs(q_str)
            if not action and "action" in parsed_qs:
                action = parsed_qs["action"][0]
            if not session_id and "session_id" in parsed_qs:
                session_id = parsed_qs["session_id"][0]

    body_data = {}
    if request.method == "POST":
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_data = json.loads(body_bytes.decode('utf-8'))
                action = action or body_data.get("action")
                session_id = session_id or body_data.get("session_id")
        except Exception:
            pass

    # 1. Получение истории / сообщений
    if action in ["history", "admin_messages"] and session_id:
        msgs = db.get_session_messages(session_id)
        return JSONResponse({"session_id": session_id, "messages": msgs})

    # 2. Получение всех сессий для админки
    if action == "admin_sessions":
        all_s = db.get_all_sessions()
        active_connected_ids = set(manager.active_connections.keys())
        online_count = 0
        active_count = 0
        completed_count = 0
        for s in all_s:
            is_online = s["session_id"] in active_connected_ids
            s["is_online"] = is_online
            if is_online:
                online_count += 1
            if s.get("status") == "completed":
                completed_count += 1
            else:
                active_count += 1
        return JSONResponse({
            "sessions": all_s,
            "stats": {
                "online_count": online_count,
                "active_count": active_count,
                "completed_count": completed_count,
                "total_count": len(all_s)
            }
        })

    # 3. Отправка сообщения клиентом
    if action == "chat":
        msg = body_data.get("message", "").strip()
        session_id = session_id or body_data.get("session_id") or f"web_{secrets.token_hex(4)}"
        clean_msg = html.escape(msg)
        if not clean_msg:
            return JSONResponse({"reply": "Пожалуйста, введите ваш вопрос.", "session_id": session_id, "score": 5})

        client_ip = request.headers.get("x-forwarded-for") or (request.client.host if request.client else "127.0.0.1")
        user_agent = request.headers.get("user-agent", "")
        db.get_or_create_session(session_id, ip_address=client_ip, user_agent=user_agent)
        db.update_session_status(session_id, "active")
        db.save_message(session_id, "client", clean_msg)

        is_manual = check_auto_reconnect(session_id)
        if is_manual:
            return JSONResponse({
                "reply": "Менеджер подключен к диалогу. Вам ответят в ближайшее время.",
                "session_id": session_id,
                "score": 8
            })

        history = db.get_session_messages(session_id)
        bot_reply, score = await asyncio.to_thread(generate_reply, history, clean_msg)
        db.save_message(session_id, "bot", bot_reply)
        db.update_session_score(session_id, score)

        return JSONResponse({
            "reply": bot_reply,
            "session_id": session_id,
            "score": score
        })

    # 4. Отправка сообщения менеджером из админки
    if action == "admin_send" and session_id:
        content = body_data.get("content", "").strip()
        if content:
            clean_content = html.escape(content)
            db.save_message(session_id, "manager", clean_content)
            await manager.send_to_client(session_id, {
                "sender": "manager",
                "content": clean_content,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })
            return JSONResponse({"status": "ok"})

    # 5. Сброс в автоматический режим (возврат бота)
    if action == "admin_auto" and session_id:
        db.set_manual_mode(session_id, is_manual=False)
        return JSONResponse({"status": "ok"})

    return JSONResponse({
        "status": "online",
        "message": "API server is running",
        "catalog_items": 29066,
        "debug_action": action,
        "debug_session_id": session_id,
        "debug_qp": dict(request.query_params),
        "debug_url": str(request.url)
    })

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "admin", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/admin/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

INVOICE_DIR = os.path.join(os.path.dirname(__file__), "admin", "invoices")
os.makedirs(INVOICE_DIR, exist_ok=True)
app.mount("/admin/invoices", StaticFiles(directory=INVOICE_DIR), name="admin_invoices")
app.mount("/invoices", StaticFiles(directory=INVOICE_DIR), name="invoices")

@app.post("/api/invoice/create")
async def create_invoice_endpoint(req: Request):
    try:
        data = await req.json()
        session_id = data.get("session_id", "web_unknown")
        client_name = data.get("client_name", "Клиент")
        phone = data.get("phone", "")
        city = data.get("city", "")
        items = data.get("items", [])
        shipping_cost = float(data.get("shipping_cost", 0))
        is_b2b = bool(data.get("is_b2b", False))
        inn = data.get("inn", "")
        passport = data.get("passport", "")
        
        import invoice_generator
        res = invoice_generator.generate_invoice(
            session_id=session_id,
            client_name=client_name,
            phone=phone,
            city=city,
            items=items,
            is_b2b=is_b2b,
            inn=inn,
            passport=passport,
            shipping_cost=shipping_cost
        )
        
        # Автоматически отправляем сообщение со счетом в чат клиенту
        db.save_message(session_id, "bot", res["chat_text"])
        await manager.send_to_client(session_id, {
            "sender": "bot",
            "content": res["chat_text"],
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return {"status": "ok", "invoice": res}
    except Exception as e:
        print(f"[-] Create invoice error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/upload")
async def upload_client_file(req: Request):
    try:
        data = await req.json()
        session_id = data.get("session_id", "web_unknown")
        file_name = data.get("file_name", "document.pdf")
        file_b64 = data.get("file_base64", "")
        
        import base64
        b64data = file_b64.split(",", 1)[1] if "," in file_b64 else file_b64
        file_bytes = base64.b64decode(b64data)
        
        rand_id = secrets.token_hex(4)
        safe_file_name = f"{rand_id}_{file_name.replace(' ', '_')}"
        file_path = os.path.join(UPLOAD_DIR, safe_file_name)
        
        with open(file_path, "wb") as f:
            f.write(file_bytes)
            
        file_url = f"https://regiontehsnab.ru/test-bot-2026/admin/uploads/{safe_file_name}"
        
        # Заносим отправленный файл в переписку в БД
        is_image = any(safe_file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])
        if is_image:
            msg_text = f"🖼️ Вложенное фото/чек:\n[{file_name}]({file_url})"
        else:
            msg_text = f"📎 Вложенный документ PDF:\n[{file_name}]({file_url})"
            
        db.add_message(session_id, "client", msg_text)
        
        # Отправляем уведомительное письмо на manager@regiontehsnab.ru
        try:
            import threading
            import email_notifier
            payload = {
                "invoice_num": f"ПОСТУПИЛ ФАЙЛ/ЧЕК ({file_name})",
                "client_name": f"Клиент сессии {session_id}",
                "phone": "См. историю чата",
                "city": "См. историю чата",
                "total": 0,
                "prepayment": 0,
                "remainder": 0,
                "file_url": file_url
            }
            t = threading.Thread(target=email_notifier.send_invoice_notification_email, args=(payload, session_id))
            t.daemon = True
            t.start()
        except Exception as e_mail:
            print(f"[Upload Email Exception]: {e_mail}")
            
        bot_reply = "Спасибо! Документ / чек об оплате успешно получен и передан в бухгалтерию для сверки. Как только поступит подтверждение оплаты, мы сразу отпишемся!"
        db.add_message(session_id, "bot", bot_reply)
        
        return {
            "status": "ok",
            "file_url": file_url,
            "user_msg": msg_text,
            "bot_reply": bot_reply
        }
    except Exception as e:
        print(f"[-] Upload error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/chat/{session_id}/messages")
def get_public_chat_messages(session_id: str):
    messages = db.get_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}

@app.get("/")
@app.get("/client")
@app.get("/test")
def get_client_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "client.html"))

@app.get("/chat_widget/chat.js")
def get_chat_widget_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "chat_widget/chat.js"))

@app.get("/chat_widget/chat.css")
def get_chat_widget_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "chat_widget/chat.css"))

@app.get("/static/chat.js")
def get_static_chat_js():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static/chat.js"))

@app.get("/static/chat.css")
def get_static_chat_css():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static/chat.css"))
# Active websocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_to_client(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)

manager = ConnectionManager()

def check_auto_reconnect(session_id: str) -> bool:
    is_manual, last_time = db.get_or_create_session(session_id)
    if is_manual and last_time:
        # Check if more than 5 minutes have passed since manager's last message
        last_time_dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() - last_time_dt > timedelta(minutes=5):
            db.set_manual_mode(session_id, is_manual=False)
            return False
    return is_manual

import html


from pydantic import BaseModel
from typing import Optional
from fastapi.responses import JSONResponse
import asyncio

class HTTPChatPayload(BaseModel):
    message: str
    session_id: Optional[str] = None
    source_site: Optional[str] = "regiontehsnab.ru"

@app.post("/chat")
@app.post("/api/chat")
async def http_chat_endpoint(payload: HTTPChatPayload, request: Request):
    session_id = payload.session_id or f"web_{secrets.token_hex(4)}"
    clean_message = html.escape(payload.message.strip())
    if not clean_message:
        return JSONResponse({"reply": "Пожалуйста, введите ваш вопрос.", "session_id": session_id, "score": 5})

    client_ip = request.headers.get("x-client-ip") or request.headers.get("x-forwarded-for") or (request.client.host if request.client else None)
    if client_ip and ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    user_agent = request.headers.get("user-agent")

    db.get_or_create_session(session_id, ip_address=client_ip, user_agent=user_agent)
    db.update_session_status(session_id, "active")

    db.save_message(session_id, "client", clean_message)

    is_manual = check_auto_reconnect(session_id)
    if is_manual:
        return JSONResponse({
            "reply": "Менеджер подключен к диалогу. Вам ответят в ближайшее время.",
            "session_id": session_id,
            "score": 8
        })

    history = db.get_session_messages(session_id)
    bot_reply, score = await asyncio.to_thread(generate_reply, history, clean_message, payload.source_site, False)

    db.save_message(session_id, "bot", bot_reply)
    db.update_session_score(session_id, score)

    return JSONResponse({
        "reply": bot_reply,
        "session_id": session_id,
        "score": score
    })


@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    client_ip = websocket.headers.get("x-forwarded-for") or (websocket.client.host if websocket.client else "127.0.0.1")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    user_agent = websocket.headers.get("user-agent", "")
    
    await manager.connect(websocket, session_id)
    db.get_or_create_session(session_id, ip_address=client_ip, user_agent=user_agent)
    db.update_session_status(session_id, "active")
    
    try:
        while True:
            data = await websocket.receive_text()
            # Escape HTML to prevent XSS attacks
            clean_data = html.escape(data.strip())
            if not clean_data:
                continue
                
            # Save client message
            db.save_message(session_id, "client", clean_data)
            
            # Check if manager is in control
            is_manual = check_auto_reconnect(session_id)
            
            if not is_manual:
                # AI replies
                history = db.get_session_messages(session_id)
                import asyncio
                bot_reply, score = await asyncio.to_thread(generate_reply, history, clean_data, "regiontehsnab.ru", False)
                db.update_session_score(session_id, score)

                import re
                parts = [p.strip() for p in re.split(r'(?<=[.!?\n])\s+', bot_reply) if p.strip()]
                
                for idx, part in enumerate(parts):
                    db.save_message(session_id, "bot", part)
                    delay = min(max(len(part) / 25.0, 1.5), 10.0)
                    if idx == 0:
                        delay = max(0.5, delay * 0.7)
                        
                    await asyncio.sleep(delay)
                    
                    await manager.send_to_client(session_id, {
                        "sender": "bot",
                        "content": part,
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    })
            else:
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(session_id)

@app.post("/api/assistant_chat")
async def assistant_chat_endpoint(payload: HTTPChatPayload, request: Request):
    clean_message = html.escape(payload.message.strip())
    if not clean_message:
        return JSONResponse({"reply": "Пожалуйста, введите ваш вопрос."})
        
    source_site = payload.source_site or "regiontehsnab.ru"
    
    # We pass empty history for assistant, or we could pass context.
    # The assistant is basically stateless for now, just transforming text.
    history = [] 
    
    bot_reply, score = await asyncio.to_thread(generate_reply, history, clean_message, source_site, True)
    
    return JSONResponse({
        "reply": bot_reply
    })

# Admin API Routes (Open access without login/password for testing phase)
@app.get("/admin")
@app.get("/admin/")
@app.get("/admin.html")
def get_admin_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin/index.html"))

@app.get("/admin/assistant.html")
@app.get("/assistant.html")
def get_assistant_ui():
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin/assistant.html"))

@app.get("/admin/db_viewer.html")
@app.get("/db_viewer.html")
def get_admin_db_viewer():
    import browse_database_and_chats
    browse_database_and_chats.generate_interactive_html_viewer()
    return FileResponse(os.path.join(os.path.dirname(__file__), "admin/db_viewer.html"))

@app.get("/api/admin/sessions")
@app.get("/admin/sessions")
def get_sessions():
    all_s = db.get_all_sessions()
    active_connected_ids = set(manager.active_connections.keys())
    
    online_count = 0
    active_count = 0
    completed_count = 0
    
    for s in all_s:
        is_online = s["session_id"] in active_connected_ids
        s["is_online"] = is_online
        if is_online:
            online_count += 1
        if s.get("status") == "completed":
            completed_count += 1
        else:
            active_count += 1

    return {
        "sessions": all_s,
        "stats": {
            "online_count": online_count,
            "active_count": active_count,
            "completed_count": completed_count,
            "total_count": len(all_s)
        }
    }

@app.get("/api/chat/{session_id}/messages")
@app.get("/chat/{session_id}/messages")
@app.get("/api/admin/sessions/{session_id}/messages")
@app.get("/admin/sessions/{session_id}/messages")
def get_messages(session_id: str):
    return {"messages": db.get_session_messages(session_id)}

@app.post("/api/admin/sessions/{session_id}/send")
@app.post("/admin/sessions/{session_id}/send")
async def send_message_from_admin(session_id: str, data: dict):
    content = data.get("content")
    if not content:
        return {"error": "Content is required"}
    
    clean_content = html.escape(content.strip())
    db.save_message(session_id, "manager", clean_content)
    
    await manager.send_to_client(session_id, {
        "sender": "manager",
        "content": clean_content,
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    })
    
    return {"status": "ok"}

@app.post("/api/admin/sessions/{session_id}/auto")
@app.post("/admin/sessions/{session_id}/auto")
def set_auto_mode(session_id: str):
    db.set_manual_mode(session_id, is_manual=False)
    return {"status": "ok"}

@app.post("/api/admin/sessions/{session_id}/complete")
def complete_session(session_id: str):
    db.update_session_status(session_id, "completed")
    return {"status": "ok"}

@app.post("/api/admin/sessions/{session_id}/activate")
def activate_session(session_id: str):
    db.update_session_status(session_id, "active")
    return {"status": "ok"}

@app.get("/api/catalog")
def get_catalog():
    db_path = os.path.join(os.path.dirname(__file__), 'motors_db.json')
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for idx, item in enumerate(data):
            item['id'] = str(idx)
        return {"status": "ok", "items": data}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/catalog/{item_id}")
def get_catalog_item(item_id: str):
    db_path = os.path.join(os.path.dirname(__file__), 'motors_db.json')
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for idx, item in enumerate(data):
            if str(idx) == item_id:
                item['id'] = str(idx)
                return {"status": "ok", "item": item}
        return {"status": "error", "detail": "Item not found"}
    except Exception as e:
         return {"status": "error", "detail": str(e)}

@app.post("/api/orders")
async def create_order(request: Request):
    try:
        data = await request.json()
        # Create a new session for this order
        session_id = f"clone_{secrets.token_hex(6)}"
        client_ip = request.headers.get("x-forwarded-for", "127.0.0.1")
        
        # Save order to DB as a session
        db.get_or_create_session(session_id, ip_address=client_ip, user_agent=request.headers.get("user-agent"))
        
        phone = data.get("phone", "")
        client_name = data.get("client_name", "Клиент с сайта-клона")
        items = data.get("items", [])
        
        # Build order summary
        order_details = ", ".join([f"{item.get('name')} x{item.get('quantity', 1)} ({item.get('price')} руб.)" for item in items])
        db.update_session_requisites(session_id, phone=phone, client_name=client_name, order_details=order_details)
        db.update_session_status(session_id, "active")
        
        # LEVEL 1: DATABASE SAVE
        initial_msg = f"🛒 **Новый заказ с сайта-клона!**\nИмя: {client_name}\nТелефон: {phone}\nЗаказ: {order_details}"
        db.save_message(session_id, "bot", initial_msg)
        
        # LEVEL 2: CSV LOCAL BACKUP (Safeguard)
        csv_path = os.path.join(os.path.dirname(__file__), "satellite_orders_backup.csv")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with open(csv_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp},{session_id},{client_name},{phone},\"{order_details}\"\n")
            
        # LEVEL 3: EMAIL NOTIFICATION
        try:
            import threading
            import email_notifier
            
            total_price = sum([float(str(item.get('price', 0)).replace(' ', '').replace(',','.')) * int(item.get('quantity', 1)) for item in items])
            
            payload = {
                "invoice_num": "ЗАКАЗ С PBN-СЕТИ",
                "client_name": client_name,
                "phone": phone,
                "city": "Уточнить у клиента",
                "total": total_price,
                "prepayment": 0,
                "remainder": 0,
                "file_url": "Источник: Сайт-сателлит (см. базу заказов)"
            }
            t = threading.Thread(target=email_notifier.send_invoice_notification_email, args=(payload, session_id))
            t.daemon = True
            t.start()
        except Exception as e_mail:
            print(f"[Triple Defense] Email notification failed: {e_mail}")
            
        # LEVEL 4: WEB PUSH NOTIFICATION (MANAGER)
        try:
            import threading
            # Append path to import notifier from satellite_builder
            builder_path = os.path.join(os.path.dirname(__file__), "satellite_builder")
            if builder_path not in sys.path:
                sys.path.append(builder_path)
            
            import notifier
            push_title = "💰 Новый заказ мотора (PBN)"
            push_body = f"Имя: {client_name}\nТелефон: {phone}\nЗаказ: {order_details}"
            
            t_push = threading.Thread(target=notifier.send_push_to_topic, args=("manager_alerts", push_title, push_body, "https://dev.regiontehsnab.ru/chat/admin.html"))
            t_push.daemon = True
            t_push.start()
        except Exception as e_push:
            print(f"[Triple Defense] Push notification failed: {e_push}")
        
        return {"status": "ok", "order_id": session_id, "message": "Order created successfully"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
