# scripts/data_processing/combine_datasets_all_targets.py
import pandas as pd
import numpy as np
import os
from config import COMBINED_DATASET_FILE, COMBINED_DATASET_ALL_TARGETS_FILE

def add_target_directions(df):
    """Добавляет TARGET_DIRECTION для всех тикеров."""
    close_cols = [col for col in df.columns if col.endswith('_CLOSE')]
    tickers = [col.replace('_CLOSE', '') for col in close_cols]

    for ticker in tickers:
        close_col = f"{ticker}_CLOSE"
        target_col = f"TARGET_DIRECTION_{ticker}"
        if close_col in df.columns:
            df[target_col] = np.where(
                df[close_col].shift(-1) > df[close_col], 1,
                np.where(df[close_col].shift(-1) < df[close_col], -1, 0)
            )

    return df.dropna().reset_index(drop=True)

def main():
    print("=== Добавление TARGET_DIRECTION для всех акций ===")
    if not os.path.exists(COMBINED_DATASET_FILE):
        print(f"Файл {COMBINED_DATASET_FILE} не найден.")
        return

    df = pd.read_csv(COMBINED_DATASET_FILE)
    df_with_targets = add_target_directions(df)
    df_with_targets.to_csv(COMBINED_DATASET_ALL_TARGETS_FILE, index=False, encoding='utf-8-sig')
    print(f"Результат сохранен в {COMBINED_DATASET_ALL_TARGETS_FILE}")

if __name__ == "__main__":
    main()
