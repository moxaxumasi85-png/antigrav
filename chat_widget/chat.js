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
        try {
            var urlParams = new URLSearchParams(window.location.search);
            var urlSession = urlParams.get('session_id');
            if (urlSession) {
                localStorage.setItem('rts_chat_session', urlSession);
                return urlSession;
            }
        } catch(e) {}
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
        
        // Parse markdown links: [text](url)
        escaped = escaped.replace(/\[([^\]]+)\]\((https?:\/\/[^\s<>"]+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
        
        // Parse bold: **text**
        escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Parse plain links not already caught (exclude trailing parenthesis)
        escaped = escaped.replace(/(^|[^"'])(https?:\/\/[^\s<>"]*[^\s<>".;,!?()])/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
        
        // Parse newlines
        escaped = escaped.replace(/\n/g, '<br>');
        
        return escaped;
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
            '    <div class="rts-header-actions" style="display:flex; align-items:center; gap:6px;">',
            '      <button class="rts-btn-header-reset" onclick="RTSChat.startNewSession()" title="Начать новый диалог с заново" style="background:rgba(255,255,255,0.2); color:#fff; border:none; border-radius:12px; padding:4px 8px; font-size:11px; font-weight:600; cursor:pointer;">✨ Новый диалог</button>',
            '      <button class="rts-close-btn" id="rts-chat-close" aria-label="Закрыть чат">',
            '        <svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>',
            '      </button>',
            '    </div>',
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
            '    <input type="file" id="rts-file-input" accept="image/*,.pdf,.doc,.docx" style="display:none">',
            '    <button class="rts-attach-btn" id="rts-attach" aria-label="Прикрепить файл" title="Прикрепить файл/чек (JPG, PDF)">',
            '      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5a2.5 2.5 0 0 1 5 0v10.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5V6H9v9.5a3.5 3.5 0 0 0 7 0V5c0-2.76-2.24-5-5-5s-5 2.24-5 5v12.5c0 3.59 2.91 6.5 6.5 6.5s6.5-2.91 6.5-6.5V6h-2.5z"/></svg>',
            '    </button>',
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
        if (path === '/chat') {
            return CONFIG.apiUrl + '/api/chat';
        }
        return CONFIG.apiUrl + path;
    }

    var pendingHistoryMessages = null;

    function openChatWindow() {
        isOpen = true;
        var win = document.getElementById('rts-chat-window');
        if (win) win.classList.add('open');
        hideProactiveBubble();
        unreadCount = 0;
        updateBadge();
        var input = document.getElementById('rts-input');
        if (input) input.focus();
        var msgs = document.getElementById('rts-messages');
        if (msgs) msgs.scrollTop = msgs.scrollHeight;
    }

    function loadHistory() {
        var url = getApiEndpoint('/api/chat/' + sessionId + '/messages', 'history&session_id=' + sessionId);

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var messagesEl = document.getElementById('rts-messages');
                if (data && data.messages && data.messages.length > 0) {
                    pendingHistoryMessages = data.messages;
                    resumeSession();
                    showSessionPrompt(data.messages);

                    // Автоматически открываем окно чата при наличии истории или session_id в URL
                    var urlParams = new URLSearchParams(window.location.search);
                    if (urlParams.has('session_id') || !isOpen) {
                        openChatWindow();
                    }
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

    function showSessionPrompt(messages) {
        var messagesEl = document.getElementById('rts-messages');
        if (!messagesEl) return;
        var existing = document.getElementById('rts-session-prompt');
        if (existing) existing.parentNode.removeChild(existing);

        var promptDiv = document.createElement('div');
        promptDiv.id = 'rts-session-prompt';
        promptDiv.className = 'rts-session-prompt';
        promptDiv.innerHTML = [
            '<div class="rts-prompt-title">💬 Ваша история общения восстановлена</div>',
            '<div class="rts-prompt-text">Вы продолжаете диалог с Анной. Хотите очистить экран и начать заново?</div>',
            '<div class="rts-prompt-buttons">',
            '  <button class="rts-btn-reset" onclick="RTSChat.startNewSession()">✨ Начать новый диалог</button>',
            '</div>'
        ].join('\n');

        if (messagesEl.children.length > 1) {
            messagesEl.insertBefore(promptDiv, messagesEl.children[1]);
        } else {
            messagesEl.appendChild(promptDiv);
        }
    }

    function resumeSession() {
        var prompt = document.getElementById('rts-session-prompt');
        if (prompt) prompt.parentNode.removeChild(prompt);

        if (pendingHistoryMessages && pendingHistoryMessages.length > 0) {
            var messagesEl = document.getElementById('rts-messages');
            messagesEl.innerHTML = '<div class="rts-welcome">🔒 Защищенное соединение · RegionTehsnab</div>';
            renderedCount = 0;
            pendingHistoryMessages.forEach(function(msg) {
                appendMessage(msg.sender, msg.content, msg.timestamp, true);
            });
            renderedCount = pendingHistoryMessages.length;
            pendingHistoryMessages = null;
        }
    }

    function startNewSession() {
        var prompt = document.getElementById('rts-session-prompt');
        if (prompt) prompt.parentNode.removeChild(prompt);

        localStorage.removeItem('rts_chat_session');
        sessionId = 'web_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
        localStorage.setItem('rts_chat_session', sessionId);
        pendingHistoryMessages = null;

        var messagesEl = document.getElementById('rts-messages');
        messagesEl.innerHTML = '<div class="rts-welcome">🔒 Защищенное соединение · RegionTehsnab</div>';
        renderedCount = 0;
        appendMessage('bot', CONFIG.welcomeMsg, null, true);
        renderedCount = 1;
    }

    function pollMessages() {
        if (!sessionId) return;
        var url = getApiEndpoint('/api/chat/' + sessionId + '/messages', 'history&session_id=' + sessionId);

        fetch(url)
            .then(function(r) { return r.json(); })
            .then(function(data) {
                if (data && data.messages && data.messages.length > 0) {
                    var messagesEl = document.getElementById('rts-messages');
                    var domMsgsCount = messagesEl.getElementsByClassName('rts-msg').length;
                    
                    if (data.messages.length > domMsgsCount) {
                        var newMsgs = data.messages.slice(domMsgsCount);
                        newMsgs.forEach(function(msg) {
                            appendMessage(msg.sender, msg.content, msg.timestamp, false);
                        });
                        renderedCount = data.messages.length;
                    }
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

        if (pendingHistoryMessages && pendingHistoryMessages.length > 0) {
            resumeSession();
        }

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
            if (data && data.reply) {
                appendMessage('bot', data.reply, null, false);
                renderedCount++;
            }
            pollMessages();
        })
        .catch(function(err) {
            showTyping(false);
            console.error('[RTSChat] HTTP Error:', err);
            appendMessage('bot', 'Здравствуйте! Чем могу помочь по подбору двигателя или КПП?', null, false);
            renderedCount++;
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
        initFileInput();

        // Показ проактивного баббла JivoSite через 7 секунд
        setTimeout(showProactiveBubble, 7000);
    }

    // ===== ЗАГРУЗКА ФАЙЛОВ / ЧЕКОВ (JPG, PNG, PDF) =====
    function initFileInput() {
        var attachBtn = document.getElementById('rts-attach');
        var fileInput = document.getElementById('rts-file-input');
        if (!attachBtn || !fileInput) return;

        attachBtn.addEventListener('click', function() {
            fileInput.click();
        });

        fileInput.addEventListener('change', function(e) {
            var files = e.target.files;
            if (!files || files.length === 0) return;

            var file = files[0];
            var reader = new FileReader();

            showTyping(true);
            hideProactiveBubble();

            reader.onload = function(evt) {
                var base64Data = evt.target.result;
                var uploadUrl = getApiEndpoint('/api/upload', 'upload');

                fetch(uploadUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        file_name: file.name,
                        file_base64: base64Data
                    })
                })
                .then(function(r) { return r.json(); })
                .then(function(res) {
                    showTyping(false);
                    if (res && res.user_msg) {
                        appendMessage('client', res.user_msg, null, false);
                        renderedCount++;
                    }
                    if (res && res.bot_reply) {
                        setTimeout(function() {
                            appendMessage('bot', res.bot_reply, null, false);
                            renderedCount++;
                        }, 500);
                    }
                    fileInput.value = '';
                })
                .catch(function(err) {
                    showTyping(false);
                    appendMessage('bot', 'Ошибка при передаче файла. Пожалуйста, попробуйте еще раз или отправьте файл на e-mail: manager@regiontehsnab.ru', null, false);
                    fileInput.value = '';
                });
            };

            reader.readAsDataURL(file);
        });
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
            openChatWindow();
            sendMessage(text);
        },
        resumeSession: resumeSession,
        startNewSession: startNewSession,
        openWindow: openChatWindow,
        openSession: function(targetSessionId) {
            if (!targetSessionId) return;
            try {
                var newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname + '?session_id=' + encodeURIComponent(targetSessionId);
                window.history.pushState({path: newUrl}, '', newUrl);
            } catch(e) {}
            localStorage.setItem('rts_chat_session', targetSessionId);
            sessionId = targetSessionId;
            loadHistory();
            openChatWindow();
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
