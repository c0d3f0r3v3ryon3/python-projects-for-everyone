import pandas as pd
import requests
import time
import os

# --- Конфигурация ---
INPUT_CONTRACT_FILE = "current_oil_future_contract.txt"
OUTPUT_DIR = "historical_data_oil"
START_DATE = "2023-01-01" # Используем ту же дату, что и для других активов
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "forts" # Рынок срочной торговли
ENGINE = "futures" # Торговая система срочного рынка
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
    # Используем правильный endpoint для истории: /history/engines/.../markets/.../boards/.../securities/[SECID]
    # Предполагаемые столбцы: TRADEDATE, OPEN, CLOSE, HIGH, LOW, VALUE, VOLUME
    # Проверим сначала, какие столбцы возвращает API для истории фьючерса.
}
# Увеличиваем задержку и таймаут для стабильности
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_current_contract_from_file(filename):
    """Загружает тикер текущего фьючерсного контракта из файла."""
    try:
        with open(filename, 'r') as f:
            secid = f.read().strip()
        print(f"Загружен тикер фьючерсного контракта: {secid}")
        return secid
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return None
    except Exception as e:
        print(f"Ошибка при чтении файла {filename}: {e}")
        return None

def get_oil_future_history(secid):
    """Получает исторические данные для фьючерсного контракта с указанного режима."""
    # Используем endpoint для истории с указанием BOARDID, как для акций/валют
    # Ищем BOARDID для BRV5 в предыдущем ответе или устанавливаем по умолчанию
    # Из предыдущего запроса к /securities/ мы знаем, что BOARDID для BRV5 - RFUD
    boardid = "RFUD" # Устанавливаем вручную, так как он известен из спецификации
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}.json"
    print(f"  Запрашиваю историю для фьючерса {secid} ({boardid}) с {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        print(f"    Таймаут при запросе истории для фьючерса {secid} ({boardid}). Пропускаю.")
        return None
    except requests.exceptions.ConnectionError as e: # Обработка ConnectionError, включая NewConnectionError
        print(f"    Ошибка подключения при запросе истории для фьючерса {secid} ({boardid}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        if isinstance(e, KeyboardInterrupt):
            print(f"\n    Запрос прерван пользователем (Ctrl+C) для фьючерса {secid} ({boardid}).")
            raise
        print(f"    Ошибка при запросе истории для фьючерса {secid} ({boardid}): {e}")
        return None
    except ValueError as e: # Ошибка при парсинге JSON
        print(f"    Ошибка при парсинге JSON ответа для фьючерса {secid} ({boardid}): {e}")
        return None

def save_oil_future_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные фьючерса в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        print(f"    Нет исторических данных для фьючерса {secid}, файл не создан.")
        return

    # Создаем директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)

    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    print(f"    Получено {len(df)} строк истории для {secid}. Столбцы: {df.columns.tolist()}")

    # Основные ожидаемые столбцы для фьючерса из истории: TRADEDATE, OPEN, CLOSE, HIGH, LOW, VALUE, VOLUME
    # Также могут быть: WAPRICE (средневзвешенная цена), SETTLEPRICE (цена расчета), и др.
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VALUE', 'VOLUME']
    # Проверим, есть ли все нужные столбцы
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"    История для фьючерса {secid} сохранена в {filename}")
        except IOError as e:
            print(f"    Ошибка при сохранении файла для фьючерса {secid}: {e}")
    else:
        print(f"    Некорректные столбцы в данных для фьючерса {secid}: {df.columns.tolist()}. Пропущено.")

def main():
    """Основная функция."""
    print("Начинаю сбор исторических данных по фьючерсу на нефть...")
    secid = load_current_contract_from_file(INPUT_CONTRACT_FILE)
    if secid is None:
        print("Не удалось загрузить тикер фьючерсного контракта. Завершение.")
        return

    data = get_oil_future_history(secid)
    if data: # Сохраняем только если данные успешно получены
        save_oil_future_history_to_csv(data, secid, OUTPUT_DIR)
    else:
        print(f"Не удалось получить исторические данные для фьючерса {secid}.")

    print("Сбор исторических данных по фьючерсу на нефть завершен (или прерван).")

if __name__ == "__main__":
    main()
