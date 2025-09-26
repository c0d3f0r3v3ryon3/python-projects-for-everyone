import pandas as pd
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.preprocessing import StandardScaler
import joblib
import logging
import os
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def train_all_models():
    try:
        if not os.path.exists('data/combined_dataset_all_targets.csv'):
            raise FileNotFoundError("Файл data/combined_dataset_all_targets.csv не найден")

        df = pd.read_csv('data/combined_dataset_all_targets.csv')
        df['Date'] = pd.to_datetime(df['Date'])
        stocks_df = pd.read_csv('data/stocks.csv')
        tickers = stocks_df['SECID'].tolist()

        if not os.path.exists('models'):
            os.makedirs('models')

        for ticker in tickers:
            target_col = f'{ticker}_TARGET_DIRECTION'
            if target_col not in df.columns:
                logger.warning(f"Целевая переменная для {ticker} отсутствует")
                continue

            # Подготовка данных
            feature_cols = [col for col in df.columns if col.endswith('_Open') or
                           col.endswith('_Close') or col.endswith('_Volume') or
                           col == 'KeyRate']
            X = df[feature_cols].dropna()
            y = df[target_col].dropna()
            X = X.loc[y.index]

            if len(X) < 10:
                logger.warning(f"Недостаточно данных для {ticker}")
                continue

            # Разделение на обучение и тест
            tscv = TimeSeriesSplit(n_splits=5)
            for train_idx, _ in tscv.split(X):
                X_train, y_train = X.iloc[train_idx], y[train_idx]

            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)

            # Обучение модели
            model = PassiveAggressiveClassifier(C=1.0, max_iter=1000, tol=1e-3, random_state=42)
            model.fit(X_train_scaled, y_train)

            # Сохранение модели и скейлера
            joblib.dump(model, f'models/{ticker}_model.joblib')
            joblib.dump(scaler, f'models/{ticker}_scaler.joblib')
            logger.info(f"Модель и скейлер для {ticker} сохранены")

        logger.info("Обучение всех моделей завершено")
    except Exception as e:
        logger.error(f"Ошибка в train_all_models: {str(e)}")
        raise

if __name__ == '__main__':
    train_all_models()
