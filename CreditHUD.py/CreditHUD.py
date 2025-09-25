import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenu, QAction, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QDateEdit, QPushButton, QHBoxLayout, QProgressBar, QMessageBox,
    QSystemTrayIcon, QStyle, QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, QDate
from PyQt5.QtGui import QFont, QIcon

# ==================================================
# 1. Инициализация базы данных
# ==================================================
def init_db():
    conn = sqlite3.connect("simple_credits.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            total_amount REAL NOT NULL,
            remaining_amount REAL NOT NULL,
            next_payment_date TEXT,
            next_payment_amount REAL
        )
    ''')
    conn.commit()
    conn.close()

# ==================================================
# 2. Форматирование валюты
# ==================================================
def format_currency(amount):
    return f"{amount:,.2f} ₽".replace(",", " ")

# ==================================================
# 3. Диалог редактирования кредита
# ==================================================
class EditCreditDialog(QDialog):
    def __init__(self, credit_data=None, parent=None):
        super().__init__(parent)
        self.credit_data = credit_data
        self.setWindowTitle("Редактировать кредит" if credit_data else "Добавить кредит")
        self.setGeometry(300, 300, 350, 250)

        layout = QFormLayout()
        layout.setSpacing(6)

        self.name_edit = QLineEdit()
        self.total_amount_spin = QDoubleSpinBox()
        self.total_amount_spin.setRange(0.01, 10000000.00)
        self.total_amount_spin.setDecimals(2)

        self.remaining_amount_spin = QDoubleSpinBox()
        self.remaining_amount_spin.setRange(0.00, 10000000.00)
        self.remaining_amount_spin.setDecimals(2)

        self.next_payment_date_edit = QDateEdit()
        self.next_payment_date_edit.setDate(QDate.currentDate())
        self.next_payment_date_edit.setCalendarPopup(True)

        self.next_payment_amount_spin = QDoubleSpinBox()
        self.next_payment_amount_spin.setRange(0.00, 10000000.00)
        self.next_payment_amount_spin.setDecimals(2)

        font = QFont("Arial", 9)
        self.name_edit.setFont(font)
        self.total_amount_spin.setFont(font)
        self.remaining_amount_spin.setFont(font)
        self.next_payment_date_edit.setFont(font)
        self.next_payment_amount_spin.setFont(font)

        layout.addRow("Название:", self.name_edit)
        layout.addRow("Общая сумма:", self.total_amount_spin)
        layout.addRow("Остаток:", self.remaining_amount_spin)
        layout.addRow("Дата след. платежа:", self.next_payment_date_edit)
        layout.addRow("Сумма след. платежа:", self.next_payment_amount_spin)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("Сохранить")
        cancel_btn = QPushButton("Отмена")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        self.setLayout(layout)

        if credit_data is not None:
            self.fill_data(credit_data)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def fill_data(self, credit_data):
        self.name_edit.setText(credit_data[1])
        self.total_amount_spin.setValue(credit_data[2])
        self.remaining_amount_spin.setValue(credit_data[3])
        if credit_data[4]:
            self.next_payment_date_edit.setDate(QDate.fromString(credit_data[4], "yyyy-MM-dd"))
        self.next_payment_amount_spin.setValue(credit_data[5] or 0.0)

    def get_data(self):
        return (
            self.name_edit.text(),
            self.total_amount_spin.value(),
            self.remaining_amount_spin.value(),
            self.next_payment_date_edit.date().toString("yyyy-MM-dd"),
            self.next_payment_amount_spin.value()
        )

# ==================================================
# 4. Главный виджет HUD
# ==================================================
class SimpleCreditHUD(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            background-color: rgba(40, 44, 52, 230);
            border-radius: 10px;
            color: #e0e0e0;
            padding: 10px;
        """)

        self.dragging = False
        self.offset = QPoint()

        self.layout = QVBoxLayout()
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)

        self.title = QLabel("💰 Мои кредиты")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 12, QFont.Bold))
        self.layout.addWidget(self.title)

        self.total_remaining_label = QLabel("Общая сумма остатков: 0.00 ₽")
        self.total_remaining_label.setAlignment(Qt.AlignCenter)
        self.total_remaining_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.layout.addWidget(self.total_remaining_label)

        self.credits_container = QVBoxLayout()
        self.credits_container.setSpacing(6)
        self.layout.addLayout(self.credits_container)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_main_context_menu)

        self.load_credits()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        elif event.button() == Qt.RightButton:
            clicked_credit = self.get_credit_at_position(event.pos())
            if clicked_credit:
                self.show_credit_context_menu(event.globalPos(), clicked_credit)
            else:
                self.show_main_context_menu(event.pos())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def get_credit_at_position(self, pos):
        for i in range(self.credits_container.count()):
            item = self.credits_container.itemAt(i)
            if item.widget():
                widget = item.widget()
                global_pos = self.mapToGlobal(pos)
                local_widget_pos = widget.mapFromGlobal(global_pos)
                if widget.rect().contains(local_widget_pos):
                    if hasattr(widget, 'credit_id'):
                        return widget.credit_id
        return None

    def show_main_context_menu(self, pos):
        menu = QMenu(self)
        add_action = QAction("➕ Добавить кредит", self)
        add_action.triggered.connect(self.add_credit)
        menu.addAction(add_action)

        refresh_action = QAction("🔄 Обновить", self)
        refresh_action.triggered.connect(self.load_credits)
        menu.addAction(refresh_action)

        menu.exec_(self.mapToGlobal(pos))

    def show_credit_context_menu(self, global_pos, credit_id):
        menu = QMenu(self)
        edit_action = QAction("✏️ Редактировать кредит", self)
        edit_action.triggered.connect(lambda: self.edit_credit_by_id(credit_id))
        menu.addAction(edit_action)

        delete_action = QAction("🗑️ Удалить кредит", self)
        delete_action.triggered.connect(lambda: self.delete_credit(credit_id))
        menu.addAction(delete_action)

        menu.exec_(global_pos)

    def load_credits(self):
        while self.credits_container.count():
            child = self.credits_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        conn = sqlite3.connect("simple_credits.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM credits ORDER BY id")
        credits = cursor.fetchall()
        conn.close()

        total_remaining = sum(credit[3] for credit in credits) if credits else 0
        self.total_remaining_label.setText(f"Общая сумма остатков: {format_currency(total_remaining)}")

        for credit in credits:
            self.add_credit_widget(credit)

    def add_credit_widget(self, credit):
        credit_id, name, total, remaining, next_date, next_amount = credit

        credit_group = QWidget()
        credit_group.credit_id = credit_id
        credit_layout = QVBoxLayout()
        credit_layout.setSpacing(4)
        credit_layout.setContentsMargins(4, 4, 4, 4)
        credit_group.setLayout(credit_layout)

        name_label = QLabel(f"<b>{name}</b>")
        name_label.setFont(QFont("Arial", 10, QFont.Bold))
        credit_layout.addWidget(name_label)

        progress = QProgressBar()
        paid = total - remaining
        percent = int((paid / total) * 100) if total > 0 else 0
        progress.setValue(percent)
        progress.setFormat(f"{percent}% | Осталось: {format_currency(remaining)}")
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                height: 16px;
                font-size: 12px;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        credit_layout.addWidget(progress)

        if next_date and next_amount:
            try:
                payment_date = datetime.strptime(next_date, "%Y-%m-%d")
                days_left = (payment_date - datetime.now()).days
                if days_left < 0:
                    days_text = "ПРОСРОЧЕНО"
                    color = "#ff6b6b"
                elif days_left < 3:
                    days_text = f"{days_left} дн."
                    color = "#ffcc00"
                else:
                    days_text = f"{days_left} дн."
                    color = "#aaffaa"

                next_payment_label = QLabel(f"→ {format_currency(next_amount)} | {next_date} ({days_text})")
                next_payment_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
                credit_layout.addWidget(next_payment_label)
            except Exception:
                next_payment_label = QLabel(f"→ {format_currency(next_amount)} | {next_date}")
                next_payment_label.setStyleSheet("font-size: 12px;")
                credit_layout.addWidget(next_payment_label)

        self.credits_container.addWidget(credit_group)

    def add_credit(self):
        dialog = EditCreditDialog()
        result = dialog.exec_()
        if result == QDialog.Accepted:
            name, total, remaining, next_date, next_amount = dialog.get_data()

            conn = sqlite3.connect("simple_credits.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO credits (name, total_amount, remaining_amount, next_payment_date, next_payment_amount)
                VALUES (?, ?, ?, ?, ?)
            """, (name, total, remaining, next_date, next_amount))
            conn.commit()
            conn.close()

            self.load_credits()

    def edit_credit_by_id(self, credit_id):
        conn = sqlite3.connect("simple_credits.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM credits WHERE id = ?", (credit_id,))
        credit = cursor.fetchone()
        conn.close()

        if not credit:
            QMessageBox.warning(self, "Ошибка", "Кредит не найден.")
            return

        dialog = EditCreditDialog(credit)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            name, total, remaining, next_date, next_amount = dialog.get_data()

            conn = sqlite3.connect("simple_credits.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE credits
                SET name = ?, total_amount = ?, remaining_amount = ?, next_payment_date = ?, next_payment_amount = ?
                WHERE id = ?
            """, (name, total, remaining, next_date, next_amount, credit_id))
            conn.commit()
            conn.close()

            self.load_credits()

    def delete_credit(self, credit_id):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить этот кредит?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect("simple_credits.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credits WHERE id = ?", (credit_id,))
            conn.commit()
            conn.close()
            self.load_credits()

    def closeEvent(self, event):
        event.ignore()

# ==================================================
# 5. Запуск приложения
# ==================================================
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)

    tray_icon = QSystemTrayIcon(QIcon())
    tray_icon.setIcon(app.style().standardIcon(QStyle.SP_TitleBarCloseButton))

    tray_menu = QMenu()
    exit_action = QAction("Закрыть программу", app)
    exit_action.triggered.connect(app.quit)
    tray_menu.addAction(exit_action)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    hud = SimpleCreditHUD(app)
    hud.resize(300, 400)
    hud.move(150, 150)
    hud.show()

    sys.exit(app.exec_())
