import pandas as pd
import numpy as np
import os
import sys
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
for dir_path in [
    config['logs_dir'],
    config['historical_data_full_dir'],
    config['historical_data_indices_dir'],
    config['historical_data_currency_dir'],
    config['historical_data_oil_dir'],
    config['historical_data_other_dir'],
    config['data_dir']
]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'combine_datasets.log')
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
HISTORICAL_DATA_DIR = {
    'stocks': config['historical_data_full_dir'],
    'indices': config['historical_data_indices_dir'],
    'currency': config['historical_data_currency_dir'],
    'oil': config['historical_data_oil_dir'],
    'other': config['historical_data_other_dir']
}
OUTPUT_FILE = os.path.join(config['data_dir'], 'combined_dataset.csv')

def load_csv_files_from_dir(directory):
    """Загружает все CSV-файлы из директории."""
    files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.csv'):
            filepath = os.path.join(directory, filename)
            files.append(filepath)
    logger.info(f"Found {len(files)} CSV files in {directory}")
    return files

def load_and_standardize_data(filepath, source_type):
    """Загружает CSV-файл и приводит его к стандартному формату."""
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        logger.info(f"Loaded file: {filepath}, rows: {len(df)}")
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return pd.DataFrame()
    if 'TRADEDATE' not in df.columns:
        logger.error(f"TRADEDATE not found in {filepath}")
        return pd.DataFrame()
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
    df = df.dropna(subset=['TRADEDATE'])
    filename = os.path.basename(filepath)
    if filename.endswith('_history.csv'):
        asset_name = filename.replace('_history.csv', '')
    elif filename.endswith('.csv'):
        asset_name = filename.replace('.csv', '')
    else:
        asset_name = filename
    if source_type == 'other':
        logger.info(f"Processing 'other' file: {asset_name} from {filepath}")
        if len(df.columns) >= 2:
            indicator_col_original = df.columns[1]
            indicator_col_new = f"{asset_name}_{indicator_col_original}"
            df_renamed = df.rename(columns={indicator_col_original: indicator_col_new})
            df_final = df_renamed[['TRADEDATE', indicator_col_new]].copy()
            logger.info(f"    Processed indicator: {indicator_col_new}")
            return df_final
        else:
            logger.error(f"    'other' file {filepath} does not contain indicator column.")
            return pd.DataFrame()
    required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
    if not all(col in df.columns for col in required_cols):
        logger.error(f"Not all standard columns (OPEN, HIGH, LOW, CLOSE) found in {filepath}")
        logger.info(f"Found columns: {df.columns.tolist()}")
        return pd.DataFrame()
    logger.info(f"Processing asset: {asset_name} (type: {source_type})")
    if 'VOLUME' not in df.columns:
        df['VOLUME'] = 0
        logger.warning(f"VOLUME not found in {filepath}, filled with zeros.")
    df = df.rename(columns={
        'OPEN': f'{asset_name}_OPEN',
        'HIGH': f'{asset_name}_HIGH',
        'LOW': f'{asset_name}_LOW',
        'CLOSE': f'{asset_name}_CLOSE',
        'VOLUME': f'{asset_name}_VOLUME'
    })
    cols_to_keep = ['TRADEDATE'] + [col for col in df.columns if col != 'TRADEDATE']
    df = df[cols_to_keep]
    return df

def main():
    """Основная функция объединения."""
    try:
        logger.info("Starting data combining...")
        all_dataframes = []
        for source_type, directory in HISTORICAL_DATA_DIR.items():
            logger.info(f"\n--- Processing {source_type} from {directory} ---")
            if not os.path.exists(directory):
                logger.warning(f"Directory {directory} does not exist, skipping.")
                continue
            files = load_csv_files_from_dir(directory)
            if not files:
                logger.info(f"No CSV files found in directory {directory}.")
                continue
            for filepath in files:
                if 'failed' in filepath.lower() and 'ticker' in filepath.lower():
                    logger.info(f"Skipped error file: {filepath}")
                    continue
                df = load_and_standardize_data(filepath, source_type)
                if not df.empty:
                    all_dataframes.append(df)
                else:
                    logger.info(f"Skipped file (no data or unsuitable): {filepath}")
        if not all_dataframes:
            logger.error("Failed to load any suitable CSV files. Exiting.")
            sys.exit(1)
        logger.info(f"\nCombining {len(all_dataframes)} DataFrames...")
        combined_df = all_dataframes[0]
        for df in all_dataframes[1:]:
            combined_df = pd.merge(combined_df, df, on='TRADEDATE', how='outer')
        combined_df = combined_df.sort_values(by='TRADEDATE').reset_index(drop=True)
        logger.info(f"Final dataset: {len(combined_df)} rows, {len(combined_df.columns)} columns.")
        logger.info("\nProcessing missing values...")
        price_cols = [col for col in combined_df.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
        volume_cols = [col for col in combined_df.columns if '_VOLUME' in col]
        other_cols = [col for col in combined_df.columns if col not in ['TRADEDATE'] + price_cols + volume_cols]
        logger.info(f"  Filling prices (ffill/bfill): {len(price_cols)} columns.")
        combined_df[price_cols] = combined_df[price_cols].ffill().bfill()
        logger.info(f"  Filling volumes (0): {len(volume_cols)} columns.")
        combined_df[volume_cols] = combined_df[volume_cols].fillna(0)
        logger.info(f"  Filling others (0 or ffill): {len(other_cols)} columns.")
        macro_indicator_cols = [col for col in other_cols if any(indicator in col for indicator in ['KEY_RATE', 'RATE', 'INFLATION', 'GDP'])]
        if macro_indicator_cols:
            logger.info(f"    Filling macro indicators (ffill): {macro_indicator_cols}")
            combined_df[macro_indicator_cols] = combined_df[macro_indicator_cols].ffill()
            other_cols = [col for col in other_cols if col not in macro_indicator_cols]
        if other_cols:
            logger.info(f"    Filling remaining (0): {other_cols}")
            combined_df[other_cols] = combined_df[other_cols].fillna(0)
        target_ticker = 'GAZP'
        target_close_col = f'{target_ticker}_CLOSE'
        if target_close_col in combined_df.columns:
            logger.info(f"\nCreating target variable for {target_ticker}...")
            target_close_series = combined_df[target_close_col].shift(-1)
            target_direction_series = np.where(
                target_close_series > combined_df[target_close_col], 1,
                np.where(target_close_series < combined_df[target_close_col], -1, 0)
            )
            combined_df = combined_df.iloc[:-1].copy()
            combined_df['TARGET_CLOSE'] = target_close_series.iloc[:-1].values
            combined_df['TARGET_DIRECTION'] = target_direction_series[:-1]
            logger.info(f"  Created {len(combined_df)} rows with target variable.")
        else:
            logger.warning(f"\nTarget stock {target_ticker} not found in combined dataset. Target variable not created.")
        logger.info(f"\nSaving combined dataset to {OUTPUT_FILE}...")
        combined_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        logger.info("Data combining completed.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
