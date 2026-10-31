/*
    AI Interview Assistant
    Premium Coding Round Interface Logic
    File: static/js/coding.js - Monaco Integration
*/

document.addEventListener('DOMContentLoaded', () => {
    let monacoEditor;
    const editorContainer = document.getElementById('editor-container');
    const problemId = 'two-sum'; // In a real app, this would be dynamic
    const localStorageKey = `monaco-code-${problemId}`;

    const starterCode = {
        python: 'def two_sum(nums, target):\n    # Write your solution here\n    pass',
        java: 'class Solution {\n    public int[] twoSum(int[] nums, int target) {\n        // Write your solution here\n        return new int[]{};\n    }\n}',
        cpp: 'class Solution {\npublic:\n    vector<int> twoSum(vector<int>& nums, int target) {\n        // Write your solution here\n        return {};\n    }\n};',
        c: '#include <stdio.h>\n\nint* twoSum(int* nums, int numsSize, int target, int* returnSize) {\n    // Write your solution here\n    *returnSize = 0;\n    return NULL;\n}',
        javascript: '/**\n * @param {number[]} nums\n * @param {number} target\n * @return {number[]}\n */\nvar twoSum = function(nums, target) {\n    // Write your solution here\n};',
        sql: '-- Write your PostgreSQL query here\n\n'
    };

    // --- Monaco Editor Initialization ---
    if (!editorContainer) {
        console.error('Monaco initialization failed: #editor-container was not found.');
    } else if (typeof require === 'undefined') {
        console.error('Monaco initialization failed: the Monaco AMD loader was not found.');
    } else {
        require.config({
            paths: {
                vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.1/min/vs'
            }
        });

        require([
            'vs/editor/editor.main'
        ], () => {
            try {
                const initialLang = (languageSelector ? languageSelector.value : 'python').toLowerCase();
                const initialCode = localStorage.getItem(localStorageKey) || starterCode[initialLang] || starterCode.python;

                monacoEditor = monaco.editor.create(editorContainer, {
                    value: initialCode,
                    language: initialLang,
                    theme: document.documentElement.dataset.theme === 'dark' ? 'vs-dark' : 'vs',
                    fontSize: 14,
                    automaticLayout: true,
                    minimap: { enabled: false },
                    wordWrap: 'on',
                    fontFamily: 'Fira Code, monospace',
                    lineNumbers: 'on',
                    roundedSelection: false,
                    scrollBeyondLastLine: false,
                    readOnly: false,
                    tabSize: 4,
                    bracketPairColorization: { enabled: true },
                    autoClosingBrackets: 'always',
                    autoClosingQuotes: 'always'
                });

                window.editor = monacoEditor;
                setTimeout(() => {
                    if (monacoEditor) monacoEditor.layout();
                }, 100);

                setupAutoSave();
                setupKeyboardShortcuts();
                setupStatusBar();
            } catch (error) {
                console.error('Monaco initialization failed:', error);
            }
        }, (error) => {
            console.error('Monaco failed to load:', error);
        });
    }

    // --- DOM Element Selectors ---
    // Corrected IDs to match HTML
    const languageSelector = document.getElementById('languageSelector');
    const themeSelector = document.getElementById('themeSelector');
    const fontSizeSelector = document.getElementById('fontSizeSelector');
    const fullscreenBtn = document.querySelector('.editor-right .btn-glass i.bi-fullscreen')?.parentElement;

    const runBtn = document.getElementById('runBtn');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetBtn');
    const copyBtn = document.getElementById('copyBtn');
    const formatBtn = document.getElementById('formatBtn');
    
    const outputArea = document.getElementById('outputArea');
    const outputDetails = document.getElementById('output-details');
    const statusArea = document.getElementById('statusArea');
    const statusDetails = document.getElementById('status-details');
    
    const scoreValue = document.getElementById('score-value');
    const testCaseStatus = document.getElementById('test-case-status');

    // --- DOM Element Selectors ---
    // Corrected IDs to match HTML
    const languageSelector = document.getElementById('languageSelector');
    const themeSelector = document.getElementById('themeSelector');
    const fontSizeSelector = document.getElementById('fontSizeSelector');
    const fullscreenBtn = document.querySelector('.editor-right .btn-glass i.bi-fullscreen')?.parentElement;

    const runBtn = document.getElementById('runBtn');
    const submitBtn = document.getElementById('submitBtn');
    const resetBtn = document.getElementById('resetBtn');
    const copyBtn = document.getElementById('copyBtn');
    const formatBtn = document.getElementById('formatBtn');
    
    const outputArea = document.getElementById('outputArea');
    const outputDetails = document.getElementById('output-details');
    const statusArea = document.getElementById('statusArea');
    const statusDetails = document.getElementById('status-details');
    
    const scoreValue = document.getElementById('score-value');
    const testCaseStatus = document.getElementById('test-case-status');
    const testCaseProgress = document.getElementById('test-case-progress');

    // Tab selectors (updated for new tab structure)
    const outputTab = new bootstrap.Tab(document.getElementById('output-tab'));
    const statusTab = new bootstrap.Tab(document.getElementById('status-tab'));

    // --- Language Selector Logic ---
    if (languageSelector) {
        languageSelector.addEventListener('change', (e) => {
            const newLang = e.target.value;
            const activeLangDisplay = document.getElementById('activeLangDisplay');
            const statusBarLang = document.getElementById('statusBarLang');
            if (activeLangDisplay) activeLangDisplay.textContent = newLang.toUpperCase();
            if (statusBarLang) statusBarLang.textContent = newLang;

            if (monacoEditor) {
                const currentCode = monacoEditor.getValue();
                const defaultCodeForNewLang = starterCode[newLang] || '';
                
                // Check if the current code is just one of the existing starter templates
                const isPristine = Object.values(starterCode).some(template => template === currentCode);

                if (currentCode.trim() === '' || isPristine) {
                    // If editor is empty or has a pristine template, just switch without asking
                    monaco.editor.setModelLanguage(monacoEditor.getModel(), newLang);
                    monacoEditor.setValue(defaultCodeForNewLang);
                    console.log(`Editor language changed to: ${newLang}`);
                } else {
                    // If there's user-written code, ask for confirmation
                    if (confirm('Changing the language will replace your current code with the template for the new language. Are you sure?')) {
                        monaco.editor.setModelLanguage(monacoEditor.getModel(), newLang);
                        monacoEditor.setValue(defaultCodeForNewLang);
                        console.log(`Editor language changed to: ${newLang}`);
                    } else {
                        // If user cancels, revert the dropdown to the editor's current language
                        e.target.value = monacoEditor.getModel().getLanguageId();
                    }
                }
            }
        });
    }

    // --- Theme Selector Logic ---
    if (themeSelector) {
        themeSelector.addEventListener('change', (e) => {
            const themes = {
                'VS Light': 'vs',
                'VS Dark': 'vs-dark',
                'High Contrast': 'hc-black'
            };
            const newTheme = themes[e.target.value] || 'vs';
            if (monacoEditor) {
                monaco.editor.setTheme(newTheme);
                console.log(`Editor theme changed to: ${newTheme}`);
            }
        });
    }

    window.addEventListener('interviewai:themechange', event => {
        if (window.monaco && monacoEditor) {
            monaco.editor.setTheme(event.detail.theme === 'dark' ? 'vs-dark' : 'vs');
        }
    });

    // --- Font Size Selector Logic ---
    if (fontSizeSelector) {
        fontSizeSelector.addEventListener('change', (e) => {
            const newSize = parseInt(e.target.value, 10);
            if (monacoEditor) {
                monacoEditor.updateOptions({ fontSize: newSize });
                console.log(`Editor font size changed to: ${newSize}`);
            }
        });
    }

    // --- Auto-Save to Local Storage ---
    function setupAutoSave() {
        let debounceTimer;
        monacoEditor.onDidChangeModelContent(() => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                localStorage.setItem(localStorageKey, monacoEditor.getValue());
                console.log('Code auto-saved to local storage.');
            }, 1000);
        });
    }

    // --- Keyboard Shortcuts ---
    function setupKeyboardShortcuts() {
        monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            console.log('Draft Saved (Ctrl+S)');
            // In a real app, you might show a small notification
        });
        monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
            runBtn.click();
        });
        monacoEditor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Enter, () => {
            submitBtn.click();
        });
    }

    // --- Status Bar Logic ---
    function setupStatusBar() {
        monacoEditor.onDidChangeCursorPosition(e => {
            const position = e.position;
            const totalLines = monacoEditor.getModel().getLineCount();
            const currentLanguage = monacoEditor.getModel().getLanguageId();
            // NOTE: The HTML does not have a dedicated status bar.
            // This data would be injected into elements within it.
            console.log(`Status Bar: Lang: ${currentLanguage}, Ln ${position.lineNumber}, Col ${position.column}, Lines: ${totalLines}`);
        });
    }

    // --- Button Functionality ---

    // 1. Run Code
    if (runBtn) { // Replaced mock with real API call
        runBtn.addEventListener('click', async () => {
            // Set loading state
            runBtn.disabled = true;
            runBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Running...';
            
            // Clear previous output and switch to output tab
            outputDetails.classList.add('d-none');
            outputArea.innerHTML = '<code>Running code...</code>';
            outputTab.show();

            try {
                const code = monacoEditor.getValue();
                const language = languageSelector.value;
                const input = document.getElementById('customInputArea').value;

                const response = await fetch('/api/coding/run', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        language: language,
                        code: code,
                        input: input,
                    }),
                });

                const result = await response.json();

                // Display execution details
                const statusClass = result.success ? 'accepted' : 'wrong-answer';
                outputDetails.innerHTML = `
                    <span class="status-badge ${statusClass}">${result.status}</span>
                    <span><i class="bi bi-clock"></i>Runtime: <strong>${result.runtime}</strong></span>
                    <span><i class="bi bi-memory"></i>Memory: <strong>${result.memory}</strong></span>
                `;
                outputDetails.classList.remove('d-none');

                // Display stdout or stderr
                if (result.stderr) {
                    outputArea.innerHTML = `<code class="text-danger">${result.stderr}</code>`;
                } else {
                    outputArea.innerHTML = `<code>${result.stdout || '(No output produced)'}</code>`;
                }

            } catch (error) {
                console.error('Error running code:', error);
                outputDetails.innerHTML = `<span class="status-badge runtime-error">Client Error</span>`;
                outputDetails.classList.remove('d-none');
                outputArea.innerHTML = `<code class="text-danger">Failed to connect to the execution service. Please check your network connection and try again.</code>`;
            } finally {
                // Restore button state
                runBtn.disabled = false;
                runBtn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Run Code';
            }
        });
    }

    // 2. Submit Solution
    if (submitBtn) { // Simulate submitting code
        submitBtn.addEventListener('click', () => {
            statusDetails.classList.add('d-none');
            statusArea.innerHTML = '<code>Submitting to the judge... This may take a moment.</code>';
            statusTab.show();

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';

            // Simulate different outcomes
            const outcomes = ['Accepted', 'Wrong Answer', 'Time Limit Exceeded', 'Runtime Error'];
            const randomOutcome = outcomes[Math.floor(Math.random() * outcomes.length)];

            setTimeout(() => {
                let statusClass, score, passedTests;
                switch(randomOutcome) {
                    case 'Accepted':
                        statusClass = 'accepted';
                        score = 100;
                        passedTests = 2;
                        break;
                    case 'Wrong Answer':
                        statusClass = 'wrong-answer';
                        score = 40;
                        passedTests = 1;
                        break;
                    case 'Time Limit Exceeded':
                        statusClass = 'time-limit';
                        score = 0;
                        passedTests = 0;
                        break;
                    default: // Runtime Error
                        statusClass = 'runtime-error';
                        score = 0;
                        passedTests = 0;
                        break;
                }

                statusDetails.innerHTML = `
                    <span class="status-badge ${statusClass}">${randomOutcome}</span>
                    <span><i class="bi bi-clock"></i>Runtime: <strong>${score > 0 ? '64ms' : 'N/A'}</strong></span>
                    <span><i class="bi bi-memory"></i>Memory: <strong>${score > 0 ? '17.1 MB' : 'N/A'}</strong></span>
                `;
                statusDetails.classList.remove('d-none');
                statusArea.innerHTML = `<code>Test Case 1: ${passedTests > 0 ? 'Accepted' : 'Failed'}\nTest Case 2: ${passedTests > 1 ? 'Accepted' : 'Failed'}\n...\nFinal Status: ${randomOutcome}</code>`;

                // Update UI panels
                scoreValue.innerHTML = `${score}<span class="report-score-total">/ 100</span>`;
                testCaseStatus.textContent = `${passedTests} / 2`;
                testCaseProgress.style.width = `${(passedTests / 2) * 100}%`;

                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="bi bi-cloud-upload me-2"></i>Submit Solution';
            }, 2500);
        });
    }

    // 3. Reset Code
    if (resetBtn) { // Reset code to initial state
        resetBtn.addEventListener('click', () => {
            if (confirm('Are you sure you want to reset your code? All changes will be lost.')) {
                const currentLang = languageSelector.value;
                monacoEditor.setValue(starterCode[currentLang] || '');
            }
        });
    }

    // 4. Copy Code
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            const code = monacoEditor.getValue();
            navigator.clipboard.writeText(code).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="bi bi-check-lg me-2"></i>Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText; // Revert button text
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
                alert('Failed to copy code. Please try again or copy manually.');
            });
        });
    }

    // 5. Format Code
    if (formatBtn) {
        formatBtn.addEventListener('click', () => {
            if (monacoEditor) {
                monacoEditor.getAction('editor.action.formatDocument').run();
                console.log('Code formatted.');
                // Optionally, show a temporary message
                const originalText = formatBtn.innerHTML;
                formatBtn.innerHTML = '<i class="bi bi-check-lg me-2"></i>Formatted!';
                setTimeout(() => {
                    formatBtn.innerHTML = originalText;
                }, 1500);
            }
        });
    }

    // 6. Fullscreen
    if (fullscreenBtn) {
        fullscreenBtn.addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                editorContainer.requestFullscreen().catch(err => alert(`Error attempting to enable full-screen mode: ${err.message}`));
            }
        });
    }
});
