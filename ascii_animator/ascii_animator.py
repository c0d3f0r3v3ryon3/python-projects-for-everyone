# ascii_simple.py - ASCII-арт из простых символов
from PIL import Image, ImageEnhance
import os
OUTPUT_WIDTH = 350           # Можно уменьшить до 100, если не влазит
CONTRAST_BOOST = 1.5         # Усиливаем контраст для чёткости
CHARS = "@%*.:- "            # Простые символы: от тёмных к светлым
def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 80
def image_to_ascii(image_path, width=OUTPUT_WIDTH):
    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return ""
    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
        bg = Image.new("RGB", img.size, (255, 255, 255))
        try:
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[-1])
            else:
                alpha = img.convert("RGBA").split()[-1]
                bg.paste(img, mask=alpha)
            img = bg
        except Exception as e:
            print(f"⚠️ Ошибка прозрачности: {e}")
            return ""
    img = img.convert('L')
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(CONTRAST_BOOST)
    ratio = img.height / img.width
    new_width = width
    new_height = int(new_width * ratio * 0.5)  # 0.5 — подгонка под шрифт
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    pixels = list(img.getdata())
    ascii_str = ""
    char_count = len(CHARS)
    for i, pixel in enumerate(pixels):
        char = CHARS[pixel * (char_count - 1) // 255]
        ascii_str += char
        if (i + 1) % new_width == 0:
            ascii_str += "\n"
    return ascii_str
def main():
    print("🖼 ASCII-АРТ ИЗ ПРОСТЫХ СИМВОЛОВ")
    print("Без █▓▒░ — только @%*.:")
    print("=" * 60)
    path = input("\n📁 Путь к изображению: ").strip()
    if not path or not os.path.exists(path):
        print("❌ Файл не найден.")
        return
    print(f"🔄 Генерирую ASCII из простых символов (ширина={OUTPUT_WIDTH})...")
    ascii_art = image_to_ascii(path, width=OUTPUT_WIDTH)
    if not ascii_art.strip():
        print("❌ Не удалось создать ASCII-арт.")
        return
    print("\n" + "="*60)
    print("🎨 РЕЗУЛЬТАТ:")
    print("="*60)
    print(ascii_art)
    print("="*60)
    save = input("\n💾 Сохранить в файл? (y/n): ").strip().lower()
    if save == 'y':
        filename = input("Имя файла (по умолчанию ascii_simple.txt): ").strip()
        if not filename:
            filename = "ascii_simple.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(ascii_art)
            print(f"✅ Сохранено: {filename}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
    print("\n✅ Готово!")
if __name__ == "__main__":
    main()
