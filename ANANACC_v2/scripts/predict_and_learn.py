# predict_and_learn.py (полная прокачанная версия)
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import json
import logging
import argparse

# Парсинг аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

def load_config(config_file):
    """Загружает конфигурационный файл."""
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError(f"Config file {config_file} not found.")
    with open(config_file, 'r') as f:
        return json.load(f)

# Загрузка конфигурации
config = load_config(args.config)

# Создание необходимых директорий
for dir_path in [
    config['data_dir'],
    config['models_dir'],
    config['scalers_dir'],
    config['logs_dir']
]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'predict_and_learn.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация путей
MODELS_DIR = config['models_dir']
SCALERS_DIR = config['scalers_dir']
DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset_all_targets.csv')
PREDICTIONS_LOG_FILE = os.path.join(config['logs_dir'], 'predictions_log.csv')
MODEL_UPDATE_LOG_FILE = os.path.join(config['logs_dir'], 'model_updates_log.csv')
DATE_COLUMN = 'TRADEDATE'
TODAY = datetime.today().strftime('%Y-%m-%d')
YESTERDAY = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

def load_models_and_scalers(models_dir, scalers_dir):
    """Загружает все модели и scaler'ы из директорий."""
    logger.info(f"Loading models from {models_dir} and scalers from {scalers_dir}...")
    models = {}
    scalers = {}
    model_files = [f for f in os.listdir(models_dir) if f.startswith('model_') and f.endswith('.joblib')]
    scaler_files = [f for f in os.listdir(scalers_dir) if f.startswith('scaler_') and f.endswith('.joblib')]
    logger.info(f"Found {len(model_files)} model files.")
    logger.info(f"Found {len(scaler_files)} scaler files.")
    for model_file in model_files:
        ticker = model_file.replace('model_', '').replace('.joblib', '')
        model_path = os.path.join(models_dir, model_file)
        try:
            model = joblib.load(model_path)
            models[ticker] = model
            logger.info(f"  Loaded model for {ticker} from {model_path}")
        except Exception as e:
            logger.error(f"  Error loading model for {ticker} from {model_path}: {e}")
    for scaler_file in scaler_files:
        ticker = scaler_file.replace('scaler_', '').replace('.joblib', '')
        scaler_path = os.path.join(scalers_dir, scaler_file)
        try:
            scaler = joblib.load(scaler_path)
            scalers[ticker] = scaler
            logger.info(f"  Loaded scaler for {ticker} from {scaler_path}")
        except Exception as e:
            logger.error(f"  Error loading scaler for {ticker} from {scaler_path}: {e}")
    logger.info(f"Successfully loaded {len(models)} models and {len(scalers)} scalers.")
    return models, scalers

