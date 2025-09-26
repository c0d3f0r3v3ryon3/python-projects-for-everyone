import pandas as pd
import requests
import yfinance as yf
import logging
import os
import time
from datetime import datetime

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'
REQUEST_DELAY = 2.0

def get_moex_currency_data(ticker, start_date, end_date):
    try:
        url = f"{MOEX_BASE_URL}/history/engines/currency/markets/selt/boards/CETS/securities/{ticker}.json"
        params = {
            'from': start_date,
            'till': end_date,
            'iss.meta': 'off',
            'iss.only': 'history',
            'history.columns': 'TRADEDATE,OPEN,HIGH,LOW,CLOSE,VOLRUR'
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
        df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
        df = df.rename(columns={'TRADEDATE': 'Date', 'OPEN': 'Open', 'HIGH': 'High',
                               'LOW': 'Low', 'CLOSE': 'Close', 'VOLRUR': 'Volume'})
        return df
    except Exception as e:
        logger.warning(f"Ошибка MOEX для {ticker}: {str(e)}")
        return pd.DataFrame()

def get_yahoo_currency_data(ticker, start_date, end_date):
    try:
        yf_ticker = 'USDRUB=X' if ticker == 'USD000000TOD' else 'EURRUB=X'
        stock = yf.Ticker(yf_ticker)
        df = stock.history(start=start_date, end=end_date)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.reset_index(inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        logger.warning(f"Ошибка Yahoo Finance для {ticker}: {str(e)}")
        return pd.DataFrame()

def compare_data(moex_df, yahoo_df):
    if moex_df.empty and yahoo_df.empty:
        return pd.DataFrame()
    elif moex_df.empty:
        return yahoo_df
    elif yahoo_df.empty:
        return moex_df

    moex_last_date = moex_df['Date'].max()
    yahoo_last_date = yahoo_df['Date'].max()
    moex_missing = moex_df[['Open', 'Close', 'Volume']].isna().sum().sum()
    yahoo_missing = yahoo_df[['Open', 'Close', 'Volume']].isna().sum().sum()

    if yahoo_last_date > moex_last_date and yahoo_missing <= moex_missing:
        return yahoo_df
    return moex_df

def get_currency_history(start_date='2023-01-01', end_date=None):
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists('data/currencies.csv'):
        raise FileNotFoundError("Файл data/currencies.csv не найден. Сначала выполните find_currency_pairs.py")

    currencies = pd.read_csv('data/currencies.csv')['SECID'].tolist()

    if not os.path.exists('data/history'):
        os.makedirs('data/history')

    for currency in currencies:
        logger.info(f"Сбор данных для {currency}")
        moex_df = get_moex_currency_data(currency, start_date, end_date)
        yahoo_df = get_yahoo_currency_data(currency, start_date, end_date)
        df = compare_data(moex_df, yahoo_df)

        if not df.empty:
            df.to_csv(f'data/history/{currency}.csv', index=False)
            logger.info(f"Данные для {currency} сохранены в data/history/{currency}.csv")
        else:
            logger.warning(f"Не удалось получить данные для {currency}")

        time.sleep(REQUEST_DELAY)

if __name__ == '__main__':
    get_currency_history()
