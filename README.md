# Сервис рекомендаций автомобилей

Этот проект представляет собой сервис рекомендаций автомобилей, написанный на Python. Он использует FastAPI для серверной части API, Streamlit для пользовательского интерфейса и Apache Airflow для парсинга данных. Проект полностью контейнеризирован с использованием Docker и управляется через Docker Compose. Включает директории для конфигураций (`configs`), DAG-файлов Airflow (`dags`), данных (`data`) и логов (`logs`).

## Структура проекта

```
CarBotML/
├── venv/                    # Виртуальное окружение
├── configs/                 # Конфигурационные YAML-файлы проекта
├── dags/                    # DAG-файлы для Apache Airflow для парсинга данных
├── data/                    # Данные сервиса
├── logs/                    # Файлы логов, генерируемых Airflow и другими сервисами
├── service.py               # Скрипт FastAPI-сервера для генерации рекомендаций
├── app.py                   # Скрипт Streamlit-приложения для пользовательского интерфейса
├── Dockerfile.fastapi       # Dockerfile для сборки контейнера FastAPI
├── Dockerfile.streamlit     # Dockerfile для сборки контейнера Streamlit
├── Dockerfile.airflow       # Dockerfile для сборки контейнеров Airflow
├── docker-compose.yml       # Конфигурация Docker Compose для управления сервисами
├── requirements.txt         # Файл с Python-зависимостями
├── README.md                # Документация проекта
└── .gitignore               # Файл .gitignore
```

## Требования

Для запуска проекта на виртуальном сервере с Ubuntu необходимы:

- **Docker**: Версия 20.10 или выше.
- **Docker Compose**: Версия 2.0 или выше.
- **Git**: Для клонирования репозитория.
- **Python 3.11**: Опционально, если требуется работа с виртуальным окружением вне Docker.

## Инструкция по установке и запуску

Следуйте этим шагам, чтобы настроить и запустить проект на виртуальном сервере с Ubuntu.

### 1. Клонирование репозитория

Склонируйте репозиторий на сервер:

```bash
git clone <repository-url>
cd <repository-directory>
```

Замените `<repository-url>` на URL вашего репозитория, а `<repository-directory>` — на имя папки проекта.

### 2. Установка Docker и Docker Compose

Если Docker и Docker Compose еще не установлены, выполните:

```bash
# Обновление индекса пакетов
sudo apt update

# Установка Docker
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

Проверьте установку:

```bash
docker --version
docker-compose --version
```

### 3. Настройка прав доступа

Для корректной работы Docker Compose предоставьте права на чтение и запись для директорий `configs`, `dags`, `data` и `logs`:

```bash
sudo chmod -R 777 configs dags data logs
```

**Примечание**: Использование `777` предоставляет полный доступ. Для продакшн-окружения рекомендуется использовать более строгие права (например, `775`) и назначить владельцем пользователя, под которым работает Docker.

### 4. Проверка конфигурации Docker Compose

Убедитесь, что файл `docker-compose.yml` валиден:

```bash
docker-compose config
```

Эта команда проверяет синтаксис и выводит обработанную конфигурацию.

### 5. Создание директорий

Убедитесь, что все необходимые директории существуют:

```bash
mkdir -p configs dags data logs
```

Если в `configs` или `dags` должны быть определенные файлы (например, YAML-конфигурации или DAG-файлы), убедитесь, что они созданы или скопированы в соответствующие директории.

### 6. Проверка данных

Убедитесь, что в директории `data` находятся необходимые файлы:
- `preprocessed_data.csv`
- `annotated_data.csv`
- `x_scaler.pkl`
- `data_columns.pkl`

Эти файлы должны быть доступны для чтения и записи. Выполните:

```bash
sudo chmod -R 777 data
```

### 7. Инициализация базы данных Airflow

Поскольку Airflow запускается впервые, необходимо инициализировать базу данных `airflow.db`, которая будет храниться в папке `data/`. Выполните следующую команду:

```bash
docker-compose run --rm airflow-webserver airflow db init
```

Эта команда создаст файл `airflow.db` в папке `data/` и настроит начальную структуру базы данных для Airflow.

### 8. Запуск сервисов

Запустите все сервисы (FastAPI, Streamlit, Airflow) в фоновом режиме:

```bash
docker-compose up -d --build
```

- Флаг `--build` пересобирает образы, если они изменились.
- Флаг `-d` запускает контейнеры в фоновом режиме.

### 9. Проверка статуса сервисов

Проверьте, что все контейнеры запущены:

```bash
docker-compose ps
```

Вы должны увидеть четыре сервиса: `fastapi`, `streamlit`, `airflow-webserver` и `airflow-scheduler`.

### 10. Доступ к сервисам

- **Streamlit**: Откройте браузер и перейдите по адресу `http://<server-ip>:8501` для доступа к пользовательскому интерфейсу.
- **FastAPI**: API доступен по адресу `http://<server-ip>:8000`. Документация API доступна по адресу `http://<server-ip>:8000/docs`.
- **Airflow**: Веб-интерфейс Airflow доступен по адресу `http://<server-ip>:8080`. По умолчанию используется `SequentialExecutor` с SQLite базой данных (`data/airflow.db`).

