import requests
import os

from langchain_gigachat import GigaChat
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from typing import Any, Dict


class State(Dict[str, Any]):
    user_message: str
    output_json: dict
    approve: str


class ModelResponse(BaseModel):
    price: int
    odo: int
    year: int
    model: str
    city: str
    transmission: str
    fuel_type: str

model = GigaChat(
    credentials="MDE5YTJiN2MtZjg4NC03MDJiLWE3NWMtNGRlZWE0NDU1ZDJlOmUxMWRkODZkLTI3NWYtNDVhMC1iMWQ0LTZmNzQ5OTYwMTAxYw==",
    model="GigaChat",
    scope="GIGACHAT_API_PERS",
    verify_ssl_certs=False,
)

parser = JsonOutputParser(pydantic_object=ModelResponse)


def initial_prompt(state: Dict[str, Any]) -> Dict[str, Any]:
    prompt = PromptTemplate(
        template=(
            '''
            {format_instructions}

            ТЫ — СИСТЕМА ПАРСИНГА. ТВОЯ ЗАДАЧА — ИЗВЛЕЧЬ ПАРАМЕТРЫ АВТОМОБИЛЯ ИЗ ТЕКСТА.
            НИКАКИХ ПОЯСНЕНИЙ, НИКАКИХ КОММЕНТАРИЕВ, НИКАКОГО ТЕКСТА ВНЕ JSON.

            ПРАВИЛА:
            - Если параметр не указан → 0 (число) или "" (строка)
            - Синонимы: "до 750 тыс" → 750000, "автомат" → "АКПП", "бензин" → "Бензин"
            - Поддерживай русский язык

            ПРИМЕРЫ:
            Запрос: "Lada Vesta 2020, до 1.2 млн, Москва, АКПП"
            Ответ: {{"price": 1200000, "odo": 0, "year": 2020, "model": "Lada Vesta", "city": "Москва", 
            "transmission": "АКПП", "fuel_type": "Бензин"}}

            Запрос: "цена до 750000 пробег до 250000"
            Ответ: {{"price": 750000, "odo": 250000, "year": 0, "model": "", "city": "", 
            "transmission": "", "fuel_type": ""}}

            ТЕПЕРЬ ТВОЙ ЗАПРОС:
            {user_message}

            ВЕРНИ ТОЛЬКО JSON. НИ СЛОВА БОЛЬШЕ.
            '''
        ),
        input_variables=["user_message"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | model | parser
    out = chain.invoke({"user_message": state["user_message"]})
    return {"output_json": out}


def ask_approval(state: Dict[str, Any]) -> Dict[str, Any]:
    output_json = state["output_json"]
    params = []
    if output_json['model'] != '':
        model = f"Модель авто: {output_json['model']}"
        params.append(model)
    if output_json['price'] != 0:
        price = f"Цена: {output_json['price']}"
        params.append(price)
    if output_json['year'] != 0:
        year = f"Год выпуска: {output_json['year']}"
        params.append(year)
    if output_json['odo'] != 0:
        odo = f"Пробег: {output_json['odo']}"
        params.append(odo)
    if output_json['city'] != '':
        city = f"Город продажи: {output_json['city']}"
        params.append(city)
    if output_json['transmission'] != '':
        transmission = f"Тип коробки передач: {output_json['transmission']}"
        params.append(transmission)
    if output_json['fuel_type'] != '':
        fuel_type = f"Тип двигателя: {output_json['fuel_type']}"
        params.append(fuel_type)

    print("Вот ваши параметры:\n")
    for param in params:
        print(param)
    print("Все верно? {да/нет)\n")
    out = str(input()).lower()
    return {"approve": out}


def modify_parameters(state: Dict[str, Any]) -> Dict[str, Any]:
    prompt = PromptTemplate(
        template=(
            '''
            {format_instructions}

            ТЫ — СИСТЕМА ПАРСИНГА. ТВОЯ ЗАДАЧА — ИЗВЛЕЧЬ ПАРАМЕТРЫ АВТОМОБИЛЯ ИЗ ТЕКСТА.
            НИКАКИХ ПОЯСНЕНИЙ, НИКАКИХ КОММЕНТАРИЕВ, НИКАКОГО ТЕКСТА ВНЕ JSON. 

            ПРАВИЛА:
            - Каждый параметр имеет свой ключ в выходном JSON: пробег - odo, цена - price, год выпуска - year,
                тип коробки передач - transmission, город продажи - city, модель - model, тип двигателя - fuel type
            - Если параметр не указан → не добавлять ключ этого параметра в выходной словарь
            - Синонимы: "до 750 тыс" → 750000, "автомат" → "АКПП", "бензин" → "Бензин"
            - Поддерживай русский язык

            ПРИМЕРЫ:
            Запрос: "Lada Vesta 2020, до 1.2 млн, Москва, АКПП"
            Ответ: {{"price": 1200000, "year": 2020, "model": "Lada Vesta", "city": "Москва", 
            "transmission": "АКПП"}}

            Запрос: "цена до 750000 пробег до 250000"
            Ответ: {{"price": 750000, "odo": 250000}}
            
            Запрос: "добавь город продажи Москва"
            Ответ: {{"city": "Москва"}}

            ТЕПЕРЬ ТВОЙ ЗАПРОС:
            {user_message}

            ВЕРНИ ТОЛЬКО JSON. НИ СЛОВА БОЛЬШЕ.
            '''
        ),
        input_variables=["user_message"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    print("Введите сообщение:\n")
    message = str(input())
    state["user_message"] = message

    chain = prompt | model | parser
    out = chain.invoke({"user_message": state["user_message"]})
    prev_json = state["output_json"]
    out = prev_json | out
    return {"output_json": out}

workflow = StateGraph(State)
workflow.add_node("initial_prompt", initial_prompt)
workflow.add_node("approval_node", ask_approval)
workflow.add_node("modify_parameters", modify_parameters)

workflow.add_edge(START, "initial_prompt")
workflow.add_edge("initial_prompt", "approval_node")
workflow.add_edge("modify_parameters", "approval_node")

def route(state: Dict[str, Any]) -> str:
    return END if str(state["approve"]).lower() == "да" else "modify"

workflow.add_conditional_edges(
    "approval_node",
    route,
    {"modify": "modify_parameters", END: END}
)


graph = workflow.compile()

graph_png = graph.get_graph(xray=True)
png_bytes = graph_png.draw_mermaid_png()
with open("car_agent.png", "wb") as f:
    f.write(png_bytes)

if __name__ == '__main__':
    print("Введите сообщение:\n")
    user_message = input()
    output = graph.invoke({"user_message": user_message})
    data = output["output_json"]
    print("Выходной JSON:\n")
    print(data)

    api_url = os.getenv('API_URL', 'http://fastapi:8000/create_recommendation')
    response = requests.post(api_url, json=data, proxies={"http": None, "https": None})
    response.raise_for_status()