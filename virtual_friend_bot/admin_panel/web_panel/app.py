# web_panel/app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO, emit
import sqlite3
import json
import pandas as pd
from datetime import datetime, timedelta
import threading
import time
import os
import logging
import requests # Для загрузки файла локализации DataTables

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'supersecretkeyforyouonly' # ОБЯЗАТЕЛЬНО СМЕНИТЕ В ПРОДАКШЕНЕ
# Используем eventlet для асинхронности
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Путь к БД
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.db')
# Путь к папке static для загрузки файлов
STATIC_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
I18N_FOLDER = os.path.join(STATIC_FOLDER, 'i18n')

# Настройка логгирования для этого модуля
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка и создание необходимых папок и файлов при запуске
def setup_static_files():
    os.makedirs(I18N_FOLDER, exist_ok=True)
    ru_json_path = os.path.join(I18N_FOLDER, 'ru.json')
    if not os.path.exists(ru_json_path):
        logger.info("Загрузка файла локализации DataTables (ru.json)...")
        try:
            # Исправлен URL (убран лишний пробел в конце)
            response = requests.get('https://cdn.datatables.net/plug-ins/1.13.6/i18n/ru.json')
            response.raise_for_status()
            with open(ru_json_path, 'wb') as f:
                f.write(response.content)
            logger.info("Файл ru.json успешно загружен.")
        except Exception as e:
            logger.error(f"Не удалось загрузить ru.json: {e}")
            # Создаем пустой файл, чтобы избежать 404
            with open(ru_json_path, 'w') as f:
                json.dump({}, f)

setup_static_files()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_chats():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT DISTINCT m.user_id, m.bot_type, u.first_name, u.last_name, u.username, u.relationship_mode, u.language
        FROM messages m
        JOIN users u ON m.user_id = u.user_id
        ORDER BY u.last_seen DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]

# Исправленная функция для получения сообщений чата
def get_chat_by_user(user_id, bot_type):
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT role, content, timestamp, sentiment, tags
        FROM messages
        WHERE user_id = ? AND bot_type = ?
        ORDER BY timestamp ASC
    """, (user_id, bot_type)).fetchall()
    conn.close()
    chat_messages = []
    for row in rows:
        try:
            tags_list = json.loads(row['tags']) if row['tags'] else []
        except (json.JSONDecodeError, TypeError):
            tags_list = []
        chat_messages.append({
            'role': row['role'],
            'content': row['content'],
            'timestamp': row['timestamp'],
            'sentiment': row['sentiment'],
            'tags': tags_list
        })
    return chat_messages

def get_user_info(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT first_name, last_name, username, email, subscribed_until,
                   free_messages_left, psych_profile, language
            FROM users WHERE user_id = ?
        """, (user_id,)).fetchone()
        if row:
            try:
                psych_profile = json.loads(row[6]) if row[6] and row[6] != '{}' else {}
            except (json.JSONDecodeError, TypeError):
                psych_profile = {}
            return {
                'first_name': row[0],
                'last_name': row[1],
                'username': row[2],
                'email': row[3],
                'subscribed': row[4] and datetime.fromisoformat(row[4]) > datetime.now(),
                'free_messages': row[5],
                'psych_profile': psych_profile,
                'language': row[7]
            }
        return None

def get_stats():
    conn = get_db_connection()
    users = conn.execute("SELECT COUNT(*) as total FROM users").fetchone()['total']
    paid = conn.execute("SELECT COUNT(*) as total FROM payments").fetchone()['total']
    active = conn.execute("SELECT COUNT(*) as total FROM users WHERE subscribed_until > datetime('now')").fetchone()['total']
    conn.close()
    return {"users": users, "paid": paid, "active": active}

# Исправленная и дополненная функция для расширенной статистики
def get_advanced_stats():
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    # DAU / MAU
    dau = conn.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE DATE(timestamp) = ?", (today,)).fetchone()[0]
    mau = conn.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE DATE(timestamp) >= ?", (month_ago,)).fetchone()[0]

    # Retention (пользователи, которые были и 7 дней назад, и за последние 7 дней)
    retention_sql = """
        SELECT COUNT(DISTINCT m1.user_id)
        FROM (
            SELECT DISTINCT user_id FROM messages WHERE DATE(timestamp) BETWEEN ? AND ?
        ) m1
        INNER JOIN (
            SELECT DISTINCT user_id FROM messages WHERE DATE(timestamp) BETWEEN ? AND ?
        ) m2 ON m1.user_id = m2.user_id
    """
    # Пользователи 14-7 дней назад
    users_two_weeks_ago = conn.execute("SELECT COUNT(DISTINCT user_id) FROM messages WHERE DATE(timestamp) BETWEEN ? AND ?", (week_ago, today)).fetchone()[0] or 1
    # Пользователи, которые были и 14-7 и 7-0 дней назад (возвращенные)
    retained_users = conn.execute(retention_sql, (week_ago, today, month_ago, week_ago)).fetchone()[0]
    retention_rate = round((retained_users / users_two_weeks_ago) * 100, 2) if users_two_weeks_ago > 0 else 0

    # LTV (средний доход с пользователя)
    total_revenue = conn.execute("SELECT SUM(amount) FROM payments").fetchone()[0] or 0
    total_users_who_paid = conn.execute("SELECT COUNT(DISTINCT user_id) FROM payments").fetchone()[0] or 1
    # LTV считаем как доход на платящего пользователя, это более точный показатель для подписок
    ltv = round(total_revenue / total_users_who_paid, 2) if total_users_who_paid > 0 else 0

    conn.close()
    # Возвращаем словарь, который можно объединить с базовой статистикой
    return {
        'dau': dau,
        'mau': mau,
        'retention_rate': retention_rate,
        'ltv': ltv
    }

