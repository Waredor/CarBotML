import os
import pickle
import yaml
import pandas as pd

from sklearn.preprocessing import MinMaxScaler
from sklearn.impute import SimpleImputer


# FILEPATHS INIT
config_filepath = 'configs/project_config.yaml'
with open(config_filepath, 'r', encoding='utf-8') as f:
    config_data = yaml.safe_load(f)

OUTPUT_DIR_FOR_DATA = config_data['output_dir_for_data']
ANNOTATED_DATA_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'annotated_data.csv')
PREPROCESSED_DATA_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'preprocessed_data.csv')
SCALED_DATA_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'scaled_data.csv')
X_SCALER_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'x_scaler.pkl')
COLUMNS_LIST_FILEPATH = os.path.join(OUTPUT_DIR_FOR_DATA, 'data_columns.pkl')

df = pd.read_csv(ANNOTATED_DATA_FILEPATH, encoding='utf-8')

categorical_features = ['transmission', 'fuel_type']
categorical_imputer = SimpleImputer(strategy='most_frequent')
df[categorical_features] = categorical_imputer.fit_transform(df[categorical_features])


numeric_features = ['price', 'odo', 'year']
numeric_imputer = SimpleImputer(strategy='mean')
df[numeric_features] = numeric_imputer.fit_transform(df[numeric_features])

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

df['price_per_mileage'] = df.apply(
    lambda row: row['price'] / row['odo'] if row['odo'] > 0 else 0, axis=1
)
df['model_selling_frequency'] = df['model_name'].map(model_counts)

one_hot_encoded_model = pd.get_dummies(df['model_name'], prefix='model', dtype='int')
df = pd.concat([df, one_hot_encoded_model], axis=1)

df.drop(columns=['fuel_type', 'transmission', 'car_model', 'car_manufacturer', 'id', 'model_name'], inplace=True)

features_scaler = MinMaxScaler()
columns = df.columns
X = features_scaler.fit_transform(df)
scaled_df = pd.DataFrame(data=X, columns=columns)

columns = columns.tolist()

with open(X_SCALER_FILEPATH, 'wb') as f:
    pickle.dump(features_scaler, f)

with open(COLUMNS_LIST_FILEPATH, 'wb') as f:
    pickle.dump(columns, f)


print(df.head(5))
scaled_df.to_csv(SCALED_DATA_FILEPATH, index=False)
df.to_csv(PREPROCESSED_DATA_FILEPATH, index=False)