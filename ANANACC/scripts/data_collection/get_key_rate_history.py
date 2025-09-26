# scripts/data_collection/get_key_rate_history.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from config import HISTORICAL_DATA_DIR

# Конфигурация
CBR_KEY_RATE_URL = "https://www.cbr.ru/hd_base/KeyRate/"
OUTPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['other'], "cbr_key_rate_history.csv")

def get_key_rate_html():
    """Получает HTML-страницу с историей ключевой ставки."""
    try:
        response = requests.get(CBR_KEY_RATE_URL, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Ошибка запроса: {e}")
        return None

def parse_key_rate_html(html):
    """Парсит HTML и извлекает таблицу с ключевой ставкой."""
    if not html:
        return pd.DataFrame()

    try:
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', class_='data')
        if not table:
            return pd.DataFrame()

        rows = table.find_all('tr')[1:]  # Пропускаем заголовок
        data = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                date_str = cols[0].get_text(strip=True)
                rate_str = cols[1].get_text(strip=True).replace('%', '').replace(',', '.').strip()
                try:
                    date = pd.to_datetime(date_str, format='%d.%m.%Y').strftime('%Y-%m-%d')
                    rate = float(rate_str)
                    data.append([date, rate])
                except:
                    continue

        return pd.DataFrame(data, columns=['TRADEDATE', 'CBR_KEY_RATE'])

    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return pd.DataFrame()

def save_key_rate_history(df):
    """Сохраняет историю ключевой ставки в CSV."""
    if df.empty:
        return False
    try:
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        return False

def main():
    print("=== Сбор истории ключевой ставки ЦБ ===")
    html = get_key_rate_html()
    if not html:
        print("Не удалось получить данные.")
        return

    df = parse_key_rate_html(html)
    if df.empty:
        print("Не удалось извлечь данные из HTML.")
        return

    if save_key_rate_history(df):
        print(f"История ключевой ставки сохранена в {OUTPUT_FILE}")
    else:
        print("Ошибка сохранения.")

if __name__ == "__main__":
    main()
