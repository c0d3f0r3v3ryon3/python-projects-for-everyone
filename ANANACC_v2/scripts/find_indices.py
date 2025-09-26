import requests
import pandas as pd

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "index" # Рынок индексов
ENGINE = "stock" # Торговая система фондового рынка

def get_index_list():
    """Получает список индексов с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    print(f"Запрашиваю список индексов с {url}")
    try:
        response = requests.get(url, params={"iss.meta": "off", "iss.only": "securities"})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе списка индексов: {e}")
        return None
    except ValueError as e:
        print(f"Ошибка при парсинге JSON ответа списка индексов: {e}")
        return None

def find_indices(data, target_indices):
    """Находит конкретные индексы в полученном списке."""
    if not data or 'securities' not in data:
        print("Нет данных о индексах.")
        return pd.DataFrame()

    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    print(f"Всего инструментов на рынке '{MARKET}': {len(securities_df)}")
    print("Первые несколько строк:")
    print(securities_df.head())

    # Фильтруем DataFrame по списку целевых индексов
    found_indices_df = securities_df[securities_df['SECID'].isin(target_indices)]
    print(f"\nНайдены индексы {target_indices}:")
    print(found_indices_df[['SECID', 'SHORTNAME', 'BOARDID']])
    return found_indices_df

def main():
    target_indices = ['IMOEX', 'RTSI']
    data = get_index_list()
    if data:
        found_df = find_indices(data, target_indices)
        if not found_df.empty:
            print("\nТикеры индексов найдены. Можно приступать к сбору истории.")
            # Сохраним найденные тикеры и их BOARDID для дальнейшего использования
            found_df[['SECID', 'BOARDID']].to_csv('moex_indices_list.csv', index=False, encoding='utf-8-sig')
            print("Список индексов сохранен в 'moex_indices_list.csv'.")
        else:
            print(f"\nИндексы {target_indices} не найдены на рынке '{MARKET}'.")

if __name__ == "__main__":
    main()
