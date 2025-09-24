import os
import numpy as np
from PyQt5.QtWidgets import QFileDialog
import pyqtgraph.exporters

def export_spectrum(plot_widget, parent):
    """Экспортирует график в PNG или PDF."""
    exporter = pyqtgraph.exporters.ImageExporter(plot_widget.plot_widget.plotItem)
    exporter.parameters()['width'] = 1920
    filename, _ = QFileDialog.getSaveFileName(parent, "Экспорт графика", "", "PNG (*.png);;PDF (*.pdf)")
    if filename:
        if filename.endswith('.pdf'):
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(parent, "Предупреждение", "PDF экспорт требует Cairo — используйте PNG.")
        else:
            exporter.export(filename)

def export_csv(data_storage, parent):
    if data_storage.x is None or data_storage.y is None:
        return
    data = np.column_stack((data_storage.x, data_storage.y))
    filename, _ = QFileDialog.getSaveFileName(parent, "Сохранить спектр", "", "CSV (*.csv)")
    if filename:
        np.savetxt(filename, data, delimiter=',', header='freq_MHz,power_dB', comments='')
