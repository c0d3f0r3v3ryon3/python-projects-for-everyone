import requests
import pandas as pd
import os
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
os.makedirs(config['logs_dir'], exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'find_indices.log')
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
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "index"
ENGINE = "stock"

def get_index_list():
    """Получает список индексов с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    logger.info(f"Requesting indices list from {url}")
    try:
        response = requests.get(url, params={"iss.meta": "off", "iss.only": "securities"})
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting indices list: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response for indices list: {e}")
        return None

def find_indices(data, target_indices):
    """Находит конкретные индексы в полученном списке."""
    if not data or 'securities' not in data:
        logger.error("No data for indices.")
        return pd.DataFrame()
    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    logger.info(f"Total instruments on market '{MARKET}': {len(securities_df)}")
    logger.info("First few rows:")
    logger.info(securities_df.head())
    found_indices_df = securities_df[securities_df['SECID'].isin(target_indices)]
    logger.info(f"\nFound indices {target_indices}:")
    logger.info(found_indices_df[['SECID', 'SHORTNAME', 'BOARDID']])
    return found_indices_df

def main():
    """Основная функция."""
    target_indices = ['IMOEX', 'RTSI']
    data = get_index_list()
    if data:
        found_df = find_indices(data, target_indices)
        if not found_df.empty:
            logger.info("\nIndices tickers found. Proceed to history collection.")
            found_df[['SECID', 'BOARDID']].to_csv('moex_indices_list.csv', index=False, encoding='utf-8-sig')
            logger.info("Indices list saved to 'moex_indices_list.csv'.")
        else:
            logger.warning(f"\nIndices {target_indices} not found on market '{MARKET}'.")
    else:
        logger.error("Failed to get indices list.")

if __name__ == "__main__":
    main()
