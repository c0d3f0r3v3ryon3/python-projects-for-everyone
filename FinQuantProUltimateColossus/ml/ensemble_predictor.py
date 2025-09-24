# ml/ensemble_predictor.py
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from prophet import Prophet
import xgboost as xgb
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)

class LSTMModel:
    def __init__(self, look_back=60):
        self.look_back = look_back
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))

    def _create_dataset(self, dataset, look_back=1):
        dataX, dataY = [], []
        for i in range(len(dataset) - look_back - 1):
            a = dataset[i:(i + look_back), 0]
            dataX.append(a)
            dataY.append(dataset[i + look_back, 0])
        return np.array(dataX), np.array(dataY)

    def train(self, ts):
        dataset = ts.values.reshape(-1, 1)
        dataset_scaled = self.scaler.fit_transform(dataset)
        X, y = self._create_dataset(dataset_scaled, self.look_back)
        X = np.reshape(X, (X.shape[0], 1, X.shape[1]))

        self.model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(1, self.look_back)),
            Dropout(0.2),
            LSTM(50, return_sequences=False),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        self.model.compile(optimizer='adam', loss='mean_squared_error')
        self.model.fit(X, y, batch_size=1, epochs=1, verbose=0)

    def predict(self, ts, periods=1):
        last_data = ts.values[-self.look_back:]
        last_data_scaled = self.scaler.transform(last_data.reshape(-1, 1))
        predictions = []
        current_batch = last_data_scaled.reshape((1, 1, self.look_back))
        for _ in range(periods):
            current_pred = self.model.predict(current_batch, verbose=0)[0, 0]
            predictions.append(current_pred)
            current_batch = np.append(current_batch[:, :, 1:], [[current_pred]], axis=2)
            current_batch = current_batch.reshape((1, 1, self.look_back))
        predictions = np.array(predictions).reshape(-1, 1)
        predictions = self.scaler.inverse_transform(predictions)
        return predictions.flatten()

class EnsemblePredictor(BaseEstimator, RegressorMixin):
    def __init__(self, models_config, sentiment_analyzer=None):
        self.models_config = models_config
        self.sentiment_analyzer = sentiment_analyzer
        self.models = {}
        self.weights = {'LSTM': 0.4, 'Prophet': 0.3, 'XGBoost': 0.3}

    def fit(self, X, y, tickers_info=None):
        logger.info("Обучение ансамблевой модели.")
        if 'LSTM' in self.models_config:
            logger.debug("Обучение LSTM.")
            self.models['LSTM'] = LSTMModel()
            self.models['LSTM'].train(y)

        if 'Prophet' in self.models_config:
            logger.debug("Обучение Prophet.")
            df_prophet = pd.DataFrame({'ds': y.index, 'y': y.values})
            self.models['Prophet'] = Prophet()
            self.models['Prophet'].fit(df_prophet)

        if 'XGBoost' in self.models_config:
            logger.debug("Обучение XGBoost.")
            self.models['XGBoost'] = xgb.XGBRegressor(objective='reg:squarederror')
            self.models['XGBoost'].fit(X, y)

        logger.info("Ансамблевая модель обучена.")
        return self

    def predict(self, X, periods=1, sentiment_score=0):
        logger.info("Прогнозирование ансамблевой моделью.")
        predictions = {}

        if 'LSTM' in self.models:
            ts = X.iloc[:, 0]
            predictions['LSTM'] = self.models['LSTM'].predict(ts, periods=periods)[-1]

        if 'Prophet' in self.models:
            future = self.models['Prophet'].make_future_dataframe(periods=periods)
            forecast = self.models['Prophet'].predict(future)
            predictions['Prophet'] = forecast['yhat'].iloc[-1]

        if 'XGBoost' in self.models:
            last_X = X.iloc[-1:].fillna(0)
            predictions['XGBoost'] = self.models['XGBoost'].predict(last_X)[0]

        final_prediction = sum(self.weights.get(name, 0) * pred for name, pred in predictions.items())

        if self.sentiment_analyzer and sentiment_score != 0:
            adjustment = 0.01 * sentiment_score
            final_prediction *= (1 + adjustment)
            logger.debug(f"Прогноз скорректирован на {adjustment*100:.2f}% из-за сентимента.")

        logger.info("Прогноз ансамблевой моделью завершен.")
        return final_prediction
