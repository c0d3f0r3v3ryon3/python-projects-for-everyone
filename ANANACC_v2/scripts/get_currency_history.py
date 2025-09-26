# get_currency_history.py (полная прокачанная версия)
import pandas as pd
import requests
import time
import os
from datetime import datetime
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('get_currency_history.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

INPUT_CSV_FILE = "moex_currency_pairs_list.csv"
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

def load_currency_tickers_from_csv(filename):
    """Загружает список валютных пар из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        logger.info(f"Loaded {len(df)} currency pairs from {filename}")
        return df
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
    """Сохраняет исторические данные валютной пары в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        logger.warning(f"No historical data for currency pair {secid}, file not created.")
        return
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    logger.info(f"Received {len(df)} rows of history for {secid}. Columns: {df.columns.tolist()}")
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VOLRUR']
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        df = df.rename(columns={'VOLRUR': 'VOLUME'})
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"History for currency pair {secid} saved to {filename}")
        except IOError as e:
            logger.error(f"Error saving file for currency pair {secid}: {e}")
    else:
        logger.error(f"Incorrect columns in data for currency pair {secid}: {df.columns.tolist()}. Skipped.")

def main():
    """Основная функция."""
    logger.info("Starting collection of historical data for currency pairs...")
    tickers_df = load_currency_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        logger.error("Failed to load currency pairs list. Exiting.")
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
