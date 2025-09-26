import pandas as pd
import matplotlib.pyplot as plt
import os
import json
import logging
import argparse

# Парсинг аргументов командной строки
parser = argparse.ArgumentParser()
parser.add_argument('--config', default='config.json', help='Path to config file')
args = parser.parse_args()

def load_config(config_file):
    """Загружает конфигурационный файл."""
    if not os.path.exists(config_file):
        logger.error(f"Config file {config_file} not found.")
        raise FileNotFoundError(f"Config file {config_file} not found.")
    with open(config_file, 'r') as f:
        return json.load(f)

# Загрузка конфигурации
config = load_config(args.config)

# Создание необходимых директорий
for dir_path in [config['logs_dir'], config['plots_dir']]:
    os.makedirs(dir_path, exist_ok=True)

# Настройка логирования
log_file = os.path.join(config['logs_dir'], 'plot_incremental_learning.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Конфигурация путей
LOG_FILE = os.path.join(config['logs_dir'], 'incremental_learning_log_final.csv')
OUTPUT_PLOT_FILE = os.path.join(config['plots_dir'], 'incremental_learning_accuracy_plot.png')
FIGURE_SIZE = (12, 6)
DPI = 150

def plot_accuracy_over_time(log_filename, output_plot_filename):
    """Строит график нарастающей точности от даты."""
    logger.info(f"Loading incremental learning log from {log_filename}...")
    if not os.path.exists(log_filename):
        logger.error(f"File {log_filename} not found.")
        return
    try:
        df = pd.read_csv(log_filename, encoding='utf-8-sig')
        logger.info(f"Log loaded: {len(df)} rows.")
    except Exception as e:
        logger.error(f"Error loading {log_filename}: {e}")
        return
    if df.empty:
        logger.error("Log is empty.")
        return
    required_columns = ['TRADEDATE', 'ACCURACY_CUMULATIVE']
    if not all(col in df.columns for col in required_columns):
        logger.error(f"Missing required columns in file {log_filename}: {required_columns}")
        logger.info(f"Found columns: {df.columns.tolist()}")
        return
    logger.info("Converting TRADEDATE column to datetime format...")
    df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'], format='%Y-%m-%d', errors='coerce')
    nat_count = df['TRADEDATE'].isna().sum()
    if nat_count > 0:
        logger.warning(f"Warning: {nat_count} rows have invalid date format and will be removed.")
        df = df.dropna(subset=['TRADEDATE'])
    if df.empty:
        logger.error("Log is empty after cleaning invalid dates.")
        return
    logger.info("Sorting data by date...")
    df = df.sort_values(by='TRADEDATE').reset_index(drop=True)
    logger.info(f"Data sorted. Date range: {df['TRADEDATE'].min()} - {df['TRADEDATE'].max()}")
    logger.info("Building plot...")
    plt.figure(figsize=FIGURE_SIZE, dpi=DPI)
    plt.plot(df['TRADEDATE'], df['ACCURACY_CUMULATIVE'], marker='o', linestyle='-', linewidth=1, markersize=3, color='blue')
    plt.title('Изменение точности модели в процессе инкрементального обучения')
    plt.xlabel('Дата (TRADEDATE)')
    plt.ylabel('Нарастающая точность (ACCURACY_CUMULATIVE)')
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.gcf().autofmt_xdate()
    plt.tight_layout()
    logger.info(f"Saving plot to {output_plot_filename}...")
    try:
        plt.savefig(output_plot_filename)
        logger.info("Plot saved.")
    except Exception as e:
        logger.error(f"Error saving plot to {output_plot_filename}: {e}")
    plt.show()
    plt.close()

def main():
    """Основная функция."""
    logger.info("Starting plot of incremental learning...")
    plot_accuracy_over_time(LOG_FILE, OUTPUT_PLOT_FILE)
    logger.info("Plotting completed.")

if __name__ == "__main__":
    main()
