# train_other_models.py (полная прокачанная версия)
import pandas as pd
import numpy as np
from sklearn.linear_model import Perceptron, PassiveAggressiveClassifier, SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import os
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.addArgument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler('train_other_models.log'), logging.StreamHandler()])
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
BEST_SGD_PARAMS = {
    'loss': 'hinge',
    'alpha': 0.001,
    'learning_rate': 'constant',
    'eta0': 0.1,
    'penalty': 'l2',
    'random_state': RANDOM_STATE,
    'max_iter': 1000,
    'tol': 1e-3,
}
scaler = StandardScaler()

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
    X_train, X_test, y_train, y_test, dates_test = train_test_split(
        X_clean, y_clean, df_dates_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
    )
    logger.info(f"Training sample size: {len(X_train)}")
    logger.info(f"Test sample size: {len(X_test)}")
    logger.info(f"Classes in y_train: {y_train.value_counts().sort_index()}")
    logger.info(f"Classes in y_test: {y_test.value_counts().sort_index()}")
    return X_train, X_test, y_train, y_test, dates_test.reset_index(drop=True)

def initialize_model(model_name):
    """Инициализирует модель с заданными параметрами."""
    logger.info(f"\n--- Initializing model {model_name} ---")
    if model_name == 'Perceptron':
        model = Perceptron(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)
    elif model_name == 'PassiveAggressiveClassifier':
        model = PassiveAggressiveClassifier(random_state=RANDOM_STATE, max_iter=1000, tol=1e-3)
    elif model_name == 'SGDClassifier':
        model = SGDClassifier(**BEST_SGD_PARAMS)
    else:
        logger.error(f"Unknown model: {model_name}")
        return None
    logger.info(f"Initialized model {model_name}.")
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

def perform_incremental_learning_simulation(model, X_test, y_test, test_dates, model_name):
    """Имитирует инкрементальное обучение на тестовой выборке."""
    logger.info(f"\n--- Simulating incremental learning for {model_name} ---")
    n_samples = len(X_test)
    if n_samples == 0:
        logger.error("Test sample is empty. Simulation impossible.")
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
    logger.info(f"\n--- Simulation results for {model_name} ---")
    logger.info(f"Total processed samples: {total_predictions}")
    logger.info(f"Correct predictions: {correct_predictions}")
    if total_predictions > 0:
        final_accuracy = correct_predictions / total_predictions
        logger.info(f"Final accuracy (on test sample with simulation): {final_accuracy:.4f}")
    else:
        logger.info("No predictions made.")
    log_df = pd.DataFrame({
        'TRADEDATE': dates_list,
        f'{model_name}_ACCURACY_CUMULATIVE': accuracies
    })
    log_file = os.path.join(config['logs_dir'], f'{model_name}_incremental_log.csv')
    log_df.to_csv(log_file, index=False, encoding='utf-8-sig')
    logger.info(f"Simulation log for {model_name} saved to '{log_file}'.")

def main():
    """Основная функция."""
    logger.info("Starting experiments with other models...")
    X_train, X_test, y_train, y_test, test_dates = load_and_prepare_data(DATASET_FILE)
    if X_train is None or X_test is None:
        logger.error("Failed to load or prepare data. Exiting.")
        return
    results_summary = []
    models_to_test = ['Perceptron', 'PassiveAggressiveClassifier', 'SGDClassifier']
    for model_name in models_to_test:
        logger.info(f"\n{'='*20} Testing {model_name} {'='*20}")
        model = initialize_model(model_name)
        if model is None:
            logger.warning(f"Failed to initialize model {model_name}. Skipping.")
            continue
        success = train_initial_model(model, X_train, y_train)
        if not success:
            logger.warning(f"Failed to train model {model_name}. Skipping.")
            continue
        logger.info(f"\n[STAGE] Evaluating {model_name} AFTER initial training (and BEFORE simulation):")
        acc_before, prec_before, rec_before, f1_before = evaluate_model(model, X_test, y_test, f"Test sample (before simulation {model_name})")
        perform_incremental_learning_simulation(model, X_test, y_test, test_dates, model_name)
        logger.info(f"\n[STAGE] Evaluating {model_name} AFTER simulation of incremental learning:")
        acc_after, prec_after, rec_after, f1_after = evaluate_model(model, X_test, y_test, f"Test sample (after simulation {model_name})")
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
        logger.info(f"\n{'='*20} Completed testing {model_name} {'='*20}")
    logger.info(f"\n{'#'*20} Results summary {'#'*20}")
    if results_summary:
        summary_df = pd.DataFrame(results_summary)
        logger.info(summary_df.to_string(index=False))
        summary_df.to_csv(os.path.join(config['logs_dir'], 'model_comparison_results.csv'), index=False, encoding='utf-8-sig')
        logger.info("\nResults summary saved to 'model_comparison_results.csv'.")
    else:
        logger.info("No results for summary.")
    logger.info(f"\n{'#'*20} Experiments completed {'#'*20}")

if __name__ == "__main__":
    main()
