/**
 * Виджет чат-бота RegionTehsnab
 * Подключить на страницу:
 *   <link rel="stylesheet" href="/chat-widget/chat.css">
 *   <script src="/chat-widget/chat.js"></script>
 *   <script>RTSChat.init({ apiUrl: 'https://regiontehsnab.ru/api.php' });</script>
 */
(function() {
    'use strict';

    // ===== КОНФИГ =====
    var CONFIG = {
        apiUrl: 'https://terry-clark-pepper-speeds.trycloudflare.com',
        welcomeMsg: 'Здравствуйте! Меня зовут Анна, я консультант магазина моторов RegionTehsnab. Помогу подобрать агрегат, уточнить наличие и рассчитать доставку. Подсказать вам что-нибудь по выбору?',
        botName: 'Анна',
        botStatus: 'Консультант онлайн',
        autoOpenDelay: 10000 // Задержка перед авто-открытием (в миллисекундах)
    };

    // ===== СОСТОЯНИЕ =====
    var ws = null;
    var sessionId = null;
    var unreadCount = 0;
    var isOpen = false;
    var reconnectTimer = null;

    // ===== УТИЛИТЫ =====
    function generateSessionId() {
        var stored = localStorage.getItem('rts_chat_session');
        if (stored) return stored;
        var id = 'web_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
        localStorage.setItem('rts_chat_session', id);
        return id;
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function linkify(text) {
        var escaped = escapeHtml(text);
        return escaped.replace(/(https?:\/\/[^\s<>"]*[^\s<>".;,!?])/g, '<a href="$1" target="_blank" rel="noopener">$1</a>');
    }

    // ===== ШАБЛОН HTML =====
    function createWidget() {
        var html = [
            '<div id="rts-proactive-bubble" class="rts-proactive-bubble">',
            '  <button class="rts-proactive-close" aria-label="Закрыть">&times;</button>',
            '  <div class="rts-proactive-content">',
            '    <strong>' + CONFIG.botName + '</strong>',
            '    <p>👋 Здравствуйте! Помочь подобрать двигатель или расчитать доставку?</p>',
            '  </div>',
            '</div>',
            '<button id="rts-chat-toggle" aria-label="Открыть чат">',
            '  <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">',
            '    <path d="M20 2H4a2 2 0 0 0-2 2v18l4-4h14a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2zm-2 10H6V10h12v2zm0-3H6V7h12v2z"/>',
            '  </svg>',
            '  <span class="rts-badge" id="rts-badge"></span>',
            '</button>',
            '<div id="rts-chat-window" role="dialog" aria-label="Чат с консультантом">',
            '  <div class="rts-header">',
            '    <div class="rts-avatar">🛞<div class="rts-online-dot"></div></div>',
            '    <div class="rts-header-info">',
            '      <strong>' + CONFIG.botName + '</strong>',
            '      <span id="rts-bot-status"><i class="rts-status-dot"></i>' + CONFIG.botStatus + '</span>',
            '    </div>',
            '    <button class="rts-close-btn" id="rts-chat-close" aria-label="Закрыть чат">',
            '      <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
            '    </button>',
            '  </div>',
            '  <div class="rts-messages" id="rts-messages">',
            '    <div class="rts-welcome">🔒 Защищенное соединение · RegionTehsnab</div>',
            '  </div>',
            '  <div class="rts-chips" id="rts-chips">',
            '    <button class="rts-chip" onclick="RTSChat.sendQuick(\'Есть двигатель ВАЗ 21126?\')">⚙️ Двигатель 21126</button>',
            '    <button class="rts-chip" onclick="RTSChat.sendQuick(\'Нужен мотор на Ниву 21214\')">🚜 Мотор на Ниву</button>',
            '    <button class="rts-chip" onclick="RTSChat.sendQuick(\'Рассчитать доставку\')">🚚 Доставка</button>',
            '    <button class="rts-chip" onclick="RTSChat.sendQuick(\'Хочу поговорить с менеджером\')">👤 Менеджер</button>',
            '  </div>',
            '  <div class="rts-typing" id="rts-typing">',
            '    <span></span><span></span><span></span>',
            '  </div>',
            '  <div class="rts-input-area">',
            '    <textarea id="rts-input" placeholder="Введите сообщение..." rows="1" aria-label="Сообщение"></textarea>',
            '    <button class="rts-mic-btn" id="rts-mic" aria-label="Голосовой ввод" title="Голосовой ввод">',
            '      <svg viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/></svg>',
            '    </button>',
            '    <button class="rts-send-btn" id="rts-send" aria-label="Отправить">',
            '      <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>',
            '    </button>',
            '  </div>',
            '</div>'
        ].join('\n');

        var container = document.createElement('div');
        container.id = 'rts-chat-root';
        container.innerHTML = html;
        document.body.appendChild(container);
    }

    // ===== ЗВУК УВЕДОМЛЕНИЯ (Web Audio API) =====
    function playNotificationSound() {
        try {
            var ctx = new (window.AudioContext || window.webkitAudioContext)();
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
            osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.12); // A5
            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.15);
        } catch(e) {}
    }

    var renderedCount = 0;

    // ===== СООБЩЕНИЯ =====
    function appendMessage(sender, text, timestamp, isSilent) {
        var messagesEl = document.getElementById('rts-messages');
        var div = document.createElement('div');
        var sClass = sender;
        if (sender === 'assistant') sClass = 'bot';
        div.className = 'rts-msg ' + sClass;

        var prefix = '';
        if (sender === 'manager') {
            prefix = '<strong style="color:#0056b3;display:block;font-size:11px;margin-bottom:2px;">👤 Менеджер</strong>';
        }
        div.innerHTML = prefix + linkify(text);

        var timeDiv = document.createElement('div');
        timeDiv.className = 'rts-msg-time';
        var t = new Date();
        if (timestamp) {
            var parsed = new Date(timestamp.replace(' ', 'T') + 'Z');
            if (!isNaN(parsed)) t = parsed;
        }
        timeDiv.textContent = t.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
        div.appendChild(timeDiv);

        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        // Звуковое оповещение и бейдж для сообщений бота/менеджера (если не тихий режим)
        if (!isSilent && (sender === 'bot' || sender === 'assistant' || sender === 'manager')) {
            playNotificationSound();
            if (!isOpen) {
                unreadCount++;
                updateBadge();
            }
        }
    }

    function showTyping(show) {
        var el = document.getElementById('rts-typing');
        if (el) el.classList.toggle('visible', show);
        if (show) {
            var msgs = document.getElementById('rts-messages');
            msgs.scrollTop = msgs.scrollHeight;
        }
    }

    function updateBadge() {
        var badge = document.getElementById('rts-badge');
        if (!badge) return;
        if (unreadCount > 0) {
            badge.textContent = unreadCount > 9 ? '9+' : unreadCount;
            badge.classList.add('visible');
        } else {
            badge.classList.remove('visible');
        }
    }

    // ===== ИСТОРИЯ И ПОЛЛИНГ =====
    function getApiEndpoint(path, legacyAction) {
        if (CONFIG.apiUrl.includes('trycloudflare.com') || CONFIG.apiUrl.includes('http://87.228.52.250')) {
            return CONFIG.apiUrl + path;
        }
        return CONFIG.apiUrl + '?action=' + legacyAction;
    }

    function loadHistory() {
        var url = getApiEndpoint('/api/chat/' + sessionId + '/messages', 'history&session_id=' + sessionId);

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var messagesEl = document.getElementById('rts-messages');
                if (data && data.messages && data.messages.length > 0) {
                    messagesEl.innerHTML = '<div class="rts-welcome">🔒 Защищенное соединение · RegionTehsnab</div>';
                    renderedCount = 0;
                    data.messages.forEach(function(msg) {
                        appendMessage(msg.sender, msg.content, msg.timestamp, true);
                    });
                    renderedCount = data.messages.length;
                } else {
                    if (renderedCount === 0) {
                        appendMessage('bot', CONFIG.welcomeMsg, null, true);
                        renderedCount = 1;
                    }
                }
            })
            .catch(function() {
                var messagesEl = document.getElementById('rts-messages');
                if (renderedCount === 0) {
                    appendMessage('bot', CONFIG.welcomeMsg, null, true);
                    renderedCount = 1;
                }
            });
    }

    function pollMessages() {
        if (!sessionId) return;
        var url = getApiEndpoint('/api/chat/' + sessionId + '/messages', 'history&session_id=' + sessionId);

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data && data.messages && data.messages.length > renderedCount) {
                    var newMsgs = data.messages.slice(renderedCount);
                    newMsgs.forEach(function(msg) {
                        appendMessage(msg.sender, msg.content, msg.timestamp, false);
                    });
                    renderedCount = data.messages.length;
                }
            })
            .catch(function() {});
    }

    function connectWS() {
        var statusEl = document.getElementById('rts-bot-status');
        if (statusEl) statusEl.textContent = CONFIG.botStatus || 'Консультант онлайн';
        setInterval(pollMessages, 3000);
    }

    // ===== ОТПРАВКА =====
    function sendMessage(customText) {
        var input = document.getElementById('rts-input');
        var text = (customText || input.value).trim();
        if (!text) return;

        appendMessage('client', text, null, false);
        renderedCount++;
        showTyping(true);
        if (!customText) {
            input.value = '';
            input.style.height = 'auto';
        }
        hideProactiveBubble();

        var payload = {
            message: text,
            session_id: sessionId,
            history: []
        };

        var chatUrl = getApiEndpoint('/chat', 'chat');

        fetch(chatUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            showTyping(false);
            pollMessages();
        })
        .catch(function(err) {
            showTyping(false);
            console.error('[RTSChat] HTTP Error:', err);
            appendMessage('assistant', 'Здравствуйте! Я на связи. Подсказать вам комплектацию или расчитать доставку мотора?', null, false);
        });
    }

    // ===== ПРОАКТИВНЫЙ БАББЛ (JivoSite Style) =====
    function showProactiveBubble() {
        if (isOpen) return;
        var bubble = document.getElementById('rts-proactive-bubble');
        if (bubble) bubble.classList.add('visible');
    }

    function hideProactiveBubble() {
        var bubble = document.getElementById('rts-proactive-bubble');
        if (bubble) bubble.classList.remove('visible');
    }

    // ===== ОТКРЫТИЕ / ЗАКРЫТИЕ =====
    function toggleChat() {
        isOpen = !isOpen;
        var win = document.getElementById('rts-chat-window');
        win.classList.toggle('open', isOpen);
        hideProactiveBubble();

        if (isOpen) {
            unreadCount = 0;
            updateBadge();
            document.getElementById('rts-input').focus();
            var msgs = document.getElementById('rts-messages');
            msgs.scrollTop = msgs.scrollHeight;
        }
    }

    // ===== ИНИЦИАЛИЗАЦИЯ =====
    function init(userConfig) {
        if (userConfig) {
            Object.assign(CONFIG, userConfig);
        }

        sessionId = generateSessionId();
        createWidget();

        // Авторастягивание textarea
        var textarea = document.getElementById('rts-input');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 90) + 'px';
        });
        textarea.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        document.getElementById('rts-send').addEventListener('click', function() { sendMessage(); });
        document.getElementById('rts-chat-toggle').addEventListener('click', toggleChat);
        document.getElementById('rts-chat-close').addEventListener('click', toggleChat);
        
        var bubble = document.getElementById('rts-proactive-bubble');
        if (bubble) {
            bubble.querySelector('.rts-proactive-content').addEventListener('click', toggleChat);
            bubble.querySelector('.rts-proactive-close').addEventListener('click', function(e) {
                e.stopPropagation();
                hideProactiveBubble();
            });
        }

        // Загружаем историю и подключаемся
        loadHistory();
        connectWS();
        initVoiceInput();

        // Показ проактивного баббла JivoSite через 7 секунд
        setTimeout(showProactiveBubble, 7000);
    }

    // ===== ГОЛОСОВОЙ ВВОД (Web Speech API) =====
    function initVoiceInput() {
        var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        var micBtn = document.getElementById('rts-mic');
        if (!micBtn) return;

        if (!SpeechRec) {
            micBtn.style.display = 'none';
            return;
        }

        var recognition = new SpeechRec();
        recognition.lang = 'ru-RU';
        recognition.continuous = false;
        recognition.interimResults = true;
        var isListening = false;

        micBtn.addEventListener('click', function() {
            if (isListening) {
                recognition.stop();
            } else {
                try {
                    recognition.start();
                    isListening = true;
                    micBtn.classList.add('listening');
                } catch(e) {}
            }
        });

        recognition.onresult = function(event) {
            var transcript = '';
            for (var i = event.resultIndex; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
            }
            var input = document.getElementById('rts-input');
            if (input) {
                input.value = transcript;
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 90) + 'px';
            }
        };

        recognition.onend = function() {
            isListening = false;
            if (micBtn) micBtn.classList.remove('listening');
            var input = document.getElementById('rts-input');
            if (input && input.value.trim().length > 0) {
                sendMessage();
            }
        };

        recognition.onerror = function() {
            isListening = false;
            if (micBtn) micBtn.classList.remove('listening');
        };
    }

    // ===== ПУБЛИЧНЫЙ API =====
    window.RTSChat = { 
        init: init,
        sendQuick: function(text) {
            if (!isOpen) toggleChat();
            sendMessage(text);
        }
    };

    // Автозапуск если задан data-атрибут
    document.addEventListener('DOMContentLoaded', function() {
        var script = document.querySelector('script[data-rts-api]');
        if (script) {
            init({ apiUrl: script.getAttribute('data-rts-api') });
        }
    });

})();
