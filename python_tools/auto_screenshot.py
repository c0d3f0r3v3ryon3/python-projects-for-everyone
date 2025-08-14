# auto_screenshot.py
import pyautogui
import time
import os

os.makedirs("downloaded_images", exist_ok=True)

for i in range(10):
    screenshot = pyautogui.screenshot()
    screenshot.save(f"downloaded_images/shot_{i+1}.png")
    time.sleep(2)  # Каждые 2 секунды

print("✅ 10 скриншотов сделано!")
