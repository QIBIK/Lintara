FROM python:3.12-slim-bookworm

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    curl \
    git \
    cppcheck \
    yamllint \
    default-jdk-headless \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g eslint@8.57.0 htmlhint stylelint stylelint-config-standard \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Go и staticcheck
RUN curl -fsSL https://go.dev/dl/go1.22.2.linux-amd64.tar.gz | tar -C /usr/local -xzf -
ENV PATH=$PATH:/usr/local/go/bin:/root/go/bin
RUN go install honnef.co/go/tools/cmd/staticcheck@latest

# Устанавливаем hadolint для Dockerfile
RUN curl -fsSL -o /usr/local/bin/hadolint \
    https://github.com/hadolint/hadolint/releases/download/v2.12.0/hadolint-Linux-x86_64 \
    && chmod +x /usr/local/bin/hadolint

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads static

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
