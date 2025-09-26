# train_other_models.py
import pandas as pd
import numpy as np
from sklearn.linear_model import Perceptron, PassiveAggressiveClassifier, SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import os

# --- Конфигурация ---
DATASET_FILE = 'combined_dataset.csv'
TARGET_COLUMN = 'TARGET_DIRECTION'
DATE_COLUMN = 'TRADEDATE'
TEST_SIZE = 0.2
RANDOM_STATE = 42

# --- Лучшие параметры SGDClassifier из GridSearchCV ---
# Обнови эти параметры после запуска tune_passive_aggressive.py
# Пример (замени на реальные значения из grid_search_sgd_results.csv):
BEST_SGD_PARAMS = {
    'loss': 'log_loss',
    'alpha': 0.0001,
    'learning_rate': 'constant',
    'eta0': 0.01,
    'penalty': 'l2',
    'max_iter': 1000,
    'tol': 0.001,
    'random_state': RANDOM_STATE,
}
# -------------------------------

# --- Глобальный StandardScaler ---
scaler = StandardScaler()
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
    X_train, X_test, y_train, y_test, dates_test = train_test_split(
        X_clean, y_clean, df_dates_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )

    print(f"Размер обучающей выборки: {len(X_train)}")
    print(f"Размер тестовой выборки: {len(X_test)}")
    print(f"Классы в y_train: {y_train.value_counts().sort_index()}")
    print(f"Классы в y_test: {y_test.value_counts().sort_index()}")

    return X_train, X_test, y_train, y_test, dates_test.reset_index(drop=True)

def initialize_model(model_name):
    """Инициализирует модель с заданными параметрами."""
    print(f"\n--- Инициализация модели {model_name} ---")

    if model_name == 'Perceptron':
        model = Perceptron(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)
    elif model_name == 'PassiveAggressiveClassifier':
        model = PassiveAggressiveClassifier(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)
    elif model_name == 'SGDClassifier':
        # Используем лучшие параметры из GridSearchCV
        model = SGDClassifier(**BEST_SGD_PARAMS)
    else:
        print(f"Неизвестная модель: {model_name}")
        return None

    print(f"Инициализирована модель {model_name}.")
    return model

def train_initial_model(model, X_train, y_train):
    """Обучает модель на обучающей выборке."""
    print("\n--- Обучение модели на обучающей выборке (с масштабированием) ---")
    if len(np.unique(y_train)) < 2:
        print("В обучающей выборке представлены не все классы.")
        return False

    # --- Масштабирование ---
    print("  Масштабирование обучающей выборки...")
    global scaler
    X_train_scaled = scaler.fit_transform(X_train)
    print("  Масштабирование завершено.")

    # --- Обучение ---
    print("  Обучение модели...")
    model.fit(X_train_scaled, y_train)
    print("  Модель обучена.")
    return True

def evaluate_model(model, X_test, y_test, dataset_name="Тестовая выборка"):
    """Оценивает производительность модели."""
    print(f"\n--- Оценка модели на {dataset_name} (с масштабированием) ---")
    if len(y_test) == 0:
        print("Выборка пуста, оценка невозможна.")
        return None, None, None, None

    # --- Масштабирование ---
    print("  Масштабирование тестовой выборки...")
    global scaler
    X_test_scaled = scaler.transform(X_test)
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

