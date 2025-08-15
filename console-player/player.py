# player.py - Консольный плеер с очисткой экрана
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")
import pygame
import time
pygame.mixer.init()
MUSIC_FOLDER = "music"
SUPPORTED = (".mp3", ".wav", ".ogg")
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')
def scan_music():
    if not os.path.exists(MUSIC_FOLDER):
        print("❌ Папка 'music' не найдена.")
        return []
    tracks = [f for f in os.listdir(MUSIC_FOLDER) if f.lower().endswith(SUPPORTED)]
    return sorted(tracks)
def show_menu(tracks):
    print("🎵 КОНСОЛЬНЫЙ ПЛЕЕР\n" + "=" * 40 + "\nДоступные треки:")
    for i, track in enumerate(tracks, 1):
        print(f"  {i}. {track}")
    print("\nВведите номер трека (или 0, чтобы выйти): ", end="")
def play_track(track_path):
    clear_screen()
    print(f"▶️ Играет: {os.path.basename(track_path)}"+"\n⏸️  Нажмите ENTER, чтобы остановить...")
    pygame.mixer.music.load(track_path)
    pygame.mixer.music.play()
    input()
    pygame.mixer.music.stop()
    print("⏹️ Остановлено.")
clear_screen()
print("🎧 Загрузка плеера...")
while True:
    tracks = scan_music()
    clear_screen()
    if not tracks:
        print("❌ Нет музыки в папке 'music'. Добавь .mp3, .wav или .ogg\nНажми Ctrl+C, чтобы выйти.")
        time.sleep(2)
        continue
    show_menu(tracks)
    try:
        choice = input().strip()
        if choice == '0':
            clear_screen()
            print("👋 Выход из плеера. Пока!")
            break
        choice = int(choice) - 1
        if 0 <= choice < len(tracks):
            full_path = os.path.join(MUSIC_FOLDER, tracks[choice])
            play_track(full_path)
    except ValueError:
        print("❌ Введите число.")
    except KeyboardInterrupt:
        clear_screen()
        print("👋 Прервано. Выход...")
        break
