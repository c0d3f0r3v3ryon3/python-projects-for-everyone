# grid_search_sgd.py (полная прокачанная версия)
import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score
import os
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.addArgument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('grid_search_sgd.log'), logging.StreamHandler()])
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
    'alpha': [0.0001, 0.001, 0.01],
    'learning_rate': ['constant', 'optimal', 'adaptive'],
    'eta0': [0.01, 0.1, 1.0],
    'loss': ['hinge', 'log_loss', 'modified_huber'],
}
CV_FOLDS = 3

def load_and_prepare_data(filename):
    """Загружает и подготавливает датасет для обучения."""
    logger.info(f"Loading dataset from {filename}...")
    if not os.path.exists(filename):
        logger.error(f"File {filename} not found.")
        return None, None, None, None, None
    df = pd.read_csv(filename, encoding='utf-8-sig')
    logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
    if TARGET_COLUMN not in df.columns:
        logger.error(f"Target variable '{TARGET_COLUMN}' not found in dataset.")
        return None, None, None, None, None
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
        return None, None, None, None, None
    X_train, X_test, y_train, y_test = train_test_split(
        X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )
    logger.info(f"Training sample size: {len(X_train)}")
    logger.info(f"Test sample size: {len(X_test)}")
    return X_train, X_test, y_train, y_test, None

def perform_grid_search(X_train, y_train):
    """Выполняет GridSearchCV для SGDClassifier."""
    logger.info("\n--- Running GridSearchCV for SGDClassifier ---")
    logger.info(f"Parameters grid: {PARAM_GRID}")
    logger.info(f"CV folds count: {CV_FOLDS}")
    logger.info("  Scaling training sample...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    logger.info("  Scaling completed.")
    base_model = SGDClassifier(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)
    grid_search = GridSearchCV(
        estimator=base_model,
        param_grid=PARAM_GRID,
        cv=CV_FOLDS,
        scoring='accuracy',
        n_jobs=1,
        verbose=1
    )
    logger.info("  Starting search for best parameters...")
    grid_search.fit(X_train_scaled, y_train)
    logger.info("  Search for best parameters completed.")
    logger.info("\n--- GridSearchCV Results ---")
    logger.info(f"Best parameters: {grid_search.best_params_}")
    logger.info(f"Best average score (accuracy) on CV: {grid_search.best_score_:.4f}")
    return grid_search, scaler

def evaluate_best_model(best_model, scaler, X_test, y_test):
    """Оценивает лучшую модель на тестовой выборке."""
    logger.info("\n--- Evaluating best model on test sample ---")
    X_test_scaled = scaler.transform(X_test)
    y_pred = best_model.predict(X_test_scaled)
    test_accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Best model accuracy on test sample: {test_accuracy:.4f}")
    return test_accuracy

def main():
    """Основная функция."""
    logger.info("Starting search for best hyperparameters for SGDClassifier with GridSearchCV...")
    X_train, X_test, y_train, y_test, _ = load_and_prepare_data(DATASET_FILE)
    if X_train is None:
        logger.error("Failed to load or prepare data. Exiting.")
        return
    grid_search_result, scaler = perform_grid_search(X_train, y_train)
    best_params = grid_search_result.best_params_
    best_model = grid_search_result.best_estimator_
    best_cv_score = grid_search_result.best_score_
    test_acc = evaluate_best_model(best_model, scaler, X_test, y_test)
    results_df = pd.DataFrame([{
        'best_params': str(best_params),
        'cv_accuracy': best_cv_score,
        'test_accuracy': test_acc
    }])
    results_df.to_csv('grid_search_results.csv', index=False, encoding='utf-8-sig')
    logger.info("\nGridSearchCV results saved to 'grid_search_results.csv'.")
    logger.info("\nSearch for best hyperparameters completed.")

if __name__ == "__main__":
    main()
