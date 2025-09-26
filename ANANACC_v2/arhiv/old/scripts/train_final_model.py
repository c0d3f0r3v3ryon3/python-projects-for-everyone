# train_final_model.py
import pandas as pd
import numpy as np
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import joblib # Для сохранения модели и scaler'а
from datetime import datetime

# --- Конфигурация ---
DATASET_FILE = 'combined_dataset.csv'
TARGET_COLUMN = 'TARGET_DIRECTION'
DATE_COLUMN = 'TRADEDATE'
TEST_SIZE = 0.2
RANDOM_STATE = 42

# --- Лучшие гиперпараметры для PassiveAggressiveClassifier ---
# Из результатов предыдущих экспериментов
BEST_PARAMS = {
    'C': 1.0, # Коэффициент регуляризации
    'loss': 'hinge', # Функция потерь
    'average': False, # Усреднение весов
    'random_state': RANDOM_STATE,
    'max_iter': 1000, # Максимальное количество итераций
    'tol': 1e-3, # Порог останова
    'fit_intercept': True,
    'shuffle': True,
}
# -------------------------------

# --- Глобальные переменные ---
scaler = StandardScaler()
model = None
# -------------------------------

def load_and_prepare_data(filename):
    """Загружает и подготавливает датасет для обучения."""
    print(f"Загружаю датасет из {filename}...")
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return None, None, None, None, None

    df = pd.read_csv(filename, encoding='utf-8-sig')
    print(f"Датасет загружен: {len(df)} строк, {len(df.columns)} столбцов.")

    if TARGET_COLUMN not in df.columns:
        print(f"Целевая переменная '{TARGET_COLUMN}' не найдена в датасете.")
        return None, None, None, None, None

    df_dates = df[[DATE_COLUMN]].copy()

    feature_columns = [col for col in df.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
    X = df[feature_columns]
    y = df[TARGET_COLUMN]

    print(f"Размер X до обработки пропусков: {X.shape}")
    print(f"Размер y до обработки пропусков: {y.shape}")

    # --- Обработка пропусков ---
    y_not_nan_mask = ~y.isnull()
    print(f"Количество строк, где TARGET_DIRECTION НЕ NaN: {y_not_nan_mask.sum()}")
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]
    df_dates_filtered = df_dates[y_not_nan_mask]

    price_cols = [col for col in X_filtered.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in X_filtered.columns if '_VOLUME' in col]
    other_cols = [col for col in X_filtered.columns if col not in price_cols + volume_cols]

    print(f"Заполнение цен (ffill/bfill): {len(price_cols)} столбцов.")
    X_filtered[price_cols] = X_filtered[price_cols].ffill().bfill()
    print(f"Заполнение объемов (0): {len(volume_cols)} столбцов.")
    X_filtered[volume_cols] = X_filtered[volume_cols].fillna(0)
    print(f"Заполнение других (0 или ffill): {len(other_cols)} столбцов.")
    cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
    if cbr_key_rate_cols:
        print(f"    Заполнение CBR_KEY_RATE (ffill): {cbr_key_rate_cols}")
        X_filtered[cbr_key_rate_cols] = X_filtered[cbr_key_rate_cols].ffill()
        other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
    if other_cols:
        print(f"    Заполнение остальных (0): {other_cols}")
        X_filtered[other_cols] = X_filtered[other_cols].fillna(0)

    mask_after_fill = ~X_filtered.isnull().any(axis=1)
    X_clean = X_filtered[mask_after_fill]
    y_clean = y_filtered[mask_after_fill]
    df_dates_clean = df_dates_filtered[mask_after_fill]

    print(f"После удаления строк с пропусками в X после обработки: {len(X_clean)} строк.")

    if len(X_clean) == 0:
        print("После очистки данных не осталось строк для обучения.")
        return None, None, None, None, None

    # --- Разделение данных ---
    clean_indices = X_clean.index
    df_dates_for_split = df_dates.loc[clean_indices].reset_index(drop=True)
    X_for_split = X_clean.reset_index(drop=True)
    y_for_split = y_clean.reset_index(drop=True)

    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test, dates_train, dates_test = train_test_split(
        X_for_split, y_for_split, df_dates_for_split, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_for_split
    )

    print(f"Размер обучающей выборки: {len(X_train)}")
    print(f"Размер тестовой выборки: {len(X_test)}")
    print(f"Классы в y_train: {y_train.value_counts().sort_index()}")
    print(f"Классы в y_test: {y_test.value_counts().sort_index()}")

    return X_train, X_test, y_train, y_test, dates_test.reset_index(drop=True)

