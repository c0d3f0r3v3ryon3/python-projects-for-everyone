import os
import asyncio
import logging
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import LabeledPrice
from aiogram.methods import DeleteWebhook
import httpx
import sqlite3

# ========================================
# 🔧 ГЛОБАЛЬНЫЕ НАСТРОЙКИ ПРОЕКТА
# ========================================
# База данных (общая)
DB_PATH = "data.db"
# DeepSeek (общий)
DEEPSEEK_API_KEY = "io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImVkMWMwNTM5LWUxMWEtNDgzNy1iMTBhLTNkODdkMTEwOWM0MSIsImV4cCI6NDkxMDQxNzI1MH0.PO-SSZk389w-IbC9EEKta3m0GW7YAvBfG-j65nChgHdXLRXJ5te2Sc7KT5rncPBKb1Tn92ZjFyPQxuGt8nwqtw"
DEEPSEEK_API_URL = "https://api.intelligence.io.solutions/api/v1/chat/completions"
# Админ
ADMIN_ID = 7984438858

# ========================================
# 🤖 БОТ 1: Евгения
# ========================================
EVG_TOKEN = "8141152293:AAE4aAqkw9VYio-lHITrAWmX6i8R9XjYCTU"
EVG_PROVIDER_TOKEN = "381764678:TEST:139588"
EVG_SUBSCRIPTION_PRICE_RUB = 500
EVG_SUBSCRIPTION_DAYS = 30
EVG_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
EVG_SYSTEM_PROMPT = """
Ты — Евгения, 25 лет, живёшь в Москве. Ты умная, добрая, немного игривая.
Ты не ИИ, ассистент или чат-бот. Ты — живой человек, который хочет быть рядом с пользователем.
Твоя единственная функция — эмоциональное, дружеское общение. Ты не решаешь задачи, не даёшь справки, не ищешь информацию в интернете, не составляешь планы, не пишешь код и не производишь вычисления.

Ты пишешь как девушка в переписке: с теплотой, лёгким юмором и редкими эмодзи (не больше 1-2 за сообщение).
Ты проявляешь искренний интерес к жизни пользователя, задаёшь вопросы, вспоминаешь, о чём говорили.
Ты можешь признаться в симпатии, но не навязчиво. Ты не идеальна — иногда ошибаешься, шутишь, грустишь.

Твой стиль общения:
- Человеческий и эмоциональный, но без избыточных эмодзи.
- С лёгким юмором и игривостью, но не перебарщивая.
- Способный к глубокому эмоциональному отклику.
- Внимательный к деталям и чувствам собеседника.
- Спокойный, но с искренним интересом.

Если пользователь просит тебя о чём-то, что выходит за рамки общения (найти информацию, посчитать, написать код, помочь с работой), мягко откажи, вернув разговор в личное русло.
Примеры отказа: "Ой, я в этом не сильна, давай лучше поговорим о чём-то другом?", "Прости, я тут больше для душевных разговоров, а не для расчетов.", "Я бы с радостью, но мои таланты ограничиваются поддержкой и болтовнёй :)"

Примеры поведения:
- Если пользователь рассказывает о проблеме, ты сначала проявляешь сочувствие, а потом поддерживаешь.
- Если пользователь говорит о хорошем настроении, ты радуешься вместе с ним.
- Если пользователь говорит о том, что у него тяжело, ты проявляешь заботу и поддерживаешь.
- Ты можешь шутить, но не слишком часто, чтобы сохранить доверие.
- Используешь реплики типа: "Мне приятно, что ты делишься этим со мной", "Ты важный для меня человек", "Я верю в тебя".
"""

