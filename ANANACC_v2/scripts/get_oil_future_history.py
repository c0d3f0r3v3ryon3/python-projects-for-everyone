import pandas as pd
import requests
import time
import os
import subprocess
import json
import logging
import argparse
import sys

# Настройка аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

def load_config(config_file):
    """Загружает конфигурационный файл."""
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError(f"Config file {config_file} not found.")
    with open(config_file, 'r') as f:
        return json.load(f)

# Загрузка конфигурации
config = load_config(args.config)

# Создание необходимых директорий
for dir_path in [config['logs_dir'], config['historical_data_oil_dir']]:
    os.makedirs(dir_path, exist_ok=True)

# Проверка существования директории scripts
SCRIPTS_DIR = 'scripts'
if not os.path.exists(SCRIPTS_DIR):
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    logger.warning(f"Scripts directory {SCRIPTS_DIR} was created, but find_oil_futures.py may be missing.")

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'get_oil_future_history.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация путей
INPUT_CONTRACT_FILE = "current_oil_future_contract.txt"
OUTPUT_DIR = config['historical_data_oil_dir']
START_DATE = config['start_date']
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "forts"
ENGINE = "futures"
REQUEST_PARAMS = {
    "from": START_DATE,
    "iss.meta": "off",
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45

def run_find_oil_futures(config_file):
    """Запускает find_oil_futures.py для создания current_oil_future_contract.txt."""
    script_path = os.path.join(SCRIPTS_DIR, "find_oil_futures.py")
    if not os.path.exists(script_path):
        logger.error(f"Script {script_path} not found.")
        return False
    try:
        logger.info(f"Running {script_path} to generate {INPUT_CONTRACT_FILE}")
        result = subprocess.run(
            [sys.executable, script_path, "--config", config_file],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"{script_path} executed successfully.")
            return True
        else:
            logger.error(f"Error running {script_path}: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Exception while running {script_path}: {e}")
        return False

def load_current_contract_from_file(filename):
    """Загружает тикер текущего фьючерсного контракта из файла."""
    if not os.path.exists(filename):
        logger.info(f"File {filename} not found. Attempting to run find_oil_futures.py...")
        success = run_find_oil_futures(args.config)
        if not success or not os.path.exists(filename):
            logger.error(f"Failed to generate {filename} after running find_oil_futures.py.")
            return None
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            secid = f.read().strip()
        logger.info(f"Loaded futures ticker: {secid}")
        return secid
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return None

def get_oil_future_history(secid):
    """Получает исторические данные для фьючерсного контракта с указанного режима."""
    boardid = "RFUD"
    url = f"{MOEX_BASE_URL}/history/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}.json"
    logger.info(f"Requesting history for future {secid} ({boardid}) from {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout requesting history for future {secid} ({boardid}). Skipping.")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error requesting history for future {secid} ({boardid}): {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting history for future {secid} ({boardid}): {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for future {secid} ({boardid}): {e}")
        return None

def save_oil_future_history_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные фьючерса в CSV файл."""
    if not data or 'history' not in data or not data['history']['data']:
        logger.warning(f"No historical data for future {secid}, file not created.")
        return False
    df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
    logger.info(f"Received {len(df)} rows of history for {secid}. Columns: {df.columns.tolist()}")
    required_cols = ['TRADEDATE', 'OPEN', 'CLOSE', 'HIGH', 'LOW', 'VALUE', 'VOLUME']
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"History for future {secid} saved to {filename}")
            return True
        except IOError as e:
            logger.error(f"Error saving file for future {secid}: {e}")
            return False
    else:
        logger.error(f"Incorrect columns in data for future {secid}: {df.columns.tolist()}. Skipped.")
        return False

def main():
    """Основная функция."""
    try:
        logger.info("Starting collection of historical data for oil future...")
        secid = load_current_contract_from_file(INPUT_CONTRACT_FILE)
        if secid is None:
            logger.error("Failed to load futures contract ticker. Exiting.")
            sys.exit(1)
        data = get_oil_future_history(secid)
        if data and save_oil_future_history_to_csv(data, secid, OUTPUT_DIR):
            logger.info("Collection of historical data for oil future completed.")
            sys.exit(0)
        else:
            logger.error(f"Failed to get or save historical data for future {secid}.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
