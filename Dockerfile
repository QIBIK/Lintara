FROM python:3.12-slim-bookworm

# Устанавливаем системные зависимости, включая Node.js для JS линтера
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y git nodejs yamllint \
    && npm install -g eslint@8.57.0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем hadolint для проверки Dockerfile
RUN curl -fsSL -o /usr/local/bin/hadolint \
    https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 \
    && chmod +x /usr/local/bin/hadolint

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python (bandit, radon, semgrep и т.д.)
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Создаем директории для загрузок и статики (на всякий случай)
RUN mkdir -p uploads static

# Открываем порт
EXPOSE 8000

# Команда для запуска приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
