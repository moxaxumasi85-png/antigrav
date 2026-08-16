import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import os
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

SMTP_SERVER = os.environ.get("SMTP_SERVER", "connect.smtp.bz")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "manager@regiontehsnab.ru")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "")

DEFAULT_RECPT = "manager@regiontehsnab.ru"

def get_session_chat_history(session_id: str) -> str:
    db_path = os.path.join(os.path.dirname(__file__), "chat.db")
    if not os.path.exists(db_path):
        return "История чата недоступна"

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
        msgs = [dict(r) for r in c.fetchall()]
        conn.close()

        lines = []
        for m in msgs:
            sender_name = "👤 Клиент" if m["sender"] == "client" else ("🤖 Анна (ИИ)" if m["sender"] == "bot" else "👨‍💼 Менеджер")
            lines.append(f"[{m['timestamp']}] {sender_name}:\n{m['content']}\n")
        
        return "\n".join(lines) if lines else "История сообщений пуста."
    except Exception as e:
        return f"Ошибка загрузки истории чата: {e}"

def send_invoice_notification_email(invoice_data: dict, session_id: str, recipient_email: str = DEFAULT_RECPT):
    """
    Отправляет уведомление о новом выписанном счете и полную историю переписки менеджеру.
    """
    try:
        chat_history = get_session_chat_history(session_id)
        invoice_num = invoice_data.get("invoice_num", "БЕЗ_НОМЕРА")
        client_name = invoice_data.get("client_name", "Физ. лицо")
        city = invoice_data.get("city", "Не указан")
        phone = invoice_data.get("phone", "Не указан")
        total = invoice_data.get("total", 0)
        prepayment = invoice_data.get("prepayment", 0)
        remainder = invoice_data.get("remainder", 0)
        file_url = invoice_data.get("file_url", "")

        subject = f"📄 ВЫСТАВЛЕН СЧЕТ № {invoice_num} — {client_name} (г. {city})"

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.5; color: #333;">
            <div style="background: #1e3a8a; color: #fff; padding: 15px; border-radius: 8px;">
                <h2 style="margin:0;">📄 Новый Выставленный Счет № {invoice_num}</h2>
                <p style="margin:5px 0 0 0;">Автоматическое уведомление от ИИ-Консультанта Анны</p>
            </div>

            <div style="background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px; margin-top: 15px; border-radius: 8px;">
                <h3>👤 Данные клиента:</h3>
                <ul>
                    <li><b>ФИО / Клиент:</b> {client_name}</li>
                    <li><b>Телефон:</b> {phone}</li>
                    <li><b>Город доставки:</b> {city}</li>
                    <li><b>ID Сессии чата:</b> {session_id}</li>
                </ul>

                <h3>💰 Финансовая сводка:</h3>
                <ul>
                    <li><b>Общая сумма заказа:</b> {total:,.2f} руб.</li>
                    <li><b>Предоплата 10%:</b> <b style="color: #059669;">{prepayment:,.2f} руб.</b></li>
                    <li><b>Остаток 90% (при получении):</b> {remainder:,.2f} руб.</li>
                </ul>

                <p>🔗 <b>Бланк счета для печати/просмотра:</b><br>
                <a href="{file_url}" target="_blank" style="color: #2563eb; font-weight: bold;">{file_url}</a></p>
            </div>

            <div style="margin-top: 20px; border-top: 2px solid #cbd5e1; padding-top: 15px;">
                <h3>💬 Полная история переписки с клиентом:</h3>
                <pre style="background: #0f172a; color: #f8fafc; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-size: 13px;">{chat_history}</pre>
            </div>

            <p style="font-size: 12px; color: #64748b; margin-top: 20px;">
                Клиенту отправлена инструкция: <i>«После оплаты прислать чек в чат или на e-mail: {recipient_email}»</i>.
            </p>
        </body>
        </html>
        """

        import requests
        
        # NOTE: Please set your actual smtp.bz API key here via environment variable
        API_KEY = os.environ.get("SMTP_BZ_API_KEY", "")
        
        url = "https://api.smtp.bz/v1/smtp/send"
        headers = {
            "Authorization": API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "name": "RTS AI Bot",
            "from": SENDER_EMAIL,
            "to": recipient_email,
            "subject": subject,
            "html": html_body
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Уведомление о счете {invoice_num} и история чата успешно отправлены на {recipient_email} через API smtp.bz!")
            return True
        else:
            print(f"[-] Ошибка API smtp.bz: {response.status_code} {response.text}")
            return False

    except Exception as e:
        print(f"[-] Ошибка отправки email менеджеру: {e}")
        return False

if __name__ == "__main__":
    # Тестовая отправка
    test_data = {
        "invoice_num": "RTS-TEST-001",
        "client_name": "Иванов Сергей Петрович",
        "phone": "+79033334461",
        "city": "Ярославль",
        "total": 157130.0,
        "prepayment": 15713.0,
        "remainder": 141417.0,
        "file_url": "https://regiontehsnab.ru/test-bot-2026/admin/invoices/invoice_test.html"
    }
    send_invoice_notification_email(test_data, "test_session_id")
