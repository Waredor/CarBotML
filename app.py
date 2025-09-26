import os
import requests
import streamlit as st
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


logger.debug(f"Initial environment proxies: HTTP_PROXY={os.environ.get('HTTP_PROXY')}, HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")


os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
logger.debug("Cleared HTTP_PROXY and HTTPS_PROXY from environment")

st.title("Сервис рекомендаций авто по пользовательским параметрам")

with st.form("Заполните форму ниже для подбора лучшего варианта авто специально для вас"):
    price = st.number_input("Цена автомобиля", min_value=10000)
    odo = st.number_input("Пробег автомобиля", min_value=0)
    year = st.number_input("Год выпуска авто", min_value=1991)
    city = st.selectbox("Укажите город продажи", ("Хабаровск", "Владивосток", "Благовещенск"))
    transmission = st.selectbox("Укажите тип трансмиссии", ("АКПП", "Вариатор", "Механическая"))
    engine = st.selectbox("Укажите тип двигателя", ("Бензиновый", "Дизельный", "Гибридный"))
    submit = st.form_submit_button("Рассчитать стоимость авто")

if submit:
    data = {
        "price": int(price),
        "odo": int(odo),
        "year": int(year),
        "city": str(city),
        "engine": str(engine),
        "transmission": str(transmission)
    }

    logger.debug(f"Form data: {data}")
    logger.debug(f"Form data types: {[(k, type(v)) for k, v in data.items()]}")

    try:
        api_url = os.getenv('API_URL', 'http://fastapi:8000/create_recommendation')
        logger.debug(f"Sending request to API: {api_url}")
        logger.debug(f"Request data: {data}")
        logger.debug(f"Environment proxies after clearing: {requests.utils.getproxies()}")
        response = requests.post(api_url, json=data, proxies={"http": None, "https": None})
        response.raise_for_status()
        logger.debug(f"API response status: {response.status_code}")
        logger.debug(f"API response content: {response.text}")
        recommendations = response.json().get('recommendation', [])
        logger.debug(f"Recommendations received: {len(recommendations)} items")

        if not recommendations:
            logger.warning("No recommendations found")
            st.write("Рекомендации не найдены.")
        else:
            top_recommendation = recommendations[0]
            logger.debug(f"Top recommendation: {top_recommendation}")

            model = top_recommendation.get("car_model", "Unknown")
            engine = top_recommendation.get("fuel_type", "Unknown")
            transmission = top_recommendation.get("transmission", "Unknown")
            price = int(top_recommendation.get("price", 0))
            odo = int(top_recommendation.get("odo", 0))
            year = int(top_recommendation.get("year", 0))

            city = ("Хабаровск" if top_recommendation.get("khv", 0) == 1
                    else "Владивосток" if top_recommendation.get("vdk", 0) == 1
                    else "Благовещенск" if top_recommendation.get("blg", 0) == 1
                    else "Unknown")

            st.write(f"Подобрали для вас идеальный авто: {model} {year} года выпуска с пробегом {odo} км, "
                     f"коробкой передач {transmission}, двигателем {engine} за {price} рублей в городе {city}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request error: {e}")
        st.error(f"Ошибка при запросе к API: {e}")