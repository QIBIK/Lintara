# Auditor Pro

**Auditor Pro** is a modern, fast, and feature-rich code analysis tool built with FastAPI and a beautiful vanilla HTML/CSS/JS frontend. It provides deep insights into code security, complexity, and linting.

## ✨ Features

- **GitHub Repository Scanning**: Easily analyze public GitHub repositories by pasting their URLs.
- **Local File Uploads**: Drag & drop support for local file and directory analysis.
- **Advanced Scanning Engines**:
  - **Semgrep Integration**: Deep semantic code analysis for catching complex security vulnerabilities.
  - **YAML Linting**: Built-in support for analyzing `.yaml` and `.yml` files using `yamllint`.
- **Interactive Code Viewer**: Integrated Monaco Editor (the editor behind VS Code) for navigating code files and pinpointing issues directly within the browser.
- **Rich Analysis Dashboard**: Beautiful, real-time statistics showing:
  - Security scores
  - Critical and Warning issues count
  - Cyclomatic complexity analysis
- **Premium UI/UX**: Apple-inspired design with sleek glassmorphism, dynamic animations, and custom interactive elements (like the animated BB8 toggle switch).
- **Containerized**: Fully Dockerized for easy deployment and setup.

## 🚀 Getting Started

### Prerequisites
- [Docker](https://www.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)

### Installation & Execution

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd project-02
   ```

2. Build and run the application using Docker Compose:
   ```bash
   docker-compose up --build -d
   ```

3. Open your browser and navigate to:
   ```
   http://localhost:8000
   ```

## 🛠 Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **Frontend**: HTML5, Vanilla CSS3 (Custom Design System), JavaScript
- **Code Editor**: Monaco Editor
- **Analysis Tools**: Semgrep, yamllint
- **Infrastructure**: Docker, Docker Compose

## 📁 Project Structure

```
.
├── docker-compose.yml     # Docker composition configuration
├── Dockerfile             # Container definition for the app
├── requirements.txt       # Python dependencies
├── scanner.py             # Main FastAPI backend application
└── static/                # Frontend assets
    ├── index.html         # Main interface
    ├── style.css          # Premium styling and animations
    └── script.js          # Client-side logic and API communication
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.
