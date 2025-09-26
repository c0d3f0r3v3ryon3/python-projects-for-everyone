# predict_and_learn.py
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
from sklearn.linear_model import PassiveAggressiveClassifier # Импортируем модель, которую мы использовали
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score

# --- Конфигурация ---
MODELS_DIR = 'models'
SCALERS_DIR = 'scalers'
DATASET_FILE = 'combined_dataset_all_targets.csv' # Используем для получения "новых" данных и признаков
PREDICTIONS_LOG_FILE = 'predictions_log.csv'
MODEL_UPDATE_LOG_FILE = 'model_updates_log.csv'
# FEATURE_COLUMNS_FILE = 'feature_columns_order.txt' # Файл с порядком столбцов признаков (если нужно)
TODAY = datetime.today().strftime('%Y-%m-%d')
YESTERDAY = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')

def load_models_and_scalers(models_dir, scalers_dir):
    """Загружает все модели и scaler'ы из директорий."""
    print(f"Загружаю модели из {models_dir} и scaler'ы из {scalers_dir}...")
    models = {}
    scalers = {}

    if not os.path.exists(models_dir) or not os.path.exists(scalers_dir):
        print(f"Директории {models_dir} или {scalers_dir} не существуют.")
        return models, scalers

    model_files = [f for f in os.listdir(models_dir) if f.startswith('model_') and f.endswith('.joblib')]
    scaler_files = [f for f in os.listdir(scalers_dir) if f.startswith('scaler_') and f.endswith('.joblib')]

    print(f"Найдено {len(model_files)} файлов моделей.")
    print(f"Найдено {len(scaler_files)} файлов scaler'ов.")

    for model_file in model_files:
        ticker = model_file.replace('model_', '').replace('.joblib', '')
        model_path = os.path.join(models_dir, model_file)
        try:
            model = joblib.load(model_path)
            models[ticker] = model
            print(f"  Загружена модель для {ticker} из {model_path}")
        except Exception as e:
            print(f"  Ошибка при загрузке модели для {ticker} из {model_path}: {e}")

    for scaler_file in scaler_files:
        ticker = scaler_file.replace('scaler_', '').replace('.joblib', '')
        scaler_path = os.path.join(scalers_dir, scaler_file)
        try:
            scaler = joblib.load(scaler_path)
            scalers[ticker] = scaler
            print(f"  Загружен scaler для {ticker} из {scaler_path}")
        except Exception as e:
            print(f"  Ошибка при загрузке scaler'а для {ticker} из {scaler_path}: {e}")

    print(f"Успешно загружено {len(models)} моделей и {len(scalers)} scaler'ов.")
    return models, scalers

def load_latest_data(dataset_file, num_days=1):
    """Загружает последние N строк из датасета как "новые" данные."""
    print(f"Загружаю последние {num_days} строк из {dataset_file} как новые данные...")
    if not os.path.exists(dataset_file):
        print(f"Файл {dataset_file} не найден.")
        return pd.DataFrame(), pd.DataFrame()

    try:
        df = pd.read_csv(dataset_file, encoding='utf-8-sig')
        print(f"Датасет загружен: {len(df)} строк, {len(df.columns)} столбцов.")

        # Берем последние num_days строк
        latest_df = df.tail(num_days).reset_index(drop=True)
        print(f"Последние {num_days} строк загружены.")

        # Извлекаем даты
        dates_df = latest_df[['TRADEDATE']].copy()

        # Извлекаем признаки (все, кроме TRADEDATE и TARGET_DIRECTION_*)
        feature_columns = [col for col in df.columns if col not in ['TRADEDATE'] and not col.startswith('TARGET_DIRECTION_')]
        features_df = latest_df[feature_columns].copy()

        print(f"Размер признаков (X): {features_df.shape}")
        print(f"Размер дат: {dates_df.shape}")

        return features_df, dates_df
    except Exception as e:
        print(f"Ошибка при загрузке последних данных из {dataset_file}: {e}")
        return pd.DataFrame(), pd.DataFrame()

def prepare_features(features_df, scaler, ticker):
    """Подготавливает (масштабирует) признаки для прогноза."""
    print(f"  Подготовка признаков для {ticker}...")
    try:
        # Масштабируем признаки с помощью загруженного scaler'а
        # ВАЖНО: scaler уже обучен, используем transform
        features_scaled = scaler.transform(features_df)
        print(f"    Признаки масштабированы. Форма: {features_scaled.shape}")
        return features_scaled
    except Exception as e:
        print(f"    Ошибка при масштабировании признаков для {ticker}: {e}")
        return None

