# chat.py - Мини-чат между двумя терминалами
import os
import time
import threading
LOG_FILE = "chat.log"
MAX_LINES = 50
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
def show_messages():
    if not os.path.exists(LOG_FILE):
        return
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        for line in lines[-MAX_LINES:]:
            print(line.strip())
    except:
        pass
def add_message(username, text):
    timestamp = time.strftime("%H:%M:%S")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {username}: {text}\n")
def monitor_file():
    if not os.path.exists(LOG_FILE):
        open(LOG_FILE, 'w').close()
    show_messages()
    print("-" * 40)
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        f.seek(0, 2)  # В конец
        while True:
            line = f.readline()
            if line:
                print(line.strip())
            else:
                time.sleep(0.3)  # Не нагружаем CPU
def main():
    clear_screen()
    print("💬 MINI-CHAT — чат без интернета")
    print("Для выхода: Ctrl+C")
    print("=" * 40)
    username = input("Введите ваше имя: ").strip()
    if not username:
        username = "Аноним"
    thread = threading.Thread(target=monitor_file, daemon=True)
    thread.start()
    print("✏️  Пишите сообщение и нажмите Enter (пустое — выход):")
    print("-" * 40)
    while True:
        try:
            text = input("> ").strip()
            if not text:
                print("👋 Выход из чата.")
                break
            add_message(username, text)
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Чат остановлен.")
            break
if __name__ == "__main__":
    main()