def load_latest_data(dataset_file, num_days=1):
    """Загружает последние N строк из датасета как 'новые' данные."""
    logger.info(f"Loading last {num_days} rows from {dataset_file} as new data...")
    if not os.path.exists(dataset_file):
        logger.error(f"File {dataset_file} not found.")
        return pd.DataFrame(), pd.DataFrame()
    try:
        df = pd.read_csv(dataset_file, encoding='utf-8-sig')
        logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
        latest_df = df.tail(num_days).reset_index(drop=True)
        logger.info(f"Loaded last {num_days} rows.")
        dates_df = latest_df[[DATE_COLUMN]].copy()
        feature_columns = [col for col in df.columns if col not in [DATE_COLUMN] and not col.startswith('TARGET_DIRECTION_')]
        features_df = latest_df[feature_columns].copy()
        # Заполнение пропусков
        price_cols = [col for col in features_df.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
        volume_cols = [col for col in features_df.columns if '_VOLUME' in col]
        other_cols = [col for col in features_df.columns if col not in price_cols + volume_cols]
        logger.info(f"  Filling prices (ffill/bfill): {len(price_cols)} columns.")
        features_df[price_cols] = features_df[price_cols].ffill().bfill()
        logger.info(f"  Filling volumes (0): {len(volume_cols)} columns.")
        features_df[volume_cols] = features_df[volume_cols].fillna(0)
        logger.info(f"  Filling others (0 or ffill): {len(other_cols)} columns.")
        cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
        if cbr_key_rate_cols:
            logger.info(f"    Filling CBR_KEY_RATE (ffill): {cbr_key_rate_cols}")
            features_df[cbr_key_rate_cols] = features_df[cbr_key_rate_cols].ffill()
            other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
        if other_cols:
            logger.info(f"    Filling remaining (0): {other_cols}")
            features_df[other_cols] = features_df[other_cols].fillna(0)
        mask_after_fill = ~features_df.isnull().any(axis=1)
        features_df_clean = features_df[mask_after_fill]
        dates_df_clean = dates_df[mask_after_fill]
        logger.info(f"Features (X) size after cleaning: {features_df_clean.shape}")
        logger.info(f"Dates size after cleaning: {dates_df_clean.shape}")
        return features_df_clean, dates_df_clean
    except Exception as e:
        logger.error(f"Error loading last data from {dataset_file}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def prepare_features(features_df, scaler, ticker):
    """Подготавливает (масштабирует) признаки для прогноза."""
    logger.info(f"  Preparing features for {ticker}...")
    try:
        features_scaled = scaler.transform(features_df)
        logger.info(f"    Features scaled. Shape: {features_scaled.shape}")
        return features_scaled
    except Exception as e:
        logger.error(f"    Error scaling features for {ticker}: {e}")
        return None

def make_predictions(models, scalers, features_df, dates_df):
    """Делает прогнозы для всех моделей."""
    logger.info("\n--- Making predictions for all models ---")
    predictions = {}
    for ticker, model in models.items():
        scaler = scalers.get(ticker)
        if scaler is None:
            logger.warning(f"  Warning: Scaler for {ticker} not found. Skipping prediction.")
            continue
        features_scaled = prepare_features(features_df, scaler, ticker)
        if features_scaled is None:
            continue
        try:
            y_pred = model.predict(features_scaled)[0]
            predictions[ticker] = {
                'prediction': y_pred,
                'date': dates_df.iloc[0][DATE_COLUMN]
            }
            logger.info(f"  Prediction for {ticker}: {y_pred} (date: {dates_df.iloc[0][DATE_COLUMN]})")
        except Exception as e:
            logger.error(f"  Error predicting for {ticker}: {e}")
    return predictions

def save_predictions(predictions, log_file):
    """Сохраняет прогнозы в лог-файл."""
    if not predictions:
        logger.warning("No predictions to save.")
        return
    logger.info(f"\n--- Saving predictions to {log_file} ---")
    try:
        log_data = []
        for ticker, pred_info in predictions.items():
            log_data.append({
                'TICKER': ticker,
                'TRADEDATE': pred_info['date'],
                'PREDICTED_DIRECTION': pred_info['prediction'],
                'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        log_df = pd.DataFrame(log_data)
        if os.path.exists(log_file):
            log_df.to_csv(log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            logger.info(f"  Predictions added to existing log {log_file}.")
        else:
            log_df.to_csv(log_file, index=False, encoding='utf-8-sig')
            logger.info(f"  Predictions saved to new log {log_file}.")
    except Exception as e:
        logger.error(f"  Error saving predictions to {log_file}: {e}")

def simulate_get_real_target_directions(dataset_file, tickers, prediction_date):
    """Симулирует получение реальных TARGET_DIRECTION для всех тикеров."""
    logger.info(f"\n--- Simulating real TARGET_DIRECTION for {len(tickers)} tickers on date {prediction_date} ---")
    if not os.path.exists(dataset_file):
        logger.error(f"File {dataset_file} not found for simulation.")
        return {}
    try:
        df = pd.read_csv(dataset_file, encoding='utf-8-sig')
        df[DATE_COLUMN] = pd.to_datetime(df[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
        prediction_date_dt = pd.to_datetime(prediction_date, format='%Y-%m-%d', errors='coerce')
        if pd.isna(prediction_date_dt):
            logger.error(f"Invalid prediction date for simulation: {prediction_date}")
            return {}
        target_row = df[df[DATE_COLUMN] == prediction_date_dt]
        if target_row.empty:
            logger.error(f"Date {prediction_date} not found in {dataset_file} for simulation.")
            return {}
        real_targets = {}
        for ticker in tickers:
            target_col = f"TARGET_DIRECTION_{ticker}"
            if target_col in target_row.columns:
                real_value = target_row[target_col].iloc[0]
                if not pd.isna(real_value):
                    real_targets[ticker] = real_value
                    logger.info(f"  Real TARGET_DIRECTION for {ticker} on {prediction_date}: {real_value}")
                else:
                    logger.warning(f"  Real TARGET_DIRECTION for {ticker} on {prediction_date} is NaN.")
            else:
                logger.warning(f"  Column {target_col} not found in {dataset_file} for simulation.")
        return real_targets
    except Exception as e:
        logger.error(f"Error simulating real TARGET_DIRECTION: {e}")
        return {}

def perform_incremental_learning(models, scalers, features_df, real_targets, update_log_file):
    """Выполняет инкрементальное обучение для всех моделей, где есть реальная метка."""
    logger.info(f"\n--- Performing incremental learning for models with real labels ---")
    updated_models = []
    correct_predictions = 0
    total_predictions = 0
    for ticker, y_true in real_targets.items():
        model = models.get(ticker)
        scaler = scalers.get(ticker)
        if model is None or scaler is None:
            logger.warning(f"  Model or scaler for {ticker} not found. Skipping retraining.")
            continue
        features_scaled = prepare_features(features_df, scaler, ticker)
        if features_scaled is None:
            continue
        try:
            y_pred_before = model.predict(features_scaled)[0]
            is_correct = (y_pred_before == y_true)
            correct_predictions += int(is_correct)
            total_predictions += 1
            classes = np.array([-1, 0, 1])
            model.partial_fit(features_scaled, [y_true], classes=classes)
            logger.info(f"  Model for {ticker} retrained on real label {y_true}. Prediction was {y_pred_before} ({'Correct' if is_correct else 'Incorrect'}).")
            updated_models.append(ticker)
        except Exception as e:
            logger.error(f"  Error retraining model for {ticker}: {e}")
    if total_predictions > 0:
        accuracy = correct_predictions / total_predictions
        logger.info(f"\nPrediction accuracy before retraining: {accuracy:.4f} ({correct_predictions}/{total_predictions})")
        try:
            update_log_entry = pd.DataFrame([{
                'UPDATE_DATE': datetime.now().strftime('%Y-%m-%d'),
                'ACCURACY_BEFORE_UPDATE': accuracy,
                'UPDATED_MODELS_COUNT': len(updated_models),
                'UPDATED_MODELS': ', '.join(updated_models),
                'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])
            if os.path.exists(update_log_file):
                update_log_entry.to_csv(update_log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                update_log_entry.to_csv(update_log_file, index=False, encoding='utf-8-sig')
            logger.info(f"Model update log saved to {update_log_file}.")
        except Exception as e:
            logger.error(f"Error saving model update log: {e}")
    else:
        logger.info("No models for retraining (no real labels).")

def save_updated_models(models, scalers, models_dir, scalers_dir):
    """Сохраняет обновленные модели и scaler'ы."""
    logger.info(f"\n--- Saving updated models and scalers ---")
    for ticker, model in models.items():
        model_path = os.path.join(models_dir, f'model_{ticker}.joblib')
        try:
            joblib.dump(model, model_path)
            logger.info(f"  Updated model for {ticker} saved to {model_path}")
        except Exception as e:
            logger.error(f"  Error saving updated model for {ticker}: {e}")
    for ticker, scaler in scalers.items():
        scaler_path = os.path.join(scalers_dir, f'scaler_{ticker}.joblib')
        try:
            joblib.dump(scaler, scaler_path)
            logger.info(f"  Updated scaler for {ticker} saved to {scaler_path}")
        except Exception as e:
            logger.error(f"  Error saving updated scaler for {ticker}: {e}")
    logger.info("Saving updated models and scalers completed.")

def main():
    """Основная функция."""
    logger.info("=== LAUNCHING COMBAT SCRIPT FOR PREDICTION AND INCREMENTAL LEARNING ===")
    logger.info(f"Launch date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    models, scalers = load_models_and_scalers(MODELS_DIR, SCALERS_DIR)
    if not models or not scalers:
        logger.error("Failed to load models or scalers. Exiting.")
        return
    features_df, dates_df = load_latest_data(DATASET_FILE, num_days=1)
    if features_df.empty or dates_df.empty:
        logger.error("Failed to load new data. Exiting.")
        return
    prediction_date = dates_df.iloc[0][DATE_COLUMN]
    logger.info(f"Prediction date: {prediction_date}")
    predictions = make_predictions(models, scalers, features_df, dates_df)
    if not predictions:
        logger.error("Failed to make any predictions. Exiting.")
        return
    save_predictions(predictions, PREDICTIONS_LOG_FILE)
    real_targets = simulate_get_real_target_directions(DATASET_FILE, list(predictions.keys()), prediction_date)
    if not real_targets:
        logger.error("Failed to get real TARGET_DIRECTION. Retraining impossible.")
        return
    perform_incremental_learning(models, scalers, features_df, real_targets, MODEL_UPDATE_LOG_FILE)
    save_updated_models(models, scalers, MODELS_DIR, SCALERS_DIR)
    logger.info("\n=== COMBAT SCRIPT COMPLETED ===")

if __name__ == "__main__":
    main()
