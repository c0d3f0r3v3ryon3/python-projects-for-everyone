# main.py
import asyncio
import threading
import logging
from aiogram.methods import DeleteWebhook

from bot_logic import dp_evg, dp_damon, evg_bot, damon_bot
from web_panel.app import app as flask_app, socketio

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

def run_bots():
    """Функция для запуска ботов в отдельном потоке."""
    async def start_bots():
        await evg_bot(DeleteWebhook(drop_pending_updates=True))
        await damon_bot(DeleteWebhook(drop_pending_updates=True))
        print("🤖 Боты Евгения и Дэймон запущены!")
        await asyncio.gather(
            dp_evg.start_polling(evg_bot),
            dp_damon.start_polling(damon_bot)
        )

    asyncio.run(start_bots())

if __name__ == "__main__":
    # Запускаем ботов в фоновом потоке
    bot_thread = threading.Thread(target=run_bots, daemon=True)
    bot_thread.start()

    # Запускаем веб-сервер Flask
    print("🌐 Веб-панель запущена на http://localhost:5000")
    # use_reloader=False важно для многопоточных приложений
    socketio.run(flask_app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
