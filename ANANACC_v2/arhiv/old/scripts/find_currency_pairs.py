import requests
import pandas as pd

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt" # Рынок Selt (валютный)
ENGINE = "currency" # Торговая система валютного рынка

def get_currency_list():
    """Получает список валютных инструментов с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    print(f"Запрашиваю список валютных инструментов с {url}")
    try:
        response = requests.get(url, params={"iss.meta": "off", "iss.only": "securities"})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе списка валютных инструментов: {e}")
        return None
    except ValueError as e:
        print(f"Ошибка при парсинге JSON ответа списка валютных инструментов: {e}")
        return None

def find_currency_pairs(data, target_specific_pairs):
    """Находит конкретные валютные пары в полученном списке."""
    if not data or 'securities' not in data:
        print("Нет данных о валютных инструментах.")
        return pd.DataFrame()

    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    print(f"Всего инструментов на рынке '{MARKET}': {len(securities_df)}")
    print("Первые несколько строк:")
    print(securities_df.head(10))

    # Фильтруем DataFrame по списку целевых пар
    found_pairs_df = securities_df[securities_df['SECID'].isin(target_specific_pairs)]
    print(f"\nНайдены валютные пары, соответствующие {target_specific_pairs}:")
    print(found_pairs_df[['SECID', 'SHORTNAME', 'BOARDID']])
    return found_pairs_df

def main():
    # Ищем конкретные ожидаемые тикеры
    target_specific_pairs = ['USD000UTSTOM', 'EUR_RUB__TOM']

    data = get_currency_list()
    if data:
        found_df = find_currency_pairs(data, target_specific_pairs)
        if not found_df.empty:
            print("\nКонкретные тикеры валютных пар найдены. Можно приступать к сбору истории.")
            # Сохраним найденные тикеры и их BOARDID для дальнейшего использования
            found_df[['SECID', 'BOARDID']].to_csv('moex_currency_pairs_list.csv', index=False, encoding='utf-8-sig')
            print("Список валютных пар сохранен в 'moex_currency_pairs_list.csv'.")
        else:
            print(f"\nКонкретные тикеры {target_specific_pairs} не найдены. Проверьте список всех инструментов выше.")
            # Попробуем найти по общим частям
            target_parts = ['USD', 'EUR', 'RUB']
            mask = securities_df['SECID'].str.contains('|'.join(target_parts), case=False, na=False)
            found_by_parts_df = securities_df[mask]
            if not found_by_parts_df.empty:
                 found_by_parts_df[['SECID', 'BOARDID']].to_csv('moex_currency_pairs_list.csv', index=False, encoding='utf-8-sig')
                 print("Список валютных пар (по частям) сохранен в 'moex_currency_pairs_list.csv'.")
            else:
                 print("Не найдено инструментов, содержащих 'USD', 'EUR', 'RUB'.")
    else:
        print("Не удалось получить список валютных инструментов.")

if __name__ == "__main__":
    main()
