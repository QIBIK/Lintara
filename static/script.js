let editor = null;
let currentFilesCode = {};
let allIssues = [];
let allComplexity = [];

document.addEventListener('DOMContentLoaded', () => {
    // --- Tabs ---
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.add('hidden'));
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab + 'Tab').classList.remove('hidden');
        });
    });

    // --- Forms ---
    const gitForm = document.getElementById('gitForm');
    const uploadForm = document.getElementById('uploadForm');
    const statusOverlay = document.getElementById('statusMessage');
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');

    dropZone.addEventListener('click', () => fileInput.click());
    
    ['dragover', 'dragenter'].forEach(evt => {
        dropZone.addEventListener(evt, (e) => {
            e.preventDefault();
            dropZone.classList.add('highlight');
        });
    });

    ['dragleave', 'dragend', 'drop'].forEach(evt => {
        dropZone.addEventListener(evt, () => {
            dropZone.classList.remove('highlight');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileInput.files = e.dataTransfer.files;
        updateFileStatus();
    });

    fileInput.addEventListener('change', updateFileStatus);

    function updateFileStatus() {
        const p = dropZone.querySelector('p');
        p.innerHTML = `Выбрано: <b>${fileInput.files.length}</b>`;
    }

    gitForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = document.getElementById('gitUrl').value;
        await startScan('/api/scan/git', { url });
    });

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files.length) return;
        const fd = new FormData();
        for (let f of fileInput.files) fd.append('files', f);
        await startScan('/api/scan', fd, true);
    });

    async function startScan(endpoint, body, isFormData = false) {
        statusOverlay.classList.remove('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        try {
            const options = { method: 'POST', body: isFormData ? body : JSON.stringify(body) };
            if (!isFormData) options.headers = { 'Content-Type': 'application/json' };
            const resp = await fetch(endpoint, options);
            const data = await resp.json();
            if (data.status === 'success') {
                allIssues = data.issues || [];
                currentFilesCode = data.files_code || {};
                renderDashboard(data);
            }
        } catch (err) {
            console.error(err);
        } finally {
            statusOverlay.classList.add('hidden');
        }
    }

    function renderDashboard(data) {
        document.getElementById('resultsSection').classList.remove('hidden');
        allIssues = data.issues || [];
        allComplexity = data.complexity || [];

        let crit = 0, warn = 0, sec = 0;
        allIssues.forEach(i => {
            if (i.severity === 'critical') crit++;
            if (i.severity === 'warning') warn++;
            if (i.category === 'security') sec++;
        });

        document.getElementById('statCritical').textContent = crit;
        document.getElementById('statWarning').textContent = warn;
        document.getElementById('statSecurity').textContent = sec;

        let score = 100 - (crit * 15) - (warn * 3) - (allComplexity.length * 7);
        score = Math.max(0, score);
        updateHealthScore(score);

        // По умолчанию показываем все проблемы
        renderIssues(allIssues);
        
        // Сбрасываем активную пилюлю на "Все"
        document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        document.querySelector('.pill[data-severity="all"]').classList.add('active');
    }

    function updateHealthScore(score) {
        const fill = document.getElementById('healthScoreFill');
        const text = document.getElementById('healthScoreText');
        const duration = 1200;
        const start = performance.now();

        function animate(time) {
            const elapsed = time - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = progress * (2 - progress);
            
            const cur = Math.floor(eased * score);
            text.textContent = cur;
            fill.style.strokeDashoffset = 283 - (283 * (eased * score) / 100);

            if (cur >= 90) fill.style.stroke = "#32d74b";
            else if (cur >= 50) fill.style.stroke = "#ff9f0a";
            else fill.style.stroke = "#ff453a";

            if (progress < 1) requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
    }

    function renderIssues(issues) {
        const container = document.getElementById('issuesList');
        container.innerHTML = '';

        if (issues.length === 0) {
            container.innerHTML = '<div class="empty-state"><span class="icon">🎉</span><h3>Код идеален!</h3><p>Никаких ошибок не обнаружено.</p></div>';
            return;
        }

        issues.forEach(issue => {
            const card = document.createElement('div');
            card.className = 'issue-card';
            card.dataset.severity = issue.severity;
            card.dataset.category = issue.category;

            let badgeClass = 'badge-warning';
            let label = 'Warning';

            if (issue.category === 'security') {
                badgeClass = 'badge-security';
                label = 'Security';
            } else if (issue.severity === 'critical') {
                badgeClass = 'badge-critical';
                label = 'Critical';
            }

            card.innerHTML = `
                <div class="issue-badge ${badgeClass}">${label}</div>
                <div class="issue-info">
                    <h4>${issue.message}</h4>
                    <p>${issue.file}</p>
                </div>
                <div class="issue-line">L:${issue.line}</div>
            `;
            card.addEventListener('click', () => openCodeViewer(issue.file, issue.line, issue.severity === 'critical'));
            container.appendChild(card);
        });
    }

    function renderComplexityTab() {
        const container = document.getElementById('issuesList');
        container.innerHTML = `
            <div class="complexity-info">
                <h4>Сложность функций (Cyclomatic Complexity)</h4>
                <div class="complexity-legend">
                    <div class="legend-item"><span class="rank-badge rank-a">A</span> Низкая (1-5)</div>
                    <div class="legend-item"><span class="rank-badge rank-b">B</span> Средняя (6-10)</div>
                    <div class="legend-item"><span class="rank-badge rank-c">C</span> Высокая (11-20)</div>
                    <div class="legend-item"><span class="rank-badge rank-d">D</span> Очень высокая (21-30)</div>
                    <div class="legend-item"><span class="rank-badge rank-e">E</span> Экстремальная (31-40)</div>
                    <div class="legend-item"><span class="rank-badge rank-f">F</span> Опасная (41+)</div>
                </div>
            </div>
            <div id="complexityItems" class="compact-complexity"></div>
        `;

        const itemsContainer = document.getElementById('complexityItems');
        if (allComplexity.length === 0) {
            itemsContainer.innerHTML = '<p style="color: var(--text-secondary)">Данные о сложности отсутствуют для выбранных файлов.</p>';
            return;
        }

        allComplexity.sort((a, b) => b.complexity - a.complexity).forEach(item => {
            const div = document.createElement('div');
            div.className = 'complexity-item';
            div.innerHTML = `<span>${item.name}</span><span class="rank-badge rank-${item.rank.toLowerCase()}">${item.rank}</span>`;
            div.addEventListener('click', () => openCodeViewer(item.file, item.line, false));
            itemsContainer.appendChild(div);
        });
    }

    const modal = document.getElementById('codeModal');
    const closeBtn = document.getElementById('closeModal');
    closeBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.add('hidden'); });

    function openCodeViewer(filename, line, isCritical) {
        modal.classList.remove('hidden');
        document.getElementById('modalTitle').textContent = filename;
        const code = currentFilesCode[filename] || "// Код недоступен";
        const ext = filename.split('.').pop().toLowerCase();
        const langMap = { 
            'py': 'python', 'js': 'javascript', 'go': 'go', 
            'cpp': 'cpp', 'c': 'cpp', 'css': 'css', 
            'html': 'html', 'java': 'java', 'yaml': 'yaml', 'yml': 'yaml' 
        };
        const lang = langMap[ext] || 'plaintext';

        if (!editor) {
            require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
            require(['vs/editor/editor.main'], function () {
                editor = monaco.editor.create(document.getElementById('monaco-container'), {
                    value: code, language: lang, theme: 'vs-dark', automaticLayout: true, readOnly: true, minimap: { enabled: false }
                });
                editor._decorationsCollection = editor.createDecorationsCollection();
                setTimeout(() => focusOnLine(line, isCritical), 50);
            });
        } else {
            editor.setValue(code);
            monaco.editor.setModelLanguage(editor.getModel(), lang);
            setTimeout(() => focusOnLine(line, isCritical), 50);
        }
    }

    function focusOnLine(line, isCritical) {
        if (!editor) return;
        
        editor.layout(); // Принудительно обновляем размеры после открытия модалки
        editor.revealLineInCenter(line);
        
        if (editor._decorationsCollection) {
            editor._decorationsCollection.set([{
                range: new monaco.Range(line, 1, line, 1),
                options: { isWholeLine: true, className: isCritical ? 'critical-line-highlight' : 'active-line-highlight' }
            }]);
        }
    }

    document.querySelector('.filter-pills').addEventListener('click', (e) => {
        if (!e.target.classList.contains('pill')) return;
        document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
        e.target.classList.add('active');
        
        const sev = e.target.dataset.severity;
        if (sev === 'complexity') {
            renderComplexityTab();
        } else {
            renderIssues(allIssues);
            if (sev !== 'all') {
                document.querySelectorAll('.issue-card').forEach(card => {
                    if (sev === 'security') {
                        card.classList.toggle('hidden', card.dataset.category !== 'security');
                    } else if (sev === 'warning') {
                        // Показываем предупреждения, которые НЕ являются безопасностью
                        card.classList.toggle('hidden', card.dataset.severity !== 'warning' || card.dataset.category === 'security');
                    } else if (sev === 'critical') {
                        // Показываем критические ошибки, которые НЕ являются безопасностью
                        card.classList.toggle('hidden', card.dataset.severity !== 'critical' || card.dataset.category === 'security');
                    }
                });
            }
        }
    });
});
