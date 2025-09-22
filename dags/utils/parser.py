import logging
import os
import json
import time
import random
import requests
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry

logger = logging.getLogger('parser')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

class Parser:
    def __init__(self, req_headers: dict, base_url_dict: dict, class_name: str, output_filepath: str) -> None:
        self.base_url_dict = base_url_dict
        self.class_name = class_name
        self.req_headers = req_headers
        self.output_filepath = output_filepath
        logger.info(f'Initialized Parser with class_name={class_name}, urls={base_url_dict}')

    @sleep_and_retry
    @limits(calls=10, period=60)
    def parse_by_url(self, url: str, tag: str) -> tuple:
        logger.info(f'Fetching URL: {url}')
        time.sleep(random.uniform(1, 5))
        src = requests.get(url, headers=self.req_headers)
        logger.info(f'Response status code: {src.status_code}')
        if src.status_code != 200:
            logger.error(f'Failed to fetch {url}: {src.status_code}')
            return src, []
        htmldata = BeautifulSoup(src.text, 'lxml')
        data = htmldata.find_all(str(tag), class_=self.class_name)
        logger.info(f'Found {len(data)} elements with class {self.class_name}')
        return src, data

    def collect_elements(self) -> None:
        for key, value in self.base_url_dict.items():
            logger.info(f'Processing key: {key}, URL: {value}')
            src, parsed_links = self.parse_by_url(url=value, tag='div')
            listoflinks = []
            i = 0
            logger.info(f'Initial page: found {len(parsed_links)} elements')
            for dt in parsed_links:
                try:
                    price = dt.find('span', 'css-46itwz e162wx9x0').text
                    price = str(price).split()
                    price.pop(-1)
                    price = int(''.join(price))
                    car_data = dt.find_all('span', 'css-1l9tp44 e162wx9x0')
                    odo = car_data[-1].text
                    odo = str(odo).split()
                    model_and_year = dt.find('h3', 'css-16kqa8y efwtv890')

                    try:
                        fuel_type = car_data[1].text[:-1]
                    except Exception as e:
                        fuel_type = None
                        logger.warning(f'Failed to parse fuel_type: {e}')

                    try:
                        transmission = car_data[2].text[:-1]
                    except Exception as e:
                        transmission = None
                        logger.warning(f'Failed to parse transmission: {e}')

                    if model_and_year is None:
                        logger.warning('No model_and_year found, skipping')
                        continue

                    model_and_year_list = model_and_year.text.split(',')
                    year = int(model_and_year_list[1])
                    model = str(model_and_year_list[0])

                    if odo[0] == '(≈':
                        odo.pop(0)
                    odo.pop(-1)
                    odo = ''.join(odo)

                    car_info = {
                        'id': i,
                        'model': model,
                        'price': price,
                        'odo': odo,
                        'year': year,
                        'fuel_type': fuel_type,
                        'transmission': transmission
                    }
                    listoflinks.append(car_info)
                    logger.info(f'Parsed car: {car_info}')
                    i += 1
                except Exception as e:
                    logger.error(f'Error parsing element: {e}')
                    continue

            htmldata = BeautifulSoup(src.text, 'lxml')
            try:
                next_page_relative_url = htmldata.find('a', class_='_1j1e08n0 _1j1e08n5')['href']
                logger.info(f'Next page found: {next_page_relative_url}')
            except (TypeError, KeyError):
                logger.warning(f'No next page found for {value}')
                next_page_relative_url = None

            while next_page_relative_url is not None:
                src, parsed_links = self.parse_by_url(url=next_page_relative_url, tag='div')
                logger.info(f'Next page: {next_page_relative_url}, found {len(parsed_links)} elements')
                for dt in parsed_links:
                    try:
                        price = dt.find('span', 'css-46itwz e162wx9x0').text
                        price = str(price).split()
                        price.pop(-1)
                        price = int(''.join(price))
                        car_data = dt.find_all('span', 'css-1l9tp44 e162wx9x0')
                        odo = car_data[-1].text
                        odo = str(odo).split()
                        model_and_year = dt.find('h3', 'css-16kqa8y efwtv890')

                        try:
                            fuel_type = car_data[1].text[:-1]
                        except Exception as e:
                            fuel_type = None
                            logger.warning(f'Failed to parse fuel_type: {e}')

                        try:
                            transmission = car_data[2].text[:-1]
                        except Exception as e:
                            transmission = None
                            logger.warning(f'Failed to parse transmission: {e}')

                        if model_and_year is None:
                            logger.warning('No model_and_year found, skipping')
                            continue

                        model_and_year_list = model_and_year.text.split(',')
                        year = int(model_and_year_list[1])
                        model = str(model_and_year_list[0])

                        if odo[0] == '(≈':
                            odo.pop(0)
                        odo.pop(-1)
                        odo = ''.join(odo)

                        car_info = {
                            'id': i,
                            'model': model,
                            'price': price,
                            'odo': odo,
                            'year': year,
                            'fuel_type': fuel_type,
                            'transmission': transmission
                        }
                        listoflinks.append(car_info)
                        logger.info(f'Parsed car: {car_info}')
                        i += 1
                    except Exception as e:
                        logger.error(f'Error parsing element: {e}')
                        continue

                htmldata = BeautifulSoup(src.text, 'lxml')
                try:
                    next_page_relative_url = htmldata.find('a', class_='_1j1e08n0 _1j1e08n5')['href']
                    logger.info(f'Next page found: {next_page_relative_url}')
                except (TypeError, KeyError):
                    logger.warning(f'No next page found for {next_page_relative_url}')
                    next_page_relative_url = None

            filename = f"{key}.json"
            json_filepath = os.path.join(self.output_filepath, filename)
            logger.info(f'Saving data to {json_filepath}')
            with open(json_filepath, 'w', encoding='utf-8') as file:
                json.dump(listoflinks, file, ensure_ascii=False)
            logger.info(f'Saved {len(listoflinks)} items to {json_filepath}')