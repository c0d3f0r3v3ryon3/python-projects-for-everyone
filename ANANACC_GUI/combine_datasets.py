import pandas as pd
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def combine_datasets():
    try:
        # Загрузка данных
        if not os.path.exists('data/stocks.csv'):
            raise FileNotFoundError("Файл data/stocks.csv не найден")
        stocks_df = pd.read_csv('data/stocks.csv')
        tickers = stocks_df['SECID'].tolist()

        all_dfs = []

        # Загрузка данных по акциям
        for ticker in tickers:
            file_path = f'data/history/{ticker}.csv'
            if not os.path.exists(file_path):
                logger.warning(f"Файл {file_path} не найден, пропускаем {ticker}")
                continue
            df = pd.read_csv(file_path)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[['Date', 'Open', 'Close', 'Volume']].rename(
                columns={'Open': f'{ticker}_Open', 'Close': f'{ticker}_Close', 'Volume': f'{ticker}_Volume'}
            )
            all_dfs.append(df)

        # Загрузка индексов
        indices = []
        if os.path.exists('data/indices.csv'):
            indices = pd.read_csv('data/indices.csv')['SECID'].tolist()
            for index in indices:
                file_path = f'data/history/{index}.csv'
                if not os.path.exists(file_path):
                    logger.warning(f"Файл {file_path} не найден, пропускаем {index}")
                    continue
                df = pd.read_csv(file_path)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df[['Date', 'Close']].rename(columns={'Close': f'{index}_Close'})
                all_dfs.append(df)
        else:
            logger.warning("Файл data/indices.csv не найден, индексы пропущены")

        # Загрузка валют
        currencies = []
        if os.path.exists('data/currencies.csv'):
            currencies = pd.read_csv('data/currencies.csv')['SECID'].tolist()
            for currency in currencies:
                file_path = f'data/history/{currency}.csv'
                if not os.path.exists(file_path):
                    logger.warning(f"Файл {file_path} не найден, пропускаем {currency}")
                    continue
                df = pd.read_csv(file_path)
                df['Date'] = pd.to_datetime(df['Date'])
                df = df[['Date', 'Close', 'Volume']].rename(
                    columns={'Close': f'{currency}_Close', 'Volume': f'{currency}_Volume'}
                )
                all_dfs.append(df)
        else:
            logger.warning("Файл data/currencies.csv не найден, валюты пропущены")

        # Загрузка Brent
        if os.path.exists('data/history/BR.csv'):
            df = pd.read_csv('data/history/BR.csv')
            df['Date'] = pd.to_datetime(df['Date'])
            df = df[['Date', 'Close', 'Volume']].rename(
                columns={'Close': 'BR_Close', 'Volume': 'BR_Volume'}
            )
            all_dfs.append(df)
        else:
            logger.warning("Файл data/history/BR.csv не найден, Brent пропущен")

        # Загрузка ключевой ставки
        if os.path.exists('data/key_rate.csv'):
            df = pd.read_csv('data/key_rate.csv')
            df['Date'] = pd.to_datetime(df['Date'])
            all_dfs.append(df)
        else:
            logger.warning("Файл data/key_rate.csv не найден, ключевая ставка пропущена")

        if not all_dfs:
            raise ValueError("Нет доступных данных для объединения")

        # Объединение
        merged_df = all_dfs[0]
        for df in all_dfs[1:]:
            merged_df = merged_df.merge(df, on='Date', how='outer')

        merged_df = merged_df.sort_values('Date')
        merged_df = merged_df.fillna(method='ffill').fillna(method='bfill')

        # Создание целевых переменных для всех тикеров
        for ticker in tickers:
            if f'{ticker}_Close' in merged_df.columns:
                merged_df[f'{ticker}_TARGET_DIRECTION'] = 0
                merged_df.loc[merged_df[f'{ticker}_Close'].shift(-1) > merged_df[f'{ticker}_Close'],
                            f'{ticker}_TARGET_DIRECTION'] = 1
                merged_df.loc[merged_df[f'{ticker}_Close'].shift(-1) < merged_df[f'{ticker}_Close'],
                            f'{ticker}_TARGET_DIRECTION'] = -1

        if not os.path.exists('data'):
            os.makedirs('data')
        merged_df.to_csv('data/combined_dataset_all_targets.csv', index=False)
        logger.info("Объединенный датасет сохранен в data/combined_dataset_all_targets.csv")
    except Exception as e:
        logger.error(f"Ошибка в combine_datasets: {str(e)}")
        raise

if __name__ == '__main__':
    combine_datasets()
