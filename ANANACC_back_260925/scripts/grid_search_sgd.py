# grid_search_sgd.py
import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score
import os

# --- Конфигурация ---
DATASET_FILE = 'combined_dataset.csv'
TARGET_COLUMN = 'TARGET_DIRECTION'
DATE_COLUMN = 'TRADEDATE'
TEST_SIZE = 0.2
RANDOM_STATE = 42

# --- Гиперпараметры для GridSearch ---
# Определим сетку параметров для поиска
PARAM_GRID = {
    'alpha': [0.0001, 0.001, 0.01],  # Коэффициент регуляризации
    'learning_rate': ['constant', 'optimal', 'adaptive'], # Тип скорости обучения
    'eta0': [0.01, 0.1, 1.0],       # Начальная скорость обучения (важна для 'constant', 'adaptive')
    # 'penalty': ['l2', 'l1', 'elasticnet'], # Тип регуляризации (убираем elasticnet для простоты, требует l1_ratio)
    'loss': ['hinge', 'log_loss', 'modified_huber'], # Функция потерь
    # max_iter и tol оставим стандартными для GridSearchCV
    # tol по умолчанию 1e-4, max_iter по умолчанию 1000 в SGDClassifier
}

# Количество фолдов для кросс-валидации
CV_FOLDS = 3 # Используем 3, так как данные временные, 5 может быть много

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

    feature_columns = [col for col in df.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
    X = df[feature_columns]
    y = df[TARGET_COLUMN]

    # --- Обработка пропусков в y ---
    y_not_nan_mask = ~y.isnull()
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]

    # --- Обработка пропусков в X ---
    price_cols = [col for col in X_filtered.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in X_filtered.columns if '_VOLUME' in col]
    other_cols = [col for col in X_filtered.columns if col not in price_cols + volume_cols]

    X_filtered[price_cols] = X_filtered[price_cols].ffill().bfill()
    X_filtered[volume_cols] = X_filtered[volume_cols].fillna(0)
    cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
    if cbr_key_rate_cols:
        X_filtered[cbr_key_rate_cols] = X_filtered[cbr_key_rate_cols].ffill()
        other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
    X_filtered[other_cols] = X_filtered[other_cols].fillna(0)

    # --- Удаление строк с оставшимися NaN в X ---
    mask_after_fill = ~X_filtered.isnull().any(axis=1)
    X_clean = X_filtered[mask_after_fill]
    y_clean = y_filtered[mask_after_fill]

    print(f"После обработки пропусков: {len(X_clean)} строк.")

    if len(X_clean) == 0:
        print("После очистки данных не осталось строк для обучения.")
        return None, None, None, None, None

    # --- Разделение данных ---
    X_train, X_test, y_train, y_test, dates_train, dates_test = train_test_split(
        X_clean, y_clean, df.loc[X_clean.index, [DATE_COLUMN]], # Используем df.loc для получения дат
        test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )

    print(f"Размер обучающей выборки: {len(X_train)}")
    print(f"Размер тестовой выборки: {len(X_test)}")

    return X_train, X_test, y_train, y_test, dates_test.reset_index(drop=True)

def perform_grid_search(X_train, y_train):
    """Выполняет GridSearchCV для SGDClassifier."""
    print("\n--- Запуск GridSearchCV для SGDClassifier ---")
    print(f"Сетка параметров: {PARAM_GRID}")
    print(f"Количество фолдов CV: {CV_FOLDS}")

    # --- Масштабирование ---
    print("  Масштабирование обучающей выборки...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    print("  Масштабирование завершено.")

    # --- Инициализация модели и GridSearch ---
    # Используем базовые параметры, которые точно работают
    base_model = SGDClassifier(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)

    # GridSearchCV
    # cv=CV_FOLDS для временных рядов может не быть идеальным, но для начала сойдет
    # scoring='accuracy' - метрика для оптимизации
    # n_jobs=1 - использовать 1 ядро CPU
    # verbose=1 - показывать прогресс
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRID,
        cv=CV_FOLDS,
        scoring='accuracy',
        n_jobs=1, # Используем 1 ядро, чтобы избежать проблем с памятью
        verbose=1
    )

    # --- Поиск ---
    print("  Начинаю поиск лучших параметров...")
    grid_search.fit(X_train_scaled, y_train)
    print("  Поиск лучших параметров завершен.")

    # --- Результаты ---
    print("\n--- Результаты GridSearchCV ---")
    print(f"Лучшие параметры: {grid_search.best_params_}")
    print(f"Лучший средний скор (accuracy) на CV: {grid_search.best_score_:.4f}")

    # Возвращаем grid_search целиком, чтобы получить доступ к best_score_
    return grid_search, scaler

def evaluate_best_model(best_model, scaler, X_test, y_test):
    """Оценивает лучшую модель на тестовой выборке."""
    print("\n--- Оценка лучшей модели на тестовой выборке ---")
    X_test_scaled = scaler.transform(X_test) # Используем тот же scaler
    y_pred = best_model.predict(X_test_scaled)
    test_accuracy = accuracy_score(y_test, y_pred)
    print(f"Точность лучшей модели на тестовой выборке: {test_accuracy:.4f}")
    return test_accuracy

def main():
    """Основная функция."""
    print("Начинаю поиск лучших гиперпараметров для SGDClassifier с GridSearchCV...")

    # 1. Загрузка и подготовка данных
    X_train, X_test, y_train, y_test, test_dates = load_and_prepare_data(DATASET_FILE)
    if X_train is None:
        print("Не удалось загрузить или подготовить данные. Завершение.")
        return

    # 2. GridSearchCV
    grid_search_result, scaler = perform_grid_search(X_train, y_train)
    # Извлекаем нужные объекты из результата
    best_params = grid_search_result.best_params_
    best_model = grid_search_result.best_estimator_
    best_cv_score = grid_search_result.best_score_

    # 3. Оценка лучшей модели
    test_acc = evaluate_best_model(best_model, scaler, X_test, y_test)

    # 4. Сохранение результатов (опционально)
    results_df = pd.DataFrame([{
        'best_params': str(best_params),
        'cv_accuracy': best_cv_score, # Используем сохраненное значение
        'test_accuracy': test_acc
    }])
    results_df.to_csv('grid_search_results.csv', index=False, encoding='utf-8-sig')
    print("\nРезультаты GridSearchCV сохранены в 'grid_search_results.csv'.")

    print("\nПоиск лучших гиперпараметров завершен.")

if __name__ == "__main__":
    main()
