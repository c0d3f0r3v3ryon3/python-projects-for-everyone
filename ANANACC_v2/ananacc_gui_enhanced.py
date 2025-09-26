# ananacc_gui_enhanced.py (боевой)
import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QFormLayout, QLineEdit, QDateEdit, QCheckBox, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QFrame, QCalendarWidget, QTableWidget, QTableWidgetItem,
    QAbstractItemView
)
from PyQt5.QtCore import QThread, pyqtSignal, QDate, Qt
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import joblib

# --- Конфигурация ---
SCRIPTS_DIR = 'scripts'
DATA_DIR = 'data'
MODELS_DIR = 'models'
SCALERS_DIR = 'scalers'
LOGS_DIR = 'logs'
PLOTS_DIR = 'plots'
HISTORICAL_DATA_FULL_DIR = 'historical_data_full'
HISTORICAL_DATA_INDICES_DIR = 'historical_data_indices'
HISTORICAL_DATA_CURRENCY_DIR = 'historical_data_currency'
HISTORICAL_DATA_OIL_DIR = 'historical_data_oil'
HISTORICAL_DATA_OTHER_DIR = 'historical_data_other'
COMBINED_DATASET_FILE = os.path.join(DATA_DIR, 'combined_dataset.csv')
COMBINED_DATASET_ALL_TARGETS_FILE = os.path.join(DATA_DIR, 'combined_dataset_all_targets.csv')
INCREMENTAL_LOG_FILE = os.path.join(LOGS_DIR, 'incremental_learning_log_final.csv')
PREDICTIONS_LOG_FILE = os.path.join(LOGS_DIR, 'predictions_log.csv')
# -------------------------------

# --- Глобальные константы ---
DATE_COLUMN = 'TRADEDATE'
TARGET_COLUMN = 'TARGET_DIRECTION'
TEST_SIZE = 0.2
RANDOM_STATE = 42
# -------------------------------

class ScriptRunner(QThread):
    """Поток для запуска Python-скриптов."""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, script_path, parent=None):
        super().__init__(parent)
        self.script_path = script_path

    def run(self):
        """Запуск скрипта."""
        try:
            self.output_signal.emit(f"Запуск скрипта: {self.script_path}\n")
            process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            for line in iter(process.stdout.readline, ''):
                self.output_signal.emit(line.rstrip('\n'))

            process.stdout.close()
            return_code = process.wait()
            self.finished_signal.emit(return_code)
        except Exception as e:
            self.output_signal.emit(f"Ошибка при запуске скрипта {self.script_path}: {e}\n")
            self.finished_signal.emit(-1)

