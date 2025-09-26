import pandas as pd
import requests
import logging
import os
import time

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'
REQUEST_DELAY = 2.0

def get_index_history(start_date='2023-01-01', end_date=None):
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    if not os.path.exists('data/indices.csv'):
        raise FileNotFoundError("Файл data/indices.csv не найден. Сначала выполните find_indices.py")

    indices = pd.read_csv('data/indices.csv')['SECID'].tolist()

    if not os.path.exists('data/history'):
        os.makedirs('data/history')

    for index in indices:
        try:
            url = f"{MOEX_BASE_URL}/history/engines/stock/markets/index/securities/{index}.json"
            params = {
                'from': start_date,
                'till': end_date,
                'iss.meta': 'off',
                'iss.only': 'history',
                'history.columns': 'TRADEDATE,OPEN,HIGH,LOW,CLOSE'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data['history']['data'], columns=data['history']['columns'])
            df['TRADEDATE'] = pd.to_datetime(df['TRADEDATE'])
            df = df.rename(columns={'TRADEDATE': 'Date', 'OPEN': 'Open', 'HIGH': 'High',
                                   'LOW': 'Low', 'CLOSE': 'Close'})
            df.to_csv(f'data/history/{index}.csv', index=False)
            logger.info(f"Данные для {index} сохранены в data/history/{index}.csv")
        except Exception as e:
            logger.warning(f"Ошибка для {index}: {str(e)}")
        time.sleep(REQUEST_DELAY)

if __name__ == '__main__':
    get_index_history()
