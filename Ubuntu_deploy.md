# Деплой сервиса рекомендаций автомобилей на облачный сервер Ubuntu

В данном файле представлен алгоритм деплоя сервиса рекомендаций автомобилей, написанного на Python. Он использует FastAPI для серверной части API, Streamlit для пользовательского интерфейса и Apache Airflow для парсинга данных. Проект полностью контейнеризирован с использованием Docker и управляется через Docker Compose. Включает директории для конфигураций (`configs`), DAG-файлов Airflow (`dags`), данных (`data`) и логов (`logs`).

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

Установите Docker и Docker Compose, если они ещё не установлены:

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

### 3. Создание директорий

Создайте необходимые директории:
```bash
mkdir -p configs dags data logs
```

### 4. Настройка прав доступа

Предоставьте права на чтение и запись для директорий:
```bash
sudo chmod -R 775 configs dags data logs
sudo chown -R $(whoami):$(whoami) configs dags data logs
```

**Примечание**: Права `775` обеспечивают доступ для владельца и группы, что безопаснее, чем `777`. Airflow в контейнере работает под пользователем `airflow` (UID 50000), поэтому убедитесь, что директории доступны.

### 5. Создание файла `airflow.cfg`

Ошибка `IsADirectoryError` возникает из-за некорректного монтирования `airflow.cfg` как директории. Чтобы избежать этого, создайте файл `airflow.cfg` на хосте:

```bash
touch airflow.cfg
chmod 664 airflow.cfg
```

Содержимое `airflow.cfg` можно оставить пустым или минимальным, так как Airflow создаст его автоматически при инициализации. Пример минимального `airflow.cfg`:

```ini
[core]
executor = SequentialExecutor
dags_folder = /opt/airflow/dags
base_log_folder = /opt/airflow/logs

[database]
sql_alchemy_conn = sqlite:////opt/airflow/data/airflow.db
```

Сохраните этот файл в корне проекта (`CarBotML/airflow.cfg`).

### 6. Проверка конфигурации Docker Compose

Проверьте синтаксис `docker-compose.yml`:
```bash
docker-compose config
```

Убедитесь, что `docker-compose.yml` монтирует `airflow.cfg` как файл, а не как директорию. Ваш текущий `docker-compose.yml` содержит строку:

```yaml
- ./airflow.cfg:/opt/airflow/airflow.cfg
```

Это правильно, если `airflow.cfg` — файл. Если в корне проекта есть папка с именем `airflow.cfg`, удалите её:
```bash
rm -rf ./airflow.cfg
```

### 7. Создание файла `gunicorn.conf.py`

Для работы сервиса FastAPI создайте файл `gunicorn.conf.py` в корне проекта:
```bash
touch gunicorn.conf.py
chmod 664 gunicorn.conf.py
```

Добавьте следующее содержимое:
```python
workers = 4
bind = "0.0.0.0:8000"
timeout = 120
```

Сохраните файл в корне проекта (`CarBotML/gunicorn.conf.py`). Это базовая конфигурация Gunicorn, которая задаёт 4 рабочих процесса и привязку к порту 8000.

### 8. Проверка данных

Убедитесь, что директория `data` доступна для записи:
```bash
sudo chmod -R 775 data
sudo chown -R $(whoami):$(whoami) data
```

### 9. Инициализация базы данных Airflow

В вашей версии Airflow (2.9.3) команда `airflow db init` заменена на `airflow db migrate`. Инициализируйте базу данных:

```bash
docker-compose run --rm airflow-webserver airflow db migrate
```

Эта команда создаст файл `airflow.db` в папке `data/` и настроит структуру базы данных. Если команда не выполняется, проверьте логи:
```bash
docker-compose logs airflow-webserver
```

### 10. Создание пользователя Airflow (опционально)

Для доступа к веб-интерфейсу Airflow создайте администратора:
```bash
docker-compose run --rm airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com
```

Введите пароль, когда будет предложено.

### 11. Запуск сервисов

Запустите все сервисы в фоновом режиме:
```bash
docker-compose up -d --build
```

### 12. Проверка статуса сервисов

Убедитесь, что все контейнеры запущены:
```bash
docker-compose ps
```

Вы должны увидеть четыре сервиса: `fastapi`, `streamlit`, `airflow-webserver`, `airflow-scheduler`.

### 13. Доступ к сервисам

- **Streamlit**: `http://<server-ip>:8501`
- **FastAPI**: `http://<server-ip>:8000` (документация: `http://<server-ip>:8000/docs`)
- **Airflow**: `http://<server-ip>:8080` (логин: `admin`, пароль: указанный при создании пользователя)

Замените `<server-ip>` на IP-адрес вашего сервера.

### 14. Просмотр логов

Для мониторинга:
```bash
docker-compose logs -f
```

Для конкретного сервиса:
```bash
docker-compose logs <service-name>
```

### 15. Остановка и удаление сервисов

Остановить контейнеры:
```bash
docker-compose stop
```

Удалить контейнеры и тома:
```bash
docker-compose down --volumes
```

### 16. Работа с виртуальным окружением (опционально)

Если требуется вне Docker:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Дополнительные замечания

- **Права доступа**: Используйте `775` вместо `777` для большей безопасности.
- **Airflow**: SQLite подходит для тестирования. Для продакшн рекомендуется PostgreSQL:
  - Добавьте сервис PostgreSQL в `docker-compose.yml`:
    ```yaml
    postgres:
      image: postgres:13
      environment:
        - POSTGRES_USER=airflow
        - POSTGRES_PASSWORD=airflow
        - POSTGRES_DB=airflow
      volumes:
        - postgres_data:/var/lib/postgresql/data
      ports:
        - "5432:5432"
    volumes:
      postgres_data:
    ```
  - Обновите `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`:
    ```yaml
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
    ```
  - Добавьте `psycopg2-binary` в `requirements.txt` или `Dockerfile.airflow`.
- **Логи**: Регулярно очищайте папку `logs`, чтобы избежать переполнения диска.

## Устранение неполадок

- **Ошибка `IsADirectoryError`**:
  - Убедитесь, что `./airflow.cfg` — файл, а не директория:
    ```bash
    ls -l ./airflow.cfg
    rm -rf ./airflow.cfg  # Если это директория
    touch ./airflow.cfg
    chmod 664 ./airflow.cfg
    ```
  - Проверьте монтирование в `docker-compose.yml`.
- **Airflow не запускается**:
  - Проверьте логи: `docker-compose logs airflow-webserver`.
  - Убедитесь, что `airflow.db` создан в `./data/`.
- **API/Streamlit не отвечает**:
  - Проверьте статус: `docker-compose ps`.
  - Убедитесь, что порты `8000` и `8501` открыты.

## Полезные команды Docker Compose

- Перезапуск: `docker-compose restart`
- Удаление ресурсов: `docker-compose down --rmi all --volumes --remove-orphans`

## Ресурсы

- [Документация Docker](https://docs.docker.com/)
- [Документация Docker Compose](https://docs.docker.com/compose/)
- [Документация Apache Airflow](https://airflow.apache.org/docs/)
- [Документация FastAPI](https://fastapi.tiangolo.com/)
- [Документация Streamlit](https://docs.streamlit.io/)