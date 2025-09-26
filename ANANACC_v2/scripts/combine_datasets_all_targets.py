# combine_datasets_all_targets.py (полная прокачанная версия)
import pandas as pd
import numpy as np
import os
import subprocess
import sys
from datetime import datetime
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('combine_datasets_all_targets.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

INPUT_DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset.csv')
OUTPUT_DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset_all_targets.csv')

def run_combine_datasets(config_file):
    """Запускает combine_datasets.py для создания combined_dataset.csv."""
    script_path = os.path.join("scripts", "combine_datasets.py")
    if not os.path.exists(script_path):
        logger.error(f"Script {script_path} not found.")
        return False
    try:
        logger.info(f"Running {script_path} to generate {INPUT_DATASET_FILE}")
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

def load_dataset(filename):
    """Загружает датасет из CSV файла."""
    logger.info(f"Loading dataset from {filename}...")
    if not os.path.exists(filename):
        logger.info(f"File {filename} not found. Attempting to run combine_datasets.py...")
        success = run_combine_datasets(args.config)
        if not success or not os.path.exists(filename):
            logger.error(f"Failed to generate {filename} after running combine_datasets.py.")
            return pd.DataFrame()
    try:
        df = pd.read_csv(filename, encoding='utf-8-sig')
        logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
        return df
    except Exception as e:
        logger.error(f"Error loading dataset from {filename}: {e}")
        return pd.DataFrame()

def add_target_directions_for_all_tickers(df):
    """Добавляет колонки TARGET_DIRECTION для всех тикеров."""
    logger.info("\n--- Adding TARGET_DIRECTION for all tickers ---")
    close_cols = [col for col in df.columns if col.endswith('_CLOSE')]
    logger.info(f"Found {len(close_cols)} columns with closing prices (_CLOSE).")
    tickers = [col.replace('_CLOSE', '') for col in close_cols]
    logger.info(f"Extracted tickers: {tickers[:10]}... (first 10)")
    new_columns_series = []
    added_targets = 0
    for ticker in tickers:
        close_col = f"{ticker}_CLOSE"
        target_col = f"TARGET_DIRECTION_{ticker}"
        if close_col in df.columns:
            logger.info(f"  Creating target variable for {ticker}...")
            shifted_close = df[close_col].shift(-1)
            target_direction_series = np.where(
                shifted_close > df[close_col], 1,
                np.where(shifted_close < df[close_col], -1, 0)
            )
            new_columns_series.append(pd.Series(target_direction_series, name=target_col, index=df.index))
            added_targets += 1
        else:
            logger.warning(f"  Warning: Column {close_col} not found. Skipped.")
    logger.info(f"Added {added_targets} target variables TARGET_DIRECTION_*.")
    if new_columns_series:
        logger.info(f"  Combining {len(new_columns_series)} new TARGET_DIRECTION columns...")
        new_columns_df = pd.concat(new_columns_series, axis=1)
        df = pd.concat([df, new_columns_df], axis=1)
        logger.info("  All new TARGET_DIRECTION columns successfully added.")
    else:
        logger.info("  No new TARGET_DIRECTION columns created.")
    return df

def save_dataset(df, filename):
    """Сохраняет датасет в CSV файл."""
    if df.empty:
        logger.error("DataFrame is empty, file will not be created.")
        return False
    logger.info(f"\nSaving updated dataset to {filename}...")
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)  # Создаем директорию
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info("Updated dataset saved.")
        return True
    except IOError as e:
        logger.error(f"Error saving file: {e}")
        return False

def main():
    """Основная функция."""
    try:
        logger.info("Starting creation of dataset with TARGET_DIRECTION for ALL stocks...")
        df = load_dataset(INPUT_DATASET_FILE)
        if df.empty:
            logger.error("Failed to load dataset. Exiting.")
            sys.exit(1)
        df_with_targets = add_target_directions_for_all_tickers(df)
        if save_dataset(df_with_targets, OUTPUT_DATASET_FILE):
            logger.info("Creation of dataset with TARGET_DIRECTION for ALL stocks completed.")
            sys.exit(0)
        else:
            logger.error("Failed to save dataset. Exiting.")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
