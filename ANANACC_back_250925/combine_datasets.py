import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- Конфигурация ---
HISTORICAL_DATA_DIR = {
    'stocks': 'historical_data_full',
    'indices': 'historical_data_indices',
    'currency': 'historical_data_currency',
    'oil': 'historical_data_oil',
    'other': 'historical_data_other' # Для ключевой ставки и других макро данных
}
OUTPUT_FILE = 'combined_dataset.csv'

def load_csv_files_from_dir(directory):
    """Загружает все CSV-филы из директории."""
    files = []
    for filename in os.listdir(directory):
        if filename.lower().endswith('.csv'):
            filepath = os.path.join(directory, filename)
            files.append(filepath)
    return files

def load_and_standardize_data(filepath, source_type):
    """
    Загружает CSV-файл и приводит его к стандартному формату.
    Для 'other' применяется особая логика.
    """
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
        print(f"  Загружен файл: {filepath}, строки: {len(df)}")
    except Exception as e:
        print(f"  Ошибка при загрузке {filepath}: {e}")
        return pd.DataFrame()

    # Убедимся, что TRADEDATE - это datetime
    if 'TRADEDATE' not in df.columns:
        print(f"  Ошибка: TRADEDATE не найден в {filepath}")
        return pd.DataFrame()
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
    df = df.dropna(subset=['TRADEDATE']) # Убираем строки с неправильной датой

    filename = os.path.basename(filepath)
    if filename.endswith('_history.csv'):
        asset_name = filename.replace('_history.csv', '')
    elif filename.endswith('.csv'):
        asset_name = filename.replace('.csv', '')
    else:
        asset_name = filename

    # --- Особая обработка для 'other' (например, ключевая ставка) ---
    if source_type == 'other':
        print(f"  Обработка файла 'other': {asset_name} из {filepath}")
        # Предполагаем, что файл 'other' имеет формат: TRADEDATE, ИНДИКАТОР
        # Например: TRADEDATE, KEY_RATE или TRADEDATE, CBR_KEY_RATE
        # Найдем столбец с индикатором (второй столбец)
        if len(df.columns) >= 2:
            indicator_col_original = df.columns[1] # Второй столбец
            # Переименуем его в стандартный формат ASSETNAME_INDICATOR
            indicator_col_new = f"{asset_name}_{indicator_col_original}"
            df_renamed = df.rename(columns={indicator_col_original: indicator_col_new})

            # Оставляем только TRADEDATE и переименованный столбец
            df_final = df_renamed[['TRADEDATE', indicator_col_new]].copy()
            print(f"    Обработан индикатор: {indicator_col_new}")
            return df_final
        else:
            print(f"    Ошибка: Файл 'other' {filepath} не содержит столбца с индикатором.")
            return pd.DataFrame()

    # --- Стандартная обработка для stocks, indices, currency, oil ---
    required_cols = ['OPEN', 'HIGH', 'LOW', 'CLOSE']
    if not all(col in df.columns for col in required_cols):
        print(f"  Ошибка: Не все стандартные столбцы (OPEN, HIGH, LOW, CLOSE) найдены в {filepath}")
        print(f"  Найденные столбцы: {df.columns.tolist()}")
        return pd.DataFrame()

    print(f"  Обработка актива: {asset_name} (тип: {source_type})")

    # Если VOLUME нет, заполним 0
    if 'VOLUME' not in df.columns:
        df['VOLUME'] = 0
        print(f"  Внимание: VOLUME не найден в {filepath}, заполнен нулями.")

    # Переименование столбцов
    df = df.rename(columns={
        'OPEN': f'{asset_name}_OPEN',
        'HIGH': f'{asset_name}_HIGH',
        'LOW': f'{asset_name}_LOW',
        'CLOSE': f'{asset_name}_CLOSE',
        'VOLUME': f'{asset_name}_VOLUME'
    })

    # Оставляем только TRADEDATE и переименованные столбцы
    cols_to_keep = ['TRADEDATE'] + [col for col in df.columns if col != 'TRADEDATE']
    df = df[cols_to_keep]

    return df

