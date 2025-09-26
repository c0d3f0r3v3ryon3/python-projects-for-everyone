# ananacc_gui_pro.py
import sys
import os
import subprocess
import pandas as pd
import numpy as np
import joblib
import logging
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QGroupBox, QFormLayout, QLineEdit, QDateEdit, QComboBox,
    QMessageBox, QProgressBar, QCalendarWidget, QTableWidget, QTableWidgetItem,
    QFileDialog, QSplitter, QStatusBar, QMenuBar, QAction, QCheckBox
)
from PyQt5.QtCore import QThread, pyqtSignal, QDate, Qt
from PyQt5.QtGui import QIcon, QFont
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates
from config import *

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'gui_log.log')),
        logging.StreamHandler()
    ]
)

# --- Поток для запуска скриптов ---
class ScriptRunner(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(int)

    def __init__(self, script_path, args=None):
        super().__init__()
        self.script_path = script_path
        self.args = args or []

    def run(self):
        try:
            cmd = [sys.executable, self.script_path] + self.args
            self.output_signal.emit(f"Запуск: {' '.join(cmd)}\n")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            for line in iter(process.stdout.readline, ''):
                self.output_signal.emit(line.rstrip('\n'))
            return_code = process.wait()
            self.finished_signal.emit(return_code)
        except Exception as e:
            self.output_signal.emit(f"Ошибка: {str(e)}\n")
            self.finished_signal.emit(-1)

# --- Вкладка "Настройки" ---
class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа путей
        paths_group = QGroupBox("Пути к данным и моделям")
        paths_layout = QFormLayout()
        self.paths = {}
        for name, path in PATHS.items():
            self.paths[name] = QLineEdit(path)
            paths_layout.addRow(f"{name}:", self.paths[name])
        paths_group.setLayout(paths_layout)

        # Группа дат
        dates_group = QGroupBox("Диапазон дат")
        dates_layout = QFormLayout()
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate(2023, 1, 1))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        dates_layout.addRow("Начальная дата:", self.start_date)
        dates_layout.addRow("Конечная дата:", self.end_date)
        dates_group.setLayout(dates_layout)

        # Группа моделей
        models_group = QGroupBox("Параметры моделей")
        models_layout = QFormLayout()
        self.model_type = QComboBox()
        self.model_type.addItems(MODEL_TYPES)
        models_layout.addRow("Тип модели:", self.model_type)
        models_group.setLayout(models_layout)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить настройки")
        save_btn.clicked.connect(self.save_settings)

        layout.addWidget(paths_group)
        layout.addWidget(dates_group)
        layout.addWidget(models_group)
        layout.addWidget(save_btn)
        self.setLayout(layout)

    def save_settings(self):
        for name, widget in self.paths.items():
            PATHS[name] = widget.text()
        QMessageBox.information(self, "Настройки", "Настройки сохранены!")
        logging.info("Настройки сохранены")

