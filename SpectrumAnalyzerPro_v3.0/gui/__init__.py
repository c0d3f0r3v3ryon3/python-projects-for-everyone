"""
Инициализация модуля графического интерфейса.
Позволяет импортировать классы GUI из gui/ через 'from gui import *'
"""

# Импорт основных виджетов
from .main_window import MainWindow
from .spectrum_plot import SpectrumPlotWidget
from .waterfall_plot import WaterfallPlotWidget
from .peaks_table import PeaksTableWidget
from .settings_dialog import SettingsDialog
from .colors_dialog import ColorsDialog
from .smoothing_dialog import SmoothingDialog
from .persistence_dialog import PersistenceDialog
from .baseline_dialog import BaselineDialog
from .iq_record_dialog import IQRecordDialog

__all__ = [
    'MainWindow',
    'SpectrumPlotWidget',
    'WaterfallPlotWidget',
    'PeaksTableWidget',
    'SettingsDialog',
    'ColorsDialog',
    'SmoothingDialog',
    'PersistenceDialog',
    'BaselineDialog',
    'IQRecordDialog'
]
