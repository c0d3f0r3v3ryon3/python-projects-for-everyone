# rename_files.py
import os

folder = "downloaded_images"
for i, filename in enumerate(os.listdir(folder)):
    os.rename(f"{folder}/{filename}", f"{folder}/photo_{i+1}.jpg")

print("✅ Все файлы переименованы!")
