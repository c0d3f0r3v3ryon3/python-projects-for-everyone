import pandas as pd
import requests
import logging
import os

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'

def find_indices():
    try:
        url = f"{MOEX_BASE_URL}/securities.json"
        params = {'iss.meta': 'off', 'iss.only': 'securities', 'securities.columns': 'SECID,SHORTNAME,TYPE'}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])
        df = df[df['TYPE'] == 'index']
        indices = df[df['SECID'].isin(['IMOEX', 'RTSI'])]

        if not os.path.exists('data'):
            os.makedirs('data')
        indices.to_csv('data/indices.csv', index=False)
        logger.info("Список индексов сохранен в data/indices.csv")
    except Exception as e:
        logger.error(f"Ошибка в find_indices: {str(e)}")
        raise

if __name__ == '__main__':
    find_indices()
