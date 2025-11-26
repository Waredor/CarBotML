import os
import pickle
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request, HTTPException
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

X_SCALER_PATH = os.path.join('/opt/airflow/data', 'x_scaler.pkl')
DATA_COLUMNS_PATH = os.path.join('/opt/airflow/data', 'data_columns.pkl')
PREPROCESSED_DATA_PATH = os.path.join('/opt/airflow/data', 'preprocessed_data.csv')
ANNOTATED_DATA_PATH = os.path.join('/opt/airflow/data', 'annotated_data.csv')

app = FastAPI()
knn = NearestNeighbors(n_neighbors=5, metric='manhattan')

logger.debug(f"Checking file existence:")
logger.debug(f"x_scaler.pkl exists: {os.path.exists(X_SCALER_PATH)}")
logger.debug(f"data_columns.pkl exists: {os.path.exists(DATA_COLUMNS_PATH)}")
logger.debug(f"preprocessed_data.csv exists: {os.path.exists(PREPROCESSED_DATA_PATH)}")
logger.debug(f"annotated_data.csv exists: {os.path.exists(ANNOTATED_DATA_PATH)}")

for path in [X_SCALER_PATH, DATA_COLUMNS_PATH, PREPROCESSED_DATA_PATH, ANNOTATED_DATA_PATH]:
    logger.debug(f"Permissions for {path}: {os.access(path, os.R_OK)}")

@app.post('/create_recommendation')
def create_recommendation(data: ClientData):
    logger.debug(f"Request body: {data}")

    try:
        with open(X_SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)
        logger.debug("Loaded scaler")

        with open(DATA_COLUMNS_PATH, 'rb') as f:
            data_columns = pickle.load(f)
        logger.debug("Loaded data_columns")

        df = pd.read_csv(ANNOTATED_DATA_PATH, encoding='utf-8')
        preprocessed_df = pd.read_csv(PREPROCESSED_DATA_PATH, encoding='utf-8')
        logger.debug("Loaded annotated_data and preprocessed_data")
        logger.debug(f"Initial df size: {len(df)}, preprocessed_df size: {len(preprocessed_df)}")

        if len(df) != len(preprocessed_df):
            logger.error("Initial DataFrame sizes do not match")
            raise HTTPException(status_code=500, detail="Initial DataFrame sizes do not match")

        filtered_df = df[df['price'] <= data.price]
        filtered_df_preprocessed = preprocessed_df[preprocessed_df['price'] <= data.price]

        logger.info(f"filtered_df length: {len(filtered_df)}")
        logger.info(f"filtered_df_preprocessed length: {len(filtered_df_preprocessed)}")

        if filtered_df.empty:
            logger.warning("Filtered DataFrame is empty")
            return {'recommendation': []}

        filtered_df_preprocessed = filtered_df_preprocessed.fillna(0)
        logger.info(f"Is NaN: {filtered_df_preprocessed.isna().any().any()}")

        if filtered_df_preprocessed.isna().any().any():
            logger.error("NaN in filtered preprocessed after fillna")
            raise ValueError("Persistent NaN in data")

        x = scaler.transform(filtered_df_preprocessed[data_columns])
        knn.fit(x)
        logger.debug("KNN fitted")

        user_params = np.zeros((1, len(data_columns)))
        for i, col in enumerate(data_columns):
            if col == 'price':
                user_params[0][i] = data.price
            elif col == 'odo':
                user_params[0][i] = data.odo
            elif col == 'year':
                user_params[0][i] = data.year
            elif col == 'khv':
                user_params[0][i] = 1 if data.city == 'Хабаровск' else 0
            elif col == 'vdk':
                user_params[0][i] = 1 if data.city == 'Владивосток' else 0
            elif col == 'blg':
                user_params[0][i] = 1 if data.city == 'Благовещенск' else 0
            elif col == 'at_transmission':
                user_params[0][i] = 1 if data.transmission == 'АКПП' else 0
            elif col == 'cvt_transmission':
                user_params[0][i] = 1 if data.transmission == 'Вариатор' else 0
            elif col == 'mt_transmission':
                user_params[0][i] = 1 if data.transmission == 'Механическая' else 0
            elif col == 'fuel_type_diesel':
                user_params[0][i] = 1 if data.engine == 'Дизельный' else 0
            elif col == 'fuel_type_gasoline':
                user_params[0][i] = 1 if data.engine == 'Бензиновый' else 0
            elif col == 'fuel_type_hybrid':
                user_params[0][i] = 1 if data.engine == 'Гибридный' else 0

        logger.debug(f"User params created: {user_params[0]}")

        user_df = pd.DataFrame(data=user_params, columns=data_columns)
        logger.debug(f"User DataFrame created, shape: {user_df.shape}, columns: {list(user_df.columns)}")
        user_embedding = scaler.transform(user_df)
        logger.debug("User embedding created")

        distances, indices = knn.kneighbors(user_embedding)
        logger.debug(f"KNN neighbors found, indices: {indices}")

        valid_indices = [i for i in indices[0] if i < len(filtered_df)]
        if not valid_indices:
            logger.warning("No valid indices found for recommendations")
            return {'recommendation': []}

        recommendations = df.iloc[valid_indices].copy()
        recommendations['distance'] = distances[0][:len(valid_indices)]
        logger.debug("Recommendations prepared")

        recommendations = recommendations.sort_values('distance')
        logger.debug("Recommendations sorted by distance")

        for col in recommendations.columns:
            if recommendations[col].dtype in ['int64', 'float64']:
                recommendations[col] = recommendations[col].astype(object).replace({np.nan: None})

        logger.debug("Recommendations converted to JSON-compatible format")
        return {'recommendation': recommendations.to_dict(orient='records')}

    except Exception as e:
        logger.error(f"Unexpected error in create_recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")