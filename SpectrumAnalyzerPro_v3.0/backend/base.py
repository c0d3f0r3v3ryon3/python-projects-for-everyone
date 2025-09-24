"""
Базовый класс для всех бэкендов.
Предоставляет единый интерфейс для QThread + QProcess.
"""

import os
import sys
import struct
import time
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal, QProcess
from PyQt5.QtGui import QFont
from typing import Dict, Any, List, Tuple
import logging

class BackendInfo:
    """Метаданные о бэкенде."""
    cmd: str = ""
    args_template: List[str] = []
    hint_range: Tuple[float, float] = (0, 0)
    hint_step: str = ""
    default_gain: int = 0
    output_type: str = "text"  # "text" or "binary"
    lna_gain_default: int = 0
    default_sample_rate: int = 2000000
    default_ppm: int = 0

class BackendPowerThread(QThread):
    """
    Абстрактный поток для выполнения команды SDR-утилиты.
    Отправляет данные через сигнал data_updated.
    """

    data_updated = pyqtSignal(dict)  # {'x': freqs, 'y': powers, 'timestamp': str}
    log_message = pyqtSignal(str)
    scan_finished = pyqtSignal()

    def __init__(self, info: BackendInfo, start_freq: float, end_freq: float, step: float,
                 gain: float, interval: float, device: str = "", sample_rate: float = 2e6,
                 ppm: int = 0, lna_gain: int = 0, bandwidth: float = 0, lnb_lo: float = 0):
        super().__init__()
        self.info = info
        self.start_freq = start_freq
        self.end_freq = end_freq
        self.step = step
        self.gain = gain
        self.lna_gain = lna_gain
        self.device = device
        self.sample_rate = sample_rate
        self.ppm = ppm
        self.bandwidth = bandwidth
        self.lnb_lo = lnb_lo
        self.interval = interval
        self.running = False
        self.process = None
        self.params = {}

    def setup(self):
        """Подготовить параметры команды."""
        raise NotImplementedError

    def process_start(self):
        """Запустить процесс."""
        raise NotImplementedError

    def parse_output(self, line_or_bytes):
        """Обработать вывод. Может быть строкой или байтами."""
        raise NotImplementedError

    def process_stop(self):
        """Остановить процесс."""
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            if not self.process.waitForFinished(2000):
                self.process.kill()
                self.process.waitForFinished(1000)

    def run(self):
        """Основной цикл потока."""
        try:
            self.setup()
            self.process_start()
            self.running = True
            self.log_message.emit(f"[INFO] Запущен бэкенд: {self.info.cmd}")

            while self.running and self.process.state() == QProcess.Running:
                if self.info.output_type == "text":
                    if self.process.canReadLine():
                        line = self.process.readLine().data().decode('utf-8', errors='ignore').strip()
                        if line:
                            self.parse_output(line)
                else:  # binary
                    if self.process.bytesAvailable():
                        chunk = self.process.readAll().data()
                        if len(chunk) > 0:
                            self.parse_output(chunk)
                time.sleep(0.01)

            if self.running:
                self.scan_finished.emit()
            else:
                self.log_message.emit("[INFO] Сканирование остановлено пользователем.")

        except Exception as e:
            error_msg = f"[CRITICAL] Ошибка в {self.info.cmd}: {str(e)}"
            self.log_message.emit(error_msg)
            logging.exception(error_msg)
        finally:
            self.process_stop()
