/**
 * Interview.ai — Production Coding Assessment Controller
 * Manages Monaco editor, dynamic question navigation, containerized code execution,
 * visible & hidden test evaluation, timer sync, and final report generation.
 */

document.addEventListener('DOMContentLoaded', () => {
    // --- Assessment Configuration ---
    const config = window.ASSESSMENT_CONFIG || {
        role: "Software Engineer",
        domain: "Software Engineering",
        difficulty: "Medium",
        language: "Python",
        questionsCount: 5,
        durationSeconds: 2700,
        questionsList: [],
        savedAnswers: {}
    };

    // --- Build Question Bank from Server Payload or Safe Fallback ---
    const questionsData = {};
    if (config.questionsList && Array.isArray(config.questionsList) && config.questionsList.length > 0) {
        config.questionsList.forEach((q, idx) => {
            const idStr = String(q.id || idx + 1);
            questionsData[idStr] = {
                id: idStr,
                key: q.key || `q-${idStr}`,
                title: q.title || `Question ${idStr}`,
                function_name: q.function_name || q.functionName || '',
                comparator: q.comparator || 'exact',
                numberText: q.numberText || `Problem ${idx + 1} of ${config.questionsList.length}`,
                progressPercent: q.progressPercent || Math.round(((idx + 1) / config.questionsList.length) * 100),
                progressText: q.progressText || `Question ${idx + 1} of ${config.questionsList.length}`,
                difficulty: q.difficulty || config.difficulty || 'Medium',
                badgeText: q.category || q.badgeText || (q.difficulty || 'Medium'),
                description: q.description || '',
                examples: q.examples || [],
                constraints: q.constraints || [],
                starterCode: q.starterCode || q.starter_code || 'def solution():\n    pass\n',
                testCases: q.testCases || q.test_cases || []
            };
        });
    } else {
        // Safe Fallback Questions
        questionsData["1"] = {
            id: "1",
            key: "two-sum",
            title: "Two Sum",
            function_name: "two_sum",
            comparator: "unordered_list",
            numberText: "Problem 1 of 2",
            progressPercent: 50,
            progressText: "Question 1 of 2",
            difficulty: "Easy",
            badgeText: "Array • Hash Table",
            description: `Given an array of integers <code>nums</code> and an integer <code>target</code>, return indices of the two numbers such that they add up to <code>target</code>.<br><br>You may assume that each input would have exactly one solution, and you may not use the same element twice.`,
            examples: [
                { input: "nums = [2,7,11,15], target = 9", output: "[0,1]", explanation: "nums[0] + nums[1] = 2 + 7 = 9" },
                { input: "nums = [3,2,4], target = 6", output: "[1,2]", explanation: "nums[1] + nums[2] = 2 + 4 = 6" }
            ],
            constraints: ["2 <= nums.length <= 10^4", "-10^9 <= nums[i] <= 10^9"],
            starterCode: "def two_sum(nums, target):\n    # Write your solution here\n    pass\n",
            testCases: [
                { title: "Test Case 1", input: "[2, 7, 11, 15], 9", expected: "[0, 1]" },
                { title: "Test Case 2", input: "[3, 2, 4], 6", expected: "[1, 2]" }
            ]
        };
        questionsData["2"] = {
            id: "2",
            key: "valid-palindrome",
            title: "Valid Palindrome",
            function_name: "is_palindrome",
            comparator: "exact",
            numberText: "Problem 2 of 2",
            progressPercent: 100,
            progressText: "Question 2 of 2",
            difficulty: "Easy",
            badgeText: "Two Pointers • String",
            description: `A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward.`,
            examples: [
                { input: 's = "A man, a plan, a canal: Panama"', output: "true", explanation: '"amanaplanacanalpanama" is a palindrome.' }
            ],
            constraints: ["1 <= s.length <= 2 * 10^5"],
            starterCode: "def is_palindrome(s):\n    # Write your solution here\n    pass\n",
            testCases: [
                { title: "Test Case 1", input: '"A man, a plan, a canal: Panama"', expected: "true" }
            ]
        };
    }

    const questionIds = Object.keys(questionsData);
    let currentQuestionId = questionIds.length > 0 ? questionIds[0] : "1";
    let monacoEditor = null;
    let autoSaveTimeout = null;
    let isReadOnly = false;
    let isExecuting = false;

    // --- Question Status Tracking for Navigator ---
    const questionStatus = {};
    questionIds.forEach(qId => {
        questionStatus[qId] = {
            status: 'unattempted', // 'unattempted' | 'attempted' | 'solved' | 'failed'
            visiblePassed: 0,
            visibleTotal: (questionsData[qId].testCases || []).length
        };
    });

    // --- Code Store: Session -> LocalStorage -> StarterCode ---
    const codeStore = {};
    questionIds.forEach(qId => {
        const serverSaved = config.savedAnswers && config.savedAnswers[qId] ? config.savedAnswers[qId].code : null;
        const localSaved = localStorage.getItem(`interviewai_code_q${qId}`);
        const starter = questionsData[qId].starterCode;
        const finalCode = serverSaved || localSaved || starter;
        codeStore[qId] = finalCode;

        if (finalCode && finalCode.trim()) {
            questionStatus[qId].status = 'attempted';
        }
    });

    // --- Helper: What counts as Answered ---
    function isQuestionAnswered(qId) {
        const code = (codeStore[qId] !== undefined ? codeStore[qId] : '').trim();
        return code.length > 0;
    }

    function getUnansweredQuestions() {
        if (currentQuestionId && typeof getEditorCode === 'function') {
            codeStore[currentQuestionId] = getEditorCode();
        }
        const unanswered = [];
        questionIds.forEach((qId, idx) => {
            if (!isQuestionAnswered(qId)) {
                unanswered.push(idx + 1);
            }
        });
        return unanswered;
    }

    // --- DOM Elements ---
    const timerDisplay = document.getElementById('timerDisplay');
    const timerBadge = document.getElementById('timerBadge');
    const btnExitAssessment = document.getElementById('btnExitAssessment');

    // Navigation & Problem Info
    const questionNavList = document.getElementById('questionNavList');
    const navigatorCountBadge = document.getElementById('navigatorCountBadge');
    const problemHeaderNumber = document.getElementById('problemHeaderNumber');
    const problemDifficultyBadge = document.getElementById('problemDifficultyBadge');
    const problemTitle = document.getElementById('problemTitle');
    const problemDescription = document.getElementById('problemDescription');
    const problemExamples = document.getElementById('problemExamples');
    const problemConstraints = document.getElementById('problemConstraints');
    const progressBarFill = document.getElementById('progressBarFill');
    const progressText = document.getElementById('progressText');

    // Editor & Toolbar
    const monacoContainer = document.getElementById('monacoEditorContainer');
    const fallbackTextarea = document.getElementById('fallbackTextarea');
    const autoSaveStatus = document.getElementById('autoSaveStatus');
    const btnResetCode = document.getElementById('btnResetCode');
    const btnRunCode = document.getElementById('btnRunCode');
    const btnToolbarSubmit = document.getElementById('btnToolbarSubmit');
    const btnSubmitSolution = document.getElementById('btnSubmitSolution');
    const btnPrevQuestion = document.getElementById('btnPrevQuestion');
    const btnNextQuestion = document.getElementById('btnNextQuestion');

    // Test Cases & Output Panel
    const tabTestCases = document.getElementById('tabTestCases');
    const tabOutput = document.getElementById('tabOutput');
    const paneTestCases = document.getElementById('paneTestCases');
    const paneOutput = document.getElementById('paneOutput');
    const testCasesList = document.getElementById('testCasesList');
    const btnTogglePanelCollapse = document.getElementById('btnTogglePanelCollapse');
    const assessmentTestPanel = document.getElementById('assessmentTestPanel');
    const iconPanelCollapse = document.getElementById('iconPanelCollapse');

    // Mobile Switcher
    const tabMobileProblem = document.getElementById('tabMobileProblem');
    const tabMobileEditor = document.getElementById('tabMobileEditor');
    const assessmentProblemPane = document.getElementById('assessmentProblemPane');
    const assessmentEditorPane = document.getElementById('assessmentEditorPane');

    // Modals & Overlays
    const exitModal = document.getElementById('exitAssessmentModal');
    const btnContinueAssessment = document.getElementById('btnContinueAssessment');
    const btnConfirmExit = document.getElementById('btnConfirmExit');

    const resetModal = document.getElementById('resetCodeModal');
    const btnCancelReset = document.getElementById('btnCancelReset');
    const btnConfirmReset = document.getElementById('btnConfirmReset');

    const submitModal = document.getElementById('submitSolutionModal');
    const btnCancelSubmit = document.getElementById('btnCancelSubmit');
    const btnConfirmSubmit = document.getElementById('btnConfirmSubmit');
    const submitModalAnsweredCount = document.getElementById('submitModalAnsweredCount');
    const submitModalPassedTests = document.getElementById('submitModalPassedTests');
    const submitModalTimeUsed = document.getElementById('submitModalTimeUsed');
    const submitModalUnansweredWarning = document.getElementById('submitModalUnansweredWarning');

    const submittingOverlay = document.getElementById('submittingOverlay');
    const timesUpModal = document.getElementById('timesUpModal');

    // ==========================================
    // 1. Monaco Editor Setup & Textarea Fallback
    // ==========================================
    function getEditorCode() {
        if (monacoEditor) {
            return monacoEditor.getValue();
        }
        return fallbackTextarea ? fallbackTextarea.value : '';
    }

    function setEditorCode(val) {
        if (monacoEditor) {
            monacoEditor.setValue(val || '');
        }
        if (fallbackTextarea) {
            fallbackTextarea.value = val || '';
        }
    }

    function setEditorReadOnly(readOnly) {
        isReadOnly = readOnly;
        if (monacoEditor) {
            monacoEditor.updateOptions({ readOnly: readOnly });
        }
        if (fallbackTextarea) {
            fallbackTextarea.readOnly = readOnly;
        }
        if (btnRunCode) btnRunCode.disabled = readOnly;
        if (btnResetCode) btnResetCode.disabled = readOnly;
        if (btnSubmitSolution) btnSubmitSolution.disabled = readOnly;
        if (btnToolbarSubmit) btnToolbarSubmit.disabled = readOnly;
    }

    function initMonaco() {
        if (typeof require !== 'undefined' && monacoContainer) {
            require.config({
                paths: {
                    vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.1/min/vs'
                }
            });

            require(['vs/editor/editor.main'], () => {
                try {
                    if (fallbackTextarea) fallbackTextarea.style.display = 'none';

                    monacoEditor = monaco.editor.create(monacoContainer, {
                        value: codeStore[currentQuestionId] || questionsData[currentQuestionId].starterCode,
                        language: (config.language || 'python').toLowerCase(),
                        theme: 'vs', // Pure Light theme
                        fontSize: 14,
                        automaticLayout: true,
                        minimap: { enabled: false },
                        wordWrap: 'on',
                        fontFamily: 'Fira Code, Consolas, Monaco, monospace',
                        lineNumbers: 'on',
                        scrollBeyondLastLine: false,
                        readOnly: isReadOnly,
                        tabSize: 4,
                        bracketPairColorization: { enabled: true },
                        padding: { top: 12, bottom: 12 }
                    });

                    monacoEditor.onDidChangeModelContent(() => {
                        handleCodeChange();
                    });

                    setTimeout(() => {
                        if (monacoEditor) monacoEditor.layout();
                    }, 100);

                } catch (e) {
                    console.warn('Monaco initialization failed, using textarea fallback:', e);
                    activateFallbackTextarea();
                }
            }, (err) => {
                console.warn('Monaco AMD loader failed, using textarea fallback:', err);
                activateFallbackTextarea();
            });
        } else {
            activateFallbackTextarea();
        }
    }

    function activateFallbackTextarea() {
        if (fallbackTextarea) {
            fallbackTextarea.style.display = 'block';
            fallbackTextarea.value = codeStore[currentQuestionId] || questionsData[currentQuestionId].starterCode;
            fallbackTextarea.addEventListener('input', handleCodeChange);
        }
    }

    // ==========================================
    // 2. Auto-Save System
    // ==========================================
    function triggerAutoSave() {
        const code = getEditorCode();
        codeStore[currentQuestionId] = code;

        localStorage.setItem(`interviewai_code_q${currentQuestionId}`, code);

        if (autoSaveStatus) {
            autoSaveStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>Saving...';
            autoSaveStatus.className = 'editor-autosave-status text-primary';
        }

        fetch('/api/coding/save_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question_id: currentQuestionId,
                code: code,
                language: config.language || 'Python',
                is_submission: false
            })
        })
        .then(res => res.json())
        .then(() => {
            if (autoSaveStatus) {
                autoSaveStatus.innerHTML = '<i class="bi bi-cloud-check text-success"></i> Saved';
                autoSaveStatus.className = 'editor-autosave-status text-muted';
            }
        })
        .catch(() => {
            if (autoSaveStatus) {
                autoSaveStatus.innerHTML = '<i class="bi bi-cloud-check text-muted"></i> Saved locally';
                autoSaveStatus.className = 'editor-autosave-status text-muted';
            }
        });
    }

    function handleCodeChange() {
        const code = getEditorCode();
        codeStore[currentQuestionId] = code;

        // Immediately update question navigation status and submit enablement
        renderQuestionNav();
        updateSubmitButtonState();

        if (autoSaveStatus) {
            autoSaveStatus.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>Saving...';
        }
        clearTimeout(autoSaveTimeout);
        autoSaveTimeout = setTimeout(triggerAutoSave, 700);
    }

    // ==========================================
    // 3. Navigation Controls & Submit Button State
    // ==========================================
    function updateSubmitButtonState() {
        const unanswered = getUnansweredQuestions();
        const allAnswered = unanswered.length === 0 && questionIds.length > 0;
        const total = questionIds.length;
        const answeredCount = total - unanswered.length;

        [btnSubmitSolution, btnToolbarSubmit].forEach(btn => {
            if (!btn) return;
            btn.disabled = !allAnswered;
            if (!allAnswered) {
                btn.classList.add('disabled');
                btn.setAttribute('title', `Please answer all questions before submitting (${answeredCount} of ${total} answered)`);
            } else {
                btn.classList.remove('disabled');
                btn.setAttribute('title', 'Submit coding assessment for final evaluation');
            }
        });

        return allAnswered;
    }

    function updateNavigationButtons() {
        const currentIndex = questionIds.indexOf(currentQuestionId);
        const total = questionIds.length;

        // Previous Question button
        if (btnPrevQuestion) {
            if (currentIndex > 0) {
                btnPrevQuestion.disabled = false;
                btnPrevQuestion.classList.remove('d-none');
            } else {
                btnPrevQuestion.disabled = true;
                btnPrevQuestion.classList.add('d-none');
            }
        }

        // Next Question button
        if (btnNextQuestion) {
            if (currentIndex < total - 1) {
                btnNextQuestion.classList.remove('d-none');
                btnNextQuestion.disabled = false;
            } else {
                btnNextQuestion.classList.add('d-none');
            }
        }

        // Submit Solution button at bottom workspace - visible on final question
        if (btnSubmitSolution) {
            if (currentIndex === total - 1) {
                btnSubmitSolution.classList.remove('d-none');
            } else {
                btnSubmitSolution.classList.add('d-none');
            }
        }

        updateSubmitButtonState();
    }

    if (btnPrevQuestion) {
        btnPrevQuestion.addEventListener('click', () => {
            const currentIndex = questionIds.indexOf(currentQuestionId);
            if (currentIndex > 0) {
                renderQuestion(questionIds[currentIndex - 1]);
            }
        });
    }

    if (btnNextQuestion) {
        btnNextQuestion.addEventListener('click', () => {
            const currentIndex = questionIds.indexOf(currentQuestionId);
            if (currentIndex < questionIds.length - 1) {
                renderQuestion(questionIds[currentIndex + 1]);
            }
        });
    }

    // ==========================================
    // 4. Question Navigator & Question Rendering
    // ==========================================
    function renderQuestionNav() {
        if (!questionNavList) return;

        questionNavList.innerHTML = questionIds.map((qId, idx) => {
            const q = questionsData[qId];
            const isActive = qId === currentQuestionId;
            const answered = isQuestionAnswered(qId);

            let statusClass = answered ? 'status-answered' : 'status-unanswered';
            if (isActive) statusClass += ' active';

            let iconHtml = answered 
                ? '<i class="bi bi-check-circle-fill text-success" title="Answered"></i>' 
                : '<i class="bi bi-circle text-muted" title="Unanswered"></i>';

            let badgeHtml = answered
                ? '<span class="badge bg-success-subtle text-success font-monospace ms-auto" style="font-size: 0.65rem;">Answered</span>'
                : '<span class="badge bg-light text-muted border font-monospace ms-auto" style="font-size: 0.65rem;">Unanswered</span>';

            return `
                <div class="question-nav-item ${isActive ? 'active' : ''} ${statusClass}" data-question-id="${qId}">
                    <span class="q-nav-num">Q${idx + 1}</span>
                    <span class="q-nav-title text-truncate" title="${escapeHtml(q.title)}">${escapeHtml(q.title)}</span>
                    ${badgeHtml}
                </div>
            `;
        }).join('');

        questionNavList.querySelectorAll('.question-nav-item').forEach(item => {
            item.addEventListener('click', () => {
                const targetId = item.getAttribute('data-question-id');
                if (targetId && targetId !== currentQuestionId) {
                    renderQuestion(targetId);
                }
            });
        });
    }

    function renderQuestion(qId) {
        const q = questionsData[qId];
        if (!q) return;

        // 1. Persist current open question's code before switching
        if (currentQuestionId && questionsData[currentQuestionId]) {
            codeStore[currentQuestionId] = getEditorCode();
            localStorage.setItem(`interviewai_code_q${currentQuestionId}`, codeStore[currentQuestionId]);
        }

        currentQuestionId = qId;

        // Header and Meta
        if (problemHeaderNumber) problemHeaderNumber.textContent = q.numberText;
        if (problemTitle) problemTitle.textContent = q.title;
        if (problemDescription) problemDescription.innerHTML = q.description;

        if (problemDifficultyBadge) {
            problemDifficultyBadge.textContent = q.difficulty;
            const diffLower = (q.difficulty || '').toLowerCase();
            if (diffLower === 'easy') {
                problemDifficultyBadge.className = 'badge bg-success-subtle text-success font-monospace';
            } else if (diffLower === 'hard') {
                problemDifficultyBadge.className = 'badge bg-danger-subtle text-danger font-monospace';
            } else {
                problemDifficultyBadge.className = 'badge bg-warning-subtle text-warning font-monospace';
            }
        }

        // Progress
        if (progressBarFill) progressBarFill.style.width = `${q.progressPercent}%`;
        if (progressText) progressText.textContent = q.progressText;

        // Examples
        if (problemExamples) {
            problemExamples.innerHTML = (q.examples || []).map((ex, idx) => `
                <div class="problem-example-box">
                    <strong>Example ${idx + 1}:</strong>
                    <pre><strong>Input:</strong> ${escapeHtml(ex.input)}<br><strong>Output:</strong> ${escapeHtml(ex.output)}${ex.explanation ? `<br><strong>Explanation:</strong> ${escapeHtml(ex.explanation)}` : ''}</pre>
                </div>
            `).join('');
        }

        // Constraints
        if (problemConstraints) {
            problemConstraints.innerHTML = (q.constraints || []).map(c => `<li><code>${escapeHtml(c)}</code></li>`).join('');
        }

        // Visible Test Cases in Bottom Panel
        if (testCasesList) {
            testCasesList.innerHTML = (q.testCases || []).map((tc, idx) => `
                <div class="test-case-item">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <strong class="text-main">${escapeHtml(tc.title || `Test Case ${idx + 1}`)}</strong>
                        <span class="badge bg-light text-muted border font-monospace small">Pre-set</span>
                    </div>
                    <div class="font-monospace text-muted small">
                        <div><span class="text-secondary">Input:</span> ${escapeHtml(tc.input)}</div>
                        <div><span class="text-secondary">Expected:</span> ${escapeHtml(tc.expected)}</div>
                    </div>
                </div>
            `).join('');
        }

        // Load targeted question's code (or starter template if none saved)
        const targetCode = codeStore[qId] !== undefined ? codeStore[qId] : q.starterCode;
        setEditorCode(targetCode);

        // Update Question Navigator active state and navigation buttons
        renderQuestionNav();
        updateNavigationButtons();
        updateSubmitButtonState();

        // Reset output console tab
        if (paneOutput) {
            paneOutput.innerHTML = `<pre class="output-console-box" id="outputConsole">No execution yet. Run your code to see results.</pre>`;
        }
        switchToTab('test-cases');
    }

    // ==========================================
    // 4. Panel Tabs & Collapsible Test Panel
    // ==========================================
    function switchToTab(tabName) {
        if (tabName === 'test-cases') {
            if (tabTestCases) tabTestCases.classList.add('active');
            if (tabOutput) tabOutput.classList.remove('active');
            if (paneTestCases) paneTestCases.classList.remove('d-none');
            if (paneOutput) paneOutput.classList.add('d-none');
        } else {
            if (tabTestCases) tabTestCases.classList.remove('active');
            if (tabOutput) tabOutput.classList.add('active');
            if (paneTestCases) paneTestCases.classList.add('d-none');
            if (paneOutput) paneOutput.classList.remove('d-none');
        }
    }

    if (tabTestCases) tabTestCases.addEventListener('click', () => switchToTab('test-cases'));
    if (tabOutput) tabOutput.addEventListener('click', () => switchToTab('output'));

    if (btnTogglePanelCollapse && assessmentTestPanel) {
        btnTogglePanelCollapse.addEventListener('click', () => {
            assessmentTestPanel.classList.toggle('collapsed');
            const isCollapsed = assessmentTestPanel.classList.contains('collapsed');
            if (iconPanelCollapse) {
                iconPanelCollapse.className = isCollapsed ? 'bi bi-chevron-up' : 'bi bi-chevron-down';
            }
            if (monacoEditor) {
                setTimeout(() => monacoEditor.layout(), 200);
            }
        });
    }

    // ==========================================
    // 5. Code Execution ("Run Code") via Isolated Sandbox
    // ==========================================
    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function renderExecutionResults(res) {
        if (!paneOutput) return;

        const status = res.status || 'Unknown';
        const passed = res.passed !== undefined ? res.passed : 0;
        const total = res.total !== undefined ? res.total : 0;
        const execTime = res.execution_time_ms !== undefined ? `${res.execution_time_ms} ms` : '--';

        if (res.is_infrastructure_error || res.error_type === 'execution_environment' || res.status === 'Execution Unavailable') {
            paneOutput.innerHTML = `
                <div class="execution-result-container p-3">
                    <div class="alert alert-warning border-warning d-flex align-items-start gap-3 p-3 rounded-3 mb-0">
                        <i class="bi bi-exclamation-triangle-fill fs-3 text-warning flex-shrink-0 mt-1"></i>
                        <div>
                            <strong class="d-block mb-1 text-dark fs-6">Execution Environment Unavailable</strong>
                            <p class="mb-1 text-muted small">${escapeHtml(res.error || res.message || 'Docker is required for containerized execution but is not currently responding.')}</p>
                            <span class="small font-monospace text-secondary">Your code has been safely saved. Please ensure Docker Desktop is running and try again.</span>
                        </div>
                    </div>
                </div>
            `;
            return;
        }

        // Update Question status in navigator
        if (questionStatus[currentQuestionId]) {
            questionStatus[currentQuestionId].visiblePassed = passed;
            questionStatus[currentQuestionId].visibleTotal = total;
            if (status === 'Passed' || status === 'Success') {
                questionStatus[currentQuestionId].status = 'solved';
            } else {
                questionStatus[currentQuestionId].status = 'failed';
            }
            renderQuestionNav();
        }

        let badgeClass = 'failed';
        let badgeIcon = 'bi-x-circle-fill';
        let statusTitle = status;

        if (status === 'Passed' || status === 'Success') {
            badgeClass = 'passed';
            badgeIcon = 'bi-check-circle-fill';
            statusTitle = 'Accepted';
        } else if (status === 'Syntax Error') {
            badgeClass = 'error';
            badgeIcon = 'bi-exclamation-triangle-fill';
            statusTitle = 'Syntax Error';
        } else if (status === 'Runtime Error') {
            badgeClass = 'error';
            badgeIcon = 'bi-bug-fill';
            statusTitle = 'Runtime Error';
        } else if (status === 'Timeout') {
            badgeClass = 'timeout';
            badgeIcon = 'bi-alarm-fill';
            statusTitle = 'Time Limit Exceeded';
        } else if (status === 'Memory Limit Exceeded') {
            badgeClass = 'timeout';
            badgeIcon = 'bi-memory';
            statusTitle = 'Memory Limit Exceeded';
        }

        let html = `
            <div class="execution-result-container">
                <div class="execution-status-header">
                    <div class="d-flex align-items-center gap-2">
                        <span class="execution-status-badge ${badgeClass}">
                            <i class="bi ${badgeIcon}"></i>
                            <span>${statusTitle}</span>
                        </span>
                        <span class="execution-meta-pill">
                            <i class="bi bi-check2-all me-1"></i>Passed: ${passed} / ${total}
                        </span>
                    </div>
                    <span class="execution-meta-pill">
                        <i class="bi bi-clock-history me-1"></i>${execTime}
                    </span>
                </div>
        `;

        if (res.error) {
            html += `
                <div class="execution-error-box">
                    <strong>${escapeHtml(res.error_type || 'Execution Error')}:</strong>
                    <div class="mt-1">${escapeHtml(res.error)}</div>
                </div>
            `;
        }

        if (res.test_cases && res.test_cases.length > 0) {
            html += `<div class="d-flex flex-column gap-2 mt-1">`;
            res.test_cases.forEach((tc, idx) => {
                const tcPassed = tc.status === 'Passed';
                const tcCardClass = tcPassed ? 'passed' : (tc.status === 'Runtime Error' ? 'error' : 'failed');
                const tcBadgeClass = tcPassed ? 'bg-success-subtle text-success' : (tc.status === 'Runtime Error' ? 'bg-warning-subtle text-warning' : 'bg-danger-subtle text-danger');

                html += `
                    <div class="tc-result-card ${tcCardClass}">
                        <div class="d-flex align-items-center justify-content-between mb-1">
                            <strong class="text-main">${escapeHtml(tc.title || `Test Case ${tc.test_case_id || (idx + 1)}`)}</strong>
                            <span class="badge ${tcBadgeClass} font-monospace">${escapeHtml(tc.status || 'Failed')}</span>
                        </div>
                        <div class="tc-result-row">
                            <span class="tc-row-label">Input:</span>
                            <span class="tc-row-value">${escapeHtml(tc.input || '')}</span>
                        </div>
                        <div class="tc-result-row">
                            <span class="tc-row-label">Expected:</span>
                            <span class="tc-row-value">${escapeHtml(tc.expected || '')}</span>
                        </div>
                        ${tc.actual !== null && tc.actual !== undefined ? `
                        <div class="tc-result-row">
                            <span class="tc-row-label">Actual:</span>
                            <span class="tc-row-value">${escapeHtml(tc.actual)}</span>
                        </div>` : ''}
                        ${tc.error ? `
                        <div class="text-danger small font-monospace mt-1">
                            <i class="bi bi-exclamation-circle me-1"></i>${escapeHtml(tc.error)}
                        </div>` : ''}
                        ${tc.stdout ? `
                        <div class="tc-stdout-box">
                            <div class="text-muted small fw-bold mb-1">Stdout:</div>
                            <div>${escapeHtml(tc.stdout)}</div>
                        </div>` : ''}
                    </div>
                `;
            });
            html += `</div>`;
        }

        if (res.stdout && (!res.test_cases || res.test_cases.every(tc => !tc.stdout))) {
            html += `
                <div class="mt-2">
                    <span class="text-muted small fw-bold font-monospace">Standard Output:</span>
                    <pre class="tc-stdout-box mb-0 mt-1">${escapeHtml(res.stdout)}</pre>
                </div>
            `;
        }

        html += `</div>`;
        paneOutput.innerHTML = html;
    }

    if (btnRunCode) {
        btnRunCode.addEventListener('click', () => {
            if (isExecuting) return;

            const code = getEditorCode();
            if (!code || !code.trim()) {
                alert('Please enter your solution code before running.');
                return;
            }

            isExecuting = true;
            btnRunCode.disabled = true;
            const originalBtnHtml = btnRunCode.innerHTML;
            btnRunCode.innerHTML = `
                <span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true" style="width: 0.85rem; height: 0.85rem;"></span>
                <span>Running...</span>
            `;

            // Expand test panel if collapsed
            if (assessmentTestPanel && assessmentTestPanel.classList.contains('collapsed')) {
                assessmentTestPanel.classList.remove('collapsed');
                if (iconPanelCollapse) iconPanelCollapse.className = 'bi bi-chevron-down';
            }

            switchToTab('output');
            if (paneOutput) {
                paneOutput.innerHTML = `
                    <div class="d-flex flex-column align-items-center justify-content-center p-4 text-muted" style="min-height: 120px;">
                        <div class="spinner-border text-primary mb-2" role="status" style="width: 1.75rem; height: 1.75rem;"></div>
                        <span class="small font-monospace">Executing in secure sandbox container...</span>
                    </div>
                `;
            }

            const qMeta = questionsData[currentQuestionId] || {};
            fetch('/api/coding/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    language: (config.language || 'Python').toLowerCase(),
                    question_id: currentQuestionId,
                    code: code,
                    test_cases: qMeta.testCases || [],
                    function_name: qMeta.function_name || '',
                    comparator: qMeta.comparator || 'exact'
                })
            })
            .then(res => res.json())
            .then(data => {
                renderExecutionResults(data);
            })
            .catch(err => {
                console.error('Execution error:', err);
                renderExecutionResults({
                    status: 'System Error',
                    passed: 0,
                    total: 0,
                    error_type: 'NetworkError',
                    error: 'Failed to communicate with code execution backend. Please verify your connection and retry.',
                    test_cases: [],
                    stdout: '',
                    stderr: String(err),
                    execution_time_ms: 0
                });
            })
            .finally(() => {
                isExecuting = false;
                btnRunCode.disabled = false;
                btnRunCode.innerHTML = originalBtnHtml;
            });
        });
    }

    // ==========================================
    // 6. Reset Code Modal Flow
    // ==========================================
    if (btnResetCode && resetModal) {
        btnResetCode.addEventListener('click', () => {
            resetModal.classList.remove('d-none');
        });
    }

    if (btnCancelReset && resetModal) {
        btnCancelReset.addEventListener('click', () => {
            resetModal.classList.add('d-none');
        });
    }

    if (btnConfirmReset && resetModal) {
        btnConfirmReset.addEventListener('click', () => {
            const defaultCode = questionsData[currentQuestionId].starterCode;
            setEditorCode(defaultCode);
            codeStore[currentQuestionId] = defaultCode;
            localStorage.setItem(`interviewai_code_q${currentQuestionId}`, defaultCode);
            if (questionStatus[currentQuestionId]) {
                questionStatus[currentQuestionId].status = 'unattempted';
                renderQuestionNav();
            }
            triggerAutoSave();
            resetModal.classList.add('d-none');
        });
    }

    // ==========================================
    // 7. Submit Solution Flow (Confirmation & Final Submit)
    // ==========================================
    function openSubmitModal() {
        // Persist current editor code first
        codeStore[currentQuestionId] = getEditorCode();
        localStorage.setItem(`interviewai_code_q${currentQuestionId}`, codeStore[currentQuestionId]);

        const unanswered = getUnansweredQuestions();
        if (unanswered.length > 0) {
            alert(`You must answer all questions before submitting the assessment.\n\nUnanswered: Question ${unanswered.join(', Question ')}`);
            return;
        }

        const totalQuestions = questionIds.length;
        let answeredCount = totalQuestions;
        let visiblePassedCount = 0;

        questionIds.forEach(qId => {
            if (questionStatus[qId]) {
                visiblePassedCount += (questionStatus[qId].visiblePassed || 0);
            }
        });

        const timeUsedSec = Math.max(0, (config.durationSeconds || 2700) - remainingSeconds);
        const mins = Math.floor(timeUsedSec / 60);
        const secs = timeUsedSec % 60;

        if (submitModalAnsweredCount) {
            submitModalAnsweredCount.textContent = `${answeredCount} / ${totalQuestions}`;
        }
        if (submitModalPassedTests) {
            submitModalPassedTests.textContent = `${visiblePassedCount} tests passed`;
        }
        if (submitModalTimeUsed) {
            submitModalTimeUsed.textContent = `${mins}m ${secs}s`;
        }

        if (submitModalUnansweredWarning) {
            submitModalUnansweredWarning.classList.add('d-none');
        }

        if (submitModal) {
            submitModal.classList.remove('d-none');
        }
    }

    if (btnSubmitSolution) btnSubmitSolution.addEventListener('click', openSubmitModal);
    if (btnToolbarSubmit) btnToolbarSubmit.addEventListener('click', openSubmitModal);

    if (btnCancelSubmit && submitModal) {
        btnCancelSubmit.addEventListener('click', () => {
            submitModal.classList.add('d-none');
        });
    }

    function executeFinalSubmission() {
        if (submitModal) submitModal.classList.add('d-none');
        if (timesUpModal) timesUpModal.classList.add('d-none');
        if (submittingOverlay) submittingOverlay.classList.remove('d-none');

        setEditorReadOnly(true);
        clearInterval(timerInterval);

        const timeUsedSec = Math.max(0, (config.durationSeconds || 2700) - remainingSeconds);

        fetch('/api/coding/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answers: codeStore,
                time_used_seconds: timeUsedSec
            })
        })
        .then(res => res.json().then(data => ({ ok: res.ok, status: res.status, data })))
        .then(({ ok, status, data }) => {
            if (status === 400 && data.error === 'incomplete_assessment') {
                if (submittingOverlay) submittingOverlay.classList.add('d-none');
                setEditorReadOnly(false);
                const qList = (data.unanswered_questions || []).map(idx => `Question ${idx}`).join(', ');
                alert(`Submission blocked: Please answer all questions before submitting.\n\nUnanswered: ${qList || 'Incomplete'}`);
                return;
            }
            if (status === 503 || data.error_type === 'execution_environment' || data.is_infrastructure_error) {
                if (submittingOverlay) submittingOverlay.classList.add('d-none');
                setEditorReadOnly(false);
                alert(`Execution Environment Unavailable:\n\n${data.message || 'Docker engine is not currently running or reachable.'}\nYour code has been safely saved. Please ensure Docker Desktop is running and try again.`);
                return;
            }
            if (data.status === 'success' && data.redirect_url) {
                // Clear local storage for clean next attempt
                questionIds.forEach(qId => {
                    localStorage.removeItem(`interviewai_code_q${qId}`);
                });
                window.location.href = data.redirect_url;
            } else {
                if (submittingOverlay) submittingOverlay.classList.add('d-none');
                setEditorReadOnly(false);
                alert(data.message || data.error || 'Submission failed. Please retry.');
            }
        })
        .catch(err => {
            console.error('Final submission error:', err);
            if (submittingOverlay) submittingOverlay.classList.add('d-none');
            setEditorReadOnly(false);
            alert('Failed to connect to assessment server. Please check your network and try submitting again.');
        });
    }

    if (btnConfirmSubmit) {
        btnConfirmSubmit.addEventListener('click', executeFinalSubmission);
    }

    // ==========================================
    // 8. Exit Assessment Flow
    // ==========================================
    if (btnExitAssessment && exitModal) {
        btnExitAssessment.addEventListener('click', () => {
            exitModal.classList.remove('d-none');
        });
    }

    if (btnContinueAssessment && exitModal) {
        btnContinueAssessment.addEventListener('click', () => {
            exitModal.classList.add('d-none');
        });
    }

    if (btnConfirmExit && exitModal) {
        btnConfirmExit.addEventListener('click', () => {
            triggerAutoSave();
            exitModal.classList.add('d-none');
            window.location.href = '/dashboard';
        });
    }

    // ==========================================
    // 9. Countdown Timer
    // ==========================================
    let remainingSeconds = config.durationSeconds || 2700;

    function formatTime(secs) {
        const m = Math.floor(secs / 60);
        const s = secs % 60;
        return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    }

    function updateTimerUI() {
        if (timerDisplay) {
            timerDisplay.textContent = formatTime(remainingSeconds);
        }

        if (timerBadge) {
            if (remainingSeconds <= 60) {
                timerBadge.className = 'assessment-timer-badge danger';
            } else if (remainingSeconds <= 300) {
                timerBadge.className = 'assessment-timer-badge warning';
            } else {
                timerBadge.className = 'assessment-timer-badge';
            }
        }
    }

    updateTimerUI();

    const timerInterval = setInterval(() => {
        if (remainingSeconds > 0) {
            remainingSeconds--;
            updateTimerUI();
        } else {
            clearInterval(timerInterval);
            handleTimesUp();
        }
    }, 1000);

    function handleTimesUp() {
        setEditorReadOnly(true);
        if (timesUpModal) {
            timesUpModal.classList.remove('d-none');
        }
        // Auto-submit after short delay
        setTimeout(() => {
            executeFinalSubmission();
        }, 1500);
    }

    // ==========================================
    // 10. Mobile View Switcher (Tabs)
    // ==========================================
    if (tabMobileProblem && tabMobileEditor) {
        tabMobileProblem.addEventListener('click', () => {
            tabMobileProblem.classList.add('active');
            tabMobileEditor.classList.remove('active');
            if (assessmentProblemPane) assessmentProblemPane.classList.remove('mobile-hidden');
            if (assessmentEditorPane) assessmentEditorPane.classList.add('mobile-hidden');
        });

        tabMobileEditor.addEventListener('click', () => {
            tabMobileEditor.classList.add('active');
            tabMobileProblem.classList.remove('active');
            if (assessmentProblemPane) assessmentProblemPane.classList.add('mobile-hidden');
            if (assessmentEditorPane) assessmentEditorPane.classList.remove('mobile-hidden');
            if (monacoEditor) monacoEditor.layout();
        });
    }

    // Initialize Monaco and First Question
    initMonaco();
    renderQuestion(currentQuestionId);
});
