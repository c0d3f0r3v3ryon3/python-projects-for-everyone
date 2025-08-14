# main.py - "Ключ от Хроноса"
import pygame
import sys

pygame.init()

# Окно
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Ключ от Хроноса")
clock = pygame.time.Clock()

# Цвета
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 100)
BLUE = (100, 150, 255)
RED = (255, 60, 60)
DIALOG_BG = (20, 20, 40, 200)

# Шрифты
title_font = pygame.font.SysFont("Arial", 60, bold=True)
dialog_font = pygame.font.SysFont("Arial", 28)
button_font = pygame.font.SysFont("Arial", 30, bold=True)

# Загрузка фона
try:
    background = pygame.image.load("assets/bg/library_night.jpg")
    background = pygame.transform.scale(background, (WIDTH, HEIGHT))
except:
    background = pygame.Surface((WIDTH, HEIGHT))
    background.fill((10, 10, 30))

# Загрузка персонажа
try:
    protagonist = pygame.image.load("assets/characters/protagonist.png")
    protagonist = pygame.transform.scale(protagonist, (200, 300))
except:
    protagonist = pygame.Surface((200, 300))
    protagonist.fill((100, 100, 150))

# Музыка и звуки
try:
    pygame.mixer.music.load("assets/music/ambient_theme.mp3")
    pygame.mixer.music.set_volume(0.3)
    pygame.mixer.music.play(-1)
except:
    pass

try:
    select_sound = pygame.mixer.Sound("assets/sfx/select.wav")
except:
    select_sound = None

# Сцены
scene = "start"

# Универсальная функция: центрированный текст
def draw_centered_text(text, font, color, y):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH // 2, y))
    screen.blit(surf, rect)

# Панель диалога (внизу)
def draw_dialog_box():
    dialog_rect = pygame.Rect(50, 500, 700, 90)
    pygame.draw.rect(screen, DIALOG_BG, dialog_rect, border_radius=16)
    pygame.draw.rect(screen, YELLOW, dialog_rect, width=2, border_radius=16)
    return dialog_rect

# Кнопки с hover
def draw_button(rect, text, hover=False):
    color = (80, 80, 180) if hover else (100, 130, 255)
    pygame.draw.rect(screen, color, rect, border_radius=12)
    text_surf = button_font.render(text, True, WHITE)
    text_rect = text_surf.get_rect(center=rect.center)
    screen.blit(text_surf, text_rect)

# Основной цикл
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    screen.blit(background, (0, 0))
    screen.blit(protagonist, (50, 250))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN and scene == "start":
            if btn_open.collidepoint(mouse_pos):
                scene = "door"
                if select_sound: select_sound.play()
            elif btn_hide.collidepoint(mouse_pos):
                scene = "hide"
                if select_sound: select_sound.play()
            elif btn_throw.collidepoint(mouse_pos):
                scene = "throw"
                if select_sound: select_sound.play()

    # === Сцены ===
    if scene == "start":
        # Заголовок (вверху)
        draw_centered_text("Ключ от Хроноса", title_font, YELLOW, 60)

        # Диалог
        dialog_rect = draw_dialog_box()
        dialog_text = "Ты нашёл странный ключ в библиотеке..."
        text_surf = dialog_font.render(dialog_text, True, WHITE)
        screen.blit(text_surf, (dialog_rect.x + 30, dialog_rect.y + 15))

        # Кнопки
        btn_open = pygame.Rect(100, 300, 580, 50)
        btn_hide = pygame.Rect(100, 370, 580, 50)
        btn_throw = pygame.Rect(100, 440, 580, 50)

        draw_button(btn_open, "1. Открыть дверь в подвале", btn_open.collidepoint(mouse_pos))
        draw_button(btn_hide, "2. Спрятать в рюкзаке", btn_hide.collidepoint(mouse_pos))
        draw_button(btn_throw, "3. Бросить в реку", btn_throw.collidepoint(mouse_pos))

    elif scene == "door":
        draw_dialog_box()
        text = "Дверь скрипнула... Кто-то внутри?"
        text_surf = dialog_font.render(text, True, RED)
        screen.blit(text_surf, (100, 520))

    elif scene == "hide":
        draw_dialog_box()
        text = "Ключ начал светиться... Время замедлилось."
        text_surf = dialog_font.render(text, True, WHITE)
        screen.blit(text_surf, (100, 520))

    elif scene == "throw":
        draw_dialog_box()
        text = "Река вспыхнула зелёным... Что-то приближается."
        text_surf = dialog_font.render(text, True, WHITE)
        screen.blit(text_surf, (100, 520))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
