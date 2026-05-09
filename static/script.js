document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const fileInput = document.getElementById('fileInput');
    const submitBtn = document.getElementById('submitBtn');
    const statusMessage = document.getElementById('statusMessage');
    const resultsBody = document.getElementById('resultsBody');
    const emptyMessage = document.getElementById('emptyMessage');
    const statsSummary = document.getElementById('statsSummary');

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

            renderResults(result);
        } catch (error) {
            showError(error.message);
        } finally {
            setLoading(false);
        }
    });

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        statusMessage.classList.toggle('hidden', !isLoading);
    }

    function clearResults() {
        resultsBody.innerHTML = '';
        statsSummary.innerHTML = '';
        statsSummary.classList.add('hidden');
        emptyMessage.classList.remove('hidden');
    }

    function renderResults(data) {
        const issues = data.issues || [];
        
        if (issues.length === 0) {
            emptyMessage.textContent = 'Ошибок не найдено! Отличный код.';
            return;
        }

        emptyMessage.classList.add('hidden');
        
        let criticalCount = 0;
        let warningCount = 0;

        issues.forEach(issue => {
            const row = document.createElement('tr');
            
            if (issue.severity === 'critical') criticalCount++;
            if (issue.severity === 'warning') warningCount++;

            const severityLabels = {
                'critical': 'КРИТИЧЕСКИЙ',
                'warning': 'ПРЕДУПРЕЖДЕНИЕ',
                'info': 'ИНФО'
            };

            row.innerHTML = `
                <td>${issue.file}</td>
                <td>${issue.line}:${issue.column}</td>
                <td><code>${issue.rule}</code></td>
                <td><span class="severity-${issue.severity}">${severityLabels[issue.severity] || issue.severity.toUpperCase()}</span></td>
                <td>
                    <div class="message-text">${issue.message}</div>
                    ${issue.line_text ? `<div class="code-snippet"><code>${escapeHtml(issue.line_text)}</code></div>` : ''}
                </td>
            `;
            resultsBody.appendChild(row);
        });

        // Статистика
        const filesCount = data.files_scanned || 0;
        statsSummary.innerHTML = `Проверено файлов: <strong>${filesCount}</strong>. Найдено: <strong>${criticalCount}</strong> критических, <strong>${warningCount}</strong> предупреждений.`;
        statsSummary.classList.remove('hidden');
    }

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