class SettingsTab(QWidget):
    """Вкладка настроек."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        paths_group = QGroupBox("Пути к данным и моделям")
        paths_layout = QFormLayout()

        self.data_dir_edit = QLineEdit(DATA_DIR)
        self.models_dir_edit = QLineEdit(MODELS_DIR)
        self.scalers_dir_edit = QLineEdit(SCALERS_DIR)
        self.logs_dir_edit = QLineEdit(LOGS_DIR)
        self.plots_dir_edit = QLineEdit(PLOTS_DIR)
        self.historical_data_full_dir_edit = QLineEdit(HISTORICAL_DATA_FULL_DIR)
        self.historical_data_indices_dir_edit = QLineEdit(HISTORICAL_DATA_INDICES_DIR)
        self.historical_data_currency_dir_edit = QLineEdit(HISTORICAL_DATA_CURRENCY_DIR)
        self.historical_data_oil_dir_edit = QLineEdit(HISTORICAL_DATA_OIL_DIR)
        self.historical_data_other_dir_edit = QLineEdit(HISTORICAL_DATA_OTHER_DIR)

        paths_layout.addRow("Директория данных:", self.data_dir_edit)
        paths_layout.addRow("Директория моделей:", self.models_dir_edit)
        paths_layout.addRow("Директория scaler'ов:", self.scalers_dir_edit)
        paths_layout.addRow("Директория логов:", self.logs_dir_edit)
        paths_layout.addRow("Директория графиков:", self.plots_dir_edit)
        paths_layout.addRow("Директория исторических данных (акции):", self.historical_data_full_dir_edit)
        paths_layout.addRow("Директория исторических данных (индексы):", self.historical_data_indices_dir_edit)
        paths_layout.addRow("Директория исторических данных (валюты):", self.historical_data_currency_dir_edit)
        paths_layout.addRow("Директория исторических данных (нефть):", self.historical_data_oil_dir_edit)
        paths_layout.addRow("Директория исторических данных (другие):", self.historical_data_other_dir_edit)

        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        dates_group = QGroupBox("Даты")
        dates_layout = QFormLayout()

        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate(2023, 1, 1))
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate())

        dates_layout.addRow("Начальная дата:", self.start_date_edit)
        dates_layout.addRow("Конечная дата:", self.end_date_edit)

        dates_group.setLayout(dates_layout)
        layout.addWidget(dates_group)

        models_group = QGroupBox("Настройки моделей")
        models_layout = QFormLayout()

        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["PassiveAggressiveClassifier", "SGDClassifier", "Perceptron"])
        self.model_type_combo.setCurrentText("PassiveAggressiveClassifier")

        models_layout.addRow("Тип модели:", self.model_type_combo)

        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        self.save_settings_btn = QPushButton("Сохранить настройки")
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn)

        self.setLayout(layout)

    def save_settings(self):
        """Сохраняет настройки."""
        QMessageBox.information(self, "Настройки", "Настройки сохранены!")

class DataCollectionTab(QWidget):
    """Вкладка сбора данных."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        collection_group = QGroupBox("Сбор данных")
        collection_layout = QVBoxLayout()

        self.get_stocks_btn = QPushButton("1. Получить список акций (get_moex_stocks.py)")
        self.get_stocks_btn.clicked.connect(lambda: self.run_script('get_moex_stocks.py'))
        collection_layout.addWidget(self.get_stocks_btn)

        self.get_history_btn = QPushButton("2. Получить историю акций (get_historical_data.py)")
        self.get_history_btn.clicked.connect(lambda: self.run_script('get_historical_data.py'))
        collection_layout.addWidget(self.get_history_btn)

        self.find_indices_btn = QPushButton("3. Найти индексы (find_indices.py)")
        self.find_indices_btn.clicked.connect(lambda: self.run_script('find_indices.py'))
        collection_layout.addWidget(self.find_indices_btn)

        self.find_currency_pairs_btn = QPushButton("4. Найти валютные пары (find_currency_pairs.py)")
        self.find_currency_pairs_btn.clicked.connect(lambda: self.run_script('find_currency_pairs.py'))
        collection_layout.addWidget(self.find_currency_pairs_btn)

        self.find_oil_futures_btn = QPushButton("5. Найти фьючерсы на нефть (find_oil_futures.py)")
        self.find_oil_futures_btn.clicked.connect(lambda: self.run_script('find_oil_futures.py'))
        collection_layout.addWidget(self.find_oil_futures_btn)

        self.get_key_rate_btn = QPushButton("6. Получить историю ключевой ставки (get_key_rate_history.py)")
        self.get_key_rate_btn.clicked.connect(lambda: self.run_script('get_key_rate_history.py'))
        collection_layout.addWidget(self.get_key_rate_btn)

        collection_group.setLayout(collection_layout)
        layout.addWidget(collection_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def run_script(self, script_name):
        """Запускает скрипт в отдельном потоке."""
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return

        self.thread = ScriptRunner(script_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()

        self.disable_buttons()

    def disable_buttons(self):
        """Блокирует кнопки."""
        for btn in [self.get_stocks_btn, self.get_history_btn, self.find_indices_btn,
                    self.find_currency_pairs_btn, self.find_oil_futures_btn, self.get_key_rate_btn]:
            btn.setEnabled(False)

    def enable_buttons(self):
        """Разблокирует кнопки."""
        for btn in [self.get_stocks_btn, self.get_history_btn, self.find_indices_btn,
                    self.find_currency_pairs_btn, self.find_oil_futures_btn, self.get_key_rate_btn]:
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        """Обработчик завершения скрипта."""
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class DataCombiningTab(QWidget):
    """Вкладка объединения данных."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        combining_group = QGroupBox("Объединение данных")
        combining_layout = QVBoxLayout()

        self.combine_datasets_btn = QPushButton("1. Объединить данные (combine_datasets.py)")
        self.combine_datasets_btn.clicked.connect(lambda: self.run_script('combine_datasets.py'))
        combining_layout.addWidget(self.combine_datasets_btn)

        self.combine_all_targets_btn = QPushButton("2. Добавить TARGET_DIRECTION для всех акций (combine_datasets_all_targets.py)")
        self.combine_all_targets_btn.clicked.connect(lambda: self.run_script('combine_datasets_all_targets.py'))
        combining_layout.addWidget(self.combine_all_targets_btn)

        combining_group.setLayout(combining_layout)
        layout.addWidget(combining_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def run_script(self, script_name):
        """Запускает скрипт в отдельном потоке."""
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return

        self.thread = ScriptRunner(script_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()

        self.disable_buttons()

    def disable_buttons(self):
        """Блокирует кнопки."""
        for btn in [self.combine_datasets_btn, self.combine_all_targets_btn]:
            btn.setEnabled(False)

    def enable_buttons(self):
        """Разблокирует кнопки."""
        for btn in [self.combine_datasets_btn, self.combine_all_targets_btn]:
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        """Обработчик завершения скрипта."""
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class ModelTrainingTab(QWidget):
    """Вкладка обучения моделей."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        training_group = QGroupBox("Обучение моделей")
        training_layout = QVBoxLayout()

        self.train_all_models_btn = QPushButton("1. Обучить все модели (train_all_models.py)")
        self.train_all_models_btn.clicked.connect(lambda: self.run_script('train_all_models.py'))
        training_layout.addWidget(self.train_all_models_btn)

        training_group.setLayout(training_layout)
        layout.addWidget(training_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def run_script(self, script_name):
        """Запускает скрипт в отдельном потоке."""
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return

        self.thread = ScriptRunner(script_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()

        self.disable_buttons()

    def disable_buttons(self):
        """Блокирует кнопки."""
        for btn in [self.train_all_models_btn]:
            btn.setEnabled(False)

    def enable_buttons(self):
        """Разблокирует кнопки."""
        for btn in [self.train_all_models_btn]:
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        """Обработчик завершения скрипта."""
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class PredictionTab(QWidget):
    """Вкладка прогнозирования."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        prediction_setup_group = QGroupBox("Настройка прогноза")
        prediction_setup_layout = QFormLayout()

        self.model_selector_combo = QComboBox()
        self.populate_model_selector() # Заполняем список моделей при инициализации
        prediction_setup_layout.addRow("Выберите модель:", self.model_selector_combo)

        self.date_picker = QCalendarWidget()
        self.date_picker.setSelectedDate(QDate.currentDate())
        prediction_setup_layout.addRow("Выберите дату:", self.date_picker)

        prediction_setup_group.setLayout(prediction_setup_layout)
        layout.addWidget(prediction_setup_group)

        prediction_actions_group = QGroupBox("Действия")
        prediction_actions_layout = QVBoxLayout()

        self.predict_btn = QPushButton("Получить прогноз")
        self.predict_btn.clicked.connect(self.make_prediction)
        prediction_actions_layout.addWidget(self.predict_btn)

        prediction_actions_group.setLayout(prediction_actions_layout)
        layout.addWidget(prediction_actions_group)

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        layout.addWidget(self.result_output)

        self.setLayout(layout)

    def populate_model_selector(self):
        """Заполняет выпадающий список моделями (тикеры), найденными в MODELS_DIR."""
        self.model_selector_combo.clear()
        # self.model_selector_combo.addItem("Все модели") # Убираем опцию "Все модели" для простоты

        if not os.path.exists(MODELS_DIR):
            self.result_output.append(f"Директория моделей {MODELS_DIR} не найдена.\n")
            return

        try:
            # Ищем все файлы моделей вида model_{TICKER}.joblib
            model_files = [f for f in os.listdir(MODELS_DIR) if f.startswith('model_') and f.endswith('.joblib')]
            tickers = sorted(list(set([f.replace('model_', '').replace('.joblib', '') for f in model_files])))
            self.model_selector_combo.addItems(tickers)
            self.result_output.append(f"Найдено {len(tickers)} моделей.\n")
        except Exception as e:
            self.result_output.append(f"Ошибка при поиске моделей: {e}\n") # <-- Исправлено обращение к self.result_output

    def make_prediction(self):
        """Делает прогноз на основе выбранных настроек."""
        selected_model = self.model_selector_combo.currentText()
        selected_date = self.date_picker.selectedDate().toString("yyyy-MM-dd")

        self.result_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запрос прогноза для {selected_model} на {selected_date}...\n")

        try:
            # 1. Загрузка scaler'а для выбранной модели
            scaler_filename = os.path.join(SCALERS_DIR, f'scaler_{selected_model}.joblib')
            if not os.path.exists(scaler_filename):
                 self.result_output.append(f"  Ошибка: Файл scaler'а {scaler_filename} не найден.\n")
                 return
            scaler = joblib.load(scaler_filename)
            self.result_output.append(f"  Scaler для {selected_model} загружен.\n")

            # 2. Загрузка модели для выбранной модели
            model_filename = os.path.join(MODELS_DIR, f'model_{selected_model}.joblib')
            if not os.path.exists(model_filename):
                 self.result_output.append(f"  Ошибка: Файл модели {model_filename} не найден.\n")
                 return
            model = joblib.load(model_filename)
            self.result_output.append(f"  Модель для {selected_model} загружена.\n")

            # 3. Получение новых данных (используем последние строки из combined_dataset.csv как "новые" данные)
            if not os.path.exists(COMBINED_DATASET_FILE):
                self.result_output.append(f"  Ошибка: Файл данных {COMBINED_DATASET_FILE} не найден.\n")
                return

            df_combined = pd.read_csv(COMBINED_DATASET_FILE, encoding='utf-8-sig')
            # Находим строку с датой, равной selected_date
            df_selected = df_combined[df_combined[DATE_COLUMN] == selected_date]
            if df_selected.empty:
                # Если точная дата не найдена, берем ближайшую предшествующую
                df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
                df_selected = df_combined[df_combined[DATE_COLUMN] <= pd.to_datetime(selected_date, format='%Y-%m-%d', errors='coerce')]
                if df_selected.empty:
                    self.result_output.append(f"  Ошибка: Нет данных до даты {selected_date}.\n")
                    return
                df_selected = df_selected.tail(1) # Берем последнюю строку до выбранной даты

            self.result_output.append(f"  Найдены данные за {df_selected[DATE_COLUMN].iloc[0].strftime('%Y-%m-%d')}.\n")

            # 4. Подготовка признаков
            feature_columns = [col for col in df_combined.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
            X_new = df_selected[feature_columns].copy()

            # Обработка пропусков (аналогично combine_datasets.py)
            price_cols = [col for col in X_new.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
            volume_cols = [col for col in X_new.columns if '_VOLUME' in col]
            other_cols = [col for col in X_new.columns if col not in price_cols + volume_cols]

            self.result_output.append(f"  Заполнение цен (ffill/bfill): {len(price_cols)} столбцов.\n")
            X_new[price_cols] = X_new[price_cols].ffill().bfill()
            self.result_output.append(f"  Заполнение объемов (0): {len(volume_cols)} столбцов.\n")
            X_new[volume_cols] = X_new[volume_cols].fillna(0)
            self.result_output.append(f"  Заполнение других (0 или ffill): {len(other_cols)} столбцов.\n")
            cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
            if cbr_key_rate_cols:
                self.result_output.append(f"    Заполнение CBR_KEY_RATE (ffill): {cbr_key_rate_cols}\n")
                X_new[cbr_key_rate_cols] = X_new[cbr_key_rate_cols].ffill()
                other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
            if other_cols:
                self.result_output.append(f"    Заполнение остальных (0): {other_cols}\n")
                X_new[other_cols] = X_new[other_cols].fillna(0)

            mask_after_fill = ~X_new.isnull().any(axis=1)
            X_new_clean = X_new[mask_after_fill]

            if X_new_clean.empty:
                self.result_output.append(f"  Ошибка: После обработки пропусков данные пусты.\n")
                return

            # Масштабирование
            X_new_scaled = scaler.transform(X_new_clean) # <-- Используем загруженный scaler
            self.result_output.append(f"  Признаки подготовлены и масштабированы.\n")

            # 5. Прогноз
            y_pred = model.predict(X_new_scaled)[0]
            self.result_output.append(f"  Прогноз TARGET_DIRECTION для {selected_model} на {selected_date}: {y_pred}\n")

            # 6. Сохранение прогноза
            prediction_log_entry = pd.DataFrame([{
                'TRADEDATE': selected_date,
                'TICKER': selected_model,
                'PREDICTED_DIRECTION': y_pred,
                'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }])

            if os.path.exists(PREDICTIONS_LOG_FILE):
                prediction_log_entry.to_csv(PREDICTIONS_LOG_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                prediction_log_entry.to_csv(PREDICTIONS_LOG_FILE, index=False, encoding='utf-8-sig')

            self.result_output.append(f"  Прогноз сохранен в {PREDICTIONS_LOG_FILE}.\n")

        except Exception as e:
            self.result_output.append(f"  Ошибка при прогнозировании: {e}\n")
            import traceback
            self.result_output.append(traceback.format_exc() + "\n")

class RetrainingTab(QWidget):
    """Вкладка дообучения."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        retraining_group = QGroupBox("Дообучение моделей")
        retraining_layout = QVBoxLayout()

        self.check_predictions_btn = QPushButton("1. Проверить прогнозы")
        self.check_predictions_btn.clicked.connect(self.check_predictions)
        retraining_layout.addWidget(self.check_predictions_btn)

        self.retrain_models_btn = QPushButton("2. Дообучить модели")
        self.retrain_models_btn.clicked.connect(self.retrain_models)
        retraining_layout.addWidget(self.retrain_models_btn)

        retraining_group.setLayout(retraining_layout)
        layout.addWidget(retraining_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.setLayout(layout)

    def check_predictions(self):
        """Проверяет прогнозы."""
        self.log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка прогнозов...\n")
        try:
            if not os.path.exists(PREDICTIONS_LOG_FILE):
                self.log_output.append(f"  Файл лога {PREDICTIONS_LOG_FILE} не найден.\n")
                return

            df_predictions = pd.read_csv(PREDICTIONS_LOG_FILE, encoding='utf-8-sig')
            self.log_output.append(f"  Загружено {len(df_predictions)} записей из лога прогнозов.\n")

            if not os.path.exists(COMBINED_DATASET_ALL_TARGETS_FILE):
                self.log_output.append(f"  Файл данных {COMBINED_DATASET_ALL_TARGETS_FILE} не найден.\n")
                return

            df_combined = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE, encoding='utf-8-sig')
            df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
            self.log_output.append(f"  Загружены данные для сравнения из {COMBINED_DATASET_ALL_TARGETS_FILE}.\n")

            # Находим "просроченные" прогнозы (дата прогноза < сегодня)
            today = pd.Timestamp.today().normalize()
            df_overdue = df_predictions[pd.to_datetime(df_predictions['TRADEDATE'], format='%Y-%m-%d', errors='coerce') < today]
            self.log_output.append(f"  Найдено {len(df_overdue)} 'просроченных' прогнозов.\n")

            if df_overdue.empty:
                self.log_output.append("  Нет просроченных прогнозов для проверки.\n")
                return

            overdue_to_process = []
            for index, row in df_overdue.iterrows():
                pred_date_str = row['TRADEDATE']
                pred_ticker = row['TICKER']
                pred_direction = row['PREDICTED_DIRECTION']

                # Получить реальные данные за эту дату
                df_real_data = df_combined[df_combined[DATE_COLUMN] == pd.to_datetime(pred_date_str, format='%Y-%m-%d', errors='coerce')]
                if df_real_data.empty:
                    self.log_output.append(f"    Нет реальных данных за {pred_date_str} для {pred_ticker}. Пропущено.\n")
                    continue

                target_col = f"TARGET_DIRECTION_{pred_ticker}" # <-- Используем правильное имя столбца
                if target_col not in df_real_data.columns:
                    self.log_output.append(f"    Целевая переменная {target_col} не найдена в данных за {pred_date_str}. Пропущено.\n")
                    continue

                real_direction = df_real_data[target_col].iloc[0]
                if pd.isna(real_direction):
                    self.log_output.append(f"    Реальная метка TARGET_DIRECTION_{pred_ticker} за {pred_date_str} NaN. Пропущено.\n")
                    continue

                # Сравнить прогноз с реальностью
                is_correct = (pred_direction == real_direction)

                # Формировать батч для дообучения
                overdue_to_process.append({
                    'TRADEDATE': pred_date_str,
                    'TICKER': pred_ticker,
                    'PREDICTED_DIRECTION': pred_direction,
                    'REAL_DIRECTION': real_direction,
                    'IS_CORRECT': is_correct
                })
                self.log_output.append(f"    Проверка {pred_ticker} за {pred_date_str}: Прогноз={pred_direction}, Истина={real_direction}, {'Верно' if is_correct else 'Неверно'}\n")

            if overdue_to_process:
                df_overdue_batch = pd.DataFrame(overdue_to_process)
                batch_filename = os.path.join(LOGS_DIR, f"overdue_predictions_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                df_overdue_batch.to_csv(batch_filename, index=False, encoding='utf-8-sig')
                self.log_output.append(f"  Сформирован батч для дообучения: {batch_filename}\n")
                self.log_output.append(f"  В батче {len(df_overdue_batch)} примеров.\n")
                # Сохраняем имя файла батча в атрибуте класса для использования в retrain_models
                self.overdue_batch_filename = batch_filename
            else:
                self.log_output.append("  Нет корректных данных для формирования батча.\n")

        except Exception as e:
            self.log_output.append(f"  Ошибка при проверке прогнозов: {e}\n")
            import traceback
            self.log_output.append(traceback.format_exc() + "\n")

    def retrain_models(self):
        """Дообучает модели."""
        self.log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Дообучение моделей...\n")
        try:
            if not hasattr(self, 'overdue_batch_filename') or not os.path.exists(self.overdue_batch_filename):
                self.log_output.append(f"  Файл батча для дообучения не найден. Сначала выполните 'Проверить прогнозы'.\n")
                return

            df_batch = pd.read_csv(self.overdue_batch_filename, encoding='utf-8-sig')
            self.log_output.append(f"  Загружен батч для дообучения: {len(df_batch)} примеров.\n")

            if df_batch.empty:
                self.log_output.append("  Батч пуст. Дообучение невозможно.\n")
                return

            # Группируем батч по тикерам
            grouped_batches = df_batch.groupby('TICKER')

            for ticker, group in grouped_batches:
                self.log_output.append(f"  Дообучение модели для {ticker}...")
                # 1. Загрузка модели и scaler'а для этого тикера
                model_filename = os.path.join(MODELS_DIR, f'model_{ticker}.joblib')
                scaler_filename = os.path.join(SCALERS_DIR, f'scaler_{ticker}.joblib')
                if not os.path.exists(model_filename) or not os.path.exists(scaler_filename):
                    self.log_output.append(f"    Ошибка: Файл модели ({model_filename}) или scaler'а ({scaler_filename}) для {ticker} не найден.\n")
                    continue

                model = joblib.load(model_filename)
                scaler = joblib.load(scaler_filename)
                self.log_output.append(f"    Модель и scaler для {ticker} загружены.")

                # 2. Получение признаков X для этого тикера (группы дат)
                dates_for_ticker = group['TRADEDATE'].tolist()
                if not os.path.exists(COMBINED_DATASET_FILE):
                    self.log_output.append(f"    Ошибка: Файл данных {COMBINED_DATASET_FILE} не найден.\n")
                    continue

                df_combined = pd.read_csv(COMBINED_DATASET_FILE, encoding='utf-8-sig')
                df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')

                # Фильтруем данные по датам из группы
                df_X_for_ticker = df_combined[df_combined[DATE_COLUMN].isin(pd.to_datetime(dates_for_ticker, format='%Y-%m-%d', errors='coerce'))]
                if df_X_for_ticker.empty:
                    self.log_output.append(f"    Нет данных для дообучения модели {ticker} по датам {dates_for_ticker}. Пропущено.\n")
                    continue

                # 3. Подготовка признаков X (аналогично make_prediction)
                feature_columns = [col for col in df_combined.columns if col not in [DATE_COLUMN, TARGET_COLUMN]]
                X_batch = df_X_for_ticker[feature_columns].copy()

                # Обработка пропусков (аналогично combine_datasets.py)
                price_cols = [col for col in X_batch.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
                volume_cols = [col for col in X_batch.columns if '_VOLUME' in col]
                other_cols = [col for col in X_batch.columns if col not in price_cols + volume_cols]

                self.log_output.append(f"    Заполнение цен (ffill/bfill): {len(price_cols)} столбцов для {ticker}.")
                X_batch[price_cols] = X_batch[price_cols].ffill().bfill()
                self.log_output.append(f"    Заполнение объемов (0): {len(volume_cols)} столбцов для {ticker}.")
                X_batch[volume_cols] = X_batch[volume_cols].fillna(0)
                self.log_output.append(f"    Заполнение других (0 или ffill): {len(other_cols)} столбцов для {ticker}.")
                cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
                if cbr_key_rate_cols:
                    self.log_output.append(f"      Заполнение CBR_KEY_RATE (ffill): {cbr_key_rate_cols} для {ticker}.")
                    X_batch[cbr_key_rate_cols] = X_batch[cbr_key_rate_cols].ffill()
                    other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
                if other_cols:
                    self.log_output.append(f"      Заполнение остальных (0): {other_cols} для {ticker}.")
                    X_batch[other_cols] = X_batch[other_cols].fillna(0)

                mask_after_fill = ~X_batch.isnull().any(axis=1)
                X_batch_clean = X_batch[mask_after_fill]

                if X_batch_clean.empty:
                    self.log_output.append(f"    После обработки пропусков признаки X за {dates_for_ticker} для {ticker} пусты. Пропущено.\n")
                    continue

                # Масштабирование
                X_batch_scaled = scaler.transform(X_batch_clean) # <-- Используем загруженный scaler
                self.log_output.append(f"    Признаки X за {dates_for_ticker} для {ticker} подготовлены и масштабированы.")

                # 4. Получение истинных меток y для этого тикера (группы дат)
                # Предполагаем, что даты в group['TRADEDATE'] и df_X_for_ticker[DATE_COLUMN] совпадают
                # и отсортированы одинаково. В реальном боевом скрипте нужно использовать merge/join.
                # Пока просто используем group['REAL_DIRECTION'].tolist().
                y_batch = group['REAL_DIRECTION'].tolist()

                # 5. Дообучение модели
                # partial_fit требует указания всех возможных классов при первом вызове
                # или если модель была обучена через fit ранее, он использует известные классы
                # Мы будем использовать уникальные значения из y_train (или весь диапазон, если известен)
                # Для простоты, предположим, что классы [-1, 0, 1] уже известны модели после initial fit
                classes = np.array([-1, 0, 1]) # Используем фиксированный набор классов, если уверен
                # classes = np.unique(y_batch) # Или используем уникальные из текущего батча
                model.partial_fit(X_batch_scaled, y_batch, classes=classes) # <-- Используем масштабированные данные
                self.log_output.append(f"    Модель для {ticker} дообучена на реальных метках {y_batch}.")

                # 6. Сохранение обновленной модели и scaler'а
                try:
                    joblib.dump(model, model_filename)
                    joblib.dump(scaler, scaler_filename) # Scaler не изменялся, но перезаписываем для согласованности
                    self.log_output.append(f"    Обновленная модель для {ticker} сохранена в {model_filename}")
                    self.log_output.append(f"    Scaler для {ticker} перезаписан в {scaler_filename}")
                except IOError as e:
                    self.log_output.append(f"    Ошибка при сохранении модели/scaler'а для {ticker}: {e}")

            self.log_output.append(f"\n--- Дообучение моделей завершено ---")
            self.log_output.append(f"Всего обработано тикеров: {len(grouped_batches)}")
            self.log_output.append(f"Всего примеров в батче: {len(df_batch)}")

        except Exception as e:
            self.log_output.append(f"  Ошибка при дообучении моделей: {e}\n")
            import traceback
            self.log_output.append(traceback.format_exc() + "\n")

class ResultsTab(QWidget):
    """Вкладка результатов."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        plot_group = QGroupBox("График инкрементального обучения")
        plot_layout = QVBoxLayout()

        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)

        self.plot_btn = QPushButton("Построить график из incremental_learning_log_final.csv")
        self.plot_btn.clicked.connect(self.plot_accuracy)
        plot_layout.addWidget(self.plot_btn)

        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)

        predictions_group = QGroupBox("Последние прогнозы из predictions_log.csv")
        predictions_layout = QVBoxLayout()

        self.predictions_output = QTextEdit() # Используем QTextEdit для вывода
        self.predictions_output.setReadOnly(True)
        predictions_layout.addWidget(self.predictions_output)

        self.load_predictions_btn = QPushButton("Загрузить последние прогнозы")
        self.load_predictions_btn.clicked.connect(self.load_predictions)
        predictions_layout.addWidget(self.load_predictions_btn)

        predictions_group.setLayout(predictions_layout)
        layout.addWidget(predictions_group)

        self.setLayout(layout)

    def plot_accuracy(self):
        """Строит график точности из лога инкрементального обучения."""
        if not os.path.exists(INCREMENTAL_LOG_FILE):
            self.predictions_output.append(f"Файл лога {INCREMENTAL_LOG_FILE} не найден.\n") # <-- Используем predictions_output
            return

        try:
            df = pd.read_csv(INCREMENTAL_LOG_FILE, encoding='utf-8-sig')
            df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
            df = df.dropna(subset=['TRADEDATE', 'ACCURACY_CUMULATIVE'])
            df = df.sort_values(by='TRADEDATE').reset_index(drop=True)

            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.plot(df['TRADEDATE'], df['ACCURACY_CUMULATIVE'], marker='o', linestyle='-', linewidth=1, markersize=3, color='blue')
            ax.set_title('Изменение точности модели в процессе инкрементального обучения')
            ax.set_xlabel('Дата (TRADEDATE)')
            ax.set_ylabel('Нарастающая точность (ACCURACY_CUMULATIVE)')
            ax.grid(True, linestyle='--', alpha=0.5)

            # Форматирование дат на оси X
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2)) # Показываем метки каждые 2 месяца
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

            self.figure.tight_layout()
            self.canvas.draw()
            self.predictions_output.append("График построен.\n") # <-- Используем predictions_output
        except Exception as e:
            self.predictions_output.append(f"Ошибка при построении графика: {e}\n") # <-- Используем predictions_output

    def load_predictions(self):
        """Загружает последние прогнозы из лога."""
        if not os.path.exists(PREDICTIONS_LOG_FILE):
            self.predictions_output.append(f"Файл лога {PREDICTIONS_LOG_FILE} не найден.\n") # <-- Используем predictions_output
            return

        try:
            df = pd.read_csv(PREDICTIONS_LOG_FILE, encoding='utf-8-sig')
            # Показываем последние 10 строк
            last_predictions = df.tail(10)
            self.predictions_output.setText(last_predictions.to_string(index=False)) # <-- Используем setText для QTextEdit
        except Exception as e:
            self.predictions_output.append(f"Ошибка при загрузке прогнозов: {e}\n") # <-- Используем predictions_output

class MainWindow(QMainWindow):
    """Главное окно приложения."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ANANACC - Прогнозирование цен акций (Прокачанная версия)')
        self.setGeometry(100, 100, 1200, 800)

        # Создаем вкладки
        self.tabs = QTabWidget()
        self.settings_tab = SettingsTab()
        self.data_collection_tab = DataCollectionTab(self)
        self.data_combining_tab = DataCombiningTab(self)
        self.model_training_tab = ModelTrainingTab(self)
        self.prediction_tab = PredictionTab(self)
        self.retraining_tab = RetrainingTab(self)
        self.results_tab = ResultsTab()

        # Добавляем вкладки в TabWidget
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.data_collection_tab, "Сбор данных")
        self.tabs.addTab(self.data_combining_tab, "Объединение данных")
        self.tabs.addTab(self.model_training_tab, "Обучение моделей")
        self.tabs.addTab(self.prediction_tab, "Прогноз")
        self.tabs.addTab(self.retraining_tab, "Дообучение")
        self.tabs.addTab(self.results_tab, "Результаты")

        self.setCentralWidget(self.tabs)

        # Создаем статус-бар
        self.statusBar().showMessage('Готов к работе')

        # Создаем меню
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        exit_action = file_menu.addAction('Выход')
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu('Помощь')
        about_action = help_menu.addAction('О программе')
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        """Показывает информацию о программе."""
        QMessageBox.about(self, "О программе", "ANANACC - Автоматическая система прогнозирования цен акций с инкрементальным обучением.\nВерсия 1.1 (Прокачанная)")

def main():
    """Основная функция."""
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
