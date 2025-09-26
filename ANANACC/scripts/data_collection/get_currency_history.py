# scripts/data_collection/get_currency_history.py
import pandas as pd
import requests
import time
import os
from config import HISTORICAL_DATA_DIR, SCRIPTS_DIR

# Конфигурация
INPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['stocks'], "moex_currency_pairs_list.csv")
OUTPUT_DIR = HISTORICAL_DATA_DIR['currency']
START_DATE = "2023-01-01"
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt"
ENGINE = "currency"
REQUEST_DELAY = 1.0

def load_currency_pairs(filename):
    """Загружает список валютных пар из CSV."""
    try:
        return pd.read_csv(filename)[['SECID', 'BOARDID']]
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return pd.DataFrame()

def get_currency_history(secid, boardid):
    """Получает исторические данные для одной валютной пары."""
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}.json"
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
        required_cols = ['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLRUR']
        if all(col in df.columns for col in required_cols):
            df = df.rename(columns={'VOLRUR': 'VOLUME'})
            return df[required_cols]
        return None

    except Exception as e:
        print(f"Ошибка для пары {secid} ({boardid}): {e}")
        return None

def save_history(df, secid):
    """Сохраняет историю валютной пары в CSV."""
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
    print("=== Сбор исторических данных валютных пар ===")
    pairs_df = load_currency_pairs(INPUT_FILE)
    if pairs_df.empty:
        print("Не удалось загрузить список валютных пар.")
        return

    total = len(pairs_df)
    success = 0
    for i, (_, row) in enumerate(pairs_df.iterrows(), 1):
        secid, boardid = row['SECID'], row['BOARDID']
        print(f"[{i}/{total}] Обработка пары {secid} ({boardid})...")

        data = get_currency_history(secid, boardid)
        if save_history(data, secid):
            success += 1
        time.sleep(REQUEST_DELAY)

    print(f"\nГотово. Успешно обработано {success}/{total} валютных пар.")

if __name__ == "__main__":
    main()
