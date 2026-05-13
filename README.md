
# 🛡️ Auditor Pro

**Auditor Pro** — современный, быстрый и многофункциональный инструмент для анализа кода, построенный на **FastAPI и HTML/CSS/JS frontend**. Обеспечивает глубокий анализ безопасности, сложности и линтинга прямо в браузере.

---

## 🌟 Особенности
| Функция | Описание |
|---|---|
| 🔍 **GitHub Repository Scanning** | Анализируйте публичные репозитории, просто вставив их URL |
| 📁 **Local File Uploads** | Поддержка **drag & drop** для локальных файлов и директорий |
| ⚙️ **Advanced Scanning Engines** | |
| &nbsp;&nbsp;🔒 **Semgrep Integration** | Глубокий семантический анализ для выявления сложных уязвимостей |
| &nbsp;&nbsp;📝 **YAML Linting** | Встроенная проверка `.yaml`/`.yml` через `yamllint` |
| 💻 **Interactive Code Viewer** | Встроенный `Monaco Editor` (тот же, что в VS Code) для навигации и подсветки проблем в браузере |
| 📊 **Rich Analysis Dashboard** | Статистика в реальном времени: `Security scores`, количество `Critical/Warning`, анализ цикломатической сложности |
| 🐳 **Containerized** | Полная поддержка **Docker** для быстрого деплоя и настройки |

---

## 📸 Демонстрация
![alt text](static/image.png)

---

## 🚀 Быстрый старт

### 📦 Предварительные требования
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### ⚡ Установка и запуск
```bash
# 1. Клонируйте репозиторий
git clone <your-repo-url>
cd project-02

# 2. Соберите и запустите контейнеры
docker-compose up --build -d

# 3. Откройте в браузере
open http://localhost:8000
```
📍 Приложение будет доступно по адресу: `http://localhost:8000`

---

## 🛠️ Стек технологий

| Категория          | Технологии                     |
| ------------------ | ------------------------------ |
| **Backend**        | `Python`, `FastAPI`, `Uvicorn` | 
| **Frontend**       | `HTML5`, `CSS`, `JavaScript`   |
| **Code Editor**    | `Monaco Editor`                |
| **Analysis Tools** | `Semgrep`, `yamllint`          |
| **Infrastructure** | `Docker`, `Docker Compose`     |

---

## 📁 Структура проекта
```text
├── docker-compose.yml     # Конфигурация Docker Compose
├── Dockerfile             # Определение контейнера для приложения
├── requirements.txt       # Python зависимости
├── scanner.py             # Основное FastAPI backend приложение
└── static/                # Frontend ресурсы
    ├── index.html         # Основной интерфейс
    ├── style.css          # Стили и анимации
    └── script.js          # Клиентская логика и API communication
```