# --- Вкладка "Сбор данных" ---
class DataCollectionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        scripts = {
            "Получить список акций": ("data_collection/get_moex_stocks.py", "Сбор списка акций с MOEX"),
            "Получить историю акций": ("data_collection/get_historical_data.py", "Сбор исторических данных акций"),
            "Получить историю индексов": ("data_collection/get_index_history.py", "Сбор истории индексов"),
            "Получить историю валют": ("data_collection/get_currency_history.py", "Сбор истории валютных пар"),
            "Получить историю нефти": ("data_collection/get_oil_future_history.py", "Сбор истории фьючерсов на нефть"),
            "Получить ключевую ставку": ("data_collection/get_key_rate_history.py", "Сбор истории ключевой ставки ЦБ")
        }

        for text, (script, desc) in scripts.items():
            btn = QPushButton(text)
            btn.setToolTip(desc)
            btn.clicked.connect(lambda _, s=script: self.run_script(s))
            layout.addWidget(btn)

        layout.addWidget(QLabel("Лог выполнения:"))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def run_script(self, script_path):
        full_path = os.path.join(SCRIPTS_DIR, script_path)
        if not os.path.exists(full_path):
            self.log_output.append(f"Ошибка: скрипт {full_path} не найден.\n")
            return

        self.thread = ScriptRunner(full_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(lambda code: self.on_script_finished(code, script_path))
        self.thread.start()

    def on_script_finished(self, code, script_path):
        if code == 0:
            self.log_output.append(f"✅ Скрипт {os.path.basename(script_path)} завершен успешно.\n")
        else:
            self.log_output.append(f"❌ Скрипт {os.path.basename(script_path)} завершен с ошибкой (код {code}).\n")

# --- Вкладка "Объединение данных" ---
class DataCombiningTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        btn1 = QPushButton("Объединить данные (целевая акция)")
        btn1.clicked.connect(lambda: self.run_script("data_processing/combine_datasets.py"))
        btn2 = QPushButton("Добавить TARGET_DIRECTION для всех акций")
        btn2.clicked.connect(lambda: self.run_script("data_processing/combine_datasets_all_targets.py"))

        layout.addWidget(btn1)
        layout.addWidget(btn2)
        layout.addWidget(QLabel("Лог выполнения:"))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def run_script(self, script_path):
        full_path = os.path.join(SCRIPTS_DIR, script_path)
        if not os.path.exists(full_path):
            self.log_output.append(f"Ошибка: скрипт {full_path} не найден.\n")
            return

        self.thread = ScriptRunner(full_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(lambda code: self.on_script_finished(code, script_path))
        self.thread.start()

    def on_script_finished(self, code, script_path):
        if code == 0:
            self.log_output.append(f"✅ Скрипт {os.path.basename(script_path)} завершен успешно.\n")
        else:
            self.log_output.append(f"❌ Скрипт {os.path.basename(script_path)} завершен с ошибкой (код {code}).\n")

# --- Вкладка "Обучение моделей" ---
class ModelTrainingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.train_btn = QPushButton("Обучить все модели (PassiveAggressive)")
        self.train_btn.clicked.connect(lambda: self.run_script("model_training/train_all_models.py"))

        layout.addWidget(self.train_btn)
        layout.addWidget(QLabel("Лог обучения:"))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def run_script(self, script_path):
        full_path = os.path.join(SCRIPTS_DIR, script_path)
        if not os.path.exists(full_path):
            self.log_output.append(f"Ошибка: скрипт {full_path} не найден.\n")
            return

        self.thread = ScriptRunner(full_path)
        self.thread.output_signal.connect(self.log_output.append)
        self.thread.finished_signal.connect(lambda code: self.on_script_finished(code, script_path))
        self.thread.start()

    def on_script_finished(self, code, script_path):
        if code == 0:
            self.log_output.append(f"✅ Обучение моделей завершено успешно.\n")
        else:
            self.log_output.append(f"❌ Ошибка при обучении моделей (код {code}).\n")

# --- Вкладка "Прогнозирование" ---
class PredictionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Выбор модели
        model_group = QGroupBox("Выбор модели и даты")
        model_layout = QFormLayout()
        self.model_selector = QComboBox()
        self.populate_models()
        self.date_picker = QCalendarWidget()
        self.date_picker.setSelectedDate(QDate.currentDate())
        model_layout.addRow("Модель (тикер):", self.model_selector)
        model_layout.addRow("Дата прогноза:", self.date_picker)
        model_group.setLayout(model_layout)

        # Кнопка прогноза
        self.predict_btn = QPushButton("Получить прогноз")
        self.predict_btn.clicked.connect(self.make_prediction)

        # Результат
        self.result_label = QLabel("Результат прогноза будет здесь")
        self.result_label.setWordWrap(True)

        layout.addWidget(model_group)
        layout.addWidget(self.predict_btn)
        layout.addWidget(self.result_label)
        self.setLayout(layout)

    def populate_models(self):
        if not os.path.exists(MODELS_DIR):
            self.result_label.setText("Ошибка: директория моделей не найдена.")
            return
        try:
            model_files = [f for f in os.listdir(MODELS_DIR) if f.endswith('.joblib')]
            tickers = sorted({f.replace('model_', '').replace('.joblib', '') for f in model_files})
            self.model_selector.addItems(tickers)
            self.result_label.setText(f"Загружено {len(tickers)} моделей.")
        except Exception as e:
            self.result_label.setText(f"Ошибка загрузки моделей: {e}")

    def make_prediction(self):
        ticker = self.model_selector.currentText()
        date = self.date_picker.selectedDate().toString("yyyy-MM-dd")
        self.result_label.setText(f"Запрос прогноза для {ticker} на {date}...")

        try:
            # Загрузка модели и scaler'а
            model_path = os.path.join(MODELS_DIR, f"model_{ticker}.joblib")
            scaler_path = os.path.join(SCALERS_DIR, f"scaler_{ticker}.joblib")
            if not os.path.exists(model_path) or not os.path.exists(scaler_path):
                self.result_label.setText(f"Ошибка: модель или scaler для {ticker} не найдены.")
                return

            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)

            # Загрузка данных
            df = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
            features = df[df['TRADEDATE'] == date].drop(
                columns=['TRADEDATE'] + [c for c in df.columns if c.startswith('TARGET_DIRECTION_')]
            )
            if features.empty:
                self.result_label.setText(f"Ошибка: нет данных для {ticker} на {date}.")
                return

            # Прогноз
            features_scaled = scaler.transform(features)
            prediction = model.predict(features_scaled)[0]
            prediction_text = {
                -1: "📉 <b>Падение</b> (продавать)",
                0: "🟡 <b>Нейтрально</b> (держать)",
                1: "📈 <b>Рост</b> (покупать)"
            }.get(prediction, f"Неизвестно ({prediction})")

            self.result_label.setText(
                f"Прогноз для {ticker} на {date}: {prediction_text}"
            )

            # Логирование
            log_entry = pd.DataFrame([[date, ticker, prediction, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]],
                                    columns=['TRADEDATE', 'TICKER', 'PREDICTION', 'TIMESTAMP'])
            log_entry.to_csv(PREDICTIONS_LOG_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')

        except Exception as e:
            self.result_label.setText(f"Ошибка прогнозирования: {e}")

# --- Вкладка "Дообучение" ---
class RetrainingTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self.check_btn = QPushButton("Проверить прогнозы")
        self.check_btn.clicked.connect(self.check_predictions)

        self.retrain_btn = QPushButton("Дообучить модели")
        self.retrain_btn.clicked.connect(self.retrain_models)

        layout.addWidget(self.check_btn)
        layout.addWidget(self.retrain_btn)
        layout.addWidget(QLabel("Лог дообучения:"))
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def check_predictions(self):
        self.log_output.append("=== Проверка прогнозов ===\n")
        try:
            if not os.path.exists(PREDICTIONS_LOG_FILE):
                self.log_output.append("Файл лога прогнозов не найден.\n")
                return

            df_pred = pd.read_csv(PREDICTIONS_LOG_FILE)
            df_data = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)

            overdue = df_pred[df_pred['TRADEDATE'] < datetime.now().strftime('%Y-%m-%d')]
            if overdue.empty:
                self.log_output.append("Нет просроченных прогнозов.\n")
                return

            self.log_output.append(f"Найдено {len(overdue)} просроченных прогнозов.\n")
            self.overdue_batch = overdue
            self.log_output.append("Готово к дообучению.\n")

        except Exception as e:
            self.log_output.append(f"Ошибка: {e}\n")

    def retrain_models(self):
        if not hasattr(self, 'overdue_batch'):
            self.log_output.append("Сначала проверьте прогнозы!\n")
            return

        self.log_output.append("=== Дообучение моделей ===\n")
        try:
            models, scalers = {}, {}
            for filename in os.listdir(MODELS_DIR):
                if filename.endswith('.joblib'):
                    ticker = filename.replace('model_', '').replace('.joblib', '')
                    models[ticker] = joblib.load(os.path.join(MODELS_DIR, filename))
                    scalers[ticker] = joblib.load(os.path.join(SCALERS_DIR, f"scaler_{ticker}.joblib"))

            for _, row in self.overdue_batch.iterrows():
                ticker = row['TICKER']
                date = row['TRADEDATE']
                pred = row['PREDICTION']

                if ticker not in models:
                    continue

                real_target = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
                real_target = real_target[real_target['TRADEDATE'] == date][f"TARGET_DIRECTION_{ticker}"].iloc[0]

                # Подготовка данных для дообучения
                features = pd.read_csv(COMBINED_DATASET_ALL_TARGETS_FILE)
                features = features[features['TRADEDATE'] == date].drop(
                    columns=['TRADEDATE'] + [c for c in features.columns if c.startswith('TARGET_DIRECTION_')]
                )
                if not features.empty:
                    features_scaled = scalers[ticker].transform(features)
                    models[ticker].partial_fit(features_scaled, [real_target], classes=[-1, 0, 1])
                    joblib.dump(models[ticker], os.path.join(MODELS_DIR, f"model_{ticker}.joblib"))

                self.log_output.append(f"Модель {ticker} дообучена. Реальное значение: {real_target}, прогноз был: {pred}\n")

            self.log_output.append("Дообучение завершено.\n")

        except Exception as e:
            self.log_output.append(f"Ошибка дообучения: {e}\n")

# --- Вкладка "Результаты" ---
class ResultsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # График точности
        self.figure = plt.Figure(figsize=(10, 5), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.plot_btn = QPushButton("Обновить график точности")
        self.plot_btn.clicked.connect(self.plot_accuracy)

        # Таблица прогнозов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Дата", "Тикер", "Прогноз", "Время"])
        self.load_btn = QPushButton("Загрузить последние прогнозы")
        self.load_btn.clicked.connect(self.load_predictions)

        layout.addWidget(QLabel("График точности модели:"))
        layout.addWidget(self.canvas)
        layout.addWidget(self.plot_btn)
        layout.addWidget(QLabel("Последние прогнозы:"))
        layout.addWidget(self.table)
        layout.addWidget(self.load_btn)
        self.setLayout(layout)

    def plot_accuracy(self):
        if not os.path.exists(INCREMENTAL_LOG_FILE):
            QMessageBox.warning(self, "Ошибка", "Файл лога точности не найден.")
            return

        df = pd.read_csv(INCREMENTAL_LOG_FILE)
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        df = df.sort_values('TRADEDATE')

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.plot(df['TRADEDATE'], df['ACCURACY_CUMULATIVE'], marker='o', color='green')
        ax.set_title("Точность модели в процессе обучения")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Точность")
        ax.grid(True)
        self.canvas.draw()

    def load_predictions(self):
        if not os.path.exists(PREDICTIONS_LOG_FILE):
            QMessageBox.warning(self, "Ошибка", "Файл лога прогнозов не найден.")
            return

        df = pd.read_csv(PREDICTIONS_LOG_FILE).tail(10)
        self.table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.table.setItem(i, 0, QTableWidgetItem(row['TRADEDATE']))
            self.table.setItem(i, 1, QTableWidgetItem(row['TICKER']))
            self.table.setItem(i, 2, QTableWidgetItem({
                -1: "📉 Падение",
                0: "🟡 Нейтрально",
                1: "📈 Рост"
            }.get(row['PREDICTION'], str(row['PREDICTION']))))
            self.table.setItem(i, 3, QTableWidgetItem(row['TIMESTAMP']))

# --- Главное окно ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("ANANACC Pro – Прогнозирование цен акций")
        self.setGeometry(100, 100, 1200, 800)
        self.setWindowIcon(QIcon("icon.png"))

        # Темная тема
        self.setStyleSheet("""
            QMainWindow { background-color: #2B2B2B; }
            QLabel, QGroupBox { color: #E0E0E0; }
            QPushButton {
                background-color: #3C3C3C;
                color: #E0E0E0;
                border: 1px solid #555;
                padding: 5px;
            }
            QPushButton:hover { background-color: #4A4A4A; }
            QTextEdit, QTableWidget {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: 1px solid #555;
            }
            QStatusBar { background-color: #1E1E1E; color: #E0E0E0; }
        """)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.addTab(SettingsTab(), "🔧 Настройки")
        self.tabs.addTab(DataCollectionTab(), "📥 Сбор данных")
        self.tabs.addTab(DataCombiningTab(), "🔗 Объединение данных")
        self.tabs.addTab(ModelTrainingTab(), "🤖 Обучение моделей")
        self.tabs.addTab(PredictionTab(), "🔮 Прогнозирование")
        self.tabs.addTab(RetrainingTab(), "🔄 Дообучение")
        self.tabs.addTab(ResultsTab(), "📊 Результаты")
        self.setCentralWidget(self.tabs)

        # Статус-бар
        self.statusBar().showMessage("Готов к работе")

        # Меню
        menubar = self.menuBar()
        file_menu = menubar.addMenu("📁 Файл")
        exit_action = file_menu.addAction("🚪 Выход")
        exit_action.triggered.connect(self.close)

        help_menu = menubar.addMenu("❓ Помощь")
        about_action = help_menu.addAction("ℹ️ О программе")
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        QMessageBox.about(
            self, "О программе",
            """<h2>ANANACC Pro</h2>
            <p><b>Автоматическая система прогнозирования направления движения цен акций</b>
            с инкрементальным обучением.</p>
            <p><b>Версия:</b> 1.0 Pro<br>
            <b>Автор:</b> Иван Василькин<br>
            <b>Лицензия:</b> MIT</p>
            <p><b>Функции:</b>
            <ul>
                <li>Сбор исторических данных с MOEX</li>
                <li>Объединение данных и формирование целевых переменных</li>
                <li>Обучение моделей (PassiveAggressive, SGD)</li>
                <li>Прогнозирование направления движения цен</li>
                <li>Инкрементальное дообучение моделей</li>
                <li>Визуализация результатов</li>
            </ul>
            </p>
            """
        )

# --- Запуск ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
