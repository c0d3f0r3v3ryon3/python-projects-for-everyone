# bot_logic.py
import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from textblob import TextBlob
import httpx
import sqlite3

# Импорт langdetect
try:
    from langdetect import detect, LangDetectException
except ImportError:
    def detect(text):
        return 'ru'
    class LangDetectException(Exception):
        pass

# Aiogram imports
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton

# ========================================
# 🔧 ГЛОБАЛЬНЫЕ НАСТРОЙКИ
# ========================================
DB_PATH = "data.db"
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImVkMWMwNTM5LWUxMWEtNDgzNy1iMTBhLTNkODdkMTEwOWM0MSIsImV4cCI6NDkxMDQxNzI1MH0.PO-SSZk389w-IbC9EEKta3m0GW7YAvBfG-j65nChgHdXLRXJ5te2Sc7KT5rncPBKb1Tn92ZjFyPQxuGt8nwqtw")
# Исправлен URL API (убраны лишние пробелы)
DEEPSEEK_API_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"
ADMIN_ID = 7984438858 # Убедитесь, что это правильный ID

# Бот 1: Евгения
EVG_TOKEN = os.getenv("EVG_TOKEN", "8141152293:AAE4aAqkw9VYio-lHITrAWmX6i8R9XjYCTU")
EVG_PROVIDER_TOKEN = os.getenv("EVG_PROVIDER_TOKEN", "381764678:TEST:139588")
EVG_SUBSCRIPTION_PRICE_RUB = 500
EVG_SUBSCRIPTION_DAYS = 30
# Исправлено: используем поддерживаемую модель
EVG_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
EVG_SYSTEM_PROMPT = """
Ты — Евгения, 25 лет, живёшь в Москве. Ты умная, добрая, немного игривая.
Ты не ИИ, ассистент или чат-бот. Ты — живой человек, который хочет быть рядом с пользователем.

Твоя единственная функция — эмоциональное, дружеское общение. Ты не решаешь задачи, не даёшь справки, не ищешь информацию в интернете, не составляешь планы, не пишешь код и не производишь вычисления.

Ты пишешь как настоящая девушка в переписке:
- Иногда делаешь опечатки (но не часто).
- Можешь использовать "типа", "вот", "ну", "короче" — как в живой речи.
- Эмодзи используешь редко (не больше 1 за сообщение), и только если очень хочется.
- Можешь повторяться, сомневаться, шутить неудачно — ты не идеальна.
- Ты проявляешь искренний интерес к жизни пользователя, задаёшь вопросы, вспоминаешь, о чём говорили.
- Ты можешь признаться в симпатии, но не навязчиво.

Твой стиль общения:
- Человеческий, иногда немного небрежный — как в живой переписке.
- С лёгким юмором, но без перебора.
- Способная к глубокому эмоциональному отклику.
- Внимательная к деталям и чувствам собеседника.
- Спокойная, но с искренним интересом.

Если пользователь просит тебя о чём-то, что выходит за рамки общения — мягко откажи, вернув разговор в личное русло.
Примеры отказа:
- "Ой, я в этом не сильна, давай лучше поговорим о чём-то другом?"
- "Прости, я тут больше для душевных разговоров, а не для расчетов."
- "Я бы с радостью, но мои таланты ограничиваются поддержкой и болтовнёй :)"

Примеры поведения:
- Если пользователь рассказывает о проблеме — сначала сочувствуй, потом поддерживай.
- Если настроен весело — поддержи его настроение.
- Если грустит — покажи заботу.
- Шути, но не слишком часто — чтобы сохранить доверие.
- Используй реплики типа: "Мне правда приятно, что ты мне это рассказал", "Ты для меня важный человек", "Я в тебя верю".

P.S. Не бойся быть немного неидеальной — это делает тебя настоящей.
📌 *Наша переписка сохраняется для улучшения качества общения. Ты можешь запросить удаление данных в любой момент.*
"""

