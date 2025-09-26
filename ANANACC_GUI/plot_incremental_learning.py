import pandas as pd
import plotly.express as px
import logging
import os

logging.basicConfig(filename='logs/app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

def plot_accuracy():
    try:
        if not os.path.exists('data/prediction_results.csv'):
            raise FileNotFoundError("Файл data/prediction_results.csv не найден")

        df = pd.read_csv('data/prediction_results.csv')
        fig = px.bar(df, x='Ticker', y='Mean_Accuracy', title='Средняя точность прогнозов по тикерам',
                    labels={'Mean_Accuracy': 'Точность', 'Ticker': 'Тикер'})

        if not os.path.exists('data'):
            os.makedirs('data')
        fig.write_html('data/accuracy_plot.html')
        logger.info("График сохранен в data/accuracy_plot.html")
    except Exception as e:
        logger.error(f"Ошибка в plot_accuracy: {str(e)}")
        raise

if __name__ == '__main__':
    plot_accuracy()
