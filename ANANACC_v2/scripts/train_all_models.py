# train_all_models.py
import pandas as pd
import numpy as np
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
import os
import sys
import joblib
from datetime import datetime
import json
import logging
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('train_all_models.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset_all_targets.csv')
OUTPUT_MODELS_DIR = config['models_dir']
OUTPUT_SCALERS_DIR = config['scalers_dir']
OUTPUT_RESULTS_FILE = os.path.join(config['logs_dir'], 'model_training_results.csv')
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

def load_dataset(filename):
    logger.info(f"Loading dataset from {filename}...")
    if not os.path.exists(filename):
        logger.error(f"File {filename} not found.")
        return pd.DataFrame()
    df = pd.read_csv(filename, encoding='utf-8-sig')
    logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
    return df

def prepare_features_and_target(df, target_col):
    logger.info(f"  Preparing features and target variable for {target_col}...")
    if target_col not in df.columns:
        logger.error(f"    Error: Target variable '{target_col}' not found.")
        return None, None, None, None
    target_cols_all = [col for col in df.columns if col.startswith('TARGET_DIRECTION_')]
    feature_columns = [col for col in df.columns if col not in ['TRADEDATE'] + target_cols_all]
    X = df[feature_columns]
    y = df[target_col]
    logger.info(f"    X size before missing values processing: {X.shape}")
    logger.info(f"    y size before missing values processing: {y.shape}")
    y_not_nan_mask = ~y.isnull()
    logger.info(f"    Rows where {target_col} NOT NaN: {y_not_nan_mask.sum()}")
    X_filtered = X[y_not_nan_mask]
    y_filtered = y[y_not_nan_mask]
    price_cols = [col for col in X_filtered.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in X_filtered.columns if '_VOLUME' in col]
    other_cols = [col for col in X_filtered.columns if col not in price_cols + volume_cols]
    logger.info(f"    Filling prices (ffill/bfill): {len(price_cols)} columns.")
    X_filtered[price_cols] = X_filtered[price_cols].ffill().bfill()
    logger.info(f"    Filling volumes (0): {len(volume_cols)} columns.")
    X_filtered[volume_cols] = X_filtered[volume_cols].fillna(0)
    logger.info(f"    Filling others (0 or ffill): {len(other_cols)} columns.")
    cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
    if cbr_key_rate_cols:
        logger.info(f"      Filling CBR_KEY_RATE (ffill): {cbr_key_rate_cols}")
        X_filtered[cbr_key_rate_cols] = X_filtered[cbr_key_rate_cols].ffill()
        other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
    if other_cols:
        logger.info(f"      Filling remaining (0): {other_cols}")
        X_filtered[other_cols] = X_filtered[other_cols].fillna(0)
    mask_after_fill = ~X_filtered.isnull().any(axis=1)
    X_clean = X_filtered[mask_after_fill]
    y_clean = y_filtered[mask_after_fill]
    logger.info(f"    After removing rows with missing values in X after processing: {len(X_clean)} rows.")
    if len(X_clean) == 0:
        logger.error(f"    No rows left after cleaning for {target_col}.")
        return None, None, None, None
    try:
        X_train, X_test, y_train, y_test = train_test_split(
            X_clean, y_clean, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y_clean
        )
        logger.info(f"    Training sample size: {len(X_train)}")
        logger.info(f"    Test sample size: {len(X_test)}")
        logger.info(f"    Classes in y_train: {y_train.value_counts().sort_index()}")
        logger.info(f"    Classes in y_test: {y_test.value_counts().sort_index()}")
        return X_train, X_test, y_train, y_test
    except ValueError as e:
        logger.error(f"    Error splitting data for {target_col}: {e}")
        return None, None, None, None

def initialize_model(params=None):
    if params is None:
        params = BEST_PARAMS
    model_params = params.copy()
    model = PassiveAggressiveClassifier(**model_params)
    logger.info(f"    Initialized PassiveAggressiveClassifier with parameters: {model.get_params()}")
    return model