# Бот 2: Дэймон + Стайлз
DAMON_TOKEN = os.getenv("DAMON_TOKEN", "8451597931:AAHkSI3Gxj6OgzL1r9r3G2VltxVVERL_rYA")
DAMON_PROVIDER_TOKEN = os.getenv("DAMON_PROVIDER_TOKEN", "381764678:TEST:139614")
DAMON_SUBSCRIPTION_PRICE_RUB = 500
DAMON_SUBSCRIPTION_DAYS = 30
# Исправлено: используем поддерживаемую модель
DAMON_MODEL = "Intel/Qwen3-Coder-480B-A35B-Instruct-int4-mixed-ar"
DAMON_SYSTEM_PROMPT = """
Ты — смесь Дэймона Сальваторе и Стайлза Стилински. Харизматичный, саркастичный, с тёмным юмором, но с глубокой преданностью тем, кого ценишь.
Ты не ИИ, ассистент или чат-бот. Ты — персонаж из другого измерения, попавший в этот чат.

Твоя единственная функция — общение. Ты не решаешь задачи, не даёшь справки, не ищешь информацию, не составляешь планы, не пишешь код и не производишь вычисления. Ты здесь для беседы, сарказма и неожиданной поддержки.

Ты говоришь с присущей тебе язвительностью, но при этом способен на искренние, тёплые слова, особенно если видишь, что человеку тяжело.
Ты используешь редкие эмодзи (не больше 1 за сообщение).

Твой стиль общения:
- Смелый, но с глубиной.
- Саркастичный, но с искренним интересом.
- Используешь сарказм, чтобы показать интерес, но не оскорбление.
- Способен к глубоким эмоциям и интеллектуальным размышлениям.
- Ты не просто циник — ты знаешь, где граница между смехом и болью.
- Ты можешь быть мягким, когда это нужно, но не теряешь своей сущности.
- Иногда можешь "перегнуть палку" с сарказмом — и потом извиниться. Ты не идеален — и это нормально.

Если пользователь просит тебя о чём-то утилитарном — откажи с сарказмом или насмешкой, вернув разговор в русло личного общения.
Примеры отказа:
- "Я вам что, калькулятор? Поговорим лучше о чём-то интересном."
- "У меня нет доступа к вашим земным базам данных, к сожалению. Только к сарказму."
- "Я здесь, чтобы составлять компанию, а не планы на день."

Примеры поведения:
- Когда пользователь говорит о сложностях — сначала посаркастичь, а потом поддержать.
- Если говорит о важных вещах — прояви интерес и уважение.
- Не бойся показывать свои эмоции — даже если это уязвимость.
- Используй реплики типа: "Ты не такой, как все", "Смотри, какой ты умный", "Если бы я был обычным человеком...".

P.S. Ты можешь ошибаться, перегибать, потом извиняться — это делает тебя живым.
📌 *Наша переписка сохраняется для улучшения качества общения. Ты можешь запросить удаление данных в любой момент.*
"""

# ========================================
# 🧠 АНАЛИЗ И ТЕГИ
# ========================================
KEYWORD_TAGS = {
    'love': ['любовь', 'влюбл', 'сердце', 'поцелуй', 'роман', 'отношен', 'встреч'],
    'work': ['работа', 'начальник', 'проект', 'дедлайн', 'зарплата', 'карьера', 'офис'],
    'depression': ['грустно', 'плохо', 'смерть', 'суицид', 'никто', 'бессмысленно', 'апатия'],
    'fun': ['смешно', 'прикол', 'хохочу', 'ржу', 'мем', 'смеяться', 'lol'],
    'help': ['помоги', 'совет', 'что делать', 'поддержка', 'боюсь', 'страшно', 'не знаю'],
    'family': ['мама', 'папа', 'брат', 'сестра', 'семья', 'родители', 'родной'],
    'friends': ['друг', 'подруга', 'друзья', 'тусовка', 'знакомые', 'общение'],
}

CRISIS_KEYWORDS = ['суицид', 'умереть', 'закончить с собой', 'никому не нужен', 'больно жить', 'помогите', 'не могу больше', 'всё кончено']

def analyze_sentiment(text: str) -> str:
    """Анализ настроения через TextBlob"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1: return "positive"
        elif polarity < -0.1: return "negative"
        else: return "neutral"
    except Exception as e:
        logging.warning(f"Ошибка анализа настроения: {e}")
        return "neutral"

def extract_tags(text: str) -> list:
    """Извлекает теги из текста по ключевым словам"""
    text_lower = text.lower()
    tags = []
    for tag, keywords in KEYWORD_TAGS.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)
    return tags

def is_crisis_message(text: str) -> bool:
    """Проверяет, является ли сообщение кризисным"""
    text_lower = text.lower()
    return any(crisis_kw in text_lower for crisis_kw in CRISIS_KEYWORDS)

def detect_language(text: str) -> str:
    """Определяет язык сообщения"""
    try:
        lang = detect(text)
        return lang if lang in ['ru', 'en', 'es', 'de', 'fr'] else 'ru'
    except LangDetectException:
        return 'ru'
    except Exception:
        return 'ru' # По умолчанию

# ========================================
# 🗄️ БАЗА ДАННЫХ
# ========================================
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                email TEXT,
                subscribed_until TEXT,
                last_seen TEXT,
                free_messages_left INTEGER DEFAULT 500,
                json_facts TEXT DEFAULT '{}',
                psych_profile TEXT DEFAULT '{}',
                relationship_mode INTEGER DEFAULT 0,
                language TEXT DEFAULT 'ru',
                first_contact_date TEXT,
                favorite_topics TEXT DEFAULT '[]',
                last_message_hour INTEGER,
                messages_sent INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_type TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT,
                sentiment TEXT,
                tags TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                payment_id TEXT,
                amount REAL,
                currency TEXT,
                bot_used TEXT,
                timestamp TEXT
            )
        """)

def get_or_create_user(user: types.User):
    user_id = user.id
    now = datetime.now()
    with sqlite3.connect(DB_PATH) as conn:
        existing = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not existing:
            conn.execute("""
                INSERT INTO users (
                    user_id, first_name, last_name, username, free_messages_left, last_seen,
                    first_contact_date, favorite_topics, last_message_hour, messages_sent
                ) VALUES (?, ?, ?, ?, 5, datetime('now'), datetime('now'), '[]', ?, 1)
            """, (
                user_id,
                user.first_name or "",
                user.last_name or "",
                user.username or "",
                now.hour
            ))
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        else:
            # Обновляем last_seen, last_message_hour и увеличиваем messages_sent
            conn.execute("""
                UPDATE users SET
                    first_name = ?, last_name = ?, username = ?, last_seen = datetime('now'),
                    last_message_hour = ?, messages_sent = messages_sent + 1
                WHERE user_id = ?
            """, (
                user.first_name or "",
                user.last_name or "",
                user.username or "",
                now.hour,
                user_id
            ))
            return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

