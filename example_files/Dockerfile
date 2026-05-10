# 1. Запуск от имени root (плохая практика)
FROM python:3.9

# 2. Использование последнего тега без версии
FROM node:latest

# 3. Отсутствие очистки кеша apt (увеличивает размер образа)
RUN apt-get update && apt-get install -y curl

# 4. Небезопасная команда
RUN pip install my-package --no-cache-dir

COPY . /app
WORKDIR /app

CMD ["python", "app.py"]
