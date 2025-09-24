# ml/data_preprocessor.py
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from pyod.models.knn import KNN
from pyod.models.iforest import IForest
from adtk.detector import PersistAD
from adtk.data import validate_series
from sklearn.impute import IterativeImputer
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class AdvancedDataPreprocessor:
    def __init__(self, config):
        self.config = config
        self.scaler = StandardScaler()
        self.imputer = IterativeImputer(random_state=42)

    def preprocess(self, df_prices):
        logger.info("Начало расширенной предобработки данных.")
        df = df_prices.copy()

        # 1. Технические индикаторы
        logger.debug("Добавление технических индикаторов.")
        df_with_ta = add_all_ta_features(df, open="Open", high="High", low="Low", close="Close", volume="Volume")

        # 2. Обнаружение аномалий (несколько моделей)
        logger.debug("Обнаружение аномалий.")
        df_anomaly = df_with_ta[['Close']].copy()
        # KNN Anomaly Detector
        knn_detector = KNN(contamination=0.05)
        knn_detector.fit(df_anomaly)
        df_anomaly['knn_outliers'] = knn_detector.predict(df_anomaly)
        # IForest Anomaly Detector
        if_detector = IForest(contamination=0.05, random_state=42)
        if_detector.fit(df_anomaly[['Close']])
        df_anomaly['iforest_outliers'] = if_detector.predict(df_anomaly[['Close']])
        # PersistAD (для временных рядов)
        persist_ad = PersistAD(c=3.0)
        anomalies = persist_ad.fit_detect(validate_series(df_anomaly['Close']))
        df_anomaly['persist_ad_outliers'] = 0
        if anomalies is not None and not anomalies.empty:
            df_anomaly.loc[anomalies.index, 'persist_ad_outliers'] = 1

        # 3. Удаление или коррекция аномалий (простая замена на NaN)
        outlier_cols = ['knn_outliers', 'iforest_outliers', 'persist_ad_outliers']
        df_anomaly['is_outlier'] = df_anomaly[outlier_cols].any(axis=1)
        df_anomaly.loc[df_anomaly['is_outlier'], df_anomaly.columns.difference(outlier_cols + ['is_outlier'])] = np.nan

        # 4. Импутация пропущенных значений (включая аномалии)
        logger.debug("Импутация пропущенных значений.")
        df_clean = df_anomaly.drop(columns=outlier_cols + ['is_outlier'])
        df_clean.loc[:, :] = self.imputer.fit_transform(df_clean)

        # 5. Масштабирование
        logger.debug("Масштабирование данных.")
        df_scaled = pd.DataFrame(self.scaler.fit_transform(df_clean), columns=df_clean.columns, index=df_clean.index)

        # 6. Расчет доходностей
        logger.debug("Расчет логарифмических доходностей.")
        returns = np.log(df_scaled / df_scaled.shift(1))
        returns.dropna(inplace=True)

        logger.info("Расширенная предобработка завершена.")
        return df_scaled, returns
