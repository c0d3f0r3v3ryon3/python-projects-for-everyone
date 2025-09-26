import pandas as pd
import requests
import time
import os
from datetime import datetime
import json
import logging
import argparse

# Настройка аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

def load_config(config_file):
    """Загружает конфигурационный файл."""
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError(f"Config file {config_file} not found.")
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)

# Загрузка конфигурации
config = load_config(args.config)

# Создание необходимых директорий
for dir_path in [config['logs_dir'], config['historical_data_currency_dir']]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'get_currency_history_cets.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация
INPUT_CSV_FILE = "moex_currency_pairs_list.csv"
FILTER_BOARDID = "CETS"
OUTPUT_DIR = config['historical_data_currency_dir']
START_DATE = config['start_date']
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt"
ENGINE = "currency"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_filtered_currency_tickers_from_csv(filename, filter_boardid):
    """Загружает список валютных пар из CSV файла, фильтруя по BOARDID."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        logger.info(f"Loaded {len(df)} records from {filename}")
        filtered_df = df[df['BOARDID'] == filter_boardid]
        logger.info(f"After filtering by BOARDID='{filter_boardid}': {len(filtered_df)} records")
        return filtered_df
    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return pd.DataFrame()

def get_currency_history(secid, boardid):
    """Получает исторические данные для одной валютной пары с указанного режима."""
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}.json"
    logger.info(f"Requesting history for currency pair {secid} ({boardid}) from {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout requesting history for currency pair {secid} ({boardid}). Skipping.")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error requesting history for currency pair {secid} ({boardid}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting history for currency pair {secid} ({boardid}): {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for currency pair {secid} ({boardid}): {e}")
        return None

def save_currency_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные валютной пары в CSV файл, адаптируя столбцы."""
    if not data or 'history' not in data or not data['history']['data']:
        logger.warning(f"No historical data for currency pair {secid}, file not created.")
        return
    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    logger.info(f"Received {len(df)} rows of history for {secid}. Columns: {df.columns.tolist()}")
    required_input_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VOLRUR']
    if all(col in df.columns for col in required_input_cols):
        df_renamed = df[['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLRUR']].copy()
        df_renamed = df_renamed.rename(columns={'VOLRUR': 'VALUE'})
        if 'NUMTRADES' in df.columns:
            df_renamed['VOLUME'] = df['NUMTRADES']
        else:
            df_renamed['VOLUME'] = 0
            logger.warning(f"NUMTRADES not found for {secid}, VOLUME filled with 0.")
        df_final = df_renamed[['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VALUE', 'VOLUME']]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df_final.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"Adapted history for currency pair {secid} saved to {filename}")
        except IOError as e:
            logger.error(f"Error saving file for currency pair {secid}: {e}")
    else:
        logger.error(f"Incorrect columns in data for currency pair {secid}: {df.columns.tolist()}. Skipped.")

def main():
    """Основная функция."""
    logger.info(f"Starting collection of historical data for currency pairs (BOARDID={FILTER_BOARDID})...")
    tickers_df = load_filtered_currency_tickers_from_csv(INPUT_CSV_FILE, FILTER_BOARDID)
    if tickers_df.empty:
        logger.error("Failed to load currency pairs list for specified BOARDID. Exiting.")
        return
    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        logger.error(f"File {INPUT_CSV_FILE} does not contain 'SECID' and 'BOARDID' columns. Exiting.")
        return
    total_pairs = len(tickers_df)
    logger.info(f"Starting processing of {total_pairs} currency pairs...")
    for index, row in tickers_df.iterrows():
        secid = row['SECID']
        boardid = row['BOARDID']
        logger.info(f"Processing {index + 1}/{total_pairs}: {secid} ({boardid})")
        data = get_currency_history(secid, boardid)
        if data:
            save_currency_history_to_csv(data, secid, OUTPUT_DIR)
        time.sleep(REQUEST_DELAY)
    logger.info("Collection of historical data for currency pairs completed.")

if __name__ == "__main__":
    main()