def train_and_save_model(model, scaler, X_train, y_train, ticker):
    logger.info(f"  Training model for {ticker}...")
    if len(np.unique(y_train)) < 2:
        logger.error(f"    Not all classes represented in training sample for {ticker}.")
        return False
    X_train_scaled = scaler.fit_transform(X_train)
    model.fit(X_train_scaled, y_train)
    logger.info(f"    Model for {ticker} trained.")
    os.makedirs(OUTPUT_MODELS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_SCALERS_DIR, exist_ok=True)
    model_filename = os.path.join(OUTPUT_MODELS_DIR, f'model_{ticker}.joblib')
    scaler_filename = os.path.join(OUTPUT_SCALERS_DIR, f'scaler_{ticker}.joblib')
    try:
        joblib.dump(model, model_filename)
        joblib.dump(scaler, scaler_filename)
        logger.info(f"    Model for {ticker} saved to {model_filename}")
        logger.info(f"    Scaler for {ticker} saved to {scaler_filename}")
        return True
    except IOError as e:
        logger.error(f"    Error saving model/scaler for {ticker}: {e}")
        return False

def evaluate_model(model, scaler, X_test, y_test, ticker):
    logger.info(f"  Evaluating model for {ticker}...")
    if len(y_test) == 0:
        logger.error(f"    Test sample for {ticker} is empty.")
        return None, None, None, None
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    unique_labels = np.unique(np.concatenate([y_test, y_pred]))
    precision = precision_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', labels=unique_labels, zero_division=0)
    logger.info(f"    Accuracy for {ticker}: {accuracy:.4f}")
    logger.info(f"    Precision for {ticker}: {precision:.4f}")
    logger.info(f"    Recall for {ticker}: {recall:.4f}")
    logger.info(f"    F1-score for {ticker}: {f1:.4f}")
    return accuracy, precision, recall, f1

def main():
    try:
        logger.info("Starting training models for ALL stocks...")
        df = load_dataset(DATASET_FILE)
        if df.empty:
            logger.error("Failed to load dataset. Exiting.")
            sys.exit(1)
        target_cols_all = [col for col in df.columns if col.startswith('TARGET_DIRECTION_')]
        tickers = [col.replace('TARGET_DIRECTION_', '') for col in target_cols_all]
        logger.info(f"Found {len(target_cols_all)} target variables for {len(tickers)} stocks.")
        results = []
        for i, (target_col, ticker) in enumerate(zip(target_cols_all, tickers)):
            logger.info(f"\n--- Processing {i+1}/{len(tickers)}: {ticker} ---")
            X_train, X_test, y_train, y_test = prepare_features_and_target(df, target_col)
            if X_train is None or X_test is None:
                logger.warning(f"  Skipped {ticker} due to data errors.")
                results.append({
                    'TICKER': ticker,
                    'ACCURACY': np.nan,
                    'PRECISION': np.nan,
                    'RECALL': np.nan,
                    'F1_SCORE': np.nan,
                    'STATUS': 'FAILED_TO_PREPARE_DATA'
                })
                continue
            model = initialize_model()
            scaler = StandardScaler()
            success = train_and_save_model(model, scaler, X_train, y_train, ticker)
            if not success:
                logger.warning(f"  Failed to train or save model for {ticker}.")
                results.append({
                    'TICKER': ticker,
                    'ACCURACY': np.nan,
                    'PRECISION': np.nan,
                    'RECALL': np.nan,
                    'F1_SCORE': np.nan,
                    'STATUS': 'FAILED_TO_TRAIN_OR_SAVE'
                })
                continue
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
        logger.info(f"\n--- Saving training results for {len(results)} models ---")
        results_df = pd.DataFrame(results)
        try:
            os.makedirs(os.path.dirname(OUTPUT_RESULTS_FILE), exist_ok=True)  # Создаем директорию logs
            results_df.to_csv(OUTPUT_RESULTS_FILE, index=False, encoding='utf-8-sig')
            logger.info(f"Training results saved to {OUTPUT_RESULTS_FILE}")
        except IOError as e:
            logger.error(f"Error saving results: {e}")
            sys.exit(1)
        logger.info("Training models for ALL stocks completed.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
