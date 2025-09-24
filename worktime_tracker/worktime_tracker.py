import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import json
import os
import pandas as pd

# Файлы данных
SETTINGS_FILE = "worktime_settings.json"
SESSIONS_FILE = "worktime_sessions.json"


class WorkTimeTracker:
    def __init__(self, root):
        self.root = root
        self.root.title("WorkTime")
        self.root.resizable(False, False)

        # Состояния
        self.full_mode = False
        self.is_running = False
        self.paused = False
        self.start_time = None
        self.pause_start = None
        self.total_pause = datetime.timedelta()
        self.hourly_rate = 500
        self.saved_topmost = False
        self.sessions = []

        # Загружаем данные
        self.load_data()

        # Создаём интерфейс
        self.create_mini_ui()
        self.update_display()

    def create_mini_ui(self):
        """Минималистичный режим: только таймер и кнопки"""
        self.root.geometry("280x120")
        self.clear_window()

        # Таймер
        self.timer_label = tk.Label(self.root, text="00:00:00", font=("Courier", 24), fg="#2E8B57")
        self.timer_label.pack(pady=10)

        # Кнопки: старт, пауза, стоп
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)

        self.start_btn = tk.Button(btn_frame, text="Старт", width=8, command=self.start_timer)
        self.start_btn.grid(row=0, column=0, padx=2)

        self.pause_btn = tk.Button(btn_frame, text="Пауза", width=8, state="disabled", command=self.pause_timer)
        self.pause_btn.grid(row=0, column=1, padx=2)

        self.stop_btn = tk.Button(btn_frame, text="Стоп", width=8, state="disabled", bg="#f44336", fg="white", command=self.prepare_stop)
        self.stop_btn.grid(row=0, column=2, padx=2)

        # Кнопка разворачивания
        self.toggle_btn = tk.Button(self.root, text=">>", width=4, command=self.toggle_mode)
        self.toggle_btn.pack(pady=5)

        # Применяем "поверх всех окон", если было включено
        self.root.attributes("-topmost", self.saved_topmost)

    def create_full_ui(self):
        """Полный режим с расширенным функционалом"""
        self.root.geometry("700x700")
        self.clear_window()

        tk.Label(self.root, text="WorkTime Tracker", font=("Arial", 16, "bold"), fg="#1E90FF").pack(pady=10)

        # Таймер
        self.timer_label = tk.Label(self.root, text="00:00:00", font=("Courier", 32), fg="#2E8B57")
        self.timer_label.pack(pady=10)

        # Кнопки управления
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        self.start_btn = tk.Button(btn_frame, text="Старт", width=10, height=2, bg="#2196F3", fg="white", command=self.start_timer)
        self.start_btn.grid(row=0, column=0, padx=5)

        self.pause_btn = tk.Button(btn_frame, text="Пауза", width=10, height=2, state="disabled", command=self.pause_timer)
        self.pause_btn.grid(row=0, column=1, padx=5)

        self.stop_btn = tk.Button(btn_frame, text="Стоп", width=10, height=2, state="disabled", bg="#f44336", fg="white", command=self.prepare_stop)
        self.stop_btn.grid(row=0, column=2, padx=5)

        # Настройка ставки
        rate_frame = tk.Frame(self.root)
        rate_frame.pack(pady=5)
        tk.Label(rate_frame, text="Ставка (₽/ч):").pack(side="left")
        self.rate_entry = tk.Entry(rate_frame, width=10, font=("Arial", 10))
        self.rate_entry.insert(0, str(self.hourly_rate))
        self.rate_entry.pack(side="left", padx=5)
        tk.Button(rate_frame, text="Сохранить", command=self.save_rate).pack(side="left")

        # Поле для комментария
        comment_frame = tk.LabelFrame(self.root, text="Что было сделано?", padx=10, pady=5)
        comment_frame.pack(fill="x", padx=20, pady=10)
        self.comment_entry = tk.Text(comment_frame, height=3, width=50, font=("Arial", 10))
        self.comment_entry.pack(fill="x")

        # Кнопки: сворачивание и поверх всех
        bottom_frame = tk.Frame(self.root)
        bottom_frame.pack(pady=5)

        self.toggle_btn = tk.Button(bottom_frame, text="<<", width=10, command=self.toggle_mode)
        self.toggle_btn.pack(side="left", padx=10)

        self.always_on_top_var = tk.BooleanVar(value=self.saved_topmost)
        self.topmost_check = tk.Checkbutton(
            bottom_frame,
            text="Поверх всех окон",
            variable=self.always_on_top_var,
            command=self.toggle_always_on_top
        )
        self.topmost_check.pack(side="left")

        # История сессий
        hist_frame = tk.LabelFrame(self.root, text="История", padx=10, pady=10)
        hist_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("Дата", "Начало", "Конец", "Длительность", "Заработок", "Комментарий")
        self.tree = ttk.Treeview(hist_frame, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            width = 90 if col in ("Дата", "Начало", "Конец") else 100
            if col == "Комментарий":
                width = 150
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True)

        # Управление историей
        ctrl_frame = tk.Frame(hist_frame)
        ctrl_frame.pack(pady=5, fill="x")
        tk.Button(ctrl_frame, text="Удалить", command=self.delete_session).pack(side="left")
        tk.Button(ctrl_frame, text="Экспорт в Excel", command=self.export_to_excel).pack(side="right")

        # Статистика
        self.stats_label = tk.Label(self.root, text="", font=("Arial", 10), fg="gray")
        self.stats_label.pack(pady=5)

        # Применяем поверх всех окон
        self.root.attributes("-topmost", self.saved_topmost)

        # Обновляем интерфейс
        self.update_history()
        self.update_stats()

    def clear_window(self):
        """Очистка окна перед перерисовкой"""
        for widget in self.root.winfo_children():
            widget.destroy()

    def toggle_mode(self):
        """Переключение между мини и полным режимом"""
        if self.full_mode:
            self.create_mini_ui()
        else:
            self.create_full_ui()
        self.full_mode = not self.full_mode
        self.update_display()

    def toggle_always_on_top(self):
        """Включить/выключить поверх всех окон"""
        self.root.attributes("-topmost", self.always_on_top_var.get())
        self.save_settings()  # Сохраняем состояние

    def save_rate(self):
        """Сохранение почасовой ставки"""
        try:
            rate = float(self.rate_entry.get())
            if rate < 0:
                raise ValueError
            self.hourly_rate = rate
            self.save_settings()
            if self.full_mode:
                messagebox.showinfo("Готово", f"Ставка: {rate} ₽/ч")
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное число!")

    def start_timer(self):
        """Запуск таймера"""
        if not self.is_running:
            self.start_time = datetime.datetime.now()
            self.is_running = True
            self.paused = False
            self.total_pause = datetime.timedelta()
            self.pause_start = None
            self.update_timer()
            self.update_buttons()
            self.comment_entry.delete("1.0", tk.END)

    def pause_timer(self):
        """Пауза/продолжение"""
        if self.is_running:
            if not self.paused:
                self.paused = True
                self.pause_start = datetime.datetime.now()
                self.pause_btn.config(text="Продолжить")
            else:
                self.paused = False
                if self.pause_start:
                    self.total_pause += datetime.datetime.now() - self.pause_start
                    self.pause_start = None
                self.pause_btn.config(text="Пауза")

    def prepare_stop(self):
        """Открытие окна для комментария перед остановкой"""
        if self.is_running:
            dialog = tk.Toplevel(self.root)
            dialog.title("Комментарий")
            dialog.geometry("400x200")
            dialog.resizable(False, False)
            dialog.transient(self.root)
            dialog.grab_set()

            tk.Label(dialog, text="Что было сделано?", font=("Arial", 12)).pack(pady=10)
            comment_temp = tk.Text(dialog, height=5, width=40)
            comment_temp.pack(pady=5)

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=10)
            tk.Button(btn_frame, text="Отмена", width=10, command=dialog.destroy).pack(side="left", padx=5)
            tk.Button(btn_frame, text="Завершить", width=10, bg="#4CAF50", fg="white",
                      command=lambda: self.finalize_stop(comment_temp.get("1.0", tk.END).strip(), dialog)).pack(
                side="right", padx=5)

    def finalize_stop(self, comment, dialog):
        """Финальная остановка сессии"""
        dialog.destroy()
        end_time = datetime.datetime.now()
        duration = end_time - self.start_time - self.total_pause
        hours = duration.total_seconds() / 3600
        earnings = hours * self.hourly_rate

        session = {
            "date": self.start_time.strftime("%Y-%m-%d"),
            "start": self.start_time.strftime("%H:%M"),
            "end": end_time.strftime("%H:%M"),
            "duration_h": round(hours, 2),
            "earnings": round(earnings, 2),
            "comment": comment
        }
        self.sessions.append(session)
        self.save_sessions()

        self.is_running = False
        self.paused = False
        self.update_buttons()
        self.timer_label.config(text="00:00:00")

        if self.full_mode:
            self.update_history()
            self.update_stats()

    def update_timer(self):
        """Обновление таймера каждую секунду"""
        if self.is_running and not self.paused:
            now = datetime.datetime.now()
            elapsed = now - self.start_time - self.total_pause
            if self.pause_start:
                elapsed -= (now - self.pause_start)

            total_seconds = int(elapsed.total_seconds())
            hours, rem = divmod(total_seconds, 3600)
            mins, secs = divmod(rem, 60)
            days = elapsed.days
            hours += days * 24
            time_str = f"{hours:02}:{mins:02}:{secs:02}"
            self.timer_label.config(text=time_str)
            self.root.after(1000, self.update_timer)

    def update_buttons(self):
        """Обновление состояния кнопок"""
        if self.is_running:
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.pause_btn.config(state="disabled", text="Пауза")
            self.stop_btn.config(state="disabled")

    def update_history(self):
        """Обновление таблицы истории"""
        if not hasattr(self, 'tree'):
            return
        for row in self.tree.get_children():
            self.tree.delete(row)
        for s in reversed(self.sessions[-100:]):
            self.tree.insert("", "end", values=(
                s["date"],
                s["start"],
                s["end"],
                f"{s['duration_h']} ч",
                f"{s['earnings']} ₽",
                s["comment"] or "-"
            ))

    def update_stats(self):
        """Обновление статистики"""
        if not hasattr(self, 'stats_label'):
            return
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        def calc_stats(sessions):
            hours = sum(s["duration_h"] for s in sessions)
            money = sum(s["earnings"] for s in sessions)
            return round(hours, 1), int(money)

        today_s = [s for s in self.sessions if s["date"] == str(today)]
        week_s = [s for s in self.sessions if week_start <= datetime.date.fromisoformat(s["date"]) <= today]
        month_s = [s for s in self.sessions if datetime.date.fromisoformat(s["date"]) >= month_start]

        t_h, t_m = calc_stats(today_s)
        w_h, w_m = calc_stats(week_s)
        m_h, m_m = calc_stats(month_s)

        stats_text = f"Сегодня: {t_h}ч ({t_m}₽) | Неделя: {w_h}ч ({w_m}₽) | Месяц: {m_h}ч ({m_m}₽)"
        self.stats_label.config(text=stats_text)

    def delete_session(self):
        """Удаление выбранной сессии"""
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        values = item['values']
        for s in self.sessions:
            if s["start"] == values[1] and s["date"] == values[0]:
                self.sessions.remove(s)
                break
        self.save_sessions()
        self.update_history()
        self.update_stats()

    def export_to_excel(self):
        """Экспорт истории в Excel или CSV"""
        if not self.sessions:
            messagebox.showwarning("Пусто", "Нет данных для экспорта!")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel файлы", "*.xlsx"), ("CSV файлы", "*.csv")]
        )
        if not file_path:
            return
        df = pd.DataFrame(self.sessions)
        try:
            if file_path.endswith(".xlsx"):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)
            messagebox.showinfo("Успех", f"Сохранено в:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{str(e)}")

    def save_settings(self):
        """Сохранение настроек"""
        data = {
            "hourly_rate": self.hourly_rate,
            "always_on_top": self.always_on_top_var.get() if hasattr(self, 'always_on_top_var') else self.saved_topmost
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def save_sessions(self):
        """Сохранение сессий"""
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.sessions, f, ensure_ascii=False, indent=2)

    def load_data(self):
        """Загрузка данных при запуске"""
        # Сессии
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                try:
                    self.sessions = json.load(f)
                except:
                    self.sessions = []

        # Настройки
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    self.hourly_rate = data.get("hourly_rate", 500)
                    self.saved_topmost = data.get("always_on_top", False)
                except:
                    self.hourly_rate = 500
                    self.saved_topmost = False
        else:
            self.hourly_rate = 500
            self.saved_topmost = False

    def update_display(self):
        """Обновление интерфейса"""
        self.update_buttons()
        if self.is_running:
            self.update_timer()


# === Запуск приложения ===
if __name__ == "__main__":
    root = tk.Tk()
    app = WorkTimeTracker(root)
    root.mainloop()