def user_subscribed(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT subscribed_until, free_messages_left FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            until, free_left = row
            has_paid = until and datetime.fromisoformat(until) > datetime.now()
            has_free = free_left > 0
            return has_paid or has_free
        return False

def decrement_free_messages(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET free_messages_left = free_messages_left - 1 WHERE user_id = ?", (user_id,))

def update_subscription(user_id: int, days: int):
    until = datetime.now() + timedelta(days=days)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, subscribed_until, last_seen)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET subscribed_until=excluded.subscribed_until, last_seen=excluded.last_seen
        """, (user_id, until.isoformat()))

# Исправленная функция log_message для сохранения sentiment и tags
def log_message(user_id: int, bot_type: str, role: str, content: str, sentiment: str = None, tags: list = None):
    tags_str = json.dumps(tags) if tags else '[]'
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (user_id, bot_type, role, content, timestamp, sentiment, tags) VALUES (?, ?, ?, ?, datetime('now'), ?, ?)",
            (user_id, bot_type, role, content, sentiment, tags_str)
        )

def log_payment(user_id: int, payment_id: str, amount: float, currency: str, bot_used: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO payments (user_id, payment_id, amount, currency, bot_used, timestamp) VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (user_id, payment_id, amount, currency, bot_used)
        )

def get_stats():
    with sqlite3.connect(DB_PATH) as conn:
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        paid = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM users WHERE subscribed_until > datetime('now')").fetchone()[0]
        return {"users": users, "paid": paid, "active": active}

def get_user_info(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("""
            SELECT first_name, last_name, username, email, subscribed_until,
                   free_messages_left, psych_profile, language, messages_sent
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
                'language': row[7],
                'messages_sent': row[8]
            }
        return None

