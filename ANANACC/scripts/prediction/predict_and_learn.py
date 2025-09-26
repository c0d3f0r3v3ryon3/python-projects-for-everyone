# scripts/prediction/predict_and_learn.py
import pandas as pd
import joblib
import os
from datetime import datetime
from config import MODELS_DIR, SCALERS_DIR, COMBINED_DATASET_ALL_TARGETS_FILE, PREDICTIONS_LOG_FILE

def load_models():
    """Загружает все модели и scaler'ы."""
    models = {}
    scalers = {}
    for filename in os.listdir(MODELS_DIR):
        if filename.endswith('.joblib'):
            ticker = filename.replace('model_', '').replace('.joblib', '')
            models[ticker] = joblib.load(os.path.join(MODELS_DIR, filename))
            scalers[ticker] = joblib.load(os.path.join(SCALERS_DIR, f"scaler_{ticker}.joblib"))
    return models, scalers

def make_prediction(ticker, date, models, scalers):
    """Делает прогноз для одного тикера на заданную дату."""
    try:
        model = models[ticker]
        scaler = scalers[ticker]
        df = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
        features = df[df['TRADEDATE'] == date].drop(
            columns=['TRADEDATE'] + [c for c in df.columns if c.startswith('TARGET_DIRECTION_')]
        )
        if features.empty:
            return None

        features_scaled = scaler.transform(features)
        prediction = model.predict(features_scaled)[0]
        return prediction

    except Exception as e:
        print(f"Ошибка прогноза для {ticker}: {e}")
        return None

def log_prediction(ticker, date, prediction):
    """Логирует прогноз."""
    log_entry = pd.DataFrame([[date, ticker, prediction, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]],
                            columns=['TRADEDATE', 'TICKER', 'PREDICTION', 'TIMESTAMP'])
    log_entry.to_csv(PREDICTIONS_LOG_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

def check_predictions():
    """Проверяет просроченные прогнозы."""
    if not os.path.exists(PREDICTIONS_LOG_FILE):
        return pd.DataFrame()

    df_pred = pd.read_csv(PREDICTIONS_LOG_FILE)
    df_data = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
    today = datetime.now().strftime('%Y-%m-%d')

    overdue = df_pred[df_pred['TRADEDATE'] < today]
    if overdue.empty:
        return pd.DataFrame()

    results = []
    for _, row in overdue.iterrows():
        ticker = row['TICKER']
        date = row['TRADEDATE']
        pred = row['PREDICTION']

        real_target = df_data[df_data['TRADEDATE'] == date][f"TARGET_DIRECTION_{ticker}"].iloc[0]
        results.append({
            'TICKER': ticker,
            'DATE': date,
            'PREDICTION': pred,
            'REAL': real_target,
            'CORRECT': pred == real_target
        })

    return pd.DataFrame(results)

def retrain_models(results, models, scalers):
    """Дообучает модели на основе реальных данных."""
    for ticker in results['TICKER'].unique():
        model = models[ticker]
        scaler = scalers[ticker]
        ticker_data = results[results['TICKER'] == ticker]

        for _, row in ticker_data.iterrows():
            date = row['DATE']
            real = row['REAL']

            df = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
            features = df[df['TRADEDATE'] == date].drop(
                columns=['TRADEDATE'] + [c for c in df.columns if c.startswith('TARGET_DIRECTION_')]
            )
            if not features.empty:
                features_scaled = scaler.transform(features)
                model.partial_fit(features_scaled, [real], classes=[-1, 0, 1])

        # Сохранение дообученной модели
        joblib.dump(model, os.path.join(MODELS_DIR, f"model_{ticker}.joblib"))

def main():
    print("=== Прогнозирование и дообучение ===")
    models, scalers = load_models()
    if not models:
        print("Нет загруженных моделей.")
        return

    # Пример: прогноз для GAZP на сегодня
    ticker = "GAZP"
    date = datetime.now().strftime('%Y-%m-%d')
    prediction = make_prediction(ticker, date, models, scalers)
    if prediction is not None:
        print(f"Прогноз для {ticker} на {date}: {prediction}")
        log_prediction(ticker, date, prediction)

    # Проверка и дообучение
    results = check_predictions()
    if not results.empty:
        print(f"\nНайдено {len(results)} просроченных прогнозов. Дообучение...")
        retrain_models(results, models, scalers)
        print("Дообучение завершено.")
    else:
        print("Нет просроченных прогнозов для дообучения.")

if __name__ == "__main__":
    main()
