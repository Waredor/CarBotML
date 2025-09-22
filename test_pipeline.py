import os
import yaml
import pandas as pd


# FILEPATHS INIT
config_filepath = 'configs/project_config.yaml'
with open(config_filepath, 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f)

OUTPUT_DIR_FOR_DATA = config_data['output_dir_for_data']
ANNOTATED_DATA_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'annotated_data.csv')
PREPROCESSED_DATA_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'preprocessed_data.csv')
Y_SCALER_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'y_scaler.pkl')
X_SCALER_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'x_scaler.pkl')
ODO_SCALER_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'odo_scaler.pkl')

df = pd.read_csv(ANNOTATED_DATA_FILEPATH, encoding='utf-8')

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

print(df.head(5))
df.to_csv(PREPROCESSED_DATA_FILEPATH, index=False)