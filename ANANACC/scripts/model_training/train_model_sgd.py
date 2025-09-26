# scripts/model_training/train_model_sgd.py
import pandas as pd
import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score
import joblib
import os
from config import COMBINED_DATASET_ALL_TARGETS_FILE, MODELS_DIR, SCALERS_DIR, MODEL_PARAMS

def prepare_data(ticker, df):
    """Подготавливает данные для обучения модели."""
    target_col = f"TARGET_DIRECTION_{ticker}"
    if target_col not in df.columns:
        return None, None, None, None

    feature_cols = [col for col in df.columns if not col.startswith('TARGET_DIRECTION_') and col != 'TRADEDATE']
    X = df[feature_cols]
    y = df[target_col].dropna()
    X = X.loc[y.index]

    # Обработка пропусков
    price_cols = [col for col in X.columns if any(s in col for s in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
    volume_cols = [col for col in X.columns if '_VOLUME' in col]
    other_cols = [col for col in X.columns if col not in price_cols + volume_cols]

    X[price_cols] = X[price_cols].ffill().bfill()
    X[volume_cols] = X[volume_cols].fillna(0)
    X[other_cols] = X[other_cols].fillna(0)

    if len(X) == 0 or len(y) == 0:
        return None, None, None, None

    return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

def train_model(ticker, X_train, y_train):
    """Обучает и сохраняет модель SGDClassifier."""
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    model = SGDClassifier(**MODEL_PARAMS["SGDClassifier"])
    model.fit(X_train_scaled, y_train)

    # Сохранение
    os.makedirs(MODELS_DIR, exist_ok=True)
    os.makedirs(SCALERS_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODELS_DIR, f"model_{ticker}_sgd.joblib"))
    joblib.dump(scaler, os.path.join(SCALERS_DIR, f"scaler_{ticker}_sgd.joblib"))

    return model, scaler

def evaluate_model(model, scaler, X_test, y_test):
    """Оценивает модель на тестовой выборке."""
    X_test_scaled = scaler.transform(X_test)
    y_pred = model.predict(X_test_scaled)
    return {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1': f1_score(y_test, y_pred, average='weighted')
    }

def main(ticker="GAZP"):
    print(f"=== Обучение модели SGD для {ticker} ===")
    if not os.path.exists(COMBINED_DATASET_ALL_TARGETS_FILE):
        print(f"Файл {COMBINED_DATASET_ALL_TARGETS_FILE} не найден.")
        return

    df = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
    X_train, X_test, y_train, y_test = prepare_data(ticker, df)
    if X_train is None:
        print(f"❌ Нет данных для {ticker}")
        return

    model, scaler = train_model(ticker, X_train, y_train)
    metrics = evaluate_model(model, scaler, X_test, y_test)
    print(f"✅ Модель для {ticker} обучена. Accuracy: {metrics['accuracy']:.4f}, F1: {metrics['f1']:.4f}")

if __name__ == "__main__":
    main()
