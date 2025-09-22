import os
import sys
import logging
import yaml
import pandas as pd

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator


# PROJECT ROOT INIT
init_path = os.path.abspath(__file__)

def get_project_root(start_path):
    current = start_path
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, "requirements.txt")):
            return current
        current = os.path.dirname(current)
    raise FileNotFoundError("Project root was not found")


project_root = get_project_root(init_path)
sys.path.insert(0, project_root)

from utils.parser import Parser
from utils.data_preprocessor import process_data



# LOGGER INIT
stream_handler = logging.StreamHandler()
logger = logging.getLogger('drom_data_etl_dag_logger')
logger.setLevel(logging.INFO)
logger.addHandler(stream_handler)

# DAG DEFAULT ARGS
default_args = {
    'owner': 'ProshutinskiyVK',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}

# CREATE DAG
with DAG(
    dag_id='drom_data_etl_dag',
    default_args=default_args,
    description='DAG пайплайна парсинга данных drom.ru',
    schedule='@daily',
    start_date=datetime(2025, 9, 17),  # Установлено на 2025-09-17
    catchup=False,
) as dag:
    def parse_data(**kwargs) -> None:
        """
        Метод parse_data() отвечает за парсинг веб-страниц и формирование .json файлов после парсинга.
        Parameters:
            kwargs
        Returns:
             None
        """
        logger.info('Filepaths init')
        config_filepath = os.path.join(project_root, 'configs', 'project_config.yaml')
        logger.info(f'Loading config from: {config_filepath}')
        try:
            with open(config_filepath, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            logger.info(f'Config loaded: {config_data}')
        except Exception as e:
            logger.error(f'Failed to load config: {e}')
            raise

        output_dir_for_data = config_data['output_dir_for_data']
        annotated_data_filepath = os.path.join(output_dir_for_data, 'annotated_data.csv')
        logger.info(f'Output dir: {output_dir_for_data}, Annotated file: {annotated_data_filepath}')

        headers = config_data['headers']
        class_name = config_data['class_name']
        url_dict = config_data['url_dict']
        logger.info(f'Headers: {headers}, Class: {class_name}, URLs: {url_dict}')

        try:
            parser = Parser(
                req_headers=headers,
                base_url_dict=url_dict,
                class_name=class_name,
                output_filepath=output_dir_for_data
            )
            logger.info('Starting collecting data')
            parser.collect_elements()
            logger.info('Data collection completed')
        except Exception as e:
            logger.error(f'Error in collect_elements: {e}')
            raise

        kwargs['ti'].xcom_push(key='output_dir_for_data', value=output_dir_for_data)
        kwargs['ti'].xcom_push(key='annotated_data_filepath', value=annotated_data_filepath)


    def preprocess_data(**kwargs) -> None:
        """
        Метод preprocess_data() отвечает за создание pandas dataframe
        из .json файлов, полученных в результате парсинга веб-страниц.
        Parameters:
            kwargs
        Returns:
             None
        """
        ti = kwargs['ti']
        output_dir_for_data = ti.xcom_pull(key='output_dir_for_data', task_ids='parse_data_task')
        annotated_data_filepath = ti.xcom_pull(key='annotated_data_filepath', task_ids='parse_data_task')
        logger.info(f'Received XCom: output_dir={output_dir_for_data}, annotated_file={annotated_data_filepath}')

        logger.info('Starting transforming data')
        try:
            files = [el for el in os.listdir(output_dir_for_data) if el.endswith('.json')]
            logger.info(f'Found {len(files)} JSON files: {files}')
            process_data(
                filepaths=files,
                output_dir_for_data=output_dir_for_data,
                annotated_data_filepath=annotated_data_filepath
            )
            logger.info('Data preprocessing completed')
        except Exception as e:
            logger.error(f'Error in preprocess_data: {e}')
            raise


    def feature_engineering(**kwargs) -> None:
        ti = kwargs['ti']
        annotated_data_filepath = ti.xcom_pull(key='annotated_data_filepath', task_ids='parse_data_task')
        output_dir_for_data = ti.xcom_pull(key='output_dir_for_data', task_ids='parse_data_task')
        preprocessed_data_filepath = os.path.join(output_dir_for_data, 'preprocessed_data.csv')

        logger.info('Starting feature engineering')
        try:
            df = pd.read_csv(annotated_data_filepath, encoding='utf-8')

            df['at_transmission'] = df['transmission'].isin(['АКПП', 'автомат']).astype(int)
            df['cvt_transmission'] = df['transmission'].isin(['вариатор']).astype(int)
            df['mt_transmission'] = df['transmission'].isin(['механика']).astype(int)

            df['fuel_type_diesel'] = df['fuel_type'].isin(['дизель']).astype(int)
            df['fuel_type_gasoline'] = df['fuel_type'].isin(['бензин']).astype(int)
            df['fuel_type_hybrid'] = df['fuel_type'].isin(['гибрид']).astype(int)

            df['car_model'] = df['car_model'].fillna('Unknown Unknown')
            df['car_manufacturer'] = df['car_model'].str.split(' ', expand=True)[0].str.strip()
            df['model_name'] = df['car_model'].str.split(' ', expand=True).iloc[:, 1:].fillna('').agg(' '.join, axis=1).str.strip()

            model_counts = df['model_name'].value_counts()

            df['price_per_mileage'] = df['price'] / df['odo']
            df['model_selling_frequency'] = df['model_name'].map(model_counts)

            one_hot_encoded_model = pd.get_dummies(df['model_name'], prefix='model', dtype='int')
            df = pd.concat([df, one_hot_encoded_model], axis=1)

            df.drop(columns=['fuel_type', 'transmission', 'car_model', 'car_manufacturer', 'id', 'model_name'], inplace=True)

            df.to_csv(preprocessed_data_filepath, index=False)
            logger.info('Feature engineering completed')
        except Exception as e:
            logger.error(f'Error in feature_engineering: {e}')
            raise


    parse_task = PythonOperator(
        task_id='parse_data_task',
        python_callable=parse_data,
        provide_context=True,
    )

    preprocess_task = PythonOperator(
        task_id='preprocess_data_task',
        python_callable=preprocess_data,
        provide_context=True,
    )

    feature_engineering_task = PythonOperator(
        task_id='feature_engineering_task',
        python_callable=feature_engineering,
        provide_context=True,
    )

    parse_task >> preprocess_task >> feature_engineering_task