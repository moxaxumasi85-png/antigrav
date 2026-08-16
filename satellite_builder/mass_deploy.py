import os
import json
import subprocess
import time
import argparse
import random
from datetime import datetime

# База данных наших сателлитов
DB_FILE = "pbn_database.json"
ENV_FILE = "../.env"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"sites": []}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_available_platforms():
    """Определяет, какие платформы имеют настроенные ключи."""
    platforms = []
    
    # Firebase (проверяем наличие JSON-ключа)
    if os.path.exists("../firebase-adminsdk.json"):
        platforms.append("firebase")
        
    # Парсим .env для Netlify/Vercel
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            if "NETLIFY_TOKEN=" in content:
                platforms.append("netlify")
            if "VERCEL_API_KEY=" in content:
                platforms.append("vercel")
            if "SURGE_TOKEN=" in content:
                platforms.append("surge")
            if "CLOUDFLARE_API_TOKEN=" in content:
                platforms.append("cloudflare")
        except Exception:
            pass
            
    # Fallback, если ничего не найдено, пробуем firebase и netlify на удачу
    if not platforms:
        platforms = ["firebase", "netlify"]
        
    return platforms

def mass_generate_and_deploy(num_sites=1, platform="random"):
    print(f"[*] Начинаем массовое создание сателлитов: {num_sites} шт.")
    db = load_db()
    
    available_platforms = get_available_platforms()
    if platform != "random" and platform not in available_platforms:
        print(f"[!] Внимание: Выбрана платформа '{platform}', но ключи для нее могут быть не настроены.")
        available_platforms = [platform]
        
    for i in range(num_sites):
        current_platform = random.choice(available_platforms) if platform == "random" else platform
        
        print(f"\n--- Создание сателлита {i+1} из {num_sites} ---")
        print(f"[*] Выбран хостинг: {current_platform}")
        
        # 1. Генерация сателлита
        print("[*] Генерация контента...")
        builder_proc = subprocess.run(["python", "builder.py"], capture_output=True, text=True)
        if builder_proc.returncode != 0:
            print("[-] Ошибка при генерации:")
            print(builder_proc.stderr)
            continue
            
        site_dir = "output_sites/satellite_1" 
        
        # 2. Деплой на платформу
        print(f"[*] Деплой в сеть (Платформа: {current_platform})...")
        deploy_proc = subprocess.run(["python", "deployer.py", "--site", site_dir, "--platform", current_platform], capture_output=True, text=True)
        
        url = None
        for line in deploy_proc.stdout.split('\n'):
            if line.startswith("[+] Ссылка на сайт:"):
                url = line.split(":", 1)[1].strip()
                break
                
        if url:
            print(f"[+] Сайт успешно размещен: {url}")
            db["sites"].append({
                "url": url,
                "topic": "Двигатели ВАЗ (тест)",
                "created_at": datetime.now().isoformat(),
                "platform": current_platform,
                "status": "active"
            })
            save_db(db)
        else:
            print("[-] Не удалось получить URL после деплоя.")
            print(deploy_proc.stdout)
            print(deploy_proc.stderr)
            
        # Пауза между созданиями, чтобы не перегружать API и нейросеть
        if i < num_sites - 1:
            time.sleep(5)
        
    print(f"\n[+] Массовая генерация завершена! Все данные сохранены в {DB_FILE}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mass Deploy PBN Sites")
    parser.add_argument("--count", type=int, default=1, help="Количество сайтов для генерации")
    parser.add_argument("--platform", type=str, choices=["random", "surge", "netlify", "vercel", "firebase", "cloudflare"], default="random", help="Платформа для публикации")
    args = parser.parse_args()
    
    mass_generate_and_deploy(args.count, args.platform)
