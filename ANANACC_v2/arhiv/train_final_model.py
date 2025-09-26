# train_final_model.py (полная прокачанная версия)
import pandas as pd
import numpy as np
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import os
import joblib
from datetime import datetime
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.addArgument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('train_final_model.log'), logging.StreamHandler()])
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
scaler = StandardScaler()
model = None

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
    df_dates = df[[DATE_COLUMN]].copy()
    feature_columns = [col for col in df.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
    X = df[feature_columns]
    y = df[TARGET_COLUMN]
    y_not_nan_mask = ~y.isnull()
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]
    df_dates_filtered = df_dates[y_not_nan_mask]
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
    df_dates_clean = df_dates_filtered[mask_after_fill]
    logger.info(f"After removing rows with missing values in X after processing: {len(X_clean)} rows.")
    if len(X_clean) == 0:
        logger.error("No rows left after cleaning data.")
        return None, None, None, None, None
    clean_indices = X_clean.index
    df_dates_for_split = df_dates.loc[clean_indices].reset_index(drop=True)
    X_for_split = X_clean.reset_index(drop=True)
    y_for_split = y_clean.reset_index(drop=True)
    X_train, X_test, y_train, y_test, dates_train, dates_test = train_test_split(
        X_for_split, y_for_split, df_dates_for_split, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_for_split
    )
    logger.info(f"Training sample size: {len(X_train)}")
    logger.info(f"Test sample size: {len(X_test)}")
    logger.info(f"Classes in y_train: {y_train.value_counts().sort_index()}")
    logger.info(f"Classes in y_test: {y_test.value_counts().sort_index()}")
    return X_train, X_test, y_train, y_test, dates_test.reset_index(drop=True)

def initialize_model(params=None):
    """Инициализирует PassiveAggressiveClassifier с заданными параметрами."""
    if params is None:
        params = BEST_PARAMS
    model_params = params.copy()
    global model
    model = PassiveAggressiveClassifier(**model_params)
    logger.info(f"Initialized PassiveAggressiveClassifier with parameters: {model.get_params()}")
    return model

def train_initial_model(model, X_train, y_train):
    """Обучает модель на обучающей выборке."""
    logger.info("\n--- Training model on training sample (with scaling) ---")
    if len(np.unique(y_train)) < 2:
        logger.error("Not all classes represented in training sample.")
        return False
    global scaler
    X_train_scaled = scaler.fit_transform(X_train)
    model.fit(X_train_scaled, y_train)
    logger.info("  Model trained.")
    return True

def evaluate_model(model, X_test, y_test, dataset_name="Test sample"):
    """Оценивает производительность модели."""
    logger.info(f"\n--- Evaluating model on {dataset_name} (with scaling) ---")
    if len(y_test) == 0:
        logger.error("Sample is empty, evaluation impossible.")
        return None, None, None, None
    global scaler
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    unique_labels = np.unique(np.concatenate([y_test, y_pred]))
    precision = precision_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    logger.info(f"Accuracy: {accuracy:.4f}")
    logger.info(f"Precision: {precision:.4f}")
    logger.info(f"Recall: {recall:.4f}")
    logger.info(f"F1-score: {f1:.4f}")
    return accuracy, precision, recall, f1

def perform_incremental_learning(model, X_test, y_test, test_dates):
    """Выполняет полноценное инкрементальное обучение на тестовой выборке."""
    logger.info("\n--- Running full incremental learning (with scaling) ---")
    n_samples = len(X_test)
    if n_samples == 0:
        logger.error("Test sample is empty. Incremental learning impossible.")
        return
    correct_predictions = 0
    total_predictions = 0
    accuracies = []
    dates_list = []
    initial_classes = np.unique(y_test)
    logger.info(f"Known classes for model: {initial_classes}")
    global scaler
    X_test_scaled = scaler.transform(X_test)
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
            logger.info(f"  Step {i+1}/{n_samples}: Date={current_date}, Prediction={y_pred}, Truth={y_true}, Accuracy={current_accuracy:.4f}")
        model.partial_fit(X_single_scaled, [y_true], classes=initial_classes)
    logger.info(f"\n--- Incremental learning results ---")
    logger.info(f"Total processed samples: {total_predictions}")
    logger.info(f"Correct predictions: {correct_predictions}")
    if total_predictions > 0:
        final_accuracy = correct_predictions / total_predictions
        logger.info(f"Final accuracy (on test sample with incremental learning): {final_accuracy:.4f}")
    else:
        logger.info("No predictions made.")
    log_df = pd.DataFrame({
        'TRADEDATE': dates_list,
        'ACCURACY_CUMULATIVE': accuracies
    })
    log_file = os.path.join(config['logs_dir'], 'incremental_learning_log_final.csv')
    log_df.to_csv(log_file, index=False, encoding='utf-8-sig')
    logger.info(f"Incremental learning log (final) saved to '{log_file}'.")

def save_model_and_scaler(model, scaler, filename_prefix='final_model'):
    """Сохраняет модель и scaler в файлы."""
    try:
        model_filename = f"{filename_prefix}.joblib"
        scaler_filename = f"{filename_prefix}_scaler.joblib"
        joblib.dump(model, model_filename)
        joblib.dump(scaler, scaler_filename)
        logger.info(f"Model saved to {model_filename}")
        logger.info(f"Scaler saved to {scaler_filename}")
    except Exception as e:
        logger.error(f"Error saving model or scaler: {e}")

def main():
    """Основная функция."""
    logger.info("Starting training of final PassiveAggressiveClassifier model with incremental learning...")
    X_train, X_test, y_train, y_test, test_dates = load_and_prepare_data(DATASET_FILE)
    if X_train is None or X_test is None:
        logger.error("Failed to load or prepare data. Exiting.")
        return
    global model
    model = initialize_model()
    success = train_initial_model(model, X_train, y_train)
    if not success:
        logger.error("Model training impossible.")
        return
    logger.info("\n[STAGE 1] Evaluating model AFTER initial training (and BEFORE incremental):")
    evaluate_model(model, X_test, y_test, "Test sample (before incremental)")
    logger.info("\n[STAGE 2] Incremental learning on test sample...")
    perform_incremental_learning(model, X_test, y_test, test_dates)
    logger.info("\n[STAGE 3] Evaluating model AFTER incremental learning (on the same test):")
    evaluate_model(model, X_test, y_test, "Test sample (after incremental)")
    logger.info("\n--- Saving final model and scaler ---")
    save_model_and_scaler(model, scaler, filename_prefix='final_model_pa')
    logger.info("\nTraining of final PassiveAggressiveClassifier model with incremental learning completed.")

if __name__ == "__main__":
    main()
