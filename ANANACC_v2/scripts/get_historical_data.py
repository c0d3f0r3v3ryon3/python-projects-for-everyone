# get_historical_data.py (полная прокачанная версия)
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('get_historical_data.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

INPUT_CSV_FILE = "moex_stocks_liquid_boards.csv"
OUTPUT_DIR = config['historical_data_full_dir']
START_DATE = config['start_date']
MOEX_BASE_URL = "https://iss.moex.com/iss"
MARKET = "shares"
ENGINE = "stock"
REQUEST_PARAMS = {
    "from": START_DATE,
    "interval": 24,
    "iss.meta": "off",
    "iss.only": "candles",
    "candles.columns": "begin,end,open,high,low,close,volume"
}
REQUEST_DELAY = 1.0
REQUEST_TIMEOUT = 45
MAX_CONNECTION_RETRY_ATTEMPTS = 5

def load_tickers_from_csv(filename):
    """Загружает список тикеров из CSV файла."""
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        logger.info(f"Loaded {len(df)} tickers from {filename}")
        return df
    except FileNotFoundError:
        logger.error(f"File {filename} not found.")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error reading file {filename}: {e}")
        return pd.DataFrame()

def get_historical_data_for_ticker(secid, boardid):
    """Получает исторические данные для одного тикера с указанного режима."""
    url = f"{MOEX_BASE_URL}/engines/{ENGINE}/markets/{MARKET}/boards/{boardid}/securities/{secid}/candles.json"
    logger.info(f"Requesting history for {secid} ({boardid}) from {url}")
    try:
        response = requests.get(url, params=REQUEST_PARAMS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.Timeout:
        logger.error(f"Timeout requesting history for {secid} ({boardid}).")
        return 'CONNECTION_ERROR'
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error requesting history for {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR'
    except requests.exceptions.RequestException as e:
        logger.error(f"Error requesting history for {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR'
    except ValueError as e:
        logger.error(f"Error parsing JSON response for {secid} ({boardid}): {e}")
        return 'CONNECTION_ERROR'

def save_historical_data_to_csv(data, secid, output_dir):
    """Сохраняет исторические данные в CSV файл для конкретного тикера."""
    if data == 'CONNECTION_ERROR':
        return False, 'CONNECTION_ERROR'
    if not data or 'candles' not in data or not data['candles']['data']:
        logger.warning(f"No historical data for {secid}, file not created.")
        return False, 'NO_DATA'
    os.makedirs(output_dir, exist_ok=True)
    df = pd.DataFrame(data['candles']['data'], columns=data['candles']['columns'])
    if 'begin' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['begin']).dt.date
        df = df.drop(columns=['begin'])
    elif 'end' in df.columns:
        df['TRADEDATE'] = pd.to_datetime(df['end']).dt.date
        df = df.drop(columns=['end'])
    else:
        logger.error(f"Neither 'begin' nor 'end' found in data for {secid}. Skipping.")
        return False, 'PARSE_ERROR'
    expected_col_mapping = {'open': 'OPEN', 'high': 'HIGH', 'low': 'LOW', 'close': 'CLOSE', 'volume': 'VOLUME'}
    missing_cols = [col for col in expected_col_mapping.keys() if col not in df.columns]
    if missing_cols:
        logger.error(f"Incorrect columns in data for {secid}: {df.columns.tolist()}. Missing: {missing_cols}. Skipped.")
        return False, 'PARSE_ERROR'
    df = df.rename(columns=expected_col_mapping)
    required_cols = ['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']
    if all(col in df.columns for col in required_cols):
        df = df[required_cols]
        filename = os.path.join(output_dir, f"{secid}_history.csv")
        try:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            logger.info(f"History for {secid} saved to {filename} ({len(df)} rows)")
            return True, 'SUCCESS'
        except IOError as e:
            logger.error(f"Error saving file for {secid}: {e}")
            return False, 'SAVE_ERROR'
    else:
        logger.error(f"Incorrect columns in data for {secid} after processing: {df.columns.tolist()}. Skipped.")
        return False, 'PARSE_ERROR'

def main():
    """Основная функция."""
    logger.info("Starting collection of historical data (full list, retry only connection errors)...")
    tickers_df = load_tickers_from_csv(INPUT_CSV_FILE)
    if tickers_df.empty:
        logger.error("Failed to load tickers list. Exiting.")
        return
    if not all(col in tickers_df.columns for col in ['SECID', 'BOARDID']):
        logger.error(f"File {INPUT_CSV_FILE} does not contain 'SECID' and 'BOARDID' columns. Exiting.")
        return
    total_tickers = len(tickers_df)
    logger.info(f"Starting processing of {total_tickers} tickers...")
    remaining_tickers_df = tickers_df.copy()
    logger.info("\n--- Main pass ---")
    failed_connection_tickers = []
    failed_other_tickers = []
    for index, row in remaining_tickers_df.iterrows():
        secid = row['SECID']
        boardid = row['BOARDID']
        logger.info(f"Processing: {secid} ({boardid})")
        try:
            data = get_historical_data_for_ticker(secid, boardid)
            success, status = save_historical_data_to_csv(data, secid, OUTPUT_DIR)
            if success:
                logger.info(f"    Successfully processed: {secid}")
            else:
                if status == 'CONNECTION_ERROR':
                    logger.info(f"    Connection error for {secid}, added to retry list.")
                    failed_connection_tickers.append({'SECID': secid, 'BOARDID': boardid})
                else:
                    logger.info(f"    Final error for {secid} (reason: {status}), added to final failed list.")
                    failed_other_tickers.append({'SECID': secid, 'BOARDID': boardid})
        except KeyboardInterrupt:
            logger.warning(f"\nProcessing interrupted by user on ticker {secid}.")
            if failed_connection_tickers:
                pd.DataFrame(failed_connection_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_connection_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
            if failed_other_tickers:
                pd.DataFrame(failed_other_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_other_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
            return
    logger.info("Main pass completed.")
    logger.info(f"  Successfully processed: {total_tickers - len(failed_connection_tickers) - len(failed_other_tickers)}")
    logger.info(f"  Connection errors: {len(failed_connection_tickers)}")
    logger.info(f"  Final errors (no data etc.): {len(failed_other_tickers)}")
    connection_retry_df = pd.DataFrame(failed_connection_tickers)
    attempt = 1
    max_attempts = MAX_CONNECTION_RETRY_ATTEMPTS
    while not connection_retry_df.empty and attempt <= max_attempts:
        logger.info(f"\n--- Retry connection - Pass {attempt} ---")
        logger.info(f"Remaining to process {len(connection_retry_df)} tickers with connection errors.")
        next_failed_connection_tickers = []
        for _, row in connection_retry_df.iterrows():
            secid = row['SECID']
            boardid = row['BOARDID']
            logger.info(f"Retry for: {secid} ({boardid})")
            try:
                data = get_historical_data_for_ticker(secid, boardid)
                success, status = save_historical_data_to_csv(data, secid, OUTPUT_DIR)
                if success:
                    logger.info(f"    Successfully processed: {secid}")
                else:
                    if status == 'CONNECTION_ERROR':
                        logger.info(f"    Connection error for {secid}, remains in retry list.")
                        next_failed_connection_tickers.append({'SECID': secid, 'BOARDID': boardid})
                    else:
                        logger.info(f"    Final error for {secid} (reason: {status}), moved to final failed.")
                        failed_other_tickers.append({'SECID': secid, 'BOARDID': boardid})
            except KeyboardInterrupt:
                logger.warning(f"\nProcessing interrupted by user on ticker {secid}.")
                if next_failed_connection_tickers:
                    pd.DataFrame(next_failed_connection_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_connection_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
                if failed_other_tickers:
                    pd.DataFrame(failed_other_tickers).to_csv(os.path.join(OUTPUT_DIR, "failed_other_tickers_on_interrupt.csv"), index=False, encoding='utf-8-sig')
                return
        connection_retry_df = pd.DataFrame(next_failed_connection_tickers)
        attempt += 1
        if not connection_retry_df.empty and attempt <= max_attempts:
            logger.info(f"After pass {attempt - 1}, remaining {len(connection_retry_df)} tickers with connection errors.")
            logger.info(f"Waiting before next pass... ({REQUEST_DELAY} seconds)")
            time.sleep(REQUEST_DELAY)
    final_success_count = total_tickers - len(connection_retry_df) - len(failed_other_tickers)
    logger.info(f"\n--- Summary ---")
    logger.info(f"All tickers processed (or max retries reached).")
    logger.info(f"  Total tickers: {total_tickers}")
    logger.info(f"  Successfully processed: {final_success_count}")
    logger.info(f"  Unresolved connection errors (after {max_attempts} retries): {len(connection_retry_df)}")
    logger.info(f"  Final errors (no data etc.): {len(failed_other_tickers)}")
    if not connection_retry_df.empty:
        logger.info(f"  Failed to process the following tickers due to repeated connection errors:")
        logger.info(connection_retry_df)
        failed_con_file = os.path.join(OUTPUT_DIR, "failed_connection_tickers_final.csv")
        connection_retry_df.to_csv(failed_con_file, index=False, encoding='utf-8-sig')
        logger.info(f"Final failed tickers (connection errors) saved to {failed_con_file}")
    if failed_other_tickers:
        failed_other_file = os.path.join(OUTPUT_DIR, "failed_other_tickers_final.csv")
        pd.DataFrame(failed_other_tickers).to_csv(failed_other_file, index=False, encoding='utf-8-sig')
        logger.info(f"Tickers with final errors (no data etc.) saved to {failed_other_file}")
    logger.info("Collection of historical data (full list) completed (or interrupted).")

if __name__ == "__main__":
    main()
