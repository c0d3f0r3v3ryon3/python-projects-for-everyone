import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Конфигурация ---
LOG_FILE = 'incremental_learning_log.csv'
OUTPUT_PLOT_FILE = 'incremental_learning_accuracy_plot.png'
FIGURE_SIZE = (12, 6) # Ширина, Высота в дюймах
DPI = 150 # Разрешение изображения

def plot_accuracy_over_time(log_filename, output_plot_filename):
    """Строит график нарастающей точности от даты."""
    print(f"Загружаю лог инкрементального обучения из {log_filename}...")
    if not os.path.exists(log_filename):
        print(f"Файл {log_filename} не найден.")
        return

    try:
        df = pd.read_csv(log_filename, encoding='utf-8-sig')
        print(f"Лог загружен: {len(df)} строк.")
    except Exception as e:
        print(f"Ошибка при загрузке {log_filename}: {e}")
        return

    if df.empty:
        print("Лог пуст.")
        return

    # Проверим наличие необходимых столбцов
    required_columns = ['TRADEDATE', 'ACCURACY_CUMULATIVE']
    if not all(col in df.columns for col in required_columns):
        print(f"В файле {log_filename} отсутствуют необходимые столбцы: {required_columns}")
        print(f"Найденные столбцы: {df.columns.tolist()}")
        return

    # Преобразуем TRADEDATE в datetime
    print("Преобразование столбца TRADEDATE в формат datetime...")
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')

    # Проверим на NaT (Not a Time) после преобразования
    nat_count = df['TRADEDATE'].isna().sum()
    if nat_count > 0:
        print(f"Предупреждение: {nat_count} строк имеют некорректный формат даты и будут удалены.")
        df = df.dropna(subset=['TRADEDATE'])

    if df.empty:
        print("После очистки некорректных дат лог пуст.")
        return

    # Сортируем по дате
    print("Сортировка данных по дате...")
    df = df.sort_values(by='TRADEDATE').reset_index(drop=True)
    print(f"Данные отсортированы. Диапазон дат: {df['TRADEDATE'].min()} - {df['TRADEDATE'].max()}")

    # Создаем график
    print("Построение графика...")
    plt.figure(figsize=FIGURE_SIZE, dpi=DPI)
    plt.plot(df['TRADEDATE'], df['ACCURACY_CUMULATIVE'], marker='o', linestyle='-', linewidth=1, markersize=3, color='blue')
    plt.title('Изменение точности модели в процессе инкрементального обучения')
    plt.xlabel('Дата (TRADEDATE)')
    plt.ylabel('Нарастающая точность (ACCURACY_CUMULATIVE)')
    plt.grid(True, linestyle='--', alpha=0.5)

    # Автоматическое форматирование дат на оси X для лучшей читаемости
    plt.gcf().autofmt_xdate() # Поворачивает метки дат

    # Добавим немного места по краям
    plt.tight_layout()

    # Сохраняем график
    print(f"Сохранение графика в {output_plot_filename}...")
    plt.savefig(output_plot_filename)
    print("График сохранен.")
    plt.show() # Открываем окно с графиком (опционально)
    plt.close() # Закрываем фигуру, чтобы освободить память

def main():
    """Основная функция."""
    print("Начинаю построение графика инкрементального обучения...")
    plot_accuracy_over_time(LOG_FILE, OUTPUT_PLOT_FILE)
    print("Построение графика завершено.")

if __name__ == "__main__":
    main()
