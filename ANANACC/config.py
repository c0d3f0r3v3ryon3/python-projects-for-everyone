# config.py
import os

# Базовая директория проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Директории
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")
SCALERS_DIR = os.path.join(BASE_DIR, "scalers")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
PLOTS_DIR = os.path.join(BASE_DIR, "plots")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

# Поддиректории исторических данных
HISTORICAL_DATA_DIR = {
    'stocks': os.path.join(DATA_DIR, "historical_data_full"),
    'indices': os.path.join(DATA_DIR, "historical_data_indices"),
    'currency': os.path.join(DATA_DIR, "historical_data_currency"),
    'oil': os.path.join(DATA_DIR, "historical_data_oil"),
    'other': os.path.join(DATA_DIR, "historical_data_other")
}

# Основные файлы данных
COMBINED_DATASET_FILE = os.path.join(DATA_DIR, "combined_dataset.csv")
COMBINED_DATASET_ALL_TARGETS_FILE = os.path.join(DATA_DIR, "combined_dataset_all_targets.csv")

# Файлы логов
PREDICTIONS_LOG_FILE = os.path.join(LOGS_DIR, "predictions_log.csv")
INCREMENTAL_LOG_FILE = os.path.join(LOGS_DIR, "incremental_learning_log.csv")
TRAINING_RESULTS_FILE = os.path.join(LOGS_DIR, "training_results.csv")

# Создание директорий при первом запуске
for dir_path in [
    DATA_DIR, MODELS_DIR, SCALERS_DIR, LOGS_DIR, PLOTS_DIR, SCRIPTS_DIR,
    HISTORICAL_DATA_DIR['stocks'], HISTORICAL_DATA_DIR['indices'],
    HISTORICAL_DATA_DIR['currency'], HISTORICAL_DATA_DIR['oil'],
    HISTORICAL_DATA_DIR['other']
]:
    os.makedirs(dir_path, exist_ok=True)

# Параметры моделей
MODEL_PARAMS = {
    "PassiveAggressiveClassifier": {
        "C": 1.0,
        "loss": "hinge",
        "random_state": 42,
        "max_iter": 1000,
        "tol": 1e-3
    },
    "SGDClassifier": {
        "loss": "hinge",
        "alpha": 0.001,
        "learning_rate": "constant",
        "eta0": 0.1,
        "penalty": "l2",
        "random_state": 42,
        "max_iter": 1000,
        "tol": 1e-3
    }
}

# Типы моделей для GUI
MODEL_TYPES = list(MODEL_PARAMS.keys())