def make_predictions(models, scalers, features_df, dates_df):
    """Делает прогнозы для всех моделей."""
    print("\n--- Делаем прогнозы для всех моделей ---")
    predictions = {}

    for ticker, model in models.items():
        scaler = scalers.get(ticker)
        if scaler is None:
            print(f"  Предупреждение: Scaler для {ticker} не найден. Пропускаю прогноз.")
            continue

        features_scaled = prepare_features(features_df, scaler, ticker)
        if features_scaled is None:
            continue

        try:
            # Делаем прогноз
            y_pred = model.predict(features_scaled)
            # Получаем вероятности (если модель поддерживает predict_proba)
            # y_proba = model.predict_proba(features_scaled) if hasattr(model, 'predict_proba') else None

            predictions[ticker] = {
                'prediction': y_pred[0], # Берем первый (и единственный) прогноз
                # 'probability': y_proba[0] if y_proba is not None else None,
                'date': dates_df.iloc[0]['TRADEDATE'] # Берем дату из первой (и единственной) строки
            }
            print(f"  Прогноз для {ticker}: {y_pred[0]} (дата: {dates_df.iloc[0]['TRADEDATE']})")
        except Exception as e:
            print(f"  Ошибка при прогнозе для {ticker}: {e}")

    return predictions

def save_predictions(predictions, log_file):
    """Сохраняет прогнозы в лог-файл."""
    if not predictions:
        print("Нет прогнозов для сохранения.")
        return

    print(f"\n--- Сохранение прогнозов в {log_file} ---")
    try:
        # Создаем DataFrame из словаря прогнозов
        log_data = []
        for ticker, pred_info in predictions.items():
            log_data.append({
                'TICKER': ticker,
                'TRADEDATE': pred_info['date'],
                'PREDICTED_DIRECTION': pred_info['prediction'],
                # 'PREDICTED_PROBABILITY': pred_info.get('probability', None),
                'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        log_df = pd.DataFrame(log_data)

        # Если файл существует, добавляем новые строки, иначе создаем новый
        if os.path.exists(log_file):
            log_df.to_csv(log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
            print(f"  Прогнозы добавлены в существующий лог {log_file}.")
        else:
            log_df.to_csv(log_file, index=False, encoding='utf-8-sig')
            print(f"  Прогнозы сохранены в новый лог {log_file}.")

    except Exception as e:
        print(f"  Ошибка при сохранении прогнозов в {log_file}: {e}")

def simulate_get_real_target_directions(dataset_file, tickers, prediction_date):
    """
    Симулирует получение реальных TARGET_DIRECTION для всех тикеров.
    В реальном боевом скрипте здесь будет запрос к API MOEX для получения цен закрытия.
    """
    print(f"\n--- Симуляция получения реальных TARGET_DIRECTION для {len(tickers)} тикеров на дату {prediction_date} ---")
    if not os.path.exists(dataset_file):
        print(f"Файл {dataset_file} не найден для симуляции.")
        return {}

    try:
        df = pd.read_csv(dataset_file, encoding='utf-8-sig')
        # Преобразуем TRADEDATE в datetime для поиска
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
        prediction_date_dt = pd.to_datetime(prediction_date, format='%Y-%m-%d', errors='coerce')

        if pd.isna(prediction_date_dt):
            print(f"Некорректная дата прогноза для симуляции: {prediction_date}")
            return {}

        # Находим строку с датой прогноза
        target_row = df[df['TRADEDATE'] == prediction_date_dt]
        if target_row.empty:
            print(f"Дата {prediction_date} не найдена в {dataset_file} для симуляции.")
            return {}

        real_targets = {}
        for ticker in tickers:
            target_col = f"TARGET_DIRECTION_{ticker}"
            if target_col in target_row.columns:
                real_value = target_row[target_col].iloc[0]
                if not pd.isna(real_value):
                    real_targets[ticker] = real_value
                    print(f"  Реальная TARGET_DIRECTION для {ticker} на {prediction_date}: {real_value}")
                else:
                    print(f"  Реальная TARGET_DIRECTION для {ticker} на {prediction_date} отсутствует (NaN).")
            else:
                print(f"  Столбец {target_col} не найден в {dataset_file} для симуляции.")

        return real_targets
    except Exception as e:
        print(f"Ошибка при симуляции получения реальных TARGET_DIRECTION: {e}")
        return {}

def perform_incremental_learning(models, scalers, features_df, real_targets, update_log_file):
    """Выполняет инкрементальное обучение для всех моделей, где есть реальная метка."""
    print(f"\n--- Выполнение инкрементального обучения для моделей с реальными метками ---")
    updated_models = []
    correct_predictions = 0
    total_predictions = 0

    for ticker, y_true in real_targets.items():
        model = models.get(ticker)
        scaler = scalers.get(ticker)

        if model is None or scaler is None:
            print(f"  Модель или scaler для {ticker} не найдены. Пропускаю дообучение.")
            continue

        features_scaled = prepare_features(features_df, scaler, ticker)
        if features_scaled is None:
            continue

        try:
            # Делаем прогноз до дообучения (для сравнения)
            y_pred_before = model.predict(features_scaled)[0]
            is_correct = (y_pred_before == y_true)
            correct_predictions += int(is_correct)
            total_predictions += 1

            # Дообучаем модель
            model.partial_fit(features_scaled, [y_true], classes=np.array([-1, 0, 1]))
            print(f"  Модель для {ticker} дообучена на реальной метке {y_true}. Прогноз был {y_pred_before} ({'Правильно' if is_correct else 'Неправильно'}).")
            updated_models.append(ticker)
        except Exception as e:
            print(f"  Ошибка при дообучении модели для {ticker}: {e}")

    if total_predictions > 0:
        accuracy = correct_predictions / total_predictions
        print(f"\nТочность прогнозов перед дообучением: {accuracy:.4f} ({correct_predictions}/{total_predictions})")

        # Сохраняем лог обновления модели
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
            print(f"Лог обновления моделей сохранен в {update_log_file}.")
        except Exception as e:
            print(f"Ошибка при сохранении лога обновления моделей: {e}")
    else:
        print("Нет моделей для дообучения (нет реальных меток).")

def save_updated_models(models, scalers, models_dir, scalers_dir):
    """Сохраняет обновленные модели и scaler'ы."""
    print(f"\n--- Сохранение обновленных моделей и scaler'ов ---")
    for ticker, model in models.items():
        model_path = os.path.join(models_dir, f'model_{ticker}.joblib')
        try:
            joblib.dump(model, model_path)
            print(f"  Обновленная модель для {ticker} сохранена в {model_path}")
        except Exception as e:
            print(f"  Ошибка при сохранении обновленной модели для {ticker}: {e}")

    # Scaler'ы не изменяются, поэтому их перезаписывать не обязательно
    # Но если бы они тоже обновлялись (например, через partial_fit или online scaling),
    # их тоже нужно было бы сохранить.
    print("Сохранение обновленных моделей завершено.")

def main():
    """Основная функция."""
    print("=== ЗАПУСК БОЕВОГО СКРИПТА ДЛЯ ПРОГНОЗА И ИНКРЕМЕНТАЛЬНОГО ОБУЧЕНИЯ ===")
    print(f"Дата запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Загрузка моделей и scaler'ов
    models, scalers = load_models_and_scalers(MODELS_DIR, SCALERS_DIR)
    if not models or not scalers:
        print("Не удалось загрузить модели или scaler'ы. Завершение.")
        return

    # 2. Получение "новых" данных (в реальном боевом скрипте здесь будет запрос к API)
    # Пока используем последние 1 строки из датасета как "новые" данные
    features_df, dates_df = load_latest_data(DATASET_FILE, num_days=1)
    if features_df.empty or dates_df.empty:
        print("Не удалось загрузить новые данные. Завершение.")
        return

    prediction_date = dates_df.iloc[0]['TRADEDATE']
    print(f"Дата прогноза: {prediction_date}")

    # 3. Прогнозирование
    predictions = make_predictions(models, scalers, features_df, dates_df)
    if not predictions:
        print("Не удалось сделать ни одного прогноза. Завершение.")
        return

    # 4. Сохранение прогнозов
    save_predictions(predictions, PREDICTIONS_LOG_FILE)

    # 5. (Симуляция) Получение реальных TARGET_DIRECTION
    # В реальном боевом скрипте здесь будет запрос к API MOEX через день
    # Пока симулируем на основе данных из датасета
    real_targets = simulate_get_real_target_directions(DATASET_FILE, list(predictions.keys()), prediction_date)
    if not real_targets:
        print("Не удалось получить реальные TARGET_DIRECTION. Дообучение невозможно.")
        return

    # 6. Инкрементальное обучение
    perform_incremental_learning(models, scalers, features_df, real_targets, MODEL_UPDATE_LOG_FILE)

    # 7. Сохранение обновленных моделей
    save_updated_models(models, scalers, MODELS_DIR, SCALERS_DIR)

    print("\n=== БОЕВОЙ СКРИПТ ЗАВЕРШЕН ===")

if __name__ == "__main__":
    main()
