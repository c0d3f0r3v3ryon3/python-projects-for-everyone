# tune_passive_aggressive_optimized.py
import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import os
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# --- Конфигурация ---
DATASET_FILE = 'combined_dataset.csv'
TARGET_COLUMN = 'TARGET_DIRECTION'
DATE_COLUMN = 'TRADEDATE'
TEST_SIZE = 0.2
RANDOM_STATE = 42

# --- Оптимизированная сетка гиперпараметров ---
PARAM_GRID = {
    'loss': ['hinge', 'log_loss', 'modified_huber'],
    'alpha': [0.0001, 0.001, 0.01],
    'learning_rate': ['constant', 'adaptive'],
    'eta0': [0.01, 0.1, 1.0],
    'penalty': ['l2', 'l1'],
    'max_iter': [1000, 2000],
    'tol': [1e-3],
}

# Количество фолдов для кросс-валидации
CV_FOLDS = 3
USE_TIMESERIES_SPLIT = False

def load_and_prepare_data(filename):
    """Загружает и подготавливает датасет для обучения."""
    print(f"Загружаю датасет из {filename}...")
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return None, None, None, None

    df = pd.read_csv(filename, encoding='utf-8-sig')
    print(f"Датасет загружен: {len(df)} строк, {len(df.columns)} столбцов.")

    if TARGET_COLUMN not in df.columns:
        print(f"Целевая переменная '{TARGET_COLUMN}' не найдена в датасете.")
        return None, None, None, None

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

    print(f"После удаления строк с пропусками в X после обработки: {len(X_clean)} строк.")

    if len(X_clean) == 0:
        print("После очистки данных не осталось строк для обучения.")
        return None, None, None, None

    # --- Разделение данных ---
    X_train, X_test, y_train, y_test = train_test_split(
        X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )

    print(f"Размер обучающей выборки: {len(X_train)}")
    print(f"Размер тестовой выборки: {len(X_test)}")
    print(f"Классы в y_train: {y_train.value_counts().sort_index().to_dict()}")
    print(f"Классы в y_test: {y_test.value_counts().sort_index().to_dict()}")

    return X_train, X_test, y_train, y_test

class ProgressTracker:
    """Трекер прогресса для GridSearchCV."""
    def __init__(self, total_combinations):
        self.start_time = time.time()
        self.total = total_combinations
        self.completed = 0
        self.last_update = 0

    def update(self):
        """Обновляет прогресс."""
        self.completed += 1
        current_time = time.time()

        # Обновляем прогресс каждые 10% или каждые 10 секунд
        if (self.completed % max(1, self.total // 10) == 0 or
            current_time - self.last_update > 10):

            elapsed = current_time - self.start_time
            progress = (self.completed / self.total) * 100
            estimated_total = elapsed * (self.total / self.completed) if self.completed > 0 else 0
            remaining = estimated_total - elapsed

            print(f"Прогресс: {progress:.1f}% ({self.completed}/{self.total}) | "
                  f"Прошло: {elapsed:.0f}с | Осталось: {remaining:.0f}с")
            self.last_update = current_time

def perform_grid_search_optimized(X_train, y_train):
    """Оптимизированный GridSearch с минимальным выводом."""
    start_time = time.time()
    print(f"\n--- Запуск оптимизированного GridSearchCV ---")

    # Вычисляем общее количество комбинаций
    total_combinations = (len(PARAM_GRID['loss']) * len(PARAM_GRID['alpha']) *
                         len(PARAM_GRID['learning_rate']) * len(PARAM_GRID['eta0']) *
                         len(PARAM_GRID['penalty']) * len(PARAM_GRID['max_iter']) *
                         len(PARAM_GRID['tol']) * CV_FOLDS)

    print(f"Всего комбинаций: {total_combinations}")
    print(f"Сетка параметров: {PARAM_GRID}")

    # Инициализируем трекер прогресса
    progress_tracker = ProgressTracker(total_combinations)

    # --- Масштабирование ---
    print("Масштабирование данных...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    # --- Настройка кросс-валидации ---
    if USE_TIMESERIES_SPLIT:
        cv_strategy = TimeSeriesSplit(n_splits=CV_FOLDS)
        print("Используется TimeSeriesSplit")
    else:
        cv_strategy = CV_FOLDS
        print("Используется стандартная K-Fold")

    # --- Создание кастомного callback ---
    def callback_function(iteration, parameters, score):
        """Callback функция для отслеживания прогресса."""
        progress_tracker.update()

    # --- Инициализация GridSearch ---
    base_model = SGDClassifier(random_state=RANDOM_STATE)

    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRID,
        cv=cv_strategy,
        scoring='accuracy',
        n_jobs=1,
        verbose=0,  # ВАЖНО: отключаем внутренний вывод GridSearch
        return_train_score=True
    )

    print(f"Начало поиска в {datetime.now().strftime('%H:%M:%S')}")
    print("Прогресс будет отображаться каждые 10% завершенных комбинаций...")

    # Запускаем GridSearch
    grid_search.fit(X_train_scaled, y_train)

    end_time = time.time()
    duration = end_time - start_time

    print(f"Поиск завершен в {datetime.now().strftime('%H:%M:%S')}")
    print(f"Общее время выполнения: {duration:.2f} секунд ({duration/60:.2f} минут)")

    return grid_search, scaler, duration

def analyze_feature_importance(best_model, feature_names, top_n=20):
    """Анализ важности признаков."""
    print(f"\n--- Анализ важности признаков (топ-{top_n}) ---")

    if hasattr(best_model, 'coef_'):
        if len(best_model.coef_.shape) > 1:
            importance = np.mean(np.abs(best_model.coef_), axis=0)
        else:
            importance = np.abs(best_model.coef_)

        feature_imp_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)

        print("Самые важные признаки:")
        for i, row in feature_imp_df.head(top_n).iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        feature_imp_df.to_csv('feature_importance_sgd.csv', index=False, encoding='utf-8-sig')
        return feature_imp_df
    else:
        print("Модель не поддерживает анализ важности признаков.")
        return None