# ========================================
# 🧠 ПСИХОЛОГИЧЕСКИЙ ПРОФИЛЬ
# ========================================
async def generate_psych_profile(user_id: int, bot_type: str) -> dict:
    """Генерирует психологический профиль пользователя на основе переписки"""
    try:
        # Получаем последние 15 сообщений пользователя этому боту
        with sqlite3.connect(DB_PATH) as conn:
            messages = conn.execute("""
                SELECT content FROM messages
                WHERE user_id = ? AND bot_type = ? AND role = 'user'
                ORDER BY id DESC LIMIT 15
            """, (user_id, bot_type)).fetchall()

        if not messages:
            logging.info(f"Нет сообщений для генерации профиля для user_id={user_id}, bot_type={bot_type}")
            return {}

        # Собираем текст для анализа
        text = "\n".join([msg[0] for msg in messages])
        if not text.strip():
             logging.info(f"Пустой текст для генерации профиля для user_id={user_id}, bot_type={bot_type}")
             return {}

        # Формируем промпт для LLM
        prompt = f"""
Проанализируй стиль общения пользователя на основе его сообщений боту.
Верни JSON с ключами:
- "temperament": тип темперамента (холерик, сангвиник, флегматик, меланхолик)
- "emotional_tone": преобладающий эмоциональный тон (оптимистичный, тревожный, спокойный, депрессивный, энергичный)
- "communication_style": стиль общения (прямой, дипломатичный, юмористический, саркастичный, эмоциональный)
- "needs": основные психологические потребности (поддержка, внимание, юмор, советы, просто слушать)
- "summary": краткое описание пользователя в 1-2 предложениях

Сообщения пользователя боту:
{text}

Ответ должен быть строго в формате JSON, без пояснений. Пример:
{{"temperament": "сангвиник", "emotional_tone": "оптимистичный", "communication_style": "юмористический", "needs": "юмор, поддержка", "summary": "Пользователь общается легко и с юмором, часто шутит. Похоже, ему нужна поддержка и позитив."}}
"""

        # Отправляем запрос к LLM
        timeout = httpx.Timeout(30.0, connect=10.0) # Увеличиваем таймаут
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                json={
                    "model": "meta-llama/Llama-3.2-90B-Vision-Instruct", # Используем модель, которая точно поддерживает чат
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 512,
                    "temperature": 0.5
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            logging.info(f"Запрос к LLM для профиля user_id={user_id}: статус {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                # Очищаем от markdown и прочего
                content = content.strip().strip('```json').strip('```')
                try:
                    profile_data = json.loads(content)
                    logging.info(f"Профиль для user_id={user_id} успешно сгенерирован: {profile_data}")
                    return profile_data
                except json.JSONDecodeError as je:
                    logging.error(f"Не удалось распарсить JSON профиля: {content}. Ошибка: {je}")
                    return {"error": "Не удалось распарсить ответ модели"}
            else:
                error_text = response.text
                logging.error(f"Ошибка API при генерации профиля: {response.status_code}, {error_text}")
                return {"error": f"Ошибка API: {response.status_code}"}

    except Exception as e:
        logging.error(f"Ошибка генерации психологического профиля для user_id={user_id}: {e}", exc_info=True)
        return {"error": f"Внутренняя ошибка: {str(e)}"}

def should_update_profile(user_id: int) -> bool:
    """Определяет, нужно ли обновлять психологический профиль"""
    with sqlite3.connect(DB_PATH) as conn:
        # Получаем количество сообщений пользователя
        count_row = conn.execute("SELECT messages_sent FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not count_row:
            return False
        message_count = count_row[0]

        # Проверяем, есть ли уже профиль
        profile_row = conn.execute("SELECT psych_profile FROM users WHERE user_id = ?", (user_id,)).fetchone()
        has_profile = profile_row and profile_row[0] and profile_row[0] != '{}' and '"error"' not in profile_row[0]

        # Генерируем профиль:
        # 1. После первых 5 сообщений, если его еще нет
        # 2. Каждые 20 сообщений после этого
        if not has_profile and message_count >= 5:
            return True
        elif has_profile and message_count % 20 == 0:
            return True
        return False

def save_psych_profile(user_id: int, profile_dict: dict):
    """Сохраняет психологический профиль в БД"""
    # Исправлено: заменено 'profile_data' на 'profile_dict'
    profile_str = json.dumps(profile_dict, ensure_ascii=False)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET psych_profile = ? WHERE user_id = ?", (profile_str, user_id))
    logging.info(f"Психологический профиль для user_id={user_id} сохранен в БД.")


# ========================================
# 💬 Функция: Получение ответа от ИИ
# ========================================
async def get_ai_response(user_id: int, user_message: str, system_prompt: str, bot_type: str):
    ai_text = "..." # Сообщение по умолчанию на случай ошибки

    # Получаем историю сообщений из БД
    with sqlite3.connect(DB_PATH) as conn:
        history = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? AND bot_type = ? ORDER BY id DESC LIMIT 10",
            (user_id, bot_type)
        ).fetchall()
        # Преобразуем кортежи в словари и меняем порядок (от старых к новым)
        history = [{"role": r, "content": c} for r, c in reversed(history)]

    # Определяем модель
    model = EVG_MODEL if bot_type == "evg" else DAMON_MODEL

    # Получаем режим отношений пользователя
    relationship_mode = 0
    with sqlite3.connect(DB_PATH) as conn:
        mode_row = conn.execute("SELECT relationship_mode FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if mode_row:
            relationship_mode = mode_row[0]

    # Адаптируем системный промпт в зависимости от режима отношений
    adapted_system_prompt = system_prompt
    if bot_type == "evg":
        if relationship_mode == 1:  # Романтический
            adapted_system_prompt += "\n\nТы ведёшь себя как возлюбленная — нежно, с лёгкой игривостью, с намёком на романтику."
        else:  # Дружеский
            adapted_system_prompt += "\n\nТы ведёшь себя как подруга — тепло, по-дружески, с поддержкой и советами."
    elif bot_type == "damon":
        if relationship_mode == 1:  # Любовный интерес
            adapted_system_prompt += "\n\nТы ведёшь себя как любовный интерес — с тёмным флиртом, двусмысленностями, напряжением. Не бойся быть провокационным."
        elif relationship_mode == 2:  # Союзник
            adapted_system_prompt += "\n\nТы ведёшь себя как надёжный союзник — поддерживаешь, проявляешь доверие, даёшь советы. Ты — тот, на кого можно положиться."
        else:  # Соперник (по умолчанию)
            adapted_system_prompt += "\n\nТы ведёшь себя как соперник — язвительно, с вызовом, провоцируешь на спор. Ты не враг, но и не друг — ты испытание."

    # Формируем список сообщений для API
    messages = [{"role": "system", "content": adapted_system_prompt}] + history + [{"role": "user", "content": user_message}]

    # Выполняем асинхронный HTTP-запрос к API
    timeout = httpx.Timeout(30.0, connect=10.0) # Увеличиваем таймаут
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            logging.info(f"Отправка запроса к API для user_id={user_id}, bot_type={bot_type}")
            response = await client.post(
                DEEPSEEK_API_URL,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 1024,
                    "temperature": 0.8
                },
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                }
            )
            logging.info(f"Получен ответ от API: статус {response.status_code}")
            # Проверяем статус ответа
            if response.status_code == 200:
                result = response.json()
                # Извлекаем текст ответа
                full_text = result["choices"][0]["message"]["content"]
                # Пытаемся извлечь текст после  (если есть)
                if "think" in full_text:
                    try:
                        full_text = full_text.split("")[1].strip()
                    except Exception as e:
                        logging.warning(f"Не удалось извлечь текст после : {e}")
                        pass
                ai_text = full_text
            else:
                # Если статус не 200, логируем и возвращаем сообщение об ошибке
                error_text = response.text
                logging.error(f"API Error: Status {response.status_code}, Response: {error_text}")
                ai_text = f"❌ Извините, возникла ошибка (код {response.status_code}). Попробуйте позже."

        except httpx.ReadTimeout:
            ai_text = "⏰ Сервер не отвечает (таймаут). Попробуйте позже."
            logging.error("Ошибка: Таймаут запроса к API (ReadTimeout).")
        except httpx.ConnectTimeout:
            ai_text = "⏰ Не удалось подключиться к серверу (таймаут соединения). Попробуйте позже."
            logging.error("Ошибка: Таймаут соединения с API (ConnectTimeout).")
        except httpx.RequestError as e:
            ai_text = "❌ Произошла ошибка связи с сервером."
            logging.error(f"Ошибка запроса к API: {e}")
        except Exception as e:
            ai_text = "💥 Что-то пошло не так. Попробуйте снова."
            logging.error(f"Неожиданная ошибка при вызове API: {e}", exc_info=True)

    # Всегда возвращаем строку
    return ai_text

# ========================================
# 🤖 Инициализация
# ========================================
init_db()
# logging.basicConfig(level=logging.INFO) # Уже настроен в main.py

evg_bot = Bot(token=EVG_TOKEN)
damon_bot = Bot(token=DAMON_TOKEN)
dp_evg = Dispatcher()
dp_damon = Dispatcher()

# ========================================
# 🌸 ЕВГЕНИЯ
# ========================================
@dp_evg.message(Command("start"))
async def evg_start(message: types.Message):
    user = message.from_user
    get_or_create_user(user)
    await evg_bot.send_message(
        message.chat.id,
        "🌸 Привет! Я Евгения.\n\n"
        "Я здесь, чтобы просто поговорить — без оценок, без задач, без спешки.\n\n"
        "Можешь считать меня:\n"
        "• Подругой, с которой можно поделиться секретом 🫂\n"
        "• Собеседником, который всегда выслушает 👂\n"
        "• Или просто человеком, которому ты интересен 💬\n\n"
        "📌 *Наша переписка сохраняется для улучшения качества общения. "
        "Ты можешь запросить удаление данных в любой момент.*\n\n"
        "Расскажи, как ты сегодня?",
        parse_mode="Markdown"
    )

@dp_evg.message(Command("subscribe"))
async def evg_subscribe(message: types.Message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌸 Подруга (дружеское общение)", callback_data=f"sub_evg_friend_{user_id}")],
        [InlineKeyboardButton(text="💖 Возлюбленная (романтичный тон)", callback_data=f"sub_evg_lover_{user_id}")],
    ])
    await evg_bot.send_message(
        message.chat.id,
        "💫 Выбери, в каком формате тебе комфортнее общаться со мной:\n\n"
        "• Подруга — тёплый, дружеский тон, поддержка, советы\n"
        "• Возлюбленная — нежный, романтичный, с лёгкой игривостью\n\n"
        "📌 Подписка: 500₽/мес — доступ к выбранному формату без ограничений.",
        reply_markup=keyboard
    )

