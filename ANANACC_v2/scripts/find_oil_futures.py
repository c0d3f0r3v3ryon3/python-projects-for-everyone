# find_oil_futures.py (полная прокачанная версия с повторными попытками)
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from datetime import datetime
import os
import json
import logging
import argparse
import sys

# Настройка аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('find_oil_futures.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Функция для загрузки конфигурации
def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "forts"
ENGINE = "futures"
MAX_RETRIES = 5
RETRY_DELAY = 5

# Настройка сессии с повторными попытками
session = requests.Session()
retries = Retry(total=MAX_RETRIES, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retries))

def get_futures_list():
    """Получает список фьючерсов с MOEX ISS с повторными попытками."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    logger.info(f"Requesting futures list from {url}")
    try:
        response = session.get(url, params={"iss.meta": "off", "iss.only": "securities"}, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting futures list after {MAX_RETRIES} retries: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for futures list: {e}")
        return None

def find_oil_futures(data, oil_symbol='BR'):
    """Находит фьючерсы на нефть в полученном списке."""
    if not data or 'securities' not in data:
        logger.error("No data for futures.")
        return pd.DataFrame()
    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    logger.info(f"Total futures on market '{MARKET}': {len(securities_df)}")
    oil_futures_df = securities_df[securities_df['SECID'].str.contains(oil_symbol, case=False, na=False)]
    logger.info(f"\nFound oil futures ({oil_symbol}):")
    logger.info(oil_futures_df[['SECID', 'SHORTNAME', 'BOARDID', 'LASTDELDATE']].head())
    return oil_futures_df

def get_current_and_next_oil_futures(oil_futures_df):
    """Определяет текущий и следующий фьючерсный контракт на нефть."""
    if oil_futures_df.empty:
        logger.error("No available oil futures to determine current/next.")
        return None, None
    oil_futures_df = oil_futures_df.copy()
    oil_futures_df['LASTDELDATE_DT'] = pd.to_datetime(oil_futures_df['LASTDELDATE'], format='%Y-%m-%d', errors='coerce')
    oil_futures_df = oil_futures_df.dropna(subset=['LASTDELDATE_DT'])
    if oil_futures_df.empty:
        logger.error("No valid expiration dates (LASTDELDATE) for oil futures.")
        return None, None
    oil_futures_df = oil_futures_df.sort_values(by='LASTDELDATE_DT')
    today = pd.Timestamp.today().normalize()
    current_contract_df = oil_futures_df[oil_futures_df['LASTDELDATE_DT'] >= today]
    if current_contract_df.empty:
        logger.error("No futures contracts with expiration >= today.")
        return None, None
    current_contract = current_contract_df.iloc[0]
    current_contract_secid = current_contract['SECID']
    current_contract_matdate = current_contract['LASTDELDATE_DT']
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
    logger.info(f"Current oil future (nearest >= today): {current_contract_secid} (expiration: {current_contract_matdate.strftime('%Y-%m-%d')})")
    if next_contract_secid:
        logger.info(f"Next oil future: {next_contract_secid}")
    else:
        logger.warning("Next oil future not found (possibly only one active).")
    return current_contract_secid, next_contract_secid

def main():
    try:
        oil_symbol = 'BR'
        data = get_futures_list()
        if data:
            oil_futures_df = find_oil_futures(data, oil_symbol)
            if not oil_futures_df.empty:
                logger.info("\n--- Determining current and next contracts ---")
                current_secid, next_secid = get_current_and_next_oil_futures(oil_futures_df)
                if current_secid:
                    logger.info(f"\nFor further history collection, current contract will be used: {current_secid}")
                    with open('current_oil_future_contract.txt', 'w') as f:
                        f.write(current_secid)
                    logger.info("Current futures ticker saved to 'current_oil_future_contract.txt'.")
                    sys.exit(0)
                else:
                    logger.error("\nFailed to determine current futures contract for oil.")
                    sys.exit(1)
            else:
                logger.warning(f"\nOil futures with symbol '{oil_symbol}' not found.")
                sys.exit(1)
        else:
            logger.error("Failed to get futures list.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
