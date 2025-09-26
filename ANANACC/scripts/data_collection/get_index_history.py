# scripts/data_collection/get_index_history.py
import pandas as pd
import requests
import time
import os
from config import HISTORICAL_DATA_DIR, SCRIPTS_DIR

# Конфигурация
INPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['stocks'], "moex_indices_list.csv")
OUTPUT_DIR = HISTORICAL_DATA_DIR['indices']
START_DATE = "2023-01-01"
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "index"
ENGINE = "stock"
REQUEST_DELAY = 1.0  # Задержка между запросами (секунды)

def load_indices_list(filename):
    """Загружает список индексов из CSV."""
    try:
        return pd.read_csv(filename)[['SECID', 'BOARDID']]
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return pd.DataFrame()

def get_index_history(secid):
    """Получает исторические данные для одного индекса."""
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/securities/{secid}.json"
    params = {
        "from": START_DATE,
        "iss.meta": "off"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if 'history' not in data or not data['history']['data']:
            return None

        df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE']).dt.date
        required_cols = ['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE']
        if all(col in df.columns for col in required_cols):
            return df[required_cols]
        return None

    except Exception as e:
        print(f"Ошибка для индекса {secid}: {e}")
        return None

def save_history(df, secid):
    """Сохраняет историю индекса в CSV."""
    if df is None or df.empty:
        return False
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = os.path.join(OUTPUT_DIR, f"{secid}_history.csv")
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return True
    except Exception as e:
        print(f"Ошибка сохранения для {secid}: {e}")
        return False

def main():
    print("=== Сбор исторических данных индексов ===")
    indices_df = load_indices_list(INPUT_FILE)
    if indices_df.empty:
        print("Не удалось загрузить список индексов.")
        return

    total = len(indices_df)
    success = 0
    for i, (_, row) in enumerate(indices_df.iterrows(), 1):
        secid = row['SECID']
        print(f"[{i}/{total}] Обработка индекса {secid}...")

        data = get_index_history(secid)
        if save_history(data, secid):
            success += 1
        time.sleep(REQUEST_DELAY)

    print(f"\nГотово. Успешно обработано {success}/{total} индексов.")

if __name__ == "__main__":
    main()
