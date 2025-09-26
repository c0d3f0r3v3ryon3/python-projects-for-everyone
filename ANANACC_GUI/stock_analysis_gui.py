import sys
import pandas as pd
import plotly.express as px
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout,
                             QPushButton, QTextEdit, QTableWidget, QTableWidgetItem,
                             QLineEdit, QLabel, QGridLayout, QMessageBox)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QThread, pyqtSignal
import logging
import os
from datetime import datetime, timedelta

# Импорт скриптов
from get_moex_stocks import get_moex_stocks
from get_historical_data import get_historical_data
from find_indices import find_indices
from find_currency_pairs import find_currency_pairs
from find_oil_futures import find_oil_futures
from get_key_rate_history import get_key_rate_history
from combine_datasets import combine_datasets
from train_all_models import train_all_models
from predict_and_learn import predict_and_learn
from plot_incremental_learning import plot_accuracy

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

class WorkerThread(QThread):
    log_signal = pyqtSignal(str)
    data_signal = pyqtSignal(pd.DataFrame)
    plot_signal = pyqtSignal(str)

    def __init__(self, task, **kwargs):
        super().__init__()
        self.task = task
        self.kwargs = kwargs

    def run(self):
        try:
            if self.task == 'get_moex_stocks':
                get_moex_stocks()
                self.log_signal.emit("Список акций успешно сохранен в data/stocks.csv")
            elif self.task == 'find_indices':
                find_indices()
                self.log_signal.emit("Список индексов сохранен в data/indices.csv")
            elif self.task == 'find_currency_pairs':
                find_currency_pairs()
                self.log_signal.emit("Список валют сохранен в data/currencies.csv")
            elif self.task == 'find_oil_futures':
                find_oil_futures()
                self.log_signal.emit("Фьючерсы Brent сохранены в data/oil_futures.csv")
            elif self.task == 'get_key_rate_history':
                get_key_rate_history()
                self.log_signal.emit("Ключевая ставка сохранена в data/key_rate.csv")
            elif self.task == 'get_historical_data':
                get_historical_data(start_date=self.kwargs.get('start_date'),
                                  end_date=self.kwargs.get('end_date'))
                self.log_signal.emit("Исторические данные собраны")
            elif self.task == 'combine_datasets':
                combine_datasets()
                df = pd.read_csv('data/combined_dataset_all_targets.csv')
                self.data_signal.emit(df.head(100))
                self.log_signal.emit("Данные объединены в data/combined_dataset_all_targets.csv")
            elif self.task == 'train_all_models':
                train_all_models()
                self.log_signal.emit("Модели обучены и сохранены в models/")
            elif self.task == 'predict_and_learn':
                predict_and_learn()
                self.log_signal.emit("Прогнозы выполнены, модели дообучены")
                self.plot_signal.emit('data/accuracy_plot.html')
        except Exception as e:
            self.log_signal.emit(f"Ошибка: {str(e)}")
            logger.error(f"Ошибка в задаче {self.task}: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализ и прогнозирование акций")
        self.setGeometry(100, 100, 1200, 800)

        # Основной виджет и вкладки
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Вкладка 1: Сбор данных
        self.data_tab = QWidget()
        self.tabs.addTab(self.data_tab, "Сбор данных")
        self.setup_data_tab()

        # Вкладка 2: Обучение и прогнозирование
        self.model_tab = QWidget()
        self.tabs.addTab(self.model_tab, "Обучение и прогнозирование")
        self.setup_model_tab()

        # Вкладка 3: Визуализация
        self.plot_tab = QWidget()
        self.tabs.addTab(self.plot_tab, "Визуализация")
        self.setup_plot_tab()

    def setup_data_tab(self):
        layout = QGridLayout()

        # Поля для параметров
        self.start_date_input = QLineEdit("2023-01-01")
        self.end_date_input = QLineEdit(datetime.now().strftime("%Y-%m-%d"))
        layout.addWidget(QLabel("Дата начала:"), 0, 0)
        layout.addWidget(self.start_date_input, 0, 1)
        layout.addWidget(QLabel("Дата окончания:"), 1, 0)
        layout.addWidget(self.end_date_input, 1, 1)

        # Кнопки для сбора данных
        self.btn_get_stocks = QPushButton("Получить список акций")
        self.btn_get_stocks.clicked.connect(self.run_get_moex_stocks)
        layout.addWidget(self.btn_get_stocks, 2, 0, 1, 2)

        self.btn_find_indices = QPushButton("Получить индексы")
        self.btn_find_indices.clicked.connect(self.run_find_indices)
        layout.addWidget(self.btn_find_indices, 3, 0, 1, 2)

        self.btn_find_currencies = QPushButton("Получить валютные пары")
        self.btn_find_currencies.clicked.connect(self.run_find_currency_pairs)
        layout.addWidget(self.btn_find_currencies, 4, 0, 1, 2)

        self.btn_find_oil = QPushButton("Получить фьючерсы Brent")
        self.btn_find_oil.clicked.connect(self.run_find_oil_futures)
        layout.addWidget(self.btn_find_oil, 5, 0, 1, 2)

        self.btn_get_key_rate = QPushButton("Получить ключевую ставку")
        self.btn_get_key_rate.clicked.connect(self.run_get_key_rate_history)
        layout.addWidget(self.btn_get_key_rate, 6, 0, 1, 2)

        self.btn_get_historical = QPushButton("Собрать исторические данные")
        self.btn_get_historical.clicked.connect(self.run_get_historical_data)
        layout.addWidget(self.btn_get_historical, 7, 0, 1, 2)

        self.btn_combine = QPushButton("Объединить данные")
        self.btn_combine.clicked.connect(self.run_combine_datasets)
        layout.addWidget(self.btn_combine, 8, 0, 1, 2)

        # Таблица для отображения данных
        self.data_table = QTableWidget()
        layout.addWidget(self.data_table, 9, 0, 1, 2)

        # Лог
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text, 10, 0, 1, 2)

        self.data_tab.setLayout(layout)

    def setup_model_tab(self):
        layout = QGridLayout()

        # Кнопки для обучения и прогнозирования
        self.btn_train = QPushButton("Обучить модели")
        self.btn_train.clicked.connect(self.run_train_models)
        layout.addWidget(self.btn_train, 0, 0, 1, 2)

        self.btn_predict = QPushButton("Прогнозировать и дообучить")
        self.btn_predict.clicked.connect(self.run_predict_and_learn)
        layout.addWidget(self.btn_predict, 1, 0, 1, 2)

        # Лог
        self.model_log_text = QTextEdit()
        self.model_log_text.setReadOnly(True)
        layout.addWidget(self.model_log_text, 2, 0, 1, 2)

        self.model_tab.setLayout(layout)

    def setup_plot_tab(self):
        layout = QVBoxLayout()

        # График через Plotly
        self.plot_view = QWebEngineView()
        layout.addWidget(self.plot_view)

        self.plot_tab.setLayout(layout)

    def log_message(self, message):
        self.log_text.append(message)
        self.model_log_text.append(message)
        logger.info(message)

    def display_data(self, df):
        self.data_table.setRowCount(df.shape[0])
        self.data_table.setColumnCount(df.shape[1])
        self.data_table.setHorizontalHeaderLabels(df.columns)
        for i in range(df.shape[0]):
            for j in range(df.shape[1]):
                self.data_table.setItem(i, j, QTableWidgetItem(str(df.iloc[i, j])))

    def display_plot(self, plot_path):
        if os.path.exists(plot_path):
            self.plot_view.setUrl(f"file://{os.path.abspath(plot_path)}")
        else:
            self.log_message(f"Файл графика {plot_path} не найден")
            QMessageBox.warning(self, "Ошибка", f"Файл графика {plot_path} не найден")

    def run_get_moex_stocks(self):
        self.thread = WorkerThread(task='get_moex_stocks')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_find_indices(self):
        self.thread = WorkerThread(task='find_indices')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_find_currency_pairs(self):
        self.thread = WorkerThread(task='find_currency_pairs')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_find_oil_futures(self):
        self.thread = WorkerThread(task='find_oil_futures')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_get_key_rate_history(self):
        self.thread = WorkerThread(task='get_key_rate_history')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_get_historical_data(self):
        try:
            start_date = datetime.strptime(self.start_date_input.text(), "%Y-%m-%d")
            end_date = datetime.strptime(self.end_date_input.text(), "%Y-%m-%d")
            if start_date >= end_date:
                QMessageBox.critical(self, "Ошибка", "Дата начала должна быть раньше даты окончания")
                return
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Неверный формат даты (ожидается ГГГГ-ММ-ДД)")
            return
        self.thread = WorkerThread(task='get_historical_data',
                                 start_date=self.start_date_input.text(),
                                 end_date=self.end_date_input.text())
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_combine_datasets(self):
        self.thread = WorkerThread(task='combine_datasets')
        self.thread.log_signal.connect(self.log_message)
        self.thread.data_signal.connect(self.display_data)
        self.thread.start()

    def run_train_models(self):
        self.thread = WorkerThread(task='train_all_models')
        self.thread.log_signal.connect(self.log_message)
        self.thread.start()

    def run_predict_and_learn(self):
        self.thread = WorkerThread(task='predict_and_learn')
        self.thread.log_signal.connect(self.log_message)
        self.thread.plot_signal.connect(self.display_plot)
        self.thread.start()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
