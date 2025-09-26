# predict_and_learn.py
import pandas as pd
import numpy as np
import joblib
import os
import sys
from datetime import datetime, timedelta
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import json
import logging
import argparse
import requests  # Для API MOEX

parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler('predict_and_learn.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_config(config_file):
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError
    with open(config_file, 'r') as f:
        return json.load(f)

config = load_config(args.config)

MODELS_DIR = config['models_dir']
SCALERS_DIR = config['scalers_dir']
DATASET_FILE = os.path.join(config['data_dir'], 'combined_dataset_all_targets.csv')
PREDICTIONS_LOG_FILE = os.path.join(config['logs_dir'], 'predictions_log.csv')
MODEL_UPDATE_LOG_FILE = os.path.join(config['logs_dir'], 'model_updates_log.csv')
TODAY = datetime.today().strftime('%Y-%m-%d')
YESTERDAY = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

def load_models_and_scalers(models_dir, scalers_dir):
    logger.info(f"Loading models from {models_dir} and scalers from {scalers_dir}...")
    models = {}
    scalers = {}
    if not os.path.exists(models_dir) or not os.path.exists(scalers_dir):
        logger.error(f"Directories {models_dir} or {scalers_dir} do not exist.")
        return models, scalers
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
    logger.info(f"Loading last {num_days} rows from {dataset_file} as new data...")
    if not os.path.exists(dataset_file):
        logger.error(f"File {dataset_file} not found.")
        return pd.DataFrame(), pd.DataFrame()
    try:
        df = pd.read_csv(dataset_file, encoding='utf-8-sig')
        logger.info(f"Dataset loaded: {len(df)} rows, {len(df.columns)} columns.")
        latest_df = df.tail(num_days).reset_index(drop=True)
        logger.info(f"Loaded last {num_days} rows.")
        dates_df = latest_df[['TRADEDATE']].copy()
        feature_columns = [col for col in df.columns if col not in ['TRADEDATE'] and not col.startswith('TARGET_DIRECTION_')]
        features_df = latest_df[feature_columns].copy()
        logger.info(f"Features (X) size: {features_df.shape}")
        logger.info(f"Dates size: {dates_df.shape}")
        return features_df, dates_df
    except Exception as e:
        logger.error(f"Error loading last data from {dataset_file}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def prepare_features(features_df, scaler, ticker):
    logger.info(f"  Preparing features for {ticker}...")
    try:
        features_scaled = scaler.transform(features_df)
        logger.info(f"    Features scaled. Shape: {features_scaled.shape}")
        return features_scaled
    except Exception as e:
        logger.error(f"    Error scaling features for {ticker}: {e}")
        return None

def make_predictions(models, scalers, features_df, dates_df):
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
                'date': dates_df.iloc[0]['TRADEDATE']
            }
            logger.info(f"  Prediction for {ticker}: {y_pred} (date: {dates_df.iloc[0]['TRADEDATE']})")
        except Exception as e:
            logger.error(f"  Error predicting for {ticker}: {e}")
    return predictions

def save_predictions(predictions, log_file):
    if not predictions:
        logger.warning("No predictions to save.")
        return
    logger.info(f"\n--- Saving predictions to {log_file} ---")
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)  # Создаем директорию logs
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
        sys.exit(1)

