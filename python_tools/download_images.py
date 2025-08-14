# download_images.py
from ddgs import DDGS
import requests
import os
from PIL import Image
from io import BytesIO
import time

QUERY = input("Введите запрос: ").strip()
MAX_IMAGES = 20
FOLDER = "downloaded_images"
os.makedirs(FOLDER, exist_ok=True)
if not QUERY:
    print("❌ Запрос не может быть пустым.")
    exit()
print(f"🔍 Ищу картинки по запросу: '{QUERY}'...")
with DDGS() as ddgs:
    try:
        results = ddgs.images(
            query=QUERY,
            max_results=MAX_IMAGES
        )
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        exit()
if not results:
    print("❌ Ничего не найдено.")
else:
    downloaded = 0
    for i, result in enumerate(results, start=1):
        try:
            image_url = result['image']
            print(f"📥 {i}/{MAX_IMAGES}: {image_url[:60]}...")
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
            ext = img.format.lower() if img.format else "jpg"
            filename = f"{QUERY.replace(' ', '_')}_{i}.{ext}"
            filepath = os.path.join(FOLDER, filename)
            with open(filepath, 'wb') as f:
                f.write(response.content)
            downloaded += 1
            time.sleep(0.2)  # лёгкая задержка, чтобы не перегружать
        except Exception as e:
            print(f"⚠️ Пропущено (ошибка): {e}")
            continue
    print(f"✅ Готово! Скачано: {downloaded} изображений в папку '{FOLDER}'")
