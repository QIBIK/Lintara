# Используем стабильный и легкий образ Python на базе Debian Bookworm
FROM python:3.12-slim-bookworm

# Устанавливаем рабочую директорию
WORKDIR /app

# Системные зависимости (build-essential не требуется для текущих пакетов)
# Если понадобятся библиотеки с C-расширениями, можно будет вернуть.

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Создаем директории для загрузок и статики (на всякий случай)
RUN mkdir -p uploads static

# Открываем порт
EXPOSE 8000

# Команда для запуска приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