def detailed_evaluation(best_model, scaler, X_test, y_test):
    """Детальная оценка модели."""
    print("\n--- Оценка на тестовой выборке ---")

    if len(y_test) == 0:
        print("Тестовая выборка пуста.")
        return None, 0

    X_test_scaled = scaler.transform(X_test)
    y_pred = best_model.predict(X_test_scaled)

    test_accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {test_accuracy:.4f}")

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    return y_pred, test_accuracy

def save_results(grid_search, test_accuracy, feature_imp_df, duration):
    """Сохраняет результаты."""
    results_df = pd.DataFrame({
        'best_params': [str(grid_search.best_params_)],
        'cv_accuracy': [grid_search.best_score_],
        'test_accuracy': [test_accuracy],
        'search_duration_seconds': [duration],
        'model_type': ['SGDClassifier'],
        'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    })

    # Сохраняем топ-10 результатов
    cv_results_df = pd.DataFrame(grid_search.cv_results_)
    top_10 = cv_results_df.nlargest(10, 'mean_test_score')[
        ['mean_test_score', 'std_test_score', 'params']
    ]
    top_10.to_csv('grid_search_sgd_top10.csv', index=False, encoding='utf-8-sig')

    results_df.to_csv('grid_search_sgd_results.csv', index=False, encoding='utf-8-sig')

    print("\nРезультаты сохранены:")
    print("- Основные результаты: grid_search_sgd_results.csv")
    print("- Топ-10 комбинаций: grid_search_sgd_top10.csv")
    if feature_imp_df is not None:
        print("- Важность признаков: feature_importance_sgd.csv")

def main():
    """Основная функция."""
    print("=== ОПТИМИЗИРОВАННЫЙ ПОИСК ГИПЕРПАРАМЕТРОВ ===")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Загрузка данных
    X_train, X_test, y_train, y_test = load_and_prepare_data(DATASET_FILE)
    if X_train is None:
        return

    # 2. Оптимизированный GridSearch
    grid_search_result, scaler, search_duration = perform_grid_search_optimized(X_train, y_train)

    best_model = grid_search_result.best_estimator_
    best_params = grid_search_result.best_params_
    best_cv_score = grid_search_result.best_score_

    print(f"\n--- ЛУЧШИЕ ПАРАМЕТРЫ ---")
    print(f"CV Accuracy: {best_cv_score:.4f}")
    print(f"Параметры: {best_params}")

    # 3. Оценка модели
    y_pred, test_accuracy = detailed_evaluation(best_model, scaler, X_test, y_test)

    # 4. Анализ признаков
    feature_names = X_train.columns.tolist()
    feature_imp_df = analyze_feature_importance(best_model, feature_names)

    # 5. Сохранение результатов
    save_results(grid_search_result, test_accuracy, feature_imp_df, search_duration)

    # 6. Итоговый отчет
    print(f"\n=== ИТОГИ ===")
    print(f"CV Score: {best_cv_score:.4f}")
    print(f"Test Score: {test_accuracy:.4f}")
    print(f"Время поиска: {search_duration/60:.1f} минут")
    print(f"Завершено: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
