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
for dir_path in [config['logs_dir'], config['historical_data_indices_dir']]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'get_index_history.log')
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
INPUT_CSV_FILE = "moex_indices_list.csv"
OUTPUT_DIR = config['historical_data_indices_dir']
START_DATE = config['start_date']
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "index"
ENGINE = "stock"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def load_index_tickers_from_csv(filename):
    """Загружает список индексов из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        logger.info(f"Loaded {len(df)} indices from {filename}")
        return df
    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return pd.DataFrame()

def get_index_history(secid):
    """Получает исторические данные для одного индекса с рынка индексов."""
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/securities/{secid}.json"
    logger.info(f"Requesting history for index {secid} from {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout requesting history for index {secid}. Skipping.")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error requesting history for index {secid}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting history for index {secid}: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for index {secid}: {e}")
        return None

def save_index_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные индекса в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        logger.warning(f"No historical data for index {secid}, file not created.")
        return
    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    logger.info(f"Received {len(df)} rows of history for {secid}. Columns: {df.columns.tolist()}")
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW']
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"History for index {secid} saved to {filename}")
        except IOError as e:
            logger.error(f"Error saving file for index {secid}: {e}")
    else:
        logger.error(f"Incorrect columns in data for index {secid}: {df.columns.tolist()}. Skipped.")

def main():
    """Основная функция."""
    logger.info("Starting collection of historical data for indices...")
    tickers_df = load_index_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        logger.error("Failed to load indices list. Exiting.")
        return
    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        logger.error(f"File {INPUT_CSV_FILE} does not contain 'SECID' and 'BOARDID' columns. Exiting.")
        return
    total_indices = len(tickers_df)
    logger.info(f"Starting processing of {total_indices} indices...")
    for index, row in tickers_df.iterrows():
        secid = row['SECID']
        logger.info(f"Processing {index + 1}/{total_indices}: {secid}")
        data = get_index_history(secid)
        if data:
            save_index_history_to_csv(data, secid, OUTPUT_DIR)
        time.sleep(REQUEST_DELAY)
    logger.info("Collection of historical data for indices completed.")

if __name__ == "__main__":
    main()