def initialize_model(params=None):
    """Инициализирует PassiveAggressiveClassifier с заданными параметрами."""
    if params is None:
        # Используем лучшие параметры по умолчанию
        params = BEST_PARAMS
    # Создаем копию, чтобы не изменять исходный словарь
    model_params = params.copy()
    # Убираем параметры, которые не нужны для __init__, если они есть
    model_params.pop('early_stopping', None)
    model_params.pop('validation_fraction', None)
    model_params.pop('n_iter_no_change', None)

    model = PassiveAggressiveClassifier(**model_params)
    print(f"Инициализирован PassiveAggressiveClassifier с параметрами: {model.get_params()}")
    return model

def train_initial_model(model, X_train, y_train):
    """Обучает модель на обучающей выборке."""
    print("\n--- Обучение модели на обучающей выборке (с масштабированием) ---")
    if len(np.unique(y_train)) < 2:
        print("В обучающей выборке представлены не все классы.")
        return False

    # --- Масштабирование признаков ---
    print("  Масштабирование обучающей выборки...")
    global scaler
    # Обучаем scaler на обучающей выборке и трансформируем её
    X_train_scaled = scaler.fit_transform(X_train)
    print("  Масштабирование завершено.")

    # --- Обучение модели ---
    print("  Обучение PassiveAggressiveClassifier...")
    model.fit(X_train_scaled, y_train)
    print("  Модель обучена.")
    return True

def evaluate_model(model, X_test, y_test, dataset_name="Тестовая выборка"):
    """Оценивает производительность модели."""
    print(f"\n--- Оценка модели на {dataset_name} (с масштабированием) ---")
    if len(y_test) == 0:
        print("Выборка пуста, оценка невозможна.")
        return None, None, None, None

    # --- Масштабирование тестовой выборки ---
    print("  Масштабирование тестовой выборки...")
    global scaler
    X_test_scaled = scaler.transform(X_test) # Только transform!
    print("  Масштабирование завершено.")

    # --- Прогноз ---
    y_pred = model.predict(X_test_scaled)

    # --- Расчет метрик ---
    accuracy = accuracy_score(y_test, y_pred)
    unique_labels = np.unique(np.concatenate([y_test, y_pred]))
    precision = precision_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-score: {f1:.4f}")
    return accuracy, precision, recall, f1

