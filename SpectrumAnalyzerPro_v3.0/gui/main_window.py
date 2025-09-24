import sys
import os
import json
import time
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from backend.soapy_power import SoapyPowerThread, SoapyPowerInfo
from data.data_storage import DataStorage
from gui.spectrum_plot import SpectrumPlotWidget
from gui.waterfall_plot import WaterfallPlotWidget
from gui.peaks_table import PeaksTableWidget
from gui.settings_dialog import SettingsDialog
from gui.colors_dialog import ColorsDialog
from gui.smoothing_dialog import SmoothingDialog
from gui.persistence_dialog import PersistenceDialog
from gui.baseline_dialog import BaselineDialog
from gui.iq_record_dialog import IQRecordDialog
from utils.signal_classifier import SignalClassifier
from utils.export import export_spectrum, export_csv
from config import DEVICE_BACKENDS, SOAPY_DEVICES
from utils.logger import get_logger
from scipy.signal import find_peaks
from backend.rtl_power import RtlPowerInfo, RtlPowerThread
from backend.hackrf_sweep import HackRFSweepInfo, HackRFSweepThread
from backend.airspy_rx import AirspyRxInfo, AirspyRxThread

logger = get_logger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📡 SpectrumAnalyzer Pro v3.0 — Универсальный SDR-анализатор")
        self.setGeometry(100, 100, 1400, 900)
        self.settings = QSettings("SpectrumLabs", "SpectrumAnalyzerPro")
        self.is_scanning = False
        self.worker_thread = None
        self.data_storage = DataStorage(max_history_size=100)
        self.classifier = SignalClassifier()

        self.init_ui()
        self.load_settings()
        self.connect_signals()

    def init_ui(self):
        self.create_menu()
        self.create_toolbar()
        self.create_status_bar()
        self.create_docks()
        self.create_tabs()

    def create_menu(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Файл")
        save_action = QAction("Сохранить скан", self)
        save_action.triggered.connect(lambda: export_csv(self.data_storage, self))
        file_menu.addAction(save_action)
        export_action = QAction("Экспорт графика (PNG)", self)
        export_action.triggered.connect(lambda: export_spectrum(self.spectrum_plot, self))
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        analysis_menu = menubar.addMenu("Анализ")
        record_iq_action = QAction("Записать IQ сигнал...", self)
        record_iq_action.triggered.connect(self.record_iq_signal)
        analysis_menu.addAction(record_iq_action)

        view_menu = menubar.addMenu("Вид")
        self.toggle_waterfall_action = QAction("Режим Waterfall", self, checkable=True)
        self.toggle_waterfall_action.setChecked(True)
        self.toggle_waterfall_action.triggered.connect(self.toggle_waterfall)
        view_menu.addAction(self.toggle_waterfall_action)

        help_menu = menubar.addMenu("Справка")
        doc_action = QAction("Документация", self)
        doc_action.triggered.connect(self.show_documentation)
        help_menu.addAction(doc_action)

    def create_toolbar(self):
        toolbar = QToolBar("Панель управления")
        self.addToolBar(toolbar)
        self.start_action = QAction("▶️ Начать", self)
        self.start_action.triggered.connect(self.start_scan)
        toolbar.addAction(self.start_action)
        self.stop_action = QAction("⏹️ Остановить", self)
        self.stop_action.triggered.connect(self.stop_scan)
        self.stop_action.setEnabled(False)
        toolbar.addAction(self.stop_action)
        toolbar.addSeparator()
        self.settings_button = QAction("⚙️ Настройки", self)
        self.settings_button.triggered.connect(self.open_settings)
        toolbar.addAction(self.settings_button)
        toolbar.setObjectName("main_toolbar")

    def create_status_bar(self):
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)
        self.statusBar.showMessage("Готов к сканированию")

    def create_docks(self):
        self.log_dock = QDockWidget("Журнал событий", self)
        self.log_dock.setObjectName("log_dock")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        self.log_dock.setWidget(self.log_text)
        self.addDockWidget(Qt.RightDockWidgetArea, self.log_dock)

        self.params_dock = QDockWidget("Параметры сканирования", self)
        self.params_dock.setObjectName("params_dock")
        self.params_widget = QWidget()
        self.params_layout = QVBoxLayout()

        # Выбор устройства
        device_group = QGroupBox("Устройство")
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Тип:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(list(DEVICE_BACKENDS.keys()))
        self.device_combo.setCurrentText("soapy_power")
        device_layout.addWidget(self.device_combo)
        device_group.setLayout(device_layout)
        self.params_layout.addWidget(device_group)

        # Параметры SoapySDR
        soapy_group = QGroupBox("SoapySDR-устройства")
        soapy_layout = QHBoxLayout()
        soapy_layout.addWidget(QLabel("Устройство:"))
        self.soapy_device_combo = QComboBox()
        self.soapy_device_combo.addItems(SOAPY_DEVICES)
        self.soapy_device_combo.setCurrentText("RTL-SDR")
        soapy_layout.addWidget(self.soapy_device_combo)
        soapy_group.setLayout(soapy_layout)
        self.params_layout.addWidget(soapy_group)

        # Частоты
        freq_group = QGroupBox("Диапазон частот")
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Начало (МГц):"))
        self.start_freq_entry = QDoubleSpinBox()
        self.start_freq_entry.setRange(1, 7250)
        self.start_freq_entry.setValue(100)
        freq_layout.addWidget(self.start_freq_entry)
        freq_layout.addWidget(QLabel("Конец (МГц):"))
        self.end_freq_entry = QDoubleSpinBox()
        self.end_freq_entry.setRange(1, 7250)
        self.end_freq_entry.setValue(200)
        freq_layout.addWidget(self.end_freq_entry)
        freq_group.setLayout(freq_layout)
        self.params_layout.addWidget(freq_group)

        # Шаг и усиление
        step_gain_group = QGroupBox("Шаг и усиление")
        step_gain_layout = QHBoxLayout()
        step_gain_layout.addWidget(QLabel("Шаг (кГц):"))
        self.step_entry = QSpinBox()
        self.step_entry.setRange(1, 5000)
        self.step_entry.setValue(100)
        step_gain_layout.addWidget(self.step_entry)
        step_gain_layout.addWidget(QLabel("Усиление (дБ):"))
        self.gain_entry = QSpinBox()
        self.gain_entry.setRange(-1, 100)
        self.gain_entry.setValue(20)
        step_gain_layout.addWidget(self.gain_entry)
        step_gain_group.setLayout(step_gain_layout)
        self.params_layout.addWidget(step_gain_group)

        # Интервал
        interval_group = QGroupBox("Интервал")
        interval_layout = QHBoxLayout()
        interval_layout.addWidget(QLabel("Интервал (с):"))
        self.interval_entry = QDoubleSpinBox()
        self.interval_entry.setRange(0.1, 10)
        self.interval_entry.setValue(1.0)
        interval_layout.addWidget(self.interval_entry)
        interval_group.setLayout(interval_layout)
        self.params_layout.addWidget(interval_group)

        # Калибровка
        cal_group = QGroupBox("Калибровка")
        cal_layout = QHBoxLayout()
        cal_layout.addWidget(QLabel("Смещение (МГц):"))
        self.calibration_entry = QDoubleSpinBox()
        self.calibration_entry.setRange(-10, 10)
        self.calibration_entry.setValue(0.0)
        cal_layout.addWidget(self.calibration_entry)
        cal_group.setLayout(cal_layout)
        self.params_layout.addWidget(cal_group)

        self.params_widget.setLayout(self.params_layout)
        self.params_dock.setWidget(self.params_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.params_dock)

    def create_tabs(self):
        self.tabs = QTabWidget()

        # Спектр
        self.spectrum_tab = QWidget()
        self.spectrum_plot = SpectrumPlotWidget()
        self.spectrum_plot.connect_to_data(self.data_storage)
        layout = QVBoxLayout()
        layout.addWidget(self.spectrum_plot)
        self.spectrum_tab.setLayout(layout)
        self.tabs.addTab(self.spectrum_tab, "Спектр")

        # Водопад
        self.waterfall_tab = QWidget()
        self.waterfall_plot = WaterfallPlotWidget()
        self.waterfall_plot.connect_to_data(self.data_storage)
        layout = QVBoxLayout()
        layout.addWidget(self.waterfall_plot)
        self.waterfall_tab.setLayout(layout)
        self.tabs.addTab(self.waterfall_tab, "Waterfall")

        # Обнаруженные сигналы
        self.peaks_tab = QWidget()
        self.peaks_table = PeaksTableWidget(self.classifier)
        layout = QVBoxLayout()
        layout.addWidget(self.peaks_table)
        self.peaks_tab.setLayout(layout)
        self.tabs.addTab(self.peaks_tab, "Обнаруженные сигналы")

        self.setCentralWidget(self.tabs)

    def connect_signals(self):
        self.spectrum_plot.mouse_moved.connect(self.on_mouse_moved)
        self.data_storage.data_updated.connect(self.update_peaks)
        self.data_storage.history_updated.connect(self.update_waterfall)

    def on_mouse_moved(self, freq_mhz, power_db):
        self.statusBar.showMessage(f"Частота: {freq_mhz:.3f} МГц, Мощность: {power_db:.1f} дБ")

    def update_peaks(self, data):
        # Поиск пиков
        peaks, props = find_peaks(data['y'], height=-60, prominence=5, distance=10)
        peak_list = []
        for i, peak in enumerate(peaks):
            if peak >= len(data['y']) or peak < 0:
                continue
            peak_val = data['y'][peak]
            half_height = peak_val - (peak_val + 60) / 2
            left = peak
            while left > 0 and data['y'][left] > half_height:
                left -= 1
            right = peak
            while right < len(data['y'])-1 and data['y'][right] > half_height:
                right += 1
            width_mhz = (data['x'][right] - data['x'][left]) if right > left else 0
            if width_mhz < 0.01:
                continue
            modulation = self.classifier.detect_modulation_around_peak(data['y'], peak)
            signal_type = self.classifier.classify_signal(modulation, width_mhz)
            peak_list.append({
                "Частота (МГц)": data['x'][peak],
                "Амплитуда (дБ)": peak_val,
                "Левая гр.": data['x'][left],
                "Правая гр.": data['x'][right],
                "Ширина (МГц)": width_mhz,
                "Модуляция": modulation,
                "Тип": signal_type
            })
        self.peaks_table.update_table(peak_list)

    def update_waterfall(self, data_storage):
        pass  # Водопад сам обновляется через сигнал