def main():
    """Основная функция объединения."""
    print("Начинаю объединение исторических данных...")
    all_dataframes = []

    for source_type, directory in HISTORICAL_DATA_DIR.items():
        print(f"\n--- Обработка {source_type} из {directory} ---")
        if not os.path.exists(directory):
            print(f"Директория {directory} не существует, пропускаю.")
            continue

        files = load_csv_files_from_dir(directory)
        if not files:
            print(f"В директории {directory} не найдено CSV-файлов.")
            continue

        for filepath in files:
            # Пропускаем файл ошибок, если он есть
            if 'failed' in filepath.lower() and 'ticker' in filepath.lower():
                print(f"  Пропущен файл ошибок: {filepath}")
                continue

            df = load_and_standardize_data(filepath, source_type)
            if not df.empty:
                all_dataframes.append(df)
            else:
                print(f"  Пропущен файл (не содержит данных или не подходит): {filepath}")

    if not all_dataframes:
        print("\nНе удалось загрузить ни одного подходящего CSV-файла. Завершение.")
        return

    print(f"\nОбъединение {len(all_dataframes)} DataFrame'ов...")
    # Объединяем все по TRADEDATE
    # Используем 'outer' join, чтобы сохранить все даты из всех источников
    combined_df = all_dataframes[0]
    for df in all_dataframes[1:]:
        combined_df = pd.merge(combined_df, df, on='TRADEDATE', how='outer')

    combined_df = combined_df.sort_values(by='TRADEDATE').reset_index(drop=True)
    print(f"Итоговый датасет: {len(combined_df)} строк, {len(combined_df.columns)} столбцов.")
    # print(f"Столбцы: {combined_df.columns.tolist()}") # Для отладки

    # --- Обработка пропущенных значений ---
    print("\nОбработка пропущенных значений...")
    # Для цен (CLOSE, OPEN, HIGH, LOW) используем forward fill
    price_cols = [col for col in combined_df.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in combined_df.columns if '_VOLUME' in col]
    other_cols = [col for col in combined_df.columns if col not in ['TRADEDATE'] + price_cols + volume_cols]

    print(f"  Заполнение цен (forward fill): {len(price_cols)} столбцов.")
    combined_df[price_cols] = combined_df[price_cols].ffill().bfill()

    print(f"  Заполнение объемов (0): {len(volume_cols)} столбцов.")
    combined_df[volume_cols] = combined_df[volume_cols].fillna(0)

    print(f"  Заполнение других (0 или ffill): {len(other_cols)} столбцов.")
    # Для CBR_KEY_RATE (или других макроиндикаторов) используем ffill
    # Исправленная строка - правильное закрытие скобок
    macro_indicator_cols = [col for col in other_cols if any(indicator in col for indicator in ['KEY_RATE', 'RATE', 'INFLATION', 'GDP'])] # Можно расширить список
    if macro_indicator_cols:
        print(f"    Заполнение макроиндикаторов (ffill): {macro_indicator_cols}")
        combined_df[macro_indicator_cols] = combined_df[macro_indicator_cols].ffill()
        other_cols = [col for col in other_cols if col not in macro_indicator_cols]

    if other_cols:
        print(f"    Заполнение остальных (0): {other_cols}")
        combined_df[other_cols] = combined_df[other_cols].fillna(0)

    # --- Создание целевой переменной ---
    target_ticker = 'GAZP' # Выбери целевую акцию
    target_close_col = f'{target_ticker}_CLOSE'
    if target_close_col in combined_df.columns:
        print(f"\nСоздание целевой переменной для {target_ticker}...")
        target_close_series = combined_df[target_close_col].shift(-1)
        target_direction_series = np.where(
            target_close_series > combined_df[target_close_col], 1,
            np.where(target_close_series < combined_df[target_close_col], -1, 0)
        )
        # Удаляем последнюю строку, где TARGET_CLOSE - NaN
        combined_df = combined_df.iloc[:-1].copy() # .copy() создаёт новый DataFrame, устраняя фрагментацию
        combined_df['TARGET_CLOSE'] = target_close_series.iloc[:-1].values
        combined_df['TARGET_DIRECTION'] = target_direction_series[:-1]
        print(f"  Создано {len(combined_df)} строк с целевой переменной.")
    else:
        print(f"\nЦелевая акция {target_ticker} не найдена в объединенном датасете. Целевая переменная не создана.")

    # --- Сохранение ---
    print(f"\nСохранение объединенного датасета в {OUTPUT_FILE}...")
    combined_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print("Объединение данных завершено.")

if __name__ == "__main__":
    main()