Замените `<server-ip>` на IP-адрес вашего сервера.

### 11. Просмотр логов

Для отладки или мониторинга используйте:

```bash
docker-compose logs
```

Для просмотра логов в реальном времени:

```bash
docker-compose logs -f
```

Для логов конкретного сервиса:

```bash
docker-compose logs <service-name>
```

Например, `docker-compose logs fastapi`.

### 12. Остановка и удаление сервисов

Чтобы остановить и удалить контейнеры:

```bash
docker-compose down
```

Для удаления также томов:

```bash
docker-compose down --volumes
```

### 13. Работа с виртуальным окружением (опционально)

Если требуется работать с проектом вне Docker, активируйте виртуальное окружение:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Примечание**: Для запуска сервисов вне Docker потребуется дополнительная настройка, например, запуск FastAPI через `uvicorn` или Airflow вручную.

## Дополнительные замечания

- **Права доступа**: Убедитесь, что файлы в папке `data` (включая `airflow.db`) доступны для чтения и записи контейнерами. Если возникают ошибки, проверьте права с помощью `ls -l`.
- **Airflow**: SQLite используется для простоты, и база данных хранится в `data/airflow.db`. Для продакшн-окружения рекомендуется PostgreSQL или MySQL. Измените `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN` в `docker-compose.yml` для другой базы данных.
- **Переменные окружения**: Переменная `API_URL` в сервисе `streamlit` в `docker-compose.yml` должна указывать на `http://fastapi:8000/create_recommendation`.
- **Логи**: Логи Airflow сохраняются в папке `logs`. Регулярно очищайте их, чтобы избежать переполнения диска.
- **Gunicorn**: FastAPI запускается через `gunicorn`. Если требуется изменить настройки, отредактируйте `gunicorn.conf.py` или создайте его.

## Устранение неполадок

- **Контейнеры не запускаются**: Проверьте логи (`docker-compose logs`) и убедитесь, что все файлы данных и конфигурации существуют.
- **Ошибка доступа к файлам**: Проверьте права доступа (`ls -l`) и установите `chmod 777` для нужных директорий.
- **API не отвечает**: Убедитесь, что сервис `fastapi` запущен (`docker-compose ps`) и порт `8000` открыт.
- **Airflow не работает**: Проверьте, что база данных `airflow.db` создана в папке `data/` и инициализирована (`docker-compose run --rm airflow-webserver airflow db init`).

## Полезные команды Docker Compose

- Перезапуск сервисов:
  ```bash
  docker-compose restart
  ```
- Остановка без удаления:
  ```bash
  docker-compose stop
  ```
- Запуск остановленных сервисов:
  ```bash
  docker-compose start
  ```
- Удаление неиспользуемых ресурсов:
  ```bash
  docker-compose down --rmi all --volumes --remove-orphans
  ```

## Ресурсы

- [Документация Docker](https://docs.docker.com/)
- [Документация Docker Compose](https://docs.docker.com/compose/)
- [Документация Apache Airflow](https://airflow.apache.org/docs/)
- [Документация FastAPI](https://fastapi.tiangolo.com/)
- [Документация Streamlit](https://docs.streamlit.io/)