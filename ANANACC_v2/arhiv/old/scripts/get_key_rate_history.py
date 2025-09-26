import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime

# --- Конфигурация ---
CBR_KEY_RATE_URL = "https://www.cbr.ru/hd_base/KeyRate/"
OUTPUT_DIR = "historical_data_other"
OUTPUT_FILE = "cbr_key_rate_history_html.csv"

def get_key_rate_html():
    """Получает HTML-страницу с историей ключевой ставки ЦБ РФ."""
    print(f"Запрашиваю HTML-страницу с историей ключевой ставки с {CBR_KEY_RATE_URL}")
    try:
        # Отправляем GET-запрос
        response = requests.get(CBR_KEY_RATE_URL, timeout=60)
        response.raise_for_status() # Проверяем на HTTP ошибки
        print("HTML-страница успешно получена.")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе HTML-страницы: {e}")
        return None

def parse_key_rate_html(html_content):
    """Парсит HTML и извлекает таблицу с ключевой ставкой."""
    if not html_content:
        print("Нет HTML-контента для парсинга.")
        return pd.DataFrame()

    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Ищем таблицу. Обычно это первая таблица с классом 'data'
        # Проверим сначала по классу 'data'
        table = soup.find('table', class_='data')

        # Если не нашли, попробуем найти первую таблицу вообще
        if not table:
             tables = soup.find_all('table')
             if tables:
                  table = tables[0] # Берем первую найденную таблицу
                  print("Таблица с классом 'data' не найдена, использую первую таблицу на странице.")
             else:
                  print("На странице не найдено ни одной таблицы.")
                  return pd.DataFrame()
        else:
             print("Найдена таблица с классом 'data'.")

        # Извлекаем строки таблицы
        rows = table.find_all('tr')
        if not rows:
            print("В найденной таблице нет строк (<tr>).")
            return pd.DataFrame()

        # Предполагаем, что первая строка - заголовок
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        print(f"Заголовки таблицы: {headers}")

        # Проверим, есть ли ожидаемые заголовки
        expected_headers_ru = ['Дата', 'Ставка']
        expected_headers_en = ['Date', 'Rate']
        if not (all(h in headers for h in expected_headers_ru) or all(h in headers for h in expected_headers_en)):
             print(f"Заголовки таблицы не соответствуют ожидаемым ({expected_headers_ru} или {expected_headers_en}).")
             print("Возможно, структура страницы изменилась.")
             # Попробуем продолжить, используя индексы 0 и 1

        data_rows = rows[1:] # Все строки, кроме заголовка
        parsed_data = []
        for row in data_rows:
            cols = row.find_all(['td', 'th']) # Ищем и ячейки данных, и заголовочные ячейки
            cols_text = [col.get_text(strip=True) for col in cols]
            if len(cols_text) >= 2: # Убедимся, что есть хотя бы 2 столбца
                 # Ожидаем: [Дата, Ставка, ...]
                 date_str = cols_text[0]
                 rate_str = cols_text[1]
                 # Очистка и преобразование
                 # Дата обычно в формате dd.mm.yyyy
                 # Ставка может содержать % или просто число
                 try:
                      # Попробуем преобразовать дату
                      date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                      # Попробуем преобразовать ставку, убрав символ %
                      rate_clean = rate_str.replace('%', '').replace(',', '.').strip()
                      rate_val = float(rate_clean)
                      parsed_data.append([date_obj.strftime('%Y-%m-%d'), rate_val])
                 except ValueError as e:
                      # Если не удалось преобразовать, пропускаем строку
                      print(f"  Предупреждение: Не удалось преобразовать строку данных: {cols_text}. Ошибка: {e}")
                      continue
            else:
                 # Пропускаем строки с недостаточным количеством столбцов
                 continue

        if not parsed_data:
             print("После парсинга таблицы не удалось извлечь данные.")
             return pd.DataFrame()

        # Создаем DataFrame
        df = pd.DataFrame(parsed_data, columns=['TRADEDATE', 'KEY_RATE'])
        print(f"Извлечено {len(df)} строк данных из HTML-таблицы.")
        # Сортируем по дате
        df = df.sort_values(by='TRADEDATE').reset_index(drop=True)
        return df

    except Exception as e:
        print(f"Ошибка при парсинге HTML: {e}")
        return pd.DataFrame()


def save_key_rate_history_to_csv(df, output_dir, output_file):
    """Сохраняет историю ключевой ставки в CSV файл."""
    if df.empty:
        print("DataFrame с историей ключевой ставки пуст, файл не будет создан.")
        return

    # Создаем директорию, если её нет
    os.makedirs(output_dir, exist_ok=True)

    filename = os.path.join(output_dir, output_file)
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig') # utf-8-sig для корректного отображения в Excel
        print(f"История ключевой ставки ЦБ РФ сохранена в {filename}")
    except IOError as e:
        print(f"Ошибка при сохранении файла: {e}")

def main():
    """Основная функция."""
    print("Начинаю сбор исторических данных по ключевой ставке ЦБ РФ через HTML-парсинг...")

    html_content = get_key_rate_html()
    if html_content:
        df = parse_key_rate_html(html_content)
        save_key_rate_history_to_csv(df, OUTPUT_DIR, OUTPUT_FILE)
    else:
        print("Не удалось получить HTML-страницу с данными.")

    print("Сбор исторических данных по ключевой ставке ЦБ РФ (через HTML) завершен (или прерван).")

if __name__ == "__main__":
    main()
