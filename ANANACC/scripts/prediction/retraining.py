# scripts/prediction/retraining.py
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
            ticker = filename.replace('model_', '').replace('.joblib', '').split('_')[0]  # Для model_GAZP_sgd.joblib → GAZP
            models[ticker] = joblib.load(os.path.join(MODELS_DIR, filename))
            scaler_filename = f"scaler_{ticker}.joblib" if "_sgd" not in filename else f"scaler_{ticker}_sgd.joblib"
            scalers[ticker] = joblib.load(os.path.join(SCALERS_DIR, scaler_filename))
    return models, scalers

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

        real_target_col = f"TARGET_DIRECTION_{ticker}"
        if real_target_col not in df_data.columns:
            continue

        real_target = df_data[df_data['TRADEDATE'] == date][real_target_col].iloc[0]
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
        if ticker not in models:
            continue

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
        model_filename = f"model_{ticker}.joblib" if not hasattr(model, 'loss_function') else f"model_{ticker}_sgd.joblib"
        joblib.dump(model, os.path.join(MODELS_DIR, model_filename))

def main():
    print("=== Дообучение моделей ===")
    models, scalers = load_models()
    if not models:
        print("Нет загруженных моделей.")
        return

    results = check_predictions()
    if results.empty:
        print("Нет просроченных прогнозов для дообучения.")
        return

    print(f"Найдено {len(results)} просроченных прогнозов. Дообучение...")
    retrain_models(results, models, scalers)
    print("Дообучение завершено.")

if __name__ == "__main__":
    main()
