import requests
import pandas as pd
import time
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
    with open(config_file, 'r') as f:
        return json.load(f)

# Загрузка конфигурации
config = load_config(args.config)

# Создание необходимых директорий
os.makedirs(config['logs_dir'], exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'get_moex_stocks.log')
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
MARKET = "shares"
ENGINE = "stock"
REQUEST_PARAMS = {
    "iss.meta": "off",
    "iss.only": "securities,marketdata",
    "securities.columns": "SECID,BOARDID,SHORTNAME,INSTRID,MARKETCODE",
    "marketdata.columns": "SECID,BOARDID,VALTODAY"
}
CSV_OUTPUT_FILE = "moex_stocks_liquid_boards.csv"  # Сохранение в корневую директорию
# Альтернативный путь для сохранения в data_dir (раскомментировать при необходимости):
# CSV_OUTPUT_FILE = os.path.join(config['data_dir'], 'moex_stocks_liquid_boards.csv')

def get_all_securities_with_marketdata():
    """Получает данные о всех инструментах и рыночной информации с MOEX ISS."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/securities.json"
    logger.info(f"Requesting data from {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting to MOEX API: {e}")
        return None
    except ValueError as e:
        logger.error(f"Error parsing JSON response: {e}")
        return None

def process_data_to_liquid_stocks_list(data):
    """Обрабатывает полученные данные, фильтрует акции и находит самый ликвидный режим."""
    if not data or 'securities' not in data or 'marketdata' not in data:
        logger.error("Received data does not contain expected 'securities' or 'marketdata' tables.")
        return pd.DataFrame()
    securities_df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
    marketdata_df = pd.DataFrame(data['marketdata']['data'], columns=data['marketdata']['columns'])
    logger.info(f"Total instruments in 'securities': {len(securities_df)}")
    logger.info(f"Total records in 'marketdata': {len(marketdata_df)}")
    securities_df = securities_df.dropna(subset=['INSTRID', 'MARKETCODE'])
    equity_stocks_df = securities_df[
        (securities_df['MARKETCODE'] == 'FNDT') &
        (securities_df['INSTRID'].str.startswith('EQ', na=False))
    ]
    logger.info(f"After filtering by MARKETCODE='FNDT' and INSTRID.startswith('EQ'): {len(equity_stocks_df)}")
    if equity_stocks_df.empty:
        logger.warning("No ordinary stocks found after filtering (MARKETCODE='FNDT', INSTRID starts with 'EQ').")
        logger.info("Unique INSTRID and MARKETCODE in original data:")
        logger.info(securities_df[['INSTRID', 'MARKETCODE']].drop_duplicates())
        return pd.DataFrame()
    marketdata_df = marketdata_df.dropna(subset=['VALTODAY'])
    merged_df = equity_stocks_df[['SECID', 'BOARDID', 'SHORTNAME']].merge(
        marketdata_df[['SECID', 'BOARDID', 'VALTODAY']], on=['SECID', 'BOARDID'], how='inner'
    )
    logger.info(f"After merging with marketdata and filtering by VALTODAY: {len(merged_df)}")
    if merged_df.empty:
        logger.warning("No data left after merging with market data and VALTODAY filtering.")
        return pd.DataFrame()
    merged_df = merged_df.sort_values(by=['SECID', 'VALTODAY'], ascending=[True, False])
    liquid_stocks_df = merged_df.groupby('SECID').first().reset_index()
    final_df = liquid_stocks_df[['SECID', 'BOARDID', 'SHORTNAME']].copy()
    final_df.rename(columns={'SHORTNAME': 'NAME'}, inplace=True)
    logger.info(f"Found {len(final_df)} ordinary stocks with most liquid mode.")
    return final_df

def save_to_csv(df, filename):
    """Сохраняет DataFrame в CSV файл."""
    if df.empty:
        logger.error("DataFrame is empty, file will not be created.")
        return
    try:
        # Создание директории для файла, если используется data_dir
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"Stocks list successfully saved to {filename}")
    except IOError as e:
        logger.error(f"Error saving file: {e}")

def main():
    """Основная функция."""
    logger.info("Starting collection of ordinary stocks list from MOEX...")
    data = get_all_securities_with_marketdata()
    if data:
        logger.info("Data successfully received. Processing...")
        liquid_stocks_df = process_data_to_liquid_stocks_list(data)
        logger.info("Processing completed. Saving result...")
        save_to_csv(liquid_stocks_df, CSV_OUTPUT_FILE)
    else:
        logger.error("Failed to get data from MOEX API.")

if __name__ == "__main__":
    main()