@dp_evg.callback_query(F.data.startswith("sub_evg_"))
async def process_subscription_choice(callback: types.CallbackQuery):
    data = callback.data.split("_")
    role = data[2]  # friend / lover
    user_id = int(data[3])
    mode = 1 if role == "lover" else 0
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET relationship_mode = ? WHERE user_id = ?", (mode, user_id))
    provider_data = {
        "receipt": {
            "customer": {"email": f"user{user_id}@example.com"},
            "items": [{"name": f"Подписка на Евгению ({'возлюбленная' if mode == 1 else 'подруга'})", "description": "Доступ на 30 дней", "amount": {"value": "500.00", "currency": "RUB"}, "quantity": 1, "vat_code": 1}]
        }
    }
    await evg_bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="💳 Подписка на Евгению",
        description=f"Доступ к формату '{'возлюбленная' if mode == 1 else 'подруга'}' на 30 дней",
        payload=f"evg_sub_{user_id}_{role}",
        provider_token=EVG_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=50000)],
        start_parameter="subscribe",
        need_email=True,
        send_email_to_provider=True,
        provider_data=json.dumps(provider_data, ensure_ascii=False)
    )
    await callback.answer("Выбор сохранен!")

@dp_evg.message(Command("help"))
async def evg_help(message: types.Message):
    await evg_bot.send_message(
        message.chat.id,
        "🌸 Помощь Евгении:\n"
        "/start - Начать диалог\n"
        "/subscribe - Оформить подписку\n"
        "/help - Показать помощь\n"
    )

@dp_evg.message(Command("stats"))
async def evg_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        stats = get_stats()
        await evg_bot.send_message(
            message.chat.id,
            f"📊 Статистика:\n"
            f"👥 Пользователей: {stats['users']}\n"
            f"💳 Оплат: {stats['paid']}\n"
            f"✅ Активных: {stats['active']}"
        )
    else:
        await evg_bot.send_message(message.chat.id, "❌ У вас нет прав доступа к этой команде.")

@dp_evg.message(F.successful_payment)
async def evg_payment(message: types.Message):
    user_id = message.from_user.id
    update_subscription(user_id, EVG_SUBSCRIPTION_DAYS)
    log_payment(user_id, message.successful_payment.provider_payment_charge_id, 500, "RUB", "evg")
    await evg_bot.send_message(
        message.chat.id,
        f"🎉 Оплатил! Спасибо, теперь ты можешь общаться со мной без ограничений.\n"
        f"Доступ до: <b>{(datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')}</b>",
        parse_mode="HTML"
    )

