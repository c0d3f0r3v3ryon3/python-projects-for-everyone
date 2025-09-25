# combine_datasets_all_targets.py
import pandas as pd
import numpy as np
import os
from datetime import datetime

# --- Конфигурация ---
INPUT_DATASET_FILE = 'combined_dataset.csv' # Входной файл
OUTPUT_DATASET_FILE = 'combined_dataset_all_targets.csv' # Выходной файл

def load_dataset(filename):
    """Загружает датасет из CSV файла."""
    print(f"Загружаю датасет из {filename}...")
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return pd.DataFrame()

    df = pd.read_csv(filename, encoding='utf-8-sig')
    print(f"Датасет загружен: {len(df)} строк, {len(df.columns)} столбцов.")
    return df

def add_target_directions_for_all_tickers(df):
    """Добавляет колонки TARGET_DIRECTION для всех тикеров."""
    print("\n--- Добавление TARGET_DIRECTION для всех тикеров ---")

    # Находим все колонки, заканчивающиеся на _CLOSE
    close_cols = [col for col in df.columns if col.endswith('_CLOSE')]
    print(f"Найдено {len(close_cols)} колонок с ценами закрытия (_CLOSE).")

    # Извлекаем тикеры из названий колонок
    tickers = [col.replace('_CLOSE', '') for col in close_cols]
    print(f"Извлечены тикеры: {tickers[:10]}... (первые 10)")

    added_targets = 0
    for ticker in tickers:
        close_col = f"{ticker}_CLOSE"
        target_col = f"TARGET_DIRECTION_{ticker}"

        if close_col in df.columns:
            print(f"  Создание целевой переменной для {ticker}...")
            # Сдвигаем цену закрытия на один день вперед
            shifted_close = df[close_col].shift(-1)
            # Сравниваем с текущей ценой закрытия
            target_direction = np.where(
                shifted_close > df[close_col], 1,
                np.where(shifted_close < df[close_col], -1, 0)
            )
            # Добавляем новую колонку
            df[target_col] = target_direction
            added_targets += 1
        else:
            print(f"  Предупреждение: Колонка {close_col} не найдена. Пропущено.")

    print(f"Добавлено {added_targets} целевых переменных TARGET_DIRECTION_*.")
    return df

def save_dataset(df, filename):
    """Сохраняет датасет в CSV файл."""
    if df.empty:
        print("DataFrame пуст, файл не будет создан.")
        return

    print(f"\nСохранение обновленного датасета в {filename}...")
    try:
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print("Обновленный датасет сохранен.")
    except IOError as e:
        print(f"Ошибка при сохранении файла: {e}")

def main():
    """Основная функция."""
    print("Начинаю создание датасета с TARGET_DIRECTION для ВСЕХ акций...")

    # 1. Загрузка данных
    df = load_dataset(INPUT_DATASET_FILE)
    if df.empty:
        print("Не удалось загрузить датасет. Завершение.")
        return

    # 2. Добавление целевых переменных
    df_with_targets = add_target_directions_for_all_tickers(df)

    # 3. Сохранение
    save_dataset(df_with_targets, OUTPUT_DATASET_FILE)

    print("Создание датасета с TARGET_DIRECTION для ВСЕХ акций завершено.")

if __name__ == "__main__":
    main()
