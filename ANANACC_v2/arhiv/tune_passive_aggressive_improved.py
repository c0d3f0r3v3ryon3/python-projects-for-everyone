# tune_passive_aggressive_improved.py (полная прокачанная версия)
import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import os
import time
from datetime import datetime
import json
import logging
import argparse
import warnings
warnings.filterwarnings('ignore')

parser = argparse.ArgumentParser()
parser.addArgument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('tune_passive_aggressive_improved.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset.csv')
TARGET_COLUMN = 'TARGET_DIRECTION'
DATE_COLUMN = 'TRADEDATE'
TEST_SIZE = 0.2
RANDOM_STATE = 42
PARAM_GRID = {
    'loss': ['hinge', 'log_loss', 'modified_huber'],
    'alpha': [0.0001, 0.001, 0.01],
    'learning_rate': ['constant', 'adaptive'],
    'eta0': [0.01, 0.1, 1.0],
    'penalty': ['l2', 'l1'],
    'max_iter': [1000, 2000],
    'tol': [1e-3],
}
CV_FOLDS = 3
USE_TIMESERIES_SPLIT = False

def load_and_prepare_data(filename):
    """Загружает и подготавливает датасет для обучения."""
    logger.info(f"Loading dataset from {filename}...")
    if not os.path.exists(filename):
        logger.error(f"File {filename} not found.")
        return None, None, None, None
    df = pd.read_csv(filename, encoding='utf-8-sig')
    logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
    if TARGET_COLUMN not in df.columns:
        logger.error(f"Target variable '{TARGET_COLUMN}' not found in dataset.")
        return None, None, None, None
    feature_columns = [col for col in df.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
    X = df[feature_columns]
    y = df[TARGET_COLUMN]
    y_not_nan_mask = ~y.isnull()
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]
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
    mask_after_fill = ~X_filtered.isnull().any(axis=1)
    X_clean = X_filtered[mask_after_fill]
    y_clean = y_filtered[mask_after_fill]
    logger.info(f"After processing missing values: {len(X_clean)} rows.")
    if len(X_clean) == 0:
        logger.error("No rows left after cleaning data.")
        return None, None, None, None
    X_train, X_test, y_train, y_test = train_test_split(
        X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )
    logger.info(f"Training sample size: {len(X_train)}")
    logger.info(f"Test sample size: {len(X_test)}")
    logger.info(f"Classes in y_train: {y_train.value_counts().sort_index().to_dict()}")
    logger.info(f"Classes in y_test: {y_test.value_counts().sort_index().to_dict()}")
    return X_train, X_test, y_train, y_test