def perform_incremental_learning_simulation(model, X_test, y_test, test_dates, model_name):
    """Имитирует инкрементальное обучение на тестовой выборке."""
    print(f"\n--- Имитация инкрементального обучения для {model_name} ---")
    n_samples = len(X_test)
    if n_samples == 0:
        print("Тестовая выборка пуста. Имитация невозможна.")
        return

    correct_predictions = 0
    total_predictions = 0
    accuracies = []
    dates_list = []

    initial_classes = np.unique(y_test)
    print(f"Известные классы для модели: {initial_classes}")

    # --- Масштабирование ---
    print("  Масштабирование тестовой выборки для инкрементального обучения...")
    global scaler
    X_test_scaled = scaler.transform(X_test)
    print("  Масштабирование завершено.")

    for i in range(n_samples):
        X_single_scaled = X_test_scaled[i:i+1]
        y_true = y_test.iloc[i]
        current_date = test_dates.iloc[i][DATE_COLUMN]

        y_pred = model.predict(X_single_scaled)[0]

        is_correct = (y_pred == y_true)
        correct_predictions += int(is_correct)
        total_predictions += 1
        current_accuracy = correct_predictions / total_predictions
        accuracies.append(current_accuracy)
        dates_list.append(current_date)

        if i % 50 == 0 or i == n_samples - 1:
             print(f"  Шаг {i+1}/{n_samples}: Дата={current_date}, Прогноз={y_pred}, Истина={y_true}, Точность={current_accuracy:.4f}")

        # --- Инкрементальное обучение ---
        model.partial_fit(X_single_scaled, [y_true], classes=initial_classes)

    print(f"\n--- Результаты имитации для {model_name} ---")
    print(f"Всего обработано образцов: {total_predictions}")
    print(f"Правильных прогнозов: {correct_predictions}")
    if total_predictions > 0:
        final_accuracy = correct_predictions / total_predictions
        print(f"Итоговая точность (на тестовой выборке с имитацией): {final_accuracy:.4f}")
    else:
        print("Не было сделано ни одного прогноза.")

    log_df = pd.DataFrame({
        'TRADEDATE': dates_list,
        f'{model_name}_ACCURACY_CUMULATIVE': accuracies
    })
    log_df.to_csv(f'{model_name}_incremental_log.csv', index=False, encoding='utf-8-sig')
    print(f"Лог имитации для {model_name} сохранен в '{model_name}_incremental_log.csv'.")

def main():
    """Основная функция."""
    print("Начинаю эксперименты с другими моделями...")

    # 1. Загрузка данных
    X_train, X_test, y_train, y_test, test_dates = load_and_prepare_data(DATASET_FILE)
    if X_train is None or X_test is None:
        print("Не удалось загрузить или подготовить данные. Завершение.")
        return

    results_summary = []

    # 2. Тестирование моделей
    models_to_test = ['Perceptron', 'PassiveAggressiveClassifier', 'SGDClassifier']

    for model_name in models_to_test:
        print(f"\n{'='*20} Тестирование {model_name} {'='*20}")

        # --- Инициализация и обучение ---
        model = initialize_model(model_name)
        if model is None:
            print(f"Не удалось инициализировать модель {model_name}. Пропускаю.")
            continue

        success = train_initial_model(model, X_train, y_train)
        if not success:
            print(f"Не удалось обучить модель {model_name}. Пропускаю.")
            continue

        # --- Оценка ДО имитации ---
        print(f"\n[ЭТАП] Оценка {model_name} ПОСЛЕ начального обучения (и ДО имитации):")
        acc_before, prec_before, rec_before, f1_before = evaluate_model(model, X_test, y_test, f"Тестовая выборка (до имитации {model_name})")

        # --- Имитация инкрементального обучения ---
        perform_incremental_learning_simulation(model, X_test, y_test, test_dates, model_name)

        # --- Оценка ПОСЛЕ имитации ---
        print(f"\n[ЭТАП] Оценка {model_name} ПОСЛЕ имитации инкрементального обучения:")
        acc_after, prec_after, rec_after, f1_after = evaluate_model(model, X_test, y_test, f"Тестовая выборка (после имитации {model_name})")

        # --- Сохранение результатов ---
        results_summary.append({
            'Model': model_name,
            'Accuracy_Before': acc_before,
            'Accuracy_After': acc_after,
            'Precision_Before': prec_before,
            'Precision_After': prec_after,
            'Recall_Before': rec_before,
            'Recall_After': rec_after,
            'F1_Before': f1_before,
            'F1_After': f1_after,
        })

        print(f"\n{'='*20} Завершено тестирование {model_name} {'='*20}")

    # 3. Вывод сводки результатов
    print(f"\n{'#'*20} Сводка результатов {'#'*20}")
    if results_summary:
        summary_df = pd.DataFrame(results_summary)
        print(summary_df.to_string(index=False))

        # Сохранение сводки в CSV
        summary_df.to_csv('model_comparison_results.csv', index=False, encoding='utf-8-sig')
        print("\nСводка результатов сохранена в 'model_comparison_results.csv'.")
    else:
        print("Нет результатов для сводки.")

    print(f"\n{'#'*20} Эксперименты завершены {'#'*20}")

if __name__ == "__main__":
    main()
