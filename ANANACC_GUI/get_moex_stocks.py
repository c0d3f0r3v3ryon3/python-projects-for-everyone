import pandas as pd
import requests
import logging
import os
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

MOEX_BASE_URL = 'https://iss.moex.com/iss'

# Fallback list of tickers
FALLBACK_TICKERS = [
    {'SECID': 'GAZP', 'SHORTNAME': 'Gazprom', 'VALTODAY': 1000000},
    {'SECID': 'SBER', 'SHORTNAME': 'Sberbank', 'VALTODAY': 2000000},
    {'SECID': 'LKOH', 'SHORTNAME': 'Lukoil', 'VALTODAY': 1500000},
    {'SECID': 'ROSN', 'SHORTNAME': 'Rosneft', 'VALTODAY': 1200000},
    {'SECID': 'YNDX', 'SHORTNAME': 'Yandex', 'VALTODAY': 800000}
]

def get_moex_stocks():
    try:
        # Настройка retry для запросов
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        url = f"{MOEX_BASE_URL}/securities.json"
        params = {
            'iss.meta': 'off',
            'iss.only': 'securities',
            'securities.columns': 'SECID,SHORTNAME,TYPE,PREVADMITTEDQUOTE'
        }
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Логируем структуру ответа
        logger.info(f"API response columns: {data['securities']['columns']}")
        logger.debug(f"API response sample: {json.dumps(data['securities']['data'][:5], indent=2)}")

        if not data['securities']['data']:
            logger.warning("Пустой ответ от API, используется fallback")
            df = pd.DataFrame(FALLBACK_TICKERS)
        else:
            df = pd.DataFrame(data['securities']['data'], columns=data['securities']['columns'])

            # Проверяем наличие нужных колонок
            if 'TYPE' not in df.columns:
                logger.error("Колонка 'TYPE' отсутствует в ответе API")
                raise KeyError("Колонка 'TYPE' отсутствует")

            # Фильтрация акций
            df = df[df['TYPE'].isin(['common_share', 'preferred_share'])]

            # Сортировка по ликвидности
            liquidity_col = 'PREVADMITTEDQUOTE' if 'PREVADMITTEDQUOTE' in df.columns else None
            if liquidity_col is None:
                logger.warning("Колонка ликвидности отсутствует, используется fallback")
                df = pd.DataFrame(FALLBACK_TICKERS)
            else:
                df = df.sort_values(by=liquidity_col, ascending=False).head(50)

        # Сохранение результата
        if not os.path.exists('data'):
            os.makedirs('data')
        df.to_csv('data/stocks.csv', index=False)
        logger.info("Список акций успешно сохранен в data/stocks.csv")
        return df

    except Exception as e:
        logger.error(f"Ошибка в get_moex_stocks: {str(e)}")
        logger.info("Используется fallback список акций")
        df = pd.DataFrame(FALLBACK_TICKERS)
        if not os.path.exists('data'):
            os.makedirs('data')
        df.to_csv('data/stocks.csv', index=False)
        logger.info("Fallback список акций сохранен в data/stocks.csv")
        return df

if __name__ == '__main__':
    get_moex_stocks()