def perform_incremental_learning(model, X_test, y_test, test_dates):
    """Выполняет полноценное инкрементальное обучение на тестовой выборке."""
    print("\n--- Запуск полноценного инкрементального обучения (с масштабированием) ---")
    n_samples = len(X_test)
    if n_samples == 0:
        print("Тестовая выборка пуста. Инкрементальное обучение невозможно.")
        return

    correct_predictions = 0
    total_predictions = 0
    accuracies = []
    dates_list = []

    initial_classes = np.unique(y_test)
    print(f"Известные классы для модели: {initial_classes}")

    # --- Масштабирование тестовой выборки ---
    print("  Масштабирование тестовой выборки для инкрементального обучения...")
    global scaler
    X_test_scaled = scaler.transform(X_test) # Только transform!
    print("  Масштабирование завершено.")

    for i in range(n_samples):
        # Извлекаем ОДИН масштабированный образец
        X_single_scaled = X_test_scaled[i:i+1] # Сохраняем форму (1, n_features)
        y_true = y_test.iloc[i]
        current_date = test_dates.iloc[i][DATE_COLUMN]

        # Делаем прогноз
        y_pred = model.predict(X_single_scaled)[0]

        # Сравниваем с истиной
        is_correct = (y_pred == y_true)
        correct_predictions += int(is_correct)
        total_predictions += 1
        current_accuracy = correct_predictions / total_predictions
        accuracies.append(current_accuracy)
        dates_list.append(current_date)

        if i % 50 == 0 or i == n_samples - 1:
             print(f"  Шаг {i+1}/{n_samples}: Дата={current_date}, Прогноз={y_pred}, Истина={y_true}, Точность={current_accuracy:.4f}")

        # --- КЛЮЧЕВОЙ МОМЕНТ: Инкрементальное обучение ---
        # Используем МАСШТАБИРОВАННЫЙ образец и истинную метку
        model.partial_fit(X_single_scaled, [y_true], classes=initial_classes)

    print(f"\n--- Результаты инкрементального обучения ---")
    print(f"Всего обработано образцов: {total_predictions}")
    print(f"Правильных прогнозов: {correct_predictions}")
    if total_predictions > 0:
        final_accuracy = correct_predictions / total_predictions
        print(f"Итоговая точность (на тестовой выборке с инкрементальным обучением): {final_accuracy:.4f}")
    else:
        print("Не было сделано ни одного прогноза.")

    log_df = pd.DataFrame({
        'TRADEDATE': dates_list,
        'ACCURACY_CUMULATIVE': accuracies
    })
    log_df.to_csv('incremental_learning_log_final.csv', index=False, encoding='utf-8-sig')
    print("Лог инкрементального обучения (финальный) сохранен в 'incremental_learning_log_final.csv'.")

def save_model_and_scaler(model, scaler, filename_prefix='final_model'):
    """Сохраняет модель и scaler в файлы."""
    try:
        model_filename = f"{filename_prefix}.joblib"
        scaler_filename = f"{filename_prefix}_scaler.joblib"
        joblib.dump(model, model_filename)
        joblib.dump(scaler, scaler_filename)
        print(f"Модель сохранена в {model_filename}")
        print(f"Scaler сохранен в {scaler_filename}")
    except Exception as e:
        print(f"Ошибка при сохранении модели или scaler'а: {e}")

def main():
    """Основная функция."""
    print("Начинаю обучение финальной модели PassiveAggressiveClassifier с инкрементальным обучением...")
    X_train, X_test, y_train, y_test, test_dates = load_and_prepare_data(DATASET_FILE)

    if X_train is None or X_test is None:
        print("Не удалось загрузить или подготовить данные. Завершение.")
        return

    # --- Инициализация и обучение ---
    global model
    model = initialize_model()
    success = train_initial_model(model, X_train, y_train)
    if not success:
        print("Обучение модели невозможно.")
        return

    # --- Оценка до инкрементного обучения ---
    print("\n[ЭТАП 1] Оценка модели ПОСЛЕ начального обучения (и ДО инкрементного):")
    evaluate_model(model, X_test, y_test, "Тестовая выборка (до инкрементного)")

    # --- Инкрементальное обучение ---
    print("\n[ЭТАП 2] Инкрементальное обучение на тестовой выборке...")
    perform_incremental_learning(model, X_test, y_test, test_dates)

    # --- Оценка ПОСЛЕ инкрементного обучения ---
    print("\n[ЭТАП 3] Оценка модели ПОСЛЕ инкрементального обучения (на том же тесте):")
    evaluate_model(model, X_test, y_test, "Тестовая выборка (после инкрементного)")

    # --- Сохранение финальной модели и scaler'а ---
    print("\n--- Сохранение финальной модели и scaler'а ---")
    save_model_and_scaler(model, scaler, filename_prefix='final_model_pa')

    print("\nОбучение финальной модели PassiveAggressiveClassifier с инкрементальным обучением завершено.")

if __name__ == "__main__":
    main()
