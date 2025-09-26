import requests
import pandas as pd
import time

# --- Конфигурация ---
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "shares"
ENGINE = "stock"
# Параметры для запроса, чтобы получить данные marketdata
REQUEST_PARAMS = {
    "iss.meta": "off",  # Отключить метаданные ISS, чтобы упростить парсинг
    "iss.only": "securities,marketdata", # Запрашивать только нужные таблицы
    "securities.columns": "SECID,BOARDID,SHORTNAME,INSTRID,MARKETCODE",
    "marketdata.columns": "SECID,BOARDID,VALTODAY" # Используем VALTODAY как индикатор ликвидности
}
CSV_OUTPUT_FILE = "moex_stocks_liquid_boards.csv"

def get_all_securities_with_marketdata():
    """Получает данные о всех инструментах и рыночной информации с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    print(f"Запрашиваю данные с {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS)
        response.raise_for_status() # Проверить на HTTP ошибки
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к MOEX API: {e}")
        return None
    except ValueError as e: # Ошибка при парсинге JSON
        print(f"Ошибка при парсинге JSON ответа: {e}")
        return None

def process_data_to_liquid_stocks_list(data):
    """Обрабатывает полученные данные, фильтрует акции и находит самый ликвидный режим."""
    if not data or 'securities' not in data or 'marketdata' not in data:
        print("Ошибка: Полученные данные не содержат ожидаемых таблиц 'securities' или 'marketdata'.")
        return pd.DataFrame()

    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    marketdata_df = pd.DataFrame(data['marketdata']['data'], columns=data['marketdata']['columns'])

    print(f"Всего инструментов в 'securities': {len(securities_df)}")
    print(f"Всего записей в 'marketdata': {len(marketdata_df)}")

    # 1. Фильтрация: оставить только инструменты фондового рынка (MARKETCODE == 'FNDT') и тип INSTRID, начинающийся на 'EQ'
    # Убираем строки, где INSTRID или MARKETCODE NaN
    securities_df = securities_df.dropna(subset=['INSTRID', 'MARKETCODE'])
    # Фильтр: MARKETCODE == 'FNDT' И INSTRID начинается с 'EQ'
    equity_stocks_df = securities_df[
        (securities_df['MARKETCODE'] == 'FNDT') &
        (securities_df['INSTRID'].str.startswith('EQ', na=False)) # na=False: NaN значения дают False
    ]

    print(f"После фильтрации по MARKETCODE='FNDT' и INSTRID.startswith('EQ'): {len(equity_stocks_df)}")

    if equity_stocks_df.empty:
        print("После фильтрации не найдено обыкновенных акций (MARKETCODE='FNDT', INSTRID начинается с 'EQ').")
        # Попробуем вывести уникальные INSTRID и MARKETCODE для диагностики
        print("Уникальные значения INSTRID и MARKETCODE в исходных данных:")
        print(securities_df[['INSTRID', 'MARKETCODE']].drop_duplicates())
        return pd.DataFrame()

    # 2. Объединение с marketdata по SECID и BOARDID
    # Убираем строки marketdata, где VALTODAY NaN (нет торгов)
    marketdata_df = marketdata_df.dropna(subset=['VALTODAY'])
    merged_df = equity_stocks_df[['SECID', 'BOARDID', 'SHORTNAME']].merge(
        marketdata_df[['SECID', 'BOARDID', 'VALTODAY']], on=['SECID', 'BOARDID'], how='inner'
    )

    print(f"После объединения с marketdata и фильтрации по VALTODAY: {len(merged_df)}")

    if merged_df.empty:
        print("После объединения с рыночными данными и фильтрации по VALTODAY не осталось данных.")
        return pd.DataFrame()

    # 3. Найти самый ликвидный режим для каждой акции (SECID)
    # Сортируем по VALTODAY (по убыванию) и берем первую строку для каждого SECID
    merged_df = merged_df.sort_values(by=['SECID', 'VALTODAY'], ascending=[True, False])
    liquid_stocks_df = merged_df.groupby('SECID').first().reset_index()

    # 4. Выбираем нужные колонки
    final_df = liquid_stocks_df[['SECID', 'BOARDID', 'SHORTNAME']].copy()
    final_df.rename(columns={'SHORTNAME': 'NAME'}, inplace=True)

    print(f"Найдено {len(final_df)} обыкновенных акций с самым ликвидным режимом.")
    return final_df

def save_to_csv(df, filename):
    """Сохраняет DataFrame в CSV файл."""
    if df.empty:
        print("DataFrame пуст, файл не будет создан.")
        return
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig') # utf-8-sig для корректного отображения в Excel
        print(f"Список акций успешно сохранен в {filename}")
    except IOError as e:
        print(f"Ошибка при сохранении файла: {e}")

def main():
    """Основная функция."""
    print("Начинаю сбор списка обыкновенных акций с MOEX...")
    data = get_all_securities_with_marketdata()
    if data:
        print("Данные успешно получены. Обрабатываю...")
        liquid_stocks_df = process_data_to_liquid_stocks_list(data)
        print("Обработка завершена. Сохраняю результат...")
        save_to_csv(liquid_stocks_df, CSV_OUTPUT_FILE)
    else:
        print("Не удалось получить данные с MOEX API.")

if __name__ == "__main__":
    main()
