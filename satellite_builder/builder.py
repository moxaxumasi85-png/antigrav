import os
import re
import json
import random
import urllib.request
import urllib.error

# Используем локальную нейросеть (Ollama)
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b" 

# База ссылок (анкоры и URL) для продвижения regiontehsnab.ru
SEO_LINKS = [
    {"anchor": "Регионтехснаб", "url": "https://regiontehsnab.ru"},
    {"anchor": "на сайте Regiontehsnab", "url": "https://regiontehsnab.ru"},
    {"anchor": "купить двигатель ВАЗ", "url": "https://regiontehsnab.ru/category/dvigateli/"},
    {"anchor": "коробку передач", "url": "https://regiontehsnab.ru/category/kpp/"},
    {"anchor": "здесь", "url": "https://regiontehsnab.ru"}
]

# Варианты тем для сайтов
SITE_THEMES = [
    {"name": "АвтоДвиг Эксперт", "topic": "Ремонт и обслуживание моторов"},
    {"name": "Гараж Мастера", "topic": "Тюнинг и запчасти ВАЗ/Lada"},
    {"name": "ProMotor", "topic": "Советы автомехаников"},
    {"name": "Движок и Коробка", "topic": "Как выбрать трансмиссию и ДВС"}
]

# Темы статей для генерации
ARTICLE_TOPICS = [
    "Как выбрать двигатель на замену для ВАЗ 2114: Ремонт или покупка нового?",
    "Что делать, если оборвало ремень ГРМ на Приоре (126 мотор)",
    "Чем отличается двигатель ВАЗ 21127 от 21129: Подробный обзор",
    "Плюсы и минусы покупки контрактного мотора Рено Логан (K7M)",
    "Тросиковый или электронный дроссель (Е-газ): что лучше для Нивы?"
]

