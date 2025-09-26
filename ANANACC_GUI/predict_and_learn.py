import pandas as pd
import numpy as np
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging
import os
from datetime import datetime, timedelta
import requests

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'
BATCH_SIZE = 5

def get_real_target_directions(tickers, date):
    real_targets = {}
    for ticker in tickers:
        try:
            url = f"{MOEX_BASE_URL}/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
            params = {'iss.only': 'marketdata', 'marketdata.columns': 'CLOSE,PREVCLOSE'}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'marketdata' in data and data['marketdata']['data']:
                close = data['marketdata']['data'][0][0]
                prev_close = data['marketdata']['data'][0][1]
                real_targets[ticker] = 1 if close > prev_close else (-1 if close < prev_close else 0)
        except Exception as e:
            logger.warning(f"Ошибка получения реальных данных для {ticker}: {str(e)}")
    return real_targets

def predict_and_learn():
    try:
        if not os.path.exists('data/combined_dataset_all_targets.csv'):
            raise FileNotFoundError("Файл data/combined_dataset_all_targets.csv не найден")

        df = pd.read_csv('data/combined_dataset_all_targets.csv')
        df['Date'] = pd.to_datetime(df['Date'])
        stocks_df = pd.read_csv('data/stocks.csv')
        tickers = stocks_df['SECID'].tolist()

        feature_cols = [col for col in df.columns if col.endswith('_Open') or
                       col.endswith('_Close') or col.endswith('_Volume') or
                       col == 'KeyRate']

        # Инициализация для накопления данных
        accumulated_data = {ticker: [] for ticker in tickers}
        accuracies = {ticker: [] for ticker in tickers}

        # Симуляция новых данных (для теста)
        latest_date = df['Date'].max()
        for offset in range(1, 6):  # Симуляция 5 дней
            current_date = latest_date + timedelta(days=offset)
            real_targets = get_real_target_directions(tickers, current_date.strftime('%Y-%m-%d'))

            for ticker in tickers:
                if f'{ticker}_TARGET_DIRECTION' not in df.columns:
                    continue

                model_path = f'models/{ticker}_model.joblib'
                scaler_path = f'models/{ticker}_scaler.joblib'
                if not (os.path.exists(model_path) and os.path.exists(scaler_path)):
                    logger.warning(f"Модель или скейлер для {ticker} не найдены")
                    continue

                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)

                # Последние данные
                latest_data = df[df['Date'] == latest_date][feature_cols]
                if latest_data.empty:
                    continue

                X_scaled = scaler.transform(latest_data)
                prediction = model.predict(X_scaled)[0]

                # Проверка прогноза
                real_target = real_targets.get(ticker, 0)
                accuracy = 1 if prediction == real_target else 0
                accuracies[ticker].append(accuracy)

                # Накопление данных
                accumulated_data[ticker].append((X_scaled, real_target))

                # Инкрементальное обучение
                if len(accumulated_data[ticker]) >= BATCH_SIZE:
                    X_batch = np.vstack([x for x, _ in accumulated_data[ticker]])
                    y_batch = np.array([y for _, y in accumulated_data[ticker]])
                    model.partial_fit(X_batch, y_batch, classes=np.array([-1, 0, 1]))
                    joblib.dump(model, model_path)
                    accumulated_data[ticker] = []
                    logger.info(f"Модель для {ticker} дообучена")

        # Сохранение результатов
        results = pd.DataFrame({
            'Ticker': tickers,
            'Mean_Accuracy': [np.mean(accuracies.get(ticker, [0])) for ticker in tickers]
        })
        results.to_csv('data/prediction_results.csv', index=False)
        logger.info("Результаты прогнозов сохранены в data/prediction_results.csv")
    except Exception as e:
        logger.error(f"Ошибка в predict_and_learn: {str(e)}")
        raise

if __name__ == '__main__':
    predict_and_learn()
