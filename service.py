import os
import pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from sklearn.neighbors import NearestNeighbors
from pydantic import BaseModel
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ClientData(BaseModel):
    price: int
    odo: int
    year: int
    city: str
    engine: str
    transmission: str

X_SCALER_PATH = os.path.join('data', 'x_scaler.pkl')
DATA_COLUMNS_PATH = os.path.join('data', 'data_columns.pkl')
PREPROCESSED_DATA_PATH = os.path.join('data', 'preprocessed_data.csv')
ANNOTATED_DATA_PATH = os.path.join('data', 'annotated_data.csv')

app = FastAPI()
knn = NearestNeighbors(n_neighbors=5, metric='cosine')


logger.debug(f"Checking file existence:")
logger.debug(f"x_scaler.pkl exists: {os.path.exists(X_SCALER_PATH)}")
logger.debug(f"data_columns.pkl exists: {os.path.exists(DATA_COLUMNS_PATH)}")
logger.debug(f"preprocessed_data.csv exists: {os.path.exists(PREPROCESSED_DATA_PATH)}")
logger.debug(f"annotated_data.csv exists: {os.path.exists(ANNOTATED_DATA_PATH)}")


for path in [X_SCALER_PATH, DATA_COLUMNS_PATH, PREPROCESSED_DATA_PATH, ANNOTATED_DATA_PATH]:
    logger.debug(f"Permissions for {path}: {os.access(path, os.R_OK)}")

@app.post('/create_recommendation')
async def create_recommendation(data: ClientData, request: Request):
    logger.debug(f"Incoming request: {request.method} {request.url}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(f"Request client: {request.client}")
    logger.debug(f"Request body: {data}")
    logger.debug(f"Data types: {[(k, type(v)) for k, v in data.__dict__.items()]}")

    try:
        with open(X_SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        logger.debug("Loaded scaler")
    except Exception as e:
        logger.error(f"Error loading scaler: {e}")
        raise

    try:
        with open(DATA_COLUMNS_PATH, 'rb') as f:
            data_columns = pickle.load(f)
        logger.debug("Loaded data_columns")
    except Exception as e:
        logger.error(f"Error loading data_columns: {e}")
        raise

    try:
        df = pd.read_csv(ANNOTATED_DATA_PATH, encoding='utf-8')
        preprocessed_df = pd.read_csv(PREPROCESSED_DATA_PATH, encoding='utf-8')
        logger.debug("Loaded annotated_data and preprocessed_data")
    except Exception as e:
        logger.error(f"Error loading CSV files: {e}")
        raise

    filtered_df_preprocessed = preprocessed_df[preprocessed_df['price'] <= data.price]

    city_condition = (
            (data.city == 'Хабаровск') & (df['khv'] == 1) |
            (data.city == 'Владивосток') & (df['vdk'] == 1) |
            (data.city == 'Благовещенск') & (df['blg'] == 1)
    )

    filtered_df = df[(df['price'] <= data.price) & city_condition]
    logger.debug(f"Filtered preprocessed df size: {len(filtered_df_preprocessed)}")
    logger.debug(f"Filtered annotated df size: {len(filtered_df)}")

    if filtered_df_preprocessed.empty:
        logger.warning("Filtered preprocessed df is empty")
        return {'recommendation': []}


    filtered_df_preprocessed = filtered_df_preprocessed.fillna(0)
    if filtered_df_preprocessed.isna().any().any():
        logger.error("NaN values detected after fillna")
        raise ValueError("NaN values detected in data")


    if not all(col in filtered_df_preprocessed.columns for col in data_columns):
        logger.error("Mismatch in columns between preprocessed data and data_columns")
        raise ValueError("Mismatch in columns")

    x = scaler.transform(filtered_df_preprocessed)
    knn.fit(x)
    logger.debug("KNN fitted")


    user_params = np.zeros((1, len(data_columns)))
    for i, col in enumerate(data_columns):
        if i == 0:
            user_params[0][i] = data.price
        elif i == 1:
            user_params[0][i] = data.odo
        elif i == 2:
            user_params[0][i] = data.year
        elif i == 3:
            user_params[0][i] = 1 if data.city.lower() in ['москва', 'санкт-петербург'] else 0
        elif i == 6:
            user_params[0][i] = 1 if data.transmission == 'АКПП' else 0
        elif i == 7:
            user_params[0][i] = 1 if data.transmission == 'Вариатор' else 0
        elif i == 8:
            user_params[0][i] = 1 if data.transmission == 'Механическая' else 0
        elif i == 9:
            user_params[0][i] = 1 if data.engine == 'Дизельный' else 0
        elif i == 10:
            user_params[0][i] = 1 if data.engine == 'Бензиновый' else 0
        elif i == 11:
            user_params[0][i] = 1 if data.engine == 'Гибридный' else 0
        else:
            user_params[0][i] = 0

    logger.debug(f"User params created: {user_params[0]}")

    user_df = pd.DataFrame(data=user_params, columns=data_columns)
    logger.debug(f"User DataFrame created, shape: {user_df.shape}, columns: {list(user_df.columns)}")
    user_embedding = scaler.transform(user_df)
    logger.debug("User embedding created")

    distances, indices = knn.kneighbors(user_embedding)
    logger.debug(f"KNN neighbors found, indices: {indices}")
    recommendations = filtered_df.iloc[indices[0]].copy()
    recommendations['distance'] = distances[0]
    logger.debug("Recommendations prepared")

    recommendations = recommendations.sort_values('distance')
    logger.debug("Recommendations sorted by distance")

    for col in recommendations.columns:
        if recommendations[col].dtype in ['int64', 'float64']:
            recommendations[col] = recommendations[col].astype(object).replace({np.nan: None})

    logger.debug("Recommendations converted to JSON-compatible format")
    return {'recommendation': recommendations.to_dict(orient='records')}