class ProgressTracker:
    """Трекер прогресса для GridSearchCV."""
    def __init__(self, total_combinations):
        self.start_time = time.time()
        self.total = total_combinations
        self.completed = 0
        self.last_update = 0

    def update(self):
        self.completed += 1
        current_time = time.time()
        if (self.completed % max(1, self.total // 10) == 0 or
            current_time - self.last_update > 10):
            elapsed = current_time - self.start_time
            progress = (self.completed / self.total) * 100
            estimated_total = elapsed * (self.total / self.completed) if self.completed > 0 else 0
            remaining = estimated_total - elapsed
            logger.info(f"Progress: {progress:.1f}% ({self.completed}/{self.total}) | "
                        f"Elapsed: {elapsed:.0f}s | Remaining: {remaining:.0f}s")
            self.last_update = current_time

def perform_grid_search_optimized(X_train, y_train):
    """Оптимизированный GridSearch с минимальным выводом."""
    start_time = time.time()
    logger.info("\n--- Running optimized GridSearchCV ---")
    total_combinations = 1
    for v in PARAM_GRID.values():
        total_combinations *= len(v)
    total_combinations *= CV_FOLDS
    logger.info(f"Total combinations: {total_combinations}")
    logger.info(f"Parameters grid: {PARAM_GRID}")
    progress_tracker = ProgressTracker(total_combinations)
    logger.info("Scaling data...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    if USE_TIMESERIES_SPLIT:
        cv_strategy = TimeSeriesSplit(n_splits=CV_FOLDS)
        logger.info("Using TimeSeriesSplit")
    else:
        cv_strategy = CV_FOLDS
        logger.info("Using standard K-Fold")
    base_model = SGDClassifier(random_state=RANDOM_STATE)
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRID,
        cv=cv_strategy,
        scoring='accuracy',
        n_jobs=1,
        verbose=0,
        return_train_score=True
    )
    logger.info(f"Starting search at {datetime.now().strftime('%H:%M:%S')}")
    logger.info("Progress will be displayed every 10% completed combinations...")
    grid_search.fit(X_train_scaled, y_train)
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Search completed at {datetime.now().strftime('%H:%M:%S')}")
    logger.info(f"Total execution time: {duration:.2f} seconds ({duration/60:.2f} minutes)")
    return grid_search, scaler, duration

def analyze_feature_importance(best_model, feature_names, top_n=20):
    """Анализ важности признаков."""
    logger.info(f"\n--- Feature importance analysis (top-{top_n}) ---")
    if hasattr(best_model, 'coef_'):
        if len(best_model.coef_.shape) > 1:
            importance = np.mean(np.abs(best_model.coef_), axis=0)
        else:
            importance = np.abs(best_model.coef_)
        feature_imp_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        logger.info("Most important features:")
        for i, row in feature_imp_df.head(top_n).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.4f}")
        feature_imp_df.to_csv('feature_importance_sgd.csv', index=False, encoding='utf-8-sig')
        return feature_imp_df
    else:
        logger.warning("Model does not support feature importance analysis.")
        return None

def detailed_evaluation(best_model, scaler, X_test, y_test):
    """Детальная оценка модели."""
    logger.info("\n--- Evaluation on test sample ---")
    if len(y_test) == 0:
        logger.error("Test sample is empty.")
        return None, 0
    X_test_scaled = scaler.transform(X_test)
    y_pred = best_model.predict(X_test_scaled)
    test_accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Accuracy: {test_accuracy:.4f}")
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred))
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
    cv_results_df = pd.DataFrame(grid_search.cv_results_)
    top_10 = cv_results_df.nlargest(10, 'mean_test_score')[
        ['mean_test_score', 'std_test_score', 'params']
    ]
    top_10.to_csv('grid_search_sgd_top10.csv', index=False, encoding='utf-8-sig')
    results_df.to_csv('grid_search_sgd_results.csv', index=False, encoding='utf-8-sig')
    logger.info("\nResults saved:")
    logger.info("- Main results: grid_search_sgd_results.csv")
    logger.info("- Top-10 combinations: grid_search_sgd_top10.csv")
    if feature_imp_df is not None:
        logger.info("- Feature importance: feature_importance_sgd.csv")

def main():
    """Основная функция."""
    logger.info("=== OPTIMIZED HYPERPARAMETER SEARCH FOR SGDCLASSIFIER (IMPROVED) ===")
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    X_train, X_test, y_train, y_test = load_and_prepare_data(DATASET_FILE)
    if X_train is None:
        return
    grid_search_result, scaler, search_duration = perform_grid_search_optimized(X_train, y_train)
    best_model = grid_search_result.best_estimator_
    best_params = grid_search_result.best_params_
    best_cv_score = grid_search_result.best_score_
    logger.info(f"\n--- BEST PARAMETERS ---")
    logger.info(f"CV Accuracy: {best_cv_score:.4f}")
    logger.info(f"Parameters: {best_params}")
    y_pred, test_accuracy = detailed_evaluation(best_model, scaler, X_test, y_test)
    feature_names = X_train.columns.tolist()
    feature_imp_df = analyze_feature_importance(best_model, feature_names)
    save_results(grid_search_result, test_accuracy, feature_imp_df, search_duration)
    logger.info(f"\n=== SUMMARY ===")
    logger.info(f"CV Score: {best_cv_score:.4f}")
    logger.info(f"Test Score: {test_accuracy:.4f}")
    logger.info(f"Search time: {search_duration/60:.1f} minutes")
    logger.info(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
