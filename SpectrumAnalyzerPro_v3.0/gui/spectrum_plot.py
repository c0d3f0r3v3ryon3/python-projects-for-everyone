import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import pyqtSignal
from data.data_storage import DataStorage

class SpectrumPlotWidget(QWidget):
    """График мощности с несколькими кривыми."""
    mouse_moved = pyqtSignal(float, float)  # freq_MHz, power_dB

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget(title="Спектр мощности")
        self.plot_widget.setLabel('left', 'Мощность (дБ)')
        self.plot_widget.setLabel('bottom', 'Частота (МГц)')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.enableAutoRange()
        self.plot_widget.setMouseEnabled(x=True, y=True)

        # Кривые
        self.curve_main = self.plot_widget.plot(pen=pg.mkPen('cyan', width=2), name='Спектр')
        self.curve_avg = self.plot_widget.plot(pen=pg.mkPen('blue', width=1), name='Среднее')
        self.curve_peak_max = self.plot_widget.plot(pen=pg.mkPen('red', width=1), name='Пик-холд макс')
        self.curve_peak_min = self.plot_widget.plot(pen=pg.mkPen('green', width=1), name='Пик-холд мин')
        self.curve_baseline = self.plot_widget.plot(pen=pg.mkPen('magenta', width=1), name='Базовая линия')

        # Кросс-хэр
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen='gray')
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen='gray')
        self.plot_widget.addItem(self.vLine, ignoreBounds=True)
        self.plot_widget.addItem(self.hLine, ignoreBounds=True)

        self.proxy = pg.SignalProxy(self.plot_widget.scene().sigMouseMoved,
                                    rateLimit=60, slot=self.mouse_moved_event)

        self.layout.addWidget(self.plot_widget)
        self.setLayout(self.layout)

    def connect_to_data(self, data_storage: DataStorage):
        data_storage.data_updated.connect(self.update_main)
        data_storage.average_updated.connect(self.update_average)
        data_storage.peak_hold_max_updated.connect(self.update_peak_max)
        data_storage.peak_hold_min_updated.connect(self.update_peak_min)
        data_storage.baseline_updated.connect(self.update_baseline)

    def update_main(self, data):
        self.curve_main.setData(data['x'], data['y'])

    def update_average(self, data):
        self.curve_avg.setData(data['x'], data['y'])

    def update_peak_max(self, data):
        self.curve_peak_max.setData(data['x'], data['y'])

    def update_peak_min(self, data):
        self.curve_peak_min.setData(data['x'], data['y'])

    def update_baseline(self, data):
        if data['baseline'] is not None:
            self.curve_baseline.setData(data['baseline_x'], data['baseline'])
        else:
            self.curve_baseline.clear()

    def mouse_moved_event(self, evt):
        pos = evt[0]
        if self.plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self.plot_widget.plotItem.vb.mapSceneToView(pos)
            freq_mhz = mouse_point.x()
            power_db = mouse_point.y()
            self.mouse_moved.emit(freq_mhz, power_db)
            self.vLine.setPos(mouse_point.x())
            self.hLine.setPos(mouse_point.y())
