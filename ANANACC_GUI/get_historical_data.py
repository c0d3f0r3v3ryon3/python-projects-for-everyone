import pandas as pd
import requests
import yfinance as yf
import logging
import os
from datetime import datetime, timedelta
import time

# Настройка логирования
logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'
REQUEST_DELAY = 3.0  # Увеличено для предотвращения rate-limiting

def get_moex_data(ticker, start_date, end_date):
    try:
        url = f"{MOEX_BASE_URL}/history/engines/stock/markets/shares/boards/TQBR/securities/{ticker}.json"
        params = {
            'from': start_date,
            'till': end_date,
            'iss.meta': 'off',
            'iss.only': 'history',
            'history.columns': 'TRADEDATE,OPEN,HIGH,LOW,CLOSE,VOLUME'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        df = df.rename(columns={'TRADEDATE': 'Date', 'OPEN': 'Open', 'HIGH': 'High',
                               'LOW': 'Low', 'CLOSE': 'Close', 'VOLUME': 'Volume'})
        return df
    except Exception as e:
        logger.warning(f"Ошибка MOEX для {ticker}: {str(e)}")
        return pd.DataFrame()

def get_yahoo_data(ticker, start_date, end_date):
    try:
        yf_ticker = f"{ticker}.ME"
        stock = yf.Ticker(yf_ticker)
        df = stock.history(start=start_date, end=end_date)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.reset_index(inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        logger.warning(f"Ошибка Yahoo Finance для {ticker}: {str(e)}")
        return pd.DataFrame()

def compare_data(moex_df, yahoo_df, ticker):
    if moex_df.empty and yahoo_df.empty:
        logger.warning(f"Нет данных для {ticker} ни с MOEX, ни с Yahoo Finance")
        return pd.DataFrame(), None
    elif yahoo_df.empty:
        logger.info(f"Используется MOEX для {ticker}")
        return moex_df, 'MOEX'
    elif moex_df.empty:
        logger.info(f"Используется Yahoo Finance для {ticker}")
        return yahoo_df, 'Yahoo'

    moex_last_date = moex_df['Date'].max()
    yahoo_last_date = yahoo_df['Date'].max()
    moex_missing = moex_df[['Open', 'Close', 'Volume']].isna().sum().sum()
    yahoo_missing = yahoo_df[['Open', 'Close', 'Volume']].isna().sum().sum()

    # Предпочитаем MOEX для российских акций
    if moex_missing <= yahoo_missing or yahoo_last_date < moex_last_date:
        logger.info(f"Используется MOEX для {ticker}")
        return moex_df, 'MOEX'
    logger.info(f"Используется Yahoo Finance для {ticker}")
    return yahoo_df, 'Yahoo'

def get_historical_data(start_date='2023-01-01', end_date=None):
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists('data/stocks.csv'):
        raise FileNotFoundError("Файл data/stocks.csv не найден. Сначала выполните get_moex_stocks.py")

    stocks_df = pd.read_csv('data/stocks.csv')
    tickers = stocks_df['SECID'].tolist()

    if not os.path.exists('data/history'):
        os.makedirs('data/history')

    for ticker in tickers:
        logger.info(f"Сбор данных для {ticker}")
        moex_df = get_moex_data(ticker, start_date, end_date)
        yahoo_df = get_yahoo_data(ticker, start_date, end_date)
        df, source = compare_data(moex_df, yahoo_df, ticker)

        if not df.empty:
            df.to_csv(f'data/history/{ticker}.csv', index=False)
            logger.info(f"Данные для {ticker} сохранены в data/history/{ticker}.csv (Источник: {source})")
        else:
            logger.warning(f"Пропущен {ticker}: нет данных")

        time.sleep(REQUEST_DELAY)

if __name__ == '__main__':
    get_historical_data()
