import requests
import pandas as pd
from datetime import datetime, timedelta

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "forts" # Рынок срочной торговли
ENGINE = "futures" # Торговая система срочного рынка

def get_futures_list():
    """Получает список фьючерсов с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    print(f"Запрашиваю список фьючерсов с {url}")
    try:
        response = requests.get(url, params={"iss.meta": "off", "iss.only": "securities"})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе списка фьючерсов: {e}")
        return None
    except ValueError as e:
        print(f"Ошибка при парсинге JSON ответа списка фьючерсов: {e}")
        return None

def find_oil_futures(data, oil_symbol='BR'):
    """Находит фьючерсы на нефть в полученном списке."""
    if not data or 'securities' not in data: # Исправленная строка
        print("Нет данных о фьючерсах.")
        return pd.DataFrame()

    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    print(f"Всего фьючерсов на рынке '{MARKET}': {len(securities_df)}")
    # print("Первые несколько строк:") # Закомментируем, так как список может быть большим
    # print(securities_df.head(10))

    # Фильтруем DataFrame по символу нефти (например, 'BR')
    oil_futures_df = securities_df[securities_df['SECID'].str.contains(oil_symbol, case=False, na=False)]
    print(f"\nНайдены фьючерсы на нефть ({oil_symbol}):")
    # Используем LASTDELDATE как дату экспирации
    print(oil_futures_df[['SECID', 'SHORTNAME', 'BOARDID', 'LASTDELDATE']].head())
    return oil_futures_df

def get_current_and_next_oil_futures(oil_futures_df):
    """Определяет текущий и следующий фьючерсный контракт на нефть."""
    if oil_futures_df.empty:
        print("Нет доступных фьючерсов на нефть для определения текущего/следующего.")
        return None, None

    # Преобразуем LASTDELDATE в datetime для сортировки
    oil_futures_df = oil_futures_df.copy() # Чтобы избежать SettingWithCopyWarning
    oil_futures_df['LASTDELDATE_DT'] = pd.to_datetime(oil_futures_df['LASTDELDATE'], format='%Y-%m-%d', errors='coerce')

    # Убираем строки, где LASTDELDATE не удалось преобразовать
    oil_futures_df = oil_futures_df.dropna(subset=['LASTDELDATE_DT'])

    if oil_futures_df.empty:
        print("Нет корректных дат экспирации (LASTDELDATE) для фьючерсов на нефть.")
        return None, None

    # Сортируем по дате экспирации
    oil_futures_df = oil_futures_df.sort_values(by='LASTDELDATE_DT')

    # Текущий контракт - это первый (ближайший срок) с датой экспирации >= сегодня
    today = pd.Timestamp.today().normalize() # Нормализуем, чтобы убрать время
    current_contract_df = oil_futures_df[oil_futures_df['LASTDELDATE_DT'] >= today]

    if current_contract_df.empty:
        print("Не найдено фьючерсных контрактов с экспирацией >= сегодня.")
        return None, None

    current_contract = current_contract_df.iloc[0]
    current_contract_secid = current_contract['SECID']
    current_contract_matdate = current_contract['LASTDELDATE_DT']

    # Следующий контракт - это следующий после текущего в отсортированном списке
    all_sorted_matdates = oil_futures_df['LASTDELDATE_DT'].unique()
    current_idx = None
    for i, date in enumerate(all_sorted_matdates):
        if date == current_contract_matdate:
            current_idx = i
            break

    next_contract_secid = None
    if current_idx is not None and current_idx + 1 < len(all_sorted_matdates):
        next_matdate = all_sorted_matdates[current_idx + 1]
        next_contract_df = oil_futures_df[oil_futures_df['LASTDELDATE_DT'] == next_matdate]
        if not next_contract_df.empty:
            next_contract_secid = next_contract_df.iloc[0]['SECID']

    print(f"Текущий фьючерс на нефть (ближайший >= сегодня): {current_contract_secid} (экспирация: {current_contract_matdate.strftime('%Y-%m-%d')})")
    if next_contract_secid:
        print(f"Следующий фьючерс на нефть: {next_contract_secid}")
    else:
        print("Следующий фьючерс на нефть не найден (возможно, только один активен).")

    return current_contract_secid, next_contract_secid

def main():
    oil_symbol = 'BR' # Символ фьючерса на нефть Brent
    data = get_futures_list()
    if data: # Исправленная строка
        oil_futures_df = find_oil_futures(data, oil_symbol)
        if not oil_futures_df.empty:
            print("\n--- Определение текущего и следующего контрактов ---")
            current_secid, next_secid = get_current_and_next_oil_futures(oil_futures_df)
            if current_secid:
                print(f"\nДля дальнейшего сбора истории будет использован текущий контракт: {current_secid}")
                # Сохраним текущий контракт в файл для использования в следующем скрипте
                with open('current_oil_future_contract.txt', 'w') as f:
                    f.write(current_secid)
                print("Текущий тикер фьючерса сохранен в 'current_oil_future_contract.txt'.")
            else:
                print("\nНе удалось определить текущий фьючерсный контракт на нефть.")
        else:
            print(f"\nФьючерсы на нефть с символом '{oil_symbol}' не найдены.")
    else:
        print("Не удалось получить список фьючерсов.")

if __name__ == "__main__":
    main()
