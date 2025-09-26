# scripts/data_processing/combine_datasets.py
import pandas as pd
import numpy as np
import os
from config import HISTORICAL_DATA_DIR, COMBINED_DATASET_FILE

def load_and_standardize_data(filepath, source_type):
    """Загружает и стандартизирует данные из CSV."""
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        if 'TRADEDATE' not in df.columns:
            return pd.DataFrame()

        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
        df = df.dropna(subset=['TRADEDATE'])

        # Определение имени актива
        filename = os.path.basename(filepath)
        asset_name = filename.replace('_history.csv', '').replace('.csv', '')

        # Обработка для макроэкономических данных
        if source_type == 'other':
            if len(df.columns) >= 2:
                indicator_col = df.columns[1]
                new_col = f"{asset_name}_{indicator_col}"
                return df.rename(columns={indicator_col: new_col})[['TRADEDATE', new_col]]
            return pd.DataFrame()

        # Стандартная обработка для акций/индексов/валют
        required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
        if not all(col in df.columns for col in required_cols):
            return pd.DataFrame()

        df = df.rename(columns={
            'OPEN': f'{asset_name}_OPEN',
            'HIGH': f'{asset_name}_HIGH',
            'LOW': f'{asset_name}_LOW',
            'CLOSE': f'{asset_name}_CLOSE',
            'VOLUME': f'{asset_name}_VOLUME' if 'VOLUME' in df.columns else None
        })
        cols = ['TRADEDATE'] + [col for col in df.columns if col != 'TRADEDATE']
        return df[cols]

    except Exception as e:
        print(f"Ошибка обработки {filepath}: {e}")
        return pd.DataFrame()

def main():
    print("=== Объединение исторических данных ===")
    all_dfs = []

    for source_type, directory in HISTORICAL_DATA_DIR.items():
        print(f"\n--- Обработка {source_type} ---")
        if not os.path.exists(directory):
            print(f"Директория {directory} не существует.")
            continue

        for filename in os.listdir(directory):
            if not filename.endswith('.csv') or 'failed' in filename:
                continue

            filepath = os.path.join(directory, filename)
            df = load_and_standardize_data(filepath, source_type)
            if not df.empty:
                all_dfs.append(df)

    if not all_dfs:
        print("Нет данных для объединения.")
        return

    # Объединение всех DataFrame по TRADEDATE
    combined_df = all_dfs[0]
    for df in all_dfs[1:]:
        combined_df = pd.merge(combined_df, df, on='TRADEDATE', how='outer')

    combined_df = combined_df.sort_values('TRADEDATE').reset_index(drop=True)
    print(f"Объединено: {len(combined_df)} строк, {len(combined_df.columns)} столбцов.")

    # Обработка пропусков
    price_cols = [col for col in combined_df.columns if any(s in col for s in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in combined_df.columns if '_VOLUME' in col]
    other_cols = [col for col in combined_df.columns if col not in ['TRADEDATE'] + price_cols + volume_cols]

    combined_df[price_cols] = combined_df[price_cols].ffill().bfill()
    combined_df[volume_cols] = combined_df[volume_cols].fillna(0)
    combined_df[other_cols] = combined_df[other_cols].fillna(0)

    # Создание целевой переменной (например, для GAZP)
    target_ticker = 'GAZP'
    target_close_col = f'{target_ticker}_CLOSE'
    if target_close_col in combined_df.columns:
        combined_df['TARGET_CLOSE'] = combined_df[target_close_col].shift(-1)
        combined_df['TARGET_DIRECTION'] = np.where(
            combined_df['TARGET_CLOSE'] > combined_df[target_close_col], 1,
            np.where(combined_df['TARGET_CLOSE'] < combined_df[target_close_col], -1, 0)
        )
        combined_df = combined_df.dropna(subset=['TARGET_DIRECTION']).reset_index(drop=True)

    # Сохранение
    combined_df.to_csv(COMBINED_DATASET_FILE, index=False, encoding='utf-8-sig')
    print(f"Результат сохранен в {COMBINED_DATASET_FILE}")

if __name__ == "__main__":
    main()
