# ananacc_gui.py
import sys
import os
import subprocess
import json
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QFormLayout, QLineEdit, QDateEdit, QComboBox,
    QCalendarWidget, QTableWidget, QTableWidgetItem, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PyQt5.QtCore import QThread, pyqtSignal, QDate, Qt
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import joblib
import numpy as np
import traceback

# --- Конфигурация GUI ---
CONFIG_FILE = 'config.json'
SCRIPTS_DIR = 'scripts'
DEFAULT_CONFIG = {
    'data_dir': 'data',
    'models_dir': 'models',
    'scalers_dir': 'scalers',
    'logs_dir': 'logs',
    'plots_dir': 'plots',
    'historical_data_full_dir': 'historical_data_full',
    'historical_data_indices_dir': 'historical_data_indices',
    'historical_data_currency_dir': 'historical_data_currency',
    'historical_data_oil_dir': 'historical_data_oil',
    'historical_data_other_dir': 'historical_data_other',
    'start_date': '2023-01-01',
    'end_date': datetime.now().strftime('%Y-%m-%d'),
    'model_type': 'PassiveAggressiveClassifier',
}

# --- Глобальные константы ---
DATE_COLUMN = 'TRADEDATE'
TARGET_COLUMN = 'TARGET_DIRECTION'
TEST_SIZE = 0.2
RANDOM_STATE = 42

class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(int)

    def __init__(self, script_path, args=None, parent=None):
        super().__init__(parent)
        self.script_path = script_path
        self.args = args or []

    def run(self):
        try:
            self.output_signal.emit(f"Запуск скрипта: {self.script_path} с аргументами: {self.args}\n")
            cmd = [sys.executable, self.script_path] + self.args
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            progress = 0
            for line in iter(process.stdout.readline, ''):
                self.output_signal.emit(line.rstrip('\n'))
                if 'progress:' in line.lower():
                    try:
                        prog_str = line.split('progress:')[1].strip().replace('%', '')
                        progress = int(prog_str)
                        self.progress_signal.emit(progress)
                    except:
                        pass
                else:
                    progress = min(progress + 5, 100)
                    self.progress_signal.emit(progress)
            process.stdout.close()
            return_code = process.wait()
            self.finished_signal.emit(return_code)
        except Exception as e:
            self.output_signal.emit(f"Ошибка при запуске скрипта {self.script_path}: {e}\n")
            self.finished_signal.emit(-1)

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = self.load_config()
        self.init_ui()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_CONFIG.copy()

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        QMessageBox.information(self, "Настройки", "Настройки сохранены в config.json!")

    def init_ui(self):
        layout = QVBoxLayout()
        paths_group = QGroupBox("Пути к данным и моделям")
        paths_layout = QFormLayout()
        self.data_dir_edit = QLineEdit(self.config['data_dir'])
        paths_layout.addRow("Директория данных:", self.data_dir_edit)
        self.models_dir_edit = QLineEdit(self.config['models_dir'])
        paths_layout.addRow("Директория моделей:", self.models_dir_edit)
        self.scalers_dir_edit = QLineEdit(self.config['scalers_dir'])
        paths_layout.addRow("Директория scaler'ов:", self.scalers_dir_edit)
        self.logs_dir_edit = QLineEdit(self.config['logs_dir'])
        paths_layout.addRow("Директория логов:", self.logs_dir_edit)
        self.plots_dir_edit = QLineEdit(self.config['plots_dir'])
        paths_layout.addRow("Директория графиков:", self.plots_dir_edit)
        self.historical_data_full_dir_edit = QLineEdit(self.config['historical_data_full_dir'])
        paths_layout.addRow("Исторические данные (акции):", self.historical_data_full_dir_edit)
        self.historical_data_indices_dir_edit = QLineEdit(self.config['historical_data_indices_dir'])
        paths_layout.addRow("Исторические данные (индексы):", self.historical_data_indices_dir_edit)
        self.historical_data_currency_dir_edit = QLineEdit(self.config['historical_data_currency_dir'])
        paths_layout.addRow("Исторические данные (валюты):", self.historical_data_currency_dir_edit)
        self.historical_data_oil_dir_edit = QLineEdit(self.config['historical_data_oil_dir'])
        paths_layout.addRow("Исторические данные (нефть):", self.historical_data_oil_dir_edit)
        self.historical_data_other_dir_edit = QLineEdit(self.config['historical_data_other_dir'])
        paths_layout.addRow("Исторические данные (другие):", self.historical_data_other_dir_edit)
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)

        dates_group = QGroupBox("Даты")
        dates_layout = QFormLayout()
        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate.fromString(self.config['start_date'], 'yyyy-MM-dd'))
        dates_layout.addRow("Начальная дата:", self.start_date_edit)
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.fromString(self.config['end_date'], 'yyyy-MM-dd'))
        dates_layout.addRow("Конечная дата:", self.end_date_edit)
        dates_group.setLayout(dates_layout)
        layout.addWidget(dates_group)

        models_group = QGroupBox("Настройки моделей")
        models_layout = QFormLayout()
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["PassiveAggressiveClassifier", "SGDClassifier", "Perceptron"])
        self.model_type_combo.setCurrentText(self.config['model_type'])
        models_layout.addRow("Тип модели:", self.model_type_combo)
        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        self.save_settings_btn = QPushButton("Сохранить настройки")
        self.save_settings_btn.clicked.connect(self.update_and_save)
        layout.addWidget(self.save_settings_btn)
        self.setLayout(layout)

    def update_and_save(self):
        self.config['data_dir'] = self.data_dir_edit.text()
        self.config['models_dir'] = self.models_dir_edit.text()
        self.config['scalers_dir'] = self.scalers_dir_edit.text()
        self.config['logs_dir'] = self.logs_dir_edit.text()
        self.config['plots_dir'] = self.plots_dir_edit.text()
        self.config['historical_data_full_dir'] = self.historical_data_full_dir_edit.text()
        self.config['historical_data_indices_dir'] = self.historical_data_indices_dir_edit.text()
        self.config['historical_data_currency_dir'] = self.historical_data_currency_dir_edit.text()
        self.config['historical_data_oil_dir'] = self.historical_data_oil_dir_edit.text()
        self.config['historical_data_other_dir'] = self.historical_data_other_dir_edit.text()
        self.config['start_date'] = self.start_date_edit.date().toString('yyyy-MM-dd')
        self.config['end_date'] = self.end_date_edit.date().toString('yyyy-MM-dd')
        self.config['model_type'] = self.model_type_combo.currentText()
        self.save_config()

class DataCollectionTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        collection_group = QGroupBox("Сбор данных")
        collection_layout = QVBoxLayout()
        self.get_moex_stocks_btn = QPushButton("Получить список акций (get_moex_stocks.py)")
        self.get_moex_stocks_btn.clicked.connect(lambda: self.run_script('get_moex_stocks.py'))
        collection_layout.addWidget(self.get_moex_stocks_btn)

        self.get_historical_data_btn = QPushButton("Получить историю акций (get_historical_data.py)")
        self.get_historical_data_btn.clicked.connect(lambda: self.run_script('get_historical_data.py'))
        collection_layout.addWidget(self.get_historical_data_btn)

        self.find_indices_btn = QPushButton("Найти индексы (find_indices.py)")
        self.find_indices_btn.clicked.connect(lambda: self.run_script('find_indices.py'))
        collection_layout.addWidget(self.find_indices_btn)

        self.get_index_history_btn = QPushButton("Получить историю индексов (get_index_history.py)")
        self.get_index_history_btn.clicked.connect(lambda: self.run_script('get_index_history.py'))
        collection_layout.addWidget(self.get_index_history_btn)

        self.find_currency_pairs_btn = QPushButton("Найти валютные пары (find_currency_pairs.py)")
        self.find_currency_pairs_btn.clicked.connect(lambda: self.run_script('find_currency_pairs.py'))
        collection_layout.addWidget(self.find_currency_pairs_btn)

        self.get_currency_history_btn = QPushButton("Получить историю валют (get_currency_history.py)")
        self.get_currency_history_btn.clicked.connect(lambda: self.run_script('get_currency_history.py'))
        collection_layout.addWidget(self.get_currency_history_btn)

        self.get_currency_history_cets_btn = QPushButton("Получить историю валют CETS (get_currency_history_cets.py)")
        self.get_currency_history_cets_btn.clicked.connect(lambda: self.run_script('get_currency_history_cets.py'))
        collection_layout.addWidget(self.get_currency_history_cets_btn)

        self.find_oil_futures_btn = QPushButton("Найти фьючерсы на нефть (find_oil_futures.py)")
        self.find_oil_futures_btn.clicked.connect(lambda: self.run_script('find_oil_futures.py'))
        collection_layout.addWidget(self.find_oil_futures_btn)

        self.get_oil_future_history_btn = QPushButton("Получить историю фьючерсов на нефть (get_oil_future_history.py)")
        self.get_oil_future_history_btn.clicked.connect(lambda: self.run_script('get_oil_future_history.py'))
        collection_layout.addWidget(self.get_oil_future_history_btn)

        self.get_key_rate_history_btn = QPushButton("Получить историю ключевой ставки (get_key_rate_history.py)")
        self.get_key_rate_history_btn.clicked.connect(lambda: self.run_script('get_key_rate_history.py'))
        collection_layout.addWidget(self.get_key_rate_history_btn)

        collection_group.setLayout(collection_layout)
        layout.addWidget(collection_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def run_script(self, script_name):
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return
        args = ['--config', CONFIG_FILE]
        self.thread = ScriptRunner(script_path, args)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()
        self.disable_buttons()

    def disable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(False)

    def enable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class DataCombiningTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        combining_group = QGroupBox("Объединение данных")
        combining_layout = QVBoxLayout()
        self.combine_datasets_btn = QPushButton("Объединить данные (combine_datasets.py)")
        self.combine_datasets_btn.clicked.connect(lambda: self.run_script('combine_datasets.py'))
        combining_layout.addWidget(self.combine_datasets_btn)

        self.combine_datasets_all_targets_btn = QPushButton("Добавить TARGET для всех акций (combine_datasets_all_targets.py)")
        self.combine_datasets_all_targets_btn.clicked.connect(lambda: self.run_script('combine_datasets_all_targets.py'))
        combining_layout.addWidget(self.combine_datasets_all_targets_btn)

        combining_group.setLayout(combining_layout)
        layout.addWidget(combining_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def run_script(self, script_name):
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return
        args = ['--config', CONFIG_FILE]
        self.thread = ScriptRunner(script_path, args)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()
        self.disable_buttons()

    def disable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(False)

    def enable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class ModelTrainingTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        training_group = QGroupBox("Обучение моделей")
        training_layout = QVBoxLayout()
        self.train_all_models_btn = QPushButton("Обучить все модели (train_all_models.py)")
        self.train_all_models_btn.clicked.connect(lambda: self.run_script('train_all_models.py'))
        training_layout.addWidget(self.train_all_models_btn)

        training_group.setLayout(training_layout)
        layout.addWidget(training_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def run_script(self, script_name):
        script_path = os.path.join(SCRIPTS_DIR, script_name)
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return
        args = ['--config', CONFIG_FILE]
        self.thread = ScriptRunner(script_path, args)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()
        self.disable_buttons()

    def disable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(False)

    def enable_buttons(self):
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

class PredictionTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        # Создание необходимых директорий
        for dir_path in [
            self.config['logs_dir'],
            self.config['data_dir'],
            self.config['models_dir'],
            self.config['scalers_dir']
        ]:
            os.makedirs(dir_path, exist_ok=True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        prediction_setup_group = QGroupBox("Настройка прогноза")
        prediction_setup_layout = QFormLayout()
        self.ticker_list = QListWidget()
        self.ticker_list.setSelectionMode(QAbstractItemView.MultiSelection)
        prediction_setup_layout.addRow("Выберите тикеры:", self.ticker_list)
        self.select_all_btn = QPushButton("Выбрать все")
        self.select_all_btn.clicked.connect(self.select_all_tickers)
        prediction_setup_layout.addWidget(self.select_all_btn)
        self.clear_selection_btn = QPushButton("Очистить выбор")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        prediction_setup_layout.addWidget(self.clear_selection_btn)
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

        self.auto_predict_btn = QPushButton("Автоматический прогноз и обучение (predict_and_learn.py)")
        self.auto_predict_btn.clicked.connect(self.run_script)  # Исправлено: без lambda
        prediction_actions_layout.addWidget(self.auto_predict_btn)

        prediction_actions_group.setLayout(prediction_actions_layout)
        layout.addWidget(prediction_actions_group)

        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        layout.addWidget(self.result_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.populate_ticker_list()  # Заполняем список тикеров при инициализации

        self.setLayout(layout)

    def run_script(self):
        script_path = os.path.join(SCRIPTS_DIR, 'predict_and_learn.py')
        if not os.path.exists(script_path):
            self.result_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return
        args = ['--config', CONFIG_FILE]
        self.thread = ScriptRunner(script_path, args)
        self.thread.output_signal.connect(self.result_output.append)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()
        self.predict_btn.setEnabled(False)
        self.auto_predict_btn.setEnabled(False)

    def populate_ticker_list(self):
        self.ticker_list.clear()
        models_dir = self.config['models_dir']
        if not os.path.exists(models_dir):
            self.result_output.append(f"Директория моделей {models_dir} не найдена.\n")
            return
        try:
            model_files = [f for f in os.listdir(models_dir) if f.startswith('model_') and f.endswith('.joblib')]
            tickers = sorted(set([f.replace('model_', '').replace('.joblib', '') for f in model_files]))
            for ticker in tickers:
                item = QListWidgetItem(ticker)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.ticker_list.addItem(item)
            self.result_output.append(f"Найдено {len(tickers)} моделей.\n")
        except Exception as e:
            self.result_output.append(f"Ошибка при поиске моделей: {e}\n")

    def select_all_tickers(self):
        for i in range(self.ticker_list.count()):
            item = self.ticker_list.item(i)
            item.setCheckState(Qt.Checked)

    def clear_selection(self):
        for i in range(self.ticker_list.count()):
            item = self.ticker_list.item(i)
            item.setCheckState(Qt.Unchecked)

    def get_selected_tickers(self):
        selected_tickers = []
        for i in range(self.ticker_list.count()):
            item = self.ticker_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_tickers.append(item.text())
        return selected_tickers

    def make_prediction(self):
        selected_tickers = self.get_selected_tickers()
        selected_date = self.date_picker.selectedDate().toString("yyyy-MM-dd")
        self.result_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Запрос прогноза для {selected_tickers} на {selected_date}...\n")
        self.progress_bar.setValue(0)
        if not selected_tickers:
            self.result_output.append("  Ошибка: Тикеры не выбраны.\n")
            return
        try:
            progress_step = 100 / len(selected_tickers) if len(selected_tickers) > 0 else 0
            current_progress = 0
            for selected_model in selected_tickers:
                scalers_dir = self.config['scalers_dir']
                scaler_filename = os.path.join(scalers_dir, f'scaler_{selected_model}.joblib')
                if not os.path.exists(scaler_filename):
                    self.result_output.append(f"  Ошибка: Файл scaler'а {scaler_filename} не найден.\n")
                    continue
                scaler = joblib.load(scaler_filename)
                self.result_output.append(f"  Scaler для {selected_model} загружен.\n")
                current_progress += progress_step * 0.2
                self.progress_bar.setValue(int(current_progress))
                models_dir = self.config['models_dir']
                model_filename = os.path.join(models_dir, f'model_{selected_model}.joblib')
                if not os.path.exists(model_filename):
                    self.result_output.append(f"  Ошибка: Файл модели {model_filename} не найден.\n")
                    continue
                model = joblib.load(model_filename)
                self.result_output.append(f"  Модель для {selected_model} загружена.\n")
                current_progress += progress_step * 0.2
                self.progress_bar.setValue(int(current_progress))
                data_dir = self.config['data_dir']
                combined_file = os.path.join(data_dir, 'combined_dataset.csv')
                if not os.path.exists(combined_file):
                    self.result_output.append(f"  Ошибка: Файл данных {combined_file} не найден.\n")
                    continue
                df_combined = pd.read_csv(combined_file, encoding='utf-8-sig')
                df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
                df_selected = df_combined[df_combined[DATE_COLUMN] == selected_date]
                if df_selected.empty:
                    df_selected = df_combined[df_combined[DATE_COLUMN] <= pd.to_datetime(selected_date)]
                    if df_selected.empty:
                        self.result_output.append(f"  Ошибка: Нет данных до даты {selected_date} для {selected_model}.\n")
                        continue
                    df_selected = df_selected.tail(1)
                self.result_output.append(f"  Найдены данные за {df_selected[DATE_COLUMN].iloc[0].strftime('%Y-%m-%d')} для {selected_model}.\n")
                current_progress += progress_step * 0.2
                self.progress_bar.setValue(int(current_progress))
                # Исключаем целевые столбцы
                feature_columns = [
                    col for col in df_combined.columns
                    if col not in [DATE_COLUMN, TARGET_COLUMN, 'TARGET_CLOSE']
                    and not col.startswith('TARGET_DIRECTION_')
                ]
                X_new = df_selected[feature_columns].copy()
                # Проверяем соответствие признаков
                expected_features = scaler.feature_names_in_ if hasattr(scaler, 'feature_names_in_') else feature_columns
                missing_features = [f for f in expected_features if f not in X_new.columns]
                extra_features = [f for f in X_new.columns if f not in expected_features]
                if missing_features or extra_features:
                    self.result_output.append(f"  Ошибка: Несоответствие признаков для {selected_model}.\n")
                    self.result_output.append(f"    Отсутствуют признаки: {missing_features}\n")
                    self.result_output.append(f"    Лишние признаки: {extra_features}\n")
                    continue
                # Убедимся, что порядок столбцов соответствует ожидаемому
                X_new = X_new[expected_features]
                price_cols = [col for col in X_new.columns if any(suffix in col for suffix in ['_OPEN', '_HIGH', '_LOW', '_CLOSE'])]
                volume_cols = [col for col in X_new.columns if '_VOLUME' in col]
                other_cols = [col for col in X_new.columns if col not in price_cols + volume_cols]
                self.result_output.append(f"  Заполнение цен (ffill/bfill): {len(price_cols)} столбцов для {selected_model}.\n")
                X_new[price_cols] = X_new[price_cols].ffill().bfill()
                self.result_output.append(f"  Заполнение объемов (0): {len(volume_cols)} столбцов для {selected_model}.\n")
                X_new[volume_cols] = X_new[volume_cols].fillna(0)
                self.result_output.append(f"  Заполнение других (0 или ffill): {len(other_cols)} столбцов для {selected_model}.\n")
                cbr_key_rate_cols = [col for col in other_cols if 'CBR_KEY_RATE' in col]
                if cbr_key_rate_cols:
                    self.result_output.append(f"    Заполнение CBR_KEY_RATE (ffill): {cbr_key_rate_cols} для {selected_model}.\n")
                    X_new[cbr_key_rate_cols] = X_new[cbr_key_rate_cols].ffill()
                    other_cols = [col for col in other_cols if col not in cbr_key_rate_cols]
                if other_cols:
                    self.result_output.append(f"    Заполнение остальных (0): {other_cols} для {selected_model}.\n")
                    X_new[other_cols] = X_new[other_cols].fillna(0)
                mask_after_fill = ~X_new.isnull().any(axis=1)
                X_new_clean = X_new[mask_after_fill]
                if X_new_clean.empty:
                    self.result_output.append(f"  Ошибка: После обработки пропусков данные пусты для {selected_model}.\n")
                    continue
                X_new_scaled = scaler.transform(X_new_clean)
                self.result_output.append(f"  Признаки подготовлены и масштабированы для {selected_model}.\n")
                current_progress += progress_step * 0.2
                self.progress_bar.setValue(int(current_progress))
                y_pred = model.predict(X_new_scaled)[0]
                self.result_output.append(f"  Прогноз TARGET_DIRECTION для {selected_model} на {selected_date}: {y_pred}\n")
                current_progress += progress_step * 0.2
                self.progress_bar.setValue(int(current_progress))
                logs_dir = self.config['logs_dir']
                predictions_log_file = os.path.join(logs_dir, 'predictions_log.csv')
                prediction_log_entry = pd.DataFrame([{
                    'TRADEDATE': selected_date,
                    'TICKER': selected_model,
                    'PREDICTED_DIRECTION': y_pred,
                    'TIMESTAMP': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }])
                if os.path.exists(predictions_log_file):
                    prediction_log_entry.to_csv(predictions_log_file, mode='a', header=False, index=False, encoding='utf-8-sig')
                else:
                    prediction_log_entry.to_csv(predictions_log_file, index=False, encoding='utf-8-sig')
                self.result_output.append(f"  Прогноз сохранен в {predictions_log_file} для {selected_model}.\n")
            self.progress_bar.setValue(100)
        except Exception as e:
            self.result_output.append(f"  Ошибка при прогнозировании: {e}\n")
            self.result_output.append(traceback.format_exc() + "\n")
            self.progress_bar.setValue(0)

class RetrainingTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        retraining_group = QGroupBox("Дообучение моделей")
        retraining_layout = QVBoxLayout()
        self.check_predictions_btn = QPushButton("Проверить прогнозы")
        self.check_predictions_btn.clicked.connect(self.check_predictions)
        retraining_layout.addWidget(self.check_predictions_btn)

        self.retrain_models_btn = QPushButton("Дообучить модели")
        self.retrain_models_btn.clicked.connect(self.retrain_models)
        retraining_layout.addWidget(self.retrain_models_btn)

        retraining_group.setLayout(retraining_layout)
        layout.addWidget(retraining_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def check_predictions(self):
        self.log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка прогнозов...\n")
        self.progress_bar.setValue(0)
        try:
            logs_dir = self.config['logs_dir']
            predictions_log_file = os.path.join(logs_dir, 'predictions_log.csv')
            if not os.path.exists(predictions_log_file):
                self.log_output.append(f"  Файл лога {predictions_log_file} не найден.\n")
                return
            df_predictions = pd.read_csv(predictions_log_file, encoding='utf-8-sig')
            self.log_output.append(f"  Загружено {len(df_predictions)} записей из лога прогнозов.\n")
            self.progress_bar.setValue(20)
            data_dir = self.config['data_dir']
            combined_all_targets_file = os.path.join(data_dir, 'combined_dataset_all_targets.csv')
            if not os.path.exists(combined_all_targets_file):
                self.log_output.append(f"  Файл данных {combined_all_targets_file} не найден.\n")
                return
            df_combined = pd.read_csv(combined_all_targets_file, encoding='utf-8-sig')
            df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
            self.log_output.append(f"  Загружены данные для сравнения из {combined_all_targets_file}.\n")
            self.progress_bar.setValue(40)
            today = pd.Timestamp.today().normalize()
            df_overdue = df_predictions[pd.to_datetime(df_predictions['TRADEDATE'], format='%Y-%m-%d', errors='coerce') < today]
            self.log_output.append(f"  Найдено {len(df_overdue)} 'просроченных' прогнозов.\n")
            self.progress_bar.setValue(50)
            if df_overdue.empty:
                self.log_output.append("  Нет просроченных прогнозов для проверки.\n")
                self.progress_bar.setValue(100)
                return
            overdue_to_process = []
            progress_step = 30 / len(df_overdue) if len(df_overdue) > 0 else 0
            current_progress = 50
            for index, row in df_overdue.iterrows():
                pred_date_str = row['TRADEDATE']
                pred_ticker = row['TICKER']
                pred_direction = row['PREDICTED_DIRECTION']
                df_real_data = df_combined[df_combined[DATE_COLUMN] == pd.to_datetime(pred_date_str, format='%Y-%m-%d', errors='coerce')]
                if df_real_data.empty:
                    self.log_output.append(f"    Нет реальных данных за {pred_date_str} для {pred_ticker}. Пропущено.\n")
                    continue
                target_col = f"TARGET_DIRECTION_{pred_ticker}"
                if target_col not in df_real_data.columns:
                    self.log_output.append(f"    Целевая переменная {target_col} не найдена в данных за {pred_date_str}. Пропущено.\n")
                    continue
                real_direction = df_real_data[target_col].iloc[0]
                if pd.isna(real_direction):
                    self.log_output.append(f"    Реальная метка {target_col} за {pred_date_str} NaN. Пропущено.\n")
                    continue
                is_correct = (pred_direction == real_direction)
                overdue_to_process.append({
                    'TRADEDATE': pred_date_str,
                    'TICKER': pred_ticker,
                    'PREDICTED_DIRECTION': pred_direction,
                    'REAL_DIRECTION': real_direction,
                    'IS_CORRECT': is_correct
                })
                self.log_output.append(f"    Проверка {pred_ticker} за {pred_date_str}: Прогноз={pred_direction}, Истина={real_direction}, {'Верно' if is_correct else 'Неверно'}\n")
                current_progress += progress_step
                self.progress_bar.setValue(int(current_progress))
            if overdue_to_process:
                df_overdue_batch = pd.DataFrame(overdue_to_process)
                batch_filename = os.path.join(logs_dir, f"overdue_predictions_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                df_overdue_batch.to_csv(batch_filename, index=False, encoding='utf-8-sig')
                self.log_output.append(f"  Сформирован батч для дообучения: {batch_filename}\n")
                self.log_output.append(f"  В батче {len(df_overdue_batch)} примеров.\n")
                self.overdue_batch_filename = batch_filename
            else:
                self.log_output.append("  Нет корректных данных для формирования батча.\n")
            self.progress_bar.setValue(100)
        except Exception as e:
            self.log_output.append(f"  Ошибка при проверке прогнозов: {e}\n")
            self.log_output.append(traceback.format_exc() + "\n")
            self.progress_bar.setValue(0)

    def retrain_models(self):
        self.log_output.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Дообучение моделей...\n")
        self.progress_bar.setValue(0)
        try:
            if not hasattr(self, 'overdue_batch_filename') or not os.path.exists(self.overdue_batch_filename):
                self.log_output.append(f"  Файл батча для дообучения не найден. Сначала выполните 'Проверить прогнозы'.\n")
                return
            df_batch = pd.read_csv(self.overdue_batch_filename, encoding='utf-8-sig')
            self.log_output.append(f"  Загружен батч для дообучения: {len(df_batch)} примеров.\n")
            self.progress_bar.setValue(20)
            if df_batch.empty:
                self.log_output.append("  Батч пуст. Дообучение невозможно.\n")
                return
            grouped_batches = df_batch.groupby('TICKER')
            progress_step = 80 / len(grouped_batches) if len(grouped_batches) > 0 else 0
            current_progress = 20
            for ticker, group in grouped_batches:
                self.log_output.append(f"  Дообучение модели для {ticker}...")
                models_dir = self.config['models_dir']
                scalers_dir = self.config['scalers_dir']
                model_filename = os.path.join(models_dir, f'model_{ticker}.joblib')
                scaler_filename = os.path.join(scalers_dir, f'scaler_{ticker}.joblib')
                if not os.path.exists(model_filename) or not os.path.exists(scaler_filename):
                    self.log_output.append(f"    Ошибка: Файл модели ({model_filename}) или scaler'а ({scaler_filename}) для {ticker} не найден.\n")
                    continue
                model = joblib.load(model_filename)
                scaler = joblib.load(scaler_filename)
                self.log_output.append(f"    Модель и scaler для {ticker} загружены.")
                data_dir = self.config['data_dir']
                combined_file = os.path.join(data_dir, 'combined_dataset.csv')
                if not os.path.exists(combined_file):
                    self.log_output.append(f"    Ошибка: Файл данных {combined_file} не найден.\n")
                    continue
                df_combined = pd.read_csv(combined_file, encoding='utf-8-sig')
                df_combined[DATE_COLUMN] = pd.to_datetime(df_combined[DATE_COLUMN], format='%Y-%m-%d', errors='coerce')
                dates_for_ticker = group['TRADEDATE'].tolist()
                df_X_for_ticker = df_combined[df_combined[DATE_COLUMN].isin(pd.to_datetime(dates_for_ticker, format='%Y-%m-%d', errors='coerce'))]
                if df_X_for_ticker.empty:
                    self.log_output.append(f"    Нет данных для дообучения модели {ticker} по датам {dates_for_ticker}. Пропущено.\n")
                    continue
                feature_columns = [
                    col for col in df_combined.columns
                    if col not in [DATE_COLUMN, TARGET_COLUMN, 'TARGET_CLOSE']
                    and not col.startswith('TARGET_DIRECTION_')
                ]
                X_batch = df_X_for_ticker[feature_columns].copy()
                # Проверяем соответствие признаков
                expected_features = scaler.feature_names_in_ if hasattr(scaler, 'feature_names_in_') else feature_columns
                missing_features = [f for f in expected_features if f not in X_batch.columns]
                extra_features = [f for f in X_batch.columns if f not in expected_features]
                if missing_features or extra_features:
                    self.log_output.append(f"    Ошибка: Несоответствие признаков для {ticker}.\n")
                    self.log_output.append(f"      Отсутствуют признаки: {missing_features}\n")
                    self.log_output.append(f"      Лишние признаки: {extra_features}\n")
                    continue
                X_batch = X_batch[expected_features]
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
                X_batch_scaled = scaler.transform(X_batch_clean)
                self.log_output.append(f"    Признаки X за {dates_for_ticker} для {ticker} подготовлены и масштабированы.")
                y_batch = group['REAL_DIRECTION'].tolist()
                classes = np.array([-1, 0, 1])
                model.partial_fit(X_batch_scaled, y_batch, classes=classes)
                self.log_output.append(f"    Модель для {ticker} дообучена на реальных метках {y_batch}.")
                joblib.dump(model, model_filename)
                joblib.dump(scaler, scaler_filename)
                self.log_output.append(f"    Обновленная модель для {ticker} сохранена в {model_filename}")
                self.log_output.append(f"    Scaler для {ticker} перезаписан в {scaler_filename}")
                current_progress += progress_step
                self.progress_bar.setValue(int(current_progress))
            self.log_output.append(f"\n--- Дообучение моделей завершено ---")
            self.log_output.append(f"Всего обработано тикеров: {len(grouped_batches)}")
            self.log_output.append(f"Всего примеров в батче: {len(df_batch)}")
            self.progress_bar.setValue(100)
        except Exception as e:
            self.log_output.append(f"  Ошибка при дообучении моделей: {e}\n")
            self.log_output.append(traceback.format_exc() + "\n")
            self.progress_bar.setValue(0)
            
class ResultsTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.config = main_window.settings_tab.config
        # Создание необходимых директорий
        for dir_path in [self.config['logs_dir'], self.config['plots_dir']]:
            os.makedirs(dir_path, exist_ok=True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        plot_group = QGroupBox("График инкрементального обучения")
        plot_layout = QVBoxLayout()
        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        plot_layout.addWidget(self.canvas)
        self.plot_btn = QPushButton("Построить график (plot_incremental_learning.py)")
        self.plot_btn.clicked.connect(self.run_plot_script)
        plot_layout.addWidget(self.plot_btn)
        plot_group.setLayout(plot_layout)
        layout.addWidget(plot_group)

        predictions_group = QGroupBox("Последние прогнозы")
        predictions_layout = QVBoxLayout()
        self.predictions_table = QTableWidget()
        predictions_layout.addWidget(self.predictions_table)
        self.load_predictions_btn = QPushButton("Загрузить последние прогнозы")
        self.load_predictions_btn.clicked.connect(self.load_predictions)
        predictions_layout.addWidget(self.load_predictions_btn)
        predictions_group.setLayout(predictions_layout)
        layout.addWidget(predictions_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def run_plot_script(self):
        script_path = os.path.join(SCRIPTS_DIR, 'plot_incremental_learning.py')
        if not os.path.exists(script_path):
            self.log_output.append(f"Ошибка: Скрипт {script_path} не найден.\n")
            return
        args = ['--config', CONFIG_FILE]
        self.thread = ScriptRunner(script_path, args)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.progress_signal.connect(self.progress_bar.setValue)
        self.thread.finished_signal.connect(self.on_script_finished)
        self.thread.start()
        self.plot_btn.setEnabled(False)

    def on_script_finished(self, return_code):
        self.plot_btn.setEnabled(True)
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
            self.plot_accuracy()
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000)

    def plot_accuracy(self):
        logs_dir = self.config['logs_dir']
        incremental_log_file = os.path.join(logs_dir, 'incremental_learning_log_final.csv')
        if not os.path.exists(incremental_log_file):
            self.log_output.append(f"Файл лога {incremental_log_file} не найден.\n")
            return
        try:
            df = pd.read_csv(incremental_log_file, encoding='utf-8-sig')
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
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            self.figure.tight_layout()
            self.canvas.draw()
            self.log_output.append("График построен.\n")
        except Exception as e:
            self.log_output.append(f"Ошибка при построении графика: {e}\n")

    def load_predictions(self):
        logs_dir = self.config['logs_dir']
        predictions_log_file = os.path.join(logs_dir, 'predictions_log.csv')
        if not os.path.exists(predictions_log_file):
            self.log_output.append(f"Файл лога {predictions_log_file} не найден.\n")
            return
        try:
            df = pd.read_csv(predictions_log_file, encoding='utf-8-sig')
            last_predictions = df.tail(10)
            self.predictions_table.setRowCount(len(last_predictions))
            self.predictions_table.setColumnCount(len(last_predictions.columns))
            self.predictions_table.setHorizontalHeaderLabels(last_predictions.columns)
            for i in range(len(last_predictions)):
                for j in range(len(last_predictions.columns)):
                    self.predictions_table.setItem(i, j, QTableWidgetItem(str(last_predictions.iloc[i, j])))
            self.log_output.append("Последние прогнозы загружены.\n")
        except Exception as e:
            self.log_output.append(f"Ошибка при загрузке прогнозов: {e}\n")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_tab = SettingsTab()
        # Создаем все необходимые директории при запуске GUI
        self.create_directories()
        self.init_ui()

    def create_directories(self):
        """Создает все директории из конфигурации, если они не существуют."""
        dirs_to_create = [
            self.settings_tab.config['data_dir'],
            self.settings_tab.config['models_dir'],
            self.settings_tab.config['scalers_dir'],
            self.settings_tab.config['logs_dir'],
            self.settings_tab.config['plots_dir'],
            self.settings_tab.config['historical_data_full_dir'],
            self.settings_tab.config['historical_data_indices_dir'],
            self.settings_tab.config['historical_data_currency_dir'],
            self.settings_tab.config['historical_data_oil_dir'],
            self.settings_tab.config['historical_data_other_dir'],
        ]
        for dir_path in dirs_to_create:
            os.makedirs(dir_path, exist_ok=True)

    def init_ui(self):
        self.setWindowTitle('ANANACC - Прогнозирование цен акций (Прокачанная версия)')
        self.setGeometry(100, 100, 1200, 800)
        self.tabs = QTabWidget()
        self.data_collection_tab = DataCollectionTab(self)
        self.data_combining_tab = DataCombiningTab(self)
        self.model_training_tab = ModelTrainingTab(self)
        self.prediction_tab = PredictionTab(self)
        self.retraining_tab = RetrainingTab(self)
        self.results_tab = ResultsTab(self)
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.data_collection_tab, "Сбор данных")
        self.tabs.addTab(self.data_combining_tab, "Объединение данных")
        self.tabs.addTab(self.model_training_tab, "Обучение моделей")
        self.tabs.addTab(self.prediction_tab, "Прогноз")
        self.tabs.addTab(self.retraining_tab, "Дообучение")
        self.tabs.addTab(self.results_tab, "Результаты")
        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage('Готов к работе')
        menubar = self.menuBar()
        file_menu = menubar.addMenu('Файл')
        exit_action = file_menu.addAction('Выход')
        exit_action.triggered.connect(self.close)
        help_menu = menubar.addMenu('Помощь')
        about_action = help_menu.addAction('О программе')
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        QMessageBox.about(self, "О программе", "ANANACC - Автоматическая система прогнозирования цен акций с инкрементальным обучением.\nВерсия 2.0 (Прокачанная)")

def main():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
