import pandas as pd
import requests
import time
import os
from datetime import datetime

# --- Конфигурация ---
INPUT_CSV_FILE = "moex_stocks_liquid_boards.csv"
OUTPUT_DIR = "historical_data_full"
START_DATE = "2023-01-01"
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "shares"
ENGINE = "stock"
REQUEST_PARAMS = {
    "from": START_DATE,
    "interval": 24,
    "iss.meta": "off",
    "iss.only": "candles",
    "candles.columns": "begin,end,open,high,low,close,volume"
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45
# MAX_RETRIES для основного цикла не нужен, но можно добавить для внутреннего цикла
MAX_CONNECTION_RETRY_ATTEMPTS = 5 # Максимальное количество попыток для тикеров с ошибками соединения

def load_tickers_from_csv(filename):
    """Загружает список тикеров из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        print(f"Загружено {len(df)} тикеров из {filename}")
        return df
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return pd.DataFrame()

def get_historical_data_for_ticker(secid, boardid):
    """Получает исторические данные для одного тикера с указанного режима."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}/candles.json"
    # print(f"  Запрашиваю историю для {secid} ({boardid}) с {url}") # Закомментируем для краткости лога при большом количестве
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        print(f"    Таймаут при запросе истории для {secid} ({boardid}).")
        return 'CONNECTION_ERROR' # Возвращаем специальный маркер
    except requests.exceptions.ConnectionError as e: # Обработка ConnectionError, включая NewConnectionError
        print(f"    Ошибка подключения при запросе истории для {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR' # Возвращаем специальный маркер
    except requests.exceptions.RequestException as e:
        if isinstance(e, KeyboardInterrupt):
            print(f"\n    Запрос прерван пользователем (Ctrl+C) для {secid} ({boardid}).")
            raise # Передаем исключение наверх
        print(f"    Ошибка при запросе истории для {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR' # Считаем любую другую RequestException ошибкой соединения
    except ValueError as e: # Ошибка при парсинге JSON
        print(f"    Ошибка при парсинге JSON ответа для {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR' # Считаем ошибкой соединения, если JSON сломан

def save_historical_data_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные в CSV файл для конкретного тикера."""
    # Проверяем, был ли возвращен специальный маркер ошибки
    if data == 'CONNECTION_ERROR':
        return False, 'CONNECTION_ERROR' # Возвращаем False и маркер ошибки

    if not data or 'candles' not in data or not data['candles']['data']:
        print(f"    Нет исторических данных для {secid}, файл не создан.")
        return False, 'NO_DATA' # Возвращаем False и маркер отсутствия данных

    # Создаем директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)

    df = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
    # print(f"    Отладка: Столбцы до обработки для {secid}: {df.columns.tolist()}") # Для отладки

    # Преобразуем 'begin' или 'end' в формат даты и переименуем в 'TRADEDATE'
    if 'begin' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['begin']).dt.date
        df = df.drop(columns=['begin'])
    elif 'end' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['end']).dt.date
        df = df.drop(columns=['end'])
    else:
        print(f"    Ошибка: Ни 'begin', ни 'end' не найдены в данных для {secid}. Пропускаю.")
        return False, 'PARSE_ERROR' # Возвращаем False и маркер ошибки парсинга

    # Переименуем остальные столбцы
    expected_col_mapping = {'open': 'OPEN', 'high': 'HIGH', 'low': 'LOW', 'close': 'CLOSE', 'volume': 'VOLUME'}
    missing_cols = [col for col in expected_col_mapping.keys() if col not in df.columns]
    if missing_cols:
        print(f"    Некорректные столбцы в данных для {secid}: {df.columns.tolist()}. Отсутствуют: {missing_cols}. Пропущено.")
        return False, 'PARSE_ERROR' # Возвращаем False и маркер ошибки парсинга

    df = df.rename(columns=expected_col_mapping)

    required_cols = ['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"    История для {secid} сохранена в {filename} ({len(df)} строк)")
            return True, 'SUCCESS' # Возвращаем True и маркер успеха
        except IOError as e:
            print(f"    Ошибка при сохранении файла для {secid}: {e}")
            return False, 'SAVE_ERROR' # Возвращаем False и маркер ошибки сохранения
    else:
        print(f"    Некорректные столбцы в данных для {secid} после обработки: {df.columns.tolist()}. Пропущено.")
        return False, 'PARSE_ERROR' # Возвращаем False и маркер ошибки парсинга


def main():
    """Основная функция."""
    print("Начинаю сбор исторических данных (полный список, циклически только ошибки соединения)...")
    tickers_df = load_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        print("Не удалось загрузить список тикеров. Завершение.")
        return

    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        print(f"Файл {INPUT_CSV_FILE} не содержит колонок 'SECID' и 'BOARDID'. Завершение.")
        return

    total_tickers = len(tickers_df)
    print(f"Начинаю обработку {total_tickers} тикеров...")

    # Инициализируем список тикеров для обработки
    remaining_tickers_df = tickers_df.copy()

    # --- Первый основной проход ---
    print(f"\n--- Основной проход ---")
    failed_connection_tickers = [] # Список тикеров с ошибками соединения
    failed_other_tickers = []      # Список тикеров с другими ошибками (нет данных и т.д.)

    for index, row in remaining_tickers_df.iterrows():
        secid = row['SECID']
        boardid = row['BOARDID']
        print(f"Обработка: {secid} ({boardid})")
        try:
            data = get_historical_data_for_ticker(secid, boardid)
            success, status = save_historical_data_to_csv(data, secid, OUTPUT_DIR)
            if success:
                print(f"    Успешно обработан: {secid}")
            else:
                if status == 'CONNECTION_ERROR':
                    print(f"    Ошибка соединения для {secid}, добавлен в список повторных попыток.")
                    failed_connection_tickers.append({'SECID': secid, 'BOARDID': boardid})
                else: # NO_DATA, PARSE_ERROR, SAVE_ERROR
                    print(f"    Окончательная ошибка для {secid} (причина: {status}), добавлен в список окончательно неудачных.")
                    failed_other_tickers.append({'SECID': secid, 'BOARDID': boardid})
        except KeyboardInterrupt:
            print(f"\nОбработка прервана пользователем на тикере {secid}.")
            # Сохраняем промежуточные результаты
            if failed_connection_tickers:
                pd.DataFrame(failed_connection_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_connection_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
            if failed_other_tickers:
                pd.DataFrame(failed_other_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_other_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
            return # Выходим из функции main

    print(f"Основной проход завершен.")
    print(f"  Успешно обработано: {total_tickers - len(failed_connection_tickers) - len(failed_other_tickers)}")
    print(f"  Ошибки соединения: {len(failed_connection_tickers)}")
    print(f"  Окончательные ошибки (нет данных и др.): {len(failed_other_tickers)}")

    # --- Циклическая обработка ошибок соединения ---
    connection_retry_df = pd.DataFrame(failed_connection_tickers)
    attempt = 1
    max_attempts = MAX_CONNECTION_RETRY_ATTEMPTS

    while not connection_retry_df.empty and attempt <= max_attempts:
        print(f"\n--- Повторная попытка соединения - Проход {attempt} ---")
        print(f"Осталось обработать {len(connection_retry_df)} тикеров с ошибками соединения.")
        next_failed_connection_tickers = [] # Список для следующей итерации

        for _, row in connection_retry_df.iterrows():
            secid = row['SECID']
            boardid = row['BOARDID']
            print(f"Повторная попытка для: {secid} ({boardid})")
            try:
                data = get_historical_data_for_ticker(secid, boardid)
                success, status = save_historical_data_to_csv(data, secid, OUTPUT_DIR)
                if success:
                    print(f"    Успешно обработан: {secid}")
                    # Не добавляем в список повторных попыток
                else:
                    if status == 'CONNECTION_ERROR':
                        print(f"    Ошибка соединения для {secid}, остается в списке повторных попыток.")
                        next_failed_connection_tickers.append({'SECID': secid, 'BOARDID': boardid})
                    else: # NO_DATA, PARSE_ERROR, SAVE_ERROR
                        print(f"    Окончательная ошибка для {secid} (причина: {status}), переносится в окончательно неудачные.")
                        failed_other_tickers.append({'SECID': secid, 'BOARDID': boardid}) # Добавляем в список окончательных ошибок
            except KeyboardInterrupt:
                print(f"\nОбработка прервана пользователем на тикере {secid}.")
                # Сохраняем промежуточные результаты
                if next_failed_connection_tickers:
                    pd.DataFrame(next_failed_connection_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_connection_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
                if failed_other_tickers:
                    pd.DataFrame(failed_other_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_other_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
                return # Выходим из функции main

        connection_retry_df = pd.DataFrame(next_failed_connection_tickers)
        attempt += 1
        if not connection_retry_df.empty and attempt <= max_attempts:
            print(f"После прохода {attempt - 1}, осталось {len(connection_retry_df)} тикеров с ошибками соединения.")
            print(f"Ждем перед следующим проходом... ({REQUEST_DELAY} секунд)")
            time.sleep(REQUEST_DELAY)

    # --- Вывод итогов ---
    final_success_count = total_tickers - len(connection_retry_df) - len(failed_other_tickers)
    print(f"\n--- Итоги ---")
    print(f"Все тикеры обработаны (или достигнут лимит попыток).")
    print(f"  Всего тикеров: {total_tickers}")
    print(f"  Успешно обработано: {final_success_count}")
    print(f"  Ошибки соединения (не устранены за {max_attempts} попыток): {len(connection_retry_df)}")
    print(f"  Окончательные ошибки (нет данных и др.): {len(failed_other_tickers)}")

    if not connection_retry_df.empty:
        print(f"  Не удалось обработать следующие тикеры из-за повторяющихся ошибок соединения:")
        print(connection_retry_df)
        # Сохраняем список неудачных тикеров (ошибки соединения) в файл
        failed_con_file = os.path.join(OUTPUT_DIR, "failed_connection_tickers_final.csv")
        connection_retry_df.to_csv(failed_con_file, index=False, encoding='utf-8-sig')
        print(f"Список неудачных тикеров (ошибки соединения) сохранен в {failed_con_file}")

    if failed_other_tickers:
        failed_other_file = os.path.join(OUTPUT_DIR, "failed_other_tickers_final.csv")
        pd.DataFrame(failed_other_tickers).to_csv(failed_other_file, index=False, encoding='utf-8-sig')
        print(f"Список тикеров с окончательными ошибками (нет данных и др.) сохранен в {failed_other_file}")

    print("Сбор исторических данных (полный список) завершен (или прерван).")

if __name__ == "__main__":
    main()
