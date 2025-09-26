import pandas as pd
import requests
from bs4 import BeautifulSoup
import logging
import os
from datetime import datetime

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def get_key_rate_history():
    try:
        url = 'https://www.cbr.ru/hd_base/KeyRate/'
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', class_='data')
        dates = []
        rates = []
        for row in table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) >= 2:
                date = pd.to_datetime(cols[0].text.strip(), dayfirst=True)
                rate = float(cols[1].text.strip().replace(',', '.'))
                dates.append(date)
                rates.append(rate)

        df = pd.DataFrame({'Date': dates, 'KeyRate': rates})
        df = df.sort_values('Date').reset_index(drop=True)

        if not os.path.exists('data'):
            os.makedirs('data')
        df.to_csv('data/key_rate.csv', index=False)
        logger.info("Ключевая ставка сохранена в data/key_rate.csv")
    except Exception as e:
        logger.error(f"Ошибка в get_key_rate_history: {str(e)}")
        raise

if __name__ == '__main__':
    get_key_rate_history()