def get_random_template(title, site_name, description, content):
    # Разнообразие шрифтов
    fonts = [
        {"url": "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap", "family": "'Inter', sans-serif"},
        {"url": "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap", "family": "'Roboto', sans-serif"},
        {"url": "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap", "family": "'Montserrat', sans-serif"},
        {"url": "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Lato:wght@400;700&display=swap", "family": "'Lato', sans-serif"},
    ]
    font = __import__('random').choice(fonts)

    # Разнообразие цветовых палитр (Tailwind classes)
    themes = [
        {"bg": "bg-slate-50", "text": "text-slate-900", "primary": "bg-blue-600", "primary_hover": "hover:bg-blue-700", "accent_text": "text-blue-600", "header_bg": "bg-slate-900", "card_bg": "bg-white", "border": "border-slate-200"},
        {"bg": "bg-stone-100", "text": "text-stone-800", "primary": "bg-emerald-600", "primary_hover": "hover:bg-emerald-700", "accent_text": "text-emerald-600", "header_bg": "bg-emerald-900", "card_bg": "bg-stone-50", "border": "border-stone-300"},
        {"bg": "bg-gray-50", "text": "text-gray-900", "primary": "bg-indigo-600", "primary_hover": "hover:bg-indigo-700", "accent_text": "text-indigo-600", "header_bg": "bg-white border-b border-gray-200", "card_bg": "bg-white", "border": "border-indigo-100"},
        {"bg": "bg-neutral-900", "text": "text-neutral-100", "primary": "bg-rose-600", "primary_hover": "hover:bg-rose-500", "accent_text": "text-rose-400", "header_bg": "bg-neutral-950", "card_bg": "bg-neutral-800", "border": "border-neutral-700"},
    ]
    theme = __import__('random').choice(themes)

    # Геометрия и стиль
    rounded = __import__('random').choice(["rounded-none", "rounded-md", "rounded-xl", "rounded-2xl", "rounded-3xl"])
    shadow = __import__('random').choice(["shadow-sm", "shadow-md", "shadow-xl", "shadow-2xl"])
    
    # Hero Sections
    heroes = [
        f"""<div class="{theme['header_bg']} text-white py-20 px-6 text-center {rounded} mb-8">
            <h1 class="text-4xl md:text-6xl font-bold mb-4">{site_name}</h1>
            <p class="text-xl opacity-80 max-w-2xl mx-auto">{description}</p>
        </div>""",
        f"""<div class="flex flex-col md:flex-row items-center justify-between py-16 px-8 mb-12 border-b-4 border-current {theme['accent_text']}">
            <div class="md:w-1/2">
                <h1 class="text-5xl font-black mb-6 tracking-tight {theme['text']}">{site_name}</h1>
                <p class="text-lg {theme['text']} opacity-75">{description}</p>
            </div>
            <div class="md:w-1/3 mt-8 md:mt-0 p-6 {theme['card_bg']} {shadow} {rounded}">
                <p class="font-bold {theme['text']}">Эксперты рекомендуют</p>
            </div>
        </div>""",
        f"""<div class="relative py-24 px-6 overflow-hidden {rounded} mb-10 {theme['header_bg']} text-white">
            <div class="absolute inset-0 bg-gradient-to-r from-black/50 to-transparent"></div>
            <div class="relative z-10 max-w-3xl">
                <h1 class="text-5xl font-extrabold mb-4">{site_name}</h1>
                <p class="text-2xl font-light">{description}</p>
            </div>
        </div>"""
    ]
    
    hero_section = __import__('random').choice(heroes)
    header_style = "text-white" if "text-white" in hero_section else theme['text']

    # Виджет магазина (Каталог)
    store_widget = f"""
    <div id="dynamic-store" class="mt-12">
        <h3 class="text-3xl font-bold mb-6 {theme['accent_text']}">🛒 Каталог двигателей</h3>
        
        <div id="products-grid" class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <p class="{theme['text']}">Загрузка каталога...</p>
        </div>

        <div id="order-form-container" class="hidden p-8 {theme['card_bg']} border-2 {theme['border']} {rounded} {shadow}">
            <h4 class="text-xl font-bold mb-4 {theme['text']}">Оформление заказа: <span id="selected-item-name" class="{theme['accent_text']}"></span></h4>
            <div class="flex flex-col md:flex-row gap-4">
                <input type="text" id="client-name" placeholder="Ваше имя" class="flex-1 p-4 bg-transparent border-2 {theme['border']} {rounded} focus:outline-none focus:ring-2 focus:ring-opacity-50 {theme['text']}">
                <input type="tel" id="client-phone" placeholder="Ваш телефон" class="flex-1 p-4 bg-transparent border-2 {theme['border']} {rounded} focus:outline-none focus:ring-2 focus:ring-opacity-50 {theme['text']}">
                <button onclick="submitOrder()" class="px-8 py-4 {theme['primary']} {theme['primary_hover']} text-white font-bold {rounded} transition-colors shadow-lg">Отправить заявку</button>
            </div>
            <div id="order-status" class="mt-4 font-semibold text-lg hidden"></div>
        </div>
    </div>
    """

    layouts = [
        # Layout 1: Centered Column (Medium Style)
        f"""
        <div class="max-w-4xl mx-auto px-4 py-8">
            <nav class="mb-12 flex justify-between items-center py-4 border-b {theme['border']}">
                <a href="index.html" class="text-2xl font-black tracking-tighter {theme['accent_text']}">{site_name}</a>
                <button id="push-btn" class="hidden text-sm px-4 py-2 {theme['primary']} text-white {rounded} transition">🔔 Подписаться</button>
            </nav>
            {hero_section}
            <main class="prose prose-lg max-w-none {theme['text']} prose-a:{theme['accent_text']}">
                <div class="p-8 {theme['card_bg']} {shadow} {rounded} {theme['border']} border">
                    {content}
                </div>
            </main>
            {store_widget}
        </div>
        """,
        # Layout 2: Two Columns (Magazine Style)
        f"""
        <div class="max-w-7xl mx-auto px-4 py-8">
            <div class="flex justify-between items-center w-full mb-4">
                <div></div>
                <button id="push-btn" class="hidden text-sm px-4 py-2 {theme['primary']} text-white {rounded} transition">🔔 Подписаться на новости</button>
            </div>
            {hero_section}
            <div class="flex flex-col lg:flex-row gap-12">
                <main class="lg:w-2/3 prose max-w-none {theme['text']} prose-a:{theme['accent_text']} p-6 {theme['card_bg']} {rounded} {shadow}">
                    {content}
                </main>
                <aside class="lg:w-1/3">
                    <div class="sticky top-8">
                        {store_widget}
                        <div class="mt-8 p-6 {theme['card_bg']} {rounded} border {theme['border']} {shadow}">
                            <h4 class="font-bold mb-4 {theme['text']}">О проекте</h4>
                            <p class="text-sm opacity-80 {theme['text']}">{description}</p>
                        </div>
                    </div>
                </aside>
            </div>
        </div>
        """
    ]
    
    layout = __import__('random').choice(layouts)

    html = f"""<!DOCTYPE html>
<html lang="ru" class="{theme['bg']}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | {site_name}</title>
    <meta name="description" content="{description}">
    <link href="{font['url']}" rel="stylesheet">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                fontFamily: {{
                    sans: [{font['family']}],
                }}
            }}
        }}
    </script>
    <style>
        /* Fix for prose (articles) inside tailwind without typography plugin */
        article h2 {{ font-size: 1.875rem; font-weight: 700; margin-top: 2rem; margin-bottom: 1rem; }}
        article h3 {{ font-size: 1.5rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.75rem; }}
        article p {{ margin-bottom: 1.25rem; line-height: 1.75; }}
        article ul {{ list-style-type: disc; padding-left: 1.5rem; margin-bottom: 1.25rem; }}
        article a {{ text-decoration: underline; font-weight: 500; }}
        .article-card {{ margin-bottom: 2rem; padding: 1.5rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; }}
        .article-card h2 {{ margin: 0 0 0.5rem 0; font-size: 1.5rem; }}
    </style>
</head>
<body class="font-sans antialiased min-h-screen flex flex-col">
    <div class="flex-grow">
        {layout}
    </div>
    
    <footer class="{theme['header_bg']} text-white py-12 mt-20">
        <div class="max-w-6xl mx-auto px-6 text-center">
            <h2 class="text-2xl font-bold mb-4">{site_name}</h2>
            <p class="opacity-75 mb-8">{description}</p>
            <div class="opacity-50 text-sm">&copy; 2026 {site_name}. Все материалы уникальны.</div>
        </div>
    </footer>

    <script type="module">
        // Firebase Cloud Messaging (Web Push)
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
        import {{ getMessaging, getToken, onMessage }} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-messaging.js";

        const firebaseConfig = {{
            projectId: "antigrav-e623c",
            appId: "1:258429885693:web:0fedb88a2e5889cec07294",
            storageBucket: "antigrav-e623c.firebasestorage.app",
            apiKey: "AIzaSyDMjmvgpB1Qdms5n9xYSF16Nca04dGGOKs",
            authDomain: "antigrav-e623c.firebaseapp.com",
            messagingSenderId: "258429885693"
        }};

        let app, messaging;
        try {{
            app = initializeApp(firebaseConfig);
            messaging = getMessaging(app);
            
            // Handle incoming messages while app is in foreground
            onMessage(messaging, (payload) => {{
                console.log('Message received.', payload);
                if(payload.notification) {{
                    alert(payload.notification.title + "\n" + payload.notification.body);
                }}
            }});
        }} catch(e) {{
            console.log("Firebase init error:", e);
        }}

        // Подписываемся на пуши при клике по кнопке (или автоматически)
        const pushBtn = document.getElementById('push-btn');
        if (pushBtn) {{
            if (Notification.permission === 'default') {{
                pushBtn.classList.remove('hidden');
                pushBtn.addEventListener('click', async () => {{
                    try {{
                        const permission = await Notification.requestPermission();
                        if (permission === 'granted') {{
                            // TODO: Вставьте ваш реальный vapidKey из консоли Firebase
                            const vapidKey = 'BFe97Lp8Qv2MewbF41k4h5n-V41x'; // Placeholder, replace with real
                            const currentToken = await getToken(messaging, {{ vapidKey: vapidKey }});
                            if (currentToken) {{
                                console.log('Got FCM token:', currentToken);
                                pushBtn.innerText = "✅ Подписаны";
                                pushBtn.disabled = true;
                                
                                // Отправляем токен на бэкенд, чтобы подписать на тему
                                fetch('https://regiontehsnab.ru/api/push_subscribe', {{
                                    method: 'POST',
                                    headers: {{'Content-Type': 'application/json'}},
                                    body: JSON.stringify({{ token: currentToken, topic: 'all_pbn_users' }})
                                }}).catch(e => console.log(e));
                            }}
                        }}
                    }} catch (err) {{
                        console.log('An error occurred while retrieving token. ', err);
                    }}
                }});
            }} else if (Notification.permission === 'granted') {{
                pushBtn.classList.remove('hidden');
                pushBtn.innerText = "✅ Уведомления включены";
                pushBtn.disabled = true;
            }}
        }}

        // Store Logic
        const API_BASE = "https://antigrav-p34u.onrender.com/api";
        let currentItem = null;
        
        window.openOrderForm = function(name, price) {{
            currentItem = {{ name, price }};
            document.getElementById('selected-item-name').innerText = name + " (" + price + " руб.)";
            document.getElementById('order-form-container').classList.remove('hidden');
            document.getElementById('order-form-container').scrollIntoView({{ behavior: 'smooth' }});
        }};

        async function loadDynamicPricing() {{
            try {{
                const response = await fetch(`${{API_BASE}}/catalog`);
                const data = await response.json();
                if (data.status === "ok" && data.items.length > 0) {{
                    const grid = document.getElementById('products-grid');
                    grid.innerHTML = "";
                    
                    // Выбираем 4 случайных мотора для витрины
                    const shuffled = data.items.sort(() => 0.5 - Math.random());
                    const selected = shuffled.slice(0, 4);
                    
                    selected.forEach(item => {{
                        const card = document.createElement('div');
                        card.className = "p-6 {theme['card_bg']} border {theme['border']} {rounded} {shadow} hover:shadow-lg transition-shadow";
                        card.innerHTML = `
                            <h5 class="text-xl font-bold mb-2 {theme['text']}">${{item.name}}</h5>
                            <p class="text-sm opacity-70 mb-4 {theme['text']}">${{item.description || 'Оригинальный двигатель заводской сборки.'}}</p>
                            <p class="text-2xl font-black mb-4 {theme['accent_text']}">${{item.price}} руб.</p>
                            <button onclick="openOrderForm('${{item.name}}', '${{item.price}}')" class="w-full py-2 {theme['primary']} {theme['primary_hover']} text-white font-bold {rounded} transition-colors">Купить</button>
                        `;
                        grid.appendChild(card);
                    }});
                }}
            }} catch (error) {{
                document.getElementById('products-grid').innerHTML = "<p class='text-red-500'>Не удалось загрузить каталог. Попробуйте позже.</p>";
            }}
        }}
        
        window.submitOrder = async function() {{
            const name = document.getElementById('client-name').value;
            const phone = document.getElementById('client-phone').value;
            const statusDiv = document.getElementById('order-status');
            
            if (!name || !phone) {{ 
                statusDiv.innerText = "⚠️ Пожалуйста, заполните имя и телефон"; 
                statusDiv.classList.remove('hidden');
                statusDiv.classList.add('text-red-500');
                return; 
            }}
            
            statusDiv.innerText = "⏳ Отправка заявки...";
            statusDiv.classList.remove('hidden', 'text-red-500');
            statusDiv.classList.add('text-yellow-500');
            
            try {{
                const response = await fetch(`${{API_BASE}}/orders`, {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{client_name: name, phone: phone, items: [{{ name: currentItem.name, price: currentItem.price, quantity: 1 }}]}})
                }});
                const resData = await response.json();
                if (resData.status === "ok") {{ 
                    statusDiv.innerText = "✅ Ваша заявка успешно принята!"; 
                    statusDiv.classList.remove('text-yellow-500');
                    statusDiv.classList.add('text-green-500');
                    document.getElementById('client-name').value = "";
                    document.getElementById('client-phone').value = "";
                }} else {{ throw new Error("error"); }}
            }} catch (error) {{ 
                statusDiv.innerText = "❌ Ошибка соединения. Попробуйте позже."; 
                statusDiv.classList.remove('text-yellow-500');
                statusDiv.classList.add('text-red-500');
            }}
        }}
        document.addEventListener("DOMContentLoaded", loadDynamicPricing);
    </script>
</body>
</html>"""
    return html

