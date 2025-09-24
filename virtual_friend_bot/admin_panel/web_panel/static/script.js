// web_panel/static/script.js
document.addEventListener('DOMContentLoaded', function () {

    // --- SOCKET.IO ---
    const socket = io();

    // --- ГРАФИКИ ---
    let sentimentChart = null;
    let tagsChart = null;

    function updateCharts(sentimentData, tagsData) {
        const ctx1 = document.getElementById('sentimentChart').getContext('2d');
        if (sentimentChart) sentimentChart.destroy();
        sentimentChart = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: ['Позитивные', 'Негативные', 'Нейтральные'],
                datasets: [{
                    data: [sentimentData.positive || 0, sentimentData.negative || 0, sentimentData.neutral || 0],
                    backgroundColor: ['#4ade80', '#f87171', '#94a3b8']
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: 'Настроение сообщений'
                    }
                }
            }
        });

        const ctx2 = document.getElementById('tagsChart').getContext('2d');
        if (tagsChart) tagsChart.destroy();
        // Подготовка данных для графика тегов
        const tagLabels = Object.keys(tagsData);
        const tagCounts = Object.values(tagsData);
        tagsChart = new Chart(ctx2, {
            type: 'bar',
            data: {
                labels: tagLabels,
                datasets: [{
                    label: 'Количество упоминаний',
                    data: tagCounts,
                    backgroundColor: '#818cf8'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    title: {
                        display: true,
                        text: 'Популярные темы'
                    }
                }
            }
        });
    }

    // --- СТАТИСТИКА ---
    // Загружаем обычную статистику
    $.getJSON('/api/stats', function(data) {
        $('#total-users').text(data.users);
        $('#total-paid').text(data.paid);
        $('#total-active').text(data.active);
    });

    // Загружаем расширенную статистику и инициализируем графики
    $.getJSON('/api/advanced_stats', function(data) {
        $('#dau').text(data.dau);
        $('#mau').text(data.mau);
        $('#retention').text(data.retention_rate.toFixed(2) + '%');
        $('#ltv').text(new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2 }).format(data.ltv).replace(/\s/g, ' '));

        // Заглушка для графиков, в реальном проекте нужно получать данные из БД
        // Например, через новый API endpoint /api/analytics/sentiment_distribution
        updateCharts(
            { positive: 15, negative: 5, neutral: 25 },
            { 'love': 8, 'work': 12, 'depression': 3, 'fun': 10, 'help': 7, 'family': 5 }
        );
    });

    // Обновление статистики по событию от сервера
    socket.on('stats_update', function(data) {
        $('#total-users').text(data.users);
        $('#total-paid').text(data.paid);
        $('#total-active').text(data.active);
        // --- Обновление DAU/MAU/Retension/LTV ---
        // Сервер теперь присылает эти данные вместе с базовой статистикой
        if (data.hasOwnProperty('dau')) {
            $('#dau').text(data.dau);
        }
        if (data.hasOwnProperty('mau')) {
            $('#mau').text(data.mau);
        }
        if (data.hasOwnProperty('retention_rate')) {
            $('#retention').text(data.retention_rate.toFixed(2) + '%');
        }
        if (data.hasOwnProperty('ltv')) {
            $('#ltv').text(new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 2 }).format(data.ltv).replace(/\s/g, ' '));
        }
    });

    // --- ЧАТЫ ---
    // Просмотр чата
    $(document).on('click', '.view-chat', function() {
        const userId = $(this).data('user-id');
        const botType = $(this).data('bot-type');
        loadChat(userId, botType);
    });

    $('#refresh-chat').click(function() {
        const userId = $(this).data('current-user');
        const botType = $(this).data('current-bot');
        if (userId && botType) {
            loadChat(userId, botType);
        }
    });

    function loadChat(userId, botType) {
        $.getJSON(`/api/chat/${userId}/${botType}`, function(data) {
            let userInfo = data.user_info || {};
            let html = `
                <h5>
                    👤 ${userInfo.first_name || '—'} ${userInfo.last_name || ''}
                    | @${userInfo.username || '—'}
                    | 🌐 ${userInfo.language || 'ru'}
                    | 💬 Бесплатных: ${userInfo.free_messages || 0}
                </h5><hr>`;

            // Психологический профиль
            if (userInfo.psych_profile && Object.keys(userInfo.psych_profile).length > 0 && !userInfo.psych_profile.error) {
                const p = userInfo.psych_profile;
                html += `
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        🧠 Психологический профиль
                    </div>
                    <div class="card-body">
                        <p><strong>Темперамент:</strong> <span class="badge bg-primary">${p.temperament || '—'}</span></p>
                        <p><strong>Эмоциональный тон:</strong> <span class="badge bg-success">${p.emotional_tone || '—'}</span></p>
                        <p><strong>Стиль общения:</strong> <span class="badge bg-warning">${p.communication_style || '—'}</span></p>
                        <p><strong>Потребности:</strong> ${(p.needs || '').split(',').map(n => `<span class="badge bg-info me-1">${n.trim()}</span>`).join(' ') || '—'}</p>
                        <p><strong>Описание:</strong> ${p.summary || '—'}</p>
                    </div>
                </div><hr>`;
            } else if (userInfo.psych_profile && userInfo.psych_profile.error) {
                 html += `<div class="alert alert-warning">Психологический профиль не сгенерирован: ${userInfo.psych_profile.error}</div><hr>`;
            }

            if (data.chat && data.chat.length > 0) {
                data.chat.forEach(msg => {
                    const badgeClass = msg.role === 'user' ? 'bg-primary' : 'bg-secondary';
                    const sentimentClass = `sentiment-${msg.sentiment || 'neutral'}`;
                    const sender = msg.role === 'user' ? '👤 Пользователь' : (botType === 'evg' ? '🌸 Евгения' : '🔥 Дэймон');

                    // Теги
                    let tagsHtml = '';
                    if (msg.tags && msg.tags.length) {
                        tagsHtml = msg.tags.map(tag => `<span class="badge bg-info tag-badge">${tag}</span>`).join(' ');
                    }

                    html += `
                        <div class="mb-3">
                            <div>
                                <span class="badge ${badgeClass}">${sender}</span>
                                <small class="text-muted">${msg.timestamp}</small>
                                <span class="${sentimentClass}">${msg.sentiment === 'positive' ? '😊' : msg.sentiment === 'negative' ? '😞' : '😐'}</span>
                            </div>
                            ${tagsHtml ? `<div class="mt-1">${tagsHtml}</div>` : ''}
                            <div class="p-2 bg-light rounded mt-1">${msg.content}</div>
                        </div>
                    `;
                });
            } else {
                html += '<p class="text-muted">Сообщений пока нет.</p>';
            }

            $('#chat-container').html(html);
            $('#chat-title').text(`💬 Чат с ${userId} (${botType})`);
            $('#chat-card').show();
            $('#refresh-chat').data('current-user', userId).data('current-bot', botType);

            // Сообщаем серверу, что мы открыли этот чат, чтобы он мог присылать обновления
            socket.emit('request_new_messages', { user_id: userId, bot_type: botType });
        }).fail(function() {
            $('#chat-container').html('<div class="alert alert-danger">Ошибка загрузки чата.</div>');
            $('#chat-card').show();
        });
    }

    // Обновление чата в реальном времени
    socket.on('chat_update', function(data) {
        // Проверяем, открыт ли сейчас этот чат
        const currentUserId = $('#refresh-chat').data('current-user');
        const currentBotType = $('#refresh-chat').data('current-bot');

        if (currentUserId == data.user_id && currentBotType == data.bot_type) {
            // Если чат открыт, добавляем новое сообщение
            if (data.chat) {
                // Если пришел весь чат целиком (например, при первом запросе)
                loadChat(data.user_id, data.bot_type);
            } else if (data.message) {
                // Если пришло одно новое сообщение
                const msg = data.message;
                const badgeClass = msg.role === 'user' ? 'bg-primary' : 'bg-secondary';
                const sentimentClass = `sentiment-${msg.sentiment || 'neutral'}`;
                const sender = msg.role === 'user' ? '👤 Пользователь' : (currentBotType === 'evg' ? '🌸 Евгения' : '🔥 Дэймон');

                let tagsHtml = '';
                if (msg.tags && msg.tags.length) {
                    tagsHtml = msg.tags.map(tag => `<span class="badge bg-info tag-badge">${tag}</span>`).join(' ');
                }

                const newMessageHtml = `
                    <div class="mb-3">
                        <div>
                            <span class="badge ${badgeClass}">${sender}</span>
                            <small class="text-muted">${msg.timestamp}</small>
                            <span class="${sentimentClass}">${msg.sentiment === 'positive' ? '😊' : msg.sentiment === 'negative' ? '😞' : '😐'}</span>
                        </div>
                        ${tagsHtml ? `<div class="mt-1">${tagsHtml}</div>` : ''}
                        <div class="p-2 bg-light rounded mt-1">${msg.content}</div>
                    </div>
                `;
                $('#chat-container').append(newMessageHtml);
                // Прокручиваем вниз
                $('#chat-container').scrollTop($('#chat-container')[0].scrollHeight);
            }
        }
    });

    // --- ЭКСПОРТ ---
    $(document).on('click', '.export-chat', function() {
        const userId = $(this).data('user-id');
        const botType = $(this).data('bot-type');
        $.getJSON(`/api/export/${userId}/${botType}`, function(data) {
            if (data.download_url) {
                window.location.href = data.download_url;
            } else {
                alert('Ошибка экспорта');
            }
        }).fail(function() {
            alert('Ошибка запроса экспорта');
        });
    });

    // --- УВЕДОМЛЕНИЯ ---
    function showToast(header, body, type = 'info') {
        const toastId = 'toast-' + Date.now();
        const bgClass = type === 'danger' ? 'bg-danger' : type === 'warning' ? 'bg-warning' : 'bg-info';
        const textColorClass = type === 'warning' ? 'text-dark' : 'text-white';

        const toastHtml = `
            <div id="${toastId}" class="toast align-items-center border-0 show" role="alert" aria-live="assertive" aria-atomic="true" style="margin-bottom: 10px;">
                <div class="d-flex">
                    <div class="toast-body ${textColorClass} ${bgClass}">
                        <strong>${header}</strong><br>
                        ${body}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        const $toast = $(toastHtml);
        $('#toast-container').append($toast);

        // Удаление тоста после 10 секунд
        setTimeout(() => {
            if ($toast.length) {
                const bsToast = new bootstrap.Toast($toast[0]);
                bsToast.hide();
                // Удаляем элемент после анимации
                $toast.on('hidden.bs.toast', function () {
                    $(this).remove();
                });
            }
        }, 10000);

        // Инициализация анимации появления
        new bootstrap.Toast($toast[0]).show();

        // Дополнительно можно мигать favicon или воспроизводить звук
        // Например, с помощью Howler.js или встроенного API
        // document.title = `🔔 ${document.title}`;
        // setTimeout(() => { document.title = document.title.replace('🔔 ', ''); }, 2000);
    }

    // Умные уведомления о новых сообщениях
    socket.on('new_message_enriched', function(data) {
        let tagsHtml = '';
        if (data.tags && data.tags.length) {
            tagsHtml = data.tags.map(t => `<span class="badge bg-light text-dark">${t}</span>`).join(' ');
        }
        const body = `
            <em>(${data.bot_type})</em>: "${data.text}"<br>
            <span class="badge ${data.sentiment === 'positive' ? 'bg-success' : data.sentiment === 'negative' ? 'bg-danger' : 'bg-secondary'}">${data.sentiment}</span>
            ${tagsHtml}
        `;
        showToast(`🆕 Новое сообщение от ${data.first_name} (@${data.username})`, body, 'info');
    });

    // Экстренные уведомления
    socket.on('emergency_alert', function(data) {
        const body = `"${data.text}"`;
        showToast(`🚨 ЭКСТРЕННО! Пользователь ${data.first_name} (@${data.username}) нуждается в помощи!`, body, 'danger');

        // Дополнительно можно мигать favicon или воспроизводить звук
        // Например, с помощью Howler.js или встроенного API
        // document.title = `🚨 ${document.title}`;
        // setTimeout(() => { document.title = document.title.replace('🚨 ', ''); }, 2000);
    });

    // --- ИНИЦИАЛИЗАЦИЯ DATATABLES ---
    $(document).ready(function() {
        // Правильная инициализация DataTables с проверкой на существование
        const tableId = '#chats-table';
        // Уничтожаем предыдущую инициализацию, если она была
        if ($.fn.DataTable.isDataTable(tableId)) {
            $(tableId).DataTable().destroy();
        }
        // Инициализируем таблицу
        $(tableId).DataTable({
            "language": {
                // Используем локальный файл i18n
                "url": "/static/i18n/ru.json"
            },
            "order": [[ 0, "desc" ]] // Сортировка по умолчанию
        });
    });

    // --- РЕГИСТРАЦИЯ SERVICE WORKER ДЛЯ PWA ---
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => console.log('SW registered:', reg))
                .catch(err => console.log('SW registration failed:', err));
        });
    }

}); // Конец DOMContentLoaded
