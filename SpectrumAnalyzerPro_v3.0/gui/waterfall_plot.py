import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from data.data_storage import DataStorage

class WaterfallPlotWidget(QWidget):
    """Водопад со шкалой уровней (HistogramLUT)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget(title="Waterfall (спектрограмма)")
        self.plot_widget.setLabel('left', 'Время (последние N сканов)')
        self.plot_widget.setLabel('bottom', 'Частота (МГц)')
        self.plot_widget.setYRange(-50, 0)
        self.plot_widget.setXLink(None)  # Будет связано с основным графиком

        # Изображение водопада
        self.waterfall_img = pg.ImageItem()
        self.waterfall_img.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        self.plot_widget.addItem(self.waterfall_img)

        # HistogramLUT
        self.hist_layout = pg.GraphicsLayoutWidget()
        self.histogram = pg.HistogramLUTItem()
        self.histogram.setImageItem(self.waterfall_img)
        self.hist_layout.addItem(self.histogram)

        # Размещение
        self.layout.addWidget(self.plot_widget)
        self.layout.addWidget(self.hist_layout)
        self.setLayout(self.layout)

    def connect_to_data(self, data_storage: DataStorage):
        data_storage.history_updated.connect(self.update_waterfall)

    def update_waterfall(self, data_storage: DataStorage):
        if data_storage.history is None:
            return
        buffer = data_storage.history.get_buffer()
        if len(buffer) == 0:
            return
        # Отображаем последние 50 сканов
        n = min(50, len(buffer))
        img = buffer[-n:].T  # Транспонируем для правильного отображения
        self.waterfall_img.setImage(img, autoLevels=False, autoRange=False)
        self.waterfall_img.setRect(
            pg.QtCore.QRectF(
                data_storage.x[0],
                -n,
                data_storage.x[-1] - data_storage.x[0],
                n
            )
        )