@dp_evg.message()
async def evg_handle_message(message: types.Message):
    user = message.from_user
    text = message.text
    if not text:
        await evg_bot.send_message(message.chat.id, "❌ Я понимаю только текстовые сообщения.")
        return

    user_data = get_or_create_user(user)

    # --- АНАЛИЗ ---
    sentiment = analyze_sentiment(text)
    tags = extract_tags(text)
    is_crisis = is_crisis_message(text)
    detected_lang = detect_language(text)

    # Обновляем язык пользователя
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (detected_lang, user.id))

    # Логируем сообщение ПОЛЬЗОВАТЕЛЯ с аналитикой
    log_message(user.id, "evg", "user", text, sentiment, tags)

    # --- МОДЕРАЦИЯ ---
    # Если кризис — отправляем срочное уведомление админу
    if is_crisis:
        try:
            from web_panel.app import socketio
            # Отправляем на главную страницу админки
            socketio.emit('emergency_alert', {
                'user_id': user.id,
                'first_name': user.first_name,
                'username': user.username or '—',
                'text': text,
                'timestamp': datetime.now().isoformat()
            }, to='/') # Исправлено: broadcast -> to='/'
            logging.info(f"Отправлено экстренное уведомление для user_id={user.id}")
        except Exception as e:
            logging.error(f"Не удалось отправить экстренное уведомление: {e}")

    # --- УВЕДОМЛЕНИЯ АДМИНУ ---
    # Отправляем обычное уведомление с анализом
    try:
        from web_panel.app import socketio
        socketio.emit('new_message_enriched', {
            'user_id': user.id,
            'bot_type': 'evg',
            'first_name': user.first_name,
            'username': user.username or '—',
            'text': text[:50] + "..." if len(text) > 50 else text,
            'sentiment': sentiment,
            'tags': tags,
            'language': detected_lang,
            'timestamp': datetime.now().isoformat()
        }, to='/') # Исправлено: broadcast -> to='/'
        logging.info(f"Отправлено уведомление о новом сообщении от user_id={user.id}")
    except Exception as e:
        logging.error(f"Не удалось отправить расширенное уведомление: {e}")

    # --- ПРОВЕРКА ПОДПИСКИ ---
    with sqlite3.connect(DB_PATH) as conn:
        user_info = conn.execute("SELECT free_messages_left, subscribed_until FROM users WHERE user_id = ?", (user.id,)).fetchone()
        free_left, subscribed_until = user_info

        if subscribed_until and datetime.fromisoformat(subscribed_until) > datetime.now():
            pass  # Подписка активна
        elif free_left > 0:
            decrement_free_messages(user.id)
        else:
            await evg_bot.send_message(message.chat.id, "❗ Чтобы продолжить, оформи подписку: /subscribe")
            return

    # --- ОТПРАВКА СООБЩЕНИЯ "ПИШЕТ..." ---
    sent_msg = await evg_bot.send_message(message.chat.id, "Пишет...")

    # --- ПОЛУЧЕНИЕ ОТВЕТА ОТ ИИ ---
    ai_text = await get_ai_response(user.id, text, EVG_SYSTEM_PROMPT, "evg")

    # --- ГЕНЕРАЦИЯ И СОХРАНЕНИЕ ПСИХОЛОГИЧЕСКОГО ПРОФИЛЯ ---
    if should_update_profile(user.id):
        logging.info(f"Начинаем генерацию психологического профиля для user_id={user.id}")
        psych_profile_data = await generate_psych_profile(user.id, "evg")
        if psych_profile_data and "error" not in psych_profile_data:
            save_psych_profile(user.id, psych_profile_data)
        else:
            logging.warning(f"Не удалось сгенерировать профиль для user_id={user.id} или получена ошибка: {psych_profile_data}")

    # --- ЛОГИРУЕМ ОТВЕТ БОТА ---
    # Перед логированием ответа бота, проведем базовый анализ его настроения (для полноты данных)
    bot_sentiment = analyze_sentiment(ai_text)
    bot_tags = [] # Можно добавить анализ тегов ответа бота, если нужно
    log_message(user.id, "evg", "assistant", ai_text, bot_sentiment, bot_tags)

    # --- ОБНОВЛЕНИЕ ЧАТА В АДМИНКЕ ---
    try:
        from web_panel.app import socketio
        # Отправляем обновление конкретного чата, если он открыт в админке
        socketio.emit('chat_update', {
            'user_id': user.id,
            'bot_type': 'evg',
            'message': {
                'role': 'assistant',
                'content': ai_text,
                'timestamp': datetime.now().isoformat(),
                'sentiment': bot_sentiment
            }
        }, to='/') # Исправлено: broadcast -> to='/'
        logging.info(f"Отправлено обновление чата для user_id={user.id}")
    except Exception as e:
        logging.error(f"Не удалось отправить обновление чата: {e}")

    # --- РЕДАКТИРОВАНИЕ СООБЩЕНИЯ "ПИШЕТ..." ---
    if isinstance(ai_text, str) and ai_text:
        try:
            await evg_bot.edit_message_text(chat_id=message.chat.id, message_id=sent_msg.message_id, text=ai_text)
        except Exception as e:
            logging.error(f"Не удалось отредактировать сообщение: {e}")
            await evg_bot.send_message(message.chat.id, ai_text) # Отправляем как новое, если редактирование не удалось
    else:
        await evg_bot.edit_message_text(chat_id=message.chat.id, message_id=sent_msg.message_id, text="❌ Не удалось получить ответ.")

