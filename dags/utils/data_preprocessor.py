import os
import json
import pandas as pd


def process_data(filepaths: list, output_dir_for_data: str, annotated_data_filepath: str) -> None:
    df_list = []
    i = 0
    for file in filepaths:
        filepath = os.path.join(output_dir_for_data, file)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            city = file.split('.')[0]

            for el in data:
                if el['odo'] != '':
                    odo = int(el['odo'])
                else:
                    odo = None

                row = {
                    'id': i,
                    'car_model': el['model'],
                    'fuel_type': el['fuel_type'],
                    'transmission': el['transmission'],
                    'price': int(el['price']),
                    'odo': odo,
                    'year': el['year'],
                    'khv': 1 if city == 'khv' else 0,
                    'vdk': 1 if city == 'vdk' else 0,
                    'blg': 1 if city == 'blg' else 0
                }
                df_list.append(row)
                i += 1

    df = pd.DataFrame(df_list)
    df.to_csv(annotated_data_filepath, index=False)