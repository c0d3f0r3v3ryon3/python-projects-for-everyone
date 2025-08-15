# typer.py - Тренажёр скорости печати
import time
import random
texts = [
    "The quick brown fox jumps over the lazy dog.",
    "Python is a powerful and easy-to-learn programming language.",
    "Speed and accuracy are key to fast typing.",
    "Code every day to improve your skills.",
    "TikTok taught me to code — now I'm a developer."
]
text = random.choice(texts)
print("\n" + "="*50)
print("⌨️  ТРЕНАЖЁР СКОРОСТИ ПЕЧАТИ")
print("="*50)
print(f"Напечатай этот текст:\n\n{text}\n")
input("Нажми ENTER, чтобы начать...")
start = time.time()
user_input = input("\n▶️ Ввод: ")
end = time.time()
duration = end - start
chars = len(user_input)
errors = sum(1 for a, b in zip(user_input, text) if a != b)
accuracy = (1 - errors / len(text)) * 100 if len(text) > 0 else 0
speed_cpm = int(chars / (duration / 60))  # символов в минуту
print("\n" + "-"*50)
print("✅ РЕЗУЛЬТАТ")
print(f"Время: {duration:.1f} сек")
print(f"Скорость: {speed_cpm} зн/мин")
print(f"Точность: {accuracy:.1f}%")
print(f"Ошибки: {errors}")
print("-"*50)
