document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsBody = document.getElementById('resultsBody');
    const emptyMessage = document.getElementById('emptyMessage');
    
    // Новые элементы для Dashboard и фильтров
    const resultsSection = document.getElementById('resultsSection');
    const statFiles = document.getElementById('statFiles');
    const statCritical = document.getElementById('statCritical');
    const statWarning = document.getElementById('statWarning');
    const filterBtns = document.querySelectorAll('.filter-btn');
    
    // Новые элементы для Git
    const gitForm = document.getElementById('gitForm');
    const gitUrl = document.getElementById('gitUrl');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Переменные для Monaco и кэша кода
    let editor = null;
    let filesCodeCache = {};
    const codeModal = document.getElementById('codeModal');
    const modalTitle = document.getElementById('modalTitle');
    const closeModal = document.getElementById('closeModal');

    // Инициализация Monaco
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {
        // Редактор инициализируется лениво при первом открытии
    });

    // Переключение вкладок
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.add('hidden'));
            
            btn.classList.add('active');
            document.getElementById(`${btn.dataset.tab}Tab`).classList.remove('hidden');
        });
    });

    // Drag & Drop
    const dropZone = document.querySelector('.upload-section');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.add('highlight'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => dropZone.classList.remove('highlight'), false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
        }
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!fileInput.files.length) return;

        const formData = new FormData();
        for (let i = 0; i < fileInput.files.length; i++) {
            formData.append('files', fileInput.files[i]);
        }

        // Состояние загрузки
        setLoading(true);
        clearResults();

        try {
            const response = await fetch('/api/scan', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Ошибка при сканировании');
            }

            // Сохраняем код в кэш
            filesCodeCache = result.files_code || {};
            renderResults(result);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    // Обработка Git формы
    gitForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = gitUrl.value.trim();
        if (!url) return;

        setLoading(true);
        clearResults();

        try {
            const response = await fetch('/api/scan/git', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: url })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Ошибка при сканировании репозитория');
            }

            // Сохраняем код в кэш
            filesCodeCache = result.files_code || {};
            renderResults(result);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        const gitSubmitBtn = document.getElementById('gitSubmitBtn');
        if (gitSubmitBtn) gitSubmitBtn.disabled = isLoading;
        statusMessage.classList.toggle('hidden', !isLoading);
    }

    function clearResults() {
        resultsBody.innerHTML = '';
        if (resultsSection) resultsSection.classList.add('hidden');
        emptyMessage.classList.remove('hidden');
    }

    function renderResults(data) {
        const issues = data.issues || [];
        const scanErrors = data.scan_errors || [];
        
        if (issues.length === 0 && scanErrors.length === 0) {
            emptyMessage.textContent = 'Ошибок не найдено! Отличный код.';
            resultsSection.classList.add('hidden');
            return;
        }

        emptyMessage.classList.add('hidden');
        resultsSection.classList.remove('hidden');
        
        let criticalCount = 0;
        let warningCount = 0;

        // Очистка таблицы
        resultsBody.innerHTML = '';

        issues.forEach(issue => {
            if (issue.severity === 'critical') criticalCount++;
            if (issue.severity === 'warning') warningCount++;
            
            const row = createIssueRow(issue);
            resultsBody.appendChild(row);
        });

        // Обновляем дашборд
        statFiles.textContent = data.files_scanned || 0;
        statCritical.textContent = criticalCount;
        statWarning.textContent = warningCount;
        
        // Сброс фильтров
        filterBtns.forEach(btn => btn.classList.remove('active'));
        document.querySelector('[data-severity="all"]').classList.add('active');
    }

    function createIssueRow(issue) {
        const row = document.createElement('tr');
        row.dataset.severity = issue.severity;
        
        const severityLabels = {
            'critical': '🔴 КРИТИЧЕСКИЙ',
            'warning': '🟡 ПРЕДУПРЕЖДЕНИЕ',
            'info': '🔵 ИНФО'
        };

        row.innerHTML = `
            <td>${issue.file}</td>
            <td>${issue.line > 0 ? issue.line : '-'}:${issue.column > 0 ? issue.column : '-'}</td>
            <td><code>${issue.rule}</code></td>
            <td><span class="severity-${issue.severity}">${severityLabels[issue.severity] || issue.severity.toUpperCase()}</span></td>
            <td>
                <div class="message-text">${issue.message}</div>
                ${issue.line_text ? `<div class="code-snippet"><code>${escapeHtml(issue.line_text)}</code></div>` : ''}
            </td>
        `;

        row.addEventListener('click', () => {
            openCodeViewer(issue.file, issue.line);
        });

        return row;
    }

    // Логика фильтрации
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const severity = btn.dataset.severity;
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const rows = resultsBody.querySelectorAll('tr');
            rows.forEach(row => {
                if (severity === 'all' || row.dataset.severity === severity) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        });
    });

    function openCodeViewer(filename, line) {
        const code = filesCodeCache[filename];
        if (!code) return;

        modalTitle.textContent = `Файл: ${filename}`;
        codeModal.classList.remove('hidden');

        let language = 'javascript';
        if (filename.endsWith('.py')) language = 'python';
        else if (filename.endsWith('.yaml') || filename.endsWith('.yml')) language = 'yaml';

        if (!editor) {
            editor = monaco.editor.create(document.getElementById('monaco-container'), {
                value: code,
                language: language,
                theme: 'vs-dark',
                automaticLayout: true,
                readOnly: true,
                fontSize: 14
            });
        } else {
            const model = monaco.editor.createModel(code, language);
            editor.setModel(model);
        }

        // Подсвечиваем строку и скроллим к ней
        if (line > 0) {
            editor.revealLineInCenter(line);
            editor.setSelection({
                startLineNumber: line,
                startColumn: 1,
                endLineNumber: line,
                endColumn: 1000
            });
        }
    }

    closeModal.addEventListener('click', () => {
        codeModal.classList.add('hidden');
    });

    window.addEventListener('click', (e) => {
        if (e.target === codeModal) codeModal.classList.add('hidden');
    });


    function showError(message) {
        emptyMessage.classList.remove('hidden');
        emptyMessage.innerHTML = `<span style="color: var(--critical)">Ошибка: ${message}</span>`;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
