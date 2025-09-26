import pandas as pd
import requests
import yfinance as yf
import logging
import os
from datetime import datetime, timedelta

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'
REQUEST_DELAY = 2.0

def get_moex_oil_data(ticker, start_date, end_date, board='RFUD'):
    try:
        url = f"{MOEX_BASE_URL}/history/engines/futures/markets/forts/boards/{board}/securities/{ticker}.json"
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

def get_yahoo_oil_data(start_date, end_date):
    try:
        stock = yf.Ticker("BZ=F")  # Brent Crude Oil Futures
        df = stock.history(start=start_date, end=end_date)
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        df.reset_index(inplace=True)
        df['Date'] = pd.to_datetime(df['Date'])
        return df
    except Exception as e:
        logger.warning(f"Ошибка Yahoo Finance для Brent: {str(e)}")
        return pd.DataFrame()

def get_oil_future_history(start_date='2023-01-01', end_date=None):
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists('data/oil_futures.csv'):
        raise FileNotFoundError("Файл data/oil_futures.csv не найден. Сначала выполните find_oil_futures.py")

    futures = pd.read_csv('data/oil_futures.csv')
    current = futures.iloc[0]['SECID']
    next_contract = futures.iloc[1]['SECID'] if len(futures) > 1 else current
    switch_date = pd.to_datetime(futures.iloc[0]['LASTTRADEDATE']) - timedelta(days=30)

    moex_df = pd.DataFrame()
    if pd.to_datetime(end_date) < switch_date:
        moex_df = get_moex_oil_data(current, start_date, end_date)
    else:
        df1 = get_moex_oil_data(current, start_date, switch_date.strftime('%Y-%m-%d'))
        df2 = get_moex_oil_data(next_contract, (switch_date + timedelta(days=1)).strftime('%Y-%m-%d'), end_date)
        moex_df = pd.concat([df1, df2]).drop_duplicates(subset='Date').reset_index(drop=True)

    yahoo_df = get_yahoo_oil_data(start_date, end_date)

    df = moex_df if yahoo_df.empty else yahoo_df  # Yahoo Finance как резервный источник
    if not df.empty:
        if not os.path.exists('data/history'):
            os.makedirs('data/history')
        df.to_csv('data/history/BR.csv', index=False)
        logger.info("Данные по Brent сохранены в data/history/BR.csv")
    else:
        logger.warning("Не удалось получить данные по Brent")

if __name__ == '__main__':
    get_oil_future_history()
