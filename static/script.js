document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsBody = document.getElementById('resultsBody');
    const emptyMessage = document.getElementById('emptyMessage');

    const resultsSection = document.getElementById('resultsSection');
    const statFiles = document.getElementById('statFiles');
    const statCritical = document.getElementById('statCritical');
    const statWarning = document.getElementById('statWarning');
    const statSecurity = document.getElementById('statSecurity');
    const statComplexity = document.getElementById('statComplexity');
    const filterBtns = document.querySelectorAll('.filter-btn');

    const gitForm = document.getElementById('gitForm');
    const gitUrl = document.getElementById('gitUrl');
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    const complexityPanel = document.getElementById('complexityPanel');
    const complexityList = document.getElementById('complexityList');

    let editor = null;
    let filesCodeCache = {};
    let complexityCache = [];
    const codeModal = document.getElementById('codeModal');
    const modalTitle = document.getElementById('modalTitle');
    const closeModal = document.getElementById('closeModal');

    // Инициализация Monaco
    require.config({ paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});
    require(['vs/editor/editor.main'], function() {});

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
            filesCodeCache = result.files_code || {};
            complexityCache = result.complexity || [];
            renderResults(result);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    // Git form
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
            filesCodeCache = result.files_code || {};
            complexityCache = result.complexity || [];
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
        complexityPanel.classList.add('hidden');
        complexityList.innerHTML = '';
    }

    function renderResults(data) {
        console.log(">>> [DEBUG] Данные от API:", data);
        
        const issues = data.issues || [];
        const scanErrors = data.scan_errors || [];
        const complexity = data.complexity || [];

        if (issues.length === 0 && scanErrors.length === 0 && complexity.length === 0) {
            console.warn(">>> [DEBUG] Результаты пусты!");
            emptyMessage.textContent = 'Ошибок не найдено! Отличный код. 🎉';
            resultsSection.classList.add('hidden');
            return;
        }

        emptyMessage.classList.add('hidden');
        resultsSection.classList.remove('hidden');

        let criticalCount = 0;
        let warningCount = 0;
        let securityCount = 0;

        resultsBody.innerHTML = '';

        issues.forEach(issue => {
            try {
                if (issue.severity === 'critical') criticalCount++;
                if (issue.severity === 'warning') warningCount++;
                if (issue.category === 'security') securityCount++;

                const row = createIssueRow(issue);
                resultsBody.appendChild(row);
            } catch (err) {
                console.error(">>> [DEBUG] Ошибка при отрисовке строки проблемы:", err, issue);
            }
        });

        // Dashboard
        statFiles.textContent = data.files_scanned || 0;
        statCritical.textContent = criticalCount;
        statWarning.textContent = warningCount;
        statSecurity.textContent = securityCount;

        // Complexity panel
        if (complexity && complexity.length > 0) {
            console.log(">>> [DEBUG] Обнаружена сложность:", complexity.length);
            complexityPanel.classList.remove('hidden');
            statComplexity.textContent = complexity.length;
            renderComplexity(complexity);
        } else {
            complexityPanel.classList.add('hidden');
            statComplexity.textContent = '0';
        }

        // Reset filters
        filterBtns.forEach(btn => btn.classList.remove('active'));
        document.querySelector('[data-severity="all"]').classList.add('active');
    }

    function createIssueRow(issue) {
        const row = document.createElement('tr');
        row.dataset.severity = issue.severity;
        row.dataset.category = issue.category || 'style';

        if (issue.category === 'security') {
            row.classList.add('is-security');
        }

        const severityLabels = {
            'critical': '🔴 КРИТИЧЕСКИЙ',
            'warning': '🟡 ПРЕДУПРЕЖДЕНИЕ',
            'info': '🔵 ИНФО'
        };

        const categoryLabels = {
            'style': { icon: '✏️', label: 'Стиль', css: 'category-style' },
            'security': { icon: '🛡️', label: 'Безопасность', css: 'category-security' },
            'docker': { icon: '🐳', label: 'Docker', css: 'category-docker' }
        };

        const cat = categoryLabels[issue.category] || categoryLabels['style'];

        row.innerHTML = `
            <td><span class="category-badge ${cat.css}">${cat.icon} ${cat.label}</span></td>
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

    function renderComplexity(items) {
        complexityList.innerHTML = '';
        // Sort by complexity descending
        const sorted = [...items].sort((a, b) => b.complexity - a.complexity);

        sorted.forEach(item => {
            const div = document.createElement('div');
            div.className = 'complexity-item';
            div.innerHTML = `
                <div class="complexity-rank rank-${item.rank}">${item.rank}</div>
                <div class="complexity-info">
                    <div class="complexity-name" title="${item.name}">${item.type === 'method' ? '🔹 ' : '⚡ '}${item.name}</div>
                    <div class="complexity-meta">${item.file} : строка ${item.line}</div>
                </div>
                <div class="complexity-score">${item.complexity}</div>
            `;
            div.addEventListener('click', () => {
                openCodeViewer(item.file, item.line, item.endline);
            });
            complexityList.appendChild(div);
        });
    }

    // Фильтрация
    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const severity = btn.dataset.severity;
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const rows = resultsBody.querySelectorAll('tr');
            rows.forEach(row => {
                if (severity === 'all') {
                    row.classList.remove('hidden');
                } else if (severity === 'security') {
                    // Filter by category for security
                    if (row.dataset.category === 'security') {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                } else {
                    if (row.dataset.severity === severity) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                }
            });
        });
    });

    function openCodeViewer(filename, line, endline) {
        const code = filesCodeCache[filename];
        if (!code) return;

        modalTitle.textContent = `Файл: ${filename}`;
        codeModal.classList.remove('hidden');

        let language = 'javascript';
        if (filename.endsWith('.py')) language = 'python';
        else if (filename.endsWith('.yaml') || filename.endsWith('.yml')) language = 'yaml';
        else if (filename.toLowerCase().includes('dockerfile')) language = 'dockerfile';
        else if (filename.endsWith('.tf')) language = 'hcl';

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

        // Highlight line / range and scroll
        if (line > 0) {
            const end = endline && endline > line ? endline : line;
            editor.revealLineInCenter(line);
            editor.setSelection({
                startLineNumber: line,
                startColumn: 1,
                endLineNumber: end,
                endColumn: 1000
            });

            // Highlight complex functions with red background in Monaco
            if (endline && endline > line) {
                editor.deltaDecorations([], [{
                    range: new monaco.Range(line, 1, endline, 1),
                    options: {
                        isWholeLine: true,
                        className: 'complexity-highlight',
                        glyphMarginClassName: 'complexity-glyph'
                    }
                }]);
            }
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

    // Inject Monaco CSS for complexity highlighting
    const monacoStyle = document.createElement('style');
    monacoStyle.textContent = `
        .complexity-highlight { background: rgba(251, 146, 60, 0.12) !important; }
        .complexity-glyph { background: #fb923c; width: 4px !important; margin-left: 3px; }
    `;
    document.head.appendChild(monacoStyle);
});
