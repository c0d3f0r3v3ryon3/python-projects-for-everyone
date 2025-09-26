# find_currency_pairs.py (полная прокачанная версия)
import requests
import pandas as pd
import os
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('find_currency_pairs.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "selt"
ENGINE = "currency"

def get_currency_list():
    """Получает список валютных инструментов с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    logger.info(f"Requesting currency instruments list from {url}")
    try:
        response = requests.get(url, params={"iss.meta": "off", "iss.only": "securities"})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting currency instruments list: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for currency instruments list: {e}")
        return None

def find_currency_pairs(data, target_specific_pairs):
    """Находит конкретные валютные пары в полученном списке."""
    if not data or 'securities' not in data:
        logger.error("No data for currency instruments.")
        return pd.DataFrame()
    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    logger.info(f"Total instruments on market '{MARKET}': {len(securities_df)}")
    logger.info("First few rows:")
    logger.info(securities_df.head(10))
    found_pairs_df = securities_df[securities_df['SECID'].isin(target_specific_pairs)]
    logger.info(f"\nFound currency pairs matching {target_specific_pairs}:")
    logger.info(found_pairs_df[['SECID', 'SHORTNAME', 'BOARDID']])
    return found_pairs_df

def main():
    target_specific_pairs = ['USD000UTSTOM', 'EUR_RUB__TOM']
    data = get_currency_list()
    if data:
        found_df = find_currency_pairs(data, target_specific_pairs)
        if not found_df.empty:
            logger.info("\nCurrency pair tickers found. Proceed to history collection.")
            found_df[['SECID', 'BOARDID']].to_csv('moex_currency_pairs_list.csv', index=False, encoding='utf-8-sig')
            logger.info("Currency pairs list saved to 'moex_currency_pairs_list.csv'.")
        else:
            logger.warning(f"\nSpecific tickers {target_specific_pairs} not found. Check the full instruments list above.")
    else:
        logger.error("Failed to get currency instruments list.")

if __name__ == "__main__":
    main()
