import pandas as pd
import requests
import time
import os
from datetime import datetime

# --- Конфигурация ---
INPUT_CSV_FILE = "moex_currency_pairs_list.csv"
OUTPUT_DIR = "historical_data_currency"
START_DATE = "2023-01-01" # Используем ту же дату, что и для акций и индексов
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt" # Рынок Selt (валютный)
ENGINE = "currency"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
    # Попробуем получить историю через /history/engines/.../markets/.../boards/.../securities/[SECID]
    # Предполагаемые столбцы: TRADEDATE, OPEN, CLOSE, HIGH, LOW, VOLRUR (объем в рублях)
}
# Увеличиваем задержку и таймаут для стабильности
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_currency_tickers_from_csv(filename):
    """Загружает список валютных пар из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        print(f"Загружено {len(df)} валютных пар из {filename}")
        return df
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return pd.DataFrame()

def get_currency_history(secid, boardid):
    """Получает исторические данные для одной валютной пары с указанного режима."""
    # Используем endpoint для истории с указанием BOARDID
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}.json"
    print(f"  Запрашиваю историю для валютной пары {secid} ({boardid}) с {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        print(f"    Таймаут при запросе истории для валютной пары {secid} ({boardid}). Пропускаю.")
        return None
    except requests.exceptions.ConnectionError as e: # Обработка ConnectionError, включая NewConnectionError
        print(f"    Ошибка подключения при запросе истории для валютной пары {secid} ({boardid}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        if isinstance(e, KeyboardInterrupt):
            print(f"\n    Запрос прерван пользователем (Ctrl+C) для валютной пары {secid} ({boardid}).")
            raise
        print(f"    Ошибка при запросе истории для валютной пары {secid} ({boardid}): {e}")
        return None
    except ValueError as e: # Ошибка при парсинге JSON
        print(f"    Ошибка при парсинге JSON ответа для валютной пары {secid} ({boardid}): {e}")
        return None

def save_currency_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные валютной пары в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        print(f"    Нет исторических данных для валютной пары {secid}, файл не создан.")
        return

    # Создаем директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)

    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    print(f"    Получено {len(df)} строк истории для {secid}. Столбцы: {df.columns.tolist()}")

    # Основные ожидаемые столбцы для валютной пары из истории: TRADEDATE, OPEN, CLOSE, HIGH, LOW, VOLRUR
    # VOLRUR - объем в рублях, соответствует VOLUME
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VOLRUR']
    # Проверим, есть ли все нужные столбцы
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        # Переименуем VOLRUR в VOLUME для единообразия с другими данными
        df = df.rename(columns={'VOLRUR': 'VOLUME'})
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"    История для валютной пары {secid} сохранена в {filename}")
        except IOError as e:
            print(f"    Ошибка при сохранении файла для валютной пары {secid}: {e}")
    else:
        print(f"    Некорректные столбцы в данных для валютной пары {secid}: {df.columns.tolist()}. Пропущено.")

def main():
    """Основная функция."""
    print("Начинаю сбор исторических данных по валютным парам...")
    tickers_df = load_currency_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        print("Не удалось загрузить список валютных пар. Завершение.")
        return

    # Убедимся, что в DataFrame есть нужные колонки
    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        print(f"Файл {INPUT_CSV_FILE} не содержит колонок 'SECID' и 'BOARDID'. Завершение.")
        return

    total_pairs = len(tickers_df)
    print(f"Начинаю обработку {total_pairs} валютных пар...")

    for index, row in tickers_df.iterrows():
        secid = row['SECID']
        boardid = row['BOARDID']
        print(f"Обработка {index + 1}/{total_pairs}: {secid} ({boardid})")
        data = get_currency_history(secid, boardid)
        if data: # Сохраняем только если данные успешно получены
            save_currency_history_to_csv(data, secid, OUTPUT_DIR)
        # Задержка между запросами
        time.sleep(REQUEST_DELAY)

    print("Сбор исторических данных по валютным парам завершен.")

if __name__ == "__main__":
    main()
