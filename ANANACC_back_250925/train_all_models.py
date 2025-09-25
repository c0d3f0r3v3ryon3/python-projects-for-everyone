# train_all_models.py
import pandas as pd
import numpy as np
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import os
import joblib
from datetime import datetime

# --- Конфигурация ---
DATASET_FILE = 'combined_dataset_all_targets.csv'
OUTPUT_MODELS_DIR = 'models'
OUTPUT_SCALERS_DIR = 'scalers'
OUTPUT_RESULTS_FILE = 'model_training_results.csv'
TEST_SIZE = 0.2
RANDOM_STATE = 42

# --- Лучшие гиперпараметры для PassiveAggressiveClassifier ---
# Используем те же параметры, что и раньше
BEST_PARAMS = {
    'C': 1.0,
    'loss': 'hinge',
    'average': False,
    'random_state': RANDOM_STATE,
    'max_iter': 1000,
    'tol': 1e-3,
    'fit_intercept': True,
    'shuffle': True,
}
# -------------------------------

def load_dataset(filename):
    """Загружает датасет из CSV файла."""
    print(f"Загружаю датасет из {filename}...")
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return pd.DataFrame()

    df = pd.read_csv(filename, encoding='utf-8-sig')
    print(f"Датасет загружен: {len(df)} строк, {len(df.columns)} столбцов.")
    return df

def prepare_features_and_target(df, target_col):
    """Готовит признаки (X) и целевую переменную (y) для одной модели."""
    print(f"  Подготовка признаков и целевой переменной для {target_col}...")

    if target_col not in df.columns:
        print(f"    Ошибка: Целевая переменная '{target_col}' не найдена.")
        return None, None, None

    # --- Выбор признаков ---
    # Пока используем все признаки, кроме даты и всех целевых переменных
    target_cols_all = [col for col in df.columns if col.startswith('TARGET_DIRECTION_')]
    feature_columns = [col for col in df.columns if col not in ['TRADEDATE'] + target_cols_all]
    X = df[feature_columns]
    y = df[target_col]

    print(f"    Размер X до обработки пропусков: {X.shape}")
    print(f"    Размер y до обработки пропусков: {y.shape}")

    # --- Обработка пропусков ---
    y_not_nan_mask = ~y.isnull()
    print(f"    Количество строк, где {target_col} НЕ NaN: {y_not_nan_mask.sum()}")
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]

    # Заполнение пропусков в признаках (аналогично предыдущим скриптам)
    price_cols = [col for col in X_filtered.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in X_filtered.columns if '_VOLUME' in col]
    other_cols = [col for col in X_filtered.columns if col not in price_cols + volume_cols]

    print(f"    Заполнение цен (ffill/bfill): {len(price_cols)} столбцов.")
    X_filtered[price_cols] = X_filtered[price_cols].ffill().bfill()
    print(f"    Заполнение объемов (0): {len(volume_cols)} столбцов.")
    X_filtered[volume_cols] = X_filtered[volume_cols].fillna(0)
    print(f"    Заполнение других (0 или ffill): {len(other_cols)} столбцов.")
    cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
    if cbr_key_rate_cols:
        print(f"      Заполнение CBR_KEY_RATE (ffill): {cbr_key_rate_cols}")
        X_filtered[cbr_key_rate_cols] = X_filtered[cbr_key_rate_cols].ffill()
        other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
    if other_cols:
        print(f"      Заполнение остальных (0): {other_cols}")
        X_filtered[other_cols] = X_filtered[other_cols].fillna(0)

    mask_after_fill = ~X_filtered.isnull().any(axis=1)
    X_clean = X_filtered[mask_after_fill]
    y_clean = y_filtered[mask_after_fill]

    print(f"    После удаления строк с пропусками в X после обработки: {len(X_clean)} строк.")

    if len(X_clean) == 0:
        print(f"    После очистки данных не осталось строк для обучения {target_col}.")
        return None, None, None

    # --- Разделение данных ---
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
        )
        print(f"    Размер обучающей выборки: {len(X_train)}")
        print(f"    Размер тестовой выборки: {len(X_test)}")
        print(f"    Классы в y_train: {y_train.value_counts().sort_index()}")
        print(f"    Классы в y_test: {y_test.value_counts().sort_index()}")
        return X_train, X_test, y_train, y_test
    except ValueError as e:
        print(f"    Ошибка при разделении данных для {target_col}: {e}")
        return None, None, None, None

def initialize_model(params=None):
    """Инициализирует PassiveAggressiveClassifier с заданными параметрами."""
    if params is None:
        params = BEST_PARAMS
    model_params = params.copy()
    model_params.pop('early_stopping', None)
    model_params.pop('validation_fraction', None)
    model_params.pop('n_iter_no_change', None)
    model = PassiveAggressiveClassifier(**model_params)
    print(f"    Инициализирован PassiveAggressiveClassifier с параметрами: {model.get_params()}")
    return model

