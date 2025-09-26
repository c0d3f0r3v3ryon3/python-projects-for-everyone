# scripts/data_collection/get_historical_data.py
import pandas as pd
import requests
import time
import os
from config import HISTORICAL_DATA_DIR, SCRIPTS_DIR

INPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['stocks'], "moex_stocks_liquid_boards.csv")
OUTPUT_DIR = HISTORICAL_DATA_DIR['stocks']
START_DATE = "2023-01-01"
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "shares"
ENGINE = "stock"
REQUEST_DELAY = 1.0  # Задержка между запросами (секунды)

def load_tickers(filename):
    """Загружает список тикеров из CSV."""
    try:
        return pd.read_csv(filename)[['SECID', 'BOARDID']]
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return pd.DataFrame()

def get_historical_data(secid, boardid):
    """Получает исторические данные для одного тикера."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}/candles.json"
    params = {
        "from": START_DATE,
        "interval": 24,
        "iss.meta": "off",
        "iss.only": "candles",
        "candles.columns": "begin,open,high,low,close,volume"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if 'candles' not in data or not data['candles']['data']:
            return None

        df = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
        df['TRADEDATE'] = pd.to_datetime(df['begin']).dt.date
        df = df.rename(columns={
            'open': 'OPEN', 'high': 'HIGH', 'low': 'LOW',
            'close': 'CLOSE', 'volume': 'VOLUME'
        })[['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']]
        return df

    except Exception as e:
        print(f"Ошибка для {secid} ({boardid}): {e}")
        return None

def save_history(df, secid):
    """Сохраняет историю в CSV."""
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
    print("=== Сбор исторических данных акций ===")
    tickers_df = load_tickers(INPUT_FILE)
    if tickers_df.empty:
        print("Не удалось загрузить список тикеров.")
        return

    total = len(tickers_df)
    success = 0
    for i, (_, row) in enumerate(tickers_df.iterrows(), 1):
        secid, boardid = row['SECID'], row['BOARDID']
        print(f"[{i}/{total}] Обработка {secid} ({boardid})...")

        data = get_historical_data(secid, boardid)
        if save_history(data, secid):
            success += 1
        time.sleep(REQUEST_DELAY)

    print(f"\nГотово. Успешно обработано {success}/{total} тикеров.")

if __name__ == "__main__":
    main()
