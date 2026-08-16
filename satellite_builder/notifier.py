import os
import sys
import firebase_admin
from firebase_admin import credentials, messaging

# Инициализация Firebase
CREDS_PATH = "../firebase-adminsdk.json"
if not os.path.exists(CREDS_PATH):
    print(f"Ошибка: Не найден файл {CREDS_PATH}")
    sys.exit(1)

cred = credentials.Certificate(CREDS_PATH)
try:
    firebase_admin.initialize_app(cred)
except ValueError:
    pass # Уже инициализировано

def send_push_to_topic(topic, title, body, url=None):
    """Отправляет пуш-уведомление всем подписчикам топика"""
    print(f"[*] Отправка Push-уведомления на тему '{topic}'...")
    
    # Формируем сообщение
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
        webpush=messaging.WebpushConfig(
            notification=messaging.WebpushNotification(
                icon="https://regiontehsnab.ru/favicon.ico",
                require_interaction=True
            ),
            fcm_options=messaging.WebpushFCMOptions(
                link=url if url else "https://regiontehsnab.ru"
            )
        ),
        topic=topic,
    )

    try:
        response = messaging.send(message)
        print(f"[+] Успешно отправлено: {response}")
        return True
    except Exception as e:
        print(f"[-] Ошибка отправки: {e}")
        return False

def subscribe_token_to_topic(token, topic):
    """Подписывает конкретный токен на топик"""
    try:
        response = messaging.subscribe_to_topic([token], topic)
        print(f"[+] Токен подписан на {topic}. Успешно: {response.success_count}, Ошибок: {response.failure_count}")
    except Exception as e:
        print(f"[-] Ошибка подписки токена: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PBN Firebase Notifier")
    parser.add_argument("--topic", type=str, default="all_pbn_users", help="Топик для рассылки (по умолчанию all_pbn_users)")
    parser.add_argument("--title", type=str, required=True, help="Заголовок уведомления")
    parser.add_argument("--body", type=str, required=True, help="Текст уведомления")
    parser.add_argument("--url", type=str, help="Ссылка при клике")
    
    args = parser.parse_args()
    
    send_push_to_topic(args.topic, args.title, args.body, args.url)
