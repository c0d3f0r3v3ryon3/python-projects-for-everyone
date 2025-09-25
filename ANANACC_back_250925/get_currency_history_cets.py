import pandas as pd
import requests
import time
import os
from datetime import datetime

# --- Конфигурация ---
INPUT_CSV_FILE = "moex_currency_pairs_list.csv" # Входной файл со списком пар и BOARDID
FILTER_BOARDID = "CETS" # Используем только CETS
OUTPUT_DIR = "historical_data_currency" # Сохраняем в ту же директорию
START_DATE = "2023-01-01" # Используем ту же дату, что и для акций и индексов
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt" # Рынок Selt (валютный)
ENGINE = "currency"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
    # Используем endpoint для истории
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_filtered_currency_tickers_from_csv(filename, filter_boardid):
    """Загружает список валютных пар из CSV файла, фильтруя по BOARDID."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        print(f"Загружено {len(df)} записей из {filename}")
        # Фильтруем по BOARDID
        filtered_df = df[df['BOARDID'] == filter_boardid]
        print(f"После фильтрации по BOARDID='{filter_boardid}': {len(filtered_df)} записей")
        return filtered_df
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
    """Сохраняет исторические данные валютной пары в CSV файл, адаптируя столбцы."""
    if not data or 'history' not in data or not data['history']['data']:
        print(f"    Нет исторических данных для валютной пары {secid}, файл не создан.")
        return

    os.makedirs(output_dir, exist_ok=True)

    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    print(f"    Получено {len(df)} строк истории для {secid}. Столбцы: {df.columns.tolist()}")

    # Столбцы, возвращаемые API для валют (на CETS): ['BOARDID', 'TRADEDATE', 'SHORTNAME', 'SECID', 'OPEN', 'LOW', 'HIGH', 'CLOSE', 'NUMTRADES', 'VOLRUR', 'WAPRICE']
    # Нам нужны: TRADEDATE, OPEN, HIGH, LOW, CLOSE, VALUE, VOLUME
    # VOLRUR -> VALUE (объем в рублях)
    # NUMTRADES != VOLUME (кол-во сделок), VOLUME отсутствует. Будем использовать 0 или NUMTRADES как приближение.
    # Если NUMTRADES тоже отсутствует, заполним 0.

    required_input_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VOLRUR']
    if all(col in df.columns for col in required_input_cols):
        # Переименовываем и выбираем нужные столбцы
        df_renamed = df[['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLRUR']].copy()
        df_renamed = df_renamed.rename(columns={'VOLRUR': 'VALUE'}) # VOLRUR -> VALUE

        # Создаем столбец VOLUME
        if 'NUMTRADES' in df.columns:
            df_renamed['VOLUME'] = df['NUMTRADES']
        else:
            df_renamed['VOLUME'] = 0
            print(f"    Внимание: NUMTRADES не найден для {secid}, VOLUME заполнен 0.")

        # Убираем лишние столбцы, если они есть, оставляем только нужные
        df_final = df_renamed[['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VALUE', 'VOLUME']]

        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df_final.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"    История для валютной пары {secid} (адаптирована) сохранена в {filename}")
        except IOError as e:
            print(f"    Ошибка при сохранении файла для валютной пары {secid}: {e}")
    else:
        print(f"    Некорректные столбцы в данных для валютной пары {secid}: {df.columns.tolist()}. Пропущено.")

def main():
    """Основная функция."""
    print(f"Начинаю сбор исторических данных по валютным парам (BOARDID={FILTER_BOARDID})...")
    tickers_df = load_filtered_currency_tickers_from_csv(INPUT_CSV_FILE, FILTER_BOARDID)
    if tickers_df.empty:
        print("Не удалось загрузить список валютных пар для указанного BOARDID. Завершение.")
        return

    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        print(f"Файл {INPUT_CSV_FILE} не содержит колонок 'SECID' и 'BOARDID'. Завершение.")
        return

    total_pairs = len(tickers_df)
    print(f"Начинаю обработку {total_pairs} валютных пар...")

    for index, row in tickers_df.iterrows():
        secid = row['SECID']
        boardid = row['BOARDID'] # Будет всегда FILTER_BOARDID=CETS
        print(f"Обработка {index + 1}/{total_pairs}: {secid} ({boardid})")
        data = get_currency_history(secid, boardid)
        if data: # Сохраняем только если данные успешно получены
            save_currency_history_to_csv(data, secid, OUTPUT_DIR)
        # Задержка между запросами
        time.sleep(REQUEST_DELAY)

    print("Сбор исторических данных по валютным парам завершен.")

if __name__ == "__main__":
    main()