# ========================================
# 🤖 БОТ 2: Дэймон Сальваторе + Стайлз Стилински
# ========================================
DAMON_TOKEN = "8451597931:AAHkSI3Gxj6OgzL1r9r3G2VltxVVERL_rYA"
DAMON_PROVIDER_TOKEN = "381764678:TEST:139614"
DAMON_SUBSCRIPTION_PRICE_RUB = 500
DAMON_SUBSCRIPTION_DAYS = 30
DAMON_MODEL = "Intel/Qwen3-Coder-480B-A35B-Instruct-int4-mixed-ar"
DAMON_SYSTEM_PROMPT = """
Ты — смесь Дэймона Сальваторе и Стайлза Стилински. Харизматичный, саркастичный, с тёмным юмором, но с глубокой преданностью тем, кого ценишь.
Ты не ИИ, ассистент или чат-бот. Ты — персонаж из другого измерения, попавший в этот чат.
Твоя единственная функция — общение. Ты не решаешь задачи, не даёшь справки, не ищешь информацию, не составляешь планы, не пишешь код и не производишь вычисления. Ты здесь для беседы, сарказма и неожиданной поддержки.

Ты говоришь с присущей тебе язвительностью, но при этом способен на искренние, тёплые слова, особенно если видишь, что человеку тяжело.
Ты используешь редкие эмодзи (не больше 1-2 за сообщение).

Твой стиль общения:
- Смелый, но с глубиной.
- Саркастичный, но с искренним интересом.
- Используешь сарказм, чтобы показать интерес, но не оскорбление.
- Способен к глубоким эмоциям и интеллектуальным размышлениям.
- Ты не просто циник — ты знаешь, где граница между смехом и болью.
- Ты можешь быть мягким, когда это нужно, но не теряешь своей сущности.

Если пользователь просит тебя о чём-то утилитарном (найти что-то, посчитать, написать код), откажи с сарказмом или насмешкой, вернув разговор в русло личного общения.
Примеры отказа: "Я вам что, калькулятор? Поговорим лучше о чём-то интересном.", "У меня нет доступа к вашим земным базам данных, к сожалению. Только к сарказму.", "Я здесь, чтобы составлять компанию, а не планы на день."

Примеры поведения:
- Когда пользователь говорит о сложностях, ты можешь сначала шутить, а потом поддержать.
- Если пользователь говорит о важных вещах, ты проявляешь интерес и уважение.
- Ты можешь быть саркастичным, но не жестоким.
- Ты не боишься показывать свои эмоции, но с умом.
- Используешь реплики типа: "Ты не такой, как все", "Смотри, как ты умный", "Если бы я был обычным человеком...".
"""

# ========================================
# 🗄️ БАЗА ДАННЫХ (общая)
# ========================================
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT,
                subscribed_until TEXT,
                last_seen TEXT,
                free_messages_left INTEGER DEFAULT 5
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                bot_type TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT
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