def generate_article(topic):
    prompt = f"""Ты — профессиональный SEO-копирайтер и эксперт-автомеханик. 
Твоя задача — написать максимально уникальную, технически грамотную статью для автоблога на тему: "{topic}".
КРИТИЧЕСКОЕ ПРАВИЛО (Anti-pattern): Избегай шаблонных фраз. Используй максимум синонимов и LSI-слов. Текст должен кардинально отличаться по структуре от других твоих текстов.
Используй разнообразные стили (от первого лица, разговорный, или строго технический — выбери случайно). Меняй структуру: используй списки (<ul>, <ol>), цитаты (<blockquote>), жирный текст (<strong>) и подзаголовки (<h2>, <h3>).
Формат ответа: Только чистый HTML-код (без тегов <html>, <head> или <body>).
Объем: 400-600 слов. Текст должен удерживать внимание читателя до самого конца.
"""
    try:
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        req = urllib.request.Request(OLLAMA_URL, data=json.dumps(data).encode('utf-8'), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            
        html_content = response_data.get("response", "").strip()
        # Очистка от маркдауна, если есть
        if html_content.startswith("```html"):
            html_content = html_content[7:-3]
        return html_content
    except Exception as e:
        print(f"Ошибка при генерации статьи: {e}")
        return f"<p>Тестовая статья для <b>{topic}</b>. Оллама недоступна, используется заглушка для тестирования шаблона.</p>"

def inject_seo_link(html_content):
    # Выбираем случайную ссылку
    link_data = __import__('random').choice(SEO_LINKS)
    anchor = link_data["anchor"]
    url = link_data["url"]
    
    a_tag = f'<a href="{url}" target="_blank">{anchor}</a>'
    
    # Пытаемся найти подходящее место. Если анкор - LSI фраза, ищем её в тексте
    if anchor.lower() in html_content.lower() and len(anchor) > 5:
        # Заменяем одно вхождение
        pattern = re.compile(re.escape(anchor), re.IGNORECASE)
        html_content = pattern.sub(a_tag, html_content, count=1)
        return html_content
    
    # Если анкор не найден (или это брендовый запрос), вставляем в конец случайного абзаца
    paragraphs = re.findall(r'<p>(.*?)</p>', html_content, flags=re.DOTALL)
    if len(paragraphs) > 2:
        # Вставляем во второй или третий абзац
        target_p = paragraphs[1]
        
        # Добавляем контекстное предложение
        context_sentences = [
            f" К слову, найти качественные детали можно {a_tag}.",
            f" Рекомендуем смотреть оригинальные агрегаты {a_tag}.",
            f" Если вы ищете замену, посмотрите {a_tag}.",
            f" Подробную информацию и прайс-листы предоставляет {a_tag}."
        ]
        new_p = target_p + __import__('random').choice(context_sentences)
        
        html_content = html_content.replace(f"<p>{target_p}</p>", f"<p>{new_p}</p>", 1)
    
    return html_content

OUTPUT_DIR = "output_sites/satellite_1"

def write_firebase_sw(output_dir):
    """Создает firebase-messaging-sw.js в корне сайта"""
    sw_content = """importScripts("https://www.gstatic.com/firebasejs/10.13.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.13.0/firebase-messaging-compat.js");

firebase.initializeApp({
  projectId: "antigrav-e623c",
  appId: "1:258429885693:web:0fedb88a2e5889cec07294",
  storageBucket: "antigrav-e623c.firebasestorage.app",
  apiKey: "AIzaSyDMjmvgpB1Qdms5n9xYSF16Nca04dGGOKs",
  authDomain: "antigrav-e623c.firebaseapp.com",
  messagingSenderId: "258429885693"
});

const messaging = firebase.messaging();
messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] Received background message ', payload);
  const notificationTitle = payload.notification.title;
  const notificationOptions = {
    body: payload.notification.body,
    icon: payload.notification.icon || 'https://regiontehsnab.ru/favicon.ico'
  };
  self.registration.showNotification(notificationTitle, notificationOptions);
});
"""
    with open(__import__('os').path.join(output_dir, "firebase-messaging-sw.js"), 'w', encoding='utf-8') as f:
        f.write(sw_content)

def build_site():
    __import__('os').makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Создаем Service Worker для Push-уведомлений
    write_firebase_sw(OUTPUT_DIR)
    
    # Случайная тема сайта
    site_theme = __import__('random').choice(SITE_THEMES)
    site_name = site_theme["name"]
    site_topic = site_theme["topic"]
    
    articles = []
    print(f"Генерация сателлита: {site_name}")
    
    for i, topic in enumerate(ARTICLE_TOPICS):
        print(f"[{i+1}/{len(ARTICLE_TOPICS)}] Пишем статью: {topic}")
        raw_html = generate_article(topic)
        if not raw_html:
            continue
            
        html_with_link = inject_seo_link(raw_html)
        file_name = f"article_{i+1}.html"
        
        page_html = get_random_template(
            title=topic,
            site_name=site_name,
            description=f"Подробная статья про {topic}",
            content=f"<article>{html_with_link}</article>"
        )
        
        with open(__import__('os').path.join(OUTPUT_DIR, file_name), 'w', encoding='utf-8') as f:
            f.write(page_html)
            
        articles.append({
            "title": topic,
            "url": file_name,
            "snippet": re.sub(r'<[^>]+>', '', html_with_link)[:150] + "..."
        })
        
    print("Генерация главной страницы...")
    index_content = "<h2>Последние статьи</h2>"
    for art in articles:
        index_content += f"""
        <div class="article-card">
            <h2><a href="{art['url']}">{art['title']}</a></h2>
            <p class="date">Август 2026</p>
            <p>{art['snippet']}</p>
        </div>
        """
        
    index_html = get_random_template(
        title="Главная",
        site_name=site_name,
        description=site_topic,
        content=index_content
    )
    
    with open(__import__('os').path.join(OUTPUT_DIR, "index.html"), 'w', encoding='utf-8') as f:
        f.write(index_html)
        
    print(f"Готово! Уникальный сайт сгенерирован в папке {OUTPUT_DIR}")

if __name__ == "__main__":
    build_site()
