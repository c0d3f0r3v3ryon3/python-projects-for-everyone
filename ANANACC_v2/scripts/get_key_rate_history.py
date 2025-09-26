# get_key_rate_history.py (полная прокачанная версия)
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('get_key_rate_history.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

CBR_KEY_RATE_URL = "https://www.cbr.ru/hd_base/KeyRate/"
OUTPUT_DIR = config['historical_data_other_dir']
OUTPUT_FILE = "cbr_key_rate_history_html.csv"

def get_key_rate_html():
    """Получает HTML-страницу с историей ключевой ставки ЦБ РФ."""
    logger.info(f"Requesting HTML page with key rate history from {CBR_KEY_RATE_URL}")
    try:
        response = requests.get(CBR_KEY_RATE_URL, timeout=60)
        response.raise_for_status()
        logger.info("HTML page successfully received.")
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting HTML page: {e}")
        return None

def parse_key_rate_html(html_content):
    """Парсит HTML и извлекает таблицу с ключевой ставкой."""
    if not html_content:
        logger.error("No HTML content for parsing.")
        return pd.DataFrame()
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', class_='data')
        if not table:
            tables = soup.find_all('table')
            if tables:
                table = tables[0]
                logger.info("Table with class 'data' not found, using first table on page.")
            else:
                logger.error("No tables found on page.")
                return pd.DataFrame()
        else:
            logger.info("Found table with class 'data'.")
        rows = table.find_all('tr')
        if not rows:
            logger.error("No rows (<tr>) found in table.")
            return pd.DataFrame()
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        logger.info(f"Table headers: {headers}")
        expected_headers_ru = ['Дата', 'Ставка']
        expected_headers_en = ['Date', 'Rate']
        data_rows = rows[1:]
        parsed_data = []
        for row in data_rows:
            cols = row.find_all(['td', 'th'])
            cols_text = [col.get_text(strip=True) for col in cols]
            if len(cols_text) >= 2:
                date_str = cols_text[0]
                rate_str = cols_text[1]
                try:
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    rate_clean = rate_str.replace('%', '').replace(',', '.').strip()
                    rate_val = float(rate_clean)
                    parsed_data.append([date_obj.strftime('%Y-%m-%d'), rate_val])
                except ValueError as e:
                    logger.warning(f"Warning: Failed to parse data row: {cols_text}. Error: {e}")
                    continue
            else:
                continue
        if not parsed_data:
            logger.error("Failed to extract data after parsing table.")
            return pd.DataFrame()
        df = pd.DataFrame(parsed_data, columns=['TRADEDATE', 'KEY_RATE'])
        logger.info(f"Extracted {len(df)} rows of data from HTML table.")
        df = df.sort_values(by='TRADEDATE').reset_index(drop=True)
        return df
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return pd.DataFrame()

def save_key_rate_history_to_csv(df, output_dir, output_file):
    """Сохраняет историю ключевой ставки в CSV файл."""
    if df.empty:
        logger.error("DataFrame with key rate history is empty, file will not be created.")
        return
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, output_file)
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"Key rate history saved to {filename}")
    except IOError as e:
        logger.error(f"Error saving file: {e}")

def main():
    """Основная функция."""
    logger.info("Starting collection of historical data for CBR key rate via HTML parsing...")
    html_content = get_key_rate_html()
    if html_content:
        df = parse_key_rate_html(html_content)
        save_key_rate_history_to_csv(df, OUTPUT_DIR, OUTPUT_FILE)
    else:
        logger.error("Failed to get HTML page with data.")
    logger.info("Collection of historical data for CBR key rate (via HTML) completed (or interrupted).")

if __name__ == "__main__":
    main()