def start_scan(self):
    if self.is_scanning:
        return
    self.is_scanning = True
    self.start_action.setEnabled(False)
    self.stop_action.setEnabled(True)
    self.progress_bar.setVisible(True)
    self.statusBar.showMessage("Сканирование...")

    start = self.start_freq_entry.value()
    end = self.end_freq_entry.value()
    step = self.step_entry.value()
    gain = self.gain_entry.value()
    interval = self.interval_entry.value()
    device = self.device_combo.currentText()
    soapy_device = self.soapy_device_combo.currentText()

    # Импорты (добавьте в начало main_window.py)
    from backend.rtl_power import RtlPowerInfo, RtlPowerThread
    from backend.hackrf_sweep import HackRFSweepInfo, HackRFSweepThread
    from backend.airspy_rx import AirspyRxInfo, AirspyRxThread

    if device == "soapy_power":
        self.worker_thread = SoapyPowerThread(
            start_freq=start,
            end_freq=end,
            step=step,
            gain=gain,
            interval=interval,
            device=soapy_device,
            sample_rate=2560000,
            ppm=0,
            lnb_lo=self.calibration_entry.value()
        )
    elif device == "rtl_power":
        self.worker_thread = RtlPowerThread(
            start_freq=start,
            end_freq=end,
            step=step,
            gain=gain,
            interval=interval,
            device="",
            sample_rate=2e6,
            ppm=0,
            lnb_lo=self.calibration_entry.value()
        )
    elif device == "hackrf_sweep":
        lna_gain = 16  # По умолчанию из config.py
        self.worker_thread = HackRFSweepThread(
            start_freq=start,
            end_freq=end,
            step=step,
            gain=gain,
            interval=interval,
            device="",
            sample_rate=20e6,
            ppm=0,
            lnb_lo=self.calibration_entry.value(),
            lna_gain=lna_gain
        )
    elif device == "airspy_rx":
        self.worker_thread = AirspyRxThread(
            start_freq=start,
            end_freq=end,
            step=step,
            gain=gain,
            interval=interval,
            device="",
            sample_rate=2.5e6,
            ppm=0,
            lnb_lo=self.calibration_entry.value()
        )
    else:
        QMessageBox.critical(self, "Ошибка", f"Неизвестный бэкенд: {device}")
        self.on_scan_finished()
        return

    # Подключаем сигналы
    self.worker_thread.data_updated.connect(self.data_storage.update)
    self.worker_thread.log_message.connect(self.log_message)
    self.worker_thread.scan_finished.connect(self.on_scan_finished)

    self.worker_thread.start()
    
    def stop_scan(self):
        if self.worker_thread:
            self.worker_thread.running = False
            self.worker_thread.wait(2000)
        self.on_scan_finished()

    def on_scan_finished(self):
        self.is_scanning = False
        self.start_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage("Сканирование завершено")

    def log_message(self, msg):
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.log_text.append(f"<b>[{timestamp}]</b> {msg}")
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

    def toggle_waterfall(self, checked):
        self.tabs.setCurrentIndex(1 if checked else 0)

    def open_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def record_iq_signal(self):
        dialog = IQRecordDialog(self)
        dialog.exec_()

    def show_documentation(self):
        QMessageBox.information(self, "📚 Документация", """
SpectrumAnalyzer Pro v3.0 — Универсальный SDR-анализатор

Поддерживает: RTL-SDR, HackRF, Airspy, LimeSDR, PlutoSDR, SDRplay и другие через SoapySDR.

Функции:
- Спектр в реальном времени
- Водопад с HistogramLUT
- Автоматическая классификация сигналов (AM, FM, Digital, CW)
- Запись IQ-данных
- Экспорт в PNG, CSV
- Калибровка частоты

Установка:
pip install -r requirements.txt
sudo apt install soapysdr soapysdr-module-rtlsdr

Запуск:
python main.py
""")

    def load_settings(self):
        geom = self.settings.value("window_geometry")
        if geom:
            self.restoreGeometry(geom)
        state = self.settings.value("window_state")
        if state:
            self.restoreState(state)

    def closeEvent(self, event):
        self.stop_scan()
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("window_state", self.saveState())
        event.accept()
