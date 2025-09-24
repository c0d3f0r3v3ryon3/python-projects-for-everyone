import sys
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenu, QAction, QDialog, QFormLayout,
    QLineEdit, QDoubleSpinBox, QComboBox, QPushButton, QHBoxLayout, QProgressBar, QMessageBox,
    QSystemTrayIcon, QStyle, QScrollArea
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QIcon

# ==================================================
# 1. Инициализация базы данных + предустановленные категории
# ==================================================
def init_db():
    conn = sqlite3.connect("budget_hud.db")
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 2,
            percentage REAL DEFAULT 0,
            fixed_amount REAL DEFAULT 0,
            is_fixed BOOLEAN DEFAULT 0
        )
    ''')

    # Проверяем, есть ли уже категории — если нет, добавляем шаблон
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ("Кредиты / Долги", 1, 0.0, 10000.0, 1),
            ("Аренда / Ипотека", 1, 0.0, 30000.0, 1),
            ("Коммунальные услуги", 1, 0.0, 5000.0, 1),
            ("Продукты питания", 1, 25.0, 0.0, 0),
            ("Транспорт", 1, 8.0, 0.0, 0),
            ("Подушка безопасности", 1, 10.0, 0.0, 0),
            ("Медицина / Аптека", 1, 5.0, 0.0, 0),
            ("Цели / Накопления", 2, 10.0, 0.0, 0),
            ("Одежда / Обувь", 2, 5.0, 0.0, 0),
            ("Развлечения", 2, 5.0, 0.0, 0),
            ("Образование / Курсы", 2, 3.0, 0.0, 0),
            ("Рестораны / Доставка", 3, 3.0, 0.0, 0),
            ("Подписки", 3, 0.0, 1500.0, 1),
            ("Инвестиции", 3, 5.0, 0.0, 0),
        ]
        cursor.executemany("""
            INSERT INTO categories (name, priority, percentage, fixed_amount, is_fixed)
            VALUES (?, ?, ?, ?, ?)
        """, default_categories)

    conn.commit()
    conn.close()

# ==================================================
# 2. Форматирование валюты
# ==================================================
def format_currency(amount):
    return f"{amount:,.2f} ₽".replace(",", " ")

# ==================================================
# 3. Диалог редактирования категории
# ==================================================
class EditCategoryDialog(QDialog):
    def __init__(self, category_data=None, parent=None):
        super().__init__(parent)
        self.category_data = category_data
        self.setWindowTitle("Редактировать категорию" if category_data else "Добавить категорию")
        self.setGeometry(300, 300, 400, 300)

        layout = QFormLayout()
        layout.setSpacing(8)

        self.name_edit = QLineEdit()
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Высокий (1)", "Средний (2)", "Низкий (3)"])

        self.percentage_spin = QDoubleSpinBox()
        self.percentage_spin.setRange(0.0, 100.0)
        self.percentage_spin.setDecimals(2)
        self.percentage_spin.setSuffix(" %")

        self.fixed_amount_spin = QDoubleSpinBox()
        self.fixed_amount_spin.setRange(0.0, 10000000.0)
        self.fixed_amount_spin.setDecimals(2)
        self.fixed_amount_spin.setPrefix("₽ ")

        font = QFont("Arial", 10)
        self.name_edit.setFont(font)
        self.priority_combo.setFont(font)
        self.percentage_spin.setFont(font)
        self.fixed_amount_spin.setFont(font)

        layout.addRow("Название:", self.name_edit)
        layout.addRow("Приоритет:", self.priority_combo)
        layout.addRow("Процент от дохода:", self.percentage_spin)
        layout.addRow("Фиксированная сумма (если есть):", self.fixed_amount_spin)

        button_layout = QHBoxLayout()
        save_btn = QPushButton("💾 Сохранить")
        cancel_btn = QPushButton("❌ Отмена")
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)

        self.setLayout(layout)

        if category_data:
            self.fill_data(category_data)

        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)

    def fill_data(self, category_data):
        self.name_edit.setText(category_data[1])
        self.priority_combo.setCurrentIndex(category_data[2] - 1)
        self.percentage_spin.setValue(category_data[3])
        self.fixed_amount_spin.setValue(category_data[4])

    def get_data(self):
        priority_text = self.priority_combo.currentText().split()[0]
        priority_map = {"Высокий": 1, "Средний": 2, "Низкий": 3}
        priority = priority_map.get(priority_text, 2)
        is_fixed = self.fixed_amount_spin.value() > 0

        return (
            self.name_edit.text(),
            priority,
            self.percentage_spin.value(),
            self.fixed_amount_spin.value(),
            is_fixed
        )

# ==================================================
# 5. Главный виджет HUD — только категории
# ==================================================
class BudgetHUD(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            background-color: rgba(40, 44, 52, 240);
            border-radius: 12px;
            color: #abb2bf;
            padding: 12px;
        """)

        self.dragging = False
        self.offset = QPoint()

        # Основной layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setSpacing(12)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.setLayout(self.main_layout)

        # Заголовок
        self.title = QLabel("📊 Умный бюджет")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 16, QFont.Bold))
        self.title.setStyleSheet("color: #61afef; margin-bottom: 5px;")
        self.main_layout.addWidget(self.title)

        # Поле ввода зарплаты + кнопка
        salary_layout = QHBoxLayout()
        salary_layout.setSpacing(10)

        salary_label = QLabel("💰 Зарплата:")
        salary_label.setFont(QFont("Arial", 11))
        salary_layout.addWidget(salary_label)

        self.salary_input = QLineEdit()
        self.salary_input.setPlaceholderText("Введите сумму")
        self.salary_input.setFont(QFont("Arial", 11))
        self.salary_input.setStyleSheet("""
            background: #3e4451; 
            border: 1px solid #5c6370; 
            border-radius: 6px; 
            padding: 6px 10px;
            color: white;
        """)
        salary_layout.addWidget(self.salary_input)

        self.distribute_button = QPushButton("⚡ Распределить")
        self.distribute_button.setFont(QFont("Arial", 11, QFont.Bold))
        self.distribute_button.setStyleSheet("""
            QPushButton {
                background: #98c379;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #89b76a;
            }
            QPushButton:pressed {
                background: #7daa5c;
            }
        """)
        self.distribute_button.clicked.connect(self.smart_distribution)
        salary_layout.addWidget(self.distribute_button)

        self.main_layout.addLayout(salary_layout)

        # Горизонтальная линия-разделитель
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #5c6370;")
        self.main_layout.addWidget(separator)

        # Секция: Категории
        categories_title = QLabel("📋 Категории")
        categories_title.setFont(QFont("Arial", 12, QFont.Bold))
        categories_title.setStyleSheet("color: #c678dd; margin-top: 8px;")
        self.main_layout.addWidget(categories_title)

        # Прокручиваемая область категорий
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("border: none;")
        self.scroll_area.setMinimumHeight(400)

        self.scroll_content = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.scroll_content.setLayout(self.content_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # Контекстное меню
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_main_context_menu)

        # Загружаем данные
        self.load_categories()

    # ===============================
    # Служебные методы окна
    # ===============================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.globalPos() - self.pos()
        elif event.button() == Qt.RightButton:
            clicked_category = self.get_category_at_position(event.pos())
            if clicked_category:
                self.show_category_context_menu(event.globalPos(), clicked_category)
            else:
                self.show_main_context_menu(event.pos())

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.globalPos() - self.offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def get_category_at_position(self, pos):
        for i in range(self.content_layout.count()):
            item = self.content_layout.itemAt(i)
            if item.widget():
                widget = item.widget()
                global_pos = self.mapToGlobal(pos)
                local_widget_pos = widget.mapFromGlobal(global_pos)
                if widget.rect().contains(local_widget_pos):
                    if hasattr(widget, 'category_id'):
                        return widget.category_id
        return None

    def show_main_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c313a;
                border: 1px solid #5c6370;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #abb2bf;
            }
            QMenu::item:selected {
                background-color: #3e4451;
                color: white;
            }
        """)

        add_action = QAction("➕ Добавить категорию", self)
        add_action.triggered.connect(self.add_category)
        menu.addAction(add_action)

        refresh_action = QAction("🔄 Обновить", self)
        refresh_action.triggered.connect(self.load_categories)
        menu.addAction(refresh_action)

        menu.exec_(self.mapToGlobal(pos))

    def show_category_context_menu(self, global_pos, category_id):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c313a;
                border: 1px solid #5c6370;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 20px;
                color: #abb2bf;
            }
            QMenu::item:selected {
                background-color: #3e4451;
                color: white;
            }
        """)

        edit_action = QAction("✏️ Редактировать", self)
        edit_action.triggered.connect(lambda: self.edit_category_by_id(category_id))
        menu.addAction(edit_action)

        delete_action = QAction("🗑️ Удалить", self)
        delete_action.triggered.connect(lambda: self.delete_category(category_id))
        menu.addAction(delete_action)

        menu.exec_(global_pos)

    # ===============================
    # Работа с категориями
    # ===============================
    def load_categories(self):
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        conn = sqlite3.connect("budget_hud.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY priority, name")
        categories = cursor.fetchall()
        conn.close()

        if not categories:
            placeholder = QLabel("Нет категорий. Добавьте через контекстное меню (ПКМ).")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #5c6370; font-style: italic; padding: 20px;")
            self.content_layout.addWidget(placeholder)
            return

        for cat in categories:
            self.add_category_widget(cat)

    def add_category_widget(self, category):
        cat_id, name, priority, percentage, fixed_amount, is_fixed = category

        group = QWidget()
        group.category_id = cat_id
        group.setStyleSheet("""
            background: #2c313a;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 4px;
            border: 1px solid #3e4451;
        """)
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(8, 8, 8, 8)

        # Название и приоритет
        title_layout = QHBoxLayout()
        name_label = QLabel(f"<b>{name}</b>")
        name_label.setFont(QFont("Arial", 11, QFont.Bold))
        name_label.setStyleSheet("color: #abb2bf;")

        priority_map = {1: "🔴 Высокий", 2: "🟡 Средний", 3: "🟢 Низкий"}
        priority_color = {1: "#e06c75", 2: "#e5c07b", 3: "#98c379"}
        priority_label = QLabel(priority_map.get(priority, "Средний"))
        priority_label.setStyleSheet(f"color: {priority_color.get(priority, '#abb2bf')}; font-weight: bold;")

        title_layout.addWidget(name_label)
        title_layout.addStretch()
        title_layout.addWidget(priority_label)
        layout.addLayout(title_layout)

        # Сумма
        if fixed_amount > 0:
            amount_text = f"Фиксированно: <b>{format_currency(fixed_amount)}</b>"
        else:
            amount_text = f"Процент: <b>{percentage}%</b>"
        amount_label = QLabel(amount_text)
        amount_label.setStyleSheet("color: #c678dd; font-size: 10pt;")
        layout.addWidget(amount_label)

        # Прогресс-бар
        progress = QProgressBar()
        progress.setValue(0)
        progress.setFormat("Не распределено")
        progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #5c6370;
                border-radius: 4px;
                text-align: center;
                height: 16px;
                font-size: 12px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #61afef;
                border-radius: 4px;
            }
        """)
        layout.addWidget(progress)

        group.setLayout(layout)
        self.content_layout.addWidget(group)

    def add_category(self):
        dialog = EditCategoryDialog()
        if dialog.exec_() == QDialog.Accepted:
            name, priority, percentage, fixed_amount, is_fixed = dialog.get_data()
            if not name.strip():
                QMessageBox.warning(self, "Ошибка", "Введите название категории!")
                return

            conn = sqlite3.connect("budget_hud.db")
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO categories (name, priority, percentage, fixed_amount, is_fixed)
                VALUES (?, ?, ?, ?, ?)
            """, (name, priority, percentage, fixed_amount, is_fixed))
            conn.commit()
            conn.close()

            self.load_categories()

    def edit_category_by_id(self, category_id):
        conn = sqlite3.connect("budget_hud.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        category = cursor.fetchone()
        conn.close()

        if not category:
            QMessageBox.warning(self, "Ошибка", "Категория не найдена.")
            return

        dialog = EditCategoryDialog(category)
        if dialog.exec_() == QDialog.Accepted:
            name, priority, percentage, fixed_amount, is_fixed = dialog.get_data()
            conn = sqlite3.connect("budget_hud.db")
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE categories
                SET name = ?, priority = ?, percentage = ?, fixed_amount = ?, is_fixed = ?
                WHERE id = ?
            """, (name, priority, percentage, fixed_amount, is_fixed, category_id))
            conn.commit()
            conn.close()
            self.load_categories()

    def delete_category(self, category_id):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить категорию? Это действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect("budget_hud.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            conn.commit()
            conn.close()
            self.load_categories()

    # ===============================
    # Умное распределение
    # ===============================
    def smart_distribution(self):
        try:
            salary = float(self.salary_input.text())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму зарплаты!")
            return

        conn = sqlite3.connect("budget_hud.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY priority, is_fixed DESC")
        categories = cursor.fetchall()
        conn.close()

        remaining_salary = salary
        distribution_results = []

        # Сначала обрабатываем фиксированные с высоким приоритетом
        for cat in categories:
            cat_id, name, priority, percentage, fixed_amount, is_fixed = cat
            required = fixed_amount if is_fixed else (salary * percentage / 100)

            if remaining_salary >= required:
                allocated = required
                remaining_salary -= required
            else:
                allocated = remaining_salary
                remaining_salary = 0
                if priority == 1 and is_fixed:
                    QMessageBox.warning(
                        self,
                        "Внимание",
                        f"Недостаточно средств для полного покрытия высокоприоритетной категории '{name}'!\n"
                        f"Требуется: {format_currency(required)}\n"
                        f"Выделено: {format_currency(allocated)}"
                    )

            distribution_results.append({
                "id": cat_id,
                "name": name,
                "priority": priority,
                "required": required,
                "allocated": allocated
            })

        # Обновляем прогресс-бары
        for i in range(self.content_layout.count()):
            widget = self.content_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'category_id'):
                cat_id = widget.category_id
                result = next((r for r in distribution_results if r["id"] == cat_id), None)
                if result:
                    progress_bar = widget.findChild(QProgressBar)
                    if progress_bar:
                        if result["required"] > 0:
                            percent = int((result["allocated"] / result["required"]) * 100)
                            progress_bar.setValue(percent)
                            progress_bar.setFormat(f"{percent}% | {format_currency(result['allocated'])}")
                        else:
                            progress_bar.setValue(100)
                            progress_bar.setFormat(f"Выделено: {format_currency(result['allocated'])}")

        if remaining_salary > 0:
            QMessageBox.information(
                self,
                "Остаток",
                f"✅ Свободные средства после распределения: {format_currency(remaining_salary)}\n"
                "Можно добавить в 'Подушку безопасности' или 'Инвестиции'."
            )

    def closeEvent(self, event):
        event.ignore()  # Не закрывать, только сворачивать

# ==================================================
# 6. Запуск приложения
# ==================================================
if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)

    # Иконка в трее
    tray_icon = QSystemTrayIcon(QIcon())
    tray_icon.setIcon(app.style().standardIcon(QStyle.SP_ComputerIcon))

    tray_menu = QMenu()
    tray_menu.setStyleSheet("""
        QMenu {
            background-color: #2c313a;
            border: 1px solid #5c6370;
            border-radius: 6px;
        }
        QMenu::item {
            padding: 8px 20px;
            color: #abb2bf;
        }
        QMenu::item:selected {
            background-color: #3e4451;
            color: white;
        }
    """)

    show_action = QAction("Показать", app)
    hide_action = QAction("Скрыть", app)
    exit_action = QAction("Выход", app)

    show_action.triggered.connect(lambda: (hud.show(), hud.activateWindow()))
    hide_action.triggered.connect(lambda: hud.hide())
    exit_action.triggered.connect(app.quit)

    tray_menu.addAction(show_action)
    tray_menu.addAction(hide_action)
    tray_menu.addAction(exit_action)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    # Создаем HUD — компактный и чистый
    hud = BudgetHUD(app)
    hud.resize(500, 600)  # Ширина 500, высота 600 — идеально без графика
    hud.move(100, 50)
    hud.show()

    sys.exit(app.exec_())