def get_moex_data(ticker, start_date, end_date):
    """Загружает данные с MOEX через ISS API."""
    try:
        url = f"https://iss.moex.com/iss/history/engines/stock/markets/shares/securities/{ticker}.json"
        params = {
            'from': start_date,
            'till': end_date,
            'iss.meta': 'off',
            'iss.json': 'extended',
            'history.columns': 'TRADEDATE,OPEN,HIGH,LOW,CLOSE,VOLUME'
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if 'history' not in data or not data['history']['data']:
            logger.warning(f"No data found for {ticker} from {start_date} to {end_date}")
            return pd.DataFrame()
        df = pd.DataFrame(data['history']['data'], columns=['TRADEDATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME'])
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d')
        return df
    except Exception as e:
        logger.error(f"Error fetching MOEX data for {ticker}: {e}")
        return pd.DataFrame()

def simulate_get_real_target_directions(tickers, prediction_date):
    """Симулирует TARGET_DIRECTION, загружая данные CLOSE через API MOEX."""
    logger.info(f"\n--- Simulating real TARGET_DIRECTION for {len(tickers)} tickers on date {prediction_date} ---")
    prediction_date_dt = pd.to_datetime(prediction_date, format='%Y-%m-%d', errors='coerce')
    if pd.isna(prediction_date_dt):
        logger.error(f"Invalid prediction date: {prediction_date}")
        return {}
    # Для расчета TARGET_DIRECTION нужен следующий день
    next_day = (prediction_date_dt + timedelta(days=1)).strftime('%Y-%m-%d')
    real_targets = {}
    for ticker in tickers:
        try:
            # Загружаем данные за два дня: день прогноза и следующий
            df = get_moex_data(ticker, prediction_date, next_day)
            if df.empty:
                logger.warning(f"No data for {ticker} from {prediction_date} to {next_day}")
                continue
            df = df.sort_values('TRADEDATE')
            if len(df) < 2:
                logger.warning(f"Not enough data for {ticker} to calculate TARGET_DIRECTION")
                continue
            close_today = df[df['TRADEDATE'] == prediction_date_dt]['CLOSE'].iloc[0]
            close_next = df[df['TRADEDATE'] == pd.to_datetime(next_day)]['CLOSE'].iloc[0]
            if pd.isna(close_today) or pd.isna(close_next):
                logger.warning(f"Missing CLOSE prices for {ticker} on {prediction_date} or {next_day}")
                continue
            # Вычисляем TARGET_DIRECTION: 1 (рост), 0 (без изменений), -1 (падение)
            if close_next > close_today:
                target_direction = 1
            elif close_next < close_today:
                target_direction = -1
            else:
                target_direction = 0
            real_targets[ticker] = target_direction
            logger.info(f"  Real TARGET_DIRECTION for {ticker} on {prediction_date}: {target_direction}")
        except Exception as e:
            logger.error(f"Error calculating TARGET_DIRECTION for {ticker}: {e}")
    return real_targets

def perform_incremental_learning(models, scalers, features_df, real_targets, update_log_file):
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
            os.makedirs(os.path.dirname(update_log_file), exist_ok=True)  # Создаем директорию logs
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
            sys.exit(1)
    else:
        logger.info("No models for retraining (no real labels).")

def save_updated_models(models, scalers, models_dir, scalers_dir):
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
    try:
        logger.info("=== LAUNCHING COMBAT SCRIPT FOR PREDICTION AND INCREMENTAL LEARNING ===")
        logger.info(f"Launch date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        models, scalers = load_models_and_scalers(MODELS_DIR, SCALERS_DIR)
        if not models or not scalers:
            logger.error("Failed to load models or scalers. Exiting.")
            sys.exit(1)
        features_df, dates_df = load_latest_data(DATASET_FILE, num_days=1)
        if features_df.empty or dates_df.empty:
            logger.error("Failed to load new data. Exiting.")
            sys.exit(1)
        prediction_date = dates_df.iloc[0]['TRADEDATE']
        logger.info(f"Prediction date: {prediction_date}")
        predictions = make_predictions(models, scalers, features_df, dates_df)
        if not predictions:
            logger.error("Failed to make any predictions. Exiting.")
            sys.exit(1)
        save_predictions(predictions, PREDICTIONS_LOG_FILE)
        real_targets = simulate_get_real_target_directions(list(predictions.keys()), prediction_date)
        if not real_targets:
            logger.error("Failed to get real TARGET_DIRECTION. Retraining impossible.")
            sys.exit(1)
        perform_incremental_learning(models, scalers, features_df, real_targets, MODEL_UPDATE_LOG_FILE)
        save_updated_models(models, scalers, MODELS_DIR, SCALERS_DIR)
        logger.info("\n=== COMBAT SCRIPT COMPLETED ===")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