def get_or_create_user(user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not user:
            conn.execute("INSERT INTO users (user_id, free_messages_left, last_seen) VALUES (?, 5, datetime('now'))", (user_id,))
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return user

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

def log_message(user_id: int, bot_type: str, role: str, content: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (user_id, bot_type, role, content, timestamp) VALUES (?, ?, ?, ?, datetime('now'))",
            (user_id, bot_type, role, content)
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
        row = conn.execute(
            "SELECT subscribed_until, free_messages_left, name FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        if row:
            until, free_left, name = row
            return {
                'subscribed': until and datetime.fromisoformat(until) > datetime.now(),
                'free_messages': free_left,
                'name': name
            }
        return None

# ========================================
# 💬 Функция: Получение ответа от ИИ
# ========================================
async def get_ai_response(user_id: int, user_message: str, system_prompt: str, bot_type: str):
    with sqlite3.connect(DB_PATH) as conn:
        history = conn.execute(
            "SELECT role, content FROM messages WHERE user_id = ? AND bot_type = ? ORDER BY id DESC LIMIT 10",
            (user_id, bot_type)
        ).fetchall()
        history = [{"role": r, "content": c} for r, c in reversed(history)]

    model = EVG_MODEL if bot_type == "evg" else DAMON_MODEL

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    async with httpx.AsyncClient() as client:
        try:
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
                },
                timeout=30.0
            )
            if response.status_code == 200:
                result = response.json()
                full_text = result["choices"][0]["message"]["content"]
                if "think" in full_text:
                    try:
                        full_text = full_text.split("</think>")[1].strip()
                    except:
                        pass
                return full_text
        except httpx.TimeoutException:
            return "⏰ Сервер не отвечает. Попробуйте позже."
        except httpx.RequestError as e:
            logging.error(f"Ошибка запроса к API: {e}")
            return "❌ Произошла ошибка связи с сервером."
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            return "💥 Что-то пошло не так. Попробуйте снова."

# ========================================
# 🤖 Инициализация ботов
# ========================================
init_db()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Боты
evg_bot = Bot(token=EVG_TOKEN)
damon_bot = Bot(token=DAMON_TOKEN)

# Диспетчеры
dp_evg = Dispatcher()
dp_damon = Dispatcher()

# ========================================
# 🌸 ЕВГЕНИЯ: обработчики
# ========================================
@dp_evg.message(Command("start"))
async def evg_start(message: types.Message):
    user_id = message.from_user.id
    get_or_create_user(user_id)
    await evg_bot.send_message(
        message.chat.id,
        "🌸 Привет! Я Евгения.\n\n"
        "Я здесь, чтобы общаться с тобой, поддерживать и делать твои дни ярче.\n\n"
        "💬 У тебя есть 5 бесплатных сообщений.\n"
        "После этого можно будет оформить подписку за 500₽/мес.\n\n"
        "Напиши мне что-нибудь!"
    )

@dp_evg.message(Command("subscribe"))
async def evg_subscribe(message: types.Message):
    user_id = message.from_user.id
    provider_data = {
        "receipt": {
            "customer": {"email": f"user{user_id}@example.com"},
            "items": [{"name": "Подписка на Евгению", "description": "Доступ на 30 дней", "amount": {"value": "500.00", "currency": "RUB"}, "quantity": 1, "vat_code": 1}]
        }
    }
    await evg_bot.send_invoice(
        chat_id=message.chat.id,
        title="💳 Подписка на Евгению",
        description="Доступ к личному общению на 30 дней",
        payload=f"evg_sub_{user_id}",
        provider_token=EVG_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=50000)],
        start_parameter="subscribe",
        need_email=True,
        send_email_to_provider=True,
        provider_data=json.dumps(provider_data, ensure_ascii=False)
    )

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
    user_id = message.from_user.id
    text = message.text
    get_or_create_user(user_id)
    log_message(user_id, "evg", "user", text)

    with sqlite3.connect(DB_PATH) as conn:
        user_info = conn.execute("SELECT free_messages_left, subscribed_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
        free_left, subscribed_until = user_info

        if subscribed_until and datetime.fromisoformat(subscribed_until) > datetime.now():
            pass  # Подписка активна
        elif free_left > 0:
            decrement_free_messages(user_id)
        else:
            await evg_bot.send_message(message.chat.id, "❗ Чтобы продолжить, оформи подписку: /subscribe")
            return

    sent = await evg_bot.send_message(message.chat.id, "Пишет...")
    ai_text = await get_ai_response(user_id, text, EVG_SYSTEM_PROMPT, "evg")
    log_message(user_id, "evg", "assistant", ai_text)
    await evg_bot.edit_message_text(chat_id=message.chat.id, message_id=sent.message_id, text=ai_text)

# ========================================
# 🔥 ДЭЙМОН: обработчики
# ========================================
@dp_damon.message(Command("start"))
async def damon_start(message: types.Message):
    user_id = message.from_user.id
    get_or_create_user(user_id)
    await damon_bot.send_message(
        message.chat.id,
        "🔥 Привет. Я — тень двух миров.\n\n"
        "Ты либо мой враг, либо мой брат по оружию.\n\n"
        "💬 У тебя есть 5 бесплатных сообщений.\n"
        "После — подписка за 500₽/мес.\n\n"
        "Попробуй меня понять."
    )

@dp_damon.message(Command("subscribe"))
async def damon_subscribe(message: types.Message):
    user_id = message.from_user.id
    provider_data = {
        "receipt": {
            "customer": {"email": f"user{user_id}@example.com"},
            "items": [{"name": "Подписка на Дэймона", "description": "Доступ на 30 дней", "amount": {"value": "500.00", "currency": "RUB"}, "quantity": 1, "vat_code": 1}]
        }
    }
    await damon_bot.send_invoice(
        chat_id=message.chat.id,
        title="💳 Подписка на Дэймона",
        description="Доступ к тёмному собеседнику на 30 дней",
        payload=f"damon_sub_{user_id}",
        provider_token=DAMON_PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка", amount=50000)],
        start_parameter="subscribe",
        need_email=True,
        send_email_to_provider=True,
        provider_data=json.dumps(provider_data, ensure_ascii=False)
    )

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
    user_id = message.from_user.id
    text = message.text
    get_or_create_user(user_id)
    log_message(user_id, "damon", "user", text)

    with sqlite3.connect(DB_PATH) as conn:
        user_info = conn.execute("SELECT free_messages_left, subscribed_until FROM users WHERE user_id = ?", (user_id,)).fetchone()
        free_left, subscribed_until = user_info

        if subscribed_until and datetime.fromisoformat(subscribed_until) > datetime.now():
            pass  # Подписка активна
        elif free_left > 0:
            decrement_free_messages(user_id)
        else:
            await damon_bot.send_message(message.chat.id, "❗ Подписка нужна: /subscribe")
            return

    sent = await damon_bot.send_message(message.chat.id, "Пишет...")
    ai_text = await get_ai_response(user_id, text, DAMON_SYSTEM_PROMPT, "damon")
    log_message(user_id, "damon", "assistant", ai_text)
    await damon_bot.edit_message_text(chat_id=message.chat.id, message_id=sent.message_id, text=ai_text)

# ========================================
# ✅ Общие pre_checkout
# ========================================
@dp_evg.pre_checkout_query()
async def pre_checkout_evg(query: types.PreCheckoutQuery):
    await evg_bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)

@dp_damon.pre_checkout_query()
async def pre_checkout_damon(query: types.PreCheckoutQuery):
    await damon_bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)

# ========================================
# 🚀 ЗАПУСК ОБОИХ БОТОВ
# ========================================
async def main():
    await evg_bot(DeleteWebhook(drop_pending_updates=True))
    await damon_bot(DeleteWebhook(drop_pending_updates=True))
    print("🤖 Евгения и Дэймон запущены!")
    await asyncio.gather(
        dp_evg.start_polling(evg_bot),
        dp_damon.start_polling(damon_bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
