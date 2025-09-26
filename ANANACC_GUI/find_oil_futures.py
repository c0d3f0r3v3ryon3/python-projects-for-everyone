import pandas as pd
import requests
import logging
import os
from datetime import datetime

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'

def find_oil_futures():
    try:
        url = f"{MOEX_BASE_URL}/securities.json"
        params = {'iss.meta': 'off', 'iss.only': 'securities',
                 'securities.columns': 'SECID,SHORTNAME,TYPE,LASTTRADEDATE'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
        df = df[df['TYPE'] == 'futures']
        br_futures = df[df['SHORTNAME'].str.contains('BR-')]
        br_futures['LASTTRADEDATE'] = pd.to_datetime(br_futures['LASTTRADEDATE'])

        current = br_futures[br_futures['LASTTRADEDATE'] >= datetime.now()].sort_values('LASTTRADEDATE').iloc[0]
        next_contract = br_futures[br_futures['LASTTRADEDATE'] > current['LASTTRADEDATE']].sort_values('LASTTRADEDATE').iloc[0] if len(br_futures) > 1 else current

        result = pd.DataFrame([current, next_contract])
        if not os.path.exists('data'):
            os.makedirs('data')
        result.to_csv('data/oil_futures.csv', index=False)
        logger.info("Фьючерсы Brent сохранены в data/oil_futures.csv")
    except Exception as e:
        logger.error(f"Ошибка в find_oil_futures: {str(e)}")
        raise

if __name__ == '__main__':
    find_oil_futures()
