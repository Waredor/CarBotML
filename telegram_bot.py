import os
import logging
import requests
import json
import telebot


from typing import Dict, Any
from langchain_gigachat import GigaChat
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel
from typing import TypedDict


TOKEN = "7796860635:AAGOKe1lT3doMcrtz22EUaELL3PdTO_zY4A"
bot = telebot.TeleBot(TOKEN)
bot.set_chat_menu_button(menu_button=telebot.types.MenuButtonDefault())
user_states = {}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class ModelResponse(BaseModel):
    price: int = 0
    odo: int = 0
    year: int = 0
    model: str = ""
    city: str = ""
    transmission: str = ""
    fuel_type: str = ""


model = GigaChat(
    credentials=os.getenv(
        "GIGACHAT_CREDENTIALS",
        "MDE5YTJiN2MtZjg4NC03MDJiLWE3NWMtNGRlZWE0NDU1ZDJlOmUxMWRkODZkLTI3NWYtNDVhMC1iMWQ0LTZmNzQ5OTYwMTAxYw=="
    ),
    model="GigaChat",
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
)

parser = JsonOutputParser(pydantic_object=ModelResponse)


class State(TypedDict):
    user_message: str
    output_json: dict
    approve: str


initial_prompt_template = PromptTemplate(
    template='''
    {format_instructions}

    ТЫ — СИСТЕМА ПАРСИНГА. ИЗВЛЕЧЬ ПАРАМЕТРЫ АВТОМОБИЛЯ ИЗ ТЕКСТА.
    НИКАКИХ ПОЯСНЕНИЙ, НИКАКОГО ТЕКСТА ВНЕ JSON.

    ПРАВИЛА:
    - Если параметр не указан → 0 (число) или "" (строка)
    - Синонимы: "до 750 тыс" → 750000, "автомат" → "АКПП", "бензин" → "Бензин"
    - Поддерживай русский язык

    ПРИМЕРЫ:
    Запрос: "Lada Vesta 2020, до 1.2 млн, Москва, АКПП"
    Ответ: {{"price": 1200000, "odo": 0, "year": 2020, "model": "Lada Vesta", "city": "Москва", "transmission": "АКПП", "fuel_type": "Бензин"}}

    ТЕПЕРЬ ТВОЙ ЗАПРОС:
    {user_message}

    ВЕРНИ ТОЛЬКО JSON.
    ''',
    input_variables=["user_message"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

modify_prompt_template = PromptTemplate(
    template='''
    {format_instructions}

    ТЫ — СИСТЕМА ПАРСИНГА. ИЗВЛЕЧЬ ПАРАМЕТРЫ АВТОМОБИЛЯ ИЗ ТЕКСТА.
    НИКАКИХ ПОЯСНЕНИЙ, НИКАКОГО ТЕКСТА ВНЕ JSON.

    ПРАВИЛА:
    - Каждый параметр имеет свой ключ: odo, price, year, transmission, city, model, fuel_type
    - Если параметр не указан → не добавлять ключ
    - Если сказано убрать параметр → по этому ключу должна возвращаться пустая строка для строковых переменных, 
        либо 0 для числовых.
    - Синонимы: "до 750 тыс" → 750000, "автомат" → "АКПП", "бензин" → "Бензин"
    - Поддерживай русский язык

    ПРИМЕРЫ:
    Запрос: "добавь город продажи Москва"
    Ответ: {{"city": "Москва"}}
    
    Запрос: "убери коробку передач"
    Ответ: {{"transmission": ""}}
    
    Запрос: "убери цену"
    Ответ: {{"price": 0}}

    ТЕПЕРЬ ТВОЙ ЗАПРОС:
    {user_message}

    ВЕРНИ ТОЛЬКО JSON.
    ''',
    input_variables=["user_message"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)


def initial_node(state: State) -> Dict[str, Any]:
    chain = initial_prompt_template | model | parser
    result = chain.invoke({"user_message": state["user_message"]})
    return {"output_json": result}

def modify_node(state: State) -> Dict[str, Any]:
    chain = modify_prompt_template | model | parser
    result = chain.invoke({"user_message": state["user_message"]})
    print(result)
    prev = state["output_json"]
    merged = prev | result
    return {"output_json": merged}


def run_node(chat_id, node_func) -> Dict[str, Any]:
    user = user_states[chat_id]
    state = user["state"]
    result = node_func(state)
    user["state"].update(result)
    return user["state"]


@bot.message_handler(commands=['start'])
def command_start(message):
    chat_id = message.chat.id
    user_states[chat_id] = {
        "step": "initial_prompt",
        "state": {"user_message": "", "output_json": {}, "approve": ""}
    }

    bot.send_message(
        message.chat.id,
        "Привет! Я помогу тебе подобрать автомобиль по требуемым параметрам.\n"
        "Введи параметры автомобиля:\n"
    )
    bot.register_next_step_handler(message, initial_response)


def initial_response(message):
    chat_id = message.chat.id
    user_states[chat_id]["state"]["user_message"] = message.text

    state = run_node(chat_id, initial_node)

    params_text = format_params(state["output_json"])
    bot.send_message(chat_id, f"Вот, что я понял:\n\n{params_text}\n\nВсе верно? (да/нет)")

    user_states[chat_id]["step"] = "approval_node"
    bot.register_next_step_handler(message, handle_approval)


def handle_approval(message):
    chat_id = message.chat.id
    answer = message.text.lower()
    state = user_states[chat_id]["state"]
    state['approve'] = answer

    if answer == 'да':
        raw_data = state["output_json"]
        # bot.send_message(
            # chat_id, f"Отлично! Вот итоговый JSON:\n{json.dumps(raw_data, indent=2, ensure_ascii=False)}"
        # )

        try:
            api_url = os.getenv('API_URL', 'http://fastapi:8000/create_recommendation')

            fuel_mapping = {
                "Бензин": "Бензиновый",
                "Дизель": "Дизельный",
                "Гибрид": "Гибридный",
                "Электро": "Гибридный",
            }

            transmission_mapping = {
                "АКПП": "АКПП",
                "Автомат": "АКПП",
                "Вариатор": "Вариатор",
                "Механика": "Механическая",
                "МКПП": "Механическая",
            }

            city_mapping = {
                "Хабаровск": "Хабаровск",
                "Владивосток": "Владивосток",
                "Благовещенск": "Благовещенск",
                # Добавь другие, если нужно
            }

            data_to_send = {
                "price": raw_data.get("price", 0),
                "odo": raw_data.get("odo", 0),
                "year": raw_data.get("year", 0),
                "city": city_mapping.get(raw_data.get("city", "").strip(), "Владивосток"),
                "engine": fuel_mapping.get(raw_data.get("fuel_type", "").strip(), "Бензиновый"),
                "transmission": transmission_mapping.get(raw_data.get("transmission", "").strip(), "АКПП"),
            }
            response = requests.post(api_url, json=data_to_send, proxies={"http": None, "https": None})
            response.raise_for_status()
            recommendations = response.json().get('recommendation', [])

            user_states.pop(chat_id, None)

            if not recommendations:
                logger.warning("No recommendations found")
                bot.send_message(chat_id, "Рекомендации не найдены.")
            else:
                top_recommendation = recommendations[0]
                logger.debug(f"Top recommendation: {top_recommendation}")

                car_model = top_recommendation.get("car_model", "Unknown")
                engine = top_recommendation.get("fuel_type", "Unknown")
                transmission = top_recommendation.get("transmission", "Unknown")
                price = int(top_recommendation.get("price", 0))
                odo = int(top_recommendation.get("odo", 0))
                year = int(top_recommendation.get("year", 0))

                city = ("Хабаровск" if top_recommendation.get("khv", 0) == 1
                        else "Владивосток" if top_recommendation.get("vdk", 0) == 1
                else "Благовещенск" if top_recommendation.get("blg", 0) == 1
                else "Unknown")

                bot.send_message(
                    chat_id,
                    f"Подобрали для вас идеальный авто: {car_model} {year} года выпуска с пробегом {odo} км, "
                    f"коробкой передач {transmission}, двигателем {engine} за {price} рублей в городе {city}"
                )

        except Exception:
            raise


    else:
        bot.send_message(chat_id, "Хорошо. Что нужно изменить?")
        user_states[chat_id]["step"] = "modify_parameters"
        bot.register_next_step_handler(message, handle_modify)


def handle_modify(message):
    chat_id = message.chat.id
    user_states[chat_id]["state"]["user_message"] = message.text

    state = run_node(chat_id, modify_node)

    params_text = format_params(state["output_json"])
    bot.send_message(chat_id, f"Обновленные параметры:\n\n{params_text}\n\nТеперь все верно? (да/нет)")

    user_states[chat_id]["step"] = "approval_node"
    bot.register_next_step_handler(message, handle_approval)


def format_params(data: dict) -> str:
    lines = []
    if data.get("model"): lines.append(f"Модель: {data['model']}")
    if data.get("price", 0) > 0: lines.append(f"Цена: {data['price']} ₽")
    if data.get("year", 0) > 0: lines.append(f"Год: {data['year']}")
    if data.get("odo", 0) > 0: lines.append(f"Пробег: {data['odo']} км")
    if data.get("city"): lines.append(f"Город: {data['city']}")
    if data.get("transmission"): lines.append(f"КПП: {data['transmission']}")
    if data.get("fuel_type"): lines.append(f"Двигатель: {data['fuel_type']}")
    return "\n".join(lines) if lines else "Параметры не найдены."


if __name__ == "__main__":
    bot.infinity_polling()