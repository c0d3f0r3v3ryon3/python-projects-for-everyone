# ananacc_gui.py
import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QTabWidget, QFileDialog, QMessageBox, QProgressBar,
    QGroupBox, QFormLayout, QLineEdit, QDateEdit, QCheckBox, QComboBox,
    QListWidget, QListWidgetItem, QSplitter, QFrame
)
from PyQt5.QtCore import QThread, pyqtSignal, QDate, Qt
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.dates as mdates

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
FINAL_MODEL_FILE = os.path.join(MODELS_DIR, 'final_model_pa.joblib')
FINAL_SCALER_FILE = os.path.join(SCALERS_DIR, 'final_model_pa_scaler.joblib')
INCREMENTAL_LOG_FILE = os.path.join(LOGS_DIR, 'incremental_learning_log_final.csv')
INCREMENTAL_PLOT_FILE = os.path.join(PLOTS_DIR, 'incremental_learning_accuracy_plot.png')

class ScriptRunner(QThread):
    """Поток для запуска Python-скриптов."""
    output_signal = pyqtSignal(str) # Сигнал для передачи вывода скрипта
    finished_signal = pyqtSignal(int) # Сигнал завершения скрипта с кодом возврата

    def __init__(self, script_path, parent=None):
        super().__init__(parent)
        self.script_path = script_path

    def run(self):
        """Запуск скрипта."""
        try:
            self.output_signal.emit(f"Запуск скрипта: {self.script_path}\n")
            # Используем subprocess.Popen для перехвата stdout/stderr построчно
            process = subprocess.Popen(
                [sys.executable, self.script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, # Перенаправляем stderr в stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Читаем вывод построчно
            for line in iter(process.stdout.readline, ''):
                self.output_signal.emit(line.rstrip('\n')) # Убираем \n, так как QTextEdit сам добавит

            process.stdout.close()
            return_code = process.wait() # Ждем завершения процесса
            self.finished_signal.emit(return_code)
        except Exception as e:
            self.output_signal.emit(f"Ошибка при запуске скрипта {self.script_path}: {e}\n")
            self.finished_signal.emit(-1) # Код ошибки

class SettingsTab(QWidget):
    """Вкладка настроек."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа настроек путей
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

        # Группа настроек дат
        dates_group = QGroupBox("Даты")
        dates_layout = QFormLayout()

        self.start_date_edit = QDateEdit(calendarPopup=True)
        self.start_date_edit.setDate(QDate(2023, 1, 1)) # Устанавливаем начальную дату
        self.end_date_edit = QDateEdit(calendarPopup=True)
        self.end_date_edit.setDate(QDate.currentDate()) # Устанавливаем текущую дату

        dates_layout.addRow("Начальная дата:", self.start_date_edit)
        dates_layout.addRow("Конечная дата:", self.end_date_edit)

        dates_group.setLayout(dates_layout)
        layout.addWidget(dates_group)

        # Группа настроек моделей
        models_group = QGroupBox("Настройки моделей")
        models_layout = QFormLayout()

        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["PassiveAggressiveClassifier", "SGDClassifier", "Perceptron"])
        self.model_type_combo.setCurrentText("PassiveAggressiveClassifier")

        models_layout.addRow("Тип модели:", self.model_type_combo)

        models_group.setLayout(models_layout)
        layout.addWidget(models_group)

        # Кнопка сохранения настроек
        self.save_settings_btn = QPushButton("Сохранить настройки")
        self.save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(self.save_settings_btn)

        self.setLayout(layout)

    def save_settings(self):
        """Сохраняет настройки (в данном случае просто выводит сообщение)."""
        # В реальном приложении здесь можно сохранять настройки в файл или базу данных
        QMessageBox.information(self, "Настройки", "Настройки сохранены!")

class DataCollectionTab(QWidget):
    """Вкладка сбора данных."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа кнопок для сбора данных
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

        # Поле вывода логов
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

        # Блокируем кнопки на время выполнения скрипта
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
        # Обновляем статус в главном окне
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000) # Показываем на 5 секунд

class DataCombiningTab(QWidget):
    """Вкладка объединения данных."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа кнопок для объединения данных
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

        # Поле вывода логов
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

        # Блокируем кнопки на время выполнения скрипта
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
        # Обновляем статус в главном окне
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000) # Показываем на 5 секунд

class ModelTrainingTab(QWidget):
    """Вкладка обучения моделей."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа кнопок для обучения моделей
        training_group = QGroupBox("Обучение моделей")
        training_layout = QVBoxLayout()

        self.train_all_models_btn = QPushButton("1. Обучить все модели (train_all_models.py)")
        self.train_all_models_btn.clicked.connect(lambda: self.run_script('train_all_models.py'))
        training_layout.addWidget(self.train_all_models_btn)

        self.train_final_model_btn = QPushButton("2. Обучить финальную модель (train_final_model.py)")
        self.train_final_model_btn.clicked.connect(lambda: self.run_script('train_final_model.py'))
        training_layout.addWidget(self.train_final_model_btn)

        training_group.setLayout(training_layout)
        layout.addWidget(training_group)

        # Поле вывода логов
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

        # Блокируем кнопки на время выполнения скрипта
        self.disable_buttons()

    def disable_buttons(self):
        """Блокирует кнопки."""
        for btn in [self.train_all_models_btn, self.train_final_model_btn]:
            btn.setEnabled(False)

    def enable_buttons(self):
        """Разблокирует кнопки."""
        for btn in [self.train_all_models_btn, self.train_final_model_btn]:
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        """Обработчик завершения скрипта."""
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        # Обновляем статус в главном окне
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000) # Показываем на 5 секунд