def train_and_save_model(model, scaler, X_train, y_train, ticker):
    """Обучает модель и сохраняет её вместе со scaler'ом."""
    print(f"  Обучение модели для {ticker}...")
    if len(np.unique(y_train)) < 2:
        print(f"    В обучающей выборке для {ticker} представлены не все классы.")
        return False

    # Масштабирование
    X_train_scaled = scaler.fit_transform(X_train)

    # Обучение
    model.fit(X_train_scaled, y_train)
    print(f"    Модель для {ticker} обучена.")

    # Сохранение
    os.makedirs(OUTPUT_MODELS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_SCALERS_DIR, exist_ok=True)

    model_filename = os.path.join(OUTPUT_MODELS_DIR, f'model_{ticker}.joblib')
    scaler_filename = os.path.join(OUTPUT_SCALERS_DIR, f'scaler_{ticker}.joblib')

    try:
        joblib.dump(model, model_filename)
        joblib.dump(scaler, scaler_filename)
        print(f"    Модель для {ticker} сохранена в {model_filename}")
        print(f"    Scaler для {ticker} сохранен в {scaler_filename}")
        return True
    except IOError as e:
        print(f"    Ошибка при сохранении модели/scaler'а для {ticker}: {e}")
        return False

def evaluate_model(model, scaler, X_test, y_test, ticker):
    """Оценивает модель на тестовой выборке."""
    print(f"  Оценка модели для {ticker}...")
    if len(y_test) == 0:
        print(f"    Тестовая выборка для {ticker} пуста.")
        return None, None, None, None

    # Масштабирование
    X_test_scaled = scaler.transform(X_test)

    # Прогноз
    y_pred = model.predict(X_test_scaled)

    # Метрики
    accuracy = accuracy_score(y_test, y_pred)
    unique_labels = np.unique(np.concatenate([y_test, y_pred]))
    precision = precision_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)

    print(f"    Accuracy для {ticker}: {accuracy:.4f}")
    print(f"    Precision для {ticker}: {precision:.4f}")
    print(f"    Recall для {ticker}: {recall:.4f}")
    print(f"    F1-score для {ticker}: {f1:.4f}")
    return accuracy, precision, recall, f1

def main():
    """Основная функция."""
    print("Начинаю обучение моделей для ВСЕХ акций...")

    # 1. Загрузка данных
    df = load_dataset(DATASET_FILE)
    if df.empty:
        print("Не удалось загрузить датасет. Завершение.")
        return

    # 2. Поиск всех целевых переменных
    target_cols_all = [col for col in df.columns if col.startswith('TARGET_DIRECTION_')]
    tickers = [col.replace('TARGET_DIRECTION_', '') for col in target_cols_all]
    print(f"Найдено {len(target_cols_all)} целевых переменных для {len(tickers)} акций.")

    # 3. Обучение моделей
    results = []
    for i, (target_col, ticker) in enumerate(zip(target_cols_all, tickers)):
        print(f"\n--- Обработка {i+1}/{len(tickers)}: {ticker} ---")

        # Подготовка данных
        X_train, X_test, y_train, y_test = prepare_features_and_target(df, target_col)
        if X_train is None or X_test is None:
            print(f"  Пропущен {ticker} из-за ошибок в данных.")
            results.append({
                'TICKER': ticker,
                'ACCURACY': np.nan,
                'PRECISION': np.nan,
                'RECALL': np.nan,
                'F1_SCORE': np.nan,
                'STATUS': 'FAILED_TO_PREPARE_DATA'
            })
            continue

        # Инициализация
        model = initialize_model()
        scaler = StandardScaler() # Создаем новый scaler для каждой модели

        # Обучение и сохранение
        success = train_and_save_model(model, scaler, X_train, y_train, ticker)
        if not success:
            print(f"  Не удалось обучить или сохранить модель для {ticker}.")
            results.append({
                'TICKER': ticker,
                'ACCURACY': np.nan,
                'PRECISION': np.nan,
                'RECALL': np.nan,
                'F1_SCORE': np.nan,
                'STATUS': 'FAILED_TO_TRAIN_OR_SAVE'
            })
            continue

        # Оценка
        acc, prec, rec, f1 = evaluate_model(model, scaler, X_test, y_test, ticker)
        if acc is not None:
            results.append({
                'TICKER': ticker,
                'ACCURACY': acc,
                'PRECISION': prec,
                'RECALL': rec,
                'F1_SCORE': f1,
                'STATUS': 'SUCCESS'
            })
        else:
            results.append({
                'TICKER': ticker,
                'ACCURACY': np.nan,
                'PRECISION': np.nan,
                'RECALL': np.nan,
                'F1_SCORE': np.nan,
                'STATUS': 'FAILED_TO_EVALUATE'
            })

    # 4. Сохранение результатов
    print(f"\n--- Сохранение результатов обучения {len(results)} моделей ---")
    results_df = pd.DataFrame(results)
    try:
        results_df.to_csv(OUTPUT_RESULTS_FILE, index=False, encoding='utf-8-sig')
        print(f"Результаты обучения сохранены в {OUTPUT_RESULTS_FILE}")
    except IOError as e:
        print(f"Ошибка при сохранении результатов: {e}")

    print("Обучение моделей для ВСЕХ акций завершено.")

if __name__ == "__main__":
    main()