# Функция для получения данных для графиков (заглушки, можно расширить)
def get_analytics_data():
    """Получает данные для графиков на дашборде."""
    # В реальном проекте здесь будет запрос к БД
    # Например, распределение настроений за последнюю неделю
    sentiment_distribution = {
        'positive': 15,
        'negative': 5,
        'neutral': 25
    }
    # Популярные теги за последнюю неделю
    popular_tags = {
        'love': 8,
        'work': 12,
        'depression': 3,
        'fun': 10,
        'help': 7,
        'family': 5
    }
    return {
        'sentiment_distribution': sentiment_distribution,
        'popular_tags': popular_tags
    }


def export_chat_to_excel(user_id, bot_type):
    chat = get_chat_by_user(user_id, bot_type)
    if not chat:
        return None
    df = pd.DataFrame(chat)
    filename = f"chat_{user_id}_{bot_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(STATIC_FOLDER, 'downloads', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_excel(filepath, index=False)
    return filename

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # В реальном проекте используйте хеширование паролей!
        if username == "admin" and password == "password123": # ОБЯЗАТЕЛЬНО СМЕНИТЕ
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Неверный логин или пароль")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    chats = get_all_chats()
    stats = get_stats()
    return render_template('index.html', chats=chats, stats=stats)

@app.route('/api/chat/<int:user_id>/<bot_type>')
def api_chat(user_id, bot_type):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    chat = get_chat_by_user(user_id, bot_type)
    user_info = get_user_info(user_id)
    return jsonify({
        "chat": chat,
        "user_info": user_info,
        "user_id": user_id,
        "bot_type": bot_type
    })

@app.route('/api/export/<int:user_id>/<bot_type>')
def export_chat(user_id, bot_type):
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    filename = export_chat_to_excel(user_id, bot_type)
    if filename:
        return jsonify({"download_url": f"/static/downloads/{filename}"})
    else:
        return jsonify({"error": "No data"}), 404

@app.route('/api/stats')
def api_stats():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_stats())

@app.route('/api/advanced_stats')
def api_advanced_stats():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_advanced_stats())

@app.route('/api/analytics')
def api_analytics():
    """API endpoint для данных графиков."""
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(get_analytics_data())

# --- SOCKET.IO HANDLERS ---
@socketio.on('connect')
def handle_connect():
    logger.info('Клиент подключился к админке')
    emit('server_response', {'data': 'Connected to admin panel'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Клиент отключился от админки')

# Обработчик для запроса обновления статистики (по таймеру на фронтенде)
@socketio.on('request_stats_update')
def handle_stats_update():
    stats = get_stats()
    # Получаем и добавляем расширенную статистику
    advanced_stats = get_advanced_stats()
    combined_stats = {**stats, **advanced_stats}
    emit('stats_update', combined_stats)

# Обработчик для запроса обновления конкретного чата
@socketio.on('request_new_messages')
def handle_new_messages(data):
    user_id = data.get('user_id')
    bot_type = data.get('bot_type')
    if user_id and bot_type:
        chat = get_chat_by_user(user_id, bot_type)
        emit('chat_update', {
            'user_id': user_id,
            'bot_type': bot_type,
            'chat': chat
        })

# Фоновая задача для периодического обновления статистики на всех клиентах
def background_thread():
    while True:
        socketio.sleep(30) # Обновляем каждые 30 секунд
        try:
            stats = get_stats()
            # Получаем и добавляем расширенную статистику
            advanced_stats = get_advanced_stats()
            # Объединяем словари
            combined_stats = {**stats, **advanced_stats}
            # Отправляем обновление ВСЕМ подключенным клиентам
            # Исправлено: broadcast=True -> to='/'
            socketio.emit('stats_update', combined_stats, to='/')
            logger.info("Фоновое обновление статистики отправлено")
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче: {e}")

# Запуск фоновой задачи
@socketio.on('start_background_thread')
def start_background():
    thread = threading.Thread(target=background_thread)
    thread.daemon = True
    thread.start()
    logger.info("Фоновая задача запущена")

if __name__ == '__main__':
    # Этот файл не должен запускаться напрямую, только через main.py
    pass
