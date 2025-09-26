import pandas as pd
import requests
import logging
import os

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'

def find_currency_pairs():
    try:
        url = f"{MOEX_BASE_URL}/securities.json"
        params = {'iss.meta': 'off', 'iss.only': 'securities', 'securities.columns': 'SECID,SHORTNAME,TYPE'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
        df = df[df['TYPE'] == 'currency']
        currencies = df[df['SECID'].isin(['USD000000TOD', 'EUR_RUB__TOD'])]

        if not os.path.exists('data'):
            os.makedirs('data')
        currencies.to_csv('data/currencies.csv', index=False)
        logger.info("Список валют сохранен в data/currencies.csv")
    except Exception as e:
        logger.error(f"Ошибка в find_currency_pairs: {str(e)}")
        raise

if __name__ == '__main__':
    find_currency_pairs()
