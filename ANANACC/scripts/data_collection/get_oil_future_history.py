# scripts/data_collection/get_oil_future_history.py
import pandas as pd
import requests
import time
import os
from config import HISTORICAL_DATA_DIR, SCRIPTS_DIR

# Конфигурация
INPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['stocks'], "current_oil_future_contract.txt")
OUTPUT_DIR = HISTORICAL_DATA_DIR['oil']
START_DATE = "2023-01-01"
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "forts"
ENGINE = "futures"
BOARDID = "RFUD"  # Режим торгов для фьючерсов на нефть
REQUEST_DELAY = 1.0

def load_current_contract(filename):
    """Загружает текущий контракт из файла."""
    try:
        with open(filename, 'r') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return None

def get_oil_history(secid):
    """Получает исторические данные для фьючерса на нефть."""
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{BOARDID}/securities/{secid}.json"
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
        required_cols = ['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
        if all(col in df.columns for col in required_cols):
            return df[required_cols]
        return None

    except Exception as e:
        print(f"Ошибка для фьючерса {secid}: {e}")
        return None

def save_history(df, secid):
    """Сохраняет историю фьючерса в CSV."""
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
    print("=== Сбор исторических данных фьючерсов на нефть ===")
    secid = load_current_contract(INPUT_FILE)
    if not secid:
        print("Не удалось загрузить текущий контракт.")
        return

    print(f"Обработка фьючерса {secid}...")
    data = get_oil_history(secid)
    if save_history(data, secid):
        print("Готово. История фьючерса сохранена.")
    else:
        print("Ошибка сохранения.")

if __name__ == "__main__":
    main()
