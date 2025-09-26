# scripts/data_collection/get_moex_stocks.py
import requests
import pandas as pd
import os
from config import HISTORICAL_DATA_DIR, SCRIPTS_DIR

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "shares"
ENGINE = "stock"
OUTPUT_FILE = os.path.join(HISTORICAL_DATA_DIR['stocks'], "moex_stocks_liquid_boards.csv")

def get_all_securities():
    """Получает список всех акций с MOEX."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    params = {
        "iss.meta": "off",
        "iss.only": "securities,marketdata",
        "securities.columns": "SECID,BOARDID,SHORTNAME,INSTRID,MARKETCODE",
        "marketdata.columns": "SECID,BOARDID,VALTODAY"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка запроса к MOEX: {e}")
        return None

def process_securities(data):
    """Обрабатывает данные и возвращает ликвидные акции."""
    if not data or 'securities' not in data or 'marketdata' not in data:
        return pd.DataFrame()

    securities_df = pd.DataFrame(
        data['securities']['data'],
        columns=data['securities']['columns']
    )
    marketdata_df = pd.DataFrame(
        data['marketdata']['data'],
        columns=data['marketdata']['columns']
    )

    # Фильтрация обыкновенных акций (MARKETCODE='FNDT', INSTRID начинается с 'EQ')
    securities_df = securities_df[
        (securities_df['MARKETCODE'] == 'FNDT') &
        (securities_df['INSTRID'].str.startswith('EQ', na=False))
    ].dropna(subset=['SECID', 'BOARDID'])

    # Объединение с рыночными данными и выбор самого ликвидного режима
    merged_df = securities_df.merge(
        marketdata_df.dropna(subset=['VALTODAY']),
        on=['SECID', 'BOARDID'],
        how='inner'
    ).sort_values('VALTODAY', ascending=False)

    # Выбор самого ликвидного режима для каждой акции
    liquid_stocks = merged_df.groupby('SECID').first().reset_index()
    return liquid_stocks[['SECID', 'BOARDID', 'SHORTNAME']].rename(columns={'SHORTNAME': 'NAME'})

def save_to_csv(df, filename):
    """Сохраняет DataFrame в CSV."""
    if df.empty:
        print("Нет данных для сохранения.")
        return False
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Список акций сохранен в {filename}")
        return True
    except Exception as e:
        print(f"Ошибка сохранения: {e}")
        return False

def main():
    print("=== Получение списка акций с MOEX ===")
    data = get_all_securities()
    if not data:
        print("Не удалось получить данные.")
        return

    liquid_stocks = process_securities(data)
    if liquid_stocks.empty:
        print("Не найдено ликвидных акций.")
        return

    if save_to_csv(liquid_stocks, OUTPUT_FILE):
        print("Успешно завершено.")
    else:
        print("Ошибка сохранения.")

if __name__ == "__main__":
    main()