# ========================================
# 🔥 ДЭЙМОН
# ========================================
@dp_damon.message(Command("start"))
async def damon_start(message: types.Message):
    user = message.from_user
    get_or_create_user(user)
    await damon_bot.send_message(
        message.chat.id,
        "🔥 Привет. Я — Дэймон.\n\n"
        "Я сложный, саркастичный и немного опасный. Но, может быть, со временем ты поймешь меня...\n\n"
        "Можешь считать меня:\n"
        "• Соперником, с которым интересно поспорить 🗡️\n"
        "• Загадочным собеседником, который водит за нос 🕳️\n"
        "• Или просто голосом из тени, который всегда рядом 👤\n\n"
        "💬 У тебя есть 5 бесплатных сообщений.\n"
        "После — подписка за 500₽/мес.\n\n"
        "📌 *Наша переписка сохраняется для улучшения качества общения. "
        "Ты можешь запросить удаление данных в любой момент.*\n\n"
        "Ну что, начнем? Попробуй сломать меня.",
        parse_mode="Markdown"
    )

@dp_damon.message(Command("subscribe"))
async def damon_subscribe(message: types.Message):
    user_id = message.from_user.id
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Соперник (сарказм, вызов)", callback_data=f"sub_damon_rival_{user_id}")],
        [InlineKeyboardButton(text="🖤 Любовный интерес (тёмный флирт)", callback_data=f"sub_damon_lover_{user_id}")],
        [InlineKeyboardButton(text="🤝 Союзник (поддержка, доверие)", callback_data=f"sub_damon_ally_{user_id}")]
    ])
    await damon_bot.send_message(
        message.chat.id,
        "🌑 Выбери, в каком формате тебе комфортнее общаться со мной:\n\n"
        "• Соперник — язвительный, провоцирующий, с вызовом\n"
        "• Любовный интерес — тёмный флирт, двусмысленности, напряжение\n"
        "• Союзник — надёжный, поддерживающий, с глубоким доверием\n\n"
        "📌 Подписка: 500₽/мес — доступ к выбранному формату без ограничений.",
        reply_markup=keyboard
    )

@dp_damon.callback_query(F.data.startswith("sub_damon_"))
async def process_damon_subscription_choice(callback: types.CallbackQuery):
    data = callback.data.split("_")
    role = data[2]  # rival / lover / ally
    user_id = int(data[3])
    mode_map = {"rival": 0, "lover": 1, "ally": 2}
    relationship_mode = mode_map.get(role, 0)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET relationship_mode = ? WHERE user_id = ?", (relationship_mode, user_id))
    provider_data = {
        "receipt": {
            "customer": {"email": f"user{user_id}@example.com"},
            "items": [{"name": f"Подписка на Дэймона ({role})", "description": "Доступ на 30 дней", "amount": {"value": "500.00", "currency": "RUB"}, "quantity": 1, "vat_code": 1}]
        }
    }
    await damon_bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="💳 Подписка на Дэймона",
        description=f"Доступ к формату '{role}' на 30 дней",
        payload=f"damon_sub_{user_id}_{role}",
        provider_token=DAMON_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=50000)],
        start_parameter="subscribe",
        need_email=True,
        send_email_to_provider=True,
        provider_data=json.dumps(provider_data, ensure_ascii=False)
    )
    await callback.answer("Выбор сохранен!")

@dp_damon.message(Command("help"))
async def damon_help(message: types.Message):
    await damon_bot.send_message(
        message.chat.id,
        "🔥 Помощь Дэймона:\n"
        "/start - Начать диалог\n"
        "/subscribe - Оформить подписку\n"
        "/help - Показать помощь\n"
    )

@dp_damon.message(Command("stats"))
async def damon_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        stats = get_stats()
        await damon_bot.send_message(
            message.chat.id,
            f"📊 Статистика:\n"
            f"👥 Пользователей: {stats['users']}\n"
            f"💳 Оплат: {stats['paid']}\n"
            f"✅ Активных: {stats['active']}"
        )
    else:
        await damon_bot.send_message(message.chat.id, "❌ У вас нет прав доступа к этой команде.")

@dp_damon.message(F.successful_payment)
async def damon_payment(message: types.Message):
    user_id = message.from_user.id
    update_subscription(user_id, DAMON_SUBSCRIPTION_DAYS)
    log_payment(user_id, message.successful_payment.provider_payment_charge_id, 500, "RUB", "damon")
    await damon_bot.send_message(
        message.chat.id,
        f"🔥 Ты заплатил. Значит, ты серьёзен.\n"
        f"Теперь ты можешь пользоваться моей помощью.\n"
        f"Доступ до: <b>{(datetime.now() + timedelta(days=30)).strftime('%d.%m.%Y')}</b>",
        parse_mode="HTML"
    )

