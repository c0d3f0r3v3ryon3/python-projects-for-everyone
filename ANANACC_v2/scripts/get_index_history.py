import pandas as pd
import requests
import time
import os
from datetime import datetime

# --- Конфигурация ---
INPUT_CSV_FILE = "moex_indices_list.csv"
OUTPUT_DIR = "historical_data_indices"
START_DATE = "2023-01-01" # Используем ту же дату, что и для акций
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "index" # Рынок индексов
ENGINE = "stock"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
    # Попробуем получить историю через /history/engines/.../markets/.../securities/[SECID]
    # Проверим сначала, какие столбцы возвращает API для истории индекса.
    # Предполагаемые столбцы: TRADEDATE, OPEN, CLOSE, HIGH, LOW, WAPRICE, VALUE, VOLUME
}
# Увеличиваем задержку и таймаут для стабильности
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_index_tickers_from_csv(filename):
    """Загружает список индексов из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        print(f"Загружено {len(df)} индексов из {filename}")
        return df
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return pd.DataFrame()

def get_index_history(secid):
    """Получает исторические данные для одного индекса с рынка индексов."""
    # Используем endpoint для истории без BOARDID, как в примере из Pasted_Text_1758710699004.txt
    # https://iss.moex.com/iss/history/engines/stock/markets/index/securities/[SECID].json
    # Пример из справки: https://iss.moex.com/iss/history/engines/stock/markets/index/securities.xml?date=2010-11-22
    # Но мы хотим историю с 'from' и до текущей даты.
    # Попробуем сначала /history/engines/.../markets/.../securities/[SECID].json
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/securities/{secid}.json"
    print(f"  Запрашиваю историю для индекса {secid} с {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        print(f"    Таймаут при запросе истории для индекса {secid}. Пропускаю.")
        return None
    except requests.exceptions.ConnectionError as e: # Обработка ConnectionError, включая NewConnectionError
        print(f"    Ошибка подключения при запросе истории для индекса {secid}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        if isinstance(e, KeyboardInterrupt):
            print(f"\n    Запрос прерван пользователем (Ctrl+C) для индекса {secid}.")
            raise
        print(f"    Ошибка при запросе истории для индекса {secid}: {e}")
        return None
    except ValueError as e: # Ошибка при парсинге JSON
        print(f"    Ошибка при парсинге JSON ответа для индекса {secid}: {e}")
        return None

def save_index_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные индекса в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        print(f"    Нет исторических данных для индекса {secid}, файл не создан.")
        return

    # Создаем директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)

    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    print(f"    Получено {len(df)} строк истории для {secid}. Столбцы: {df.columns.tolist()}")

    # Основные ожидаемые столбцы для индекса из истории: TRADEDATE, OPEN, CLOSE, HIGH, LOW
    # Также могут быть: WAPRICE, VALUE, VOLUME
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW']
    # Проверим, есть ли все нужные столбцы
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"    История для индекса {secid} сохранена в {filename}")
        except IOError as e:
            print(f"    Ошибка при сохранении файла для индекса {secid}: {e}")
    else:
        print(f"    Некорректные столбцы в данных для индекса {secid}: {df.columns.tolist()}. Пропущено.")

def main():
    """Основная функция."""
    print("Начинаю сбор исторических данных по индексам...")
    tickers_df = load_index_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        print("Не удалось загрузить список индексов. Завершение.")
        return

    # Убедимся, что в DataFrame есть нужные колонки
    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        print(f"Файл {INPUT_CSV_FILE} не содержит колонок 'SECID' и 'BOARDID'. Завершение.")
        return

    total_indices = len(tickers_df)
    print(f"Начинаю обработку {total_indices} индексов...")

    for index, row in tickers_df.iterrows():
        secid = row['SECID']
        # boardid = row['BOARDID'] # Больше не используем BOARDID в URL
        print(f"Обработка {index + 1}/{total_indices}: {secid}")
        data = get_index_history(secid)
        if data: # Сохраняем только если данные успешно получены
            save_index_history_to_csv(data, secid, OUTPUT_DIR)
        # Задержка между запросами
        time.sleep(REQUEST_DELAY)

    print("Сбор исторических данных по индексам завершен.")

if __name__ == "__main__":
    main()