class PredictionTab(QWidget):
    """Вкладка прогнозирования."""
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа кнопок для прогнозирования
        prediction_group = QGroupBox("Прогнозирование и инкрементальное обучение")
        prediction_layout = QVBoxLayout()

        self.predict_and_learn_btn = QPushButton("1. Запустить прогнозирование и инкрементальное обучение (predict_and_learn.py)")
        self.predict_and_learn_btn.clicked.connect(lambda: self.run_script('predict_and_learn.py'))
        prediction_layout.addWidget(self.predict_and_learn_btn)

        prediction_group.setLayout(prediction_layout)
        layout.addWidget(prediction_group)

        # Поле вывода логов
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

        # Блокируем кнопки на время выполнения скрипта
        self.disable_buttons()

    def disable_buttons(self):
        """Блокирует кнопки."""
        for btn in [self.predict_and_learn_btn]:
            btn.setEnabled(False)

    def enable_buttons(self):
        """Разблокирует кнопки."""
        for btn in [self.predict_and_learn_btn]:
            btn.setEnabled(True)

    def on_script_finished(self, return_code):
        """Обработчик завершения скрипта."""
        self.enable_buttons()
        if return_code == 0:
            self.log_output.append("Скрипт успешно завершен.\n")
        else:
            self.log_output.append(f"Скрипт завершен с ошибкой (код {return_code}).\n")
        # Обновляем статус в главном окне
        self.main_window.statusBar().showMessage("Скрипт завершен.", 5000) # Показываем на 5 секунд

class ResultsTab(QWidget):
    """Вкладка результатов."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Группа для отображения графика
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

        # Группа для отображения прогнозов
        predictions_group = QGroupBox("Последние прогнозы из incremental_learning_log_final.csv")
        predictions_layout = QVBoxLayout()

        self.predictions_table = QTextEdit()
        self.predictions_table.setReadOnly(True)
        predictions_layout.addWidget(self.predictions_table)

        self.load_predictions_btn = QPushButton("Загрузить последние прогнозы")
        self.load_predictions_btn.clicked.connect(self.load_predictions)
        predictions_layout.addWidget(self.load_predictions_btn)

        predictions_group.setLayout(predictions_layout)
        layout.addWidget(predictions_group)

        self.setLayout(layout)

    def plot_accuracy(self):
        """Строит график точности из лога инкрементального обучения."""
        if not os.path.exists(INCREMENTAL_LOG_FILE):
            self.predictions_table.append(f"Файл лога {INCREMENTAL_LOG_FILE} не найден.\n")
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
            self.predictions_table.append("График построен.\n")
        except Exception as e:
            self.predictions_table.append(f"Ошибка при построении графика: {e}\n")

    def load_predictions(self):
        """Загружает последние прогнозы из лога."""
        if not os.path.exists(INCREMENTAL_LOG_FILE):
            self.predictions_table.append(f"Файл лога {INCREMENTAL_LOG_FILE} не найден.\n")
            return

        try:
            df = pd.read_csv(INCREMENTAL_LOG_FILE, encoding='utf-8-sig')
            # Показываем последние 10 строк
            last_predictions = df.tail(10)
            self.predictions_table.setText(last_predictions.to_string(index=False))
        except Exception as e:
            self.predictions_table.append(f"Ошибка при загрузке прогнозов: {e}\n")

class MainWindow(QMainWindow):
    """Главное окно приложения."""
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('ANANACC - Прогнозирование цен акций')
        self.setGeometry(100, 100, 1200, 800)

        # Создаем вкладки
        self.tabs = QTabWidget()
        self.settings_tab = SettingsTab()
        self.data_collection_tab = DataCollectionTab(self)
        self.data_combining_tab = DataCombiningTab(self)
        self.model_training_tab = ModelTrainingTab(self)
        self.prediction_tab = PredictionTab(self)
        self.results_tab = ResultsTab()

        # Добавляем вкладки в TabWidget
        self.tabs.addTab(self.settings_tab, "Настройки")
        self.tabs.addTab(self.data_collection_tab, "Сбор данных")
        self.tabs.addTab(self.data_combining_tab, "Объединение данных")
        self.tabs.addTab(self.model_training_tab, "Обучение моделей")
        self.tabs.addTab(self.prediction_tab, "Прогнозирование")
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
        QMessageBox.about(self, "О программе", "ANANACC - Автоматическая система прогнозирования цен акций с инкрементальным обучением.\nВерсия 1.0")

def main():
    """Основная функция."""
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