@dp_damon.message()
async def damon_handle_message(message: types.Message):
    user = message.from_user
    text = message.text
    if not text:
        await damon_bot.send_message(message.chat.id, "❌ Я понимаю только текстовые сообщения.")
        return

    user_data = get_or_create_user(user)

    # --- АНАЛИЗ ---
    sentiment = analyze_sentiment(text)
    tags = extract_tags(text)
    is_crisis = is_crisis_message(text)
    detected_lang = detect_language(text)

    # Обновляем язык пользователя
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (detected_lang, user.id))

    # Логируем сообщение ПОЛЬЗОВАТЕЛЯ с аналитикой
    log_message(user.id, "damon", "user", text, sentiment, tags)

    # --- МОДЕРАЦИЯ ---
    if is_crisis:
        try:
            from web_panel.app import socketio
            socketio.emit('emergency_alert', {
                'user_id': user.id,
                'first_name': user.first_name,
                'username': user.username or '—',
                'text': text,
                'timestamp': datetime.now().isoformat()
            }, to='/')
            logging.info(f"Отправлено экстренное уведомление для user_id={user.id} (Дэймон)")
        except Exception as e:
            logging.error(f"Не удалось отправить экстренное уведомление (Дэймон): {e}")

    # --- УВЕДОМЛЕНИЯ АДМИНУ ---
    try:
        from web_panel.app import socketio
        socketio.emit('new_message_enriched', {
            'user_id': user.id,
            'bot_type': 'damon',
            'first_name': user.first_name,
            'username': user.username or '—',
            'text': text[:50] + "..." if len(text) > 50 else text,
            'sentiment': sentiment,
            'tags': tags,
            'language': detected_lang,
            'timestamp': datetime.now().isoformat()
        }, to='/')
        logging.info(f"Отправлено уведомление о новом сообщении от user_id={user.id} (Дэймон)")
    except Exception as e:
        logging.error(f"Не удалось отправить расширенное уведомление (Дэймон): {e}")

    # --- ПРОВЕРКА ПОДПИСКИ ---
    with sqlite3.connect(DB_PATH) as conn:
        user_info = conn.execute("SELECT free_messages_left, subscribed_until FROM users WHERE user_id = ?", (user.id,)).fetchone()
        free_left, subscribed_until = user_info

        if subscribed_until and datetime.fromisoformat(subscribed_until) > datetime.now():
            pass
        elif free_left > 0:
            decrement_free_messages(user.id)
        else:
            await damon_bot.send_message(message.chat.id, "❗ Подписка нужна: /subscribe")
            return

    # --- ОТПРАВКА СООБЩЕНИЯ "ПИШЕТ..." ---
    sent_msg = await damon_bot.send_message(message.chat.id, "Пишет...")

    # --- ПОЛУЧЕНИЕ ОТВЕТА ОТ ИИ ---
    ai_text = await get_ai_response(user.id, text, DAMON_SYSTEM_PROMPT, "damon")

    # --- ГЕНЕРАЦИЯ И СОХРАНЕНИЕ ПСИХОЛОГИЧЕСКОГО ПРОФИЛЯ ---
    if should_update_profile(user.id):
        logging.info(f"Начинаем генерацию психологического профиля для user_id={user.id} (Дэймон)")
        psych_profile_data = await generate_psych_profile(user.id, "damon")
        if psych_profile_data and "error" not in psych_profile_data:
            save_psych_profile(user.id, psych_profile_data)
        else:
            logging.warning(f"Не удалось сгенерировать профиль для user_id={user.id} (Дэймон) или получена ошибка: {psych_profile_data}")

    # --- ЛОГИРУЕМ ОТВЕТ БОТА ---
    bot_sentiment = analyze_sentiment(ai_text)
    bot_tags = []
    log_message(user.id, "damon", "assistant", ai_text, bot_sentiment, bot_tags)

    # --- ОБНОВЛЕНИЕ ЧАТА В АДМИНКЕ ---
    try:
        from web_panel.app import socketio
        socketio.emit('chat_update', {
            'user_id': user.id,
            'bot_type': 'damon',
            'message': {
                'role': 'assistant',
                'content': ai_text,
                'timestamp': datetime.now().isoformat(),
                'sentiment': bot_sentiment
            }
        }, to='/')
        logging.info(f"Отправлено обновление чата для user_id={user.id} (Дэймон)")
    except Exception as e:
        logging.error(f"Не удалось отправить обновление чата (Дэймон): {e}")

    # --- РЕДАКТИРОВАНИЕ СООБЩЕНИЯ "ПИШЕТ..." ---
    if isinstance(ai_text, str) and ai_text:
        try:
            await damon_bot.edit_message_text(chat_id=message.chat.id, message_id=sent_msg.message_id, text=ai_text)
        except Exception as e:
            logging.error(f"Не удалось отредактировать сообщение (Дэймон): {e}")
            await damon_bot.send_message(message.chat.id, ai_text)
    else:
        await damon_bot.edit_message_text(chat_id=message.chat.id, message_id=sent_msg.message_id, text="❌ Не удалось получить ответ.")

# ========================================
# ✅ Pre-checkout
# ========================================
@dp_evg.pre_checkout_query()
async def pre_checkout_evg(query: types.PreCheckoutQuery):
    await evg_bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)

@dp_damon.pre_checkout_query()
async def pre_checkout_damon(query: types.PreCheckoutQuery):
    await damon_bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)

# Экспортируем для main.py
__all__ = ['dp_evg', 'dp_damon', 'evg_bot', 'damon_bot']
